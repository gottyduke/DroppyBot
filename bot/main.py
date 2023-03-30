import datetime
import os

import discord
from discord.ext import commands
from util.config import load_config
from util.logger import setup_logger
import shared

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


### dev flag
extension_status = {
    'gpt': True
}


### initializer
@bot.event 
async def on_ready():
    global activity
    
    print(f'{bot.user} is launching...')
    await bot.change_presence(activity=activity)
    shared.CogBase.bot = bot

    load_config()

    #tts.routine_check.start()
    await setup_logger(bot, 1.0)

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

    print(f'runtime version: {shared.CogBase.config.runtime.version}')

    shared.CogBase.bot_ready = True
    print(f'{bot.user} is now ready!')
            

### online!
bot.run(os.environ['BOT_TOKEN'])
