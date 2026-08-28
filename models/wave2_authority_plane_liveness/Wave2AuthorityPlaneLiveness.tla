---- MODULE Wave2AuthorityPlaneLiveness ----
EXTENDS Naturals, TLC

(*
Small Wave 2 liveness model for the node transport writer.

Scope:
- one serialized WebSocket writer;
- explicit authority, reconciliation, ordinary, and bulk/media work classes;
- active claim/result authority traffic receives service ahead of backlog;
- HTTP claim readback is an independent authority observation path;
- reconciliation reminders are bounded and cannot starve active authority.

The model intentionally abstracts away DurableRemote request material safety.
Those invariants remain in models/wave2_durable_remote/Wave2DurableRemote.tla.
*)

CONSTANT MaxBulkBacklog, MaxReconBacklog, MaxReconChecks

VARIABLES
    authorityQueued,
    resultQueued,
    requiredQueued,
    bulkBacklog,
    reconciliationBacklog,
    writerLive,
    claimPending,
    claimAckPending,
    readbackHealthy,
    authorityServiced,
    resultServiced,
    authorityProven,
    readbackObserved,
    failedClosed,
    executed,
    reconciliationChecks,
    reconciliationReminderEvents

vars == <<
    authorityQueued,
    resultQueued,
    requiredQueued,
    bulkBacklog,
    reconciliationBacklog,
    writerLive,
    claimPending,
    claimAckPending,
    readbackHealthy,
    authorityServiced,
    resultServiced,
    authorityProven,
    readbackObserved,
    failedClosed,
    executed,
    reconciliationChecks,
    reconciliationReminderEvents
>>

Init ==
    /\ authorityQueued \in BOOLEAN
    /\ resultQueued \in BOOLEAN
    /\ requiredQueued \in BOOLEAN
    /\ bulkBacklog \in 0..MaxBulkBacklog
    /\ reconciliationBacklog \in 0..MaxReconBacklog
    /\ writerLive = TRUE
    /\ claimPending \in BOOLEAN
    /\ claimAckPending \in BOOLEAN
    /\ readbackHealthy \in BOOLEAN
    /\ authorityServiced = FALSE
    /\ resultServiced = FALSE
    /\ authorityProven = FALSE
    /\ readbackObserved = FALSE
    /\ failedClosed = FALSE
    /\ executed = FALSE
    /\ reconciliationChecks = 0
    /\ reconciliationReminderEvents = 0

SendAuthority ==
    /\ writerLive
    /\ authorityQueued
    /\ authorityQueued' = FALSE
    /\ authorityServiced' = TRUE
    /\ authorityProven' = authorityProven \/ claimAckPending
    /\ UNCHANGED <<
        resultQueued, requiredQueued, bulkBacklog, reconciliationBacklog,
        writerLive, claimPending, claimAckPending, readbackHealthy,
        resultServiced, readbackObserved, failedClosed, executed,
        reconciliationChecks, reconciliationReminderEvents
    >>

SendResult ==
    /\ writerLive
    /\ resultQueued
    /\ resultQueued' = FALSE
    /\ resultServiced' = TRUE
    /\ UNCHANGED <<
        authorityQueued, requiredQueued, bulkBacklog, reconciliationBacklog,
        writerLive, claimPending, claimAckPending, readbackHealthy,
        authorityServiced, authorityProven, readbackObserved, failedClosed,
        executed, reconciliationChecks, reconciliationReminderEvents
    >>

SendRequired ==
    /\ writerLive
    /\ ~authorityQueued
    /\ ~resultQueued
    /\ requiredQueued
    /\ requiredQueued' = FALSE
    /\ UNCHANGED <<
        authorityQueued, resultQueued, bulkBacklog, reconciliationBacklog,
        writerLive, claimPending, claimAckPending, readbackHealthy,
        authorityServiced, resultServiced, authorityProven, readbackObserved,
        failedClosed, executed, reconciliationChecks,
        reconciliationReminderEvents
    >>

SendReconciliation ==
    /\ writerLive
    /\ ~authorityQueued
    /\ ~resultQueued
    /\ ~requiredQueued
    /\ reconciliationBacklog > 0
    /\ reconciliationBacklog' = reconciliationBacklog - 1
    /\ UNCHANGED <<
        authorityQueued, resultQueued, requiredQueued, bulkBacklog, writerLive,
        claimPending, claimAckPending, readbackHealthy, authorityServiced,
        resultServiced, authorityProven, readbackObserved, failedClosed,
        executed, reconciliationChecks, reconciliationReminderEvents
    >>

