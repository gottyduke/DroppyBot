from .gpt import GPTHandler
from discord.ext import commands


# extension entry
async def setup(bot: commands.Bot):
    await bot.add_cog(GPTHandler())


# extension exit
async def teardown(bot: commands.Bot):
    await bot.remove_cog("GPTHandler")
    pass
