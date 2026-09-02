from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TLA = ROOT / "models" / "wave2_authority_plane_liveness" / "Wave2AuthorityPlaneLiveness.tla"
CFG = TLA.with_suffix(".cfg")
ADEQUACY = TLA.with_name("Wave2AuthorityPlaneAdequacy.tla")
ADEQUACY_RUNNER = ROOT / "scripts" / "wave2_authority_model_adequacy.py"


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
    assert "/\\ result.sent\n" in canonical_acceptance
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
    assert "cancelProvenBeforeLaunch" in cancellation
    assert "cancelDuringLaunchUncertainty" in cancellation
    assert "~result.processCreated" in cancellation
    assert "result.launchReconciliation" in cancellation


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
    assert "proofGeneration = transport.generation" in stale_ack
    assert "proofExchangeId = claim.ackExchangeId" in stale_ack


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


def test_model_initial_state_is_type_correct_not_the_boolean_set() -> None:
    source = TLA.read_text(encoding="utf-8")
    init = _action(source, "Init", "ClaimOutstanding")
    assert "|-> BOOLEAN" not in init
    assert "cancelIdentityValid |-> FALSE" in init
    assert "identityValid |-> FALSE" in init
    assert "TypeOK ==" in source
    assert "INVARIANT TypeOK" in CFG.read_text(encoding="utf-8")


def test_model_outcome_branches_are_explicit_and_reachable_from_running() -> None:
    source = TLA.read_text(encoding="utf-8")
    for action_name, outcome in (
        ("ProduceSucceededTerminalResult", "SucceededOutcome"),
        ("ProduceFailedTerminalResult", "FailedOutcome"),
        ("ProduceCancelledTerminalResult", "CancelledOutcome"),
    ):
        action = _action(
            source,
            action_name,
            {
                "ProduceSucceededTerminalResult": "ProduceFailedTerminalResult",
                "ProduceFailedTerminalResult": "ProduceCancelledTerminalResult",
                "ProduceCancelledTerminalResult": "LoseExecutionObserver",
            }[action_name],
        )
        assert "result.executionRunning" in action
        assert "/\\ FALSE" not in action
        assert f"!.outcome = {outcome}" in action
    observer_loss = _action(source, "LoseExecutionObserver", "ProduceTerminalResult")
    assert "!.observerPresent = FALSE" in observer_loss
    assert "!.outcome = ReconciliationOutcome" in observer_loss


def test_model_has_non_vacuous_foreign_claim_and_singleton_overlap_attempts() -> None:
    source = TLA.read_text(encoding="utf-8")
    foreign = _action(source, "PresentForeignControl", "RejectForeignCancel")
    reject = _action(source, "RejectForeignCancel", "ProduceBulk")
    connection = _action(
        source,
        "AttemptConnectionGenerationOverlap",
        "AttemptPumpGenerationOverlap",
    )
    pump = _action(source, "AttemptPumpGenerationOverlap", "WriterStart")
    assert "incomingLogicalAuthorityId" in foreign
    assert "incomingLogicalAuthorityId # claim.logicalAuthorityId" in reject
    assert "connectionOverlapAttempted = TRUE" in connection
    assert "pumpOverlapAttempted = TRUE" in pump
    assert "activeGenerationCount <= 1" in source
    assert "pumpActiveCount <= 1" in source


def test_model_shell_launch_uncertainty_is_reachable_and_fences_execution() -> None:
    source = TLA.read_text(encoding="utf-8")
    required_actions = (
        "PersistShellLaunchIntent",
        "AttemptShellLaunch",
        "CreateShellProcess",
        "AssignShellJob",
        "VerifyShellJobMembership",
        "PersistShellProcessIdentity",
        "ResumeShellProcess",
        "AdmitShellRunning",
        "CrashDuringUncertainShellLaunch",
        "RejectDuplicateShellLaunch",
    )
    for action in required_actions:
        assert f"{action} ==" in source
    crash = _action(
        source,
        "CrashDuringUncertainShellLaunch",
        "RejectDuplicateShellLaunch",
    )
    admit = _action(source, "AdmitShellRunning", "CrashDuringUncertainShellLaunch")
    execute = _action(source, "Execute", "ProduceSucceededTerminalResult")
    assert "result.processResumed" in admit
    assert "(~result.launchIntentPersisted \\/ result.shellRunning)" in execute
    assert "result.launchAttempted" in crash
    assert "~result.processIdentityPersisted" in crash
    assert "!.outcome = ReconciliationOutcome" in crash
    assert "UncertainShellLaunchCannotExecuteOrRelaunch" in source


