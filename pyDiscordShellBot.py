import subprocess
import os
import re
import datetime
import hashlib
import time
import discord
import requests
from inspect import getsourcefile
import textwrap
import psutil

print(os.path.dirname(os.path.abspath(getsourcefile(lambda: 0))))

__author__ = "EnriqueMoran"

__version__ = "v0.0.3"

if os.name == 'nt':
    slashType = "\\"
    print('Nt/Windows found, using \\')
    pingFlag = 'n'
elif os.name == 'posix':
    print('Posix based OS (probably linux) found, using /')
    slashType = "/"
    pingFlag = 'c'
else:
    print('Unknown OS, defaulting to /')
    slashType = "/"
    pingFlag = 'c'

# LOCATIONOVERRIDE detects running location
LOCATIONOVERRIDE = os.getcwd() + slashType
shareInStart = True
VERSION = None
Reboot = True
USERS = "users.txt"  # users.txt path
LOG = "log.txt"  # log.txt path
LOGLINES = 0  # Current lines of log.txt
SHAREFOLDER = None  # Shared files storage folder path
LOGLIMIT = None  # Max number of lines to register in log
GUILD = None  # Server's name
TOKEN = None
PASSWORD = None
ROOT = None
guildID = None
INGUILD = False  # Is this bot running in configured server?
USERSLOGIN = []  # List of users id waiting for pass to be added
USERSUPDATE = []  # List of users id waiting to update system's response
USERSUPGRADE = []  # List of users id waiting to upgrade system's response
USERSINSTALL = []  # List of users id waiting to install a package
USERSUNINSTALL = []  # List of users id waiting to uninstall a package
USERSREBOOT = []  # List of users id waiting to reboot, cleared after 5 messages
rebootTime = 0
AVALIABLECOMMANDS = [
    "/start", "/update", "/upgrade", "/install", "/uninstall", "/forbidden",
    "/help", "/reboot", "/killall"
]
FORBIDDENCOMMANDS = [
    "wait", "exit", "clear", "aptitude", "raspi-config",
    "nano", "dc", "htop", "ex", "expand", "vim", "man", "apt-get", "poweroff",
    "reboot", "ssh", "scp", "wc", "vi", "apt", "powershell", "cmd"
]  # non working commands due to API error or output error


def load_config(configFile):
    global VERSION, TOKEN, PASSWORD, USERS, LOG, LOGLIMIT, ROOT, \
        SHAREFOLDER, LOGLINES, GUILD, INGUILD
    if LOCATIONOVERRIDE:
        configFile = LOCATIONOVERRIDE + configFile
    print(configFile)
    file = open(configFile, "r")
    lines = file.read().splitlines()
    cont = 0
    read = False

    for line in lines:
        if cont == 5 and line[:1] != "" and read is True:
            VERSION = [file.strip() for file in line.split('=')][1]
            read = False
        if cont == 6 and line[:1] != "" and read is True:
            TOKEN = [file.strip() for file in line.split('=')][1]
            read = False
        if cont == 8 and line[:1] != "" and read is True:
            GUILD = [file.strip() for file in line.split('=')][1]
            read = False
        if cont == 11 and line[:1] != "" and read is True:
            PASSWORD = [file.strip() for file in line.split('=')][1]
            read = False
        if cont == 14 and line[:1] != "" and read is True:
            SHAREFOLDER = [file.strip() for file in line.split('=')][1]
            read = False
        if cont == 18 and line[:1] != "" and read is True:
            USERS = [file.strip() for file in line.split('=')][1]
            read = False
        if cont == 21 and line[:1] != "" and read is True:
            LOG = [file.strip() for file in line.split('=')][1]
            read = False
        if cont == 22 and line[:1] != "" and read is True:
            LOGLIMIT = int([file.strip() for file in line.split('=')][1])
            read = False
        if cont == 25 and line[:1] != "" and read is True:
            ROOT = bool([file.strip() for file in line.split('=')][1])
            read = False
        if line[:1] == "#":
            cont += 1
            read = True
    LOG = LOCATIONOVERRIDE + LOG
    USERS = LOCATIONOVERRIDE + USERS
    if shareInStart:
        SHAREFOLDER = LOCATIONOVERRIDE + SHAREFOLDER


