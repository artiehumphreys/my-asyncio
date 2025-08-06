"""A toy implementation of an asyncio Future object"""

from __future__ import annotations
from typing import (
    Any,
    Callable,
    cast,
    Coroutine,
    Generator,
    Self,
    TypeVar,
    TYPE_CHECKING,
)
from .event_loop import get_event_loop
from .exceptions import (
    AsyncioError,
    CancelledError,
    FutureAlreadyDoneError,
    InvalidStateError,
)

if TYPE_CHECKING:
    from .event_loop import EventLoop

T = TypeVar("T")


class Future[T]:
    """Type of awaitable that does not block code to be executed."""

    def __init__(self) -> None:
        self._done: bool = False
        self._exception: BaseException | None = None
        self._result: T | None = None
        self._callbacks: list[Callable[[Self], None]] = []

    def result(self) -> T:
        if not self._done:
            raise InvalidStateError
        if self._result is not None:
            return self._result
        return cast(T, self._result)

    @property
    def done(self) -> bool:
        return self._done

    @property
    def exception(self) -> BaseException | None:
        return self._exception if self._done else None

    def add_done_callback(self, callback: Callable[[Self], None]) -> None:
        if self._done:
            callback(self)
        else:
            self._callbacks.append(callback)

    def set_result(self, res: T) -> None:
        self._done = True
        self._result = res
        for callback in self._callbacks:
            callback(self)

    def set_exception(self, exception: BaseException) -> None:
        if self._done:
            raise FutureAlreadyDoneError("Future is already done")
        self._done = True
        self._exception = exception
        for callback in self._callbacks:
            callback(self)

    def __await__(self) -> Generator[Any, None, T]:
        if not self._done:
            yield self
        return self.result()


class Task(Future[T]):
    """
    Coroutine wrapper, extends Future (see future.py)

    https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-2.html
    """

    def __init__(
        self,
        coroutine: Coroutine[Any, T | None, T],
        *,
        loop: EventLoop | None,
    ) -> None:
        super().__init__()
        self.finished: bool = False
        self._coroutine: Coroutine[Any, T | None, T] = coroutine
        self._loop: EventLoop = loop or get_event_loop()
        # enqueue task into event loop
        self._loop.call_soon(self._step)

    def _step(self, waited: Future[T] | None = None) -> None:
        """Advance the wrapped coroutine by one step."""
        if self.done:
            return

        try:
            # step coroutine forward
            if waited is None:
                # first entry
                next_awaitable = self._coroutine.send(None)
            else:
                # resume with either exception or result
                if waited.exception is not None:
                    next_awaitable = self._coroutine.throw(waited.exception)
                else:
                    result = waited.result()
                    next_awaitable = self._coroutine.send(result)

        except StopIteration as stop:
            # complete task
            self.set_result(stop.value)

        except CancelledError:
            self.set_exception(CancelledError())

        else:
            from .tasks import ensure_future

            # ensure that next_awaitable is a future.
            next_awaitable = ensure_future(next_awaitable)
            next_awaitable.add_done_callback(self._step)
