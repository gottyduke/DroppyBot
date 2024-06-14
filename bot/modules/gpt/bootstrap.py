import os
import shared as shared

from openai import OpenAI
from modules.gpt.chat import GPTHandler
from modules.gpt.image import GPTIHandler
from modules.gpt.tools import GPTTools


# extension entry
async def setup(bot):
    shared.CogBase.endpoint = OpenAI(api_key=os.environ["OPENAI_KEY"])
    await bot.add_cog(GPTHandler())
    await bot.add_cog(GPTIHandler())
    await bot.add_cog(GPTTools())


# extension exit
async def teardown(bot):
    pass
