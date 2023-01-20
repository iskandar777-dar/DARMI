from io import BytesIO
from typing import Optional
import uuid
import re
import json
import time
import csv
import os
import ast
from telegram.ext import CallbackContext
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram import (
    ParseMode,
    Update,
    Chat,
    User,
    MessageEntity,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatAction,
)
from telegram.utils.helpers import mention_html, mention_markdown

from Telegram import (
    dispatcher,
    OWNER_ID,
    SUDO_USERS,
    WHITELIST_USERS,
    GBAN_LOGS,
    log,
)
from Telegram.modules.helper_funcs.chat_status import is_user_admin
from Telegram.modules.helper_funcs.extraction import (
    extract_user,
    extract_unt_fedban,
    extract_user_fban,
)
from Telegram.modules.helper_funcs.string_handling import markdown_parser

import Telegram.modules.sql.feds_sql as sql

from Telegram.modules.helper_funcs.alternate import (
    send_message,
    typing_action,
    send_action,
)
from Telegram.modules.helper_funcs.decorators import zaid, zaidcallback

# Hello bot owner, I spent many hours of my life for feds, Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
#
# Time spended on feds = 10h by #MrYacha
# Time spended on reworking on the whole feds = 22+ hours by @peaktogoo
# Time spended on updating version to v2 = 26+ hours by @AyraHikari
#
# Total spended for making this features is 68+ hours

log.info("Modul federasi asli oleh MrYacha, dikerjakan ulang oleh Mizukito Akito (@peaktogoo) di Telegram.")

# TODO: Fix Loads of code duplication

FBAN_ERRORS = {
    "Pengguna adalah administrator obrolan",
    "Obrolan tidak ditemukan",
    "Tidak cukup hak untuk membatasi/membatalkan anggota obrolan",
    "Pengguna_bukan_peserta",
    "Peer_id_invalid",
    "Obrolan grup dinonaktifkan",
    "Perlu menjadi pengundang pengguna untuk menendangnya dari grup dasar",
    "Chat_admin_required",
    "Hanya pembuat grup dasar yang dapat menendang administrator grup",
    "Saluran_pribadi",
    "Tidak di obrolan",
    "Tidak punya hak untuk mengirim pesan",
}

UNFBAN_ERRORS = {
    "Pengguna adalah administrator obrolan",
    "Obrolan tidak ditemukan",
    "Tidak cukup hak untuk membatasi/membatalkan anggota obrolan",
    "Pengguna_bukan_peserta",
    "Metode hanya tersedia untuk grup super dan obrolan saluran",
    "Tidak di obrolan",
    "Saluran_pribadi",
    "Chat_admin_required",
    "Tidak punya hak untuk mengirim pesan",
}


@typing_action
@zaid(command='newfed')
def new_fed(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message
    if chat.type != "private":
        update.effective_message.reply_text(
            "Anda dapat federasi Anda di PM saya, bukan di grup."
        )
        return
    fednam = message.text.split(None, 1)
    if len(fednam) >= 2:
        fednam = fednam[1]
        fed_id = str(uuid.uuid4())
        fed_name = fednam
        log.info(fed_id)

        # Currently only for creator
        # if fednam == 'Team Nusantara Disciplinary Circle':
        # fed_id = "TeamNusantaraDevs"

        x = sql.new_fed(user.id, fed_name, fed_id)
        if not x:
            update.effective_message.reply_text(
                "Tidak bisa bersekutu! Laporkan di @YorkTownEagleUnion jika masalah terus berlanjut."
            )
            return

        update.effective_message.reply_text(
            "*Anda telah berhasil membuat federasi baru!*"
            "\nNama: `{}`"
            "\nID: `{}`"
            "\n\nGunakan perintah di bawah untuk bergabung dengan federasi:"
            "\n`/joinfed {}`".format(fed_name, fed_id, fed_id),
            parse_mode=ParseMode.MARKDOWN,
        )
        try:
            context.bot.send_message(
                GBAN_LOGS,
                "Federasi <b>{}</b> telah dibuat dengan ID: <pre>{}</pre>".format(
                    fed_name, fed_id
                ),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            log.warning("Tidak dapat mengirim pesan ke GBAN_LOGS")
    else:
        update.effective_message.reply_text(
            "Tolong tuliskan nama federasi"
        )


@typing_action
@zaid(command='delfed', pass_args=True)
def del_fed(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = context.args
    if chat.type != "private":
        update.effective_message.reply_text(
            "Anda dapat menghapus federasi Anda di PM saya, bukan di grup."
        )
        return
    if args:
        is_fed_id = args[0]
        getinfo = sql.get_fed_info(is_fed_id)
        if getinfo is False:
            update.effective_message.reply_text("Federasi ini tidak ditemukan")
            return
        if int(getinfo["owner"]) == int(user.id) or int(user.id) == OWNER_ID:
            fed_id = is_fed_id
        else:
            update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
            return
    else:
        update.effective_message.reply_text("Apa yang harus saya hapus?")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
        return

    update.effective_message.reply_text(
        "Apakah Anda yakin ingin menghapus federasi Anda? Tindakan ini tidak dapat dibatalkan, Anda akan kehilangan seluruh daftar larangan, dan '{}' akan hilang secara permanen.".format(
            getinfo["fname"]
        ),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="⚠️ Hapus Federasi ⚠️",
                        callback_data="rmfed_{}".format(fed_id),
                    )
                ],
                [InlineKeyboardButton(text="Cancel", callback_data="rmfed_cancel")],
            ]
        ),
    )


