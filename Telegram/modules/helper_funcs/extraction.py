from typing import List, Optional, Tuple

from Telegram import log
from Telegram.modules.users import get_user_id
from telegram import Message, MessageEntity
from telegram.error import BadRequest


def id_from_reply(message):
    prev_message = message.reply_to_message
    if not prev_message:
        return None, None
    user_id = prev_message.from_user.id
    res = message.text.split(None, 1)
    if prev_message.sender_chat:
        user_id = prev_message.sender_chat.id
    if len(res) < 2:
        return user_id, ""
    return user_id, res[1]


def extract_user(message: Message, args: List[str]) -> Optional[int]:
    return extract_user_and_text(message, args)[0]


def extract_user_and_text(
    message: Message, args: List[str]
) -> Tuple[Optional[int], Optional[str]]:
    prev_message = message.reply_to_message
    split_text = message.text.split(None, 1)

    if len(split_text) < 2:
        return id_from_reply(message)  # only option possible

    text_to_parse = split_text[1]

    text = ""

    entities = list(message.parse_entities([MessageEntity.TEXT_MENTION]))
    ent = entities[0] if entities else None
    # if entity offset matches (command end/text start) then all good
    if entities and ent and ent.offset == len(message.text) - len(text_to_parse):
        ent = entities[0]
        user_id = ent.user.id
        text = message.text[ent.offset + ent.length :]

    elif len(args) >= 1 and args[0][0] == "@":
        user = args[0]
        user_id = get_user_id(user)
        if not user_id:
            message.reply_text(
                "Tidak tahu siapa pengguna ini. Anda dapat berinteraksi dengan mereka jika "
                "Anda malah membalas pesan orang itu, atau meneruskan salah satu pesan pengguna itu."            )
            return None, None

        else:
            user_id = user_id
            res = message.text.split(None, 2)
            if len(res) >= 3:
                text = res[2]

    elif len(args) >= 1 and args[0].isdigit():
        user_id = int(args[0])
        res = message.text.split(None, 2)
        if len(res) >= 3:
            text = res[2]

    elif prev_message:
        user_id, text = id_from_reply(message)

    else:
        return None, None

    try:
        message.bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in ("User_id_invalid", "Obrolan tidak ditemukan"):
            message.reply_text(
                "Sepertinya saya belum pernah berinteraksi dengan pengguna ini sebelumnya - teruskan pesan dari "
                "mereka memberi saya kendali! (seperti boneka voodoo, saya butuh bagian dari mereka untuk bisa "
                "untuk menjalankan perintah tertentu...)"
            )
        else:
            log.exception("Pengecualian %s pada pengguna %s", excp.message, user_id)

        return None, None

    return user_id, text


def extract_text(message) -> str:
    return (
        message.text
        or message.caption
        or (message.sticker.emoji if message.sticker else None)
    )


def extract_unt_fedban(
    message: Message, args: List[str]
) -> Tuple[Optional[int], Optional[str]]:  # sourcery no-metrics
    prev_message = message.reply_to_message
    split_text = message.text.split(None, 1)

    if len(split_text) < 2:
        return id_from_reply(message)  # only option possible

    text_to_parse = split_text[1]

    text = ""

    entities = list(message.parse_entities([MessageEntity.TEXT_MENTION]))
    ent = entities[0] if entities else None
    # if entity offset matches (command end/text start) then all good
    if entities and ent and ent.offset == len(message.text) - len(text_to_parse):
        ent = entities[0]
        user_id = ent.user.id
        text = message.text[ent.offset + ent.length :]

    elif len(args) >= 1 and args[0][0] == "@":
        user = args[0]
        user_id = get_user_id(user)
        if not user_id and not isinstance(user_id, int):
            message.reply_text(
                "Saya tidak memiliki pengguna di DB saya. Anda dapat berinteraksi dengan mereka jika "
                "Anda membalas pesan orang tersebut, atau meneruskan salah satu pesan pengguna"
            )
            return None, None

        else:
            user_id = user_id
            res = message.text.split(None, 2)
            if len(res) >= 3:
                text = res[2]

    elif len(args) >= 1 and args[0].isdigit():
        user_id = int(args[0])
        res = message.text.split(None, 2)
        if len(res) >= 3:
            text = res[2]

    elif prev_message:
        user_id, text = id_from_reply(message)

    else:
        return None, None

    try:
        message.bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message in ("User_id_invalid", "Obrolan tidak ditemukan") and not isinstance(
            user_id, int
        ):
            message.reply_text(
                "Sepertinya saya tidak pernah berinteraksi dengan pengguna ini "
                "Sebelumnya - tolong teruskan pesan dari mereka untuk memberi saya kendali!"
                "(Seperti boneka voodoo, aku butuh sepotong untuk bisa"
                "jalankan perintah tertentu ...)"
            )
            return None, None
        elif excp.message != "Obrolan tidak ditemukan":
            log.exception("Pengecualian %s pada pengguna %s", excp.message, user_id)
            return None, None
        elif not isinstance(user_id, int):
            return None, None

    return user_id, text


def extract_user_fban(message: Message, args: List[str]) -> Optional[int]:
    return extract_unt_fedban(message, args)[0]
