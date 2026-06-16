"""Operator Context Models — types for the operator home surface.

Defines the data structures that compose existing UMH subsystem
outputs into a single operator-facing view. No new authority,
no new state, no execution — aggregation types only.

Phase 31. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class OperatorSeverity(str, Enum):
    """How urgently something needs operator attention."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class OperatorAttentionType(str, Enum):
    """Which subsystem produced the attention item."""

    GOVERNANCE = "governance"
    ACTION = "action"
    SERVICE = "service"
    WORKSPACE = "workspace"
    RUNTIME = "runtime"
    STATE = "state"
    ENGINEERING = "engineering"


@dataclass
class OperatorAttentionItem:
    """A single item requiring operator awareness or action."""

    attention_type: OperatorAttentionType
    severity: OperatorSeverity
    title: str
    detail: str
    source: str
    attention_id: str = field(default_factory=lambda: f"oai-{uuid4().hex[:10]}")
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attention_id": self.attention_id,
            "attention_type": self.attention_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "detail": self.detail,
            "source": self.source,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatorAttentionItem:
        return cls(
            attention_id=data.get("attention_id", f"oai-{uuid4().hex[:10]}"),
            attention_type=OperatorAttentionType(data["attention_type"]),
            severity=OperatorSeverity(data["severity"]),
            title=data["title"],
            detail=data.get("detail", ""),
            source=data.get("source", ""),
            timestamp=data.get("timestamp", time.time()),
        )


@dataclass
class OperatorStatusCard:
    """A single health metric card for the operator dashboard."""

    label: str
    value: Any
    status: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "status": self.status,
            "detail": self.detail,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatorStatusCard:
        return cls(
            label=data["label"],
            value=data["value"],
            status=data["status"],
            detail=data.get("detail", ""),
        )


@dataclass
class OperatorHealthSummary:
    """Aggregated organism health across all subsystems."""

    overall_status: str
    cards: list[OperatorStatusCard] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "cards": [c.to_dict() for c in self.cards],
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatorHealthSummary:
        return cls(
            overall_status=data["overall_status"],
            cards=[OperatorStatusCard.from_dict(c) for c in data.get("cards", [])],
            generated_at=data.get("generated_at", time.time()),
        )


@dataclass
class OperatorTimelineEvent:
    """A single event in the operator timeline feed."""

    event_id: str
    domain: str
    event_type: str
    source: str
    summary: str
    timestamp: float
    priority: str = "normal"

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "domain": self.domain,
            "event_type": self.event_type,
            "source": self.source,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatorTimelineEvent:
        return cls(
            event_id=data["event_id"],
            domain=data["domain"],
            event_type=data["event_type"],
            source=data.get("source", ""),
            summary=data.get("summary", ""),
            timestamp=data["timestamp"],
            priority=data.get("priority", "normal"),
        )


@dataclass
class OperatorSnapshot:
    """Complete operator context — answers all 8 operator questions."""

    health_summary: OperatorHealthSummary
    attention_items: list[OperatorAttentionItem] = field(default_factory=list)
    active_workspaces: list[dict[str, Any]] = field(default_factory=list)
    pending_approvals: int = 0
    service_alerts: list[dict[str, Any]] = field(default_factory=list)
    node_status: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[OperatorTimelineEvent] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "health_summary": self.health_summary.to_dict(),
            "attention_items": [a.to_dict() for a in self.attention_items],
            "active_workspaces": self.active_workspaces,
            "pending_approvals": self.pending_approvals,
            "service_alerts": self.service_alerts,
            "node_status": self.node_status,
            "timeline": [t.to_dict() for t in self.timeline],
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatorSnapshot:
        return cls(
            health_summary=OperatorHealthSummary.from_dict(data["health_summary"]),
            attention_items=[
                OperatorAttentionItem.from_dict(a)
                for a in data.get("attention_items", [])
            ],
            active_workspaces=data.get("active_workspaces", []),
            pending_approvals=data.get("pending_approvals", 0),
            service_alerts=data.get("service_alerts", []),
            node_status=data.get("node_status", []),
            timeline=[
                OperatorTimelineEvent.from_dict(t)
                for t in data.get("timeline", [])
            ],
            generated_at=data.get("generated_at", time.time()),
        )
