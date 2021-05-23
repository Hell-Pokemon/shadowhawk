from pyrogram import Client, filters
from .. import config, help_dict, log_errors, public_log_errors, get_entity, self_destruct, name_escape, slave

ZWS = '\u200B'
def _generate_sexy(entity, ping, is_creator):
    text = entity.first_name
    if entity.last_name:
        text += f' {entity.last_name}'
    sexy_text = '<code>[DELETED]</code>' if entity.is_deleted else name_escape(text or 'Empty???')
    if not entity.is_deleted:
        if ping:
            sexy_text = f'<a href="tg://user?id={entity.id}">{sexy_text}</a>'
        elif entity.username:
            sexy_text = f'<a href="https://t.me/{entity.username}">{sexy_text}</a>'
        elif not ping:
            sexy_text = sexy_text.replace('@', f'@{ZWS}')
    if entity.is_bot:
        sexy_text += ' <code>[BOT]</code>'
    if entity.is_verified:
        sexy_text += ' <code>[VERIFIED]</code>'
    if entity.is_support:
        sexy_text += ' <code>[SUPPORT]</code>'
    if entity.is_scam:
        sexy_text += ' <code>[SCAM]</code>'
    if entity.is_fake:
        sexy_text += ' <code>[FAKE]</code>'
    if is_creator:
        sexy_text += ' <code>[CREATOR]</code>'
    return sexy_text

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['admin', 'admins'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def admins(client, message):
    chat, entity_client = message.chat, client
    command = message.command
    command.pop(0)
    silent = False
    if '-p' in command:
        command.remove('-p')
        silent = True
    if command:
        chat = ' '.join(command)
        try:
            chat = int(chat)
        except ValueError:
            pass
        try:
            chat, entity_client = await get_entity(client, chat)
        except:
            await self_destruct(message, "<code>Invalid chat or group</code>")
            return
    text_unping = text_ping = ''
    async for i in entity_client.iter_chat_members(chat.id, filter='administrators'):
        text_unping += f'\n[<code>{i.user.id}</code>] {_generate_sexy(i.user, False, i.status == "creator")}'
        text_ping += f'\n[<code>{i.user.id}</code>] {_generate_sexy(i.user, True, i.status == "creator")}'
        if i.title:
            text_unping += f' // {name_escape(i.title.replace("@", "@" + ZWS))}'
            text_ping += f' // {name_escape(i.title)}'
    if silent:
        await slave.send_message(message.from_user.id, text_ping, disable_web_page_preview=True)
        await message.delete()
    else:
        reply = await message.reply_text(text_unping, disable_web_page_preview=True)
        await reply.edit_text(text_ping, disable_web_page_preview=True)

helptext = '''{prefix}admins <i>[chat]</i> - Lists the admins in <i>[chat]</i>
Aliases: {prefix}admin

'''
if 'info' in help_dict:
	idk = help_dict['info']
	help_dict['info'] = (idk[0], idk[1] + helptext)
else:
	help_dict['info'] = ('Info', helptext)
