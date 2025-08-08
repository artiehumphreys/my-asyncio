"""Task-level utilities"""

from typing import Any, AsyncIterator, Awaitable, Coroutine, Literal, Sequence, TypeVar
from .future import Future
from .event_loop import EventLoop, get_event_loop
from .runner import Runner

T = TypeVar("T", default=None)


def ensure_future(
    awaitable: Awaitable[T], *, loop: EventLoop | None = None
) -> Future[T]:
    """Wrap an awaitable in a Future, scheduling coroutines as Tasks."""
    # https://peps.python.org/pep-0492/
    loop = loop or get_event_loop()
    if isinstance(awaitable, Future):
        return awaitable
    if isinstance(awaitable, Coroutine):
        return loop.create_task(awaitable)
    raise TypeError(
        f"object provided is not a Future or Corotuine. Type: {type(awaitable).__name__}"
    )


async def sleep(delay: float = 1.0, loop: EventLoop | None = None) -> None:
    """Pause execution for the specified delay without blocking the OS thread"""
    loop = loop or get_event_loop()
    fut = Future[None]()
    if delay <= 0.0:
        loop.call_soon(fut.set_result, None)
    else:
        loop.call_later(fut.set_result, None, delay=delay)
    await fut


def run(coroutine: Coroutine[Any, Any, T]) -> T:
    """Execute a coroutine to completion on a fresh EventLoop, then close it"""
    with Runner() as runner:
        return runner.run(coroutine=coroutine)


def gather(
    *aws: Coroutine[Any, Any, T] | Future[T],
    return_exceptions: bool = True,
    loop: EventLoop | None = None,
) -> Future[list[T | Exception]]:
    """Execute multiple coroutines simultaneously and collect their results"""
    loop = loop or get_event_loop()
    futures = [ensure_future(a, loop=loop) for a in aws]
    out = Future()
    n = len(futures)

    if n == 0:
        out.set_result([])
        return out

    results: list[T | Exception | None] = [None for _ in range(n)]
    remaining = n

    def make_callback(idx: int):
        def _on_done(fut: Future[T]) -> None:
            nonlocal remaining
            if out.done:
                return
            try:
                results[idx] = fut.result()
            except Exception as e:
                if return_exceptions:
                    results[idx] = e
                else:
                    out.set_exception(e)
                    return

            remaining -= 1
            if remaining == 0:
                out.set_result(results.copy())

        return _on_done

    for i, fut in enumerate(futures):
        fut.add_done_callback(make_callback(i))

    return out


ALL_COMPLETED: Literal["ALL_COMPLETED"] = "ALL_COMPLETED"
FIRST_COMPLETED: Literal["FIRST_COMPLETED"] = "FIRST_COMPLETED"
FIRST_EXCEPTION: Literal["FIRST_EXCEPTION"] = "FIRST_EXCEPTION"

ReturnWhen = Literal["ALL_COMPLETED", "FIRST_COMPLETED", "FIRST_EXCEPTION"]


def wait(
    aws: Sequence[Coroutine[Any, Any, T] | Future[T]],
    *,
    return_when: ReturnWhen = ALL_COMPLETED,
    loop: EventLoop | None = None,
) -> Future[tuple[set[Future[T]], set[Future[T]]]]:
    """Returns a future that yields (done, pending) sets of Futures."""
    loop = loop or get_event_loop
    futs = [ensure_future(aw) for aw in aws]
    out = Future()

    done = set()
    pending = set(futs)

    def _set_result() -> None:
        out.set_result((set(done), set(pending)))

    def _on_done(f: Future[T]) -> None:
        nonlocal done, pending
        if out.done:
            return

        pending.discard(f)
        done.add(f)

        if return_when == FIRST_COMPLETED and done:
            _set_result()
        elif return_when == FIRST_EXCEPTION:
            try:
                _ = f.result()
            except Exception:
                _set_result()
        elif return_when == ALL_COMPLETED and not pending:
            _set_result()

    for fut in futs:
        fut.add_done_callback(_on_done)

    return out


async def as_completed(
    aws: Sequence[Coroutine[Any, Any, T] | Future[T]], *, loop: EventLoop | None = None
) -> AsyncIterator[Future[T]]:
    """Yield each Future as it is completed, in order of completion"""
    loop = loop or get_event_loop()
    futs = [ensure_future(aw) for aw in aws]
    n = len(futs)
    q = []

    def _on_done(f: Future[T]) -> None:
        q.append(f)

    for fut in futs:
        fut.add_done_callback(_on_done)

    for _ in range(n):
        while not q:
            await sleep(0)
        yield q.pop(0)
