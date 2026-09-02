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

VARIABLES state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt, readErrorPresent, evidenceIncomplete, attemptStoreUnknownCorruption, unsafeDuplicateAuthority, corruptRequestMaterialPresent, corruptRequestRecoverableKey, corruptRequestSerializedIdentity

protocolVars == <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
idemVars == <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt, readErrorPresent, evidenceIncomplete, attemptStoreUnknownCorruption, unsafeDuplicateAuthority, corruptRequestMaterialPresent, corruptRequestRecoverableKey, corruptRequestSerializedIdentity>>
vars == <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects, requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt, readErrorPresent, evidenceIncomplete, attemptStoreUnknownCorruption, unsafeDuplicateAuthority, corruptRequestMaterialPresent, corruptRequestRecoverableKey, corruptRequestSerializedIdentity>>
IntegrityUnchanged == UNCHANGED <<readErrorPresent, evidenceIncomplete, attemptStoreUnknownCorruption, unsafeDuplicateAuthority, corruptRequestMaterialPresent, corruptRequestRecoverableKey, corruptRequestSerializedIdentity>>

Terminal == {"SUCCEEDED", "FAILED", "CANCELLED", "RECONCILIATION_REQUIRED"}
ClaimedLike == {"CLAIMED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"}
Keys == {"key1", "key2"}
MaybeKey == Keys \cup {"none"}
SerializedIdentities == {"none", "unknown", "key1_raw", "key1_escaped", "key2_raw", "key2_escaped"}
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
ArtifactStates == {"ABSENT", "VALID", "CORRUPT", "READ_ERROR"}
RequestArtifact ==
    IF readErrorPresent
    THEN "READ_ERROR"
    ELSE IF RecordCorrupt
    THEN "CORRUPT"
    ELSE IF HasCanonicalIdempotency \/ recoveredFromPersistence
    THEN "VALID"
    ELSE "ABSENT"
IndexArtifact ==
    IF readErrorPresent
    THEN "READ_ERROR"
    ELSE IF idempotencyConflict /\ duplicateRecoveryDone /\ ~indexPresent
    THEN "CORRUPT"
    ELSE IF indexPresent
    THEN "VALID"
    ELSE "ABSENT"
ResultArtifact ==
    IF readErrorPresent
    THEN "READ_ERROR"
    ELSE IF invalidRecoveredResultAttempt /\ ~MaterialValid
    THEN "CORRUPT"
    ELSE IF ResultPresent
    THEN "VALID"
    ELSE "ABSENT"
CanonicalIdentity(serialized) ==
    IF serialized \in {"key1_raw", "key1_escaped"}
    THEN "key1"
    ELSE IF serialized \in {"key2_raw", "key2_escaped"}
    THEN "key2"
    ELSE "none"
CorruptRequestFencesKey(k) ==
    corruptRequestMaterialPresent
    /\ (
        corruptRequestRecoverableKey = k
        \/ CanonicalIdentity(corruptRequestSerializedIdentity) = k
        \/ corruptRequestRecoverableKey = "none"
    )
BindingState(k) ==
    IF canonicalRequestForKey[k] # "none"
    THEN "BOUND"
    ELSE IF idempotencyConflict
    THEN "AMBIGUOUS"
    ELSE "PROVEN_ABSENT"
IntegrityState(k) ==
    IF readErrorPresent
    THEN "READ_ERROR"
    ELSE IF evidenceIncomplete
    THEN "INCOMPLETE_EVIDENCE"
    ELSE IF CorruptRequestFencesKey(k)
    THEN "CORRUPT_FENCED"
    ELSE "CLEAN"
FreshAuthorityProvenAbsent(k) ==
    /\ BindingState(k) = "PROVEN_ABSENT"
    /\ IntegrityState(k) = "CLEAN"
    /\ ~CorruptRequestFencesKey(k)
    /\ ~readErrorPresent
    /\ ~evidenceIncomplete

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
    /\ readErrorPresent = FALSE
    /\ evidenceIncomplete = FALSE
    /\ attemptStoreUnknownCorruption = FALSE
    /\ unsafeDuplicateAuthority = FALSE
    /\ corruptRequestMaterialPresent = FALSE
    /\ corruptRequestRecoverableKey = "none"
    /\ corruptRequestSerializedIdentity = "none"

