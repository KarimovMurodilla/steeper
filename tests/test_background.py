import asyncio
import threading

from steeper._background import fire_and_forget, fire_and_forget_threadsafe


async def test_runs_coroutine_to_completion() -> None:
    done = asyncio.Event()

    async def work() -> None:
        done.set()

    fire_and_forget(work())
    await asyncio.wait_for(done.wait(), timeout=1)


async def test_swallows_exceptions() -> None:
    async def boom() -> None:
        raise RuntimeError("boom")

    fire_and_forget(boom())
    # Give the task a few loop iterations to fail; nothing should propagate.
    for _ in range(3):
        await asyncio.sleep(0)


def test_without_running_loop_drops_work_silently() -> None:
    async def work() -> None:
        raise AssertionError("should not run")

    fire_and_forget(work())


def test_threadsafe_runs_coroutine_from_sync_context() -> None:
    done = threading.Event()

    async def work() -> None:
        done.set()

    fire_and_forget_threadsafe(work())
    assert done.wait(timeout=2)


def test_threadsafe_survives_exceptions() -> None:
    async def boom() -> None:
        raise RuntimeError("boom")

    done = threading.Event()

    async def work() -> None:
        done.set()

    fire_and_forget_threadsafe(boom())
    fire_and_forget_threadsafe(work())
    assert done.wait(timeout=2)
