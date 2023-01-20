import os

from telethon import Button, events
from Telegram import telethn as Zaid
from Telegram.helpers.queues import get_active_chats


@Zaid.on(events.NewMessage(pattern="^/activevoice"))
async def activevc(message):
    mystic = await message.reply(
        "Mendapatkan obrolan suara aktif.. Harap tunggu"
    )
    served_chats = await get_active_chats()
    text = ""
    j = 0
    for x in served_chats:
        try:
            title = (await message.client.get_entity(x)).title
        except Exception:
            title = "Private Group"
        if (await message.client.get_entity(x)).username:
            user = (await message.client.get_entity(x)).username
            text += f"{j + 1}.  [{title}](https://t.me/{user})[`{x}`]\n"
        else:
            text += f"{j + 1}. {title} [`{x}`]\n"
        j += 1
    if not text:
        await mystic.edit("Tidak Ada Obrolan Suara Aktif")
    else:
        await mystic.edit(
            f"**Obrolan Suara Aktif:-**\n\n{text}"
        )
