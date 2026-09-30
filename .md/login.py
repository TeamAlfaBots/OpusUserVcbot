import logging

from pyrogram import Client, filters
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
)
from pyrogram.types import Message, CallbackQuery

from config import Config
from helpers.db import save_session, delete_session, get_session, get_all_sessions
from helpers.i18n import t
from helpers.userbot_manager import manager

logger = logging.getLogger(__name__)

# in-memory login session state per user_id while they're going through /login
# {user_id: {"step": ..., "api_id":..., "api_hash":..., "phone":..., "client": Client, "phone_code_hash":...}}
pending_logins: dict[int, dict] = {}

LOGIN_TIMEOUT = 300  # seconds, per reply step


async def _login_blocked_reason(user_id: int) -> str | None:
    """
    Returns a locale key explaining why this user can't log in, or None if allowed.
    Personal-use lock: only whitelisted IDs, and never more than MAX_LOGINS at once.
    """
    allowed = set(Config.ALLOWED_USER_IDS)
    if Config.OWNER_ID:
        allowed.add(Config.OWNER_ID)

    if user_id not in allowed:
        return "login_not_allowed"

    already_saved = await get_session(user_id)
    if not already_saved:
        current_count = len(await get_all_sessions())
        if current_count >= Config.MAX_LOGINS:
            return "login_limit_reached"

    return None


@Client.on_message(filters.command("login") & filters.private)
async def login_start(client: Client, message: Message):
    user_id = message.from_user.id

    blocked = await _login_blocked_reason(user_id)
    if blocked:
        await message.reply_text(t(blocked, max_logins=Config.MAX_LOGINS))
        return

    if manager.is_logged_in(user_id):
        await message.reply_text(t("login_already"))
        return

    pending_logins[user_id] = {"step": "api_id"}
    await message.reply_text(t("login_ask_api_id"))


@Client.on_message(filters.command("cancel") & filters.private & filters.reply)
async def cancel_login(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in pending_logins:
        temp_client = pending_logins[user_id].get("client")
        if temp_client:
            try:
                await temp_client.disconnect()
            except Exception:
                pass
        pending_logins.pop(user_id, None)
        await message.reply_text(t("login_cancelled"))


def _is_login_reply(_, __, message: Message) -> bool:
    """Matches any private text message from a user currently mid-login flow."""
    if not message.from_user:
        return False
    return message.from_user.id in pending_logins


login_reply_filter = filters.create(_is_login_reply)


@Client.on_message(filters.private & filters.text & login_reply_filter, group=1)
async def login_flow(client: Client, message: Message):
    user_id = message.from_user.id
    state = pending_logins.get(user_id)
    if not state:
        return

    step = state["step"]
    text = message.text.strip()

    try:
        # ---------------- Step 1: API ID ----------------
        if step == "api_id":
            if not text.isdigit():
                await message.reply_text("⚠️ API ID sirf number hona chahiye. Dobara bhejein.")
                return
            state["api_id"] = int(text)
            state["step"] = "api_hash"
            await message.reply_text(t("login_ask_api_hash"))
            return

        # ---------------- Step 2: API HASH ----------------
        if step == "api_hash":
            state["api_hash"] = text
            state["step"] = "number"
            await message.reply_text(t("login_ask_number"))
            return

        # ---------------- Step 3: Phone Number ----------------
        if step == "number":
            phone = text.replace(" ", "")
            temp_client = Client(
                name=f"login_{user_id}",
                api_id=state["api_id"],
                api_hash=state["api_hash"],
                in_memory=True,
            )
            await temp_client.connect()

            try:
                sent_code = await temp_client.send_code(phone)
            except (ApiIdInvalid, PhoneNumberInvalid) as e:
                await temp_client.disconnect()
                pending_logins.pop(user_id, None)
                await message.reply_text(t("login_failed", error=str(e)))
                return

            state["phone"] = phone
            state["client"] = temp_client
            state["phone_code_hash"] = sent_code.phone_code_hash
            state["step"] = "otp"
            await message.reply_text(t("login_ask_otp"))
            return

        # ---------------- Step 4: OTP ----------------
        if step == "otp":
            otp = text.replace(" ", "")
            temp_client: Client = state["client"]

            try:
                await temp_client.sign_in(
                    phone_number=state["phone"],
                    phone_code_hash=state["phone_code_hash"],
                    phone_code=otp,
                )
            except SessionPasswordNeeded:
                state["step"] = "password"
                await message.reply_text(t("login_ask_password"))
                return
            except (PhoneCodeInvalid, PhoneCodeExpired) as e:
                await message.reply_text(f"⚠️ {e} \u2014 dobara OTP bhejein ya /login se restart karein.")
                return

            await _finalize_login(client, message, user_id, state)
            return

        # ---------------- Step 5: 2FA Password ----------------
        if step == "password":
            temp_client: Client = state["client"]
            try:
                await temp_client.check_password(text)
            except PasswordHashInvalid:
                await message.reply_text("⚠️ Galat password. Dobara bhejein.")
                return

            await _finalize_login(client, message, user_id, state)
            return

    except Exception as e:
        logger.exception("Login flow error")
        pending_logins.pop(user_id, None)
        await message.reply_text(t("login_failed", error=str(e)))


async def _finalize_login(client: Client, message: Message, user_id: int, state: dict):
    temp_client: Client = state["client"]
    me = await temp_client.get_me()
    session_string = await temp_client.export_session_string()

    await save_session(
        user_id=user_id,
        session_string=session_string,
        name=me.first_name or "",
        username=me.username or "",
        number=state["phone"],
    )

    await temp_client.disconnect()
    pending_logins.pop(user_id, None)

    # boot the real persistent userbot client + PyTgCalls
    await manager.start_client(user_id, session_string)

    await message.reply_text(t("login_success", bot_name=Config.BOT_NAME))


@Client.on_message(filters.command("logout") & filters.private)
async def logout_cmd(client: Client, message: Message):
    user_id = message.from_user.id

    if not manager.is_logged_in(user_id) and not await get_session(user_id):
        await message.reply_text(t("logout_none"))
        return

    await manager.stop_client(user_id)
    await delete_session(user_id)
    await message.reply_text(t("logout_success"))


# ---------------- Inline button hooks (from start menu) ----------------

@Client.on_callback_query(filters.regex("^menu_login$"))
async def menu_login_cb(client: Client, cq: CallbackQuery):
    user_id = cq.from_user.id

    blocked = await _login_blocked_reason(user_id)
    if blocked:
        await cq.answer(t(blocked, max_logins=Config.MAX_LOGINS), show_alert=True)
        return

    if manager.is_logged_in(user_id):
        await cq.answer(t("login_already"), show_alert=True)
        return
    pending_logins[user_id] = {"step": "api_id"}
    await cq.answer()
    await client.send_message(cq.from_user.id, t("login_ask_api_id"))


@Client.on_callback_query(filters.regex("^menu_logout$"))
async def menu_logout_cb(client: Client, cq: CallbackQuery):
    user_id = cq.from_user.id
    if not manager.is_logged_in(user_id) and not await get_session(user_id):
        await cq.answer(t("logout_none"), show_alert=True)
        return
    await manager.stop_client(user_id)
    await delete_session(user_id)
    await cq.answer(t("logout_success"), show_alert=True)
