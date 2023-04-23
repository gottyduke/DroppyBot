from modules.gpt.chat import GPTHandler
from modules.gpt.image import GPTIHandler


# extension entry
async def setup(bot):
    await bot.add_cog(GPTHandler())
    await bot.add_cog(GPTIHandler())


# extension exit
async def teardown(bot):
    pass
