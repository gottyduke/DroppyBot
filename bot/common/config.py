import json
import os

from prodict import Prodict

import shared


def load_config(filename="rules/config.json"):
    file = os.path.join(shared.cwd, filename)
    if not os.path.exists(file):
        raise FileNotFoundError("Expecting config.json")

    config = Prodict()
    with open(file, "rb") as f:
        config = Prodict.from_dict(json.load(f))
        if config is None:
            raise RuntimeError("config file is not initialized")
        else:
            shared.CogBase.config = config

    print(f"current config profile [{os.path.relpath(file)}]")
    return config
