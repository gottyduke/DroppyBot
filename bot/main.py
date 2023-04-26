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
    print(f"runtime version: {config.bot.version}")

    await setup_logger(bot)
    await scan_and_load()
    await update_presence()

    # command prefix
    bot.command_prefix = config.bot.command_prefix

    # finalize
    shared.CogBase.bot_ready = True
    print(f"{bot.user} is now ready!")


# help info
bot.help_command = None


@bot.command()
async def help(ctx: commands.Context, *, payload=None):
    if payload is not None:
        if payload in shared.CogBase.help_info and shared.CogBase.help_info[payload] is not None:
            return await ctx.reply(embeds=shared.CogBase.help_info[payload])

    catagories = discord.Embed(title="请使用以下命令查看详细类别:")
    catagories.description = ""
    for cata in shared.CogBase.help_info:
        catagories.description += f"- `{bot.command_prefix}help {cata}`\n"
    catagories.set_thumbnail(url=bot.user.display_avatar.url)
    img = f"https://raster.shields.io/badge/Droppy%20Bot-{shared.CogBase.config.bot.version}-green.png?style=for-the-badge&logo=github"
    catagories.set_image(url=img)
    src = "https://github.com/gottyduke"
    catagories.description += f"\n[机器人黑奴供应者: DK]({src})"

    await ctx.reply(embed=catagories)


# online!
shared.CogBase.bot = bot
bot.run(os.environ["BOT_TOKEN"])
