import os

from shared import CogBase

import discord
import openai
from discord.ext import commands


class GPTIHandler(CogBase, commands.Cog):

    def __init__(self):
        openai.api_key = os.environ['OPENAI_KEY']

    @commands.command()
    async def gpti(self, ctx: commands.Context, *, prompt: str):
        embed = self.as_embed(self.config.gpti.painting_indicator, ctx.author)
        message = await ctx.reply(embed=embed)

        # check for creation quantity
        tokenized_prompt = prompt.split(' ')
        quantity = 1
        if len(tokenized_prompt) > 1 and tokenized_prompt[0].startswith('x') and tokenized_prompt[0][1].isnumeric():
            quantity = tokenized_prompt[0][1]
            quantity = 1 if quantity < 1 else 10 if quantity > 10 else quantity
            prompt = " ".join(tokenized_prompt[1:])

        # image creation
        responses = await openai.Image.acreate(prompt=prompt, n=quantity, size=self.config.gpti.dimension.large)
        embed.description = self.config.gpti.painting_completed
        await message.edit(embed=embed)

        # if multi-creation
        for res in responses.data:
            await ctx.send(res.url)

        self.log(ctx.message, f"`gpti x{quantity} {prompt}` | {message.jump_url}")
