import os

import discord
from discord.ext import commands

from util.config import load_config
from util.logger import setup_logger
import shared

# bot instance
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
intents.presences = True
intents.reactions = True
intents.typing = True
intents.voice_states = True

bot = commands.Bot("!", intents=intents)

# dev flag
enabled_module = {"gpt": True, "tts": False}


async def scan_and_load():
    """
    scan the modules folder and load extension that is determined enabled
    """
    modules = os.path.join(shared.cwd, "modules")
    for module in os.listdir(modules):
        module_dir = os.path.join(modules, module)
        if os.path.isdir(module_dir) and os.path.exists(os.path.join(module_dir, "bootstrap.py")):
            print(f">> loading module >> {module}")
            if module in enabled_module and enabled_module[module]:
                await bot.load_extension(f"modules.{module}.bootstrap")
                print(">> success")
            else:
                print(">> pass")


async def update_presence(activity=None):
    """
    update bot presence from default config value or an specified activity
    """

    activity = activity or discord.Activity(
        type=discord.ActivityType[shared.CogBase.config.bot.presense.type],
        name=shared.CogBase.config.bot.presense.name,
        details=shared.CogBase.config.bot.presense.details,
    )
    print(f"updating presence: {activity.type.name} {activity.name} {activity.details}")

    return await shared.CogBase.bot.change_presence(activity=activity)


# initializer
@bot.event
async def on_ready():
    print(f"{bot.user} is launching...")

    # load config and extensions
    config = load_config()
    print(f"runtime version: {config.runtime.version}")

    await setup_logger(bot)
    await scan_and_load()
    await update_presence()

    # command prefix
    bot.command_prefix = config.bot.command_prefix

    # finalize
    shared.CogBase.bot_ready = True
    print(f"{bot.user} is now ready!")


# online!
shared.CogBase.bot = bot
bot.run(os.environ["BOT_TOKEN"])
