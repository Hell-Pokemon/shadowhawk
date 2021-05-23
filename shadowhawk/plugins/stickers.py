# Mostly kanged from https://github.com/pokurt/Nana-Remix/blob/master/nana/modules/stickers.py

import math, os, asyncio
from PIL import Image
from .. import slave, config, help_dict, get_entity, log_chat, log_errors, self_destruct, database, public_log_errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram import filters, Client

button = InlineKeyboardMarkup([[InlineKeyboardButton("Set Sticker Pack", callback_data="setsticker")]])

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['kang'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def kang_stickers(client, message):

	sticker_pack = await database.get_sticker_set(message.from_user.id)
	animation_pack = await database.get_animated_set(message.from_user.id)
	if not sticker_pack:
		await slave.send_message(message.from_user.id,
								  "Looks like want to kang a sticker, but a sticker pack was not set!\n"
								  "To set a sticker pack, type /setsticker and follow the instructions.", reply_markup=button)
		await self_destruct(message, "<code>You have not set a sticker pack!\nCheck your slave for more information!</code>")
		return

	sticker_pack = sticker_pack.sticker
	if message.reply_to_message and message.reply_to_message.sticker:
		if message.reply_to_message.sticker.mime_type == "application/x-tgsticker":
			if not animation_pack:
				await slave.send_message(message.from_user.id,
								  "Looks like want to kang an animated sticker, but a sticker pack was not set!\n"
								  "To set a sticker pack, type /setanimation and follow the instructions.", reply_markup=button)
				await self_destruct(message, "<code>You have not set an animated sticker pack!\nCheck your slave for more information!</code>")
				return
			await message.edit("<code>That's a nice sticker you sent in chat, I'm gonna kang it to my kang pack!</code>")
			await client.download_media(message.reply_to_message.sticker, file_name="cache/sticker.tgs")
		else:
			await message.edit("<code>That's a nice sticker you sent in chat, I'm gonna kang it to my kang pack!</code>")
			await client.download_media(message.reply_to_message.sticker, file_name="cache/sticker.png")
	elif message.reply_to_message and message.reply_to_message.photo:
		await message.edit("<code>That's a nice sticker you sent in chat, I'm gonna kang it to my kang pack!</code>")
		await client.download_media(message.reply_to_message.photo, file_name="cache/sticker.png")
	elif message.reply_to_message and message.reply_to_message.document and message.reply_to_message.document.mime_type in ["image/png", "image/jpeg"]:
		await message.edit("<code>That's a nice sticker you sent in chat, I'm gonna kang it to my kang pack!</code>")
		await client.download_media(message.reply_to_message.document, file_name="cache/sticker.png")
	else:
		await self_destruct(message, f"Reply with a sticker or photo to kang it!\nCurrent sticker pack is: {sticker_pack}\nCurrent animation pack is: {animation_pack.sticker}")
		return
	
	if ((message.reply_to_message.sticker and message.reply_to_message.sticker.mime_type)) != "application/x" "-tgsticker":
		im = Image.open("cache/sticker.png")
		if (im.width and im.height) < 512:
			size1 = im.width
			size2 = im.height
			if size1 > size2:
				scale = 512 / size1
				size1new = 512
				size2new = size2 * scale
			else:
				scale = 512 / size2
				size1new = size1 * scale
				size2new = 512
			size1new = math.floor(size1new)
			size2new = math.floor(size2new)
			sizenew = (size1new, size2new)
			im = im.resize(sizenew)
		else:
			maxsize = (512, 512)
			im.thumbnail(maxsize)
		im.save("cache/sticker.png", 'PNG')

	# Lets talk to Stickers!
	await client.send_message("@Stickers", "/addsticker")
	await asyncio.sleep(0.2)

	if message.reply_to_message.sticker and message.reply_to_message.sticker.mime_type == "application/x-tgsticker":
		await client.send_message("@Stickers", animation_pack.sticker)
	else:
		await client.send_message("@Stickers", sticker_pack)

	await asyncio.sleep(0.2)

	checkfull = await client.get_history("@Stickers", limit=1)
	# Their stickerpack is full.
	if checkfull[0].text == "Whoa! That's probably enough stickers for one pack, give it a break. A pack can't have more than " \
				   "120 stickers at the moment.":
		await self_destruct(message, "<code>Your sticker pack is full!\nPlease change to a different one via your slave.</code>")
		os.remove('cache/sticker.png')
		return
	
	if message.reply_to_message.sticker and message.reply_to_message.sticker.mime_type == "application/x-tgsticker":
		await client.send_document("@Stickers", 'cache/sticker.tgs')
		os.remove('cache/sticker.tgs')
	else:
		await client.send_document("@Stickers", 'cache/sticker.png')
		os.remove('cache/sticker.png')

	if len(message.text.split(None,1)) > 1:
		ic = message.text.split(None, 1)[1]
	elif message.reply_to_message.sticker:
		ic = message.reply_to_message.sticker.emoji
	else:
		ic = "\N{thinking face}"

	await client.send_message("@Stickers", ic)
	await asyncio.sleep(1)
	await client.send_message("@Stickers", "/done")
	await asyncio.sleep(1)
	await client.delete_messages("@Stickers", [ms.message_id for ms in await client.get_history("@Stickers", limit=11)])
	if message.reply_to_message.sticker and message.reply_to_message.sticker.mime_type == "application/x-tgsticker":
		await self_destruct(message, f'<code>Kanged! Your pack is <a href="https://t.me/addstickers/{animation_pack.sticker}">here</a>.')
	else:
		await self_destruct(message, f'<code>Kanged! Your pack is <a href="https://t.me/addstickers/{sticker_pack}">here</a>.')

help_dict['stickers'] = ('Stickers',
'''{prefix}kang <i>(as reply to text)</i> <i>[emoji]</i> - Kang an image or sticker to your stickerpack
Aliases: {prefix}tr

<b>Note</b>: Message the slave with /setsticker or /setanimation to either create a new sticker pack or set the one you would like to use.
''')