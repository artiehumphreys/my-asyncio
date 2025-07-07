from collections
from typing import TypeVar imprt deque
from future import Future
from task import Task


T = TypeVar('T')


class EventLoop:


    def __init__(self) -> None:
        self._scheduled = []
        # TODO: Consider selectors for I/O watchers


