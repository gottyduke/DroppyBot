import os

from shared import CogBase
import discord
from discord.ext import commands
import openai


class GPTIHandler(CogBase, commands.Cog):
    def __init__(self):
        openai.api_key = os.environ['OPENAI_KEY']


    @commands.command()
    async def gpti(self, ctx: commands.Context, *, prompt):
        embed = self.as_embed(self.config.gpti.painting_indicator, ctx.author)
        message = await ctx.reply(embed=embed)

        response = await openai.Image.acreate(
            prompt=prompt,
            n=1,
            size=self.config.gpti.dimension.default
        )

        embed = discord.Embed()
        embed.set_image(url=response.data[0].url)
        print(type(response))
        await message.edit(embed=embed)
        self.log(message, f"`gpti {prompt}` | {message.jump_url}")
