from functools import wraps

from Telegram import (
    DEL_CMDS,
    DEV_USERS,
    SUDO_USERS,
    SUPPORT_USERS,
    SARDEGNA_USERS,
    WHITELIST_USERS,
    dispatcher,
)
from cachetools import TTLCache
from telegram import Chat, ChatMember, ParseMode, Update, TelegramError, User
from telegram.ext import CallbackContext

# stores admin in memory for 10 min.
ADMIN_CACHE = TTLCache(maxsize=512, ttl=60 * 10)


def is_anon(user: User, chat: Chat):
    return chat.get_member(user.id).is_anonymous


def is_whitelist_plus(_: Chat, user_id: int) -> bool:
    return any(
        user_id in user
        for user in [
            WHITELIST_USERS,
            SARDEGNA_USERS,
            SUPPORT_USERS,
            SUDO_USERS,
            DEV_USERS,
        ]
    )


def is_support_plus(_: Chat, user_id: int) -> bool:
    return user_id in SUPPORT_USERS or user_id in SUDO_USERS or user_id in DEV_USERS


def is_sudo_plus(_: Chat, user_id: int) -> bool:
    return user_id in SUDO_USERS or user_id in DEV_USERS


def is_user_admin(update: Update, user_id: int, member: ChatMember = None) -> bool:
    chat = update.effective_chat
    msg = update.effective_message
    if (
            chat.type == "private"
            or user_id in SUDO_USERS
            or user_id in DEV_USERS
            or chat.all_members_are_administrators
            or (msg.reply_to_message and msg.reply_to_message.sender_chat is not None and
                msg.reply_to_message.sender_chat.type != "channel")
    ):
        return True

    if not member:
        # try to fetch from cache first.
        try:
            return user_id in ADMIN_CACHE[chat.id]
        except KeyError:
            # KeyError happened means cache is deleted,
            # so query bot api again and return user status
            # while saving it in cache for future usage...
            chat_admins = dispatcher.bot.getChatAdministrators(chat.id)
            admin_list = [x.user.id for x in chat_admins]
            ADMIN_CACHE[chat.id] = admin_list

            if user_id in admin_list:
                return True
            return False


def is_bot_admin(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    if chat.type == "private" or chat.all_members_are_administrators:
        return True

    if not bot_member:
        bot_member = chat.get_member(bot_id)

    return bot_member.status in ("administrator", "creator")


def can_delete(chat: Chat, bot_id: int) -> bool:
    return chat.get_member(bot_id).can_delete_messages


def is_user_ban_protected(update: Update, user_id: int, member: ChatMember = None) -> bool:
    chat = update.effective_chat
    msg = update.effective_message
    if (
            chat.type == "private"
            or user_id in SUDO_USERS
            or user_id in DEV_USERS
            or user_id in WHITELIST_USERS
            or user_id in SARDEGNA_USERS
            or chat.all_members_are_administrators
            or (msg.reply_to_message and msg.reply_to_message.sender_chat is not None
                and msg.reply_to_message.sender_chat.type != "channel")
    ):
        return True

    if not member:
        member = chat.get_member(user_id)

    return member.status in ("administrator", "creator")


def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    member = chat.get_member(user_id)
    return member.status not in ("left", "kicked")


def dev_plus(func):
    @wraps(func)
    def is_dev_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        # bot = context.bot
        user = update.effective_user

        if user.id in DEV_USERS:
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                update.effective_message.delete()
            except TelegramError:
                pass
        else:
            update.effective_message.reply_text(
                "Ini adalah perintah terbatas pengembang."
                " Anda tidak memiliki izin untuk menjalankan ini."
            )

    return is_dev_plus_func


def sudo_plus(func):
    @wraps(func)
    def is_sudo_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        # bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and is_sudo_plus(chat, user.id):
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                update.effective_message.delete()
            except TelegramError:
                pass
        else:
            update.effective_message.reply_text(
                "Siapa non-admin yang memberi tahu saya apa yang harus dilakukan?"
            )

    return is_sudo_plus_func


def support_plus(func):
    @wraps(func)
    def is_support_plus_func(update: Update, context: CallbackContext, *args, **kwargs):
        # bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and is_support_plus(chat, user.id):
            return func(update, context, *args, **kwargs)
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                update.effective_message.delete()
            except TelegramError:
                pass

    return is_support_plus_func


def whitelist_plus(func):
    @wraps(func)
    def is_whitelist_plus_func(
            update: Update, context: CallbackContext, *args, **kwargs
    ):
        # bot = context.bot
        user = update.effective_user
        chat = update.effective_chat

        if user and is_whitelist_plus(chat, user.id):
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                f"Anda tidak memiliki akses untuk menggunakan ini.\nKunjungi @medsupportt"
            )

    return is_whitelist_plus_func


def user_admin(func):
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        # bot = context.bot
        user = update.effective_user
        # chat = update.effective_chat

        if user and is_user_admin(update, user.id):
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                update.effective_message.delete()
            except TelegramError:
                pass
        else:
            update.effective_message.reply_text(
                "Siapa non-admin yang memberi tahu saya apa yang harus dilakukan?"
            )

    return is_admin


