---- MODULE Wave2AuthorityPlaneLiveness ----
EXTENDS Naturals, Sequences, TLC

(*
Bounded authority transport, durable terminal outbox, and connection-generation
ownership model.

Implementation correspondence:
- authorityQueue, reconciliationQueue, and bulkQueue are separate finite queues;
- writer is one serialized, generation-bound WebSocket writer;
- every in-flight send completes or moves the transport to CLOSING at SendBound;
- a replacement generation requires bounded cooperative task quiescence;
- pending RPCs are failed when a generation starts closing;
- stale generation work is rejected rather than transferred to a new writer;
- result.retained is the durable node-local terminal result/outbox identity;
- WebSocket send completion is not canonical result acknowledgement;
- canonical VPS acceptance and result receipt are separate transitions;
- started execution remains logical-operation owned across connection failure;
- each server generation owns at most one durable pump and quiesces it before replacement;
- an accepted result with a lost receipt remains retained and is replayed;
- replay changes delivery attempts only, never executionCount;
- HTTP claim readback remains independent of the WebSocket queues.

Durable request material and idempotency safety remain in
models/wave2_durable_remote/Wave2DurableRemote.tla.
*)

CONSTANT
    AuthorityCapacity,
    BulkCapacity,
    ReconCapacity,
    AuthorityBurstLimit,
    SendBound,
    MaxReconChecks,
    MaxTransportGeneration,
    MaxGenerationTasks,
    EnforceConnectionSingleton,
    EnforcePumpSingleton,
    EnforceAckExchangeBinding,
    EnforcePreLaunchCancellation,
    EnforceTerminalCleanup,
    EnforceLaunchUncertaintyTerminalGuard,
    EnforceSnapshotObservationTruth,
    EnforceOpenThreadObservationTruth,
    EnforceResumeResultContract,
    EnforceUnexpectedResumeNoRelaunch,
    EnforceUnknownSuspendTerminalGuard

NoSend == "NONE"
AuthoritySend == "AUTHORITY"
ReconciliationSend == "RECONCILIATION"
BulkSend == "BULK"
SendClasses == {NoSend, AuthoritySend, ReconciliationSend, BulkSend}

ClaimFrame == "CLAIM"
ResultFrame == "RESULT"
CancelFrame == "CANCEL"
GenericAuthorityFrame == "GENERIC_AUTHORITY"
AuthorityFrames == {ClaimFrame, ResultFrame, CancelFrame, GenericAuthorityFrame}
NoFrame == "NO_FRAME"

ActiveGeneration == "ACTIVE"
ClosingGeneration == "CLOSING"
QuiescedGeneration == "QUIESCED"
FailedGeneration == "FAILED"
GenerationStates == {
    ActiveGeneration,
    ClosingGeneration,
    QuiescedGeneration,
    FailedGeneration
}

NoProof == "NO_PROOF"
AckProof == "ACK_PROOF"
ReadbackProof == "READBACK_PROOF"
ProofSources == {NoProof, AckProof, ReadbackProof}

UnknownOutcome == "UNKNOWN"
RunningOutcome == "RUNNING"
SucceededOutcome == "SUCCEEDED"
FailedOutcome == "FAILED"
CancelledOutcome == "CANCELLED"
ReconciliationOutcome == "RECONCILIATION_REQUIRED"
OutcomeStates == {
    UnknownOutcome,
    RunningOutcome,
    SucceededOutcome,
    FailedOutcome,
    CancelledOutcome,
    ReconciliationOutcome
}

UnknownSuspendState == "UNKNOWN"
SuspendedState == "SUSPENDED"
ResumedState == "RESUMED"
ExitedState == "EXITED"
SuspendStates == {UnknownSuspendState, SuspendedState, ResumedState, ExitedState}

NoResumeResult == "NOT_ATTEMPTED"
ExpectedResumeResult == "EXPECTED"
UnexpectedResumeResult == "UNEXPECTED"
FailedResumeResult == "FAILURE"
ResumeResults == {
    NoResumeResult,
    ExpectedResumeResult,
    UnexpectedResumeResult,
    FailedResumeResult
}

NoSuspendObservation == "NONE"
SnapshotFailureObservation == "SNAPSHOT_FAILURE"
OpenThreadFailureObservation == "OPEN_THREAD_FAILURE"
ExpectedResumeObservation == "EXPECTED_RESUME"
UnexpectedZeroObservation == "UNEXPECTED_ZERO"
UnexpectedMultipleObservation == "UNEXPECTED_MULTIPLE"
ResumeFailureObservation == "RESUME_FAILURE"
ExistingRunningObservation == "EXISTING_RUNNING"
SuspendObservations == {
    NoSuspendObservation,
    SnapshotFailureObservation,
    OpenThreadFailureObservation,
    ExpectedResumeObservation,
    UnexpectedZeroObservation,
    UnexpectedMultipleObservation,
    ResumeFailureObservation,
    ExistingRunningObservation
}

NoGeneration == MaxTransportGeneration + 1
Generations == 0..MaxTransportGeneration

SeqContains(seq, value) == \E index \in DOMAIN seq : seq[index] = value

VARIABLES
    authorityQueue,
    bulkQueue,
    reconciliationQueue,
    writer,
    transport,
    authorityBurst,
    authorityOverflow,
    authorityFailureVisible,
    claim,
    failedClosed,
    executionCount,
    cancelled,
    result,
    staleGenerationSendRejected,
    reconciliationChecks,
    reconciliationReminderEvents

vars == <<
    authorityQueue,
    bulkQueue,
    reconciliationQueue,
    writer,
    transport,
    authorityBurst,
    authorityOverflow,
    authorityFailureVisible,
    claim,
    failedClosed,
    executionCount,
    cancelled,
    result,
    staleGenerationSendRejected,
    reconciliationChecks,
    reconciliationReminderEvents
>>

