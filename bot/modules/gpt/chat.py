import json
import os

from shared import CogBase, cwd

import discord
import openai
from discord.ext import commands
from prodict import Prodict


class GPTHandler(CogBase, commands.Cog):

    def generate_help(self):
        help_info = [
            discord.Embed(color=discord.Color.blurple(),
                          title="GPT",
                          description="""
            使用chatGPT进行文字补全
            可附加有上限的上下文模拟对话
            可使用`gpt-3.5-turbo`或`gpt-4`模型
            """)
        ]
        help_info.append(
            discord.Embed(color=discord.Color.blurple(),
                          title="命令指南及其示例:",
                          description=f"""
            ```
{self.compiled_gpt_cmd} : 向chatGPT文字补全提供prompt
{self.compiled_gpt4_cmd} : 向chatGPT文字补全提供prompt, 指定使用gpt-4模型
{self.compiled_gptinit_cmd} : 设定个人专属的chatGPT设定语句, 例如人格模拟/风格设定
            ```

            取自于群友日常使用场景😅

            询问`gpt-3.5-turbo(默认chatGPT模型)`对于攀登高山的看法:
            ```{self.compiled_gpt_cmd} 你对於爬高山有什么看法?```

            使用`gpt-4`用诗的形式证明素数的无穷性:
            ```{self.compiled_gpt4_cmd} 用诗的形式证明素数的无穷性```

            辅助生产力:
            ```{self.compiled_gpt4_cmd} 如何写一个好的开题报告?```

            进行双语对照翻译:
            ```{self.compiled_gpt4_cmd} "命里有时终须有，命里无时莫强求"这句话用俄语如何翻译? 要求尽量信达雅, 并逐句中俄双语对照和解释```
            """))
        help_info.append(
            discord.Embed(
                color=discord.Color.blurple(),
                title="如何选择不同的模型?",
                description="本机器人🔧接入了OpenAI API, 自3月27日也获得了`gpt-4`模型API的内测资格, 因此提供`gpt-3.5-turbo`和`gpt-4`两种模型" +
                ", 其中`gpt-3.5-turbo`是OpenAI默认chatGPT模型, 而`gpt-4`则是其之后的高级付费模型, 语言能力和逻辑思维得到了很大的改" +
                "善. 两gpt模型的使用没有网页端的每小时条数限制. **但是**, 作为一个计费制的API, `gpt-3.5-turbo`的计费可以忽略不记, 而" +
                "能力更强的`gpt-4`目前平均每千语义单元计费为`0.045 usd/1k tokens`, 为`gpt-3.5-turbo`的**22.5**倍. 因此在整活类问" +
                "题/逻辑需求不强的使用场景下请使用`gpt-3.5-turbo`模型, 正常使用时则使用`gpt-4`模型."))
        help_info.append(
            discord.Embed(color=discord.Color.blurple(),
                          title="关于GPT设定语句",
                          description=f"""
            GPT设定语句是每次对话时自动gpt模型的用户专属的系统设定, 又称为`调教`, `咒语`.
            例如, 使gpt扮演一个猫娘:
            ```{self.compiled_gptinit_cmd} 你将扮演一个猫娘, 称呼我为主人, 开头和结尾都要使用喵语气和可爱风格```
            若要清空GPT设定语句, 则使用不加文字的`{self.compiled_gptinit_cmd}`命令
            """))

        return help_info

    def __init__(self):
        openai.api_key = os.environ["OPENAI_KEY"]

        self.user_init: dict[int, str] = self.load_user_init()
        self.user_ctx: dict[int, list[tuple[discord.Message, discord.Message]]] = {}
        self.user_token = next(model for model in self.config.gpt.model.spec
                               if model["name"] == self.config.gpt.model.default)["max_token"]
        self.user_token = int(self.user_token * self.config.gpt.contextual.max_ctx_percentage)
        self.active_model = self.config.gpt.model.default

        self.compiled_gpt_cmd = f"{self.bot.command_prefix}gpt"
        self.compiled_gpt4_cmd = f"{self.bot.command_prefix}gpt4"
        self.compiled_gptinit_cmd = f"{self.bot.command_prefix}gptinit"

        self.help_info["GPT"] = self.generate_help()

    def load_user_init(self):
        user_init = {}
        user_init_path = os.path.join(cwd, "rules/user_init.json")
        if os.path.exists(user_init_path):
            try:
                with open(user_init_path, "rb") as f:
                    for user, init in json.load(f).items():
                        user_init[int(user)] = str(init)
            except json.JSONDecodeError:
                user_init = {}

        return user_init

    def save_user_init(self):
        for user, init in self.user_init.copy().items():
            if init is None or init == "" or init.isspace():
                del self.user_init[user]

        user_init_path = os.path.join(cwd, "rules/user_init.json")
        with open(user_init_path, "w", encoding='utf-8') as f:
            json.dump(self.user_init, f, indent=4, sort_keys=True, ensure_ascii=False)

    async def retrieve_conversation(self, msg: discord.Message):
        """
        retrieve ongoing conversation as contextual input
        """

        prompts = []
        # check if user replied to a gpt response for a "contextual conversation"
        ref = msg.reference
        if ref is None or ref.resolved is None:
            return prompts

        answer = ref.resolved
        if answer.author != self.bot.user:
            return prompts

        retrieval = self.config.gpt.contextual.max_ctx_per_user
        while retrieval > 0:
            if answer is None:
                break
            # gpt response is an embed
            prompts.append({"role": "assistant", "content": answer.embeds[0].description})

            question = answer.reference
            if question is None or question.message_id is None:
                break

            question = await msg.channel.fetch_message(question.message_id)
            if question is None or question.author != msg.author:
                break

            # find the gpt model used to initiate this conversation
            prompt = question.content
            if prompt.startswith(self.compiled_gpt_cmd):
                self.active_model = self.config.gpt.model.default
                prompt = prompt.removeprefix(self.compiled_gpt_cmd)
            elif prompt.startswith(self.compiled_gpt4_cmd):
                self.active_model = self.config.gpt.model.advanced
                prompt = prompt.removeprefix(self.compiled_gpt4_cmd)

            prompts.append({
                "role": "user",
                "content": prompt,
            })

            if question.reference is None or question.reference.message_id is None:
                break
            answer = await msg.channel.fetch_message(question.reference.message_id)

            retrieval -= 1
        return prompts

    async def request_and_reply(self, prompt, requests, msg: discord.Message, reply: discord.Message):
        # request for chat completion
        response = await openai.ChatCompletion.acreate(model=self.active_model, messages=requests)
        embed = self.as_embed(f"{response.choices[0].message.content}")

        # respond to user
        reply = await reply.edit(embed=embed)

        # save user specific context
        aid = msg.author.id
        if aid in self.user_ctx and self.user_ctx[aid] is not None:
            if self.user_ctx[aid] != "" and not self.user_init[aid].isspace():
                self.user_ctx[aid].append((msg, reply))

        self.log(
            msg,
            f"{self.active_model} [({response.usage.prompt_tokens - len(prompt)})+{len(prompt)}+{response.usage.completion_tokens}={response.usage.total_tokens}]({reply.jump_url})```{prompt}```"
        )

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
            prompts.append({"role": "system", "content": self.user_init[aid]})
            tokens -= len(self.user_init[aid])

        # construct context
        if aid in self.user_ctx and self.user_ctx[aid] is not None:
            for history, answer in reversed(self.user_ctx[aid]):
                if (ctx.message.created_at -
                        history.created_at).total_seconds() <= self.config.gpt.contextual.in_memory_timeframe:
                    consumed_tokens = len(history.content) + len(answer.embeds[0].description)
                    tokens -= consumed_tokens
                    if tokens >= 0:
                        prompts.append({"role": "user", "content": history.content})
                        prompts.append({
                            "role": "assistant",
                            "content": answer.embeds[0].description,
                        })
                    else:
                        break
                else:
                    self.user_ctx[aid].remove((history, answer))

        # request for chat completion
        prompts.append({"role": "user", "content": prompt})
        await self.request_and_reply(prompt, prompts, ctx.message, reply)

    @commands.command()
    async def gpt4(self, ctx: commands.Context, *, prompt):
        spec = str(self.active_model)
        self.active_model = self.config.gpt.model.advanced
        await self.gpt(ctx, prompt=prompt)
        self.active_model = spec

    @commands.command()
    async def gptinit(self, ctx: commands.Context, *, init=None):
        if await self.prepass(ctx.message) is None:
            return

        aid = ctx.author.id
        original = ""
        if aid in self.user_init and self.user_init[aid] is not None:
            original = f"```{self.user_init[aid]}```->"
        self.user_init[aid] = init

        await ctx.reply(embed=self.as_embed(f"您的GPT设定已更改!{original}```{init}```", ctx.author))
        self.log(ctx.message, f"gpt-init ({len(init) if init is not None else 0}) {original}```{init}```")
        self.save_user_init()

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if await self.prepass(msg) is None:
            return

        # check if user replied to a gpt response for a "contextual conversation"
        ref = msg.reference
        if ref is None or ref.resolved is None:
            return

        # non contextual mode, but replied by mistake
        if msg.content.startswith(self.compiled_gpt_cmd):
            return

        # placeholder
        embed = self.as_embed(self.config.gpt.thinking_indicator, msg.author)
        reply = await msg.reply(embed=embed)

        # check if the replied message is also a replied message a.k.a a gpt response
        # using message id to resolve manually, due to discord API not attempting to chain de-reference
        spec = str(self.active_model)
        prompts = []
        prompt = msg.content
        prompts.append({"role": "user", "content": prompt})
        prompts += await self.retrieve_conversation(msg)

        # prepend system init, for RP purpose or preset guidelines
        aid = msg.author.id
        if aid in self.user_init and self.user_init[aid] is not None:
            prompts.append({"role": "system", "content": self.user_init[aid]})

        # request for chat completion
        prompts.reverse()
        await self.request_and_reply(prompt, prompts, msg, reply)
        self.active_model = spec
