import os

from util.config import load_config
from util.logger import setup_logger
import shared

import discord
from discord.ext import commands


### bot instance
intents = discord.Intents.default()
intents.typing = True
intents.messages = True
intents.reactions = True
intents.presences = True
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot('!', intents=intents)


### dev flag
extension_status = {
    'gpt': True,
    'tts': False
}


async def scan_and_load():
    modules = os.path.join(shared.cwd, 'modules')
    for module in os.listdir(modules):
        module_dir = os.path.join(modules, module)
        if os.path.isdir(module_dir) and os.path.exists(os.path.join(module_dir, '__init__.py')):     
            print(f">> loading module >> {module}")
            if module in extension_status and extension_status[module]:
                await bot.load_extension(f"modules.{module}.__init__")
                print('>> success')
            else:
                print('>> passed')


### initializer
@bot.event 
async def on_ready():
    config = load_config()

    print(f'{bot.user} is launching...')
    bot.command_prefix = config.bot.command_prefix
    activity = discord.Activity()
    activity.type = discord.ActivityType[config.bot.presense.type]
    activity.name = config.bot.presense.name
    activity.details = config.bot.presense.details
    await bot.change_presence(activity=activity)

    shared.CogBase.bot = bot

    await setup_logger(bot, 1)
    await scan_and_load()

    print(f'runtime version: {config.runtime.version}')

    shared.CogBase.bot_ready = True
    print(f'{bot.user} is now ready!')
            

### online!
bot.run(os.environ['BOT_TOKEN'])
