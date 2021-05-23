import re
import asyncio
import random

# Kanged from:
# https://github.com/pokurt/Nana-Remix/blob/master/nana/modules/pm.py
# https://github.com/pokurt/Nana-Remix/blob/master/nana/assistant/inline.py#L239

from pyrogram import Client, filters
from pyrogram.raw import functions
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from .. import (
	config,
	slave,
	help_dict,
	log_errors,
	get_entity,
	get_user,
	get_app,
	_ParseCommandArguments,
	public_log_errors,
	app_user_ids,
	self_destruct
)
from shadowhawk.database.pmpermit import get_authorized, AuthorizedUsers
from sqlalchemy.future import select
from shadowhawk.database import session

welc_txt = """
<b>\N{WARNING SIGN} [AUTOMATED] \N{WARNING SIGN}</b>
Hello! I do not accept private messages (PMs/DMs) from
unknown people. Please do not continue messaging me
until my response as you will be blocked automatically.

<b>SPAMMING WILL GET YOU BLOCKED + REPORTED</b>

Please use one of the buttons below to try contacting me
"""

spam_warn = """
<b>\N{WARNING SIGN} [AUTOMATED] \N{WARNING SIGN}</b>
Continuing to send messages will get you <b>BLOCKED + REPORTED!</b>

This is your final warning!
"""

BLACKLIST = ["hack", "fuck", "bitch", "pubg", "sex", "asshole", "madarchod"
"\N{REVERSED HAND WITH MIDDLE FINGER EXTENDED}",
"dick", "cunt", "bhenchod", "kuttiya", "chutiya", "bhosadike",
"chod", "gaand", "lund", "lauda", "tatti", "kamina", "chunni",
"bhen", "chhed", "chut", "vagina", "titty", "ass"]

lock = asyncio.Lock()

DEBUG = False

async def special_user(user):
	return user.is_verified or user.is_support or user.is_contact

# Based on code from here:
# https://github.com/ColinTheShark/Pyrogram-Snippets/blob/master/Snippets/block_new_pm.py
async def spamreport(client, userid):
	if DEBUG:
		return
	try:
		peer = await client.resolve_peer(userid)
		# report as spam
		await client.send(functions.messages.ReportSpam(peer=peer))
	except KeyError:
		pass

def _make_sexy(user):
	username = user.first_name
	if getattr(user, 'username', None):
		username = f'<a href="https://t.me/{user.username}">{username}</a>'
	else:
		username = f'<a href="tg://user?id={user.id}">{username}</a>'
	return username

@slave.on_inline_query(filters.regex('^engine_pm-(\d+)$'))
@log_errors
async def main_help(client, inline_query):
	# Context: We're the bot, one of the apps messaged us
	user = int(inline_query.matches[0].group(1))
	async with lock:
		auth = await get_authorized(user)
		if not auth:
			await session.rollback()
			raise ValueError("PM Permit: What.")
		if auth.requested:
			button = [[InlineKeyboardButton("I'd like to discuss Binances", callback_data=f"engine_pm_block={inline_query.from_user.id}")]]
		else:
			button = [
				[InlineKeyboardButton("I'd like to discuss Binances", callback_data=f"engine_pm_block={inline_query.from_user.id}"),
				InlineKeyboardButton("Contact me", callback_data=f"engine_pm_nope={inline_query.from_user.id}")],
			]
			random.shuffle(button)

	answers = [InlineQueryResultArticle(
		title="Engine pm",
		description="Filter pm",
		input_message_content=InputTextMessageContent(welc_txt, parse_mode="html"),
		reply_markup=InlineKeyboardMarkup(button))]
	
	await client.answer_inline_query(inline_query.id, results=answers, cache_time=0)

@Client.on_message(~filters.me & filters.private & ~filters.bot)
@log_errors
async def pm_block(client, message):
	if not config['config']['pmpermit']['enabled']:
		return

	if not DEBUG and await special_user(message.from_user):
		return

	async with lock:
		auth = await get_authorized(message.from_user.id)
		if not auth:
			auth = AuthorizedUsers(message.from_user.id, False, False, False)
			session.add(auth)
	
	if not auth.approved:
		await client.read_history(message.chat.id)
		if message.text:
			for x in message.text.lower().split():
				if x in BLACKLIST:
					await message.reply("I don't accept DMs from people who are insulting. Blocked.")
					if not DEBUG:
						await client.block_user(message.chat.id)
						#await spamreport(client, message.from_user.id)
					async with lock:
						if auth.warned:
							session.delete(auth)
							await session.commit()
						else:
							await session.rollback()
					return
		# Check their retard level.
		auth.retardlevel += 1
		if auth.retardlevel == int(config['config']['pmpermit']['warnretard']):
			await client.send_message(message.chat.id, spam_warn)
		if auth.retardlevel >= int(config['config']['pmpermit']['maxretard']):
			await client.send_message(message.chat.id, "<code>Automatically blocked and reported for spam! Bye!!</code>")
			async with lock:
				if auth.warned:
					session.delete(auth)
					await session.commit()
				else:
					await session.rollback()
			if not DEBUG:
				await client.block_user(message.from_user.id)
				await spamreport(client, message.from_user.id)
			return

		if not auth.warned:
			auth.warned = True
			async with lock:
				await session.commit()
			x = await client.get_inline_bot_results((await slave.get_me()).username, f"engine_pm-{message.chat.id}")
			await client.send_inline_bot_result(message.chat.id, query_id=x.query_id, result_id=x.results[0].id, hide_via=True)
	async with lock:
		await session.commit()


