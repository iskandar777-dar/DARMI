import html
import re
from telegram import ParseMode, ChatPermissions
from telegram.error import BadRequest
from telegram.ext import Filters
from telegram.utils.helpers import mention_html
from Telegram.modules.sql.approve_sql import is_approved
import Telegram.modules.sql.blacklist_sql as sql
from Telegram import log, dispatcher
from Telegram.modules.helper_funcs.chat_status import user_admin as u_admin, user_not_admin
from Telegram.modules.helper_funcs.extraction import extract_text
from Telegram.modules.helper_funcs.misc import split_message
from Telegram.modules.log_channel import loggable
from Telegram.modules.warns import warn
from Telegram.modules.helper_funcs.string_handling import extract_time
from Telegram.modules.connection import connected
from Telegram.modules.helper_funcs.decorators import zaid, zaidmsg
from Telegram.modules.helper_funcs.alternate import send_message, typing_action

from ..modules.helper_funcs.anonymous import user_admin, AdminPerms

BLACKLIST_GROUP = -3

@zaid(command="blacklist", pass_args=True, admin_ok=True)
@u_admin
@typing_action
def blacklist(update, context):
    chat = update.effective_chat
    user = update.effective_user
    args = context.args

    conn = connected(context.bot, update, chat, user.id, need_admin=False)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if chat.type == "private":
            return
        chat_id = update.effective_chat.id
        chat_name = chat.title
    chat_name = html.escape(chat_name)

    filter_list = "Kata-kata yang masuk daftar hitam saat ini di <b>{}</b>:\n".format(chat_name)

    all_blacklisted = sql.get_chat_blacklist(chat_id)

    if len(args) > 0 and args[0].lower() == "copy":
        for trigger in all_blacklisted:
            filter_list += "<code>{}</code>\n".format(html.escape(trigger))
    else:
        for trigger in all_blacklisted:
            filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    # for trigger in all_blacklisted:
    #     filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message(filter_list)
    for text in split_text:
        if filter_list == "Kata-kata yang masuk daftar hitam saat ini di <b>{}</b>:\n".format(chat_name):
            send_message(
                update.effective_message,
                "Tidak ada kata-kata yang masuk daftar hitam <b>{}</b>!".format(chat_name),
                parse_mode=ParseMode.HTML,
            )
            return
        send_message(update.effective_message, text, parse_mode=ParseMode.HTML)

