from __future__ import annotations
from typing import Any, Coroutine, TypeVar

from .future import Future
from .event_loop import EventLoop
from .exceptions import AsyncioError, CancelledError
from .asyncio_utils import ensure_future


T = TypeVar("T", default=None)


class Task(Future[T]):
    """
    Coroutine wrapper, extends Future (see future.py)

    https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-2.html
    """

    def __init__(
        self,
        coroutine: Coroutine[Any, T | None, T],
        *,
        loop: Any,
    ) -> None:
        super().__init__()
        self.finished: bool = False
        self._coroutine: Coroutine[Any, T | None, T] = coroutine
        self._loop: EventLoop = loop
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
            # ensure that next_awaitable is a future.
            next_awaitable = ensure_future(next_awaitable, loop=self._loop)
            next_awaitable.add_done_callback(self._step)

    def cancel(self) -> bool:
        if self.done:
            return False

        def _cancel_step(_):
            try:
                self._coroutine.throw(CancelledError())
            except CancelledError:
                self.set_exception(CancelledError())
            # pylint: disable=broad-exception-caught
            except Exception as e:
                self.set_exception(AsyncioError(str(e)))
            except BaseException as be:
                self.set_exception(AsyncioError(f"Fatal: {be!r}"))

        # enqueue _cancel_step so that the error throwing and status
        # updates are done  on the next iteration of event loop, not on the
        # current one to not interrupt execution of another task.
        # https://www.reddit.com/r/learnpython/comments/o5g1n8/are_exceptions_silenced_in_asyncio_how_do_you/
        self._loop.call_soon(_cancel_step, None)
        return True
