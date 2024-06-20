import common.helper as helper
import discord
import os

from .cog import DroppyCog
from .config import DroppyBotConfig
from .exception import failsafe_ainvoke, DroppyBotError
from .logger import log
from .translator import DroppyTranslator
from discord.ext import commands
from functools import wraps
from typing import Optional, Union, get_args


class DroppyView(discord.ui.View):
    def __init__(self, cog: DroppyCog, *args, **kwards):
        timeout = kwards.pop("timeout", None)
        super().__init__(timeout=timeout, *args, **kwards)
        self.cog = cog

    def get_field(self, embeds: list[discord.Embed], name: str):
        return helper.first_iequal(sum([e.fields for e in embeds], []), "name", name)


class DroppyModal(discord.ui.Modal):
    def __init__(self, view: DroppyView, title: str):
        super().__init__(title=title, timeout=None)
        self.view = view
        self.cog = self.view.cog
