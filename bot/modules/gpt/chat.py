import os

import shared
import discord
from discord.ext import commands
import openai


class GPTHandler(shared.CogBase, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        openai.api_key = os.environ['OPENAI_KEY']


    @commands.command()
    async def gpt(self, ctx: commands.Context, *, prompt):
        embed = self.as_embed(shared.gpt_think_node_response, ctx.author)
        message = await ctx.reply(embed=embed)

        response = await openai.ChatCompletion.acreate(
            model=shared.gpt_model_default, 
            messages=[{'role': 'user', 'content': prompt}]) 

        embed.description = f'{response.choices[0].message.content}'
        await message.edit(embed=embed)
        self.log(message, f" `{__name__} {prompt}` | ({response.usage.prompt_tokens - len(prompt)})+{len(prompt)}+{response.usage.completion_tokens}={response.usage.total_tokens}")


    @commands.command()
    async def gpti(self, ctx: commands.Context, *, prompt):
        embed = self.as_embed(shared.gpt_paint_node_response, ctx.author)
        message = await ctx.reply(embed=embed)

        response = await openai.Image.acreate(
            prompt=prompt,
            n=1,
            size="512x512"
        )

        embed = discord.Embed()
        embed.set_image(url=response.data[0].url)
        print(type(response))
        await message.edit(embed=embed)
        self.log(message, f" | {message.jump_url}")

