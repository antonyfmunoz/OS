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
        "corrupt_same_key_request_blocks_fresh_admission",
        "corrupt_same_key_retry_new_request_id_denied",
        "corrupt_same_key_survives_restart",
        "corrupt_quarantined_request_preserves_key_fence",
        "corrupt_valid_binding_plus_duplicate_preserves_canonical",
        "corrupt_index_plus_corrupt_request_fences_key",
        "corrupt_unknown_scope_request_blocks_unproven_admission",
        "corrupt_unrelated_key_progresses_beside_key_scoped_corruption",
        "corrupt_event_history_incomplete_cannot_prove_absence",
        "corrupt_restart_still_non_executable",
        "corrupt_result_does_not_terminalize",
        "canonicalization_escaped_json_key_value_bypass",
        "canonicalization_escaped_field_name_bypass",
        "canonicalization_attempt_store_escaped_scope",
        "canonicalization_lease_store_escaped_scope",
        "canonicalization_duplicate_authority_field_ambiguous",
        "canonicalization_nested_decoy_identity_unknown_scope",
        "canonicalization_malformed_raw_token_unknown_scope",
        "canonicalization_bound_and_corrupt_fenced_represented",
        "canonicalization_bound_and_corrupt_fenced_blocks_fresh",
        "canonicalization_terminal_bound_plus_corruption",
        "canonicalization_restart_preserves_fence",
        "canonicalization_unrelated_clean_key_progresses",
        "transport_bulk_saturation_claim_gets_authority_service",
        "transport_bulk_saturation_result_gets_authority_service",
        "transport_reconciliation_cannot_starve_new_claim",
        "transport_ws_ack_unavailable_http_readback_healthy",
        "transport_ws_ack_unavailable_http_readback_unavailable",
        "transport_bounded_reconciliation_reminders",
        "transport_cancellation_while_authority_delayed",
        "transport_combined_starvation_reproduction_closed",
        "transport_blocked_bulk_send_resets_generation",
        "transport_authority_overflow_fails_closed",
        "transport_terminal_result_retained_during_overload",
        "transport_continuous_bulk_producer_cannot_starve_claim",
        "transport_reconciliation_backoff_survives_restart",
        "transport_http_timeout_and_ws_ack_loss_fail_closed",
        "transport_cancel_under_saturation_never_launches",
        "terminal_result_send_timeout_then_reconnect_replay",
        "terminal_result_startup_replay",
        "terminal_result_ack_lost_replays_same_identity",
        "terminal_result_conflict_fails_closed",
        "transport_old_generation_handler_cannot_send_on_reconnect",
        "transport_pending_rpc_failed_during_generation_teardown",
        "transport_stubborn_generation_task_blocks_reconnect",
        "terminal_result_and_stale_handler_generation_race",
        "execution_disconnect_preserves_actual_terminal_truth",
        "execution_cancel_non_cancellable_records_actual_outcome",
        "terminal_result_send_not_canonical_acceptance",
        "transport_durable_pump_quiesces_before_replacement",
        "execution_foreign_claim_cancel_rejected",
        "execution_known_success_is_monotonic",
        "execution_observerless_restart_stays_unresolved",
        "authority_claim_send_without_persistence_cannot_execute",
        "authority_reconnect_preserves_proven_logical_authority",
        "shell_prelaunch_cancel_prevents_process_creation",
        "shell_cancel_during_launch_uncertainty_reconciles",
        "cleanup_pid_reuse_does_not_touch_unrelated_process",
        "cleanup_escaped_descendant_fails_positive_zero",
        "cleanup_incomplete_enumeration_fails_closed",
        "sol_unapproved_executable_cannot_attest",
        "model_ambient_substitution_rejected",
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
        "terminal_recovery_bypass_rejected",
        "terminal_reconciliation_bypass_rejected",
        "terminal_timeout_bypass_rejected",
        "terminal_prelaunch_no_process_proof_admitted",
        "sol_replaced_path_executes_approved_open_object",
        "sol_governed_immutable_runner_attests",
        "shell_resume_zero_observes_running_process",
        "shell_resume_failure_sentinel_reconciles",
        "shell_resume_multiple_count_fails_after_cleanup",
        "shell_resume_ambiguous_running_observes_outcome",
        "authority_ack_old_exchange_cannot_prove_new",
        "transport_connection_overlap_attempt_guarded",
        "transport_pump_overlap_attempt_guarded",
    }
    assert results["fallback_unavailable"]["executed"] == 0
    assert results["fallback_unavailable"]["fail_closed"] is True
    assert results["terminal_late_foreign_running"]["lifecycle"] == "SUCCEEDED"
    assert results["terminal_recovery_bypass_rejected"]["lifecycle"] == (
        "RECONCILIATION_REQUIRED"
    )
    assert results["terminal_timeout_bypass_rejected"]["lifecycle"] == (
        "RECONCILIATION_REQUIRED"
    )
    assert results["terminal_prelaunch_no_process_proof_admitted"]["lifecycle"] == "FAILED"
    assert results["sol_replaced_path_executes_approved_open_object"][
        "codex_executable_approved"
    ] is True
    assert results["shell_resume_failure_sentinel_reconciles"]["lifecycle"] == (
        "RECONCILIATION_REQUIRED"
    )
    assert results["authority_ack_old_exchange_cannot_prove_new"]["executed"] == 0
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
    assert results["transport_bulk_saturation_claim_gets_authority_service"]["executed"] == 1
    assert results["transport_ws_ack_unavailable_http_readback_unavailable"]["executed"] == 0
    assert results["transport_ws_ack_unavailable_http_readback_unavailable"]["fail_closed"] is True
    assert results["transport_authority_overflow_fails_closed"]["fail_closed"] is True
    assert results["transport_terminal_result_retained_during_overload"][
        "terminal_result_retained"
    ] is True
    assert results["transport_http_timeout_and_ws_ack_loss_fail_closed"]["executed"] == 0
    assert results["transport_cancel_under_saturation_never_launches"]["executed"] == 0
    assert results["terminal_result_send_timeout_then_reconnect_replay"]["executed"] == 1
    assert results["terminal_result_conflict_fails_closed"]["fail_closed"] is True
    assert results["transport_stubborn_generation_task_blocks_reconnect"][
        "fail_closed"
    ] is True
    assert results["execution_foreign_claim_cancel_rejected"]["executed"] == 1
    assert results["execution_foreign_claim_cancel_rejected"]["lifecycle"] == "RUNNING"
    assert results["execution_known_success_is_monotonic"]["lifecycle"] == "SUCCEEDED"
    assert results["execution_observerless_restart_stays_unresolved"]["lifecycle"] == "RUNNING"
    assert results["authority_claim_send_without_persistence_cannot_execute"]["executed"] == 0
    assert results["authority_reconnect_preserves_proven_logical_authority"]["executed"] == 1
    assert results["shell_prelaunch_cancel_prevents_process_creation"][
        "shell_process_created"
    ] is False
    assert results["shell_cancel_during_launch_uncertainty_reconciles"][
        "lifecycle"
    ] == "RECONCILIATION_REQUIRED"
    assert results["cleanup_pid_reuse_does_not_touch_unrelated_process"][
        "unrelated_reused_process_touched"
    ] is False
    assert results["cleanup_escaped_descendant_fails_positive_zero"][
        "cleanup_verified"
    ] is False
    assert results["cleanup_incomplete_enumeration_fails_closed"][
        "cleanup_verified"
    ] is False
    assert results["sol_unapproved_executable_cannot_attest"]["fail_closed"] is True
    assert results["sync_generic_shell_declares_read_only_denied"]["fail_closed"] is True
    assert results["sync_policy_lookup_unavailable_denied"]["fail_closed"] is True
    assert results["sync_stale_effect_policy_verdict_rejected"]["fail_closed"] is True
    assert results["sync_caller_effect_change_no_authority_change"]["fail_closed"] is True
    assert results["recovery_incomplete_candidate_sha_fails_closed"]["fail_closed"] is True
    assert results["recovery_invalid_existing_success_cannot_legitimize"]["executed"] == 0
    assert results["risk_consequential_effect_read_only_declared_risk_denied"]["executed"] == 0
    assert results["risk_generic_shell_read_only_node_cap_denied"]["executed"] == 0
    assert results["corrupt_request_among_valid_isolated"]["fail_closed"] is True
    assert results["corrupt_same_key_request_blocks_fresh_admission"]["fail_closed"] is True
    assert any(
        "admission_absence_unproven:key=K:corrupt_request" in event
        for event in results["corrupt_same_key_request_blocks_fresh_admission"]["log"]
    )
    assert results["corrupt_same_key_retry_new_request_id_denied"]["fail_closed"] is True
    assert results["corrupt_same_key_survives_restart"]["fail_closed"] is True
    assert results["corrupt_quarantined_request_preserves_key_fence"]["fail_closed"] is True
    assert results["corrupt_valid_binding_plus_duplicate_preserves_canonical"]["fail_closed"] is False
    assert results["corrupt_index_plus_corrupt_request_fences_key"]["fail_closed"] is True
    assert (
        results["corrupt_unknown_scope_request_blocks_unproven_admission"]["fail_closed"]
        is True
    )
    assert results["corrupt_unrelated_key_progresses_beside_key_scoped_corruption"]["fail_closed"] is False
    assert results["corrupt_event_history_incomplete_cannot_prove_absence"]["fail_closed"] is True
    assert results["corrupt_result_does_not_terminalize"]["lifecycle"] == "RECONCILIATION_REQUIRED"
    assert results["canonicalization_escaped_json_key_value_bypass"]["fail_closed"] is True
    assert results["canonicalization_escaped_field_name_bypass"]["fail_closed"] is True
    assert results["canonicalization_duplicate_authority_field_ambiguous"]["fail_closed"] is True
    assert results["canonicalization_nested_decoy_identity_unknown_scope"]["fail_closed"] is True
    assert results["canonicalization_malformed_raw_token_unknown_scope"]["fail_closed"] is True
    assert results["canonicalization_bound_and_corrupt_fenced_represented"]["fail_closed"] is False
    assert results["canonicalization_bound_and_corrupt_fenced_blocks_fresh"]["fail_closed"] is False
    assert results["canonicalization_terminal_bound_plus_corruption"]["lifecycle"] == "SUCCEEDED"
    assert results["canonicalization_restart_preserves_fence"]["fail_closed"] is True
    assert results["canonicalization_unrelated_clean_key_progresses"]["fail_closed"] is False
    assert results["event_journal_malformed_line_fails_closed"]["fail_closed"] is True
    assert results["event_journal_read_error_fails_closed"]["fail_closed"] is True
    assert results["attempt_store_unknown_corruption_blocks_attempt_authority"]["fail_closed"] is True
    assert results["attempt_store_lease_corruption_blocks_conflicting_lease"]["fail_closed"] is True
    assert results["attempt_store_cas_rewrite_preserves_corruption"]["fail_closed"] is True
    assert all(int(result["executed"]) <= 1 for result in results.values())
    assert all(int(result["sync_side_effects"]) == 0 for result in results.values())
