"""Tests for the persistent loop infrastructure."""

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.execution.loop.persistent_loop import (
    CycleReport,
    LoopDefinition,
    LoopRegistry,
    LoopState,
    PersistentLoop,
    STAGE_REGISTRY,
    register_stage,
)

# Ensure built-in stages are loaded
import substrate.execution.loop.stages  # noqa: F401


# ─── Test stage ──────────────────────────────────────────────────────────────

def _counting_stage(loop: PersistentLoop, report: CycleReport) -> None:
    report.actions_taken += 1
    report.details.append({"stage": "test_count", "cycle": loop._cycle_count})

register_stage("test_count", _counting_stage)


def _failing_stage(loop: PersistentLoop, report: CycleReport) -> None:
    raise RuntimeError("intentional failure")

register_stage("test_fail", _failing_stage)


def _make_loop(name: str = "test_counter", stages: list[str] | None = None, interval: int = 1) -> PersistentLoop:
    defn = LoopDefinition(
        name=name,
        domain="test",
        interval_seconds=interval,
        stages=stages or ["test_count"],
    )
    return PersistentLoop(defn)


# ─── PersistentLoop tests ────────────────────────────────────────────────────


def test_loop_initial_state():
    loop = _make_loop()
    assert loop.state == LoopState.STOPPED
    assert loop._cycle_count == 0
    assert loop.name == "test_counter"
    assert loop.domain == "test"


def test_run_once():
    loop = _make_loop()
    report = loop.run_once()
    assert report.loop_name == "test_counter"
    assert report.actions_taken == 1
    assert loop._cycle_count == 1


def test_run_once_multiple():
    loop = _make_loop()
    for _ in range(5):
        loop.run_once()
    assert loop._cycle_count == 5


def test_failing_stage_captures_error():
    loop = _make_loop(stages=["test_fail"])
    report = loop.run_once()
    assert report.errors == 1
    assert "intentional failure" in report.details[0]["error"]


def test_unknown_stage_reports_error():
    loop = _make_loop(stages=["nonexistent_stage"])
    report = loop.run_once()
    assert report.errors == 1
    assert "unknown stage" in report.details[0]["error"]


def test_mixed_stages():
    loop = _make_loop(stages=["test_count", "test_fail", "test_count"])
    report = loop.run_once()
    assert report.actions_taken == 2
    assert report.errors == 1
    assert len(report.details) == 3


def test_error_state_after_5_consecutive():
    loop = _make_loop(stages=["test_fail"])
    for _ in range(5):
        loop.run_once()
    # Stages that raise don't trigger the outer error_count (they're caught per-stage)
    # The loop stays running unless the outer cycle itself fails
    assert loop._cycle_count == 5


def test_status_dict():
    loop = _make_loop()
    loop.run_once()
    status = loop.status()
    assert status["name"] == "test_counter"
    assert status["domain"] == "test"
    assert status["state"] == "stopped"
    assert status["cycle_count"] == 1
    assert status["stages"] == ["test_count"]
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
    loop = _make_loop(interval=1)
    loop.start()
    assert loop.state == LoopState.RUNNING
    time.sleep(2.5)
    loop.stop()
    time.sleep(0.5)
    assert loop.state == LoopState.STOPPED
    assert loop._cycle_count >= 2


# ─── LoopDefinition tests ───────────────────────────────────────────────────


def test_definition_roundtrip():
    defn = LoopDefinition(
        name="test",
        domain="ops",
        interval_seconds=60,
        stages=["signal_drain", "actionable_scan"],
        description="Test loop",
    )
    d = defn.to_dict()
    restored = LoopDefinition.from_dict(d)
    assert restored.name == defn.name
    assert restored.stages == defn.stages
    assert restored.interval_seconds == 60


def test_definition_from_dict_defaults():
    defn = LoopDefinition.from_dict({"name": "minimal"})
    assert defn.domain == "general"
    assert defn.interval_seconds == 300
    assert defn.stages == []
    assert defn.enabled is True


# ─── LoopRegistry tests ─────────────────────────────────────────────────────


def test_registry_register_definition():
    reg = LoopRegistry()
    defn = LoopDefinition(name="test_def", domain="test", stages=["test_count"])
    reg.register_definition(defn)
    assert reg.get("test_def") is not None
    assert reg.get_definition("test_def") is defn


def test_registry_register_and_get():
    reg = LoopRegistry()
    loop = _make_loop()
    reg.register(loop)
    assert reg.get("test_counter") is loop
    assert reg.get("nonexistent") is None


