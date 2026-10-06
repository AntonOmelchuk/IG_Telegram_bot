from aiogram import Router, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from firebase_admin import db

from config import ALLY_IMAGE_PATH, MEMBERS_PATH
from utils.localization import get_text

router = Router()

@router.message(Command("ally"))
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

@router.message(Command("top"))
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
