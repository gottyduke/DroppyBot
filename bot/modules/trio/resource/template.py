from dataclasses import dataclass


@dataclass(frozen=True)
class TrioTemplate:
    name: str
    author: str
    base_model: str
    add_models: dict
    base_prompt: str
    negative_prompt: str
    guidance: float
    steps: int
