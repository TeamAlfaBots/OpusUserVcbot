import asyncio
import logging
import threading

from flask import Flask
from pyrogram import Client

from config import Config
from helpers.userbot_manager import manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------- Frontend Bot ----------------
app = Client(
    name="OpusUserbotFrontend",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="plugins"),
)

# ---------------- Keep-alive web server ----------------
web = Flask(__name__)


@web.route("/")
def home():
    return "OpusUserbot is alive!"


def run_web():
    web.run(host="0.0.0.0", port=Config.PORT)


async def main():
    await app.start()
    logger.info("Frontend bot started.")

    await manager.load_all_sessions()
    logger.info(f"Restored {len(manager.clients)} userbot session(s).")

    logger.info("OpusUserbot is up and running.")
    await asyncio.Event().wait()  # run forever


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    asyncio.run(main())