AdmitRequestA ==
    /\ ~requestAAdmitted
    /\ requestAAdmitted' = TRUE
    /\ IF requestAKey = "none"
        THEN
            /\ canonicalRequestForKey' = canonicalRequestForKey
            /\ admittedRequestForKey' = admittedRequestForKey
            /\ canonicalPayloadForKey' = canonicalPayloadForKey
            /\ idempotencyConflict' = TRUE
        ELSE IF canonicalRequestForKey[requestAKey] = "none" /\ FreshAuthorityProvenAbsent(requestAKey)
        THEN
            /\ canonicalRequestForKey' = [canonicalRequestForKey EXCEPT ![requestAKey] = "A"]
            /\ admittedRequestForKey' =
                IF admittedRequestForKey[requestAKey] = "none"
                THEN [admittedRequestForKey EXCEPT ![requestAKey] = "A"]
                ELSE admittedRequestForKey
            /\ canonicalPayloadForKey' = [canonicalPayloadForKey EXCEPT ![requestAKey] = requestAPayload]
            /\ indexPresent' = TRUE
            /\ idempotencyConflict' = idempotencyConflict
        ELSE IF canonicalRequestForKey[requestAKey] = "none"
        THEN
            /\ canonicalRequestForKey' = canonicalRequestForKey
            /\ admittedRequestForKey' = admittedRequestForKey
            /\ canonicalPayloadForKey' = canonicalPayloadForKey
            /\ indexPresent' = indexPresent
            /\ idempotencyConflict' = TRUE
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
    /\ IntegrityUnchanged

AdmitRequestB ==
    /\ ~requestBAdmitted
    /\ requestBAdmitted' = TRUE
    /\ IF requestBKey = "none"
        THEN
            /\ canonicalRequestForKey' = canonicalRequestForKey
            /\ admittedRequestForKey' = admittedRequestForKey
            /\ canonicalPayloadForKey' = canonicalPayloadForKey
            /\ idempotencyConflict' = TRUE
        ELSE IF canonicalRequestForKey[requestBKey] = "none" /\ FreshAuthorityProvenAbsent(requestBKey)
        THEN
            /\ canonicalRequestForKey' = [canonicalRequestForKey EXCEPT ![requestBKey] = "B"]
            /\ admittedRequestForKey' =
                IF admittedRequestForKey[requestBKey] = "none"
                THEN [admittedRequestForKey EXCEPT ![requestBKey] = "B"]
                ELSE admittedRequestForKey
            /\ canonicalPayloadForKey' = [canonicalPayloadForKey EXCEPT ![requestBKey] = requestBPayload]
            /\ indexPresent' = TRUE
            /\ idempotencyConflict' = idempotencyConflict
        ELSE IF canonicalRequestForKey[requestBKey] = "none"
        THEN
            /\ canonicalRequestForKey' = canonicalRequestForKey
            /\ admittedRequestForKey' = admittedRequestForKey
            /\ canonicalPayloadForKey' = canonicalPayloadForKey
            /\ indexPresent' = indexPresent
            /\ idempotencyConflict' = TRUE
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
    /\ IntegrityUnchanged

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
    /\ IntegrityUnchanged

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
    /\ IntegrityUnchanged

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
    /\ IntegrityUnchanged

DropAdmissionEvidence ==
    /\ ~noncanonicalDuplicatePersisted
    /\ \E k \in Keys:
        /\ admittedRequestForKey[k] # "none"
        /\ admittedRequestForKey' = [admittedRequestForKey EXCEPT ![k] = "none"]
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars
    /\ IntegrityUnchanged

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
    /\ IntegrityUnchanged

MutateCanonicalIdentity ==
    /\ HasCanonicalIdempotency
    /\ canonicalMaterialValid
    /\ executed = 0
    /\ canonicalMaterialValid' = FALSE
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars
    /\ IntegrityUnchanged

CanonicalIdentityDriftDetected ==
    /\ HasCanonicalIdempotency
    /\ ~canonicalMaterialValid
    /\ idempotencyConflict' = TRUE
    /\ noncanonicalDuplicateDeliverable' = FALSE
    /\ duplicateRecoveryDone' = TRUE
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars
    /\ IntegrityUnchanged

LoseIdempotencyIndex ==
    /\ HasCanonicalIdempotency
    /\ indexPresent
    /\ indexPresent' = FALSE
    /\ indexRecovered' = FALSE
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt>>
    /\ UNCHANGED protocolVars
    /\ IntegrityUnchanged

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
    /\ IntegrityUnchanged

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
    /\ IntegrityUnchanged

InjectCorruptRequestWithRecoverableKey ==
    /\ ~corruptRequestMaterialPresent
    /\ executed = 0
    /\ corruptRequestMaterialPresent' = TRUE
    /\ corruptRequestSerializedIdentity' \in SerializedIdentities
    /\ corruptRequestRecoverableKey' = CanonicalIdentity(corruptRequestSerializedIdentity')
    /\ UNCHANGED protocolVars
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt, readErrorPresent, evidenceIncomplete, attemptStoreUnknownCorruption, unsafeDuplicateAuthority>>

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
    /\ IntegrityUnchanged

