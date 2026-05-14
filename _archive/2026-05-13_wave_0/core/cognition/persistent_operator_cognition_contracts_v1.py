"""Persistent Operator Cognition Contracts v1.

Data shapes for persistent operator cognition:
  OperatorCognitiveState → WorkingCognitionWindow →
  ActiveOperationalFocus → OpenOperationalLoop →
  CognitiveCheckpoint → TemporalExecutionContext →
  OperationalIntentState → RuntimeAttentionMap →
  ContinuityFocusState → CognitiveLineageReceipt

These sit above the Phase 96.8BS workflow contracts,
adding persistent working cognition, operational
attention, temporal continuity, and focus management.

The substrate maintains operational continuity.
The operator still owns intentionality.

All contracts are immutable after creation. All carry provenance.
All serialize deterministically.

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:16]}"


def _content_hash(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CognitionPhase(str, Enum):
    INITIALIZED = "initialized"
    ACTIVE = "active"
    FOCUSED = "focused"
    CHECKPOINTED = "checkpointed"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    STALE = "stale"
    ARCHIVED = "archived"
    TERMINATED = "terminated"


class OperatorMode(str, Enum):
    FOCUSED_EXECUTION = "focused_execution"
    OPERATIONAL_SUPERVISION = "operational_supervision"
    CONTINUITY_RESUME = "continuity_resume"
    INSPECTION_MODE = "inspection_mode"
    PLANNING_MODE = "planning_mode"


class LoopState(str, Enum):
    ACTIVE = "active"
    WAITING = "waiting"
    SUSPENDED = "suspended"
    STALE = "stale"
    RESUMED = "resumed"
    RESOLVED = "resolved"
    ARCHIVED = "archived"


class AttentionWeightType(str, Enum):
    CONTINUITY = "continuity"
    TEMPORAL = "temporal"
    WORKFLOW = "workflow"
    EMBODIMENT = "embodiment"
    LOOP_URGENCY = "loop_urgency"
    OPERATOR_FOCUS = "operator_focus"


class CognitionEventType(str, Enum):
    COGNITION_INITIALIZED = "cognition_initialized"
    FOCUS_SHIFTED = "focus_shifted"
    LOOP_OPENED = "loop_opened"
    LOOP_RESOLVED = "loop_resolved"
    CONTINUITY_RESTORED = "continuity_restored"
    CHECKPOINT_CREATED = "cognition_checkpoint_created"
    ATTENTION_REWEIGHTED = "attention_reweighted"
    TEMPORAL_SNAPSHOT_CREATED = "temporal_snapshot_created"
    COGNITION_RESUMED = "cognition_resumed"
    COGNITION_ARCHIVED = "cognition_archived"


class CognitionDecisionType(str, Enum):
    FOCUS_SHIFT = "focus_shift"
    ATTENTION_REWEIGHT = "attention_reweight"
    LOOP_PRIORITIZE = "loop_prioritize"
    CONTINUITY_RESTORE = "continuity_restore"
    CHECKPOINT = "checkpoint"
    STALE_SUPPRESS = "stale_suppress"
    MODE_TRANSITION = "mode_transition"


# ---------------------------------------------------------------------------
# Mode permissions
# ---------------------------------------------------------------------------

MODE_COGNITION_POLICIES: dict[str, dict[str, Any]] = {
    "focused_execution": {
        "cognition_persistence_depth": 3,
        "attention_decay_factor": 0.9,
        "continuity_retention_hours": 4,
        "workflow_visibility": "active_only",
        "open_loop_persistence": True,
        "checkpoint_frequency": "per_workflow",
        "description": "Focused on current execution, minimal historical cognition",
    },
    "operational_supervision": {
        "cognition_persistence_depth": 5,
        "attention_decay_factor": 0.8,
        "continuity_retention_hours": 12,
        "workflow_visibility": "all_recent",
        "open_loop_persistence": True,
        "checkpoint_frequency": "per_step",
        "description": "Broad operational awareness, moderate retention",
    },
    "continuity_resume": {
        "cognition_persistence_depth": 8,
        "attention_decay_factor": 0.6,
        "continuity_retention_hours": 48,
        "workflow_visibility": "all",
        "open_loop_persistence": True,
        "checkpoint_frequency": "on_change",
        "description": "Deep continuity restoration, high retention",
    },
    "inspection_mode": {
        "cognition_persistence_depth": 2,
        "attention_decay_factor": 0.95,
        "continuity_retention_hours": 1,
        "workflow_visibility": "active_only",
        "open_loop_persistence": False,
        "checkpoint_frequency": "none",
        "description": "Read-only inspection, minimal persistence",
    },
    "planning_mode": {
        "cognition_persistence_depth": 6,
        "attention_decay_factor": 0.7,
        "continuity_retention_hours": 24,
        "workflow_visibility": "all_recent",
        "open_loop_persistence": True,
        "checkpoint_frequency": "per_decision",
        "description": "Planning context, moderate depth, high relevance weighting",
    },
}


# ---------------------------------------------------------------------------
# Contract 1: OperatorCognitiveState
# ---------------------------------------------------------------------------


@dataclass
class OperatorCognitiveState:
    """The top-level persistent cognitive state of the operator session.

    Aggregates working cognition, operational focus, open loops,
    temporal context, and attention state into one coherent view.
    """

    state_id: str = ""
    session_id: str = ""
    operator_mode: OperatorMode = OperatorMode.FOCUSED_EXECUTION
    phase: CognitionPhase = CognitionPhase.INITIALIZED
    active_focus_id: str = ""
    active_workflow_ids: list[str] = field(default_factory=list)
    open_loop_count: int = 0
    attention_window_size: int = 0
    continuity_chain_length: int = 0
    last_checkpoint_id: str = ""
    last_activity_iso: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.state_id:
            self.state_id = _new_id("cogst")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.last_activity_iso:
            self.last_activity_iso = self.timestamp

    def content_hash(self) -> str:
        return _content_hash({
            "operator_mode": self.operator_mode.value,
            "phase": self.phase.value,
            "active_focus_id": self.active_focus_id,
            "open_loop_count": self.open_loop_count,
            "continuity_chain_length": self.continuity_chain_length,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "session_id": self.session_id,
            "operator_mode": self.operator_mode.value,
            "phase": self.phase.value,
            "active_focus_id": self.active_focus_id,
            "active_workflow_ids": self.active_workflow_ids,
            "open_loop_count": self.open_loop_count,
            "attention_window_size": self.attention_window_size,
            "continuity_chain_length": self.continuity_chain_length,
            "last_checkpoint_id": self.last_checkpoint_id,
            "last_activity_iso": self.last_activity_iso,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 2: WorkingCognitionWindow
# ---------------------------------------------------------------------------


@dataclass
class WorkingCognitionWindow:
    """A bounded window of active operational cognition.

    Contains the currently relevant context items, weighted
    by attention and bounded by mode policies.
    """

    window_id: str = ""
    session_id: str = ""
    max_items: int = 20
    items: list[dict[str, Any]] = field(default_factory=list)
    total_weight: float = 0.0
    oldest_item_iso: str = ""
    newest_item_iso: str = ""
    mode: OperatorMode = OperatorMode.FOCUSED_EXECUTION
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.window_id:
            self.window_id = _new_id("cogwin")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def add_item(self, item: dict[str, Any], weight: float = 1.0) -> bool:
        if len(self.items) >= self.max_items:
            return False
        item["_weight"] = weight
        item["_added_at"] = _now_iso()
        self.items.append(item)
        self.total_weight += weight
        ts = item.get("_added_at", "")
        if not self.oldest_item_iso or ts < self.oldest_item_iso:
            self.oldest_item_iso = ts
        self.newest_item_iso = ts
        return True

    def evict_lowest_weight(self) -> dict[str, Any] | None:
        if not self.items:
            return None
        lowest = min(self.items, key=lambda x: x.get("_weight", 0))
        self.items.remove(lowest)
        self.total_weight -= lowest.get("_weight", 0)
        return lowest

    def content_hash(self) -> str:
        return _content_hash({
            "max_items": self.max_items,
            "item_count": len(self.items),
            "total_weight": round(self.total_weight, 4),
            "mode": self.mode.value,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "session_id": self.session_id,
            "max_items": self.max_items,
            "item_count": len(self.items),
            "total_weight": round(self.total_weight, 4),
            "oldest_item_iso": self.oldest_item_iso,
            "newest_item_iso": self.newest_item_iso,
            "mode": self.mode.value,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 3: ActiveOperationalFocus
# ---------------------------------------------------------------------------


@dataclass
class ActiveOperationalFocus:
    """The current operational focus of the operator.

    Represents what the substrate should prioritize
    in attention and context retrieval.
    """

    focus_id: str = ""
    session_id: str = ""
    focus_type: str = ""
    focus_description: str = ""
    related_workflow_ids: list[str] = field(default_factory=list)
    related_loop_ids: list[str] = field(default_factory=list)
    priority: float = 1.0
    set_by: str = "operator"
    active: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.focus_id:
            self.focus_id = _new_id("cogfoc")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "focus_type": self.focus_type,
            "focus_description": self.focus_description,
            "priority": self.priority,
            "set_by": self.set_by,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "focus_id": self.focus_id,
            "session_id": self.session_id,
            "focus_type": self.focus_type,
            "focus_description": self.focus_description,
            "related_workflow_ids": self.related_workflow_ids,
            "related_loop_ids": self.related_loop_ids,
            "priority": self.priority,
            "set_by": self.set_by,
            "active": self.active,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 4: OpenOperationalLoop
# ---------------------------------------------------------------------------


@dataclass
class OpenOperationalLoop:
    """An unresolved operational loop tracked by cognition.

    Represents work that was started but not completed,
    requiring future attention or resolution.
    """

    loop_id: str = ""
    session_id: str = ""
    source_type: str = ""
    source_id: str = ""
    description: str = ""
    state: LoopState = LoopState.ACTIVE
    priority: float = 1.0
    created_at: str = ""
    last_touched: str = ""
    stale_after_seconds: float = 3600.0
    resolution_summary: str = ""
    related_workflow_ids: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.loop_id:
            self.loop_id = _new_id("cogloop")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.created_at:
            self.created_at = self.timestamp
        if not self.last_touched:
            self.last_touched = self.timestamp

    def content_hash(self) -> str:
        return _content_hash({
            "source_type": self.source_type,
            "source_id": self.source_id,
            "state": self.state.value,
            "priority": self.priority,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop_id": self.loop_id,
            "session_id": self.session_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "description": self.description,
            "state": self.state.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "last_touched": self.last_touched,
            "stale_after_seconds": self.stale_after_seconds,
            "resolution_summary": self.resolution_summary,
            "related_workflow_ids": self.related_workflow_ids,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 5: CognitiveCheckpoint
# ---------------------------------------------------------------------------


@dataclass
class CognitiveCheckpoint:
    """A snapshot of cognitive state at a specific point.

    Enables restoration of full cognition context on
    session restart or after interruption.
    """

    checkpoint_id: str = ""
    session_id: str = ""
    phase: CognitionPhase = CognitionPhase.CHECKPOINTED
    operator_mode: OperatorMode = OperatorMode.FOCUSED_EXECUTION
    cognitive_state_snapshot: dict[str, Any] = field(default_factory=dict)
    active_focus_snapshot: dict[str, Any] = field(default_factory=dict)
    open_loops_snapshot: list[dict[str, Any]] = field(default_factory=list)
    attention_snapshot: dict[str, Any] = field(default_factory=dict)
    continuity_chain_ids: list[str] = field(default_factory=list)
    resumable: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.checkpoint_id:
            self.checkpoint_id = _new_id("cogchk")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "operator_mode": self.operator_mode.value,
            "phase": self.phase.value,
            "open_loops_count": len(self.open_loops_snapshot),
            "continuity_chain_length": len(self.continuity_chain_ids),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "phase": self.phase.value,
            "operator_mode": self.operator_mode.value,
            "cognitive_state_snapshot": self.cognitive_state_snapshot,
            "active_focus_snapshot": self.active_focus_snapshot,
            "open_loops_snapshot": self.open_loops_snapshot,
            "attention_snapshot": self.attention_snapshot,
            "continuity_chain_ids": self.continuity_chain_ids,
            "resumable": self.resumable,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 6: TemporalExecutionContext
# ---------------------------------------------------------------------------


@dataclass
class TemporalExecutionContext:
    """Temporal context for cognition continuity.

    Tracks session boundaries, restart events, and
    operational chronology to maintain temporal ordering.
    """

    context_id: str = ""
    session_id: str = ""
    session_started_at: str = ""
    previous_session_id: str = ""
    restart_count: int = 0
    continuity_gap_seconds: float = 0.0
    chronology_entries: int = 0
    last_checkpoint_iso: str = ""
    last_resumption_iso: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.context_id:
            self.context_id = _new_id("cogtmp")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.session_started_at:
            self.session_started_at = self.timestamp

    def content_hash(self) -> str:
        return _content_hash({
            "session_id": self.session_id,
            "restart_count": self.restart_count,
            "continuity_gap_seconds": self.continuity_gap_seconds,
            "chronology_entries": self.chronology_entries,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "session_started_at": self.session_started_at,
            "previous_session_id": self.previous_session_id,
            "restart_count": self.restart_count,
            "continuity_gap_seconds": self.continuity_gap_seconds,
            "chronology_entries": self.chronology_entries,
            "last_checkpoint_iso": self.last_checkpoint_iso,
            "last_resumption_iso": self.last_resumption_iso,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 7: OperationalIntentState
# ---------------------------------------------------------------------------


@dataclass
class OperationalIntentState:
    """Tracks operator-originated intent across sessions.

    Distinguishes operator-set objectives from
    substrate-inferred context. The substrate NEVER
    generates its own operational intent.
    """

    intent_id: str = ""
    session_id: str = ""
    intent_description: str = ""
    set_by: str = "operator"
    source_command: str = ""
    active: bool = True
    related_focus_ids: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.intent_id:
            self.intent_id = _new_id("cogint")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "intent_description": self.intent_description,
            "set_by": self.set_by,
            "source_command": self.source_command,
            "active": self.active,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "session_id": self.session_id,
            "intent_description": self.intent_description,
            "set_by": self.set_by,
            "source_command": self.source_command,
            "active": self.active,
            "related_focus_ids": self.related_focus_ids,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 8: RuntimeAttentionMap
# ---------------------------------------------------------------------------


@dataclass
class RuntimeAttentionMap:
    """Maps attention weights across operational dimensions.

    Determines what the substrate prioritizes in context
    retrieval and operational focus.
    """

    map_id: str = ""
    session_id: str = ""
    weights: dict[str, float] = field(default_factory=dict)
    mode: OperatorMode = OperatorMode.FOCUSED_EXECUTION
    total_items: int = 0
    suppressed_items: int = 0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.map_id:
            self.map_id = _new_id("cogatn")
        if not self.timestamp:
            self.timestamp = _now_iso()
        if not self.weights:
            self.weights = {
                AttentionWeightType.CONTINUITY.value: 1.0,
                AttentionWeightType.TEMPORAL.value: 1.0,
                AttentionWeightType.WORKFLOW.value: 1.0,
                AttentionWeightType.EMBODIMENT.value: 0.5,
                AttentionWeightType.LOOP_URGENCY.value: 1.5,
                AttentionWeightType.OPERATOR_FOCUS.value: 2.0,
            }

    def get_weight(self, weight_type: AttentionWeightType) -> float:
        return self.weights.get(weight_type.value, 1.0)

    def set_weight(self, weight_type: AttentionWeightType, value: float) -> None:
        self.weights[weight_type.value] = max(0.0, min(5.0, value))

    def content_hash(self) -> str:
        return _content_hash({
            "weights": {k: round(v, 4) for k, v in sorted(self.weights.items())},
            "mode": self.mode.value,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_id": self.map_id,
            "session_id": self.session_id,
            "weights": {k: round(v, 4) for k, v in self.weights.items()},
            "mode": self.mode.value,
            "total_items": self.total_items,
            "suppressed_items": self.suppressed_items,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 9: ContinuityFocusState
# ---------------------------------------------------------------------------


@dataclass
class ContinuityFocusState:
    """Tracks what the operator was focused on across sessions.

    Used during continuity restoration to reconstruct
    the operator's working context from prior sessions.
    """

    state_id: str = ""
    session_id: str = ""
    previous_session_id: str = ""
    restored_focus_ids: list[str] = field(default_factory=list)
    restored_loop_ids: list[str] = field(default_factory=list)
    restored_workflow_ids: list[str] = field(default_factory=list)
    continuity_score: float = 0.0
    restoration_complete: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.state_id:
            self.state_id = _new_id("cogcfs")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "session_id": self.session_id,
            "previous_session_id": self.previous_session_id,
            "restored_focus_count": len(self.restored_focus_ids),
            "restored_loop_count": len(self.restored_loop_ids),
            "continuity_score": round(self.continuity_score, 4),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "session_id": self.session_id,
            "previous_session_id": self.previous_session_id,
            "restored_focus_ids": self.restored_focus_ids,
            "restored_loop_ids": self.restored_loop_ids,
            "restored_workflow_ids": self.restored_workflow_ids,
            "continuity_score": round(self.continuity_score, 4),
            "restoration_complete": self.restoration_complete,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }


# ---------------------------------------------------------------------------
# Contract 10: CognitiveLineageReceipt
# ---------------------------------------------------------------------------


@dataclass
class CognitiveLineageReceipt:
    """Proof that a cognition transition went through governed channels.

    Every focus shift, attention reweight, loop state change,
    and continuity restoration emits a receipt.
    """

    receipt_id: str = ""
    session_id: str = ""
    cognition_phase: CognitionPhase = CognitionPhase.ACTIVE
    decision_type: CognitionDecisionType = CognitionDecisionType.FOCUS_SHIFT
    action: str = ""
    component: str = ""
    input_hash: str = ""
    output_hash: str = ""
    approved: bool = True
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_id:
            self.receipt_id = _new_id("cogrcpt")
        if not self.timestamp:
            self.timestamp = _now_iso()

    def content_hash(self) -> str:
        return _content_hash({
            "cognition_phase": self.cognition_phase.value,
            "decision_type": self.decision_type.value,
            "action": self.action,
            "component": self.component,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "session_id": self.session_id,
            "cognition_phase": self.cognition_phase.value,
            "decision_type": self.decision_type.value,
            "action": self.action,
            "component": self.component,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "approved": self.approved,
            "timestamp": self.timestamp,
            "content_hash": self.content_hash(),
        }