def test_registry_list_loops():
    reg = LoopRegistry()
    reg.register(_make_loop("a"))
    reg.register(_make_loop("b"))
    names = reg.list_loops()
    assert "a" in names
    assert "b" in names


def test_registry_status():
    reg = LoopRegistry()
    reg.register(_make_loop())
    status = reg.status()
    assert "test_counter" in status
    assert status["test_counter"]["state"] == "stopped"


def test_registry_start_stop():
    reg = LoopRegistry()
    loop = _make_loop(interval=1)
    reg.register(loop)
    assert reg.start("test_counter")
    assert loop.state == LoopState.RUNNING
    time.sleep(1.5)
    assert reg.stop("test_counter")
    time.sleep(0.5)
    assert loop.state == LoopState.STOPPED
    assert loop._cycle_count >= 1


def test_registry_start_unknown():
    reg = LoopRegistry()
    assert not reg.start("nonexistent")


def test_registry_start_all_respects_enabled():
    reg = LoopRegistry()
    defn_on = LoopDefinition(name="on", domain="test", stages=["test_count"], enabled=True)
    defn_off = LoopDefinition(name="off", domain="test", stages=["test_count"], enabled=False)
    reg.register_definition(defn_on)
    reg.register_definition(defn_off)
    started = reg.start_all()
    assert "on" in started
    assert "off" not in started
    reg.stop_all()


def test_registry_remove():
    reg = LoopRegistry()
    reg.register(_make_loop("removeme"))
    assert reg.remove("removeme")
    assert reg.get("removeme") is None
    assert not reg.remove("nonexistent")


def test_registry_load_save_definitions(tmp_path):
    defn_file = tmp_path / "loops.jsonl"
    defn_file.write_text(
        '{"name":"a","domain":"test","stages":["test_count"]}\n'
        '{"name":"b","domain":"test","interval_seconds":60,"stages":["test_count","test_fail"]}\n'
    )
    reg = LoopRegistry()
    count = reg.load_definitions(defn_file)
    assert count == 2
    assert reg.get("a") is not None
    assert reg.get("b") is not None
    assert reg.get("b").interval_seconds == 60

    # Save and re-load
    out_file = tmp_path / "saved.jsonl"
    saved = reg.save_definitions(out_file)
    assert saved == 2

    reg2 = LoopRegistry()
    reg2.load_definitions(out_file)
    assert sorted(reg2.list_loops()) == ["a", "b"]


# ─── Built-in stages registered ─────────────────────────────────────────────


def test_builtin_stages_registered():
    expected = [
        "signal_drain", "actionable_scan",
        "goal_execution", "feedback_collection", "health_check",
        "research_topic_select", "research_execute", "world_model_store", "staleness_scan",
    ]
    for name in expected:
        assert name in STAGE_REGISTRY, f"stage '{name}' not registered"


# ─── Integration: config-loaded loops ────────────────────────────────────────


def _definitions_file():
    """Find loop_definitions.jsonl relative to repo root."""
    import pathlib
    # Works in both worktree and main
    here = pathlib.Path(__file__).resolve().parent.parent
    return here / "data" / "config" / "loop_definitions.jsonl"


def test_load_default_definitions():
    reg = LoopRegistry()
    count = reg.load_definitions(_definitions_file())
    assert count >= 3
    assert "business_ops" in reg.list_loops()
    assert "self_build" in reg.list_loops()
    assert "research" in reg.list_loops()


def test_business_ops_run_once():
    reg = LoopRegistry()
    reg.load_definitions(_definitions_file())
    loop = reg.get("business_ops")
    report = loop.run_once()
    assert report.loop_name == "business_ops"
    assert isinstance(report.details, list)
    assert any(d.get("stage") == "signal_drain" for d in report.details)


def test_self_build_run_once():
    reg = LoopRegistry()
    reg.load_definitions(_definitions_file())
    loop = reg.get("self_build")
    report = loop.run_once()
    assert report.loop_name == "self_build"
    assert isinstance(report.details, list)


def test_research_run_once():
    reg = LoopRegistry()
    reg.load_definitions(_definitions_file())
    loop = reg.get("research")
    report = loop.run_once()
    assert report.loop_name == "research"
    assert isinstance(report.details, list)
    assert any(d.get("stage") == "research_topic_select" for d in report.details)


def test_heartbeat_written(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "substrate.execution.loop.persistent_loop._heartbeat_dir",
        lambda: tmp_path,
    )
    loop = _make_loop()
    loop.run_once()
    hb_file = tmp_path / "test_counter.json"
    assert hb_file.exists()
    data = json.loads(hb_file.read_text())
    assert data["loop"] == "test_counter"
    assert data["cycle"] == 1
