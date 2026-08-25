---- MODULE Wave2DurableRemote ----
EXTENDS Naturals, TLC

(*
Minimal Wave 2 DurableRemote authority model.

Scope:
- one logical durable request
- canonical lifecycle and claim ownership
- transport duplication/loss/delay/restart as nondeterministic interleavings
- execution marker and cancellation

This model intentionally excludes Docker, Windows process management, frontend
activation, and model-provider behavior. Those are adapter/lifecycle concerns
outside the critical durable authority protocol.
*)

VARIABLES state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects

vars == <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

Terminal == {"SUCCEEDED", "FAILED", "CANCELLED", "RECONCILIATION_REQUIRED"}
ClaimedLike == {"CLAIMED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"}

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
    /\ syncEffect \in {"READ_ONLY", "CONSEQUENTIAL_WRITE", "UNKNOWN"}
    /\ syncExecuted = 0
    /\ syncConsequentialEffects = 0

Deliver ==
    /\ state = "QUEUED"
    /\ delivered' = TRUE
    /\ UNCHANGED <<state, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

DuplicateDelivery ==
    /\ delivered
    /\ state \in {"QUEUED", "CLAIMED", "RUNNING"} \cup Terminal
    /\ UNCHANGED vars

CanonicalClaimWrite ==
    /\ state = "QUEUED"
    /\ delivered
    /\ meshUp /\ nodeUp
    /\ state' = "CLAIMED"
    /\ claim' = "claim1"
    /\ UNCHANGED <<delivered, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

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
    /\ UNCHANGED <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, authorityAtLaunch, terminalSeen, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

CanonicalReadUnavailable ==
    /\ state \in {"QUEUED", "CLAIMED"}
    /\ delivered
    /\ proof = FALSE
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

Run ==
    /\ state = "CLAIMED"
    /\ proof
    /\ ~cancelled
    /\ claim = "claim1"
    /\ candidate = expectedCandidate
    /\ state' = "RUNNING"
    /\ executed' = executed + 1
    /\ authorityAtLaunch' = TRUE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, proof, terminalSeen, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

RunningReadReconcile ==
    /\ state = "RUNNING"
    /\ proof
    /\ UNCHANGED vars

Terminalize ==
    /\ state = "RUNNING"
    /\ state' \in {"SUCCEEDED", "FAILED"}
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

CancelBeforeLaunch ==
    /\ state \in {"QUEUED", "CLAIMED"}
    /\ executed = 0
    /\ cancelled' = TRUE
    /\ state' = "CANCELLED"
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, executed, proof, authorityAtLaunch, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

ForeignClaim ==
    /\ state \in {"QUEUED", "CLAIMED"}
    /\ delivered
    /\ claim # "none"
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

CandidateMismatch ==
    /\ state \in {"QUEUED", "CLAIMED"}
    /\ delivered
    /\ candidate' = "foreign"
    /\ state' = "RECONCILIATION_REQUIRED"
    /\ terminalSeen' = TRUE
    /\ UNCHANGED <<delivered, claim, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, meshUp, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

LateForeignRunningAfterTerminal ==
    /\ state \in Terminal
    /\ UNCHANGED vars

NodeRestart ==
    /\ nodeUp' = ~nodeUp
    /\ proof' = FALSE
    /\ UNCHANGED <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, authorityAtLaunch, terminalSeen, meshUp, syncEffect, syncExecuted, syncConsequentialEffects>>

MeshRestart ==
    /\ meshUp' = ~meshUp
    /\ UNCHANGED <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, nodeUp, syncEffect, syncExecuted, syncConsequentialEffects>>

SyncMeshExecuteReadOnly ==
    /\ syncEffect = "READ_ONLY"
    /\ syncExecuted = 0
    /\ syncExecuted' = 1
    /\ syncConsequentialEffects' = 0
    /\ UNCHANGED <<state, delivered, claim, candidate, expectedCandidate, cancelled, executed, proof, authorityAtLaunch, terminalSeen, meshUp, nodeUp, syncEffect>>

SyncMeshRejectNonReadOnly ==
    /\ syncEffect \in {"CONSEQUENTIAL_WRITE", "UNKNOWN"}
    /\ UNCHANGED vars

Next ==
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
    \/ SyncMeshExecuteReadOnly
    \/ SyncMeshRejectNonReadOnly

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
    /\ WF_vars(Deliver)
    /\ WF_vars(CanonicalClaimWrite)
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
UnknownEffectNeverExecutesViaSyncMesh == syncEffect = "UNKNOWN" => syncExecuted = 0
ReadOnlySyncDoesNotCreateConsequentialEffect == syncExecuted > 0 => syncEffect = "READ_ONLY" /\ syncConsequentialEffects = 0

EventuallyHealthy == <>[](meshUp /\ nodeUp)

EventualGovernedResolution ==
    EventuallyHealthy => <>(state \in {"RUNNING"} \cup Terminal)

====