RecoveredInvalidClaimRejected ==
    /\ recoveredFromPersistence
    /\ ~recoveredMaterialValid
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ recoveredDeliverable' = FALSE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, invalidRecoveredResultAttempt>>
    /\ IntegrityUnchanged

RecoveredInvalidResultRejected ==
    /\ recoveredFromPersistence
    /\ ~recoveredMaterialValid
    /\ invalidRecoveredResultAttempt' = TRUE
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ recoveredDeliverable' = FALSE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid>>
    /\ IntegrityUnchanged

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
    /\ IntegrityUnchanged

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

ReadErrorDetected ==
    /\ ~readErrorPresent
    /\ executed = 0
    /\ ~authorityAtLaunch
    /\ readErrorPresent' = TRUE
    /\ evidenceIncomplete' = TRUE
    /\ idempotencyConflict' = TRUE
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ noncanonicalDuplicateDeliverable' = FALSE
    /\ recoveredDeliverable' = FALSE
    /\ unsafeDuplicateAuthority' = FALSE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, invalidRecoveredResultAttempt, attemptStoreUnknownCorruption, corruptRequestMaterialPresent, corruptRequestRecoverableKey, corruptRequestSerializedIdentity>>

AttemptStoreUnknownCorruptionDetected ==
    /\ ~attemptStoreUnknownCorruption
    /\ executed = 0
    /\ ~authorityAtLaunch
    /\ attemptStoreUnknownCorruption' = TRUE
    /\ evidenceIncomplete' = TRUE
    /\ idempotencyConflict' = TRUE
    /\ unsafeDuplicateAuthority' = FALSE
    /\ UNCHANGED <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt, readErrorPresent, corruptRequestMaterialPresent, corruptRequestRecoverableKey, corruptRequestSerializedIdentity>>

UnsafeDuplicateAuthorityAttempt ==
    /\ evidenceIncomplete
    /\ unsafeDuplicateAuthority' = FALSE
    /\ UNCHANGED <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, declaredSyncEffect, canonicalSyncEffect, durableCanonicalEffect, durableExecutionPath, syncExecutionPath, syncExecuted, syncConsequentialEffects>>
    /\ UNCHANGED <<requestAAdmitted, requestBAdmitted, requestAKey, requestBKey, requestAPayload, requestBPayload, canonicalRequestForKey, admittedRequestForKey, canonicalPayloadForKey, canonicalMaterialValid, idempotencyConflict, noncanonicalDuplicatePersisted, noncanonicalDuplicateKey, noncanonicalDuplicateDeliverable, duplicateRecoveryDone, noncanonicalDuplicateExecuted, recoveredFromPersistence, indexPresent, indexRecovered, recoveredMaterialValid, recoveredDeliverable, invalidRecoveredResultAttempt, readErrorPresent, evidenceIncomplete, attemptStoreUnknownCorruption, corruptRequestMaterialPresent, corruptRequestRecoverableKey, corruptRequestSerializedIdentity>>

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
    \/ InjectCorruptRequestWithRecoverableKey
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
    \/ ReadErrorDetected
    \/ AttemptStoreUnknownCorruptionDetected
    \/ UnsafeDuplicateAuthorityAttempt

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
CorruptRequestNeverExecutes == RequestArtifact = "CORRUPT" => executed = 0
CorruptIndexNeverCreatesFreshAuthority ==
    IndexArtifact = "CORRUPT" => idempotencyConflict /\ noncanonicalDuplicateExecuted = 0
CorruptIndexIsNotEquivalentToAbsent ==
    IndexArtifact = "CORRUPT" => idempotencyConflict
CorruptResultNeverLegitimizesExecution ==
    ResultArtifact = "CORRUPT" => ~ResultConverged
CorruptResultNeverSilentlyOverwritten ==
    ResultArtifact = "CORRUPT" => ResultArtifact # "VALID"
CorruptArtifactCannotBeRepairedByNormalExecution ==
    RequestArtifact = "CORRUPT" \/ ResultArtifact = "CORRUPT"
    => executed = 0 \/ state = "RECONCILIATION_REQUIRED"
ReadErrorNeverCreatesAuthority ==
    readErrorPresent => executed = 0 /\ ~authorityAtLaunch
ReadErrorIsNotAbsent ==
    readErrorPresent => RequestArtifact = "READ_ERROR" /\ IndexArtifact = "READ_ERROR" /\ ResultArtifact = "READ_ERROR"
