import html
from typing import Optional

from Telegram import SARDEGNA_USERS
from Telegram.modules.helper_funcs.chat_status import (
    bot_admin,
    can_restrict,
    connection_status,
    is_user_admin,
)
from Telegram.modules.helper_funcs.extraction import extract_user_and_text
from Telegram.modules.helper_funcs.string_handling import extract_time
from Telegram.modules.log_channel import loggable
from telegram import Bot, Chat, ChatPermissions, ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html
from Telegram.modules.language import gs
from Telegram.modules.helper_funcs.decorators import zaid

from ..modules.helper_funcs.anonymous import user_admin, AdminPerms


def check_user(user_id: int, bot: Bot, update: Update) -> Optional[str]:
    if not user_id:
        return "Sepertinya Anda tidak merujuk ke pengguna atau ID yang ditentukan salah.."

    try:
        member = update.effective_chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == 'Pengguna tidak ditemukan':
            return "Sepertinya saya tidak dapat menemukan pengguna ini"
        else:
            raise
    if user_id == bot.id:
        return "Saya tidak akan membungkam diri saya sendiri, Seberapa tinggi Anda?"

    if is_user_admin(update, user_id, member) or user_id in SARDEGNA_USERS:
        return "Tidak bisa. Temukan orang lain untuk dibisukan tetapi bukan yang ini."

    return None


@zaid(command='mute')
@connection_status
@bot_admin
@can_restrict
@user_admin(AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def mute(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args

    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id, reason = extract_user_and_text(message, args)
    reply = check_user(user_id, bot, update)

    if reply:
        message.reply_text(reply)
        return ""

    member = chat.get_member(user_id)

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#MUTE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna:</b> {mention_html(member.user.id, member.user.first_name)}"
    )

    if reason:
        log += f"\n<b>Alasan:</b> {reason}"

    if member.can_send_messages is None or member.can_send_messages:
        chat_permissions = ChatPermissions(can_send_messages=False)
        bot.restrict_chat_member(chat.id, user_id, chat_permissions)
        bot.sendMessage(
            chat.id,
            "{} dibisukan oleh {} di <b>{}</b>\n<b>Alasan</b>: <code>{}</code>".format(
                mention_html(member.user.id, member.user.first_name), mention_html(user.id, user.first_name),
                message.chat.title, reason
            ),
            parse_mode=ParseMode.HTML,
        )
        return log

    else:
        message.reply_text("Pengguna ini sudah dibisukan!")

    return ""


@zaid(command='unmute')
@connection_status
@bot_admin
@can_restrict
@user_admin(AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def unmute(update: Update, context: CallbackContext) -> str:
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id, reason = extract_user_and_text(message, args)
    if not user_id:
        message.reply_text(
            "Anda harus memberi saya nama pengguna untuk disuarakan, atau membalas seseorang untuk disuarakan."
        )
        return ""

    member = chat.get_member(int(user_id))

    if member.status in ["kicked", "left"]:
        message.reply_text(
            "Pengguna ini bahkan tidak ada dalam obrolan, membunyikannya tidak akan membuat mereka berbicara lebih banyak daripada "
            "sudah lakukan!"
        )

    elif (
            member.can_send_messages
            and member.can_send_media_messages
            and member.can_send_other_messages
            and member.can_add_web_page_previews
    ):
        message.reply_text("Pengguna ini sudah memiliki hak untuk berbicara.")
    else:
        chat_permissions = ChatPermissions(
            can_send_messages=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_send_polls=True,
            can_change_info=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
        try:
            bot.restrict_chat_member(chat.id, int(user_id), chat_permissions)
        except BadRequest:
            pass
        bot.sendMessage(
            chat.id,
            "{} disuarakan oleh {} di <b>{}</b>\n<b>Alasan</b>: <code>{}</code>".format(
                mention_html(member.user.id, member.user.first_name), mention_html(user.id, user.first_name),
                message.chat.title, reason
            ),
            parse_mode=ParseMode.HTML,
        )
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#SUARAKAN\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>Pengguna:</b> {mention_html(member.user.id, member.user.first_name)}"
        )
    return ""


@zaid(command=['tmute', 'tempmute'])
@connection_status
@bot_admin
@can_restrict
@user_admin(AdminPerms.CAN_RESTRICT_MEMBERS)
@loggable
def temp_mute(update: Update, context: CallbackContext) -> str:
    bot, args = context.bot, context.args
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    user_id, reason = extract_user_and_text(message, args)
    reply = check_user(user_id, bot, update)

    if reply:
        message.reply_text(reply)
        return ""

    member = chat.get_member(user_id)

    if not reason:
        message.reply_text("Anda belum menentukan waktu untuk membisukan pengguna ini!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    reason = split_reason[1] if len(split_reason) > 1 else ""
    mutetime = extract_time(message, time_val)

    if not mutetime:
        return ""

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#TEMP MUTED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna:</b> {mention_html(member.user.id, member.user.first_name)}\n"
        f"<b>Waktu:</b> {time_val}"
    )
    if reason:
        log += f"\n<b>Alasan:</b> {reason}"

    try:
        if member.can_send_messages is None or member.can_send_messages:
            chat_permissions = ChatPermissions(can_send_messages=False)
            bot.restrict_chat_member(
                chat.id, user_id, chat_permissions, until_date=mutetime
            )
            bot.sendMessage(
                chat.id,
                f"Meredam <b>{html.escape(member.user.first_name)}</b> Untuk {time_val}!\n<b>Alasan</b>: <code>{reason}</code>",
                parse_mode=ParseMode.HTML,
            )
            return log
        else:
            message.reply_text("Pengguna ini sudah dibisukan.")

    except BadRequest as excp:
        if excp.message == "Pesan balasan tidak ditemukan":
            # Do not reply
            message.reply_text(f"Dibisukan untuk {time_val}!", quote=False)
            return log
        else:
            log.warning(update)
            log.exception(
                "KESALAHAN menonaktifkan pengguna %s di obrolan %s (%s) karena %s",
                user_id,
                chat.title,
                chat.id,
                excp.message,
            )
            message.reply_text("Sial, saya tidak bisa membisukan pengguna itu.")

    return ""


def get_help(chat):
    return gs(chat, "muting_help")


__mod_name__ = "Muting"
