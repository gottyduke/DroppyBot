from dataclasses import dataclass


@dataclass(frozen=True)
class TrioCache:
    author: str
    timestamp: str
    input_model: str
    seeds: list[int]
