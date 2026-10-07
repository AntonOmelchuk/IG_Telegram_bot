from datetime import datetime, timedelta, timezone

from firebase_admin import db

from config import EVENTS_PATH, USERS_PATH
from services.scheduler import scheduler, send_reminder_notification
from utils.localization import get_user_tz


def parse_event_ms(event_data: dict):
    raw_time = event_data.get("respawnTimestamp") or event_data.get("timestamp") or event_data.get("date") or event_data.get("time")
    if not raw_time:
        return None
    try:
        event_ms = int(raw_time) if str(raw_time).isdigit() else int(datetime.fromisoformat(str(raw_time)).timestamp() * 1000)
        if event_ms < 10000000000:
            event_ms *= 1000
        return event_ms
    except ValueError:
        return None


def reminder_job_id(user_id: int, event_id: str) -> str:
    return f"remind_{user_id}_{event_id}"


def reminders_ref(user_id: int):
    return db.reference(f"{USERS_PATH}/{user_id}/reminders")


def get_user_reminders(user_id: int) -> dict:
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

    scheduler.add_job(
        send_reminder_notification,
        trigger="date",
        run_date=remind_at_utc,
        args=[user_id, event_id, title, minutes, start_time_str, event_type or ""],
        id=reminder_job_id(user_id, event_id),
        replace_existing=True,
    )


def delete_reminder(user_id: int, event_id: str):
    job_id = reminder_job_id(user_id, event_id)
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    reminders_ref(user_id).child(event_id).delete()


def restore_reminders():
    users = db.reference(USERS_PATH).get() or {}
    now = datetime.now(timezone.utc)

    if not isinstance(users, dict):
        return

    for user_id, data in users.items():
        if not isinstance(data, dict):
            continue
        reminders = data.get("reminders") or {}
        if not isinstance(reminders, dict):
            continue

        for event_id, rem in reminders.items():
            if not isinstance(rem, dict):
                continue

            remind_at_ms = rem.get("remind_at_ms")
            if not remind_at_ms:
                minutes = int(rem.get("minutes") or 0)
                event_ms = int(rem.get("event_ms") or 0)
                if not event_ms or not minutes:
                    continue
                remind_at_ms = event_ms - minutes * 60 * 1000

            remind_at = datetime.fromtimestamp(int(remind_at_ms) / 1000, tz=timezone.utc)
            if remind_at <= now:
                db.reference(f"{USERS_PATH}/{user_id}/reminders/{event_id}").delete()
                continue

            title = rem.get("title") or event_id
            minutes = int(rem.get("minutes") or 5)
            start_time_str = rem.get("start_time") or ""
            event_type = rem.get("event_type") or ""

            scheduler.add_job(
                send_reminder_notification,
                trigger="date",
                run_date=remind_at,
                args=[int(user_id), event_id, title, minutes, start_time_str, event_type],
                id=reminder_job_id(user_id, event_id),
                replace_existing=True,
            )


def apply_event_reminder(user_id: int, event_id: str, minutes: int) -> tuple[str, str | None]:
    event_data = db.reference(f"{EVENTS_PATH}/{event_id}").get()
    if not event_data:
        return "not_found", None

    event_ms = parse_event_ms(event_data)
    if event_ms is None:
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
