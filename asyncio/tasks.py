from typing import Any, Awaitable, Coroutine, TypeVar
from .future import Future
from .event_loop import EventLoop
from .runner import Runner

T = TypeVar("T", default=None)


def ensure_future(awaitable: Awaitable[T], *, loop: EventLoop) -> Future[T]:
    # https://peps.python.org/pep-0492/
    if isinstance(awaitable, Future):
        return awaitable
    if isinstance(awaitable, Coroutine):
        return loop.create_task(awaitable)
    raise TypeError(
        f"object provided is not a Future or Corotuine. Type: {type(awaitable).__name__}"
    )


def sleep(delay: float = 1.0, *, loop: EventLoop) -> Future[None]:
    fut = Future[None]()
    loop.call_later(fut.set_result, None, delay=delay)
    return fut


def run(coroutine: Coroutine[Any, Any, T]) -> T:
    with Runner() as runner:
        return runner.run(coroutine=coroutine)


def gather(*aws: Coroutine[Any, Any, T] | Future[T]) -> None:
    pass
