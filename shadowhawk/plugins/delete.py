import html, time
import asyncio
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, public_log_errors, self_destruct

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['d', 'del', 'delete'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def delete(client, message):
    messages = set((message.message_id,))
    reply = message.reply_to_message
    if not getattr(reply, 'empty', True):
        messages.add(reply.message_id)
    else:
        async for i in client.iter_history(message.chat.id, offset=1):
            if i.outgoing:
                messages.add(i.message_id)
                break
    await client.delete_messages(message.chat.id, messages)

@Client.on_message(~filters.forwarded & ~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['da', 'deleteall'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def deleteall(client, message):
    await message.delete()
    reply = message.reply_to_message
    if getattr(reply, 'empty', True) or not reply.from_user or not reply.from_user.id:
        return
    await client.delete_user_history(message.chat.id, reply.from_user.id)

@Client.on_message(~filters.forwarded & ~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['p', 'purge', 'sp', 'selfpurge'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def purge(client, message):
    # Define a generator
    async def _generator(client, message):
        command = message.command
        selfpurge = 's' in command.pop(0)
        supergroup = message.chat.type == 'supergroup'
        reply = message.reply_to_message
        start = message.message_id

        # If they specify the number of msgs to delete.
        total = None
        if command:
            total = command.pop(0)
            total = int(total) if total.isnumeric() else None
        end = total

        # Replies are always first
        if reply:
            end = reply.message_id

        # idiot check.
        if not end:
            return
        
        # Ok now check if we're in a supergroup.
        # Supergroup IDs are sequential so purging is
        # very fast and very easy.
        if supergroup and not selfpurge:
            # Account for it not being a reply.
            if not reply:
                end = start + total
            # swap start and end, since it's confusing.
            end,start = start,end
            # make sure we're not purging our own msgs
            if end - start > 100:
                # Loop
                num = start
                while True:
                    it = min(end - num, 100)
                    yield set(range(num, num + it))
                    if num + it >= end:
                        return
                    else:
                        num += it
            else:
                yield set(range(start, end))
        else:
            # Do slow iteration over message history to check for info.
            ids = set()
            cnt = 0
            
            async for i in client.iter_history(message.chat.id, offset=1):
                if selfpurge and i.outgoing:
                    ids.add(i.message_id)
                    cnt += 1
                    if (not reply and cnt >= end) or (reply and end + 1 >= i.message_id):
                        yield ids
                        return
                elif not selfpurge:
                    ids.add(i.message_id)
                    cnt += 1
                    if (not reply and cnt >= end) or (reply and end + 1 >= i.message_id):
                        yield ids
                        return
                
                if cnt % 100 == 0:
                    yield ids
                    ids.clear()
    
    cnt = msgcnt = 0
    s = time.time()
    async for chunk in _generator(client, message):
        cnt += 1
        msgcnt += len(chunk)
        await client.delete_messages(message.chat.id, chunk)
        if cnt > 1:
            await message.edit(f"Purging {msgcnt} messages ({cnt} chunks)...")
    f = time.time()
    if cnt > 1:
        await self_destruct(message, f"Purged {msgcnt} messages ({cnt} chunks) in {round((f-s)*1000)}ms.")
    else:
        await message.delete()

yeetpurge_info = {True: dict(), False: dict()}
yeetpurge_lock = asyncio.Lock()
@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.command(['yp', 'yeetpurge', 'syp', 'selfyeetpurge'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def yeetpurge(client, message):
    reply = message.reply_to_message
    if getattr(reply, 'empty', True):
        await message.delete()
        return
    info = yeetpurge_info['s' in message.command[0]]
    async with yeetpurge_lock:
        if message.from_user.id not in info:
            info[message.from_user.id] = dict()
        info = info[message.from_user.id]
        if message.chat.id not in info:
            resp = await message.reply_text('Reply to end destination')
            info[message.chat.id] = (message, reply, resp)
            return
        og_message, og_reply, og_resp = info.pop(message.chat.id)
    messages = set((og_message.message_id, message.message_id, og_resp.message_id))
    if not ('s' in message.command[0] and not og_reply.outgoing):
        messages.add(og_reply.message_id)
    if not ('s' in message.command[0] and not reply.outgoing):
        messages.add(reply.message_id)
    from_id, to_id = sorted((og_reply.message_id, reply.message_id))
    async for i in client.iter_history(message.chat.id, offset_id=to_id):
        if not ('s' in message.command[0] and not i.outgoing):
            messages.add(i.message_id)
        if from_id >= i.message_id:
            break
    await client.delete_messages(message.chat.id, messages)

help_dict['delete'] = ('Delete',
'''{prefix}delete <i>(maybe reply to a message)</i> - Deletes the replied to message, or your latest message
Aliases: {prefix}d, {prefix}del

{prefix}purge <i>(as reply to a message)</i> - Purges the messages between the one you replied (and including the one you replied)
Aliases: {prefix}p

{prefix}selfpurge <i>(as reply to a message)</i> - {prefix}p but only your messages
Aliases: {prefix}sp

{prefix}yeetpurge <i>(as reply to a message)</i> - Purges messages in between
Aliases: {prefix}yp

{prefix}selfyeetpurge <i>(as reply to a message)</i> - {prefix}yp but only your messages
Aliases: {prefix}syp

{prefix}deleteall <i>(as reply to a message)</i> - Deletes all of the replied to user's messages
Aliases: {prefix}da''')
