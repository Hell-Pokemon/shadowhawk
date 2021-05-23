import asyncio
from collections import deque
from pyrogram import Client, filters
from .. import config, slave, log_errors, log_chat, name_escape, get_chat_link

warned = deque(maxlen=50)
lock = asyncio.Lock()

@Client.on_message(~filters.chat(config['logging']['regular']) & filters.regex(r'^[/!](?:[d]*warn?)(?:$|\W+)') & filters.group)
@log_errors
async def log_warn(client, message):
	if not config['logging']['log_warns']:
		return

	# Ignore the slave forwards
	if not getattr(message.forward_from, 'empty', True):
		if message.forward_from.id == (await slave.get_me()).id:
			return

	# Ignore bots, they never report.
	if message.from_user:
		if message.from_user.is_bot:
			return

	identifier = (message.chat.id, message.message_id)
	async with lock:
		if identifier in warned:
			return
		chat_text = name_escape(message.chat.title)
		link = await get_chat_link(client, message)
		chat_text = f'<a href="{link}">{chat_text}</a>'
		text = f'<b>Warn Event</b> [#WARN]\n- <b>Chat:</b> {chat_text} '
		if message.chat.is_verified:
			chat_text += '<code>[VERIFIED]</code> '
		if message.chat.is_support:
			chat_text += '<code>[SUPPORT]</code> '
		if message.chat.is_scam:
			chat_text += '<code>[SCAM]</code> '
		if getattr(message.chat, 'is_fake', None):
			chat_text += ' <code>[FAKE]</code>'
		text += f'[<code>{message.chat.id}</code>]\n- <b>Warner:</b> '
		if message.from_user:
			user_text = message.from_user.first_name
			if message.from_user.last_name:
				user_text += f' {message.from_user.last_name}'
			user_text = '<code>[DELETED]</code>' if message.from_user.is_deleted else name_escape(user_text or 'Empty???')
			if message.from_user.is_verified:
				user_text += ' <code>[VERIFIED]</code>'
			if message.from_user.is_support:
				user_text += ' <code>[SUPPORT]</code>'
			if message.from_user.is_scam:
				user_text += ' <code>[SCAM]</code>'
			if getattr(message.from_user, 'is_fake', None):
				user_text += ' <code>[FAKE]</code>'
			user_text += f' [<code>{message.from_user.id}</code>]'
		elif message.sender_chat and message.sender_chat.id != message.chat.id:
			user_text = name_escape(message.sender_chat.title)
			link = await get_chat_link(client, message)
			user_text = f'<a href="{link}">{user_text}</a>'
			if message.sender_chat.is_verified:
				user_text += ' <code>[VERIFIED]</code>'
			if message.sender_chat.is_support:
				user_text += ' <code>[SUPPORT]</code>'
			if message.sender_chat.is_scam:
				user_text += ' <code>[SCAM]</code>'
			if getattr(message.sender_chat, 'is_fake', None):
				user_text += ' <code>[FAKE]</code>'
		else:
			user_text = 'Anonymous'
		text += f'{user_text}\n'
		start, end = message.matches[0].span()
		text += f'- <b><a href="{message.link}">Warn Message'
		mtext = (message.text or message.caption or '').strip()
		if start or end < len(mtext):
			text += ':'
		text += '</a></b>'
		if start or end < len(mtext):
			text += f' {name_escape(mtext.strip()[:1000])}'
		reply = message.reply_to_message
		if not getattr(reply, 'empty', True):
			text += '\n- <b>Warnee:</b> '
			if reply.from_user:
				user_text = reply.from_user.first_name
				if reply.from_user.last_name:
					user_text += f' {reply.from_user.last_name}'
				user_text = '<code>[DELETED]</code>' if reply.from_user.is_deleted else name_escape(user_text or 'Empty???')
				if reply.from_user.is_verified:
					user_text += ' <code>[VERIFIED]</code>'
				if reply.from_user.is_support:
					user_text += ' <code>[SUPPORT]</code>'
				if reply.from_user.is_scam:
					user_text += ' <code>[SCAM]</code>'
				if getattr(message.from_user, 'is_fake', None):
					user_text += ' <code>[FAKE]</code>'
				user_text += f' [<code>{reply.from_user.id}</code>]'
			else:
				user_text = 'None???'
			text += f'{user_text}\n- <b><a href="{reply.link}">Warned Message'
			mtext = reply.text or reply.caption or ''
			if mtext.strip():
				text += ':'
			text += f'</a></b> {name_escape(mtext.strip()[:1000])}'
			warned.append((reply.chat.id, reply.message_id))
		await log_chat(text)
		warned.append(identifier)
