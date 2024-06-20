from dataclasses import dataclass
from enum import IntEnum
import re
import civitai.models

import civitai.models
import requests


class TrioModelType(IntEnum):
    CKPT = 1
    LORA = 2
    EMBEDDING = 3


@dataclass(frozen=True)
class TrioModel:
    """
    A state descriptor of an ai model
    """

    model: TrioModelType
    name: str
    urn: str

    def version(self):
        model_id = re.search(r":(\d+)@", self.urn)
        if model_id:

            response = requests.get(
                f"https://civitai.com/api/v1/models/{model_id.group(1)}",
                params={"token": os.environ["CIVITAI_API_TOKEN"]},
            )
            if response.status_code == 200:
                return Prodict.from_dict(response.json()["modelVersions"][0])
        return Prodict.from_dict({"name": "unknown"})
