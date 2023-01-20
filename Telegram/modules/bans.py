import html
from typing import Optional

from telegram import Update, ParseMode
from telegram.error import BadRequest
from telegram.ext import Filters, CallbackContext
from telegram.utils.helpers import mention_html

from Telegram import (
    DEV_USERS,
    SUDO_USERS,
    SARDEGNA_USERS,
    SUPPORT_USERS,
    OWNER_ID,
    WHITELIST_USERS,
)
from Telegram.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    connection_status,
    is_user_admin,
    is_user_ban_protected,
    is_user_in_chat,
)
from Telegram.modules.helper_funcs.extraction import extract_user_and_text
from Telegram.modules.helper_funcs.string_handling import extract_time
from Telegram.modules.log_channel import loggable, gloggable
from Telegram.modules.helper_funcs.decorators import zaid

from ..modules.helper_funcs.anonymous import user_admin, AdminPerms


@zaid(command='ban', pass_args=True)
@connection_status
@bot_admin
@can_restrict
@user_admin(AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def ban(update: Update, context: CallbackContext) -> Optional[str]:  # sourcery no-metrics
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = context.args
    bot = context.bot
    log_message = ""
    reason = ""
    if message.reply_to_message and message.reply_to_message.sender_chat:
        r = bot.ban_chat_sender_chat(chat_id=chat.id, sender_chat_id=message.reply_to_message.sender_chat.id)
        if r:
            message.reply_text("Saluran {} berhasil dilarang {}".format(
                html.escape(message.reply_to_message.sender_chat.title),
                html.escape(chat.title)
            ),
                parse_mode="html"
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#BANNED\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>Channel:</b> {html.escape(message.reply_to_message.sender_chat.title)} ({message.reply_to_message.sender_chat.id})"
            )
        else:
            message.reply_text("Gagal mencekal saluran")
        return

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Saya ragu itu pengguna.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != "Pengguna tidak ditemukan":
            raise

        message.reply_text("Sepertinya tidak dapat menemukan orang ini.")
        return log_message
    if user_id == context.bot.id:
        message.reply_text("Oh ya, larang diri saya sendiri, noob!")
        return log_message

    if is_user_ban_protected(update, user_id, member) and user not in DEV_USERS:
        if user_id == OWNER_ID:
            message.reply_text("Saya tidak akan pernah melarang pemilik saya.")
        elif user_id in DEV_USERS:
            message.reply_text("Aku tidak bisa bertindak melawan kita sendiri.")
        elif user_id in SUDO_USERS:
            message.reply_text("Sudo saya ban kebal")
        elif user_id in SUPPORT_USERS:
            message.reply_text("Pengguna dukungan saya dilarang kebal")
        elif user_id in SARDEGNA_USERS:
            message.reply_text("Bawa perintah dari Eagle Union untuk melawan Sardegna.")
        elif user_id in WHITELIST_USERS:
            message.reply_text("Neptunus dilarang kebal!")
        else:
            message.reply_text("Pengguna ini memiliki kekebalan dan tidak dapat diblokir.")
        return log_message
    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    )
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        chat.ban_member(user_id)
        # context.bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        context.bot.sendMessage(
            chat.id,
            "{} dilarang oleh {} in <b>{}</b>\n<b>Reason</b>: <code>{}</code>".format(
                mention_html(member.user.id, member.user.first_name), mention_html(user.id, user.first_name),
                message.chat.title, reason
            ),
            parse_mode=ParseMode.HTML,
        )
        return log

    except BadRequest as excp:
        if excp.message == "Pesan balasan tidak ditemukan":
            # Do not reply
            message.reply_text("Dilarang!", quote=False)
            return log
        else:
            log.warning(update)
            log.exception(
                "ERROR melarang pengguna %s dalam obrolan %s (%s) karena %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Sialan, saya tidak bisa melarang pengguna itu.")

    return ""


@zaid(command='tban', pass_args=True)
@connection_status
@bot_admin
@can_restrict
@user_admin(AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def temp_ban(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    reason = ""
    bot, args = context.bot, context.args

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Saya ragu itu pengguna.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != 'Pengguna tidak ditemukan':
            raise
        message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Saya tidak akan BAN sendiri, apakah Anda gila?")
        return log_message

    if is_user_ban_protected(update, user_id, member):
        message.reply_text("Saya tidak merasa seperti itu.")
        return log_message

    if not reason:
        message.reply_text("Anda belum menentukan waktu untuk mencekal pengguna ini!")
        return log_message

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    reason = split_reason[1] if len(split_reason) > 1 else ""
    bantime = extract_time(message, time_val)

    if not bantime:
        return log_message

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        "#TEMP BANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}\n"
        f"<b>Time:</b> {time_val}"
    )
    if reason:
        log += "\n<b>Alasan:</b> {}".format(reason)

    try:
        chat.ban_member(user_id, until_date=bantime)
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            f"Dilarang! Pengguna {mention_html(member.user.id, member.user.first_name)} akan diblokir selama {time_val}.\nAlasan: {reason}",
            parse_mode=ParseMode.HTML,
        )
        return log

    except BadRequest as excp:
        if excp.message == "Pesan balasan tidak ditemukan":
            # Do not reply
            message.reply_text(
                f"Dilarang! Pengguna akan dilarang untuk {time_val}.", quote=False
            )
            return log
        else:
            log.warning(update)
            log.exception(
                "ERROR melarang pengguna %s di obrolan %s (%s) karena %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Sialan, saya tidak bisa melarang pengguna itu.")

    return log_message


