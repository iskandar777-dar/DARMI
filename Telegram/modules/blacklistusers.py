# Module to blacklist users and prevent them from using commands by @TheRealPhoenix

import Telegram.modules.sql.blacklistusers_sql as sql
from Telegram import (
    DEV_USERS,
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    SARDEGNA_USERS,
    WHITELIST_USERS,
    dispatcher,
)
from Telegram.modules.helper_funcs.chat_status import dev_plus
from Telegram.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from Telegram.modules.log_channel import gloggable
from telegram import ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html
from Telegram.modules.helper_funcs.decorators import zaid

BLACKLISTWHITELIST = (
    [OWNER_ID] + DEV_USERS + SUDO_USERS + WHITELIST_USERS + SUPPORT_USERS
)
BLABLEUSERS = [OWNER_ID] + DEV_USERS

@zaid(command=['ignore', 'addblocklist'], pass_args=True)
@dev_plus
@gloggable
def bl_user(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Saya ragu itu pengguna.")
        return ""

    if user_id == bot.id:
        message.reply_text("Bagaimana saya bisa melakukan pekerjaan saya jika saya mengabaikan diri saya sendiri?")
        return ""

    if user_id in BLACKLISTWHITELIST:
        message.reply_text("Tidak!\nMemperhatikan Bangsa adalah pekerjaan saya.")
        return ""

    try:
        target_user = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message != 'Pengguna tidak ditemukan':
            raise
        message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
        return ''
    sql.blacklist_user(user_id, reason)
    message.reply_text("Saya akan mengabaikan keberadaan pengguna ini!")
    log_message = (
        f"#BLACKLIST\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(target_user.id, target_user.first_name)}"
    )
    if reason:
        log_message += f"\n<b>Alasan:</b> {reason}"

    return log_message

@zaid(command='notice', pass_args=True)
@dev_plus
@gloggable
def unbl_user(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text("Saya ragu itu pengguna.")
        return ""

    if user_id == bot.id:
        message.reply_text("Saya selalu memperhatikan diri saya sendiri.")
        return ""

    try:
        target_user = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message == "Pengguna tidak ditemukan":
            message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
            return ""
        else:
            raise

    if sql.is_user_blacklisted(user_id):

        sql.unblacklist_user(user_id)
        message.reply_text("*notices user*")
        log_message = (
            f"#UNBLACKLIST\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>User:</b> {mention_html(target_user.id, target_user.first_name)}"
        )

        return log_message

    else:
        message.reply_text("I am not ignoring them at all though!")
        return ""

@zaid(command='ignoredlist', pass_args=True)
@dev_plus
def bl_users(update: Update, context: CallbackContext):
    users = []
    bot = context.bot
    for each_user in sql.BLACKLIST_USERS:
        user = bot.get_chat(each_user)
        reason = sql.get_reason(each_user)

        if reason:
            users.append(f"• {mention_html(user.id, user.first_name)} :- {reason}")
        else:
            users.append(f"• {mention_html(user.id, user.first_name)}")

    message = "<b>Pengguna Daftar Hitam</b>\n"
    message += "\n".join(users) if users else "Belum ada yang diabaikan."
    update.effective_message.reply_text(message, parse_mode=ParseMode.HTML)


def __user_info__(user_id):

    if user_id in (777000, 1087968824):
        return ""

    is_blacklisted = sql.is_user_blacklisted(user_id)

    text = "Blacklisted: <b>{}</b>"
    if (
        user_id
        in [777000, 1087968824, dispatcher.bot.id]
        + SUDO_USERS
        + SARDEGNA_USERS
        + WHITELIST_USERS
    ):
        return ""
    if is_blacklisted:
        text = text.format("Yes")
        reason = sql.get_reason(user_id)
        if reason:
            text += f"\nAlasan: <code>{reason}</code>"
    else:
        text = text.format("No")

    return text

__mod_name__ = "Blacklisting Users"