@Client.on_message(filters.me & filters.command("approve", prefixes=config['config']['prefixes']))
@log_errors
async def approve_pm(client, message):
	command = message.command
	command.pop(0)
	async with lock:
		if message.chat.type == 'private':
			rart = await get_authorized(message.chat.id)
			if rart:
				rart.approved = True
			else:
				rart = AuthorizedUsers(message.from_user.id, True, False, False)
				session.add(rart)
			await session.commit()
			await self_destruct(message, "<code>PM permission was approved!</code>")
		elif command:
				for user in command:
					# Resolve the user
					try:
						user, uclient = await get_entity(client, user)
					except:
						await message.edit(f"<code>Could not approve {user}</code>")
						continue

					if user.type != "private":
						await message.edit(f"<code>This is not a user: {user.title}</code>")
						continue
					
					rart = await get_authorized(user.id)
					if not rart:
						rart = AuthorizedUsers(user.id, True, False, False)
						session.add(rart)
						await message.edit("<code>PM permission was approved!</code>")
				await session.commit()
				await asyncio.sleep(3)
				await message.delete()
		else:
			if message.reply_to_message:
				rart = await get_authorized(message.reply_to_message.from_user.id)
				if rart:
					rart.approved = True
				else:
					rart = AuthorizedUsers(message.from_user.id, True, False, False)
					session.add(rart)
				await session.commit()
				await self_destruct(message, "<code>PM permission was approved!</code>")
			else:
				await self_destruct(message, "<code>Who am I to approve?</code>")
	


@Client.on_message(filters.me & filters.command(["revoke", "disapprove", "unapprove"], prefixes=config['config']['prefixes']))
@log_errors
async def revoke_pm_block(client, message):
	command = message.command
	command.pop(0)
	async with lock:
		if message.chat.type == 'private':
			rart = await get_authorized(message.chat.id)
			if rart:
				session.delete(rart)
				await session.commit()
		elif command:
				for user in command:
					# Resolve the user
					try:
						user, uclient = await get_entity(client, user)
					except:
						continue

					if user.type != "private":
						continue
					
					rart = await get_authorized(user.id)
					if rart:
						session.delete(rart)
				await session.commit()
		else:
			if message.reply_to_message:
				rart = await get_authorized(message.reply_to_message.from_user.id)
				if rart:
					session.delete(rart)
					await session.commit()
			else:
				message.delete()
				return
	await self_destruct(message, "<code>PM permission was revoked!</code>")

@slave.on_callback_query(filters.regex('^engine_pm_(\w+)=(\d+)(?:-(\d+)|)$'))
@log_errors
async def pm_button(client, query):
	# Context: We're the bot, someone clicked a button (either the DMing user or app)
	if not config['config']['pmpermit']['enabled']:
		return
	
	subcommand = query.matches[0].group(1)
	app = await get_app(int(query.matches[0].group(2)))

	if query.from_user.id in app_user_ids and subcommand not in ["apr", "blk", "rpt", "blk_rpt"]:
		await client.answer_callback_query(query.id, "That's for them, not you.", show_alert=False)
		return

	async with lock:
		auth = await get_authorized(query.from_user.id)

	if subcommand == "block":
		await slave.edit_inline_text(query.inline_message_id, "Great! Bye!")
		if not DEBUG:
			await app.block_user(query.from_user.id)
	elif subcommand == "nope":
		me = await app.get_me()
		await slave.edit_inline_text(query.inline_message_id, "Thanks for contacting me, please wait for my response!")
		buttons = InlineKeyboardMarkup([[InlineKeyboardButton("Block + Report",
															callback_data=f"engine_pm_blk_rpt={me.id}-{query.from_user.id}")],
										[InlineKeyboardButton("Approve",
															callback_data=f"engine_pm_apr={me.id}-{query.from_user.id}"),
										InlineKeyboardButton("Block",
															callback_data=f"engine_pm_blk={me.id}-{query.from_user.id}")]])

		pm_bot_message = f'<b>PM Event</b> [#PMREQUEST]\n{_make_sexy(query.from_user)} wants to contact {_make_sexy(me)}'
		await slave.send_message(config['logging']['regular'], pm_bot_message, reply_markup=buttons)
		auth.requested = True
		async with lock:
			await session.commit()
	elif subcommand == "apr":
		target = int(query.matches[0].group(3))
		user, client = await get_user(client, target)
		await query.message.edit_text(f"<b>PM Event</b> [#PMREQUEST]\n{_make_sexy(user)} has been approved for PM.")
		await app.send_message(target, "<code>Approved.</code>")
		async with lock:
			auth = await get_authorized(target)
			auth.approved = True
			await session.commit()
	elif subcommand == "blk":
		target = int(query.matches[0].group(3))
		async with lock:
			auth = await get_authorized(target)
			if auth:
				session.delete(auth)
				await session.commit()
		await query.message.edit_text(f"<b>PM Event</b> [#PMREQUEST]\n{_make_sexy(user)} blocked.")
		await app.send_message(target, "<code>You have been blocked.</code>")
		if not DEBUG:
			await app.block_user(target)
	elif subcommand == "blk_rpt":
		target = int(query.matches[0].group(3))
		async with lock:
			auth = await get_authorized(target)
			if auth:
				session.delete(auth)
				await session.commit()
		await query.message.edit_text(f"<b>PM Event</b> [#PMREQUEST]\n{_make_sexy(user)} blocked and reported.")
		await app.send_message(target, "<code>You have been blocked and reported as spam.</code>")
		if not DEBUG:
			await spamreport(app, target)
			await app.block_user(target)
	else:
		await slave.edit_inline_text(query.inline_message_id, "\‍N{FACE WITH OK GESTURE}")