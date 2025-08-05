from enum import Enum
from typing import Any, Coroutine, Self, TypeVar
from .event_loop import EventLoop, get_event_loop

T = TypeVar("T")


class _State(Enum):
    INITIALIZED = "initialized"
    CLOSED = "closed"
    RUNNING = "running"


class Runner:
    def __init__(self) -> None:
        self._loop: EventLoop | None = None
        self._state: _State | None = None

    def __enter__(self) -> Self:
        self._lazy_init()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _lazy_init(self) -> None:
        if self._state is _State.INITIALIZED:
            return
        if self._state is _State.CLOSED or self._state is None:
            self._loop = get_event_loop()
            self._state = _State.INITIALIZED
        else:
            raise RuntimeError(f"Invalid Runner state {self._state}.")

    def close(self) -> None:
        if self._state is _State.CLOSED:
            return

        if self._loop is not None:
            try:
                self._loop.stop()
            except Exception:
                pass
        self._loop = None
        self._state = _State.CLOSED

    def run(self, coroutine: Coroutine[Any, Any, T]) -> T:
        self._lazy_init()
        assert self._loop is not None and self._state is _State.INITIALIZED

        self._state = _State.RUNNING
        try:
            result = self._loop.run_until_complete(coroutine)
            return result
        finally:
            self.close()
