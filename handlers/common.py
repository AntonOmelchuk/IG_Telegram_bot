import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import F, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from firebase_admin import db

from config import USERS_PATH
from handlers.clan import cmd_ally
from handlers.events import cmd_events
from handlers.profile import cmd_profile
from handlers.reminders import cmd_reminders
from handlers.states import SetupStates
from utils.localization import (
    get_lang_keyboard,
    get_main_reply_keyboard,
    get_text,
    get_tz_keyboard,
)

router = Router()


def _user_record(user_id: int) -> dict:
    return db.reference(f"{USERS_PATH}/{user_id}").get() or {}


async def _send_language_prompt(message: types.Message, user_id: int, user_code: str = None):
    prompt = get_text(user_id, "select_lang", user_code)
    await message.answer(prompt, reply_markup=get_lang_keyboard())


async def _send_timezone_prompt(message: types.Message, user_id: int, user_code: str = None, extra_key: str = None):
    text = get_text(user_id, "tz_title", user_code)
    if extra_key:
        text = get_text(user_id, extra_key, user_code) + "\n\n" + text
    await message.answer(text, reply_markup=get_tz_keyboard(user_id, user_code), parse_mode=ParseMode.MARKDOWN)


async def _finish_setup(target: types.Message, user, user_code: str = None):
    text = get_text(user.id, "welcome", user_code, name=user.first_name)
    await target.answer(text, reply_markup=get_main_reply_keyboard(user.id, user_code), parse_mode=ParseMode.MARKDOWN)


@router.message(Command("help"))
async def cmd_help(message: types.Message, state: FSMContext = None):
    if state:
        await state.clear()
    user_id = message.from_user.id
    user_code = message.from_user.language_code

    text = get_text(user_id, "help_text", user_code)
    keyboard = get_main_reply_keyboard(user_id, user_code)

    await message.answer(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)


@router.message(F.text.in_({"📅 Евенти", "📅 Events"}))
async def menu_events_trigger(message: types.Message, state: FSMContext):
    await state.clear()
    await cmd_events(message)


@router.message(F.text.in_({"🔔 Нагадування", "🔔 Reminders"}))
async def menu_reminders_trigger(message: types.Message, state: FSMContext):
    await state.clear()
    await cmd_reminders(message)


@router.message(F.text.in_({"🤝 Альянс", "🤝 Alliance"}))
async def menu_ally_trigger(message: types.Message, state: FSMContext):
    await state.clear()
    await cmd_ally(message)


@router.message(F.text.in_({"👤 Профіль", "👤 Profile"}))
async def menu_profile_trigger(message: types.Message, state: FSMContext):
    await cmd_profile(message, state)


@router.message(F.text.in_({"ℹ️ Довідка", "ℹ️ Help"}))
async def menu_help_trigger(message: types.Message, state: FSMContext):
    await cmd_help(message, state)


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = message.from_user

    db.reference(f"{USERS_PATH}/{user.id}").update({
        "first_name": user.first_name,
        "username": user.username or "",
        "full_name": user.full_name,
    })

    record = _user_record(user.id)
    user_code = record.get("language") or user.language_code

    if not record.get("language"):
        await state.set_state(SetupStates.language)
        await state.update_data(onboarding=True)
        await _send_language_prompt(message, user.id, user_code)
        return

    if not record.get("timezone"):
        await state.set_state(SetupStates.timezone)
        await state.update_data(onboarding=True)
        await _send_timezone_prompt(message, user.id, user_code, extra_key="setup_need_tz")
        return

    await state.clear()
    await _finish_setup(message, user, user_code)


@router.message(Command("language"))
async def cmd_language(message: types.Message, state: FSMContext):
    await state.set_state(SetupStates.language)
    await state.update_data(onboarding=False)
    await _send_language_prompt(message, message.from_user.id, message.from_user.language_code)


