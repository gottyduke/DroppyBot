from .gpti import GPTIHandler
from discord.ext import commands


# extension entry
async def setup(bot: commands.Bot):
    await bot.add_cog(GPTIHandler())


# extension exit
async def teardown(bot: commands.Bot):
    await bot.remove_cog("GPTIHandler")
    pass