raw_config_path = "config.txt"
load_config(raw_config_path)

f1 = open(LOG, "a+")
f1.close
f2 = open(USERS, "a+")
f2.close

with open(LOG) as f:
    LOGLINES = sum(1 for _ in f)

os.makedirs(SHAREFOLDER, exist_ok=True)

client = discord.Client()


async def check_config(message):
    # TODO: CURRENTLY NOT USED, USE IT ON WELCOME MESSAGE
    error = False
    error_msg = "Config file not properly filled, errors:"
    if "./" in SHAREFOLDER:
        error = True
        error_msg += "\n- Share Folder path field is empty."
    if PASSWORD == "":
        error = True
        error_msg += "\n- Password field is empty."
    if USERS == "":
        error = True
        error_msg += "\n- Users File path field is empty."
    if "./" in USERS:
        error = True
        error_msg += "\n- Users File path is relative."
    if LOG == "":
        error = True
        error_msg += "\n- Log File path field is empty."
    if "./" in LOG:
        error = True
        error_msg += "\n- Log File path is relative."
    if LOGLIMIT == "":
        error = True
        error_msg += "\n- Log limit field is empty."
    if ROOT == "":
        error = True
        error_msg += "\n- Root field is empty."
    if error:
        await message.channel.send(error_msg)
    return error


def in_guild(func):  # Check if bot is in configured server
    def wrapper(*args, **kwargs):
        if INGUILD:
            return func(*args, **kwargs)
        return wrapper


def encrypt(uid):  # Cipher users.txt content using SHA256
    m = hashlib.sha256()
    m.update(str(uid).encode())
    return m.hexdigest()


def register(user):  # Register user and allow him to access
    encrypted_user = encrypt(user)
    file = open(USERS, "a+")
    content = file.readlines()
    content = [x.strip() for x in content]
    if encrypted_user not in content:
        f.write(str(encrypted_user) + "\n")
    file.close


def check_user_login(login):  # Check if user ID is on users.txt
    encrypted_login = encrypt(login)
    check = False
    with open(USERS) as file:
        content = file.readlines()
        content = [x.strip() for x in content]
        if encrypted_login in content:
            check = True
    return check


def register_log(message):  # Register message in log.txt
    global LOGLIMIT, LOG, LOGLINES
    LOGLINES += 1
    with open(LOG, 'a+') as file:
        now = datetime.datetime.now().strftime("%m-%d-%y %H:%M:%S ")
        file.write(now + "[" + str(message.author.name) + " (" + str(message.author.id) + ")]: " +
                   str(message.content) + "\n")
    if 0 < LOGLIMIT < LOGLINES:
        with open(LOG) as file:
            lines = file.read().splitlines(True)
        with open(LOG, 'w+') as file:
            file.writelines(lines[abs(LOGLINES - LOGLIMIT):])


async def updateSystem(message):
    try:
        proc = subprocess.Popen('sudo apt-get update -y', shell=True,
                                stdin=None, stdout=subprocess.PIPE,
                                executable="/bin/bash")
        while True:
            output = proc.stdout.readline()
            if output == b'' and proc.poll() is not None:
                break
            if output:
                await message.channel.send(output.decode('utf-8'))
        proc.wait()

        if proc.poll() == 0:
            await message.channel.send("System updated sucessfully.")
        else:
            await message.channel.send("System not updated" +
                                       ", error code: " + str(proc.poll()))
    except Exception as e:
        error = "Error ocurred: " + str(e)
        errorType = "Error type: " + str(e.__class__.__name__)
        await message.channel.send(str(error))
        await message.channel.send(str(errorType))