@router.callback_query(F.data.startswith("setlang_"))
async def process_lang_callback(callback: types.CallbackQuery, state: FSMContext):
    lang_code = callback.data.split("setlang_")[1]
    user_id = callback.from_user.id
    fsm_data = await state.get_data()
    onboarding = fsm_data.get("onboarding", False)

    db.reference(f"{USERS_PATH}/{user_id}/language").set(lang_code)

    success_text = get_text(user_id, "lang_set_success", lang_code)
    await callback.message.edit_text(success_text, parse_mode=ParseMode.MARKDOWN)

    record = _user_record(user_id)
    if onboarding or not record.get("timezone"):
        await state.set_state(SetupStates.timezone)
        await state.update_data(onboarding=True)
        await _send_timezone_prompt(callback.message, user_id, lang_code, extra_key="setup_need_tz")
    else:
        await state.clear()
        await callback.message.answer(
            get_text(user_id, "lang_changed", lang_code),
            reply_markup=get_main_reply_keyboard(user_id, lang_code),
        )

    await callback.answer()


@router.message(Command("timezone"))
async def cmd_timezone(message: types.Message, state: FSMContext):
    await state.set_state(SetupStates.timezone)
    await state.update_data(onboarding=False)
    await _send_timezone_prompt(message, message.from_user.id, message.from_user.language_code)


@router.callback_query(F.data.startswith("settz_"))
async def process_tz_callback(callback: types.CallbackQuery, state: FSMContext):
    tz_code = callback.data.split("settz_")[1]
    user_id = callback.from_user.id
    user_code = callback.from_user.language_code
    fsm_data = await state.get_data()
    onboarding = fsm_data.get("onboarding", False)

    db.reference(f"{USERS_PATH}/{user_id}/timezone").set(tz_code)
    await state.clear()

    success_text = get_text(user_id, "tz_set_success", user_code, tz=tz_code)
    await callback.message.edit_text(success_text, parse_mode=ParseMode.MARKDOWN)

    if onboarding:
        await _finish_setup(callback.message, callback.from_user, user_code)

    await callback.answer()


def _parse_timezone_input(text: str) -> str | None:
    value = text.strip()
    match = re.match(r"^([+-]?\d{1,2}(\.\d)?)$", value)
    if match:
        val = float(match.group(1))
        if -12 <= val <= 14:
            return f"+{val}" if val > 0 else str(val)
        return None

    try:
        ZoneInfo(value)
        return value
    except (ZoneInfoNotFoundError, Exception):
        return None


@router.message(StateFilter(SetupStates.timezone), F.text, ~F.text.startswith("/"))
async def process_tz_text_input(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_code = message.from_user.language_code
    fsm_data = await state.get_data()
    onboarding = fsm_data.get("onboarding", False)

    formatted_tz = _parse_timezone_input(message.text)
    if not formatted_tz:
        await _send_timezone_prompt(message, user_id, user_code)
        return

    tz_label = formatted_tz if formatted_tz.startswith(("+", "-")) or formatted_tz == "0" else formatted_tz
    if formatted_tz.startswith(("+", "-")) or re.match(r"^\d", formatted_tz):
        tz_label = f"UTC{formatted_tz}" if not str(formatted_tz).upper().startswith("UTC") else formatted_tz

    db.reference(f"{USERS_PATH}/{user_id}/timezone").set(formatted_tz)
    await state.clear()

    if onboarding:
        await _finish_setup(message, message.from_user, user_code)
        return

    success_text = get_text(user_id, "tz_set_success", user_code, tz=tz_label)
    await message.answer(
        success_text,
        reply_markup=get_main_reply_keyboard(user_id, user_code),
        parse_mode=ParseMode.MARKDOWN,
    )


@router.message(StateFilter(SetupStates.language), F.text, ~F.text.startswith("/"))
async def process_lang_text_fallback(message: types.Message):
    await _send_language_prompt(message, message.from_user.id, message.from_user.language_code)
