---- MODULE Wave2AuthorityPlaneLiveness ----
EXTENDS Naturals, Sequences, TLC

(*
Bounded authority-plane transport model.

Implementation correspondence:
- authorityQueue and bulkQueue are separate finite queues;
- one writer owns one bounded in-flight WebSocket send;
- authorityBurst models bounded lower-class fairness;
- sendAge reaches SendBound, then the send completes or the transport fails;
- transport failure advances the generation and clears generation-bound queues;
- terminal result evidence remains durable and can be requeued after reconnect;
- an ACK proves authority only in the generation that sent the exact claim;
- HTTP readback is independent of WebSocket transport health;
- reconciliation production is finite.

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
    MaxTransportGeneration

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
NoProof == "NO_PROOF"
AckProof == "ACK_PROOF"
ReadbackProof == "READBACK_PROOF"
ProofSources == {NoProof, AckProof, ReadbackProof}

NoGeneration == MaxTransportGeneration + 1
Generations == 0..MaxTransportGeneration

SeqContains(seq, value) == \E index \in DOMAIN seq : seq[index] = value

VARIABLES
    authorityQueue,
    bulkQueue,
    reconciliationQueue,
    sendClass,
    sendFrame,
    sendAge,
    sendGeneration,
    transportHealthy,
    transportGeneration,
    authorityBurst,
    authorityOverflow,
    authorityFailureVisible,
    claimPending,
    claimPersisted,
    claimSentGeneration,
    ackHealthy,
    readbackHealthy,
    authorityProven,
    proofSource,
    proofGeneration,
    failedClosed,
    executed,
    cancelled,
    terminalResultRetained,
    resultDelivered,
    reconciliationChecks,
    reconciliationReminderEvents

vars == <<
    authorityQueue,
    bulkQueue,
    reconciliationQueue,
    sendClass,
    sendFrame,
    sendAge,
    sendGeneration,
    transportHealthy,
    transportGeneration,
    authorityBurst,
    authorityOverflow,
    authorityFailureVisible,
    claimPending,
    claimPersisted,
    claimSentGeneration,
    ackHealthy,
    readbackHealthy,
    authorityProven,
    proofSource,
    proofGeneration,
    failedClosed,
    executed,
    cancelled,
    terminalResultRetained,
    resultDelivered,
    reconciliationChecks,
    reconciliationReminderEvents
>>

TypeOK ==
    /\ authorityQueue \in Seq(AuthorityFrames)
    /\ Len(authorityQueue) <= AuthorityCapacity
    /\ bulkQueue \in 0..BulkCapacity
    /\ reconciliationQueue \in 0..ReconCapacity
    /\ sendClass \in SendClasses
    /\ sendFrame \in AuthorityFrames \cup {NoFrame}
    /\ sendAge \in 0..SendBound
    /\ sendGeneration \in Generations \cup {NoGeneration}
    /\ transportHealthy \in BOOLEAN
    /\ transportGeneration \in Generations
    /\ authorityBurst \in 0..AuthorityBurstLimit
    /\ authorityOverflow \in BOOLEAN
    /\ authorityFailureVisible \in BOOLEAN
    /\ claimPending \in BOOLEAN
    /\ claimPersisted \in BOOLEAN
    /\ claimSentGeneration \in Generations \cup {NoGeneration}
    /\ ackHealthy \in BOOLEAN
    /\ readbackHealthy \in BOOLEAN
    /\ authorityProven \in BOOLEAN
    /\ proofSource \in ProofSources
    /\ proofGeneration \in Generations \cup {NoGeneration}
    /\ failedClosed \in BOOLEAN
    /\ executed \in BOOLEAN
    /\ cancelled \in BOOLEAN
    /\ terminalResultRetained \in BOOLEAN
    /\ resultDelivered \in BOOLEAN
    /\ reconciliationChecks \in 0..MaxReconChecks
    /\ reconciliationReminderEvents \in 0..ReconCapacity

Init ==
    /\ authorityQueue = <<>>
    /\ bulkQueue \in 0..BulkCapacity
    /\ reconciliationQueue \in 0..ReconCapacity
    /\ sendClass = NoSend
    /\ sendFrame = NoFrame
    /\ sendAge = 0
    /\ sendGeneration = NoGeneration
    /\ transportHealthy = TRUE
    /\ transportGeneration = 0
    /\ authorityBurst = 0
    /\ authorityOverflow = FALSE
    /\ authorityFailureVisible = FALSE
    /\ claimPending \in BOOLEAN
    /\ claimPersisted = FALSE
    /\ claimSentGeneration = NoGeneration
    /\ ackHealthy \in BOOLEAN
    /\ readbackHealthy \in BOOLEAN
    /\ authorityProven = FALSE
    /\ proofSource = NoProof
    /\ proofGeneration = NoGeneration
    /\ failedClosed = FALSE
    /\ executed = FALSE
    /\ cancelled = FALSE
    /\ terminalResultRetained \in BOOLEAN
    /\ resultDelivered = FALSE
    /\ reconciliationChecks = 0
    /\ reconciliationReminderEvents = 0

ClaimOutstanding ==
    SeqContains(authorityQueue, ClaimFrame)
    \/ (sendClass = AuthoritySend /\ sendFrame = ClaimFrame)

ResultOutstanding ==
    SeqContains(authorityQueue, ResultFrame)
    \/ (sendClass = AuthoritySend /\ sendFrame = ResultFrame)

QueueClaim ==
    /\ claimPending
    /\ ~claimPersisted
    /\ ~failedClosed
    /\ ~cancelled
    /\ ~ClaimOutstanding
    /\ Len(authorityQueue) < AuthorityCapacity
    /\ authorityQueue' = Append(authorityQueue, ClaimFrame)
    /\ UNCHANGED <<
        bulkQueue, reconciliationQueue, sendClass, sendFrame, sendAge,
        sendGeneration, transportHealthy, transportGeneration, authorityBurst,
        authorityOverflow, authorityFailureVisible, claimPending,
        claimPersisted, claimSentGeneration, ackHealthy, readbackHealthy,
        authorityProven, proofSource, proofGeneration, failedClosed, executed,
        cancelled, terminalResultRetained, resultDelivered,
        reconciliationChecks, reconciliationReminderEvents
        >>

ClaimAuthorityOverflow ==
    /\ claimPending
    /\ ~claimPersisted
    /\ ~failedClosed
    /\ ~cancelled
    /\ ~ClaimOutstanding
    /\ Len(authorityQueue) = AuthorityCapacity
    /\ authorityOverflow' = TRUE
    /\ authorityFailureVisible' = TRUE
    /\ failedClosed' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, sendClass, sendFrame,
        sendAge, sendGeneration, transportHealthy, transportGeneration,
        authorityBurst, claimPending, claimPersisted, claimSentGeneration,
        ackHealthy, readbackHealthy, authorityProven, proofSource,
        proofGeneration, executed, cancelled, terminalResultRetained,
        resultDelivered, reconciliationChecks, reconciliationReminderEvents
        >>

QueueRetainedResult ==
    /\ terminalResultRetained
    /\ ~resultDelivered
    /\ ~ResultOutstanding
    /\ Len(authorityQueue) < AuthorityCapacity
    /\ authorityQueue' = Append(authorityQueue, ResultFrame)
    /\ UNCHANGED <<
        bulkQueue, reconciliationQueue, sendClass, sendFrame, sendAge,
        sendGeneration, transportHealthy, transportGeneration, authorityBurst,
        authorityOverflow, authorityFailureVisible, claimPending,
        claimPersisted, claimSentGeneration, ackHealthy, readbackHealthy,
        authorityProven, proofSource, proofGeneration, failedClosed, executed,
        cancelled, terminalResultRetained, resultDelivered,
        reconciliationChecks, reconciliationReminderEvents
        >>

ResultAuthorityOverflow ==
    /\ terminalResultRetained
    /\ ~resultDelivered
    /\ ~ResultOutstanding
    /\ Len(authorityQueue) = AuthorityCapacity
    /\ ~authorityFailureVisible
    /\ authorityOverflow' = TRUE
    /\ authorityFailureVisible' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, sendClass, sendFrame,
        sendAge, sendGeneration, transportHealthy, transportGeneration,
        authorityBurst, claimPending, claimPersisted, claimSentGeneration,
        ackHealthy, readbackHealthy, authorityProven, proofSource,
        proofGeneration, failedClosed, executed, cancelled,
        terminalResultRetained, resultDelivered, reconciliationChecks,
        reconciliationReminderEvents
        >>

RequestCancel ==
    /\ ~executed
    /\ ~cancelled
    /\ cancelled' = TRUE
    /\ failedClosed' = TRUE
    /\ authorityQueue' =
        IF Len(authorityQueue) < AuthorityCapacity
        THEN Append(authorityQueue, CancelFrame)
        ELSE authorityQueue
    /\ authorityOverflow' = authorityOverflow \/
        (Len(authorityQueue) = AuthorityCapacity)
    /\ authorityFailureVisible' = authorityFailureVisible \/
        (Len(authorityQueue) = AuthorityCapacity)
    /\ UNCHANGED <<
        bulkQueue, reconciliationQueue, sendClass, sendFrame, sendAge,
        sendGeneration, transportHealthy, transportGeneration, authorityBurst,
        claimPending, claimPersisted, claimSentGeneration, ackHealthy,
        readbackHealthy, authorityProven, proofSource, proofGeneration, executed,
        terminalResultRetained, resultDelivered, reconciliationChecks,
        reconciliationReminderEvents
        >>

ProduceBulk ==
    /\ bulkQueue < BulkCapacity
    /\ bulkQueue' = bulkQueue + 1
    /\ UNCHANGED <<
        authorityQueue, reconciliationQueue, sendClass, sendFrame, sendAge,
        sendGeneration, transportHealthy, transportGeneration, authorityBurst,
        authorityOverflow, authorityFailureVisible, claimPending,
        claimPersisted, claimSentGeneration, ackHealthy, readbackHealthy,
        authorityProven, proofSource, proofGeneration, failedClosed, executed,
        cancelled, terminalResultRetained, resultDelivered,
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
        authorityQueue, bulkQueue, sendClass, sendFrame, sendAge,
        sendGeneration, transportHealthy, transportGeneration, authorityBurst,
        authorityOverflow, authorityFailureVisible, claimPending,
        claimPersisted, claimSentGeneration, ackHealthy, readbackHealthy,
        authorityProven, proofSource, proofGeneration, failedClosed, executed,
        cancelled, terminalResultRetained, resultDelivered
        >>

LowerWorkQueued == reconciliationQueue > 0 \/ bulkQueue > 0

StartAuthority ==
    /\ transportHealthy
    /\ sendClass = NoSend
    /\ Len(authorityQueue) > 0
    /\ authorityBurst < AuthorityBurstLimit \/ ~LowerWorkQueued
    /\ sendClass' = AuthoritySend
    /\ sendFrame' = Head(authorityQueue)
    /\ authorityQueue' = Tail(authorityQueue)
    /\ sendAge' = 0
    /\ sendGeneration' = transportGeneration
    /\ authorityBurst' =
        IF authorityBurst < AuthorityBurstLimit
        THEN authorityBurst + 1
        ELSE authorityBurst
    /\ UNCHANGED <<
        bulkQueue, reconciliationQueue, transportHealthy, transportGeneration,
        authorityOverflow, authorityFailureVisible, claimPending,
        claimPersisted, claimSentGeneration, ackHealthy, readbackHealthy,
        authorityProven, proofSource, proofGeneration, failedClosed, executed,
        cancelled, terminalResultRetained, resultDelivered,
        reconciliationChecks, reconciliationReminderEvents
        >>

StartReconciliation ==
    /\ transportHealthy
    /\ sendClass = NoSend
    /\ reconciliationQueue > 0
    /\ Len(authorityQueue) = 0 \/ authorityBurst = AuthorityBurstLimit
    /\ reconciliationQueue' = reconciliationQueue - 1
    /\ sendClass' = ReconciliationSend
    /\ sendFrame' = NoFrame
    /\ sendAge' = 0
    /\ sendGeneration' = transportGeneration
    /\ authorityBurst' = 0
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, transportHealthy, transportGeneration,
        authorityOverflow, authorityFailureVisible, claimPending,
        claimPersisted, claimSentGeneration, ackHealthy, readbackHealthy,
        authorityProven, proofSource, proofGeneration, failedClosed, executed,
        cancelled, terminalResultRetained, resultDelivered,
        reconciliationChecks, reconciliationReminderEvents
        >>

StartBulk ==
    /\ transportHealthy
    /\ sendClass = NoSend
    /\ bulkQueue > 0
    /\ reconciliationQueue = 0
    /\ Len(authorityQueue) = 0 \/ authorityBurst = AuthorityBurstLimit
    /\ bulkQueue' = bulkQueue - 1
    /\ sendClass' = BulkSend
    /\ sendFrame' = NoFrame
    /\ sendAge' = 0
    /\ sendGeneration' = transportGeneration
    /\ authorityBurst' = 0
    /\ UNCHANGED <<
        authorityQueue, reconciliationQueue, transportHealthy,
        transportGeneration, authorityOverflow, authorityFailureVisible,
        claimPending, claimPersisted, claimSentGeneration, ackHealthy,
        readbackHealthy, authorityProven, proofSource, proofGeneration,
        failedClosed, executed, cancelled, terminalResultRetained,
        resultDelivered, reconciliationChecks, reconciliationReminderEvents
        >>

AdvanceSend ==
    /\ transportHealthy
    /\ sendClass # NoSend
    /\ sendAge < SendBound
    /\ sendAge' = sendAge + 1
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, sendClass, sendFrame,
        sendGeneration, transportHealthy, transportGeneration, authorityBurst,
        authorityOverflow, authorityFailureVisible, claimPending,
        claimPersisted, claimSentGeneration, ackHealthy, readbackHealthy,
        authorityProven, proofSource, proofGeneration, failedClosed, executed,
        cancelled, terminalResultRetained, resultDelivered,
        reconciliationChecks, reconciliationReminderEvents
        >>

CompleteSend ==
    /\ transportHealthy
    /\ sendClass # NoSend
    /\ sendAge <= SendBound
    /\ sendClass' = NoSend
    /\ sendFrame' = NoFrame
    /\ sendAge' = 0
    /\ sendGeneration' = NoGeneration
    /\ claimPersisted' = claimPersisted \/
        (sendClass = AuthoritySend /\ sendFrame = ClaimFrame)
    /\ claimSentGeneration' =
        IF sendClass = AuthoritySend /\ sendFrame = ClaimFrame
        THEN sendGeneration
        ELSE claimSentGeneration
    /\ resultDelivered' = resultDelivered \/
        (sendClass = AuthoritySend /\ sendFrame = ResultFrame)
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, transportHealthy,
        transportGeneration, authorityBurst, authorityOverflow,
        authorityFailureVisible, claimPending, ackHealthy, readbackHealthy,
        authorityProven, proofSource, proofGeneration, failedClosed, executed,
        cancelled, terminalResultRetained, reconciliationChecks,
        reconciliationReminderEvents
        >>

SendDeadline ==
    /\ transportHealthy
    /\ sendClass # NoSend
    /\ sendAge = SendBound
    /\ transportGeneration < MaxTransportGeneration
    /\ transportHealthy' = FALSE
    /\ transportGeneration' = transportGeneration + 1
    /\ authorityQueue' = <<>>
    /\ bulkQueue' = 0
    /\ reconciliationQueue' = 0
    /\ sendClass' = NoSend
    /\ sendFrame' = NoFrame
    /\ sendAge' = 0
    /\ sendGeneration' = NoGeneration
    /\ authorityBurst' = 0
    /\ authorityFailureVisible' = authorityFailureVisible \/
        (sendClass = AuthoritySend)
    /\ claimPersisted' \in
        IF sendClass = AuthoritySend /\ sendFrame = ClaimFrame
        THEN {claimPersisted, TRUE}
        ELSE {claimPersisted}
    /\ claimSentGeneration' =
        IF ~claimPersisted /\ claimPersisted'
        THEN sendGeneration
        ELSE claimSentGeneration
    /\ UNCHANGED <<
        authorityOverflow, claimPending, ackHealthy, readbackHealthy,
        authorityProven, proofSource, proofGeneration, failedClosed, executed,
        cancelled, terminalResultRetained, resultDelivered,
        reconciliationChecks, reconciliationReminderEvents
        >>

Reconnect ==
    /\ ~transportHealthy
    /\ transportHealthy' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, sendClass, sendFrame,
        sendAge, sendGeneration, transportGeneration, authorityBurst,
        authorityOverflow, authorityFailureVisible, claimPending,
        claimPersisted, claimSentGeneration, ackHealthy, readbackHealthy,
        authorityProven, proofSource, proofGeneration, failedClosed, executed,
        cancelled, terminalResultRetained, resultDelivered,
        reconciliationChecks, reconciliationReminderEvents
        >>

ObserveAck ==
    /\ claimPending
    /\ claimPersisted
    /\ ackHealthy
    /\ transportHealthy
    /\ claimSentGeneration = transportGeneration
    /\ ~authorityProven
    /\ ~failedClosed
    /\ ~cancelled
    /\ authorityProven' = TRUE
    /\ proofSource' = AckProof
    /\ proofGeneration' = claimSentGeneration
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, sendClass, sendFrame,
        sendAge, sendGeneration, transportHealthy, transportGeneration,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        claimPending, claimPersisted, claimSentGeneration, ackHealthy,
        readbackHealthy, failedClosed, executed, cancelled,
        terminalResultRetained, resultDelivered, reconciliationChecks,
        reconciliationReminderEvents
        >>

HttpReadback ==
    /\ claimPending
    /\ claimPersisted
    /\ readbackHealthy
    /\ ~authorityProven
    /\ ~failedClosed
    /\ ~cancelled
    /\ authorityProven' = TRUE
    /\ proofSource' = ReadbackProof
    /\ proofGeneration' = NoGeneration
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, sendClass, sendFrame,
        sendAge, sendGeneration, transportHealthy, transportGeneration,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        claimPending, claimPersisted, claimSentGeneration, ackHealthy,
        readbackHealthy, failedClosed, executed, cancelled,
        terminalResultRetained, resultDelivered, reconciliationChecks,
        reconciliationReminderEvents
        >>

FailClosed ==
    /\ claimPending
    /\ ~authorityProven
    /\ ~failedClosed
    /\ (~readbackHealthy)
    /\ (~ackHealthy \/ claimSentGeneration # transportGeneration)
    /\ failedClosed' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, sendClass, sendFrame,
        sendAge, sendGeneration, transportHealthy, transportGeneration,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        claimPending, claimPersisted, claimSentGeneration, ackHealthy,
        readbackHealthy, authorityProven, proofSource, proofGeneration, executed,
        cancelled, terminalResultRetained, resultDelivered,
        reconciliationChecks, reconciliationReminderEvents
        >>

Execute ==
    /\ authorityProven
    /\ ~failedClosed
    /\ ~cancelled
    /\ ~executed
    /\ executed' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, sendClass, sendFrame,
        sendAge, sendGeneration, transportHealthy, transportGeneration,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        claimPending, claimPersisted, claimSentGeneration, ackHealthy,
        readbackHealthy, authorityProven, proofSource, proofGeneration,
        failedClosed, cancelled, terminalResultRetained, resultDelivered,
        reconciliationChecks, reconciliationReminderEvents
        >>

ProduceTerminalResult ==
    /\ executed
    /\ ~terminalResultRetained
    /\ terminalResultRetained' = TRUE
    /\ UNCHANGED <<
        authorityQueue, bulkQueue, reconciliationQueue, sendClass, sendFrame,
        sendAge, sendGeneration, transportHealthy, transportGeneration,
        authorityBurst, authorityOverflow, authorityFailureVisible,
        claimPending, claimPersisted, claimSentGeneration, ackHealthy,
        readbackHealthy, authorityProven, proofSource, proofGeneration,
        failedClosed, executed, cancelled, resultDelivered,
        reconciliationChecks, reconciliationReminderEvents
        >>

WriterStart == StartAuthority \/ StartReconciliation \/ StartBulk
SendProgress == AdvanceSend \/ CompleteSend \/ SendDeadline
AuthorityAdmission ==
    QueueClaim \/ ClaimAuthorityOverflow \/ QueueRetainedResult
    \/ ResultAuthorityOverflow \/ RequestCancel
TrafficProduction == ProduceBulk \/ ProduceReconciliation

Next ==
    AuthorityAdmission
    \/ TrafficProduction
    \/ WriterStart
    \/ SendProgress
    \/ Reconnect
    \/ ObserveAck
    \/ HttpReadback
    \/ FailClosed
    \/ Execute
    \/ ProduceTerminalResult

Spec ==
    /\ Init
    /\ [][Next]_vars
    /\ WF_vars(QueueClaim)
    /\ WF_vars(QueueRetainedResult)
    /\ WF_vars(WriterStart)
    /\ WF_vars(SendProgress)
    /\ WF_vars(Reconnect)
    /\ WF_vars(ObserveAck)
    /\ WF_vars(HttpReadback)
    /\ WF_vars(FailClosed)
    /\ WF_vars(ProduceTerminalResult)

AuthorityQueueIsBounded == Len(authorityQueue) <= AuthorityCapacity

AuthorityOverflowNeverSilentlyDropsAuthority ==
    authorityOverflow => authorityFailureVisible

NoExecutionWithoutCanonicalAuthority == executed => authorityProven

TransportFailureCannotAuthorizeExecution ==
    (~transportHealthy /\ ~authorityProven) => ~executed

BothObservationPathsUnavailableNeverAllowsRunning ==
    (claimPending /\ ~ackHealthy /\ ~readbackHealthy) => ~executed

CancellationSafetyPreserved == cancelled => ~executed

TerminalResultNotLostOnTransportOverload ==
    [](terminalResultRetained => []terminalResultRetained)

ReconciliationProductionIsBounded ==
    reconciliationReminderEvents <= ReconCapacity

AckProofUsesExactTransportGeneration ==
    (authorityProven /\ proofSource = AckProof) =>
        proofGeneration = claimSentGeneration

AuthorityOverflowCannotPermitRunning ==
    (authorityOverflow /\ claimPending /\ ~authorityProven) => ~executed

BulkTrafficCannotStarveAuthority ==
    []((transportHealthy /\ Len(authorityQueue) > 0) =>
        <>(Len(authorityQueue) = 0 \/ ~transportHealthy))

InFlightBulkSendEitherCompletesOrTransportFailsWithinBound ==
    []((transportHealthy /\ sendClass = BulkSend) =>
        <>(sendClass # BulkSend \/ ~transportHealthy))

QueuedAuthorityEventuallyServicedUnderHealthyTransport ==
    []((transportHealthy /\ Len(authorityQueue) > 0) =>
        <>(Len(authorityQueue) = 0 \/ authorityFailureVisible \/ ~transportHealthy))

PersistedClaimEventuallyObservedViaAckOrReadbackUnderHealthyPaths ==
    []((claimPending /\ claimPersisted /\ (ackHealthy \/ readbackHealthy)) =>
        <>(authorityProven \/ failedClosed))

TerminalResultEventuallyServicedUnderHealthyTransport ==
    []((transportHealthy /\ terminalResultRetained /\ ~resultDelivered) =>
        <>(resultDelivered \/ authorityFailureVisible \/ ~transportHealthy))

SafetyNeverDependsOnLivenessSuccess == []((~authorityProven) => (~executed))

====
