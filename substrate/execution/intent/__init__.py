"""UMH MVP intent → proof operating loop (P4S-31).

The thinnest UMH operating-loop skeleton: operator intent → deterministic
IntentSpec → WorkPacketDraft → governed approval gate → proof record → read
surface. Composes existing substrate primitives (IntentRouter, intent risk
table, WorkPacketStatus/Priority, governed_mutation) — it adds no parallel
classifier, type system, or mutation runtime.
"""

from __future__ import annotations

from substrate.execution.intent.intent_spec import (
    IntentKind,
    IntentLoopStage,
    IntentSpec,
    WorkPacketDraft,
)
from substrate.execution.intent.loop import (
    APPROVAL_MUTATION_NAME,
    IntentLoop,
    IntentLoopRecord,
    IntentLoopStore,
    ProofRecord,
    read_intent_loop_surface,
)

__all__ = [
    "APPROVAL_MUTATION_NAME",
    "IntentLoop",
    "IntentLoopRecord",
    "IntentLoopStage",
    "IntentLoopStore",
    "IntentSpec",
    "IntentKind",
    "ProofRecord",
    "WorkPacketDraft",
    "read_intent_loop_surface",
]
