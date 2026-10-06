import os
import json
import base64
import asyncio
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import credentials, db

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------------
# FIREBASE INITIALIZATION
# ----------------------------------------------------------------
if os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64"):
    decoded_json = base64.b64decode(os.getenv("FIREBASE_SERVICE_ACCOUNT_BASE64")).decode("utf-8")
    cred_dict = json.loads(decoded_json)
    cred = credentials.Certificate(cred_dict)
else:
    cred = credentials.Certificate("./serviceAccountKey.json")

firebase_admin.initialize_app(cred, {
    "databaseURL": "https://reborn-5f1dc-default-rtdb.europe-west1.firebasedatabase.app"
})

MEMBERS_PATH = "iron_gates_members"
EVENTS_PATH = "regroups/events"
ALLY_IMAGE_PATH = "images/ally"
USERS_PATH = "users"

# ----------------------------------------------------------------
# DICTIONARIES & STYLING
# ----------------------------------------------------------------
EVENT_EMOJIS = {
    "siege": "🏰", "ch": "🛡️", "mtb": "⚔️", "ctb": "🚩",
    "ebc": "🐲", "dm": "☠️", "qa": "🐜", "core": "⚙️",
    "orfen": "🕸️", "zaken": "🏴‍☠️", "tezza": "🎻",
    "baium": "👑", "antharas": "🐉", "valakas": "🔥"
}

TEXTS = {
    "uk": {
        "welcome": "Вітаємо, **{name}**! Я менеджер клану **Iron Gates**.\nОбирай потрібну команду в меню або використовуй /help.",
        "select_lang": "Оберіть мову / Select language:",
        "lang_changed": "✅ Мову успішно змінено на Українську!",
        "no_events": "📅 Наразі немає запланованих евентів.",
        "events_header": "🛡️ **Найближчі евенти:**\n\n",
        "btn_remind": "🔔 Нагадати: {title}",
        "choose_time": "⏰ Оберіть, за скільки часу до початку **{title}** надіслати нагадування:",
        "time_options": {"5": "⏱️ За 5 хв", "15": "⏱️ За 15 хв", "30": "⏱️ За 30 хв", "60": "⏱️ За 1 годину"},
        "reminder_set": "✅ Нагадування встановлено! Я надішлю повідомлення про **{title}** за **{time}**.",
        "time_passed": "❌ Цей час нагадування вже минув!",
        "reminder_msg": "⏰ **НАГАДУВАННЯ!**\nЕвент **{title}** розпочнеться через **{time}**!\n⏰ Час старту: `{start_time}`",
        "no_ally_image": "❌ Зображення альянсу відсутнє в базі даних.",
        "ally_title": "🛡️ Склад Альянсу",
        "no_top_data": "🏆 База даних гравців порожня.",
        "top_title": "🏆 Top 10 Iron Gates — PvP Leaderboard",
        "help_text": "📖 **Інструкція з команд:**\n\n"
                    "🛡️ /events — Найближчі евенти та підписка на нагадування\n"
                    "🤝 /ally — Картинка складу альянсу\n"
                    "🏆 /top — Топ 10 гравців за PvP\n"
                    "🌐 /language — Змінити мову інтерфейсу\n"
                    "❓ /help — Ця довідка"
    },
    "en": {
        "welcome": "Welcome, **{name}**! I am the **Iron Gates** clan manager.\nChoose a command below or use /help.",
        "select_lang": "Select language / Оберіть мову:",
        "lang_changed": "✅ Language successfully changed to English!",
        "no_events": "📅 No upcoming events scheduled at the moment.",
        "events_header": "🛡️ **Upcoming Events:**\n\n",
        "btn_remind": "🔔 Remind: {title}",
        "choose_time": "⏰ Choose how long before **{title}** to send a reminder:",
        "time_options": {"5": "⏱️ 5m before", "15": "⏱️ 15m before", "30": "⏱️ 30m before", "60": "⏱️ 1 hour before"},
        "reminder_set": "✅ Reminder set! I will send a message for **{title}** **{time}** before start.",
        "time_passed": "❌ This reminder time has already passed!",
        "reminder_msg": "⏰ **REMINDER!**\nEvent **{title}** starts in **{time}**!\n⏰ Start time: `{start_time}`",
        "no_ally_image": "❌ Alliance image is missing in database.",
        "ally_title": "🛡️ Alliance Clan Roster",
        "no_top_data": "🏆 Player database is empty.",
        "top_title": "🏆 Top 10 Iron Gates — PvP Leaderboard",
        "help_text": "📖 **Command Guide:**\n\n"
                    "🛡️️ /events — Upcoming events and reminder subscriptions\n"
                    "🤝 /ally — Alliance clan roster image\n"
                    "🏆 /top — Top 10 PvP Leaderboard\n"
                    "🌐 /language — Switch language\n"
                    "❓ /help — Show this help message"
    }
}

# ----------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()
scheduler = AsyncIOScheduler()

