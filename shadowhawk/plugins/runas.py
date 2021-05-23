import html
import asyncio
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, public_log_errors, get_app, get_entity, self_destruct

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['rs', 'runas'], prefixes=config['config']['prefixes']))
@log_errors
async def runas(client, message):
	reply = message.reply_to_message
	command = message.command
	command.pop(0)
	user = command[0]
	chat = message.chat.id
	msg = " ".join(command[1:])

	try:
		entity, ec = await get_entity(client, user)
	except:
		entity, ec = (None, None)
	
	if not entity:
		await self_destruct(message, f"unknown user \"{user}\"")
		return
	
	try:
		app = await get_app(entity.id)
	except:
		app = None
	
	if not app:
		await self_destruct(message, f"{user} is not a user that shadowhawk is logged into.")
		return
	
	await message.delete()

	if reply:
		await app.send_message(chat, msg, reply_to_message_id=reply.message_id)
	else:
		await app.send_message(chat, msg)

yeetpurge_info = {True: dict(), False: dict()}
yeetpurge_lock = asyncio.Lock()
@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['multirun', 'mr'], prefixes=config['config']['prefixes']))
@log_errors
async def multirun(client, message):
	reply = message.reply_to_message
	if getattr(reply, 'empty', True):
		await message.delete()
		return

	info = yeetpurge_info[False]
	async with yeetpurge_lock:
		if message.from_user.id not in info:
			info[message.from_user.id] = dict()
		info = info[message.from_user.id]
		if message.chat.id not in info:
			resp = await message.reply_text('Reply to end destination')
			info[message.chat.id] = (message, reply, resp)
			return
		og_message, og_reply, og_resp = info.pop(message.chat.id)

	deletion = set((og_message.message_id, message.message_id, og_resp.message_id))
	messages = set()
	from_id, to_id = sorted((og_reply.message_id, reply.message_id))
	async for i in client.iter_history(message.chat.id, offset_id=to_id):
		if not i.outgoing:
			messages.add(i.message_id)
		if from_id >= i.message_id:
			break
	command = " ".join(message.command[1:])
	tasks = set()
	for m in messages:
		tasks |= set((client.send_message(message.chat.id, command, reply_to_message_id=m),))
	tasks |= set((client.delete_messages(message.chat.id, deletion),))
	asyncio.gather(*tasks)


helptext = '''{prefix}multirun <i>(maybe reply to a message)</i> - replies to messages between messages (useful for running many commands at once)
Aliases: {prefix}mr

{prefix}runas <i>username</i> <i>(maybe reply to a message)</i> - Run the command as another account
Aliases: {prefix}rs

'''
if 'misc' in help_dict:
	idk = help_dict['misc']
	help_dict['misc'] = (idk[0], idk[1] + helptext)
else:
	help_dict['misc'] = ('Miscellaneous', helptext)