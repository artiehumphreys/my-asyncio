"""A toy implementation of the asyncio Future and Task objects"""

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
    CancelledError,
    FutureAlreadyDoneError,
    InvalidStateError,
)

if TYPE_CHECKING:
    from .event_loop import EventLoop

T = TypeVar("T")


class Future[T]:
    """
    An awaitable placeholder for a result to be set later.

    Futures can be awaited with await fut, and callbacks can be
    registered with add_done_callback.
    """

    def __init__(self) -> None:
        self._done: bool = False
        self._cancelled: bool = False
        self._exception: BaseException | None = None
        self._result: T | None = None
        self._callbacks: list[Callable[[Self], None]] = []

    def cancel(self) -> bool:
        """Cancel the execution of this Future"""
        if self._done:
            return False
        self._cancelled = True
        self.set_exception(CancelledError())
        return True

    def result(self) -> T:
        """Return result if the Future has completed, otherwise raise InvalidStateError"""
        if not self._done:
            raise InvalidStateError
        if self._exception is not None:
            raise self._exception
        if self._result is not None:
            return self._result
        return cast(T, self._result)

    @property
    def cancelled(self) -> bool:
        """Return True if the Future was cancelled"""
        return self._cancelled

    @property
    def done(self) -> bool:
        """Return True if the Future is completed"""
        return self._done

    @property
    def exception(self) -> BaseException | None:
        """Return the exception raised during execution of the coroutine otherwise None"""
        return self._exception if self._done else None

    def add_done_callback(self, callback: Callable[[Self], None]) -> None:
        """
        Register the given callback to be invoked when the future completes.

        If the future is already done, the callback is called immediately
        """
        if self._done:
            callback(self)
        else:
            self._callbacks.append(callback)

    def set_result(self, res: T) -> None:
        """Mark the future as done and set the result of the Future to res"""
        self._done = True
        self._result = res
        for callback in self._callbacks:
            callback(self)

    def set_exception(self, exception: BaseException) -> None:
        """Mark the Future as done with an error and store the exception"""
        if self._done:
            raise FutureAlreadyDoneError("Future is already done")
        self._done = True
        self._exception = exception
        for callback in self._callbacks:
            callback(self)

    def __await__(self) -> Generator[Any, None, T]:
        """Yield control to the EventLoop until this Future is done, then return its result."""
        if not self._done:
            yield self
        return self.result()


class Task(Future[T]):
    """
    Wraps and drives a coroutine, completing when it returns.

    This extends Future[T] and schedules its coroutine on the loop
    via successive calls to _step(). Cancellation ejects a
    CancelledError into the coroutine.

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
        self._cancel_requested = False
        self._coroutine: Coroutine[Any, T | None, T] = coroutine
        self._waiting_on: Future[T] | None = None
        self._loop: EventLoop = loop or get_event_loop()
        # enqueue task into event loop
        self._loop.call_soon(self._step)

    def cancel(self) -> bool:
        if self.done:
            return False
        self._cancel_requested = True
        if self._waiting_on is not None:
            self._waiting_on.cancel()
        else:
            self._loop.call_soon(self._step)
        return True

    def _step(self, waited: Future[T] | None = None) -> None:
        """
        Advance the wrapped coroutine by one step, sending in the awaited result
        or throwing in any exception.
        """
        if self.done:
            return

        try:
            if self._cancel_requested:
                # inject cancellation immediately at next resume
                self._cancel_requested = False
                next_awaitable = self._coroutine.throw(CancelledError())
            # step coroutine forward
            elif waited is None:
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
            self._waiting_on = next_awaitable
            next_awaitable.add_done_callback(self._step)
