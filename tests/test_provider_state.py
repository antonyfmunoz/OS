"""
Tests for eos_ai.runtime.provider_state — global failure state + backpressure.

Simulates:
  - All providers failing → no retry storm
  - Execution budget enforcement → no new processes
  - Resource pressure → system stabilizes
  - Recovery → system resumes
"""

import sys
import time

sys.path.insert(0, "/opt/OS")

from eos_ai.runtime.provider_state import (
    ExecutionBudget,
    ProviderState,
    ProviderStatus,
    SystemProviderState,
    SystemStatus,
    get_system_state,
)


def test_provider_state_lifecycle():
    """Provider transitions: healthy → degraded → down → recovery."""
    ps = ProviderState(provider_name="test_provider")
    assert ps.status == ProviderStatus.HEALTHY
    assert ps.is_available()

    # 3 failures → degraded
    for _ in range(3):
        ps.record_failure()
    assert ps.status == ProviderStatus.DEGRADED
    assert ps.is_available()

    # 5 failures → down with cooldown
    for _ in range(2):
        ps.record_failure()
    assert ps.status == ProviderStatus.DOWN
    assert ps.cooldown_until > time.time()
    assert not ps.is_available()

    # Success → recovery
    ps.record_success()
    assert ps.status == ProviderStatus.HEALTHY
    assert ps.is_available()
    assert ps.consecutive_failures == 0
    print("  PASS: provider_state_lifecycle")


def test_system_global_status():
    """System status reflects worst-case across all providers."""
    sys_state = SystemProviderState()

    # No providers registered = healthy
    assert sys_state.global_status == SystemStatus.HEALTHY

    # One healthy provider
    sys_state.record_provider_success("gemini")
    assert sys_state.global_status == SystemStatus.HEALTHY

    # Make one provider fail enough to go down
    for _ in range(5):
        sys_state.record_provider_failure("anthropic")
    assert sys_state.global_status == SystemStatus.DEGRADED

    # Make all providers go down
    for _ in range(5):
        sys_state.record_provider_failure("gemini")
    assert sys_state.global_status == SystemStatus.DOWN
    print("  PASS: system_global_status")


def test_all_providers_failed_backoff():
    """All-providers-failed triggers exponential backoff."""
    sys_state = SystemProviderState()

    # First all-fail → 30s backoff
    sys_state.record_all_providers_failed()
    assert sys_state._backoff_until > time.time()
    assert sys_state._consecutive_all_down == 1

    # Second all-fail → 60s backoff (doubled)
    sys_state.record_all_providers_failed()
    assert sys_state._consecutive_all_down == 2

    # Success resets backoff counter and timer
    sys_state.record_provider_success("ollama")
    assert sys_state._consecutive_all_down == 0
    assert sys_state._backoff_until == 0.0
    print("  PASS: all_providers_failed_backoff")


def test_no_retry_storm():
    """After all-providers-failed, backoff timer prevents rapid retries."""
    sys_state = SystemProviderState()

    # Simulate 10 rapid all-providers-failed events
    for _ in range(10):
        sys_state.record_all_providers_failed()

    # Backoff should be at max (300s) after 10 failures
    remaining = sys_state._backoff_until - time.time()
    assert remaining > 200, f"Expected >200s backoff, got {remaining:.0f}s"
    assert sys_state._consecutive_all_down == 10
    print("  PASS: no_retry_storm")


def test_execution_budget():
    """Cycle rate limiting prevents runaway execution."""
    budget = ExecutionBudget(max_cycles_per_minute=5)

    for _ in range(5):
        assert budget.can_start_cycle()
        budget.record_cycle()

    # 6th cycle should be blocked
    assert not budget.can_start_cycle()
    print("  PASS: execution_budget")


def test_agent_spawn_guard():
    """Agent spawn guard respects max concurrent limit."""
    budget = ExecutionBudget(max_concurrent_agents=2)

    assert budget.can_spawn_agent()
    budget.agent_started()
    assert budget.can_spawn_agent()
    budget.agent_started()
    assert not budget.can_spawn_agent()

    budget.agent_finished()
    assert budget.can_spawn_agent()
    print("  PASS: agent_spawn_guard")


def test_system_allow_agent_spawn():
    """System-level spawn guard integrates budget + resource check."""
    sys_state = SystemProviderState()
    sys_state.budget.max_concurrent_agents = 2
    # Override resource check so tests don't depend on VPS load
    sys_state._check_resource_pressure = lambda: "low"

    assert sys_state.allow_agent_spawn()
    sys_state.budget.agent_started()
    sys_state.budget.agent_started()
    assert not sys_state.allow_agent_spawn()
    print("  PASS: system_allow_agent_spawn")


def test_recovery_path():
    """System recovers from full outage when providers come back."""
    sys_state = SystemProviderState()

    # Drive system to full outage
    for _ in range(10):
        sys_state.record_all_providers_failed()
    assert sys_state._consecutive_all_down == 10
    assert sys_state._backoff_until > time.time()

    # Simulate provider recovery — resets counters
    sys_state.record_provider_success("gemini")
    assert sys_state._consecutive_all_down == 0
    assert sys_state._backoff_until == 0.0
    assert sys_state.global_status != SystemStatus.DOWN
    print("  PASS: recovery_path")


def test_singleton():
    """get_system_state returns the same instance."""
    s1 = get_system_state()
    s2 = get_system_state()
    assert s1 is s2
    print("  PASS: singleton")


def test_summary():
    """Summary produces structured diagnostic output."""
    sys_state = SystemProviderState()
    sys_state.record_provider_success("gemini")
    sys_state.record_provider_failure("anthropic")

    summary = sys_state.summary()
    assert "global_status" in summary
    assert "providers" in summary
    assert "gemini" in summary["providers"]
    assert "anthropic" in summary["providers"]
    assert "active_agents" in summary
    assert "resource_pressure" in summary
    print("  PASS: summary")


if __name__ == "__main__":
    print("Testing provider_state...")
    test_provider_state_lifecycle()
    test_system_global_status()
    test_all_providers_failed_backoff()
    test_no_retry_storm()
    test_execution_budget()
    test_agent_spawn_guard()
    test_system_allow_agent_spawn()
    test_recovery_path()
    test_singleton()
    test_summary()
    print("\nAll tests passed.")
