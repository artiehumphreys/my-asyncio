import time
from typing import Any
from utils.event_loop import EventLoop


async def hello(name: str) -> str:
    print(f"Hello, {name}!")
    time.sleep(1)
    return f"Goodbye, {name}!"


async def main(loop: EventLoop) -> None:
    task = loop.create_task(hello("Artie"))

    greeting = await task
    print(f"Task returned: {greeting}")


if __name__ == "__main__":
    loop = EventLoop()
    loop.run_until_complete(main(loop))
