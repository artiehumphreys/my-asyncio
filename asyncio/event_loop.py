"""Asyncio‐style EventLoop for scheduling and executing coroutine callbacks."""

from __future__ import annotations

# defer type hint evaluation until it is needed
import time
import heapq
from typing import Any, Callable, Coroutine, TypeVar, TYPE_CHECKING

from .exceptions import QueueEmpty

if TYPE_CHECKING:
    from .future import Task, Future

T = TypeVar("T")
MAXSIZE = 1024
_current_loop: EventLoop | None = None


def get_event_loop() -> EventLoop:
    """Return the global event loop, creating one if necessary"""
    global _current_loop
    if not _current_loop:
        _current_loop = EventLoop()
    return _current_loop


def set_event_loop(loop: EventLoop) -> None:
    """Set the global EventLoop instance"""
    global _current_loop
    _current_loop = loop


class EventLoop:
    """
    Manages the ready-queue and timer-heap for coroutine callbacks

    Callbacks can be scheduled immediately via call_soon or after a delay
    via call_later. Coroutines are driven to completion by wrapping them
    in Task instances (via create_task), which in turn use this loop.
    """

    def __init__(self) -> None:
        from .async_queue import Queue

        self.begin = time.time()

        # queue of ready callbacks of the form (callback, args)
        self._ready: Queue[tuple[Callable[..., Any], tuple[Any, ...]]] = Queue(
            MAXSIZE, loop=self
        )
        # scheduled callbacks: min heap of (when, call order, callback, args)
        self._scheduled: list[
            tuple[float, int, Callable[..., None], tuple[Any, ...]]
        ] = []
        self._seq = 0
        self._stopped = False
        # TODO: Consider selectors for I/O watchers

    @property
    def stopped(self) -> bool:
        """Return True if the event loop has been stopped"""
        return self._stopped

    def stop(self) -> None:
        """Stop the event loop"""
        self._stopped = True

    def time(self) -> float:
        """Return the elapsed time since the loop was created"""
        return time.time() - self.begin

    def call_soon(self, callback: Callable[..., None], *args: Any) -> None:
        """Schedule a callback to run on the next loop iteration"""
        # add callable to queue to be invoked
        self._ready.put_nowait((callback, args))

    def call_later(
        self, callback: Callable[..., None], *args: Any, delay: float
    ) -> None:
        """Schedule a callback to run after delay seconds"""
        run_time = self.time() + delay
        self._seq += 1
        heapq.heappush(self._scheduled, (run_time, self._seq, callback, args))

    def create_task(self, coroutine: Coroutine[Any, Any, T]) -> Task[T]:
        """
        Wrap a coroutine in a Task object and schedule its first step.

        The returned Task is also a Future[T] you can await.
        """
        from .future import Task

        task: Task[T] = Task(coroutine, loop=self)
        return task

    def run_until_complete(self, fut: Future[T] | Coroutine[Any, Any, T]) -> T:
        """Run the loop until fut completes, then return its result."""
        from .future import Future

        if not isinstance(fut, Future):
            fut = self.create_task(fut)
        while not fut.done:
            self.run_forever()
        return fut.result()

    def run_forever(self) -> None:
        """Run the event loop indefinitely, processing callbacks as they arrive."""
        now = self.time()
        # add ready callbacks to be processed
        while self._scheduled and self._scheduled[0][0] <= now:
            _, _, callback, args = heapq.heappop(self._scheduled)
            self.call_soon(callback, *args)

        # process a single ready callback
        try:
            callback, args = self._ready.get_nowait()
        except QueueEmpty:
            # If there is no work currently, wait.
            if self._scheduled:
                delay = max(0.0, self._scheduled[0][0] - self.time())
                time.sleep(delay)
            else:
                time.sleep(0.01)

        else:
            # Once we have a ready callback, execute it
            try:
                callback(*args)
            except Exception as e:
                print(f"error in callback {e}")
