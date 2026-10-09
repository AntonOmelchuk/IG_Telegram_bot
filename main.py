import asyncio
from datetime import datetime, timezone

from bot import bot, dp
from handlers import register_handlers
from services.reminders import check_and_send_telegram_reminders, restore_reminders
from services.scheduler import scheduler


async def main():
    scheduler.start()
    scheduler.add_job(
        check_and_send_telegram_reminders,
        "interval",
        minutes=1,
        id="reminders_live_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(timezone.utc),
    )
    restore_reminders()

    register_handlers(dp)

    print("🤖 Telegram Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
