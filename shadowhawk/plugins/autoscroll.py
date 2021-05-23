import html, asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from sqlalchemy.future import select
from .. import config, help_dict, get_entity, log_chat, log_errors, CheckAdmin, self_destruct, public_log_errors, ee
from ..database import session, AutoScroll

f = filters.chat([])
initted = False

@ee.on('OnDatabaseStart')
async def __init_autoscroll():
    global initted
    if not initted:
        initted = True
        chats = await session.execute(select(AutoScroll))
        for a in chats.scalars():
            f.add(a.id)

@Client.on_message(f)
async def auto_read(client, message):
    await client.read_history(message.chat.id)
    message.continue_propagation()

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['as', 'autoscroll'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def autoscroll(client, message):
    command = message.command
    command.pop(0)
    chat = message.chat.id
    if command:
        chat = command[0]
    
    try:
        chat, entity_client = await get_entity(client, chat)
    except:
        await self_destruct("<code>Invalid chat or group</code>")
        return

    if chat.id in f:
        f.remove(chat.id)
        lel = (await session.execute(select(AutoScroll).where(AutoScroll.id==chat.id)))
        # lel = session.query(AutoScroll).get(chat.id)
        if lel.scalar().one_or_none():
            await session.delete(lel.scalar().one())
        await message.edit(f"<code>Autoscroll disabled in {chat.title}</code>")
    else:
        f.add(chat.id)
        lel = (await session.execute(select(AutoScroll).where(AutoScroll.id==chat.id)))
        # lel = session.query(AutoScroll).get(chat.id)
        if not lel:
            await session.add(AutoScroll(chat.id))
        await message.edit(f"<code>Autoscroll enabled in {chat.title}</code>")
    await session.commit()
    await asyncio.sleep(3)
    await message.delete()

helptext = '''{prefix}autoscroll <i>[channel id]</i> - Automatically mark chat messages as read
Aliases: {prefix}as

'''

if 'misc' in help_dict:
	idk = help_dict['misc']
	help_dict['misc'] = (idk[0], idk[1] + helptext)
else:
	help_dict['misc'] = ('Miscellaneous', helptext)

