from common.models.shared import *


class GptiInputModel(BaseModel):
    model: sanitized_str
    prompt: sanitized_str
    size: sanitized_str
    quality: Optional[sanitized_str] = None
    style: Optional[sanitized_str] = None

    def __str__(self):
        detail = f"{self.model} {self.size}"

        if self.quality:
            detail += f" **{self.quality}**"

        if self.style:
            detail += f" **{self.style}**"

        return detail
