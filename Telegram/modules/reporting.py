import html

from Telegram import log, SUDO_USERS, SARDEGNA_USERS, WHITELIST_USERS
from Telegram.modules.helper_funcs.chat_status import user_not_admin
from Telegram.modules.log_channel import loggable
from Telegram.modules.sql import reporting_sql as sql
from telegram import Chat, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import BadRequest, Unauthorized
from telegram.ext import (
    CallbackContext,
    Filters,
)
import Telegram.modules.sql.log_channel_sql as logsql
from telegram.utils.helpers import mention_html
from Telegram.modules.helper_funcs.decorators import zaid, zaidmsg, zaidcallback

from ..modules.helper_funcs.anonymous import user_admin, AdminPerms

REPORT_GROUP = 12
REPORT_IMMUNE_USERS = SUDO_USERS + SARDEGNA_USERS + WHITELIST_USERS


@zaid(command='reports')
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def report_setting(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    chat = update.effective_chat
    msg = update.effective_message

    if chat.type == chat.PRIVATE:
        if len(args) >= 1:
            if args[0] in ("yes", "on"):
                sql.set_user_setting(chat.id, True)
                msg.reply_text(
                    "Mengaktifkan pelaporan! Anda akan diberi tahu setiap kali ada yang melaporkan sesuatu."
                )

            elif args[0] in ("no", "off"):
                sql.set_user_setting(chat.id, False)
                msg.reply_text("Nonaktifkan pelaporan! Anda tidak akan mendapatkan laporan apapun.")
        else:
            msg.reply_text(
                f"Preferensi laporan Anda saat ini adalah: `{sql.user_should_report(chat.id)}`",
                parse_mode=ParseMode.MARKDOWN,
            )

    elif len(args) >= 1:
        if args[0] in ("yes", "on"):
            sql.set_chat_setting(chat.id, True)
            msg.reply_text(
                "Mengaktifkan pelaporan! Admin yang sudah aktifkan report akan di notif saat /report"
                "atau @admin dipanggil."
            )

        elif args[0] in ("no", "off"):
            sql.set_chat_setting(chat.id, False)
            msg.reply_text(
                "Nonaktifkan pelaporan! Tidak ada admin yang akan diberi tahu di /report atau @admin."
            )
    else:
        msg.reply_text(
            f"Setelan grup ini saat ini adalah: `{sql.chat_should_report(chat.id)}`",
            parse_mode=ParseMode.MARKDOWN,
        )


@zaid(command='report', filters=Filters.chat_type.groups, group=REPORT_GROUP)
@zaidmsg((Filters.regex(r"(?i)@admin(s)?")), group=REPORT_GROUP)
@user_not_admin
@loggable
def report(update: Update, context: CallbackContext) -> str:
    # sourcery no-metrics
    global reply_markup
    bot = context.bot
    args = context.args
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    
    log_setting = logsql.get_chat_setting(chat.id)
    if not log_setting:
        logsql.set_chat_setting(logsql.LogChannelSettings(chat.id, True, True, True, True, True))
        log_setting = logsql.get_chat_setting(chat.id)
        
    if message.sender_chat:
        admin_list = bot.getChatAdministrators(chat.id)
        reported = "Dilaporkan ke admin."
        for admin in admin_list:
            if admin.user.is_bot:  # AI didnt take over yet
                continue
            try:
                reported += f"<a href=\"tg://user?id={admin.user.id}\">\u2063</a>"
            except BadRequest:
                log.exception("Pengecualian saat melaporkan pengguna")
        message.reply_text(reported, parse_mode=ParseMode.HTML)

    if chat and message.reply_to_message and sql.chat_should_report(chat.id):
        reported_user = message.reply_to_message.from_user
        chat_name = chat.title or chat.username
        admin_list = chat.get_administrators()
        message = update.effective_message

        if not args:
            message.reply_text("Tambahkan alasan untuk melaporkan terlebih dahulu.")
            return ""

        if user.id == reported_user.id:
            message.reply_text("Uh yeah, Tentu yakin... sangat banyak?")
            return ""

        if user.id == bot.id:
            message.reply_text("Usaha yang bagus.")
            return ""

        if reported_user.id in REPORT_IMMUNE_USERS:
            message.reply_text("Eh? Anda melaporkan sebuah negara?")
            return ""

        if chat.username and chat.type == Chat.SUPERGROUP:

            reported = f"{mention_html(user.id, user.first_name)} dilaporkan {mention_html(reported_user.id, reported_user.first_name)} kepada admin!"

            msg = (
                f"<b>⚠️ Laporan: </b>{html.escape(chat.title)}\n"
                f"<b> • Laporkan oleh:</b> {mention_html(user.id, user.first_name)}(<code>{user.id}</code>)\n"
                f"<b> • Pengguna yang dilaporkan:</b> {mention_html(reported_user.id, reported_user.first_name)} (<code>{reported_user.id}</code>)\n"
            )
            link = f'<b> • Pesan yang dilaporkan :</b> <a href="https://t.me/{chat.username}/{message.reply_to_message.message_id}">click here</a>'
            should_forward = False
            keyboard = [
                [
                    InlineKeyboardButton(
                        "➡ Pesan",
                        url=f"https://t.me/{chat.username}/{message.reply_to_message.message_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⚠ Tendangan",
                        callback_data=f"report_{chat.id}=kick={reported_user.id}={reported_user.first_name}",
                    ),
                    InlineKeyboardButton(
                        "⛔️ Melarang",
                        callback_data=f"report_{chat.id}=banned={reported_user.id}={reported_user.first_name}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "❎ Hapus pesan",
                        callback_data=f"report_{chat.id}=delete={reported_user.id}={message.reply_to_message.message_id}",
                    )
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            reported = (
                f"{mention_html(user.id, user.first_name)} dilaporkan "
                f"{mention_html(reported_user.id, reported_user.first_name)} kepada admin!"
            )

            msg = f'{mention_html(user.id, user.first_name)} memanggil admin masuk "{html.escape(chat_name)}"!'
            link = ""
            should_forward = True

        for admin in admin_list:
            if admin.user.is_bot:  # can't message bots
                continue

            if sql.user_should_report(admin.user.id):
                try:
                    if chat.type != Chat.SUPERGROUP:
                        bot.send_message(
                            admin.user.id, msg + link, parse_mode=ParseMode.HTML
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                    len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)
                    if not chat.username:
                        bot.send_message(
                            admin.user.id, msg + link, parse_mode=ParseMode.HTML
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                    len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                    if chat.username and chat.type == Chat.SUPERGROUP:
                        bot.send_message(
                            admin.user.id,
                            msg + link,
                            parse_mode=ParseMode.HTML,
                            reply_markup=reply_markup,
                        )

                        if should_forward:
                            message.reply_to_message.forward(admin.user.id)

                            if (
                                    len(message.text.split()) > 1
                            ):  # If user is giving a reason, send his message too
                                message.forward(admin.user.id)

                except Unauthorized:
                    pass
                except BadRequest as excp:  # TODO: cleanup exceptions
                    log.exception("Pengecualian saat melaporkan pengguna\n{}".format(excp))

        try:
            update.effective_message.reply_sticker(
                "CAACAgUAAx0CRSKHWwABAXGoYB2UJauytkH4RJWSStz9DTlxQg0AAlcHAAKAUF41_sNx9Y1z2DQeBA")
        except:
            pass
        message.reply_to_message.reply_text(
            reported,
            parse_mode=ParseMode.HTML,
        )
        if not log_setting.log_report:
            return ""
        return msg

    return ""


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, _):
    return f"Obrolan ini disiapkan untuk mengirimkan laporan pengguna ke admin, melalui /report dan @admin: `{sql.chat_should_report(chat_id)}`"


def __user_settings__(user_id):
    if sql.user_should_report(user_id) is True:
        return "Anda akan menerima laporan dari obrolan yang Anda kelola."
    else:
        return "Anda *tidak* akan menerima laporan dari obrolan yang Anda kelola."


@zaidcallback(pattern=r"report_")
def buttons(update: Update, context: CallbackContext):
    bot = context.bot
    query = update.callback_query
    splitter = query.data.replace("report_", "").split("=")
    if splitter[1] == "kick":
        try:
            bot.kickChatMember(splitter[0], splitter[2])
            bot.unbanChatMember(splitter[0], splitter[2])
            query.answer("✅ Berhasil ditendang")
            return ""
        except Exception as err:
            query.answer("🛑 Gagal menendang")
            bot.sendMessage(
                text=f"Error: {err}",
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
    elif splitter[1] == "banned":
        try:
            bot.kickChatMember(splitter[0], splitter[2])
            query.answer("✅  Berhasil Dilarang")
            return ""
        except Exception as err:
            bot.sendMessage(
                text=f"Error: {err}",
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
            query.answer("🛑 Gagal Melarang")
    elif splitter[1] == "delete":
        try:
            bot.deleteMessage(splitter[0], splitter[3])
            query.answer("✅ Pesan dihapus")
            return ""
        except Exception as err:
            bot.sendMessage(
                text=f"Error: {err}",
                chat_id=query.message.chat_id,
                parse_mode=ParseMode.HTML,
            )
            query.answer("🛑 Gagal menghapus pesan!")


from Telegram.modules.language import gs


def get_help(chat):
    return gs(chat, "reports_help")


__mod_name__ = "Reporting"
