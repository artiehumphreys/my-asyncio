from typing import Any, Coroutine, TypeVar
from .event_loop import EventLoop
from .future import Future
from .runner import Runner

T = TypeVar("T")


def sleep(delay: float = 1.0, *, loop: EventLoop) -> Future[None]:
    fut = Future[None]()
    loop.call_later(fut.set_result, None, delay=delay)
    return fut


def run(coroutine: Coroutine[Any, Any, T]) -> T:
    with Runner() as runner:
        return runner.run(coroutine=coroutine)


def gather(*aws: Coroutine[Any, Any, T] | Future[T]) -> None:
    pass
