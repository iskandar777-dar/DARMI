import html
from typing import Optional

from telegram import ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext
from telegram.utils.helpers import escape_markdown, mention_html

from Telegram.modules.helper_funcs.chat_status import (
    bot_admin,
    can_pin,
    can_promote,
    connection_status,
)
from Telegram.modules.helper_funcs.decorators import zaid
from Telegram.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from Telegram.modules.language import gs
from Telegram.modules.log_channel import loggable
from ..modules.helper_funcs.anonymous import user_admin, AdminPerms


@zaid(command="promote", can_disable=False)
@connection_status
@bot_admin
@can_promote
@user_admin(AdminPerms.CAN_PROMOTE_MEMBERS)
@loggable
def promote(update: Update, context: CallbackContext) -> Optional[str]:
    bot = context.bot
    args = context.args

    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    # promoter = chat.get_member(user.id)
    """
    if (
            bukan (promoter.can_promote_members atau promotor.status == "pembuat")
            dan bukan user.id di SUDO_USERS
    ):
        message.reply_text("Anda tidak memiliki hak yang diperlukan untuk melakukan itu!")
        return
    """
    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text(
            "Sepertinya Anda tidak merujuk ke pengguna atau ID yang ditentukan salah.."
        )
        return

    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if user_member.status in ("administrator", "creator"):
        message.reply_text("Bagaimana saya bisa mempromosikan seseorang yang sudah menjadi admin?")
        return

    if user_id == bot.id:
        message.reply_text("Saya tidak bisa mempromosikan diri saya sendiri! Dapatkan admin untuk melakukannya untuk saya.")
        return

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    try:
        bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=bot_member.can_change_info,
            can_post_messages=bot_member.can_post_messages,
            can_edit_messages=bot_member.can_edit_messages,
            can_delete_messages=bot_member.can_delete_messages,
            can_invite_users=bot_member.can_invite_users,
            # can_promote_members=bot_member.can_promote_members,
            can_restrict_members=bot_member.can_restrict_members,
            can_pin_messages=bot_member.can_pin_messages,
            can_manage_voice_chats=bot_member.can_manage_voice_chats,
        )
    except BadRequest as err:
        if err.message == "User_not_mutual_contact":
            message.reply_text("Saya tidak dapat mempromosikan seseorang yang tidak ada dalam grup.")
        else:
            message.reply_text("Terjadi kesalahan saat mempromosikan.")
        return

    bot.sendMessage(
        chat.id,
        f"<b>{user_member.user.first_name or user_id}</b> dipromosikan oleh <b>{message.from_user.first_name}</b> in <b>{chat.title}</b>",
        parse_mode=ParseMode.HTML,
    )

    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#PROMOTED\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
    )

    return log_message


@zaid(command="demote", can_disable=False)
@connection_status
@bot_admin
@can_promote
@user_admin(AdminPerms.CAN_PROMOTE_MEMBERS)
@loggable
def demote(update: Update, context: CallbackContext) -> Optional[str]:
    bot = context.bot
    args = context.args

    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text(
            "Sepertinya Anda tidak merujuk ke pengguna atau ID yang ditentukan salah.."
        )
        return

    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if user_member.status == "creator":
        message.reply_text("Orang ini MENCIPTAKAN obrolan, bagaimana cara menurunkan mereka?")
        return

    if user_member.status != "administrator":
        message.reply_text("Tidak dapat mendemosikan apa yang tidak dipromosikan!")
        return

    if user_id == bot.id:
        message.reply_text("Aku tidak bisa menurunkan diriku sendiri! Dapatkan admin untuk melakukannya untuk saya.")
        return

    try:
        bot.promoteChatMember(
            chat.id,
            user_id,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_voice_chats=False,
        )

        bot.sendMessage(
            chat.id,
            f"<b>{user_member.user.first_name or user_id or None}</b> diturunkan oleh <b>{message.from_user.first_name or None}</b> dalam <b>{chat.title or None}</b>",
            parse_mode=ParseMode.HTML,
        )

        log_message = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#DEMOTED\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
        )

        return log_message
    except BadRequest:
        message.reply_text(
            "Tidak dapat menurunkan pangkat. Saya mungkin bukan admin, atau status admin diangkat oleh orang lain"
            " pengguna, jadi saya tidak bisa menindak mereka!"
        )
        return


"""
@zaid(command="admincache", can_disable=False)
@u_admin
def refresh_admin(update, _):
    ADMIN_CACHE.pop(update.effective_chat.id)
    update.effective_message.reply_text("Admins cache refreshed!")
"""


