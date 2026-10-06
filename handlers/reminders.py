from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode

from utils.localization import get_text
from services.scheduler import scheduler

router = Router()


@router.message(Command("reminders"))
@router.message(F.text.in_({"🔔 Нагадування", "🔔 Reminders"}))
async def cmd_reminders(message: types.Message):
    user_id = message.from_user.id
    user_code = message.from_user.language_code

    all_jobs = scheduler.get_jobs()

    user_jobs = [
        job for job in all_jobs
        if job.id.startswith(f"remind_{user_id}_")
    ]

    if not user_jobs:
        await message.answer(get_text(user_id, "no_active_reminders", user_code))
        return

    header = get_text(user_id, "active_reminders_header", user_code)
    text = f"{header}\n\n"

    for job in user_jobs:
        _, title, minutes, start_time_str = job.args
        remind_time_str = job.next_run_time.strftime("%d.%m %H:%M") if job.next_run_time else "—"

        item_text = get_text(
            user_id,
            "reminder_item",
            user_code,
            title=title,
            start_time=start_time_str,
            minutes=minutes,
            remind_time=remind_time_str
        )
        text += f"{item_text}\n\n"

    await message.answer(text.strip(), parse_mode=ParseMode.MARKDOWN)