TypeOK ==
    /\ authorityQueue \in Seq(AuthorityFrames)
    /\ Len(authorityQueue) <= AuthorityCapacity
    /\ bulkQueue \in 0..BulkCapacity
    /\ reconciliationQueue \in 0..ReconCapacity
    /\ writer \in [
        class: SendClasses,
        frame: AuthorityFrames \cup {NoFrame},
        age: 0..SendBound,
        generation: Generations \cup {NoGeneration}
        ]
    /\ transport \in [
        healthy: BOOLEAN,
        generation: Generations,
        state: GenerationStates,
        tasks: 0..MaxGenerationTasks,
        cooperative: BOOLEAN,
        pendingRpc: BOOLEAN,
        reconnectWasQuiescent: BOOLEAN,
        activeGenerationCount: 0..2,
        pumpActive: BOOLEAN,
        pumpActiveCount: 0..2,
        pumpGeneration: Generations \cup {NoGeneration},
        connectionOverlapAttempted: BOOLEAN,
        pumpOverlapAttempted: BOOLEAN,
        connectionAActive: BOOLEAN,
        connectionBActive: BOOLEAN,
        pumpAActive: BOOLEAN,
        pumpBActive: BOOLEAN
        ]
    /\ authorityBurst \in 0..AuthorityBurstLimit
    /\ authorityOverflow \in BOOLEAN
    /\ authorityFailureVisible \in BOOLEAN
    /\ claim \in [
        pending: BOOLEAN,
        prepared: BOOLEAN,
        queued: BOOLEAN,
        sent: BOOLEAN,
        received: BOOLEAN,
        persisted: BOOLEAN,
        ackSent: BOOLEAN,
        sentGeneration: Generations \cup {NoGeneration},
        logicalAuthorityId: 1..2,
        incomingLogicalAuthorityId: 1..2,
        proofLogicalAuthorityId: 0..2,
        requestIdentityId: 1..2,
        claimIdentityId: 1..2,
        executionIdentityId: 1..2,
        ackExchangeId: 1..2,
        incomingAckExchangeId: 1..2,
        incomingAckGeneration: Generations,
        incomingAckRequestId: 1..2,
        incomingAckClaimId: 1..2,
        incomingAckExecutionId: 1..2,
        ackMessageId: 1..2,
        incomingAckMessageId: 1..2,
        proofExchangeId: 0..2,
        proofRequestId: 0..2,
        proofClaimId: 0..2,
        proofExecutionId: 0..2,
        proofMessageId: 0..2,
        staleAckRejected: BOOLEAN,
        cancelIdentityValid: BOOLEAN,
        foreignControlRejected: BOOLEAN,
        ackHealthy: BOOLEAN,
        readbackHealthy: BOOLEAN,
        proven: BOOLEAN,
        proofSource: ProofSources,
        proofGeneration: Generations \cup {NoGeneration}
        ]
    /\ failedClosed \in BOOLEAN
    /\ executionCount \in 0..1
    /\ cancelled \in BOOLEAN
    /\ result \in [
        retained: BOOLEAN,
        logicalId: 0..1,
        sent: BOOLEAN,
        identityValid: BOOLEAN,
        accepted: BOOLEAN,
        acknowledged: BOOLEAN,
        awaitingReceipt: BOOLEAN,
        sentGeneration: Generations \cup {NoGeneration},
        receiptHealthy: BOOLEAN,
        conflict: BOOLEAN,
        reconciliation: BOOLEAN,
        executionRunning: BOOLEAN,
        outcomeKnown: BOOLEAN,
        outcome: OutcomeStates,
        observerPresent: BOOLEAN,
        connectionLossObserved: BOOLEAN,
        cancelRequested: BOOLEAN,
        cancelProvenBeforeLaunch: BOOLEAN,
        cancelDuringLaunchUncertainty: BOOLEAN,
        cancelAppliedToKnownProcess: BOOLEAN,
        cancellationOutcomeKnown: BOOLEAN,
        launchIntentPersisted: BOOLEAN,
        launchAttempted: BOOLEAN,
        processCreated: BOOLEAN,
        jobAssigned: BOOLEAN,
        jobMembershipVerified: BOOLEAN,
        processIdentityPersisted: BOOLEAN,
        processCreationCount: 0..2,
        processResumed: BOOLEAN,
        resumeAmbiguous: BOOLEAN,
        suspendState: SuspendStates,
        resumeResult: ResumeResults,
        suspendObservation: SuspendObservations,
        shellRunning: BOOLEAN,
        launchReconciliation: BOOLEAN,
        duplicateLaunchRejected: BOOLEAN,
        cleanupComplete: BOOLEAN,
        noExecutionProof: BOOLEAN,
        terminalAdmissibilityRejected: BOOLEAN,
        replayCount: 0..3
        ]
    /\ staleGenerationSendRejected \in BOOLEAN
    /\ reconciliationChecks \in 0..MaxReconChecks
    /\ reconciliationReminderEvents \in 0..ReconCapacity

Init ==
    /\ authorityQueue = <<>>
    /\ bulkQueue \in 0..BulkCapacity
    /\ reconciliationQueue \in 0..ReconCapacity
    /\ writer = [
        class |-> NoSend,
        frame |-> NoFrame,
        age |-> 0,
        generation |-> NoGeneration
        ]
    /\ transport = [
        healthy |-> TRUE,
        generation |-> 0,
        state |-> ActiveGeneration,
        tasks |-> MaxGenerationTasks,
        cooperative |-> TRUE,
        pendingRpc |-> FALSE,
        reconnectWasQuiescent |-> TRUE,
        activeGenerationCount |-> 1,
        pumpActive |-> TRUE,
        pumpActiveCount |-> 1,
        pumpGeneration |-> 0,
        connectionOverlapAttempted |-> FALSE,
        pumpOverlapAttempted |-> FALSE,
        connectionAActive |-> TRUE,
        connectionBActive |-> FALSE,
        pumpAActive |-> TRUE,
        pumpBActive |-> FALSE
        ]
    /\ authorityBurst = 0
    /\ authorityOverflow = FALSE
    /\ authorityFailureVisible = FALSE
    /\ claim = [
        pending |-> TRUE,
        prepared |-> TRUE,
        queued |-> FALSE,
        sent |-> FALSE,
        received |-> FALSE,
        persisted |-> FALSE,
        ackSent |-> FALSE,
        sentGeneration |-> NoGeneration,
        logicalAuthorityId |-> 1,
        incomingLogicalAuthorityId |-> 1,
        proofLogicalAuthorityId |-> 0,
        requestIdentityId |-> 1,
        claimIdentityId |-> 1,
        executionIdentityId |-> 1,
        ackExchangeId |-> 1,
        incomingAckExchangeId |-> 1,
        incomingAckGeneration |-> 0,
        incomingAckRequestId |-> 1,
        incomingAckClaimId |-> 1,
        incomingAckExecutionId |-> 1,
        ackMessageId |-> 1,
        incomingAckMessageId |-> 1,
        proofExchangeId |-> 0,
        proofRequestId |-> 0,
        proofClaimId |-> 0,
        proofExecutionId |-> 0,
        proofMessageId |-> 0,
        staleAckRejected |-> FALSE,
        cancelIdentityValid |-> FALSE,
        foreignControlRejected |-> FALSE,
        ackHealthy |-> TRUE,
        readbackHealthy |-> TRUE,
        proven |-> FALSE,
        proofSource |-> NoProof,
        proofGeneration |-> NoGeneration
        ]
    /\ failedClosed = FALSE
    /\ executionCount = 0
    /\ cancelled = FALSE
    /\ result = [
        retained |-> FALSE,
        logicalId |-> 0,
        sent |-> FALSE,
        identityValid |-> FALSE,
        accepted |-> FALSE,
        acknowledged |-> FALSE,
        awaitingReceipt |-> FALSE,
        sentGeneration |-> NoGeneration,
        receiptHealthy |-> TRUE,
        conflict |-> FALSE,
        reconciliation |-> FALSE,
        executionRunning |-> FALSE,
        outcomeKnown |-> FALSE,
        outcome |-> UnknownOutcome,
        observerPresent |-> TRUE,
        connectionLossObserved |-> FALSE,
        cancelRequested |-> FALSE,
        cancelProvenBeforeLaunch |-> FALSE,
        cancelDuringLaunchUncertainty |-> FALSE,
        cancelAppliedToKnownProcess |-> FALSE,
        cancellationOutcomeKnown |-> FALSE,
        launchIntentPersisted |-> FALSE,
        launchAttempted |-> FALSE,
        processCreated |-> FALSE,
        jobAssigned |-> FALSE,
        jobMembershipVerified |-> FALSE,
        processIdentityPersisted |-> FALSE,
        processCreationCount |-> 0,
        processResumed |-> FALSE,
        resumeAmbiguous |-> FALSE,
        suspendState |-> UnknownSuspendState,
        resumeResult |-> NoResumeResult,
        suspendObservation |-> NoSuspendObservation,
        shellRunning |-> FALSE,
        launchReconciliation |-> FALSE,
        duplicateLaunchRejected |-> FALSE,
        cleanupComplete |-> FALSE,
        noExecutionProof |-> FALSE,
        terminalAdmissibilityRejected |-> FALSE,
        replayCount |-> 0
        ]
    /\ staleGenerationSendRejected = FALSE
    /\ reconciliationChecks = 0
    /\ reconciliationReminderEvents = 0

ClaimOutstanding ==
    claim.queued
    \/ SeqContains(authorityQueue, ClaimFrame)
    \/ (writer.class = AuthoritySend /\ writer.frame = ClaimFrame)

