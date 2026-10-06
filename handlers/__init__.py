from aiogram import Dispatcher
from .common import router as common_router
from .events import router as events_router
from .clan import router as clan_router

def register_handlers(dp: Dispatcher):
    dp.include_router(common_router)
    dp.include_router(events_router)
    dp.include_router(clan_router)
