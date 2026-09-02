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

====
