"""
Capability Evolution Engine — Campaign 12.2

Tracks how capabilities change over time and recommends where to invest.
Bridges pattern intelligence into capability-specific growth trajectories.

Operator questions answered:
  - Which capabilities are maturing?
  - Which are declining or stalled?
  - What should we invest in next?
  - What outcomes are driving capability changes?
  - When will a capability reach the next maturity level?

Composes:
  - CapabilityRuntime (Gate 5) — capability CRUD + maturity + evidence
  - CapabilityPortfolioRuntime (C10.2) — portfolio health + compounding
  - OutcomePatternEngine (C12.1) — patterns affecting capabilities
  - LearningExtractionRuntime (C12.0) — gap lessons
  - CompoundingEngine — promotion pipeline

This runtime never mutates capability state. It observes and predicts.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
_DEFAULT_STORE = os.path.join(_REPO_ROOT, "data", "umh", "learning", "evolution_events.jsonl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class EvolutionEventType(str, Enum):
    """Types of capability evolution events."""
    MATURITY_ADVANCE = "maturity_advance"
    MATURITY_DECLINE = "maturity_decline"
    NEW_EVIDENCE = "new_evidence"
    GAP_IDENTIFIED = "gap_identified"
    GAP_CLOSED = "gap_closed"
    PATTERN_DRIVEN_PROPOSAL = "pattern_driven_proposal"
    OPERATIONALIZATION_LINKED = "operationalization_linked"


@dataclass
class EvolutionEvent:
    """A single evolution event for a capability."""
    event_id: str = ""
    capability_id: str = ""
    event_type: str = EvolutionEventType.NEW_EVIDENCE.value
    before_state: dict[str, Any] = field(default_factory=dict)
    after_state: dict[str, Any] = field(default_factory=dict)
    trigger_pattern_id: str = ""
    trigger_outcome_id: str = ""
    timestamp: float = 0.0
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EvolutionEvent:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


@dataclass
class CapabilityTrajectory:
    """Evolution trajectory for a single capability."""
    capability_id: str = ""
    capability_name: str = ""
    current_maturity: str = ""
    maturity_score: float = 0.0
    maturity_trend: float = 0.0
    evidence_count: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
    pattern_count: int = 0
    gap_lesson_count: int = 0
    predicted_next_level: str = ""
    time_to_next_level_days: float = -1.0
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["maturity_score"] = round(self.maturity_score, 4)
        d["maturity_trend"] = round(self.maturity_trend, 4)
        d["time_to_next_level_days"] = round(self.time_to_next_level_days, 1)
        return d


@dataclass
class EvolutionSnapshot:
    """Aggregate view of all capability evolution trajectories."""
    total_capabilities: int = 0
    advancing_count: int = 0
    declining_count: int = 0
    stalled_count: int = 0
    evolution_velocity: float = 0.0
    top_advancing: list[dict[str, Any]] = field(default_factory=list)
    top_declining: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["evolution_velocity"] = round(self.evolution_velocity, 4)
        return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Constants
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_STALLED_THRESHOLD_DAYS = 14.0
_MATURITY_LEVELS = ["emerging", "validated", "operational", "institutional"]
_TREND_WINDOW_EVENTS = 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CapabilityEvolutionEngine:
    """Tracks capability evolution trajectories and recommends investments."""

    def __init__(
        self,
        capability_runtime: Any | None = None,
        capability_portfolio: Any | None = None,
        outcome_patterns: Any | None = None,
        learning_extraction: Any | None = None,
        compounding_engine: Any | None = None,
        store_path: str = "",
    ) -> None:
        self._capability_runtime = capability_runtime
        self._capability_portfolio = capability_portfolio
        self._outcome_patterns = outcome_patterns
        self._learning_extraction = learning_extraction
        self._compounding_engine = compounding_engine
        self._store_path = store_path or _DEFAULT_STORE
        self._events: list[EvolutionEvent] = []
        self._load()

    # ── Lazy subsystem access ────────────────────────────────────────────

    @property
    def capability_runtime(self) -> Any | None:
        if self._capability_runtime is None:
            try:
                from substrate.organism.capability_runtime import CapabilityRuntime
                self._capability_runtime = CapabilityRuntime()
            except Exception:
                logger.debug("CapabilityRuntime unavailable")
        return self._capability_runtime

    @property
    def capability_portfolio(self) -> Any | None:
        if self._capability_portfolio is None:
            try:
                from substrate.organism.capability_portfolio_runtime import CapabilityPortfolioRuntime
                self._capability_portfolio = CapabilityPortfolioRuntime()
            except Exception:
                logger.debug("CapabilityPortfolioRuntime unavailable")
        return self._capability_portfolio

    @property
    def outcome_patterns(self) -> Any | None:
        if self._outcome_patterns is None:
            try:
                from substrate.organism.outcome_pattern_engine import OutcomePatternEngine
                self._outcome_patterns = OutcomePatternEngine()
            except Exception:
                logger.debug("OutcomePatternEngine unavailable")
        return self._outcome_patterns

    @property
    def learning_extraction(self) -> Any | None:
        if self._learning_extraction is None:
            try:
                from substrate.organism.learning_extraction_runtime import LearningExtractionRuntime
                self._learning_extraction = LearningExtractionRuntime()
            except Exception:
                logger.debug("LearningExtractionRuntime unavailable")
        return self._learning_extraction

    @property
    def compounding_engine(self) -> Any | None:
        if self._compounding_engine is None:
            try:
                from substrate.organism.compounding_engine import CompoundingEngine
                self._compounding_engine = CompoundingEngine()
            except Exception:
                logger.debug("CompoundingEngine unavailable")
        return self._compounding_engine

    # ── Persistence ──────────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.isfile(self._store_path):
            return
        try:
            with open(self._store_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    self._events.append(EvolutionEvent.from_dict(d))
        except Exception:
            logger.debug("Failed to load evolution events from %s", self._store_path)

    def _append(self, event: EvolutionEvent) -> None:
        try:
            os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
            with open(self._store_path, "a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception:
            logger.debug("Failed to append evolution event")

    # ── Trajectory computation ───────────────────────────────────────────

    def trajectory(self, capability_id: str) -> CapabilityTrajectory:
        """Compute the evolution trajectory for a single capability."""
        cr = self.capability_runtime

        # Get capability metadata
        cap_name = capability_id
        current_maturity = "unknown"
        maturity_score = 0.0
        evidence_count = 0

        if cr is not None:
            try:
                cap = cr.get(capability_id)
                if cap is not None:
                    cap_name = getattr(cap, "name", capability_id)
                    mat = getattr(cap, "maturity", "unknown")
                    current_maturity = mat.value if hasattr(mat, "value") else str(mat)
                    maturity_score = cr.maturity_score(capability_id)
                    evidence = cr.evidence_for(capability_id)
                    evidence_count = len(evidence) if evidence else 0
            except Exception:
                logger.debug("Failed to get capability %s", capability_id)

        # Get evolution events for this capability
        cap_events = [e for e in self._events if e.capability_id == capability_id]
        cap_events.sort(key=lambda e: e.timestamp)

        # Compute maturity trend from recent events
        maturity_trend = self._compute_trend(cap_events)

        # Get pattern context
        pattern_count = 0
        op = self.outcome_patterns
        if op is not None:
            try:
                patterns = op.patterns_for_capability(capability_id)
                pattern_count = len(patterns)
            except Exception:
                pass

        # Get gap lesson count
        gap_lesson_count = 0
        le = self.learning_extraction
        if le is not None:
            try:
                gap_lessons = le.lessons_by_category("capability_gap")
                gap_lesson_count = sum(
                    1 for l in gap_lessons
                    if capability_id in getattr(l, "related_capability_ids", [])
                )
            except Exception:
                pass

        # Predict next level
        predicted_next, time_to_next = self._predict_next_level(
            current_maturity, maturity_score, maturity_trend
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            cap_name, current_maturity, maturity_trend, pattern_count, gap_lesson_count
        )

        return CapabilityTrajectory(
            capability_id=capability_id,
            capability_name=cap_name,
            current_maturity=current_maturity,
            maturity_score=maturity_score,
            maturity_trend=maturity_trend,
            evidence_count=evidence_count,
            events=[e.to_dict() for e in cap_events[-10:]],
            pattern_count=pattern_count,
            gap_lesson_count=gap_lesson_count,
            predicted_next_level=predicted_next,
            time_to_next_level_days=time_to_next,
            recommendation=recommendation,
        )

    def _compute_trend(self, events: list[EvolutionEvent]) -> float:
        """Compute maturity trend from recent events. Positive = advancing."""
        if len(events) < 2:
            return 0.0

        recent = events[-_TREND_WINDOW_EVENTS:]
        advances = sum(1 for e in recent if e.event_type == EvolutionEventType.MATURITY_ADVANCE.value)
        declines = sum(1 for e in recent if e.event_type == EvolutionEventType.MATURITY_DECLINE.value)
        new_evidence = sum(1 for e in recent if e.event_type == EvolutionEventType.NEW_EVIDENCE.value)

        # Trend: advances and evidence push positive, declines push negative
        score = (advances * 1.0 + new_evidence * 0.3 - declines * 1.0) / len(recent)
        return max(-1.0, min(1.0, score))

    def _predict_next_level(
        self, current: str, score: float, trend: float
    ) -> tuple[str, float]:
        """Predict next maturity level and time to reach it."""
        current_lower = current.lower()
        if current_lower not in _MATURITY_LEVELS:
            return "", -1.0

        idx = _MATURITY_LEVELS.index(current_lower)
        if idx >= len(_MATURITY_LEVELS) - 1:
            return "institutional (max)", -1.0

        next_level = _MATURITY_LEVELS[idx + 1]

        if trend <= 0:
            return next_level, -1.0

        # Rough estimation based on maturity score thresholds
        thresholds = {"emerging": 0.25, "validated": 0.5, "operational": 0.75, "institutional": 1.0}
        target = thresholds.get(next_level, 1.0)
        gap = max(0, target - score)

        if trend > 0 and gap > 0:
            days = gap / (trend * 0.1) if trend * 0.1 > 0 else -1.0
            return next_level, min(days, 365.0)

        return next_level, -1.0

    def _generate_recommendation(
        self,
        name: str,
        maturity: str,
        trend: float,
        pattern_count: int,
        gap_count: int,
    ) -> str:
        """Generate actionable recommendation based on trajectory analysis."""
        if gap_count > 2 and trend <= 0:
            return f"Critical: '{name}' has {gap_count} gap lessons and declining trend — prioritize remediation"
        if pattern_count > 3 and maturity in ("emerging", "validated"):
            return f"Invest: '{name}' has strong pattern evidence but low maturity — accelerate growth"
        if trend > 0.5:
            return f"Momentum: '{name}' is advancing rapidly — maintain current approach"
        if trend < -0.3:
            return f"Attention: '{name}' is declining — investigate root cause"
        if trend == 0.0 and maturity not in ("institutional",):
            return f"Stalled: '{name}' shows no evolution — consider active investment or retire"
        return ""

    # ── Record events ────────────────────────────────────────────────────

    def record_evolution(
        self,
        capability_id: str,
        event_type: str,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        trigger_pattern_id: str = "",
        trigger_outcome_id: str = "",
        description: str = "",
    ) -> EvolutionEvent:
        """Record a capability evolution event."""
        event = EvolutionEvent(
            event_id=f"evo-{uuid.uuid4().hex[:12]}",
            capability_id=capability_id,
            event_type=event_type,
            before_state=before_state or {},
            after_state=after_state or {},
            trigger_pattern_id=trigger_pattern_id,
            trigger_outcome_id=trigger_outcome_id,
            timestamp=time.time(),
            description=description,
        )
        self._events.append(event)
        self._append(event)
        return event

    # ── Public API ────────────────────────────────────────────────────────

    def all_trajectories(self) -> list[CapabilityTrajectory]:
        """Compute trajectories for all known capabilities."""
        cr = self.capability_runtime
        if cr is None:
            return []

        trajectories: list[CapabilityTrajectory] = []
        try:
            capabilities = cr.list_capabilities()
            for cap in capabilities:
                cid = getattr(cap, "capability_id", "")
                if cid:
                    trajectories.append(self.trajectory(cid))
        except Exception:
            logger.debug("Failed to compute all trajectories")

        return trajectories

    def advancing(self) -> list[CapabilityTrajectory]:
        """Return capabilities with positive maturity trend."""
        return [t for t in self.all_trajectories() if t.maturity_trend > 0]

    def declining(self) -> list[CapabilityTrajectory]:
        """Return capabilities with negative maturity trend."""
        return [t for t in self.all_trajectories() if t.maturity_trend < 0]

    def stalled(self, days: float = _STALLED_THRESHOLD_DAYS) -> list[CapabilityTrajectory]:
        """Return capabilities with no evolution within threshold."""
        now = time.time()
        cutoff = now - (days * 86400)
        result: list[CapabilityTrajectory] = []

        for traj in self.all_trajectories():
            if traj.maturity_trend != 0.0:
                continue
            # Check if any events exist within the window
            cap_events = [e for e in self._events if e.capability_id == traj.capability_id]
            recent = [e for e in cap_events if e.timestamp > cutoff]
            if not recent:
                result.append(traj)

        return result

    def evolution_recommendations(self) -> list[dict[str, Any]]:
        """Generate prioritized recommendations for capability investment."""
        recs: list[dict[str, Any]] = []
        for traj in self.all_trajectories():
            if traj.recommendation:
                priority = 0.0
                if "Critical" in traj.recommendation:
                    priority = 1.0
                elif "Invest" in traj.recommendation:
                    priority = 0.8
                elif "Attention" in traj.recommendation:
                    priority = 0.6
                elif "Stalled" in traj.recommendation:
                    priority = 0.4
                elif "Momentum" in traj.recommendation:
                    priority = 0.2
                recs.append({
                    "capability_id": traj.capability_id,
                    "capability_name": traj.capability_name,
                    "recommendation": traj.recommendation,
                    "priority": priority,
                    "maturity": traj.current_maturity,
                    "trend": round(traj.maturity_trend, 4),
                })

        return sorted(recs, key=lambda r: r["priority"], reverse=True)

    def snapshot(self) -> EvolutionSnapshot:
        """Full evolution snapshot."""
        now = time.time()
        trajectories = self.all_trajectories()

        advancing_list = [t for t in trajectories if t.maturity_trend > 0]
        declining_list = [t for t in trajectories if t.maturity_trend < 0]
        stalled_count = sum(1 for t in trajectories if t.maturity_trend == 0.0)

        # Evolution velocity: events per day in last 7d
        cutoff = now - (7 * 86400)
        recent_events = [e for e in self._events if e.timestamp > cutoff]
        velocity = len(recent_events) / 7.0 if recent_events else 0.0

        recs = self.evolution_recommendations()

        return EvolutionSnapshot(
            total_capabilities=len(trajectories),
            advancing_count=len(advancing_list),
            declining_count=len(declining_list),
            stalled_count=stalled_count,
            evolution_velocity=velocity,
            top_advancing=[t.to_dict() for t in advancing_list[:5]],
            top_declining=[t.to_dict() for t in declining_list[:5]],
            recommendations=recs[:10],
            generated_at=now,
        )

    def summary(self) -> dict[str, Any]:
        """Compact summary for API consumption."""
        snap = self.snapshot()
        return snap.to_dict()

    def health(self) -> str:
        """Quick health classification."""
        snap = self.snapshot()
        if snap.total_capabilities == 0:
            return "unknown"
        if snap.advancing_count > snap.declining_count and snap.evolution_velocity > 0:
            return "evolving"
        if snap.declining_count > snap.advancing_count:
            return "declining"
        if snap.stalled_count > snap.total_capabilities * 0.7:
            return "stalled"
        if snap.evolution_velocity > 0:
            return "stable"
        return "dormant"
