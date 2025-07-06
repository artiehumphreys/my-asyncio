from typing import Any, Coroutine, Optional
from future import Future
from exceptions import CancelledError


class Task(Future):
    """
    Coroutine wrapper, extends Future (see future.py)

    https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-2.html
    """

    def __init__(
        self,
        coroutine: Coroutine[Any, None, None],
        *,
        loop: Any,
    ) -> None:
        super().__init__()
        self.finished = False
        self._coroutine = coroutine
        self._loop = loop
        # TODO: enqueue task into event loop

    def _step(self, waited: Optional[Future] = None) -> None:
        """Advance the wrapped coroutine by one step."""
        if self._done:
            return

        try:
            # step coroutine forward
            if waited is None:
                # first entry
                next_awaitable = self._coroutine.send(None)
            else:
                # resume with either exception or result
                if waited.exception() is not None:
                    next_awaitable = self._coroutine.throw(waited.exception())
                else:
                    result = waited.result()
                    next_awaitable = self._coroutine.send(result)

        except StopIteration as stop:
            # complete task
            self.set_result(stop.value)

        except CancelledError:
            self.set_exception(CancelledError())

        else:
            # TODO: ensure that next_awaitable is a future.
            next_awaitable.add_finished_callback(self._step)

    def cancel(self):
        if self.done():
            return False

        def _cancel_step(_):
            try:
                self._coroutine.throw(CancelledError())
            except CancelledError:
                self.set_exception(CancelledError())
            except Exception as e:
                self.set_exception(e)

        # TODO: enqueue _cancel_step so that the error throwing and status
        # updates are done  on the next iteration of event loop, not on the
        # current one to not interrupt execution of another task.
        # https://www.reddit.com/r/learnpython/comments/o5g1n8/are_exceptions_silenced_in_asyncio_how_do_you/
        return True
