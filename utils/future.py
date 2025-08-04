"""A toy implementation of an asyncio Future object"""

from typing import Self, TypeVar, Callable, Generator, Any, cast

from .exceptions import FutureAlreadyDoneError, InvalidStateError, AsyncioError


T = TypeVar("T")


class Future[T]:
    """Type of awaitable that does not block code to be executed."""

    def __init__(self) -> None:
        self._done: bool = False
        self._exception: AsyncioError | None = None
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
    def exception(self) -> AsyncioError | None:
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

    def set_exception(self, exception: AsyncioError) -> None:
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
