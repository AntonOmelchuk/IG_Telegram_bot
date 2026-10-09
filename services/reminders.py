from datetime import datetime, timedelta, timezone

from firebase_admin import db

from config import EVENTS_PATH, PVP_EVENTS_PATH, USERS_PATH
from services.scheduler import send_reminder_notification
from utils.localization import get_user_tz

# Memory cache to prevent duplicate notification dispatches
SENT_TRACKER = set()


def parse_event_ms(event_data: dict) -> int | None:
    """Parses timestamps from dynamic event payload and converts them to UTC milliseconds."""
    raw_time = (
        event_data.get("respawnTimestamp")
        or event_data.get("timestamp")
        or event_data.get("date")
        or event_data.get("time")
    )
    if not raw_time or isinstance(raw_time, (list, dict)):
        return None
    try:
        ts_val = (
            int(raw_time)
            if str(raw_time).isdigit()
            else int(datetime.fromisoformat(str(raw_time)).timestamp() * 1000)
        )
        if ts_val < 10000000000:
            ts_val *= 1000
        return ts_val
    except ValueError:
        return None


def iter_firebase_children(snapshot):
    """Safely iterates over Firebase snapshot children (handles both list and dict structures)."""
    if not snapshot:
        return
    if isinstance(snapshot, list):
        for i, item in enumerate(snapshot):
            if item:
                yield str(i), item
    elif isinstance(snapshot, dict):
        for key, item in snapshot.items():
            if item:
                yield str(key), item


def pvp_event_id(firebase_key: str, data: dict) -> str:
    """Generates standard event identifier for recurring PvP events."""
    kind = str((data or {}).get("type") or firebase_key).strip().lower()
    return f"pvp_{kind}"


def next_pvp_occurrence_ms(times, tz) -> int | None:
    """Calculates the next upcoming UTC timestamp in milliseconds for daily recurring PvP times."""
    if isinstance(times, str):
        times = [times]
    if not isinstance(times, list):
        return None

    now = datetime.now(tz)
    candidates = []
    for raw in times:
        try:
            hour, minute = map(int, str(raw).split(":")[:2])
        except (ValueError, TypeError):
            continue
        dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=1)
        candidates.append(dt)
    if not candidates:
        return None
    return int(min(candidates).timestamp() * 1000)


def get_pvp_events() -> list[tuple[str, dict]]:
    """Fetches PvP events configuration from Firebase."""
    snapshot = db.reference(PVP_EVENTS_PATH).get()
    items = []
    for key, data in iter_firebase_children(snapshot):
        if isinstance(data, dict):
            items.append((pvp_event_id(key, data), data))
    return items


def find_pvp_event(event_id: str) -> dict | None:
    """Finds a specific PvP event by its ID."""
    for eid, data in get_pvp_events():
        if eid == event_id:
            return data
    return None


def list_upcoming_pvp_events() -> list[dict]:
    """Returns sorted list of upcoming PvP events with UTC timestamps."""
    tz = timezone.utc
    upcoming = []
    for event_id, data in get_pvp_events():
        event_ms = next_pvp_occurrence_ms(data.get("time"), tz)
        if event_ms is None:
            continue
        upcoming.append({
            "id": event_id,
            "title": data.get("name") or data.get("title") or event_id,
            "type": data.get("type") or "",
            "ms": event_ms,
        })
    upcoming.sort(key=lambda x: x["ms"])
    return upcoming


def get_event_for_reminder(event_id: str) -> tuple[dict | None, int | None]:
    """Retrieves event metadata and timestamp for setting up a new reminder."""
    if str(event_id).startswith("pvp_"):
        data = find_pvp_event(event_id)
        if not data:
            return None, None
        event_ms = next_pvp_occurrence_ms(data.get("time"), timezone.utc)
        return data, event_ms

    event_data = db.reference(f"{EVENTS_PATH}/{event_id}").get()
    if not event_data:
        return None, None
    return event_data, parse_event_ms(event_data)


def reminders_ref(user_id: int):
    """Returns Firebase Reference path for user reminders."""
    return db.reference(f"{USERS_PATH}/{user_id}/reminders")


def get_user_reminders(user_id: int) -> dict:
    """Fetches all active reminders for a specific user from Firebase."""
    return reminders_ref(user_id).get() or {}


def save_reminder(
    user_id: int,
    event_id: str,
    title: str,
    minutes: int,
    event_ms: int,
    event_type: str,
    start_time_str: str,
    remind_at,
):
    """Saves user reminder subscription to Firebase."""
    remind_at_utc = remind_at.astimezone(timezone.utc)
    reminders_ref(user_id).child(event_id).set({
        "event_id": event_id,
        "title": title,
        "minutes": minutes,
        "event_ms": event_ms,
        "event_type": event_type or "",
        "start_time": start_time_str,
        "remind_at_ms": int(remind_at_utc.timestamp() * 1000),
    })


def delete_reminder(user_id: int, event_id: str):
    """Deletes user reminder subscription from Firebase."""
    reminders_ref(user_id).child(event_id).delete()


def apply_event_reminder(user_id: int, event_id: str, minutes: int) -> tuple[str, str | None]:
    """Validates and creates an event reminder for the specified user."""
    event_data, event_ms = get_event_for_reminder(event_id)
    if not event_data or event_ms is None:
        return "not_found", None

    user_tz = get_user_tz(user_id)
    event_dt_user = datetime.fromtimestamp(event_ms / 1000, tz=timezone.utc).astimezone(user_tz)
    remind_at = event_dt_user - timedelta(minutes=minutes)

    if remind_at <= datetime.now(user_tz):
        return "time_passed", None

    title = event_data.get("title") or event_data.get("name") or event_id
    start_time_str = event_dt_user.strftime("%d.%m %H:%M")
    event_type = event_data.get("type") or ""

    save_reminder(
        user_id=user_id,
        event_id=event_id,
        title=title,
        minutes=minutes,
        event_ms=event_ms,
        event_type=event_type,
        start_time_str=start_time_str,
        remind_at=remind_at,
    )
    return "ok", title


