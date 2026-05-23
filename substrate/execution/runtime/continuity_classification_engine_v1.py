"""Continuity Classification Engine v1.

Classifies runtime events into continuity categories:
which events are transient noise, which are operationally critical,
which should persist as canonical memory, which are resumable.

Deterministic. Rule-based. No ML.

UMH substrate subsystem. Phase 96.8BN.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .runtime_cognition_contracts_v1 import (
    EventSeverity,
    OutcomeResult,
    _deterministic_id,
)


class ContinuityClass(str, Enum):
    TRANSIENT = "transient"
    RESUMABLE = "resumable"
    OPERATIONALLY_CRITICAL = "operationally_critical"
    CANONICAL_WORTHY = "canonical_worthy"
    UNRESOLVED = "unresolved"
    BLOCKED = "blocked"
    STALE = "stale"
    SUPERSEDED = "superseded"


@dataclass
class ClassificationDecision:
    """One classification decision for a runtime record."""

    decision_id: str
    record_id: str
    record_type: str
    classification: ContinuityClass
    reason: str
    persist: bool = True
    promote_to_memory: bool = False
    track_as_open_loop: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "record_id": self.record_id,
            "record_type": self.record_type,
            "classification": self.classification.value,
            "reason": self.reason,
            "persist": self.persist,
            "promote_to_memory": self.promote_to_memory,
            "track_as_open_loop": self.track_as_open_loop,
            "timestamp": self.timestamp,
        }


TRANSIENT_EVENT_TYPES = frozenset(
    {
        "reply_chunk",
        "step_started",
        "inbound_received",
        "node_reconnected",
    }
)

CRITICAL_EVENT_TYPES = frozenset(
    {
        "execution_failed",
        "execution_timed_out",
        "execution_rejected",
        "action_failed",
        "action_expired",
        "relay_failed",
        "permission_denied",
        "node_degraded",
    }
)

CANONICAL_EVENT_TYPES = frozenset(
    {
        "execution_completed",
        "action_completed",
        "delivery_complete",
        "permission_granted",
    }
)

RESUMABLE_EVENT_TYPES = frozenset(
    {
        "execution_started",
        "pipeline_created",
        "action_dispatched",
        "execution_requested",
    }
)


def classify_event(event: dict[str, Any]) -> ClassificationDecision:
    """Classify a runtime event by its type and severity."""
    event_type = event.get("event_type", "")
    severity = event.get("severity", "info")
    record_id = event.get("event_id", "")

    if event_type in TRANSIENT_EVENT_TYPES:
        return ClassificationDecision(
            decision_id=_deterministic_id("cclass", f"{record_id}:transient"),
            record_id=record_id,
            record_type="event",
            classification=ContinuityClass.TRANSIENT,
            reason=f"Event type {event_type} is transient",
            persist=False,
        )

    if event_type in CRITICAL_EVENT_TYPES or severity in ("error", "critical"):
        return ClassificationDecision(
            decision_id=_deterministic_id("cclass", f"{record_id}:critical"),
            record_id=record_id,
            record_type="event",
            classification=ContinuityClass.OPERATIONALLY_CRITICAL,
            reason=f"Event type {event_type} is operationally critical",
            persist=True,
            track_as_open_loop=True,
        )

    if event_type in CANONICAL_EVENT_TYPES:
        return ClassificationDecision(
            decision_id=_deterministic_id("cclass", f"{record_id}:canonical"),
            record_id=record_id,
            record_type="event",
            classification=ContinuityClass.CANONICAL_WORTHY,
            reason=f"Event type {event_type} may promote to canonical memory",
            persist=True,
            promote_to_memory=True,
        )

    if event_type in RESUMABLE_EVENT_TYPES:
        return ClassificationDecision(
            decision_id=_deterministic_id("cclass", f"{record_id}:resumable"),
            record_id=record_id,
            record_type="event",
            classification=ContinuityClass.RESUMABLE,
            reason=f"Event type {event_type} is resumable",
            persist=True,
            track_as_open_loop=True,
        )

    return ClassificationDecision(
        decision_id=_deterministic_id("cclass", f"{record_id}:default"),
        record_id=record_id,
        record_type="event",
        classification=ContinuityClass.RESUMABLE,
        reason="Default classification: persist and resume",
        persist=True,
    )


def classify_outcome(outcome: dict[str, Any]) -> ClassificationDecision:
    """Classify a runtime outcome by its result."""
    result = outcome.get("result", "success")
    record_id = outcome.get("outcome_id", "")

    if result in ("failure", "timeout"):
        return ClassificationDecision(
            decision_id=_deterministic_id("cclass", f"{record_id}:failure"),
            record_id=record_id,
            record_type="outcome",
            classification=ContinuityClass.OPERATIONALLY_CRITICAL,
            reason=f"Outcome result {result} is operationally critical",
            persist=True,
            promote_to_memory=True,
            track_as_open_loop=True,
        )

    if result == "blocked":
        return ClassificationDecision(
            decision_id=_deterministic_id("cclass", f"{record_id}:blocked"),
            record_id=record_id,
            record_type="outcome",
            classification=ContinuityClass.BLOCKED,
            reason="Execution blocked — requires intervention",
            persist=True,
            track_as_open_loop=True,
        )

    if result == "deferred":
        return ClassificationDecision(
            decision_id=_deterministic_id("cclass", f"{record_id}:deferred"),
            record_id=record_id,
            record_type="outcome",
            classification=ContinuityClass.UNRESOLVED,
            reason="Execution deferred — open loop",
            persist=True,
            track_as_open_loop=True,
        )

    if result == "success":
        return ClassificationDecision(
            decision_id=_deterministic_id("cclass", f"{record_id}:success"),
            record_id=record_id,
            record_type="outcome",
            classification=ContinuityClass.CANONICAL_WORTHY,
            reason="Successful outcome — canonical worthy",
            persist=True,
            promote_to_memory=True,
        )

    return ClassificationDecision(
        decision_id=_deterministic_id("cclass", f"{record_id}:partial"),
        record_id=record_id,
        record_type="outcome",
        classification=ContinuityClass.RESUMABLE,
        reason=f"Outcome result {result} — resumable",
        persist=True,
    )
