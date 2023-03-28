import datetime
import os

import shared
import discord
#import modules.tts.tts as tts
from discord.ext import commands
from util.logger import setup_logger
from util.config import load_config, get_config

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

activity = discord.Activity(
    type=discord.ActivityType.listening,
    name='whispererererer..')

bot = commands.Bot('!', intents=intents)


### bot control
# for dev control, lock all output to DEV_CHANNEL
on_maintenance = True


### initializer
@bot.event 
async def on_ready():
    global activity

    print(f'{bot.user} is launching...')

    #tts.routine_check.start()
    await bot.change_presence(activity=activity)
    await setup_logger(bot)
    
    print(f'{bot.user} is setting up...')

    modules = os.path.join(shared.cwd, 'modules')
    for module in os.listdir(modules):
        module_dir = os.path.join(modules, module)
        if os.path.isdir(module_dir) and os.path.exists(os.path.join(module_dir, '__init__.py')):     
            print(f"loading module >> {module}")
            await bot.load_extension(f"modules.{module}.__init__")
            print('success')

    config = await load_config(bot)
    print(f'bot version: {config.runtime.version}')

    print(f'{bot.user} is now ready!')
            

### online!
bot.run(os.environ['BOT_TOKEN'])