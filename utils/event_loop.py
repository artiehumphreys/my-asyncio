from __future__ import annotations

# defer type hint evaluation until it is needed
import time
import heapq
from typing import Any, Callable, Coroutine, TypeVar, TYPE_CHECKING

from .future import Future
from .exceptions import QueueEmpty

if TYPE_CHECKING:
    from .task import Task


T = TypeVar("T")
MAXSIZE = 1024


class EventLoop:
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
        return self._stopped

    def stop(self) -> None:
        self._stopped = True

    def time(self) -> float:
        return time.time() - self.begin

    def call_soon(self, callback: Callable[..., None], *args: Any) -> None:
        # add callable to queue to be invoked
        self._ready.put_nowait((callback, args))

    def call_later(
        self, callback: Callable[..., None], *args: Any, delay: float
    ) -> None:
        run_time = self.time() + delay
        self._seq += 1
        heapq.heappush(self._scheduled, (run_time, self._seq, callback, args))

    def create_task(self, coroutine: Coroutine[Any, Any, T]) -> Task[T]:
        from .task import Task

        task: Task[T] = Task(coroutine, loop=self)
        return task

    def run_until_complete(self, fut: Future[T] | Coroutine[Any, Any, T]) -> T:
        """
        Run the loop until the given Future or coroutine completes,
        then return its result.
        """
        if not isinstance(fut, Future):
            fut = self.create_task(fut)
        while not fut.done:
            self.run_forever()
        return fut.result()

    def run_forever(self) -> None:
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
