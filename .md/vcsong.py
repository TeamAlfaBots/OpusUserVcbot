import logging

from pyrogram import filters
from pytgcalls.types import MediaStream, AudioQuality, VideoQuality

from helpers import youtube
from helpers.i18n import t
from helpers.userbot_manager import manager

logger = logging.getLogger(__name__)


def register_vcsong_handlers(user_id: int):
    client = manager.get_client(user_id)
    call_py = manager.get_call(user_id)
    if not client or not call_py:
        return

    # chat_id -> track currently playing (our own bookkeeping, no private pytgcalls attrs)
    now_playing: dict[int, dict] = {}

    def _build_stream(path: str, is_video: bool):
        if is_video:
            return MediaStream(
                path,
                audio_parameters=AudioQuality.HIGH,
                video_parameters=VideoQuality.HD_720p,
            )
        return MediaStream(
            path,
            audio_parameters=AudioQuality.HIGH,
            video_flags=MediaStream.Flags.IGNORE,
        )

    async def _start_track(chat_id: int, track: dict):
        path = await youtube.download(track["id"], video=track["video"])
        if not path:
            await client.send_message(chat_id, t("vc_not_found"))
            return False

        await call_py.play(chat_id, _build_stream(path, track["video"]))
        now_playing[chat_id] = track
        await client.send_message(chat_id, t("vc_playing", title=track["title"]))
        return True

    async def _play_next(chat_id: int):
        queue = manager.queues.setdefault(user_id, [])

        while queue:
            next_track = queue.pop(0)
            try:
                if await _start_track(chat_id, next_track):
                    return
            except Exception as e:
                logger.exception("play next error")
                await client.send_message(chat_id, f"⚠️ {e}")

        # queue finished
        now_playing.pop(chat_id, None)
        try:
            await call_py.leave_call(chat_id)
        except Exception:
            pass
        await client.send_message(chat_id, t("vc_queue_empty"))

    @client.on_message(filters.me & filters.command(["play", "vplay"], prefixes="."))
    async def play_cmd(c, message):
        chat_id = message.chat.id
        is_video = message.command[0] == "vplay"
        parts = message.text.split(None, 1)

        if len(parts) < 2:
            await message.reply_text(t("vc_no_song"))
            return

        await message.reply_text("🔎 Searching...")

        found = await youtube.search(parts[1])
        if not found or not found.get("id"):
            await message.reply_text(t("vc_not_found"))
            return

        track = {
            "id": found["id"],
            "title": found["title"],
            "video": is_video,
        }

        queue = manager.queues.setdefault(user_id, [])

        if chat_id in now_playing:
            queue.append(track)
            await message.reply_text(t("vc_queued", title=track["title"]))
            return

        try:
            await _start_track(chat_id, track)
        except Exception as e:
            logger.exception("initial play error")
            await message.reply_text(f"⚠️ {e}")

    @client.on_message(filters.me & filters.command("stop", prefixes="."))
    async def stop_cmd(c, message):
        chat_id = message.chat.id
        try:
            await call_py.pause(chat_id)
            await message.reply_text(t("vc_stopped"))
        except Exception as e:
            await message.reply_text(f"⚠️ {e}")

    @client.on_message(filters.me & filters.command("end", prefixes="."))
    async def end_cmd(c, message):
        chat_id = message.chat.id
        try:
            manager.queues[user_id] = []
            now_playing.pop(chat_id, None)
            await call_py.leave_call(chat_id)
            await message.reply_text(t("vc_ended"))
        except Exception as e:
            await message.reply_text(f"⚠️ {e}")

    @client.on_message(filters.me & filters.command("skip", prefixes="."))
    async def skip_cmd(c, message):
        chat_id = message.chat.id
        queue = manager.queues.setdefault(user_id, [])
        if not queue:
            await message.reply_text(t("vc_queue_empty"))
            return
        await message.reply_text(t("vc_skipped"))
        await _play_next(chat_id)

    @call_py.on_update()
    async def on_update(_, update):
        # pytgcalls fires StreamEnded when a track finishes
        if update.__class__.__name__ == "StreamEnded":
            await _play_next(update.chat_id)
