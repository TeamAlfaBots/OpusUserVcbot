import logging

from pyrogram import Client
from pytgcalls import PyTgCalls

from config import Config
from helpers.db import get_all_sessions, delete_session

logger = logging.getLogger(__name__)


class UserbotManager:
    """
    Holds every logged-in userbot Client + its PyTgCalls instance in memory.
    Keyed by owner's Telegram user_id (the person who ran /login).
    """

    def __init__(self):
        self.clients: dict[int, Client] = {}
        self.calls: dict[int, PyTgCalls] = {}
        # runtime state used by feature plugins
        self.tagall_tasks: dict[int, bool] = {}   # user_id -> is_running flag
        self.autodm_cache: dict[int, bool] = {}   # user_id -> enabled (mirrors DB, avoids extra reads)
        self.queues: dict[int, list] = {}         # user_id -> list of queued tracks

    async def start_client(self, user_id: int, session_string: str) -> Client:
        client = Client(
            name=f"userbot_{user_id}",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            session_string=session_string,
            in_memory=True,
        )
        await client.start()

        call_py = PyTgCalls(client)
        await call_py.start()

        self.clients[user_id] = client
        self.calls[user_id] = call_py
        self.queues.setdefault(user_id, [])

        # register per-account feature handlers now that the client exists
        from plugins.tagall import register_tagall_handlers
        from plugins.autodm import register_autodm_handlers
        from plugins.vcsong import register_vcsong_handlers
        from plugins.meme import register_meme_handlers

        register_tagall_handlers(user_id)
        register_autodm_handlers(user_id)
        register_vcsong_handlers(user_id)
        register_meme_handlers(user_id)

        logger.info(f"Userbot started for {user_id}")
        return client

    async def stop_client(self, user_id: int):
        client = self.clients.pop(user_id, None)
        call_py = self.calls.pop(user_id, None)
        self.queues.pop(user_id, None)
        self.tagall_tasks.pop(user_id, None)

        if call_py:
            try:
                await call_py.stop()
            except Exception:
                pass
        if client:
            try:
                await client.stop()
            except Exception:
                pass

    async def load_all_sessions(self):
        """Called once at startup — restores every saved session from MongoDB."""
        sessions = await get_all_sessions()
        for doc in sessions:
            try:
                await self.start_client(doc["user_id"], doc["session_string"])
            except Exception as e:
                logger.error(f"Failed to restore session for {doc['user_id']}: {e}")
                # session likely revoked/expired on Telegram's side — clean it up
                await delete_session(doc["user_id"])

    def get_client(self, user_id: int) -> Client | None:
        return self.clients.get(user_id)

    def get_call(self, user_id: int) -> PyTgCalls | None:
        return self.calls.get(user_id)

    def is_logged_in(self, user_id: int) -> bool:
        return user_id in self.clients


# single shared instance used across all plugins
manager = UserbotManager()
