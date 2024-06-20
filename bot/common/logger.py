import asyncio
import common.helper as helper
import discord
import enum
import os
import queue
import requests
import socket
import time

from datetime import datetime, timezone, timedelta
from discord.ext import commands, tasks


class Logger:
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
        if not channel:
            raise RuntimeError("Log channel does not exist or unable to fetch")

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

        session_start_time = datetime.fromtimestamp(self.session_start, tz=timezone.utc)
        session_start_time += timedelta(hours=-5)
        session_end_time = datetime.fromtimestamp(self.session_end, tz=timezone.utc)
        session_end_time += timedelta(hours=-5)
        msg = f"*SESSION [{session_start_time.strftime('%Y/%m/%d %H:%M:%S')} - "
        msg += f"{session_end_time.strftime('%H:%M:%S')}]* "
        msg += f">>> **`{len(self.logpool.queue)}`** command(s) executed\n"
        await self.saved_channel.send(msg, silent=True)

        while not self.logpool.empty():
            log_entry, level = self.logpool.get()
            if not log_entry:
                break
            if level == self.LogLevel.ERROR:
                log_entry += f"\n<@{os.environ['DEV_ID']}>"
            for chunk in helper.chunk_with_size(log_entry, 1800):
                await self.saved_channel.send(chunk, silent=True)

        self.session_start = None
        self.session_end = None

    @staticmethod
    def normalized_console_output(msg: str, level: LogLevel):
        console_normalization = {
            " **__": " \033[1m\033[4m",
            "__** ": "\033[0m ",
            " **": " \033[1m",
            "** ": "\033[0m ",
            "```": "\n",
        }

        msg = msg.replace(level.name, f"\033[9{level.value}m{level.name}\033[0m")
        for deco, norm in console_normalization.items():
            msg = msg.replace(deco, norm)

        return msg

    def log(self, msg: str, level=LogLevel.INFO):
        if not self.saved_channel:
            raise RuntimeError(
                "Log channel has not been initialized or unable to fetch"
            )

        if not self.session_start:
            self.session_start = time.time()

        msg = f"{helper.timestamp_now('%H:%M:%S')} **{level.name}** {msg}"
        self.logpool.put((msg, level))

        print(self.normalized_console_output(msg, level))

        self.flush.restart()

    async def report_success(self):
        fallback_ip = "N/A"
        try:
            ip = requests.get("https://api.ipify.org", timeout=5).text
        except requests.RequestException:
            ip = fallback_ip

        login_info = (
            f"```\ntime : {helper.timestamp_now('%Y/%m/%d %H:%M:%S')}\n"
            f"fqdn : {socket.getfqdn()}\n"
            f"ipv4 : {socket.gethostbyname(socket.gethostname())}\n"
            f"addr : {ip}\n```"
        )

        await self.saved_channel.send(
            embed=discord.Embed(
                description=login_info,
                color=discord.Color.green(),
                title=f"{self.bot.user} 已上线!",
            )
        )


logger: Logger = None


def setup_logger(bot):
    global logger

    logger = Logger(bot)


def change_interval(seconds):
    logger.flush.change_interval(seconds=seconds)
    logger.flush.restart()


def log(msg: str):
    logger.log(msg)


def error(msg: str, *, mention=True):
    level = Logger.LogLevel.ERROR if mention else Logger.LogLevel.WARN
    logger.log(msg, level)
