import asyncio

from pyrogram import Client, filters
from pyrogram.methods.chats.get_chat_members import Filters as ChatMemberFilters
from pyrogram.types import Message
from .. import config, help_dict, log_errors, public_log_errors

# kanged from https://github.com/Dank-del/EagleX/blob/master/Bot/modules/pin.py

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['pin'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def pin_message(client, message: Message):
    # First of all check if its a group or not
    if message.chat.type in ["group", "supergroup"]:
        # Here lies the sanity checks
        admins = await client.get_chat_members(
            message.chat.id, filter=ChatMemberFilters.ADMINISTRATORS
        )
        admin_ids = [user.user.id for user in admins]
        me = await client.get_me()

        # If you are an admin
        if me.id in admin_ids:
            # If you replied to a message so that we can pin it.
            if message.reply_to_message:
                disable_notification = True

                # Let me see if you want to notify everyone. People are gonna hate you for this...
                if len(message.command) >= 2 and message.command[1] in [
                    "alert",
                    "notify",
                    "loud",
                ]:
                    disable_notification = False

                # Pin the fucking message.
                await client.pin_chat_message(
                    message.chat.id,
                    message.reply_to_message.message_id,
                    disable_notification=disable_notification,
                )
                await message.edit("<code>Pinned message!</code>")
            else:
                # You didn't reply to a message and we can't pin anything. ffs
                await message.edit(
                    "<code>Reply to a message so that I can pin the god damned thing...</code>"
                )
        else:
            # You have no business running this command.
            await message.edit("<code>I am not an admin here lmao. What am I doing?</code>")
    else:
        # Are you fucking dumb this is not a group ffs.
        await message.edit("<code>This is not a place where I can pin shit.</code>")

    # And of course delete your lame attempt at changing the group picture.
    # RIP you.
    # You're probably gonna get ridiculed by everyone in the group for your failed attempt.
    # RIP.
    await asyncio.sleep(3)
    await message.delete()

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['unpin', 'unpinall'], prefixes=config['config']['prefixes']))
@log_errors
async def unpin_message(client, message: Message):
    # First of all check if its a group or not
    if message.chat.type in ["group", "supergroup"]:
        # Here lies the sanity checks
        admins = await client.get_chat_members(
            message.chat.id, filter=ChatMemberFilters.ADMINISTRATORS
        )
        admin_ids = [user.user.id for user in admins]
        me = await client.get_me()

        # If you are an admin
        if me.id in admin_ids:
            # If you replied to a message so that we can unpin it.
            if message.reply_to_message:

                # unpin the fucking message.
                await client.unpin_chat_message(
                    message.chat.id,
                    message.reply_to_message.message_id
                )
                await message.edit("<code>Unpinned message!</code>")
            else:
                # You didn't reply to a message and we can't unpin anything. ffs
                await message.edit(
                    "<code>Reply to a message so that I can unpin the god damned thing...</code>"
                )
        else:
            # You have no business running this command.
            await message.edit("<code>I am not an admin here lmao. What am I doing?</code>")
    else:
        # Are you fucking dumb this is not a group ffs.
        await message.edit("<code>This is not a place where I can unpin shit.</code>")

    # And of course delete your lame attempt at changing the group picture.
    # RIP you.
    # You're probably gonna get ridiculed by everyone in the group for your failed attempt.
    # RIP.
    await asyncio.sleep(3)
    await message.delete()

help_dict['pin'] = ('Pin',
'''{prefix}pin <i>(maybe reply to a message) [loud]</i> - Pins the replied message (use <code>loud</code> to notify all users)

{prefix}unpin <i>(maybe reply to a message)</i> - Unpins the replied message''')