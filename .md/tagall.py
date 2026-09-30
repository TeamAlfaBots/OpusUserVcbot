import asyncio
import logging

from pyrogram import filters
from pyrogram.errors import FloodWait

from helpers.i18n import t
from helpers.userbot_manager import manager

logger = logging.getLogger(__name__)

TAG_DELAY = 3  # seconds between each tag, keeps flood-wait risk low
BATCH_SIZE = 5  # members tagged per message (kept short to fit "typing animation" feel)


def register_tagall_handlers(user_id: int):
    """
    Registers the .tagall / .cancel handlers on the userbot Client for this user_id.
    Called right after a userbot Client is started (see helpers/userbot_manager.py caller).
    """
    client = manager.get_client(user_id)
    if not client:
        return

    @client.on_message(filters.me & filters.command("tagall", prefixes="."))
    async def tagall_cmd(c, message):
        chat_id = message.chat.id
        custom_text = message.text.split(None, 1)[1] if len(message.text.split(None, 1)) > 1 else ""

        if manager.tagall_tasks.get(user_id):
            await message.reply_text(t("tagall_no_task"))
            return

        manager.tagall_tasks[user_id] = True
        await message.reply_text(t("tagall_started"))

        count = 0
        try:
            members = []
            async for member in c.get_chat_members(chat_id):
                if member.user and not member.user.is_bot and not member.user.is_deleted:
                    members.append(member.user)

            for i in range(0, len(members), BATCH_SIZE):
                if not manager.tagall_tasks.get(user_id):
                    break  # cancelled

                batch = members[i : i + BATCH_SIZE]
                mentions = " ".join(f"[\u200b](tg://user?id={u.id})" for u in batch)
                names = ", ".join(u.first_name for u in batch)

                await c.send_chat_action(chat_id, "typing")
                await asyncio.sleep(1.5)

                body = f"{mentions}{custom_text or names}"
                await c.send_message(chat_id, body)
                count += len(batch)

                await asyncio.sleep(TAG_DELAY)

        except FloodWait as e:
            await asyncio.sleep(e.value)
        except Exception as e:
            logger.exception("tagall error")
        finally:
            manager.tagall_tasks[user_id] = False
            await message.reply_text(t("tagall_done", count=count))

    @client.on_message(filters.me & filters.command("cancel", prefixes="."))
    async def cancel_tagall(c, message):
        if manager.tagall_tasks.get(user_id):
            manager.tagall_tasks[user_id] = False
            await message.reply_text(t("tagall_cancelled"))
        else:
            await message.reply_text(t("tagall_no_task"))
