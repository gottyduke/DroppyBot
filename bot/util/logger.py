import datetime
import enum
import os
import queue
import requests
import socket
import time

import discord
from discord.ext import commands, tasks


class Logger():
    log_interval = 60.0

    class LogLevel(enum.Enum):
        ERROR = 1
        INFO = 2
        WARN = 3
        DEBUG = 4
        TRACE = 6

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.logpool = queue.Queue()
        self.session_start = None
        self.session_end = None
        self.session_count = 0

        channel = self.bot.get_channel(int(os.environ["DEV_CHANNEL"]))
        if channel is None:
            raise RuntimeError("Log channel does not exist!")

        self.saved_channel = channel
        self.flush.start()

    @tasks.loop(seconds=log_interval)
    async def flush(self):
        if self.session_start is None:
            return

        self.session_end = time.time()
        elapsed = self.session_end - self.session_start
        if elapsed < self.log_interval:
            return

        msg = f"*SESSION [{datetime.datetime.fromtimestamp(int(self.session_start)).strftime('%Y/%m/%d %H:%M:%S')} - "
        msg += f"{datetime.datetime.fromtimestamp(int(self.session_end)).strftime('%H:%M:%S')}]* "
        msg += f">>> **`{len(self.logpool.queue)}`** commands executed\n"

        while not self.logpool.empty():
            log = self.logpool.get()
            if log is None:
                break
            msg += f"- {log}\n"

        await self.saved_channel.send(msg)
        self.session_start = None
        self.session_end = None

    def log(self, msg: str, level: LogLevel = LogLevel.INFO):
        if self.saved_channel is None:
            raise ValueError("Log channel has not been initialized!")

        if self.session_start is None:
            self.session_start = time.time()

        msg = f"{datetime.datetime.now().strftime('%H:%M:%S')} **{level.name}** {msg}"
        self.logpool.put(msg)
        msg = msg.replace(level.name, f"\033[9{level.value}m{level.name}\033[0m")\
                 .replace(" **__", " \033[1m\033[4m").replace("__** ", "\033[0m ")\
                 .replace(" **", " \033[1m").replace("** ", "\033[0m ")
        print(msg)

        self.flush.restart()

    async def report_success(self):
        login_info = \
            f"```\ntime : {datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')}\n"\
            f"name : {socket.gethostname()}\n"\
            f"fqdn : {socket.getfqdn()}\n"\
            f"ipv4 : {socket.gethostbyname(socket.gethostname())}\n"\
            f"addr : {requests.get('https://api.ipify.org').text}\n```"

        await self.saved_channel.send(
            embed=discord.Embed(description=login_info, color=discord.Color.green(), title=f"{self.bot.user} 已上线!"))


logger: Logger = None


async def setup_logger(bot):
    global logger

    logger = Logger(bot)
    await logger.report_success()


def log(msg: str):
    logger.log(msg)
