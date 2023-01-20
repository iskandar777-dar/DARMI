import html
import json
from datetime import datetime
from platform import python_version
from typing import List
from uuid import uuid4

import requests
from telegram import InlineQueryResultArticle, ParseMode, InputTextMessageContent, Update, InlineKeyboardMarkup, \
    InlineKeyboardButton
from telegram import __version__
from telegram.error import BadRequest
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

import Telegram.modules.sql.users_sql as sql
from Telegram import (
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    DEV_USERS,
    SARDEGNA_USERS,
    WHITELIST_USERS,
    sw, log
)
from Telegram.modules.helper_funcs.misc import article
from Telegram.modules.helper_funcs.decorators import zaidinline


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        text = text.replace(prefix, "", 1)
    return text

@zaidinline()
def inlinequery(update: Update, _) -> None:
    """
    Callback InlineQueryHandler Utama.
    """
    query = update.inline_query.query
    user = update.effective_user

    results: List = []
    inline_help_dicts = [
        {
            "title": "Info akun tentang Anie",
            "description": "Cari akun Telegram di basis data Anie",
            "message_text": "Klik tombol di bawah untuk mencari seseorang di basis data Anie menggunakan ID Telegram mereka",
            "thumb_urL": "https://telegra.ph/file/8fd1b2351135e778700a0.jpg",
            "keyboard": ".info ",
        },
        {
            "judul": "Tentang",
            "description": "Ketahui tentang Anie",
            "message_text": "Klik tombol di bawah untuk mengetahui tentang Kigyo.",
            "thumb_urL": "https://telegra.ph/file/8fd1b2351135e778700a0.jpg",
            "keyboard": ".about ",
        },
        {
            "judul": "Anime",
            "description": "Cari anime dan manga di AniList.co",
            "message_text": "Klik tombol di bawah untuk mencari anime dan manga di AniList.co",
            "thumb_urL": "https://telegra.ph/file/8fd1b2351135e778700a0.jpg",
            "keyboard": ".anilist ",
        },
    ]

    inline_funcs = {
        ".spb": spb,
        ".info": inlineinfo,
        ".about": about,
        ".anilist": media_query,
    }

    if (f := query.split(" ", 1)[0]) in inline_funcs:
        inline_funcs[f](remove_prefix(query, f).strip(), update, user)
    else:
        for ihelp in inline_help_dicts:
            results.append(
                article(
                    title=ihelp["title"],
                    description=ihelp["description"],
                    message_text=ihelp["message_text"],
                    thumb_url=ihelp["thumb_urL"],
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text="Click Here",
                                    switch_inline_query_current_chat=ihelp[
                                        "keyboard"
                                    ],
                                )
                            ]
                        ]
                    ),
                )
            )

        update.inline_query.answer(results, cache_time=5)


def inlineinfo(query: str, update: Update, context: CallbackContext) -> None:
    """Handle the inline query."""
    bot = context.bot
    query = update.inline_query.query
    log.info(query)
    user_id = update.effective_user.id

    try:
        search = query.split(" ", 1)[1]
    except IndexError:
        search = user_id

    try:
        user = bot.get_chat(int(search))
    except (BadRequest, ValueError):
        user = bot.get_chat(user_id)

    chat = update.effective_chat
    sql.update_user(user.id, user.username)

    text = (
        f"<b>Informasi:</b>\n"
        f"• ID: <code>{user.id}</code>\n"
        f"• Nama Depan: {html.escape(user.first_name)}"
    )

    jika pengguna.nama_belakang:
        text += f"\n• Nama Belakang: {html.escape(user.last_name)}"

    jika pengguna. nama pengguna:
        teks += f"\n• Nama pengguna: @{html.escape(nama pengguna.nama pengguna)}"

    teks += f"\n• Tautan pengguna permanen: {mention_html(user.id, 'link')}"

    nation_level_present = False

    jika user.id == OWNER_ID:
        teks += f"\n\nOrang ini adalah pemilik saya"
        nation_level_present = Benar
    elif user.id di DEV_USERS:
        text += f"\n\nOrang ini adalah bagian dari Eagle Union"
        nation_level_present = Benar
    elif user.id di SUDO_USERS:
        teks += f"\n\nTingkat Bangsa orang ini adalah Bangsawan"
        nation_level_present = Benar
    elif user.id di SUPPORT_USERS:
        teks += f"\n\nTingkat Bangsa orang ini adalah Sakura"
        nation_level_present = Benar
    elif user.id di SARDEGNA_USERS:
        teks += f"\n\nTingkat Bangsa orang ini adalah Sardegna"
        nation_level_present = Benar
    elif user.id di WHITELIST_USERS:
        teks += f"\n\nTingkat Bangsa orang ini adalah Neptunia"
        nation_level_present = Benar

    if nation_level_present:
        text += ' [<a href="https://t.me/{}?start=nations">?</a>]'.format(bot.username)

    try:
        spamwtc = sw.get_ban(int(user.id))
        if spamwtc:
            teks += "<b>\n\n• Ditonton Spam:\n</b> Ya"
            text += f"\n• Alasan: <pre>{spamwtc.reason}</pre>"
            teks += "\n• Banding di @SpamWatchSupport"
        else:
            text += "<b>\n\n• SpamMenonton:</b> No"
    except:
        pass  # don't crash if api is down somehow...

    num_chats = sql.get_user_num_chats(user.id)
    text += f"\n• <b>Jumlah obrolan</b>: <code>{num_chats}</code>"




    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Mencari lagi",
                    switch_inline_query_current_chat=".info ",
                ),

            ],
        ]
        )

    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"Info pengguna dari {html.escape(user.first_name)}",
            input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML,
                                                            disable_web_page_preview=True),
            reply_markup=kb
        ),
    ]

    update.inline_query.answer(results, cache_time=5)


