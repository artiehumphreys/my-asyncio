"""
asyncio Queue implementation for coordinating producers and consumers
within a single-threaded EventLoop.
"""

from typing import Deque, TypeVar
from collections import deque

from .event_loop import EventLoop
from .exceptions import QueueEmpty, QueueFull
from .future import Future

T = TypeVar("T")


# https://peps.python.org/pep-0695/
class Queue[T]:
    """
    Wrapper for FIFO double-ended queue, integrated with EventLoop.

    Producers call `put` or `put_nowait`, consumers `get` or `get_nowait`

    When full or empty, coroutines will block until queue state changes.

    https://github.com/python/cpython/blob/main/Lib/asyncio/queues.py
    https://childsish.github.io/python/2016/09/23/asynchronous-python-queue.html
    """

    def __init__(self, max_size: int = 0, *, loop: EventLoop | None = None) -> None:
        self._loop = loop or EventLoop()
        self._maxsize = max_size
        self._queue: Deque[T] = deque()

        self._getters: Deque[Future[T]] = deque()
        self._putters: Deque[Future[None]] = deque()

    @property
    def maxsize(self) -> int:
        """Return the maximum number of items allowed in the Queue"""
        return self._maxsize

    def qsize(self) -> int:
        """Return the number of items in the queue"""
        return len(self._queue)

    def empty(self) -> bool:
        """Return True if the queue is empty"""
        return not self._queue

    def full(self) -> bool:
        """Return True if the queue is full"""
        return self.qsize() >= self.maxsize

    async def put(self, item: T) -> None:
        """
        Enqueue an item, waiting if necessary for a spot to be available

        Blocks coroutine if full() == True
        """
        while self.full():
            fut: Future[None] = Future()
            self._putters.append(fut)
            await fut
        self.put_nowait(item)

    async def get(self) -> T:
        """
        Dequeue an item, waiting if necessary for a spot to be available

        Blocks coroutine if empty() == True
        """
        while self.empty():
            fut: Future[T] = Future()
            self._getters.append(fut)
            item = await fut
            return item
        return self.get_nowait()

    def put_nowait(self, item: T) -> None:
        """
        Enqueue an item without blocking, or raise QueueFull

        If there are getters waiting (via get), wake one up so that
        it can proceed and dequeue its item immediately.
        """
        if self.full():
            self._maxsize *= 2
        if self._getters:
            # waking up next getter now that there's a result
            getter = self._getters.popleft()
            getter.set_result(item)
        else:
            self._queue.append(item)

    def get_nowait(self) -> T:
        """
        Dequeue an item without blocking, or raise QueueEmpty

        If there are producers waiting (via put), wake one up now that
        there’s free space and let it enqueue its item.
        """
        if self.empty():
            raise QueueEmpty()
        item = self._queue.popleft()
        if self._putters:
            # waking up a producer now that there's space
            putter = self._putters.popleft()
            putter.set_result(None)

        return item
