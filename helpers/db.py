from motor.motor_asyncio import AsyncIOMotorClient

from config import Config

_client = AsyncIOMotorClient(Config.MONGO_URL)
db = _client[Config.DB_NAME]

sessions_col = db["sessions"]       # userbot session strings
users_col = db["users"]             # bot users (for /broadcast)
autodm_col = db["autodm_settings"]  # per-account autodm on/off
autodm_seen_col = db["autodm_seen"] # already-greeted user ids per account


# ---------------- Sessions ----------------

async def save_session(user_id: int, session_string: str, name: str, username: str, number: str):
    await sessions_col.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "session_string": session_string,
                "name": name,
                "username": username or "",
                "number": number,
            }
        },
        upsert=True,
    )


async def get_session(user_id: int):
    return await sessions_col.find_one({"user_id": user_id})


async def get_all_sessions():
    return await sessions_col.find({}).to_list(length=None)


async def delete_session(user_id: int):
    result = await sessions_col.delete_one({"user_id": user_id})
    return result.deleted_count > 0


# ---------------- Bot Users (for broadcast) ----------------

async def add_bot_user(user_id: int):
    await users_col.update_one(
        {"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True
    )


async def get_all_bot_users():
    docs = await users_col.find({}).to_list(length=None)
    return [d["user_id"] for d in docs]


# ---------------- AutoDM Settings ----------------

async def set_autodm(user_id: int, enabled: bool):
    await autodm_col.update_one(
        {"user_id": user_id}, {"$set": {"enabled": enabled}}, upsert=True
    )


async def get_autodm(user_id: int, default: bool = True) -> bool:
    doc = await autodm_col.find_one({"user_id": user_id})
    if doc is None:
        return default
    return doc.get("enabled", default)


async def has_been_greeted(owner_id: int, target_id: int) -> bool:
    doc = await autodm_seen_col.find_one({"owner_id": owner_id, "target_id": target_id})
    return doc is not None


async def mark_greeted(owner_id: int, target_id: int):
    await autodm_seen_col.update_one(
        {"owner_id": owner_id, "target_id": target_id},
        {"$set": {"owner_id": owner_id, "target_id": target_id}},
        upsert=True,
    )