@typing_action
@zaid(command='chatfed', pass_args=True)
def fed_chat(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    fed_id = sql.get_fed_id(chat.id)

    user_id = update.effective_message.from_user.id
    if not is_user_admin(update, user_id):
        update.effective_message.reply_text(
            "Anda harus menjadi admin untuk menjalankan perintah ini"
        )
        return

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak berada dalam federasi manapun!")
        return

    chat = update.effective_chat  # type: Optional[Chat]
    info = sql.get_fed_info(fed_id)

    text = "Obrolan ini adalah bagian dari federasi berikut:"
    text += "\n{} (ID: <code>{}</code>)".format(info["fname"], fed_id)

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@typing_action
@zaid(command='joinfed', pass_args=True)
def join_fed(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM!",
        )
        return

    message = update.effective_message
    administrators = chat.get_administrators()
    fed_id = sql.get_fed_id(chat.id)
    args = context.args

    if user.id in SUDO_USERS:
        pass
    else:
        for admin in administrators:
            status = admin.status
            if status == "creator":
                if str(admin.user.id) == str(user.id):
                    pass
                else:
                    update.effective_message.reply_text(
                        "Hanya pembuat grup yang dapat menggunakan perintah ini!"
                    )
                    return
    if fed_id:
        message.reply_text("Anda tidak dapat bergabung dengan dua federasi dari satu obrolan")
        return

    if len(args) >= 1:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            message.reply_text("Masukkan ID federasi yang valid")
            return

        x = sql.chat_join_fed(args[0], chat.title, chat.id)
        if not x:
            message.reply_text("Gagal bergabung dengan federasi!")
            return

        get_fedlog = sql.get_fed_log(args[0])
        if get_fedlog:
            if ast.literal_eval(get_fedlog):
                context.bot.send_message(
                    get_fedlog,
                    "Obrolan *{}* telah bergabung dengan federasi *{}*".format(
                        chat.title, getfed["fname"]
                    ),
                    parse_mode="markdown",
                )

        message.reply_text(
            "Obrolan ini telah bergabung dengan federasi: {}!".format(getfed["fname"])
        )


@typing_action
@zaid(command='leavefed')
def leave_fed(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fed_info = sql.get_fed_info(fed_id)

    # administrators = chat.get_administrators().status
    getuser = context.bot.get_chat_member(chat.id, user.id).status
    if getuser in "creator" or user.id in SUDO_USERS:
        if sql.chat_leave_fed(chat.id) is True:
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if ast.literal_eval(get_fedlog):
                    context.bot.send_message(
                        get_fedlog,
                        "Obrolan *{}* telah keluar dari federasi *{}*".format(
                            chat.title, fed_info["fname"]
                        ),
                        parse_mode="markdown",
                    )
            send_message(
                update.effective_message,
                "Obrolan ini telah keluar dari federasi {}!".format(fed_info["fname"]),
            )
        else:
            update.effective_message.reply_text(
                "Bagaimana Anda bisa meninggalkan federasi yang tidak pernah Anda ikuti?!"
            )
    else:
        update.effective_message.reply_text("Hanya pembuat grup yang dapat menggunakan perintah ini!")


@typing_action
@zaid(command='fpromote', pass_args=True)
def user_join_fed(update, context):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id) or user.id in SUDO_USERS:
        user_id = extract_user(msg, args)
        if user_id:
            user = context.bot.get_chat(user_id)
        elif not msg.reply_to_message and not args:
            user = msg.from_user
        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            msg.reply_text("Saya tidak dapat mengekstrak pengguna dari pesan ini")
            return
        else:
            log.warning("error")
        getuser = sql.search_user_in_fed(fed_id, user_id)
        fed_id = sql.get_fed_id(chat.id)
        info = sql.get_fed_info(fed_id)
        get_owner = ast.literal_eval(info["fusers"])["owner"]
        get_owner = context.bot.get_chat(get_owner).id
        if user_id == get_owner:
            update.effective_message.reply_text(
                "Anda tahu bahwa pengguna adalah pemilik federasi, bukan? BAIK?"
            )
            return
        if getuser:
            update.effective_message.reply_text(
                "Saya tidak dapat mempromosikan pengguna yang sudah menjadi admin federasi! Tapi, saya bisa menghapusnya jika Anda mau!"
            )
            return
        if user_id == context.bot.id:
            update.effective_message.reply_text(
                "Saya sudah menjadi admin federasi di semua federasi!"
            )
            return
        res = sql.user_join_fed(fed_id, user_id)
        if res:
            update.effective_message.reply_text("Berhasil Dipromosikan!")
        else:
            update.effective_message.reply_text("Gagal mempromosikan!")
    else:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")


@typing_action
@zaid(command='fdemote', pass_args=True)
def user_demote_fed(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if is_user_fed_owner(fed_id, user.id):
        msg = update.effective_message  # type: Optional[Message]
        user_id = extract_user(msg, args)
        if user_id:
            user = context.bot.get_chat(user_id)

        elif not msg.reply_to_message and not args:
            user = msg.from_user

        elif not msg.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not msg.parse_entities([MessageEntity.TEXT_MENTION])
            )
        ):
            msg.reply_text("Saya tidak dapat mengekstrak pengguna dari pesan ini")
            return
        else:
            log.warning("error")

        if user_id == context.bot.id:
            update.effective_message.reply_text(
                "Hal yang Anda coba turunkan dari saya akan gagal bekerja tanpa saya! Hanya mengatakan."
            )
            return

        if sql.search_user_in_fed(fed_id, user_id) is False:
            update.effective_message.reply_text(
                "Saya tidak dapat menurunkan orang yang bukan admin federasi!"
            )
            return

        res = sql.user_demote_fed(fed_id, user_id)
        if res is True:
            update.effective_message.reply_text("Keluar dari sini!")
        else:
            update.effective_message.reply_text("Demosi gagal!")
    else:
        update.effective_message.reply_text("Hanya pemilik federasi yang dapat melakukan ini!")
        return


