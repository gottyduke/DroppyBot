from .shared import *


class GptiModels(BaseModel):
    advanced: sanitized_str
    default: sanitized_str


class GptiDimensions(BaseModel):
    square: Dimension
    vertical: Dimension
    horizontal: Dimension


class GptiQualities(BaseModel):
    standard: sanitized_str
    hd: sanitized_str


class GptiStyles(BaseModel):
    vivid: sanitized_str
    natural: sanitized_str


class GptiDefaults(BaseModel):
    model: sanitized_str
    dimension: sanitized_str
    style: sanitized_str
    quality: sanitized_str


class GptiConfigModel(BaseModel):
    dimensions: GptiDimensions
    models: GptiModels
    output: sanitized_str
    qualities: GptiQualities
    styles: GptiStyles
    defaults: GptiDefaults
    variation_max: Annotated[PositiveInt, Field(le=15)]
    painting_completed: sanitized_str
    painting_indicator: sanitized_str
