"""Tests for the persistent loop infrastructure."""

import json
import os
import sys
import tempfile
import threading
import time

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.execution.loop.persistent_loop import (
    CycleReport,
    LoopRegistry,
    LoopState,
    PersistentLoop,
)


class CountingLoop(PersistentLoop):
    """Test loop that counts cycles."""

    def __init__(self, interval: int = 1):
        super().__init__(name="test_counter", domain="test", interval_seconds=interval)
        self.cycles_run = 0

    def run_cycle(self) -> CycleReport:
        self.cycles_run += 1
        now = "2026-01-01T00:00:00+00:00"
        return CycleReport(
            loop_name=self.name,
            cycle_num=self._cycle_count,
            started_at=now,
            finished_at=now,
            actions_taken=1,
        )


class FailingLoop(PersistentLoop):
    """Test loop that always raises."""

    def __init__(self):
        super().__init__(name="test_fail", domain="test", interval_seconds=1)

    def run_cycle(self) -> CycleReport:
        raise RuntimeError("intentional failure")


# ─── PersistentLoop tests ────────────────────────────────────────────────────


def test_loop_initial_state():
    loop = CountingLoop()
    assert loop.state == LoopState.STOPPED
    assert loop._cycle_count == 0
    assert loop.name == "test_counter"
    assert loop.domain == "test"


def test_run_once():
    loop = CountingLoop()
    report = loop.run_once()
    assert report.loop_name == "test_counter"
    assert report.actions_taken == 1
    assert loop.cycles_run == 1
    assert loop._cycle_count == 1


def test_run_once_multiple():
    loop = CountingLoop()
    for i in range(5):
        report = loop.run_once()
    assert loop.cycles_run == 5
    assert loop._cycle_count == 5


def test_failing_loop_captures_error():
    loop = FailingLoop()
    report = loop.run_once()
    assert report.errors == 1
    assert "intentional failure" in report.details[0]["error"]
    assert loop._error_count == 1


def test_failing_loop_enters_error_state_after_5():
    loop = FailingLoop()
    for _ in range(5):
        loop.run_once()
    assert loop.state == LoopState.ERROR
    assert loop._error_count == 5


def test_status_dict():
    loop = CountingLoop()
    loop.run_once()
    status = loop.status()
    assert status["name"] == "test_counter"
    assert status["domain"] == "test"
    assert status["state"] == "stopped"
    assert status["cycle_count"] == 1
    assert status["last_cycle"] is not None
    assert status["last_cycle"]["actions_taken"] == 1


def test_cycle_report_to_dict():
    report = CycleReport(
        loop_name="test",
        cycle_num=1,
        started_at="t0",
        finished_at="t1",
        actions_taken=3,
        errors=1,
        details=[{"key": "value"}],
    )
    d = report.to_dict()
    assert d["loop_name"] == "test"
    assert d["actions_taken"] == 3
    assert d["errors"] == 1
    assert len(d["details"]) == 1


def test_start_stop_threading():
    loop = CountingLoop(interval=1)
    loop.start()
    assert loop.state == LoopState.RUNNING
    time.sleep(2.5)
    loop.stop()
    time.sleep(0.5)
    assert loop.state == LoopState.STOPPED
    assert loop.cycles_run >= 2


# ─── LoopRegistry tests ─────────────────────────────────────────────────────


def test_registry_register_and_get():
    reg = LoopRegistry()
    loop = CountingLoop()
    reg.register(loop)
    assert reg.get("test_counter") is loop
    assert reg.get("nonexistent") is None


def test_registry_list_loops():
    reg = LoopRegistry()
    reg.register(CountingLoop())
    reg.register(FailingLoop())
    names = reg.list_loops()
    assert "test_counter" in names
    assert "test_fail" in names


def test_registry_status():
    reg = LoopRegistry()
    reg.register(CountingLoop())
    status = reg.status()
    assert "test_counter" in status
    assert status["test_counter"]["state"] == "stopped"


def test_registry_start_stop():
    reg = LoopRegistry()
    loop = CountingLoop(interval=1)
    reg.register(loop)
    assert reg.start("test_counter")
    assert loop.state == LoopState.RUNNING
    time.sleep(1.5)
    assert reg.stop("test_counter")
    time.sleep(0.5)
    assert loop.state == LoopState.STOPPED
    assert loop.cycles_run >= 1


def test_registry_start_unknown():
    reg = LoopRegistry()
    assert not reg.start("nonexistent")


def test_registry_start_stop_all():
    reg = LoopRegistry()
    reg.register(CountingLoop(interval=1))
    started = reg.start_all()
    assert len(started) == 1
    time.sleep(1.5)
    stopped = reg.stop_all()
    assert len(stopped) == 1


def test_registry_register_defaults():
    reg = LoopRegistry()
    reg.register_defaults()
    names = reg.list_loops()
    assert "business_ops" in names
    assert "self_build" in names
    assert "research" in names


# ─── Integration: real loops run_once ────────────────────────────────────────


def test_business_ops_run_once():
    from substrate.execution.loop.business_ops import BusinessOpsLoop
    loop = BusinessOpsLoop()
    report = loop.run_once()
    assert report.loop_name == "business_ops"
    assert isinstance(report.details, list)


def test_self_build_run_once():
    from substrate.execution.loop.self_build import SelfBuildLoop
    loop = SelfBuildLoop()
    report = loop.run_once()
    assert report.loop_name == "self_build"
    assert isinstance(report.details, list)


def test_research_run_once():
    from substrate.execution.loop.research import ResearchLoop
    loop = ResearchLoop()
    report = loop.run_once()
    assert report.loop_name == "research"
    assert isinstance(report.details, list)


def test_heartbeat_written(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.loop.persistent_loop._HEARTBEAT_DIR",
        tmp_path,
    )
    loop = CountingLoop()
    loop.run_once()
    hb_file = tmp_path / "test_counter.json"
    assert hb_file.exists()
    data = json.loads(hb_file.read_text())
    assert data["loop"] == "test_counter"
    assert data["cycle"] == 1
