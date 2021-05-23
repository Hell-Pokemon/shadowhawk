import html
import asyncio
import logging
import datetime
import ziproto
import time
from io import BytesIO
from pyrogram import Client, filters
from pyrogram.methods.chats.get_chat_members import Filters as ChatMemberFilters
from shadowhawk import config, slave, log_errors, app_user_ids, log_chat, get_entity, get_user, self_destruct, database, CheckAdmin, public_log_errors, ee, help_dict
from shadowhawk.plugins.shell import processes

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['dig'], prefixes=config['config']['prefixes']))
@log_errors
async def dig_command(client, message):
	# dig +noall +comments +answer
	command = message.command
	command.pop(0)
	command = "dig +noall +comments +answer " + " ".join(command)
	process = await asyncio.create_subprocess_shell(command, stdin=None, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
	process.cmdline = command
	processes[process.pid] = process
	stdout, stderr = await process.communicate(None)
	
	text = ""
	if process.pid in processes:
		del processes[process.pid]
	stdout = stdout.decode().replace('\r', '').strip('\n').rstrip()
	stderr = stderr.decode().replace('\r', '').strip('\n').rstrip()
	if stderr:
		text += f'<code>{html.escape(stderr)}</code>\n'
	if stdout:
		text += f'<code>{html.escape(stdout)}</code>'

	# send as a file if it's longer than 4096 bytes
	if len(text) > 4096:
		out = stderr.strip() + "\n" + stdout.strip()
		f = BytesIO(out.strip().encode('utf-8'))
		f.name = "output.txt"
		await message.reply_document(f, caption=f'<b>Exit Code:</b> <code>{process.returncode}</code>')
	else:
		await message.reply(text)

helptext = '''{prefix}dig <i>(domain name)</i> - Gives dig information (this is just an alias to <code>{prefix}sh dig +noall +comments +answer</code>)

'''
if 'misc' in help_dict:
	idk = help_dict['misc']
	help_dict['misc'] = (idk[0], idk[1] + helptext)
else:
	help_dict['misc'] = ('Miscellaneous', helptext)