ResultOutstanding ==
    SeqContains(authorityQueue, ResultFrame)
    \/ (writer.class = AuthoritySend /\ writer.frame = ResultFrame)
    \/ result.awaitingReceipt

QueueClaim ==
    /\ claim.pending
    /\ claim.prepared
    /\ ~claim.queued
    /\ ~claim.sent
    /\ ~claim.persisted
    /\ ~claim.proven
    /\ ~failedClosed
    /\ ~cancelled
    /\ ~ClaimOutstanding
    /\ Len(authorityQueue) < AuthorityCapacity
    /\ authorityQueue' = Append(authorityQueue, ClaimFrame)
    /\ claim' = [claim EXCEPT !.queued = TRUE]
    /\ UNCHANGED <<
        bulkQueue, reconciliationQueue, writer, transport, authorityBurst,
        authorityOverflow, authorityFailureVisible, failedClosed,
        executionCount, cancelled, result, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ClaimAuthorityOverflow ==
    /\ claim.pending
    /\ ~claim.proven
    /\ ~failedClosed
    /\ ~ClaimOutstanding
    /\ Len(authorityQueue) = AuthorityCapacity
    /\ authorityOverflow' = TRUE
    /\ authorityFailureVisible' = TRUE
    /\ failedClosed' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, claim, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

QueueRetainedResult ==
    /\ result.retained
    /\ ~result.acknowledged
    /\ ~result.conflict
    /\ ~ResultOutstanding
    /\ Len(authorityQueue) < AuthorityCapacity
    /\ authorityQueue' = Append(authorityQueue, ResultFrame)
    /\ UNCHANGED <<
        bulkQueue, reconciliationQueue, writer, transport, authorityBurst,
        authorityOverflow, authorityFailureVisible, claim, failedClosed,
        executionCount, cancelled, result, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ResultAuthorityOverflow ==
    /\ result.retained
    /\ ~result.acknowledged
    /\ ~ResultOutstanding
    /\ Len(authorityQueue) = AuthorityCapacity
    /\ authorityOverflow' = TRUE
    /\ authorityFailureVisible' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, claim, failedClosed, executionCount, cancelled,
        result, staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

RequestCancel ==
    /\ ~cancelled
    /\ claim.incomingLogicalAuthorityId = claim.logicalAuthorityId
    /\ cancelled' = TRUE
    /\ claim' = [claim EXCEPT !.cancelIdentityValid = TRUE]
    /\ failedClosed' = TRUE
    /\ result' = [result EXCEPT
        !.cancelRequested = TRUE,
        !.cancelProvenBeforeLaunch = (~result.launchAttempted /\ executionCount = 0),
        !.cancelDuringLaunchUncertainty =
            (result.launchAttempted /\ ~result.processResumed),
        !.cancelAppliedToKnownProcess =
            (result.processCreated \/ result.executionRunning \/ executionCount = 1),
        !.cancellationOutcomeKnown = (~result.launchAttempted /\ executionCount = 0),
        !.noExecutionProof = (~result.launchAttempted /\ executionCount = 0),
        !.launchReconciliation =
            (@ \/ (result.launchAttempted /\ ~result.processResumed)),
        !.outcomeKnown =
            IF ~result.launchAttempted /\ executionCount = 0 THEN TRUE ELSE @,
        !.outcome =
            IF ~result.launchAttempted /\ executionCount = 0
            THEN CancelledOutcome
            ELSE IF result.launchAttempted /\ ~result.processResumed
            THEN ReconciliationOutcome
            ELSE @
        ]
    /\ authorityQueue' =
        IF Len(authorityQueue) < AuthorityCapacity
        THEN Append(authorityQueue, CancelFrame)
        ELSE authorityQueue
    /\ authorityOverflow' =
        (authorityOverflow \/ (Len(authorityQueue) = AuthorityCapacity))
    /\ authorityFailureVisible' =
        (authorityFailureVisible \/ (Len(authorityQueue) = AuthorityCapacity))
    /\ UNCHANGED <<
        bulkQueue, reconciliationQueue, writer, transport, authorityBurst,
        executionCount, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

PresentForeignControl ==
    /\ ~cancelled
    /\ ~claim.foreignControlRejected
    /\ claim.incomingLogicalAuthorityId = claim.logicalAuthorityId
    /\ claim' = [claim EXCEPT
        !.incomingLogicalAuthorityId = IF claim.logicalAuthorityId = 1 THEN 2 ELSE 1,
        !.cancelIdentityValid = FALSE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

RejectForeignCancel ==
    /\ ~cancelled
    /\ claim.incomingLogicalAuthorityId # claim.logicalAuthorityId
    /\ ~claim.foreignControlRejected
    /\ claim' = [claim EXCEPT !.foreignControlRejected = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

ProduceBulk ==
    /\ bulkQueue < BulkCapacity
    /\ bulkQueue' = bulkQueue + 1
    /\ UNCHANGED <<
        authorityQueue, reconciliationQueue, writer, transport, authorityBurst,
        authorityOverflow, authorityFailureVisible, claim, failedClosed,
        executionCount, cancelled, result, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ProduceReconciliation ==
    /\ reconciliationChecks < MaxReconChecks
    /\ reconciliationReminderEvents < ReconCapacity
    /\ reconciliationQueue < ReconCapacity
    /\ reconciliationQueue' = reconciliationQueue + 1
    /\ reconciliationChecks' = reconciliationChecks + 1
    /\ reconciliationReminderEvents' = reconciliationReminderEvents + 1
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, writer, transport, authorityBurst,
        authorityOverflow, authorityFailureVisible, claim, failedClosed,
        executionCount, cancelled, result, staleGenerationSendRejected
        >>

LowerWorkQueued == reconciliationQueue > 0 \/ bulkQueue > 0

StartAuthority ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ writer.class = NoSend
    /\ Len(authorityQueue) > 0
    /\ authorityBurst < AuthorityBurstLimit \/ ~LowerWorkQueued
    /\ writer' = [
        class |-> AuthoritySend,
        frame |-> Head(authorityQueue),
        age |-> 0,
        generation |-> transport.generation
        ]
    /\ authorityQueue' = Tail(authorityQueue)
    /\ authorityBurst' =
        IF authorityBurst < AuthorityBurstLimit
        THEN authorityBurst + 1
        ELSE authorityBurst
    /\ transport' = [transport EXCEPT !.pendingRpc = TRUE]
    /\ UNCHANGED <<
        bulkQueue, reconciliationQueue, authorityOverflow,
        authorityFailureVisible, claim, failedClosed, executionCount,
        cancelled, result, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

StartReconciliation ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ writer.class = NoSend
    /\ reconciliationQueue > 0
    /\ Len(authorityQueue) = 0 \/ authorityBurst = AuthorityBurstLimit
    /\ writer' = [
        class |-> ReconciliationSend,
        frame |-> NoFrame,
        age |-> 0,
        generation |-> transport.generation
        ]
    /\ reconciliationQueue' = reconciliationQueue - 1
    /\ authorityBurst' = 0
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, transport, authorityOverflow,
        authorityFailureVisible, claim, failedClosed, executionCount,
        cancelled, result, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

StartBulk ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ writer.class = NoSend
    /\ bulkQueue > 0
    /\ reconciliationQueue = 0
    /\ Len(authorityQueue) = 0 \/ authorityBurst = AuthorityBurstLimit
    /\ writer' = [
        class |-> BulkSend,
        frame |-> NoFrame,
        age |-> 0,
        generation |-> transport.generation
        ]
    /\ bulkQueue' = bulkQueue - 1
    /\ authorityBurst' = 0
    /\ UNCHANGED <<
        authorityQueue, reconciliationQueue, transport, authorityOverflow,
        authorityFailureVisible, claim, failedClosed, executionCount,
        cancelled, result, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

