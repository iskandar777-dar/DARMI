import time
import re

from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, Update, Bot
from telegram.error import BadRequest, Unauthorized
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
)

import Telegram.modules.sql.connection_sql as sql
from Telegram import dispatcher, SUDO_USERS, DEV_USERS
from Telegram.modules.helper_funcs import chat_status
from Telegram.modules.helper_funcs.alternate import send_message, typing_action

user_admin = chat_status.user_admin


@user_admin
@typing_action
def allow_connections(update, context) -> str:

    chat = update.effective_chat
    args = context.args

    if chat.type != chat.PRIVATE:
        if len(args) >= 1:
            var = args[0]
            if var == "no":
                sql.set_allow_connect_to_chat(chat.id, False)
                send_message(
                    update.effective_message,
                    "Koneksi telah dinonaktifkan untuk obrolan ini",
                )
            elif var == "yes":
                sql.set_allow_connect_to_chat(chat.id, True)
                send_message(
                    update.effective_message,
                    "Koneksi telah diaktifkan untuk obrolan ini",
                )
            else:
                send_message(
                    update.effective_message,
                    "Silakan masuk `yes` atau `no`!",
                    parse_mode=ParseMode.MARKDOWN,
                )
        else:
            get_settings = sql.allow_connect_to_chat(chat.id)
            if get_settings:
                send_message(
                    update.effective_message,
                    "Koneksi ke grup ini *Diizinkan* untuk anggota!",
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                send_message(
                    update.effective_message,
                    "Koneksi ke grup ini *Tidak Diizinkan* untuk anggota!",
                    parse_mode=ParseMode.MARKDOWN,
                )
    else:
        send_message(
            update.effective_message, "Perintah ini hanya untuk grup. Tidak di PM!"
        )


@typing_action
def connection_chat(update, context):

    chat = update.effective_chat
    user = update.effective_user

    conn = connected(context.bot, update, chat, user.id, need_admin=True)

    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type != "private":
            return
        chat = update.effective_chat
        chat_name = update.effective_message.chat.title

    if conn:
        message = "Anda saat ini terhubung ke {}.\n".format(chat_name)
    else:
        message = "Saat ini Anda tidak terhubung dalam grup mana pun.\n"
    send_message(update.effective_message, message, parse_mode="markdown")


@typing_action
def connect_chat(update, context):  # sourcery no-metrics

    chat = update.effective_chat
    user = update.effective_user
    args = context.args

    if update.effective_chat.type == "private":
        if args and len(args) >= 1:
            try:
                connect_chat = int(args[0])
                getstatusadmin = context.bot.get_chat_member(
                    connect_chat, update.effective_message.from_user.id
                )
            except ValueError:
                try:
                    connect_chat = str(args[0])
                    get_chat = context.bot.getChat(connect_chat)
                    connect_chat = get_chat.id
                    getstatusadmin = context.bot.get_chat_member(
                        connect_chat, update.effective_message.from_user.id
                    )
                except BadRequest:
                    send_message(update.effective_message, "ID Obrolan tidak valid!")
                    return
            except BadRequest:
                send_message(update.effective_message, "ID Obrolan tidak valid!")
                return

            isadmin = getstatusadmin.status in ("administrator", "creator")
            ismember = getstatusadmin.status == "member"
            isallow = sql.allow_connect_to_chat(connect_chat)

            if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
                connection_status = sql.connect(
                    update.effective_message.from_user.id, connect_chat
                )
                if connection_status:
                    conn_chat = dispatcher.bot.getChat(
                        connected(context.bot, update, chat, user.id, need_admin=False)
                    )
                    chat_name = conn_chat.title
                    send_message(
                        update.effective_message,
                        "Berhasil terhubung ke *{}*. \nGunakan /helpconnect untuk memeriksa perintah yang tersedia.".format(
                            chat_name
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    sql.add_history_conn(user.id, str(conn_chat.id), chat_name)
                else:
                    send_message(update.effective_message, "Koneksi gagal!")
            else:
                send_message(
                    update.effective_message, "Sambungan ke obrolan ini tidak diizinkan!"
                )
        else:
            gethistory = sql.get_history_conn(user.id)
            if gethistory:
                buttons = [
                    InlineKeyboardButton(
                        text="❎ Tombol tutup", callback_data="connect_close"
                    ),
                    InlineKeyboardButton(
                        text="🧹 Hapus riwayat", callback_data="connect_clear"
                    ),
                ]
            else:
                buttons = []
            conn = connected(context.bot, update, chat, user.id, need_admin=False)
            if conn:
                connectedchat = dispatcher.bot.getChat(conn)
                text = "Anda saat ini terhubung ke *{}* (`{}`)".format(
                    connectedchat.title, conn
                )
                buttons.append(
                    InlineKeyboardButton(
                        text="🔌 Memutuskan", callback_data="connect_disconnect"
                    )
                )
            else:
                text = "Tulis ID obrolan atau tag untuk terhubung!"
            if gethistory:
                text += "\n\n*Sejarah koneksi:*\n"
                text += "╒═══「 *Info* 」\n"
                text += "│  Diurutkan: `Terbaru`\n"
                text += "│\n"
                buttons = [buttons]
                for x in sorted(gethistory.keys(), reverse=True):
                    htime = time.strftime("%d/%m/%Y", time.localtime(x))
                    text += "╞═「 *{}* 」\n│   `{}`\n│   `{}`\n".format(
                        gethistory[x]["chat_name"], gethistory[x]["chat_id"], htime
                    )
                    text += "│\n"
                    buttons.append(
                        [
                            InlineKeyboardButton(
                                text=gethistory[x]["chat_name"],
                                callback_data="connect({})".format(
                                    gethistory[x]["chat_id"]
                                ),
                            )
                        ]
                    )
                text += "╘══「 Total {} Chats 」".format(
                    str(len(gethistory)) + " (max)"
                    if len(gethistory) == 5
                    else str(len(gethistory))
                )
                conn_hist = InlineKeyboardMarkup(buttons)
            elif buttons:
                conn_hist = InlineKeyboardMarkup([buttons])
            else:
                conn_hist = None
            send_message(
                update.effective_message,
                text,
                parse_mode="markdown",
                reply_markup=conn_hist,
            )

    else:
        getstatusadmin = context.bot.get_chat_member(
            chat.id, update.effective_message.from_user.id
        )
        isadmin = getstatusadmin.status in ("administrator", "creator")
        ismember = getstatusadmin.status == "member"
        isallow = sql.allow_connect_to_chat(chat.id)
        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
            connection_status = sql.connect(
                update.effective_message.from_user.id, chat.id
            )
            if connection_status:
                chat_name = dispatcher.bot.getChat(chat.id).title
                send_message(
                    update.effective_message,
                    "Berhasil terhubung ke *{}*.".format(chat_name),
                    parse_mode=ParseMode.MARKDOWN,
                )
                try:
                    sql.add_history_conn(user.id, str(chat.id), chat_name)
                    context.bot.send_message(
                        update.effective_message.from_user.id,
                        "Anda terhubung ke *{}*. \nGunakan `/helpconnect` untuk memeriksa perintah yang tersedia.".format(
                            chat_name
                        ),
                        parse_mode="markdown",
                    )
                except BadRequest:
                    pass
                except Unauthorized:
                    pass
            else:
                send_message(update.effective_message, "Koneksi gagal!")
        else:
            send_message(
                update.effective_message, "Sambungan ke obrolan ini tidak diizinkan!"
            )


def disconnect_chat(update, context):

    if update.effective_chat.type == "private":
        disconnection_status = sql.disconnect(update.effective_message.from_user.id)
        if disconnection_status:
            sql.disconnected_chat = send_message(
                update.effective_message, "Terputus dari obrolan!"
            )
        else:
            send_message(update.effective_message, "Anda tidak terhubung!")
    else:
        send_message(update.effective_message, "Perintah ini hanya tersedia di PM.")


def connected(bot: Bot, update: Update, chat, user_id, need_admin=True):
    user = update.effective_user

    if chat.type == chat.PRIVATE and sql.get_connected_chat(user_id):

        conn_id = sql.get_connected_chat(user_id).chat_id
        getstatusadmin = bot.get_chat_member(
            conn_id, update.effective_message.from_user.id
        )
        isadmin = getstatusadmin.status in ("administrator", "creator")
        ismember = getstatusadmin.status == "member"
        isallow = sql.allow_connect_to_chat(conn_id)

        if (
            (isadmin)
            or (isallow and ismember)
            or (user.id in SUDO_USERS)
            or (user.id in DEV_USERS)
        ):
            if need_admin is not True:
                return conn_id
            if (
                getstatusadmin.status in ("administrator", "creator")
                or user_id in SUDO_USERS
                or user.id in DEV_USERS
            ):
                return conn_id
            else:
                send_message(
                    update.effective_message,
                    "Anda harus menjadi admin di grup yang terhubung!",
                )
        else:
            send_message(
                update.effective_message,
                "Grup mengubah hak koneksi atau Anda tidak lagi menjadi admin.\nSaya telah memutuskan hubungan Anda.",
            )
            disconnect_chat(update, bot)
    else:
        return False


CONN_HELP = """
Tindakan tersedia dengan grup yang terhubung:
• Melihat dan mengedit Catatan.
• Lihat dan edit Filter.
• Dapatkan tautan undangan obrolan.
• Mengatur dan mengontrol pengaturan AntiFlood.
• Mengatur dan mengontrol pengaturan Daftar Hitam.
• Setel Kunci dan Buka di obrolan.
• Aktifkan dan Nonaktifkan perintah dalam obrolan.
• Ekspor dan Impor cadangan obrolan.
• Lebih banyak lagi di masa depan!"""


def help_connect_chat(update, context):

    args = context.args

    if update.effective_message.chat.type != "private":
        send_message(update.effective_message, "PM saya dengan perintah itu untuk mendapatkan bantuan.")
        return
    else:
        send_message(update.effective_message, CONN_HELP, parse_mode="markdown")


def connect_button(update, context):

    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user

    connect_match = re.match(r"connect\((.+?)\)", query.data)
    disconnect_match = query.data == "connect_disconnect"
    clear_match = query.data == "connect_clear"
    connect_close = query.data == "connect_close"

    if connect_match:
        target_chat = connect_match.group(1)
        getstatusadmin = context.bot.get_chat_member(target_chat, query.from_user.id)
        isadmin = getstatusadmin.status in ("administrator", "creator")
        ismember = getstatusadmin.status == "member"
        isallow = sql.allow_connect_to_chat(target_chat)

        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
            connection_status = sql.connect(query.from_user.id, target_chat)

            if connection_status:
                conn_chat = dispatcher.bot.getChat(
                    connected(context.bot, update, chat, user.id, need_admin=False)
                )
                chat_name = conn_chat.title
                query.message.edit_text(
                    "Berhasil terhubung ke *{}*. \nGunakan `/helpconnect` untuk memeriksa perintah yang tersedia.".format(
                        chat_name
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                sql.add_history_conn(user.id, str(conn_chat.id), chat_name)
            else:
                query.message.edit_text("Koneksi gagal!")
        else:
            context.bot.answer_callback_query(
                query.id, "Sambungan ke obrolan ini tidak diizinkan!", show_alert=True
            )
    elif disconnect_match:
        disconnection_status = sql.disconnect(query.from_user.id)
        if disconnection_status:
            sql.disconnected_chat = query.message.edit_text("Terputus dari obrolan!")
        else:
            context.bot.answer_callback_query(
                query.id, "Anda tidak terhubung!", show_alert=True
            )
    elif clear_match:
        sql.clear_history_conn(query.from_user.id)
        query.message.edit_text("Riwayat terhubung telah dihapus!")
    elif connect_close:
        query.message.edit_text("Tertutup.\nUntuk membuka lagi, ketik /sambungkan")
    else:
        connect_chat(update, context)


from Telegram.modules.language import gs

def get_help(chat):
    return gs(chat, "connections_help")

CONNECT_CHAT_HANDLER = CommandHandler("connect", connect_chat, pass_args=True)
CONNECTION_CHAT_HANDLER = CommandHandler("connection", connection_chat, run_async=True)
DISCONNECT_CHAT_HANDLER = CommandHandler("disconnect", disconnect_chat, run_async=True)
ALLOW_CONNECTIONS_HANDLER = CommandHandler(
    "allowconnect", allow_connections, pass_args=True, run_async=True
)
HELP_CONNECT_CHAT_HANDLER = CommandHandler(
    "helpconnect", help_connect_chat, run_async=True
)
CONNECT_BTN_HANDLER = CallbackQueryHandler(
    connect_button, pattern=r"connect", run_async=True
)

dispatcher.add_handler(CONNECT_CHAT_HANDLER)
dispatcher.add_handler(CONNECTION_CHAT_HANDLER)
dispatcher.add_handler(DISCONNECT_CHAT_HANDLER)
dispatcher.add_handler(ALLOW_CONNECTIONS_HANDLER)
dispatcher.add_handler(HELP_CONNECT_CHAT_HANDLER)
dispatcher.add_handler(CONNECT_BTN_HANDLER)

__mod_name__ = "Connection"
__handlers__ = [
    CONNECT_CHAT_HANDLER,
    CONNECTION_CHAT_HANDLER,
    DISCONNECT_CHAT_HANDLER,
    ALLOW_CONNECTIONS_HANDLER,
    HELP_CONNECT_CHAT_HANDLER,
    CONNECT_BTN_HANDLER,
]
