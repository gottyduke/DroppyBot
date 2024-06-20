from typing import Callable, TypeVar, Iterable


T = TypeVar("T")


def first_if(iterable: Iterable[T], predicate: Callable[[T], bool]):
    return next((x for x in iterable if predicate(x)), None)
