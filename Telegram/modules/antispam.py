import html
import time
from datetime import datetime
from io import BytesIO
from Telegram.modules.sql.users_sql import get_user_com_chats
import Telegram.modules.sql.antispam_sql as sql
from Telegram import (
    DEV_USERS,
    GBAN_LOGS,
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    SARDEGNA_USERS,
    WHITELIST_USERS,
    sw,
    dispatcher,
    log,
)
from Telegram.modules.helper_funcs.chat_status import (
    is_user_admin,
    support_plus,
)
from Telegram.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from Telegram.modules.helper_funcs.misc import send_to_list
from telegram import ParseMode, Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import CallbackContext, Filters
from telegram.utils.helpers import mention_html
from spamwatch.errors import SpamWatchError, Error, UnauthorizedError, NotFoundError, Forbidden, TooManyRequests
from  Telegram.modules.helper_funcs.decorators import zaid, zaidmsg

from ..modules.helper_funcs.anonymous import user_admin, AdminPerms

GBAN_ENFORCE_GROUP = -1

GBAN_ERRORS = {
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
    "Tidak dapat menghapus pemilik obrolan",
}

UNGBAN_ERRORS = {
    "Pengguna adalah administrator obrolan",
    "Obrolan tidak ditemukan",
    "Tidak cukup hak untuk membatasi/membatalkan anggota obrolan",
    "Pengguna_bukan_peserta",
    "Metode hanya tersedia untuk grup super dan obrolan saluran",
    "Tidak di obrolan",
    "Saluran_pribadi",
    "Chat_admin_required",
    "Peer_id_invalid",
    "Pengguna tidak ditemukan",
}


