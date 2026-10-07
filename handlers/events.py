from datetime import datetime, timezone

from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from firebase_admin import db

from config import EVENTS_PATH
from services.reminders import apply_event_reminder, parse_event_ms
from utils.localization import get_event_emoji, get_text, get_time_keyboard, get_time_label, get_user_tz

router = Router()


@router.message(Command("events"))
async def cmd_events(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
    user_id = message.from_user.id
    user_code = message.from_user.language_code
    snapshot = db.reference(EVENTS_PATH).get()

    user_tz = get_user_tz(user_id)

    if not snapshot:
        await message.answer(get_text(user_id, "no_events", user_code))
        return

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    upcoming_events = []

    for key, data in snapshot.items():
        if not data:
            continue
        event_ms = parse_event_ms(data)
        if event_ms is None:
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

        dt_user = datetime.fromtimestamp(ev["ms"] / 1000, tz=timezone.utc).astimezone(user_tz)
        dt_str = dt_user.strftime("%d.%m %H:%M")

        text += f"{emoji} **{ev['title']}** — `{dt_str}`\n"

        btn_label = get_text(user_id, "btn_remind", user_code, title=ev["title"])
        keyboard.append([InlineKeyboardButton(text=btn_label, callback_data=f"sub_{ev['id']}")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data.startswith("sub_"))
async def process_event_select(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_code = callback.from_user.language_code
    event_id = callback.data.removeprefix("sub_")

    event_data = db.reference(f"{EVENTS_PATH}/{event_id}").get()
    if not event_data:
        await callback.answer(get_text(user_id, "event_not_found", user_code), show_alert=True)
        return

    title = event_data.get("title") or event_data.get("name") or event_id
    keyboard = get_time_keyboard(user_id, event_id, user_code, prefix="settime")

    prompt = get_text(user_id, "choose_time", title=title)
    await callback.message.edit_text(prompt, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()


@router.callback_query(F.data.startswith("settime_"))
async def process_reminder_time(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_code = callback.from_user.language_code
    payload = callback.data.removeprefix("settime_")
    event_id, minutes_str = payload.rsplit("_", 1)
    minutes = int(minutes_str)

    status, title = apply_event_reminder(user_id, event_id, minutes)
    if status == "not_found":
        await callback.answer(get_text(user_id, "event_not_found", user_code), show_alert=True)
        return
    if status == "time_passed":
        await callback.answer(get_text(user_id, "time_passed"), show_alert=True)
        return

    time_label = get_time_label(user_id, minutes, user_code)
    success_msg = get_text(user_id, "reminder_set", title=title, time=time_label)
    await callback.message.edit_text(success_msg, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()
