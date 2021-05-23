import html
import time
import asyncio
import humanize
import datetime
from statistics import mean
from pyrogram import Client, filters, ContinuePropagation
from pyrogram.types import Dialog, Chat, Message
from pyrogram.raw import functions
from shadowhawk import ObjectProxy as SessionProxy
from shadowhawk import (
	config,
	help_dict,
	log_errors,
	public_log_errors,
	get_app,
	get_entity,
	self_destruct,
	statistics,
	log_ring,
	spammy_log_ring,
	app_user_ids,
	loads,
	apps,
	statistics,
	ee
)

# Adapted from https://gitlab.com/Dank-del/EnterpriseALRobot/-/blob/master/tg_bot/modules/dev.py#L57
class Store:
    def __init__(self, func):
        self.func = func
        self.calls = []
        self.time = time.time()
        self.lock = asyncio.Lock()

    def average(self):
        return round(mean(self.calls), 2) if self.calls else 0

    def __repr__(self):
        return f"<Store func={self.func.__name__}, average={self.average()}>"

    async def __call__(self, event):
        async with self.lock:
            if not self.calls:
                self.calls = [0]
            if time.time() - self.time > 1:
                self.time = time.time()
                self.calls.append(1)
            else:
                self.calls[-1] += 1
        await self.func(event)

async def nothing(*args, **kwargs):
    pass

user_joins = Store(nothing)
user_adds = Store(nothing)
messages = Store(nothing)
updates = Store(nothing)


@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['stats'], prefixes=config['config']['prefixes']))
@log_errors
async def stats(client, message):
	reply = await message.reply("Generating statistics, please wait...")
	# Start with the header
	text = "<b>ShadowHawk Statistics</b>\n"

	# Show total logged in accounts plus the one for the slave
	text += f" - Total Accounts: <code>{len(app_user_ids.keys()) + 1}</code>\n"
	# General statistics
	text += f" - Avg. User Joins: <code>{user_joins.average()}/s</code>\n"
	text += f" - Avg. User Adds: <code>{user_adds.average()}/s</code>\n"
	text += f" - Avg. Messages: <code>{messages.average()}/s</code>\n"
	text += f" - Avg. Updates: <code>{updates.average()}/s</code>\n"
	# Statistics from ShadowHawk
	text += f" - Task Avg: <code>{loads[1]:.2f}, {loads[5]:.2f}, {loads[15]:.2f}, {loads[30]:.2f}</code>\n"
	text += f" - Log Ring: <code>{log_ring.qsize()}/{log_ring.maxsize}</code>\n"
	text += f" - Spammy Ring: <code>{spammy_log_ring.qsize()}/{spammy_log_ring.maxsize}</code>\n"
	text += f" - Logs Sent: <code>{statistics['Logs Sent']}</code>\n"
	delta = datetime.datetime.now() - statistics['start']
	text += f" - Uptime: <code>{humanize.precisedelta(delta)}</code>\n\n"

	await reply.edit(f"Getting statistics from modules...")
	# Announce for the modules to append information, getting dialog stats
	# will take some time so hopefully we can use that to wait for modules
	updateproxy = SessionProxy("")
	ee.emit("OnStatistics", updateproxy)
	# Give modules a minimum of 5 seconds to generate their stats.
	await asyncio.sleep(5)

	# Get total chats, channels, and DMs we have in each account
	for a in apps:
		chats = channels = private = bots = unknown = 0
		unread_msg_cnt = unread_mentions = 0
		me = await a.get_me()
		name = ""
		if me.first_name:
			name += me.first_name
		if me.last_name:
			name += " " + me.last_name
		if me.username:
			name += f" ({me.username})"
		await reply.edit(f"Getting statistics for {name}...")

		# Iterate the chats
		async for dialog in a.iter_dialogs():
			chat = dialog.chat
			unread_msg_cnt += dialog.unread_messages_count
			unread_mentions += dialog.unread_mentions_count
			if chat.type == "supergroup" or chat.type == "group":
				chats += 1
			elif chat.type == "channel":
				channels += 1
			elif chat.type == "private":
				private += 1
			elif chat.type == "bot":
				bots += 1
			else:
				unknown += 1

		# Get the blocked user count
		blocked = await a.send(functions.contacts.GetBlocked(offset=0, limit=1))
		# Get how many devices are logged in
		sessions = await a.send(functions.account.GetAuthorizations())
		
		text += f"<b>{name} Statistics</b>\n"
		text += f" - Authorized Sessions: <code>{len(sessions.authorizations)}</code>\n"
		text += f" - Total Contacts: <code>{await a.get_contacts_count()}</code>\n"
		text += f" - Blocked Accounts: <code>{blocked.count}</code>\n"
		text += f" - Unread Messages: <code>{unread_msg_cnt}</code>\n"
		text += f" - Unread Mentions: <code>{unread_mentions}</code>\n"
		text += f" - Total Private Chats: <code>{private}</code>\n"
		text += f" - Total Groups: <code>{chats}</code>\n"
		text += f" - Total Channels: <code>{channels}</code>\n"
		text += f" - Total Bots: <code>{bots}</code>\n"
		text += f" - Total Unknown: <code>{unknown}</code>\n\n"
	
	text += updateproxy.get_thing()

	# Send the statistics message
	await reply.edit(text, disable_web_page_preview=True)

# Used to track statistics on messages and stuff
@Client.on_raw_update()
async def update_stats(*args, **kwargs):
	# Update the update count
	await updates("")
	# Ensure we still update other events
	raise ContinuePropagation

@Client.on_message()
async def message_stats(*args, **kwargs):
	await messages("")
	raise ContinuePropagation

@ee.on('OnUserJoin')
async def join_stats(*args, **kwargs):
	await user_joins("")

@ee.on('OnAddedUser')
async def add_stats(*args, **kwargs):
	await user_adds("")

helptext = '''{prefix}stats - Get some statistics

'''
if 'misc' in help_dict:
	idk = help_dict['misc']
	help_dict['misc'] = (idk[0], idk[1] + helptext)
else:
	help_dict['misc'] = ('Miscellaneous', helptext)
