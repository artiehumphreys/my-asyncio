import time
import heapq
from typing import Callable, Coroutine, TypeVar, Any
from future import Future
from task import Task
from async_queue import Queue
from utils.exceptions import QueueEmpty


T = TypeVar("T")
MAXSIZE = 1024


class EventLoop:
    def __init__(self) -> None:
        # queue of ready callbacks of the form (callback, args)
        self._ready: Queue[tuple[Callable[..., Any], tuple[Any, ...]]] = Queue()
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

    def time(self) -> float:
        return time.time()

    def call_soon(self, callback: Callable[..., None], *args: Any) -> None:
        # add callable to queue to be invoked
        self._ready.put_nowait((callback, args))

    def create_task(self, coroutine: Coroutine[Any, Any, T]) -> Task[T]:
        task: Task[T] = Task(coroutine, loop=self)
        return task

    def run_until_complete(self, fut: Future[T] | Callable[Any, Any, T]) -> T:
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
        self._stopped = False
        while not self.stopped:
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
