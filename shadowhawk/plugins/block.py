import html, asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from .. import config, help_dict, log_errors, get_entity, log_chat, public_log_errors

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['block'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def block(client, message):
	entity = message.chat
	command = message.command
	command.pop(0)
	if command:
		entity = ' '.join(command)
	elif not getattr(message.reply_to_message, 'empty', True):
		entity = message.reply_to_message.from_user or message.reply_to_message.chat
	entity, entity_client = await get_entity(client, entity)

	if not command and entity.type != "private":
		await message.edit(f"<code>I can't block {entity.title} because it's not a private chat you retard</code>")
		await asyncio.sleep(3)
		await message.delete()
		return

	try:
		if await client.block_user(entity.id):
			user_text = entity.first_name
			if entity.last_name:
				user_text += f' {entity.last_name}'
			user_text = html.escape(user_text or 'Empty???')
			user_text += f' <code>[{entity.id}]</code>'
			await log_chat("<b>User Block Event</b> [#BLOCKED]\n- <b>User:</b> " + user_text)
		else:
			await message.edit(f"<code>I cannot block {entity.title}</code>")
			await asyncio.sleep(3)
	except:
		await message.edit(f"<code>I cannot block {entity.title}</code>")
		await asyncio.sleep(3)

	await message.delete()

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['unblock'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def unblock(client, message):
	entity = message.chat
	command = message.command
	command.pop(0)
	if command:
		entity = ' '.join(command)
	elif not getattr(message.reply_to_message, 'empty', True):
		entity = message.reply_to_message.from_user or message.reply_to_message.chat
	entity, entity_client = await get_entity(client, entity)

	if not command and entity.type != "private":
		await message.edit(f"<code>I can't unblock {entity.title} because it's not a private chat you retard</code>")
		await asyncio.sleep(3)
		await message.delete()
		return

	try:
		if await client.unblock_user(entity.id):
			user_text = entity.first_name
			if entity.last_name:
				user_text += f' {entity.last_name}'
			user_text = html.escape(user_text or 'Empty???')
			user_text += f' <code>[{entity.id}]</code>'
			await log_chat("<b>User Unblock Event</b> [#UNBLOCK]\n- <b>User:</b> " + user_text)
		else:
			await message.edit(f"<code>I cannot unblock {entity.title}</code>")
			await asyncio.sleep(3)
	except:
		await message.edit(f"<code>I cannot unblock {entity.title}</code>")
		await asyncio.sleep(3)
	await message.delete()

help_dict['block'] = ('Block',
'''{prefix}block <i>[user id]</i> - Blocks the user either by reply or by id

{prefix}unblock <i>[user id]</i> - Unblocks the user either by reply or by id
''')