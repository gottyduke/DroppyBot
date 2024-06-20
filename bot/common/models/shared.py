import json
import os

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PlainSerializer,
    PositiveFloat,
    PositiveInt,
)
from typing_extensions import Annotated, List, Optional


sanitized_str = Annotated[str, Field(strip_whitespace=True)]
date_time = Annotated[
    datetime,
    PlainSerializer(lambda d: d.strftime("%Y-%m-%d %H:%M:%S"), return_type=str),
]


class Dimension(BaseModel):
    width: PositiveInt
    height: PositiveInt

    def __str__(self):
        return f"{self.width}x{self.height}"
