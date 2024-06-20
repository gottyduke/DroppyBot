from .shared import *


class LogModel(BaseModel):
    do_truncate: bool
    entry_truncation: PositiveInt
    session_interval: PositiveInt


class PresenceModel(BaseModel):
    details: sanitized_str
    name: sanitized_str
    type: sanitized_str


class LocalizationModel(BaseModel):
    storage: sanitized_str
    fallback_indicator: sanitized_str
    fallback_error: sanitized_str


class BotConfigModel(BaseModel):
    version: sanitized_str
    command_prefix: sanitized_str
    log: LogModel
    presence: PresenceModel
    localization: LocalizationModel
    usage_path: sanitized_str
