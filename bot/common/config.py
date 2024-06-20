from .models.allocation import *
from .models.bot import *
from .models.gpt import *
from .models.gpti import *
from .models.shared import *
from .models.trio import *


class DroppyBotConfig(BaseModel):
    allocations: List[AllocationModel]
    bot: BotConfigModel
    gpt: GptConfigModel
    gpti: GptiConfigModel
    trio: TrioConfigModel


def load_config(config_storage: str = "rules/configs"):
    models = {}
    cwd = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    for root, _, files in os.walk(os.path.join(cwd, config_storage)):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, "rb") as f:
                model = os.path.splitext(os.path.basename(file_path))[0]
                print(f"reading config: {model}")
                models[model] = json.load(f)

    config = DroppyBotConfig(
        allocations=[AllocationModel(**a) for a in models["allocation"]],
        bot=BotConfigModel(**models["bot"]),
        gpt=GptConfigModel(**models["gpt"]),
        gpti=GptiConfigModel(**models["gpti"]),
        trio=TrioConfigModel(**models["trio"]),
    )

    return config


def load_json(path: str):
    json_dict = {}
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                json_dict = json.load(f)
        except Exception:
            json_dict = {}
    return json_dict


def save_json(path: str, model: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(model, indent=4))
