#
# Settings For Sticker
# Kanged from https://github.com/pokurt/Nana-Remix/blob/master/nana/assistant/stickers.py
#
import asyncio
from pyrogram import filters, Client
from pyrogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.future import select
from .. import slave, DB_AVAILABLE, app_user_ids, log_errors, get_app, database
from ..database import session, StickerSet, AnimatedStickerSet

TEMP_KEYBOARD = []
USER_SET = {}
TODEL = {}

@slave.on_message(filters.command(["setsticker"]))
@log_errors
async def get_stickers(client, message):
	if message.from_user.id not in app_user_ids:
		return

	if not DB_AVAILABLE:
		await message.edit("Your database is not avaiable!")
		return

	global TEMP_KEYBOARD, USER_SET
	app = await get_app(message.from_user.id)
	if not app:
		return

	await app.send_message("@Stickers", "/stats")
	await asyncio.sleep(0.2)
	keyboard = await app.get_history("@Stickers", limit=1)
	keyboard = keyboard[0].reply_markup.keyboard

	for x in keyboard:
		for y in x:
			TEMP_KEYBOARD.append(y)

	await app.send_message("@Stickers", "/cancel")
	# cleanup
	await app.delete_messages("@Stickers", [ms.message_id for ms in await app.get_history("@Stickers", limit=4)])
	msg = await message.reply("Please select your kang pack", reply_markup=ReplyKeyboardMarkup(keyboard))
	USER_SET[message.from_user.id] = msg.message_id
	USER_SET["type"] = 1

@slave.on_message(filters.command(["setanimation"]))
@log_errors
async def get_stickers_animation(client, message):
	if message.from_user.id not in app_user_ids:
		return

	if not DB_AVAILABLE:
		await message.edit("Your database is not avaiable!")
		return

	global TEMP_KEYBOARD, USER_SET
	app = await get_app(message.from_user.id)
	if not app:
		return

	await app.send_message("@Stickers", "/stats")
	await asyncio.sleep(0.2)

	keyboard = await app.get_history("@Stickers", limit=1)
	keyboard = keyboard[0].reply_markup.keyboard

	for x in keyboard:
		for y in x:
			TEMP_KEYBOARD.append(y)

	await app.send_message("@Stickers", "/cancel")
	await app.delete_messages("@Stickers", [ms.message_id for ms in await app.get_history("@Stickers", limit=4)])
	msg = await message.reply("Select your stickers for set as kang animation sticker", reply_markup=ReplyKeyboardMarkup(keyboard))
	USER_SET[message.from_user.id] = msg.message_id
	USER_SET["type"] = 2

def get_stickerlist(client,message):
	if not DB_AVAILABLE:
		return
	global TEMP_KEYBOARD, USER_SET
	if message.from_user and message.from_user.id in list(USER_SET):
		return True
	TEMP_KEYBOARD = []
	USER_SET = {}

@slave.on_message(get_stickerlist)
@log_errors
async def set_stickers(client, message):
	if message.from_user.id not in app_user_ids:
		return

	if not DB_AVAILABLE:
		await message.edit("Your database is not avaiable!")
		return

	global TEMP_KEYBOARD, USER_SET
	if message.text in TEMP_KEYBOARD:
		await client.delete_messages(message.chat.id, USER_SET[message.from_user.id])
		if USER_SET["type"] == 1:
			sticker = (await session.execute(select(StickerSet).where(StickerSet.id == message.from_user.id))).scalars().one_or_none()
			if sticker:
				sticker.sticker = message.text
			else:
				sticker = StickerSet(message.from_user.id, message.text)
				session.add(sticker)
		elif USER_SET["type"] == 2:
			sticker = (await session.execute(select(AnimatedStickerSet).where(AnimatedStickerSet.id == message.from_user.id))).scalars().one_or_none()
			sticker = session.query(AnimatedStickerSet).get(message.from_user.id)
			if sticker:
				sticker.sticker = message.text
			else:
				sticker = AnimatedStickerSet(message.from_user.id, message.text)
				session.add(sticker)
		await session.commit()
		status = "Ok, sticker pack was set to <code>{}</code>.".format(message.text)
	else:
		status = "Invalid pack selected."

	TEMP_KEYBOARD = []
	USER_SET = {}
	button = InlineKeyboardMarkup([[InlineKeyboardButton("Set Sticker Pack", callback_data="setsticker")]])
	await slave.send_message(message.chat.id, f"{status}\nWhat else would you like to do?", reply_markup=button)


@slave.on_callback_query(filters.regex("^setsticker$"))
@log_errors
async def settings_sticker(client, message):
	if message.from_user.id not in app_user_ids:
		await message.answer('...no', cache_time=3600, show_alert=True)
		return

	if not DB_AVAILABLE:
		await message.edit("Your database is not avaiable!")
		return

	global TEMP_KEYBOARD, USER_SET
	app = await get_app(message.from_user.id)
	if not app:
		return

	await app.send_message("@Stickers", "/stats")
	await asyncio.sleep(0.2)
	try:
		keyboard = await app.get_history("@Stickers", limit=1)
		keyboard = keyboard[0].reply_markup.keyboard
	except:
		await message.edit("You dont have any sticker pack!\nAdd stickers pack in @Stickers")
		return
	for x in keyboard:
		for y in x:
			TEMP_KEYBOARD.append(y)

	await app.send_message("@Stickers", "/cancel")
	await app.delete_messages("@Stickers", [ms.message_id for ms in await app.get_history("@Stickers", limit=4)])
	msg = await slave.send_message(message.from_user.id, "Select your stickers for set as kang animation sticker", reply_markup=ReplyKeyboardMarkup(keyboard))
	USER_SET[message.from_user.id] = msg.message_id
	USER_SET["type"] = 1