@typing_action
@zaid(command='fedinfo', pass_args=True)
def fed_info(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = context.args
    if args:
        fed_id = args[0]
    else:
        fed_id = sql.get_fed_id(chat.id)
        if not fed_id:
            send_message(
                update.effective_message,
                "Grup ini tidak berada dalam federasi manapun!",
            )
            return
    info = sql.get_fed_info(fed_id)
    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    owner = context.bot.get_chat(info["owner"])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except:
        owner_name = owner.first_name
    FEDADMIN = sql.all_fed_users(fed_id)
    FEDADMIN.append(int(owner.id))
    TotalAdminFed = len(FEDADMIN)

    user = update.effective_user  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    info = sql.get_fed_info(fed_id)

    text = "<b>ℹ️ Informasi Federasi:</b>"
    text += "\nFedID: <code>{}</code>".format(fed_id)
    text += "\nNama: {}".format(info["fname"])
    text += "\nPencipta: {}".format(mention_html(owner.id, owner_name))
    text += "\nSemua Admin: <code>{}</code>".format(TotalAdminFed)
    getfban = sql.get_all_fban_users(fed_id)
    text += "\nTotal pengguna yang diblokir: <code>{}</code>".format(len(getfban))
    getfchat = sql.all_fed_chats(fed_id)
    text += "\nJumlah grup di federasi ini: <code>{}</code>".format(
        len(getfchat)
    )

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@typing_action
@zaid(command='fedadmins', pass_args=True)
def fed_admin(update, context):

    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Grup ini tidak berada dalam federasi manapun!")
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    user = update.effective_user  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    info = sql.get_fed_info(fed_id)

    text = "<b>Pengurus Federasi {}:</b>\n\n".format(info["fname"])
    text += "👑 Pemilik:\n"
    owner = context.bot.get_chat(info["owner"])
    try:
        owner_name = owner.first_name + " " + owner.last_name
    except BaseException:
        owner_name = owner.first_name or 'Deleted'
    text += " • {}\n".format(mention_html(owner.id, owner_name))

    members = sql.all_fed_members(fed_id)
    if len(members) == 0:
        text += "\n🔱 Tidak ada admin di federasi ini"
    else:
        text += "\n🔱 Admin:\n"
        for x in members:
            user = context.bot.get_chat(x)
            name = user.first_name or 'Deleted'
            text += " • {}\n".format(mention_html(user.id, user.first_name))

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@typing_action
@zaid(command=['fban', 'fedban'], pass_args=True)
def fed_ban(update, context):  # sourcery no-metrics

    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    message = update.effective_message

    user_id, reason = extract_unt_fedban(message, args)

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)

    if not user_id:
        message.reply_text("Anda sepertinya tidak merujuk ke pengguna")
        return

    if user_id == context.bot.id:
        message.reply_text(
            "Apa yang lebih lucu daripada menendang pembuat grup? Pengorbanan diri."
        )
        return

    if is_user_fed_owner(fed_id, user_id) is True:
        message.reply_text("Mengapa Anda mencoba federasi fban?")
        return

    if is_user_fed_admin(fed_id, user_id) is True:
        message.reply_text("Dia adalah admin federasi, saya tidak bisa melarangnya.")
        return

    if user_id == OWNER_ID:
        message.reply_text("Itu ide yang sangat BODOH!")
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text("Saya tidak akan melarang Bangsa Kerajaan")
        return

    if int(user_id) in WHITELIST_USERS:
        message.reply_text("Orang ini tidak dapat diblokir!")
        return

    if int(user_id) in (777000, 1087968824):
        message.reply_text("Saya tidak melarang bot Telegram.")
        return

    try:
        user_chat = context.bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_name = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_uname = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            send_message(update.effective_message, excp.message)
            return
        elif not len(str(user_id)) == 9:
            send_message(update.effective_message, "Itu bukan pengguna!")
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_name = "user({})".format(user_id)
        fban_user_lname = None
        fban_user_uname = None

    if isvalid and user_chat.type != "private":
        send_message(update.effective_message, "Itu bukan pengguna!")
        return

    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_name)
    else:
        user_target = fban_user_name

    if fban:
        fed_name = info["fname"]
        if reason == "":
            reason = "Tidak ada alasan yang diberikan."

        temp = sql.un_fban_user(fed_id, fban_user_id)
        if not temp:
            message.reply_text("Gagal memperbarui alasan fedban!")
            return
        x = sql.fban_user(
            fed_id,
            fban_user_id,
            fban_user_name,
            fban_user_lname,
            fban_user_uname,
            reason,
            int(time.time()),
        )
        if not x:
            message.reply_text("Gagal melarang dari federasi!")
            return

        fed_chats = sql.all_fed_chats(fed_id)
        # Will send to current chat
        context.bot.send_message(
            chat.id,
            "<b>Ban Federasi Baru</b>"
            "\n<b>Federasi:</b> {}"
            "\n<b>Admin Federasi:</b> {}"
            "\n<b>Pengguna:</b> {}"
            "\n<b>ID Pengguna:</b> <code>{}</code>"
            "\n<b>Alasan:</b> {}".format(
                fed_name,
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
                reason,
            ),
            parse_mode="HTML",
        )
        # Send message to owner if fednotif is enabled
        if getfednotif:
            context.bot.send_message(
                info["owner"],
                "<b>Alasan FedBan diperbarui</b>"
                "\n<b>Federasi:</b> {}"
                "\n<b>Admin Federasi:</b> {}"
                "\n<b>Pengguna:</b> {}"
                "\n<b>ID Pengguna:</b> <code>{}</code>"
"\n<b>Diprakarsai Dari:</b> <code>{}</code>"
                "\n<b>Alasan:</b> {}".format(
                    fed_name,
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
		    message.chat.title,
                    reason,
                ),
                parse_mode="HTML",
            )
        # If fedlog is set, then send message, except fedlog is current chat
        get_fedlog = sql.get_fed_log(fed_id)
        if get_fedlog:
            if int(get_fedlog) != int(chat.id):
                context.bot.send_message(
                    get_fedlog,
                    "<b>Alasan FedBan diperbarui</b>"
                    "\n<b>Federasi:</b> {}"
                    "\n<b>Admin Federasi:</b> {}"
                    "\n<b>Pengguna:</b> {}"
                    "\n<b>ID Pengguna:</b> <code>{}</code>"
"\n<b>Diprakarsai Dari:</b> <code>{}</code>"
                    "\n<b>Alasan:</b> {}".format(
                        fed_name,
                        mention_html(user.id, user.first_name),
                        user_target,
                        fban_user_id,
			message.chat.title,
                        reason,
                    ),
                    parse_mode="HTML",
                )
        for fedschat in fed_chats:
            try:
                # Do not spam all fed chats
                """
				context.bot.send_message(chat, "<b>FedBan reason updated</b>" \
							    "\n<b>Federasi:</b> {}" \
                                "\n<b>Admin Federasi:</b> {}" \
                                "\n<b>Pengguna:</b> {}" \
                                "\n<b>ID Pengguna:</b> <code>{}</code>" \
                                "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
				"""
                context.bot.kick_chat_member(fedschat, fban_user_id)
            except BadRequest as excp:
                if excp.message in FBAN_ERRORS:
                    try:
                        dispatcher.bot.getChat(fedschat)
                    except Unauthorized:
                        sql.chat_leave_fed(fedschat)
                        log.info(
                            "Obrolan {} telah meninggalkan umpan {} karena saya ditendang".format(
                                fedschat, info["fname"]
                            )
                        )
                        continue
                elif excp.message == "User_id_invalid":
                    break
                else:
                    log.warning(
                        "Tidak bisa fban pada {} karena: {}".format(chat, excp.message)
                    )
            except TelegramError:
                pass
        # Also do not spam all fed admins

        # send_to_list(bot, FEDADMIN,
        # "<b>FedBan reason updated</b>" \
        # "\n<b>Federation:</b> {}" \
        # "\n<b>Federation Admin:</b> {}" \
        # "\n<b>User:</b> {}" \
        # "\n<b>User ID:</b> <code>{}</code>" \
        # "\n<b>Reason:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason),
        # html=True)

        # Fban for fed subscriber
        subscriber = list(sql.get_subscriber(fed_id))
        if len(subscriber) != 0:
            for fedsid in subscriber:
                all_fedschat = sql.all_fed_chats(fedsid)
                for fedschat in all_fedschat:
                    try:
                        context.bot.kick_chat_member(fedschat, fban_user_id)
                    except BadRequest as excp:
                        if excp.message in FBAN_ERRORS:
                            try:
                                dispatcher.bot.getChat(fedschat)
                            except Unauthorized:
                                targetfed_id = sql.get_fed_id(fedschat)
                                sql.unsubs_fed(fed_id, targetfed_id)
                                log.info(
                                    "Chat {} telah unsub fed {} karena saya ditendang".format(
                                        fedschat, info["fname"]
                                    )
                                )
                                continue
                        elif excp.message == "User_id_invalid":
                            break
                        else:
                            log.warning(
                                "Tidak dapat melakukan fban pada {} karena: {}".format(
                                    fedschat, excp.message
                                )
                            )
                    except TelegramError:
                        pass
        # send_message(update.effective_message, "Fedban Reason has been updated.")
        return

    fed_name = info["fname"]

    starting = "Memulai larangan federasi untuk {} di Federasi <b>{}</b>.".format(
        user_target, fed_name
    )
    update.effective_message.reply_text(starting, parse_mode=ParseMode.HTML)

    if reason == "":
        reason = "Tidak ada alasan yang diberikan."

    x = sql.fban_user(
        fed_id,
        fban_user_id,
        fban_user_name,
        fban_user_lname,
        fban_user_uname,
        reason,
        int(time.time()),
    )
    if not x:
        message.reply_text("Gagal melarang dari federasi!")
        return

    fed_chats = sql.all_fed_chats(fed_id)
    # Will send to current chat
    context.bot.send_message(
        chat.id,
        "<b>Alasan FedBan diperbarui</b>"
        "\n<b>Federasi:</b> {}"
        "\n<b>Admin Federasi:</b> {}"
        "\n<b>Pengguna:</b> {}"
        "\n<b>ID Pengguna:</b> <code>{}</code>"
        "\n<b>Alasan:</b> {}".format(
            fed_name,
            mention_html(user.id, user.first_name),
            user_target,
            fban_user_id,
            reason,
        ),
        parse_mode="HTML",
    )
    # Send message to owner if fednotif is enabled
    if getfednotif:
        context.bot.send_message(
            info["owner"],
            "<b>Alasan FedBan diperbarui</b>"
            "\n<b>Federasi:</b> {}"
            "\n<b>Admin Federasi:</b> {}"
            "\n<b>Pengguna:</b> {}"
            "\n<b>ID Pengguna:</b> <code>{}</code>"
"\n<b>Diprakarsai Dari:</b> <code>{}</code>"
            "\n<b>Alasan:</b> {}".format(
                fed_name,
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
		message.chat.title,
                reason,
            ),
            parse_mode="HTML",
        )
    # If fedlog is set, then send message, except fedlog is current chat
    get_fedlog = sql.get_fed_log(fed_id)
    if get_fedlog:
        if int(get_fedlog) != int(chat.id):
            context.bot.send_message(
                get_fedlog,
                "<b>Alasan FedBan diperbarui</b>"
                "\n<b>Federasi:</b> {}"
                "\n<b>Admin Federasi:</b> {}"
                "\n<b>Pengguna:</b> {}"
                "\n<b>ID Pengguna:</b> <code>{}</code>"
"\n<b>Diprakarsai Dari:</b> <code>{}</code>"
                "\n<b>Alasan:</b> {}".format(
                    fed_name,
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
		    message.chat.title,
                    reason,
                ),
                parse_mode="HTML",
            )
    chats_in_fed = 0
    for fedschat in fed_chats:
        chats_in_fed += 1
        try:
            # Do not spamming all fed chats
            """
			context.bot.send_message(chat, "<b>Alasan FedBan diperbarui</b>" \
                                            "\n<b>Federasi:</b> {}" \
                                            "\n<b>Admin Federasi:</b> {}" \
                                            "\n<b>Pengguna:</b> {}" \
                                            "\n<b>ID Pengguna:</b> <code>{}</code>" \
                                            "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason), parse_mode="HTML")
			"""
            context.bot.kick_chat_member(fedschat, fban_user_id)
        except BadRequest as excp:
            if excp.message in FBAN_ERRORS:
                pass
            elif excp.message == "User_id_invalid":
                break
            else:
                log.warning(
                    "Could not fban on {} because: {}".format(chat, excp.message)
                )
        except TelegramError:
            pass

        # Also do not spamming all fed admins
        """
		send_to_list(bot, FEDADMIN,
				    "<b>Alasan FedBan diperbarui</b>" \
                    "\n<b>Federasi:</b> {}" \
                    "\n<b>Admin Federasi:</b> {}" \
                    "\n<b>Pengguna:</b> {}" \
                    "\n<b>ID Pengguna:</b> <code>{}</code>" \
                    "\n<b>Alasan:</b> {}".format(fed_name, mention_html(user.id, user.first_name), user_target, fban_user_id, reason),
							html=True)
		"""

        # Fban for fed subscriber
        subscriber = list(sql.get_subscriber(fed_id))
        if len(subscriber) != 0:
            for fedsid in subscriber:
                all_fedschat = sql.all_fed_chats(fedsid)
                for fedschat in all_fedschat:
                    try:
                        context.bot.kick_chat_member(fedschat, fban_user_id)
                    except BadRequest as excp:
                        if excp.message in FBAN_ERRORS:
                            try:
                                dispatcher.bot.getChat(fedschat)
                            except Unauthorized:
                                targetfed_id = sql.get_fed_id(fedschat)
                                sql.unsubs_fed(fed_id, targetfed_id)
                                log.info(
                                    "Chat {} telah unsub fed {} karena saya ditendang".format(
                                        fedschat, info["fname"]
                                    )
                                )
                                continue
                        elif excp.message == "User_id_invalid":
                            break
                        else:
                            log.warning(
                                "Tidak dapat melakukan fban pada {} karena: {}".format(
                                    fedschat, excp.message
                                )
                            )
                    except TelegramError:
                        pass
    if chats_in_fed == 0:
        send_message(update.effective_message, "Fedban memengaruhi 0 obrolan. ")
    elif chats_in_fed > 0:
        send_message(
            update.effective_message,
            "Obrolan {} yang terpengaruh Fedban. ".format(chats_in_fed),
        )


