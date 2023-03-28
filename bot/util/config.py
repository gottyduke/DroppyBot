import json
import os

import shared
from prodict import Prodict


class Config(shared.CogBase):
    def __init__(self, bot):
        super().__init__(bot)

        file = os.path.join(shared.cwd, 'config.json')
        if not os.path.exists(file):
            raise FileNotFoundError('Expecting config.json')

        with open(file, 'rb') as f:
            self.config = Prodict.from_dict(json.load(f))
            self.log(None, f'loaded config file [{file}]')
        
    def get(self):
        return self.config
        

config: Config = None


async def load_config(bot):
    global config

    config = Config(bot)
    return config.get()


def get_config():
    return config.get()
