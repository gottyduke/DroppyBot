import asyncio
import common.logger as logger
import common.helper as helper
import discord
import discord.app_commands as app
import os

try:
    import modules.secrets
except ModuleNotFoundError:
    """
    if secrets not present in current workspace
    os.envi[] attempts should stop bot from running
    """
    pass

from common.cog import DroppyCog
from common.config import load_config
from common.translator import DroppyTranslator
from discord.ext import commands
from typing import Optional


DroppyCog.config = load_config()
DroppyCog.cwd = os.path.realpath(os.path.dirname(__file__))
DroppyCog.enabled_modules = {
    "allocation": True,
    "gpt": True,
    "gpti": True,
    "trio": False,
}
DroppyCog.on_maintenance = False
DroppyCog.sneaky_mode = False
localization_storage = os.path.join(
    DroppyCog.cwd, DroppyCog.config.bot.localization.storage
)
DroppyCog.translator = DroppyTranslator(localization_storage)


class DroppyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.check(DroppyCog.prepass)

    async def scan_and_load(self):
        """
        scan the modules folder and load extension that is determined enabled
        """
        modules = os.path.join(DroppyCog.cwd, "modules")
        for module in os.listdir(modules):
            module_dir = os.path.join(modules, module)
            if os.path.isdir(module_dir) and os.path.exists(
                os.path.join(module_dir, "bootstrap.py")
            ):
                print(f">> loading module >> {module}")
                if (
                    module in DroppyCog.enabled_modules
                    and DroppyCog.enabled_modules[module]
                ):
                    await DroppyCog.bot.load_extension(f"modules.{module}.bootstrap")
                    print(">> success")
                else:
                    print(">> pass")

    async def setup_hook(self):
        await self.scan_and_load()
        await self.tree.set_translator(DroppyCog.translator)
        await self.tree.sync()


DroppyCog.bot = DroppyBot(
    DroppyCog.config.bot.command_prefix,
    help_command=None,
    intents=discord.Intents.all(),
)


async def update_presence(activity: Optional[discord.Activity] = None):
    """
    update bot presence from default config value or an specified activity
    """

    activity = activity or discord.Activity(
        type=discord.ActivityType[DroppyCog.config.bot.presence.type],
        name=DroppyCog.config.bot.presence.name,
        details=DroppyCog.config.bot.presence.details,
    )
    print(f"updating presence: {activity.type.name} {activity.name} {activity.details}")

    status = (
        discord.Status.invisible
        if (DroppyCog.sneaky_mode or DroppyCog.on_maintenance)
        else discord.Status.online
    )

    await DroppyCog.bot.change_presence(activity=activity, status=status)
    return


async def category_autocomplete(ctx: commands.Context, buffer: str):
    return [
        app.Choice(name=category, value=category)
        for category in DroppyCog.help_info.keys()
        if buffer.lower() in category.lower()
    ]


@DroppyCog.bot.hybrid_command(description="help_desc")
@app.rename(category="help_category")
@app.describe(category="help_category_desc")
@app.autocomplete(category=category_autocomplete)
@helper.sanitize
@DroppyCog.failsafe_ref()
async def help(ctx: commands.Context, *, category: Optional[str] = None):
    ref = await DroppyCog.get_ctx_ref(ctx)
    locale = DroppyCog.get_ctx_locale(ctx)

    if category:
        category = category.upper()
        if category in DroppyCog.help_info and DroppyCog.help_info[category]:
            await DroppyCog.help_info[category](ref)
            return

    img = f"https://raster.shields.io/badge/Droppy%20Bot-{DroppyCog.config.bot.version}-green.png?style=for-the-badge&logo=github"
    help_detail = DroppyCog.translate("help_detail", locale)
    categories = (
        discord.Embed(title=help_detail, description="")
        .set_thumbnail(url=DroppyCog.bot.user.display_avatar.url)
        .set_image(url=img)
    )
    for cate in DroppyCog.help_info:
        categories.description += f"- `help {cate}`\n"

    src = "https://github.com/gottyduke"
    footer = DroppyCog.translate("help_footer", locale)
    categories.description += f"\n{helper.jump_url(footer, src)}"

    await ref.edit(embed=categories)


@DroppyCog.bot.event
async def on_command_error(ctx: commands.Context, e: commands.CommandError):
    if isinstance(e, commands.CheckFailure):
        pass
    else:
        await commands.Bot.on_command_error(DroppyCog.bot, ctx, e)


# initializer
@DroppyCog.bot.event
async def on_ready():
    # logger
    logger.setup_logger(DroppyCog.bot)

    print(f"{DroppyCog.bot.user} is launching...")
    print(f"runtime version: {DroppyCog.config.bot.version}")

    # stats
    for i, guild in enumerate(DroppyCog.bot.guilds):
        print(f"serving: #{i} [{guild.name}]")

    # init
    init_tasks = [
        update_presence(),
    ]
    init_tasks = list(map(asyncio.create_task, init_tasks))
    await asyncio.gather(*init_tasks)

    # finalize
    DroppyCog.bot_ready = True
    print(f"{DroppyCog.bot.user} is now ready!")
    if not DroppyCog.sneaky_mode:
        await logger.logger.report_success()


# online!
DroppyCog.bot.run(os.environ["BOT_TOKEN"])
