import html
import random
import re
import time
from functools import partial
from io import BytesIO
import Telegram.modules.sql.welcome_sql as sql
from Telegram import (
    DEV_USERS,
    SYS_ADMIN,
    log,
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    SARDEGNA_USERS,
    WHITELIST_USERS,
    sw,
    dispatcher,
)
from Telegram.modules.helper_funcs.chat_status import (
    is_user_ban_protected,
    user_admin as u_admin,
)
from Telegram.modules.helper_funcs.misc import build_keyboard, revert_buttons
from Telegram.modules.helper_funcs.msg_types import get_welcome_type
from Telegram.modules.helper_funcs.string_handling import (
    escape_invalid_curly_brackets,
    markdown_parser,
)
from Telegram.modules.log_channel import loggable
from Telegram.modules.sql.antispam_sql import is_user_gbanned
from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update, ChatMember, User,
)
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown
import Telegram.modules.sql.log_channel_sql as logsql
from ..modules.helper_funcs.anonymous import user_admin, AdminPerms

VALID_WELCOME_FORMATTERS = [
    "first",
    "last",
    "fullname",
    "username",
    "id",
    "count",
    "chatname",
    "mention",
]

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video,
}

VERIFIED_USER_WAITLIST = {}
CAPTCHA_ANS_DICT = {}

from multicolorcaptcha import CaptchaGenerator

WHITELISTED = [OWNER_ID, SYS_ADMIN] + DEV_USERS + SUDO_USERS + SUPPORT_USERS + WHITELIST_USERS

