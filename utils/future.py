"""A toy implementation of an asyncio Future object"""

from typing import TypeVar, Generic, Callable, Generator, Self, Any

from exceptions import FutureAlreadyDoneError, InvalidStateError, AsyncioError

# https://peps.python.org/pep-0696/
T = TypeVar("T", default=None)


class Future(Generic[T]):
    """Type of awaitable that does not block code to be executed."""

    def __init__(self) -> None:
        self._done: bool = False
        self._exception: AsyncioError | None = None
        self._result: T | None = None
        self._callbacks: list[Callable[[Future[T]], None]] = []

    def result(self) -> T:
        if self._done:
            return self._result
        raise InvalidStateError

    @property
    def done(self) -> bool:
        return self._done

    @property
    def exception(self) -> AsyncioError | None:
        return self._exception if self._done else None

    def add_finished_callback(self, callback: Callable[[Self], None]) -> None:
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
