from abc import ABCMeta
from threading import Lock
from typing import Any, Type


class Singleton(ABCMeta):
    __instances: dict[Type, object] = {}
    __lock: Lock = Lock()

    def __call__(cls, *args: Any, **kwargs: Any):
        metaclass = type(cls)
        if cls not in metaclass.__instances:
            with metaclass.__lock:
                if cls not in metaclass.__instances:
                    metaclass.__instances[cls] = super().__call__(
                        *args, **kwargs
                    )
        return metaclass.__instances[cls]

    @classmethod
    def clear_singleton(cls):
        if cls in cls.__instances:
            del cls.__instances[cls]
