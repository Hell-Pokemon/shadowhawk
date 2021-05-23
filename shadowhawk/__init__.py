import os
import html
import time
import logging
import asyncio
import traceback
import functools
import yaml
import aiohttp
from pathlib import Path
from typing import List
from io import BytesIO
from pyee import AsyncIOEventEmitter
from datetime import timedelta
from pyrogram import Client, filters, StopPropagation, ContinuePropagation
from pyrogram.types import Chat, User, Message, InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from pyrogram.parser import parser
from pyrogram.parser.html import HTML as pyrogram_html
from pyrogram.handlers import CallbackQueryHandler, InlineQueryHandler
from pyrogram.methods.chats.get_chat_members import Filters as ChatMemberFilters
from pyrogram.errors.exceptions.bad_request_400 import PeerIdInvalid, ChannelInvalid
from pyrogram.errors.exceptions.flood_420 import FloodWait

# Globals.
loop = asyncio.get_event_loop()
help_dict = dict()
apps = []
app_user_ids = dict()
log_peer_ids = []
statistics = {}
ee = AsyncIOEventEmitter(loop=loop)
DB_AVAILABLE = False
# awaited task load measurements
loads = {
	1: 0.0,  # 1 minute load
	5: 0.0,  # 5 minute load
	15: 0.0, # 15 minute load
	30: 0.0  # 30 minute load
}

# this code here exists because i can't be fucked
class Parser(parser.Parser):
	async def parse(self, text, mode):
		if mode == 'through':
			return text
		return await super().parse(text, mode)

# Dirty hack to get around python's global variable scope copying
# bulllshit. Thanks @TheKneesocks for this code!
class ObjectProxy:
	def __init__(self, thing=None):
		self.thing = thing
	def __getattr__(self, attr):
		return getattr(self.thing, attr)
	def __bool__(self):
		return bool(self.thing)
	def __repr__(self):
		return repr(self.thing)
	def __str__(self):
		return str(self.thing)
	def __iter__(self):
		yield iter(self.thing)
	def __call__(self, *args, **kwargs):
		return self.thing(*args, **kwargs)
	def get_thing(self):
		return self.thing
	def set_thing(self, thing):
		self.thing = thing

#################
# ShadowHawk main
#
with open('config.yaml') as c:
	config = yaml.safe_load(c)

log_ring = asyncio.Queue(maxsize=config['logging']['regular_ring_size'])
spammy_log_ring = asyncio.Queue(maxsize=config['logging']['spammy_ring_size'])

sessions_path = Path("sessions")
sessions_test_path = sessions_path / "test"
sessions_path.mkdir(exist_ok=True)

for session_name in config['config']['sessions']:
	testserver = False
	workdir = str(sessions_path)
	if session_name.startswith("test:"):
		sessions_test_path.mkdir(exist_ok=True)
		session_name = session_name[5:]
		testserver = True
		workdir = str(sessions_test_path)
	app = Client(session_name, api_id=config['telegram']['api_id'], api_hash=config['telegram']['api_hash'], plugins={'root': os.path.join(__package__, 'plugins')}, parse_mode='html', workdir=workdir, test_mode=testserver)
	app.parser = Parser(app)
	apps.append(app)

slave = Client('ShadowHawk-slave', api_id=config['telegram']['api_id'], api_hash=config['telegram']['api_hash'], plugins={'root': os.path.join(__package__, 'slave-plugins')}, parse_mode='html', bot_token=config['telegram']['slave_bot_token'], workdir='sessions')
slave.parser = Parser(slave)
# Http client session for making various HTTP requests
session = aiohttp.ClientSession()
# Get the info on what the server supports
server_support = ObjectProxy()
###############

async def get_entity(client, entity):
	entity_client = client
	if not isinstance(entity, Chat):
		try:
			entity = int(entity)
		except ValueError:
			pass
		except TypeError:
			entity = entity.id
		try:
			entity = await client.get_chat(entity)
		except (PeerIdInvalid, ChannelInvalid):
			for app in apps:
				if app != client:
					try:
						entity = await app.get_chat(entity)
					except (PeerIdInvalid, ChannelInvalid):
						pass
					else:
						entity_client = app
						break
			else:
				entity = await slave.get_chat(entity)
				entity_client = slave
	return entity, entity_client

async def get_user(client, entity):
	entity_client = client
	if not isinstance(entity, User):
		try:
			entity = int(entity)
		except ValueError:
			pass
		except TypeError:
			entity = entity.id
		try:
			entity = await client.get_users(entity)
		except PeerIdInvalid:
			for app in apps:
				if app != client:
					try:
						entity = await app.get_users(entity)
					except PeerIdInvalid:
						pass
					else:
						entity_client = app
						break
			else:
				entity = await slave.get_users(entity)
				entity_client = slave
	return entity, entity_client

