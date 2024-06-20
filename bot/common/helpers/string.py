import discord

from typing import Optional, Callable, TypeVar


T = TypeVar("T")


def as_embed(
    msg,
    color_owner: Optional[discord.User] = None,
    color: discord.Color = discord.Color.from_rgb(236, 248, 248),
    footer_append: Optional[str] = "updated: 2024/06/13*",
    footer_icon: Optional[str] = None,
):
    """
    Shared embed builder to accommodate user's top role color

    Also append some footer texts
    """

    if color_owner and color_owner.color != discord.Color.default():
        color = color_owner.color

    embed = discord.Embed(description=msg, color=color)
    if footer_append:
        embed.set_footer(
            text=footer_append,
            icon_url=footer_icon,
        )

    if color_owner:
        embed.set_author(
            name=color_owner.display_name, icon_url=color_owner.display_avatar.url
        )

    return embed


def chunk_with_size(content: str, chunk_size: int):
    """
    Chunk a string to avoid length limitation
    """

    formatted = [""]

    if content is None:
        return formatted

    accum = 0
    code_block = False
    code_block_syntax = ""
    for line in content.splitlines(keepends=True):
        # preserve code block
        if "```" in line:
            code_block = not code_block
            code_block_syntax = line
        # append chunk
        formatted[-1] += line
        accum += len(line)
        # close this chunk
        if accum >= chunk_size:
            if code_block:
                formatted[-1] += "```"

            # begins new chunk
            formatted.append("")

            if code_block:
                formatted[-1] += f"{code_block_syntax}\n"
            accum = 0

    if formatted[-1].isspace() or formatted[-1] == "":
        formatted.pop()

    return formatted


def codeblock(content: str, syntax: str = ""):
    return f"```{syntax}\n{content}\n```"


def mention(user_id: int):
    return f"<@{user_id}>"


def jump_url(content: str, url: str):
    return f"[{content}]({url})"


def iequal(lhs: str, rhs: str):
    """
    Remove whitespace then casefold comparison
    """

    return lhs.strip().casefold() == rhs.strip().casefold()


def tokenize(
    content: str,
    delimiter: str = " ",
    *,
    modifier: Optional[Callable[[str], str]] = None,
):
    """
    Tokenize a string by delimiter and removes any falsey value
    """

    tokenized = [t.strip() for t in content.split(delimiter) if t.strip()]
    if modifier:
        tokenized = list(map(modifier, tokenized))
    return tokenized