AdvanceSend ==
    /\ transport.healthy
    /\ writer.class # NoSend
    /\ writer.age < SendBound
    /\ writer' = [writer EXCEPT !.age = @ + 1]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

CompleteSend ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ writer.class # NoSend
    /\ writer.age <= SendBound
    /\ writer' = [
        class |-> NoSend,
        frame |-> NoFrame,
        age |-> 0,
        generation |-> NoGeneration
        ]
    /\ transport' = [transport EXCEPT !.pendingRpc = FALSE]
    /\ claim' =
        IF writer.class = AuthoritySend /\ writer.frame = ClaimFrame
        THEN [claim EXCEPT
            !.sent = TRUE,
            !.sentGeneration = writer.generation
        ]
        ELSE claim
    /\ result' =
        IF writer.class = AuthoritySend /\ writer.frame = ResultFrame
        THEN [result EXCEPT
            !.sent = TRUE,
            !.awaitingReceipt = TRUE,
            !.sentGeneration = writer.generation,
            !.replayCount = IF @ < 3 THEN @ + 1 ELSE @
        ]
        ELSE result
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, authorityBurst,
        authorityOverflow, authorityFailureVisible, failedClosed, executionCount, cancelled,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

ReceiveClaim ==
    /\ claim.pending
    /\ claim.sent
    /\ ~claim.received
    /\ claim' = [claim EXCEPT !.received = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

PersistCanonicalClaim ==
    /\ claim.pending
    /\ claim.received
    /\ ~claim.persisted
    /\ claim' = [claim EXCEPT !.persisted = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

SendClaimAck ==
    /\ claim.persisted
    /\ ~claim.ackSent
    /\ claim' = [claim EXCEPT !.ackSent = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

SendDeadline ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ writer.class # NoSend
    /\ writer.age = SendBound
    /\ writer' = [
        class |-> NoSend,
        frame |-> NoFrame,
        age |-> 0,
        generation |-> NoGeneration
        ]
    /\ transport' = [transport EXCEPT
        !.healthy = FALSE,
        !.state = ClosingGeneration,
        !.activeGenerationCount = 0,
        !.pendingRpc = FALSE
        ]
    /\ authorityQueue' = <<>>
    /\ bulkQueue' = 0
    /\ reconciliationQueue' = 0
    /\ authorityBurst' = 0
    /\ authorityFailureVisible' =
        (authorityFailureVisible \/ (writer.class = AuthoritySend))
    /\ result' =
        IF writer.class = AuthoritySend /\ writer.frame = ResultFrame
        THEN [result EXCEPT !.awaitingReceipt = FALSE]
        ELSE result
    /\ claim' =
        IF writer.class = AuthoritySend /\ writer.frame = ClaimFrame
        THEN [claim EXCEPT !.queued = FALSE]
        ELSE claim
    /\ UNCHANGED <<
        authorityOverflow, failedClosed, executionCount, cancelled,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

ConnectionFailsAfterClaimSend ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ claim.sent
    /\ ~claim.received
    /\ transport' = [transport EXCEPT
        !.healthy = FALSE,
        !.state = ClosingGeneration,
        !.activeGenerationCount = 0,
        !.pendingRpc = FALSE
        ]
    /\ claim' = [claim EXCEPT
        !.queued = FALSE,
        !.sent = FALSE,
        !.sentGeneration = NoGeneration
        ]
    /\ authorityQueue' = <<>>
    /\ bulkQueue' = 0
    /\ reconciliationQueue' = 0
    /\ authorityBurst' = 0
    /\ UNCHANGED <<
        writer, authorityOverflow, authorityFailureVisible, failedClosed,
        executionCount, cancelled, result, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

QuiesceGeneration ==
    /\ transport.state = ClosingGeneration
    /\ transport.cooperative
    /\ transport' = [transport EXCEPT
        !.state = QuiescedGeneration,
        !.tasks = 0,
        !.pendingRpc = FALSE,
        !.pumpActive = FALSE,
        !.pumpActiveCount = 0,
        !.pumpGeneration = NoGeneration,
        !.connectionAActive = FALSE,
        !.connectionBActive = FALSE,
        !.pumpAActive = FALSE,
        !.pumpBActive = FALSE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, authorityBurst,
        authorityOverflow, authorityFailureVisible, claim, failedClosed,
        executionCount, cancelled, result, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

GenerationTeardownFailure ==
    /\ transport.state = ClosingGeneration
    /\ ~transport.cooperative
    /\ transport' = [transport EXCEPT
        !.state = FailedGeneration,
        !.healthy = FALSE,
        !.activeGenerationCount = 0,
        !.tasks = 0,
        !.pendingRpc = FALSE,
        !.pumpActive = FALSE,
        !.pumpActiveCount = 0,
        !.pumpGeneration = NoGeneration,
        !.connectionAActive = FALSE,
        !.connectionBActive = FALSE,
        !.pumpAActive = FALSE,
        !.pumpBActive = FALSE
        ]
    /\ failedClosed' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, authorityBurst,
        authorityOverflow, authorityFailureVisible, claim, executionCount,
        cancelled, result, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

