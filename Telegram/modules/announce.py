import html

from telegram import Update
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

from Telegram.modules.log_channel import loggable
from Telegram.modules.helper_funcs.decorators import zaid

import Telegram.modules.sql.logger_sql as sql
from ..modules.helper_funcs.anonymous import user_admin as u_admin, AdminPerms


@zaid(command="announce", pass_args=True)
@u_admin(AdminPerms.CAN_CHANGE_INFO)
@loggable
def announcestat(update: Update, context: CallbackContext) -> str:
    args = context.args
    if len(args) > 0:
        u = update.effective_user
        message = update.effective_message
        chat = update.effective_chat
        user = update.effective_user
        if args[0].lower() in ["on", "yes", "true"]:
            sql.enable_chat_log(update.effective_chat.id)
            update.effective_message.reply_text(
                "Saya telah mengaktifkan pengumuman di grup ini. Sekarang setiap tindakan admin di grup Anda akan diumumkan."
            )
            logmsg = (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#ANNOUNCE_TOGGLED\n"
                f"Pengumuman tindakan admin telah <b>enabled</b>\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name) if not message.sender_chat else message.sender_chat.title}\n "
            )
            return logmsg
        elif args[0].lower() in ["off", "no", "false"]:
            sql.disable_chat_log(update.effective_chat.id)
            update.effective_message.reply_text(
                "Saya telah menonaktifkan pengumuman di grup ini. Sekarang tindakan admin di grup Anda tidak akan diumumkan."
            )
            logmsg = (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#ANNOUNCE_TOGGLED\n"
                f"Pengumuman tindakan admin telah <b>disabled</b>\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name) if not message.sender_chat else message.sender_chat.title}\n "
            )
            return logmsg
    else:
        update.effective_message.reply_text(
            "Beri saya beberapa argumen untuk memilih setelan! hidup/mati, ya/tidak!\n\n"
            "Setelan Anda saat ini adalah: {\n"
            "Bila Benar, setiap tindakan admin di grup Anda akan diumumkan."
            "Bila Salah, tindakan admin di grup Anda tidak akan diumumkan.".format(
                sql.does_chat_log(update.effective_chat.id))
        )
        return ''


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)
