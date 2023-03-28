import enum
import os
import re

import modules.tts.endpoint as endpoint
import modules.tts.nlp as nlp
import modules.tts.session as session
import shared
import discord
from discord.ext import tasks
from util.logger import log



# shared embed builder
def as_embed(msg, color_owner: discord.User = None, color=discord.Color.red()):
    if color_owner is not None:
        color = color_owner.color
    return discord.Embed(color=color, description=msg)


# global
delayed_deleter:discord.User = []


# session deleter
@tasks.loop(seconds=shared.tts_deleter_interval)
async def routine_check():
    global delayed_deleter

    for user in delayed_deleter:
        if user in session.active_users:
            del session.active_users[user]

    # check for lingering idle connection
    if len(session.active_users) == 0 or session.active_voice is None:
        await session.stop()


# export
# tts cmd prompt
@shared.bot.listen()
async def on_message(message: discord.Message):
    if not shared.bot_ready or message.author == shared.bot.user:
        return
    
    raw = message.content.strip().split(' ', 1)
    cmd = raw[0]
    prompt = raw[1].strip() if len(raw) > 1 else ''

    if cmd.startswith(shared.bot.command_prefix):
        if cmd[1:] == 'tts':
            # check current session
            if prompt == '':
                if session.active_scope is not None and session.active_voice is not None and len(session.active_users) != 0:
                    report = f"当前的tts活动({'正在进行' if session.is_active else '已被暂停'}): "
                    report += f"**[{session.active_voice.guild.name}|{session.active_voice.channel.mention}] ({len(session.active_users.keys())})位参加者**"
                    for user in session.active_users:
                        report += f"\n- `{user}`"
                    await message.reply(embed=as_embed(report))
                else:
                    await message.reply(embed=as_embed('当前无tts活动'))
            else:
                raw = prompt.split(' ', 1)
                cmd = raw[0].lower()
                prompt = raw[1].split(' ', 1) if len(raw) > 1 else ''

                if cmd == 'add' or cmd == 'del':
                    if prompt[0] == '':
                        await message.reply(embed=as_embed(f'未请求tts用户! 语法: `!tts {cmd} 用户名`'))
                    else:
                        user = message.guild.get_member_named(prompt[0])
                        if user is None:
                            await message.reply(embed=as_embed(f'请求的tts用户`{prompt[0]}`不存在! 语法: `!tts {cmd} 用户名`'))
                        else:
                            await session.add(user, message.channel, prompt[1] if len(prompt) > 1 else None, False if cmd == 'add' else True)
                elif cmd == 'resume' or cmd == 'pause':
                    await session.pause(True if cmd == 'pause' else False)
                elif cmd == 'stop':
                    await session.stop()
                else:
                    await message.add_reaction('❓')
        
        if not routine_check.is_running():        
            routine_check.cancel()
            routine_check.start()
    elif session.active_scope == message.channel and len(session.active_users) != 0 and session.is_active:
        # process tts messages from active participants
        if message.author in session.active_users and len(message.clean_content) <= shared.tts_nlp_truncation:
            speech = await nlp.process(message)
            for spc in speech:
                endpoint.speech.put(spc)
            
            if not endpoint.create.is_running():
                endpoint.create.cancel()
                endpoint.create.start()

        