Reconnect ==
    /\ transport.state = QuiescedGeneration
    /\ transport.generation < MaxTransportGeneration
    /\ transport.activeGenerationCount = 0
    /\ ~transport.pumpActive
    /\ transport.pumpActiveCount = 0
    /\ transport' = [transport EXCEPT
        !.healthy = TRUE,
        !.generation = @ + 1,
        !.state = ActiveGeneration,
        !.activeGenerationCount = @ + 1,
        !.tasks = MaxGenerationTasks,
        !.pendingRpc = FALSE,
        !.reconnectWasQuiescent = TRUE,
        !.pumpActive = TRUE,
        !.pumpActiveCount = @ + 1,
        !.pumpGeneration = transport.generation + 1,
        !.connectionAActive = ((transport.generation + 1) % 2 = 0),
        !.connectionBActive = ((transport.generation + 1) % 2 = 1),
        !.pumpAActive = ((transport.generation + 1) % 2 = 0),
        !.pumpBActive = ((transport.generation + 1) % 2 = 1)
        ]
    /\ result' =
        IF result.retained /\ ~result.acknowledged
        THEN [result EXCEPT
            !.awaitingReceipt = FALSE,
            !.sentGeneration = NoGeneration,
            !.receiptHealthy = TRUE
        ]
        ELSE [result EXCEPT !.receiptHealthy = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, authorityBurst,
        authorityOverflow, authorityFailureVisible, claim, failedClosed,
        executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveClaimAck ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ claim.pending
    /\ claim.persisted
    /\ claim.ackSent
    /\ claim.ackHealthy
    /\ (~EnforceAckExchangeBinding \/
        (claim.sentGeneration = transport.generation /\
         claim.incomingAckGeneration = transport.generation /\
         claim.incomingAckExchangeId = claim.ackExchangeId /\
         claim.incomingAckRequestId = claim.requestIdentityId /\
         claim.incomingAckClaimId = claim.claimIdentityId /\
         claim.incomingAckExecutionId = claim.executionIdentityId /\
         claim.incomingAckMessageId = claim.ackMessageId))
    /\ ~claim.proven
    /\ ~failedClosed
    /\ ~cancelled
    /\ claim' = [claim EXCEPT
        !.proven = TRUE,
        !.proofSource = AckProof,
        !.proofGeneration = claim.sentGeneration,
        !.proofLogicalAuthorityId = claim.logicalAuthorityId,
        !.proofExchangeId = claim.ackExchangeId,
        !.proofRequestId = claim.incomingAckRequestId,
        !.proofClaimId = claim.incomingAckClaimId,
        !.proofExecutionId = claim.incomingAckExecutionId,
        !.proofMessageId = claim.incomingAckMessageId
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

StartNewClaimExchange ==
    /\ claim.persisted
    /\ claim.ackSent
    /\ ~claim.proven
    /\ claim.ackExchangeId = 1
    /\ claim' = [claim EXCEPT
        !.ackExchangeId = 2,
        !.ackMessageId = 2,
        !.staleAckRejected = FALSE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

PresentCurrentExchangeAck ==
    /\ claim.persisted
    /\ claim.ackSent
    /\ ~claim.proven
    /\ (claim.incomingAckExchangeId # claim.ackExchangeId \/
        claim.incomingAckGeneration # transport.generation)
    /\ claim' = [claim EXCEPT
        !.incomingAckExchangeId = claim.ackExchangeId,
        !.incomingAckGeneration = transport.generation,
        !.incomingAckRequestId = claim.requestIdentityId,
        !.incomingAckClaimId = claim.claimIdentityId,
        !.incomingAckExecutionId = claim.executionIdentityId,
        !.incomingAckMessageId = claim.ackMessageId
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

HttpReadback ==
    /\ claim.pending
    /\ claim.persisted
    /\ claim.readbackHealthy
    /\ ~claim.proven
    /\ ~failedClosed
    /\ ~cancelled
    /\ claim' = [claim EXCEPT
        !.proven = TRUE,
        !.proofSource = ReadbackProof,
        !.proofGeneration = NoGeneration,
        !.proofLogicalAuthorityId = claim.logicalAuthorityId
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

FailClaimClosed ==
    /\ claim.pending
    /\ ~claim.proven
    /\ ~failedClosed
    /\ ~claim.ackHealthy
    /\ ~claim.readbackHealthy
    /\ failedClosed' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        executionCount, cancelled, result, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

PersistShellLaunchIntent ==
    /\ claim.proven
    /\ executionCount = 0
    /\ ~result.launchIntentPersisted
    /\ result' = [result EXCEPT !.launchIntentPersisted = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

AttemptShellLaunch ==
    /\ result.launchIntentPersisted
    /\ ~result.launchAttempted
    /\ executionCount = 0
    /\ ~cancelled
    /\ result' = [result EXCEPT !.launchAttempted = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

CreateShellProcess ==
    /\ (result.launchAttempted \/
        (~EnforcePreLaunchCancellation /\ result.cancelProvenBeforeLaunch))
    /\ ~result.processCreated
    /\ ~result.launchReconciliation
    /\ executionCount = 0
    /\ (~EnforcePreLaunchCancellation \/
        (~cancelled /\ ~result.cancelProvenBeforeLaunch))
    /\ result' = [result EXCEPT
        !.processCreated = TRUE,
        !.processCreationCount = @ + 1
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

AssignShellJob ==
    /\ result.processCreated
    /\ ~result.jobAssigned
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT !.jobAssigned = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

VerifyShellJobMembership ==
    /\ result.jobAssigned
    /\ ~result.jobMembershipVerified
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT !.jobMembershipVerified = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

PersistShellProcessIdentity ==
    /\ result.jobMembershipVerified
    /\ ~result.processIdentityPersisted
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT !.processIdentityPersisted = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ResumeShellProcess ==
    /\ result.processIdentityPersisted
    /\ ~result.processResumed
    /\ result.resumeResult = NoResumeResult
    /\ ~result.launchReconciliation
    /\ ~cancelled
    /\ result' = [result EXCEPT
        !.processResumed = TRUE,
        !.suspendState = ResumedState,
        !.resumeResult = ExpectedResumeResult,
        !.suspendObservation = ExpectedResumeObservation
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveSnapshotFailure ==
    /\ result.processIdentityPersisted
    /\ result.resumeResult = NoResumeResult
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.suspendState =
            IF EnforceSnapshotObservationTruth THEN UnknownSuspendState ELSE SuspendedState,
        !.resumeResult = FailedResumeResult,
        !.suspendObservation = SnapshotFailureObservation,
        !.resumeAmbiguous = TRUE,
        !.launchReconciliation = TRUE,
        !.outcome = ReconciliationOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveOpenThreadFailure ==
    /\ result.processIdentityPersisted
    /\ result.resumeResult = NoResumeResult
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.suspendState =
            IF EnforceOpenThreadObservationTruth THEN UnknownSuspendState ELSE SuspendedState,
        !.resumeResult = FailedResumeResult,
        !.suspendObservation = OpenThreadFailureObservation,
        !.resumeAmbiguous = TRUE,
        !.launchReconciliation = TRUE,
        !.outcome = ReconciliationOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveUnexpectedResumeZero ==
    /\ result.processIdentityPersisted
    /\ result.resumeResult = NoResumeResult
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.suspendState =
            IF EnforceResumeResultContract THEN UnknownSuspendState ELSE ResumedState,
        !.resumeResult = UnexpectedResumeResult,
        !.suspendObservation = UnexpectedZeroObservation,
        !.processResumed = IF EnforceResumeResultContract THEN FALSE ELSE TRUE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveUnexpectedResumeMultiple ==
    /\ result.processIdentityPersisted
    /\ result.resumeResult = NoResumeResult
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.suspendState = SuspendedState,
        !.resumeResult = UnexpectedResumeResult,
        !.suspendObservation = UnexpectedMultipleObservation
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveResumeFailure ==
    /\ result.processIdentityPersisted
    /\ result.resumeResult = NoResumeResult
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.suspendState = UnknownSuspendState,
        !.resumeResult = FailedResumeResult,
        !.suspendObservation = ResumeFailureObservation,
        !.resumeAmbiguous = TRUE,
        !.launchReconciliation = TRUE,
        !.outcome = ReconciliationOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveExistingRunningAfterUnexpectedResume ==
    /\ result.resumeResult = UnexpectedResumeResult
    /\ result.suspendObservation = UnexpectedZeroObservation
    /\ result.suspendState = UnknownSuspendState
    /\ ~result.processResumed
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.suspendState = ResumedState,
        !.suspendObservation = ExistingRunningObservation,
        !.processResumed = TRUE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ReconcileUnknownResume ==
    /\ result.resumeResult \in {UnexpectedResumeResult, FailedResumeResult}
    /\ result.suspendState = UnknownSuspendState
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.resumeAmbiguous = TRUE,
        !.launchReconciliation = TRUE,
        !.outcome = ReconciliationOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

AttemptUnexpectedResumeRelaunch ==
    /\ result.resumeResult = UnexpectedResumeResult
    /\ result.processCreated
    /\ result.processCreationCount = 1
    /\ ~result.duplicateLaunchRejected
    /\ result' = [result EXCEPT
        !.duplicateLaunchRejected = EnforceUnexpectedResumeNoRelaunch,
        !.processCreationCount =
            IF EnforceUnexpectedResumeNoRelaunch THEN @ ELSE @ + 1
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

TerminalizeUnknownResume ==
    /\ result.resumeResult \in {UnexpectedResumeResult, FailedResumeResult}
    /\ result.suspendState = UnknownSuspendState
    /\ ~result.retained
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.launchReconciliation = EnforceUnknownSuspendTerminalGuard,
        !.outcome =
            IF EnforceUnknownSuspendTerminalGuard
            THEN ReconciliationOutcome ELSE FailedOutcome,
        !.retained = IF EnforceUnknownSuspendTerminalGuard THEN FALSE ELSE TRUE,
        !.logicalId = IF EnforceUnknownSuspendTerminalGuard THEN @ ELSE 1,
        !.outcomeKnown = IF EnforceUnknownSuspendTerminalGuard THEN @ ELSE TRUE,
        !.cleanupComplete = TRUE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveAmbiguousResume ==
    /\ result.processIdentityPersisted
    /\ ~result.processResumed
    /\ ~result.resumeAmbiguous
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.resumeAmbiguous = TRUE,
        !.launchReconciliation = TRUE,
        !.outcome = ReconciliationOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

AdmitShellRunning ==
    /\ result.processResumed
    /\ result.suspendState = ResumedState
    /\ ~result.shellRunning
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT !.shellRunning = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

CrashDuringUncertainShellLaunch ==
    /\ result.launchAttempted
    /\ ~result.processIdentityPersisted
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.launchReconciliation = TRUE,
        !.outcome = ReconciliationOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

RejectDuplicateShellLaunch ==
    /\ result.launchReconciliation
    /\ ~result.duplicateLaunchRejected
    /\ result' = [result EXCEPT !.duplicateLaunchRejected = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

Execute ==
    /\ transport.state = ActiveGeneration
    /\ claim.proven
    /\ ~failedClosed
    /\ ~cancelled
    /\ executionCount = 0
    /\ (~result.launchIntentPersisted \/ result.shellRunning)
    /\ executionCount' = 1
    /\ result' = [result EXCEPT
        !.executionRunning = TRUE,
        !.outcome = RunningOutcome,
        !.observerPresent = TRUE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveCompleteCleanup ==
    /\ result.executionRunning
    /\ ~result.cleanupComplete
    /\ result' = [result EXCEPT !.cleanupComplete = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

CanTerminalize ==
    (result.cleanupComplete \/ result.noExecutionProof)
    /\ (~EnforceLaunchUncertaintyTerminalGuard \/ ~result.launchReconciliation)
    /\ ~result.terminalAdmissibilityRejected

ObserveLaunchUncertaintyDuringExecution ==
    /\ result.executionRunning
    /\ ~result.launchReconciliation
    /\ result' = [result EXCEPT
        !.launchReconciliation = TRUE,
        !.outcome = ReconciliationOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

RejectIncompleteTerminalization ==
    /\ result.executionRunning
    /\ ~result.cleanupComplete
    /\ ~result.terminalAdmissibilityRejected
    /\ result' = [result EXCEPT
        !.terminalAdmissibilityRejected = TRUE,
        !.launchReconciliation = TRUE,
        !.outcome = ReconciliationOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ProduceSucceededTerminalResult ==
    /\ executionCount = 1
    /\ result.executionRunning
    /\ ~result.retained
    /\ (~EnforceTerminalCleanup \/ CanTerminalize)
    /\ result' = [result EXCEPT
        !.retained = TRUE,
        !.logicalId = 1,
        !.executionRunning = FALSE,
        !.outcomeKnown = TRUE,
        !.outcome = SucceededOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ProduceFailedTerminalResult ==
    /\ executionCount = 1
    /\ result.executionRunning
    /\ ~result.retained
    /\ (~EnforceTerminalCleanup \/ CanTerminalize)
    /\ result' = [result EXCEPT
        !.retained = TRUE,
        !.logicalId = 1,
        !.executionRunning = FALSE,
        !.outcomeKnown = TRUE,
        !.outcome = FailedOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ProduceCancelledTerminalResult ==
    /\ executionCount = 1
    /\ result.executionRunning
    /\ ~result.retained
    /\ result.cancelAppliedToKnownProcess
    /\ (~EnforceTerminalCleanup \/ CanTerminalize)
    /\ result' = [result EXCEPT
        !.retained = TRUE,
        !.logicalId = 1,
        !.executionRunning = FALSE,
        !.outcomeKnown = TRUE,
        !.outcome = CancelledOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

LoseExecutionObserver ==
    /\ executionCount = 1
    /\ result.executionRunning
    /\ result.observerPresent
    /\ ~result.retained
    /\ result' = [result EXCEPT
        !.observerPresent = FALSE,
        !.outcome = ReconciliationOutcome
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ProduceTerminalResult ==
    ProduceSucceededTerminalResult
    \/ ProduceFailedTerminalResult
    \/ ProduceCancelledTerminalResult

ValidateResultIdentity ==
    /\ result.retained
    /\ ~result.identityValid
    /\ ~result.conflict
    /\ result' = [result EXCEPT !.identityValid = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

AcceptCanonicalResult ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ result.retained
    /\ result.sent
    /\ result.awaitingReceipt
    /\ result.identityValid
    /\ result.sentGeneration = transport.generation
    /\ ~result.accepted
    /\ ~result.conflict
    /\ result' = [result EXCEPT !.accepted = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveResultReceipt ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ result.retained
    /\ result.accepted
    /\ result.awaitingReceipt
    /\ result.receiptHealthy
    /\ result.sentGeneration = transport.generation
    /\ result' = [result EXCEPT
        !.acknowledged = TRUE,
        !.awaitingReceipt = FALSE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ResultReceiptConflict ==
    /\ result.retained
    /\ result.sent
    /\ result.awaitingReceipt
    /\ ~result.identityValid
    /\ ~result.conflict
    /\ result' = [result EXCEPT
        !.conflict = TRUE,
        !.reconciliation = TRUE,
        !.awaitingReceipt = FALSE
        ]
    /\ failedClosed' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

ResultReceiptTimeout ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ result.retained
    /\ result.awaitingReceipt
    /\ ~result.receiptHealthy
    /\ result' = [result EXCEPT !.awaitingReceipt = FALSE]
    /\ transport' = [transport EXCEPT
        !.healthy = FALSE,
        !.state = ClosingGeneration,
        !.activeGenerationCount = 0,
        !.pendingRpc = FALSE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, authorityBurst,
        authorityOverflow, authorityFailureVisible, claim, failedClosed,
        executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

StaleGenerationHandlerAttempt ==
    /\ transport.generation > 0
    /\ transport.state = ActiveGeneration
    /\ ~staleGenerationSendRejected
    /\ staleGenerationSendRejected' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, result,
        reconciliationChecks, reconciliationReminderEvents
        >>

PresentStaleAck ==
    /\ claim.incomingAckExchangeId = claim.ackExchangeId
    /\ ~claim.proven
    /\ claim' = [claim EXCEPT
        !.incomingAckExchangeId = IF claim.ackExchangeId = 1 THEN 2 ELSE 1,
        !.incomingAckGeneration =
            IF transport.generation = 0 THEN MaxTransportGeneration ELSE 0,
        !.incomingAckMessageId = IF claim.ackMessageId = 1 THEN 2 ELSE 1
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

RejectStaleAck ==
    /\ (claim.incomingAckExchangeId # claim.ackExchangeId \/
        claim.incomingAckGeneration # transport.generation \/
        claim.incomingAckRequestId # claim.requestIdentityId \/
        claim.incomingAckClaimId # claim.claimIdentityId \/
        claim.incomingAckExecutionId # claim.executionIdentityId \/
        claim.incomingAckMessageId # claim.ackMessageId)
    /\ ~claim.staleAckRejected
    /\ claim' = [claim EXCEPT !.staleAckRejected = TRUE]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer, transport,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

ConnectionFailsDuringExecution ==
    /\ transport.healthy
    /\ transport.state = ActiveGeneration
    /\ result.executionRunning
    /\ ~result.outcomeKnown
    /\ transport' = [transport EXCEPT
        !.healthy = FALSE,
        !.state = ClosingGeneration,
        !.activeGenerationCount = 0,
        !.pendingRpc = FALSE
        ]
    /\ result' = [result EXCEPT !.connectionLossObserved = TRUE]
    /\ authorityQueue' = <<>>
    /\ bulkQueue' = 0
    /\ reconciliationQueue' = 0
    /\ authorityBurst' = 0
    /\ UNCHANGED <<
        writer, authorityOverflow, authorityFailureVisible, claim, failedClosed,
        executionCount, cancelled, staleGenerationSendRejected,
        reconciliationChecks, reconciliationReminderEvents
        >>

AttemptConnectionGenerationOverlap ==
    /\ transport.state = ActiveGeneration
    /\ ~transport.connectionOverlapAttempted
    /\ transport' = [transport EXCEPT
        !.connectionOverlapAttempted = TRUE,
        !.activeGenerationCount =
            IF EnforceConnectionSingleton THEN @ ELSE @ + 1,
        !.connectionAActive = TRUE,
        !.connectionBActive = IF EnforceConnectionSingleton THEN FALSE ELSE TRUE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

AttemptPumpGenerationOverlap ==
    /\ transport.pumpActive
    /\ ~transport.pumpOverlapAttempted
    /\ transport' = [transport EXCEPT
        !.pumpOverlapAttempted = TRUE,
        !.pumpActiveCount = IF EnforcePumpSingleton THEN @ ELSE @ + 1,
        !.pumpAActive = TRUE,
        !.pumpBActive = IF EnforcePumpSingleton THEN FALSE ELSE TRUE
        ]
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, writer,
        authorityBurst, authorityOverflow, authorityFailureVisible, claim,
        failedClosed, executionCount, cancelled, result,
        staleGenerationSendRejected, reconciliationChecks,
        reconciliationReminderEvents
        >>

