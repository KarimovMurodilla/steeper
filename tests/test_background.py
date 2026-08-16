import asyncio
import threading
import time

import pytest

from steeper import _background
from steeper._background import fire_and_forget, fire_and_forget_threadsafe, run_threadsafe


@pytest.fixture(autouse=True)
def _reset_drop_state() -> None:
    """Drop accounting is module-global; keep it from leaking between tests."""
    _background._dropped_total = 0
    _background._drop_warned = False


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


async def test_drops_work_past_the_in_flight_cap(
    caplog: pytest.LogCaptureFixture, recwarn: pytest.WarningsRecorder
) -> None:
    release = asyncio.Event()
    started = 0

    async def blocked() -> None:
        nonlocal started
        started += 1
        await release.wait()

    with caplog.at_level("DEBUG", logger="steeper"):
        for _ in range(_background.MAX_IN_FLIGHT + 10):
            fire_and_forget(blocked())
        # Let the scheduled tasks reach their first await.
        await asyncio.sleep(0)

        assert started == _background.MAX_IN_FLIGHT
        assert _background._dropped_total == 10

        release.set()
        for _ in range(3):
            await asyncio.sleep(0)

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(warnings) == 1, "only the first drop should warn"
    assert str(_background.MAX_IN_FLIGHT) in warnings[0].getMessage()

    # A dropped coroutine must be closed, not left to emit "never awaited".
    assert not [w for w in recwarn.list if w.category is RuntimeWarning]


async def test_queue_draining_rearms_the_warning() -> None:
    release = asyncio.Event()

    async def blocked() -> None:
        await release.wait()

    for _ in range(_background.MAX_IN_FLIGHT + 1):
        fire_and_forget(blocked())
    await asyncio.sleep(0)
    assert _background._drop_warned is True

    release.set()
    while _background._tasks:
        await asyncio.sleep(0)

    # Drained: a later outage is a new event and deserves its own warning.
    assert _background._drop_warned is False


def test_threadsafe_drops_work_past_the_in_flight_cap() -> None:
    release = threading.Event()

    async def blocked() -> None:
        await asyncio.get_running_loop().run_in_executor(None, release.wait)

    try:
        for _ in range(_background.MAX_IN_FLIGHT + 5):
            fire_and_forget_threadsafe(blocked())
        assert _background._dropped_total >= 5
    finally:
        release.set()
        # Drain before returning: the background loop is shared, and leaving it
        # at the cap would make whatever test runs next drop its own work.
        deadline = time.monotonic() + 10
        while _background._background_loop._in_flight and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not _background._background_loop._in_flight


def test_run_threadsafe_waits_for_completion() -> None:
    done = threading.Event()

    async def work() -> None:
        await asyncio.sleep(0)
        done.set()

    run_threadsafe(work(), timeout=5)
    # Already finished by the time the call returns — no polling needed.
    assert done.is_set()


def test_run_threadsafe_swallows_failures() -> None:
    async def boom() -> None:
        raise RuntimeError("boom")

    run_threadsafe(boom(), timeout=5)
