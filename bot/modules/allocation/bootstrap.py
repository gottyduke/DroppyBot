from .allocation import DroppyAllocationManager
from discord.ext import commands


# extension entry
async def setup(bot: commands.Bot):
    await bot.add_cog(DroppyAllocationManager())


# extension exit
async def teardown(bot: commands.Bot):
    await bot.remove_cog("DroppyAllocationManager")
    pass
