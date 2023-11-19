import os

import bot.shared as shared
import discord


# shared embed builder
def as_embed(msg, color_owner: discord.User = None, color=discord.Color.red()):
    if color_owner is not None:
        color = color_owner.color
    return discord.Embed(color=color, description=msg)


# export
async def relay_external(channel, detail, message: discord.Message):
    if message.author.id != int(os.environ["DEV_ID"]):
        return
    detail = detail.split(" ", 1)
    channel = shared.bot.get_channel(int(detail[0]))
    if channel is not None:
        await channel.send(
            embed=discord.Embed(description=detail[1], color=discord.Color.red())
        )
    return f" {detail}"


payload = {}


async def relay_internal(channel, detail, message: discord.Message):
    if message.author.id != int(os.environ["DEV_ID"]):
        return

    global payload
    detail = detail.lower().split(" ")
    if detail[0] == "toggle":
        if detail[1] == "maintenance":
            shared.on_maintenance = not shared.on_maintenance
            if shared.on_maintenance:
                payload["log_interval"] = shared.log_interval
                shared.log_interval = 5.0
                await channel.send(embed=as_embed(">进入维护模式<"))
            else:
                shared.log_interval = payload["log_interval"]
                await channel.send(
                    embed=as_embed(">进入工作模式<", color=discord.Color.green())
                )
            return f" | `{not shared.on_maintenance}` -> `{shared.on_maintenance}`"
    elif detail[0] == "activity":
        activity = discord.Activity()
        activity.type = discord.ActivityType[detail[1]]
        activity.name = detail[2]
        old_activity = shared.bot.activity
        shared.bot.change_presence(activity=activity)
        return f" | `{old_activity.name}` -> `{activity.type.name}`"
    elif detail[0] == "tts":
        dev = shared.bot.get_user(int(os.environ["DEV_ID"]))
        channel = await dev.create_dm()

        if channel is None:
            return

        channel.send()
