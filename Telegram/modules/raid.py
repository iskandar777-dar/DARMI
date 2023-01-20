# Raid module by Luke (t.me/itsLuuke)
import html
from typing import Optional
from datetime import timedelta
from pytimeparse.timeparse import timeparse

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

from .log_channel import loggable
from .helper_funcs.anonymous import user_admin, AdminPerms
from .helper_funcs.chat_status import bot_admin, connection_status, user_admin_no_reply
from .helper_funcs.decorators import zaid, zaidcallback
from .. import log, updater

import Telegram.modules.sql.welcome_sql as sql

j = updater.job_queue

# store job id in a dict to be able to cancel them later
RUNNING_RAIDS = {}  # {chat_id:job_id, ...}


def get_time(time: str) -> int:
    try:
        return timeparse(time)
    except BaseException:
        return 0


def get_readable_time(time: int) -> str:
    t = f"{timedelta(seconds=time)}".split(":")
    if time == 86400:
        return "1 day"
    return "{} hour(s)".format(t[0]) if time >= 3600 else "{} minutes".format(t[1])


@zaid(command="raid", pass_args=True)
@bot_admin
@connection_status
@loggable
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def setRaid(update: Update, context: CallbackContext) -> Optional[str]:
    args = context.args
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    if chat.type == "private":
        context.bot.sendMessage(chat.id, "Perintah ini tidak tersedia di PM.")
        return
    stat, time, acttime = sql.getRaidStatus(chat.id)
    readable_time = get_readable_time(time)
    if len(args) == 0:
        if stat:
            text = 'Mode serangan saat ini <code>Diaktifkan</code>\nApakah Anda ingin <code>Nonaktifkan</code> serangan?'
            keyboard = [[
                InlineKeyboardButton("Nonaktifkan Mode Serangan", callback_data="disable_raid={}={}".format(chat.id, time)),
                InlineKeyboardButton("Batalkan Tindakan", callback_data="cancel_raid=1"),
            ]]
        else:
            text = f"Mode penyerangan saat ini <code>Nonaktif</code>\nApakah Anda ingin <code>Aktifkan</code> " \
                    f"raid for {readable_time}?"
            keyboard = [[
                InlineKeyboardButton("Aktifkan Mode Serangan", callback_data="enable_raid={}={}".format(chat.id, time)),
                InlineKeyboardButton("Batalkan Tindakan", callback_data="cancel_raid=0"),
            ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    elif args[0] == "off":
        if stat:
            sql.setRaidStatus(chat.id, False, time, acttime)
            j.scheduler.remove_job(RUNNING_RAIDS.pop(chat.id))
            text = "Mode Raid telah <code>Nonaktif</code>, anggota yang bergabung tidak akan ditendang lagi."
            msg.reply_text(text, parse_mode=ParseMode.HTML)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#RAID\n"
                f"Disabled\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n")

    else:
        args_time = args[0].lower()
        if time := get_time(args_time):
            readable_time = get_readable_time(time)
            if 300 <= time < 86400:
                text = f"Mode penyerangan saat ini <code>Nonaktif</code>\nApakah Anda ingin <code>Aktifkan</code> " \
                        f"razia untuk {readable_time}? "
                keyboard = [[
                    InlineKeyboardButton("Aktifkan Raid", callback_data="enable_raid={}={}".format(chat.id, waktu)),
                    InlineKeyboardButton("Batalkan Tindakan", callback_data="cancel_raid=0"),
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            else:
                msg.reply_text("Anda hanya dapat mengatur waktu antara 5 menit dan 1 hari", parse_mode=ParseMode.HTML)

        else:
            msg.reply_text("Waktu yang tidak diketahui diberikan, beri saya waktu sekitar 5 menit atau 1 jam", parse_mode=ParseMode.HTML)


@zaidcallback(pattern="enable_raid=")
@connection_status
@user_admin_no_reply
@loggable
def enable_raid_cb(update: Update, ctx: CallbackContext) -> Optional[str]:
    args = update.callback_query.data.replace("enable_raid=", "").split("=")
    chat = update.effective_chat
    user = update.effective_user
    chat_id = args[0]
    time = int(args[1])
    readable_time = get_readable_time(time)
    _, t, acttime = sql.getRaidStatus(chat_id)
    sql.setRaidStatus(chat_id, True, time, acttime)
    update.effective_message.edit_text(f"Mode serangan telah <code>Diaktifkan</code> {readable_time}.",
                                        parse_mode=ParseMode.HTML)
    log.info("mengaktifkan mode serangan di {} untuk {}".format(chat_id, readable_time))
    try:
        oldRaid = RUNNING_RAIDS.pop(int(chat_id))
        j.scheduler.remove_job(oldRaid)  # check if there was an old job
    except KeyError:
        pass

    def disable_raid(_):
        sql.setRaidStatus(chat_id, False, t, acttime)
        log.info("mode serangan yang dinonaktifkan di {}".format(chat_id))
        ctx.bot.send_message(chat_id, "Mode serangan telah dinonaktifkan secara otomatis!")

    raid = j.run_once(disable_raid, time)
    RUNNING_RAIDS[int(chat_id)] = raid.job.id
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RAID\n"
        f"Diaktifkan selama {readable_time}\n"
        f"<b>Administrasi:</b> {mention_html(user.id, user.first_name)}\n"
    )


@zaidcallback(pattern="disable_raid=")
@connection_status
@user_admin_no_reply
@loggable
def disable_raid_cb(update: Update, _: CallbackContext) -> Optional[str]:
    args = update.callback_query.data.replace("disable_raid=", "").split("=")
    chat = update.effective_chat
    user = update.effective_user
    chat_id = args[0]
    time = args[1]
    _, _, acttime = sql.getRaidStatus(chat_id)
    sql.setRaidStatus(chat_id, False, time, acttime)
    j.scheduler.remove_job(RUNNING_RAIDS.pop(int(chat_id)))
    update.effective_message.edit_text(
        'Mode Raid telah <code>Nonaktif</code>, anggota yang baru bergabung tidak akan ditendang lagi.',
        parse_mode=ParseMode.HTML,
    )
    logmsg = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RAID\n"
        f"Dinonaktifkan\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
    )
    return logmsg


@zaidcallback(pattern="cancel_raid=")
@connection_status
@user_admin_no_reply
def disable_raid_cb(update: Update, _: CallbackContext):
    args = update.callback_query.data.split("=")
    what = args[0]
    update.effective_message.edit_text(
        f"Tindakan dibatalkan, mode Raid akan tetap <code>{'Enabled' if what == 1 else 'Disabled'}</code>.",
        parse_mode=ParseMode.HTML)


@zaid(command="raidtime")
@connection_status
@loggable
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def raidtime(update: Update, context: CallbackContext) -> Optional[str]:
    what, time, acttime = sql.getRaidStatus(update.effective_chat.id)
    args = context.args
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not args:
        msg.reply_text(
            f"Mode penyerangan saat ini disetel ke {get_readable_time(time)}\nSaat dialihkan, mode penyerangan akan berlangsung "
            f"untuk {get_readable_time(time)} lalu matikan secara otomatis",
            parse_mode=ParseMode.HTML)
        return
    args_time = args[0].lower()
    if time := get_time(args_time):
        readable_time = get_readable_time(time)
        if 300 <= time < 86400:
            text = f"Mode Raid saat ini disetel ke {readable_time}\nSaat diaktifkan, mode serangan akan berlangsung selama " \
                    f"{readable_time} lalu matikan secara otomatis"
            msg.reply_text(text, parse_mode=ParseMode.HTML)
            sql.setRaidStatus(chat.id, what, time, acttime)
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#RAID\n"
                    f"Atur waktu mode Raid ke : {readable_time}\n"
                    f"<b>Admin :</b> {mention_html(user.id, user.first_name)}\n")
        else:
            msg.reply_text("Anda hanya dapat mengatur waktu antara 5 menit dan 1 hari", parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("Waktu yang tidak diketahui diberikan, beri saya waktu sekitar 5 menit atau 1 jam", parse_mode=ParseMode.HTML)


@zaid(command="raidactiontime", pass_args=True)
@connection_status
@user_admin(AdminPerms.CAN_CHANGE_INFO)
@loggable
def raidtime(update: Update, context: CallbackContext) -> Optional[str]:
    what, t, time = sql.getRaidStatus(update.effective_chat.id)
    args = context.args
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not args:
        msg.reply_text(
            f"Waktu aksi serbuan saat ini disetel ke {get_readable_time(time)}\nSaat dialihkan, anggota yang "
            f"bergabung akan dilarang sementara  {get_readable_time(time)}",
            parse_mode=ParseMode.HTML)
        return
    args_time = args[0].lower()
    if time := get_time(args_time):
        readable_time = get_readable_time(time)
        if 300 <= time < 86400:
            text = f"Waktu aksi penyerangan saat ini disetel ke {get_readable_time(time)}\nSaat dialihkan, anggota yang" \
                    f" join akan dilarang sementara {readable_time}"
            msg.reply_text(text, parse_mode=ParseMode.HTML)
            sql.setRaidStatus(chat.id, what, t, time)
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#RAID\n"
                    f"Atur waktu aksi mode Raid ke {readable_time}\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n")
        else:
            msg.reply_text("Anda hanya dapat mengatur waktu antara 5 menit dan 1 hari", parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("Waktu yang tidak diketahui diberikan, beri saya waktu sekitar 5 menit atau 1 jam", parse_mode=ParseMode.HTML)


from .language import gs


def get_help(chat):
    return gs(chat, "raid_help")


__mod_name__ = "AntiRaid"
