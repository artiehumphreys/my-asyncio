import time
from typing import Callable, TypeVar, Any
from future import Future
from task import Task
from async_queue import Queue


T = TypeVar("T")
MAXSIZE = 1024


class EventLoop:
    def __init__(self) -> None:
        # queue of ready callbacks of the form (callback, args)
        self._ready: Queue[tuple[Callable[..., Any], tuple[Any, ...]]] = Queue()
        # scheduled callbacks: min heap of (when, call order, callback, args)
        self._scheduled: list[
            tuple[float, int, Callable[..., None], tuple[Any, ...]]
        ] = []
        self._seq = 0
        self._stopped = False
        # TODO: Consider selectors for I/O watchers

    def time(self) -> float:
        return time.time()

    def call_soon(self, callback: Callable[..., None], *args: Any) -> None:
        pass
