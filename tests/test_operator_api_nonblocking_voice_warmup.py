from __future__ import annotations

import asyncio
import concurrent.futures
import sys
import threading
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import services.operator_api as operator_api
from substrate.execution.voice.voice_engine import IntelligentVoiceProcessor


def _reset_operator_warmup_state() -> None:
    operator_api._voice_warmup_task = None
    operator_api._voice_warmup_status = {
        "state": "NOT_STARTED",
        "started_at": None,
        "ended_at": None,
        "error": None,
        "shutdown_waiting": False,
        "shutdown_slow": False,
        "cancel_requested": False,
    }


async def test_slow_voice_warmup_does_not_block_health() -> None:
    _reset_operator_warmup_state()
    started = threading.Event()
    release = threading.Event()

    def slow_preload() -> bool:
        started.set()
        release.wait(timeout=5)
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        warmup_task = asyncio.create_task(operator_api._run_voice_warmup(executor, slow_preload))
        operator_api._voice_warmup_task = warmup_task
        assert await asyncio.to_thread(started.wait, 1)
        assert operator_api.voice_warmup_status()["state"] == "WARMING"

        health = await operator_api.health()
        assert health["status"] == "ok"
        assert health["voice_warmup"]["state"] == "WARMING"
        assert not operator_api._voice_warmup_task.done()

        release.set()
        await asyncio.wait_for(operator_api._voice_warmup_task, timeout=1)
        assert operator_api.voice_warmup_status()["state"] == "READY"


async def test_voice_warmup_failure_is_fail_soft() -> None:
    _reset_operator_warmup_state()

    def failing_preload() -> bool:
        raise RuntimeError("model cache unavailable")

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        await operator_api._run_voice_warmup(executor, failing_preload)

    status = operator_api.voice_warmup_status()
    assert status["state"] == "FAILED"
    assert "model cache unavailable" in status["error"]
    assert (await operator_api.health())["status"] == "ok"


async def test_voice_warmup_shutdown_drains_owned_task() -> None:
    _reset_operator_warmup_state()
    started = threading.Event()
    release = threading.Event()

    def slow_preload() -> bool:
        started.set()
        release.wait(timeout=5)
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        warmup_task = asyncio.create_task(operator_api._run_voice_warmup(executor, slow_preload))
        operator_api._voice_warmup_task = warmup_task
        assert await asyncio.to_thread(started.wait, 1)
        drain_task = asyncio.create_task(operator_api._drain_voice_warmup_task_for_shutdown())
        await asyncio.sleep(0)
        assert not drain_task.done()
        assert operator_api.voice_warmup_status()["shutdown_waiting"] is True

        release.set()
        await asyncio.wait_for(drain_task, timeout=1)

    assert operator_api._voice_warmup_task is None
    assert operator_api.voice_warmup_status()["state"] == "READY"


async def test_voice_warmup_shutdown_slow_drain_keeps_waiting(monkeypatch) -> None:
    _reset_operator_warmup_state()
    monkeypatch.setattr(operator_api, "_VOICE_WARMUP_SHUTDOWN_DRAIN_SECONDS", 0.01)
    started = threading.Event()
    release = threading.Event()

    def slow_preload() -> bool:
        started.set()
        release.wait(timeout=5)
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        warmup_task = asyncio.create_task(operator_api._run_voice_warmup(executor, slow_preload))
        operator_api._voice_warmup_task = warmup_task
        assert await asyncio.to_thread(started.wait, 1)
        drain_task = asyncio.create_task(operator_api._drain_voice_warmup_task_for_shutdown())
        await asyncio.sleep(0.05)

        assert not drain_task.done()
        assert operator_api._voice_warmup_task is not None
        assert operator_api.voice_warmup_status()["shutdown_slow"] is True

        release.set()
        await asyncio.wait_for(drain_task, timeout=1)
        await asyncio.wait_for(warmup_task, timeout=1)

    assert operator_api._voice_warmup_task is None
    assert operator_api.voice_warmup_status()["state"] == "READY"
    assert operator_api.voice_warmup_status()["shutdown_slow"] is True


async def test_external_warmup_task_cancellation_still_drains_executor_work() -> None:
    _reset_operator_warmup_state()
    started = threading.Event()
    release = threading.Event()
    finished = threading.Event()

    def slow_preload() -> bool:
        started.set()
        release.wait(timeout=5)
        finished.set()
        return True

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        task = asyncio.create_task(operator_api._run_voice_warmup(executor, slow_preload))
        assert await asyncio.to_thread(started.wait, 1)

        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        assert not finished.is_set()
        assert operator_api.voice_warmup_status()["cancel_requested"] is True

        release.set()
        await asyncio.wait_for(task, timeout=1)

    assert finished.is_set()
    assert operator_api.voice_warmup_status()["state"] == "READY"


def test_faster_whisper_lazy_load_is_single_flight(monkeypatch) -> None:
    created: list[tuple[str, str, str, bool]] = []
    constructor_entered = threading.Event()

    class FakeWhisperModel:
        def __init__(
            self,
            model_size: str,
            *,
            device: str,
            compute_type: str,
            local_files_only: bool,
        ) -> None:
            constructor_entered.set()
            # Keep the constructor occupied long enough for a racing lazy load to
            # reach the single-flight lock.
            threading.Event().wait(timeout=0.05)
            created.append((model_size, device, compute_type, local_files_only))

    monkeypatch.setitem(
        sys.modules,
        "faster_whisper",
        types.SimpleNamespace(WhisperModel=FakeWhisperModel),
    )
    proc = IntelligentVoiceProcessor()
    results: list[bool] = []

    def load() -> None:
        results.append(proc.load_faster_whisper())

    t1 = threading.Thread(target=load)
    t2 = threading.Thread(target=load)
    t1.start()
    assert constructor_entered.wait(timeout=1)
    t2.start()
    t1.join(timeout=2)
    t2.join(timeout=2)

    assert results == [True, True]
    assert created == [("base", "cpu", "int8", False)]
