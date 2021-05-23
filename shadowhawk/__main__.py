import asyncio
import math
import logging
import datetime
from pyrogram import idle
from pyrogram.raw import functions
from pyrogram.errors.exceptions.flood_420 import FloodWait
from . import loop, apps, slave, app_user_ids, session, log_chat, loads, log_ring, spammy_log_ring, config, ee, statistics, server_support
from shadowhawk import database

# Calculate the load avg magic numbers
load1_magic = math.exp(-5.0 / (1 * 60))
load5_magic = math.exp(-5.0 / (5 * 60))
load15_magic = math.exp(-5.0 / (15 * 60))
load30_magic = math.exp(-5.0 / (30 * 60))

async def main():
    async def _start_app(app):
        await app.start()
        asyncio.create_task(_get_me_loop(app))
    async def _get_me_loop(app):
        while True:
            try:
                me = await app.get_me()
                app_user_ids[me.id] = me
            except:
                pass
            await asyncio.sleep(60)
    async def _get_load_loop():
        while True:
            try:
                # get total pending tasks
                tasks = len(asyncio.all_tasks())
                # calculate 1 minute load
                loads[1] *= load1_magic
                loads[1] += tasks * (1 - load1_magic)
                # calculate 5 minute load
                loads[5] *= load5_magic
                loads[5] += tasks * (1 - load5_magic)
                # calculate 15 minute load
                loads[15] *= load15_magic
                loads[15] += tasks * (1 - load15_magic)
                # calculate 30 minute load
                loads[30] *= load30_magic
                loads[30] += tasks * (1 - load30_magic)
            except:
                # this exception will screw up the measurement but oh well.
                pass
            # our sample rate is 5 seconds for the magics
            await asyncio.sleep(5)
    async def _send_log_loop():
        flipflop = False
        while True:
            # send log messages to their chats
            # alternate logs
            flipflop = not flipflop
            try:
                if flipflop:
                    msg, chat = log_ring.get_nowait()
                else:
                    msg, chat = spammy_log_ring.get_nowait()

                while True:
                    try:
                        await slave.send_message(config['logging'][chat], msg, disable_web_page_preview=True)
                        if 'Logs Sent' in statistics:
                            statistics['Logs Sent'] += 1
                        else:
                            statistics['Logs Sent'] = 1
                    except FloodWait as ex:
                        await asyncio.sleep(ex.x + 1)
                    else:
                        break
            except asyncio.QueueEmpty:
                pass
            await asyncio.sleep(config['logging']['send_rate'])
    # on first start, populate the loads with initial values
    t = len(asyncio.all_tasks())
    loads[1] = loads[5] = loads[15] = loads[30] = t
    # Set our start time
    statistics['start'] = datetime.datetime.now()
    # Start the telegram clients
    await asyncio.gather(*(_start_app(app) for app in apps), slave.start())
    # Start the loops for our data
    asyncio.create_task(_get_load_loop())
    asyncio.create_task(_send_log_loop())
    # Load the database after all the plugins are loaded. 
    await database.innit()
    # Announce that the bot has started.
    ee.emit('OnStart')
    # Get some basic info on telegram limits I suppose.
    server_support.set_thing(await apps[0].send(functions.help.GetConfig()))
    # Send a log message to the log chat saying the bot started, make it
    # a bit more informative than "lmao we started!"
    start_msg = f"<b>=-=-= [ShadowHawk] =-=-=</b>\n"
    start_msg += f"<b>Current DC:</b> <code>{server_support.this_dc}{'[TEST]' if server_support.test_mode else ''}</code>\n"
    start_msg += f"<b>Max Supergroup Size:</b> <code>{server_support.megagroup_size_max}</code>\n"
    start_msg += f"<b>Max Group Size:</b> <code>{server_support.chat_size_max}</code>\n"
    start_msg += f"<b>Max Pinned Chats:</b> <code>{server_support.pinned_dialogs_count_max}</code>\n"
    start_msg += f"<b>Max Pinned Chats In Folders:</b> <code>{server_support.pinned_infolder_count_max}</code>\n"
    start_msg += f"<b>Max Forwarded Messages:</b> <code>{server_support.forwarded_count_max}</code>\n"
    start_msg += f"<b>Max Saved GIFs:</b> <code>{server_support.saved_gifs_limit}</code>\n"
    start_msg += f"<b>Max Recent Stickers:</b> <code>{server_support.stickers_recent_limit}</code>\n"
    start_msg += f"<b>Max Favorited Stickers:</b> <code>{server_support.stickers_faved_limit}</code>\n"
    start_msg += f"<b>Max Caption Length:</b> <code>{server_support.caption_length_max}</code>\n"
    start_msg += f"<b>Max Message Length:</b> <code>{server_support.message_length_max}</code>\n"
    start_msg += f"<b>GIF Search Username:</b> @{server_support.gif_search_username}\n"
    start_msg += f"<b>Venue Search Username:</b> @{server_support.venue_search_username}\n"
    start_msg += f"<b>Image Search Username:</b> @{server_support.img_search_username}\n"
    await log_chat(start_msg)
    # Idle forever.
    await idle()
    ee.emit('OnStop')
    await asyncio.gather(*(app.stop() for app in apps), slave.stop())
    await session.close()

logging.basicConfig(format="[%(levelname)s - %(asctime)s] In thread %(threadName)s, module %(module)s at %(funcName)s line %(lineno)s -> %(message)s", level=logging.INFO)
loop.run_until_complete(main())