CorruptRequestWithRecoverableKeyPreventsFreshAuthority ==
    \A k \in Keys:
        CorruptRequestFencesKey(k)
        => ~(canonicalRequestForKey[k] = "none" /\ admittedRequestForKey[k] # "none")
NoFreshAuthorityWithoutProvenAbsence ==
    \A k \in Keys:
        CorruptRequestFencesKey(k) => ~FreshAuthorityProvenAbsent(k)
CorruptFenceIsNotAbsent ==
    \A k \in Keys:
        CorruptRequestFencesKey(k) => corruptRequestMaterialPresent
IncompleteEvidenceIsNotAbsent ==
    evidenceIncomplete => idempotencyConflict
CorruptionFenceSurvivesRecovery ==
    \A k \in Keys:
        CorruptRequestFencesKey(k) /\ (meshUp \/ nodeUp)
        => IntegrityState(k) # "CLEAN"
BoundAndCorruptFencedIsRepresentable ==
    \A k \in Keys:
        canonicalRequestForKey[k] # "none" /\ CorruptRequestFencesKey(k)
        => BindingState(k) = "BOUND" /\ IntegrityState(k) # "CLEAN"
BoundAndCorruptFencedNeverCreatesSecondRequest ==
    \A k \in Keys:
        BindingState(k) = "BOUND" /\ IntegrityState(k) = "CORRUPT_FENCED"
        => ~FreshAuthorityProvenAbsent(k) /\ canonicalRequestForKey[k] \in Requests
CorruptRequestWithEquivalentSerializedKeyPreventsFreshAuthority ==
    \A k \in Keys:
        corruptRequestMaterialPresent /\ CanonicalIdentity(corruptRequestSerializedIdentity) = k
        => ~FreshAuthorityProvenAbsent(k)
EquivalentSerializedIdentityCannotBypassFence ==
    /\ (corruptRequestSerializedIdentity = "key1_raw" \/ corruptRequestSerializedIdentity = "key1_escaped")
       /\ corruptRequestMaterialPresent => ~FreshAuthorityProvenAbsent("key1")
    /\ (corruptRequestSerializedIdentity = "key2_raw" \/ corruptRequestSerializedIdentity = "key2_escaped")
       /\ corruptRequestMaterialPresent => ~FreshAuthorityProvenAbsent("key2")
UnknownRecoveredIdentityNeverGrantsAuthority ==
    corruptRequestMaterialPresent /\ CanonicalIdentity(corruptRequestSerializedIdentity) = "none"
    => \A k \in Keys: ~FreshAuthorityProvenAbsent(k)
CorruptArtifactIsNotAbsent ==
    /\ RequestArtifact = "CORRUPT" => RequestArtifact # "ABSENT"
    /\ IndexArtifact = "CORRUPT" => IndexArtifact # "ABSENT"
    /\ ResultArtifact = "CORRUPT" => ResultArtifact # "ABSENT"
InvalidMaterialNeverExecutes == ~MaterialValid => executed = 0
IncompleteEvidenceCannotProveAuthority == evidenceIncomplete => ~authorityAtLaunch
UnknownAuthorityRecordPreventsUnsafeDuplicateAuthority ==
    attemptStoreUnknownCorruption => ~unsafeDuplicateAuthority
ValidRequestCanProgressBesideUnrelatedCorruptRecord ==
    RecordCorrupt /\ HasCanonicalIdempotency /\ ~idempotencyConflict
    => state \in {"QUEUED", "CLAIMED", "RUNNING"} \cup Terminal
IndexRecoveryRequiresProvableValidBinding ==
    indexRecovered /\ ~readErrorPresent
    => IndexArtifact = "VALID" /\ recoveredMaterialValid /\ HasCanonicalIdempotency
ResultConvergenceRequiresValidRequestAndValidResult ==
    ResultConverged => MaterialValid /\ ResultArtifact = "VALID"
SyncExecutionRequiresCanonicalReadOnlyPolicy == syncExecuted > 0 => canonicalSyncEffect = "READ_ONLY" /\ declaredSyncEffect = "READ_ONLY"
ConsequentialExecutionImpliesDurableRemotePath == executed > 0 => durableExecutionPath = "DurableRemote"
DurableRemoteExecutionRequiresCanonicalConsequentialPolicy == executed > 0 => durableCanonicalEffect = "CONSEQUENTIAL_WRITE"
AtMostOneCanonicalRequestPerIdempotencyKey == \A k \in Keys: canonicalRequestForKey[k] \in Requests
SameLogicalOperationConvergesToSameCanonicalRequest ==
    requestAAdmitted /\ requestBAdmitted /\ requestAKey \in Keys
    /\ requestAKey = requestBKey /\ requestAPayload = requestBPayload
    /\ ~idempotencyConflict => canonicalRequestForKey[requestAKey] \in {"A", "B"}
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
