from datetime import datetime
from functools import wraps

from telegram.ext import CallbackContext
from Telegram.modules.helper_funcs.decorators import zaid, zaidcallback
from Telegram.modules.helper_funcs.misc import is_module_loaded
from Telegram.modules.language import gs

from ..modules.helper_funcs.anonymous import user_admin, AdminPerms


def get_help(chat):
    return gs(chat, "log_help")


FILENAME = __name__.rsplit(".", 1)[-1]

if is_module_loaded(FILENAME):
    from telegram import ParseMode, Update, InlineKeyboardMarkup, InlineKeyboardButton
    from telegram.error import BadRequest, Unauthorized
    from telegram.utils.helpers import escape_markdown

    from Telegram import GBAN_LOGS, log, dispatcher
    from Telegram.modules.helper_funcs.chat_status import user_admin as u_admin, is_user_admin
    from Telegram.modules.sql import log_channel_sql as sql


    def loggable(func):
        @wraps(func)
        def log_action(update, context, *args, **kwargs):
            result = func(update, context, *args, **kwargs)
            chat = update.effective_chat  # type: Optional[Chat]
            message = update.effective_message  # type: Optional[Message]

            if result:
                datetime_fmt = "%H:%M - %d-%m-%Y"
                result += f"\n<b>Stempel Acara</b>: <code>{datetime.utcnow().strftime(datetime_fmt)}</code>"
                try:
                    if message.chat.type == chat.SUPERGROUP:
                        if message.chat.username:
                            result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
                        else:
                            cid = str(chat.id).replace("-100", '')
                            result += f'\n<b>Link:</b> <a href="https://t.me/c/{cid}/{message.message_id}">click here</a>'
                except AttributeError:
                    result += '\n<b>Link:</b> No link for manual actions.' # or just without the whole line
                log_chat = sql.get_chat_log_channel(chat.id)
                if log_chat:
                    send_log(context, log_chat, chat.id, result)

            return result

        return log_action


    def gloggable(func):
        @wraps(func)
        def glog_action(update, context, *args, **kwargs):
            result = func(update, context, *args, **kwargs)
            chat = update.effective_chat  # type: Optional[Chat]
            message = update.effective_message  # type: Optional[Message]

            if result:
                datetime_fmt = "%H:%M - %d-%m-%Y"
                result += "\n<b>Stempel Acara</b>: <code>{}</code>".format(
                    datetime.utcnow().strftime(datetime_fmt)
                )

                if message.chat.type == chat.SUPERGROUP and message.chat.username:
                    result += f'\n<b>Link:</b> <a href="https://t.me/{chat.username}/{message.message_id}">click here</a>'
                log_chat = str(GBAN_LOGS)
                if log_chat:
                    send_log(context, log_chat, chat.id, result)

            return result

        return glog_action


    def send_log(
            context: CallbackContext, log_chat_id: str, orig_chat_id: str, result: str
    ):
        bot = context.bot
        try:
            bot.send_message(
                log_chat_id,
                result,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except BadRequest as excp:
            if excp.message == "Obrolan tidak ditemukan":
                bot.send_message(
                    orig_chat_id, "Saluran log ini telah dihapus - tidak disetel."
                )
                sql.stop_chat_logging(orig_chat_id)
            else:
                log.warning(excp.message)
                log.warning(result)
                log.exception("Tidak dapat mengurai")

                bot.send_message(
                    log_chat_id,
                    result
                    + "\n\nPemformatan telah dinonaktifkan karena kesalahan tak terduga.",
                )


    @zaid(command='logchannel')
    @u_admin
    def logging(update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.get_chat_log_channel(chat.id)
        if log_channel:
            log_channel_info = bot.get_chat(log_channel)
            message.reply_text(
                f"Grup ini memiliki semua log yang dikirim ke:"
                f" {escape_markdown(log_channel_info.title)} (`{log_channel}`)",
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            message.reply_text("Tidak ada saluran log yang disetel untuk grup ini!")


    @zaid(command='setlog')
    @user_admin(AdminPerms.CAN_CHANGE_INFO)
    def setlog(update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat
        if chat.type == chat.CHANNEL:
            message.reply_text(
                "Sekarang, teruskan /setlog ke grup tempat Anda ingin mengikat saluran ini!"
            )

        elif message.forward_from_chat:
            sql.set_chat_log_channel(chat.id, message.forward_from_chat.id)
            try:
                message.delete()
            except BadRequest as excp:
                if excp.message != 'Pesan untuk dihapus tidak ditemukan':
                    log.exception(
                        'Terjadi kesalahan saat menghapus pesan di saluran log. Harus tetap bekerja.'
                    )

            try:
                bot.send_message(
                    message.forward_from_chat.id,
                    f"Saluran ini telah ditetapkan sebagai saluran log untuk {chat.title or chat.first_name}.",
                )
            except Unauthorized as excp:
                if excp.message == "Dilarang: bot bukan anggota obrolan saluran":
                    bot.send_message(chat.id, "Berhasil menyetel saluran log!")
                else:
                    log.exception("KESALAHAN dalam menyetel saluran log.")

            bot.send_message(chat.id, "Berhasil menyetel saluran log!")

        else:
            message.reply_text(
                "Langkah-langkah untuk menyetel saluran log adalah:\n"
                " - tambahkan bot ke saluran yang diinginkan\n"
                " - kirim /setlog ke saluran\n"
                " - teruskan /setlog ke grup\n"
            )


    @zaid(command='unsetlog')
    @user_admin(AdminPerms.CAN_CHANGE_INFO)
    def unsetlog(update: Update, context: CallbackContext):
        bot = context.bot
        message = update.effective_message
        chat = update.effective_chat

        log_channel = sql.stop_chat_logging(chat.id)
        if log_channel:
            bot.send_message(
                log_channel, f"Saluran telah dibatalkan tautannya {chat.title}"
            )
            message.reply_text("Saluran log tidak disetel.")

        else:
            message.reply_text("Belum ada saluran log yang ditetapkan!")


    def __stats__():
        return f"• {sql.num_logchannels()} saluran log ditetapkan."


    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)


    def __chat_settings__(chat_id, user_id):
        log_channel = sql.get_chat_log_channel(chat_id)
        if log_channel:
            log_channel_info = dispatcher.bot.get_chat(log_channel)
            return f"Grup ini memiliki semua log yang dikirim ke : {escape_markdown(log_channel_info.title)} (`{log_channel}`)"
        return "Tidak ada saluran log yang disetel untuk grup ini!"


    __help__ = """
*Admin saja:*
• `/logchannel`*:* dapatkan info saluran log
• `/setlog`*:* menyetel saluran log.
• `/unsetlog`*:* batal menyetel saluran log.

Pengaturan saluran log dilakukan dengan:
• menambahkan bot ke saluran yang diinginkan (sebagai admin!)
• mengirim `/setlog` di saluran
• meneruskan `/setlog` ke grup
"""

    __mod_name__ = "Logger"

else:
    # run anyway if module not loaded
    def loggable(func):
        return func


    def gloggable(func):
        return func


@zaid("logsettings")
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def log_settings(update: Update, _: CallbackContext):
    chat = update.effective_chat
    chat_set = sql.get_chat_setting(chat_id=chat.id)
    if not chat_set:
        sql.set_chat_setting(setting=sql.LogChannelSettings(chat.id, True, True, True, True, True))
    btn = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="Warn", callback_data="log_tog_warn"),
                InlineKeyboardButton(text="Action", callback_data="log_tog_act")
            ],
            [
                InlineKeyboardButton(text="Join", callback_data="log_tog_join"),
                InlineKeyboardButton(text="Leave", callback_data="log_tog_leave")
            ],
            [
                InlineKeyboardButton(text="Report", callback_data="log_tog_rep")
            ]
        ]
    )
    msg = update.effective_message
    msg.reply_text("Toggle channel log settings", reply_markup=btn)


