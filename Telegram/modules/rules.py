from typing import Optional

import Telegram.modules.sql.rules_sql as sql
from Telegram import dispatcher
from Telegram.modules.helper_funcs.string_handling import markdown_parser
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ParseMode,
    Update,
    User,
)
from telegram.error import BadRequest
from telegram.ext import CallbackContext, Filters
from telegram.utils.helpers import escape_markdown
from Telegram.modules.helper_funcs.decorators import zaid

from ..modules.helper_funcs.anonymous import user_admin, AdminPerms


@zaid(command='rules', filters=Filters.chat_type.groups)
def get_rules(update: Update, _: CallbackContext):
    chat_id = update.effective_chat.id
    send_rules(update, chat_id)


# Do not async - not from a handler
def send_rules(update, chat_id, from_pm=False):
    bot = dispatcher.bot
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message
    try:
        chat = bot.get_chat(chat_id)
    except BadRequest as excp:
        if excp.message != "Obrolan tidak ditemukan" or not from_pm:
            raise

        bot.send_message(
            user.id,
            "Pintasan aturan untuk obrolan ini belum disetel dengan benar! Minta admin untuk "
            "perbaiki ini.\nMungkin mereka lupa tanda hubung di ID",
        )
        return
    rules = sql.get_rules(chat_id)
    text = f"Aturan untuk *{escape_markdown(chat.title)}* adalah:\n\n{rules}"

    if from_pm and rules:
        bot.send_message(
            user.id, text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )
    elif from_pm:
        bot.send_message(
            user.id,
            "Admin grup belum menetapkan aturan apa pun untuk obrolan ini."
            "Ini mungkin tidak berarti itu tanpa hukum...!",
        )
    elif rules:
        btn = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Aturan", url=f"t.me/{bot.username}?start={chat_id}"
                        )
                    ]
                ]
        )
        txt = "Silakan klik tombol di bawah ini untuk melihat peraturannya."
        if not message.reply_to_message:
            message.reply_text(txt, reply_markup=btn)

        if message.reply_to_message:
            message.reply_to_message.reply_text(txt, reply_markup=btn)
    else:
        update.effective_message.reply_text(
            "Admin grup belum menetapkan aturan apa pun untuk obrolan ini."
            "Ini mungkin tidak berarti itu melanggar hukum...!"
        )


@zaid(command='setrules', filters=Filters.chat_type.groups)
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def set_rules(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
    if len(args) == 2:
        txt = args[1]
        offset = len(txt) - len(raw_text)  # set correct offset relative to command
        markdown_rules = markdown_parser(
            txt, entities=msg.parse_entities(), offset=offset
        )

        sql.set_rules(chat_id, markdown_rules)
        update.effective_message.reply_text("Berhasil menetapkan aturan untuk grup ini.")


@zaid(command='clearrules', filters=Filters.chat_type.groups)
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def clear_rules(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    sql.set_rules(chat_id, "")
    update.effective_message.reply_text("Berhasil menghapus aturan!")


def __stats__():
    return f"• {sql.num_chats()} obrolan memiliki aturan yang ditetapkan."


def __import_data__(chat_id, data):
    # set chat rules
    rules = data.get("info", {}).get("rules", "")
    sql.set_rules(chat_id, rules)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return f"Obrolan ini telah menetapkan aturannya: `{bool(sql.get_rules(chat_id))}`"


from Telegram.modules.language import gs


def get_help(chat):
    return gs(chat, "rules_help")


__mod_name__ = "Rules"
