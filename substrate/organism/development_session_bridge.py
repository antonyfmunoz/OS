"""DevelopmentSessionBridge — makes coding agents governed organs of the organism.

The coding agent (Claude Code, Codex, or any future harness) is the
highest-leverage mutator in the organism. It changes architecture,
moves files, installs gates, creates types — mutations that reshape
the entire system. Without this bridge, those mutations are invisible
to the organism: no event spine emission, no learning signal capture,
no world model observation, no execution journal record.

This bridge closes that gap. It provides a lightweight protocol for
coding sessions to:
  1. Register as an active execution context
  2. Emit structured events into the EventSpine
  3. Record decisions as LearningSignals
  4. Log mutations for world model awareness
  5. Capture coherence violations as they happen

The bridge does NOT require mutations to flow through the
GovernedExecutionSpine (that would block the coding agent's normal
workflow). Instead, it observes and records — making the organism
aware of what its development agent is doing, so the world model
stays coherent and learning signals compound across sessions.

UMH substrate subsystem. Instance-agnostic. Harness-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_SESSIONS_DIR = Path(os.environ.get("UMH_ROOT", "/opt/OS")) / "data" / "umh" / "sessions"
_LEARNING_DIR = Path(os.environ.get("UMH_ROOT", "/opt/OS")) / "data" / "umh" / "organism"


@dataclass
class DevelopmentEvent:
    event_type: str
    description: str
    files_affected: list[str] = field(default_factory=list)
    layer: str = ""
    risk_level: str = "low"
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid4().hex[:12])

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "description": self.description,
            "files_affected": self.files_affected,
            "layer": self.layer,
            "risk_level": self.risk_level,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class CoherenceObservation:
    category: str
    description: str
    severity: str = "info"
    affected_files: list[str] = field(default_factory=list)
    resolution: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "description": self.description,
            "severity": self.severity,
            "affected_files": self.affected_files,
            "resolution": self.resolution,
            "timestamp": self.timestamp,
        }


class DevelopmentSessionBridge:
    """Bridge between a coding agent session and the organism.

    One instance per coding session. Records events, learning signals,
    and coherence observations into organism storage so the world model
    and learning loops can observe development activity.
    """

    def __init__(
        self,
        session_id: str | None = None,
        harness: str = "claude_code",
        event_spine: Any | None = None,
    ) -> None:
        self.session_id = session_id or uuid4().hex[:12]
        self.harness = harness
        self._event_spine = event_spine
        self._events: list[DevelopmentEvent] = []
        self._coherence_observations: list[CoherenceObservation] = []
        self._decisions: list[dict[str, Any]] = []
        self._started_at = time.time()
        self._files_touched: set[str] = set()

        _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        _LEARNING_DIR.mkdir(parents=True, exist_ok=True)

    def register_session(self, intent: str = "", context: dict[str, Any] | None = None) -> None:
        """Register this session as an active organism execution context."""
        record = {
            "session_id": self.session_id,
            "harness": self.harness,
            "intent": intent,
            "started_at": self._started_at,
            "context": context or {},
            "status": "active",
        }
        self._append_jsonl(_SESSIONS_DIR / "active_sessions.jsonl", record)

        if self._event_spine is not None:
            self._emit_event("session_started", f"{self.harness} session registered", {
                "intent": intent,
            })

        logger.info(
            "development session registered: %s (harness=%s, intent=%s)",
            self.session_id, self.harness, intent[:80],
        )

    def record_mutation(
        self,
        description: str,
        files: list[str],
        layer: str,
        risk_level: str = "low",
        metadata: dict[str, Any] | None = None,
    ) -> DevelopmentEvent:
        """Record a mutation performed by the coding agent."""
        event = DevelopmentEvent(
            event_type="mutation",
            description=description,
            files_affected=files,
            layer=layer,
            risk_level=risk_level,
            metadata=metadata or {},
        )
        self._events.append(event)
        self._files_touched.update(files)

        if self._event_spine is not None:
            self._emit_event("development_mutation", description, {
                "files": files,
                "layer": layer,
                "risk_level": risk_level,
            })

        return event

    def record_decision(
        self,
        decision: str,
        rationale: str,
        alternatives_considered: list[str] | None = None,
        confidence: float = 0.8,
    ) -> dict[str, Any]:
        """Record an architectural or design decision."""
        record = {
            "decision": decision,
            "rationale": rationale,
            "alternatives": alternatives_considered or [],
            "confidence": confidence,
            "session_id": self.session_id,
            "timestamp": time.time(),
        }
        self._decisions.append(record)

        self._append_jsonl(
            _LEARNING_DIR / "learning_signals.jsonl",
            {
                "id": str(uuid4()),
                "agent_id": f"developer:{self.harness}",
                "deliverable_id": self.session_id,
                "pattern_observed": decision,
                "generalization_hint": rationale,
                "confidence": confidence,
                "created_at": time.time(),
            },
        )

        if self._event_spine is not None:
            self._emit_event("development_decision", decision, {
                "rationale": rationale,
                "confidence": confidence,
            })

        return record

    def record_coherence_observation(
        self,
        category: str,
        description: str,
        severity: str = "info",
        affected_files: list[str] | None = None,
        resolution: str = "",
    ) -> CoherenceObservation:
        """Record a coherence violation or observation found during development."""
        obs = CoherenceObservation(
            category=category,
            description=description,
            severity=severity,
            affected_files=affected_files or [],
            resolution=resolution,
        )
        self._coherence_observations.append(obs)

        if severity in ("warning", "error"):
            if self._event_spine is not None:
                self._emit_event("coherence_violation", description, {
                    "category": category,
                    "severity": severity,
                    "affected_files": affected_files or [],
                }, priority="high")

        return obs

    def record_gate_result(
        self,
        gate_name: str,
        passed: bool,
        violations: int = 0,
        details: str = "",
    ) -> None:
        """Record a pre-commit gate execution result."""
        event = DevelopmentEvent(
            event_type="gate_check",
            description=f"gate:{gate_name} {'passed' if passed else f'FAILED ({violations} violations)'}",
            metadata={
                "gate_name": gate_name,
                "passed": passed,
                "violations": violations,
                "details": details,
            },
        )
        self._events.append(event)

        if self._event_spine is not None:
            priority = "normal" if passed else "high"
            self._emit_event("gate_result", event.description, event.metadata, priority=priority)

    def close_session(self, outcome: str = "completed", summary: str = "") -> dict[str, Any]:
        """Close this session and persist the full session record."""
        duration = time.time() - self._started_at
        record = {
            "session_id": self.session_id,
            "harness": self.harness,
            "outcome": outcome,
            "summary": summary,
            "started_at": self._started_at,
            "ended_at": time.time(),
            "duration_seconds": round(duration, 1),
            "total_events": len(self._events),
            "total_decisions": len(self._decisions),
            "total_coherence_observations": len(self._coherence_observations),
            "files_touched": sorted(self._files_touched),
            "coherence_observations": [o.to_dict() for o in self._coherence_observations],
            "events": [e.to_dict() for e in self._events[-50:]],
        }

        session_file = _SESSIONS_DIR / f"{self.session_id}.json"
        session_file.write_text(json.dumps(record, indent=2, default=str))

        self._append_jsonl(_SESSIONS_DIR / "completed_sessions.jsonl", {
            "session_id": self.session_id,
            "harness": self.harness,
            "outcome": outcome,
            "duration_seconds": round(duration, 1),
            "events": len(self._events),
            "decisions": len(self._decisions),
            "coherence_issues": sum(
                1 for o in self._coherence_observations
                if o.severity in ("warning", "error")
            ),
            "files_touched": len(self._files_touched),
            "ended_at": time.time(),
        })

        if self._event_spine is not None:
            self._emit_event("session_completed", summary or f"session {outcome}", {
                "outcome": outcome,
                "duration_seconds": round(duration, 1),
                "total_events": len(self._events),
            })

        logger.info(
            "development session closed: %s — %s (%d events, %d decisions, %.0fs)",
            self.session_id, outcome, len(self._events), len(self._decisions), duration,
        )

        return record

    def _emit_event(
        self,
        event_type: str,
        description: str,
        data: dict[str, Any],
        priority: str = "normal",
    ) -> None:
        if self._event_spine is None:
            return
        try:
            from substrate.organism.event_spine import EventDomain, EventPriority

            priority_map = {
                "low": EventPriority.LOW,
                "normal": EventPriority.NORMAL,
                "high": EventPriority.HIGH,
                "critical": EventPriority.CRITICAL,
            }
            self._event_spine.emit(
                EventDomain.EXECUTION,
                event_type,
                f"dev_session:{self.session_id}",
                {"description": description, **data},
                priority=priority_map.get(priority, EventPriority.NORMAL),
                correlation_id=self.session_id,
            )
        except Exception as exc:
            logger.debug("event spine emission failed: %s", exc)

    @staticmethod
    def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(record, default=str, separators=(",", ":")) + "\n")

    def to_dict(self) -> dict[str, Any]:
        duration = time.time() - self._started_at
        return {
            "session_id": self.session_id,
            "harness": self.harness,
            "status": "active",
            "duration_seconds": round(duration, 1),
            "total_events": len(self._events),
            "total_decisions": len(self._decisions),
            "coherence_observations": len(self._coherence_observations),
            "files_touched": len(self._files_touched),
        }
