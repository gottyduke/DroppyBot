import datetime
import enum
import os
import queue

from shared import CogBase

import discord
from discord.ext import commands


class SessionContext:

    class UserProfile:

        def __init__(self, owner, *, voice=None, alias=None):
            self.owner: discord.User = owner
            self.voice_type: str = voice
            self.alias: str = alias

    def __init__(self):
        self.active_voice: discord.VoiceClient = None
        self.active_users: list[SessionContext.UserProfile] = []
        self.speech_queue: queue.Queue[str] = queue.Queue()


class SessionManager(CogBase, commands.Cog):

    class ControlView(discord.ui.View):

        def __init__(self, session: SessionContext):
            super().__init__()
            self.session = session

        @discord.ui.button(label="帮助❓", style=discord.ButtonStyle.blurple)
        async def show_help(self, intrct: discord.Interaction, item):
            await intrct.response.send_message('Help!', ephemeral=True)

        @discord.ui.button(label="参加👏", style=discord.ButtonStyle.green)
        async def try_join(self, intrct: discord.Interaction, item):
            # check for active voice client
            if self.session.active_voice is None:
                if intrct.user.voice is not None:
                    self.session.active_voice = await intrct.user.voice.channel.connect()
                else:
                    await intrct.response.send_message(embed=CogBase.as_embed(f"请求的用户 `{intrct.user.name}` 并未在语音频道中!"))
                    return

            # connection failed somehow
            if self.session.active_voice is None:
                await intrct.response.send_message(embed=CogBase.as_embed("未能在此频道创建tts活动"))
                return

            # add to active users
            self.session.active_users.append(
                SessionContext.UserProfile(
                    intrct.user,
                    voice=f"{CogBase.config.tts.neural.culture}-{CogBase.config.tts.neural.default}",
                    alias=intrct.user.display_name))

            await intrct.response.send_message(embed=CogBase.as_embed("已参加当前tts活动", color=discord.Color.green()),
                                               ephemeral=True)

        @discord.ui.button(label="离开❌", style=discord.ButtonStyle.red)
        async def leave(self, intrct: discord.Interaction, item):
            self.session.active_users = list(filter(lambda u: u.owner != intrct.user, self.session.active_users))
            await intrct.response.send_message(embed=CogBase.as_embed(
                f"已离开当前tts活动 <#{self.session.active_voice.channel.id}>", color=discord.Color.green()),
                                               ephemeral=True)

    def __init__(self):
        self.active_session: dict[discord.Guild, SessionContext] = {}

    @commands.command()
    async def tts(self, ctx: commands.Context, cmd=None):
        if ctx.guild not in self.active_session:
            self.active_session[ctx.guild] = SessionContext()
        session = self.active_session[ctx.guild]
        status = None

        if session.active_voice is not None:
            status = self.as_embed("", color=discord.Color.green())
            status.title = f"当前的tts活动(正在进行): **[{ctx.guild.name}]|<#{session.active_voice.channel.id}> ({len(session.active_users)})位参加者**"

            for user in session.active_users:
                status.description += f"- {user.alias} -> `{user.owner}`"
        else:
            status = self.as_embed("当前无正在进行的tts活动, 使用`参加`按钮以创建新的tts活动")
            session.active_users.clear()

        await ctx.reply(embed=status, view=self.ControlView(session))
