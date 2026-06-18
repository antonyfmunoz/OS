"""Capability Portfolio Runtime — portfolio-level health and compounding metrics.

Campaign 10.2. UMH substrate layer.

Aggregates CapabilityRuntime + CapabilityGraphEngine + CapabilityGapEngine +
AgentCapabilityModel into a portfolio-level view: health classification,
compounding score, maturity velocity, top/weakest/bottleneck capabilities.

Deterministic. No LLM. No execution. No mutation.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PortfolioHealth(str, Enum):
    THRIVING = "thriving"
    HEALTHY = "healthy"
    STAGNATING = "stagnating"
    DECAYING = "decaying"


@dataclass
class CapabilityPortfolioSnapshot:
    total_capabilities: int = 0
    by_maturity: dict[str, int] = field(default_factory=dict)
    compounding_score: float = 0.0
    maturity_velocity: float = 0.0
    health: PortfolioHealth = PortfolioHealth.HEALTHY
    top_capabilities: list[dict[str, Any]] = field(default_factory=list)
    weakest_capabilities: list[dict[str, Any]] = field(default_factory=list)
    bottleneck_capabilities: list[dict[str, Any]] = field(default_factory=list)
    critical_gaps: list[dict[str, Any]] = field(default_factory=list)
    agent_coverage: dict[str, Any] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_capabilities": self.total_capabilities,
            "by_maturity": self.by_maturity,
            "compounding_score": self.compounding_score,
            "maturity_velocity": self.maturity_velocity,
            "health": self.health.value,
            "top_capabilities": self.top_capabilities,
            "weakest_capabilities": self.weakest_capabilities,
            "bottleneck_capabilities": self.bottleneck_capabilities,
            "critical_gaps": self.critical_gaps,
            "agent_coverage": self.agent_coverage,
            "generated_at": self.generated_at,
        }


_MATURITY_SCORES: dict[str, float] = {
    "institutional": 1.0,
    "operational": 0.75,
    "validated": 0.5,
    "emerging": 0.25,
}


class CapabilityPortfolioRuntime:
    """Portfolio-level capability health and compounding metrics."""

    def __init__(
        self,
        capability_runtime: Any | None = None,
        graph_engine: Any | None = None,
        gap_engine: Any | None = None,
        agent_model: Any | None = None,
    ) -> None:
        self._capability_runtime = capability_runtime
        self._graph_engine = graph_engine
        self._gap_engine = gap_engine
        self._agent_model = agent_model

    def snapshot(self) -> CapabilityPortfolioSnapshot:
        """Generate a full portfolio snapshot."""
        snap = CapabilityPortfolioSnapshot(generated_at=time.time())

        self._fill_maturity_distribution(snap)
        self._fill_top_and_weakest(snap)
        self._fill_bottlenecks(snap)
        self._fill_gaps(snap)
        self._fill_agent_coverage(snap)
        snap.compounding_score = self._compute_compounding_score(snap)
        snap.maturity_velocity = self._compute_maturity_velocity(snap)
        snap.health = self._classify_health(snap)

        return snap

    def compounding_score(self) -> float:
        """Quick compounding score without full snapshot."""
        snap = CapabilityPortfolioSnapshot()
        self._fill_maturity_distribution(snap)
        return self._compute_compounding_score(snap)

    def health(self) -> PortfolioHealth:
        """Quick health classification."""
        snap = self.snapshot()
        return snap.health

    def summary(self) -> dict[str, Any]:
        """Compact summary."""
        snap = self.snapshot()
        return {
            "total_capabilities": snap.total_capabilities,
            "health": snap.health.value,
            "compounding_score": snap.compounding_score,
            "maturity_velocity": snap.maturity_velocity,
            "critical_gap_count": len(snap.critical_gaps),
            "by_maturity": snap.by_maturity,
            "generated_at": snap.generated_at,
        }

    # ── Fill methods ──────────────────────────────────────────────

    def _fill_maturity_distribution(self, snap: CapabilityPortfolioSnapshot) -> None:
        if not self._capability_runtime:
            return
        try:
            all_caps = self._capability_runtime.list_capabilities()
            snap.total_capabilities = len(all_caps)
            dist: dict[str, int] = {}
            for cap in all_caps:
                mat = cap.maturity.value if hasattr(cap.maturity, "value") else str(cap.maturity)
                dist[mat] = dist.get(mat, 0) + 1
            snap.by_maturity = dist
        except Exception as exc:
            logger.debug("portfolio: maturity distribution failed: %s", exc)

    def _fill_top_and_weakest(self, snap: CapabilityPortfolioSnapshot) -> None:
        if not self._capability_runtime:
            return
        try:
            all_caps = self._capability_runtime.list_capabilities()
            scored: list[tuple[float, Any]] = []
            for cap in all_caps:
                try:
                    score = self._capability_runtime.maturity_score(cap.capability_id)
                except Exception:
                    mat = cap.maturity.value if hasattr(cap.maturity, "value") else str(cap.maturity)
                    score = _MATURITY_SCORES.get(mat, 0.0)
                scored.append((score, cap))

            scored.sort(key=lambda x: -x[0])

            for score, cap in scored[:5]:
                mat = cap.maturity.value if hasattr(cap.maturity, "value") else str(cap.maturity)
                snap.top_capabilities.append({
                    "capability_id": cap.capability_id,
                    "name": cap.name,
                    "maturity": mat,
                    "score": round(score, 3),
                })

            for score, cap in scored[-5:]:
                mat = cap.maturity.value if hasattr(cap.maturity, "value") else str(cap.maturity)
                snap.weakest_capabilities.append({
                    "capability_id": cap.capability_id,
                    "name": cap.name,
                    "maturity": mat,
                    "score": round(score, 3),
                })
        except Exception as exc:
            logger.debug("portfolio: top/weakest fill failed: %s", exc)

    def _fill_bottlenecks(self, snap: CapabilityPortfolioSnapshot) -> None:
        if not self._graph_engine:
            return
        try:
            snap.bottleneck_capabilities = self._graph_engine.bottlenecks(5)
        except Exception as exc:
            logger.debug("portfolio: bottlenecks fill failed: %s", exc)

    def _fill_gaps(self, snap: CapabilityPortfolioSnapshot) -> None:
        if not self._gap_engine:
            return
        try:
            critical = self._gap_engine.critical_gaps()
            snap.critical_gaps = [g.to_dict() for g in critical[:10]]
        except Exception as exc:
            logger.debug("portfolio: gaps fill failed: %s", exc)

    def _fill_agent_coverage(self, snap: CapabilityPortfolioSnapshot) -> None:
        if not self._agent_model:
            return
        try:
            if hasattr(self._agent_model, "summary"):
                snap.agent_coverage = self._agent_model.summary()
            elif hasattr(self._agent_model, "get_all_profiles"):
                profiles = self._agent_model.get_all_profiles()
                snap.agent_coverage = {
                    "agent_count": len(profiles),
                    "profiles": [p.to_dict() if hasattr(p, "to_dict") else str(p) for p in profiles[:5]],
                }
        except Exception as exc:
            logger.debug("portfolio: agent coverage fill failed: %s", exc)

    # ── Scoring ───────────────────────────────────────────────────

    def _compute_compounding_score(self, snap: CapabilityPortfolioSnapshot) -> float:
        """Compounding = weighted maturity distribution.

        Score 0.0–1.0. Higher when more capabilities are at higher maturity.
        institutional=1.0, operational=0.75, validated=0.5, emerging=0.25
        """
        if snap.total_capabilities == 0:
            return 0.0

        total_weighted = 0.0
        for mat, count in snap.by_maturity.items():
            weight = _MATURITY_SCORES.get(mat.lower(), 0.0)
            total_weighted += weight * count

        return round(total_weighted / snap.total_capabilities, 3)

    def _compute_maturity_velocity(self, snap: CapabilityPortfolioSnapshot) -> float:
        """Velocity = ratio of operational+ to total.

        Simple proxy: higher velocity = more capabilities reaching maturity.
        """
        if snap.total_capabilities == 0:
            return 0.0

        operational_plus = snap.by_maturity.get("operational", 0) + snap.by_maturity.get("institutional", 0)
        return round(operational_plus / snap.total_capabilities, 3)

    def _classify_health(self, snap: CapabilityPortfolioSnapshot) -> PortfolioHealth:
        """Deterministic health classification."""
        if snap.total_capabilities == 0:
            return PortfolioHealth.STAGNATING

        operational_plus = (
            snap.by_maturity.get("operational", 0)
            + snap.by_maturity.get("institutional", 0)
        )
        ratio = operational_plus / snap.total_capabilities

        critical_gap_count = len(snap.critical_gaps)

        if ratio >= 0.7 and snap.compounding_score >= 0.6 and critical_gap_count == 0:
            return PortfolioHealth.THRIVING
        if ratio >= 0.5 or (snap.compounding_score >= 0.4 and critical_gap_count <= 2):
            return PortfolioHealth.HEALTHY
        if ratio < 0.1 and snap.compounding_score <= 0.25:
            return PortfolioHealth.DECAYING
        return PortfolioHealth.STAGNATING
