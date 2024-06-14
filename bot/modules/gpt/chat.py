import asyncio
import discord
import json
import os
import time

from discord.ext import commands
from shared import CogBase, cwd


class GPTHandler(CogBase, commands.Cog):
    def generate_help_info(self):
        help_info = [
            discord.Embed(
                color=discord.Color.blurple(),
                title="GPT",
                description="""
            使用chatGPT进行文字生成, powered by OpenAI

            可附加有上限的上下文, 模拟连续对话(参考使用方法)

            已提供`gpt-4-turbo`或`gpt-4o`**(新!)**模型

            *2024/05/16 更新:*
            + 移除了`gpt-3.5-turbo`, 现有的`!gpt`命令将会指向`gpt-4-turbo`
            + 添加了`gpt-4o`模型, 现有的`!gpt4`命令将会指向它

            2024/04/06 更新:*
            + 训练数据已更新至2023年12月份

            2024/03/24 更新:
            + gpt模型`1106`->`0125`

            2023/12/18 更新:
            + 已支持联网搜索, 结果基于互联网查找

            2023/11/19 更新:
            + 训练数据已更新至2023年4月份
            + 支持长文本输入/输出(参考使用方法)
            + 支持图片识别/图片辅助的文字生成(参考使用方法)
            """,
            ),
            discord.Embed(
                color=discord.Color.blurple(),
                title="如何选择不同的模型?",
                description=f"""
            本机器人🔧接入了OpenAI API, 自3月27日也获得了gpt-4模型API的内测资格, ~~因此提供gpt-3.5-turbo和gpt-4两种模型~~

            ~~其中`gpt-3.5-turbo`是OpenAI默认chatGPT模型, 而`gpt-4`则是其之后的高级付费模型, 语言能力和逻辑思维得到了很大的加强~~

            ~~两GPT模型的使用**没有**网页端的每小时条数限制. 但是, 作为一个计费制的API, 在整活类问题/逻辑需求不强的使用场景下请调用`gpt-3.5-turbo`模型, 正常使用时则调用`gpt-4`模型~~

            现已移除`gpt-3.5-turbo`, 默认设置为`gpt-4-turbo`, 高级模型为`gpt-4o`, 尽情使用吧!

            """,
            ),
            discord.Embed(
                color=discord.Color.blurple(),
                title="命令指南及其示例:",
                description=f"""
            ```
{self.compiled_gpt_cmd} : 向chatGPT文字补全提供prompt
{self.compiled_gpt4_cmd} : 向chatGPT文字补全提供prompt, 指定使用gpt-4模型
{self.compiled_gptinit_cmd} : 设定个人专属的chatGPT设定语句, 例如人格模拟/风格设定```

            取自于群友日常使用场景😅

            询问`gpt-3.5-turbo(默认chatGPT模型)`对于攀登高山的看法:
            ```
{self.compiled_gpt_cmd} 你对於爬高山有什么看法?```
            使用`gpt-4`用诗的形式证明素数的无穷性:
            ```
{self.compiled_gpt4_cmd} 用诗的形式证明素数的无穷性```
            辅助生产力:
            ```
{self.compiled_gpt4_cmd} 如何写一个好的开题报告? 我的方向是XXXX, 需要注重XXXX, XXXX```
            进行双语对照翻译:
            ```
{self.compiled_gpt4_cmd} "命里有时终须有，命里无时莫强求"这句话用俄语如何翻译? 要求尽量信达雅, 并逐句附加中俄双语对照和解释```
            """,
            ),
            discord.Embed(
                color=discord.Color.blurple(),
                title="附加上下文进行连续对话",
                description=f"""
            每次使用`!gpt`/`!gpt4`命令时, 这便开启了一个**新的对话**.

            若要跟随此对话上下文进行连续对话, 请右键该🤖的回答, 选择回复即可.

            当跟随上下文继续对话时, **不需要再次使用**`!gpt`/`!gpt4`命令, 请直接输入你的文字.
            """,
            ).set_image(url="https://i.postimg.cc/j5SxZLrL/reply.png"),
            discord.Embed(
                color=discord.Color.blurple(),
                title="关于GPT设定语句",
                description=f"""
            GPT设定语句是每次对话时各用户专属的前置设定, 又称为调教, 咒语等

            例如, 使GPT扮演一个猫娘:
            ```
{self.compiled_gptinit_cmd} 你将扮演一个猫娘, 称呼我为主人, 开头和结尾都要使用喵语气和可爱风格```

            若要清空GPT设定语句, 则使用不加文字的`{self.compiled_gptinit_cmd}`命令
            """,
            ),
            discord.Embed(
                color=discord.Color.blurple(),
                title="附加文件用于文字生成",
                description=f"""
            使用GPT命令时, 将文件拖拽至输入栏即可附加此文件用于下次文字生成

            机器人未支持如`.docx`, `.pdf`等格式的自动转换, 文档类文件请自行转换为纯文本格式(`.txt`), 代码类文件可直接附加

            可一次附加多个文件
            """,
            ).set_image(url="https://i.postimg.cc/cLqK5yXp/1.png"),
            discord.Embed(
                color=discord.Color.blurple(),
                title="附加图片进行图片识别/辅助生成",
                description=f"""
            使用GPT命令时, 将图片拖拽/复制至输入栏即可附加此文件用于下次图片识别/辅助生成

            图片类文件不支持图形交换格式(`.gif`, 即动图), 仅支持常见图片格式如`.jpg`, `.png`

            可一次附加多个文件
            """,
            ).set_image(url="https://i.postimg.cc/wxPqbL9t/2.png"),
        ]

        return help_info

    def __init__(self):
        self.internal_latency = None
        self.active_model = self.config.gpt.model.default
        self.max_token = next(
            model
            for model in self.config.gpt.model.spec
            if model["name"] == self.active_model
        )["max_token"]
        self.user_init: dict[int, str] = self.load_user_init()
        self.user_ctx: dict[int, list[tuple[discord.Message, discord.Message]]] = {}
        self.user_token = int(
            self.max_token * self.config.gpt.contextual.max_ctx_percentage
        )

        self.private_query = False

        self.compiled_gpt_cmd = f"{self.bot.command_prefix}gpt"
        self.compiled_gpt4_cmd = f"{self.bot.command_prefix}gpt4"
        self.compiled_gptinit_cmd = f"{self.bot.command_prefix}gptinit"

        self.help_info["GPT"] = self.generate_help_info()

    def load_user_init(self):
        user_init = {}
        user_init_path = os.path.join(cwd, self.config.gpt.user_init_path)
        if os.path.exists(user_init_path):
            try:
                with open(user_init_path, "rb") as f:
                    for user, init in json.load(f).items():
                        user_init[int(user)] = str(init)
            except Exception:
                user_init = {}

        return user_init

    def save_user_init(self):
        for user, init in self.user_init.copy().items():
            if init is None or init == "" or init.isspace():
                del self.user_init[user]

        user_init_path = os.path.join(cwd, self.config.gpt.user_init_path)
        with open(user_init_path, "w", encoding="utf-8") as f:
            json.dump(self.user_init, f, indent=4, ensure_ascii=False)

    async def retrieve_conversation(self, msg: discord.Message):
        """
        retrieve ongoing conversation as contextual input
        conversation should be in request-and-reply style
        """

        prompts = []
        valid_gpt = False
        # check if user replied to a gpt response for a "contextual conversation"
        ref = msg.reference
        if ref is None or ref.resolved is None:
            return None

        answer = ref.resolved
        if answer.author != self.bot.user:
            return None

        retrieval = self.config.gpt.contextual.max_ctx_per_user
        while retrieval > 0:
            if answer is None:
                break
            # gpt response is an embed
            prompts.append(
                {"role": "assistant", "content": answer.embeds[0].description}
            )

            # using message id to resolve manually, due to discord API not attempting to chain de-reference
            question = answer.reference
            if question is None or question.message_id is None:
                break

            question = await msg.channel.fetch_message(question.message_id)
            if question is None or question.author != msg.author:
                break

            prompt = question.content
            prompts.append({"role": "user", "content": prompt})

            if self.compiled_gpt_cmd in prompt:
                valid_gpt = True

            if question.reference is None or question.reference.message_id is None:
                break
            answer = await msg.channel.fetch_message(question.reference.message_id)

            retrieval -= 1
        return prompts if valid_gpt else None

    async def request_and_reply(
        self, prompt, requests, msg: discord.Message, reply: discord.Message
    ):
        """
        make actual chatGPT request with openAI endpoint
        update user context storage and log the action
        """

        # telemetry
        tele_prompt_token = 0
        tele_res_token = 0

        # request for chat completion
        completion = await asyncio.to_thread(
            self.endpoint.chat.completions.create,
            model=self.active_model,
            messages=requests,
            tools=self.config.gpt.tools,
        )

        tele_prompt_token += completion.usage.prompt_tokens - len(prompt)
        tele_res_token += completion.usage.completion_tokens

        # if tools are called
        if (
            completion.choices[0].message.tool_calls is not None
            and len(completion.choices[0].message.tool_calls) != 0
        ):
            tools = self.bot.get_cog("GPTTools")
            if tools is not None:
                tool_response = tools.process_tool_call(
                    completion.choices[0].message.tool_calls[0]
                )

                requests.append(
                    {
                        "role": "assistant",
                        "tool_calls": completion.choices[0].message.tool_calls,
                    }
                )
                requests.append(
                    {
                        "role": "tool",
                        "content": str(tool_response),
                        "tool_call_id": completion.choices[0].message.tool_calls[0].id,
                    }
                )

            # if tool call failed, fall back to default completion, otherwise commit
            completion = await asyncio.to_thread(
                self.endpoint.chat.completions.create,
                model=self.active_model,
                messages=requests,
            )

            tele_prompt_token += completion.usage.prompt_tokens - len(prompt)
            tele_res_token += completion.usage.completion_tokens

        # get perf latency
        latency = time.perf_counter() - self.internal_latency
        latency = int(round(latency * 1000))

        # respond to user
        response = self.format_response(completion.choices[0].message.content)
        await reply.edit(embed=self.as_embed(response[0]))
        for res in response[1:]:
            await reply.reply(embed=self.as_embed(res))

        # save user specific context
        aid = msg.author.id
        if aid in self.user_ctx and self.user_ctx[aid] is not None:
            if self.user_init[aid].strip() != "":
                self.user_ctx[aid].append((msg, reply))

        if not self.private_query:
            context = f"({completion.usage.prompt_tokens - len(prompt)})+{len(prompt)}"
            completion_token = completion.usage.completion_tokens
            tally = completion.usage.total_tokens
            telemetry = f"[{context}+{completion_token}={tally}]({reply.jump_url})"
            self.log(
                msg,
                f"{self.active_model} {telemetry} {latency}ms\n```{prompt}```",
            )

    @commands.hybrid_command()
    @CogBase.failsafe(CogBase.config.gpt.thinking_indicator)
    async def gpt(self, ctx: commands.Context, *, prompt):
        """
        gpt-4-turbo, 128k
        """

        ref = await self.get_ctx_ref(ctx)

        self.internal_latency = time.perf_counter()

        # placeholder
        embed = self.as_embed(self.config.gpt.thinking_indicator, ctx.author)
        await ref.edit(embed=embed)

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
                if (
                    ctx.message.created_at - history.created_at
                ).total_seconds() <= self.config.gpt.contextual.in_memory_timeframe:
                    consumed_tokens = len(history.content) + len(
                        answer.embeds[0].description
                    )
                    tokens -= consumed_tokens
                    if tokens >= 0:
                        prompts.append({"role": "user", "content": history.content})
                        prompts.append(
                            {
                                "role": "assistant",
                                "content": answer.embeds[0].description,
                            }
                        )
                    else:
                        break
                else:
                    self.user_ctx[aid].remove((history, answer))

        # append file inputs
        if len(ctx.message.attachments) >= 1:
            for file in ctx.message.attachments:
                if file.content_type.startswith("image"):
                    prompts.append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": file.proxy_url,
                                "detail": self.config.gpt.model.vision_fidelity,
                            },
                        }
                    )
                if file.content_type.startswith("text"):
                    prompts.append(
                        {
                            "role": "user",
                            "content": f"{file.filename}:\n```{(await file.read()).decode('utf-8')}```",
                        }
                    )
        prompts.append({"role": "user", "content": prompt})

        # request for chat completion
        await self.request_and_reply(prompt, prompts, ctx.message, ref)
        self.active_model = self.config.gpt.model.default

    @commands.hybrid_command()
    async def gpt4(self, ctx: commands.Context, *, prompt):
        """
        gpt-4o, 128k
        """

        spec = str(self.active_model)
        self.active_model = self.config.gpt.model.advanced
        await self.gpt(ctx, prompt=prompt)
        self.active_model = spec

    @commands.command()
    async def gptp(self, ctx: commands.Context, *, prompt):
        self.private_query = True
        await self.gpt4(ctx, prompt=prompt)
        self.private_query = False

    @commands.hybrid_command()
    @CogBase.failsafe()
    async def gptinit(self, ctx: commands.Context, *, init=None):
        """
        Set startup prompt for your own
        """

        ref = await self.get_ctx_ref(ctx)

        aid = ctx.author.id
        original = ""
        if aid in self.user_init and self.user_init[aid] is not None:
            original = f"\n```{self.user_init[aid]}```->"
        self.user_init[aid] = init

        await ref.edit(
            embed=self.as_embed(
                f"您的GPT设定已更改!{original}\n```{init}```", ctx.author
            )
        )
        self.log(
            ctx.message,
            f"gpt-init ({len(init) if init is not None else 0}) {original}\n```{init}```",
        )
        self.save_user_init()

    async def build_contextual(self, ctx: discord.Message):
        # check if the replied message is also a replied message a.k.a a gpt response
        prompts = []
        prompt = ctx.content
        prompts.append({"role": "user", "content": prompt})

        conversation = await self.retrieve_conversation(ctx)
        if conversation is None:
            return

        # replies from other commands
        if len(conversation) <= 1:
            return

        prompts += conversation

        # placeholder
        embed = self.as_embed(self.config.gpt.thinking_indicator, ctx.author)
        reply = await ctx.reply(embed=embed)

        # prepend system init, for RP purpose or preset guidelines
        aid = ctx.author.id
        if aid in self.user_init and self.user_init[aid] is not None:
            prompts.append({"role": "system", "content": self.user_init[aid]})

        # request for chat completion
        prompts.reverse()
        spec = str(self.active_model)
        self.active_model = self.config.gpt.model.advanced
        await self.request_and_reply(prompt, prompts, ctx, reply)
        self.active_model = spec

    # listen for inputs
    @commands.Cog.listener()
    async def on_message(self, ctx: discord.Message):
        if await self.prepass(ctx) is None:
            return

        ref = ctx.reference
        if ref is None or ref.resolved is None:
            return

        # check if user replied to a gpt response for a "contextual conversation"
        if ref.resolved.author != self.bot.user:
            return

        self.internal_latency = time.perf_counter()
        await self.build_contextual(ctx)