# do not async
def send(update, message, keyboard, backup_message):
    chat = update.effective_chat
    cleanserv = sql.clean_service(chat.id)
    reply = update.message.message_id
    # Clean service welcome
    if cleanserv:
        try:
            dispatcher.bot.delete_message(chat.id, update.message.message_id)
        except BadRequest:
            pass
        reply = False
    try:
        msg = update.effective_message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            reply_to_message_id=reply,
            allow_sending_without_reply=True,
        )
    except BadRequest as excp:
        if excp.message == 'Button_url_invalid':
            msg = update.effective_message.reply_text(
                markdown_parser(
                    (
                            backup_message
                            + '\nNote: pesan saat ini memiliki url yang tidak valid di salah satu tombolnya. Harap perbarui.'
                    )
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )

        elif excp.message == 'Tidak memiliki hak untuk mengirim pesan':
            return
        elif excp.message == 'Pesan balasan tidak ditemukan':
            msg = update.effective_message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
                quote=False,
            )

        elif excp.message == 'Protokol url tidak didukung':
            msg = update.effective_message.reply_text(
                markdown_parser(
                    (
                            backup_message
                            + '\nNote: pesan saat ini memiliki tombol yang menggunakan protokol url yang tidak didukung oleh '
                                'telegram. Harap perbarui. '
                    )
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )

        elif excp.message == 'Host url salah':
            msg = update.effective_message.reply_text(
                markdown_parser(
                    (
                            backup_message
                            + '\nNote: pesan saat ini memiliki beberapa url yang buruk. Harap perbarui.'
                    )
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )

            log.warning(message)
            log.warning(keyboard)
            log.exception('Tidak dapat mengurai! mendapat kesalahan host url tidak valid')
        else:
            msg = update.effective_message.reply_text(
                markdown_parser(
                    (
                            backup_message
                            + '\nNote: Terjadi kesalahan saat mengirim pesan khusus. Harap perbarui.'
                    )
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )

            log.exception()
    return msg


@loggable
def new_member(update: Update, context: CallbackContext):  # sourcery no-metrics
    bot, job_queue = context.bot, context.job_queue
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    log_setting = logsql.get_chat_setting(chat.id)
    if not log_setting:
        logsql.set_chat_setting(logsql.LogChannelSettings(chat.id, True, True, True, True, True))
        log_setting = logsql.get_chat_setting(chat.id)
    should_welc, cust_welcome, cust_content, welc_type = sql.get_welc_pref(chat.id)
    welc_mutes = sql.welcome_mutes(chat.id)
    human_checks = sql.get_human_checks(user.id, chat.id)
    raid, _, deftime = sql.getRaidStatus(str(chat.id))

    new_members = update.effective_message.new_chat_members

    for new_mem in new_members:

        welcome_log = None
        res = None
        sent = None
        should_mute = True
        welcome_bool = True
        media_wel = False

        if raid and new_mem.id not in WHITELISTED:
            bantime = deftime
            try:
                chat.ban_member(new_mem.id, until_date=bantime)
            except BadRequest:
                pass
            return
        if sw != None:
            sw_ban = sw.get_ban(new_mem.id)
            if sw_ban:
                return

        reply = update.message.message_id
        cleanserv = sql.clean_service(chat.id)
        # Clean service welcome
        if cleanserv:
            try:
                dispatcher.bot.delete_message(chat.id, update.message.message_id)
            except BadRequest:
                pass
            reply = False

        if should_welc:

            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text(
                    "Oh hai, pencipta saya.", reply_to_message_id=reply
                )
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"Pemilik Bot baru saja bergabung dalam obrolan"
                )
                continue

            # Welcome Devs
            elif new_mem.id in DEV_USERS:
                update.effective_message.reply_text(
                    "Wah! Tuan baru saja bergabung!",
                    reply_to_message_id=reply,
                )
                continue

            # Welcome Sudos
            elif new_mem.id in SUDO_USERS:
                update.effective_message.reply_text(
                    "Hah! Bangsa Kerajaan baru saja bergabung! Tetap waspada!",
                    reply_to_message_id=reply,
                )
                continue

            # Welcome Support
            elif new_mem.id in SUPPORT_USERS:
                update.effective_message.reply_text(
                    "Hah! Seseorang dengan level Negeri Sakura baru saja bergabung!",
                    reply_to_message_id=reply,
                )
                continue

            # Welcome Whitelisted
            elif new_mem.id in SARDEGNA_USERS:
                update.effective_message.reply_text(
                    "Oof! Bangsa Sadegna baru saja bergabung!", reply_to_message_id=reply
                )
                continue

            # Welcome SARDEGNA_USERS
            elif new_mem.id in WHITELIST_USERS:
                update.effective_message.reply_text(
                    "Oof! Bangsa Neptuia baru saja bergabung!", reply_to_message_id=reply
                )
                continue

            # Welcome yourself
            elif new_mem.id == bot.id:
                update.effective_message.reply_text(
                    "Terima kasih telah menambahkan saya! Bergabunglah dengan @medsupportt untuk mendapatkan dukungan.",
                    reply_to_message_id=reply,
                )
                continue

            else:
                buttons = sql.get_welc_buttons(chat.id)
                keyb = build_keyboard(buttons)

                if welc_type not in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
                    media_wel = True

                first_name = (
                        new_mem.first_name or "PersonWithNoName"
                )  # edge case of empty name - occurs for some bugs.

                if cust_welcome:
                    if cust_welcome == sql.DEFAULT_WELCOME:
                        cust_welcome = random.choice(
                            sql.DEFAULT_WELCOME_MESSAGES
                        ).format(first=escape_markdown(first_name))

                    if new_mem.last_name:
                        fullname = escape_markdown(f"{first_name} {new_mem.last_name}")
                    else:
                        fullname = escape_markdown(first_name)
                    count = chat.get_member_count()
                    mention = mention_markdown(new_mem.id, escape_markdown(first_name))
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(
                        cust_welcome, VALID_WELCOME_FORMATTERS
                    )
                    res = valid_format.format(
                        first=escape_markdown(first_name),
                        last=escape_markdown(new_mem.last_name or first_name),
                        fullname=escape_markdown(fullname),
                        username=username,
                        mention=mention,
                        count=count,
                        chatname=escape_markdown(chat.title),
                        id=new_mem.id,
                    )

                else:
                    res = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                        first=escape_markdown(first_name)
                    )
                    keyb = []

                backup_message = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                    first=escape_markdown(first_name)
                )
                keyboard = InlineKeyboardMarkup(keyb)

        else:
            welcome_bool = False
            res = None
            keyboard = None
            backup_message = None
            reply = None

        # User exceptions from welcomemutes
        if (
                is_user_ban_protected(update, new_mem.id, chat.get_member(new_mem.id))
                or human_checks
        ):
            should_mute = False
        # Join welcome: soft mute
        if new_mem.is_bot:
            should_mute = False
            
        if user.id == new_mem.id and should_mute:
            if welc_mutes == "soft":
                bot.restrict_chat_member(
                    chat.id,
                    new_mem.id,
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_send_polls=False,
                        can_change_info=False,
                        can_add_web_page_previews=False,
                    ),
                    until_date=(int(time.time() + 24 * 60 * 60)),
                )
                sql.set_human_checks(user.id, chat.id)
            if welc_mutes == "strong":
                welcome_bool = False
                if not media_wel:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            (chat.id, new_mem.id): {
                                "should_welc": should_welc,
                                "media_wel": False,
                                "status": False,
                                "update": update,
                                "res": res,
                                "keyboard": keyboard,
                                "backup_message": backup_message,
                            }
                        }
                    )
                else:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            (chat.id, new_mem.id): {
                                "should_welc": should_welc,
                                "chat_id": chat.id,
                                "status": False,
                                "media_wel": True,
                                "cust_content": cust_content,
                                "welc_type": welc_type,
                                "res": res,
                                "keyboard": keyboard,
                            }
                        }
                    )
                new_join_mem = f"[{escape_markdown(new_mem.first_name)}](tg://user?id={user.id})"
                message = msg.reply_text(
                    f"{new_join_mem}, klik tombol di bawah untuk membuktikan bahwa Anda adalah manusia.\nAnda memiliki waktu 120 detik.",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text="Ya, saya manusia.",
                                    callback_data=f"user_join_({new_mem.id})",
                                )
                            ]
                        ]
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=reply,
                    allow_sending_without_reply=True,
                )
                bot.restrict_chat_member(
                    chat.id,
                    new_mem.id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_send_polls=False,
                        can_change_info=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                    ),
                )
                job_queue.run_once(
                    partial(check_not_bot, new_mem, chat.id, message.message_id),
                    120,
                    name="welcomemute",
                )
            if welc_mutes == "captcha":
                btn = []
                # Captcha image size number (2 -> 640x360)
                CAPCTHA_SIZE_NUM = 2
                # Create Captcha Generator object of specified size
                generator = CaptchaGenerator(CAPCTHA_SIZE_NUM)

                # Generate a captcha image
                captcha = generator.gen_captcha_image(difficult_level=3)
                # Get information
                image = captcha["image"]
                characters = captcha["characters"]
                # print(characters)
                fileobj = BytesIO()
                fileobj.name = f'captcha_{new_mem.id}.png'
                image.save(fp=fileobj)
                fileobj.seek(0)
                CAPTCHA_ANS_DICT[(chat.id, new_mem.id)] = int(characters)
                welcome_bool = False
                if not media_wel:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            (chat.id, new_mem.id): {
                                "should_welc": should_welc,
                                "media_wel": False,
                                "status": False,
                                "update": update,
                                "res": res,
                                "keyboard": keyboard,
                                "backup_message": backup_message,
                                "captcha_correct": characters,
                            }
                        }
                    )
                else:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            (chat.id, new_mem.id): {
                                "should_welc": should_welc,
                                "chat_id": chat.id,
                                "status": False,
                                "media_wel": True,
                                "cust_content": cust_content,
                                "welc_type": welc_type,
                                "res": res,
                                "keyboard": keyboard,
                                "captcha_correct": characters,
                            }
                        }
                    )

                nums = [random.randint(1000, 9999) for _ in range(7)]
                nums.append(characters)
                random.shuffle(nums)
                to_append = []
                # print(nums)
                for a in nums:
                    to_append.append(InlineKeyboardButton(text=str(a),
                                                            callback_data=f"user_captchajoin_({chat.id},{new_mem.id})_({a})"))
                    if len(to_append) > 2:
                        btn.append(to_append)
                        to_append = []
                if to_append:
                    btn.append(to_append)

                message = msg.reply_photo(fileobj,
                                            caption=f'Selamat datang [{escape_markdown(new_mem.first_name)}](tg://user?id={user.id}). Click the correct button to get unmuted!\n'
                                                    f'Anda punya 120 detik untuk ini.',
                                            reply_markup=InlineKeyboardMarkup(btn),
                                            parse_mode=ParseMode.MARKDOWN,
                                            reply_to_message_id=reply,
                                            allow_sending_without_reply=True,
                                            )
                bot.restrict_chat_member(
                    chat.id,
                    new_mem.id,
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_send_polls=False,
                        can_change_info=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                    ),
                )
                job_queue.run_once(
                    partial(check_not_bot, new_mem, chat.id, message.message_id),
                    120,
                    name="welcomemute",
                )

        if welcome_bool:
            if media_wel:
                if ENUM_FUNC_MAP[welc_type] == dispatcher.bot.send_sticker:
                    sent = ENUM_FUNC_MAP[welc_type](
                        chat.id,
                        cust_content,
                        reply_markup=keyboard,
                        reply_to_message_id=reply,
                    )
                else:
                    sent = ENUM_FUNC_MAP[welc_type](
                        chat.id,
                        cust_content,
                        caption=res,
                        reply_markup=keyboard,
                        reply_to_message_id=reply,
                        parse_mode="markdown",
                    )
            else:
                sent = send(update, res, keyboard, backup_message)
            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

        if not log_setting.log_joins:
            return ""
        if welcome_log:
            return welcome_log

    return ""


