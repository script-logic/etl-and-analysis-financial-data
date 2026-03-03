from collections.abc import Callable
from typing import TypeVar

from .interfaces import BaseLoggerFactory

T = TypeVar("T", bound=type)


def register_in(
    registry: type[BaseLoggerFactory], name: str
) -> Callable[[T], T]:
    def decorator(cls: T) -> T:
        registry().register(name, cls)
        return cls

    return decorator
