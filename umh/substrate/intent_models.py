"""
Intent and Plan models for the intelligence layer.

Intents represent structured goals: "finalize this session,"
"execute this primitive," "run this workflow."  Plans are
deterministic step sequences derived from intent type + state.

Both are pure data — no execution, no side effects.

Storage convention:
    Intents live in RuntimeStateStore under the key prefix "intent:".
    Example: store.get("intent:int_abc123") → serialised Intent dict.
    Active intent membership is keyed: active_intent.{intent_id} → metadata dict.
    Uses SET for add/update, REMOVE for deactivation.

Design constraints:
    - Frozen dataclasses for immutability after creation.
    - to_dict / from_dict for store serialisation (plain dicts only).
    - Deterministic: no randomness in any construction path.
    - Plan steps are value objects — same inputs always produce same steps.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ─── Enums ────────────────────────────────────────────────────────────


class IntentType(str, Enum):
    """Categories of intent the planner can reason about."""

    LIFECYCLE_FINALIZE = "lifecycle_finalize"
    LIFECYCLE_PUBLISH = "lifecycle_publish"
    LIFECYCLE_CLEAR = "lifecycle_clear"
    EXECUTION_REQUEST = "execution_request"
    WORKFLOW_RUN = "workflow_run"
    CUSTOM = "custom"


class IntentStatus(str, Enum):
    """Lifecycle states of an intent."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