@zaid(command="title", can_disable=False)
@connection_status
@bot_admin
@can_promote
@user_admin(AdminPerms.CAN_PROMOTE_MEMBERS)
def set_title(update: Update, context: CallbackContext):
    bot = context.bot
    args = context.args

    chat = update.effective_chat
    message = update.effective_message

    user_id, title = extract_user_and_text(message, args)
    try:
        user_member = chat.get_member(user_id)
    except:
        return

    if not user_id:
        message.reply_text(
            "Sepertinya Anda tidak merujuk ke pengguna atau ID yang ditentukan salah.."
        )
        return

    if user_member.status == "creator":
        message.reply_text(
            "Orang ini MEMBUAT obrolan, bagaimana cara mengatur judul khusus untuknya?"
        )
        return

    if user_member.status != "administrator":
        message.reply_text(
            "Tidak dapat menyetel judul untuk non-admin!\nPromosikan mereka terlebih dahulu untuk menyetel judul khusus!"
        )
        return

    if user_id == bot.id:
        message.reply_text(
            "Saya tidak dapat menetapkan judul saya sendiri! Dapatkan orang yang menjadikan saya admin untuk melakukannya untuk saya."
        )
        return

    if not title:
        message.reply_text("Menetapkan judul kosong tidak melakukan apa-apa!")
        return

    if len(title) > 16:
        message.reply_text(
            "Panjang judul lebih dari 16 karakter.\nMemotongnya menjadi 16 karakter."
        )

    try:
        bot.setChatAdministratorCustomTitle(chat.id, user_id, title)
    except BadRequest:
        message.reply_text("Saya tidak dapat menetapkan judul khusus untuk admin yang tidak saya promosikan!")
        return

    bot.sendMessage(
        chat.id,
        f"Berhasil menyetel judul untuk <code>{user_member.user.first_name or user_id}</code> "
        f"to <code>{html.escape(title[:16])}</code>!",
        parse_mode=ParseMode.HTML,
    )


@zaid(command="pin", can_disable=False)
@bot_admin
@can_pin
@user_admin(AdminPerms.CAN_PIN_MESSAGES)
@loggable
def pin(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    args = context.args

    user = update.effective_user
    chat = update.effective_chat

    is_group = chat.type != "private" and chat.type != "channel"
    prev_message = update.effective_message.reply_to_message

    is_silent = True
    if len(args) >= 1:
        is_silent = (
                args[0].lower() != "notify"
                or args[0].lower() == "loud"
                or args[0].lower() == "violent"
        )

    if prev_message and is_group:
        try:
            bot.pinChatMessage(
                chat.id, prev_message.message_id, disable_notification=is_silent
            )
        except BadRequest as excp:
            if excp.message == "Chat_not_modified":
                pass
            else:
                raise
        log_message = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#PINNED\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}"
        )

        return log_message


@zaid(command="unpin", can_disable=False)
@bot_admin
@can_pin
@user_admin(AdminPerms.CAN_PIN_MESSAGES)
@loggable
def unpin(update: Update, context: CallbackContext) -> str:
    bot = context.bot
    chat = update.effective_chat
    user = update.effective_user

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        else:
            raise

    log_message = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNPINNED\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}"
    )

    return log_message


@zaid(command="invitelink", can_disable=False)
@bot_admin
@user_admin(AdminPerms.CAN_INVITE_USERS)
@connection_status
def invite(update: Update, context: CallbackContext):
    bot = context.bot
    chat = update.effective_chat

    if chat.username:
        update.effective_message.reply_text(f"https://t.me/{chat.username}")
    elif chat.type in [chat.SUPERGROUP, chat.CHANNEL]:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            update.effective_message.reply_text(invitelink)
        else:
            update.effective_message.reply_text(
                "Saya tidak memiliki akses ke tautan undangan, coba ubah izin saya!"
            )
    else:
        update.effective_message.reply_text(
            "Saya hanya bisa memberi Anda tautan undangan untuk grup dan saluran super, maaf!"
        )


@zaid(command=["admin", "admins", "staff"])
def adminlist(update: Update, _):
    administrators = update.effective_chat.get_administrators()
    text = "Admins in *{}*:".format(update.effective_chat.title or "this chat")
    for admin in administrators:
        if not admin.is_anonymous:
            user = admin.user
            name = user.mention_markdown()
            text += "\n -> {} • `{}` • `{}` • `{}`".format(name, user.id, admin.status,
                                                            escape_markdown(
                                                                admin.custom_title) if admin.custom_title else "")

    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def get_help(chat):
    return gs(chat, "admin_help")


__mod_name__ = "Admin"
