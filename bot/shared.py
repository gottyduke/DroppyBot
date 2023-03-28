import os
import json

from util.logger import log
import discord
from discord.ext import commands
from azure.cognitiveservices.speech import speech, SpeechConfig, SpeechSynthesizer, SpeechSynthesisOutputFormat
try:
    import modules.secrets
except ModuleNotFoundError:
    pass


cwd = os.path.realpath(os.path.dirname(__file__))
### bot control
# for dev control, lock all output to DEV_CHANNEL
on_maintenance = True


### shared ###
class CogBase():
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.bot_ready = False


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
            if on_maintenance and message.channel.id != int(os.environ['DEV_CHANNEL']):
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
        header = f" __[{'internal' if message is None else 'DM' if type(message.channel) is discord.DMChannel else message.guild.name}]__"
        log(header + entry)


### openai gpt ###
# default model
gpt_model_default = 'gpt-3.5-turbo-0301'
gpt_think_node_response = '小G思考中...'
gpt_paint_node_response = '小G乱涂乱画中...'
gpt_contextual_frame = 600.0
gpt_contextual_capacity = 12
gpt_contextual_init_message = ''


### azure tts ###
# time takes for reintroduction
tts_reintroduce_interval = 30.0
# time between available speech check
tts_speech_interval = 3.0
# regular tts routine check
tts_deleter_interval = 30.0
# tts entry maximum length
tts_nlp_truncation = 256
# tts cache storage
tts_cache_target = 'speech.wav'

speech_config = SpeechConfig(subscription=os.environ['ACS_KEY'], region='eastus')
speech.audio.AudioOutputConfig(filename=tts_cache_target)
speech_config.speech_synthesis_voice_name = 'zh-CN-XiaoyiNeural'
speech_config.set_speech_synthesis_output_format(SpeechSynthesisOutputFormat.Audio24Khz96KBitRateMonoMp3)
synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=None)
