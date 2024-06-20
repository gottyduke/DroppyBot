import asyncio
import common.helper as helper
import discord
import traceback

from .logger import error
from typing import Callable, Coroutine, Optional


class DroppyBotError(Exception):
    pass


def as_exception_embed(
    e: Exception, description: str, *, header_override: Optional[str] = None
):
    header_removal = ["sanitize_wrapper", "allocated_wrapper"]
    stack = traceback.format_exception(type(e), e, e.__traceback__)
    header = type(e).__name__
    clean_stack = [
        s for s in stack[2:] if not helper.first_if(header_removal, lambda h: h in s)
    ]
    full = "".join(clean_stack)
    if not isinstance(e, DroppyBotError):
        error(f"**{header}**\n```\n{full}\n```")

    header_override = header_override or header

    error_timestamp = helper.timestamp_now("%Y/%m/%d %H:%M:%S")

    embed = helper.as_embed(
        "",
        color=discord.Color.red(),
        footer_append=error_timestamp,
    ).add_field(name=header_override, value=f"```\n{str(e)}\n```", inline=False)
    embed.title = description
    return embed


def failsafe_invoke(
    callable: Callable,
    *args,
    error_override: Optional[str] = None,
    description: str = "",
    **kwargs,
):
    """
    Wrapper for a callable, invoke immediately and return result

    Return exception embed and log if failed
    """

    try:
        return callable(*args, **kwargs)
    except Exception as e:
        return as_exception_embed(
            e,
            description,
            header_override=error_override,
        )


def failsafe_ainvoke(
    awaitable: Coroutine,
    *args,
    error_override: Optional[str] = None,
    error_converter: Callable = None,
    description: str = "",
    ref_callback: Optional[discord.Message] = None,
    **kwargs,
):
    """
    Wrapper for a coroutine, invoke immediately and return Task

    Return None if failed, edit ref and log if provided
    """

    async def async_functor(awaitable: Coroutine, *args, **kwargs):
        try:
            return await awaitable(*args, **kwargs)
        except Exception as e:
            if error_converter:
                e = error_converter(e)
            if isinstance(ref_callback, discord.Message):
                await ref_callback.edit(
                    embed=as_exception_embed(
                        e,
                        description,
                        header_override=error_override,
                    ),
                    view=None,
                )
            else:
                raise e
            return None

    return asyncio.create_task(async_functor(awaitable, *args, **kwargs))
