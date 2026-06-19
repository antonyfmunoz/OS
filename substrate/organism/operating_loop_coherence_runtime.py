"""Operating Loop Coherence Runtime — aggregation, reporting, coherence synthesis.

Answers: "Do all systems agree on reality after loops execute?"

This is NOT a validator. It aggregates coherence state from 7 existing systems
plus C4.0–C4.2 into a unified report. Detection methods surface orphans,
broken chains, stale approvals, and contradictions.

Campaign 4.3. UMH substrate layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


class LoopCoherenceStatus(str, Enum):
    COHERENT = "coherent"
    DRIFT_DETECTED = "drift_detected"
    ORPHANED = "orphaned"
    INCOMPLETE = "incomplete"


class LoopCoherenceIssueType(str, Enum):
    ORPHAN_INTENT = "orphan_intent"
    ORPHAN_WORK = "orphan_work"
    MISSING_LINEAGE = "missing_lineage"
    MISSING_LEARNING = "missing_learning"
    STALE_APPROVAL = "stale_approval"
    BROKEN_CHAIN = "broken_chain"
    MISSING_PROOF = "missing_proof"
    CONTRADICTION_DETECTED = "contradiction_detected"


@dataclass
class LoopCoherenceIssue:
    issue_id: str = ""
    issue_type: LoopCoherenceIssueType = LoopCoherenceIssueType.ORPHAN_INTENT
    severity: str = "medium"
    description: str = ""
    affected_loop_id: str = ""
    affected_subsystem: str = ""
    recommendation: str = ""

    def __post_init__(self) -> None:
        if not self.issue_id:
            self.issue_id = f"lci-{uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "issue_type": self.issue_type.value,
            "severity": self.severity,
            "description": self.description,
            "affected_loop_id": self.affected_loop_id,
            "affected_subsystem": self.affected_subsystem,
            "recommendation": self.recommendation,
        }


@dataclass
class LoopCoherenceReport:
    overall_status: LoopCoherenceStatus = LoopCoherenceStatus.COHERENT
    coherence_score: float = 1.0
    issues: list[LoopCoherenceIssue] = field(default_factory=list)
    subsystem_health: dict[str, str] = field(default_factory=dict)
    state_coherence: dict[str, Any] = field(default_factory=dict)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    awareness_score: float = 0.0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "coherence_score": self.coherence_score,
            "issues": [i.to_dict() for i in self.issues],
            "subsystem_health": self.subsystem_health,
            "state_coherence": self.state_coherence,
            "contradictions": self.contradictions,
            "awareness_score": self.awareness_score,
            "generated_at": self.generated_at,
        }


# ── Helpers ───────────────────────────────────────────────────────────────

_STALE_APPROVAL_SECONDS = 86400.0  # 24 hours

_EXPECTED_COMPLETE_STAGES = {"intent", "plan", "assign", "execute", "review", "approve", "learn", "complete"}


def _safe_call(obj: Any, method: str, *args: Any, **kwargs: Any) -> Any:
    if obj is None:
        return None
    fn = getattr(obj, method, None)
    if fn is None:
        return None
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.debug("Coherence: %s.%s() failed: %s", type(obj).__name__, method, exc)
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


def _safe_list(obj: Any, method: str, *args: Any, **kwargs: Any) -> list[Any]:
    result = _safe_call(obj, method, *args, **kwargs)
    if isinstance(result, list):
        return result
    return []


# ── Runtime ───────────────────────────────────────────────────────────────


class OperatingLoopCoherenceRuntime:
    """Aggregation, reporting, and coherence synthesis for operating loops.

    Composes 7 existing coherence systems + C4.0/C4.1/C4.2 into a single
    coherence view. All detection methods are deterministic and read-only.
    """

    def __init__(
        self,
        state_coherence: Any | None = None,
        execution_graph: Any | None = None,
        contradiction_engine: Any | None = None,
        learning_loop: Any | None = None,
        intent_runtime: Any | None = None,
        governed_work: Any | None = None,
        approval_runtime: Any | None = None,
        loop_runtime: Any | None = None,
        awareness: Any | None = None,
    ) -> None:
        self._state_coherence = state_coherence
        self._graph = execution_graph
        self._contradictions = contradiction_engine
        self._learning = learning_loop
        self._intent = intent_runtime
        self._governed = governed_work
        self._approvals = approval_runtime
        self._loops = loop_runtime
        self._awareness = awareness

    # ── Primary ───────────────────────────────────────────────────────

    def full_report(self) -> LoopCoherenceReport:
        issues: list[LoopCoherenceIssue] = []
        issues.extend(self.detect_orphans())
        issues.extend(self.detect_broken_chains())
        issues.extend(self.detect_stale_approvals())
        issues.extend(self.detect_contradictions())

        state_coh = _safe_dict(self._state_coherence, "coherence_report")
        contradictions_raw = _safe_list(self._contradictions, "detect_contradictions")
        contradiction_dicts = []
        for c in contradictions_raw:
            if isinstance(c, dict):
                contradiction_dicts.append(c)
            elif hasattr(c, "to_dict"):
                try:
                    contradiction_dicts.append(c.to_dict())
                except Exception:
                    contradiction_dicts.append({"value": str(c)})

        awareness_sc = 0.0
        aw_result = _safe_call(self._awareness, "awareness_score")
        if isinstance(aw_result, (int, float)):
            awareness_sc = float(aw_result)

        score = self._compute_score(issues)
        status = self._derive_status(issues, score)

        subsystem_health = self._build_subsystem_health()

        return LoopCoherenceReport(
            overall_status=status,
            coherence_score=score,
            issues=issues,
            subsystem_health=subsystem_health,
            state_coherence=state_coh,
            contradictions=contradiction_dicts,
            awareness_score=awareness_sc,
            generated_at=time.time(),
        )

    def validate_loop(self, loop: Any) -> LoopCoherenceReport:
        issues: list[LoopCoherenceIssue] = []
        loop_id = getattr(loop, "loop_id", "") or ""
        intent_id = getattr(loop, "intent_id", "") or ""
        lineage = getattr(loop, "lineage", []) or []
        current_stage = getattr(loop, "current_stage", None)
        stage_val = current_stage.value if hasattr(current_stage, "value") else str(current_stage)

        if not intent_id:
            issues.append(LoopCoherenceIssue(
                issue_type=LoopCoherenceIssueType.ORPHAN_INTENT,
                severity="high",
                description="Loop has no intent_id — cannot trace lineage",
                affected_loop_id=loop_id,
                affected_subsystem="intent_runtime",
                recommendation="Ensure loop is tracked with an intent_id",
            ))

        if stage_val == "complete":
            stages_seen = set()
            for t in lineage:
                to_stage = getattr(t, "to_stage", None)
                if to_stage is not None:
                    sv = to_stage.value if hasattr(to_stage, "value") else str(to_stage)
                    stages_seen.add(sv)
            missing = _EXPECTED_COMPLETE_STAGES - stages_seen
            if missing:
                issues.append(LoopCoherenceIssue(
                    issue_type=LoopCoherenceIssueType.BROKEN_CHAIN,
                    severity="medium",
                    description=f"Completed loop missing stages: {sorted(missing)}",
                    affected_loop_id=loop_id,
                    affected_subsystem="loop_runtime",
                    recommendation="Ensure all stages are recorded before completion",
                ))

            if intent_id and self._graph is not None:
                graph_result = _safe_call(self._graph, "trace_from_intent", intent_id)
                if not graph_result:
                    issues.append(LoopCoherenceIssue(
                        issue_type=LoopCoherenceIssueType.MISSING_LINEAGE,
                        severity="high",
                        description="Completed loop has no execution graph lineage",
                        affected_loop_id=loop_id,
                        affected_subsystem="execution_graph",
                        recommendation="Record lineage in ExecutionGraph during execution",
                    ))

            outcomes = _safe_list(self._learning, "recent_outcomes")
            has_outcome = any(
                (isinstance(o, dict) and o.get("intent_id") == intent_id) or
                (hasattr(o, "intent_id") and getattr(o, "intent_id") == intent_id)
                for o in outcomes
            ) if intent_id and outcomes else False
            if not has_outcome and intent_id:
                issues.append(LoopCoherenceIssue(
                    issue_type=LoopCoherenceIssueType.MISSING_LEARNING,
                    severity="low",
                    description="Completed loop has no learning outcome recorded",
                    affected_loop_id=loop_id,
                    affected_subsystem="learning_loop",
                    recommendation="Record outcome in OutcomeLearningLoop after completion",
                ))

        score = self._compute_score(issues)
        status = self._derive_status(issues, score)

        return LoopCoherenceReport(
            overall_status=status,
            coherence_score=score,
            issues=issues,
            subsystem_health={},
            state_coherence={},
            contradictions=[],
            awareness_score=0.0,
            generated_at=time.time(),
        )

    # ── Detection ─────────────────────────────────────────────────────

    def detect_orphans(self) -> list[LoopCoherenceIssue]:
        issues: list[LoopCoherenceIssue] = []

        active_intents = _safe_list(self._intent, "active_by_scope")
        active_loops = _safe_list(self._loops, "active_loops")
        active_work = _safe_list(self._governed, "active")

        loop_intent_ids: set[str] = set()
        for loop in active_loops:
            iid = getattr(loop, "intent_id", None) or (loop.get("intent_id") if isinstance(loop, dict) else "")
            if iid:
                loop_intent_ids.add(iid)

        for intent in active_intents:
            iid = intent.get("intent_id", "") if isinstance(intent, dict) else getattr(intent, "intent_id", "")
            if iid and iid not in loop_intent_ids:
                issues.append(LoopCoherenceIssue(
                    issue_type=LoopCoherenceIssueType.ORPHAN_INTENT,
                    severity="medium",
                    description=f"Intent {iid} has no tracked operating loop",
                    affected_loop_id="",
                    affected_subsystem="intent_runtime",
                    recommendation="Track intent with OperatingLoopRuntime.track()",
                ))

        loop_work_ids: set[str] = set()
        for loop in active_loops:
            wids = getattr(loop, "work_ids", None) or (loop.get("work_ids") if isinstance(loop, dict) else [])
            if isinstance(wids, list):
                loop_work_ids.update(wids)

        for work in active_work:
            wid = work.get("work_id", "") if isinstance(work, dict) else getattr(work, "work_id", "")
            if wid and wid not in loop_work_ids:
                issues.append(LoopCoherenceIssue(
                    issue_type=LoopCoherenceIssueType.ORPHAN_WORK,
                    severity="medium",
                    description=f"Work {wid} not associated with any operating loop",
                    affected_loop_id="",
                    affected_subsystem="governed_work",
                    recommendation="Associate work with a tracked loop",
                ))

        return issues

    def detect_broken_chains(self) -> list[LoopCoherenceIssue]:
        issues: list[LoopCoherenceIssue] = []
        active_loops = _safe_list(self._loops, "active_loops")

        for loop in active_loops:
            lineage = getattr(loop, "lineage", None) or (loop.get("lineage") if isinstance(loop, dict) else [])
            if not isinstance(lineage, list) or len(lineage) < 2:
                continue

            prev_stage = None
            for transition in lineage:
                from_s = getattr(transition, "from_stage", None) or (transition.get("from_stage") if isinstance(transition, dict) else None)
                if from_s is not None and prev_stage is not None:
                    from_val = from_s.value if hasattr(from_s, "value") else str(from_s)
                    prev_val = prev_stage.value if hasattr(prev_stage, "value") else str(prev_stage)
                    if from_val != prev_val:
                        loop_id = getattr(loop, "loop_id", "") or (loop.get("loop_id") if isinstance(loop, dict) else "")
                        issues.append(LoopCoherenceIssue(
                            issue_type=LoopCoherenceIssueType.BROKEN_CHAIN,
                            severity="high",
                            description=f"Transition gap: from_stage={from_val} but previous to_stage={prev_val}",
                            affected_loop_id=loop_id,
                            affected_subsystem="loop_runtime",
                            recommendation="Ensure transitions are sequential",
                        ))

                to_s = getattr(transition, "to_stage", None) or (transition.get("to_stage") if isinstance(transition, dict) else None)
                prev_stage = to_s

        return issues

    def detect_stale_approvals(self) -> list[LoopCoherenceIssue]:
        issues: list[LoopCoherenceIssue] = []
        pending = _safe_list(self._approvals, "pending")
        now = time.time()

        for approval in pending:
            waiting_since = 0.0
            if isinstance(approval, dict):
                waiting_since = approval.get("waiting_since", 0.0)
            else:
                waiting_since = getattr(approval, "waiting_since", 0.0)

            if waiting_since > 0 and (now - waiting_since) > _STALE_APPROVAL_SECONDS:
                aid = ""
                if isinstance(approval, dict):
                    aid = approval.get("approval_id", "")
                else:
                    aid = getattr(approval, "approval_id", "")

                age_hours = round((now - waiting_since) / 3600, 1)
                issues.append(LoopCoherenceIssue(
                    issue_type=LoopCoherenceIssueType.STALE_APPROVAL,
                    severity="high",
                    description=f"Approval {aid} pending for {age_hours}h (> 24h threshold)",
                    affected_loop_id="",
                    affected_subsystem="approval_runtime",
                    recommendation="Review and decide on stale approvals",
                ))

        return issues

    def detect_contradictions(self) -> list[LoopCoherenceIssue]:
        issues: list[LoopCoherenceIssue] = []
        contradictions = _safe_list(self._contradictions, "detect_contradictions")

        for c in contradictions:
            desc = ""
            ctype = ""
            if isinstance(c, dict):
                desc = c.get("description", str(c))
                ctype = c.get("type", "unknown")
            else:
                desc = getattr(c, "description", str(c))
                ctype = getattr(c, "contradiction_type", "unknown")
                if hasattr(ctype, "value"):
                    ctype = ctype.value

            issues.append(LoopCoherenceIssue(
                issue_type=LoopCoherenceIssueType.CONTRADICTION_DETECTED,
                severity="high",
                description=f"Contradiction ({ctype}): {desc}",
                affected_loop_id="",
                affected_subsystem="contradiction_engine",
                recommendation="Resolve declared-vs-observed mismatch",
            ))

        return issues

    def coherence_score(self) -> float:
        report = self.full_report()
        return report.coherence_score

    # ── Private ───────────────────────────────────────────────────────

    def _compute_score(self, issues: list[LoopCoherenceIssue]) -> float:
        if not issues:
            return 1.0
        severity_weights = {"critical": 0.25, "high": 0.15, "medium": 0.08, "low": 0.03}
        penalty = sum(severity_weights.get(i.severity, 0.05) for i in issues)
        return round(max(0.0, 1.0 - penalty), 3)

    def _derive_status(
        self,
        issues: list[LoopCoherenceIssue],
        score: float,
    ) -> LoopCoherenceStatus:
        if not issues:
            return LoopCoherenceStatus.COHERENT
        has_orphan = any(
            i.issue_type in (LoopCoherenceIssueType.ORPHAN_INTENT, LoopCoherenceIssueType.ORPHAN_WORK)
            for i in issues
        )
        if has_orphan:
            return LoopCoherenceStatus.ORPHANED
        has_incomplete = any(
            i.issue_type in (
                LoopCoherenceIssueType.BROKEN_CHAIN,
                LoopCoherenceIssueType.MISSING_LINEAGE,
                LoopCoherenceIssueType.MISSING_LEARNING,
            )
            for i in issues
        )
        if has_incomplete:
            return LoopCoherenceStatus.INCOMPLETE
        return LoopCoherenceStatus.DRIFT_DETECTED

    def _build_subsystem_health(self) -> dict[str, str]:
        subsystems = {
            "state_coherence": self._state_coherence,
            "execution_graph": self._graph,
            "contradiction_engine": self._contradictions,
            "learning_loop": self._learning,
            "intent_runtime": self._intent,
            "governed_work": self._governed,
            "approval_runtime": self._approvals,
            "loop_runtime": self._loops,
            "awareness": self._awareness,
        }
        return {
            name: "available" if dep is not None else "unavailable"
            for name, dep in subsystems.items()
        }
