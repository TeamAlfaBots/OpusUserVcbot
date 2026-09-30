import asyncio
import logging
import os
import random
import re
import time

import aiohttp
import yt_dlp
from py_yt import VideosSearch

from config import Config

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = "downloads"
YT_BASE = "https://www.youtube.com/watch?v="

# Circuit breaker (same idea as the main bots): 3 fails -> block that key for 5 hours
FAIL_THRESHOLD = 3
BLOCK_DURATION = 5 * 3600

YT_REGEX = re.compile(
    r"(https?://)?(www\.|m\.|music\.)?"
    r"(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)

_fail_count: dict[str, int] = {}
_blocked_until: dict[str, float] = {}
_rr_index = 0


def _is_blocked(key: str) -> bool:
    now = time.time()
    if now < _blocked_until.get(key, 0):
        return True
    if _fail_count.get(key, 0) >= FAIL_THRESHOLD:
        _fail_count[key] = 0
    return False


def _mark_fail(key: str):
    _fail_count[key] = _fail_count.get(key, 0) + 1
    if _fail_count[key] >= FAIL_THRESHOLD:
        _blocked_until[key] = time.time() + BLOCK_DURATION
        logger.warning("YT API key blocked for 5 hours after repeated failures")


def _mark_success(key: str):
    _fail_count[key] = 0
    _blocked_until[key] = 0


def extract_video_id(text: str) -> str | None:
    match = YT_REGEX.search(text)
    return match.group(5) if match else None


async def search(query: str) -> dict | None:
    """Returns {'id', 'title', 'duration', 'url'} for the top result, or None."""
    # If the user pasted a YouTube link, no need to search
    vid = extract_video_id(query)
    if vid:
        return {"id": vid, "title": query, "duration": None, "url": YT_BASE + vid}

    try:
        results = await VideosSearch(query, limit=1).next()
    except Exception as e:
        logger.error(f"Search error: {e}")
        return None

    if results and results.get("result"):
        data = results["result"][0]
        return {
            "id": data.get("id"),
            "title": (data.get("title") or query)[:60],
            "duration": data.get("duration"),
            "url": data.get("link"),
        }
    return None


async def _api_download(video_id: str, video: bool) -> str | None:
    """Download via our own API. Response is a direct file stream."""
    global _rr_index

    if not Config.YT_API_URL or not Config.YT_API_KEYS:
        return None

    keys = [k for k in Config.YT_API_KEYS if not _is_blocked(k)]
    if not keys:
        logger.error("All YT API keys are blocked, falling back to yt-dlp")
        return None

    start = _rr_index % len(keys)
    ordered = keys[start:] + keys[:start]
    _rr_index += 1

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    ext = "mp4" if video else "mp3"
    filename = f"{DOWNLOAD_DIR}/{video_id}.{ext}"

    # already downloaded earlier? reuse it
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        return filename

    for key in ordered:
        params = {
            "url": YT_BASE + video_id,
            "type": "video" if video else "audio",
            Config.YT_API_KEY_PARAM: key,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{Config.YT_API_URL}{Config.YT_API_ENDPOINT}",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=90, connect=10),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(f"YT API status: {resp.status}")
                        _mark_fail(key)
                        continue

                    with open(filename, "wb") as f:
                        async for chunk in resp.content.iter_chunked(131072):
                            f.write(chunk)

            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                _mark_success(key)
                return filename

            _mark_fail(key)
        except Exception as e:
            logger.warning(f"YT API error: {e}")
            _mark_fail(key)

    return None


async def _ytdlp_download(video_id: str, video: bool) -> str | None:
    """Fallback: direct yt-dlp (needs cookies/proxy on most VPS IPs)."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    opts = {
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "quiet": True,
        "nocheckcertificate": True,
        "format": "bestvideo+bestaudio" if video else "bestaudio",
    }

    cookie_dir = "cookies"
    if os.path.isdir(cookie_dir):
        cookies = [
            f"{cookie_dir}/{f}"
            for f in os.listdir(cookie_dir)
            if f.endswith(".txt")
        ]
        if cookies:
            opts["cookiefile"] = random.choice(cookies)

    def run():
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(YT_BASE + video_id, download=True)
                return ydl.prepare_filename(info)
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            return None

    return await asyncio.to_thread(run)


async def download(video_id: str, video: bool = False) -> str | None:
    """API first, then yt-dlp fallback. Returns a local file path or None."""
    file = await _api_download(video_id, video)
    if file:
        return file

    logger.warning("API download failed, trying yt-dlp fallback")
    return await _ytdlp_download(video_id, video)
