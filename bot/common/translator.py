import discord
import os

from .config import load_json
from discord.app_commands import Translator, locale_str, TranslationContext


class DroppyTranslator(Translator):
    def __init__(self, storage):
        super().__init__()

        self.storage = storage
        self.loaded_str: dict[discord.Locale, dict] = {}
        self.load_translations()

    def load_translations(self):
        """
        Load all translation jsons from locale file and locale folder
        """

        for root, containers, strings in os.walk(self.storage):
            for container in containers:
                try:
                    locale = discord.Locale(container)
                except:
                    continue

                for subroot, _, substrings in os.walk(os.path.join(root, container)):
                    for substring in substrings:
                        content = load_json(os.path.join(subroot, substring))
                        contents = self.loaded_str.setdefault(locale, {})
                        contents.update(content)

            for string in strings:
                try:
                    locale = discord.Locale(os.path.splitext(string)[0])
                except:
                    continue

                content = load_json(os.path.join(root, string))
                contents = self.loaded_str.setdefault(locale, {})
                contents.update(content)

    def get_text(
        self, string: str, locale: discord.Locale = discord.Locale.american_english
    ):
        if locale.name not in [l.name for l in self.loaded_str.keys()]:
            return None
        return self.loaded_str[locale].get(string, None)

    async def translate(
        self, string: locale_str, locale: discord.Locale, context: TranslationContext
    ):
        return self.get_text(str(string), locale)
