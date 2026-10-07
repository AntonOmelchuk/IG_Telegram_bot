from aiogram import Dispatcher

from .clan import router as clan_router
from .common import router as common_router
from .events import router as events_router
from .profile import router as profile_router
from .reminders import router as reminders_router


def register_handlers(dp: Dispatcher):
    dp.include_router(profile_router)
    dp.include_router(reminders_router)
    dp.include_router(events_router)
    dp.include_router(clan_router)
    dp.include_router(common_router)