def about(query: str, update: Update, context: CallbackContext) -> None:
    """Tangani kueri sebaris."""
    query = update.inline_query.query
    user_id = update.effective_user.id
    user = context.bot.get_chat(user_id)
    sql.update_user(user.id, user.username)
    about_text = f"""
    Somed (@{context.bot.username})
    Dikelola oleh [Darmi](t.me/kenapatagdar)
    Dibangun dengan ❤️ menggunakan python-telegram-bot v{str(__version__)}
    Berjalan di Python {python_version()}
    """
    results: list = []
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Support",
                    url=f"https://t.me/medsupportt",
                ),
                InlineKeyboardButton(
                    text="Channel",
                    url=f"https://t.me/",
                ),
                InlineKeyboardButton(
                    text='Ping',
                    callback_data='pingCB'
                ),

            ],
            [
                InlineKeyboardButton(
                    text="GitLab",
                    url=f"https://www.gitlab.com/",
                ),
                InlineKeyboardButton(
                    text="GitHub",
                    url="https://www.github.com/",
                ),
            ],
        ])

    results.append(

        InlineQueryResultArticle
            (
            id=str(uuid4()),
            title=f"Tentang Somed (@{context.bot.username})",
            input_message_content=InputTextMessageContent(about_text, parse_mode=ParseMode.MARKDOWN,
                                                        disable_web_page_preview=True),
            reply_markup=kb
        )
    )
    update.inline_query.answer(results)


def spb(query: str, update: Update, context: CallbackContext) -> None:
    """Tangani kueri sebaris."""
    query = update.inline_query.query
    user_id = update.effective_user.id
    srdata = None
    apst = requests.get(f'https://api.intellivoid.net/spamprotection/v1/lookup?query={context.bot.username}')
    api_status = apst.status_code
    if (api_status != 200):
        stats = f"API KEMBALI {api_status}"
    else:
        try:
            search = query.split(" ", 1)[1]
        except IndexError:
            search = user_id

        srdata = search or user_id
        url = f"https://api.intellivoid.net/spamprotection/v1/lookup?query={srdata}"
        r = requests.get(url)
        a = r.json()
        response = a["success"]
        if response is True:
            date = a["results"]["last_updated"]
            stats = f"*◢ Intellivoid• SpamProtection Info*:\n"
            stats += f' • *Updated on*: `{datetime.fromtimestamp(date).strftime("%Y-%m-%d %I:%M:%S %p")}`\n'

            if a["results"]["attributes"]["is_potential_spammer"] is True:
                stats += f" • *User*: `USERxSPAM`\n"
            elif a["results"]["attributes"]["is_operator"] is True:
                stats += f" • *User*: `USERxOPERATOR`\n"
            elif a["results"]["attributes"]["is_agent"] is True:
                stats += f" • *User*: `USERxAGENT`\n"
            elif a["results"]["attributes"]["is_whitelisted"] is True:
                stats += f" • *User*: `USERxWHITELISTED`\n"

            stats += f' • *Type*: `{a["results"]["entity_type"]}`\n'
            stats += (
                f' • *Language*: `{a["results"]["language_prediction"]["language"]}`\n'
            )
            stats += f' • *Language Probability*: `{a["results"]["language_prediction"]["probability"]}`\n'
            stats += f"*Spam Prediction*:\n"
            stats += f' • *Ham Prediction*: `{a["results"]["spam_prediction"]["ham_prediction"]}`\n'
            stats += f' • *Spam Prediction*: `{a["results"]["spam_prediction"]["spam_prediction"]}`\n'
            stats += f'*Blacklisted*: `{a["results"]["attributes"]["is_blacklisted"]}`\n'
            if a["results"]["attributes"]["is_blacklisted"] is True:
                stats += (
                    f' • *Reason*: `{a["results"]["attributes"]["blacklist_reason"]}`\n'
                )
                stats += f' • *Flag*: `{a["results"]["attributes"]["blacklist_flag"]}`\n'
            stats += f'*PTID*:\n`{a["results"]["private_telegram_id"]}`\n'

        else:
            stats = "`cannot reach SpamProtection API`"

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Report Error",
                    url=f"https://t.me/AnieSupports",
                ),
                InlineKeyboardButton(
                    text="Search again",
                    switch_inline_query_current_chat=".spb ",
                ),

            ],
        ])

    a = "entitas tidak ditemukan"
    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"Info SpamProtection API dari {srdata or a}",
            input_message_content=InputTextMessageContent(stats, parse_mode=ParseMode.MARKDOWN,
                                                            disable_web_page_preview=True),
            reply_markup=kb
        ),
    ]

    update.inline_query.answer(results, cache_time=5)