def test_model_prelaunch_cancel_guards_process_creation_and_connection_loss_preserves_execution() -> None:
    source = TLA.read_text(encoding="utf-8")
    create = _action(source, "CreateShellProcess", "PersistShellProcessIdentity")
    disconnect = _action(
        source,
        "ConnectionFailsDuringExecution",
        "AttemptConnectionGenerationOverlap",
    )
    observer_loss = _action(source, "LoseExecutionObserver", "ProduceTerminalResult")

    assert "~cancelled" in create
    assert "~result.cancelProvenBeforeLaunch" in create
    assert "result.executionRunning" in disconnect
    assert "!.connectionLossObserved = TRUE" in disconnect
    assert "!.executionRunning = FALSE" not in disconnect
    assert "!.executionRunning = FALSE" not in observer_loss
    assert "PreLaunchCancellationPreventsProcessCreation" in source
    assert "ConnectionLossDoesNotTerminateExecution" in source


def test_model_stale_ack_requires_exact_transport_and_exchange_generation() -> None:
    source = TLA.read_text(encoding="utf-8")
    observe = _action(source, "ObserveClaimAck", "HttpReadback")
    stale = _action(source, "PresentStaleAck", "RejectStaleAck")
    reject = _action(source, "RejectStaleAck", "ConnectionFailsDuringExecution")

    assert "claim.sentGeneration = transport.generation" in observe
    assert "claim.incomingAckExchangeId = claim.ackExchangeId" in observe
    assert "claim.incomingAckGeneration = transport.generation" in observe
    assert "incomingAckExchangeId" in stale
    assert "!.staleAckRejected = TRUE" in reject


def test_model_job_resume_and_overlap_guards_are_mutation_visible() -> None:
    source = TLA.read_text(encoding="utf-8")
    config = CFG.read_text(encoding="utf-8")
    resume = _action(source, "ResumeShellProcess", "AdmitShellRunning")
    connection = _action(
        source,
        "AttemptConnectionGenerationOverlap",
        "AttemptPumpGenerationOverlap",
    )
    pump = _action(source, "AttemptPumpGenerationOverlap", "WriterStart")

    assert "result.processIdentityPersisted" in resume
    assert "~cancelled" in resume
    assert "EnforceConnectionSingleton" in connection
    assert "@ + 1" in connection
    assert "EnforcePumpSingleton" in pump
    assert "@ + 1" in pump
    assert "EnforceConnectionSingleton = TRUE" in config
    assert "EnforcePumpSingleton = TRUE" in config
    assert "INVARIANT JobContainmentPrecedesResume" in config


def test_model_adequacy_manifest_is_executable_and_complete() -> None:
    adequacy = ADEQUACY.read_text(encoding="utf-8")
    runner = ADEQUACY_RUNNER.read_text(encoding="utf-8")
    for witness in (
        "PreLaunchCancel",
        "CancelDuringLaunch",
        "KnownProcessCancel",
        "ConnectionLossDuringExecution",
        "Failed",
        "Cancelled",
        "Reconciliation",
        "StaleAck",
        "ConnectionOverlapAttempt",
        "PumpOverlapAttempt",
        "ResultSentNotAccepted",
        "ClaimSentNotPersisted",
        "JobContainedBeforeResume",
    ):
        assert f"Witness{witness} ==" in adequacy
        assert f'"{witness}"' in runner
    assert "MODEL_ADEQUACY=true" in runner
    assert "EnforceConnectionSingleton = FALSE" in runner
    assert "EnforcePumpSingleton = FALSE" in runner


def test_model_claim_ack_and_result_acceptance_have_separate_observation_stages() -> None:
    source = TLA.read_text(encoding="utf-8")
    send_ack = _action(source, "SendClaimAck", "SendDeadline")
    observe_ack = _action(source, "ObserveClaimAck", "HttpReadback")
    validate_result = _action(source, "ValidateResultIdentity", "AcceptCanonicalResult")
    assert "claim.persisted" in send_ack
    assert "!.ackSent = TRUE" in send_ack
    assert "claim.ackSent" in observe_ack
    assert "result.retained" in validate_result
    assert "!.identityValid = TRUE" in validate_result
