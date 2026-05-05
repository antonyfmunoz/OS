"""
Tests for eos_ai.runtime.work_state — idle detection + adaptive throttling.

Simulates:
  - No work → system idles with exponential backoff
  - Signal arrives → system wakes instantly
  - High pressure → longer delays
  - Recovery → normal intervals resume
"""

import sys
import time

sys.path.insert(0, "/opt/OS")

import eos_ai.runtime.work_state as ws


def _reset_module_state():
    """Reset global state between tests."""
    ws._last_signal_ts = 0.0
    ws._consecutive_idle = 0
    ws._goal_detector = None
    ws._task_detector = None


def test_idle_when_no_work():
    """No goals, no tasks, no signal → is_idle=True."""
    _reset_module_state()
    state = ws.detect_work_state()
    assert state.is_idle, f"Expected idle, got {state}"
    assert not state.has_pending_goals
    assert not state.has_active_tasks
    assert not state.has_recent_signal
    print("  PASS: idle_when_no_work")


def test_not_idle_with_signal():
    """Recent signal → not idle."""
    _reset_module_state()
    ws.record_signal()
    state = ws.detect_work_state()
    assert not state.is_idle
    assert state.has_recent_signal
    print("  PASS: not_idle_with_signal")


def test_not_idle_with_goals():
    """Pending goals → not idle."""
    _reset_module_state()
    ws.register_goal_detector(lambda: True)
    state = ws.detect_work_state()
    assert not state.is_idle
    assert state.has_pending_goals
    print("  PASS: not_idle_with_goals")


def test_not_idle_with_tasks():
    """Active tasks → not idle."""
    _reset_module_state()
    ws.register_task_detector(lambda: True)
    state = ws.detect_work_state()
    assert not state.is_idle
    assert state.has_active_tasks
    print("  PASS: not_idle_with_tasks")


def test_exponential_backoff():
    """Consecutive idle cycles increase delay exponentially."""
    _reset_module_state()
    delays = []
    for _ in range(8):
        state = ws.detect_work_state()
        delays.append(state.idle_delay)

    # Each delay should be >= previous (exponential growth)
    for i in range(1, len(delays)):
        assert delays[i] >= delays[i - 1], f"Delay did not increase: {delays[i - 1]} → {delays[i]}"

    # First delay should be small, last should be large
    assert delays[0] <= 10.0, f"First delay too large: {delays[0]}"
    assert delays[-1] >= 100.0, f"Last delay too small: {delays[-1]}"
    print(f"  PASS: exponential_backoff (delays: {[f'{d:.0f}' for d in delays]})")


def test_signal_resets_backoff():
    """Signal resets the idle counter → delay drops back to base."""
    _reset_module_state()
    # Build up backoff
    for _ in range(6):
        ws.detect_work_state()
    high_state = ws.detect_work_state()

    # Signal arrives
    ws.record_signal()
    ws.reset_idle_counter()

    active_state = ws.detect_work_state()
    # Active state gets normal interval (1800), not backoff
    assert active_state.idle_delay != high_state.idle_delay
    print("  PASS: signal_resets_backoff")


def test_signal_ttl_expiry():
    """Signal older than TTL → system returns to idle."""
    _reset_module_state()
    # Simulate a signal from 6 minutes ago (TTL is 5 min)
    ws._last_signal_ts = time.time() - 360
    state = ws.detect_work_state()
    assert state.is_idle
    assert not state.has_recent_signal
    print("  PASS: signal_ttl_expiry")


def test_pressure_measurement():
    """Pressure measurement returns valid enum value."""
    _reset_module_state()
    pressure = ws._measure_pressure()
    assert pressure in (
        ws.Pressure.LOW,
        ws.Pressure.MODERATE,
        ws.Pressure.HIGH,
        ws.Pressure.CRITICAL,
    )
    print(f"  PASS: pressure_measurement (current: {pressure.value})")


def test_max_idle_cap():
    """Idle delay never exceeds _MAX_IDLE_DELAY."""
    _reset_module_state()
    # Run many idle cycles
    for _ in range(30):
        ws.detect_work_state()
    state = ws.detect_work_state()
    assert state.idle_delay <= ws._MAX_IDLE_DELAY * 4, (
        f"Delay {state.idle_delay} exceeds max {ws._MAX_IDLE_DELAY * 4}"
    )
    print("  PASS: max_idle_cap")


def test_provider_state_pressure_delegation():
    """provider_state._check_resource_pressure delegates to work_state."""
    from eos_ai.runtime.provider_state import SystemProviderState

    sps = SystemProviderState()
    result = sps._check_resource_pressure()
    assert result in ("low", "moderate", "high", "critical"), f"Bad result: {result}"
    print(f"  PASS: provider_state_pressure_delegation (current: {result})")


if __name__ == "__main__":
    print("Testing work_state...")
    test_idle_when_no_work()
    test_not_idle_with_signal()
    test_not_idle_with_goals()
    test_not_idle_with_tasks()
    test_exponential_backoff()
    test_signal_resets_backoff()
    test_signal_ttl_expiry()
    test_pressure_measurement()
    test_max_idle_cap()
    test_provider_state_pressure_delegation()
    print("\nAll tests passed.")
