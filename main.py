import asyncio

from bot import bot, dp
from handlers import register_handlers
from services.reminders import restore_reminders
from services.scheduler import scheduler


async def main():
    scheduler.start()
    restore_reminders()

    register_handlers(dp)

    print("🤖 Telegram Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