def user_admin_no_reply(func):
    @wraps(func)
    def is_not_admin_no_reply(
            update: Update, context: CallbackContext, *args, **kwargs
    ):
        # bot = context.bot
        user = update.effective_user
        # chat = update.effective_chat

        if user and is_user_admin(update, user.id):
            return func(update, context, *args, **kwargs)
        elif not user:
            pass
        elif DEL_CMDS and " " not in update.effective_message.text:
            try:
                update.effective_message.delete()
            except TelegramError:
                pass

    return is_not_admin_no_reply


def user_not_admin(func):
    @wraps(func)
    def is_not_admin(update: Update, context: CallbackContext, *args, **kwargs):
        message = update.effective_message
        user = update.effective_user
        # chat = update.effective_chat

        if message.is_automatic_forward:
            return
        if message.sender_chat and message.sender_chat.type != "channel":
            return
        elif user and not is_user_admin(update, user.id):
            return func(update, context, *args, **kwargs)

        elif not user:
            pass

    return is_not_admin


def bot_admin(func):
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            not_admin = "Saya bukan admin! - REEEEEE"
        else:
            not_admin = f"Saya bukan admin dalam <b>{update_chat_title}</b>! - REEEEEE"

        if is_bot_admin(chat, bot.id):
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(not_admin, parse_mode=ParseMode.HTML)

    return is_admin


def bot_can_delete(func):
    @wraps(func)
    def delete_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_delete = "Saya tidak dapat menghapus pesan di sini!\nPastikan saya adalah admin dan dapat menghapus pesan pengguna lain."
        else:
            cant_delete = f"Saya tidak dapat menghapus pesan di <b>{update_chat_title}</b>!\nPastikan saya admin dan bisa " \
                        f"hapus pesan pengguna lain di sana. "

        if can_delete(chat, bot.id):
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(cant_delete, parse_mode=ParseMode.HTML)

    return delete_rights


def can_pin(func):
    @wraps(func)
    def pin_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_pin = (
                "Saya tidak dapat menyematkan pesan di sini!\nPastikan saya adalah admin dan dapat menyematkan pesan."            )
        else:
            cant_pin = f"Saya tidak dapat menyematkan pesan <b>{update_chat_title}</b>!\nPastikan saya admin dan dapat menyematkan " \
                        f"pesan di sana. "

        if chat.get_member(bot.id).can_pin_messages:
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(cant_pin, parse_mode=ParseMode.HTML)

    return pin_rights


def can_promote(func):
    @wraps(func)
    def promote_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_promote = "Saya tidak dapat mempromosikan/menurunkan orang di sini!\nPastikan saya adalah admin dan dapat menunjuk admin baru."
        else:
            cant_promote = (
                f"Saya tidak dapat mempromosikan/menurunkan orang <b>{update_chat_title}</b>!\n"
                f"Pastikan saya admin disana dan bisa menunjuk admin baru."
            )

        if chat.get_member(bot.id).can_promote_members:
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(cant_promote, parse_mode=ParseMode.HTML)

    return promote_rights


def can_restrict(func):
    @wraps(func)
    def restrict_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message.chat.title

        if update_chat_title == message_chat_title:
            cant_restrict = "Saya tidak dapat membatasi orang di sini!\nPastikan saya adalah admin dan dapat membatasi pengguna."        else:
            cant_restrict = f"Saya tidak bisa membatasi orang masuk <b>{update_chat_title}</b>!\nPastikan saya admin di sana dan " \
                            f"dapat membatasi pengguna. "

        if chat.get_member(bot.id).can_restrict_members:
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                cant_restrict, parse_mode=ParseMode.HTML
            )

    return restrict_rights


def user_can_ban(func):
    @wraps(func)
    def user_is_banhammer(update: Update, context: CallbackContext, *args, **kwargs):
        # bot = context.bot
        user = update.effective_user.id
        member = update.effective_chat.get_member(user)

        if (
                not (member.can_restrict_members or member.status == "creator")
                and not user in SUDO_USERS
        ):
            update.effective_message.reply_text(
                "Maaf nak, tapi kamu tidak layak menggunakan banhammer."
            )
            return ""

        return func(update, context, *args, **kwargs)

    return user_is_banhammer


def connection_status(func):
    @wraps(func)
    def connected_status(update: Update, context: CallbackContext, *args, **kwargs):
        conn = connected(
            context.bot,
            update,
            update.effective_chat,
            update.effective_user.id,
            need_admin=False,
        )

        if conn:
            chat = dispatcher.bot.getChat(conn)
            update.__setattr__("_effective_chat", chat)
            return func(update, context, *args, **kwargs)
        else:
            if update.effective_message.chat.type == "private":
                update.effective_message.reply_text(
                    "Kirim / hubungkan dalam grup yang Anda dan saya miliki bersama terlebih dahulu."
                )
                return connected_status

            return func(update, context, *args, **kwargs)

    return connected_status


# Workaround for circular import with connection.py
from Telegram.modules import connection

connected = connection.connected
