import html, asyncio, time
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from .. import config, help_dict, get_entity, log_chat, log_errors, CheckAdmin, is_admin, _ParseCommandArguments, self_destruct, public_log_errors

# Mute Permissions
mute_permissions = ChatPermissions(
    can_send_messages=False,
    can_send_media_messages=False,
    can_send_stickers=False,
    can_send_animations=False,
    can_send_games=False,
    can_use_inline_bots=False,
    can_add_web_page_previews=False,
    can_send_polls=False,
    can_change_info=False,
    can_invite_users=False,
    can_pin_messages=False,
)
# Unmute permissions
unmute_permissions = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=True,
    can_send_stickers=True,
    can_send_animations=True,
    can_send_games=True,
    can_use_inline_bots=True,
    can_add_web_page_previews=True,
    can_send_polls=True,
    can_change_info=False,
    can_invite_users=True,
    can_pin_messages=False,
)

# Convenience functions
async def _CheckGroupAndPerms(client, message):
	if not await CheckAdmin(client, message):
		await self_destruct(message, "<code>I am not an admin here lmao. What am I doing?</code>")
		return False

	return True

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['promote'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def promote(client, message):
	if not await _CheckGroupAndPerms(client, message):
		return

	value = await _ParseCommandArguments(client, message)
	if value:
		chat_id, entity_id, reason = value

		if not await client.promote_chat_member(
			chat_id=chat_id.id,
			user_id=entity_id.id,
			is_anonymous=False,
			can_change_info=False,
			can_manage_chat=True,
			can_post_messages=True,
			can_edit_messages=True,
			can_delete_messages=True,
			can_restrict_members=True,
			can_invite_users=True,
			can_pin_messages=True,
			can_promote_members=False,
			can_manage_voice_chats=True
		):
			await self_destruct(message, "<code>I cannot promote that.</code>")
			return

		# log if we successfully promoted someone.
		chat_name = html.escape(chat_id.title)
		if message.chat.username:
			chat_name = f'<a href="https://t.me/{chat_id.username}">{chat_name}</a>'

		chat_text = '<b>Promotion Event</b> [#PROMOTE]\n- <b>Chat:</b> ' + chat_name + '\n- <b>Promoted:</b> '
		user_text = entity_id.first_name
		if entity_id.last_name:
			user_text += f' {entity_id.last_name} <code>[{entity_id.id}]</code>'
		user = user_text = html.escape(user_text or 'Empty???')
		if entity_id.is_verified:
			user_text += ' <code>[VERIFIED]</code>'
		if entity_id.is_support:
			user_text += ' <code>[SUPPORT]</code>'
		if entity_id.is_scam:
			user_text += ' <code>[SCAM]</code>'
		if getattr(message.chat, 'is_fake', None):
			chat_text += ' <code>[FAKE]</code>'
		user_text += f' [<code>{entity_id.id}</code>]'

		if reason and chat_id.type == "supergroup":
			# if they also have a title
			try:
				if not await client.set_administrator_title(
					chat_id=chat_id.id,
					user_id=entity_id.id,
					title=reason
				):
					await message.edit(f'<code>User was promoted but I cannot set their title to "{reason}"</code>')
				else:
					user_text += f"\n<b>Title:</b> <code>{html.escape(reason.strip()[:1000])}</code>"
			except:
				await message.edit(f'<code>User was promoted but I cannot set their title to "{reason}"</code>')
		await message.edit(f'<a href="https://t.me/{entity_id.username}">{user}</a><code> can now reign too!</code>', disable_web_page_preview=True)

		await log_chat(chat_text + user_text)
		await asyncio.sleep(3)
		await message.delete()

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['t', 'title'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def title(client, message):
	if not await _CheckGroupAndPerms(client, message):
		return

	value = await _ParseCommandArguments(client, message)
	if value:
		chat_id, entity_id, reason = value

		if not await client.set_administrator_title(
			chat_id=chat_id.id,
			user_id=entity_id.id,
			title=reason
		):
			await message.edit(f'<code>I cannot set their title to "{reason}"</code>')
		else:
			await message.edit(f'<code>Title set successfully to "{reason}"</code>')
		
		await asyncio.sleep(3)
		await message.delete()
	

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['demote'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def demote(client, message):
	if not await _CheckGroupAndPerms(client, message):
		return

	value = await _ParseCommandArguments(client, message)
	if value:
		chat_id, entity_id, reason = value

		if not await client.promote_chat_member(
			chat_id=chat_id.id,
			user_id=entity_id.id,
			is_anonymous=False,
			can_manage_chat=False,
			can_change_info=False,
			can_post_messages=False,
			can_edit_messages=False,
			can_delete_messages=False,
			can_restrict_members=False,
			can_invite_users=False,
			can_pin_messages=False,
			can_promote_members=False,
			can_manage_voice_chats=False
		):
			await self_destruct(message, "<code>I cannot demote that.</code>")
			return

		# log if we successfully demoted someone.
		chat_name = html.escape(chat_id.title)
		if message.chat.username:
			chat_name = f'<a href="https://t.me/{chat_id.username}">{chat_name}</a>'

		chat_text = '<b>Demotion Event</b> [#DEMOTE]\n- <b>Chat:</b> ' + chat_name + '\n- <b>Demoted:</b> '
		user_text = entity_id.first_name
		if entity_id.last_name:
			user_text += f' {entity_id.last_name} <code>[{entity_id.id}]</code>'
		user = user_text = html.escape(user_text or 'Empty???')
		if entity_id.is_verified:
			user_text += ' <code>[VERIFIED]</code>'
		if entity_id.is_support:
			user_text += ' <code>[SUPPORT]</code>'
		if entity_id.is_scam:
			user_text += ' <code>[SCAM]</code>'
		if getattr(message.chat, 'is_fake', None):
			chat_text += ' <code>[FAKE]</code>'
		user_text += f' [<code>{entity_id.id}</code>]'

		await log_chat(chat_text + user_text)
		await self_destruct(message, f'<a href="https://t.me/{entity_id.username}">{user}</a><code> is no longer king.</code>')

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['m', 'mute'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def mute(client, message):

	if not await _CheckGroupAndPerms(client, message):
		return

	value = await _ParseCommandArguments(client, message)
	if value:
		chat_id, entity_id, reason = value

		if await is_admin(client, message, entity_id):
			await self_destruct(message, "<code>are you okay?</code>")
			return

		if not await client.restrict_chat_member(
			chat_id=chat_id.id,
			user_id=entity_id.id,
			permissions=mute_permissions
		):
			await self_destruct(message, "<code>I cannot mute that.</code>")
			return

		# log if we successfully kicked someone.
		chat_name = html.escape(chat_id.title)
		if message.chat.username:
			chat_name = f'<a href="https://t.me/{chat_id.username}">{chat_name}</a>'

		chat_text = '<b>Mute Event</b> [#USERMUTE]\n- <b>Chat:</b> ' + chat_name + '\n- <b>Muted:</b> '
		user_text = entity_id.first_name
		if entity_id.last_name:
			user_text += f' {entity_id.last_name}'
		user = user_text = html.escape(user_text or 'Empty???')
		if entity_id.is_verified:
			user_text += ' <code>[VERIFIED]</code>'
		if entity_id.is_support:
			user_text += ' <code>[SUPPORT]</code>'
		if entity_id.is_scam:
			user_text += ' <code>[SCAM]</code>'
		if getattr(message.chat, 'is_fake', None):
			chat_text += ' <code>[FAKE]</code>'
		user_text += f' [<code>{entity_id.id}</code>]'
		chat_text += f'{user_text}\n- <b>Reason:</b> {html.escape(reason.strip()[:1000])}'

		await log_chat(chat_text)
		await self_destruct(message, f'<a href="https://t.me/{entity_id.username}">{user}</a><code>\'s enter key was removed.</code>')

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['um', 'unmute'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def unmute(client, message):
	if not await _CheckGroupAndPerms(client, message):
		return

	value = await _ParseCommandArguments(client, message)
	if value:
		chat_id, entity_id, reason = value

		if await is_admin(client, message, entity_id):
			await self_destruct(message, "<code>are you okay?</code>")
			return

		if not await client.restrict_chat_member(
			chat_id=chat_id.id,
			user_id=entity_id.id,
			permissions=unmute_permissions
		):
			await self_destruct(message, "<code>I cannot unmute that.</code>")
			return

		# log if we successfully kicked someone.
		chat_name = html.escape(chat_id.title)
		if message.chat.username:
			chat_name = f'<a href="https://t.me/{chat_id.username}">{chat_name}</a>'

		chat_text = '<b>Unmute Event</b> [#USERUNMUTE]\n- <b>Chat:</b> ' + chat_name + '\n- <b>Muted:</b> '
		user_text = entity_id.first_name
		if entity_id.last_name:
			user_text += f' {entity_id.last_name} <code>[{entity_id.id}]</code>'
		user = user_text = html.escape(user_text or 'Empty???')
		if entity_id.is_verified:
			user_text += ' <code>[VERIFIED]</code>'
		if entity_id.is_support:
			user_text += ' <code>[SUPPORT]</code>'
		if entity_id.is_scam:
			user_text += ' <code>[SCAM]</code>'
		if getattr(message.chat, 'is_fake', None):
			chat_text += ' <code>[FAKE]</code>'
		user_text += f' [<code>{entity_id.id}</code>]'
		chat_text += f'{user_text}\n- <b>Reason:</b> {html.escape(reason.strip()[:1000])}'

		await log_chat(chat_text)
		await self_destruct(message, f'<a href="https://t.me/{entity_id.username}">{user}</a> <code>can now spam.</code>')

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['b', 'ban'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def banhammer(client, message):
	if not await _CheckGroupAndPerms(client, message):
		return

	value = await _ParseCommandArguments(client, message)
	print(value)
	if value:
		chat_id, entity_id, reason = value

		if await is_admin(client, message, entity_id):
			await self_destruct(message, "<code>are you okay?</code>")
			return

		# TODO: timed bans
		await client.kick_chat_member(
			chat_id=chat_id.id,
			user_id=entity_id.id
		)

		# delete our kick command so pajeets don't try and run it themselves
		await message.delete()

		# log if we successfully kicked someone.
		chat_name = html.escape(chat_id.title)
		if message.chat.username:
			chat_name = f'<a href="https://t.me/{chat_id.username}">{chat_name}</a>'

		chat_text = '<b>Userbot Ban Event</b> [#USERBAN]\n- <b>Chat:</b> ' + chat_name + '\n- <b>Ban:</b> '
		user_text = entity_id.first_name
		if entity_id.last_name:
			user_text += f' {entity_id.last_name}'
		user_text = html.escape(user_text or 'Empty???')
		if entity_id.is_verified:
			user_text += ' <code>[VERIFIED]</code>'
		if entity_id.is_support:
			user_text += ' <code>[SUPPORT]</code>'
		if entity_id.is_scam:
			user_text += ' <code>[SCAM]</code>'
		if getattr(message.chat, 'is_fake', None):
			chat_text += ' <code>[FAKE]</code>'
		user_text += f' [<code>{entity_id.id}</code>]'
		chat_text += f'{user_text}\n- <b>Reason:</b> {html.escape(reason.strip()[:1000])}'

		await log_chat(chat_text)

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['ub', 'unban'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def unbanhammer(client, message):
	if not await _CheckGroupAndPerms(client, message):
		return

	value = await _ParseCommandArguments(client, message)
	if value:
		chat_id, entity_id, reason = value

		if await is_admin(client, message, entity_id):
			await self_destruct(message, "<code>are you okay?</code>")
			return

		await client.unban_chat_member(
			chat_id=chat_id.id,
			user_id=entity_id.id
		)

		# delete our kick command so pajeets don't try and run it themselves
		await message.delete()

		# log if we successfully kicked someone.
		chat_name = html.escape(chat_id.title)
		if message.chat.username:
			chat_name = f'<a href="https://t.me/{chat_id.username}">{chat_name}</a>'

		chat_text = '<b>Userbot Unban Event</b> [#USERUNBAN]\n- <b>Chat:</b> ' + chat_name + '\n- <b>Unban:</b> '
		user_text = entity_id.first_name
		if entity_id.last_name:
			user_text += f' {entity_id.last_name}'
		user_text = html.escape(user_text or 'Empty???')
		if entity_id.is_verified:
			user_text += ' <code>[VERIFIED]</code>'
		if entity_id.is_support:
			user_text += ' <code>[SUPPORT]</code>'
		if entity_id.is_scam:
			user_text += ' <code>[SCAM]</code>'
		if getattr(message.chat, 'is_fake', None):
			chat_text += ' <code>[FAKE]</code>'
		user_text += f' [<code>{entity_id.id}</code>]'
		chat_text += f'{user_text}\n- <b>Reason:</b> {html.escape(reason.strip()[:1000])}'

		await log_chat(chat_text)


@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['add'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def add_user(client, message: Message):
	
	value = await _ParseCommandArguments(client, message)
	if value:
		chat_id, entity_id, reason = value

		# TODO: maybe support adding multiple people?
		if await client.add_chat_members(chat_id.id, entity_id.id):
			await message.edit(f"<code>Successfully added to {chat_id.title}</code>")
		else:
			await message.edit(f"<code>Failed to add {entity_id.title} to {chat_id.title}</code>")
		await asyncio.sleep(3)
		await message.delete()

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['k', 'kick'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def kick(client, message):

	if not await _CheckGroupAndPerms(client, message):
		return

	value = await _ParseCommandArguments(client, message)
	if value:
		chat_id, entity_id, reason = value

		if await is_admin(client, message, entity_id):
			await self_destruct(message, "<code>are you okay?</code>")
			return

		await client.kick_chat_member(
			chat_id=chat_id.id,
			user_id=entity_id.id,
		)

		# delete our kick command so pajeets don't try and run it themselves
		await message.delete()

		# Should be enough time to unban since kick == ban apparently
		await client.unban_chat_member(
			chat_id=chat_id.id,
			user_id=entity_id.id
		)

		# log if we successfully kicked someone.
		chat_name = html.escape(chat_id.title)
		if message.chat.username:
			chat_name = f'<a href="https://t.me/{chat_id.username}">{chat_name}</a>'

		chat_text = '<b>Kick Event</b> [#USERKICK]\n- <b>Chat:</b> ' + chat_name + '\n- <b>Kicked:</b> '
		user_text = entity_id.first_name
		if entity_id.last_name:
			user_text += f' {entity_id.last_name}'
		user_text = html.escape(user_text or 'Empty???')
		if entity_id.is_verified:
			user_text += ' <code>[VERIFIED]</code>'
		if entity_id.is_support:
			user_text += ' <code>[SUPPORT]</code>'
		if entity_id.is_scam:
			user_text += ' <code>[SCAM]</code>'
		if getattr(message.chat, 'is_fake', None):
			chat_text += ' <code>[FAKE]</code>'
		user_text += f' [<code>{entity_id.id}</code>]'
		chat_text += f'{user_text}\n- <b>Reason:</b> {html.escape(reason.strip()[:1000])}'

		await log_chat(chat_text)

help_dict['moderation'] = ('Moderation',
'''{prefix}kick <i>[channel id|user id] [user id] [reason]</i> - Removes the user from the chat
Aliases: {prefix}k

{prefix}add <i>(maybe reply to a message)</i> - Adds the user to a chat (either via a reply or in the chat itself)

{prefix}promote <i>[channel id|user id] [user id] [title]</i> - Promotes the user to an administrator

{prefix}demote <i>[channel id|user id] [user id]</i> - Removes the user's administrator permissions

{prefix}title <i>[channel id|user id] [user id] [title]</i> - Sets or removes the title for the user.
Aliases: {prefix}t

{prefix}mute <i>[channel id|user id] [user id]</i> - Prevent the user from sending any messages to the chat
Aliases: {prefix}m

{prefix}unmute <i>[channel id|user id] [user id]</i> - Allow the user to send messages to the chat
Aliases: {prefix}um

{prefix}ban <i>[channel id|user id] [user id]</i> - Remove the user from the chat
Aliases: {prefix}b

{prefix}unban <i>[channel id|user id] [user id]</i> - Allow the user to participate in the chat
Aliases: {prefix}ub
''')
