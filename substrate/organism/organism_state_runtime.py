"""Organism State Runtime — Campaign 16.1.

Unified "what is the organism doing right now?" view.
Composes portfolio health (C15.3) + governed execution (C16.0) +
executive brief into a single cross-cutting state classification.

Distinct from OrganismPortfolioRuntime: the portfolio aggregates
subsystem health scores. This runtime classifies the organism's
current MODE — idle, executing, governing, learning, or degraded.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ───────────────────────────────────────────────────────────


class OrganismMode(str, Enum):
    IDLE = "idle"
    EXECUTING = "executing"
    GOVERNING = "governing"
    LEARNING = "learning"
    DEGRADED = "degraded"


# ── Dataclasses ─────────────────────────────────────────────────────


@dataclass
class OrganismStateSnapshot:
    mode: str = OrganismMode.IDLE.value
    health: str = "unknown"
    coherence_score: float = 0.0
    execution_state: str = "idle"
    active_concerns: int = 0
    subsystem_count: int = 8
    healthy_subsystems: int = 0
    drift_count: int = 0
    attention_items: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "health": self.health,
            "coherence_score": self.coherence_score,
            "execution_state": self.execution_state,
            "active_concerns": self.active_concerns,
            "subsystem_count": self.subsystem_count,
            "healthy_subsystems": self.healthy_subsystems,
            "drift_count": self.drift_count,
            "attention_items": self.attention_items,
            "generated_at": self.generated_at,
        }


# ── Runtime ─────────────────────────────────────────────────────────

_BEST_HEALTH_VALUES = frozenset({
    "coherent", "synchronized", "optimized", "thriving", "optimal",
})


class OrganismStateRuntime:
    """Unified organism state — the dashboard root.

    Composes 3 subsystems:
    - OrganismPortfolioRuntime (C15.3): subsystem health aggregation
    - GovernedExecutionRuntime (C16.0): execution state coordination
    - ExecutiveBriefRuntime: strategic context for attention items

    Answers: "What is the organism doing right now?"
    """

    def __init__(
        self,
        organism_portfolio: Any | None = None,
        governed_execution: Any | None = None,
        executive_brief: Any | None = None,
    ) -> None:
        self._organism_portfolio_dep = organism_portfolio
        self._governed_execution_dep = governed_execution
        self._executive_brief_dep = executive_brief

    # ── Lazy subsystem access ───────────────────────────────────────

    @property
    def _organism_portfolio(self) -> Any | None:
        if self._organism_portfolio_dep is not None:
            return self._organism_portfolio_dep
        try:
            from substrate.organism.organism_portfolio_runtime import (
                OrganismPortfolioRuntime,
            )

            self._organism_portfolio_dep = OrganismPortfolioRuntime()
        except Exception as exc:
            logger.debug("organism_state: organism_portfolio init failed: %s", exc)
        return self._organism_portfolio_dep

    @property
    def _governed_execution(self) -> Any | None:
        if self._governed_execution_dep is not None:
            return self._governed_execution_dep
        try:
            from substrate.organism.governed_execution_runtime import (
                GovernedExecutionRuntime,
            )

            self._governed_execution_dep = GovernedExecutionRuntime()
        except Exception as exc:
            logger.debug("organism_state: governed_execution init failed: %s", exc)
        return self._governed_execution_dep

    @property
    def _executive_brief(self) -> Any | None:
        if self._executive_brief_dep is not None:
            return self._executive_brief_dep
        try:
            from substrate.organism.executive_brief_runtime import (
                ExecutiveBriefRuntime,
            )

            self._executive_brief_dep = ExecutiveBriefRuntime()
        except Exception as exc:
            logger.debug("organism_state: executive_brief init failed: %s", exc)
        return self._executive_brief_dep

    # ── Data extraction ─────────────────────────────────────────────

    def _get_coherence_score(self) -> float:
        try:
            if self._organism_portfolio is not None:
                return self._organism_portfolio.coherence_score()
        except Exception as exc:
            logger.debug("organism_state: coherence_score failed: %s", exc)
        return 0.0

    def _get_portfolio_health(self) -> str:
        try:
            if self._organism_portfolio is not None:
                h = self._organism_portfolio.health()
                return h.value if hasattr(h, "value") else str(h)
        except Exception as exc:
            logger.debug("organism_state: portfolio_health failed: %s", exc)
        return "unknown"

    def _get_subsystem_health_entries(self) -> list[Any]:
        try:
            if self._organism_portfolio is not None:
                return self._organism_portfolio.subsystem_health()
        except Exception as exc:
            logger.debug("organism_state: subsystem_health failed: %s", exc)
        return []

    def _get_drift_count(self) -> int:
        try:
            if self._organism_portfolio is not None:
                return len(self._organism_portfolio.drift_warnings())
        except Exception as exc:
            logger.debug("organism_state: drift_count failed: %s", exc)
        return 0

    def _get_execution_state(self) -> str:
        try:
            if self._governed_execution is not None:
                s = self._governed_execution.state()
                return s.value if hasattr(s, "value") else str(s)
        except Exception as exc:
            logger.debug("organism_state: execution_state failed: %s", exc)
        return "idle"

    def _get_attention_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        try:
            if self._executive_brief is not None:
                brief = self._executive_brief.generate()
                for risk in getattr(brief, "risks", [])[:3]:
                    items.append({"type": "risk", "description": str(risk)})
                for blocker in getattr(brief, "blockers", [])[:3]:
                    items.append({"type": "blocker", "description": str(blocker)})
                for drift in getattr(brief, "drift_warnings", [])[:2]:
                    items.append({"type": "drift", "description": str(drift)})
        except Exception as exc:
            logger.debug("organism_state: attention_items failed: %s", exc)
        return items[:8]

    def _count_healthy_subsystems(self) -> int:
        entries = self._get_subsystem_health_entries()
        count = 0
        for entry in entries:
            h = ""
            if hasattr(entry, "health"):
                h = entry.health
            elif isinstance(entry, dict):
                h = entry.get("health", "")
            if h in _BEST_HEALTH_VALUES or h in ("aligned", "focused", "growing"):
                count += 1
        return count

    def _has_critical_subsystem(self) -> bool:
        entries = self._get_subsystem_health_entries()
        for entry in entries:
            h = ""
            if hasattr(entry, "health"):
                h = entry.health
            elif isinstance(entry, dict):
                h = entry.get("health", "")
            if h == "critical":
                return True
        return False

    def _get_recent_lesson_count(self) -> int:
        try:
            if self._executive_brief is not None:
                brief = self._executive_brief.generate()
                lessons = getattr(brief, "recent_lessons", [])
                return len(lessons)
        except Exception as exc:
            logger.debug("organism_state: recent_lesson_count failed: %s", exc)
        return 0

    # ── Mode classification ─────────────────────────────────────────

    def mode(self) -> OrganismMode:
        coherence = self._get_coherence_score()
        has_critical = self._has_critical_subsystem()
        exec_state = self._get_execution_state()

        if has_critical or coherence < 0.3:
            return OrganismMode.DEGRADED

        if exec_state == "executing":
            return OrganismMode.EXECUTING

        if exec_state == "governed":
            return OrganismMode.GOVERNING

        if self._get_recent_lesson_count() > 0:
            return OrganismMode.LEARNING

        return OrganismMode.IDLE

    # ── Public API ──────────────────────────────────────────────────

    def health(self) -> str:
        return self._get_portfolio_health()

    def is_degraded(self) -> bool:
        return self.mode() == OrganismMode.DEGRADED

    def snapshot(self) -> OrganismStateSnapshot:
        entries = self._get_subsystem_health_entries()
        return OrganismStateSnapshot(
            mode=self.mode().value,
            health=self._get_portfolio_health(),
            coherence_score=self._get_coherence_score(),
            execution_state=self._get_execution_state(),
            active_concerns=self._get_drift_count() + len(self._get_attention_items()),
            subsystem_count=len(entries) if entries else 8,
            healthy_subsystems=self._count_healthy_subsystems(),
            drift_count=self._get_drift_count(),
            attention_items=self._get_attention_items(),
        )

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode().value,
            "health": self._get_portfolio_health(),
            "coherence_score": self._get_coherence_score(),
            "execution_state": self._get_execution_state(),
            "is_degraded": self.is_degraded(),
            "healthy_subsystems": self._count_healthy_subsystems(),
            "drift_count": self._get_drift_count(),
        }
