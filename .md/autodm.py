from pyrogram import filters

from config import Config
from helpers.db import set_autodm, get_autodm, has_been_greeted, mark_greeted
from helpers.i18n import t
from helpers.userbot_manager import manager


def register_autodm_handlers(user_id: int):
    client = manager.get_client(user_id)
    if not client:
        return

    @client.on_message(filters.me & filters.command("autodm", prefixes="."))
    async def autodm_toggle(c, message):
        parts = message.text.split(None, 1)
        if len(parts) < 2 or parts[1].lower() not in ("on", "off"):
            current = await get_autodm(user_id, Config.AUTODM_DEFAULT)
            await message.reply_text(f"AutoDM is currently: {'ON' if current else 'OFF'}\nUse `.autodm on` or `.autodm off`")
            return

        enabled = parts[1].lower() == "on"
        await set_autodm(user_id, enabled)
        await message.reply_text(t("autodm_on") if enabled else t("autodm_off"))

    @client.on_message(filters.private & filters.incoming & ~filters.me & ~filters.bot)
    async def autodm_greet(c, message):
        # don't greet the owner/self, and only greet real users
        if not message.from_user:
            return

        enabled = await get_autodm(user_id, Config.AUTODM_DEFAULT)
        if not enabled:
            return

        target_id = message.from_user.id
        if await has_been_greeted(user_id, target_id):
            return

        await mark_greeted(user_id, target_id)
        await message.reply_text(
            t("autodm_greet", full_name=message.from_user.first_name)
        )
