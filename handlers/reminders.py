from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from firebase_admin import db

from config import USERS_PATH
from utils.localization import get_text

router = Router()


@router.message(Command("reminders"))
@router.message(F.text.in_({"🔔 Нагадування", "🔔 Reminders"}))
async def cmd_reminders(message: types.Message):
    user_id = message.from_user.id
    user_code = message.from_user.language_code

    user_data = db.reference(f"{USERS_PATH}/{user_id}").get()

    if not user_data or "subscriptions" not in user_data or not user_data["subscriptions"]:
        await message.answer(get_text(user_id, "no_active_reminders", user_code))
        return

    subscriptions = user_data["subscriptions"]
    active_events = [k for k, v in subscriptions.items() if v]

    if not active_events:
        await message.answer(get_text(user_id, "no_active_reminders", user_code))
        return

    header = get_text(user_id, "active_reminders_header", user_code)
    text = f"{header}\n\n"

    for event_key in active_events:
        event_title = get_text(user_id, f"event_{event_key}", user_code) or event_key
        text += f"• **{event_title}**\n"

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)