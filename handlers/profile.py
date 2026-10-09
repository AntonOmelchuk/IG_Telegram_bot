from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from firebase_admin import db

from config import USERS_PATH
from handlers.states import ProfileStates
from utils.localization import TEXTS, get_text

MENU_BUTTONS = {
    TEXTS[lang][key]
    for lang in TEXTS
    for key in ("menu_events", "menu_pvp_events", "menu_reminders", "menu_ally", "menu_profile", "menu_help")
}

router = Router()


def _profile_keyboard(user_id: int, user_code: str = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text(user_id, "profile_btn_cp", user_code), callback_data="profile_set_cp"),
            InlineKeyboardButton(text=get_text(user_id, "profile_btn_nick", user_code), callback_data="profile_set_nick"),
        ]
    ])


def _profile_text(user_id: int, user_code: str = None) -> str:
    data = db.reference(f"{USERS_PATH}/{user_id}").get() or {}
    not_set = get_text(user_id, "profile_not_set", user_code)
    cp_name = data.get("cp_name") or not_set
    nickname = data.get("game_nickname") or not_set
    return get_text(user_id, "profile_title", user_code, cp_name=cp_name, nickname=nickname)


async def show_profile(message: types.Message, edit: bool = False):
    user_id = message.chat.id if edit else message.from_user.id
    user_code = message.from_user.language_code if message.from_user else None
    text = _profile_text(user_id, user_code)
    keyboard = _profile_keyboard(user_id, user_code)
    if edit:
        await message.edit_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


@router.message(Command("profile"))
@router.message(F.text.in_({TEXTS["uk"]["menu_profile"], TEXTS["en"]["menu_profile"]}))
async def cmd_profile(message: types.Message, state: FSMContext):
    await state.clear()
    await show_profile(message)


@router.callback_query(F.data == "profile_set_cp")
async def ask_cp_name(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(ProfileStates.cp_name)
    await callback.message.answer(get_text(user_id, "profile_ask_cp", callback.from_user.language_code))
    await callback.answer()


@router.callback_query(F.data == "profile_set_nick")
async def ask_nickname(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await state.set_state(ProfileStates.nickname)
    await callback.message.answer(get_text(user_id, "profile_ask_nick", callback.from_user.language_code))
    await callback.answer()


@router.message(StateFilter(ProfileStates.cp_name), F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def save_cp_name(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    db.reference(f"{USERS_PATH}/{user_id}/cp_name").set(message.text.strip())
    await state.clear()
    await message.answer(get_text(user_id, "profile_saved", message.from_user.language_code))
    await show_profile(message)


@router.message(StateFilter(ProfileStates.nickname), F.text, ~F.text.startswith("/"), ~F.text.in_(MENU_BUTTONS))
async def save_nickname(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    db.reference(f"{USERS_PATH}/{user_id}/game_nickname").set(message.text.strip())
    await state.clear()
    await message.answer(get_text(user_id, "profile_saved", message.from_user.language_code))
    await show_profile(message)