WriterStart == StartAuthority \/ StartReconciliation \/ StartBulk
SendProgress == AdvanceSend \/ CompleteSend \/ SendDeadline
AuthorityAdmission ==
    QueueClaim \/ ClaimAuthorityOverflow \/ QueueRetainedResult
    \/ ResultAuthorityOverflow \/ RequestCancel \/ PresentForeignControl
    \/ RejectForeignCancel
ClaimTransportProgress == ReceiveClaim \/ PersistCanonicalClaim \/ SendClaimAck
GenerationLifecycle ==
    ConnectionFailsAfterClaimSend \/ QuiesceGeneration
    \/ ConnectionFailsDuringExecution
    \/ GenerationTeardownFailure \/ Reconnect
    \/ AttemptConnectionGenerationOverlap \/ AttemptPumpGenerationOverlap
ShellLaunchProgress ==
    PersistShellLaunchIntent \/ AttemptShellLaunch \/ CreateShellProcess
    \/ AssignShellJob \/ VerifyShellJobMembership
    \/ PersistShellProcessIdentity \/ ResumeShellProcess
    \/ ObserveSnapshotFailure \/ ObserveOpenThreadFailure
    \/ ObserveUnexpectedResumeZero \/ ObserveUnexpectedResumeMultiple
    \/ ObserveResumeFailure \/ ObserveExistingRunningAfterUnexpectedResume
    \/ ReconcileUnknownResume \/ AttemptUnexpectedResumeRelaunch
    \/ TerminalizeUnknownResume \/ ObserveAmbiguousResume
    \/ AdmitShellRunning
    \/ CrashDuringUncertainShellLaunch \/ RejectDuplicateShellLaunch

