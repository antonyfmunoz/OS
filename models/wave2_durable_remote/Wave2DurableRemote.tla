---- MODULE Wave2DurableRemote ----
EXTENDS Naturals, TLC

(*
Minimal Wave 2 DurableRemote authority model.

Scope:
- one logical durable request
- canonical lifecycle and claim ownership
- transport duplication/loss/delay/restart as nondeterministic interleavings
- execution marker and cancellation
- logical idempotency admission distinct from transport request ids

This model intentionally excludes Docker, Windows process management, frontend
activation, and model-provider behavior. Those are adapter/lifecycle concerns
outside the critical durable authority protocol.
*)

VARIABLES state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt

protocolVars == <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
idemVars == <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
vars == <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>

Terminal == {"SUCCEEDED", "FAILED", "CANCELLED", "RECONCILIATION_REQUIRED"}
ClaimedLike == {"CLAIMED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"}
Keys == {"key1", "key2"}
MaybeKey == Keys \cup {"none"}
Payloads == {"payload1", "payload2"}
Requests == {"none", "A", "B"}
HasCanonicalIdempotency == \E k \in Keys: canonicalRequestForKey[k] # "none"
MaterialComplete == canonicalMaterialValid /\ recoveredMaterialValid
MaterialValid == MaterialComplete
ResultPresent == invalidRecoveredResultAttempt
ResultConverged == invalidRecoveredResultAttempt /\ state \in {"SUCCEEDED", "FAILED", "CANCELLED"}
DeclaredRisk == IF declaredSyncEffect = "READ_ONLY" THEN "read_only" ELSE "reversible_write"
CanonicalRisk == IF canonicalSyncEffect = "READ_ONLY" THEN "read_only" ELSE "reversible_write"
RecordCorrupt == ~canonicalMaterialValid \/ ~recoveredMaterialValid

Init ==
    /\ state = "QUEUED"
    /\ delivered = FALSE
    /\ claim = "none"
    /\ candidate = "cand"
    /\ expectedCandidate = "cand"
    /\ cancelled = FALSE
    /\ executed = 0
    /\ proof = FALSE
    /\ authorityAtLaunch = FALSE
    /\ terminalSeen = FALSE
    /\ meshUp = TRUE
    /\ nodeUp = TRUE
    /\ declaredSyncEffect \in {"READ_ONLY", "CONSEQUENTIAL_WRITE", "UNKNOWN"}
    /\ canonicalSyncEffect \in {"READ_ONLY", "CONSEQUENTIAL_WRITE", "UNKNOWN"}
    /\ durableCanonicalEffect \in {"CONSEQUENTIAL_WRITE", "UNKNOWN"}
    /\ durableExecutionPath = "NONE"
    /\ syncExecutionPath = "NONE"
    /\ syncExecuted = 0
    /\ syncConsequentialEffects = 0
    /\ requestAAdmitted = FALSE
    /\ requestBAdmitted = FALSE
    /\ requestAKey \in MaybeKey
    /\ requestBKey \in MaybeKey
    /\ requestAPayload = "payload1"
    /\ requestBPayload \in Payloads
    /\ canonicalRequestForKey = [k \in Keys |-> "none"]
    /\ admittedRequestForKey = [k \in Keys |-> "none"]
    /\ canonicalPayloadForKey = [k \in Keys |-> "none"]
    /\ canonicalMaterialValid = TRUE
    /\ idempotencyConflict = FALSE
    /\ noncanonicalDuplicatePersisted = FALSE
    /\ noncanonicalDuplicateKey = "none"
    /\ noncanonicalDuplicateDeliverable = FALSE
    /\ duplicateRecoveryDone = FALSE
    /\ noncanonicalDuplicateExecuted = 0
    /\ recoveredFromPersistence = FALSE
    /\ indexPresent = FALSE
    /\ indexRecovered = FALSE
    /\ recoveredMaterialValid = TRUE
    /\ recoveredDeliverable = FALSE
    /\ invalidRecoveredResultAttempt = FALSE

