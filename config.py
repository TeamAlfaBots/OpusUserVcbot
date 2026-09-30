import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ---- Frontend Bot Credentials ----
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

    # ---- Owner ----
    OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

    # ---- Login Restrictions (personal use only) ----
    # Hard cap on how many accounts can ever be logged in at once
    MAX_LOGINS = int(os.environ.get("MAX_LOGINS", "5"))
    # Comma-separated Telegram user IDs allowed to run /login (your own 5 accounts)
    # e.g. ALLOWED_USER_IDS=111111111,222222222,333333333,444444444,555555555
    ALLOWED_USER_IDS = {
        int(x) for x in os.environ.get("ALLOWED_USER_IDS", "").split(",") if x.strip().isdigit()
    }

    # ---- MongoDB ----
    MONGO_URL = os.environ.get("MONGO_URL", "")
    DB_NAME = os.environ.get("DB_NAME", "OpusUserbot")

    # ---- Branding / UI ----
    START_IMG_URL = os.environ.get(
        "START_IMG_URL",
        "https://files.catbox.moe/1yr7xp.png",
    )
    BOT_NAME = os.environ.get("BOT_NAME", "OpusUserbot")
    SUPPORT_CHAT = os.environ.get("SUPPORT_CHAT", "OpusBotSupport")
    UPDATE_CHANNEL = os.environ.get("UPDATE_CHANNEL", "OpusBotupdate")

    # ---- Web / Port (keep-alive ping) ----
    PORT = int(os.environ.get("PORT", "8080"))

    # ---- YouTube Download API (apni khud ki API) ----
    # Response: direct file stream. Call: GET {YT_API_URL}/download?url=<yt url>&type=audio|video&api_key=<key>
    YT_API_URL = os.environ.get("YT_API_URL", "").rstrip("/")
    YT_API_KEYS = [k.strip() for k in os.environ.get("YT_API_KEYS", "").split(",") if k.strip()]
    YT_API_ENDPOINT = os.environ.get("YT_API_ENDPOINT", "/download")
    YT_API_KEY_PARAM = os.environ.get("YT_API_KEY_PARAM", "api_key")

    # ---- Misc ----
    AUTODM_DEFAULT = os.environ.get("AUTODM_DEFAULT", "True") == "True"
    LOCALE = os.environ.get("LOCALE", "en")
