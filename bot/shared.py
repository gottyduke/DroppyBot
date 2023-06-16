import os
from typing import Optional

import discord
from azure.cognitiveservices.speech import (
    speech,
    SpeechConfig,
    SpeechSynthesizer,
    SpeechSynthesisOutputFormat,
)
from discord.ext import commands
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

    @staticmethod
    def as_embed(msg, color_owner=None, color=discord.Color.red()):
        """
        shared embed builder to accomodate user's top role color
        also auto adds some footer texts
        """

        embed = discord.Embed(description=msg).set_footer(
            text=f"使用 {CogBase.bot.command_prefix}help 命令来查看新功能!",
            icon_url=CogBase.bot.user.display_avatar.url,
        )

        if color_owner is not None:
            color = color_owner.color
            embed.set_author(
                name=color_owner.display_name, icon_url=color_owner.display_avatar.url
            )

        embed.color = color
        return embed

    async def prepass(self, message: discord.Message):
        """
        optional 1st layer filter for messaging if using exclusive commanding
        """

        if not self.bot_ready or message.author == self.bot.user:
            return None
        else:
            if self.on_maintenance and message.channel.id != int(
                os.environ["DEV_CHANNEL"]
            ):
                await message.reply(embed=self.as_embed(">维护中<"))
                return None

            raw = message.content.strip().split(" ", 1)
            cmd = raw[0]
            if cmd == "":
                return None
            prompt = raw[1].strip() if len(raw) > 1 else ""
            return (cmd.lower(), prompt)

    @staticmethod
    def log(message: discord.Message, entry: str):
        """
        shared logger method, syncs to console output
        """

        if entry.strip() == "":
            return

        if message is None:
            channel = "internal"
        else:
            author = message.author
            channel = (
                "DM"
                if type(message.channel) is discord.DMChannel
                else message.guild.name
            )

        # log format
        util.logger.log(f" **__[[{channel}]]__** {author} >> {entry}")


speech_config = SpeechConfig(subscription=os.environ["ACS_KEY"], region="eastus")
speech.audio.AudioOutputConfig(filename="cache.wav")
speech_config.speech_synthesis_voice_name = "zh-CN-XiaoyiNeural"
speech_config.set_speech_synthesis_output_format(
    SpeechSynthesisOutputFormat.Audio24Khz96KBitRateMonoMp3
)
synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=None)
