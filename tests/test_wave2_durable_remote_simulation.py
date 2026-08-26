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
        "corrupt_index_rebuilds_only_from_valid_request",
        "corrupt_request_among_valid_isolated",
        "corrupt_restart_still_non_executable",
        "corrupt_result_does_not_terminalize",
        "durable_unknown_policy_denied",
        "event_journal_malformed_line_fails_closed",
        "event_journal_read_error_fails_closed",
        "ingress_malformed_server_durable_frame_rejected",
        "ingress_malformed_node_delivery_rejected",
        "attempt_store_unknown_corruption_blocks_attempt_authority",
        "attempt_store_lease_corruption_blocks_conflicting_lease",
        "attempt_store_cas_rewrite_preserves_corruption",
        "recovery_incomplete_candidate_sha_fails_closed",
        "recovery_incomplete_node_id_fails_closed",
        "recovery_incomplete_operation_type_fails_closed",
        "recovery_invalid_existing_success_cannot_legitimize",
        "risk_consequential_effect_read_only_declared_risk_denied",
        "risk_generic_shell_read_only_node_cap_denied",
        "sync_consequential_routes_to_durable_remote",
        "sync_caller_effect_change_no_authority_change",
        "sync_declared_read_only_for_canonical_write_denied",
        "sync_duplicate_consequential_denied",
        "sync_generic_shell_declares_read_only_denied",
        "sync_payload_substitution_rejected",
        "sync_policy_lookup_unavailable_denied",
        "sync_read_only_retry_observation",
        "sync_stale_effect_policy_verdict_rejected",
        "sync_stale_verdict_rejected",
        "sync_unknown_effect_fails_closed",
        "terminal_late_foreign_running",
    }
    assert results["fallback_unavailable"]["executed"] == 0
    assert results["fallback_unavailable"]["fail_closed"] is True
    assert results["terminal_late_foreign_running"]["lifecycle"] == "SUCCEEDED"
    assert results["sync_duplicate_consequential_denied"]["sync_side_effects"] == 0
    assert results["sync_consequential_routes_to_durable_remote"]["executed"] == 1
    assert results["sync_consequential_routes_to_durable_remote"]["sync_side_effects"] == 0
    assert results["durable_unknown_policy_denied"]["executed"] == 0
    assert results["durable_unknown_policy_denied"]["fail_closed"] is True
    assert results["sync_read_only_retry_observation"]["sync_observations"] == 2
    assert results["sync_read_only_retry_observation"]["sync_side_effects"] == 0
    assert results["sync_unknown_effect_fails_closed"]["fail_closed"] is True
    assert results["sync_stale_verdict_rejected"]["fail_closed"] is True
    assert results["sync_payload_substitution_rejected"]["fail_closed"] is True
    assert results["sync_declared_read_only_for_canonical_write_denied"]["fail_closed"] is True
    assert results["sync_generic_shell_declares_read_only_denied"]["fail_closed"] is True
    assert results["sync_policy_lookup_unavailable_denied"]["fail_closed"] is True
    assert results["sync_stale_effect_policy_verdict_rejected"]["fail_closed"] is True
    assert results["sync_caller_effect_change_no_authority_change"]["fail_closed"] is True
    assert results["recovery_incomplete_candidate_sha_fails_closed"]["fail_closed"] is True
    assert results["recovery_invalid_existing_success_cannot_legitimize"]["executed"] == 0
    assert results["risk_consequential_effect_read_only_declared_risk_denied"]["executed"] == 0
    assert results["risk_generic_shell_read_only_node_cap_denied"]["executed"] == 0
    assert results["corrupt_request_among_valid_isolated"]["fail_closed"] is True
    assert results["corrupt_result_does_not_terminalize"]["lifecycle"] == "RECONCILIATION_REQUIRED"
    assert results["event_journal_malformed_line_fails_closed"]["fail_closed"] is True
    assert results["event_journal_read_error_fails_closed"]["fail_closed"] is True
    assert results["attempt_store_unknown_corruption_blocks_attempt_authority"]["fail_closed"] is True
    assert results["attempt_store_lease_corruption_blocks_conflicting_lease"]["fail_closed"] is True
    assert results["attempt_store_cas_rewrite_preserves_corruption"]["fail_closed"] is True
    assert all(int(result["executed"]) <= 1 for result in results.values())
    assert all(int(result["sync_side_effects"]) == 0 for result in results.values())
