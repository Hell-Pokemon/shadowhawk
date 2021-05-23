from pyrogram import filters
from .. import slave, config, help_dict, app_user_ids, log_errors

@slave.on_message(filters.regex(r"^[\/!]start"))
@log_errors
async def start(_client, message):
	if message.chat.type != 'private':
		# Get ourselves
		username = (await slave.get_me()).username
		if username in message.text:
			if message.from_user.id in app_user_ids:
				await message.reply("Hiiii master! \N{heavy black heart}")
			else:
				await message.reply("owo who're you?")
	else:
		if message.from_user.id not in app_user_ids:
			await slave.send_message(message.chat.id, "Hewwo! I don't handle commands from strangers, sorry!")
			return

		await slave.send_message(message.chat.id, "Under construction.")