AdmitRequestA ==
    /\ ~requestAAdmitted
    /\ requestAAdmitted' = TRUE
    /\ IF requestAKey = "none"
        THEN
            /\ canonicalRequestForKey' = canonicalRequestForKey
            /\ admittedRequestForKey' = admittedRequestForKey
            /\ canonicalPayloadForKey' = canonicalPayloadForKey
            /\ idempotencyConflict' = TRUE
        ELSE IF canonicalRequestForKey[requestAKey] = "none"
        THEN
            /\ canonicalRequestForKey' = [canonicalRequestForKey EXCEPT ![requestAKey] = "A"]
            /\ admittedRequestForKey' =
                IF admittedRequestForKey[requestAKey] = "none"
                THEN [admittedRequestForKey EXCEPT ![requestAKey] = "A"]
                ELSE admittedRequestForKey
            /\ canonicalPayloadForKey' = [canonicalPayloadForKey EXCEPT ![requestAKey] = requestAPayload]
            /\ indexPresent' = TRUE
            /\ idempotencyConflict' = idempotencyConflict
        ELSE
            /\ canonicalRequestForKey' = canonicalRequestForKey
            /\ admittedRequestForKey' = admittedRequestForKey
            /\ canonicalPayloadForKey' = canonicalPayloadForKey
            /\ indexPresent' = indexPresent
            /\ idempotencyConflict' =
                (idempotencyConflict \/ (canonicalPayloadForKey[requestAKey] # requestAPayload))
    /\ IF requestAKey = "none"
        THEN indexPresent' = indexPresent
        ELSE TRUE
    /\ UNCHANGED <<requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalMaterialValid, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

AdmitRequestB ==
    /\ ~requestBAdmitted
    /\ requestBAdmitted' = TRUE
    /\ IF requestBKey = "none"
        THEN
            /\ canonicalRequestForKey' = canonicalRequestForKey
            /\ admittedRequestForKey' = admittedRequestForKey
            /\ canonicalPayloadForKey' = canonicalPayloadForKey
            /\ idempotencyConflict' = TRUE
        ELSE IF canonicalRequestForKey[requestBKey] = "none"
        THEN
            /\ canonicalRequestForKey' = [canonicalRequestForKey EXCEPT ![requestBKey] = "B"]
            /\ admittedRequestForKey' =
                IF admittedRequestForKey[requestBKey] = "none"
                THEN [admittedRequestForKey EXCEPT ![requestBKey] = "B"]
                ELSE admittedRequestForKey
            /\ canonicalPayloadForKey' = [canonicalPayloadForKey EXCEPT ![requestBKey] = requestBPayload]
            /\ indexPresent' = TRUE
            /\ idempotencyConflict' = idempotencyConflict
        ELSE
            /\ canonicalRequestForKey' = canonicalRequestForKey
            /\ admittedRequestForKey' = admittedRequestForKey
            /\ canonicalPayloadForKey' = canonicalPayloadForKey
            /\ indexPresent' = indexPresent
            /\ idempotencyConflict' =
                (idempotencyConflict \/ (canonicalPayloadForKey[requestBKey] # requestBPayload))
    /\ IF requestBKey = "none"
        THEN indexPresent' = indexPresent
        ELSE TRUE
    /\ UNCHANGED <<requestAAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalMaterialValid, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

InjectNoncanonicalDuplicateFile ==
    /\ HasCanonicalIdempotency
    /\ ~idempotencyConflict
    /\ ~noncanonicalDuplicatePersisted
    /\ \E k \in Keys:
        /\ canonicalRequestForKey[k] # "none"
        /\ admittedRequestForKey[k] # "none"
        /\ noncanonicalDuplicateKey' = k
    /\ noncanonicalDuplicatePersisted' = TRUE
    /\ noncanonicalDuplicateDeliverable' = TRUE
    /\ duplicateRecoveryDone' = FALSE
    /\ noncanonicalDuplicateExecuted' = noncanonicalDuplicateExecuted
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

CorruptIndexToBDetected ==
    /\ \E k \in Keys:
        /\ admittedRequestForKey[k] = "A"
        /\ requestBAdmitted
        /\ requestBKey = k
        /\ canonicalRequestForKey[k] # "B"
        /\ canonicalRequestForKey' = [canonicalRequestForKey EXCEPT ![k] = "B"]
    /\ idempotencyConflict' = TRUE
    /\ noncanonicalDuplicateDeliverable' = FALSE
    /\ duplicateRecoveryDone' = TRUE
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

CorruptIndexToADetected ==
    /\ \E k \in Keys:
        /\ admittedRequestForKey[k] = "B"
        /\ requestAAdmitted
        /\ requestAKey = k
        /\ canonicalRequestForKey[k] # "A"
        /\ canonicalRequestForKey' = [canonicalRequestForKey EXCEPT ![k] = "A"]
    /\ idempotencyConflict' = TRUE
    /\ noncanonicalDuplicateDeliverable' = FALSE
    /\ duplicateRecoveryDone' = TRUE
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

DropAdmissionEvidence ==
    /\ ~noncanonicalDuplicatePersisted
    /\ \E k \in Keys:
        /\ admittedRequestForKey[k] # "none"
        /\ admittedRequestForKey' = [admittedRequestForKey EXCEPT ![k] = "none"]
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

CorruptIndexWithoutAdmissionEvidenceDetected ==
    /\ \E k \in Keys:
        /\ admittedRequestForKey[k] = "none"
        /\ canonicalRequestForKey[k] # "none"
        /\ ((requestAAdmitted /\ requestAKey = k) /\ (requestBAdmitted /\ requestBKey = k))
        /\ noncanonicalDuplicateKey' = k
    /\ idempotencyConflict' = TRUE
    /\ noncanonicalDuplicatePersisted' = TRUE
    /\ noncanonicalDuplicateDeliverable' = FALSE
    /\ duplicateRecoveryDone' = TRUE
    /\ noncanonicalDuplicateExecuted' = noncanonicalDuplicateExecuted
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

MutateCanonicalIdentity ==
    /\ HasCanonicalIdempotency
    /\ canonicalMaterialValid
    /\ executed = 0
    /\ canonicalMaterialValid' = FALSE
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

CanonicalIdentityDriftDetected ==
    /\ HasCanonicalIdempotency
    /\ ~canonicalMaterialValid
    /\ idempotencyConflict' = TRUE
    /\ noncanonicalDuplicateDeliverable' = FALSE
    /\ duplicateRecoveryDone' = TRUE
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

LoseIdempotencyIndex ==
    /\ HasCanonicalIdempotency
    /\ indexPresent
    /\ indexPresent' = FALSE
    /\ indexRecovered' = FALSE
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

RecoverValidMissingIndex ==
    /\ HasCanonicalIdempotency
    /\ ~indexPresent
    /\ canonicalMaterialValid
    /\ recoveredMaterialValid
    /\ indexPresent' = TRUE
    /\ indexRecovered' = TRUE
    /\ recoveredFromPersistence' = TRUE
    /\ recoveredDeliverable' = FALSE
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredMaterialValid, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars

InjectInvalidRecoveredMaterial ==
    /\ ~recoveredFromPersistence
    /\ ~HasCanonicalIdempotency
    /\ recoveredFromPersistence' = TRUE
    /\ recoveredMaterialValid' = FALSE
    /\ canonicalMaterialValid' = FALSE
    /\ recoveredDeliverable' = FALSE
    /\ indexPresent' = FALSE
    /\ indexRecovered' = FALSE
    /\ invalidRecoveredResultAttempt' = invalidRecoveredResultAttempt
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted>>
    /\ UNCHANGED protocolVars

RecoverInvalidMaterialDetected ==
    /\ recoveredFromPersistence
    /\ ~recoveredMaterialValid
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ recoveredDeliverable' = FALSE
    /\ idempotencyConflict' = TRUE
    /\ indexPresent' = FALSE
    /\ indexRecovered' = FALSE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, recoveredMaterialValid, invalidRecoveredResultAttempt>>

RecoveredInvalidClaimRejected ==
    /\ recoveredFromPersistence
    /\ ~recoveredMaterialValid
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ recoveredDeliverable' = FALSE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, invalidRecoveredResultAttempt>>

RecoveredInvalidResultRejected ==
    /\ recoveredFromPersistence
    /\ ~recoveredMaterialValid
    /\ invalidRecoveredResultAttempt' = TRUE
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ recoveredDeliverable' = FALSE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid>>

Deliver ==
    /\ HasCanonicalIdempotency
    /\ ~idempotencyConflict
    /\ canonicalMaterialValid
    /\ state = "QUEUED"
    /\ delivered' = TRUE
    /\ noncanonicalDuplicateDeliverable' = FALSE
    /\ duplicateRecoveryDone' = (duplicateRecoveryDone \/ noncanonicalDuplicatePersisted)
    /\ noncanonicalDuplicatePersisted' = noncanonicalDuplicatePersisted
    /\ noncanonicalDuplicateKey' = noncanonicalDuplicateKey
    /\ noncanonicalDuplicateExecuted' = noncanonicalDuplicateExecuted
    /\ UNCHANGED <<state, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>

DuplicateDelivery ==
    /\ delivered
    /\ state \in {"QUEUED", "CLAIMED", "RUNNING"} \cup Terminal
    /\ UNCHANGED vars

CanonicalClaimWrite ==
    /\ state = "QUEUED"
    /\ delivered
    /\ meshUp /\ nodeUp
    /\ ~idempotencyConflict
    /\ canonicalMaterialValid
    /\ durableCanonicalEffect = "CONSEQUENTIAL_WRITE"
    /\ state' = "CLAIMED"
    /\ claim' = "claim1"
    /\ UNCHANGED <<delivered, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED idemVars

LostAck ==
    /\ state = "CLAIMED"
    /\ UNCHANGED vars

DelayedAck ==
    /\ state \in ClaimedLike
    /\ UNCHANGED vars

CanonicalReadProof ==
    /\ state \in ClaimedLike
    /\ claim = "claim1"
    /\ candidate = expectedCandidate
    /\ proof' = TRUE
    /\ UNCHANGED <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED idemVars

CanonicalReadUnavailable ==
    /\ state \in {"QUEUED", "CLAIMED"}
    /\ delivered
    /\ proof = FALSE
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED idemVars

Run ==
    /\ state = "CLAIMED"
    /\ proof
    /\ HasCanonicalIdempotency
    /\ ~idempotencyConflict
    /\ canonicalMaterialValid
    /\ ~cancelled
    /\ claim = "claim1"
    /\ candidate = expectedCandidate
    /\ durableCanonicalEffect = "CONSEQUENTIAL_WRITE"
    /\ state' = "RUNNING"
    /\ executed' = executed + 1
    /\ authorityAtLaunch' = TRUE
    /\ durableExecutionPath' = "DurableRemote"
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, proof, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED idemVars

RunningReadReconcile ==
    /\ state = "RUNNING"
    /\ proof
    /\ UNCHANGED vars

Terminalize ==
    /\ state = "RUNNING"
    /\ state' \in {"SUCCEEDED", "FAILED"}
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED idemVars

CancelBeforeLaunch ==
    /\ state \in {"QUEUED", "CLAIMED"}
    /\ executed = 0
    /\ cancelled' = TRUE
    /\ state' = "CANCELLED"
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED idemVars

ForeignClaim ==
    /\ state \in {"QUEUED", "CLAIMED"}
    /\ delivered
    /\ claim # "none"
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED idemVars

CandidateMismatch ==
    /\ state \in {"QUEUED", "CLAIMED"}
    /\ delivered
    /\ candidate' = "foreign"
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED idemVars

LateForeignRunningAfterTerminal ==
    /\ state \in Terminal
    /\ UNCHANGED vars

NodeRestart ==
    /\ nodeUp' = ~nodeUp
    /\ proof' = FALSE
    /\ UNCHANGED <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, authorityAtLaunch, terminalSeen, meshUp, declaredSyncEffect, canonicalSyncEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED idemVars

MeshRestart ==
    /\ meshUp' = ~meshUp
    /\ UNCHANGED <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, durableCanonicalEffect>>
    /\ UNCHANGED idemVars

DurableRemoteRejectUnknownPolicy ==
    /\ state = "QUEUED"
    /\ HasCanonicalIdempotency
    /\ durableCanonicalEffect # "CONSEQUENTIAL_WRITE"
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
    /\ UNCHANGED idemVars

SyncMeshExecuteReadOnly ==
    /\ declaredSyncEffect = "READ_ONLY"
    /\ canonicalSyncEffect = "READ_ONLY"
    /\ syncExecuted = 0
    /\ syncExecuted' = 1
    /\ syncExecutionPath' = "SyncMesh"
    /\ syncConsequentialEffects' = 0
    /\ UNCHANGED <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath>>
    /\ UNCHANGED idemVars

SyncMeshRejectUnsafeOrMismatched ==
    /\ canonicalSyncEffect # "READ_ONLY" \/ declaredSyncEffect # canonicalSyncEffect
    /\ UNCHANGED vars

Next ==
    \/ AdmitRequestA
    \/ AdmitRequestB
    \/ InjectNoncanonicalDuplicateFile
    \/ CorruptIndexToBDetected
    \/ CorruptIndexToADetected
    \/ DropAdmissionEvidence
    \/ CorruptIndexWithoutAdmissionEvidenceDetected
    \/ MutateCanonicalIdentity
    \/ CanonicalIdentityDriftDetected
    \/ LoseIdempotencyIndex
    \/ RecoverValidMissingIndex
    \/ InjectInvalidRecoveredMaterial
    \/ RecoverInvalidMaterialDetected
    \/ RecoveredInvalidClaimRejected
    \/ RecoveredInvalidResultRejected
    \/ Deliver
    \/ DuplicateDelivery
    \/ CanonicalClaimWrite
    \/ LostAck
    \/ DelayedAck
    \/ CanonicalReadProof
    \/ CanonicalReadUnavailable
    \/ Run
    \/ RunningReadReconcile
    \/ Terminalize
    \/ CancelBeforeLaunch
    \/ ForeignClaim
    \/ CandidateMismatch
    \/ LateForeignRunningAfterTerminal
    \/ NodeRestart
    \/ MeshRestart
    \/ DurableRemoteRejectUnknownPolicy
    \/ SyncMeshExecuteReadOnly
    \/ SyncMeshRejectUnsafeOrMismatched

Spec == Init /\ [][Next]_vars

(*
The liveness contract is intentionally narrower than safety. Safety must hold
through arbitrary duplicate delivery, ACK loss/delay, and restart interleavings.
Liveness is only promised once node/mesh/store are eventually healthy and the
enabled protocol progress actions receive weak fairness. This prevents the model
from "proving" or refuting useful liveness through infinite stutter or duplicate
delivery with no forward progress.
*)
FairSpec ==
    /\ Spec
    /\ WF_vars(AdmitRequestA)
    /\ WF_vars(Deliver)
    /\ WF_vars(CanonicalClaimWrite)
    /\ WF_vars(DurableRemoteRejectUnknownPolicy)
    /\ WF_vars(CorruptIndexWithoutAdmissionEvidenceDetected)
    /\ WF_vars(CanonicalIdentityDriftDetected)
    /\ WF_vars(RecoverInvalidMaterialDetected)
    /\ WF_vars(CanonicalReadProof)
    /\ WF_vars(Run)
    /\ WF_vars(Terminalize)

NoExecutionWithoutCanonicalAuthority == executed > 0 => authorityAtLaunch
AtMostOneExecutionPerLogicalRequest == executed <= 1
TerminalNeverRegresses == terminalSeen => state \in Terminal
TerminalNeverRelaunches == terminalSeen => executed <= 1
CancellationBeforeLaunchPreventsExecution == cancelled /\ state = "CANCELLED" => executed = 0
ForeignClaimNeverExecutes == candidate # expectedCandidate => executed = 0
CandidateMismatchNeverExecutes == candidate # expectedCandidate => executed = 0
NoConsequentialWriteViaSyncMesh == syncConsequentialEffects = 0
UnknownEffectNeverExecutesViaSyncMesh == canonicalSyncEffect = "UNKNOWN" => syncExecuted = 0
ReadOnlySyncDoesNotCreateConsequentialEffect == syncExecuted > 0 => canonicalSyncEffect = "READ_ONLY" /\ syncConsequentialEffects = 0
IncompleteMaterialNeverExecutes == ~MaterialComplete => executed = 0
IncompleteMaterialNeverBecomesDeliverable == ~MaterialComplete => ~recoveredDeliverable
ResultConvergenceRequiresValidMaterial == ResultConverged => MaterialValid
ResultCannotLegitimizeInvalidRequest ==
    ResultPresent /\ ~MaterialValid => state = "RECONCILIATION_REQUIRED" /\ executed = 0
DeclaredRiskCannotDowngradeCanonicalRisk ==
    CanonicalRisk # "read_only" /\ DeclaredRisk = "read_only" => syncExecuted = 0
DeclaredEffectCannotDowngradeCanonicalEffect ==
    canonicalSyncEffect = "CONSEQUENTIAL_WRITE" /\ declaredSyncEffect = "READ_ONLY" => syncExecuted = 0
ConsequentialExecutionRequiresCompatibleCanonicalRiskEffect ==
    executed > 0 => durableCanonicalEffect = "CONSEQUENTIAL_WRITE" /\ canonicalMaterialValid
CorruptRecordNeverExecutes == RecordCorrupt => executed = 0
CorruptRecordDoesNotBlockUnrelatedValidRequest ==
    RecordCorrupt /\ HasCanonicalIdempotency => state \in {"QUEUED", "CLAIMED", "RUNNING"} \cup Terminal
SyncExecutionRequiresCanonicalReadOnlyPolicy == syncExecuted > 0 => canonicalSyncEffect = "READ_ONLY" /\ declaredSyncEffect = "READ_ONLY"
ConsequentialExecutionImpliesDurableRemotePath == executed > 0 => durableExecutionPath = "DurableRemote"
DurableRemoteExecutionRequiresCanonicalConsequentialPolicy == executed > 0 => durableCanonicalEffect = "CONSEQUENTIAL_WRITE"
AtMostOneCanonicalRequestPerIdempotencyKey == \A k \in Keys: canonicalRequestForKey[k] \in Requests
SameLogicalOperationConvergesToSameCanonicalRequest ==
    requestAAdmitted /\ requestBAdmitted /\ requestAKey \in Keys
    /\ requestAKey = requestBKey /\ requestAPayload = requestBPayload
    => canonicalRequestForKey[requestAKey] \in {"A", "B"}
IdempotencyKeyCannotAuthorizeDifferentPayload ==
    requestAAdmitted /\ requestBAdmitted /\ requestAKey \in Keys
    /\ requestAKey = requestBKey /\ requestAPayload # requestBPayload
    => idempotencyConflict
IdempotencyKeyCannotForkTerminalTrajectory == terminalSeen => \A k \in Keys: canonicalRequestForKey[k] \in Requests
AtMostOneExecutionPerIdempotencyKey == executed <= 1
ConsequentialExecutionRequiresStableIdempotencyIdentity == executed > 0 => HasCanonicalIdempotency
MissingIdempotencyKeyNeverAdmitted ==
    ((requestAAdmitted /\ requestAKey = "none") \/ (requestBAdmitted /\ requestBKey = "none"))
    => idempotencyConflict
NoncanonicalDuplicateNeverExecutes == noncanonicalDuplicateExecuted = 0
DeliveryScanQuarantinesNoncanonicalDuplicate == duplicateRecoveryDone => ~noncanonicalDuplicateDeliverable
IndexMismatchWithAdmissionEvidenceFailsClosed ==
    \A k \in Keys:
        admittedRequestForKey[k] # "none" /\ canonicalRequestForKey[k] # "none"
        /\ admittedRequestForKey[k] # canonicalRequestForKey[k]
        => idempotencyConflict /\ ~noncanonicalDuplicateDeliverable
MissingAdmissionEvidenceWithMultipleRecordsFailsClosed ==
    \A k \in Keys:
        admittedRequestForKey[k] = "none" /\ canonicalRequestForKey[k] # "none"
        /\ noncanonicalDuplicatePersisted /\ noncanonicalDuplicateKey = k
        => idempotencyConflict /\ ~noncanonicalDuplicateDeliverable
CanonicalIdentityDriftNeverExecutes == ~canonicalMaterialValid => executed = 0
RecoveredInvalidMaterialNeverExecutes ==
    recoveredFromPersistence /\ ~recoveredMaterialValid => executed = 0
RecoveredInvalidMaterialNeverBecomesDeliverable ==
    recoveredFromPersistence /\ ~recoveredMaterialValid => ~recoveredDeliverable
RecoveredInvalidMaterialNeverBecomesRunning ==
    recoveredFromPersistence /\ ~recoveredMaterialValid => state # "RUNNING"
IndexRecoveryRequiresValidMaterial ==
    indexRecovered => recoveredMaterialValid
ResultCannotLegitimizeInvalidRecoveredRequest ==
    invalidRecoveredResultAttempt /\ recoveredFromPersistence /\ ~recoveredMaterialValid
    => state = "RECONCILIATION_REQUIRED" /\ executed = 0
ValidRecoveredRequestPreservesLogicalIdempotency ==
    recoveredFromPersistence /\ recoveredMaterialValid /\ indexRecovered => HasCanonicalIdempotency

EventuallyHealthy == <>[](meshUp /\ nodeUp)

EventualGovernedResolution ==
    (EventuallyHealthy /\ <>HasCanonicalIdempotency) => <>(state \in {"RUNNING"} \cup Terminal \/ idempotencyConflict)

====