@zaid(command='kick', pass_args=True)
@connection_status
@bot_admin
@can_restrict
@user_admin(AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def kick(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Saya ragu itu pengguna.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != 'Pengguna tidak ditemukan':
            raise
        message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Yeahhh aku tidak akan melakukan itu.")
        return log_message

    if is_user_ban_protected(update, user_id):
        message.reply_text("Saya benar-benar berharap bisa menendang pengguna ini....")
        return log_message

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            f"{mention_html(member.user.id, member.user.first_name)} ditendang oleh {mention_html(user.id, user.first_name)} dalam {message.chat.title}\n<b>Alasan</b>: <code>{reason}</code>",
            parse_mode=ParseMode.HTML,
        )
        log = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#KICKED\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
        )
        if reason:
            log += f"\n<b>Alasan:</b> {reason}"

        return log

    else:
        message.reply_text("Sialan, saya tidak bisa menendang pengguna itu.")

    return log_message


@zaid(command='kickme', pass_args=True, filters=Filters.chat_type.groups)
@bot_admin
@can_restrict
def kickme(update: Update, context: CallbackContext):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update, user_id):
        update.effective_message.reply_text("Saya berharap saya bisa... tetapi Anda seorang admin.")
        return

    res = update.effective_chat.unban_member(user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("*mengeluarkanmu dari grup*")
    else:
        update.effective_message.reply_text("Hah? Saya tidak bisa :/")


@zaid(command='unban', pass_args=True)
@connection_status
@bot_admin
@can_restrict
@user_admin(AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def unban(update: Update, context: CallbackContext) -> Optional[str]:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""
    bot, args = context.bot, context.args
    if message.reply_to_message and message.reply_to_message.sender_chat:
        r = bot.unban_chat_sender_chat(chat_id=chat.id, sender_chat_id=message.reply_to_message.sender_chat.id)
        if r:
            message.reply_text("Saluran {} berhasil dibatalkan pencekalannya {}".format(
                html.escape(message.reply_to_message.sender_chat.title),
                html.escape(chat.title)
            ),
                parse_mode="html"
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#UNBANNED\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>Channel:</b> {html.escape(message.reply_to_message.sender_chat.title)} ({message.reply_to_message.sender_chat.id})"
            )
        else:
            message.reply_text("Gagal membatalkan pencekalan saluran")
        return
    user_id, reason = extract_user_and_text(message, args)
    if not user_id:
        message.reply_text("Saya ragu itu pengguna.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message != 'Pengguna tidak ditemukan':
            raise
        message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
        return log_message
    if user_id == bot.id:
        message.reply_text("Bagaimana saya akan membatalkan larangan diri sendiri jika saya tidak ada di sini...?")
        return log_message

    if is_user_in_chat(chat, user_id):
        message.reply_text("Bukankah orang ini sudah ada di sini??")
        return log_message

    chat.unban_member(user_id)
    bot.sendMessage(
        chat.id,
        "{} dibatalkan pencekalannya oleh {} di <b>{}</b>\n<b>Alasan</b>: <code>{}</code>".format(
            mention_html(member.user.id, member.user.first_name), mention_html(user.id, user.first_name),
            message.chat.title, reason
        ),
        parse_mode=ParseMode.HTML,
    )

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    )
    if reason:
        log += f"\n<b>Alasan:</b> {reason}"

    return log


@zaid(command='selfunban', pass_args=True)
@connection_status
@bot_admin
@can_restrict
@gloggable
def selfunban(context: CallbackContext, update: Update) -> Optional[str]:
    message = update.effective_message
    user = update.effective_user
    bot, args = context.bot, context.args
    if user.id not in SUDO_USERS or user.id not in SARDEGNA_USERS:
        return

    try:
        chat_id = int(args[0])
    except:
        message.reply_text("Berikan ID obrolan yang valid.")
        return

    chat = bot.getChat(chat_id)

    try:
        member = chat.get_member(user.id)
    except BadRequest as excp:
        if excp.message == "Pengguna tidak ditemukan":
            message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
            return
        else:
            raise

    if is_user_in_chat(chat, user.id):
        message.reply_text("Bukankah kamu sudah ada di obrolan??")
        return

    chat.unban_member(user.id)
    message.reply_text("Yap, saya telah membatalkan pemblokiran Anda.")

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}"
    )

    return log


from Telegram.modules.language import gs


def get_help(chat):
    return gs(chat, "bans_help")


__mod_name__ = "Bans"
