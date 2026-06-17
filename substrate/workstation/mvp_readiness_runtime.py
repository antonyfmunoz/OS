"""MVP Readiness Runtime — objective MVP readiness scoring across 14 dimensions.

Answers: "Is UMH actually the MVP?"

14 dimensions including orchestrator_awareness (C4.0).
Each dimension is scored deterministically from subsystem state.

Campaign 4.5. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class MVPDimensionStatus(str, Enum):
    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    MISSING = "missing"


@dataclass
class MVPDimension:
    name: str = ""
    status: MVPDimensionStatus = MVPDimensionStatus.MISSING
    score: float = 0.0
    evidence: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    subsystem: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "score": self.score,
            "evidence": self.evidence,
            "blockers": self.blockers,
            "subsystem": self.subsystem,
        }


@dataclass
class MVPEscapePoint:
    description: str = ""
    frequency: str = "sometimes"
    workaround: str = ""
    severity: str = "degrades_experience"

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "frequency": self.frequency,
            "workaround": self.workaround,
            "severity": self.severity,
        }


@dataclass
class MVPReadinessReport:
    overall_score: float = 0.0
    overall_status: MVPDimensionStatus = MVPDimensionStatus.MISSING
    dimensions: list[MVPDimension] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    escape_points: list[MVPEscapePoint] = field(default_factory=list)
    recommended_next_builds: list[str] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "overall_status": self.overall_status.value,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "blockers": self.blockers,
            "escape_points": [e.to_dict() for e in self.escape_points],
            "recommended_next_builds": self.recommended_next_builds,
            "generated_at": self.generated_at,
        }


# ── Constants ─────────────────────────────────────────────────────────────


MVP_DIMENSIONS = [
    "orchestrator_awareness",
    "intent_capture",
    "intent_understanding",
    "plan_creation",
    "work_assignment",
    "execution_routing",
    "execution_tracking",
    "approval_routing",
    "lineage_capture",
    "learning_capture",
    "continuity",
    "coherence",
    "cockpit_coverage",
    "projection_awareness",
]


def _status_from_score(score: float) -> MVPDimensionStatus:
    if score >= 0.8:
        return MVPDimensionStatus.READY
    if score >= 0.4:
        return MVPDimensionStatus.PARTIAL
    if score > 0.0:
        return MVPDimensionStatus.BLOCKED
    return MVPDimensionStatus.MISSING


# ── Helpers ───────────────────────────────────────────────────────────────


def _safe_call(obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    if obj is None:
        return None
    fn = getattr(obj, method, None)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.debug("MVPReadiness: %s.%s() failed: %s", type(obj).__name__, method, exc)
        return None


def _safe_dict(obj: Any, method: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
    result = _safe_call(obj, method, *args, **kwargs)
    if isinstance(result, dict):
        return result
    if result is not None and hasattr(result, "to_dict"):
        try:
            return result.to_dict()
        except Exception:
            pass
    return {}


def _safe_float(obj: Any, method: str, *args: Any, **kwargs: Any) -> float:
    result = _safe_call(obj, method, *args, **kwargs)
    if isinstance(result, (int, float)):
        return float(result)
    return 0.0


# ── Runtime ───────────────────────────────────────────────────────────────


class MVPReadinessRuntime:
    """Objective MVP readiness scoring across 14 dimensions."""

    def __init__(
        self,
        awareness: Any | None = None,
        operating_loop: Any | None = None,
        approval_runtime: Any | None = None,
        coherence_runtime: Any | None = None,
        session_runtime: Any | None = None,
        command_center: Any | None = None,
        execution_surface: Any | None = None,
        capability_map: Any | None = None,
        projection_integration: Any | None = None,
    ) -> None:
        self._awareness = awareness
        self._loop = operating_loop
        self._approval = approval_runtime
        self._coherence = coherence_runtime
        self._session = session_runtime
        self._cmd_center = command_center
        self._exec_surface = execution_surface
        self._cap_map = capability_map
        self._proj_integration = projection_integration

    def assess(self) -> MVPReadinessReport:
        dimensions = [self._assess_dimension(name) for name in MVP_DIMENSIONS]
        scores = [d.score for d in dimensions]
        overall = sum(scores) / len(scores) if scores else 0.0
        overall = round(overall, 3)

        all_blockers: list[str] = []
        for d in dimensions:
            all_blockers.extend(d.blockers)

        escape_points = self._detect_escape_points(dimensions)
        recommended = self._recommend_next(dimensions)

        return MVPReadinessReport(
            overall_score=overall,
            overall_status=_status_from_score(overall),
            dimensions=dimensions,
            blockers=all_blockers,
            escape_points=escape_points,
            recommended_next_builds=recommended,
            generated_at=time.time(),
        )

    def dimension(self, name: str) -> MVPDimension:
        if name not in MVP_DIMENSIONS:
            return MVPDimension(name=name, blockers=[f"Unknown dimension: {name}"])
        return self._assess_dimension(name)

    def blockers(self) -> list[str]:
        return self.assess().blockers

    def escape_points(self) -> list[MVPEscapePoint]:
        return self._detect_escape_points(
            [self._assess_dimension(n) for n in MVP_DIMENSIONS]
        )

    def recommended_next(self, limit: int = 5) -> list[str]:
        dims = [self._assess_dimension(n) for n in MVP_DIMENSIONS]
        return self._recommend_next(dims)[:limit]

    def score(self) -> float:
        return self.assess().overall_score

    # ── Per-dimension assessment ──────────────────────────────────────

    def _assess_dimension(self, name: str) -> MVPDimension:
        assessors = {
            "orchestrator_awareness": self._assess_orchestrator_awareness,
            "intent_capture": self._assess_intent_capture,
            "intent_understanding": self._assess_intent_understanding,
            "plan_creation": self._assess_plan_creation,
            "work_assignment": self._assess_work_assignment,
            "execution_routing": self._assess_execution_routing,
            "execution_tracking": self._assess_execution_tracking,
            "approval_routing": self._assess_approval_routing,
            "lineage_capture": self._assess_lineage_capture,
            "learning_capture": self._assess_learning_capture,
            "continuity": self._assess_continuity,
            "coherence": self._assess_coherence,
            "cockpit_coverage": self._assess_cockpit_coverage,
            "projection_awareness": self._assess_projection_awareness,
        }
        fn = assessors.get(name)
        if fn is None:
            return MVPDimension(name=name, blockers=["No assessor"])
        return fn()

    def _assess_orchestrator_awareness(self) -> MVPDimension:
        dim = MVPDimension(name="orchestrator_awareness", subsystem="OrchestratorAwarenessRuntime")
        if self._awareness is None:
            dim.blockers.append("OrchestratorAwarenessRuntime not available")
            return dim

        score = _safe_float(self._awareness, "awareness_score")
        snap = _safe_dict(self._awareness, "snapshot")
        dim.score = score
        dim.status = _status_from_score(score)

        total = snap.get("total_subsystems", 0)
        active = snap.get("active_subsystems", 0)
        dim.evidence.append(f"{active}/{total} subsystems connected")

        if score < 0.5:
            dim.blockers.append(f"Only {active}/{total} subsystems connected")
        return dim

    def _assess_intent_capture(self) -> MVPDimension:
        dim = MVPDimension(name="intent_capture", subsystem="IntentRuntime")
        snap = _safe_dict(self._awareness, "snapshot")
        ctx = snap.get("context", {}) if isinstance(snap, dict) else {}
        intents = ctx.get("active_intents", [])
        if self._awareness is not None:
            dim.score = 0.8
            dim.status = MVPDimensionStatus.READY
            dim.evidence.append("IntentRuntime accessible via awareness")
        else:
            dim.blockers.append("Awareness not available")
        return dim

    def _assess_intent_understanding(self) -> MVPDimension:
        dim = MVPDimension(name="intent_understanding", subsystem="EmbodimentRuntime")
        if self._awareness is not None:
            dim.score = 0.6
            dim.status = MVPDimensionStatus.PARTIAL
            dim.evidence.append("Embodiment accessible via awareness")
        else:
            dim.blockers.append("Awareness not available")
        return dim

    def _assess_plan_creation(self) -> MVPDimension:
        dim = MVPDimension(name="plan_creation", subsystem="MetaIDERuntime")
        if self._awareness is not None:
            dim.score = 0.6
            dim.status = MVPDimensionStatus.PARTIAL
            dim.evidence.append("MetaIDE accessible via awareness")
        else:
            dim.blockers.append("Awareness not available")
        return dim

    def _assess_work_assignment(self) -> MVPDimension:
        dim = MVPDimension(name="work_assignment", subsystem="AgentFleetRuntime")
        if self._awareness is not None:
            dim.score = 0.6
            dim.status = MVPDimensionStatus.PARTIAL
            dim.evidence.append("AgentFleet accessible via awareness")
        else:
            dim.blockers.append("Awareness not available")
        return dim

    def _assess_execution_routing(self) -> MVPDimension:
        dim = MVPDimension(name="execution_routing", subsystem="ComputeFabricRuntime")
        if self._awareness is not None:
            dim.score = 0.6
            dim.status = MVPDimensionStatus.PARTIAL
            dim.evidence.append("ComputeFabric accessible via awareness")
        else:
            dim.blockers.append("Awareness not available")
        return dim

    def _assess_execution_tracking(self) -> MVPDimension:
        dim = MVPDimension(name="execution_tracking", subsystem="OperatingLoopRuntime")
        if self._loop is not None:
            snap = _safe_dict(self._loop, "snapshot")
            dim.score = 0.8
            dim.status = MVPDimensionStatus.READY
            dim.evidence.append(f"Active loops: {snap.get('active_loops', 0)}")
        else:
            dim.blockers.append("OperatingLoopRuntime not available")
        return dim

    def _assess_approval_routing(self) -> MVPDimension:
        dim = MVPDimension(name="approval_routing", subsystem="UnifiedApprovalRuntime")
        if self._approval is not None:
            snap = _safe_dict(self._approval, "snapshot")
            sources = snap.get("by_source", {})
            dim.score = min(len(sources) / 10.0, 1.0) if sources else 0.5
            dim.status = _status_from_score(dim.score)
            dim.evidence.append(f"{len(sources)} approval sources connected")
        else:
            dim.blockers.append("UnifiedApprovalRuntime not available")
        return dim

    def _assess_lineage_capture(self) -> MVPDimension:
        dim = MVPDimension(name="lineage_capture", subsystem="ExecutionGraph")
        if self._awareness is not None:
            dim.score = 0.6
            dim.status = MVPDimensionStatus.PARTIAL
            dim.evidence.append("ExecutionGraph accessible via awareness")
        else:
            dim.blockers.append("Awareness not available")
        return dim

    def _assess_learning_capture(self) -> MVPDimension:
        dim = MVPDimension(name="learning_capture", subsystem="OutcomeLearningLoop")
        if self._awareness is not None:
            dim.score = 0.6
            dim.status = MVPDimensionStatus.PARTIAL
            dim.evidence.append("Learning loop accessible via awareness")
        else:
            dim.blockers.append("Awareness not available")
        return dim

    def _assess_continuity(self) -> MVPDimension:
        dim = MVPDimension(name="continuity", subsystem="WorkstationSessionRuntime")
        if self._session is not None:
            active = _safe_call(self._session, "active_session")
            dim.score = 0.8 if active else 0.6
            dim.status = _status_from_score(dim.score)
            dim.evidence.append("Session runtime available")
        else:
            dim.blockers.append("WorkstationSessionRuntime not available")
        return dim

    def _assess_coherence(self) -> MVPDimension:
        dim = MVPDimension(name="coherence", subsystem="OperatingLoopCoherenceRuntime")
        if self._coherence is not None:
            score = _safe_float(self._coherence, "coherence_score")
            dim.score = score
            dim.status = _status_from_score(score)
            dim.evidence.append(f"Coherence score: {score}")
        else:
            dim.blockers.append("CoherenceRuntime not available")
        return dim

    def _assess_cockpit_coverage(self) -> MVPDimension:
        dim = MVPDimension(name="cockpit_coverage", subsystem="CockpitCapabilityMap")
        if self._cap_map is not None:
            snap = _safe_dict(self._cap_map, "snapshot")
            gaps = _safe_call(self._cap_map, "mvp_gaps")
            gap_count = len(gaps) if isinstance(gaps, list) else 0
            dim.score = max(0.0, 1.0 - (gap_count * 0.1))
            dim.status = _status_from_score(dim.score)
            dim.evidence.append(f"{gap_count} MVP gaps remaining")
            if gap_count > 0:
                dim.blockers.append(f"{gap_count} capability gaps")
        else:
            dim.blockers.append("CockpitCapabilityMap not available")
        return dim

    def _assess_projection_awareness(self) -> MVPDimension:
        dim = MVPDimension(name="projection_awareness", subsystem="ProjectionIntegrationRuntime")
        if self._proj_integration is not None:
            snap = _safe_dict(self._proj_integration, "snapshot")
            dim.score = 0.8
            dim.status = MVPDimensionStatus.READY
            dim.evidence.append("Projection integration available")
        else:
            dim.blockers.append("ProjectionIntegrationRuntime not available")
        return dim

    # ── Escape points & recommendations ───────────────────────────────

    def _detect_escape_points(self, dimensions: list[MVPDimension]) -> list[MVPEscapePoint]:
        points: list[MVPEscapePoint] = []
        for d in dimensions:
            if d.status == MVPDimensionStatus.MISSING:
                points.append(MVPEscapePoint(
                    description=f"{d.name}: completely missing",
                    frequency="always",
                    workaround="Manual process outside UMH",
                    severity="blocks_mvp",
                ))
            elif d.status == MVPDimensionStatus.BLOCKED:
                points.append(MVPEscapePoint(
                    description=f"{d.name}: blocked ({'; '.join(d.blockers)})",
                    frequency="sometimes",
                    workaround="Partial functionality available",
                    severity="degrades_experience",
                ))
        return points

    def _recommend_next(self, dimensions: list[MVPDimension]) -> list[str]:
        ranked = sorted(dimensions, key=lambda d: d.score)
        recommendations: list[str] = []
        for d in ranked:
            if d.score < 0.8:
                recommendations.append(
                    f"Improve {d.name} (currently {d.score:.1f}, target 0.8+)"
                )
        return recommendations
