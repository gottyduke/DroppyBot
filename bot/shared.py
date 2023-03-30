import os

from azure.cognitiveservices.speech import speech, SpeechConfig, SpeechSynthesizer, SpeechSynthesisOutputFormat
import discord
from discord.ext import commands
from prodict import Prodict
from util.logger import log
try:
    import modules.secrets
except ModuleNotFoundError:
    pass


cwd = os.path.realpath(os.path.dirname(__file__))


### shared ###
class CogBase():
    bot: commands.Bot = None
    bot_ready = False
    config: Prodict = None
    on_maintenance = False


    @staticmethod
    def as_embed(msg, color_owner: discord.User=None, color=discord.Color.red()):
        if color_owner is not None:
            color = color_owner.color
        return discord.Embed(color=color, description=msg)
    
    
    async def prepass(self, message: discord.Message):
        if  not self.bot_ready or message.author == self.bot.user or \
            not message.content.startswith(self.bot.command_prefix):
            return None
        else:
            if self.on_maintenance and message.channel.id != int(os.environ['DEV_CHANNEL']):
                await message.reply(embed=self.as_embed('>维护中<'))
                return None

            raw = message.content.strip().split(' ', 1)
            cmd = raw[0]
            if cmd == '':
                return None
            prompt = raw[1].strip() if len(raw) > 1 else ''
            return (cmd.lower(), prompt)
        

    def log(self, message: discord.Message, entry):
        if entry == '':
            return
        author = ''
        channel = ''
        if message is None:
            channel = 'internal'
        else:
            author = message.author
            channel = 'DM' if type(message.channel) is discord.DMChannel else message.guild.name
        header = f" **__[[{channel}]]__** {author} >> "
        log(header + entry)


speech_config = SpeechConfig(subscription=os.environ['ACS_KEY'], region='eastus')
speech.audio.AudioOutputConfig(filename='cache.wav')
speech_config.speech_synthesis_voice_name = 'zh-CN-XiaoyiNeural'
speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Audio24Khz96KBitRateMonoMp3)
synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=None)
