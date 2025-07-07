"""Custom exception hierarchy for our asyncio-like event loop"""


class AsyncioError(Exception):
    """Base class for all asyncio errors in this runtime"""


class InvalidStateError(AsyncioError):
    """
    Raised when an operation is requested on a Future or Task
    that’s in an inappropriate state
    """


class FutureAlreadyDoneError(InvalidStateError):
    """
    Raised when attempting to set a result or exception on
    a Future that has already completed
    """


class CancelledError(AsyncioError):
    """Raised when a Future or Task is cancelled"""


class TimeoutError(AsyncioError):
    """Raised when an operation exceeds its allotted timeout"""


class TaskError(AsyncioError):
    """Base class for Task-specific errors"""


class TaskAlreadyRunningError(TaskError):
    """
    Raised if you attempt to schedule or start a Task
    that’s already been started
    """


class TaskNotRunnableError(TaskError):
    """Raised if the Task cannot be started or resumed"""


class QueueEmpty(Exception):
    """Raised when calling get_nowait on an empty queue"""


class QueueFull(Exception):
    """Raised when calling put_nowait on a full queue"""