from Telegram.modules.sql import log_channel_sql as sql


@zaidcallback(pattern=r"log_tog_.*")
def log_setting_callback(update: Update, context: CallbackContext):
    cb = update.callback_query
    user = cb.from_user
    chat = cb.message.chat
    if not is_user_admin(update, user.id):
        cb.answer("Anda bukan admin", show_alert=True)
        return
    setting = cb.data.replace("log_tog_", "")
    chat_set = sql.get_chat_setting(chat_id=chat.id)
    if not chat_set:
        sql.set_chat_setting(setting=sql.LogChannelSettings(chat.id, True, True, True, True, True))

    t = sql.get_chat_setting(chat.id)
    if setting == "warn":
        r = t.toggle_warn()
        cb.answer("Log peringatan disetel ke {}".format(r))
        return
    if setting == "act":
        r = t.toggle_action()
        cb.answer("Log tindakan diatur ke {}".format(r))
        return
    if setting == "join":
        r = t.toggle_joins()
        cb.answer("Gabung log disetel ke {}".format(r))
        return
    if setting == "leave":
        r = t.toggle_leave()
        cb.answer("Biarkan log disetel ke {}".format(r))
        return
    if setting == "rep":
        r = t.toggle_report()
        cb.answer("Log laporan diatur ke {}".format(r))
        return

    cb.answer("Aku tidak tahu apa yang harus dilakukan")
