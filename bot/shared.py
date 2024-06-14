import asyncio
import datetime
import discord
import os
import traceback

from discord.ext import commands
from functools import wraps
from openai import OpenAI
from prodict import Prodict
import util.logger


try:
    import modules.secrets
except ModuleNotFoundError:
    """
    if secrets not present in current workspace
    os.envi[] attempts should stop bot from running
    """
    pass

cwd = os.path.realpath(os.path.dirname(__file__))


# shared cog addons
class CogBase:
    bot: commands.Bot = None
    bot_ready = False
    config: Prodict = None
    on_maintenance = False
    help_info: dict[str, list[discord.Embed]] = {}
    endpoint: OpenAI = None
    sneaky_mode = False
    ctx_refs = {}

    @staticmethod
    def format_response(response: str):
        if response is None:
            return [""]

        formatted = []
        if (
            not CogBase.config.gpt.response.do_truncate
            or len(response) < CogBase.config.gpt.response.entry_truncation
        ):
            return [response]

        # starts with at least 1 entry
        formatted.append(
            f"*---此回复超出消息字数限制({len(response)}/{CogBase.config.gpt.response.entry_truncation}), 已分段发送---*\n\n"
        )
        accum = 0
        code_block = False
        code_block_syntax = ""
        for line in response.splitlines():
            accum += len(line)
            # preserve code block
            if "```" in line:
                code_block = not code_block
                code_block_syntax = line
            # close this response chunk
            if accum >= CogBase.config.gpt.response.entry_truncation:
                if code_block:
                    formatted[-1] += "```"

                # begins new chunk
                formatted.append("")

                if code_block:
                    formatted[-1] += code_block_syntax
                    formatted[-1] += "\n"
                accum = 0

            formatted[-1] += f"{line}\n"

        return formatted

    @staticmethod
    def get_fail_embed(e: Exception, header_override: str | None = None):
        stack = traceback.format_exception(type(e), e, e.__traceback__)
        header = type(e).__name__
        full = "".join(stack)
        util.logger.error(f"**{header}**\n```\n{full}\n```")

        if header_override is None:
            header_override = header

        error_timestamp = completion_time = datetime.datetime.now(
            datetime.UTC
        ).strftime("%Y/%m/%d %H:%M:%S")

        return CogBase.as_embed(
            CogBase.config.bot.fallback_error,
            color=discord.Color.red(),
            footer_append=error_timestamp,
        ).add_field(name=header_override, value=f"```\n{str(e)}\n```", inline=False)

    @staticmethod
    def failsafe_invoke(callable, *args, override_error=None, **kwargs):
        try:
            return callable(*args, **kwargs)
        except Exception as e:
            return CogBase.get_fail_embed(e, override_error)

    @staticmethod
    def afailsafe_invoke(
        awaitable, *args, override_error=None, logger_callback=None, **kwargs
    ):
        async def async_failsafe(awaitable, *args, **kwargs):
            try:
                return await awaitable(*args, **kwargs)
            except Exception as e:
                if logger_callback is not None and isinstance(
                    logger_callback, discord.Message
                ):
                    await logger_callback.edit(
                        embed=CogBase.get_fail_embed(e, override_error), view=None
                    )
                return None

        return asyncio.create_task(async_failsafe(awaitable, *args, **kwargs))

    @staticmethod
    def as_embed(
        msg,
        color_owner=None,
        color=discord.Color.from_rgb(236, 248, 248),
        footer_append=None,
    ):
        """
        shared embed builder to accommodate user's top role color
        also auto adds some footer texts
        """

        if footer_append is None:
            footer_append = f"使用 {CogBase.bot.command_prefix}help 命令来查看新功能! 更新日期: 2024/06/13*"

        if color_owner is not None and color_owner.color != discord.Color.default():
            color = color_owner.color

        embed = discord.Embed(description=msg, color=color)
        if footer_append != "":
            embed.set_footer(
                text=footer_append,
                icon_url=CogBase.bot.user.display_avatar.url,
            )

        if color_owner is not None:
            embed.set_author(
                name=color_owner.display_name, icon_url=color_owner.display_avatar.url
            )

        return embed

    @staticmethod
    def log(ctx: discord.Message, entry: str):
        """
        shared logger method, syncs to console output
        """
        if entry.strip() == "":
            return

        author = ctx.author

        if ctx is None:
            channel = "internal"
        else:
            channel = (
                "DM"
                if ctx.channel.type == discord.ChannelType.private
                else ctx.guild.name
            )

        # log format
        util.logger.log(f" **__[[{channel}]]__** {author.name} >> {entry}")

    @staticmethod
    def failsafe(thinking_indicator: str | None = None, force_ephemeral: bool = False):
        def failsafe_decorator(command):
            @wraps(command)
            async def failsafe_wrapper(*args, **kwargs):
                nonlocal thinking_indicator
                nonlocal force_ephemeral
                ctx = kwargs.get("ctx") if "ctx" in kwargs else args[1]

                if (
                    isinstance(ctx, commands.Context)
                    and await CogBase.prepass(ctx.message) is None
                ):
                    return

                if thinking_indicator is None:
                    thinking_indicator = CogBase.config.bot.fallback_indicator
                ref = await CogBase.get_ctx_ref(
                    ctx, thinking_indicator, force_ephemeral
                )
                await CogBase.afailsafe_invoke(
                    command, *args, **kwargs, logger_callback=ref
                )

            return failsafe_wrapper

        return failsafe_decorator

    @staticmethod
    async def prepass(ctx: discord.Message):
        """
        optional 1st layer filter for messaging if using exclusive commanding
        """

        if not CogBase.bot_ready or ctx.author.bot:
            return None
        else:
            if CogBase.on_maintenance and ctx.channel.id != int(
                os.environ["DEV_CHANNEL"]
            ):
                return None

            if ctx.is_system():
                return "_"

            raw = ctx.content.strip().split(" ", 1)
            cmd = raw[0]
            if cmd == "":
                return None
            prompt = raw[1].strip() if len(raw) > 1 else ""
            return cmd.lower(), prompt

    @staticmethod
    async def get_ctx_ref(
        ctx: commands.Context | discord.Interaction,
        thinking_indicator: str | None = None,
        force_ephemeral: bool = False,
    ):
        ref = ctx.message
        if isinstance(ctx, commands.Context):
            # slash command
            if ctx.interaction is not None:
                if ctx.interaction.response.type is None:
                    await ctx.defer(ephemeral=force_ephemeral)
                ref = await ctx.interaction.original_response()
                CogBase.ctx_refs[ctx.message.id] = ref
            elif thinking_indicator is not None:
                embed = CogBase.as_embed(
                    thinking_indicator, ref.author, footer_append=""
                )
                ref = await ctx.reply(embed=embed, silent=True)
                CogBase.ctx_refs[ctx.message.id] = ref
            else:
                ref = CogBase.ctx_refs[ctx.message.id]
        else:
            # view modals
            if ctx.response.type is None:
                if thinking_indicator is not None:
                    embed = CogBase.as_embed(
                        thinking_indicator, ref.author, footer_append=""
                    )
                    await ctx.response.send_message(embed=embed, silent=True)
                else:
                    await ctx.response.defer(ephemeral=force_ephemeral)
                ref = await ctx.original_response()
                CogBase.ctx_refs[ctx.message.id] = ref
            else:
                ref = CogBase.ctx_refs[ctx.message.id]

        return ref
