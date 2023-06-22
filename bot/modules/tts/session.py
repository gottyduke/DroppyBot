import datetime
import enum
import os
import queue

from shared import CogBase

from azure.cognitiveservices.speech import AudioDataStream
import discord
from discord.ext import commands, tasks


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


class SessionControlView(discord.ui.View):
    def __init__(self, session: SessionContext):
        super().__init__()
        self.session = session
        self.default_voice = (
            f"{CogBase.config.tts.neural.culture}-{CogBase.config.tts.neural.default}"
        )

    async def first_time_connect(self, intrct: discord.Interaction):
        if intrct.user.voice is None or intrct.user.voice.channel is None:
            await intrct.response.send_message(
                embed=CogBase.as_embed(f"请求的用户 `{intrct.user.name}` 并未在语音频道中!")
            )
            return False

        self.session.active_voice = await intrct.user.voice.channel.connect()
        success = self.session.active_voice is not None

        # connection failed somehow
        if not success:
            embed = CogBase.as_embed(
                "未能在此频道创建tts活动!", color=discord.Color.red()
            ).set_footer(text="原因: 无法连接至语音", icon_url=CogBase.bot.user.avatar.url)
        else:
            embed = CogBase.as_embed(
                "成功在此频道创建tts活动!", color=discord.Color.green()
            ).set_footer(text="使用 !tts 命令控制活动!", icon_url=CogBase.bot.user.avatar.url)

        CogBase.log(
            None,
            f"tts first time connection {'succeeded' if success else 'failed'} @ <#{self.session.active_voice.channel.id}>",
        )

        await intrct.channel.send(embed=embed)
        return success

    async def cleanup_session(self, intrct: discord.Interaction):
        self.session.active_voice.cleanup()
        await self.session.active_voice.disconnect()

        CogBase.log(
            None,
            f"tts connection closed @ <#{intrct.user.voice.channel.id}>",
        )

    @discord.ui.button(label="👏参加🎤", style=discord.ButtonStyle.green)
    async def try_join(self, intrct: discord.Interaction, btn: discord.ui.Button):
        # check for active voice client
        if self.session.active_voice is None and not await self.first_time_connect(
            intrct
        ):
            return

        # add to active users
        self.session.active_users.append(
            SessionContext.UserProfile(
                intrct.user,
                voice=self.default_voice,
                alias=intrct.user.display_name,
            )
        )

        await intrct.response.send_message(
            embed=CogBase.as_embed(
                f"已参加当前tts活动 <#{self.session.active_voice.channel.id}>",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="❌离开❌", style=discord.ButtonStyle.red)
    async def leave(self, intrct: discord.Interaction, btn: discord.ui.Button):
        self.session.active_users = list(
            filter(lambda u: u.owner != intrct.user, self.session.active_users)
        )
        await intrct.response.send_message(
            embed=CogBase.as_embed(
                f"已离开当前tts活动 <#{self.session.active_voice.channel.id}>",
                color=discord.Color.blurple(),
            ),
            ephemeral=True,
        )

        if len(self.session.active_users) == 0:
            await self.cleanup_session(intrct)


class SessionManager(CogBase, commands.Cog):
    def __init__(self):
        self.active_session: dict[discord.Guild, SessionContext] = {}
        self.current_allowed_guild = 974365925526626304
        self.guild: discord.Guild = None
