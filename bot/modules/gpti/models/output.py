from common.models.shared import *


class GptiOutputModel(BaseModel):
    cost: float
    url: sanitized_str
    latency: sanitized_str
    revised: sanitized_str
