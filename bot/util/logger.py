import datetime
import enum
import os
import requests
import socket
import time
import queue

import discord
from discord.ext import commands, tasks


class Logger():
    log_interval = 60.0

    class LogLevel(enum.Enum):
        INFO = 1
        DEBUG = 2
        WARN = 3
        ERROR = 4
        TRACE = 5


    def __init__(self, bot, interval):
        global log_interval

        self.bot: commands.Bot = bot
        self.logpool = queue.Queue()
        self.session_start = None
        self.session_end = None
        self.session_count = 0

        channel = self.bot.get_channel(int(os.environ['DEV_CHANNEL']))
        if channel is None:
            raise Exception(f'Log channel does not exist!')

        self.saved_channel = channel
        self.flush.start()

        log_interval = interval


    @tasks.loop(seconds=log_interval)
    async def flush(self):
        if self.session_start is None:
            return
        
        self.session_end = time.time()
        elapsed = self.session_end - self.session_start
        if elapsed < log_interval:
            return

        msg = f"*SESSION [{datetime.datetime.fromtimestamp(int(self.session_start)).strftime('%Y/%m/%d %H:%M:%S')} - "
        msg += f"{datetime.datetime.fromtimestamp(int(self.session_end)).strftime('%H:%M:%S')}]* "
        msg += f">>> **`{len(self.logpool.queue)}`** commands executed\n"

        while not self.logpool.empty():
            log = self.logpool.get()
            if log is None:
                break
            msg += f'- {log}\n'

        await self.saved_channel.send(msg)
        self.session_start = None
        self.session_end = None

    
    def log(self, msg: str, level: LogLevel = LogLevel.INFO):
        if self.saved_channel is None:
            raise ValueError(f'Log channel has not been initialized!')
        
        if self.session_start is None:
            self.session_start = time.time()

        msg = f"{datetime.datetime.now().strftime('%H:%M:%S')} **[{level.name}]** {msg}"
        self.logpool.put(msg)
        print(msg)

        self.flush.restart()


    async def report_success(self):
        await self.saved_channel.send(embed=discord.Embed(description=f"```\ntime : {datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')}\n"
                                    f"name : {socket.gethostname()}\n"
                                    f"fqdn : {socket.getfqdn()}\n"
                                    f"ipv4 : {socket.gethostbyname(socket.gethostname())}\n"
                                    f"addr : {requests.get('https://api.ipify.org').text}\n```",
                                    color=discord.Color.green(), title=f'{self.bot.user} 已上线!'))


logger: Logger = None


async def setup_logger(bot, interval):
    global logger
    
    logger = Logger(bot, interval)
    await logger.report_success()


def log(msg: str):
    logger.log(msg)
    