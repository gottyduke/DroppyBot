import os
import shared as shared

from modules.gpt.chat import GPTHandler
from modules.gpt.image import GPTIHandler
from openai import OpenAI


# extension entry
async def setup(bot):
    shared.CogBase.endpoint = OpenAI(api_key=os.environ["OPENAI_KEY"])
    await bot.add_cog(GPTHandler())
    await bot.add_cog(GPTIHandler())


# extension exit
async def teardown(bot):
    pass
