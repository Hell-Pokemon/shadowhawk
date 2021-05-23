import time
import asyncio
from collections import deque
from spamprotection import SPBClient
from pyrogram import Client, ContinuePropagation
from pyrogram.errors.exceptions.flood_420 import FloodWait
from pyrogram.raw.types import UpdateNewChannelMessage, UpdateNewMessage, MessageService, PeerChat, PeerChannel, MessageActionChatAddUser, MessageActionChatJoinedByLink, PeerUser
from pyrogram.methods.chats.get_chat_members import Filters as ChatMemberFilters
from .. import config, log_errors, slave, log_chat, database, get_entity, app_user_ids, log_peer_ids, ee, name_escape, get_chat_link
from shadowhawk.database import session

spb = SPBClient()
admincache = {}

async def _get_flags(spbinfo):
    # Check for statuses.
    text = ""
    if spbinfo:

        entity = "user"
        if spbinfo.entity_type == "supergroup":
            entity = "group"
        if spbinfo.entity_type == "supergroup":
            entity = "channel"

        needline = False
        if spbinfo.attributes.intellivoid_accounts_verified:
            text += "\N{WHITE HEAVY CHECK MARK} This user's Telegram account is verified by Intellivoid Accounts\n"
            needline = True
        if spbinfo.attributes.is_official:
            text += f"\N{WHITE HEAVY CHECK MARK} This {entity} is verified by Intellivoid Technologies\n"
            needline = True
        if spbinfo.attributes.is_potential_spammer:
            text += f"\N{warning sign} This {entity} may be an active spammer!\n"
            needline = True
        if spbinfo.attributes.is_blacklisted:
            text += f"\N{warning sign} This {entity} is blacklisted!\n"
            needline = True
        if spbinfo.attributes.is_agent:
            text += "\N{police officer} This user is an agent who actively reports spam automatic\n"
            needline = True
        if spbinfo.attributes.is_operator:
            text += "\N{police officer} This user is an operator who can blacklist users\n"
            needline = True

        if needline:
            text += "\n"
    return text

async def _get_info(spbinfo):
    text = ""
    if spbinfo:
        text += f"<b>Trust Prediction:</b> <code>{spbinfo.spam_prediction.ham_prediction}/{spbinfo.spam_prediction.spam_prediction}</code>\n"
        text += f"<b>Language Prediction:</b> <code>{spbinfo.language_prediction.language}</code> (<code>{spbinfo.language_prediction.probability}</code>)\n"
        if spbinfo.attributes.is_whitelisted:
            text += f"<b>Whitelisted:</b> <code>True</code>\n"
        if spbinfo.attributes.is_operator:
            text += f"<b>Operator:</b> <code>True</code>\n"
        if spbinfo.attributes.is_agent:
            text += f"<b>Spam Detection Agent:</b> <code>True</code>\n"
        if spbinfo.attributes.is_potential_spammer:
            text += f"<b>Active Spammer:</b> <code>True</code>\n"
        if spbinfo.attributes.is_blacklisted:
            text += f"<b>Blacklisted:</b> <code>True</code>\n"
            text += f"<b>Blacklist Reason:</b> <code>{spbinfo.attributes.blacklist_reason}</code>\n"
        if spbinfo.attributes.original_private_id:
            text += f"<b>Original Private ID:</b> <code>{spbinfo.attributes.original_private_id}</code>\n"
    return text

