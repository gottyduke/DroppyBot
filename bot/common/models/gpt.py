from .shared import *
from typing import List, Dict


class ContextualModel(BaseModel):
    max_ctx_per_user: Annotated[PositiveInt, Field(le=128)]
    max_ctx_percentage: Annotated[PositiveFloat, Field(le=1.0)]


class SpecItemModel(BaseModel):
    max_token: PositiveInt
    name: sanitized_str


class GptModel(BaseModel):
    advanced: sanitized_str
    default: sanitized_str
    specs: List[SpecItemModel]
    vision_fidelity: sanitized_str


class GptConfigModel(BaseModel):
    contextual: ContextualModel
    user_init_path: sanitized_str
    model: GptModel
    thinking_indicator: sanitized_str
