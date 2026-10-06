from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from firebase_admin import db
from config import USERS_PATH
from utils.localization import get_user_lang, get_text, TEXTS

router = Router()

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
