import os
import sys

from shared import CogBase
import discord
from discord.ext import commands
import openai


class GPTHandler(CogBase, commands.Cog):
    def __init__(self):
        openai.api_key = os.environ['OPENAI_KEY']
        self.user_init = {int: str}
        self.user_ctx = {int: [(discord.Message, discord.Message)]}


    @commands.command()
    async def gpt(self, ctx: commands.Context, *, prompt):
        if await self.prepass(ctx.message) is None:
            return

        embed = self.as_embed(self.config.gpt.thinking_indicator, ctx.author)
        message = await ctx.reply(embed=embed)

        # calc max tokens allowed for contextual gpt
        aid = ctx.author.id
        prompts = []
        tokens = next(model for model in self.config.gpt.model.available if model['name'] == self.config.gpt.model.default)['max_token']
        tokens = int(tokens * self.config.gpt.contextual.max_ctx_percentage)
        tokens -= len(prompt)

        # prepend system init, for RP purpose or preset guidelienes
        if aid in self.user_init and self.user_init[aid] is not None:
            prompts.append({'role': 'system', 'content': self.user_init[aid]})
            tokens -= len(self.user_init[aid])

        # construct context
        if aid in self.user_ctx and self.user_ctx[aid] is not None:
            for history, answer in reversed(self.user_ctx[aid]):
                if (ctx.message.created_at - history.created_at).total_seconds() <= \
                    self.config.gpt.contextual.in_memory_timeframe:
                    consumed_tokens = len(history.content) + len(answer.embeds[0].description)
                    tokens -= consumed_tokens
                    if tokens >= 0:
                        prompts.append({'role': 'user', 'content': history.content})
                        prompts.append({'role': 'assistant', 'content': answer.embeds[0].description})
                    else:
                        break
                else:
                    self.user_ctx[aid].remove((history, answer))
        
        # gpt request
        prompts.append({'role': 'user', 'content': prompt})
        response = await openai.ChatCompletion.acreate(
            model=self.config.gpt.model.default, 
            messages=prompts) 

        # respond to user
        embed.description = f'{response.choices[0].message.content}'
        message = await message.edit(embed=embed)

        # save user specific context
        if aid in self.user_ctx and self.user_ctx[aid] is not None:
            self.user_ctx[aid].append((ctx.message, message))

        self.log(message, f"`gpt {prompt}` | ({response.usage.prompt_tokens - len(prompt)})+{len(prompt)}+{response.usage.completion_tokens}={response.usage.total_tokens}")