# ─── Intent ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Intent:
    """A structured goal to be achieved through a plan.

    Fields:
        intent_id:       Deterministic ID derived from type + goal hash.
        intent_type:     What category of goal this represents.
        goal:            Structured payload describing the desired outcome.
        priority:        Lower number = higher priority (evaluated first).
        status:          Current lifecycle state.
        created_at:      ISO timestamp of creation.
        session_name:    Scoping — which session this intent belongs to.
        current_step:    Index of the next step to execute (0-based).
        total_steps:     Total steps in the derived plan (set after planning).
        metadata:        Optional tracing/diagnostic data.
    """

    intent_id: str
    intent_type: IntentType
    goal: dict[str, Any]
    priority: int = 100
    status: IntentStatus = IntentStatus.PENDING
    created_at: str = ""
    session_name: str = ""
    current_step: int = 0
    total_steps: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.created_at:
            # Frozen — use object.__setattr__ for init-time defaults
            object.__setattr__(
                self,
                "created_at",
                datetime.now(timezone.utc).isoformat(),
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict for store persistence."""
        return {
            "intent_id": self.intent_id,
            "intent_type": self.intent_type.value,
            "goal": self.goal,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at,
            "session_name": self.session_name,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Intent:
        """Reconstruct from a plain dict."""
        return Intent(
            intent_id=d["intent_id"],
            intent_type=IntentType(d["intent_type"]),
            goal=d["goal"],
            priority=d.get("priority", 100),
            status=IntentStatus(d.get("status", "pending")),
            created_at=d.get("created_at", ""),
            session_name=d.get("session_name", ""),
            current_step=d.get("current_step", 0),
            total_steps=d.get("total_steps", 0),
            metadata=d.get("metadata", {}),
        )

    def with_status(self, status: IntentStatus) -> Intent:
        """Return a copy with updated status."""
        d = self.to_dict()
        d["status"] = status.value
        return Intent.from_dict(d)

    def with_step_advanced(self) -> Intent:
        """Return a copy with current_step incremented by 1."""
        d = self.to_dict()
        d["current_step"] = self.current_step + 1
        return Intent.from_dict(d)

    def with_total_steps(self, n: int) -> Intent:
        """Return a copy with total_steps set."""
        d = self.to_dict()
        d["total_steps"] = n
        return Intent.from_dict(d)

    @property
    def is_terminal(self) -> bool:
        """True if the intent is in a terminal state."""
        return self.status in (IntentStatus.COMPLETED, IntentStatus.FAILED)

    @property
    def steps_remaining(self) -> int:
        """Number of steps left to execute."""
        return max(0, self.total_steps - self.current_step)


# ─── Plan step ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PlanStep:
    """A single step in a plan.

    Maps directly to one SchedulerEvent emission.

    Fields:
        step_index:     Position in the plan (0-based).
        event_type:     The event type this step emits.
        payload:        The event payload (may reference intent goal fields).
        description:    Human-readable description of what this step does.
    """

    step_index: int
    event_type: str
    payload: dict[str, Any]
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "event_type": self.event_type,
            "payload": dict(self.payload),
            "description": self.description,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> PlanStep:
        return PlanStep(
            step_index=d["step_index"],
            event_type=d["event_type"],
            payload=d.get("payload", {}),
            description=d.get("description", ""),
        )


# ─── Plan ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Plan:
    """A deterministic sequence of steps derived from an intent.

    Plans are NOT persisted — they are re-derived from intent type +
    state on every evaluation.  This guarantees replay consistency:
    same state always produces the same plan.

    Fields:
        plan_id:     Deterministic ID derived from intent_id + step hashes.
        intent_id:   The intent this plan serves.
        steps:       Ordered sequence of PlanSteps.
        variant_id:  Stable identifier of the plan variant that produced
                     this plan.  Used for plan memory keying.  Empty string
                     when not using multi-variant selection.
    """

    plan_id: str
    intent_id: str
    steps: tuple[PlanStep, ...] = ()
    variant_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "intent_id": self.intent_id,
            "steps": [s.to_dict() for s in self.steps],
            "variant_id": self.variant_id,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> Plan:
        return Plan(
            plan_id=d["plan_id"],
            intent_id=d["intent_id"],
            steps=tuple(PlanStep.from_dict(s) for s in d.get("steps", [])),
            variant_id=d.get("variant_id", ""),
        )

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def step_at(self, index: int) -> PlanStep | None:
        """Get step at index, or None if out of bounds."""
        if 0 <= index < len(self.steps):
            return self.steps[index]
        return None


# ─── Deterministic ID helpers ─────────────────────────────────────────


def compute_intent_id(intent_type: IntentType, goal: dict[str, Any]) -> str:
    """Deterministic intent ID from type + goal.

    Same type + same goal always produces the same ID.
    """
    canonical = json.dumps(
        {"type": intent_type.value, "goal": goal},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"int_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def compute_plan_id(intent_id: str, steps: tuple[PlanStep, ...]) -> str:
    """Deterministic plan ID from intent + step sequence.

    Same intent + same steps always produces the same ID.
    """
    step_data = [{"i": s.step_index, "e": s.event_type, "p": s.payload} for s in steps]
    canonical = json.dumps(
        {"intent_id": intent_id, "steps": step_data},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"pln_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ─── State mutation helpers ───────────────────────────────────────────


def intent_store_key(intent_id: str) -> str:
    """RuntimeStateStore key for a given intent."""
    return f"intent:{intent_id}"


def build_intent_create_mutations(intent: Intent) -> list[dict[str, Any]]:
    """Build mutations to persist a new intent into the store.

    Writes both the intent record (intent:{id}) and the active membership
    index entry (active_intent.{id}).  The keyed index stores metadata
    for fast enumeration without loading full intent records.
    """
    return [
        {
            "op": "SET",
            "key": intent_store_key(intent.intent_id),
            "value": intent.to_dict(),
        },
        {
            "op": "SET",
            "key": f"active_intent.{intent.intent_id}",
            "value": {
                "priority": intent.priority,
                "intent_type": intent.intent_type.value,
                "status": intent.status.value,
                "activated_at": intent.created_at,
                "current_step": intent.current_step,
                "total_steps": intent.total_steps,
            },
        },
    ]


def build_intent_update_mutations(intent: Intent) -> list[dict[str, Any]]:
    """Build mutations to update an existing intent in the store.

    Updates the intent record and syncs the keyed active index.
    If the intent is terminal, removes the active membership key.
    Otherwise, updates the index with current step/status.
    """
    mutations: list[dict[str, Any]] = [
        {
            "op": "SET",
            "key": intent_store_key(intent.intent_id),
            "value": intent.to_dict(),
        },
    ]
    if intent.is_terminal:
        mutations.append(
            {"op": "REMOVE", "key": f"active_intent.{intent.intent_id}"},
        )
    else:
        mutations.append(
            {
                "op": "SET",
                "key": f"active_intent.{intent.intent_id}",
                "value": {
                    "priority": intent.priority,
                    "intent_type": intent.intent_type.value,
                    "status": intent.status.value,
                    "activated_at": intent.created_at,
                    "current_step": intent.current_step,
                    "total_steps": intent.total_steps,
                },
            },
        )
    return mutations


def get_intent_from_state(state: dict[str, Any], intent_id: str) -> Intent | None:
    """Extract an intent from a state snapshot dict."""
    key = intent_store_key(intent_id)
    raw = state.get(key)
    if raw is None:
        return None
    return Intent.from_dict(raw)


def get_active_intents_from_state(state: dict[str, Any]) -> list[Intent]:
    """Extract all active intents from a state snapshot, sorted by priority.

    Scans the keyed active_intent.{id} index entries, loads full intent
    records, and returns non-terminal intents sorted by (priority, created_at, id).
    """
    prefix = "active_intent."
    intent_ids: list[str] = [k[len(prefix) :] for k in state if k.startswith(prefix)]
    intents: list[Intent] = []
    for iid in intent_ids:
        intent = get_intent_from_state(state, iid)
        if intent is not None and not intent.is_terminal:
            intents.append(intent)
    intents.sort(key=lambda i: (i.priority, i.created_at, i.intent_id))
    return intents
