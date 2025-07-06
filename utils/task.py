from typing import Any, Coroutine, Optional
from future import Future
import exceptions


class Task(Future):
    """
    Coroutine wrapper, extends Future (see future.py)

    https://bbc.github.io/cloudfit-public-docs/asyncio/asyncio-part-2.html
    """

    def __init__(
        self,
        coroutine: Coroutine[Any, None, None],
        *,
        loop: Any,
    ) -> None:
        super().__init__()
        self.finished = False
        self._coroutine = coroutine
        self._loop = loop
        # TODO: enqueue task into event loop

    def _step(self, future: Optional[Future] = None) -> None:
        """Advance the wrapped coroutine by one step."""
        try:
            pass
        except:
            pass
