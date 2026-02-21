from typing import Callable, Type, TypeVar

from .interfaces import BaseLoggerFactory


T = TypeVar("T", bound=Type)


def register_in(
    registry: Type[BaseLoggerFactory], name: str
) -> Callable[[T], T]:
    def decorator(cls: T) -> T:
        registry().register(name, cls)
        return cls

    return decorator