async def get_app(id):
	for app in apps:
		me = await app.get_me()
		if me.id == id:
			return app
	return None

async def get_chat_link(client, message):
	if not isinstance(message, Message):
		raise PeerIdInvalid
	
	if message.chat.username:
		return f"https://t.me/{message.chat.username}/{message.message_id}"
	elif getattr(message, 'link', None):
		return message.link
	else:
		# Last resort.
		peer_id = (await client.resolve_peer(message.chat.id)).channel_id
		return f"https://t.me/c/{peer_id}/{message.message_id}"
	return ""

def name_escape(name):
	return "\u200E" + html.escape(name) + "\u200E"

async def log_chat(message, chat="regular"):
	# Append it to the queue
	ee.emit('OnLogRingInsert', message, chat)
	if chat == 'regular':
		await log_ring.put((message, chat))
	else:
		try:
			spammy_log_ring.put_nowait((message, chat))
		except asyncio.QueueFull:
			pass

async def self_destruct(message, text):
	await message.edit(text, disable_web_page_preview=True)
	await asyncio.sleep(3)
	await message.delete()

async def is_admin(client, message, entity):
	# Here lies the sanity checks
	admins = await client.get_chat_members(
		message.chat.id, filter=ChatMemberFilters.ADMINISTRATORS
	)
	admin_ids = [user.user.id for user in admins]
	return entity.id in admin_ids

async def _ParseCommandArguments(client, message):
	""" Parse command arguments in the following order:
		1. If the message is a reply, assume entity_id is the replied to user
		2. Attempt to find the 1st and 2nd argument as a chat and/or user
		3. if none of the above conditions succeed, treat it all as reason text.

		if the chat ID is missing then assume the current chat the message was in.
	"""
	command = message.command
	command.pop(0)
	chat_id = message.chat.id
	entity_id = None
	reason = ""
	reasonstart = 0
	entity0 = entity1 = None

	# Always assume the replied-to message is the intended user
	if not getattr(message.reply_to_message, 'empty', True):
		entity_id = message.reply_to_message.from_user.id

	if len(command) >= 1:
		try:
			entity0, entit0_client = await get_entity(client, command[0])

			if type(entity0) != type(command[0]):
				if entity0.type in ["group", 'supergroup']:
					chat_id = entity0.id
				elif not entity_id:
					entity_id = entity0.id
				reasonstart += 1
		except:
			pass

		# only try to resolve the 2nd argument if we still don't have
		# the entity that we want to perform the action on.
		if len(command) >= 2 and not entity_id:
			try:
				entity1, entity1_client = await get_entity(client, command[1])
				if type(entity1) != type(command[1]):
					if not entity1.type in ["group", "supergroup"] and not entity_id:
						entity_id = entity1.id
						reasonstart += 1
			except:
				pass

	# we've resolved the entity_id and chat_id, lets get the reason.
	if command:
		reason = " ".join(command[reasonstart:])

	# validate we actually have everything resolved
	if not chat_id or not entity_id:
		await message.edit("<code>wtf are you trying to do??</code>")
		await asyncio.sleep(3)
		await message.delete()
		return None

	entity_id, entity_client = await get_entity(client, entity_id)
	chat_id, chat_client = await get_entity(client, chat_id)

	return chat_id, entity_id, reason

async def CheckAdmin(client, message: Message):
	"""Check if we are an admin."""

	# Here lies the sanity checks
	admins = await client.get_chat_members(
		message.chat.id, filter=ChatMemberFilters.ADMINISTRATORS
	)
	admin_ids = [user.user.id for user in admins]
	me = await client.get_me()

	# If you are an admin
	if me.id in admin_ids:
		return True
	return False

	# ranks = ["administrator", "creator"]
	# me = await app.get_chat_member(chat_id=message.chat.id, user_id=message.from_user.id)
	# if me.status not in ranks:
	# 	return False
	# else:
	# 	if me.status != "administrator" or me.can_restrict_members:
	# 		return True
	# return False

def make_file(puke):
	barf = BytesIO(puke.encode('utf-8'))
	barf.name = "traceback.txt"
	return barf

