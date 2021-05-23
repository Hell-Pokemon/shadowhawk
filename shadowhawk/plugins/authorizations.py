import html
import time
import asyncio
import humanize
import datetime
import humanize
import dateparser
from zlib import crc32
from typing import List
from statistics import mean
from pyrogram import Client, filters, ContinuePropagation
from pyrogram.raw import functions
from pyrogram.raw.types import UpdateServiceNotification
from shadowhawk import slave, get_app, app_user_ids, get_user, Paginator, config, log_errors, self_destruct, help_dict

# Prevent normal people from dumping their IP address and stuff
# into a public chat
confirmation = {}

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['auths', 'authorizations'], prefixes=config['config']['prefixes']))
@log_errors
async def auth_cmd(client, message):
	tokens = message.command
	thiscmd = tokens.pop(0)

	confirm_id = 0
	if not message.chat.id in app_user_ids:
		if not tokens:
			confirm_id = crc32(int(time.time()).to_bytes(4, "big")) # some random value who cares
			confirmation[confirm_id] = message.chat.id
			warntext = "\N{WARNING SIGN} This command exposes personal information "
			warntext += "(such as IP address, device type, client version, device "
			warntext += "location, and more) and should not be used publicly. If "
			warntext += "you wish to use this command publicly then please run "
			warntext += f"<code>{config['config']['prefixes'][0]}{thiscmd} {confirm_id}</code>"
			await message.reply(warntext)
			return
		else:
			try:
				confirm_id = int(tokens.pop(0))
				if not confirm_id in confirmation:
					raise ValueError
			except ValueError:
				await self_destruct(message, "<code>That is an invalid confirmation ID</code>")
				return
			if message.chat.id != confirmation[confirm_id]:
				await self_destruct(message, "<code>That confirmation ID is for a different chat</code>")
				return
	
	# delete old confirmations
	if confirm_id:
		del confirmation[confirm_id]
	
	# Get our authoriations
	authorizations = await client.send(functions.account.GetAuthorizations())
	# generate the pages
	pages = []

	for a in authorizations.authorizations:
		text = f"<b>Summary:</b> <code>{a.device_model} {a.system_version} ({a.platform})</code>\n"
		text += f"<b>Application:</b> <code>{a.app_name} {a.app_version}{' [OFFICIAL]' if a.official_app else ''}</code>\n"
		text += f"<b>Address:</b> <code>{a.ip} ({a.country})</code>\n"
		text += f"<b>Hash:</b> <code>{a.hash}</code>\n"
		creat = datetime.datetime.fromtimestamp(a.date_created)
		activ = datetime.datetime.fromtimestamp(a.date_active)
		now = datetime.datetime.now()
		cdelta = humanize.naturaldelta(now - creat)
		adelta = humanize.naturaldelta(now - activ)
		text += f"<b>Session Creation:</b> <code>{creat.strftime('%Y-%m-%dT%H:%M:%SZ')} ({cdelta})</code>\n"
		text += f"<b>Session Last Active:</b> <code>{creat.strftime('%Y-%m-%dT%H:%M:%SZ')} ({adelta})</code>\n"
		if a.password_pending:
			text += "\N{CLOSED LOCK WITH KEY}<b>Currently waiting for 2FA password</b>\n"
		if a.current:
			text += "\N{ROBOT FACE}<b>This is the session for this userbot</b>\n"

		pages.append(text)
	
	paginator = Paginator("auths", "Authorizations", pages)
	x = await client.get_inline_bot_results((await slave.get_me()).username, paginator.get_inline_start())
	await client.send_inline_bot_result(message.chat.id, query_id=x.query_id, result_id=x.results[0].id, hide_via=True)

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['deauth', 'deauthorize'], prefixes=config['config']['prefixes']))
@log_errors
async def deauth_cmd(client, message):
	command = message.command
	command.pop(0)

	if not command:
		await self_destruct(message, "<code>Invalid syntax</code>")
		return
	
	try:
		auth_hash = int(command.pop(0))
		# TODO: check if session is 0 and make warning?

		# deauthorize the session
		if await client.send(functions.account.ResetAuthorization(hash=auth_hash)):
			await self_destruct(message, "<code>Success! Session was logged out!</code>")
		else:
			await self_destruct(message, "<code>Failure! Session was not logged out!</code>")
	except ValueError:
		await self_destruct(message, "<code>Invalid session hash</code>")

