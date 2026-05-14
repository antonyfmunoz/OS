"""Operational Intelligence Contracts v1.

Data contracts for operational intelligence coordination:
  synthesis, relevance, routing, reasoning, compression,
  awareness, intent anchoring, projection, signal clustering.

The intelligence layer understands and synthesizes —
it NEVER self-directs or creates autonomous objectives.

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import enum
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class IntelligenceLifecycleState(enum.Enum):
    INACTIVE = "inactive"
    OBSERVING = "observing"
    SYNTHESIZING = "synthesizing"
    CONTEXTUALIZING = "contextualizing"
    PRIORITIZING = "prioritizing"
    COMPRESSING = "compressing"
    PROJECTING = "projecting"
    VALIDATING = "validating"
    REPLAYING = "replaying"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class IntelligenceEventType(enum.Enum):
    INTELLIGENCE_SYNTHESIZED = "intelligence_synthesized"
    RELEVANCE_SCORED = "relevance_scored"
    CONTEXT_COMPRESSED = "context_compressed"
    OPERATIONAL_AWARENESS_UPDATED = "operational_awareness_updated"
    INTENT_ANCHOR_VALIDATED = "intent_anchor_validated"
    INTELLIGENCE_ROUTE_CREATED = "intelligence_route_created"
    REASONING_COMPOSED = "reasoning_composed"
    INTELLIGENCE_BOUNDARY_DENIED = "intelligence_boundary_denied"
    COGNITION_WINDOW_REGULATED = "cognition_window_regulated"
    OPERATIONAL_PROJECTION_UPDATED = "operational_projection_updated"


class RelevanceClass(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    STANDARD = "standard"
    LOW = "low"
    NOISE = "noise"


class SignalSource(enum.Enum):
    INGRESS = "ingress"
    WORKFLOWS = "workflows"
    SESSIONS = "sessions"
    ENVIRONMENTS = "environments"
    SCALING = "scaling"
    RESILIENCE = "resilience"
    CONTINUITY = "continuity"
    OBSERVABILITY = "observability"
    COGNITION = "cognition"


class ReasoningType(enum.Enum):
    OPERATIONAL_STATUS = "operational_status"
    PRESSURE_ANALYSIS = "pressure_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    CONTINUITY_REVIEW = "continuity_review"
    RECOMMENDATION = "recommendation"


@dataclass
class OperationalIntelligenceState:
    state_id: str = field(default_factory=lambda: _new_id("oist"))
    lifecycle: str = "inactive"
    synthesis_count: int = 0
    relevance_assessments: int = 0
    routing_decisions: int = 0
    reasoning_compositions: int = 0
    compressions: int = 0
    awareness_updates: int = 0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "lifecycle": self.lifecycle,
            "synthesis_count": self.synthesis_count,
            "relevance_assessments": self.relevance_assessments,
            "routing_decisions": self.routing_decisions,
            "reasoning_compositions": self.reasoning_compositions,
            "compressions": self.compressions,
            "awareness_updates": self.awareness_updates,
            "timestamp": self.timestamp,
        }


@dataclass
class IntelligenceContextWindow:
    window_id: str = field(default_factory=lambda: _new_id("ictx"))
    signals: list[dict[str, Any]] = field(default_factory=list)
    max_signals: int = 50
    current_size: int = 0
    compressed: bool = False
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "signal_count": len(self.signals),
            "max_signals": self.max_signals,
            "current_size": self.current_size,
            "compressed": self.compressed,
            "timestamp": self.timestamp,
        }


@dataclass
class IntelligenceSynthesisState:
    synthesis_id: str = field(default_factory=lambda: _new_id("isyn"))
    sources: list[str] = field(default_factory=list)
    signal_count: int = 0
    synthesis_hash: str = ""
    operator_intent: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "sources": self.sources,
            "signal_count": self.signal_count,
            "synthesis_hash": self.synthesis_hash,
            "operator_intent": self.operator_intent,
            "timestamp": self.timestamp,
        }


@dataclass
class RelevanceScore:
    score_id: str = field(default_factory=lambda: _new_id("rscore"))
    signal_id: str = ""
    score: float = 0.0
    relevance_class: str = "standard"
    source: str = ""
    reason: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "score_id": self.score_id,
            "signal_id": self.signal_id,
            "score": self.score,
            "relevance_class": self.relevance_class,
            "source": self.source,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalFocusState:
    focus_id: str = field(default_factory=lambda: _new_id("ofoc"))
    active_focus: str = ""
    focus_source: str = "operator"
    priority_signals: list[str] = field(default_factory=list)
    suppressed_signals: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "focus_id": self.focus_id,
            "active_focus": self.active_focus,
            "focus_source": self.focus_source,
            "priority_signals": self.priority_signals,
            "suppressed_signals": self.suppressed_signals,
            "timestamp": self.timestamp,
        }


@dataclass
class ContextPriorityState:
    priority_id: str = field(default_factory=lambda: _new_id("cpri"))
    ordered_signals: list[str] = field(default_factory=list)
    set_by: str = "operator"
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority_id": self.priority_id,
            "ordered_signals": self.ordered_signals,
            "set_by": self.set_by,
            "timestamp": self.timestamp,
        }


@dataclass
class IntelligenceRoutingState:
    routing_id: str = field(default_factory=lambda: _new_id("iroute"))
    source_layer: str = ""
    target_layer: str = ""
    signal_ids: list[str] = field(default_factory=list)
    routing_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "routing_id": self.routing_id,
            "source_layer": self.source_layer,
            "target_layer": self.target_layer,
            "signal_ids": self.signal_ids,
            "routing_hash": self.routing_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class IntelligenceCoordinationReceipt:
    receipt_id: str = field(default_factory=lambda: _new_id("icrcpt"))
    operation: str = ""
    from_state: str = ""
    to_state: str = ""
    signal_count: int = 0
    synthesis_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "operation": self.operation,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "signal_count": self.signal_count,
            "synthesis_hash": self.synthesis_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalReasoningState:
    reasoning_id: str = field(default_factory=lambda: _new_id("orsn"))
    reasoning_type: str = "operational_status"
    inputs: list[str] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    reasoning_chain: list[str] = field(default_factory=list)
    set_by: str = "operator"
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reasoning_id": self.reasoning_id,
            "reasoning_type": self.reasoning_type,
            "inputs": self.inputs,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "reasoning_chain": self.reasoning_chain,
            "set_by": self.set_by,
            "timestamp": self.timestamp,
        }


@dataclass
class ContextCompressionState:
    compression_id: str = field(default_factory=lambda: _new_id("ccomp"))
    original_size: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    preserved_signals: int = 0
    discarded_signals: int = 0
    compression_hash: str = ""
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "compression_id": self.compression_id,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": self.compression_ratio,
            "preserved_signals": self.preserved_signals,
            "discarded_signals": self.discarded_signals,
            "compression_hash": self.compression_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class IntelligenceProjectionState:
    projection_id: str = field(default_factory=lambda: _new_id("iproj"))
    projected_risks: list[str] = field(default_factory=list)
    projected_pressures: list[str] = field(default_factory=list)
    projected_opportunities: list[str] = field(default_factory=list)
    confidence: float = 0.0
    projection_basis: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_id": self.projection_id,
            "projected_risks": self.projected_risks,
            "projected_pressures": self.projected_pressures,
            "projected_opportunities": self.projected_opportunities,
            "confidence": self.confidence,
            "projection_basis": self.projection_basis,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalSignalCluster:
    cluster_id: str = field(default_factory=lambda: _new_id("osclust"))
    signal_ids: list[str] = field(default_factory=list)
    source: str = ""
    cluster_type: str = ""
    weight: float = 0.0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "signal_ids": self.signal_ids,
            "source": self.source,
            "cluster_type": self.cluster_type,
            "weight": self.weight,
            "timestamp": self.timestamp,
        }


@dataclass
class IntentAnchorState:
    anchor_id: str = field(default_factory=lambda: _new_id("ianch"))
    operator_intent: str = ""
    anchored_at: str = field(default_factory=_now_iso)
    validated: bool = False
    set_by: str = "operator"
    lineage: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "operator_intent": self.operator_intent,
            "anchored_at": self.anchored_at,
            "validated": self.validated,
            "set_by": self.set_by,
            "lineage": self.lineage,
            "timestamp": self.timestamp,
        }


@dataclass
class CognitiveConstraintState:
    constraint_id: str = field(default_factory=lambda: _new_id("ccnst"))
    max_context_window: int = 50
    max_reasoning_depth: int = 5
    max_signal_clusters: int = 20
    max_synthesis_sources: int = 9
    within_bounds: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "max_context_window": self.max_context_window,
            "max_reasoning_depth": self.max_reasoning_depth,
            "max_signal_clusters": self.max_signal_clusters,
            "max_synthesis_sources": self.max_synthesis_sources,
            "within_bounds": self.within_bounds,
            "timestamp": self.timestamp,
        }


@dataclass
class OperationalAwarenessState:
    awareness_id: str = field(default_factory=lambda: _new_id("oaware"))
    active_subsystems: list[str] = field(default_factory=list)
    pressure_signals: list[str] = field(default_factory=list)
    continuity_risks: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    environment_status: dict[str, str] = field(default_factory=dict)
    governance_constraints: list[str] = field(default_factory=list)
    operational_priorities: list[str] = field(default_factory=list)
    replay_integrity: bool = True
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "awareness_id": self.awareness_id,
            "active_subsystems": self.active_subsystems,
            "pressure_signals": self.pressure_signals,
            "continuity_risks": self.continuity_risks,
            "open_loops": self.open_loops,
            "environment_status": self.environment_status,
            "governance_constraints": self.governance_constraints,
            "operational_priorities": self.operational_priorities,
            "replay_integrity": self.replay_integrity,
            "timestamp": self.timestamp,
        }