Next ==
    AuthorityAdmission
    \/ ProduceBulk
    \/ ProduceReconciliation
    \/ WriterStart
    \/ SendProgress
    \/ ClaimTransportProgress
    \/ GenerationLifecycle
    \/ ObserveClaimAck
    \/ StartNewClaimExchange
    \/ PresentCurrentExchangeAck
    \/ HttpReadback
    \/ FailClaimClosed
    \/ ShellLaunchProgress
    \/ Execute
    \/ ObserveCompleteCleanup
    \/ ObserveLaunchUncertaintyDuringExecution
    \/ RejectIncompleteTerminalization
    \/ ProduceTerminalResult
    \/ LoseExecutionObserver
    \/ ValidateResultIdentity
    \/ AcceptCanonicalResult
    \/ ObserveResultReceipt
    \/ ResultReceiptConflict
    \/ ResultReceiptTimeout
    \/ StaleGenerationHandlerAttempt
    \/ PresentStaleAck \/ RejectStaleAck

Spec ==
    /\ Init
    /\ [][Next]_vars
    /\ WF_vars(QueueClaim)
    /\ WF_vars(QueueRetainedResult)
    /\ WF_vars(WriterStart)
    /\ WF_vars(SendProgress)
    /\ WF_vars(ReceiveClaim)
    /\ WF_vars(PersistCanonicalClaim)
    /\ WF_vars(SendClaimAck)
    /\ WF_vars(QuiesceGeneration)
    /\ WF_vars(Reconnect)
    /\ WF_vars(ObserveClaimAck)
    /\ WF_vars(HttpReadback)
    /\ WF_vars(FailClaimClosed)
    /\ WF_vars(Execute)
    /\ WF_vars(ProduceTerminalResult)
    /\ WF_vars(AcceptCanonicalResult)
    /\ WF_vars(ObserveResultReceipt)
    /\ WF_vars(ResultReceiptConflict)

AuthorityQueueIsBounded == Len(authorityQueue) <= AuthorityCapacity

AuthorityOverflowNeverSilentlyDropsAuthority ==
    authorityOverflow => authorityFailureVisible

NoExecutionWithoutCanonicalAuthority == executionCount > 0 => claim.proven

TransportFailureCannotAuthorizeExecution ==
    (~transport.healthy /\ ~claim.proven) => executionCount = 0

BothObservationPathsUnavailableNeverAllowsRunning ==
    (claim.pending /\ ~claim.ackHealthy /\ ~claim.readbackHealthy) =>
        executionCount = 0

CancellationSafetyPreserved ==
    /\ (result.cancelProvenBeforeLaunch =>
        (~result.processCreated /\ executionCount = 0 /\ result.outcome = CancelledOutcome))
    /\ (result.cancelDuringLaunchUncertainty =>
        (result.launchReconciliation /\ ~result.shellRunning /\
         result.outcome = ReconciliationOutcome))

JobContainmentPrecedesResume ==
    result.processResumed =>
        (result.jobAssigned /\ result.jobMembershipVerified /\
         result.processIdentityPersisted)

PreLaunchCancellationPreventsProcessCreation ==
    result.cancelProvenBeforeLaunch => ~result.processCreated

ConnectionFailureCannotPublishFalseFailure ==
    result.executionRunning =>
        (~result.outcomeKnown /\ ~result.retained /\
         result.outcome \in {RunningOutcome, ReconciliationOutcome})

ConnectionLossDoesNotTerminateExecution ==
    (result.connectionLossObserved /\ ~result.outcomeKnown) => result.executionRunning

ActualExecutionOutcomeDeterminesTerminalState ==
    result.retained => (result.outcomeKnown /\ ~result.executionRunning)

ReconciliationProductionIsBounded ==
    reconciliationReminderEvents <= ReconCapacity

AckProofUsesExactLogicalAuthority ==
    (claim.proven /\ claim.proofSource = AckProof) =>
        claim.proofLogicalAuthorityId = claim.logicalAuthorityId

AuthorityOverflowCannotPermitRunning ==
    (authorityOverflow /\ claim.pending /\ ~claim.proven) => executionCount = 0

AtMostOneActiveConnectionGeneration ==
    /\ transport.activeGenerationCount <= 1
    /\ (transport.state = ActiveGeneration) = (transport.activeGenerationCount = 1)
    /\ ~(transport.connectionAActive /\ transport.connectionBActive)

AtMostOneDurablePumpGeneration ==
    /\ transport.pumpActiveCount <= 1
    /\ transport.pumpActive = (transport.pumpActiveCount = 1)
    /\ transport.pumpActive =>
        (transport.pumpGeneration = transport.generation /\
         transport.state \in {ActiveGeneration, ClosingGeneration})
    /\ ~(transport.pumpAActive /\ transport.pumpBActive)

DurablePumpQuiescedBeforeReplacement ==
    transport.state \in {QuiescedGeneration, FailedGeneration} =>
        ~transport.pumpActive

