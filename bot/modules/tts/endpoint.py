import asyncio
import os
import datetime
from queue import Queue

from azure.cognitiveservices.speech import AudioDataStream
import discord
from discord.ext import tasks
import shared
from util.logger import log
import modules.tts.nlp as nlp
import modules.tts.session as session


# global
speech = Queue[nlp.Speech]()
last_speaker = ('', datetime.datetime.now(datetime.timezone.utc))


# export
async def speak(text):
    print(f"[ssh] {text}")

    if not session.is_active or session.active_voice is None:
        return

    result = shared.synthesizer.speak_text_async(text).get()
    stream = AudioDataStream(result)
    stream.save_to_wav_file(shared.tts_cache_target)

    session.active_voice.play(discord.FFmpegPCMAudio(shared.tts_cache_target))
    while session.active_voice.is_playing():
        await asyncio.sleep(1)
        
    return


@tasks.loop(seconds=shared.tts_speech_interval)
async def create():
    global last_speaker, speech

    if not session.is_active:
        return

    while not speech.empty():
        spc = speech.get()
        if spc is None:
            break
        body = spc.speaker
        match spc.type:
            case nlp.SpeechType.TEXT:
                if last_speaker[0] == spc.speaker and (spc.timestamp - last_speaker[1]).total_seconds() <= shared.tts_reintroduce_interval:
                    body = spc.content
                else:
                    body += f"说: {spc.content}"
            case nlp.SpeechType.EMOJI:
                body += '发送了一张图片 '
            case nlp.SpeechType.URL:
                body += '发送了一条链接 '
            case nlp.SpeechType.MENTION:
                body += f'说: 喂, {spc.content}! '
            case nlp.SpeechType.REPLY:
                body += f'回复了{spc.content}的消息'
        
        last_speaker = (spc.speaker, spc.timestamp)
        await speak(body)
                