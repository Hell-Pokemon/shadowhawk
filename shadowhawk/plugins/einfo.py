import re
import html
import time
import asyncio
import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from pyrogram.parser.html import HTML as pyrogram_html
from .. import config, help_dict, get_entity, session, log_errors, public_log_errors, slave, get_user, get_entity, get_app, app_user_ids

conversation_hack = dict()

DEAI_BAN_CODES = {
    "00": "Gban",
    "01": "Joinspam",
    "02": "Spambot",
    "03": "Generic spam",
    "04": "Scam",
    "05": "Illegal",
    "06": "Pornography",
    "07": "Nonsense",
    "08": "Chain bans",
    "09": "Special",
    "10": "Preemptive",
    "11": "Copyright",
    "12": "Admin rights abuse",
    "13": "Toxicity",
    "14": "Flood",
    "15": "Detected but not classified",
    "16": "Advanced detection",
    "17": "Reported",
    "18": "AI association",
    "19": "Impersonation",
    "20": "Malware",
    "21": "Ban evasion",
    "22": "PM spam",
    "23": "Spam adding members",
    "24": "RESERVED (debug)",
    "25": "RESERVED",
    "26": "Raid initiation",
    "27": "Raid participation",
    "28": "Kriminalamt"
}
DEAI_MODULE_CODES = {
    "0": "Gban",
    "1": "Database parser",
    "2": "Realtime",
    "3": "Profiler",
    "4": "Scraper",
    "5": "Association analytics",
    "6": "Codename Autobahn",
    "7": "Codename Polizei",
    "8": "Codename Gestapo"
}

# Dictionary of our recent CAS queries.
cas_queries = dict()

message_lock = asyncio.Lock()

@slave.on_inline_query(filters.regex('^engine_cas-(\d+)$'))
@log_errors
async def combot_start(client, inline_query):
	async with message_lock:
		user = inline_query.matches[0].group(1)
		try:
			u, uc = await get_user(client, user)
			text = f'CAS messages for: <a href="https://cas.chat/query?u={u.id}">{u.first_name}</a>\n\n'
		except:
			text = f'CAS messages for: <a href="https://cas.chat/query?u={user}">{user}</a>\n\n'
		answers = []
		results, page  = cas_queries[user]
		results = results['result']['messages']
		parser = pyrogram_html(client)
		for a, result in enumerate(results):
			full_snippet = None
			
			if result:
				full_snippet = snippet = (await parser.parse(result))['message']
				total_length = len((await parser.parse(text))['message'])
				if len(snippet) > 1022 - total_length:
					snippet = snippet[:1021-total_length] + '…'
				text += snippet
			buttons = [
				InlineKeyboardButton('Back', f'engine_cas_prev={inline_query.from_user.id}-{user}'), 
				InlineKeyboardButton(f'{a + 1}/{len(results)}', 'wikipedia_nop'),
				InlineKeyboardButton('Next', f'engine_cas_next={inline_query.from_user.id}-{user}')
			]
			if not a:
				buttons.pop(0)
			if len(results) == a + 1:
				buttons.pop()
			answers.append(InlineQueryResultArticle("Engine CAS", 
				InputTextMessageContent(text, disable_web_page_preview=True), reply_markup=InlineKeyboardMarkup([buttons]), id=f'cas{a}-{time.time()}', description=full_snippet)
			)
		await inline_query.answer(answers, is_personal=True)