@typing_action
@zaid(command=['unfban', 'rmfedban'], pass_args=True)
def unfban(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    info = sql.get_fed_info(fed_id)
    getfednotif = sql.user_feds_report(info["owner"])

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    user_id = extract_user_fban(message, args)
    if not user_id:
        message.reply_text("Anda sepertinya tidak merujuk ke pengguna.")
        return

    try:
        user_chat = context.bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_name = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_uname = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            send_message(update.effective_message, excp.message)
            return
        elif not len(str(user_id)) == 9:
            send_message(update.effective_message, "Itu bukan pengguna!")
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_name = "user({})".format(user_id)
        fban_user_lname = None
        fban_user_uname = None

    if isvalid and user_chat.type != "private":
        message.reply_text("Itu bukan pengguna!")
        return

    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_name)
    else:
        user_target = fban_user_name

    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, fban_user_id)
    if fban is False:
        message.reply_text("Pengguna ini tidak di-fbanned!")
        return

    message.reply_text(
        "Saya akan memberikan {} kesempatan lagi di federasi ini".format(user_chat.first_name)
    )

    chat_list = sql.all_fed_chats(fed_id)
    # Will send to current chat
    context.bot.send_message(
        chat.id,
        "<b>Un-FedBan</b>"
        "\n<b>Federasi:</b> {}"
        "\n<b>Admin Federasi:</b> {}"
        "\n<b>Pengguna:</b> {}"
        "\n<b>ID Pengguna:</b> <code>{}</code>".format(
            info["fname"],
            mention_html(user.id, user.first_name),
            user_target,
            fban_user_id,
        ),
        parse_mode="HTML",
    )
    # Send message to owner if fednotif is enabled
    if getfednotif:
        context.bot.send_message(
            info["owner"],
            "<b>Un-FedBan</b>"
            "\n<b>Federasi:</b> {}"
            "\n<b>Admin Federasi:</b> {}"
            "\n<b>Pengguna:</b> {}"
            "\n<b>ID Pengguna:</b> <code>{}</code>"
	    "\n<b>Dimulai Dari:</b> <code>{}</code>".format(
                info["fname"],
                mention_html(user.id, user.first_name),
                user_target,
                fban_user_id,
		message.chat.title,
            ),
            parse_mode="HTML",
        )
    # If fedlog is set, then send message, except fedlog is current chat
    get_fedlog = sql.get_fed_log(fed_id)
    if get_fedlog:
        if int(get_fedlog) != int(chat.id):
            context.bot.send_message(
                get_fedlog,
                "<b>Un-FedBan</b>"
                "\n<b>Federasi:</b> {}"
                "\n<b>Admin Federasi:</b> {}"
                "\n<b>Pengguna:</b> {}"
                "\n<b>ID Pengguna:</b> <code>{}</code>"
"\n<b>Diprakarsai Dari:</b> <code>{}</code>".format(
                    info["fname"],
                    mention_html(user.id, user.first_name),
                    user_target,
                    fban_user_id,
		    message.chat.title,
                ),
                parse_mode="HTML",
            )
    unfbanned_in_chats = 0
    for fedchats in chat_list:
        unfbanned_in_chats += 1
        try:
            member = context.bot.get_chat_member(fedchats, user_id)
            if member.status == "kicked":
                context.bot.unban_chat_member(fedchats, user_id)
            # Do not spamming all fed chats
            """
			context.bot.send_message(chat, "<b>Un-FedBan</b>" \
                                    "\n<b>Federasi:</b> {}" \
                                    "\n<b>Admin Federasi:</b> {}" \
                                    "\n<b>Pengguna:</b> {}" \
                                    "\n<b>ID Pengguna:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name), user_target, fban_user_id), parse_mode="HTML")
			"""
        except BadRequest as excp:
            if excp.message in UNFBAN_ERRORS:
                pass
            elif excp.message == "User_id_invalid":
                break
            else:
                log.warning(
                    "Tidak bisa fban pada {} karena: {}".format(chat, excp.message)
                )
        except TelegramError:
            pass

    try:
        x = sql.un_fban_user(fed_id, user_id)
        if not x:
            send_message(
                update.effective_message,
                "Un-fban gagal, pengguna ini mungkin sudah un-fbanned!",
            )
            return
    except Exception:
        pass

    # UnFban for fed subscriber
    subscriber = list(sql.get_subscriber(fed_id))
    if len(subscriber) != 0:
        for fedsid in subscriber:
            all_fedschat = sql.all_fed_chats(fedsid)
            for fedschat in all_fedschat:
                try:
                    context.bot.unban_chat_member(fedchats, user_id)
                except BadRequest as excp:
                    if excp.message in FBAN_ERRORS:
                        try:
                            dispatcher.bot.getChat(fedschat)
                        except Unauthorized:
                            targetfed_id = sql.get_fed_id(fedschat)
                            sql.unsubs_fed(fed_id, targetfed_id)
                            log.info(
                                "Chat {} telah unsub fed {} karena saya ditendang".format(
                                    fedschat, info["fname"]
                                )
                            )
                            continue
                    elif excp.message == "User_id_invalid":
                        break
                    else:
                        log.warning(
                            "Tidak dapat melakukan fban pada {} karena: {}".format(
                                fedschat, excp.message
                            )
                        )
                except TelegramError:
                    pass

    if unfbanned_in_chats == 0:
        send_message(
            update.effective_message,
            "Orang ini telah dibatalkan larangannya dalam 0 obrolan.",
        )
    if unfbanned_in_chats > 0:
        send_message(
            update.effective_message,
            "Orang ini telah dibatalkan larangannya dalam {} obrolan.".format(unfbanned_in_chats),
        )
    # Also do not spamming all fed admins
    """
	FEDADMIN = sql.all_fed_users(fed_id)
	for x in FEDADMIN:
		getreport = sql.user_feds_report(x)
		if getreport == False:
			FEDADMIN.remove(x)
	send_to_list(bot, FEDADMIN,
			    "<b>Un-FedBan</b>" \
                "\n<b>Federasi:</b> {}" \
                "\n<b>Admin Federasi:</b> {}" \
                "\n<b>Pengguna:</b> {}" \
                "\n<b>ID Pengguna:</b> <code>{}</code>".format(info['fname'], mention_html(user.id, user.first_name),
												    mention_html(user_chat.id, user_chat.first_name),
															    user_chat.id),
			html=True)
	"""


