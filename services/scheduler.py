from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.enums import ParseMode
from bot import bot
from utils.localization import get_user_lang, get_event_emoji, get_text, TEXTS

scheduler = AsyncIOScheduler()


async def send_reminder_notification(
    user_id: int,
    title: str,
    minutes: int,
    start_time_str: str,
    event_type: str = ""
):
    lang = get_user_lang(user_id)
    time_label = TEXTS[lang]["time_options"].get(str(minutes), f"{minutes}m")
    emoji = get_event_emoji(title, event_type)
    msg_text = get_text(user_id, "reminder_msg", emoji=emoji title=title, time=time_label, start_time=start_time_str)

    try:
        await bot.send_message(chat_id=user_id, text=msg_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Error sending reminder to {user_id}: {e}")
