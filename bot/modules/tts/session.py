import os

import discord
import shared

from util.logger import log
import modules.tts.endpoint as endpoint


# global
active_scope: discord.TextChannel = None
active_users = {}
active_voice = None
is_active = False


# shared embed builder
def as_embed(msg, color_owner: discord.Member = None, color=discord.Color.red()):
    if color_owner is not None:
        color = color_owner.color
    return discord.Embed(color=color, description=msg)


async def stop():
    global active_scope, active_users, active_voice, is_active

    if active_voice is not None:
        await active_voice.disconnect()
        active_voice = None

    if active_scope is not None:
        await active_scope.send(embed=as_embed('tts活动已结束'))
        log(f'**[tts]** session ended @ [{active_scope.guild.name}|{active_scope.mention}]')
        active_scope = None

    if len(active_users) != 0:
        active_users.clear()
    
    is_active = False

    endpoint.create.cancel()
    with endpoint.speech.mutex:
        endpoint.speech.queue.clear()


async def pause(pause: bool):
    global active_scope, is_active

    if active_scope is None:
        return

    is_active = False if is_active and pause else not pause
    
    await active_scope.send(embed=as_embed(f"tts活动已{'恢复' if is_active else '挂起'}"))
    return log(f"**[tts]** session {'resumed' if is_active else 'paused'} @ [{active_scope.guild.name}|{active_scope.mention}]")


async def add(target: discord.Member, channel: discord.TextChannel, voice, remove=False):
    global active_scope, active_users, active_voice, is_active

    if active_scope is None:
        active_scope = channel
    
    if shared.on_maintenance:
        active_scope = await shared.bot.fetch_channel(int(os.environ['DEV_CHANNEL']))

    status = f'`{target}` '

    if remove:
        if target in active_users:
            del active_users[target]
        status += '已离开当前tts活动'
    else:        
        if target not in active_users:
            active_users[target] = voice
        status += '已参加当前tts活动'

        # create active connection if not present
        if active_voice is None:
            if target.voice is not None:
                active_voice = await target.voice.channel.connect()
                if active_voice is not None:
                    await active_scope.send(embed=as_embed('已在此频道创建tts活动', color=discord.Color.green()))
                    log(f"**[tts]** session created @ [{active_voice.guild.name}|{active_voice.channel.mention}]")
                    is_active = True
                else:
                    await active_scope.send(embed=as_embed('未能在此频道创建tts活动'))
                    log(f"**[tts]** session creation failed @ [{active_voice.guild.name}|{active_voice.channel.mention}]")
                    await stop()
            else:
                await active_scope.send(embed=as_embed('请求的tts用户并未在语音频道中!'))
    
    await active_scope.send(embed=as_embed(status))
    return log(f"**[tts]** 'add/del' {target} >> {status}")