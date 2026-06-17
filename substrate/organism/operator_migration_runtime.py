"""Operator Migration Runtime — track and close external-loop dependencies.

Answers: "What are the highest-value reasons the operator still leaves UMH?"

Records exit events (operator leaves UMH for external tool), classifies them
deterministically, scores migration priority (frequency × duration × feasibility),
and bridges gaps to OperationalizationRuntime for closure.

Composes:
  - CapabilityRuntime (Gate 5) — what the organism can do
  - OperationalizationRuntime (Gate 6) — skill/template registry
  - InfrastructureRuntime (Gate 7) — infrastructure chain awareness
  - CompoundingEngine (Gate 9) — learning from outcomes
  - EmbodimentRuntime (W4) — intent routing baseline
  - ScreenAwareness (Phase 33) — visual context
  - PresenceTimeline (Phase 32) — activity tracking

Campaign invariant: measures how close operator is to building UMH from
inside UMH. Coverage metric = % workflow time inside UMH.

W5. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Enums
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ExitReason(str, Enum):
    CAPABILITY_GAP = "capability_gap"
    TOOLING_GAP = "tooling_gap"
    PREFERENCE = "preference"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class MigrationStatus(str, Enum):
    PROPOSED = "proposed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dataclasses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass
class ExitEvent:
    """Operator leaves UMH for an external tool."""

    exit_id: str = field(default_factory=lambda: f"ex-{uuid4().hex[:8]}")
    description: str = ""
    external_tool: str = ""
    reason: ExitReason = ExitReason.UNKNOWN
    exited_at: float = field(default_factory=time.time)
    returned_at: float = 0.0
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "exit_id": self.exit_id,
            "description": self.description,
            "external_tool": self.external_tool,
            "reason": self.reason.value,
            "exited_at": self.exited_at,
            "returned_at": self.returned_at,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class ExitClassification:
    """Deterministic classification of an exit event."""

    reason: ExitReason = ExitReason.UNKNOWN
    confidence: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason": self.reason.value,
            "confidence": self.confidence,
            "matched_keywords": list(self.matched_keywords),
        }


@dataclass
class MigrationPriority:
    """A scored exit pattern to close."""

    pattern: str = ""
    external_tool: str = ""
    exit_reason: ExitReason = ExitReason.UNKNOWN
    frequency: int = 0
    avg_duration_seconds: float = 0.0
    feasibility_score: float = 0.0
    priority_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "external_tool": self.external_tool,
            "exit_reason": self.exit_reason.value,
            "frequency": self.frequency,
            "avg_duration_seconds": round(self.avg_duration_seconds, 1),
            "feasibility_score": round(self.feasibility_score, 3),
            "priority_score": round(self.priority_score, 3),
        }


@dataclass
class CoverageReport:
    """What percentage of operator workflow stays inside UMH."""

    total_exits: int = 0
    total_exit_duration_seconds: float = 0.0
    total_session_duration_seconds: float = 0.0
    coverage_pct: float = 1.0
    top_exit_tools: list[str] = field(default_factory=list)
    trend: str = "stable"

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_exits": self.total_exits,
            "total_exit_duration_seconds": round(self.total_exit_duration_seconds, 1),
            "total_session_duration_seconds": round(self.total_session_duration_seconds, 1),
            "coverage_pct": round(self.coverage_pct, 4),
            "top_exit_tools": list(self.top_exit_tools),
            "trend": self.trend,
        }


@dataclass
class OperationalizationSuggestion:
    """Bridge from exit pattern to operationalization."""

    exit_pattern: str = ""
    suggested_form: str = "template"
    capability_gap: str = ""
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "exit_pattern": self.exit_pattern,
            "suggested_form": self.suggested_form,
            "capability_gap": self.capability_gap,
            "rationale": self.rationale,
        }


@dataclass
class Migration:
    """Active migration to close an exit pattern."""

    migration_id: str = field(default_factory=lambda: f"mg-{uuid4().hex[:8]}")
    exit_pattern: str = ""
    external_tool: str = ""
    status: MigrationStatus = MigrationStatus.PROPOSED
    proposed_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "migration_id": self.migration_id,
            "exit_pattern": self.exit_pattern,
            "external_tool": self.external_tool,
            "status": self.status.value,
            "proposed_at": self.proposed_at,
            "completed_at": self.completed_at,
        }


@dataclass
class MigrationStatusSnapshot:
    """Aggregated migration status."""

    total_exits: int = 0
    active_migrations: int = 0
    completed_migrations: int = 0
    coverage_pct: float = 1.0
    top_priorities: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_exits": self.total_exits,
            "active_migrations": self.active_migrations,
            "completed_migrations": self.completed_migrations,
            "coverage_pct": round(self.coverage_pct, 4),
            "top_priorities": list(self.top_priorities),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Operator Migration Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OperatorMigrationRuntime:
    """Track and close external-loop dependencies.

    Composes Gate 5-9 subsystems + W4 EmbodimentRuntime to answer:
    what still forces the operator to leave UMH?
    """

    def __init__(
        self,
        capability_runtime: Any | None = None,
        operationalization_runtime: Any | None = None,
        infrastructure_runtime: Any | None = None,
        compounding_engine: Any | None = None,
        embodiment_runtime: Any | None = None,
        screen_awareness: Any | None = None,
        presence_timeline: Any | None = None,
    ) -> None:
        self._capability_runtime = capability_runtime
        self._operationalization_runtime = operationalization_runtime
        self._infrastructure_runtime = infrastructure_runtime
        self._compounding_engine = compounding_engine
        self._embodiment_runtime = embodiment_runtime
        self._screen_awareness = screen_awareness
        self._presence_timeline = presence_timeline

        self._exits: dict[str, ExitEvent] = {}
        self._migrations: dict[str, Migration] = {}
        self._session_start: float = time.time()

    # ── Record exits ─────────────────────────────────────────────

    def record_exit(self, description: str = "", external_tool: str = "") -> str:
        """Record that the operator left UMH for an external tool."""
        classification = self.classify_exit(description)
        event = ExitEvent(
            description=description,
            external_tool=external_tool,
            reason=classification.reason,
        )
        self._exits[event.exit_id] = event
        return event.exit_id

    def record_return(self, exit_id: str) -> bool:
        """Record the operator's return from an exit."""
        event = self._exits.get(exit_id)
        if not event:
            return False
        event.returned_at = time.time()
        event.duration_seconds = event.returned_at - event.exited_at
        return True

    # ── Classification (deterministic) ───────────────────────────

    _CAPABILITY_GAP_KEYWORDS: list[str] = [
        "can't do", "cannot", "unable", "missing feature", "no way to",
        "doesn't support", "not available", "need to use",
    ]

    _TOOLING_GAP_KEYWORDS: list[str] = [
        "vscode", "vs code", "cursor", "terminal", "ssh", "termius",
        "ide", "editor", "debugger", "chrome", "browser",
    ]

    _PREFERENCE_KEYWORDS: list[str] = [
        "prefer", "easier", "faster", "used to", "comfortable",
        "habit", "familiar",
    ]

    _EXTERNAL_KEYWORDS: list[str] = [
        "meeting", "call", "email", "slack", "discord", "phone",
        "client", "customer", "external",
    ]

    def classify_exit(self, description: str) -> ExitClassification:
        """Deterministic classification of why the operator left."""
        lower = description.lower()

        for reason, keywords in [
            (ExitReason.CAPABILITY_GAP, self._CAPABILITY_GAP_KEYWORDS),
            (ExitReason.TOOLING_GAP, self._TOOLING_GAP_KEYWORDS),
            (ExitReason.PREFERENCE, self._PREFERENCE_KEYWORDS),
            (ExitReason.EXTERNAL, self._EXTERNAL_KEYWORDS),
        ]:
            matched = [kw for kw in keywords if kw in lower]
            if matched:
                confidence = min(1.0, len(matched) / 2.0)
                return ExitClassification(
                    reason=reason,
                    confidence=confidence,
                    matched_keywords=matched,
                )

        return ExitClassification(
            reason=ExitReason.UNKNOWN,
            confidence=0.3,
        )

    # ── Migration scoring ────────────────────────────────────────

    def migration_priorities(self) -> list[MigrationPriority]:
        """Score exit patterns by frequency × duration × feasibility."""
        tool_exits: dict[str, list[ExitEvent]] = {}
        for e in self._exits.values():
            key = e.external_tool or e.description[:30]
            tool_exits.setdefault(key, []).append(e)

        priorities: list[MigrationPriority] = []
        for tool, exits in tool_exits.items():
            freq = len(exits)
            durations = [e.duration_seconds for e in exits if e.duration_seconds > 0]
            avg_dur = sum(durations) / len(durations) if durations else 60.0

            feasibility = self._estimate_feasibility(tool, exits[0].reason if exits else ExitReason.UNKNOWN)

            score = freq * (avg_dur / 60.0) * feasibility

            priorities.append(MigrationPriority(
                pattern=tool,
                external_tool=tool,
                exit_reason=exits[0].reason if exits else ExitReason.UNKNOWN,
                frequency=freq,
                avg_duration_seconds=avg_dur,
                feasibility_score=feasibility,
                priority_score=score,
            ))

        priorities.sort(key=lambda p: p.priority_score, reverse=True)
        return priorities

    def _estimate_feasibility(self, tool: str, reason: ExitReason) -> float:
        """Estimate how feasible it is to close this exit pattern."""
        if reason == ExitReason.EXTERNAL:
            return 0.1
        if reason == ExitReason.PREFERENCE:
            return 0.4
        if reason == ExitReason.TOOLING_GAP:
            return 0.7
        if reason == ExitReason.CAPABILITY_GAP:
            if self._capability_runtime is not None:
                return 0.8
            return 0.6
        return 0.5

    # ── Coverage ─────────────────────────────────────────────────

    def coverage_report(self) -> CoverageReport:
        """What percentage of operator time stays inside UMH."""
        total_exit_dur = sum(
            e.duration_seconds for e in self._exits.values() if e.duration_seconds > 0
        )
        session_dur = max(1.0, time.time() - self._session_start)
        coverage = max(0.0, 1.0 - (total_exit_dur / session_dur))

        tool_counts: dict[str, int] = {}
        for e in self._exits.values():
            t = e.external_tool or "unknown"
            tool_counts[t] = tool_counts.get(t, 0) + 1
        top_tools = sorted(tool_counts, key=tool_counts.get, reverse=True)[:5]

        return CoverageReport(
            total_exits=len(self._exits),
            total_exit_duration_seconds=total_exit_dur,
            total_session_duration_seconds=session_dur,
            coverage_pct=coverage,
            top_exit_tools=top_tools,
        )

    # ── Operationalization bridge ────────────────────────────────

    def suggest_operationalization(self, exit_pattern: str) -> OperationalizationSuggestion | None:
        """Suggest how to close an exit pattern via operationalization."""
        priorities = self.migration_priorities()
        matched = [p for p in priorities if p.pattern == exit_pattern]
        if not matched:
            return None

        priority = matched[0]
        form = "template"
        if priority.exit_reason == ExitReason.TOOLING_GAP:
            form = "automation"
        elif priority.exit_reason == ExitReason.CAPABILITY_GAP:
            form = "workflow"

        return OperationalizationSuggestion(
            exit_pattern=exit_pattern,
            suggested_form=form,
            capability_gap=f"{priority.exit_reason.value}: {exit_pattern}",
            rationale=f"freq={priority.frequency}, avg_dur={priority.avg_duration_seconds:.0f}s, feasibility={priority.feasibility_score:.2f}",
        )

    # ── Migration lifecycle ──────────────────────────────────────

    def active_migrations(self) -> list[Migration]:
        """All in-progress migrations."""
        return [
            m for m in self._migrations.values()
            if m.status in (MigrationStatus.PROPOSED, MigrationStatus.IN_PROGRESS)
        ]

    def propose_migration(self, exit_pattern: str, external_tool: str = "") -> Migration:
        """Propose a new migration to close an exit pattern."""
        migration = Migration(
            exit_pattern=exit_pattern,
            external_tool=external_tool,
        )
        self._migrations[migration.migration_id] = migration
        return migration

    def start_migration(self, migration_id: str) -> bool:
        """Move a proposed migration to in_progress."""
        m = self._migrations.get(migration_id)
        if not m or m.status != MigrationStatus.PROPOSED:
            return False
        m.status = MigrationStatus.IN_PROGRESS
        return True

    def complete_migration(self, migration_id: str, success: bool = True) -> bool:
        """Complete a migration and feed CompoundingEngine."""
        m = self._migrations.get(migration_id)
        if not m:
            return False

        m.status = MigrationStatus.COMPLETED if success else MigrationStatus.ABANDONED
        m.completed_at = time.time()

        if self._compounding_engine is not None and success:
            try:
                self._compounding_engine.record_learning(
                    source="migration",
                    description=f"closed exit: {m.exit_pattern}",
                )
            except Exception:
                pass

        return True

    # ── Status ───────────────────────────────────────────────────

    def migration_status(self) -> MigrationStatusSnapshot:
        """Aggregated migration status."""
        coverage = self.coverage_report()
        priorities = self.migration_priorities()

        return MigrationStatusSnapshot(
            total_exits=len(self._exits),
            active_migrations=len(self.active_migrations()),
            completed_migrations=len([
                m for m in self._migrations.values()
                if m.status == MigrationStatus.COMPLETED
            ]),
            coverage_pct=coverage.coverage_pct,
            top_priorities=[p.to_dict() for p in priorities[:3]],
        )