@zaid(command="gban")
@support_plus
def gban(update: Update, context: CallbackContext):  # sourcery no-metrics
    bot, args = context.bot, context.args
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text(
            "Sepertinya Anda tidak merujuk ke pengguna atau ID yang ditentukan salah.."
        )
        return

    if int(user_id) in DEV_USERS:
        message.reply_text(
            "Pengguna itu adalah bagian dari Persatuan\nSaya tidak dapat bertindak melawan Persatuan kami."
        )
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text(
            "Saya memata-matai, dengan mata kecil saya... sebuah bangsa! Mengapa kalian menyalakan satu sama lain?"
        )
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text(
            "OOOH seseorang mencoba untuk menghancurkan Negara Sakura! *ambil popcorn*"
        )
        return

    if int(user_id) in SARDEGNA_USERS:
        message.reply_text("Itu Sardegna! Mereka tidak bisa dilarang!")
        return

    if int(user_id) in WHITELIST_USERS:
        message.reply_text("Itu Neptunia! Mereka tidak bisa dilarang!")
        return

    if int(user_id) in (777000, 1087968824):
        message.reply_text("Huh, kenapa saya gban Telegram bots?")
        return

    if user_id == bot.id:
        message.reply_text("Anda uhh ... ingin saya bunuh diri?")
        return

    try:
        user_chat = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message != "Pengguna tidak ditemukan":
            return

        message.reply_text("Sepertinya saya tidak dapat menemukan pengguna ini.")
        return ""
    if user_chat.type != "private":
        message.reply_text("Itu bukan pengguna!")
        return

    if sql.is_user_gbanned(user_id):

        if not reason:
            message.reply_text(
                "Pengguna ini sudah di-gban; Saya akan mengubah alasannya, tetapi Anda belum memberi saya satu pun..."
            )
            return

        old_reason = sql.update_gban_reason(
            user_id, user_chat.username or user_chat.first_name, reason
        )
        if old_reason:
            message.reply_text(
                "Pengguna ini sudah di-gban, karena alasan berikut:\n"
                "<code>{}</code>\n"
                "Saya telah pergi dan memperbaruinya dengan alasan baru Anda!".format(
                    html.escape(old_reason)
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            message.reply_text(
                "Pengguna ini sudah di-gban, tetapi alasan tidak ditetapkan; Saya telah pergi dan memperbaruinya!"
            )

        return

    message.reply_text("On it!")

    start_time = time.time()
    datetime_fmt = "%Y-%m-%dT%H:%M"
    current_time = datetime.utcnow().strftime(datetime_fmt)

    if chat.type != "private":
        chat_origin = "<b>{} ({})</b>\n".format(html.escape(chat.title), chat.id)
    else:
        chat_origin = "<b>{}</b>\n".format(chat.id)

    log_message = (
        f"#GBANNED\n"
        f"<b>Berasal dari:</b> <code>{chat_origin}</code>\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna yang Dilarang:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
        f"<b>Pengguna yang Dilarang ID:</b> <code>{user_chat.id}</code>\n"
        f"<b>Stempel Acara:</b> <code>{current_time}</code>"
    )

    if reason:
        if chat.type == chat.SUPERGROUP and chat.username:
            log_message += f'\n<b>Alasan:</b> <a href="https://telegram.me/{chat.username}/{message.message_id}">{reason}</a>'
        else:
            log_message += f"\n<b>Alasan:</b> <code>{reason}</code>"

    if GBAN_LOGS:
        try:
            log = bot.send_message(GBAN_LOGS, log_message, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            log = bot.send_message(
                GBAN_LOGS,
                log_message
                + "\n\nPemformatan telah dinonaktifkan karena kesalahan tak terduga.",
            )

    else:
        send_to_list(bot, SUDO_USERS + SUPPORT_USERS, log_message, html=True)

    sql.gban_user(user_id, user_chat.username or user_chat.first_name, reason)

    chats = get_user_com_chats(user_id)
    gbanned_chats = 0

    for chat in chats:
        chat_id = int(chat)

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            bot.kick_chat_member(chat_id, user_id)
            gbanned_chats += 1

        except BadRequest as excp:
            if excp.message not in GBAN_ERRORS:
                message.reply_text(f"Tidak bisa gban karena: {excp.message}")
                if GBAN_LOGS:
                    bot.send_message(
                        GBAN_LOGS,
                        f"Tidak bisa gban karena {excp.message}",
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    send_to_list(
                        bot,
                        SUDO_USERS + SUPPORT_USERS,
                        f"Tidak bisa gban karena: {excp.message}",
                    )
                sql.ungban_user(user_id)
                return
        except TelegramError:
            pass

    if GBAN_LOGS:
        log.edit_text(
            log_message + f"\n<b>Obrolan terpengaruh:</b> <code>{gbanned_chats}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        send_to_list(
            bot,
            SUDO_USERS + SUPPORT_USERS,
            f"Lengkap Gan! (Pengguna dilarang masuk <code>{gbanned_chats}</code> chats)",
            html=True,
        )

    end_time = time.time()
    gban_time = round((end_time - start_time), 2)

    if gban_time > 60:
        gban_time = round((gban_time / 60), 2)
    message.reply_text("Selesai! Dilarang.", parse_mode=ParseMode.HTML)
    try:
        bot.send_message(
            user_id,
            "#GBAN"
            "Anda telah ditandai sebagai Berbahaya dan dengan demikian telah dilarang dari grup mana pun yang kami kelola di masa mendatang."
            f"\n<b>Alasan:</b> <code>{html.escape(user.reason)}</code>"
            f"</b>Obrolan banding:</b> @medsupportt",
            parse_mode=ParseMode.HTML,
        )
    except:
        pass  # bot probably blocked by user


@zaid(command="ungban")
@support_plus
def ungban(update: Update, context: CallbackContext):  # sourcery no-metrics
    bot, args = context.bot, context.args
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""

    user_id = extract_user(message, args)

    if not user_id:
        message.reply_text(
            "Sepertinya Anda tidak merujuk ke pengguna atau ID yang ditentukan salah.."
        )
        return

    user_chat = bot.get_chat(user_id)
    if user_chat.type != "private":
        message.reply_text("Itu bukan pengguna!")
        return

    if not sql.is_user_gbanned(user_id):
        message.reply_text("Pengguna ini tidak dilarang!")
        return

    message.reply_text(f"Saya akan memberikan {user_chat.first_name} kesempatan kedua, secara global.")

    start_time = time.time()
    datetime_fmt = "%Y-%m-%dT%H:%M"
    current_time = datetime.utcnow().strftime(datetime_fmt)

    if chat.type != "private":
        chat_origin = f"<b>{html.escape(chat.title)} ({chat.id})</b>\n"
    else:
        chat_origin = f"<b>{chat.id}</b>\n"

    log_message = (
        f"#UNGBANNED\n"
        f"<b>Berasal dari:</b> <code>{chat_origin}</code>\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"<b>Pengguna yang Tidak Diblokir:</b> {mention_html(user_chat.id, user_chat.first_name)}\n"
        f"<b>Pengguna yang Tidak Diblokir ID:</b> <code>{user_chat.id}</code>\n"
        f"<b>Stempel Acara:</b> <code>{current_time}</code>"
    )

    if GBAN_LOGS:
        try:
            log = bot.send_message(GBAN_LOGS, log_message, parse_mode=ParseMode.HTML)
        except BadRequest as excp:
            log = bot.send_message(
                GBAN_LOGS,
                log_message
                + "\n\nPemformatan telah dinonaktifkan karena kesalahan tak terduga.",
            )
    else:
        send_to_list(bot, SUDO_USERS + SUPPORT_USERS, log_message, html=True)

    chats = get_user_com_chats(user_id)
    ungbanned_chats = 0

    for chat in chats:
        chat_id = int(chat)

        # Check if this group has disabled gbans
        if not sql.does_chat_gban(chat_id):
            continue

        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status == "kicked":
                bot.unban_chat_member(chat_id, user_id)
                ungbanned_chats += 1

        except BadRequest as excp:
            if excp.message not in UNGBAN_ERRORS:
                message.reply_text(f"Tidak dapat membatalkan gban karena : {excp.message}")
                if GBAN_LOGS:
                    bot.send_message(
                        GBAN_LOGS,
                        f"Tidak dapat membatalkan gban karena : {excp.message}",
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    bot.send_message(
                        OWNER_ID, f"Tidak dapat membatalkan gban karena : {excp.message}"
                    )
                return
        except TelegramError:
            pass

    sql.ungban_user(user_id)

    if GBAN_LOGS:
        log.edit_text(
            log_message + f"\n<b>Obrolan terpengaruh:</b> {ungbanned_chats}",
            parse_mode=ParseMode.HTML,
        )
    else:
        send_to_list(bot, SUDO_USERS + SUPPORT_USERS, "un-gban selesai!")

    end_time = time.time()
    ungban_time = round((end_time - start_time), 2)

    if ungban_time > 60:
        ungban_time = round((ungban_time / 60), 2)
        message.reply_text(f"Orang telah dicabut larangannya. Butuh waktu {ungban_time} mnt")
    else:
        message.reply_text(f"Orang telah dicabut larangannya. Butuh waktu {ungban_time} det")


@zaid(command="gbanlist")
@support_plus
def gbanlist(update: Update, context: CallbackContext):
    banned_users = sql.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text(
            "Tidak ada pengguna yang dilarang! Anda lebih baik dari yang saya harapkan..."
        )
        return

    banfile = "Persetan dengan orang-orang ini.\n"
    for user in banned_users:
        banfile += f"[x] {user['name']} - {user['user_id']}\n"
        if user["reason"]:
            banfile += f"Reason: {user['reason']}\n"

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="gbanlist.txt",
            caption="Berikut adalah daftar pengguna yang saat ini di-gban.",
        )


def check_and_ban(update, user_id, should_message=True):
    chat = update.effective_chat  # type: Optional[Chat]
    try:
        sw_ban = sw.get_ban(int(user_id))
    except AttributeError:
        sw_ban = None
    except (SpamWatchError, Error, UnauthorizedError, NotFoundError, Forbidden, TooManyRequests) as e:
        log.warning(f" Kesalahan Jam Spam: {e}")
        sw_ban = None

    if sw_ban:
        chat.ban_member(user_id)
        if should_message:
            update.effective_message.reply_text(
                f"Orang ini telah terdeteksi sebagai spammer oleh @SpamWatch dan telah dihapus!\nAlasan: <code>{sw_ban.reason}</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    if sql.is_user_gbanned(user_id):
        update.effective_chat.ban_member(user_id)
        if should_message:
            text = (
                f"<b>Alert</b>: pengguna ini dilarang secara global.\n"
                f"<code>*melarang mereka dari sini*</code>.\n"
                f"<b>Appeal chat</b>: @medsupportt\n"
                f"<b>User ID</b>: <code>{user_id}</code>"
            )
            user = sql.get_gbanned_user(user_id)
            if user.reason:
                text += f"\n<b>Alasan Larangan:</b> <code>{html.escape(user.reason)}</code>"
            update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


@zaidmsg((Filters.all & Filters.chat_type.groups), can_disable=False, group=GBAN_ENFORCE_GROUP)
def enforce_gban(update: Update, context: CallbackContext):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    bot = context.bot
    if (
            sql.does_chat_gban(update.effective_chat.id)
            and update.effective_chat.get_member(bot.id).can_restrict_members
    ):
        user = update.effective_user
        chat = update.effective_chat
        msg = update.effective_message

        if user and not is_user_admin(update, user.id):
            check_and_ban(update, user.id)
            return

        if msg.new_chat_members:
            new_members = update.effective_message.new_chat_members
            for mem in new_members:
                check_and_ban(update, mem.id)

        if msg.reply_to_message:
            user = msg.reply_to_message.from_user
            if user and not is_user_admin(update, user.id):
                check_and_ban(update, user.id, should_message=False)


@zaid(command="antispam")
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def gbanstat(update: Update, context: CallbackContext):
    args = context.args
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            sql.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "Saya telah mengaktifkan gban di grup ini. Ini akan membantu melindungi Anda "
                "dari spammer, karakter jahat, dan troll terbesar."
            )
        elif args[0].lower() in ["off", "no"]:
            sql.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "Saya telah menonaktifkan gban di grup ini. GBans tidak akan memengaruhi pengguna Anda "
                "lagi. Anda akan kurang terlindungi dari troll dan spammer"
                "meskipun!"
            )
    else:
        update.effective_message.reply_text(
            "Beri saya beberapa argumen untuk memilih pengaturan! aktif/nonaktif, ya/tidak!\n\n"
            "Setelan Anda saat ini adalah: {\n"
            "Bila Benar, setiap gban yang terjadi juga akan terjadi di grup Anda."
            "Ketika Salah, mereka tidak akan melakukannya, meninggalkan Anda pada belas kasihan yang mungkin dari"
            "spammer.".format(sql.does_chat_gban(update.effective_chat.id))
        )


def __stats__():
    return f"• {sql.num_gbanned_users()} pengguna yang dilarang."


def __user_info__(user_id):
    if user_id in (777000, 1087968824):
        return ""

    is_gbanned = sql.is_user_gbanned(user_id)
    text = "Gbanned: <b>{}</b>"
    if user_id in [777000, 1087968824]:
        return ""
    if user_id == dispatcher.bot.id:
        return ""
    if int(user_id) in SUDO_USERS + SARDEGNA_USERS + WHITELIST_USERS:
        return ""
    if is_gbanned:
        text = text.format("Yes")
        user = sql.get_gbanned_user(user_id)
        if user.reason:
            text += f"\n<b>Alasan :</b> <code>{html.escape(user.reason)}</code>"
        text += '\n<b>Obrolan banding :</b> @medsupportt'
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return f"Obrolan ini berlaku *gbans*: `{sql.does_chat_gban(chat_id)}`."


from Telegram.modules.language import gs


def get_help(chat):
    return gs(chat, "antispam_help")


__mod_name__ = 'AntiSpam'
