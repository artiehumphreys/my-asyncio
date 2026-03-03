import time
import random
from _c_event_loop import EventLoop as CEventLoop
from asyncio.event_loop import EventLoop as PyEventLoop


def bench_c_throughput(n):
    """Schedule n call_soon callbacks on the C loop, drain via run_forever."""
    loop = CEventLoop()
    count = [0]

    def callback():
        count[0] += 1
        if count[0] >= n:
            loop.stop()

    t0 = time.perf_counter()
    for _ in range(n):
        loop.call_soon(callback)
    loop.run_forever()
    return time.perf_counter() - t0


def bench_py_throughput(n):
    """Schedule n call_soon callbacks on the Python loop, drain via run_forever."""
    loop = PyEventLoop()
    count = [0]

    def callback():
        count[0] += 1

    t0 = time.perf_counter()
    for _ in range(n):
        loop.call_soon(callback)
    while count[0] < n:
        loop.run_forever()
    return time.perf_counter() - t0


def bench_c_timing(delay):
    """Measure actual vs expected delay for a single call_later on the C loop."""
    loop = CEventLoop()
    fired_at = [None]

    def record():
        fired_at[0] = time.perf_counter()
        loop.stop()

    scheduled_at = time.perf_counter()
    loop.call_later(delay, record)
    loop.run_forever()
    return fired_at[0] - scheduled_at


def bench_py_timing(delay):
    """Measure actual vs expected delay for a single call_later on the Python loop."""
    loop = PyEventLoop()
    fired_at = [None]

    def record():
        fired_at[0] = time.perf_counter()

    scheduled_at = time.perf_counter()
    loop.call_later(record, delay=delay)
    while fired_at[0] is None:
        loop.run_forever()
    return fired_at[0] - scheduled_at


def bench_c_mixed(n):
    """Schedule n/2 call_soon + n/2 call_later with small random delays on C loop."""
    loop = CEventLoop()
    count = [0]

    def callback():
        count[0] += 1
        if count[0] >= n:
            loop.stop()

    t0 = time.perf_counter()
    for i in range(n):
        if i % 2 == 0:
            loop.call_soon(callback)
        else:
            loop.call_later(random.uniform(0.0, 0.005), callback)
    loop.run_forever()
    return time.perf_counter() - t0


def bench_py_mixed(n):
    """Schedule n/2 call_soon + n/2 call_later with small random delays on Python loop."""
    loop = PyEventLoop()
    count = [0]

    def callback():
        count[0] += 1

    t0 = time.perf_counter()
    for i in range(n):
        if i % 2 == 0:
            loop.call_soon(callback)
        else:
            loop.call_later(callback, delay=random.uniform(0.0, 0.005))
    while count[0] < n:
        loop.run_forever()
    return time.perf_counter() - t0


def bench_concurrent(n, rounds, is_c):
    """Simulate n concurrent routines each rescheduling themselves for `rounds` iterations.
    Returns (elapsed_time, ops_per_sec)."""
    loop = CEventLoop() if is_c else PyEventLoop()
    done = [0]
    total = n * rounds

    def worker():
        done[0] += 1
        if done[0] >= total:
            if is_c:
                loop.stop()
            return
        if is_c:
            loop.call_soon(worker)
        else:
            loop.call_soon(worker)

    for _ in range(n):
        loop.call_soon(worker)

    t0 = time.perf_counter()
    if is_c:
        loop.run_forever()
    else:
        while done[0] < total:
            loop.run_forever()
    elapsed = time.perf_counter() - t0
    ops = total / elapsed if elapsed > 0 else float("inf")
    return elapsed, ops


def main():
    print("=" * 60)
    print("Event Loop Benchmark: C vs Python")
    print("=" * 60)

    # Benchmark 1: call_soon throughput
    print("\n--- call_soon throughput ---")
    print(f"{'N':>10}  {'C (s)':>10}  {'Py (s)':>10}  {'Speedup':>10}")
    for n in [10_000, 100_000, 1_000_000]:
        c_time = bench_c_throughput(n)
        py_time = bench_py_throughput(n)
        speedup = py_time / c_time if c_time > 0 else float("inf")
        print(f"{n:>10}  {c_time:>10.4f}  {py_time:>10.4f}  {speedup:>9.1f}x")

    # Benchmark 2: call_later timing accuracy
    print("\n--- call_later timing accuracy ---")
    print(f"{'Delay':>10}  {'C actual':>10}  {'C err':>10}  {'Py actual':>10}  {'Py err':>10}")
    for delay in [0.001, 0.01, 0.05, 0.1, 0.5]:
        c_actual = bench_c_timing(delay)
        py_actual = bench_py_timing(delay)
        c_err = c_actual - delay
        py_err = py_actual - delay
        print(
            f"{delay:>10.3f}  {c_actual:>10.6f}  {c_err:>+10.6f}  {py_actual:>10.6f}  {py_err:>+10.6f}"
        )

    # Benchmark 3: mixed load
    print("\n--- mixed load (call_soon + call_later) ---")
    print(f"{'N':>10}  {'C (s)':>10}  {'Py (s)':>10}  {'Speedup':>10}")
    for n in [10_000, 50_000]:
        c_time = bench_c_mixed(n)
        py_time = bench_py_mixed(n)
        speedup = py_time / c_time if c_time > 0 else float("inf")
        print(f"{n:>10}  {c_time:>10.4f}  {py_time:>10.4f}  {speedup:>9.1f}x")

    # Benchmark 4: concurrent routines (scale until degradation)
    print("\n--- concurrent routines (10 rounds each) ---")
    rounds = 10
    print(f"{'N':>10}  {'C (s)':>10}  {'C ops/s':>12}  {'Py (s)':>10}  {'Py ops/s':>12}  {'Speedup':>10}")
    prev_c_ops = None
    prev_py_ops = None
    for n in [1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000]:
        c_time, c_ops = bench_concurrent(n, rounds, is_c=True)
        py_time, py_ops = bench_concurrent(n, rounds, is_c=False)
        speedup = py_time / c_time if c_time > 0 else float("inf")
        print(f"{n:>10}  {c_time:>10.4f}  {c_ops:>12,.0f}  {py_time:>10.4f}  {py_ops:>12,.0f}  {speedup:>9.1f}x")

        # stop if ops/sec drops below 50% of peak for both loops
        if prev_c_ops and prev_py_ops:
            if c_ops < prev_c_ops * 0.5 and py_ops < prev_py_ops * 0.5:
                print("  (stopping — significant degradation detected)")
                break
        if prev_c_ops is None or c_ops > prev_c_ops:
            prev_c_ops = c_ops
        if prev_py_ops is None or py_ops > prev_py_ops:
            prev_py_ops = py_ops

    print()


if __name__ == "__main__":
    main()