@zaid(command="addblacklist", pass_args=True)
@user_admin(AdminPerms.CAN_DELETE_MESSAGES)
@typing_action
def add_blacklist(update, context):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    words = msg.text.split(None, 1)

    conn = connected(context.bot, update, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            return
        else:
            chat_name = chat.title
    chat_name = html.escape(chat_name)

    if len(words) > 1:
        text = words[1]
        to_blacklist = list(
            {
                trigger.strip()
                for trigger in text.split("\n")
                if trigger.strip()
            }
        )

        for trigger in to_blacklist:
            sql.add_to_blacklist(chat_id, trigger.lower())

        if len(to_blacklist) == 1:
            send_message(
                update.effective_message,
                "Menambahkan daftar hitam <code>{}</code> dalam obrolan: <b>{}</b>!".format(
                    html.escape(to_blacklist[0]), chat_name
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            send_message(
                update.effective_message,
                "Menambahkan pemicu daftar hitam: <code>{}</code> in <b>{}</b>!".format(
                    len(to_blacklist), chat_name
                ),
                parse_mode=ParseMode.HTML,
            )

    else:
        send_message(
            update.effective_message,
            "Beri tahu saya kata-kata mana yang ingin Anda tambahkan ke daftar hitam.",
        )

@zaid(command="unblacklist", pass_args=True)
@user_admin(AdminPerms.CAN_DELETE_MESSAGES)
@typing_action
def unblacklist(update, context):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    words = msg.text.split(None, 1)

    conn = connected(context.bot, update, chat, user.id)
    if conn:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            return
        else:
            chat_name = chat.title
    chat_name = html.escape(chat_name)

    if len(words) > 1:
        text = words[1]
        to_unblacklist = list(
            {
                trigger.strip()
                for trigger in text.split("\n")
                if trigger.strip()
            }
        )

        successful = 0
        for trigger in to_unblacklist:
            success = sql.rm_from_blacklist(chat_id, trigger.lower())
            if success:
                successful += 1

        if len(to_unblacklist) == 1:
            if successful:
                send_message(
                    update.effective_message,
                    "Menghapus <code>{}</code> dari daftar hitam di <b>{}</b>!".format(
                        html.escape(to_unblacklist[0]), chat_name
                    ),
                    parse_mode=ParseMode.HTML,
                )
            else:
                send_message(
                    update.effective_message, "Ini bukan pemicu daftar hitam!"
                )

        elif successful == len(to_unblacklist):
            send_message(
                update.effective_message,
                "Menghapus <code>{}</code> dari daftar hitam di <b>{}</b>!".format(
                    successful, chat_name
                ),
                parse_mode=ParseMode.HTML,
            )

        elif not successful:
            send_message(
                update.effective_message,
                "Tak satu pun dari pemicu ini ada sehingga tidak dapat dihapus.".format(
                    successful, len(to_unblacklist) - successful
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            send_message(
                update.effective_message,
                "Menghapus <code>{}</code> dari daftar hitam. {} Tidak ada, "
                "Jadi tidak dihapus.".format(
                    successful, len(to_unblacklist) - successful
                ),
                parse_mode=ParseMode.HTML,
            )
    else:
        send_message(
            update.effective_message,
            "Beri tahu saya kata mana yang ingin Anda hapus dari daftar hitam!",
        )

@zaid(command="blacklistmode", pass_args=True)
@loggable
@user_admin(AdminPerms.CAN_RESTRICT_MEMBERS)
@typing_action
def blacklist_mode(update, context):  # sourcery no-metrics
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    args = context.args

    conn = connected(context.bot, update, chat, user.id, need_admin=True)
    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type == "private":
            send_message(
                update.effective_message,
                "Perintah ini hanya dapat digunakan di grup bukan di PM",
            )
            return ""
        chat = update.effective_chat
        chat_id = update.effective_chat.id
        chat_name = update.effective_message.chat.title
    chat_name = html.escape(chat_name)

    if args:
        if args[0].lower() in ["off", "nothing", "no"]:
            settypeblacklist = "tidak melakukan apapun"
            sql.set_blacklist_strength(chat_id, 0, "0")
        elif args[0].lower() in ["del", "delete"]:
            settypeblacklist = "akan menghapus pesan yang masuk daftar hitam"
            sql.set_blacklist_strength(chat_id, 1, "0")
        elif args[0].lower() == "warn":
            settypeblacklist = "memperingatkan pengirim"
            sql.set_blacklist_strength(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            settypeblacklist = "membisukan pengirim"
            sql.set_blacklist_strength(chat_id, 3, "0")
        elif args[0].lower() == "kick":
            settypeblacklist = "tendang pengirimnya"
            sql.set_blacklist_strength(chat_id, 4, "0")
        elif args[0].lower() == "ban":
            settypeblacklist = "melarang pengirim"
            sql.set_blacklist_strength(chat_id, 5, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                teks = """Sepertinya Anda mencoba menyetel nilai waktu untuk daftar hitam tetapi Anda tidak menentukan waktu; Coba, `/blacklistmode tban <timevalue>`.

Contoh nilai waktu: 4m = 4 menit, 3h = 3 jam, 6d = 6 hari, 5w = 5 minggu."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            restime = extract_time(msg, args[1])
            if not restime:
                teks = """Invalid time value!
Contoh nilai waktu: 4m = 4 menit, 3h = 3 jam, 6d = 6 hari, 5w = 5 minggu."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            settypeblacklist = "larangan sementara untuk {}".format(args[1])
            sql.set_blacklist_strength(chat_id, 6, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                teks = """Sepertinya Anda mencoba menyetel nilai waktu untuk daftar hitam tetapi Anda tidak menentukan waktu; coba, `/blacklistmode tmute <timevalue>`.

Examples of time value: 4m = 4 minutes, 3h = 3 hours, 6d = 6 days, 5w = 5 weeks."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            restime = extract_time(msg, args[1])
            if not restime:
                teks = """Invalid time value!
Contoh nilai waktu: 4m = 4 menit, 3h = 3 jam, 6d = 6 hari, 5w = 5 minggu."""
                send_message(update.effective_message, teks, parse_mode="markdown")
                return ""
            settypeblacklist = "bisu sementara untuk {}".format(args[1])
            sql.set_blacklist_strength(chat_id, 7, str(args[1]))
        else:
            send_message(
                update.effective_message,
                "Saya hanya mengerti: off/del/warn/ban/kick/mute/tban/tmute!",
            )
            return ""
        if conn:
            text = "Mengubah mode daftar hitam: `{}` in *{}*!".format(
                settypeblacklist, chat_name
            )
        else:
            text = "Mengubah mode daftar hitam: `{}`!".format(settypeblacklist)
        send_message(update.effective_message, text, parse_mode="markdown")
        return (
            "<b>{}:</b>\n"
            "<b>Admin:</b> {}\n"
            "Mengubah mode daftar hitam. akan {}.".format(
                html.escape(chat.title),
                mention_html(user.id, user.first_name),
                settypeblacklist,
            )
        )
    else:
        getmode, getvalue = sql.get_blacklist_setting(chat.id)
        if getmode == 0:
            settypeblacklist = "do nothing"
        elif getmode == 1:
            settypeblacklist = "delete"
        elif getmode == 2:
            settypeblacklist = "warn"
        elif getmode == 3:
            settypeblacklist = "mute"
        elif getmode == 4:
            settypeblacklist = "kick"
        elif getmode == 5:
            settypeblacklist = "ban"
        elif getmode == 6:
            settypeblacklist = "larangan sementara untuk {}".format(getvalue)
        elif getmode == 7:
            settypeblacklist = "bisu sementara untuk {}".format(getvalue)
        if conn:
            text = "mode daftar hitam saat ini: *{}* di *{}*.".format(
                settypeblacklist, chat_name
            )
        else:
            text = "Mode daftar hitam saat ini: *{}*.".format(settypeblacklist)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)
    return ""


def findall(p, s):
    i = s.find(p)
    while i != -1:
        yield i
        i = s.find(p, i + 1)



@zaidmsg(((Filters.text | Filters.command | Filters.sticker | Filters.photo) & Filters.chat_type.groups), group=BLACKLIST_GROUP)
@user_not_admin
def del_blacklist(update, context):  # sourcery no-metrics
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    bot = context.bot
    to_match = extract_text(message)
    if not to_match:
        return
    if is_approved(chat.id, user.id):
        return
    getmode, value = sql.get_blacklist_setting(chat.id)

    chat_filters = sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                if getmode == 0:
                    return
                elif getmode == 1:
                    message.delete()
                elif getmode == 2:
                    message.delete()
                    warn(
                        update.effective_user,
                        update,
                        ("Menggunakan pemicu daftar hitam: {}".format(trigger)),
                        message,
                        update.effective_user,
                    )
                    return
                elif getmode == 3:
                    message.delete()
                    bot.restrict_chat_member(
                        chat.id,
                        update.effective_user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                    )
                    bot.sendMessage(
                        chat.id,
                        f"Meredam {user.first_name} karena menggunakan kata Daftar Hitam: {trigger}!",
                    )
                    return
                elif getmode == 4:
                    message.delete()
                    res = chat.unban_member(update.effective_user.id)
                    if res:
                        bot.sendMessage(
                            chat.id,
                            f"Ditendang {user.first_name} karena menggunakan kata Daftar Hitam: {trigger}!",
                        )
                    return
                elif getmode == 5:
                    message.delete()
                    chat.ban_member(user.id)
                    bot.sendMessage(
                        chat.id,
                        f"Dilarang {user.first_name} karena menggunakan kata Daftar Hitam: {trigger}",
                    )
                    return
                elif getmode == 6:
                    message.delete()
                    bantime = extract_time(message, value)
                    chat.ban_member(user.id, until_date=bantime)
                    bot.sendMessage(
                        chat.id,
                        f"Dilarang {user.first_name} until '{value}' karena menggunakan kata Daftar Hitam: {trigger}!",
                    )
                    return
                elif getmode == 7:
                    message.delete()
                    mutetime = extract_time(message, value)
                    bot.restrict_chat_member(
                        chat.id,
                        user.id,
                        until_date=mutetime,
                        permissions=ChatPermissions(can_send_messages=False),
                    )
                    bot.sendMessage(
                        chat.id,
                        f"Meredam {user.first_name} sampai '{value}' karena menggunakan kata Daftar Hitam: {trigger}!",
                    )
                    return
            except BadRequest as excp:
                if excp.message != "Pesan untuk dihapus tidak ditemukan":
                    log.exception("Kesalahan saat menghapus pesan daftar hitam.")
            break


def __import_data__(chat_id, data):
    # set chat blacklist
    blacklist = data.get("blacklist", {})
    for trigger in blacklist:
        sql.add_to_blacklist(chat_id, trigger)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    blacklisted = sql.num_blacklist_chat_filters(chat_id)
    return "Ada {} kata yang masuk daftar hitam.".format(blacklisted)


def __stats__():
    return "• {} pemicu daftar hitam, di {} obrolan.".format(
        sql.num_blacklist_filters(), sql.num_blacklist_filter_chats()
    )


__mod_name__ = "Blacklists"

from Telegram.modules.language import gs

def get_help(chat):
    return gs(chat, "blacklist_help")
