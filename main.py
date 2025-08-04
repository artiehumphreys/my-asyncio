from asyncio import sleep
from asyncio.event_loop import EventLoop


async def hello(name: str, loop: EventLoop) -> str:
    print(f"{loop.time():.3f}: Hello, {name}!")
    await sleep(1.0, loop=loop)
    return f"Goodbye, {name}!"


async def shout(loop: EventLoop) -> None:
    print(f"{loop.time():.3f}: AHHHHHHH")
    await sleep(0.75, loop=loop)
    print(f"{loop.time():.3f}: Ok. I'm done shouting.")


async def test_sleep(loop: EventLoop) -> None:
    t1 = loop.create_task(hello("Artie", loop=loop))
    t2 = loop.create_task(shout(loop=loop))

    res = await t1
    await t2
    print(f"{loop.time():.3f}: Task returned: {res}")


if __name__ == "__main__":
    loop = EventLoop()
    loop.run_until_complete(test_sleep(loop))
