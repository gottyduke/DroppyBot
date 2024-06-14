from dataclasses import dataclass


@dataclass
class TrioArtifact:
    author: str
    timestamp: str
    input_model: str
    cache: str
    seeds: list[int]