SendBulk ==
    /\ writerLive
    /\ ~authorityQueued
    /\ ~resultQueued
    /\ ~requiredQueued
    /\ reconciliationBacklog = 0
    /\ bulkBacklog > 0
    /\ bulkBacklog' = bulkBacklog - 1
    /\ UNCHANGED <<
        authorityQueued, resultQueued, requiredQueued, reconciliationBacklog,
        writerLive, claimPending, claimAckPending, readbackHealthy,
        authorityServiced, resultServiced, authorityProven, readbackObserved,
        failedClosed, executed, reconciliationChecks,
        reconciliationReminderEvents
    >>

HttpReadback ==
    /\ claimPending
    /\ readbackHealthy
    /\ ~authorityProven
    /\ readbackObserved' = TRUE
    /\ authorityProven' = TRUE
    /\ UNCHANGED <<
        authorityQueued, resultQueued, requiredQueued, bulkBacklog,
        reconciliationBacklog, writerLive, claimPending, claimAckPending,
        readbackHealthy, authorityServiced, resultServiced, failedClosed,
        executed, reconciliationChecks, reconciliationReminderEvents
    >>

FailClosed ==
    /\ claimPending
    /\ ~authorityProven
    /\ ~readbackHealthy
    /\ ~claimAckPending
    /\ failedClosed' = TRUE
    /\ UNCHANGED <<
        authorityQueued, resultQueued, requiredQueued, bulkBacklog,
        reconciliationBacklog, writerLive, claimPending, claimAckPending,
        readbackHealthy, authorityServiced, resultServiced, authorityProven,
        readbackObserved, executed, reconciliationChecks,
        reconciliationReminderEvents
    >>

Execute ==
    /\ authorityProven
    /\ ~failedClosed
    /\ executed' = TRUE
    /\ UNCHANGED <<
        authorityQueued, resultQueued, requiredQueued, bulkBacklog,
        reconciliationBacklog, writerLive, claimPending, claimAckPending,
        readbackHealthy, authorityServiced, resultServiced, authorityProven,
        readbackObserved, failedClosed, reconciliationChecks,
        reconciliationReminderEvents
    >>

ObserveReconciliation ==
    /\ reconciliationBacklog > 0
    /\ reconciliationChecks < MaxReconChecks
    /\ reconciliationChecks' = reconciliationChecks + 1
    /\ reconciliationReminderEvents' =
        IF reconciliationReminderEvents < 3
        THEN reconciliationReminderEvents + 1
        ELSE reconciliationReminderEvents
    /\ UNCHANGED <<
        authorityQueued, resultQueued, requiredQueued, bulkBacklog,
        reconciliationBacklog, writerLive, claimPending, claimAckPending,
        readbackHealthy, authorityServiced, resultServiced, authorityProven,
        readbackObserved, failedClosed, executed
    >>

Next ==
    SendAuthority
    \/ SendResult
    \/ SendRequired
    \/ SendReconciliation
    \/ SendBulk
    \/ HttpReadback
    \/ FailClosed
    \/ Execute
    \/ ObserveReconciliation

Spec ==
    /\ Init
    /\ [][Next]_vars
    /\ WF_vars(SendAuthority)
    /\ WF_vars(SendResult)
    /\ WF_vars(HttpReadback)

NoExecutionWithoutAuthority ==
    executed => authorityProven

SafetyNeverDependsOnLivenessSuccess ==
    []((~authorityProven) => (~executed))

AuthorityTrafficCannotBeStarvedByBulkTraffic ==
    []((writerLive /\ authorityQueued) => <>authorityServiced)

AuthorityTrafficCannotBeStarvedByReconciliationTraffic ==
    []((writerLive /\ authorityQueued /\ reconciliationBacklog > 0) => <>authorityServiced)

QueuedAuthorityEventuallyReceivesServiceUnderHealthyTransport ==
    []((writerLive /\ authorityQueued) => <>~authorityQueued)

TerminalResultEventuallyReceivesServiceUnderHealthyTransport ==
    []((writerLive /\ resultQueued) => <>resultServiced)

PersistedClaimEventuallyGetsAckOrIndependentReadbackUnderHealthyPaths ==
    []((claimPending /\ (claimAckPending \/ readbackHealthy)) => <>(authorityProven \/ failedClosed))

ReconciliationTrafficIsBounded ==
    [](reconciliationReminderEvents <= 3)

====
