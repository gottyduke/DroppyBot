from dataclasses import dataclass
from enum import IntEnum


class TrioModelType(IntEnum):
    CKPT = 1
    LORA = 2
    VAE = 3


@dataclass
class TrioModel:
    """
    a state descriptor of an ai model
    """

    model: TrioModelType
    name: str
    urn: str
