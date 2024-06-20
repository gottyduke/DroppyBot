from .shared import *


class AllocationModel(BaseModel):
    action: sanitized_str
    allocated_user: float
    allocated_pool: float
    reset_interval: NonNegativeInt
