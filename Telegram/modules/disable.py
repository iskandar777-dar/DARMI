from typing import Union

from future.utils import string_types
from telegram import ParseMode, Update, Chat
from telegram.ext import CommandHandler, MessageHandler
from telegram.utils.helpers import escape_markdown

from Telegram import dispatcher
from Telegram.modules.helper_funcs.handlers import CMD_STARTERS
from Telegram.modules.helper_funcs.misc import is_module_loaded
from Telegram.modules.helper_funcs.alternate import send_message, typing_action
from Telegram.modules.connection import connected
from Telegram.modules.language import gs

def get_help(chat):
    return gs(chat, "disable_help")


CMD_STARTERS = tuple(CMD_STARTERS)


FILENAME = __name__.rsplit(".", 1)[-1]

# If module is due to be loaded, then setup all the magical handlers
if is_module_loaded(FILENAME):
    from Telegram.modules.helper_funcs.chat_status import (
        user_admin,
        is_user_admin,
    )

    from Telegram.modules.sql import disable_sql as sql

    DISABLE_CMDS = []
    DISABLE_OTHER = []
    ADMIN_CMDS = []

    class DisableAbleCommandHandler(CommandHandler):
        def __init__(self, command, callback, run_async=True, admin_ok=False, **kwargs):
            super().__init__(command, callback, run_async=run_async, **kwargs)
            self.admin_ok = admin_ok
            if isinstance(command, string_types):
                DISABLE_CMDS.append(command)
                if admin_ok:
                    ADMIN_CMDS.append(command)
            else:
                DISABLE_CMDS.extend(command)
                if admin_ok:
                    ADMIN_CMDS.extend(command)

        def check_update(self, update):
            if not isinstance(update, Update) or not update.effective_message:
                return
            message = update.effective_message

            if message.text and len(message.text) > 1:
                fst_word = message.text.split(None, 1)[0]
                if len(fst_word) > 1 and any(
                    fst_word.startswith(start) for start in CMD_STARTERS
                ):
                    args = message.text.split()[1:]
                    command = fst_word[1:].split("@")
                    command.append(message.bot.username)

                    if not (
                        command[0].lower() in self.command
                        and command[1].lower() == message.bot.username.lower()
                    ):
                        return None

                    filter_result = self.filters(update)
                    if filter_result:
                        chat = update.effective_chat
                        user = update.effective_user
                        # disabled, admincmd, user admin
                        if sql.is_command_disabled(chat.id, command[0].lower()):
                            # check if command was disabled
                            is_disabled = command[
                                0
                            ] in ADMIN_CMDS and is_user_admin(update, user.id)
                            if not is_disabled:
                                return None
                            else:
                                return args, filter_result

                        return args, filter_result
                    else:
                        return False

    class DisableAbleMessageHandler(MessageHandler):
        def __init__(self, pattern, callback, run_async=True, friendly="", **kwargs):
            super().__init__(pattern, callback, run_async=run_async, **kwargs)
            DISABLE_OTHER.append(friendly or pattern)
            self.friendly = friendly or pattern

        def check_update(self, update):
            if isinstance(update, Update) and update.effective_message:
                chat = update.effective_chat
                return self.filters(update) and not sql.is_command_disabled(
                    chat.id, self.friendly
                )

    @user_admin
    @typing_action
    def disable(update, context):
        chat = update.effective_chat  # type: Optional[Chat]
        user = update.effective_user
        args = context.args

        conn = connected(context.bot, update, chat, user.id, need_admin=True)
        if conn:
            chat = dispatcher.bot.getChat(conn)
            chat_name = dispatcher.bot.getChat(conn).title
        else:
            if update.effective_message.chat.type == "private":
                send_message(
                    update.effective_message,
                    "Perintah ini dimaksudkan untuk digunakan dalam grup bukan di PM",
                )
                return ""
            chat = update.effective_chat
            chat_name = update.effective_message.chat.title

        if len(args) >= 1:
            disable_cmd = args[0]
            if disable_cmd.startswith(CMD_STARTERS):
                disable_cmd = disable_cmd[1:]

            if disable_cmd in set(DISABLE_CMDS + DISABLE_OTHER):
                sql.disable_command(chat.id, disable_cmd)
                if conn:
                    text = "Menonaktifkan penggunaan perintah `{}` di *{}*!".format(
                        disable_cmd, chat_name
                    )
                else:
                    text = "Menonaktifkan penggunaan perintah `{}`!".format(disable_cmd)
                send_message(
                    update.effective_message,
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                send_message(update.effective_message, "Perintah ini tidak dapat dinonaktifkan")

        else:
            send_message(update.effective_message, "Apa yang harus saya nonaktifkan?")

    @user_admin
    @typing_action
    def enable(update, context):
        chat = update.effective_chat  # type: Optional[Chat]
        user = update.effective_user
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
                    "Perintah ini dimaksudkan untuk digunakan dalam grup bukan di PM",
                )
                return ""
            chat = update.effective_chat
            chat_id = update.effective_chat.id
            chat_name = update.effective_message.chat.title

        if len(args) >= 1:
            enable_cmd = args[0]
            if enable_cmd.startswith(CMD_STARTERS):
                enable_cmd = enable_cmd[1:]

            if sql.enable_command(chat.id, enable_cmd):
                if conn:
                    text = "Mengaktifkan penggunaan perintah `{}` di *{}*!".format(
                        enable_cmd, chat_name
                    )
                else:
                    text = "Mengaktifkan penggunaan perintah `{}`!".format(enable_cmd)
                send_message(
                    update.effective_message,
                    text,
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                send_message(update.effective_message, "Apakah itu bahkan dinonaktifkan?")

        else:
            send_message(update.effective_message, "Apa yang harus saya aktifkan?")

    @user_admin
    @typing_action
    def list_cmds(update, context):
        if DISABLE_CMDS + DISABLE_OTHER:
            result = "".join(
                " - `{}`\n".format(escape_markdown(str(cmd)))
                for cmd in set(DISABLE_CMDS + DISABLE_OTHER)
            )

            update.effective_message.reply_text(
                "Perintah berikut dapat dialihkan:\n{}".format(result),
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            update.effective_message.reply_text("Tidak ada perintah yang dapat dinonaktifkan.")

    # do not async
    def build_curr_disabled(chat_id: Union[str, int]) -> str:
        disabled = sql.get_all_disabled(chat_id)
        if not disabled:
            return "Tidak ada perintah yang dinonaktifkan!"

        result = "".join(" - `{}`\n".format(escape_markdown(cmd)) for cmd in disabled)
        return "Perintah berikut saat ini dibatasi:\n{}".format(result)

    @typing_action
    def commands(update, context):
        chat = update.effective_chat
        user = update.effective_user
        conn = connected(context.bot, update, chat, user.id, need_admin=True)
        if conn:
            chat = dispatcher.bot.getChat(conn)
            chat_id = conn
        else:
            if update.effective_message.chat.type == "private":
                send_message(
                    update.effective_message,
                    "Perintah ini dimaksudkan untuk digunakan dalam grup bukan di PM",
                )
                return ""
            chat = update.effective_chat
            chat_id = update.effective_chat.id

        text = build_curr_disabled(chat.id)
        send_message(update.effective_message, text, parse_mode=ParseMode.MARKDOWN)

    def __import_data__(chat_id, data):
        disabled = data.get("disabled", {})
        for disable_cmd in disabled:
            sql.disable_command(chat_id, disable_cmd)

    def __stats__():
        return "• {} item yang dinonaktifkan, di {} obrolan.".format(
            sql.num_disabled(), sql.num_chats()
        )

    def __migrate__(old_chat_id, new_chat_id):
        sql.migrate_chat(old_chat_id, new_chat_id)

    def __chat_settings__(chat_id, user_id):
        return build_curr_disabled(chat_id)

    __mod_name__ = "Disabling"

    __help__ = """
Tidak semua orang menginginkan setiap fitur yang ditawarkan bot. Beberapa perintah adalah yang terbaik \
dibiarkan tidak terpakai; untuk menghindari spam dan penyalahgunaan.

Ini memungkinkan Anda untuk menonaktifkan beberapa perintah yang umum digunakan, sehingga tidak ada yang dapat menggunakannya. \
Ini juga akan memungkinkan Anda untuk menghapusnya secara otomatis, menghentikan orang dari mem-bluetexting.

 • /cmds: Memeriksa status saat ini dari perintah yang dinonaktifkan

*Admin only:*
 • /enable <cmd name>: Aktifkan perintah itu
 • /disable <cmd name>: Nonaktifkan perintah itu
 • /listcmds: Buat daftar semua kemungkinan perintah yang dapat dinonaktifkan
    """

    DISABLE_HANDLER = CommandHandler(
        "disable", disable, pass_args=True
    )  # , filters=Filters.chat_type.groups)
    ENABLE_HANDLER = CommandHandler(
        "enable", enable, pass_args=True
    )  # , filters=Filters.chat_type.groups)
    COMMANDS_HANDLER = CommandHandler(
        ["cmds", "disabled"], commands
    )  # , filters=Filters.chat_type.groups)
    TOGGLE_HANDLER = CommandHandler(
        "listcmds", list_cmds
    )  # , filters=Filters.chat_type.groups)

    dispatcher.add_handler(DISABLE_HANDLER)
    dispatcher.add_handler(ENABLE_HANDLER)
    dispatcher.add_handler(COMMANDS_HANDLER)
    dispatcher.add_handler(TOGGLE_HANDLER)

else:
    DisableAbleCommandHandler = CommandHandler
    DisableAbleMessageHandler = MessageHandler
