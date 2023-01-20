import html
import json
import os
from typing import List, Optional

from telegram import Update, ParseMode, TelegramError
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

from Telegram import (
    dispatcher,
    WHITELIST_USERS,
    SARDEGNA_USERS,
    SUPPORT_USERS,
    SUDO_USERS,
    DEV_USERS,
    OWNER_ID,
)
from Telegram.modules.helper_funcs.chat_status import whitelist_plus, dev_plus, sudo_plus
from Telegram.modules.helper_funcs.extraction import extract_user
from Telegram.modules.log_channel import gloggable
from Telegram.modules.sql import nation_sql as sql
from Telegram.modules.helper_funcs.decorators import zaid

def check_user_id(user_id: int, context: CallbackContext) -> Optional[str]:
    bot = context.bot
    if not user_id:
        return "Itu... adalah obrolan! baka ka omae?"

    elif user_id == bot.id:
        return "Ini tidak bekerja seperti itu."

    else:
        return None

@zaid(command='addsudo')
@dev_plus
@gloggable
def addsudo(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        message.reply_text("Anggota ini sudah menjadi pengguna Sudo")
        return ""

    if user_id in SUPPORT_USERS:
        rt += "Meminta Eagle Union untuk mempromosikan pengguna Dukungan ke Sudo."
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        rt += "Meminta Eagle Union untuk mempromosikan pengguna Daftar Putih ke Sudo."
        WHITELIST_USERS.remove(user_id)

    # will add or update their role
    sql.set_royal_role(user_id, "sudos")
    SUDO_USERS.append(user_id)

    update.effective_message.reply_text(
        rt
        + "\nBerhasil mempromosikan {} ke Sudo!".format(
            user_member.first_name
        )
    )

    log_message = (
        f"#SUDO\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>Pengguna:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@zaid(command='addsupport')
@sudo_plus
@gloggable
def addsupport(
    update: Update,
    context: CallbackContext,
) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        rt += "Meminta Eagle Union untuk menurunkan Sudo ini ke Support"
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        message.reply_text("Pengguna ini sudah menjadi pengguna Dukungan.")
        return ""

    if user_id in WHITELIST_USERS:
        rt += "Meminta Eagle Union untuk mempromosikan pengguna Daftar Putih ini ke Dukungan"
        WHITELIST_USERS.remove(user_id)

    sql.set_royal_role(user_id, "supports")
    SUPPORT_USERS.append(user_id)

    update.effective_message.reply_text(
        rt + f"\n{user_member.first_name} telah ditambahkan sebagai pengguna Dukungan!"
    )

    log_message = (
        f"#DUKUNGAN\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>Pengguna:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@zaid(command='addwhitelist')
@sudo_plus
@gloggable
def addwhitelist(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        rt += "Anggota ini adalah pengguna Sudo, Mendemosikan ke pengguna Daftar Putih."
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        rt += "Pengguna ini sudah menjadi pengguna Dukungan, Demoting ke pengguna Daftar Putih."
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        message.reply_text("Pengguna ini sudah menjadi pengguna Daftar Putih.")
        return ""

    sql.set_royal_role(user_id, "whitelists")
    WHITELIST_USERS.append(user_id)

    update.effective_message.reply_text(
        rt + f"\nBerhasil dipromosikan {user_member.first_name} ke pengguna Daftar Putih!"
    )

    log_message = (
        f"#DAFTAR PUTIH\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>Pengguna:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@zaid(command='addsardegna')
@sudo_plus
@gloggable
def addsardegna(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        rt += "Anggota ini adalah pengguna Sudo, Demoting ke Sardegna."
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        rt += "Pengguna ini sudah menjadi pengguna Dukungan, Demoting ke Sardegna."
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        rt += "Pengguna ini sudah menjadi pengguna Daftar Putih, Demoting ke Sardegna."
        WHITELIST_USERS.remove(user_id)

    if user_id in SARDEGNA_USERS:
        message.reply_text("Pengguna ini sudah menjadi Sardegna.")
        return ""

    sql.set_royal_role(user_id, "sardegnas")
    SARDEGNA_USERS.append(user_id)

    update.effective_message.reply_text(
        rt + f"\nBerhasil dipromosikan {user_member.first_name} ke Bangsa Sardegna!"
    )

    log_message = (
        f"#SARDEGNA\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>Pengguna:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@zaid(command='removesudo')
@dev_plus
@gloggable
def removesudo(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        message.reply_text("Meminta Eagle Union untuk menurunkan pengguna ini menjadi Sipil")
        SUDO_USERS.remove(user_id)
        sql.remove_royal(user_id)

        log_message = (
            f"#UNSUDO\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>Pengguna: </b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = "<b>{}:</b>\n".format(html.escape(chat.title)) + log_message

        return log_message

    else:
        message.reply_text("Pengguna ini bukan pengguna Sudo!")
        return ""


@zaid(command='removesupport')
@sudo_plus
@gloggable
def removesupport(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUPPORT_USERS:
        message.reply_text("Meminta Eagle Union untuk menurunkan pengguna ini menjadi Sipil")
        SUPPORT_USERS.remove(user_id)
        sql.remove_royal(user_id)

        log_message = (
            f"#TIDAK DUKUNGAN\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>Pengguna: </b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message

    else:
        message.reply_text("Pengguna ini bukan pengguna Dukungan!")
        return ""


@zaid(command='removewhitelist')
@sudo_plus
@gloggable
def removewhitelist(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in WHITELIST_USERS:
        message.reply_text("Demoting ke pengguna normal")
        WHITELIST_USERS.remove(user_id)
        sql.remove_royal(user_id)

        log_message = (
            f"#UNWHITELIST\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("Pengguna ini bukan pengguna Daftar Putih!")
        return ""


@zaid(command='removesardegna')
@sudo_plus
@gloggable
def removesardegna(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SARDEGNA_USERS:
        message.reply_text("Demoting ke pengguna normal")
        SARDEGNA_USERS.remove(user_id)
        sql.remove_royal(user_id)

        log_message = (
            f"#UNSARDEGNA\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>Pengguna:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("Pengguna ini bukan Bangsa Sardegna!")
        return ""

# I added extra new lines
nations = """ Darmi memiliki tingkat akses bot yang kami sebut sebagai *"Tingkat Bangsa"*
\n*Eagle Union* - Pengembang yang dapat mengakses server bot dan dapat mengeksekusi, mengedit, mengubah kode bot. Bisa juga mengelola Bangsa lain
\n*Tuhan* - Hanya ada satu, pemilik bot.
Pemilik memiliki akses bot yang lengkap, termasuk admin bot di chat tempat Zaid berada.
\n*Royals* - Memiliki akses pengguna super, dapat melakukan gban, mengelola Bangsa yang lebih rendah dari mereka dan menjadi admin di Kigyō.
\n*Sakuras* - Dapatkan akses untuk mencekal pengguna secara global di seluruh Zaid.
\n*Sardegnas* - Sama seperti Neptunian tetapi dapat membatalkan pemblokiran diri mereka sendiri jika diblokir.
\n*Neptunus* - Tidak dapat diblokir, banjir diredam ditendang tetapi dapat diblokir secara manual oleh admin.
\n*Penafian*: Level Bangsa di Kigyō ada untuk pemecahan masalah, dukungan, pelarangan penipu potensial.
Laporkan penyalahgunaan atau tanyakan lebih lanjut tentang hal ini kepada kami di [Null-coder](https://t.me/Shubhanshutya).
"""


def send_nations(update):
    update.effective_message.reply_text(
        nations, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
    )

@zaid(command='removesardegna')
@whitelist_plus
def whitelistlist(update: Update, context: CallbackContext):
    bot = context.bot
    reply = "<b>Bangsa Neptunia yang dikenal :</b>\n"
    for each_user in WHITELIST_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)

            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@zaid(command='sardegnas')
@whitelist_plus
def Sardegnalist(update: Update, context: CallbackContext):
    bot = context.bot
    reply = "<b>Bangsa Sardegna yang dikenal :</b>\n"
    for each_user in SARDEGNA_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@zaid(command=["supportlist", "sakuras"])
@whitelist_plus
def supportlist(update: Update, context: CallbackContext):
    bot = context.bot
    reply = "<b>Bangsa Sakura yang dikenal :</b>\n"
    for each_user in SUPPORT_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@zaid(command=["sudolist", "royals"])
@whitelist_plus
def sudolist(update: Update, context: CallbackContext):
    bot = context.bot
    true_sudo = list(set(SUDO_USERS) - set(DEV_USERS))
    reply = "<b>Bangsa Kerajaan yang dikenal :</b>\n"
    for each_user in true_sudo:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@zaid(command=["devlist", "eagle"])
@whitelist_plus
def devlist(update: Update, context: CallbackContext):
    bot = context.bot
    true_dev = list(set(DEV_USERS) - {OWNER_ID})
    reply = "<b>Anggota Serikat Elang :</b>\n"
    for each_user in true_dev:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


from Telegram.modules.language import gs

