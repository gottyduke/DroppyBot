from common.models.shared import *


class Usage(BaseModel):
    user_id: Annotated[int, Field(frozen=True)]
    used: float
    count: int
    cycle: date_time
