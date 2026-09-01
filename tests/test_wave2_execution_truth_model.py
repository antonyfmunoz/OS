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
