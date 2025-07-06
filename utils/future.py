"""A toy implementation of an asyncio Future object"""

from typing import Any, Literal
from exceptions import FutureAlreadyDoneError, InvalidStateError


__all__: tuple[Literal["Future"]] = ("Future",)


class Future:
    """Type of awaitable that does not block code to be executed."""

    def __init__(self) -> None:
        self._done: bool = False
        self._exception: Any = None
        self._result: Any = None
        self._callbacks: list[Any] = []

    def result(self):
        if self._done:
            return self._result
        raise InvalidStateError

    def add_finished_callback(self, callback):
        if self._done:
            callback(self)
        else:
            self._callbacks.append(callback)

    def set_result(self, res):
        self._done = True
        self._result = res
        for callback in self._callbacks:
            callback(self)

    def set_exception(self, exception) -> None:
        if self._done:
            raise FutureAlreadyDoneError("Future is already done")
        self._done = True
        self._exception = exception
        for callback in self._callbacks:
            callback(self)

    def __await__(self):
        if not self._done:
            yield self
        return self.result()
