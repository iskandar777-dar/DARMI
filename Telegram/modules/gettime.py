import datetime
from typing import List

import requests
from Telegram import TIME_API_KEY, dispatcher
from telegram import ParseMode, Update
from telegram.ext import CallbackContext
from Telegram.modules.helper_funcs.decorators import zaid


def generate_time(to_find: str, findtype: List[str]) -> str:
    data = requests.get(
        f"https://api.timezonedb.com/v2.1/list-time-zone"
        f"?key={TIME_API_KEY}"
        f"&format=json"
        f"&fields=countryCode,countryName,zoneName,gmtOffset,timestamp,dst"
    ).json()

    for zone in data["zones"]:
        for eachtype in findtype:
            if to_find in zone[eachtype].lower():
                country_name = zone["countryName"]
                country_zone = zone["zoneName"]
                country_code = zone["countryCode"]

                daylight_saving = "Yes" if zone["dst"] == 1 else "No"
                date_fmt = r"%d-%m-%Y"
                time_fmt = r"%H:%M:%S"
                day_fmt = r"%A"
                gmt_offset = zone["gmtOffset"]
                timestamp = datetime.datetime.now(
                    datetime.timezone.utc
                ) + datetime.timedelta(seconds=gmt_offset)
                current_date = timestamp.strftime(date_fmt)
                current_time = timestamp.strftime(time_fmt)
                current_day = timestamp.strftime(day_fmt)

                break

    try:
        result = (
            f"<b>Negara:</b> <kode>{nama_negara}</kode>\n"
            f"<b>Nama Zona:</b> <code>{country_zone}</code>\n"
            f"<b>Kode Negara:</b> <code>{country_code}</code>\n"
            f"<b>Penghematan siang hari:</b> <code>{daylight_saving}</code>\n"
            f"<b>Hari:</b> <code>{current_day}</code>\n"
            f"<b>Waktu Saat Ini:</b> <code>{current_time}</code>\n"
            f"<b>Tanggal Sekarang:</b> <code>{current_date}</code>\n"
            '<b>Zona waktu: </b> <a href="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones">List here</a>'
        )
    except:
        result = None

    return result

@zaid(command='time')
def gettime(update: Update, context: CallbackContext):
    message = update.effective_message

    try:
        query = message.text.strip().split(" ", 1)[1]
    except:
        message.reply_text("Menyediakan negara name/abbreviation/timezone to find.")
        return
    send_message = message.reply_text(
        f"Menemukan info zona waktu untuk <b>{query}</b>", parse_mode=ParseMode.HTML
    )

    query_timezone = query.lower()
    if len(query_timezone) == 2:
        result = generate_time(query_timezone, ["countryCode"])
    else:
        result = generate_time(query_timezone, ["zoneName", "countryName"])

    if not result:
        send_message.edit_text(
            f"Info zona waktu tidak tersedia untuk <b>{query}</b>\n"
            '<b>Semua Zona Waktu :</b> <a href="https://en.wikipedia.org/wiki/List_of_tz_database_time_zones">List here</a>',
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return

    send_message.edit_text(
        result, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )

__mod_name__ = "Time"
