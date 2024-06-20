import shared

from modules.trio.trio import TrioHandler


# extension entry
async def setup(bot):
    await shared.CogBase.bot.add_cog(TrioHandler())


# extension exit
async def teardown(bot):
    pass
