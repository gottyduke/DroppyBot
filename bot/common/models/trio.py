from .shared import *


class Delimiter(BaseModel):
    pack: sanitized_str
    parameter: sanitized_str
    modifier: sanitized_str


class TrioCacheModel(BaseModel):
    path: sanitized_str
    output: sanitized_str
    storage: sanitized_str
    retention: Annotated[PositiveInt, Field(le=180)]


class TrioConfigModel(BaseModel):
    delimiter: Delimiter

    cache: TrioCacheModel
    output_type: sanitized_str
    dimension: Dimension
    models_path: sanitized_str
    templates_path: sanitized_str

    cancelled_indicator: sanitized_str
    generating_completed: sanitized_str
    generating_indicator: sanitized_str
    querying_indicator: sanitized_str
    remixing_completed: sanitized_str
    remixing_indicator: sanitized_str

    concurrent_job_max: Annotated[PositiveInt, Field(le=8)]
    concurrent_timeout: Annotated[PositiveInt, Field(le=600)]

    guidance: Annotated[PositiveFloat, Field(le=30.0)]
    sampler: sanitized_str
    steps: Annotated[PositiveInt, Field(le=60)]
