import os
import re
import html
import asyncio
from time import sleep
from io import BytesIO
from pyrogram import Client, filters
from .. import config, help_dict, log_errors, public_log_errors, self_destruct

# All the processes we've started
processes = {}

def _dumb_wait(pid, timeout):
    time = 0
    try:
        while time < timeout:
            blah, idk = os.waitpid(pid, os.WNOHANG)
            if not blah:
                sleep(1)
                time += 1
            else:
                return True
    except ChildProcessError as e:
        if e.errno == 10:
            return True
        # Assume it never exited
        return False

    return False

SHELL_REGEX = '^(?:' + '|'.join(map(re.escape, config['config']['prefixes'])) + r')(?:(?:ba)?sh|shell|term(?:inal)?)\s+(.+)(?:\n([\s\S]+))?$'
@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & ~filters.forwarded & filters.me & filters.regex(SHELL_REGEX))
@log_errors
@public_log_errors
async def shell(client, message):
    match = re.match(SHELL_REGEX, message.text.markdown)
    if not match:
        return
    command = message.matches[0].group(1)
    stdin = message.matches[0].group(2)
    process = await asyncio.create_subprocess_shell(command, stdin=asyncio.subprocess.PIPE if stdin else None, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    process.cmdline = command
    processes[process.pid] = process
    reply = await message.reply_text(f'Executing process {process.pid}...')
    stdout, stderr = await process.communicate(stdin.encode() if stdin else None)
    returncode = process.returncode
    text = f'<b>Exit Code:</b> <code>{returncode}</code>\n'
    if process.pid in processes:
        del processes[process.pid]
    stdout = stdout.decode().replace('\r', '').strip('\n').rstrip()
    stderr = stderr.decode().replace('\r', '').strip('\n').rstrip()
    if stderr:
        text += f'<code>{html.escape(stderr)}</code>\n'
    if stdout:
        text += f'<code>{html.escape(stdout)}</code>'

    # send as a file if it's longer than 4096 bytes
    if len(text) > 4096:
        out = stderr.strip() + "\n" + stdout.strip()
        f = BytesIO(out.strip().encode('utf-8'))
        f.name = "output.txt"
        await reply.delete()
        await message.reply_document(f, caption=f'<b>Exit Code:</b> <code>{returncode}</code>')
    else:
        await reply.edit_text(text)

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['kill', 'terminate'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def terminate(client, message):
    print("Received kill:", message.command)
    command = message.command
    command.pop(0)
    if command:
        try:
            pid = int(command[0])
        except ValueError:
            await self_destruct(message, f'<code>"{command[0]}" is not a valid process id.</code>')
            return

        process = None
        if pid in processes:
            process = processes[pid]
        else:
            await self_destruct(message, f'<code>{pid} is not a process started by us</code>')
            return

        print("Terminating!")
        process.terminate()
        if not _dumb_wait(process.pid, 30):
            await message.edit(f"<code>Sending SIGKILL to the process.</code>")
            process.kill()
            if not _dumb_wait(process.pid, 30):
                await message.edit(f'<code>{pid} is a cockroach and cannot be killed.</code>')
            else:
                if pid in processes:
                    del processes[pid]
                await message.edit(f'<code>Child {pid} was murdered successfully! \N{hocho}</code>')
        else:
            if pid in processes:
                del processes[pid]
            await self_destruct(message, f'<code>{pid} terminated successfully!</code>')
    else:
        await self_destruct(message, "<code>You must specify a process ID to terminate</code>")

@Client.on_message(~filters.sticker & ~filters.via_bot & ~filters.edited & filters.me & filters.command(['jobs'], prefixes=config['config']['prefixes']))
@log_errors
@public_log_errors
async def jobs(client, message):
    text = "<b>List of running background tasks:</b>\n"
    for p, j in processes.items():
        text += f"<b>{j.pid}:</b> <code>{j.cmdline}</code>\n"
    await message.edit(text)


help_dict['shell'] = ('Shell',
'''{prefix}sh <i>&lt;command&gt;</i> \\n <i>[stdin]</i> - Executes <i>&lt;command&gt;</i> in shell
Aliases: {prefix}bash, {prefix}shell, {prefix}term, {prefix}terminal

{prefix}kill <i>&lt;pid&gt;</i> - Kills a process based on it's pid
Aliases: {prefix}terminate

{prefix}jobs - Lists the running background processes (if any)
''')
