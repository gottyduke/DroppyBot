import time

from .helpers.string import *
from .helpers.timestamp import *
from .helpers.iterable import *
from functools import wraps
from typing import Iterable


def extract_attr(packed: T, key: str):
    if isinstance(packed, dict):
        return packed[key]
    else:
        return getattr(packed, key, "")


def first_iequal(iterable: Iterable[T], key: str, rhs: str):
    return first_if(iterable, lambda i: iequal(extract_attr(i, key), rhs))


latency_sessions = {}


def latency_start(session_id: int):
    start = time.perf_counter()
    latency_sessions[session_id] = start
    return start


def latency_end(session_id: int):
    elapsed = time.perf_counter() - latency_sessions[session_id]
    elapsed = int(round(elapsed * 1000))
    del latency_sessions[session_id]
    return elapsed


def sanitize(command):
    """
    Remove leading/trailing spaces from all parameters
    """

    @wraps(command)
    async def sanitize_wrapper(*args, **kwargs):
        args = [arg.strip() if isinstance(arg, str) else arg for arg in args]
        kwargs = {k: v.strip() if isinstance(v, str) else v for k, v in kwargs.items()}
        return await command(*args, **kwargs)

    return sanitize_wrapper
