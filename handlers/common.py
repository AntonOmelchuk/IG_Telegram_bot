import re
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from firebase_admin import db
from config import USERS_PATH
from utils.localization import get_text, get_main_reply_keyboard
from handlers.events import cmd_events
from handlers.clan import cmd_top, cmd_ally
from handlers.reminders import cmd_reminders


router = Router()


@router.message(Command("start"))
@router.message(Command("help"))
async def cmd_start_or_help(message: types.Message):
    user_id = message.from_user.id
    user_code = message.from_user.language_code

    text = get_text(user_id, "help_text", user_code)
    keyboard = get_main_reply_keyboard(user_id, user_code)

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


@router.message(F.text.in_({"📅 Евенти", "📅 Events"}))
async def menu_events_trigger(message: types.Message):
    await cmd_events(message)


@router.message(F.text.in_({"🔔 Нагадування", "🔔 Reminders"}))
async def menu_reminders_trigger(message: types.Message):
    await cmd_reminders(message)


@router.message(F.text.in_({"🤝 Альянс", "🤝 Alliance"}))
async def menu_ally_trigger(message: types.Message):
    await cmd_ally(message)


@router.message(F.text.in_({"ℹ️ Довідка", "ℹ️ Help"}))
async def menu_help_trigger(message: types.Message):
    await cmd_start_or_help(message)


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    text = get_text(message.from_user.id, "welcome", message.from_user.language_code, name=message.from_user.first_name)
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("language"))
async def cmd_language(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="setlang_uk"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en")
        ]
    ])
    prompt = get_text(message.from_user.id, "select_lang", message.from_user.language_code)
    await message.answer(prompt, reply_markup=keyboard)


@router.callback_query(F.data.startswith("setlang_"))
async def process_lang_switch(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    db.reference(f"{USERS_PATH}/{user_id}/language").set(lang_code)

    confirm_text = TEXTS[lang_code]["lang_changed"]
    await callback.message.edit_text(confirm_text)


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = get_text(message.from_user.id, "help_text", message.from_user.language_code)
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("timezone"))
async def cmd_timezone(message: types.Message):
    user_id = message.from_user.id
    user_code = message.from_user.language_code

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text(user_id, "tz_btn_br", user_code), callback_data="settz_America/Sao_Paulo")],
        [InlineKeyboardButton(text=get_text(user_id, "tz_btn_ua", user_code), callback_data="settz_Europe/Kyiv")],
        [InlineKeyboardButton(text=get_text(user_id, "tz_btn_eu", user_code), callback_data="settz_Europe/Warsaw")],
        [InlineKeyboardButton(text=get_text(user_id, "tz_btn_vn", user_code), callback_data="settz_Asia/Ho_Chi_Minh")],
        [InlineKeyboardButton(text=get_text(user_id, "tz_btn_utc", user_code), callback_data="settz_UTC")]
    ])

    text = get_text(user_id, "tz_title", user_code)
    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


@router.callback_query(F.data.startswith("settz_"))
async def process_tz_callback(callback: types.CallbackQuery):
    tz_code = callback.data.split("settz_")[1]
    user_id = callback.from_user.id
    user_code = callback.from_user.language_code

    db.reference(f"{USERS_PATH}/{user_id}/timezone").set(tz_code)

    success_text = get_text(user_id, "tz_set_success", user_code, tz=tz_code)
    await callback.message.edit_text(success_text, parse_mode=ParseMode.MARKDOWN)


@router.message(F.text & ~F.text.startswith("/"))
async def process_tz_text_input(message: types.Message):
    text = message.text.strip()
    user_id = message.from_user.id
    user_code = message.from_user.language_code


    match = re.match(r"^([+-]?\d{1,2}(\.\d)?)$", text)

    if match:
        val = float(match.group(1))
        if -12 <= val <= 14:
            formatted_tz = f"+{val}" if val > 0 else str(val)
            tz_label = f"UTC{formatted_tz}"

            db.reference(f"{USERS_PATH}/{user_id}/timezone").set(formatted_tz)

            success_text = get_text(user_id, "tz_set_success", user_code, tz=tz_label)
            await message.answer(success_text, parse_mode=ParseMode.MARKDOWN)
            return
