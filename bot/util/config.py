import json
import os

import shared
from prodict import Prodict


def load_config(filename='config.json'):
    file = os.path.join(shared.cwd, filename)
    if not os.path.exists(file):
        raise FileNotFoundError('Expecting config.json')

    with open(file, 'rb') as f:
        shared.CogBase.config = Prodict.from_dict(json.load(f))
        if shared.CogBase.config is None:
            raise RuntimeError('config file is not initialized')
        print(f'current config profile [{file}]')
    