MEDIA_QUERY = '''query ($search: String) {
    Page (perPage: 10) {
    media (search: $search) {
        id
        title {
        romaji
        english
        native
      }
      type
      format
      status
      description
      episodes
      bannerImage
      duration
      chapters
      volumes
      genres
      synonyms
      averageScore
      airingSchedule(notYetAired: true) {
        nodes {
          airingAt
          timeUntilAiring
          episode
        }
      }
      siteUrl
    }
  }
}'''


def media_query(query: str, update: Update, context: CallbackContext) -> None:
    """
    Tangani kueri inline anime.
    """
    results: List = []

    try:
        results: List = []
        r = requests.post('https://graphql.anilist.co',
                          data=json.dumps({'query': MEDIA_QUERY, 'variables': {'search': query}}),
                          headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
        res = r.json()
        data = res['data']['Page']['media']
        res = data
        for data in res:
            title_en = data["title"].get("english") or "N/A"
            title_ja = data["title"].get("romaji") or "N/A"
            format = data.get("format") or "N/A"
            type = data.get("type") or "N/A"
            bannerimg = data.get("bannerImage") or "https://telegra.ph/file/8fd1b2351135e778700a0.jpg"
            try:
                des = data.get("description").replace("<br>", "").replace("</br>", "")
                description = des.replace("<i>", "").replace("</i>", "") or "N/A"
            except AttributeError:
                description = data.get("description")

            try:
                description = html.escape(description)
            except AttributeError:
                description = description or "N/A"

            if len((str(description))) > 700:
                description = description [0:700] + "....."

            avgsc = data.get("averageScore") or "N/A"
            status = data.get("status") or "N/A"
            genres = data.get("genres") or "N/A"
            genres = ", ".join(genres)
            img = f"https://img.anili.st/media/{data['id']}" or "https://telegra.ph/file/8fd1b2351135e778700a0.jpg"
            aurl = data.get("siteUrl")


            kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Read More",
                            url=aurl,
                        ),
                        InlineKeyboardButton(
                            text="Search again",
                            switch_inline_query_current_chat=".anilist ",
                        ),

                    ],
                ])

            txt = f"<b>{title_en} | {title_ja}</b>\n"
            txt += f"<b>Format</b>: <kode>{format}</code>\n"
            txt += f"<b>Ketik</b>: <code>{type}</code>\n"
            txt += f"<b>Skor Rata-rata</b>: <code>{avgsc}</code>\n"
            txt += f"<b>Status</b>: <kode>{status}</code>\n"
            txt += f"<b>Genre</b>: <code>{genres}</code>\n"
            txt += f"<b>Deskripsi</b>: <code>{description}</code>\n"
            txt += f"<a href='{img}'>&#xad</a>"

            results.append(
                InlineQueryResultArticle
                    (
                    id=str(uuid4()),
                    title=f"{title_en} | {title_ja} | {format}",
                    thumb_url=img,
                    description=f"{description}",
                    input_message_content=InputTextMessageContent(txt, parse_mode=ParseMode.HTML,
                                                                    disable_web_page_preview=False),
                    reply_markup=kb
                )
            )
    except Exception as e:

        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="Report error",
                        url="t.me/medsupportt",
                    ),
                    InlineKeyboardButton(
                        text="Mencari lagi",
                        switch_inline_query_current_chat=".anilist ",
                    ),

                ],
            ])

        results.append(

            InlineQueryResultArticle
                (
                id=str(uuid4()),
                title=f"Media {query} tidak ditemukan",
                input_message_content=InputTextMessageContent(f"Media {query} tidak ditemukan karena {e}", parse_mode=ParseMode.MARKDOWN,
                                                            disable_web_page_preview=True),
                reply_markup=kb
            )

        )

    update.inline_query.answer(results, cache_time=5)