@typing_action
def set_frules(update, context):

    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text("Obrolan ini tidak ada di federasi mana pun!")
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin yang diberi makan yang dapat melakukan ini!")
        return

    if len(args) >= 1:
        msg = update.effective_message  # type: Optional[Message]
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        if len(args) == 2:
            txt = args[1]
            offset = len(txt) - len(raw_text)  # set correct offset relative to command
            markdown_rules = markdown_parser(
                txt, entities=msg.parse_entities(), offset=offset
            )
        x = sql.set_frules(fed_id, markdown_rules)
        if not x:
            update.effective_message.reply_text(
                "F Besar! Terjadi kesalahan saat menyetel aturan federasi!"
            )
            return

        rules = sql.get_fed_info(fed_id)["frules"]
        getfed = sql.get_fed_info(fed_id)
        get_fedlog = sql.get_fed_log(fed_id)
        if get_fedlog:
            if ast.literal_eval(get_fedlog):
                context.bot.send_message(
                    get_fedlog,
                    "*{}* telah mengubah aturan federasi untuk diberi makan *{}*".format(
                        user.first_name, getfed["fname"]
                    ),
                    parse_mode="markdown",
                )
        update.effective_message.reply_text(f"Aturan telah diubah menjadi :\n{rules}!")
    else:
        update.effective_message.reply_text("Harap tulis aturan untuk mengaturnya!")


