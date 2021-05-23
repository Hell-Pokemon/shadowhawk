import asyncio, arrow
from forex_python.converter import CurrencyRates, CurrencyCodes
from pyrogram import Client, filters
from pint import UnitRegistry
from .. import config, help_dict, get_entity, log_chat, log_errors, self_destruct, public_log_errors

c = CurrencyRates()
cc = CurrencyCodes()
ureg = UnitRegistry()
Q_ = ureg.Quantity

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['curr'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def currency(client, message):
	if len(message.command) <= 3:
		await self_destruct(message, "<code>Incorrect Syntax</code>")
		return

	value = message.command[1]
	curr1 = message.command[2].upper()
	curr2 = message.command[3].upper()
	try:
		from_sym = cc.get_symbol(curr1)
		to_sym = cc.get_symbol(curr2)
		conv = c.convert(curr1, curr2, float(value))
		await message.edit(f"<code>{value}{from_sym} = {conv:,.2f}{to_sym}</code>")
	except ValueError as err:
		await self_destruct(message, f"<code>{str(err)}</code>")

commands = ['conv', 'convert', 'length', 'len', 'mass', 'vol', 'volume', 'temp']

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(commands, prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def uconvert(client, message):
	if len(message.command) <= 3:
		await self_destruct(message, "<code>Incorrect Syntax</code>")
		return

	value = message.command[1]
	curr1 = message.command[2]
	curr2 = message.command[3]

	# Fix for -temp
	if curr1.lower() == "f":
		curr1 = "degF"
	elif curr1.lower() == "c":
		curr1 = "degC"
	if curr2.lower() == "f":
		curr2 = "degF"
	elif curr2.lower() == "c":
		curr2 = "degC"

	try:
		from_u = ureg(curr1)
		in_u = ureg.Quantity(float(value), from_u)
		conv = in_u.to(ureg(curr2))
		newval = f"{conv.magnitude:,.2f}"
		if newval == "0.00":
			newval = f"{conv.magnitude:f}"
		await message.edit(f"<code>{value} {from_u.units} = {newval} {conv.units}</code>")
	except (TypeError, ValueError) as err:
		await self_destruct(message, f"<code>{str(err)}</code>")

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['time'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def calc_time(client, message):

	try:
		command = message.command
		command.pop(0)
		if command:
			tz = " ".join(command)
		elif not config['config']['timezone']:
			await message.delete()
			return
		else:
			tz = config['config']['timezone']

		now = arrow.utcnow().to(tz)
		time = now.format("hh:mm A (HH:mm)")
		date = now.format(r"MM-DD-YYYY")

		await message.edit(f"<i>Currently it is <b>{time}</b> on <b>{date}</b> in <b>{now.format('ZZZ')}</b></i>")
	except ValueError as e:
		await self_destruct(message, f"<code>{str(e)}</code>")

help_dict["calculator"] = ('Calculator',
'''{prefix}curr <i>[value] [from currency] [to currency]</i> - Convert source currency to dest currency

{prefix}time <i>[TZ database name]</i> - Get the time in the timezone

{prefix}convert <i>value &lt;from unit&gt; &lt;to unit&gt;</i> - Convert between units of measure
Aliases: {prefix}conv, {prefix}vol, {prefix}volume, {prefix}temp, {prefix}lenth, {prefix}len, {prefix}mass

Unit conversion can be any of the units defined in <a href="https://github.com/hgrecco/pint/blob/master/pint/default_en.txt">this document</a>.
You can also provide expressions in quoted arguments such as <code>{prefix}convert 90 mph "light_year/second"</code> which will convert 90
miles per hour to the equivalent light years per second.

''')