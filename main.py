import asyncio
from bot import bot, dp
from services.scheduler import scheduler
from handlers import register_handlers

async def main():
    scheduler.start()

    register_handlers(dp)

    print("🤖 Telegram Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