async def do_spb_check(client, user, chat):

	if not config['config']['do_spb_check']:
		return

	try:
		status = await spb.check_blacklist(user.id)
	except: # Just ignore any errors.
		status = type('', (), {})()
		status.success = False
		pass

	if status.success:
		# check if they're blacklisted or an active spammer
		if status.attributes.is_blacklisted or status.attributes.is_potential_spammer:
			# Send a notification to the log chat
			eventtype = "Blacklisted" if status.attributes.is_blacklisted else "Active Spammer"

			# Get the chat we're in.
			atext = name_escape(chat.title)
			if getattr(chat, 'username', None):
				atext = f'<a href="https://t.me/{chat.username}">{atext}</a>'
			ctext = f"{atext} \N{left-to-right mark}[<code>{chat.id}</code>]"

			# Get the user's info
			user_text = user.first_name
			if user.last_name:
				user_text += f' {user.last_name}'
			user_text = '<code>[DELETED]</code>' if user.deleted else name_escape(user_text or 'Empty???')
			if user.verified:
				user_text += ' <code>[VERIFIED]</code>'
			if user.support:
				user_text += ' <code>[SUPPORT]</code>'
			if user.scam:
				user_text += ' <code>[SCAM]</code>'
			if getattr(user, 'is_fake', None):
				user_text += ' <code>[FAKE]</code>'
			user_text += f' [<code>{user.id}</code>]'

			text = f"\N{warning sign} <b>{eventtype} Join Event</b> \N{warning sign}\n\n"
			text += await _get_flags(status)

			attributes = {
				"Private ID": status.private_telegram_id,
				"Chat": ctext,
				"User": user_text,
				"Lang": f"<code>{status.language_prediction.language}</code> (<code>{status.language_prediction.probability}</code>)",
				"Trust": f"{status.spam_prediction.ham_prediction}/{status.spam_prediction.spam_prediction}",
				"Flag": f"<code>{status.attributes.blacklist_flag}</code> (<i>{status.attributes.blacklist_reason}</i>)",
				"Whitelisted": status.attributes.is_whitelisted,
				"Operator": status.attributes.is_operator,
				"Spam Detection Agent": status.attributes.is_agent,
				"Verified": status.attributes.intellivoid_accounts_verified,
				"Active Spammer": status.attributes.is_potential_spammer,
				"Original Private ID": status.attributes.original_private_id,
				"User Link": f"<a href=\"tg://user?id={user.id}\">tg://user?id={user.id}</a>"
			}

			for key, value in attributes.items():
				if not value:
					continue
				if key in ["Lang", "Flag", "User Link"]:
					text += f"<b>{key}:</b> {str(value)}\n"
				else:
					text += f"<b>{key}:</b> <code>{str(value)}</code>\n"
			
			banchat = await database.session.query(database.AutoBanSpammers).get(chat.id)
			msg = None
			if banchat:
				# Don't rape the telegram API for admins, they rarely change anyway.
				if not admincache[chat.id]:
					admincache[chat.id] = await client.get_chat_members(chat.id, filter=ChatMemberFilters.ADMINISTRATORS)

				admins = admincache[chat.id]
				# Get ourselves.
				me = await client.get_me()
				# make sure SPB isn't already in the chat and we're admin.
				if (not 1113787435 in admins) and (me.id in admins):
					text += "<i>\N{shield} Auto Ban: This user was removed from the chat.</i>"
					# Remove the user.
					await client.kick_chat_member(chat.id, user.id)
					# Format an announce message
					if status.attributes.is_potential_spammer:
						announcemsg = f"<a href=\"tg://user?id={user.id}\"></a> has been banned because they might be an active spammer\n\n"
						announcemsg += f"<b>Private Telegram ID:</b> <code>{status.private_telegram_id}</code>\n"
					else:
						announcemsg = f"<a href=\"tg://user?id={user.id}\"></a> has been banned because they've been blacklisted!\n\n"
						announcemsg += f"<b>Private Telegram ID:</b> <code>{status.private_telegram_id}</code>\n"
						announcemsg += f"<b>Blacklist Reason:</b> <code>{status.attributes.blacklist_reason}</code>\n"
					announcemsg += "\n<i>You can find evidence of abuse by searching the Private Telegram ID in @SpamProtectionLogs else If you believe that this is was a mistake then let us know in @SpamProtectionSupport</i>"
					msg = await client.send_message(announcemsg, disable_web_page_preview=True)
			# Send a log message to the log chat
			await log_chat(text)
			if msg:
				await asyncio.sleep(5)
				await msg.delete()

def sexy_user_name(user):
	text = user.first_name
	if user.last_name:
		text += ' ' + user.last_name
	return f'{"<code>[DELETED]</code>" if user.deleted else name_escape(text or "Empty???")} [<code>{user.id}</code>]'

