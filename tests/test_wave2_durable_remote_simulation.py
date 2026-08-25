from __future__ import annotations

from substrate.execution.durable_remote_simulation import run_all_scenarios


def test_durable_remote_simulator_historical_failure_family_preserves_invariants() -> None:
    results = run_all_scenarios()

    assert set(results) >= {
        "ambiguous_claimed_success",
        "claimed_to_running_race",
        "fallback_unavailable",
        "post_handler_stale_delivery",
        "redelivery_amplification",
        "terminal_late_foreign_running",
    }
    assert results["fallback_unavailable"]["executed"] == 0
    assert results["fallback_unavailable"]["fail_closed"] is True
    assert results["terminal_late_foreign_running"]["lifecycle"] == "SUCCEEDED"
    assert all(int(result["executed"]) <= 1 for result in results.values())
