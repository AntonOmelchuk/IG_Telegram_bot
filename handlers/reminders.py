from datetime import datetime, timezone

from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.reminders import apply_event_reminder, delete_reminder, get_event_for_reminder, get_user_reminders
from utils.localization import get_text, get_time_keyboard, get_user_tz

router = Router()


def _format_reminders(user_id: int, user_code: str = None):
    reminders = get_user_reminders(user_id)
    user_tz = get_user_tz(user_id)
    now = datetime.now(timezone.utc)

    items = []
    now_ms = int(now.timestamp() * 1000)
    for event_id, rem in (reminders or {}).items():
        if not isinstance(rem, dict):
            continue
        minutes = int(rem.get("minutes") or 0)
        _, live_ms = get_event_for_reminder(event_id)
        event_ms = live_ms or rem.get("event_ms")
        if event_ms:
            event_ms = int(event_ms)
            remind_at_ms = event_ms - minutes * 60 * 1000
        else:
            remind_at_ms = rem.get("remind_at_ms")

        if event_ms and event_ms <= now_ms:
            delete_reminder(user_id, event_id)
            continue
        items.append((event_id, rem, event_ms, remind_at_ms))

    items.sort(key=lambda x: int(x[3] or 0))

    if not items:
        return get_text(user_id, "no_active_reminders", user_code), None

    header = get_text(user_id, "active_reminders_header", user_code)
    text = f"{header}\n\n"
    keyboard = []

    for event_id, rem, event_ms, remind_at_ms in items:
        title = rem.get("title") or event_id
        minutes = rem.get("minutes") or 0

        if event_ms:
            start_time_str = datetime.fromtimestamp(int(event_ms) / 1000, tz=timezone.utc).astimezone(user_tz).strftime("%d.%m %H:%M")
        else:
            start_time_str = rem.get("start_time") or "—"

        if remind_at_ms:
            remind_time_str = datetime.fromtimestamp(int(remind_at_ms) / 1000, tz=timezone.utc).astimezone(user_tz).strftime("%d.%m %H:%M")
        else:
            remind_time_str = "—"

        text += get_text(
            user_id,
            "reminder_item",
            user_code,
            title=title,
            start_time=start_time_str,
            minutes=minutes,
            remind_time=remind_time_str,
        ) + "\n\n"

        short_title = title if len(title) <= 16 else title[:15] + "…"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{get_text(user_id, 'btn_edit', user_code)} {short_title}",
                callback_data=f"rmedit_{event_id}",
            ),
            InlineKeyboardButton(
                text=get_text(user_id, "btn_cancel", user_code),
                callback_data=f"rmcancel_{event_id}",
            ),
        ])

    return text.strip(), InlineKeyboardMarkup(inline_keyboard=keyboard)


async def render_reminders(message: types.Message, user_id: int, user_code: str = None, edit: bool = False):
    text, markup = _format_reminders(user_id, user_code)
    if edit:
        await message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(text, reply_markup=markup, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("reminders"))
async def cmd_reminders(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
    await render_reminders(message, message.from_user.id, message.from_user.language_code)


@router.callback_query(F.data.startswith("rmedit_"))
async def reminder_edit(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_code = callback.from_user.language_code
    event_id = callback.data.removeprefix("rmedit_")

    reminders = get_user_reminders(user_id)
    rem = reminders.get(event_id)
    if not rem:
        await callback.answer(get_text(user_id, "reminder_not_found", user_code), show_alert=True)
        await render_reminders(callback.message, user_id, user_code, edit=True)
        return

    title = rem.get("title") or event_id
    keyboard = get_time_keyboard(user_id, event_id, user_code, prefix="edtime")
    rows = list(keyboard.inline_keyboard)
    rows.append([InlineKeyboardButton(text=get_text(user_id, "btn_back", user_code), callback_data="rmback")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    prompt = get_text(user_id, "choose_time", user_code, title=title)
    await callback.message.edit_text(prompt, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    await callback.answer()


@router.callback_query(F.data.startswith("edtime_"))
async def reminder_edit_time(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_code = callback.from_user.language_code
    payload = callback.data.removeprefix("edtime_")
    event_id, minutes_str = payload.rsplit("_", 1)
    minutes = int(minutes_str)

    status, _title = apply_event_reminder(user_id, event_id, minutes)
    if status == "not_found":
        await callback.answer(get_text(user_id, "event_not_found", user_code), show_alert=True)
        return
    if status == "time_passed":
        await callback.answer(get_text(user_id, "time_passed"), show_alert=True)
        return

    await callback.answer()
    await render_reminders(callback.message, user_id, user_code, edit=True)


@router.callback_query(F.data.startswith("rmcancel_"))
async def reminder_cancel(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_code = callback.from_user.language_code
    event_id = callback.data.removeprefix("rmcancel_")

    reminders = get_user_reminders(user_id)
    rem = reminders.get(event_id)
    if not rem:
        await callback.answer(get_text(user_id, "reminder_not_found", user_code), show_alert=True)
    else:
        delete_reminder(user_id, event_id)
        await callback.answer()

    await render_reminders(callback.message, user_id, user_code, edit=True)


@router.callback_query(F.data == "rmback")
async def reminder_back(callback: types.CallbackQuery):
    await render_reminders(callback.message, callback.from_user.id, callback.from_user.language_code, edit=True)
    await callback.answer()
