import os

from shared import CogBase

import discord
from discord.ext import commands
import openai


class GPTHandler(CogBase, commands.Cog):
    def __init__(self):
        openai.api_key = os.environ['OPENAI_KEY']
        self.user_init: dict[int, str] = {}
        self.user_ctx: dict[int, list[tuple[discord.Message, discord.Message]]] = {}
        self.user_token = next(model for model in self.config.gpt.model.spec if model['name'] == self.config.gpt.model.default)['max_token']
        self.user_token = int(self.user_token * self.config.gpt.contextual.max_ctx_percentage)
        self.active_model = self.config.gpt.model.default


    @commands.command()
    async def gpt(self, ctx: commands.Context, *, prompt):
        if await self.prepass(ctx.message) is None:
            return

        # placeholder
        embed = self.as_embed(self.config.gpt.thinking_indicator, ctx.author)
        reply = await ctx.reply(embed=embed)

        # calc max tokens allowed for contextual gpt
        aid = ctx.author.id
        prompts = []
        tokens = self.user_token
        tokens -= len(prompt)

        # prepend system init, for RP purpose or preset guidelines
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
            model=self.active_model, 
            messages=prompts) 

        # respond to user
        embed.description = f'{response.choices[0].message.content}'
        reply = await reply.edit(embed=embed)

        # save user specific context
        if aid in self.user_ctx and self.user_ctx[aid] is not None:
            self.user_ctx[aid].append((ctx.message, reply))

        self.log(ctx.message, f"`{self.active_model} {prompt}` | ({response.usage.prompt_tokens - len(prompt)})+{len(prompt)}+{response.usage.completion_tokens}={response.usage.total_tokens}")


    @commands.command()
    async def gpt4(self, ctx: commands.Context, *, prompt):
        old_spec = str(self.active_model)
        self.active_model = self.config.gpt.model.advanced
        await self.gpt(ctx, prompt=prompt)
        self.active_model = old_spec


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if await self.prepass(message) is None:
            return
        
        # check if user replied to a gpt response for a "contextual conversation"
        ref = message.reference
        if ref is None or ref.resolved is None:
            return
        
        ref = ref.resolved
        if ref.author != self.bot.user:
            return

        # placeholder
        embed = self.as_embed(self.config.gpt.thinking_indicator, message.author)
        reply = await message.reply(embed=embed)

        # check if the replied message is also a replied message a.k.a a gpt response
        # using message id to resolve manually, due to discord API not attempting to chain de-reference
        prompts = []
        prompt = message.content.replace(f"{self.bot.command_prefix}gpt", '')
        prompts.append({'role': 'user', 'content': prompt})

        # retrieve ongoing conversation as contextual input
        retrieval = self.config.gpt.contextual.max_ctx_per_user
        answer = ref
        while retrieval > 0:
            if answer is None:
                break
            prompts.append({'role': 'assistant', 'content': answer.embeds[0].description})

            question = answer.reference
            if question is None or question.message_id is None:
                break
            question = await message.channel.fetch_message(question.message_id)
            if question is None or question.author != message.author:
                break
            prompts.append({'role': 'user', 'content': question.content.replace(f"{self.bot.command_prefix}gpt", '')})

            if question.reference is None or question.reference.message_id is None:
                break
            answer = await message.channel.fetch_message(question.reference.message_id)

            retrieval -= 1
        
        # prepend system init, for RP purpose or preset guidelines
        aid = message.author.id 
        if aid in self.user_init and self.user_init[aid] is not None:
            prompts.append({'role': 'system', 'content': self.user_init[aid]})
        prompts.reverse()
        
        response = await openai.ChatCompletion.acreate(
            model=self.config.gpt.model.default, 
            messages=prompts)

        # respond to user
        embed.description = f'{response.choices[0].message.content}'
        reply = await reply.edit(embed=embed)

        # save user specific context
        if aid in self.user_ctx and self.user_ctx[aid] is not None:
            self.user_ctx[aid].append((message, reply))

        self.log(message, f"`{self.active_model} {prompt}` | ({response.usage.prompt_tokens - len(prompt)})+{len(prompt)}+{response.usage.completion_tokens}={response.usage.total_tokens}")
