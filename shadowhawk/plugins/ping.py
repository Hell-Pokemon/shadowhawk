import time
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, public_log_errors, loads, log_ring, spammy_log_ring

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['ping', 'pong'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def ping_pong(client, message):
    strings = {
        'ping': 'Pong!',
        'pong': 'Ping!'
    }
    text = strings[message.command[0].lower()]
    start = time.time()
    reply = await message.reply_text(text)
    end = time.time()
    # Log the time between receiving the message and our response
    avgs = f"{loads[1]:.2f}, {loads[5]:.2f}, {loads[15]:.2f}, {loads[30]:.2f}"
    logring = f"{log_ring.qsize()}/{log_ring.maxsize}"
    spammyring = f"{spammy_log_ring.qsize()}/{spammy_log_ring.maxsize}"
    await reply.edit_text(f'{text}\n<i>{round((end-start)*1000)}ms</i>\n<b>Delta: </b><i>{end-message.date:.2f}s</i>\n<b>Task Avg:</b> {avgs}\n<b>Log Ring:</b> {logring}\n<b>Spammy Ring:</b> {spammyring}')

help_dict['ping'] = ('Ping',
'''{prefix}ping - Pong!
{prefix}pong - Ping!''')
