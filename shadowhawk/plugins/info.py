from pyrogram import Client, filters
from pyrogram.errors.exceptions.bad_request_400 import MessageNotModified
from .. import config, help_dict, get_entity, log_errors, public_log_errors, name_escape, slave

ZWS = '\u200B'
def _generate_sexy(entity, ping):
    text = getattr(entity, 'title', None)
    if not text:
        text = entity.first_name
        if entity.last_name:
            text += f' {entity.last_name}'
    sexy_text = name_escape(text or '') or '<code>[DELETED]</code>'
    if ping and entity.type in ('private', 'bot') and text:
        sexy_text = f'<a href="tg://user?id={entity.id}">{sexy_text}</a>'
    elif entity.username:
        sexy_text = f'<a href="https://t.me/{entity.username}">{sexy_text}</a>'
    elif not ping:
        sexy_text = sexy_text.replace('@', f'@{ZWS}')
    if entity.type == 'bot':
        sexy_text += ' <code>[BOT]</code>'
    if entity.is_verified:
        sexy_text += ' <code>[VERIFIED]</code>'
    if entity.is_support:
        sexy_text += ' <code>[SUPPORT]</code>'
    if entity.is_scam:
        sexy_text += ' <code>[SCAM]</code>'
    if entity.is_fake:
        sexy_text += ' <code>[FAKE]</code>'
    return sexy_text

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['info', 'whois'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def info(client, message):
    entity = message.chat
    command = message.command
    command.pop(0)
    silent = False
    if '-p' in command:
        command.remove('-p')
        silent = True
    if command:
        entity = ' '.join(command)
    elif not getattr(message.reply_to_message, 'empty', True):
        entity = message.reply_to_message.from_user or message.reply_to_message.chat
    try:
        entity, entity_client = await get_entity(client, entity)
    except Exception as ex:
        await message.reply_text(f'{type(ex).__name__}: {str(ex)}', parse_mode=None)
        return
    text_ping = _generate_sexy(entity, True)
    text_unping = _generate_sexy(entity, False)
    text_ping += f'\n<b>ID:</b> <code>{entity.id}</code>'
    text_unping += f'\n<b>ID:</b> <code>{entity.id}</code>'
    if entity.dc_id:
        text_ping += f'\n<b>DC ID:</b> {entity.dc_id}'
        text_unping += f'\n<b>DC ID:</b> {entity.dc_id}'
    if entity.username:
        text_ping += f'\n<b>Username:</b> @{entity.username}'
        text_unping += f'\n<b>Username:</b> @{ZWS}{entity.username}'
    if entity.restrictions:
        restrictions = []
        for r in entity.restrictions:
            restrictions.append(f"{r.reason}-{r.platform}")
        text_ping += f'\n<b>Restrictions:</b> {", ".join(restrictions)}'
        text_unping += f'\n<b>Restrictions:</b> {", ".join(restrictions)}'
    if entity.members_count:
        text_ping += f'\n<b>Members:</b> {entity.members_count}'
        text_unping += f'\n<b>Members:</b> {entity.members_count}'
    if entity.linked_chat:
        text_ping += f'\n<b>Linked Chat:</b> {_generate_sexy(entity.linked_chat, False)} [<code>{entity.linked_chat.id}</code>]'
        text_unping += f'\n<b>Linked Chat:</b> {_generate_sexy(entity.linked_chat, False)} [<code>{entity.linked_chat.id}</code>]'
    if entity.description or entity.bio:
        text_ping += f'\n<b>Description:</b>\n{name_escape(entity.description or entity.bio)}'
        text_unping += f'\n<b>Description:</b>\n{name_escape((entity.description or entity.bio).replace("@", "@" + ZWS))}'
    if silent:
        await slave.send_message(message.from_user.id, text_ping, disable_web_page_preview=True)
        await message.delete()
    else:
        reply = await message.reply_text(text_unping, disable_web_page_preview=True)
        if text_ping != text_unping:
            try:
                await reply.edit_text(text_ping, disable_web_page_preview=True)
            except MessageNotModified:
                pass

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command('id', prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def id(client, message):
    silent = '-p' in message.command
    text_unping = '<b>Chat ID:</b>'
    if message.chat.username:
        text_unping = f'<a href="https://t.me/{message.chat.username}">{text_unping}</a>'
    text_unping += f' <code>{message.chat.id}</code>\n'
    text = '<b>Message ID:</b>'
    if message.link:
        text = f'<a href="{message.link}">{text}</a>'
    text += f' <code>{message.message_id}</code>\n'
    text_unping += text
    if message.from_user:
        text_unping += f'<b><a href="tg://user?id={message.from_user.id}">User ID:</a></b> <code>{message.from_user.id}</code>\n'
    text_ping = text_unping
    reply = message.reply_to_message
    if not getattr(reply, 'empty', True):
        text_unping += '\n'
        text = '<b>Replied Message ID:</b>'
        if reply.link:
            text = f'<a href="{reply.link}">{text}</a>'
        text += f' <code>{reply.message_id}</code>\n'
        text_unping += text
        text_ping = text_unping
        if reply.from_user:
            text = '<b>Replied User ID:</b>'
            if reply.from_user.username:
                text = f'<a href="https://t.me/{reply.from_user.username}">{text}</a>'
            text += f' <code>{reply.from_user.id}</code>\n'
            text_unping += text
            text_ping += f'<b><a href="tg://user?id={reply.from_user.id}">Replied User ID:</a></b> <code>{reply.from_user.id}</code>\n'
        if reply.forward_from:
            text_unping += '\n'
            text = '<b>Forwarded User ID:</b>'
            if reply.forward_from.username:
                text = f'<a href="https://t.me/{reply.forward_from.username}">{text}</a>'
            text += f' <code>{reply.forward_from.id}</code>\n'
            text_unping += text
            text_ping += f'\n<b><a href="tg://user?id={reply.forward_from.id}">Forwarded User ID:</a></b> <code>{reply.forward_from.id}</code>\n'
        if getattr(reply, 'document', None):
            text = "\n"
            text += f"<b>File ID:</b> {reply.document.file_id}\n"
            text += f"<b>File Unique ID:</b> {reply.document.file_unique_id}\n"
            text += f"<b>File Name:</b> {reply.document.file_name}\n"
            text += f"<b>File Size:</b> {reply.document.file_size}\n"
            text += f"<b>Mime Type:</b> {reply.document.mime_type}\n"
            text_unping += text
            text_ping += text
    if silent:
        await slave.send_message(message.from_user.id, text_ping, disable_web_page_preview=True)
        await message.delete()
    else:
        reply = await message.reply_text(text_unping, disable_web_page_preview=True)
        if text_unping != text_ping:
            await reply.edit_text(text_ping, disable_web_page_preview=True)

helptext = '''{prefix}info <i>&lt;entity&gt;</i> - Get entity info
{prefix}info <i>(as reply to message)</i> - Get entity info of replied user
Aliases: {prefix}whois

{prefix}id <i>[maybe reply to message]</i> - Gets IDs

'''

if 'info' in help_dict:
	idk = help_dict['info']
	help_dict['info'] = (idk[0], idk[1] + helptext)
else:
	help_dict['info'] = ('Info', helptext)