@slave.on_callback_query(filters.regex('^engine_cas_(\w+)=(\d+)(?:-(\d+)|)$'))
@log_errors
async def combot_info(client, query):

	subcommand = query.matches[0].group(1)
	app = await get_app(int(query.matches[0].group(2)))
	me = await app.get_me()
	target = query.matches[0].group(3)
	
	if query.from_user.id not in app_user_ids:
		await query.answer('...no', cache_time=3600, show_alert=True)
		return
		
	user, client = await get_user(client, target)
	
	async with message_lock:
		if target not in cas_queries:
			await query.answer('This message is too old', cache_time=3600, show_alert=True)
			return
	async with message_lock:
		origquery, page  = cas_queries[target]
	results = origquery['result']['messages']
	opage = page
	if subcommand == "next":
		page += 1
	if subcommand == "prev":
		page -= 1
	
	if page > len(results):
		page = len(results)
	if page < 0:
		page = 0
		
	if opage != page:
		try:
			text = f'CAS messages for: <a href="https://cas.chat/query?u={user.id}">{user.first_name}</a>\n\n'
		except:
			text = f'CAS messages for: <a href="https://cas.chat/query?u={target}">{target}</a>\n\n'
			
			
		result = results[page]
		if result:
			parser = pyrogram_html(client)
			snippet = (await parser.parse(result))['message']
			total_length = len((await parser.parse(text))['message'])
			if len(snippet) > 1022 - total_length:
				snippet = snippet[:1021-total_length] + '…'
			text += snippet
		buttons = [
				InlineKeyboardButton('Back', f'engine_cas_prev={query.from_user.id}-{target}'), 
				InlineKeyboardButton(f'{page + 1}/{len(results)}', 'wikipedia_nop'),
				InlineKeyboardButton('Next', f'engine_cas_next={query.from_user.id}-{target}')
			]
		if not page:
			buttons.pop(0)
		if len(results) == page + 1:
			buttons.pop()
		await query.edit_message_text(text, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([buttons]))
		async with message_lock:
			cas_queries[target] = origquery, page
	await query.answer()
	

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['cas', 'combot'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def combotinfo(client, message):
	entity = message.from_user
	args = message.command
	command = args.pop(0).lower()
	me = await client.get_me()

	if args:
		entity = ' '.join(args)
	elif not getattr(message.reply_to_message, 'empty', True):
		entity = message.reply_to_message.from_user or entity
	if isinstance(entity, str) and (not entity.isnumeric() and not entity.startswith('TEL-')):
		entity, entity_client = await get_entity(client, entity)
	if not isinstance(entity, str):
		entity = str(entity.id)
	
	# Perform our async request first
	async with session.get('https://api.cas.chat/check', params={"user_id": entity}) as resp:
		async with message_lock:
			# we always start on page 1.
			cas_queries[entity] = await resp.json(), 0

	# Get the inline results from the function above
	x = await client.get_inline_bot_results((await slave.get_me()).username, f"engine_cas-{entity}")
	await client.send_inline_bot_result(message.chat.id, query_id=x.query_id, result_id=x.results[0].id, hide_via=True)



@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['einfo', 'externalinfo', 'bw', 'bolverwatch', 'owl', 'owlantispam', 'sw', 'spamwatch', 'deai', 'spb', 'spamprotection', 'rose', 'kara'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def fedstat(client, message):
    entity = message.from_user
    args = message.command
    command = args.pop(0).lower()

    trun = False
    silent = False
    if '-t' in args:
        args.remove('-t')
        trun = True
    if '-p' in args:
        args.remove('-p')
        silent = True

    swtoken = {"token": config["config"]["spamwatch_api"], "endpoint": "https://api.spamwat.ch/banlist/"}
    owltoken = {"token": config["config"]["owlantispam_api"], "endpoint": "https://antispam.godofowls.eu/banlist/"}
    BolverWatchtoken = {"token": config["config"]["bolverwatch_api"], "endpoint": "https://spamapi.bolverblitz.net/banlist/"}

    reply_text = ""

    if args:
        entity = ' '.join(args)
    elif not getattr(message.reply_to_message, 'empty', True):
        entity = message.reply_to_message.from_user or entity
    if isinstance(entity, str) and (not entity.isnumeric() and not entity.startswith('TEL-')):
        entity, entity_client = await get_entity(client, entity)
    if not isinstance(entity, str):
        entity = str(entity.id)

    if entity.startswith('TEL-') or int(entity) < 0 or command in ('spb', 'spamprotection'):
        reply_text = f'Spam Protection:\n{await get_spam_protection(entity)}'
    elif command in ('sw', 'spamwatch'):
        reply_text = f'SpamWatch:\n{await get_spamwatch(swtoken, entity, trun)}'
    elif command in ('owl', 'owlantispam'):
        reply_text = f'Owl Antispam:\n{await get_spamwatch(owltoken, entity, trun)}'
    elif command in ('bw', 'bolverwatch'):
        reply_text = f'BolverWatch:\n{await get_spamwatch(BolverWatchtoken, entity, trun)}'
    elif command == 'deai':
        reply_text = f'DEAI:\n{await get_deai(client, entity)}'
    elif command == 'rose':
        reply_text = f'Rose Support:\n{await get_rose(client, entity)}'
    elif command == 'kara':
        reply_text = f'Kara\'s Disciplinary Circle:\n{await get_kara(client, entity)}'
    else:
        spamwatch, owl, bolver, deai, cas, spam_protection, rose, kara = await asyncio.gather(
            get_spamwatch(swtoken, entity, True),
            get_spamwatch(owltoken, entity, True),
            get_spamwatch(BolverWatchtoken, entity, True),
            get_deai(client, entity),
            get_cas(entity),
            get_spam_protection(entity),
            get_rose(client, entity),
            get_kara(client, entity)
        )
        reply_text = f'''SpamWatch:
{spamwatch}

Owl Antispam:
{owl}

BolverWatch:
{bolver}

CAS:
{cas}

Kara's Disciplinary Circle:
{kara}

Rose Support:
{rose}

DEAI:
{deai}

Spam Protection:
{spam_protection}'''
    if silent:
        await slave.send_message(message.from_user.id, reply_text)
        await message.delete()
    else:
        await message.reply_text(reply_text)

async def get_spamwatch(token, entity, trunc=False):
    async with session.get(f'{token["endpoint"]}{entity}', headers={'Authorization': f'Bearer {token["token"]}'}) as resp:
        try:
            json = await resp.json()
        except Exception as ex:
            return f'- <b>{resp.status}:</b> {html.escape(type(ex).__name__)}: {html.escape(str(ex))}'
    if 'code' in json:
        return f'- <b>{json["code"]}:</b> {html.escape(json.get("error", ""))}'
    msg = f'''- <b>Banned on:</b> {str(datetime.datetime.fromtimestamp(json["date"]))}
- <b>Reason:</b> {html.escape(json["reason"].strip())}'''
    if json['message']:
        msgtxt = json['message'][:200] + "..." if trunc else json['message']
        msg += f"\n- <b>Message:</b> <code>{html.escape(msgtxt)}</code>"
    return msg

async def get_rose(client, entity):
    new_message = await client.send_message('missrose_bot', f'/fbanstat {entity} 86718661-6bfc-4bd0-9447-7c419eb08e69')
    identifier = (new_message.chat.id, new_message.message_id)
    conversation_hack[identifier] = None
    while not conversation_hack[identifier]:
        await asyncio.sleep(0.5)
    ntext = conversation_hack[identifier].split('\n')
    del conversation_hack[identifier]
    ntext.pop(0)
    if ntext:
        date = '-'.join(ntext.pop().split(' ')[-1].split('/')[::-1])
        reason = '\n'.join(ntext).strip()
        text = f'- <b>Banned on:</b> {date}'
        if reason:
            text += f'\n- <b>Reason:</b> {html.escape(reason)}'
        return text
    return '- <b>404:</b> Not Found'

async def get_kara(client, entity):
    new_message = await client.send_message('missrose_bot', f'/fbanstat {entity} 423680c6-9044-4a4b-92ba-b4e6a36aaec6')
    identifier = (new_message.chat.id, new_message.message_id)
    conversation_hack[identifier] = None
    while not conversation_hack[identifier]:
        await asyncio.sleep(0.5)
    ntext = conversation_hack[identifier].split('\n')
    del conversation_hack[identifier]
    ntext.pop(0)
    if ntext:
        date = '-'.join(ntext.pop().split(' ')[-1].split('/')[::-1])
        reason = '\n'.join(ntext).strip()
        text = f'- <b>Banned on:</b> {date}'
        if reason:
            text += f'\n- <b>Reason:</b> {html.escape(reason)}'
        return text
    return '- <b>404:</b> Not Found'

async def get_deai(client, entity):
    new_message = await client.send_message('rsophiebot', f'/fcheck {entity} 845d33d3-0961-4e44-b4b5-4c57775fbdac')
    identifier = (new_message.chat.id, new_message.message_id)
    conversation_hack[identifier] = None
    while not conversation_hack[identifier]:
        await asyncio.sleep(0.5)
    ntext = conversation_hack[identifier].split('\n')
    del conversation_hack[identifier]
    ntext.pop(0)
    if ntext:
        ntext.pop(0)
    if ntext and not ntext[0].startswith('They aren\'t fbanned in the '):
        text = '- <b>Reason:</b> '
        ntext.pop(0)
        reason = '\n'.join(ntext).strip()
        text += html.escape(reason) or 'None'
        match = re.match(r'(?:AIdetection:)?((?:0x\d{2} )+)risk:(\S+) mod:X([0-8])(?: eng:(\S+))?(?: cmt:(.+))?', reason)
        if match:
            text += '\n- <b>Ban Codes:</b>\n'
            for i in match.group(1).split(' '):
                if i:
                    i = DEAI_BAN_CODES.get(i.strip()[2:], i.strip())
                    text += f'--- {i}\n'
            text += f'- <b>Risk Factor:</b> {match.group(2).capitalize()}\n'
            text += f'- <b>Module:</b> {DEAI_MODULE_CODES.get(match.group(3), match.group(3))}'
            engine = (match.group(4) or '').strip()
            if engine:
                text += f'\n- <b>Engine:</b> {engine.capitalize()}'
            comment = (match.group(5) or '').strip()
            if comment:
                text += f'\n- <b>Comment:</b> {html.escape(comment)}'
                match = re.match(r'^banstack trigger:0x(\d{2})$', comment)
                if match:
                    text += f'\n- <b>Banstack Trigger Code:</b> {DEAI_BAN_CODES.get(match.group(1), "0x" + match.group(1))}'
        return text
    return '- <b>404:</b> Not Found'

async def get_cas(entity):
    async with session.get(f'https://api.cas.chat/check?user_id={entity}') as resp:
        try:
            json = await resp.json()
        except Exception as ex:
            return f'- <b>{resp.status}:</b> {html.escape(type(ex).__name__)}: {html.escape(str(ex))}'
    if json['ok']:
        return f'''- <b>Banned on:</b> {str(datetime.datetime.fromisoformat(json["result"]["time_added"][:-1]))}
- <b>Offenses:</b> {json["result"]["offenses"]}'''
    return f'- <b>XXX:</b> {html.escape(json.get("description", "XXX"))}'

async def get_spam_protection(entity):
    async with session.get(f'https://api.intellivoid.net/spamprotection/v1/lookup?query={entity}') as resp:
        try:
            json = await resp.json()
        except Exception as ex:
            return f'- <b>{resp.status}:</b> {html.escape(type(ex).__name__)}: {html.escape(str(ex))}'
    if json['success']:
        text = ''
        if json['results']['private_telegram_id']:
            text += f'- <b>PTID:</b> <code>' + json['results']['private_telegram_id'] + "</code>\n"
        if json['results']['attributes']['intellivoid_accounts_verified']:
            text += '- <b>Intellivoid Account Linked:</b> Yes\n'
        if json['results']['attributes']['is_potential_spammer']:
            text += '- <b>Potential Spammer:</b> Yes\n'
        if json['results']['attributes']['is_operator']:
            text += '- <b>Operator:</b> Yes\n'
        if json['results']['attributes']['is_agent']:
            text += '- <b>Agent:</b> Yes\n'
        if json['results']['attributes']['is_whitelisted']:
            text += '- <b>Whitelisted:</b> Yes\n'
        text += f'- <b>Ham/Spam Prediction:</b> {json["results"]["spam_prediction"]["ham_prediction"] or 0}/{json["results"]["spam_prediction"]["spam_prediction"] or 0}'
        if json['results']['language_prediction']['language']:
            text += f'''\n- <b>Language Prediction:</b> {json["results"]["language_prediction"]["language"]}
- <b>Language Prediction Probability:</b> {json["results"]["language_prediction"]["probability"]}'''
        if json['results']['attributes']['is_blacklisted']:
            text += f'''\n- <b>Blacklist Flag:</b> {json["results"]["attributes"]["blacklist_flag"]}
- <b>Blacklist Reason:</b> {json["results"]["attributes"]["blacklist_reason"]}'''
        if json['results']['attributes']['original_private_id']:
            text += f'\n- <b>Original Private ID:</b> {json["results"]["attributes"]["original_private_id"]}'
        return text
    return f'- <b>{json["response_code"]}</b>: {json["error"]["error_code"]}: {json["error"]["type"]}: {html.escape(json["error"]["message"])}'

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.chat(['rsophiebot', 'missrose_bot']) & filters.incoming & filters.regex('^Federation ban info:\n|You ain\'t fbanned in this fed\.|^Failed to get user: unable to getChatMember: Bad Request: chat not found$|^.+ is not banned in this fed\.$|^.+ is currently banned in .+, for the following reason:\n\n'))
async def fedstat_conversation_hack(client, message):
    reply = message.reply_to_message
    if not getattr(reply, 'empty', True):
        identifier = (reply.chat.id, reply.message_id)
        if identifier in conversation_hack:
            conversation_hack[identifier] = message.text
            await client.read_history(message.chat.id, message.message_id)

help_dict['einfo'] = ('External Info',
'''{prefix}externalinfo <i>&lt;user&gt;</i> - Get extended info of <i>&lt;user&gt;</i>
{prefix}externalinfo <i>(as reply to message)</i> - Get extended info of replied user
Aliases: {prefix}extinfo, {prefix}einfo

{prefix}owlantispam <i>&lt;user&gt;</i> - Get Owl Anti-Spam info of <i>&lt;user&gt;</i>
{prefix}owlantispam <i>(as reply to message)</i> - Get Owl Anti-Spam info of replied user
Aliases: {prefix}owl

{prefix}spamwatch <i>&lt;user&gt;</i> - Get SpamWatch info of <i>&lt;user&gt;</i>
{prefix}spamwatch <i>(as reply to message)</i> - Get SpamWatch info of replied user
Aliases: {prefix}sw

{prefix}cas <i>&lt;user&gt;</i> - Get Combot Anti Spam info of <i>&lt;user&gt;</i>
{prefix}cas <i>(as reply to message)</i> - Get Combot Anti Spam info of replied user
Aliases: {prefix}combot

{prefix}kara <i>&lt;user&gt;</i> - Get Kara's Disciplinary Circle info of <i>&lt;user&gt;</i>
{prefix}kara <i>(as reply to message)</i> - Get Kara's Disciplinary Circle info of replied user

{prefix}rose <i>&lt;user&gt;</i> - Get Rose Support Federation info of <i>&lt;user&gt;</i>
{prefix}rose <i>(as reply to message)</i> - Get Rose Support Federation info of replied user

{prefix}deai <i>&lt;user&gt;</i> - Get DEAI info of <i>&lt;user&gt;</i>
{prefix}deai <i>(as reply to message)</i> - Get DEAI info of replied user

{prefix}spamprotection <i>&lt;user&gt;</i> - Get Spam Protection info of <i>&lt;user&gt;</i>
{prefix}spamprotection <i>(as reply to message)</i> - Get Spam Protection info of replied user
Aliases: {prefix}spb''')
