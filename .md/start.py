from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
)

from config import Config
from helpers.db import add_bot_user
from helpers.i18n import t

MAIN_MENU = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🆘 Support", url=f"https://t.me/{Config.SUPPORT_CHAT}"),
            InlineKeyboardButton("📢 Update", url=f"https://t.me/{Config.UPDATE_CHANNEL}"),
        ],
        [InlineKeyboardButton("📖 Help", callback_data="menu_help")],
        [
            InlineKeyboardButton("🔐 Login", callback_data="menu_login"),
            InlineKeyboardButton("🚪 Logout", callback_data="menu_logout"),
        ],
        [InlineKeyboardButton("👑 Owner", url="https://t.me/OpusBotSupport")],
    ]
)

HELP_MENU = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("🏷 Tag All", callback_data="help_tagall"),
            InlineKeyboardButton("🤖 AutoDM", callback_data="help_autodm"),
        ],
        [
            InlineKeyboardButton("🎵 VcSong", callback_data="help_vcsong"),
            InlineKeyboardButton("😂 Meme", callback_data="help_meme"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="menu_back"),
            InlineKeyboardButton("❌ Close", callback_data="menu_close"),
        ],
    ]
)

BACK_ONLY = InlineKeyboardMarkup(
    [[InlineKeyboardButton("🔙 Back", callback_data="menu_help_back")]]
)


@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client: Client, message: Message):
    await add_bot_user(message.from_user.id)
    caption = t(
        "start_caption",
        full_name=message.from_user.first_name,
        bot_name=Config.BOT_NAME,
    )
    await client.send_photo(
        chat_id=message.chat.id,
        photo=Config.START_IMG_URL,
        caption=caption,
        reply_markup=MAIN_MENU,
    )


@Client.on_callback_query(filters.regex("^menu_help$"))
async def open_help_menu(client: Client, cq: CallbackQuery):
    await cq.message.edit_caption(caption=t("help_menu"), reply_markup=HELP_MENU)


@Client.on_callback_query(filters.regex("^menu_back$"))
async def back_to_main(client: Client, cq: CallbackQuery):
    caption = t(
        "start_caption",
        full_name=cq.from_user.first_name,
        bot_name=Config.BOT_NAME,
    )
    await cq.message.edit_caption(caption=caption, reply_markup=MAIN_MENU)


@Client.on_callback_query(filters.regex("^menu_help_back$"))
async def back_to_help(client: Client, cq: CallbackQuery):
    await cq.message.edit_caption(caption=t("help_menu"), reply_markup=HELP_MENU)


@Client.on_callback_query(filters.regex("^menu_close$"))
async def close_menu(client: Client, cq: CallbackQuery):
    await cq.message.delete()


@Client.on_callback_query(filters.regex("^help_tagall$"))
async def help_tagall(client: Client, cq: CallbackQuery):
    await cq.message.edit_caption(caption=t("tagall_help"), reply_markup=BACK_ONLY)


@Client.on_callback_query(filters.regex("^help_autodm$"))
async def help_autodm(client: Client, cq: CallbackQuery):
    await cq.message.edit_caption(caption=t("autodm_help"), reply_markup=BACK_ONLY)


@Client.on_callback_query(filters.regex("^help_vcsong$"))
async def help_vcsong(client: Client, cq: CallbackQuery):
    await cq.message.edit_caption(caption=t("vcsong_help"), reply_markup=BACK_ONLY)


@Client.on_callback_query(filters.regex("^help_meme$"))
async def help_meme(client: Client, cq: CallbackQuery):
    await cq.message.edit_caption(caption=t("meme_help"), reply_markup=BACK_ONLY)
