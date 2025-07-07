from typing import Deque, TypeVar
from collections import deque
from event import EventLoop
from exceptions import QueueEmpty, QueueFull
from future import Future


T = TypeVar("T")


class Queue(T):
    """
    Wrapper for FIFO double-ended queue, integrated with EventLoop.

    Producers call `put` or `put_nowait`, consumers `get` or `get_nowait`

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
        return self._maxsize

    def qsize(self) -> int:
        return len(self._queue)

    def empty(self) -> bool:
        return not self._queue

    def full(self) -> bool:
        return self.qsize() >= self.maxsize

    async def put(self, item: T) -> None:
        """
        Coroutine that puts an item, waiting if necessary until a
        free slot is available
        """
        while self.full():
            fut: Future[None] = Future()
            self._putters.append(fut)
            await fut
        self.put_nowait(item)

    async def get(self) -> T:
        """
        Coroutine that removes and returns an item, waiting if necessary
        until one is available
        """
        while self.empty():
            fut: Future[T] = Future()
            self._getters.append(fut)
            item = await fut
            return item
        return self.get_nowait()

    def put_nowait(self, item: T) -> None:
        """Put an item into the queue without blocking, or raise QueueFull"""
        if self.full():
            raise QueueFull()
        if self._getters:
            # waking up next getter now that there's a result
            getter = self._getters.popleft()
            getter.set_result(item)
        else:
            self._queue.append(item)

    def get_nowait(self) -> T:
        """
        Remove and return an item immediately, or raise QueueEmpty

        If there are waiting putters, wake one up to signal free space
        """
        if self.empty():
            raise QueueEmpty()
        item = self._queue.popleft()
        if self._putters:
            # waking up a producer now that there's space
            putter = self._putters.popleft()
            putter.set_result(None)

        return item
