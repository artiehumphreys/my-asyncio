"""Asyncio runner for managing event loop lifetime and handling coroutine execution"""

from enum import Enum
from typing import Any, Coroutine, Self, TypeVar
from .event_loop import EventLoop, get_event_loop

T = TypeVar("T")


class _State(Enum):
    INITIALIZED = "initialized"
    CLOSED = "closed"
    RUNNING = "running"


class Runner:
    """
    Context‐manager for safely running a single EventLoop.

    Use with Runner() as r: or the run() helper to drive
    one coroutine to completion and ensure the loop is closed afterward.
    """

    def __init__(self) -> None:
        self._loop: EventLoop | None = None
        self._state: _State | None = None

    def __enter__(self) -> Self:
        """Enter the context, initializing the EventLoop if needed"""
        self._lazy_init()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context, stopping and closing the EventLoop"""
        self.close()

    def _lazy_init(self) -> None:
        """Create or re-initialize the EventLoop if not already INITIALIZED"""
        if self._state is _State.INITIALIZED:
            return
        if self._state is _State.CLOSED or self._state is None:
            self._loop = get_event_loop()
            self._state = _State.INITIALIZED
        else:
            raise RuntimeError(f"Invalid Runner state {self._state}.")

    def close(self) -> None:
        """
        Stop and dispose of the managed EventLoop.

        Once closed, the runner cannot be reused.
        """
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
        """
        Run the coroutine to completion on the managed EventLoop.

        Closes the runner upon completion or exception.
        """
        self._lazy_init()
        assert self._loop is not None and self._state is _State.INITIALIZED

        self._state = _State.RUNNING
        try:
            result = self._loop.run_until_complete(coroutine)
            return result
        finally:
            self.close()
