import common.helper as helper
import discord
import os

from .config import DroppyBotConfig, load_json, save_json
from .exception import failsafe_ainvoke, DroppyBotError
from .logger import log
from .translator import DroppyTranslator
from discord.ext import commands
from functools import wraps
from typing import Optional, Union, get_args


DroppyCtx = Union[commands.Context, discord.Interaction, discord.Message]


class DroppyCog(commands.Cog):
    """
    Base class for all cogs, basically a shared static singleton
    """

    bot: commands.Bot = None
    bot_ready = False
    config: DroppyBotConfig = None
    ctx_refs = {}
    ctx_locales = {}
    cwd: str
    enabled_modules = {}
    help_info = {}
    on_maintenance = False
    sneaky_mode = False
    translator: DroppyTranslator = None

    @staticmethod
    def is_dev(ctx: discord.Message):
        return str(ctx.author.id) == os.environ["DEV_ID"]

    @staticmethod
    def is_dev_ctx(ctx: discord.Message):
        dev_channel = str(ctx.channel.id) == os.environ["DEV_CHANNEL"]
        dev_author = DroppyCog.is_dev(ctx)
        dev_ctx = dev_channel and dev_author
        return dev_ctx

    @staticmethod
    def prepass_check_internal(ctx: discord.Message):
        if not DroppyCog.bot_ready or ctx.author.bot:
            return False
        else:
            dev_ctx = DroppyCog.is_dev_ctx(ctx)
            if (DroppyCog.on_maintenance and not dev_ctx) or (
                not DroppyCog.on_maintenance and dev_ctx
            ):
                return False
            return True

    @staticmethod
    def prepass(ctx: commands.Context):
        """
        Optional 1st layer filter for messaging if using exclusive commanding
        """

        return DroppyCog.prepass_check_internal(ctx.message)

    @staticmethod
    def log(ctx: discord.Message, entry: str, author_override: discord.User = None):
        """
        Shared logger method, syncs to console output
        """
        if not entry.strip():
            return

        author = author_override or ctx.author
        if not ctx:
            channel = "DEV"
        elif ctx.channel.type == discord.ChannelType.private:
            channel = "DM"
        else:
            channel = f"{ctx.guild.name}::{ctx.channel.name}"

        # log format
        log(f" **__[[{channel}]]__** {author.display_name} >> {entry}")

    @staticmethod
    def translate(
        string: str, locale: discord.Locale = discord.Locale.american_english
    ) -> str:
        """
        Translate a string key
        """
        translated = DroppyCog.translator.get_text(string, locale)
        if not translated:
            raise DroppyBotError(
                f"Non-localized string, Droppy needs to fix it\nstring: {string}\nlocale: {locale.name}"
            )
        return translated

    @staticmethod
    def save_ctx_locale():
        locales_path = os.path.join(DroppyCog.cwd, "rules/locales.json")
        fixed_json = {u: l.name for u, l in DroppyCog.ctx_locales.items()}

    @staticmethod
    def load_ctx_locale():
        locales_path = os.path.join(DroppyCog.cwd, "rules/locales.json")
        fixed_json = load_json(locales_path)
        fixed_json = {u: discord.Locale(l) for u, l in fixed_json.items()}
        DroppyCog.ctx_locales = fixed_json

    @staticmethod
    def get_ctx_locale(ctx: DroppyCtx):
        """
        Get locale related to a user

        Fallback to american_english
        """

        if not DroppyCog.ctx_locales:
            DroppyCog.load_ctx_locale()

        fallback = discord.Locale.american_english
        if isinstance(ctx, discord.Interaction):
            locale = ctx.locale
            DroppyCog.ctx_locales[str(ctx.user.id)] = locale
            DroppyCog.save_ctx_locale()
            return locale
        elif isinstance(ctx, commands.Context) and ctx.interaction:
            locale = ctx.interaction.locale
            DroppyCog.ctx_locales[str(ctx.interaction.user.id)] = locale
            DroppyCog.save_ctx_locale()
            return locale
        elif str(ctx.author.id) in DroppyCog.ctx_locales:
            return DroppyCog.ctx_locales[str(ctx.author.id)]
        elif isinstance(ctx, discord.Message) or isinstance(ctx, commands.Context):
            if ctx.channel.type != discord.ChannelType.private:
                return ctx.guild.preferred_locale
        return fallback

    @staticmethod
    def get_ctx_author(ctx: DroppyCtx):
        if isinstance(ctx, commands.Context):
            return ctx.author
        elif isinstance(ctx, discord.Interaction):
            return ctx.user
        elif isinstance(ctx, discord.Message):
            if ctx.author.bot:
                if ctx.reference and ctx.reference.resolved:
                    return ctx.reference.resolved.author
                elif ctx.interaction:
                    return ctx.interaction.user
            return ctx.author
        else:
            return None

    @staticmethod
    async def get_ctx_ref(
        ctx: DroppyCtx,
        *,
        thinking_indicator: Optional[str] = None,
        force_ephemeral: bool = True,
        force_silent: bool = True,
    ):
        """
        Setup a contextual reference, normally an embed reply

        Or an interaction defer response, then edit with embed reply

        Consecutive calls will return the same reference
        """

        footer = None

        if isinstance(ctx, discord.Message):
            # explicit message
            if ctx.id in DroppyCog.ctx_refs:
                return DroppyCog.ctx_refs[ctx.id]
            else:
                embed = helper.as_embed(
                    thinking_indicator, ctx.author, footer_append=footer
                )
                ref = await ctx.reply(embed=embed, silent=True)
                DroppyCog.ctx_refs[ctx.id] = ref
                return ref

        ref = msg = ctx.message

        if isinstance(ctx, commands.Context):
            # contextual mode
            if ctx.interaction:
                # slash command
                if not ctx.interaction.response.type:
                    # first time response
                    if thinking_indicator and not force_silent:
                        embed = helper.as_embed(
                            thinking_indicator, ref.author, footer_append=footer
                        )
                        await ctx.interaction.response.send_message(
                            embed=embed, ephemeral=force_ephemeral, silent=True
                        )
                    else:
                        await ctx.interaction.response.defer(
                            ephemeral=force_ephemeral, thinking=False
                        )

                if msg.id in DroppyCog.ctx_refs:
                    return DroppyCog.ctx_refs[msg.id]
                ref = await ctx.interaction.original_response()
                DroppyCog.ctx_refs[msg.id] = ref
            elif thinking_indicator:
                # textual command
                embed = helper.as_embed(
                    thinking_indicator, ref.author, footer_append=footer
                )
                ref = await ctx.reply(embed=embed, silent=True)
                DroppyCog.ctx_refs[msg.id] = ref
        else:
            # interaction mode
            if not ctx.response.type:
                # first time response
                if thinking_indicator and not force_silent:
                    embed = helper.as_embed(
                        thinking_indicator, ref.author, footer_append=footer
                    )
                    await ctx.response.send_message(
                        embed=embed, ephemeral=force_ephemeral, silent=True
                    )
                else:
                    await ctx.response.defer(ephemeral=force_ephemeral, thinking=False)

            if msg.id in DroppyCog.ctx_refs:
                return DroppyCog.ctx_refs[msg.id]
            ref = await ctx.original_response()
            DroppyCog.ctx_refs[msg.id] = ref

        if msg.id in DroppyCog.ctx_refs:
            return DroppyCog.ctx_refs[msg.id]
        return ref

    @staticmethod
    def get_fallback_indicator(ctx: DroppyCtx):
        locale = DroppyCog.get_ctx_locale(ctx)
        thinking_indicator = DroppyCog.translate(
            DroppyCog.config.bot.localization.fallback_indicator, locale
        )
        return thinking_indicator

    @staticmethod
    def get_fallback_errorr(ctx: DroppyCtx):
        locale = DroppyCog.get_ctx_locale(ctx)
        error_indicator = DroppyCog.translate(
            DroppyCog.config.bot.localization.fallback_error, locale
        )
        return error_indicator

    @staticmethod
    def failsafe_ref(
        thinking_indicator: Optional[str] = None,
        *,
        custom_handler: bool = False,
        force_ephemeral: bool = True,
        no_ref: bool = False,
        error_converter=None,
    ):
        """
        Decorate a command as failsafe, setup contextual reference, print the exception stack and log on fail
        """

        def failsafe_decorator(command):
            @wraps(command)
            async def async_functor(*args, **kwargs):
                nonlocal thinking_indicator
                nonlocal force_ephemeral
                ctx = kwargs.get("ctx", None)
                if not ctx:
                    ctx = helper.first_if(
                        args, lambda c: isinstance(c, get_args(DroppyCtx))
                    )

                locale = DroppyCog.get_ctx_locale(ctx)
                thinking_indicator = (
                    thinking_indicator
                    or DroppyCog.config.bot.localization.fallback_indicator
                )
                indicator = DroppyCog.translate(thinking_indicator, locale)

                if not custom_handler:
                    ref = await DroppyCog.get_ctx_ref(
                        ctx,
                        thinking_indicator=indicator,
                        force_ephemeral=force_ephemeral,
                        force_silent=no_ref,
                    )
                else:
                    ref = None

                description = DroppyCog.translate(
                    DroppyCog.config.bot.localization.fallback_error, locale
                )

                await failsafe_ainvoke(
                    command,
                    *args,
                    error_converter=error_converter,
                    description=description,
                    ref_callback=ref,
                    **kwargs,
                )

            return async_functor

        return failsafe_decorator

    @staticmethod
    def allocated(allocate_as: str):
        """
        Decorate a command as an allocated resource
        """

        if not allocate_as:
            raise DroppyBotError(f"Invalid allocation action")

        def allocated_decorator(command):
            @wraps(command)
            async def allocated_wrapper(*args, **kwargs):
                ctx = kwargs.get("ctx", None)
                if not ctx:
                    ctx = helper.first_if(
                        args, lambda c: isinstance(c, get_args(DroppyCtx))
                    )

                locale = DroppyCog.get_ctx_locale(ctx)
                allocator = DroppyCog.bot.get_cog("DroppyAllocationManager")
                author = DroppyCog.get_ctx_author(ctx)
                if allocator and author:
                    limit = allocator.check_limit(author, allocate_as)
                    if limit:
                        allocation = allocator.get_allocation(allocate_as)
                        limit_prompt = DroppyCog.translate("allocation_limited", locale)
                        limit_prompt = limit_prompt.format(
                            allocate_as,
                            allocation.allocated_user,
                            allocation.reset_interval,
                            limit,
                        )
                        raise DroppyBotError(limit_prompt)

                usage = await command(*args, **kwargs)
                if allocator and usage:
                    allocator.commit(author, allocate_as, usage)

            return allocated_wrapper

        return allocated_decorator
