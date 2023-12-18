import json
import os
from datetime import datetime, timedelta


from bot.shared import CogBase, cwd

import discord
import openai
from discord.ext import commands
from prodict import Prodict


class TelemetryHandler(CogBase, commands.Cog):
    def generate_help_info(self):
        help_info = [
            discord.Embed(
                color=discord.Color.blurple(),
                title="Telemetry",
                description="""
                """,
            )
        ]

        return help_info

    def __init__(self):
        self.user_data = {}
        self.recordingInterval = 60

        self.help_info["Telemetry"] = self.generate_help_info()

        
    def load_user_init(self):
        user_data = {}
        user_data_path = os.path.join(cwd, "rules/telemetry.json")
        if os.path.exists(user_data_path):
            try:
                with open(user_data_path, "rb") as f:
                    for user, data in json.load(f).items():
                        user_data[int(user)] = str(data)
            except json.JSONDecodeError:
                user_data = {}

        return user_data

    def save_user_init(self):
        for user, data in self.user_data.copy().items():
            if data is None or data == "" or data.isspace():
                del self.user_data[user]

        user_data_path = os.path.join(cwd, "rules/telemetry.json")
        with open(user_data_path, "w", encoding="utf-8") as f:
            json.dump(self.user_data, f, indent=4, sort_keys=True, ensure_ascii=False)


    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        uid = member.id

        if after.channel is not None:
        # 用户加入了频道
        self.user_data[uid] = {'joined_at': datetime.now(), 'total_time': self.user_data.get(uid, {'joined_at': None, 'total_time': timedelta()}).get('total_time')}
    else:
        # 用户离开了频道或者离开了服务器
        if uid in self.user_data:    
            joined_time = self.user_data[uid].get('joined_at')
            total_time_old = self.user_data[uid].get('total_time')
            if joined_time is not None:
                total_time_new = total_time_old + (datetime.now() - joined_time)
                self.user_data[uid] = {'joined_at': None, 'total_time': total_time_new}

        self.save_user_init()