async def killAll(message):
    try:
        me = psutil.Process(os.getpid())
        for child in me.children():
            child.kill()
    except Exception as e:
        error = "Error ocurred: " + str(e)
        errorType = "Error type: " + str(e.__class__.__name__)
        await message.channel.send(str(error))
        await message.channel.send(str(errorType))


async def upgradeSystem(message):
    try:
        proc = subprocess.Popen('sudo apt-get upgrade -y', shell=True,
                                stdin=None, stdout=subprocess.PIPE,
                                executable="/bin/bash")
        while True:
            output = proc.stdout.readline()
            if output == b'' and proc.poll() is not None:
                break
            if output:
                await message.channel.send(output.decode('utf-8'))
        proc.wait()

        if proc.poll() == 0:
            await message.channel.send("System upgraded sucessfully.")
        else:
            await message.channel.send("System not upgraded" +
                                       ", error code: " + str(proc.poll()))
    except Exception as e:
        error = "Error ocurred: " + str(e)
        errorType = "Error type: " + str(e.__class__.__name__)
        await message.channel.send(str(error))
        await message.channel.send(str(errorType))


async def reboot(message):
    try:
        proc = subprocess.Popen('systemctl reboot -i', shell=True,
                                stdin=None, stdout=subprocess.PIPE,
                                executable="/bin/bash")
        while True:
            output = proc.stdout.readline()
            if output == b'' and proc.poll() is not None:
                break
            if output:
                await message.channel.send(output.decode('utf-8'))
        proc.wait()
        if proc.poll() == 0:
            await message.channel.send("System rebooted sucessfully.")
        else:
            await message.channel.send("System not rebooted" +
                                       ", error code: " + str(proc.poll()))
    except Exception as e:
        error = "Error ocurred: " + str(e) + "\nError type: " + str(e.__class__.__name__)
        await message.channel.send(str(error))


async def installPackage(message):
    try:
        proc = subprocess.Popen('sudo apt-get install -y ' + message.content,
                                shell=True, stdin=None,
                                stdout=subprocess.PIPE, executable="/bin/bash")
        already_installed = False

        while True:
            output = proc.stdout.readline()
            already_installed = (already_installed or
                                 "0 newly installed" in str(output))
            if output == b'' and proc.poll() is not None:
                break
            if output:
                await message.channel.send(output.decode('utf-8'))
        proc.wait()

        if already_installed:
            return  # Dont send any message
        if proc.poll() == 0:
            await message.channel.send(f"Package {message.content} " +
                                       "sucessfully installed.")
        else:
            await message.channel.send(f"Package {message.content} " +
                                       "not installed. Error code: " +
                                       str(proc.poll()))
    except Exception as e:
        error = "Error ocurred: " + str(e)
        errorType = "Error type: " + str(e.__class__.__name__)
        await message.channel.send(str(error))
        await message.channel.send(str(errorType))


async def removePackage(message):
    try:
        proc = subprocess.Popen('sudo apt-get --purge remove -y ' +
                                message.content, shell=True, stdin=None,
                                stdout=subprocess.PIPE,
                                executable="/bin/bash")
        already_removed = False

        while True:
            output = proc.stdout.readline()
            already_removed = (already_removed or
                               "0 to remove" in str(output))
            if output == b'' and proc.poll() is not None:
                break
            if output:
                await message.channel.send(output.decode('utf-8'))
        proc.wait()

        if already_removed:
            return  # Dont send any message
        if proc.poll() == 0:
            await message.channel.send(f"Package {message.content} " +
                                       "sucessfully removed.")
        else:
            await message.channel.send(f"Package {message.content} " +
                                       "not removed. Error code: " +
                                       str(proc.poll()))
    except Exception as e:
        error = "Error ocurred: " + str(e)
        errorType = "Error type: " + str(e.__class__.__name__)
        await message.channel.send(str(error))
        await message.channel.send(str(errorType))


async def show_forbidden_commands(message):
    res = ""
    for element in FORBIDDENCOMMANDS:
        res += element + ", "
    await message.channel.send(res[:-2])