def log_errors(func):
	@functools.wraps(func)
	async def wrapper(client, *args):
		try:
			await func(client, *args)
		except (StopPropagation, ContinuePropagation):
			raise
		except Exception:
			tb = traceback.format_exc()
			is_vomit =  len(tb) >= 4096
			try:
				if is_vomit:
					await slave.send_document(config['logging']['regular'], make_file(tb.strip()), caption=f"Exception occured in <code>{func.__name__}</code>")
				else:
					await slave.send_message(config['logging']['regular'], f'Exception occured in <code>{func.__name__}\n\n{html.escape(tb)}</code>', disable_web_page_preview=True)
			except Exception:
				logging.exception('Failed to log exception for %s as slave', func.__name__)
				tb2 = traceback.format_exc()
				is_vomit_again = len(tb2) >= 4096
				for app in apps:
					try:
						if is_vomit:
							puke_msg = await app.send_document(config['logging']['regular'], make_file(tb.strip()), caption=f"Exception occured in <code>{func.__name__}</code>")
							if is_vomit_again:
								await puke_msg.reply_document(make_file(tb2.strip()), caption=f"Exception occured in the exception handler")
							else:
								await puke_msg.reply(f'Exception occured in exception handler <code>{func.__name__}\n\n{html.escape(tb2)}</code>', disable_web_page_preview=True)
						else:
							puke_msg = await app.send_message(config['logging']['regular'], f'Exception occured in <code>{func.__name__}\n\n{html.escape(tb)}</code>', disable_web_page_preview=True)
							if is_vomit_again:
								await puke_msg.reply_document(make_file(tb2.strip()), caption=f"Exception occured in the exception handler")
							else:
								await puke_msg.reply(f'Exception occured in exception handler <code>{func.__name__}\n\n{html.escape(tb2)}</code>', disable_web_page_preview=True)
					except Exception:
						logging.exception('Failed to log exception for %s as app', func.__name__)
						tb = traceback.format_exc()
					else:
						break
				raise
			raise
	return wrapper

def public_log_errors(func):
	@functools.wraps(func)
	async def wrapper(client, message):
		try:
			await func(client, message)
		except (StopPropagation, ContinuePropagation):
			raise
		except Exception as ex:
			await message.reply_text("<code>" + html.escape(f"{type(ex).__name__}: {str(ex)}") + "</code>", disable_web_page_preview=True)
			raise
	return wrapper

# Active pages we have
paginators = {}
# the lock for this page
page_lock = asyncio.Lock()

@Client.on_callback_query(filters.regex('^generic_nop$'))
@log_errors
async def generic_nop(client, callback_query):
    await callback_query.answer(cache_time=3600)

class Paginator:
	# Our current page
	page = 0
	
	# Scope is the scope of this content
	# content is what is to be paginated (it's an array)
	# Each page is an index into the content array
	def __init__(self, scope: str, title: str, content: List[str]):
		global paginators
		self.scope = scope
		self.content = content
		self.title = title
		# just make time an identifier
		self.identifier = int(time.time())
		# track our paginators
		paginators[self.identifier] = self

	def get_inline_start(self) -> str:
		return f"paginator_{self.scope}-{self.identifier}"

	def get_current_page(self) -> int:
		return self.page

	def get_total_pages(self) -> int:
		return len(self.content)
	
	def get_title(self) -> str:
		return self.title
	
	def next_page(self) -> str:
		self.page += 1
		if self.page > len(self.content):
			self.page = len(self.content)
		return self.get_page()
	
	def prev_page(self) -> str:
		self.page -= 1
		if self.page < 0:
			self.page = 0
		return self.get_page()

	def get_page(self) -> str:
		return self.content[self.page]

# This is sent when the client requests inline
@slave.on_inline_query(filters.regex(r'^paginator_(\w+)-(\d+)$'))
@log_errors
async def pagination_on_inline(client, query):
	global paginators
	try:
		scope = query.matches[0].group(1)
		identifier = int(query.matches[0].group(2))
		answers = []
		page = paginators[identifier]
		parser = pyrogram_html(client)
		text = f"<b>{page.get_title()}</b>\n"
		text += page.get_page()

		for a, result in enumerate(page.content):
			full_snippet = text
			
			# if result:
			# 	full_snippet = snippet = (await parser.parse(result))['message']
			# 	total_length = len((await parser.parse(text))['message'])
			# 	if len(snippet) > 1022 - total_length:
			# 		snippet = snippet[:1021-total_length] + '…'
			# 	text += snippet

			buttons = [
				InlineKeyboardButton('Back', f'paginator_{scope}_prev={query.from_user.id}-{identifier}'), 
				InlineKeyboardButton(f'{page.get_current_page() + 1}/{page.get_total_pages()}', 'generic_nop'),
				InlineKeyboardButton('Next', f'paginator_{scope}_next={query.from_user.id}-{identifier}')
			]

			if not page.get_current_page():
				buttons.pop(0)
			if page.get_total_pages() == page.get_current_page() + 1:
				buttons.pop()
				
			answers.append(InlineQueryResultArticle("Pagination " + scope,
				InputTextMessageContent(text, disable_web_page_preview=True), reply_markup=InlineKeyboardMarkup([buttons]), id=f'paginator{a}-{time.time()}', description=full_snippet)
			)
		await query.answer(answers, is_personal=True)
	except Exception as ex:
		traceback.print_exc()
	raise ContinuePropagation

