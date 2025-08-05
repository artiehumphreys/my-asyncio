from asyncio import sleep
from asyncio.event_loop import get_event_loop

loop = get_event_loop()


async def hello(name: str) -> str:
    print(f"{loop.time():.3f}: Hello, {name}!")
    await sleep(1.0)
    return f"Goodbye, {name}!"


async def shout() -> None:
    print(f"{loop.time():.3f}: AHHHHHHH")
    await sleep(0.75)
    print(f"{loop.time():.3f}: Ok. I'm done shouting.")


async def test_sleep() -> None:
    t1 = loop.create_task(hello("Artie"))
    t2 = loop.create_task(shout())

    res = await t1
    await t2
    print(f"{loop.time():.3f}: Task returned: {res}")


if __name__ == "__main__":
    loop.run_until_complete(test_sleep())
