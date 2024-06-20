import asyncio
import common.config as config
import common.helper as helper
import discord
import discord.app_commands as app
import openai
import os

from .help import generate_help_info
from common.cog import DroppyCog
from common.exception import DroppyBotError
from discord.ext import commands
from typing import Optional, Union


class GPTHandler(DroppyCog):
    def __init__(self):
        self.endpoint = openai.AsyncOpenAI(
            api_key=os.environ["OPENAI_KEY"], base_url=os.environ["OPENAI_API"]
        )
        self.endpoint_alt = openai.AsyncOpenAI(
            api_key=os.environ["OPENAI_ALT_KEY"], base_url=os.environ["OPENAI_ALT_API"]
        )

        self.user_init: dict[str, str] = self.load_user_init()
        self.user_ctx: dict[int, str] = {}

        self.help_info["GPT"] = generate_help_info

    def as_embed(self, content: str, referrer: discord.User, footer: str = ""):
        embed = helper.as_embed(content, referrer)

        if self.on_maintenance:
            embed.set_footer(text=footer)

        return embed

    def load_user_init(self):
        user_init_path = os.path.join(self.cwd, self.config.gpt.user_init_path)
        return config.load_json(user_init_path)

    def save_user_init(self):
        user_init_path = os.path.join(self.cwd, self.config.gpt.user_init_path)
        config.save_json(user_init_path, self.user_init)

    def get_user_init(self, user: discord.User):
        aid = str(user.id)
        return self.user_init.get(aid, None)

    def get_gpt_model(self, name: str):
        return helper.first_if(self.config.gpt.model.specs, lambda m: m.name == name)

    def is_gpt_question(self, ctx: discord.Message):
        """
        Whether a user message/command is a gpt command

        If it is, return the gpt type
        """

        if ctx.author.bot:
            return None

        content = ctx.system_content
        print(content)
        if "gpt" in content and "gpti" not in content:
            return True

        return None

    def gpt_system_content(self, content: str):
        return {"role": "system", "content": content}

    def gpt_user_content(self, content: Union[str, list]):
        return {"role": "user", "content": content}

    def gpt_bot_content(self, content: str):
        return {"role": "assistant", "content": content}

    def truncate_contextual_input(self, messages: list[dict], token_limit: int):
        accum = 0
        truncated = []
        for message in messages:
            if message["role"] == "system":
                truncated.append(message)
                accum += len(message["content"])

            if accum >= token_limit:
                break

            truncated.append(message)
            content = message["content"]
            if isinstance(content, list):
                for payload in content:
                    match payload["type"]:
                        case "image_url":
                            accum += 935
                        case "text":
                            accum += len(payload["text"])
            else:
                accum += len(message["content"])
        return truncated, accum

    async def retrieve_conversation(self, ctx: discord.Message):
        """
        Retrieve ongoing conversation as contextual input

        Conversation should be in request-and-reply style,
        starts with bot reply(aka answer)

        Resolves backwards
        """

        messages = []
        valid_gpt = False

        messages.append(self.gpt_user_content(ctx.content))

        # check if user replied to a gpt response for a "contextual conversation"
        ref = ctx.reference
        if not ref or not ref.resolved:
            return []

        answer = ref.resolved
        if not answer.author.bot:
            return []

        retrieval = self.config.gpt.contextual.max_ctx_per_user
        while retrieval:
            if not answer:
                break

            # gpt response is an embed
            messages.append(self.gpt_bot_content(answer.embeds[0].description))

            # using message id to resolve manually, due to discord API not attempting to chain de-reference
            question = answer.reference or answer.interaction
            if not question:
                break

            if isinstance(question, discord.MessageReference):
                question = await ctx.channel.fetch_message(question.message_id)
                if not question:
                    break

                if question.author.bot:
                    answer = question
                    continue

                if self.is_gpt_question(question):
                    valid_gpt = True

                files = await self.process_file_upload(question)
                if files:
                    messages.append(self.gpt_user_content(files))

                prompt = question.content
                messages.append(self.gpt_user_content(prompt))
            elif isinstance(question, discord.MessageInteraction):
                if (
                    "gpt" in question.name
                    and question.name != "gptinit"
                    and answer.id in self.user_ctx
                ):
                    valid_gpt = True
                    prompt = self.user_ctx[answer.id]
                    messages.append(self.gpt_user_content(prompt))
                break
            else:
                break

            if not question.reference or not question.reference.message_id:
                break

            answer = await ctx.channel.fetch_message(question.reference.message_id)
            retrieval -= 1

        messages.reverse()
        return messages if valid_gpt else []

    async def process_file_upload(self, attached: discord.Message):
        """
        Process text files and images
        """

        file_contents = []
        for attachment in attached.attachments:
            if attachment.content_type.startswith("image"):
                file_contents.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": attachment.proxy_url,
                            "detail": self.config.gpt.model.vision_fidelity,
                        },
                    }
                )
            if attachment.content_type.startswith("text"):
                file_contents.append(
                    {
                        "type": "text",
                        "text": f"file: {attachment.filename}\n\n{(await attachment.read()).decode('utf-8')}\n\nend of file",
                    }
                )
        return file_contents

    async def create_gpt_input_model(self, ctx: commands.Context, prompt: str):
        """
        Create a list of gpt message params,
        including user init prompt and any file upload
        """

        messages = []

        user_init = self.get_user_init(ctx.author)
        if user_init:
            messages.append(self.gpt_system_content(user_init))

        files = await self.process_file_upload(ctx.message)
        if files:
            messages.append(self.gpt_user_content(files))

        messages.append(self.gpt_user_content(prompt))
        return messages

    async def request_and_reply(
        self,
        ctx: discord.Message,
        ref: discord.Message,
        messages: list,
        model: str,
        *,
        private: bool = False,
    ):
        """
        Make actual gpt request with openAI endpoint

        Update user context cache
        """

        locale = self.get_ctx_locale(ctx)

        gpt_model = self.get_gpt_model(model)
        max_token = gpt_model.max_token * self.config.gpt.contextual.max_ctx_percentage
        messages, accum = self.truncate_contextual_input(messages, max_token)

        helper.latency_start(ref.id)
        # request for chat completion
        completion = await self.endpoint.chat.completions.create(
            model=gpt_model.name, messages=messages
        )

        # get perf latency
        latency = f" ⏱️ {helper.latency_end(ref.id)}ms"

        # content policy?
        if completion.choices[0].finish_reason == "content_filter":
            raise DroppyBotError(self.translate("gpt_content_blocked", locale))

        # respond to user
        raw_content = completion.choices[0].message.content
        responses = helper.chunk_with_size(raw_content, 3800)

        ref = await ref.edit(embed=self.as_embed(responses[0], ctx.author, latency))
        for i, res in enumerate(responses[1:]):
            ref = await ref.reply(
                embed=self.as_embed(res, ctx.author, f"{i + 2} / {len(responses)}"),
                silent=True,
            )

        token = completion.usage.completion_tokens
        tally = completion.usage.total_tokens

        if not private:
            prompt = messages[-1]["content"]
            context = f"({completion.usage.prompt_tokens - len(prompt)})+{len(prompt)}"
            telemetry = helper.jump_url(f"{context}+{token}={tally}", ref.jump_url)
            self.log(
                ctx,
                f"{gpt_model.name} {telemetry} {latency}\n{helper.codeblock(prompt)}",
            )
        return tally

    @helper.sanitize
    async def create_gpt_request(
        self, ctx: commands.Context, prompt: str, model: str, private: bool
    ):
        """
        Internal handler for direct gpt request
        """

        ref = await self.get_ctx_ref(ctx)

        if ctx.interaction:
            self.user_ctx[ref.id] = prompt

        messages = await self.create_gpt_input_model(ctx, prompt)
        return await self.request_and_reply(
            ctx.message, ref, messages, model, private=private
        )

    @commands.hybrid_command(description="gpt_desc")
    @app.rename(prompt="gpt_prompt")
    @app.describe(prompt="gpt_prompt_desc")
    @DroppyCog.failsafe_ref(
        DroppyCog.config.gpt.thinking_indicator, force_ephemeral=False
    )
    @DroppyCog.allocated("gpt")
    async def gpt(self, ctx: commands.Context, *, prompt: str):
        """
        Start a new conversation with gpt-4-turbo, 128k
        """

        model = self.config.gpt.model.default
        return await self.create_gpt_request(ctx, prompt, model, False)

    @commands.hybrid_command(description="gpt4_desc")
    @app.rename(prompt="gpt_prompt")
    @app.describe(prompt="gpt4_prompt_desc")
    @DroppyCog.failsafe_ref(
        DroppyCog.config.gpt.thinking_indicator, force_ephemeral=False
    )
    @DroppyCog.allocated("gpt")
    async def gpt4(self, ctx: commands.Context, *, prompt: str):
        """
        Start a new conversation with gpt-4o, 128k
        """

        model = self.config.gpt.model.advanced
        return await self.create_gpt_request(ctx, prompt, model, False)

    @commands.command()
    @DroppyCog.failsafe_ref(DroppyCog.config.gpt.thinking_indicator)
    @DroppyCog.allocated("gpt")
    async def gptp(self, ctx: commands.Context, *, prompt: str):
        """
        Start a new conversation, private, text command only
        """

        model = self.config.gpt.model.advanced
        return await self.create_gpt_request(ctx, prompt, model, True)

    @commands.hybrid_command(description="gptinit_desc")
    @app.rename(prompt="gptinit_prompt")
    @app.describe(prompt="gptinit_prompt_desc")
    @helper.sanitize
    @DroppyCog.failsafe_ref()
    async def gptinit(self, ctx: commands.Context, *, prompt: Optional[str]):
        """
        Set startup prompt for user
        """

        ref = await self.get_ctx_ref(ctx)
        locale = self.get_ctx_locale(ctx)

        aid = str(ctx.author.id)
        original = helper.codeblock(self.user_init.get(aid, None))

        self.user_init[aid] = prompt
        self.save_user_init()

        prompt_block = helper.codeblock(prompt)
        init_changed = self.translate("gptinit_changed", locale)
        embed = (
            self.as_embed(init_changed, ctx.author)
            .add_field(name="From", value=str(original), inline=False)
            .add_field(name="To", value=prompt_block, inline=False)
        )
        await ref.edit(embed=embed)
        self.log(
            ctx.message,
            f"gpt-init ({len(prompt) if prompt else 0})\n{original}->{prompt_block}",
        )

    @DroppyCog.failsafe_ref(
        DroppyCog.config.gpt.thinking_indicator, force_ephemeral=False
    )
    @DroppyCog.allocated("gpt")
    async def create_gpt_contextual(self, ctx: discord.Message, messages: list):
        ref = await self.get_ctx_ref(ctx)

        model = self.config.gpt.model.advanced
        return await self.request_and_reply(ctx, ref, messages, model)

    @commands.Cog.listener("on_message")
    async def gpt_reply(self, ctx: discord.Message):
        if not self.prepass_check_internal(ctx):
            return

        # check if user replied to a gpt response for a "contextual conversation"
        # as a first step to save resource on actual chain de-referencing
        ref = ctx.reference
        if not ref or not ref.resolved:
            return

        if not ref.resolved.author.bot:
            return

        messages = await self.retrieve_conversation(ctx)
        if messages:
            await self.create_gpt_contextual(ctx, messages)
