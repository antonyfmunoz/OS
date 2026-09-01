from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TLA = (
    ROOT
    / "models"
    / "wave2_authority_plane_liveness"
    / "Wave2AuthorityPlaneLiveness.tla"
)
CFG = TLA.with_suffix(".cfg")


def _action(source: str, name: str, next_name: str) -> str:
    return source.split(f"{name} ==", 1)[1].split(f"{next_name} ==", 1)[0]


def test_transport_send_and_canonical_result_acceptance_are_distinct_model_actions() -> None:
    source = TLA.read_text(encoding="utf-8")
    complete_send = _action(source, "CompleteSend", "SendDeadline")
    canonical_acceptance = _action(
        source,
        "AcceptCanonicalResult",
        "ObserveResultReceipt",
    )

    assert "!.sent = TRUE" in complete_send
    assert "!.accepted =" not in complete_send
    assert "result.sent" in canonical_acceptance
    assert "result.identityValid" in canonical_acceptance
    assert "result.sentGeneration = transport.generation" in canonical_acceptance
    assert "!.accepted = TRUE" in canonical_acceptance


def test_claim_send_receipt_and_canonical_persistence_are_distinct_model_actions() -> None:
    source = TLA.read_text(encoding="utf-8")
    complete_send = _action(source, "CompleteSend", "ReceiveClaim")
    receive_claim = _action(source, "ReceiveClaim", "PersistCanonicalClaim")
    persist_claim = _action(source, "PersistCanonicalClaim", "SendDeadline")

    assert "!.sent = TRUE" in complete_send
    assert "!.persisted = TRUE" not in complete_send
    assert "claim.sent" in receive_claim
    assert "!.received = TRUE" in receive_claim
    assert "claim.received" in persist_claim
    assert "!.persisted = TRUE" in persist_claim


def test_model_represents_execution_truth_receipt_conflict_and_pump_quiescence() -> None:
    source = TLA.read_text(encoding="utf-8")
    config = CFG.read_text(encoding="utf-8")
    required = {
        "ConnectionFailureCannotPublishFalseFailure",
        "ActualExecutionOutcomeDeterminesTerminalState",
        "StableResultIdentityRequiredForAcceptance",
        "ConflictingResultEntersReconciliation",
        "TransportSendDoesNotImplyCanonicalAcceptance",
        "AtMostOneDurablePumpGeneration",
        "DurablePumpQuiescedBeforeReplacement",
        "DurablePumpEventuallyQuiescesOnShutdown",
    }

    for property_name in required:
        assert f"{property_name} ==" in source
        assert property_name in config
    assert "executionRunning" in source
    assert "outcomeKnown" in source
    assert "pumpGeneration" in source


def test_model_preserves_started_execution_truth_after_cancel_request() -> None:
    source = TLA.read_text(encoding="utf-8")
    cancellation = _action(
        source,
        "CancellationSafetyPreserved",
        "ConnectionFailureCannotPublishFalseFailure",
    )
    assert "~result.executionRunning" in cancellation
    assert "~result.outcomeKnown" in cancellation
    assert "executionCount = 0" in cancellation


def test_model_replays_retained_results_without_attempt_cutoff() -> None:
    source = TLA.read_text(encoding="utf-8")
    queue_replay = _action(source, "QueueRetainedResult", "ResultAuthorityOverflow")
    replay_liveness = _action(
        source,
        "PendingTerminalResultEventuallyReplayedAfterHealthyReconnect",
        "GenerationTasksEventuallyQuiesceUnderCooperativeTasks",
    )
    assert "result.replayCount < 3" not in queue_replay
    assert "result.replayCount < 3" not in replay_liveness


def test_model_requires_closed_generation_pump_quiescence() -> None:
    source = TLA.read_text(encoding="utf-8")
    property_text = _action(
        source,
        "DurablePumpQuiescedBeforeReplacement",
        "ReplacementGenerationRequiresPriorGenerationQuiescence",
    )
    assert "QuiescedGeneration" in property_text
    assert "~transport.pumpActive" in property_text


def test_model_structurally_bounds_connection_and_pump_singletons() -> None:
    source = TLA.read_text(encoding="utf-8")
    connection = _action(
        source,
        "AtMostOneActiveConnectionGeneration",
        "AtMostOneDurablePumpGeneration",
    )
    pump = _action(
        source,
        "AtMostOneDurablePumpGeneration",
        "DurablePumpQuiescedBeforeReplacement",
    )

    assert "activeGenerationCount <= 1" in connection
    assert "pumpActiveCount <= 1" in pump
    assert "pumpGeneration = transport.generation" in pump


def test_model_binds_ack_to_logical_authority_without_rejecting_reconnect() -> None:
    source = TLA.read_text(encoding="utf-8")
    stale_ack = _action(
        source,
        "StaleAckCannotSatisfyNewGeneration",
        "ReconnectDoesNotInvalidateProvenLogicalAuthority",
    )
    assert "proofLogicalAuthorityId = claim.logicalAuthorityId" in stale_ack
    assert "proofGeneration <= transport.generation" in stale_ack
    assert "proofGeneration = transport.generation" not in stale_ack


def test_model_requires_exact_cancel_identity_and_monotonic_outcome() -> None:
    source = TLA.read_text(encoding="utf-8")
    foreign_cancel = _action(
        source,
        "ForeignClaimCannotCancelActiveExecution",
        "ClaimSendDoesNotImplyCanonicalPersistence",
    )
    assert "foreignControlRejected" in foreign_cancel
    assert "~cancelled" in foreign_cancel
    assert "ExecutionOutcomeIsMonotonic ==" in source
    assert "KnownSuccessCannotBecomeFailure ==" in source
