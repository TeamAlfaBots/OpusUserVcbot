import os
import logging

from pyrogram import filters
from pytgcalls.types import MediaStream, AudioQuality

from helpers.i18n import t
from helpers.userbot_manager import manager

logger = logging.getLogger(__name__)

MEME_DIR = "meme"
ALLOWED_EXT = (".mp3", ".ogg", ".wav", ".m4a", ".opus")


def _find_meme_file(name: str):
    """Case-insensitive match of a filename (with or without extension) inside meme/."""
    if not os.path.isdir(MEME_DIR):
        return None

    name_lower = name.lower().strip()
    for filename in os.listdir(MEME_DIR):
        base, ext = os.path.splitext(filename)
        if ext.lower() not in ALLOWED_EXT:
            continue
        if base.lower() == name_lower or filename.lower() == name_lower:
            return os.path.join(MEME_DIR, filename)
    return None


def register_meme_handlers(user_id: int):
    client = manager.get_client(user_id)
    call_py = manager.get_call(user_id)
    if not client or not call_py:
        return

    @client.on_message(filters.me & filters.command("meme", prefixes="."))
    async def meme_cmd(c, message):
        chat_id = message.chat.id
        parts = message.text.split(None, 1)

        if len(parts) < 2:
            await message.reply_text(t("meme_usage"))
            return

        filename = parts[1].strip()
        filepath = _find_meme_file(filename)

        if not filepath:
            await message.reply_text(t("meme_not_found"))
            return

        try:
            stream = MediaStream(
                filepath,
                audio_parameters=AudioQuality.STUDIO,
                video_flags=MediaStream.Flags.IGNORE,
            )
            await call_py.play(chat_id, stream)
            await message.reply_text(t("vc_playing", title=os.path.basename(filepath)))
        except Exception as e:
            logger.exception("meme play error")
            await message.reply_text(f"⚠️ {e}")