handled = deque(maxlen=50)
lock = asyncio.Lock()
@Client.on_raw_update()
@log_errors
async def log_user_joins(client, update, users, chats):
	if isinstance(update, (UpdateNewChannelMessage, UpdateNewMessage)):
		message = update.message
		if isinstance(message, MessageService):
			action = message.action
			if isinstance(action, (MessageActionChatAddUser, MessageActionChatJoinedByLink)):
				if isinstance(message.peer_id, PeerChannel):
					chat_id = message.peer_id.channel_id
					sexy_chat_id = int('-100' + str(chat_id))
				elif isinstance(message.peer_id, PeerChat):
					chat_id = message.peer_id.chat_id
					sexy_chat_id = -chat_id
				else:
					raise ContinuePropagation

				# Don't log our own adds, it's annoying.
				if not log_peer_ids:
					log_peer_ids.append(await slave.resolve_peer(config['logging']['spammy']))
					log_peer_ids.append(await slave.resolve_peer(config['logging']['regular']))
				if message.peer_id in log_peer_ids:
					raise ContinuePropagation

				# Check if the user was a join or not.
				is_join = isinstance(action, MessageActionChatJoinedByLink)
				if not is_join:
					is_join = action.users == [getattr(message.from_id, 'user_id', None)]

				# user join or user was added?
				text = f"<b>{'User Join Event</b> [#USERJOIN]' if is_join else 'User Add Event</b> [#USERADD]'}\n- <b>Chat:</b> "
				atext = name_escape(chats[chat_id].title)
				if getattr(chats[chat_id], 'username', None):
					atext = f'<a href="https://t.me/{chats[chat_id].username}">{atext}</a>'
				else:
					atext = f'<a href="https://t.me/c/{chat_id}/{message.id}">{atext}</a>'

				text += f"{atext} [<code>{sexy_chat_id}</code>]\n"

				async with lock:
					if (sexy_chat_id, message.id) not in handled:
						spbchecks = set()
						if isinstance(message.from_id, PeerUser):
							adder = sexy_user_name(users[message.from_id.user_id])
							# spbchecks |= set((do_spb_check(client, users[message.from_id.user_id], chats[chat_id]),))
						else:
							adder = 'Anonymous'
						if is_join:
							text += f'- <b>User:</b> {adder}\n'
							ee.emit('OnUserJoin', users[message.from_id.user_id], chats[chat_id])
							if config['logging']['log_join_bios']:
								try:
									entity, ec = await get_entity(client, message.from_id.user_id)
									if entity.bio:
										text += f"- <b>Bio:</b> {entity.bio}\n"
								except:
									pass
							if isinstance(action, MessageActionChatJoinedByLink):
								spbchecks |= set((do_spb_check(client, users[action.inviter_id], chats[chat_id]),))
								text += f'- <b>Inviter:</b> {sexy_user_name(users[action.inviter_id])}'
						else:
							text += f'- <b>Adder:</b> {adder}\n- <b>Added Users:</b>\n'
							
							# Iterate over all the users being added.
							addedlist = []
							for user in action.users:
								text += f'--- {sexy_user_name(users[user])}\n'
								addedlist.append(users[user])
								if config['config']['spb_check_adds']:
									spbchecks |= set((do_spb_check(client, users[user], chats[chat_id]),))
								if users[user].id in app_user_ids:
									await log_chat(text)

							ee.emit('OnAddedUser', users[message.from_id.user_id], chats[chat_id], addedlist, message.id)

						# Call the SPB checks, may take some time.
						await asyncio.gather(*spbchecks)
						# Process all the other stuff.
						while True:
							try:
								# Check the config.
								if is_join and not config['logging']['log_user_joins']:
									raise ContinuePropagation
								if not is_join and not config['logging']['log_user_adds']:
									raise ContinuePropagation
								# Send our message.
								await log_chat(text, 'spammy')
							except FloodWait as ex:
								await asyncio.sleep(ex.x + 1)
							else:
								break
						handled.append((sexy_chat_id, message.id))
						raise ContinuePropagation
	raise ContinuePropagation
