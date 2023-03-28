import os

from shared import CogBase
import discord
from discord.ext import commands
import openai


class GPTHandler(CogBase, commands.Cog):
    def __init__(self):
        openai.api_key = os.environ['OPENAI_KEY']


    @commands.command()
    async def gpt(self, ctx: commands.Context, *, prompt):
        embed = self.as_embed(self.config.gpt.thinking_indicator, ctx.author)
        message = await ctx.reply(embed=embed)

        response = await openai.ChatCompletion.acreate(
            model=self.config.gpt.default_model, 
            messages=[{'role': 'user', 'content': prompt}]) 

        embed.description = f'{response.choices[0].message.content}'
        await message.edit(embed=embed)
        self.log(message, f"`gpt {prompt}` | ({response.usage.prompt_tokens - len(prompt)})+{len(prompt)}+{response.usage.completion_tokens}={response.usage.total_tokens}")


    @commands.command()
    async def gpti(self, ctx: commands.Context, *, prompt):
        embed = self.as_embed(self.config.gpti.painting_indicator, ctx.author)
        message = await ctx.reply(embed=embed)

        response = await openai.Image.acreate(
            prompt=prompt,
            n=1,
            size=self.config.gpti.dimension
        )

        embed = discord.Embed()
        embed.set_image(url=response.data[0].url)
        print(type(response))
        await message.edit(embed=embed)
        self.log(message, f"`gpti {prompt}` | {message.jump_url}")

