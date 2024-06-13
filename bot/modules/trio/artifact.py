from dataclasses import dataclass
from datetime import datetime


@dataclass
class TrioArtifact:
    author: str
    timestamp: str
    input_model: str
    cache: str
    seeds: list[int]