def check_not_bot(member: User, chat_id: int, message_id: int, context: CallbackContext):
    bot = context.bot
    member_dict = VERIFIED_USER_WAITLIST.pop((chat_id, member.id))
    member_status = member_dict.get("status")
    if not member_status:
        try:
            bot.unban_chat_member(chat_id, member.id)
        except BadRequest:
            pass

        try:
            bot.edit_message_text(
                "*menendang pengguna*\nMereka selalu dapat bergabung kembali dan mencoba.",
                chat_id=chat_id,
                message_id=message_id,
            )
        except TelegramError:
            bot.delete_message(chat_id=chat_id, message_id=message_id)
            bot.send_message("{} ditendang karena mereka gagal memverifikasi diri mereka sendiri".format(mention_html(member.id,
                                                                                                        member.first_name)),
                                chat_id=chat_id, parse_mode=ParseMode.HTML)


def left_member(update: Update, context: CallbackContext):  # sourcery no-metrics
    bot = context.bot
    chat = update.effective_chat
    user = update.effective_user
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)

    if user.id == bot.id:
        return

    reply = update.message.message_id
    cleanserv = sql.clean_service(chat.id)
    # Clean service welcome
    if cleanserv:
        try:
            dispatcher.bot.delete_message(chat.id, update.message.message_id)
        except BadRequest:
            pass
        reply = False

    if should_goodbye:

        left_mem = update.effective_message.left_chat_member
        if left_mem:

            # Thingy for spamwatched users
            if sw:
                sw_ban = sw.get_ban(left_mem.id)
                if sw_ban:
                    return

            # Dont say goodbyes to gbanned users
            if is_user_gbanned(left_mem.id):
                return

            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text(
                    "Maaf melihatmu pergi :(", reply_to_message_id=reply
                )
                return

            # Give the devs a special goodbye
            elif left_mem.id in DEV_USERS:
                update.effective_message.reply_text(
                    "Sampai jumpa di Eagle Union!",
                    reply_to_message_id=reply,
                )
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type not in [sql.Types.TEXT, sql.Types.BUTTON_TEXT]:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = (
                    left_mem.first_name or "PersonWithNoName"
            )  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if cust_goodbye == sql.DEFAULT_GOODBYE:
                    cust_goodbye = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(
                        first=escape_markdown(first_name)
                    )
                if left_mem.last_name:
                    fullname = escape_markdown(f"{first_name} {left_mem.last_name}")
                else:
                    fullname = escape_markdown(first_name)
                count = chat.get_member_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(
                    cust_goodbye, VALID_WELCOME_FORMATTERS
                )
                res = valid_format.format(
                    first=escape_markdown(first_name),
                    last=escape_markdown(left_mem.last_name or first_name),
                    fullname=escape_markdown(fullname),
                    username=username,
                    mention=mention,
                    count=count,
                    chatname=escape_markdown(chat.title),
                    id=left_mem.id,
                )
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(
                    first=first_name
                )
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(
                update,
                res,
                keyboard,
                random.choice(sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name),
            )