async def show_help(message):
    global VERSION
    message_one = "Current version: " + VERSION + "\n" + "Welcome to remoteDiscordShell, this bot allows users " + \
                  "to remotely control a computer terminal. Current commands: \n" + \
                  ", ".join(AVALIABLECOMMANDS)
    await message.channel.send(message_one)


@client.event
async def on_ready():
    global TOKEN, GUILD, INGUILD, guildID

    guild = discord.utils.get(client.guilds, id=GUILD)
    discord.utils.get(client.guilds)
    number = 0
    for guilds in client.guilds:

        if f'{GUILD}' == f'{guilds}':
            INGUILD = True
            print("Server found! running...")
            guildID = client.guilds[number].id
            return
    if INGUILD:
        print("No server found... Press ctrl+c to exit.")


@in_guild
@client.event
async def on_message(message):
    global USERSLOGIN, VERSION, FORBIDDENCOMMANDS, ROOT, USERSUPDATE, \
        USERSUPGRADE, USERSINSTALL, USERSUNINSTALL, rebootTime, \
        USERSREBOOT, guildID

    if message.author.bot:
        return

    if message.guild.id != guildID:
        return

    if message.author == client.user:
        return

    register_log(message)
    if not rebootTime == 0:
        if message.author.id in USERSREBOOT and message.content.lower() == 'yes':
            USERSREBOOT = []
            rebootTime = 0
            await reboot(message)
        elif rebootTime >= 5 or (message.content.lower() == 'no' and message.author.id in USERSREBOOT):
            USERSREBOOT = []
            rebootTime = 0
        else:
            rebootTime = rebootTime + 1

    if message.author.id in USERSLOGIN:  # User must add password to access
        if message.content == PASSWORD:
            register(message.author.id)  # Grant access to user
            USERSLOGIN.remove(message.author.id)
            response = "Logged in, you can use commands now."
            await message.author.dm_channel.send(response)
            return

    if not check_user_login(message.author.id):
        USERSLOGIN.append(message.author.id)  # Waiting for pass to be written
        await message.author.create_dm()
        response = "Please log in, insert password:"
        await message.author.dm_channel.send(response)
        return

    if message.author.id in USERSUPDATE:
        # User must reply whether update system or not
        if message.content.lower() == 'yes':
            USERSUPDATE.remove(message.author.id)
            response = "System updating..."
            await message.channel.send(response)
            await updateSystem(message)
        elif message.content.lower() == 'no':
            USERSUPDATE.remove(message.author.id)
            response = "System won't update."
            await message.channel.send(response)
        else:
            response = "Please reply 'yes' or 'no'."
            await message.channel.send(response)
        return

    if message.author.id in USERSUPGRADE:
        # User must reply whether upgrade system or not
        if message.content.lower() == 'yes':
            USERSUPGRADE.remove(message.author.id)
            response = "System upgrading..."
            await message.channel.send(response)
            await upgradeSystem(message)
        elif message.content.lower() == 'no':
            USERSUPGRADE.remove(message.author.id)
            response = "System won't upgrade."
            await message.channel.send(response)
        else:
            response = "Please reply 'yes' or 'no'."
            await message.channel.send(response)
        return

    if not check_user_login(message.author.id):
        USERSLOGIN.append(message.author.id)  # Waiting for pass to be written
        await message.author.create_dm()
        response = "Please log in, insert password:"
        await message.author.dm_channel.send(response)
        return

    if message.author.id in USERSINSTALL:
        # User must reply which package to install
        if message.content.lower() == 'cancel':
            USERSINSTALL.remove(message.author.id)
            response = "No package will be installed."
            await message.channel.send(response)
        else:
            USERSINSTALL.remove(message.author.id)
            response = "Trying to install package..."
            await message.channel.send(response)
            await installPackage(message)
        return

    if message.author.id in USERSUNINSTALL:
        # User must reply which package to install
        if message.content.lower() == 'cancel':
            USERSINSTALL.remove(message.author.id)
            response = "No package will be removed."
            await message.channel.send(response)
        else:
            USERSINSTALL.remove(message.author.id)
            response = "Trying to remove package..."
            await message.channel.send(response)
            await removePackage(message)
        return

    if len(message.attachments) > 0:  # A file is sent
        attachments = 0
        for _ in message.attachments:
            file_path = f'{SHAREFOLDER}' + message.attachments[attachments].filename
            r = requests.get(message.attachments[attachments].url)
            with open(file_path, 'wb') as file:
                file.write(r.content)
            await message.channel.send(f"File saved as {file_path}")

    else:
        if message.content.lower() == '/start':  # TODO: TMP welcome message
            welcome_one = "Welcome to discordShell, this bot allows " + \
                          "you to remotely control a computer terminal."
            welcome_two = "List of avaliable commands: \n- To " + \
                          "install packages use /install \n- To update system " + \
                          "use /update \n- To upgrade system use /upgrade" \
                          "To reboot system, use /reboot\n" \
                          "To kill **ALL** processes, use /killall \n" \
                          "- To view forbidden commands use /forbidden."
            welcome_three = "You can send files to the computer, " + \
                            "also download them by using getfile + path (e.g. getfile" + \
                            " /home/user/Desktop/file.txt)."
            await message.channel.send(f"Current version: {VERSION}")
            await message.channel.send(welcome_one)
            await message.channel.send(welcome_two)
            await message.channel.send(welcome_three)
        elif message.content.lower() == '/update':  # Update system
            await message.channel.send("Update system? (Write yes/no): ")
            USERSUPDATE.append(message.author.id)  # Waiting for response
        elif message.content.lower() == '/upgrade':  # Upgrade system
            await message.channel.send("Upgrade system? (Write yes/no): ")
            USERSUPGRADE.append(message.author.id)  # Waiting for response
        elif message.content.lower() == '/killall':
            await killAll(message)
        elif message.content.lower() == '/reboot':  # Reboot system
            if Reboot:
                await message.channel.send("Reboot system? (Write yes/no): ")
                USERSREBOOT.append(message.author.id)  # Waiting for response
                rebootTime = 1
            else:
                await message.channel.send("Rebooting has been disabled ")
        elif message.content.lower() == '/install':  # Install package
            await message.channel.send("Write package name to install or " +
                                       "'cancel' to exit: ")
            USERSINSTALL.append(message.author.id)  # Waiting for response
        elif message.content.lower() == '/uninstall':  # Remove package
            await message.channel.send("Write package name to uninstall or " +
                                       "'cancel' to exit: ")
            USERSUNINSTALL.append(message.author.id)  # Waiting for response
        elif message.content.lower() == '/forbidden':  # Forbidden commands
            await message.channel.send("Currently forbidden commands:")
            await show_forbidden_commands(message)
        elif message.content.lower() == '/help':  # Show help message
            await show_help(message)
        else:  # Linux command
            if message.content[0:2] == 'cd':
                try:
                    os.chdir(message.content[3:])
                    await message.channel.send("Current directory: " +
                                               str(os.getcwd()))
                except Exception as e:
                    await message.channel.send(str(e))

            elif message.content.split()[0] in FORBIDDENCOMMANDS:
                await message.channel.send("Forbidden command.")

            elif message.content[0:4] == "sudo" and not ROOT:
                await message.channel.send("root commands are disabled.")

            elif message.content[0:3] == "top":
                try:
                    com = "top -b -n 1 |  \
                    awk '{print $1, $2, $5, $8, $9, $10, $NF}' > \
                    Qv0g09khgKtop4A80GUjQvU.txt"
                    p = subprocess.Popen(com, stdout=subprocess.PIPE,
                                         shell=True, cwd=os.getcwd(),
                                         bufsize=1)
                    time.sleep(1)

                    com = "cat Qv0g09khgKtop4A80GUjQvU.txt"
                    p = subprocess.Popen(com, stdout=subprocess.PIPE,
                                         shell=True, cwd=os.getcwd(),
                                         bufsize=1)

                    file = discord.File('Qv0g09khgKtop4A80GUjQvU.txt')
                    await message.channel.send(files=[file])

                    time.sleep(1)
                    com = "rm Qv0g09khgKtop4A80GUjQvU.txt"
                    p = subprocess.Popen(com, stdout=subprocess.PIPE,
                                         shell=True, cwd=os.getcwd(),
                                         bufsize=1)
                except Exception as e:
                    error = "Error ocurred: " + str(e)
                    errorType = "Error type: " + str(e.__class__.__name__)
                    await message.channel.send(str(error))
                    await message.channel.send(str(errorType))

            elif message.content[0:7] == "getfile":
                file_path = os.path.join(message.content[7:].strip())
                if os.path.isfile(file_path):
                    await message.channel.send("Sending file.")
                    file = discord.File(file_path)
                    await message.channel.send(files=[file])
                else:
                    await message.channel.send("File doesn't exists.")

            elif (
                    message.content[0:4] == "ping" and
                    len(message.content.split()) == 2
            ):
                ip = str(message.content).split()[1]
                com = "ping " + str(ip) + f" -{pingFlag} 4"  # Infinite ping fix
                try:
                    p = subprocess.Popen(com, stdout=subprocess.PIPE,
                                         shell=True, cwd=os.getcwd(),
                                         bufsize=1)
                    for line in iter(p.stdout.readline, b''):
                        try:
                            await message.channel.send(line.decode('utf-8'))
                        except Exception:
                            pass
                    p.communicate()
                    if p.returncode != 0:
                        await message.channel.send(" Name or " +
                                                   "service not known")
                except Exception as e:
                    error = "Error ocurred: " + str(e)
                    errorType = "Error type: " + str(e.__class__.__name__)
                    await message.channel.send(str(error))
                    await message.channel.send(str(errorType))

            else:
                try:
                    if message.content.lower == 'yes':
                        raise FileNotFoundError
                    p = subprocess.Popen(message.content,
                                         stdout=subprocess.PIPE,
                                         shell=True, cwd=os.getcwd(),
                                         bufsize=1)

                    lines = []
                    for line in iter(p.stdout.readline, b''):
                        try:
                            lines.append(line.decode('utf-8'))
                        except Exception as e:
                            try:
                                lines.append(str(e))
                            except Exception:
                                pass
                    if len(lines) > 2:
                        lineString = "\0".join(lines)
                        if len(lineString) > 1980:
                            await message.channel.send(
                                "Message output larger than discord's limit, cutting into 2000 character clumps")
                            x = list(textwrap.fill(lineString, 1980).split("\n"))
                            for y in x:
                                try:
                                    z = y.replace("\0", "\n")
                                    await message.channel.send(str(z))
                                except Exception as n:
                                    await message.channel.send("Error sending message: " + n)
                        else:
                            await message.channel.send(lineString)
                    elif len(lines) <= 0:
                        await message.channel.send("܁")
                    else:
                        for line in lines:
                            try:
                                await message.channel.send(line)
                            except Exception:
                                pass

                    for line in iter(p.stdout.readline, b''):
                        decoded = line.decode('windows-1252').strip()
                        if len(re.sub('[^A-Za-z0-9]+', '', decoded)) <= 0:
                            # Empty message that raises api 400 error
                            # Send special blank character (U+0701)
                            await message.channel.send("܁")
                        else:
                            try:
                                await message.channel.send(
                                    line.decode('utf-8'))
                            except Exception as e:
                                await message.channel.send(str(e))
                    p.communicate()
                    p.wait()
                    if p.returncode != 0:
                        pass
                except FileNotFoundError as e:
                    # todo replace ^ w/ exception
                    error = "Error: Command not found " + str(e)
                    await message.channel.send(error)
    return


client.run(TOKEN)
