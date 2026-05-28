"""Tests for the autonomous tick engine."""

from __future__ import annotations

import sys
import time
import threading

sys.path.insert(0, "/opt/OS")

from substrate.organism.autonomous_tick import (
    AutonomousTick,
    TickConfig,
    TickMetrics,
    TickStage,
)
from substrate.organism.event_spine import EventDomain, EventSpine


def _make_tick(interval: float = 0.05, **kwargs) -> AutonomousTick:
    spine = EventSpine()
    config = TickConfig(
        base_interval_seconds=interval,
        min_interval_seconds=0.01,
        max_interval_seconds=1.0,
        **kwargs,
    )
    return AutonomousTick(spine=spine, config=config)


def test_tick_config_defaults():
    config = TickConfig()
    assert config.base_interval_seconds == 30.0
    assert config.min_interval_seconds == 5.0
    assert config.max_interval_seconds == 300.0
    assert config.adaptive_cadence is True


def test_tick_register_stage():
    tick = _make_tick()
    called: list[int] = []
    tick.register_stage("test_stage", lambda: called.append(1))
    assert "test_stage" in tick.stages


def test_tick_single_cycle():
    tick = _make_tick()
    results: list[str] = []
    tick.register_stage("stage_a", lambda: results.append("a"))
    tick.register_stage("stage_b", lambda: results.append("b"))

    report = tick.execute_cycle()
    assert report.cycle_number == 1
    assert report.stages_executed == 2
    assert report.stages_failed == 0
    assert results == ["a", "b"]


def test_tick_stage_failure_isolation():
    tick = _make_tick()
    good_results: list[int] = []

    def bad_stage():
        raise RuntimeError("boom")

    tick.register_stage("bad", bad_stage)
    tick.register_stage("good", lambda: good_results.append(1))

    report = tick.execute_cycle()
    assert report.stages_executed == 2
    assert report.stages_failed == 1
    assert len(good_results) == 1


def test_tick_emits_events():
    spine = EventSpine()
    config = TickConfig(base_interval_seconds=0.05)
    tick = AutonomousTick(spine=spine, config=config)
    tick.register_stage("noop", lambda: None)

    tick.execute_cycle()
    events = spine.recent(limit=50)

    tick_events = [e for e in events if e.event_type == "tick_completed"]
    assert len(tick_events) == 1
    assert tick_events[0].domain == EventDomain.EXECUTION


def test_tick_governance_kill():
    tick = _make_tick()
    tick.register_stage("noop", lambda: None)

    tick.kill()
    assert tick.is_killed

    report = tick.execute_cycle()
    assert report.stages_executed == 0
    assert report.skipped_reason == "killed"


def test_tick_governance_pause_resume():
    tick = _make_tick()
    tick.register_stage("noop", lambda: None)

    tick.pause()
    assert tick.is_paused

    report = tick.execute_cycle()
    assert report.stages_executed == 0
    assert report.skipped_reason == "paused"

    tick.resume()
    report = tick.execute_cycle()
    assert report.stages_executed == 1


def test_tick_metrics():
    tick = _make_tick()
    tick.register_stage("fast", lambda: None)

    tick.execute_cycle()
    tick.execute_cycle()

    metrics = tick.metrics
    assert metrics.total_cycles == 2
    assert metrics.total_stages_executed == 2
    assert metrics.total_stages_failed == 0
    assert metrics.avg_cycle_ms >= 0


def test_tick_adaptive_cadence_speeds_up():
    tick = _make_tick(interval=1.0, adaptive_cadence=True)
    tick.register_stage("work", lambda: True)  # returns truthy = had_work

    tick.execute_cycle()
    first_interval = tick.current_interval

    for _ in range(5):
        tick.execute_cycle()

    assert tick.current_interval < first_interval


def test_tick_adaptive_cadence_slows_down():
    tick = _make_tick(interval=0.05, adaptive_cadence=True,
                      idle_threshold_cycles=1)
    tick.register_stage("idle", lambda: None)  # returns None = no work

    for _ in range(5):
        tick.execute_cycle()

    assert tick.current_interval > 0.05


def test_tick_run_loop_stops_on_kill():
    tick = _make_tick(interval=0.02)
    tick.register_stage("noop", lambda: None)

    def kill_after_delay():
        time.sleep(0.05)
        tick.kill()

    threading.Thread(target=kill_after_delay, daemon=True).start()
    tick.run(max_cycles=100)

    assert tick.is_killed
    assert tick.metrics.total_cycles >= 1
    assert tick.metrics.total_cycles < 100


def test_tick_to_dict():
    tick = _make_tick()
    tick.register_stage("s1", lambda: None)
    tick.execute_cycle()

    d = tick.to_dict()
    assert "metrics" in d
    assert "config" in d
    assert "stages" in d
    assert "is_killed" in d
    assert "is_paused" in d
    assert "current_interval" in d