@u_admin
def welcome(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat
    # if no args, show current replies.
    if not args or args[0].lower() == "noformat":
        noformat = True
        pref, welcome_m, cust_content, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            f"Obrolan ini memiliki setelan selamat datang yang disetel ke: `{pref}`.\n"
            f"*Pesan selamat datang (tidak mengisi {{}}) adalah:*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if welcome_type in [sql.Types.BUTTON_TEXT, sql.Types.TEXT]:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)
        else:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                ENUM_FUNC_MAP[welcome_type](chat.id, cust_content, caption=welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                ENUM_FUNC_MAP[welcome_type](
                    chat.id,
                    cust_content,
                    caption=welcome_m,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text(
                "Oke! Saya akan menyapa anggota ketika mereka bergabung."
            )

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text(
                "Saya akan pergi bermalas-malasan dan tidak menyambut siapa pun saat itu."
            )

        else:
            update.effective_message.reply_text(
                "saya mengerti 'on/yes' or 'off/no' saja!"
            )


@u_admin
def goodbye(update: Update, context: CallbackContext):
    args = context.args
    chat = update.effective_chat

    if not args or args[0] == "noformat":
        noformat = True
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            f"Chat ini memiliki setelan selamat tinggal yang disetel ke: `{pref}`.\n"
            f"*Pesan selamat tinggal (tidak mengisi {{}}) adalah:*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        elif noformat:
            ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

        else:
            ENUM_FUNC_MAP[goodbye_type](
                chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN
            )

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("Ok!")

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("Ok!")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text(
                "saya mengerti 'on/yes' or 'off/no' saja!"
            )


@user_admin(AdminPerms.CAN_CHANGE_INFO)
@loggable
def set_welcome(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Anda tidak menentukan apa yang harus dibalas!")
        return ""

    sql.set_custom_welcome(chat.id, content, text, data_type, buttons)
    msg.reply_text("Berhasil menyetel pesan sambutan khusus!")

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Atur pesan selamat datang."
    )


@user_admin(AdminPerms.CAN_CHANGE_INFO)
@loggable
def reset_welcome(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_welcome(chat.id, None, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text(
        "Berhasil mereset pesan selamat datang ke default!"
    )

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Setel ulang pesan selamat datang ke default."
    )


@user_admin(AdminPerms.CAN_CHANGE_INFO)
@loggable
def set_goodbye(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Anda tidak menentukan apa yang harus dibalas!")
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text("Berhasil menyetel pesan selamat tinggal khusus!")
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Tetapkan pesan selamat tinggal."
    )


@user_admin(AdminPerms.CAN_CHANGE_INFO)
@loggable
def reset_goodbye(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text(
        "Berhasil mereset pesan selamat tinggal ke default!"
    )

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Setel ulang pesan selamat tinggal."
    )


@user_admin(AdminPerms.CAN_CHANGE_INFO)
@loggable
def welcomemute(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if len(args) >= 1:
        if args[0].lower() in ("off", "no"):
            sql.set_welcome_mutes(chat.id, False)
            msg.reply_text("Saya tidak akan lagi membisukan orang untuk bergabung!")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Telah beralih selamat datang bisu ke <b>OFF</b>."
            )
        elif args[0].lower() in ["soft"]:
            sql.set_welcome_mutes(chat.id, "soft")
            msg.reply_text(
                "Saya akan membatasi izin pengguna untuk mengirim media selama 24 jam."
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Telah beralih selamat datang bisu ke <b>SOFT</b>."
            )
        elif args[0].lower() in ["strong"]:
            sql.set_welcome_mutes(chat.id, "strong")
            msg.reply_text(
                "Sekarang saya akan membisukan orang ketika mereka bergabung sampai mereka membuktikan bahwa mereka bukan bot.\nMereka akan memiliki waktu 120 detik "
                "sebelum mereka ditendang. "
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Telah beralih selamat datang bisu ke <b>STRONG</b>."
            )
        elif args[0].lower() in ["captcha"]:
            sql.set_welcome_mutes(chat.id, "captcha")
            msg.reply_text(
                "Sekarang saya akan membisukan orang saat mereka bergabung sampai mereka membuktikan bahwa mereka bukan bot.\nMereka harus menyelesaikan "
                "captcha untuk dinonaktifkan. "
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Telah beralih selamat datang bisu ke <b>CAPTCHA</b>."
            )
        else:
            msg.reply_text(
                "Silakan masuk `off`/`no`/`soft`/`strong`/`captcha`!",
                parse_mode=ParseMode.MARKDOWN,
            )
            return ""
    else:
        curr_setting = sql.welcome_mutes(chat.id)
        reply = (
            f"\n Beri saya setelan!\nPilih salah satu dari: `off`/`no` atau `soft`, `strong` atau `captcha` saja! \n"
            f"Pengaturan saat ini: `{curr_setting}`"
        )
        msg.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        return ""


@user_admin(AdminPerms.CAN_CHANGE_INFO)
@loggable
def clean_welcome(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text(
                "Saya harus menghapus pesan selamat datang hingga dua hari."
            )
        else:
            update.effective_message.reply_text(
                "Saat ini saya tidak menghapus pesan selamat datang yang lama!"
            )
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text("Saya akan mencoba menghapus pesan selamat datang yang lama!")
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Telah toggle clean welcome to <code>ON</code>."
        )
    elif args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text("Saya tidak akan menghapus pesan selamat datang yang lama.")
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Telah toggle clean welcome to <code>OFF</code>."
        )
    else:
        update.effective_message.reply_text("saya mengerti 'on/yes' or 'off/no' only!")
        return ""


@user_admin(AdminPerms.CAN_CHANGE_INFO)
def cleanservice(update: Update, context: CallbackContext) -> str:
    args = context.args
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type == chat.PRIVATE:
        curr = sql.clean_service(chat.id)
        if curr:
            update.effective_message.reply_text(
                "Selamat datang layanan bersih : on", parse_mode=ParseMode.MARKDOWN
            )
        else:
            update.effective_message.reply_text(
                "Selamat datang layanan bersih : off", parse_mode=ParseMode.MARKDOWN
            )

    elif len(args) >= 1:
        var = args[0]
        if var in ("no", "off"):
            sql.set_clean_service(chat.id, False)
            update.effective_message.reply_text("Selamat datang layanan bersih : off")
        elif var in ("yes", "on"):
            sql.set_clean_service(chat.id, True)
            update.effective_message.reply_text("Selamat datang layanan bersih : on")
        else:
            update.effective_message.reply_text(
                "Opsi tidak valid", parse_mode=ParseMode.MARKDOWN
            )
    else:
        update.effective_message.reply_text(
            "Penggunaan adalah on/yes or off/no", parse_mode=ParseMode.MARKDOWN
        )


def user_button(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    query = update.callback_query
    bot = context.bot
    match = re.match(r"user_join_\((.+?)\)", query.data)
    message = update.effective_message
    join_user = int(match.group(1))

    if join_user == user.id:
        sql.set_human_checks(user.id, chat.id)
        member_dict = VERIFIED_USER_WAITLIST[(chat.id, user.id)]
        member_dict["status"] = True
        query.answer(text="Yeet! Anda seorang manusia, tidak dibisukan!")
        bot.restrict_chat_member(
            chat.id,
            user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_send_polls=True,
                can_change_info=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        try:
            bot.deleteMessage(chat.id, message.message_id)
        except:
            pass
        if member_dict["should_welc"]:
            if member_dict["media_wel"]:
                sent = ENUM_FUNC_MAP[member_dict["welc_type"]](
                    member_dict["chat_id"],
                    member_dict["cust_content"],
                    caption=member_dict["res"],
                    reply_markup=member_dict["keyboard"],
                    parse_mode="markdown",
                )
            else:
                sent = send(
                    member_dict["update"],
                    member_dict["res"],
                    member_dict["keyboard"],
                    member_dict["backup_message"],
                )

            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

    else:
        query.answer(text="Anda tidak diizinkan melakukan ini!")


def user_captcha_button(update: Update, context: CallbackContext):
    # sourcery no-metrics
    chat = update.effective_chat
    user = update.effective_user
    query = update.callback_query
    bot = context.bot
    # print(query.data)
    match = re.match(r"user_captchajoin_\(([\d\-]+),(\d+)\)_\((\d{4})\)", query.data)
    message = update.effective_message
    join_chat = int(match.group(1))
    join_user = int(match.group(2))
    captcha_ans = int(match.group(3))
    join_usr_data = bot.getChat(join_user)

    if join_user == user.id:
        c_captcha_ans = CAPTCHA_ANS_DICT.pop((join_chat, join_user))
        if c_captcha_ans == captcha_ans:
            sql.set_human_checks(user.id, chat.id)
            member_dict = VERIFIED_USER_WAITLIST[(chat.id, user.id)]
            member_dict["status"] = True
            query.answer(text="Yeet! Anda seorang manusia, tidak dibisukan!")
            bot.restrict_chat_member(
                chat.id,
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_invite_users=True,
                    can_pin_messages=True,
                    can_send_polls=True,
                    can_change_info=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            try:
                bot.deleteMessage(chat.id, message.message_id)
            except:
                pass
            if member_dict["should_welc"]:
                if member_dict["media_wel"]:
                    sent = ENUM_FUNC_MAP[member_dict["welc_type"]](
                        member_dict["chat_id"],
                        member_dict["cust_content"],
                        caption=member_dict["res"],
                        reply_markup=member_dict["keyboard"],
                        parse_mode="markdown",
                    )
                else:
                    sent = send(
                        member_dict["update"],
                        member_dict["res"],
                        member_dict["keyboard"],
                        member_dict["backup_message"],
                    )

                prev_welc = sql.get_clean_pref(chat.id)
                if prev_welc:
                    try:
                        bot.delete_message(chat.id, prev_welc)
                    except BadRequest:
                        pass

                    if sent:
                        sql.set_clean_welcome(chat.id, sent.message_id)
        else:
            try:
                bot.deleteMessage(chat.id, message.message_id)
            except:
                pass
            kicked_msg = f'''
            ❌ [{escape_markdown(join_usr_data.first_name)}](tg://user?id={join_user}) failed the captcha and was kicked.
            '''
            query.answer(text="Wrong answer")
            res = chat.unban_member(join_user)
            if res:
                bot.sendMessage(chat_id=chat.id, text=kicked_msg, parse_mode=ParseMode.MARKDOWN)


    else:
        query.answer(text="Anda tidak diizinkan melakukan ini!")


WELC_HELP_TXT = (
    "Pesan selamat datang/selamat tinggal grup Anda dapat dipersonalisasi dengan berbagai cara. Jika Anda menginginkan pesannya"
    " agar dibuat satu per satu, seperti pesan selamat datang default, Anda dapat menggunakan *variabel ini*:\n"
    " • `{first}`*:* ini menunjukkan *nama depan* pengguna\n"
    " • `{last}`*:* ini menunjukkan *nama belakang* pengguna. Defaultnya adalah *nama depan* jika pengguna tidak memiliki "
    "nama belakang.\n"
    " • `{namalengkap}`*:* ini menunjukkan *nama lengkap* pengguna. Defaultnya adalah *nama depan* jika pengguna tidak memiliki "
    "nama belakang.\n"
    " • `{namapengguna}`*:* ini menunjukkan *namapengguna* pengguna. Defaultnya adalah *sebutan* dari "
    "nama depan jika tidak memiliki nama pengguna.\n"
    " • `{mention}`*:* ini hanya *menyebutkan* pengguna - menandai mereka dengan nama depannya.\n"
    " • `{id}`*:* ini mewakili *id*\n pengguna"
    " • `{count}`*:* ini mewakili *nomor anggota* pengguna.\n"
    " • `{chatname}`*:* ini mewakili *nama chat saat ini*.\n"
    "\nSetiap variabel HARUS diapit oleh `{}` untuk diganti.\n"
    "Pesan selamat datang juga mendukung penurunan harga, sehingga Anda dapat membuat elemen apa pun menjadi tebal/miring/kode/tautan."
    "Tombol juga didukung, sehingga Anda dapat membuat sambutan Anda terlihat mengagumkan dengan intro yang bagus"
    "tombol.\n"
    f"Untuk membuat tombol yang menautkan ke aturan Anda, gunakan ini: `[Aturan](buttonurl://t.me/{dispatcher.bot.username}?start=group_id)`."
    "Cukup ganti `group_id` dengan id grup Anda, yang dapat diperoleh melalui /id, dan Anda siap "
    "pergi. Perhatikan bahwa id grup biasanya diawali dengan tanda `-`; ini diperlukan, jadi tolong jangan "
    "hapus itu.\n"
    "Anda bahkan dapat menyetel gambar/gif/video/pesan suara sebagai pesan selamat datang dengan "
    "membalas ke media yang diinginkan, dan memanggil `/ setwelcome`."
)

WELC_MUTE_HELP_TXT = (
    "Anda bisa mendapatkan bot untuk membisukan orang baru yang bergabung dengan grup Anda dan karenanya mencegah robot spam membanjiri grup Anda."
    "Opsi berikut dimungkinkan:\n"
    "• `/welcomemute soft`*:* membatasi anggota baru untuk mengirim media selama 24 jam.\n"
    "• `/welcomemute strong`*:* membisukan anggota baru hingga mereka mengetuk tombol sehingga memverifikasi bahwa mereka adalah manusia.\n"
    "• `/welcomemute captcha`*:* membisukan anggota baru sampai mereka menyelesaikan captcha tombol sehingga memverifikasi bahwa mereka adalah manusia.\n"
    "• `/welcomemute nonaktif`*:* menonaktifkan welcomemute.\n"
    "*Catatan:* Mode kuat mengeluarkan pengguna dari obrolan jika mereka tidak memverifikasi dalam 120 detik. Namun, mereka selalu dapat bergabung kembali"
)


@u_admin
def welcome_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


@u_admin
def welcome_mute_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        WELC_MUTE_HELP_TXT, parse_mode=ParseMode.MARKDOWN
    )


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref = sql.get_welc_pref(chat_id)[0]
    goodbye_pref = sql.get_gdbye_pref(chat_id)[0]
    return (
        "Obrolan ini menyetel preferensi selamat datang ke `{}`.\n"
        "Ini preferensi selamat tinggal adalah `{}`.".format(welcome_pref, goodbye_pref)
    )


from Telegram.modules.language import gs


def get_help(chat):
    return gs(chat, "greetings_help")


NEW_MEM_HANDLER = MessageHandler(
    Filters.status_update.new_chat_members, new_member, run_async=True
)
LEFT_MEM_HANDLER = MessageHandler(
    Filters.status_update.left_chat_member, left_member, run_async=True
)
WELC_PREF_HANDLER = CommandHandler(
    "welcome", welcome, filters=Filters.chat_type.groups, run_async=True
)
GOODBYE_PREF_HANDLER = CommandHandler(
    "goodbye", goodbye, filters=Filters.chat_type.groups, run_async=True
)
SET_WELCOME = CommandHandler(
    "setwelcome", set_welcome, filters=Filters.chat_type.groups, run_async=True
)
SET_GOODBYE = CommandHandler(
    "setgoodbye", set_goodbye, filters=Filters.chat_type.groups, run_async=True
)
RESET_WELCOME = CommandHandler(
    "resetwelcome", reset_welcome, filters=Filters.chat_type.groups, run_async=True
)
RESET_GOODBYE = CommandHandler(
    "resetgoodbye", reset_goodbye, filters=Filters.chat_type.groups, run_async=True
)
WELCOMEMUTE_HANDLER = CommandHandler(
    "welcomemute", welcomemute, filters=Filters.chat_type.groups, run_async=True
)
CLEAN_SERVICE_HANDLER = CommandHandler(
    "cleanservice", cleanservice, filters=Filters.chat_type.groups, run_async=True
)
CLEAN_WELCOME = CommandHandler(
    "cleanwelcome", clean_welcome, filters=Filters.chat_type.groups, run_async=True
)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help, run_async=True)
WELCOME_MUTE_HELP = CommandHandler("welcomemutehelp", welcome_mute_help, run_async=True)
BUTTON_VERIFY_HANDLER = CallbackQueryHandler(
    user_button, pattern=r"user_join_", run_async=True
)
CAPTCHA_BUTTON_VERIFY_HANDLER = CallbackQueryHandler(
    user_captcha_button, pattern=r"user_captchajoin_\([\d\-]+,\d+\)_\(\d{4}\)", run_async=True
)

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(WELCOME_HELP)
dispatcher.add_handler(WELCOMEMUTE_HANDLER)
dispatcher.add_handler(CLEAN_SERVICE_HANDLER)
dispatcher.add_handler(BUTTON_VERIFY_HANDLER)
dispatcher.add_handler(WELCOME_MUTE_HELP)
dispatcher.add_handler(CAPTCHA_BUTTON_VERIFY_HANDLER)

__mod_name__ = "Greetings"
__command_list__ = []
__handlers__ = [
    NEW_MEM_HANDLER,
    LEFT_MEM_HANDLER,
    WELC_PREF_HANDLER,
    GOODBYE_PREF_HANDLER,
    SET_WELCOME,
    SET_GOODBYE,
    RESET_WELCOME,
    RESET_GOODBYE,
    CLEAN_WELCOME,
    WELCOME_HELP,
    WELCOMEMUTE_HANDLER,
    CLEAN_SERVICE_HANDLER,
    BUTTON_VERIFY_HANDLER,
    CAPTCHA_BUTTON_VERIFY_HANDLER,
    WELCOME_MUTE_HELP,
]
