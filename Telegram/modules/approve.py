import html

from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, Filters
from telegram.utils.helpers import mention_html

import Telegram.modules.sql.approve_sql as sql
from Telegram import SUDO_USERS
from Telegram.modules.helper_funcs.chat_status import user_admin as u_admin
from Telegram.modules.helper_funcs.decorators import zaid, zaidcallback
from Telegram.modules.helper_funcs.extraction import extract_user
from Telegram.modules.log_channel import loggable
from ..modules.helper_funcs.anonymous import user_admin, AdminPerms


@zaid(command='approve', filters=Filters.chat_type.groups)
@loggable
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def approve(update: Update, context: CallbackContext):
    message = update.effective_message
    chat_title = message.chat.title
    chat = update.effective_chat
    args = context.args
    user = update.effective_user
    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text(
            "Saya tidak tahu siapa yang Anda bicarakan, Anda harus menentukan pengguna!"
        )
        return ""
    try:
        member = chat.get_member(user_id)
    except BadRequest:
        return ""
    if member.status == "administrator" or member.status == "creator":
        message.reply_text(
            "Pengguna sudah menjadi admin - kunci, daftar blokir, dan antiflood sudah tidak berlaku untuk mereka."
        )
        return ""
    if sql.is_approved(message.chat_id, user_id):
        message.reply_text(
            f"[{member.user['first_name']}](tg://user?id={member.user['id']}) sudah disetujui di {chat_title}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ""
    sql.approve(message.chat_id, user_id)
    message.reply_text(
        f"[{member.user['first_name']}](tg://user?id={member.user['id']}) telah disetujui di {chat_title}! Mereka "
        f"sekarang akan diabaikan oleh tindakan admin otomatis seperti penguncian, daftar blokir, dan antiflood.",
        parse_mode=ParseMode.MARKDOWN,
    )
    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#APPROVED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}")

    return log_message


@zaid(command='unapprove', filters=Filters.chat_type.groups)
@loggable
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def disapprove(update: Update, context: CallbackContext):
    message = update.effective_message
    chat_title = message.chat.title
    chat = update.effective_chat
    args = context.args
    user = update.effective_user
    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text(
            "Saya tidak tahu siapa yang Anda bicarakan, Anda harus menentukan pengguna!"
        )
        return ""
    try:
        member = chat.get_member(user_id)
    except BadRequest:
        return ""
    if member.status == "administrator" or member.status == "creator":
        message.reply_text("Pengguna ini adalah admin, mereka tidak dapat ditolak.")
        return ""
    if not sql.is_approved(message.chat_id, user_id):
        message.reply_text(f"{member.user['first_name']} belum disetujui!")
        return ""
    sql.disapprove(message.chat_id, user_id)
    message.reply_text(
        f"{member.user['first_name']} tidak lagi disetujui di {chat_title}.")
    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNAPPROVED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(member.user.id, member.user.first_name)}")

    return log_message


@zaid(command='approved', filters=Filters.chat_type.groups)
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def approved(update: Update, _: CallbackContext):
    message = update.effective_message
    chat_title = message.chat.title
    chat = update.effective_chat
    msg = "Pengguna berikut disetujui.\n"
    approved_users = sql.list_approved(message.chat_id)
    for i in approved_users:
        member = chat.get_member(int(i.user_id))
        msg += f"- `{i.user_id}`: {member.user['first_name']}\n"
    if msg.endswith("approved.\n"):
        message.reply_text(f"Tidak ada pengguna yang disetujui {chat_title}.")
        return ""
    else:
        message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


@zaid(command='approval', filters=Filters.chat_type.groups)
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def approval(update, context):
    message = update.effective_message
    chat = update.effective_chat
    args = context.args
    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text(
            "Saya tidak tahu siapa yang Anda bicarakan, Anda harus menentukan pengguna!"
        )
        return ""
    member = chat.get_member(int(user_id))

    if sql.is_approved(message.chat_id, user_id):
        message.reply_text(
            f"{member.user['first_name']} adalah pengguna yang disetujui. Kunci, antiflood, dan daftar blokir tidak berlaku untuk mereka."
        )
    else:
        message.reply_text(
            f"{member.user['first_name']} bukan pengguna yang disetujui. Mereka dipengaruhi oleh perintah normal."
        )


@zaid(command='unapproveall', filters=Filters.chat_type.groups)
def unapproveall(update: Update, _: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    member = chat.get_member(user.id)
    if member.status != "creator" and user.id not in SUDO_USERS:
        update.effective_message.reply_text(
            "Hanya pemilik obrolan yang dapat membatalkan persetujuan semua pengguna sekaligus.")
    else:
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    text="Unapprove all users",
                    callback_data="unapproveall_user")
            ],
            [
                InlineKeyboardButton(
                    text="Cancel", callback_data="unapproveall_cancel")
            ],
        ])
        update.effective_message.reply_text(
            f"Anda yakin ingin membatalkan persetujuan SEMUA pengguna di {chat.title}? Tindakan ini tidak bisa dibatalkan.",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN,
        )


@zaidcallback(pattern=r"unapproveall_.*")
def unapproveall_btn(update: Update, _: CallbackContext):
    query = update.callback_query
    chat = update.effective_chat
    message = update.effective_message
    member = chat.get_member(query.from_user.id)
    if query.data == "unapproveall_user":
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            approved_users = sql.list_approved(chat.id)
            users = [int(i.user_id) for i in approved_users]
            for user_id in users:
                sql.disapprove(chat.id, user_id)

        if member.status == "administrator":
            query.answer("Hanya pemilik obrolan yang dapat melakukan ini.")

        if member.status == "member":
            query.answer("Anda harus menjadi admin untuk melakukan ini.")
    elif query.data == "unapproveall_cancel":
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            message.edit_text(
                "Penghapusan semua pengguna yang disetujui telah dibatalkan.")
            return ""
        if member.status == "administrator":
            query.answer("Hanya pemilik obrolan yang dapat melakukan ini.")
        if member.status == "member":
            query.answer("Anda harus menjadi admin untuk melakukan ini.")


from Telegram.modules.language import gs


def get_help(chat):
    return gs(chat, "approve_help")


__mod_name__ = "Approvals"
