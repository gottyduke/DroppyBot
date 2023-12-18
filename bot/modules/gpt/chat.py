import datetime
import json
import os

from shared import CogBase, cwd
from modules.gpt.tools import GPTTools

import discord
from discord.ext import commands
from prodict import Prodict


class GPTHandler(CogBase, commands.Cog):
    def generate_help_info(self):
        help_info = [
            discord.Embed(
                color=discord.Color.blurple(),
                title="GPT",
                description="""
            使用chatGPT进行文字生成, powered by OpenAI

            可附加有上限的上下文, 模拟连续对话

            已提供`gpt-3.5-turbo-1106`或`gpt-4-1106-preview`模型

            *2023/12/18 更新:*
            + 已支持联网搜索, 结果基于互联网查找

            2023/11/19 更新:
            + 训练数据已更新至2023年4月份
            + 支持长文本输入/输出(参考使用方法)
            + 支持图片识别/图片辅助的文字生成(参考使用方法)
            """,
            )
        ]
        help_info.append(
            discord.Embed(
                color=discord.Color.blurple(),
                title="如何选择不同的模型?",
                description=f"""
            本机器人🔧接入了OpenAI API, 自3月27日也获得了gpt-4模型API的内测资格, 因此提供gpt-3.5-turbo和gpt-4两种模型

            其中`gpt-3.5-turbo`是OpenAI默认chatGPT模型, 而`gpt-4`则是其之后的高级付费模型, 语言能力和逻辑思维得到了很大的加强

            两GPT模型的使用**没有**网页端的每小时条数限制. 但是, 作为一个计费制的API, 在整活类问题/逻辑需求不强的使用场景下请调用`gpt-3.5-turbo`模型, 正常使用时则调用`gpt-4`模型
            """,
            )
        )
        help_info.append(
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
            )
        )
        help_info.append(
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
            )
        )
        help_info.append(
            discord.Embed(
                color=discord.Color.blurple(),
                title="附加文件用于文字生成",
                description=f"""
            使用GPT命令时, 将文件拖拽至输入栏即可附加此文件用于下次文字生成

            机器人未支持如`.docx`, `.pdf`等格式的自动转换, 文档类文件请自行转换为纯文本格式(`.txt`), 代码类文件可直接附加 
            
            可一次附加多个文件
            """,
            ).set_image(url="https://i.postimg.cc/cLqK5yXp/1.png")
        )
        help_info.append(
            discord.Embed(
                color=discord.Color.blurple(),
                title="附加图片进行图片识别/辅助生成",
                description=f"""
            使用GPT命令时, 将图片拖拽/复制至输入栏即可附加此文件用于下次图片识别/辅助生成

            图片类文件不支持图形交换格式(`.gif`, 即动图), 仅支持常见图片格式如`.jpg`, `.png`

            可一次附加多个文件
            """,
            ).set_image(url="https://i.postimg.cc/wxPqbL9t/2.png")
        )

        return help_info

    def __init__(self):
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
        with open(user_init_path, "w", encoding="utf-8") as f:
            json.dump(self.user_init, f, indent=4, sort_keys=True, ensure_ascii=False)

    async def retrieve_conversation(self, msg: discord.Message):
        """
        retrieve ongoing conversation as contextual input
        conversation should be in request-and-reply style
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

            if question.reference is None or question.reference.message_id is None:
                break
            answer = await msg.channel.fetch_message(question.reference.message_id)

            retrieval -= 1
        return prompts

    def format_response(self, response: str):
        if response is None:
            return [""]

        formatted = []
        if (
            not self.config.gpt.response.do_truncate
            or len(response) < self.config.gpt.response.entry_truncation
        ):
            return [response]

        # starts with atleast 1 entry
        formatted.append(
            f"*---此回复超出消息字数限制({len(response)}/{self.config.gpt.response.entry_truncation}), 已分段发送---*\n\n"
        )
        accum = 0
        code_block = False
        for line in response.splitlines():
            accum += len(line)
            # preserve code block
            if "```" in line:
                code_block = not code_block
            # close this response chunk
            if accum >= self.config.gpt.response.entry_truncation:
                if code_block:
                    formatted[-1] += "```"

                # begins new chunk
                formatted.append("")

                if code_block:
                    formatted[-1] += "```\n"
                accum = 0

            formatted[-1] += f"{line}\n"

        return formatted

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
        completion = self.endpoint.chat.completions.create(
            model=self.active_model,
            messages=requests,
            max_tokens=4096,
            tools=self.config.gpt.tools,
        )
        tele_prompt_token += completion.usage.prompt_tokens - len(prompt)
        tele_res_token += completion.usage.completion_tokens

        # if tools are called
        if len(completion.choices[0].message.tool_calls) != 0:
            tools: GPTTools = self.bot.get_cog("GPTTools")
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
            completion = self.endpoint.chat.completions.create(
                model=self.active_model, messages=requests, max_tokens=4096
            )
            tele_prompt_token += completion.usage.prompt_tokens - len(prompt)
            tele_res_token += completion.usage.completion_tokens

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
            self.log(
                msg,
                f"{self.active_model} [({completion.usage.prompt_tokens - len(prompt)})+{len(prompt)}+{completion.usage.completion_tokens}={completion.usage.total_tokens}]({reply.jump_url})\n```{prompt}```",
            )

    @commands.command()
    async def gpt(self, ctx: commands.Context, *, prompt):
        """
        prepare requests and file inputs/long text
        """

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
        vision_prompts = [{"type": "text", "text": prompt}]
        if len(ctx.message.attachments) >= 1:
            for file in ctx.message.attachments:
                # if vision assist is requested, switch to gpt-4-vision model
                if file.content_type.startswith("image"):
                    self.active_model = self.config.gpt.model.vision
                    self.max_token = next(
                        model
                        for model in self.config.gpt.model.spec
                        if model["name"] == self.active_model
                    )["max_token"]
                    vision_prompts.append(
                        {"type": "image_url", "image_url": file.proxy_url}
                    )
                if file.content_type.startswith("text"):
                    prompts.append(
                        {
                            "role": "user",
                            "content": f"{file.filename}:\n```{(await file.read()).decode('utf-8')}```",
                        }
                    )
        if self.active_model == self.config.gpt.model.vision:
            prompts.append({"role": "user", "content": vision_prompts})
        else:
            prompts.append({"role": "user", "content": prompt})

        # request for chat completion
        await self.request_and_reply(prompt, prompts, ctx.message, reply)
        self.active_model = self.config.gpt.model.default

    @commands.command()
    async def gpt4(self, ctx: commands.Context, *, prompt):
        spec = str(self.active_model)
        self.active_model = self.config.gpt.model.advanced
        await self.gpt(ctx, prompt=prompt)
        self.active_model = spec

    @commands.command()
    async def gptp(self, ctx: commands.Context, *, prompt):
        self.private_query = True
        await self.gpt4(ctx, prompt=prompt)
        self.private_query = False

    @commands.command()
    async def gptinit(self, ctx: commands.Context, *, init=None):
        if await self.prepass(ctx.message) is None:
            return

        aid = ctx.author.id
        original = ""
        if aid in self.user_init and self.user_init[aid] is not None:
            original = f"\n```{self.user_init[aid]}```->"
        self.user_init[aid] = init

        await ctx.reply(
            embed=self.as_embed(f"您的GPT设定已更改!{original}\n```{init}```", ctx.author)
        )
        self.log(
            ctx.message,
            f"gpt-init ({len(init) if init is not None else 0}) {original}\n```{init}```",
        )
        self.save_user_init()

    async def build_contextual(self, msg: discord.Message):
        # check if the replied message is also a replied message a.k.a a gpt response
        prompts = []
        prompt = msg.content
        prompts.append({"role": "user", "content": prompt})
        prompts += await self.retrieve_conversation(msg)

        # placeholder
        embed = self.as_embed(self.config.gpt.thinking_indicator, msg.author)
        reply = await msg.reply(embed=embed)

        # prepend system init, for RP purpose or preset guidelines
        aid = msg.author.id
        if aid in self.user_init and self.user_init[aid] is not None:
            prompts.append({"role": "system", "content": self.user_init[aid]})

        # request for chat completion
        prompts.reverse()
        spec = str(self.active_model)
        self.active_model = self.config.gpt.model.advanced
        await self.request_and_reply(prompt, prompts, msg, reply)
        self.active_model = spec

    # listen for inputs
    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if await self.prepass(msg) is None:
            return

        ref = msg.reference
        if ref is None or ref.resolved is None:
            return

        # check if user replied to a gpt response for a "contextual conversation"
        if ref.resolved.author != self.bot.user:
            return

        await self.build_contextual(msg)