allow_time = datetime.datetime.now()

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['allowauth', 'allowauthorizations'], prefixes=config['config']['prefixes']))
@log_errors
async def disable_strictauth_cmd(client, message):
	global allow_time
	command = message.command
	command.pop(0)
	if not command:
		await self_destruct(message, "<code>Invalid Syntax</code>")
		return

	if not config['config']['strict_logins']:
		await self_destruct(message, "<code>Strict logins are not enabled.</code>")
		return
	
	allow_time = dateparser.parse(" ".join(command))
	await self_destruct(message, f"<code>Will allow logins for {humanize.naturaldelta(allow_time)}</code>")

# Grab the login message from the official Telegram account
@Client.on_message(filters.chat([777000]) & filters.regex(r'Login code: \d+\. Do not give this code to anyone.*'))
async def handle_login(client, message):
	if not config['config']['strict_logins']:
		return

	# Allow the authentication
	now = datetime.datetime.now()
	if now < allow_time:
		return

	# get whatever client this is
	me = await client.get_me()

	# Begin our message header
	await slave.send_message(me.id, f"The following telegram logins have been terminated for {me.username} ({me.id}) due to strict auth being enabled:")

	# Now get the authorization that is still pending and
	# terminate the session, forcing them to have to try
	# again entirely.
	authorizations = await client.send(functions.account.GetAuthorizations())
	# Iterate it's session information and try to do something with that too I guess
	for a in authorizations.authorizations:
		if a.password_pending and not a.current:
			text = f"<b>Summary:</b> <code>{a.device_model} {a.system_version} ({a.platform})</code>\n"
			text += f"<b>Application:</b> <code>{a.app_name} {a.app_version}{' [OFFICIAL]' if a.official_app else ''}</code>\n"
			text += f"<b>Address:</b> <code>{a.ip} ({a.country})</code>\n"
			text += f"<b>Hash:</b> <code>{a.hash}</code>\n"
			creat = datetime.datetime.fromtimestamp(a.date_created)
			activ = datetime.datetime.fromtimestamp(a.date_active)
			now = datetime.datetime.now()
			cdelta = humanize.naturaldelta(now - creat)
			adelta = humanize.naturaldelta(now - activ)
			text += f"<b>Session Creation:</b> <code>{creat.strftime('%Y-%m-%dT%H:%M:%SZ')} ({cdelta})</code>\n"
			text += f"<b>Session Last Active:</b> <code>{creat.strftime('%Y-%m-%dT%H:%M:%SZ')} ({adelta})</code>\n"
			if a.password_pending:
				text += "\N{CLOSED LOCK WITH KEY}<b>Currently waiting for 2FA password</b>\n"
			if a.current:
				text += "\N{ROBOT FACE}<b>This is the session for this userbot</b>\n"

			# Termiante the session
			await client.send(functions.account.ResetAuthorization(hash=a.hash))
			# Send the message after terminated the session in case the user
			# hasn't started the bot.
			await slave.send_message(me.id, text, disable_web_page_preview=True)

	# By forwarding the message outside of the DM with 777000
	# it will invalidate the login code.
	fwd = await message.forward(config['logging']['regular'])

	# Forward this message to them
	await slave.forward_messages(me.id, fwd.chat.id, fwd.message_id)

	# Then immediately delete the forward
	await fwd.delete()




helptext = '''{prefix}authorizations - List all currently authorized telegram client sessions for this account
Aliases: {prefix}auths

{prefix}deauthorize <i>&lt;session hash&gt;</i> - Deauthorize (log out) a telegram session
Aliases: {prefix}deauth

{prefix}allowauthorizations <i>(relative delta)</i> - Allow new authorizations when in strict-auth mode for a period of time
Aliases: {prefix}allowauth

Relative deltas can be strings like "1d 4h 30m 2s" or even "4 minutes"
'''
help_dict['authorizations'] = ('Authorizations', helptext)