@typing_action
@zaid(command='frules', pass_args=True)
def get_frules(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        update.effective_message.reply_text("Obrolan ini tidak ada di federasi mana pun!")
        return

    rules = sql.get_frules(fed_id)
    text = "*Aturan dalam fed ini:*\n"
    text += rules
    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


@typing_action
@zaid(command='fbroadcast', pass_args=True)
def fed_broadcast(update, context):
    msg = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    if args:
        chat = update.effective_chat  # type: Optional[Chat]
        fed_id = sql.get_fed_id(chat.id)
        fedinfo = sql.get_fed_info(fed_id)
        # Parsing md
        raw_text = msg.text
        args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        text_parser = markdown_parser(txt, entities=msg.parse_entities(), offset=offset)
        text = text_parser
        try:
            broadcaster = user.first_name
        except:
            broadcaster = user.first_name + " " + user.last_name
        text += "\n\n- {}".format(mention_markdown(user.id, broadcaster))
        chat_list = sql.all_fed_chats(fed_id)
        failed = 0
        for chat in chat_list:
            title = "*Siaran baru dari Fed {}*\n".format(fedinfo["fname"])
            try:
                context.bot.sendMessage(chat, title + text, parse_mode="markdown")
            except TelegramError:
                try:
                    dispatcher.bot.getChat(chat)
                except Unauthorized:
                    failed += 1
                    sql.chat_leave_fed(chat)
                    log.info(
                        "Obrolan {} telah meninggalkan umpan {} karena saya ditendang".format(
                            chat, fedinfo["fname"]
                        )
                    )
                    continue
                failed += 1
                log.warning("Tidak dapat mengirim siaran ke {}".format(str(chat)))

        send_text = "Siaran federasi selesai"
        if failed >= 1:
            send_text += "{} grup gagal menerima pesan, mungkin karena meninggalkan Federasi.".format(
                failed
            )
        update.effective_message.reply_text(send_text)


@send_action(ChatAction.UPLOAD_DOCUMENT)
@zaid(command='fbanlist', pass_args=True, pass_chat_data=True)
def fed_ban_list(update, context):  # sourcery no-metrics
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = context.args
    chat_data = context.chat_data

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya pemilik Federasi yang dapat melakukan ini!")
        return

    user = update.effective_user  # type: Optional[Chat]
    chat = update.effective_chat  # type: Optional[Chat]
    getfban = sql.get_all_fban_users(fed_id)
    if len(getfban) == 0:
        update.effective_message.reply_text(
            "Daftar larangan federasi {} kosong".format(info["fname"]),
            parse_mode=ParseMode.HTML,
        )
        return

    if args:
        if args[0] == "json":
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get("status"):
                if jam <= int(cek.get("value")):
                    waktu = time.strftime(
                        "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value"))
                    )
                    update.effective_message.reply_text(
                        "Anda dapat mencadangkan data setiap 30 menit sekali!\nAnda dapat mencadangkan data lagi di `{}`".format(
                            waktu
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                else:
                    if user.id not in SUDO_USERS:
                        put_chat(chat.id, new_jam, chat_data)
            elif user.id not in SUDO_USERS:
                put_chat(chat.id, new_jam, chat_data)
            backups = ""
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                json_parser = {
                    "user_id": users,
                    "first_name": getuserinfo["first_name"],
                    "last_name": getuserinfo["last_name"],
                    "user_name": getuserinfo["user_name"],
                    "reason": getuserinfo["reason"],
                }
                backups += json.dumps(json_parser)
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "kigyo_fbanned_users.json"
                update.effective_message.reply_document(
                    document=output,
                    filename="kigyo_fbanned_users.json",
                    caption="Total {} Pengguna diblokir oleh Federasi {}.".format(
                        len(getfban), info["fname"]
                    ),
                )
            return
        elif args[0] == "csv":
            jam = time.time()
            new_jam = jam + 1800
            cek = get_chat(chat.id, chat_data)
            if cek.get("status"):
                if jam <= int(cek.get("value")):
                    waktu = time.strftime(
                        "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value"))
                    )
                    update.effective_message.reply_text(
                        "Anda dapat mencadangkan data setiap 30 menit sekali!\nAnda dapat mencadangkan data lagi di `{}`".format(
                            waktu
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    return
                else:
                    if user.id not in SUDO_USERS:
                        put_chat(chat.id, new_jam, chat_data)
            elif user.id not in SUDO_USERS:
                put_chat(chat.id, new_jam, chat_data)
            backups = "id,firstname,lastname,username,reason\n"
            for users in getfban:
                getuserinfo = sql.get_all_fban_users_target(fed_id, users)
                backups += (
                    "{user_id},{first_name},{last_name},{user_name},{reason}".format(
                        user_id=users,
                        first_name=getuserinfo["first_name"],
                        last_name=getuserinfo["last_name"],
                        user_name=getuserinfo["user_name"],
                        reason=getuserinfo["reason"],
                    )
                )
                backups += "\n"
            with BytesIO(str.encode(backups)) as output:
                output.name = "kigyo_fbanned_users.csv"
                update.effective_message.reply_document(
                    document=output,
                    filename="kigyo_fbanned_users.csv",
                    caption="Total {} Pengguna diblokir oleh Federasi {}.".format(
                        len(getfban), info["fname"]
                    ),
                )
            return

    text = "<b>{} pengguna telah dilarang dari federasi {}:</b>\n".format(
        len(getfban), info["fname"]
    )
    for users in getfban:
        getuserinfo = sql.get_all_fban_users_target(fed_id, users)
        if getuserinfo is False:
            text = "Tidak ada pengguna yang dilarang dari federasi {}".format(
                info["fname"]
            )
            break
        user_name = getuserinfo["first_name"]
        if getuserinfo["last_name"]:
            user_name += " " + getuserinfo["last_name"]
        text += " • {} (<code>{}</code>)\n".format(
            mention_html(users, user_name), users
        )

    try:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get("status"):
            if jam <= int(cek.get("value")):
                waktu = time.strftime(
                    "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value"))
                )
                update.effective_message.reply_text(
                    "Anda dapat mencadangkan data setiap 30 menit sekali!\nAnda dapat mencadangkan data lagi di `{}`".format(
                        waktu
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            else:
                if user.id not in SUDO_USERS:
                    put_chat(chat.id, new_jam, chat_data)
        elif user.id not in SUDO_USERS:
            put_chat(chat.id, new_jam, chat_data)
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fbanlist.txt"
            update.effective_message.reply_document(
                document=output,
                filename="fbanlist.txt",
                caption="Berikut ini adalah daftar pengguna yang saat ini di-fban di Federasi {}.".format(
                    info["fname"]
                ),
            )


@typing_action
@zaid(command='fednotif', pass_args=True)
def fed_notif(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args
    fed_id = sql.get_fed_id(chat.id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    if args:
        if args[0] in ("yes", "on"):
            sql.set_feds_setting(user.id, True)
            msg.reply_text(
                "Pelaporan Federasi kembali! Setiap pengguna yang fban / unfban Anda akan diberitahu melalui PM."
            )
        elif args[0] in ("no", "off"):
            sql.set_feds_setting(user.id, False)
            msg.reply_text(
                "Federasi Pelaporan telah berhenti! Setiap pengguna yang fban / unfban Anda tidak akan diberitahu melalui PM."
            )
        else:
            msg.reply_text("Silakan masuk `on`/`off`", parse_mode="markdown")
    else:
        getreport = sql.user_feds_report(user.id)
        msg.reply_text(
            "Preferensi laporan Federasi Anda saat ini: `{}`".format(getreport),
            parse_mode="markdown",
        )


@typing_action
@zaid(command='fedchats', pass_args=True)
def fed_chats(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    info = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    if is_user_fed_admin(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya admin federasi yang dapat melakukan ini!")
        return

    getlist = sql.all_fed_chats(fed_id)
    if len(getlist) == 0:
        update.effective_message.reply_text(
            "Tidak ada pengguna yang dilarang dari federasi {}".format(info["fname"]),
            parse_mode=ParseMode.HTML,
        )
        return

    text = "<b>Obrolan baru bergabung dengan federasi {}:</b>\n".format(info["fname"])
    for chats in getlist:
        try:
            chat_name = dispatcher.bot.getChat(chats).title
        except Unauthorized:
            sql.chat_leave_fed(chats)
            log.info(
                "Obrolan {} telah meninggalkan umpan {} karena saya ditendang".format(
                    chats, info["fname"]
                )
            )
            continue
        text += " • {} (<code>{}</code>)\n".format(chat_name, chats)

    try:
        update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = "fedchats.txt"
            update.effective_message.reply_document(
                document=output,
                filename="fedchats.txt",
                caption="Berikut adalah daftar semua obrolan yang bergabung dengan federasi {}.".format(
                    info["fname"]
                ),
            )


@typing_action
@zaid(command='importfbans', pass_args=True, pass_chat_data=True)
def fed_import_bans(update, context):  # sourcery no-metrics
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    chat_data = context.chat_data

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    # info = sql.get_fed_info(fed_id)
    getfed = sql.get_fed_info(fed_id)

    if not fed_id:
        update.effective_message.reply_text(
            "Grup ini bukan bagian dari federasi mana pun!"
        )
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        update.effective_message.reply_text("Hanya pemilik Federasi yang dapat melakukan ini!")
        return

    if msg.reply_to_message and msg.reply_to_message.document:
        jam = time.time()
        new_jam = jam + 1800
        cek = get_chat(chat.id, chat_data)
        if cek.get("status"):
            if jam <= int(cek.get("value")):
                waktu = time.strftime(
                    "%H:%M:%S %d/%m/%Y", time.localtime(cek.get("value"))
                )
                update.effective_message.reply_text(
                    "Anda bisa mendapatkan data setiap 30 menit sekali!\nAnda bisa mendapatkan data lagi di `{}`".format(
                        waktu
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            else:
                if user.id not in SUDO_USERS:
                    put_chat(chat.id, new_jam, chat_data)
        else:
            if user.id not in SUDO_USERS:
                put_chat(chat.id, new_jam, chat_data)
        # if int(int(msg.reply_to_message.document.file_size)/1024) >= 200:
        # 	msg.reply_text("This file is too big!")
        # 	return
        success = 0
        failed = 0
        try:
            file_info = context.bot.get_file(msg.reply_to_message.document.file_id)
        except BadRequest:
            msg.reply_text(
                "Coba unduh dan unggah ulang file, yang ini sepertinya rusak!"
            )
            return
        fileformat = msg.reply_to_message.document.file_name.split(".")[-1]
        if fileformat == "json":
            multi_fed_id = []
            multi_import_userid = []
            multi_import_firstname = []
            multi_import_lastname = []
            multi_import_username = []
            multi_import_reason = []
            with BytesIO() as file:
                file_info.download(out=file)
                file.seek(0)
                reading = file.read().decode("UTF-8")
                splitting = reading.split("\n")
                for x in splitting:
                    if x == "":
                        continue
                    try:
                        data = json.loads(x)
                    except json.decoder.JSONDecodeError:
                        failed += 1
                        continue
                    try:
                        import_userid = int(data["user_id"])  # Make sure it int
                        import_firstname = str(data["first_name"])
                        import_lastname = str(data["last_name"])
                        import_username = str(data["user_name"])
                        import_reason = str(data["reason"])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == context.bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in SUDO_USERS:
                        failed += 1
                        continue
                    if int(import_userid) in WHITELIST_USERS:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            text = "Blok berhasil diimpor. {} orang diblokir.".format(
                success
            )
            if failed >= 1:
                text += " {} Gagal mengimpor.".format(failed)
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if ast.literal_eval(get_fedlog):
                    teks = "Fed *{}* telah berhasil mengimpor data. {} dilarang.".format(
                        getfed["fname"], success
                    )
                    if failed >= 1:
                        teks += " {} Gagal mengimpor.".format(failed)
                    context.bot.send_message(get_fedlog, teks, parse_mode="markdown")
        elif fileformat == "csv":
            multi_fed_id = []
            multi_import_userid = []
            multi_import_firstname = []
            multi_import_lastname = []
            multi_import_username = []
            multi_import_reason = []
            file_info.download(
                "fban_{}.csv".format(msg.reply_to_message.document.file_id)
            )
            with open(
                "fban_{}.csv".format(msg.reply_to_message.document.file_id),
                "r",
                encoding="utf8",
            ) as csvFile:
                reader = csv.reader(csvFile)
                for data in reader:
                    try:
                        import_userid = int(data[0])  # Make sure it int
                        import_firstname = str(data[1])
                        import_lastname = str(data[2])
                        import_username = str(data[3])
                        import_reason = str(data[4])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == context.bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in SUDO_USERS:
                        failed += 1
                        continue
                    if int(import_userid) in WHITELIST_USERS:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                    # t = ThreadWithReturnValue(target=sql.fban_user, args=(fed_id, str(import_userid), import_firstname, import_lastname, import_username, import_reason,))
                    # t.start()
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            csvFile.close()
            os.remove("fban_{}.csv".format(msg.reply_to_message.document.file_id))
            text = "File berhasil diimpor. {} orang dilarang.".format(success)
            if failed >= 1:
                text += " {} Failed to import.".format(failed)
            get_fedlog = sql.get_fed_log(fed_id)
            if get_fedlog:
                if ast.literal_eval(get_fedlog):
                    teks = "Fed *{}* telah berhasil mengimpor data. {} dilarang.".format(
                        getfed["fname"], success
                    )
                    if failed >= 1:
                        teks += " {} Gagal mengimpor.".format(failed)
                    context.bot.send_message(get_fedlog, teks, parse_mode="markdown")
        else:
            send_message(update.effective_message, "File ini tidak didukung.")
            return
        send_message(update.effective_message, text)


@zaidcallback(pattern=r"rmfed_")
def del_fed_button(update, context):
    query = update.callback_query
    fed_id = query.data.split("_")[1]

    if fed_id == "cancel":
        query.message.edit_text("Penghapusan federasi dibatalkan")
        return

    getfed = sql.get_fed_info(fed_id)
    if getfed:
        delete = sql.del_fed(fed_id)
        if delete:
            query.message.edit_text(
                "Anda telah menghapus Federasi Anda! Sekarang semua Grup yang terhubung dengan `{}` tidak memiliki Federasi.".format(
                    getfed["fname"]
                ),
                parse_mode="markdown",
            )


@typing_action
@zaid(command='fbanstat', pass_args=True)
def fed_stat_user(update, context):  # sourcery no-metrics
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

    if args:
        if args[0].isdigit():
            user_id = args[0]
        else:
            user_id = extract_user(msg, args)
    else:
        user_id = extract_user(msg, args)

    if user_id:
        if len(args) == 2 and args[0].isdigit():
            fed_id = args[1]
            user_name, reason, fbantime = sql.get_user_fban(fed_id, str(user_id))
            if fbantime:
                fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
            else:
                fbantime = "Unavaiable"
            if user_name is False:
                send_message(
                    update.effective_message,
                    "Makan {} tidak ditemukan!".format(fed_id),
                    parse_mode="markdown",
                )
                return
            if user_name == "" or user_name == None:
                user_name = "He/she"
            if not reason:
                send_message(
                    update.effective_message,
                    "{} tidak dilarang di federasi ini!".format(user_name),
                )
            else:
                teks = "{} dilarang di federasi ini karena:\n`{}`\n*Dilarang di:* `{}`".format(
                    user_name, reason, fbantime
                )
                send_message(update.effective_message, teks, parse_mode="markdown")
            return
        user_name, fbanlist = sql.get_user_fbanlist(str(user_id))
        if user_name == "":
            try:
                user_name = context.bot.get_chat(user_id).first_name
            except BadRequest:
                user_name = "He/she"
            if user_name == "" or user_name == None:
                user_name = "He/she"
        if len(fbanlist) == 0:
            send_message(
                update.effective_message,
                "{} tidak dilarang di federasi mana pun!".format(user_name),
            )
            return
        else:
            teks = "{} telah dilarang di federasi ini:\n".format(user_name)
            for x in fbanlist:
                teks += "- `{}`: {}\n".format(x[0], x[1][:20])
            teks += "\nJika Anda ingin mengetahui lebih lanjut tentang alasan khusus Fedban, gunakan /fbanstat <FedID>"
            send_message(update.effective_message, teks, parse_mode="markdown")

    elif not msg.reply_to_message and not args:
        user_id = msg.from_user.id
        user_name, fbanlist = sql.get_user_fbanlist(user_id)
        if user_name == "":
            user_name = msg.from_user.first_name
        if len(fbanlist) == 0:
            send_message(
                update.effective_message,
                "{} tidak dilarang di federasi mana pun!".format(user_name),
            )
        else:
            teks = "{} telah dilarang di federasi ini:\n".format(user_name)
            for x in fbanlist:
                teks += "- `{}`: {}\n".format(x[0], x[1][:20])
            teks += "\nJika Anda ingin mengetahui lebih lanjut tentang alasan khusus Fedban, gunakan /fbanstat <FedID>"
            send_message(update.effective_message, teks, parse_mode="markdown")

    else:
        fed_id = args[0]
        fedinfo = sql.get_fed_info(fed_id)
        if not fedinfo:
            send_message(update.effective_message, "Makan {} tidak ditemukan!".format(fed_id))
            return
        name, reason, fbantime = sql.get_user_fban(fed_id, msg.from_user.id)
        if fbantime:
            fbantime = time.strftime("%d/%m/%Y", time.localtime(fbantime))
        else:
            fbantime = "Unavaiable"
        if not name:
            name = msg.from_user.first_name
        if not reason:
            send_message(
                update.effective_message,
                "{} tidak dilarang di federasi ini".format(name),
            )
            return
        send_message(
            update.effective_message,
            "{} dilarang di federasi ini karena:\n`{}`\n*Dilarang di:* `{}`".format(
                name, reason, fbantime
            ),
            parse_mode="markdown",
        )


@typing_action
@zaid(command='setfedlog', pass_args=True)
def set_fed_log(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    if args:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            send_message(update.effective_message, "Federasi ini tidak ada!")
            return
        isowner = is_user_fed_owner(args[0], user.id)
        if not isowner:
            send_message(
                update.effective_message,
                "Hanya pembuat federasi yang dapat menyetel log federasi.",
            )
            return
        setlog = sql.set_fed_log(args[0], chat.id)
        if setlog:
            send_message(
                update.effective_message,
                "Log federasi `{}` telah disetel ke {}".format(
                    fedinfo["fname"], chat.title
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "Anda belum memberikan ID federasi Anda!",
        )


@typing_action
@zaid(command='unsetfedlog', pass_args=True)
def unset_fed_log(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    if args:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            send_message(update.effective_message, "Federasi ini tidak ada!")
            return
        isowner = is_user_fed_owner(args[0], user.id)
        if not isowner:
            send_message(
                update.effective_message,
                "Hanya pembuat federasi yang dapat menyetel log federasi.",
            )
            return
        setlog = sql.set_fed_log(args[0], None)
        if setlog:
            send_message(
                update.effective_message,
                "Log federasi `{}` telah dicabut {}".format(
                    fedinfo["fname"], chat.title
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "Anda belum memberikan ID federasi Anda!",
        )


@typing_action
@zaid('subfed', pass_args=True)
def subs_feds(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "Obrolan ini tidak ada di federasi mana pun!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        send_message(update.effective_message, "Hanya pemilik yang diberi makan yang dapat melakukan ini!")
        return

    if args:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            send_message(
                update.effective_message, "Masukkan id federasi yang valid."
            )
            return
        subfed = sql.subs_fed(args[0], fed_id)
        if subfed:
            send_message(
                update.effective_message,
                "Federation `{}` telah berlangganan federasi `{}`. Setiap kali ada Fedban dari federasi tersebut, federasi ini juga akan melarang pengguna tersebut.".format(
                    fedinfo["fname"], getfed["fname"]
                ),
                parse_mode="markdown",
            )
            get_fedlog = sql.get_fed_log(args[0])
            if get_fedlog:
                if int(get_fedlog) != int(chat.id):
                    context.bot.send_message(
                        get_fedlog,
                        "Federation `{}` telah berlangganan federasi `{}`".format(
                            fedinfo["fname"], getfed["fname"]
                        ),
                        parse_mode="markdown",
                    )
        else:
            send_message(
                update.effective_message,
                "Federasi `{}` sudah berlangganan federasi `{}`.".format(
                    fedinfo["fname"], getfed["fname"]
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "Anda belum memberikan ID federasi Anda!",
        )


@typing_action
@zaid(command='unsubfed', pass_args=True)
def unsubs_feds(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "Obrolan ini tidak ada di federasi mana pun!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        send_message(update.effective_message, "Hanya pemilik yang diberi makan yang dapat melakukan ini!")
        return

    if args:
        getfed = sql.search_fed_by_id(args[0])
        if getfed is False:
            send_message(
                update.effective_message, "Masukkan id federasi yang valid."
            )
            return
        subfed = sql.unsubs_fed(args[0], fed_id)
        if subfed:
            send_message(
                update.effective_message,
                "Federasi `{}` sekarang berhenti berlangganan fed `{}`.".format(
                    fedinfo["fname"], getfed["fname"]
                ),
                parse_mode="markdown",
            )
            get_fedlog = sql.get_fed_log(args[0])
            if get_fedlog:
                if int(get_fedlog) != int(chat.id):
                    context.bot.send_message(
                        get_fedlog,
                        "Federasi `{}` telah berhenti berlangganan feed `{}`.".format(
                            fedinfo["fname"], getfed["fname"]
                        ),
                        parse_mode="markdown",
                    )
        else:
            send_message(
                update.effective_message,
                "Federasi `{}` tidak berlangganan `{}`.".format(
                    fedinfo["fname"], getfed["fname"]
                ),
                parse_mode="markdown",
            )
    else:
        send_message(
            update.effective_message,
            "Anda belum memberikan ID federasi Anda!",
        )


@typing_action
@zaid(command='fedsubs', pass_args=True)
def get_myfedsubs(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

    if chat.type == "private":
        send_message(
            update.effective_message,
            "Perintah ini khusus untuk grup, bukan untuk PM! ",
        )
        return

    fed_id = sql.get_fed_id(chat.id)
    fedinfo = sql.get_fed_info(fed_id)

    if not fed_id:
        send_message(update.effective_message, "Obrolan ini tidak ada di federasi mana pun!")
        return

    if is_user_fed_owner(fed_id, user.id) is False:
        send_message(update.effective_message, "Hanya pemilik yang diberi makan yang dapat melakukan ini!")
        return

    getmy = sql.get_mysubs(fed_id)

    if getmy is None:
        send_message(
            update.effective_message,
            "Federasi `{}` tidak berlangganan federasi apa pun.".format(
                fedinfo["fname"]
            ),
            parse_mode="markdown",
        )
        return
    else:
        listfed = "Federasi `{}` berlangganan federasi:\n".format(
            fedinfo["fname"]
        )
        for x in getmy:
            listfed += "- `{}`\n".format(x)
        listfed += (
            "\nUntuk mendapatkan info makan `/fedinfo <fedid>`. Untuk berhenti berlangganan `/unsubfed <fedid>`."
        )
        send_message(update.effective_message, listfed, parse_mode="markdown")


@typing_action
@zaid(command='myfeds', pass_args=True)
def get_myfeds_list(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    args = context.args

    fedowner = sql.get_user_owner_fed_full(user.id)
    if fedowner:
        text = "*Anda adalah pemilik FBI:\n*"
        for f in fedowner:
            text += "- `{}`: *{}*\n".format(f["fed_id"], f["fed"]["fname"])
    else:
        text = "*Anda tidak memiliki FBI!*"
    send_message(update.effective_message, text, parse_mode="markdown")


def is_user_fed_admin(fed_id, user_id):
    fed_admins = sql.all_fed_users(fed_id)
    if fed_admins is False:
        return False
    if int(user_id) in fed_admins or int(user_id) == OWNER_ID:
        return True
    else:
        return False


def is_user_fed_owner(fed_id, user_id):
    getsql = sql.get_fed_info(fed_id)
    if getsql is False:
        return False
    getfedowner = ast.literal_eval(getsql["fusers"])
    if getfedowner == None or getfedowner == False:
        return False
    getfedowner = getfedowner["owner"]
    if str(user_id) == getfedowner or int(user_id) == OWNER_ID:
        return True
    else:
        return False


def welcome_fed(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    fed_id = sql.get_fed_id(chat.id)
    fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user.id)
    if fban:
        update.effective_message.reply_text(
            "Pengguna ini dilarang di federasi saat ini! Aku akan menyingkirkannya."
        )
        context.bot.kick_chat_member(chat.id, user.id)
        return True
    else:
        return False


def __stats__():
    all_fbanned = sql.get_all_fban_users_global()
    all_feds = sql.get_all_feds_users_global()
    return "• {} pengguna dilarang, dalam {} federasi".format(
        len(all_fbanned), len(all_feds)
    )


def __user_info__(user_id, chat_id):
    fed_id = sql.get_fed_id(chat_id)
    if fed_id:
        fban, fbanreason, fbantime = sql.get_fban_user(fed_id, user_id)
        info = sql.get_fed_info(fed_id)
        infoname = info["fname"]

        if int(info["owner"]) == user_id:
            text = (
                "Pengguna ini adalah pemilik Federasi saat ini: <b>{}</b>.".format(
                    infoname
                )
            )
        elif is_user_fed_admin(fed_id, user_id):
            text = (
                "Pengguna ini adalah admin dari Federasi saat ini: <b>{}</b>.".format(
                    infoname
                )
            )

        elif fban:
            text = "<b>Dilarang di Fed saat ini</b>: Yes"
            text += "\n<b>Reason</b>: {}".format(fbanreason)
        else:
            text = "<b>Dilarang di Fed saat ini</b>: No"
    else:
        text = ""
    return text


# Temporary data
def put_chat(chat_id, value, chat_data):
    # print(chat_data)
    if value is False:
        status = False
    else:
        status = True
    chat_data[chat_id] = {"federation": {"status": status, "value": value}}


def get_chat(chat_id, chat_data):
    # print(chat_data)
    try:
        value = chat_data[chat_id]["federation"]
        return value
    except KeyError:
        return {"status": False, "value": False}


__mod_name__ = "Federations"

from Telegram.modules.language import gs

def fed_owner_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        gs(update.effective_chat.id, "FED_OWNER_HELP"),
        parse_mode=ParseMode.MARKDOWN,
    )


def fed_admin_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        gs(update.effective_chat.id, "FED_ADMIN_HELP"),
        parse_mode=ParseMode.MARKDOWN,
    )



def fed_user_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        gs(update.effective_chat.id, "FED_USER_HELP"),
        parse_mode=ParseMode.MARKDOWN,
    )


@zaidcallback(pattern=r"fed_help_")
def fed_help(update: Update, context: CallbackContext):
    query = update.callback_query
    bot = context.bot
    help_info = query.data.split("fed_help_")[1]
    if help_info == "owner":
        help_text = gs(update.effective_chat.id, "FED_OWNER_HELP")
    elif help_info == "admin":
        help_text = gs(update.effective_chat.id, "FED_ADMIN_HELP")
    elif help_info == "user":
        help_text = gs(update.effective_chat.id, "FED_USER_HELP") 
    query.message.edit_text(
        text=help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Back", callback_data=f"help_module({__mod_name__.lower()})")]]
        ),
    )
    bot.answer_callback_query(query.id)


def get_help(chat):
    return [gs(chat, "feds_help"),
    [
        InlineKeyboardButton(text="Fedadmins", callback_data="fed_help_admin"),
        InlineKeyboardButton(text="Fedowners", callback_data="fed_help_owner")
    ],
    [
        InlineKeyboardButton(text="Users", callback_data="fed_help_user")
    ],
]