def get_user_lang(user_id: int, fallback_code: str = "uk") -> str:
    lang = db.reference(f"{USERS_PATH}/{user_id}/language").get()
    if not lang:
        lang = "uk" if fallback_code and "uk" in fallback_code.lower() else "en"
    return lang if lang in TEXTS else "uk"

def get_text(user_id: int, key: str, fallback_code: str = "uk", **kwargs) -> str:
    lang = get_user_lang(user_id, fallback_code)
    template = TEXTS[lang].get(key, TEXTS["uk"].get(key, ""))
    return template.format(**kwargs) if kwargs else template

def get_event_emoji(title: str = "", event_type: str = "") -> str:
    text = f"{title} {event_type}".lower()
    if "qa" in text or "queen" in text or "ant" in text: return EVENT_EMOJIS["qa"]
    if "core" in text: return EVENT_EMOJIS["core"]
    if "orfen" in text: return EVENT_EMOJIS["orfen"]
    if "zaken" in text: return EVENT_EMOJIS["zaken"]
    if "tezza" in text or "frintezza" in text: return EVENT_EMOJIS["tezza"]
    if "baium" in text: return EVENT_EMOJIS["baium"]
    if "antharas" in text: return EVENT_EMOJIS["antharas"]
    if "valakas" in text: return EVENT_EMOJIS["valakas"]
    if "siege" in text: return EVENT_EMOJIS["siege"]
    if "ch" in text or "hall" in text: return EVENT_EMOJIS["ch"]
    if "mtb" in text: return EVENT_EMOJIS["mtb"]
    if "ctb" in text: return EVENT_EMOJIS["ctb"]
    if "ebc" in text or "dragon" in text: return EVENT_EMOJIS["ebc"]
    if "dm" in text or "deathmatch" in text: return EVENT_EMOJIS["dm"]
    return "🛡️"

async def send_reminder_notification(user_id: int, title: str, minutes: int, start_time_str: str):
    lang = get_user_lang(user_id)
    time_label = TEXTS[lang]["time_options"].get(str(minutes), f"{minutes}m")
    msg_text = get_text(user_id, "reminder_msg", title=title, time=time_label, start_time=start_time_str)
    try:
        await bot.send_message(chat_id=user_id, text=msg_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Error sending reminder to {user_id}: {e}")

# ----------------------------------------------------------------
# COMMAND HANDLERS
# ----------------------------------------------------------------

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    lang = get_user_lang(message.from_user.id, message.from_user.language_code)
    text = get_text(message.from_user.id, "welcome", message.from_user.language_code, name=message.from_user.first_name)
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("language"))
async def cmd_language(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="setlang_uk"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang_en")
        ]
    ])
    prompt = get_text(message.from_user.id, "select_lang", message.from_user.language_code)
    await message.answer(prompt, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("setlang_"))
async def process_lang_switch(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[1]
    user_id = callback.from_user.id
    db.reference(f"{USERS_PATH}/{user_id}/language").set(lang_code)

    confirm_text = TEXTS[lang_code]["lang_changed"]
    await callback.message.edit_text(confirm_text)

@dp.message(Command("events"))
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

@dp.callback_query(F.data.startswith("sub_"))
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

@dp.callback_query(F.data.startswith("settime_"))
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

@dp.message(Command("ally"))
async def cmd_ally(message: types.Message):
    user_id = message.from_user.id
    snapshot = db.reference(ALLY_IMAGE_PATH).get()

    if not snapshot:
        await message.answer(get_text(user_id, "no_ally_image"))
        return

    ally_url = snapshot if isinstance(snapshot, str) else (snapshot.get("url") or snapshot.get("imageUrl"))

    if not ally_url:
        await message.answer(get_text(user_id, "no_ally_image"))
        return

    caption = get_text(user_id, "ally_title")
    await message.answer_photo(photo=ally_url, caption=caption)

@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    user_id = message.from_user.id
    snapshot = db.reference(MEMBERS_PATH).get()

    if not snapshot:
        await message.answer(get_text(user_id, "no_top_data"))
        return

    members_list = []
    for child in snapshot.values():
        if child:
            members_list.append({
                "name": child.get("name", "Unknown"),
                "pvp": int(child.get("pvp", 0))
            })

    members_list.sort(key=lambda x: x["pvp"], reverse=True)
    medals = ["🥇", "🥈", "🥉"]

    text = f"**{get_text(user_id, 'top_title')}**\n\n"
    for idx, member in enumerate(members_list[:10]):
        icon = medals[idx] if idx < 3 else f"**#{idx + 1}**"
        text += f"{icon} **{member['name']}** — `{member['pvp']}` PvP\n"

    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    text = get_text(message.from_user.id, "help_text", message.from_user.language_code)
    await message.answer(text, parse_mode=ParseMode.MARKDOWN)

# ----------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------
async def main():
    scheduler.start()
    print("🤖 Telegram Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())