@slave.on_callback_query(filters.regex(r'^paginator_(\w+)_(\w+)=(\d+)(?:-(\d+)|)$'))
@log_errors
async def paginator_on_callback(client, query):
	global page_lock, paginators
	try:
		scope = query.matches[0].group(1)
		subcmd = query.matches[0].group(2)
		me_id = int(query.matches[0].group(3))
		target = int(query.matches[0].group(4))
		# app = await get_app(me_id)
		# me = app_user_ids[me_id]
		
		if query.from_user.id not in app_user_ids:
			await query.answer('...no', cache_time=3600, show_alert=True)
			raise ContinuePropagation

		async with page_lock:
			if target not in paginators:
				await query.answer('This message is too old', cache_time=3600, show_alert=True)
				raise ContinuePropagation
			
			paginator: Paginator = paginators[target]

		opage = paginator.get_page()
		if subcmd == "next":
			page = paginator.next_page()
		elif subcmd == "prev":
			page = paginator.prev_page()
			
		if opage != page:
			text = f"<b>{paginator.get_title()}</b>\n"
			text += page
			snippet = text
				
			# parser = pyrogram_html(client)
			# snippet = (await parser.parse(page))['message']
			# total_length = len((await parser.parse(text))['message'])
			# if len(snippet) > 1022 - total_length:
			# 	snippet = snippet[:1021-total_length] + '…'
			# text += snippet
			buttons = [
					InlineKeyboardButton('Back', f'paginator_{scope}_prev={query.from_user.id}-{target}'), 
					InlineKeyboardButton(f'{paginator.get_current_page() + 1}/{paginator.get_total_pages()}', 'generic_nop'),
					InlineKeyboardButton('Next', f'paginator_{scope}_next={query.from_user.id}-{target}')
				]
			if not paginator.get_current_page():
				buttons.pop(0)
			if paginator.get_total_pages() == paginator.get_current_page() + 1:
				buttons.pop()
			await query.edit_message_text(text, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([buttons]))
			async with page_lock:
				paginators[target] = paginator
		await query.answer()
	except Exception as ex:
		traceback.print_exc()
	raise ContinuePropagation

# https://stackoverflow.com/a/49361727
def format_bytes(size):
	size = int(size)
	# 2**10 = 1024
	power = 1024
	n = 0
	power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
	while size > power:
		size /= power
		n += 1
	return f"{size:.2f} {power_labels[n]+'B'}"

# https://stackoverflow.com/a/34325723
def return_progress_string(current, total):
	filled_length = int(30 * current // total)
	return '[' + '=' * filled_length + ' ' * (30 - filled_length) + ']'

# https://stackoverflow.com/a/852718
# https://stackoverflow.com/a/775095
def calculate_eta(current, total, start_time):
	if not current:
		return '00:00:00'
	end_time = time.time()
	elapsed_time = end_time - start_time
	seconds = (elapsed_time * (total / current)) - elapsed_time
	thing = ''.join(str(timedelta(seconds=seconds)).split('.')[:-1]).split(', ')
	thing[-1] = thing[-1].rjust(8, '0')
	return ', '.join(thing)

progress_callback_data = dict()
async def progress_callback(current, total, reply, text, upload):
	message_identifier = (reply.chat.id, reply.message_id)
	last_edit_time, prevtext, start_time = progress_callback_data.get(message_identifier, (0, None, time.time()))
	if current == total:
		try:
			progress_callback_data.pop(message_identifier)
		except KeyError:
			pass
	elif (time.time() - last_edit_time) > 1:
		handle = 'Upload' if upload else 'Download'
		if last_edit_time:
			speed = format_bytes((total - current) / (time.time() - start_time))
		else:
			speed = '0 B'
		text = f'''{text}
<code>{return_progress_string(current, total)}</code>

<b>Total Size:</b> {format_bytes(total)}
<b>{handle}ed Size:</b> {format_bytes(current)}
<b>{handle} Speed:</b> {speed}/s
<b>ETA:</b> {calculate_eta(current, total, start_time)}'''
		if prevtext != text:
			await reply.edit_text(text)
			prevtext = text
			last_edit_time = time.time()
			progress_callback_data[message_identifier] = last_edit_time, prevtext, start_time
