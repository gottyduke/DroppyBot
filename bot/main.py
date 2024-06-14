import asyncio
import os

import discord
from discord.ext import commands

import shared
from util.config import load_config
from util.logger import setup_logger, logger

# sneaky
shared.CogBase.sneaky_mode = False

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
enabled_module = {"gpt": True, "trio": True}


async def scan_and_load():
    """
    scan the modules folder and load extension that is determined enabled
    """
    modules = os.path.join(shared.cwd, "modules")
    for module in os.listdir(modules):
        module_dir = os.path.join(modules, module)
        if os.path.isdir(module_dir) and os.path.exists(
            os.path.join(module_dir, "bootstrap.py")
        ):
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
        type=discord.ActivityType[shared.CogBase.config.bot.presence.type],
        name=shared.CogBase.config.bot.presence.name,
        details=shared.CogBase.config.bot.presence.details,
    )
    print(f"updating presence: {activity.type.name} {activity.name} {activity.details}")

    status = (
        discord.Status.invisible
        if shared.CogBase.sneaky_mode
        else discord.Status.online
    )

    return await shared.CogBase.bot.change_presence(activity=activity, status=status)


# initializer
@bot.event
async def on_ready():
    print(f"{bot.user} is launching...")

    # load config and extensions
    config = load_config()
    print(f"runtime version: {config.bot.version}")

    # command prefix
    bot.command_prefix = config.bot.command_prefix

    # stats
    for guild in bot.guilds:
        print(f"serving {guild.name}")

    # init
    init_tasks = [
        setup_logger(bot, shared.CogBase.sneaky_mode),
        scan_and_load(),
        bot.tree.sync(),
        update_presence(),
    ]
    init_tasks = [asyncio.create_task(t) for t in init_tasks]
    await asyncio.gather(*init_tasks)
    logger.log_interval = shared.CogBase.config.bot.log.session_interval

    # finalize
    shared.CogBase.bot_ready = True
    print(f"{bot.user} is now ready!")


# help info
bot.help_command = None


@bot.command()
async def help(ctx: commands.Context, *, payload=None):
    if payload is not None:
        if (
            payload in shared.CogBase.help_info
            and shared.CogBase.help_info[payload] is not None
        ):
            return await ctx.reply(embeds=shared.CogBase.help_info[payload])

    categories = discord.Embed(title="请使用以下命令查看详细类别:")
    categories.description = ""
    for cate in shared.CogBase.help_info:
        categories.description += f"- `{bot.command_prefix}help {cate}`\n"
    categories.set_thumbnail(url=bot.user.display_avatar.url)
    img = f"https://raster.shields.io/badge/Droppy%20Bot-{shared.CogBase.config.bot.version}-green.png?style=for-the-badge&logo=github"
    categories.set_image(url=img)
    src = "https://github.com/gottyduke"
    categories.description += f"\n[机器人黑奴供应者: DK]({src})"

    await ctx.reply(embed=categories)


# online!
shared.CogBase.bot = bot
bot.run(os.environ["BOT_TOKEN"])