def restore_reminders():
    """Backward compatibility stub. The cron worker handles dispatching dynamically."""
    pass


def load_events_schedule() -> dict:
    """Live event map from Firebase: id -> {title, timestamp, type, is_pvp}."""
    events_schedule = {}
    events_ref = db.reference(EVENTS_PATH).get() or {}

    if isinstance(events_ref, dict):
        events_iterator = events_ref.items()
    elif isinstance(events_ref, list):
        events_iterator = [(str(idx), item) for idx, item in enumerate(events_ref) if item]
    else:
        events_iterator = []

    for event_id, event_data in events_iterator:
        if not event_data or not isinstance(event_data, dict):
            continue

        event_ms = parse_event_ms(event_data)
        if not event_ms:
            continue

        payload = {
            "title": (
                event_data.get("title")
                or event_data.get("name")
                or event_data.get("event")
                or str(event_id)
            ),
            "timestamp": event_ms,
            "type": event_data.get("type", ""),
            "is_pvp": False,
        }
        events_schedule[str(event_id)] = payload
        if event_data.get("id"):
            events_schedule[str(event_data["id"])] = payload

    for pvp_key, pvp_data in get_pvp_events():
        p_ms = next_pvp_occurrence_ms(
            pvp_data.get("time") or pvp_data.get("times") or [],
            timezone.utc,
        )
        if p_ms is None:
            continue
        events_schedule[pvp_key] = {
            "title": pvp_data.get("name") or pvp_data.get("title") or pvp_key,
            "timestamp": p_ms,
            "type": pvp_data.get("type") or "",
            "is_pvp": True,
        }

    return events_schedule


def _sync_stored_reminder(user_id: int, event_id: str, rem_info: dict, event: dict, user_tz, lead_minutes: int):
    """Rewrite frozen reminder times when Firebase respawn timestamp changes."""
    target_event_ms = int(event["timestamp"])
    stored_ms = rem_info.get("event_ms")
    try:
        stored_ms = int(stored_ms) if stored_ms is not None else None
    except (TypeError, ValueError):
        stored_ms = None

    if stored_ms == target_event_ms:
        return

    event_dt_user = datetime.fromtimestamp(target_event_ms / 1000, tz=timezone.utc).astimezone(user_tz)
    reminders_ref(user_id).child(event_id).update({
        "event_ms": target_event_ms,
        "remind_at_ms": target_event_ms - lead_minutes * 60 * 1000,
        "start_time": event_dt_user.strftime("%d.%m %H:%M"),
        "title": event["title"],
        "event_type": event.get("type") or rem_info.get("event_type") or "",
    })
    print(
        f"⏱ Reminder time updated for user {user_id} / {event_id}: "
        f"{stored_ms} -> {target_event_ms}",
        flush=True,
    )


async def check_and_send_telegram_reminders():
    """Every-minute worker: send from live Firebase times, not frozen reminder timestamps."""
    global SENT_TRACKER

    if len(SENT_TRACKER) > 3000:
        SENT_TRACKER.clear()

    now_utc = datetime.now(timezone.utc)
    current_ms = int(now_utc.timestamp() * 1000)

    try:
        events_schedule = load_events_schedule()
        users_ref = db.reference(USERS_PATH).get() or {}
    except Exception as e:
        print(f"❌ [CRON WORKER ERROR] Failed to fetch data from Firebase: {e}")
        return

    if not users_ref or not isinstance(users_ref, dict):
        return

    for user_id_str, user_data in users_ref.items():
        if not isinstance(user_data, dict):
            continue

        reminders = user_data.get("reminders")
        if not reminders or not isinstance(reminders, dict):
            continue

        try:
            user_id = int(user_id_str)
        except ValueError:
            continue

        user_tz = get_user_tz(user_id)

        for event_id, rem_info in list(reminders.items()):
            if not isinstance(rem_info, dict):
                continue

            event = events_schedule.get(str(event_id))
            if not event:
                continue

            target_event_ms = int(event["timestamp"])
            lead_minutes = int(rem_info.get("minutes") or 5)
            is_pvp = event["is_pvp"]
            remind_at_ms = target_event_ms - lead_minutes * 60 * 1000

            _sync_stored_reminder(user_id, event_id, rem_info, event, user_tz, lead_minutes)

            if target_event_ms <= current_ms:
                if not is_pvp:
                    delete_reminder(user_id, event_id)
                continue

            dedup_key = f"{user_id}_{event_id}_{target_event_ms}_{lead_minutes}"
            if dedup_key in SENT_TRACKER:
                continue

            # Fire once the live remind-at has arrived, as long as the event has not started.
            # Covers respawn time moving earlier after a game-server restart.
            if current_ms < remind_at_ms:
                continue

            event_dt_user = datetime.fromtimestamp(
                target_event_ms / 1000, tz=timezone.utc
            ).astimezone(user_tz)
            start_time_str = event_dt_user.strftime("%d.%m %H:%M")

            await send_reminder_notification(
                user_id=user_id,
                event_id=event_id,
                title=event["title"],
                minutes=lead_minutes,
                start_time_str=start_time_str,
                event_type=event["type"],
            )

            SENT_TRACKER.add(dedup_key)

            if not is_pvp:
                delete_reminder(user_id, event_id)
