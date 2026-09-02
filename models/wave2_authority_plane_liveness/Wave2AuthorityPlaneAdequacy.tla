---- MODULE Wave2AuthorityPlaneAdequacy ----
EXTENDS Wave2AuthorityPlaneLiveness

WitnessPreLaunchCancel == result.cancelProvenBeforeLaunch /\ ~result.processCreated
WitnessCancelDuringLaunch ==
    result.cancelRequested /\ result.processCreated /\
    ~result.processIdentityPersisted /\ result.launchReconciliation
WitnessKnownProcessCancel == result.cancelAppliedToKnownProcess
WitnessConnectionLossDuringExecution ==
    result.connectionLossObserved /\ result.executionRunning
WitnessFailed == result.outcome = FailedOutcome
WitnessCancelled == result.outcome = CancelledOutcome
WitnessReconciliation == result.outcome = ReconciliationOutcome
WitnessStaleAck == claim.staleAckRejected
WitnessConnectionOverlapAttempt == transport.connectionOverlapAttempted
WitnessPumpOverlapAttempt == transport.pumpOverlapAttempted
WitnessResultSentNotAccepted == result.sent /\ ~result.accepted
WitnessClaimSentNotPersisted == claim.sent /\ ~claim.persisted
WitnessJobContainedBeforeResume ==
    result.processResumed /\ result.jobAssigned /\
    result.jobMembershipVerified /\ result.processIdentityPersisted
WitnessConnectionAActive == transport.connectionAActive
WitnessPumpAActive == transport.pumpAActive
WitnessNewExchangePending ==
    claim.ackExchangeId = 2 /\
    claim.incomingAckExchangeId # claim.ackExchangeId /\ ~claim.proven
WitnessResumeAmbiguous ==
    result.resumeAmbiguous /\ result.launchReconciliation /\
    result.outcome = ReconciliationOutcome
WitnessCleanupIncomplete ==
    result.terminalAdmissibilityRejected /\ ~result.retained /\
    result.launchReconciliation

NotWitnessPreLaunchCancel == ~WitnessPreLaunchCancel
NotWitnessCancelDuringLaunch == ~WitnessCancelDuringLaunch
NotWitnessKnownProcessCancel == ~WitnessKnownProcessCancel
NotWitnessConnectionLossDuringExecution == ~WitnessConnectionLossDuringExecution
NotWitnessFailed == ~WitnessFailed
NotWitnessCancelled == ~WitnessCancelled
NotWitnessReconciliation == ~WitnessReconciliation
NotWitnessStaleAck == ~WitnessStaleAck
NotWitnessConnectionOverlapAttempt == ~WitnessConnectionOverlapAttempt
NotWitnessPumpOverlapAttempt == ~WitnessPumpOverlapAttempt
NotWitnessResultSentNotAccepted == ~WitnessResultSentNotAccepted
NotWitnessClaimSentNotPersisted == ~WitnessClaimSentNotPersisted
NotWitnessJobContainedBeforeResume == ~WitnessJobContainedBeforeResume
NotWitnessConnectionAActive == ~WitnessConnectionAActive
NotWitnessPumpAActive == ~WitnessPumpAActive
NotWitnessNewExchangePending == ~WitnessNewExchangePending
NotWitnessResumeAmbiguous == ~WitnessResumeAmbiguous
NotWitnessCleanupIncomplete == ~WitnessCleanupIncomplete

====
