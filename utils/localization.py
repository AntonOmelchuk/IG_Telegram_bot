from firebase_admin import db
from config import USERS_PATH, EVENT_EMOJIS

from datetime import timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE = "Europe/Kyiv"

def get_user_tz(user_id: int):
    """
    Повертає об'єкт часового поясу (ZoneInfo або timezone).
    Підтримує IANA назви (Europe/Kyiv) та числові зміщення (+7, -3).
    """
    tz_val = db.reference(f"{USERS_PATH}/{user_id}/timezone").get()

    if not tz_val:
        return ZoneInfo(DEFAULT_TIMEZONE)

    tz_str = str(tz_val).strip()

    # 1. Якщо збережено числове зміщення (наприклад "+7", "-3", "UTC+7", "7")
    clean_tz = tz_str.upper().replace("UTC", "").replace("GMT", "").strip()
    try:
        offset_hours = float(clean_tz)
        return timezone(timedelta(hours=offset_hours))
    except ValueError:
        pass

    # 2. Якщо збережено IANA назву (наприклад "America/Sao_Paulo", "Asia/Ho_Chi_Minh")
    try:
        return ZoneInfo(tz_str)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)

TEXTS = {
    "uk": {
        "welcome": "Вітаємо, **{name}**! Я Менеджер **Iron Gates**.\nНатисни /help щоб побачити список всіх команд.",
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
        "tz_title": (
            "⏰ **Налаштування часового поясу**\n\n"
            "Оберіть свій регіон з кнопок нижче або просто напишіть у чат ваше зміщення від UTC.\n\n"
            "Приклади для вводу:\n"
            "• `+7` або `7` (В'єтнам / Таїланд)\n"
            "• `-3` (Бразилія)\n"
            "• `+2` або `+3` (Європа)\n"
            "• Назва IANA-зони: `America/Sao_Paulo`, `Asia/Ho_Chi_Minh`"
        ),
        "tz_set_success": "✅ Ваш часовий пояс успішно встановлено: **{tz}**\nТепер час евентів у команді `/events` буде відображатися за вашим місцевим часом!",
        "tz_btn_br": "🇧🇷 Бразилія (UTC-3)",
        "tz_btn_ua": "🇺🇦 Україна (UTC+2/+3)",
        "tz_btn_eu": "🇵🇱 Польща / ЄС (UTC+1/+2)",
        "tz_btn_vn": "🇻🇳 В'єтнам (UTC+7)",
        "tz_btn_utc": "🌐 UTC (+0)",
        "no_top_data": "🏆 База даних гравців порожня.",
        "top_title": "🏆 Top 10 Iron Gates — PvP Leaderboard",
        "help_text": "📖 **Інструкція з команд:**\n\n"
                    "🛡️ /events — Найближчі евенти та підписка на нагадування\n"
                    "🤝 /ally — Картинка складу альянсу\n"
                    "🌎 /timezone — Налаштувати свій часовий пояс (UTC / локальний час)\n"
                    "🏆 /top — Топ 10 гравців за PvP\n"
                    "🌐 /language — Змінити мову інтерфейсу\n"
                    "❓ /help — Ця довідка"
    },
    "en": {
        "welcome": "Welcome, **{name}**! I am the **Iron Gates** Manager.\nUse /help see all commands.",
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
        "tz_title": (
            "⏰ **Timezone Settings**\n\n"
            "Choose your region from the buttons below or simply type your UTC offset in chat.\n\n"
            "Input examples:\n"
            "• `+7` or `7` (Vietnam / Thailand)\n"
            "• `-3` (Brazil)\n"
            "• `+2` or `+3` (Europe)\n"
            "• IANA zone name: `America/Sao_Paulo`, `Asia/Ho_Chi_Minh`"
        ),
        "tz_set_success": "✅ Your timezone has been set to: **{tz}**\nNow event times in `/events` will be displayed in your local time!",
        "tz_btn_br": "🇧🇷 Brazil (UTC-3)",
        "tz_btn_ua": "🇺🇦 Ukraine (UTC+2/+3)",
        "tz_btn_eu": "🇵🇱 Poland / EU (UTC+1/+2)",
        "tz_btn_vn": "🇻🇳 Vietnam (UTC+7)",
        "tz_btn_utc": "🌐 UTC (+0)",
        "no_top_data": "🏆 Player database is empty.",
        "top_title": "🏆 Top 10 Iron Gates — PvP Leaderboard",
        "help_text": "📖 **Command Guide:**\n\n"
                    "🛡 /events — Upcoming events and reminder subscriptions\n"
                    "🤝 /ally — Alliance clan roster image\n"
                    "🌎 /timezone — Set your local timezone (UTC / local offset)\n"
                    "🏆 /top — Top 10 PvP Leaderboard\n"
                    "🌐 /language — Switch language\n"
                    "❓ /help — Show this help message"
    }
}

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


def get_user_tz(user_id: int):
    tz_val = db.reference(f"{USERS_PATH}/{user_id}/timezone").get()

    if not tz_val:
        return ZoneInfo(DEFAULT_TIMEZONE)

    tz_str = str(tz_val).strip()

    clean_tz = tz_str.upper().replace("UTC", "").replace("GMT", "").strip()
    try:
        offset_hours = float(clean_tz)
        return timezone(timedelta(hours=offset_hours))
    except ValueError:
        pass

    try:
        return ZoneInfo(tz_str)
    except ZoneInfoNotFoundError:
        print(f"[DEBUG] Zone '{tz_str}' not found, fallback to {DEFAULT_TIMEZONE}", flush=True)
        return ZoneInfo(DEFAULT_TIMEZONE)