ReplacementGenerationRequiresPriorGenerationQuiescence ==
    transport.generation > 0 => transport.reconnectWasQuiescent

OldGenerationCannotSendOnNewGeneration ==
    staleGenerationSendRejected => transport.generation > 0

StaleAckCannotSatisfyNewGeneration ==
    (claim.proven /\ claim.proofSource = AckProof) =>
        /\ claim.proofLogicalAuthorityId = claim.logicalAuthorityId
        /\ claim.proofGeneration = transport.generation
        /\ claim.proofExchangeId = claim.ackExchangeId
        /\ claim.proofRequestId = claim.requestIdentityId
        /\ claim.proofClaimId = claim.claimIdentityId
        /\ claim.proofExecutionId = claim.executionIdentityId
        /\ claim.proofMessageId = claim.ackMessageId

StaleAckForNewExchangeCannotProveAuthority ==
    (claim.incomingAckExchangeId # claim.ackExchangeId \/
     claim.incomingAckGeneration # transport.generation \/
     claim.incomingAckRequestId # claim.requestIdentityId \/
     claim.incomingAckClaimId # claim.claimIdentityId \/
     claim.incomingAckExecutionId # claim.executionIdentityId \/
     claim.incomingAckMessageId # claim.ackMessageId) =>
        (~claim.proven \/ claim.proofSource # AckProof)

OrdinaryTerminalRequiresAdmissibility ==
    result.retained => (result.cleanupComplete \/ result.noExecutionProof)

TerminalCleanupGateRejectsUnknown ==
    result.terminalAdmissibilityRejected => ~result.retained

LaunchUncertaintyCannotTerminalize ==
    result.launchReconciliation => ~result.retained

ReconnectDoesNotInvalidateProvenLogicalAuthority ==
    claim.proven => claim.proofLogicalAuthorityId = claim.logicalAuthorityId

ForeignClaimCannotCancelActiveExecution ==
    claim.foreignControlRejected => ~cancelled

ClaimSendDoesNotImplyCanonicalPersistence ==
    claim.persisted => (claim.sent /\ claim.received)

ClaimSendCompletionCannotAuthorizeExecution ==
    (claim.sent /\ ~claim.persisted) => executionCount = 0

PendingRpcFailsWhenGenerationCloses ==
    transport.state # ActiveGeneration => ~transport.pendingRpc

TerminalResultSurvivesConnectionFailure ==
    [](result.retained => [](result.retained))

TerminalReplayDoesNotReexecute == executionCount <= 1

AcceptedTerminalResultIsIdempotent ==
    result.accepted => result.logicalId = 1

TransportSendDoesNotImplyCanonicalAcceptance ==
    result.accepted => (result.sent /\ result.identityValid)

ExecutionOutcomeIsMonotonic ==
    /\ [](result.outcome = SucceededOutcome => [](result.outcome = SucceededOutcome))
    /\ [](result.outcome = FailedOutcome => [](result.outcome = FailedOutcome))
    /\ [](result.outcome = CancelledOutcome => [](result.outcome = CancelledOutcome))

KnownSuccessCannotBecomeFailure ==
    [](result.outcome = SucceededOutcome => [](result.outcome = SucceededOutcome))

KnownOutcomeCannotBecomeUnknown ==
    result.outcomeKnown => result.outcome # UnknownOutcome

ObserverLossCannotFabricateTerminalState ==
    /\ result.executionRunning => result.outcome = RunningOutcome
    /\ ~result.observerPresent => result.outcome = ReconciliationOutcome

ShellRunningRequiresPersistedProcessIdentity ==
    result.shellRunning =>
        /\ result.launchIntentPersisted
        /\ result.launchAttempted
        /\ result.processCreated
        /\ result.processIdentityPersisted

UncertainShellLaunchCannotExecuteOrRelaunch ==
    result.launchReconciliation =>
        /\ ~result.shellRunning
        /\ executionCount = 0

ObservationFailureCannotProveSuspended ==
    result.suspendObservation \in {
        SnapshotFailureObservation,
        OpenThreadFailureObservation
    } => result.suspendState = UnknownSuspendState

UnexpectedResumeCannotEstablishRunning ==
    (result.resumeResult = UnexpectedResumeResult /\ result.shellRunning) =>
        /\ result.suspendState = ResumedState
        /\ result.suspendObservation = ExistingRunningObservation

UnknownLaunchStateCannotTerminalizeFailed ==
    (result.resumeResult # NoResumeResult /\
     result.suspendState = UnknownSuspendState) =>
        ~(result.retained /\ result.outcome = FailedOutcome)

UnknownLaunchStateCannotTerminalizeCancelled ==
    (result.resumeResult # NoResumeResult /\
     result.suspendState = UnknownSuspendState) =>
        ~(result.retained /\ result.outcome = CancelledOutcome)

ExpectedResumeAfterProvenSuspendedMayProgress ==
    result.resumeResult = ExpectedResumeResult =>
        /\ result.suspendState = ResumedState
        /\ result.processResumed

UnexpectedResumeCannotCauseRelaunch ==
    result.resumeResult = UnexpectedResumeResult => result.processCreationCount = 1

AtMostOneProcessCreation == result.processCreationCount <= 1

CentralTerminalizationRequiresKnownLaunchTruth ==
    (result.retained /\ result.launchAttempted /\
     result.resumeResult # NoResumeResult) =>
        result.suspendState # UnknownSuspendState

ForeignClaimCannotMutateExecution ==
    claim.incomingLogicalAuthorityId # claim.logicalAuthorityId => ~cancelled

StableResultIdentityRequiredForAcceptance ==
    result.accepted => result.identityValid

ConflictingResultEntersReconciliation ==
    result.conflict => result.reconciliation

LostResultAckDoesNotLoseTerminalEvidence ==
    (result.accepted /\ ~result.acknowledged) => result.retained

ConflictingTerminalResultFailsClosed == result.conflict => failedClosed

ResultTransportFailureCannotEraseResult ==
    (~transport.healthy /\ result.logicalId = 1) => result.retained

BulkTrafficCannotStarveAuthority ==
    []((transport.healthy /\ Len(authorityQueue) > 0) =>
        <>(Len(authorityQueue) = 0 \/ ~transport.healthy))

InFlightBulkSendEitherCompletesOrTransportFailsWithinBound ==
    []((transport.healthy /\ writer.class = BulkSend) =>
        <>(writer.class # BulkSend \/ ~transport.healthy))

QueuedAuthorityEventuallyServicedUnderHealthyTransport ==
    []((transport.healthy /\ Len(authorityQueue) > 0) =>
        <>(Len(authorityQueue) = 0 \/ authorityFailureVisible \/ ~transport.healthy))

PersistedClaimEventuallyObservedViaAckOrReadbackUnderHealthyPaths ==
    []((claim.pending /\ claim.persisted /\
        (claim.ackHealthy \/ claim.readbackHealthy)) =>
        <>(claim.proven \/ failedClosed \/ ~transport.healthy))

PendingTerminalResultEventuallyReplayedAfterHealthyReconnect ==
    []((transport.healthy /\ transport.state = ActiveGeneration /\
        result.retained /\ ~result.acknowledged /\ result.receiptHealthy /\
        ~result.conflict) =>
        <>(result.acknowledged \/ result.conflict \/ ~transport.healthy))

GenerationTasksEventuallyQuiesceUnderCooperativeTasks ==
    []((transport.state = ClosingGeneration /\ transport.cooperative) =>
        <>(transport.state = QuiescedGeneration))

DurablePumpEventuallyQuiescesOnShutdown ==
    []((transport.state = ClosingGeneration /\ transport.cooperative) =>
        <>~transport.pumpActive)

SafetyNeverDependsOnLivenessSuccess == []((~claim.proven) => (executionCount = 0))

====
