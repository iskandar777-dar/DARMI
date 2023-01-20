import html

from telegram import Update, ParseMode, MAX_MESSAGE_LENGTH
from telegram.ext.dispatcher import CallbackContext
from telegram.utils.helpers import escape_markdown

import Telegram.modules.sql.userinfo_sql as sql
from Telegram import SUDO_USERS, DEV_USERS
from Telegram.modules.helper_funcs.decorators import zaid
from Telegram.modules.helper_funcs.extraction import extract_user


@zaid(command='me', pass_args=True)
def about_me(update: Update, context: CallbackContext):
    args = context.args
    bot = context.bot
    message = update.effective_message
    user_id = extract_user(message, args)

    user = bot.get_chat(user_id) if user_id else message.from_user
    info = sql.get_user_me_info(user.id)

    if info:
        update.effective_message.reply_text(
            f"*{user.first_name}*:\n{escape_markdown(info)}",
            parse_mode=ParseMode.MARKDOWN,
        )
    elif message.reply_to_message:
        username = message.reply_to_message.from_user.first_name
        update.effective_message.reply_text(
            f"{username} belum menetapkan pesan info tentang diri mereka sendiri!"
        )
    else:
        update.effective_message.reply_text(
            "Anda belum menyetel pesan info tentang diri Anda!"
        )


@zaid(command='setme')
def set_about_me(update: Update, context: CallbackContext):
    bot = context.bot
    message = update.effective_message
    user_id = message.from_user.id
    if user_id in (777000, 1087968824):
        message.reply_text("Jangan atur info untuk bot Telegram!")
        return
    if message.reply_to_message:
        repl_message = message.reply_to_message
        repl_user_id = repl_message.from_user.id
        if repl_user_id == bot.id and (user_id in SUDO_USERS or user_id in DEV_USERS):
            user_id = repl_user_id

    text = message.text
    info = text.split(None, 1)

    if len(info) == 2:
        if len(info[1]) < MAX_MESSAGE_LENGTH // 4:
            sql.set_user_me_info(user_id, info[1])
            if user_id == bot.id:
                message.reply_text("Diperbarui info saya!")
            else:
                message.reply_text("Memperbarui info Anda!")
        else:
            message.reply_text(
                "Info harus di bawah {} karakter! Kamu punya {}.".format(
                    MAX_MESSAGE_LENGTH // 4, len(info[1])
                )
            )


@zaid(command='bio', pass_args=True)
def about_bio(update: Update, context: CallbackContext):
    args = context.args
    bot = context.bot
    message = update.effective_message

    user_id = extract_user(message, args)
    user = bot.get_chat(user_id) if user_id else message.from_user
    info = sql.get_user_bio(user.id)

    if info:
        update.effective_message.reply_text(
            "*{}*:\n{}".format(user.first_name, escape_markdown(info)),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif message.reply_to_message:
        username = user.first_name
        update.effective_message.reply_text(
            f"{username} belum memiliki pesan tentang diri mereka sendiri!"
        )
    else:
        update.effective_message.reply_text(
            "Anda belum memiliki kumpulan bio tentang diri Anda!"
        )
    message = update.effective_message
    if message.reply_to_message:
        repl_message = message.reply_to_message
        user_id = repl_message.from_user.id

        if user_id == message.from_user.id:
            message.reply_text(
                "Ha, Anda tidak dapat mengatur bio Anda sendiri! Anda berada di belas kasihan orang lain di sini..."
            )
            return

        sender_id = update.effective_user.id

        if (
                user_id == bot.id
                and sender_id not in SUDO_USERS
                and sender_id not in DEV_USERS
        ):
            message.reply_text(
                "Erm... ya, saya hanya mempercayai pengguna atau pengembang sudo untuk mengatur bio saya."
            )
            return

        text = message.text
        # use python's maxsplit to only remove the cmd, hence keeping newlines.
        bio = text.split(None, 1)

        if len(bio) == 2:
            if len(bio[1]) < MAX_MESSAGE_LENGTH // 4:
                sql.set_user_bio(user_id, bio[1])
                message.reply_text(
                    "Memperbarui biodata {}!".format(repl_message.from_user.first_name)
                )
            else:
                message.reply_text(
                    "Biografi harus di bawah {} karakter! Anda mencoba mengatur {}.".format(
                        MAX_MESSAGE_LENGTH // 4, len(bio[1])
                    )
                )
    else:
        message.reply_text("Balas pesan seseorang untuk menyetel biodata mereka!")


@zaid(command='setbio')
def set_about_bio(update: Update, context: CallbackContext):
    message = update.effective_message
    sender_id = update.effective_user.id
    bot = context.bot

    if message.reply_to_message:
        repl_message = message.reply_to_message
        user_id = repl_message.from_user.id
        if user_id in (777000, 1087968824):
            message.reply_text("Jangan setel bio untuk bot Telegram!")
            return

        if user_id == message.from_user.id:
            message.reply_text(
                "Ha, Anda tidak dapat mengatur bio Anda sendiri! Anda berada di belas kasihan orang lain di sini..."
            )
            return

        if user_id in [777000, 1087968824] and sender_id not in DEV_USERS:
            message.reply_text("Anda tidak berwenang")
            return

        if user_id == bot.id and sender_id not in DEV_USERS:
            message.reply_text("Erm... ya, saya hanya mempercayai Eagle Union untuk mengatur biodata saya.")
            return

        text = message.text
        bio = text.split(
            None, 1
        )  # use python's maxsplit to only remove the cmd, hence keeping newlines.

        if len(bio) == 2:
            if len(bio[1]) < MAX_MESSAGE_LENGTH // 4:
                sql.set_user_bio(user_id, bio[1])
                message.reply_text(
                    "Memperbarui biodata {}!".format(repl_message.from_user.first_name)
                )
            else:
                message.reply_text(
                    "Bio harus di bawah {} karakter! Anda mencoba mengatur {}.".format(
                        MAX_MESSAGE_LENGTH // 4, len(bio[1])
                    )
                )
    else:
        message.reply_text("Balas ke seseorang untuk mengatur bio mereka!")


def __user_info__(user_id):
    bio = html.escape(sql.get_user_bio(user_id) or "")
    me = html.escape(sql.get_user_me_info(user_id) or "")
    if bio and me:
        return f"\n<b>Tentang pengguna:</b>\n{me}\n<b>Apa yang orang lain katakan:</b>\n{bio}\n"
    elif bio:
        return f"\n<b>Apa yang orang lain katakan:</b>\n{bio}\n"
    elif me:
        return f"\n<b>Tentang pengguna:</b>\n{me}\n"
    else:
        return "\n"


from Telegram.modules.language import gs


def get_help(chat):
    return gs(chat, "userinfo_help")


__mod_name__ = "Bios/Abouts"
