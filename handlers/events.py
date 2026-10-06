from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from firebase_admin import db

from config import EVENTS_PATH
from utils.localization import get_user_lang, get_text, get_event_emoji, TEXTS
from services.scheduler import scheduler, send_reminder_notification

router = Router()


@router.message(Command("events"))
async def cmd_events(message: types.Message):
    user_id = message.from_user.id
    user_code = message.from_user.language_code
    snapshot = db.reference(EVENTS_PATH).get()

    if not snapshot:
        await message.answer(get_text(user_id, "no_events", user_code))
        return

    now_ms = int(datetime.now().timestamp() * 1000)
    upcoming_events = []

    for key, data in snapshot.items():
        if not data: continue
        raw_time = data.get("respawnTimestamp") or data.get("timestamp") or data.get("date") or data.get("time")
        if not raw_time: continue

        try:
            event_ms = int(raw_time) if str(raw_time).isdigit() else int(datetime.fromisoformat(str(raw_time)).timestamp() * 1000)
            if event_ms < 10000000000: event_ms *= 1000
        except ValueError:
            continue

        if event_ms >= now_ms:
            title = data.get("title") or data.get("name") or key
            event_type = data.get("type", "")
            upcoming_events.append({"id": key, "title": title, "type": event_type, "ms": event_ms})

    if not upcoming_events:
        await message.answer(get_text(user_id, "no_events", user_code))
        return

    upcoming_events.sort(key=lambda x: x["ms"])

    text = get_text(user_id, "events_header", user_code)
    keyboard = []

    for ev in upcoming_events[:5]:
        emoji = get_event_emoji(ev["title"], ev["type"])
        dt_str = datetime.fromtimestamp(ev["ms"] / 1000).strftime("%d.%m %H:%M")
        text += f"{emoji} **{ev['title']}** — `{dt_str}`\n"

        btn_label = get_text(user_id, "btn_remind", user_code, title=ev["title"])
        keyboard.append([InlineKeyboardButton(text=btn_label, callback_data=f"sub_{ev['id']}")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data.startswith("sub_"))
async def process_event_select(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    event_id = callback.data.split("_")[1]

    event_data = db.reference(f"{EVENTS_PATH}/{event_id}").get()
    if not event_data:
        await callback.answer("Event not found.", show_alert=True)
        return

    title = event_data.get("title") or event_data.get("name") or event_id
    lang = get_user_lang(user_id)
    time_options = TEXTS[lang]["time_options"]

    keyboard = [
        [
            InlineKeyboardButton(text=time_options["5"], callback_data=f"settime_{event_id}_5"),
            InlineKeyboardButton(text=time_options["15"], callback_data=f"settime_{event_id}_15")
        ],
        [
            InlineKeyboardButton(text=time_options["30"], callback_data=f"settime_{event_id}_30"),
            InlineKeyboardButton(text=time_options["60"], callback_data=f"settime_{event_id}_60")
        ]
    ]

    prompt = get_text(user_id, "choose_time", title=title)
    await callback.message.edit_text(prompt, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data.startswith("settime_"))
async def process_reminder_time(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, event_id, minutes_str = callback.data.split("_")
    minutes = int(minutes_str)

    event_data = db.reference(f"{EVENTS_PATH}/{event_id}").get()
    if not event_data:
        await callback.answer("Event not found.", show_alert=True)
        return

    raw_time = event_data.get("respawnTimestamp") or event_data.get("timestamp") or event_data.get("date") or event_data.get("time")
    event_ms = int(raw_time) if str(raw_time).isdigit() else int(datetime.fromisoformat(str(raw_time)).timestamp() * 1000)
    if event_ms < 10000000000: event_ms *= 1000

    event_dt = datetime.fromtimestamp(event_ms / 1000)
    remind_at = event_dt - timedelta(minutes=minutes)

    if remind_at <= datetime.now():
        await callback.answer(get_text(user_id, "time_passed"), show_alert=True)
        return

    title = event_data.get("title") or event_data.get("name") or event_id
    start_time_str = event_dt.strftime("%d.%m %H:%M")

    job_id = f"remind_{user_id}_{event_id}_{minutes}"
    scheduler.add_job(
        send_reminder_notification,
        trigger="date",
        run_date=remind_at,
        args=[user_id, title, minutes, start_time_str],
        id=job_id,
        replace_existing=True
    )

    lang = get_user_lang(user_id)
    time_label = TEXTS[lang]["time_options"].get(str(minutes), f"{minutes}m")
    success_msg = get_text(user_id, "reminder_set", title=title, time=time_label)

    await callback.message.edit_text(success_msg, parse_mode=ParseMode.MARKDOWN)
