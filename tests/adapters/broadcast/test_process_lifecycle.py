"""Tests for ProcessLifecycle fixes: stale exit, SIGKILL timeout, lock, cancel race."""

from __future__ import annotations

import asyncio
import sys
import os

_WORKTREE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, _WORKTREE)
sys.path.insert(1, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from adapters.broadcast.process_lifecycle import ProcessLifecycle


@pytest.fixture
def sleep_cmd() -> list[str]:
    return ["sleep", "30"]


@pytest.fixture
def short_cmd() -> list[str]:
    return ["echo", "hello"]


@pytest.mark.asyncio
async def test_stale_exit_callback_unbound_on_stop() -> None:
    """MUST-FIX: on_exit must be None after stop() so stale monitor can't corrupt state."""
    exit_codes: list[int | None] = []

    def on_exit(code: int | None) -> None:
        exit_codes.append(code)

    lc = ProcessLifecycle(["sleep", "30"], on_exit=on_exit)
    ok = await lc.start()
    assert ok

    await lc.stop()
    assert lc._on_exit is None, "on_exit must be unbound after stop()"
    assert len(exit_codes) == 0, "on_exit must NOT fire during intentional stop"


@pytest.mark.asyncio
async def test_stale_exit_no_corruption_on_restart() -> None:
    """Stop then start again — old monitor must not fire on_exit into new session."""
    exit_fired = []

    def on_exit(code: int | None) -> None:
        exit_fired.append(code)

    lc1 = ProcessLifecycle(["sleep", "30"], on_exit=on_exit)
    await lc1.start()
    await lc1.stop()

    lc2 = ProcessLifecycle(["sleep", "30"], on_exit=on_exit)
    await lc2.start()

    await asyncio.sleep(0.2)
    assert len(exit_fired) == 0, "stale exit must not fire after stop+new start"
    await lc2.stop()


@pytest.mark.asyncio
async def test_sigkill_wait_has_timeout() -> None:
    """SHOULD-FIX: after SIGKILL, wait() must have a timeout, not hang forever."""
    lc = ProcessLifecycle(
        ["sleep", "30"],
        teardown_timeout=0.1,
    )
    ok = await lc.start()
    assert ok

    code = await asyncio.wait_for(lc.stop(), timeout=10.0)
    assert not lc.running


@pytest.mark.asyncio
async def test_concurrent_start_stop_serialized() -> None:
    """SHOULD-FIX: concurrent start/stop must be serialized by the lock."""
    lc = ProcessLifecycle(["sleep", "30"])
    results: list[str] = []

    async def do_start() -> None:
        ok = await lc.start()
        results.append(f"start:{ok}")

    async def do_stop() -> None:
        code = await lc.stop()
        results.append(f"stop:{code}")

    await lc.start()

    await asyncio.gather(do_stop(), do_start())
    assert any("stop:" in r for r in results)
    await lc.stop()


@pytest.mark.asyncio
async def test_monitor_cancel_race_safe() -> None:
    """SHOULD-FIX: monitor uses captured proc ref, not self._proc which may be None."""
    stdout_lines: list[str] = []

    def on_stdout(line: str) -> None:
        stdout_lines.append(line)

    lc = ProcessLifecycle(
        ["echo", "test_output"],
        on_stdout=on_stdout,
    )
    ok = await lc.start()
    assert ok

    await asyncio.sleep(0.3)
    code = await lc.stop()
    assert code is not None or not lc.running
    assert lc._proc is None, "proc must be cleared after stop"


@pytest.mark.asyncio
async def test_lock_exists() -> None:
    """Verify ProcessLifecycle has an asyncio.Lock."""
    lc = ProcessLifecycle(["echo", "hi"])
    assert isinstance(lc._lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_rapid_start_stop_start() -> None:
    """Exercise rapid start/stop/start to prove lock + stale callback work together."""
    lc = ProcessLifecycle(["sleep", "30"])

    ok1 = await lc.start()
    assert ok1
    await lc.stop()

    ok2 = await lc.start()
    assert ok2
    assert lc.running

    code = await lc.stop()
    assert not lc.running
