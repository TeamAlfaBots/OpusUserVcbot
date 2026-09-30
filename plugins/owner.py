from pyrogram import Client, filters
from pyrogram.types import Message

from config import Config
from helpers.db import get_all_sessions, delete_session, get_all_bot_users, get_session
from helpers.i18n import t
from helpers.userbot_manager import manager

owner_filter = filters.user(Config.OWNER_ID) & filters.private


@Client.on_message(filters.command("activeac") & owner_filter)
async def active_accounts(client: Client, message: Message):
    sessions = await get_all_sessions()
    if not sessions:
        await message.reply_text(t("activeac_none"))
        return

    text = "<b>🗂 Active Accounts</b>\n\n"
    for doc in sessions:
        uid = doc["user_id"]
        status = "🟢 Online" if manager.is_logged_in(uid) else "🔴 Offline (needs restart)"
        text += t(
            "activeac_entry",
            name=doc.get("name", "-"),
            username=doc.get("username", "-") or "-",
            user_id=uid,
            number=doc.get("number", "-"),
            session_status=status,
        )
        text += "\n"

    await message.reply_text(text)


@Client.on_message(filters.command("revoke") & owner_filter)
async def revoke_account(client: Client, message: Message):
    if len(message.command) < 2 or not message.command[1].isdigit():
        await message.reply_text(t("revoke_usage"))
        return

    target_id = int(message.command[1])
    existing = await get_session(target_id)
    if not existing:
        await message.reply_text(t("revoke_not_found"))
        return

    await manager.stop_client(target_id)
    await delete_session(target_id)
    await message.reply_text(t("revoke_success", user_id=target_id))


@Client.on_message(filters.command("broadcast") & owner_filter)
async def broadcast_cmd(client: Client, message: Message):
    if not message.reply_to_message:
        await message.reply_text(t("broadcast_usage"))
        return

    user_ids = await get_all_bot_users()
    success, failed = 0, 0

    for uid in user_ids:
        try:
            await message.reply_to_message.copy(chat_id=uid)
            success += 1
        except Exception:
            failed += 1

    await message.reply_text(t("broadcast_done", success=success, failed=failed))
