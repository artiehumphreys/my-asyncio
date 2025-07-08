from collections.abc import Coroutine
from typing import Awaitable, TypeVar

from future import Future
from event import EventLoop


T = TypeVar("T")


def ensure_future(awaitable: Awaitable[T] | Future[T], *, loop: EventLoop) -> Future[T]:
    # https://peps.python.org/pep-0492/
    if isinstance(awaitable, Future):
        return awaitable
    if isinstance(awaitable, Coroutine):
        return loop.create_task(awaitable)
    raise TypeError(
        f"object provided is not a Future or Corotuine. Type: {type(awaitable).__name__}"
    )
