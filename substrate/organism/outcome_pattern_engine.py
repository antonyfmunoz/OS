"""
Outcome Pattern Engine — Campaign 12.1

The intellectual core of the learning intelligence layer.
Detects recurring success/failure patterns, correlates outcomes
with decisions, and attributes causation across the subsystem graph.

Operator questions answered:
  - Why did this outcome happen?
  - What decisions correlate with success?
  - What capability bottlenecks keep recurring?
  - Are there assumption chain failures?
  - What patterns are emerging in our execution?

Composes:
  - LearningExtractionRuntime (C12.0) — semantic lessons
  - DecisionLineageEngine — decision causation tracing
  - DecisionValidityEngine — decision health
  - DecisionImpactEngine — decision blast radius
  - OutcomeLearningLoop — mechanical outcome data
  - CompoundingEngine — promotion pipeline signals
  - GoalHierarchyEngine — goal tree navigation

This is where outcome → cause → correlation → pattern is established.
Everything downstream depends on this being correct.
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
_DEFAULT_STORE = os.path.join(_REPO_ROOT, "data", "umh", "learning", "patterns.jsonl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PatternType(str, Enum):
    """Classification of detected patterns."""
    RECURRING_SUCCESS = "recurring_success"
    RECURRING_FAILURE = "recurring_failure"
    DECISION_CORRELATION = "decision_correlation"
    CAPABILITY_BOTTLENECK = "capability_bottleneck"
    ASSUMPTION_CHAIN_FAILURE = "assumption_chain_failure"
    GOAL_DRIFT_PATTERN = "goal_drift_pattern"
    VELOCITY_TREND = "velocity_trend"


@dataclass
class DetectedPattern:
    """A recurring pattern detected across subsystem evidence."""
    pattern_id: str = ""
    pattern_type: str = PatternType.RECURRING_SUCCESS.value
    title: str = ""
    description: str = ""
    evidence: list[str] = field(default_factory=list)
    occurrences: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0
    confidence: float = 0.0
    confidence_reason: str = ""
    affected_goals: list[str] = field(default_factory=list)
    affected_decisions: list[str] = field(default_factory=list)
    affected_capabilities: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["confidence"] = round(self.confidence, 4)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DetectedPattern:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


@dataclass
class AttributionLink:
    """A causal or correlative link between two entities."""
    source_type: str = ""
    source_id: str = ""
    target_type: str = ""
    target_id: str = ""
    strength: float = 0.0
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["strength"] = round(self.strength, 4)
        return d


@dataclass
class PatternSnapshot:
    """Aggregate view of all detected patterns."""
    total_patterns: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    top_patterns: list[dict[str, Any]] = field(default_factory=list)
    attribution_links: list[dict[str, Any]] = field(default_factory=list)
    top_correlations: list[dict[str, Any]] = field(default_factory=list)
    pattern_velocity: float = 0.0
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pattern_velocity"] = round(self.pattern_velocity, 4)
        return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pattern detection thresholds
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_MIN_OCCURRENCES = 3
_PROXIMITY_DECAY = 0.5
_HIGH_RELIABILITY_THRESHOLD = 0.8
_LOW_RELIABILITY_THRESHOLD = 0.3
_PATTERN_WINDOW_DAYS = 30


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OutcomePatternEngine:
    """Detects recurring patterns and attributes causation across subsystems.

    This is the intellectual heart of the learning layer. It establishes
    outcome → cause → correlation → pattern chains that everything
    downstream depends on.
    """

    def __init__(
        self,
        learning_extraction: Any | None = None,
        decision_lineage: Any | None = None,
        decision_validity: Any | None = None,
        decision_impact: Any | None = None,
        outcome_learning: Any | None = None,
        compounding_engine: Any | None = None,
        goal_hierarchy: Any | None = None,
        store_path: str = "",
    ) -> None:
        self._learning_extraction = learning_extraction
        self._decision_lineage = decision_lineage
        self._decision_validity = decision_validity
        self._decision_impact = decision_impact
        self._outcome_learning = outcome_learning
        self._compounding_engine = compounding_engine
        self._goal_hierarchy = goal_hierarchy
        self._store_path = store_path or _DEFAULT_STORE
        self._patterns: list[DetectedPattern] = []
        self._pattern_hashes: set[str] = set()
        self._load()

    # ── Lazy subsystem access ────────────────────────────────────────────

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
    def decision_lineage(self) -> Any | None:
        if self._decision_lineage is None:
            try:
                from substrate.organism.decision_lineage_engine import DecisionLineageEngine
                self._decision_lineage = DecisionLineageEngine()
            except Exception:
                logger.debug("DecisionLineageEngine unavailable")
        return self._decision_lineage

    @property
    def decision_validity(self) -> Any | None:
        if self._decision_validity is None:
            try:
                from substrate.organism.decision_validity_engine import DecisionValidityEngine
                self._decision_validity = DecisionValidityEngine()
            except Exception:
                logger.debug("DecisionValidityEngine unavailable")
        return self._decision_validity

    @property
    def decision_impact(self) -> Any | None:
        if self._decision_impact is None:
            try:
                from substrate.organism.decision_impact_engine import DecisionImpactEngine
                self._decision_impact = DecisionImpactEngine()
            except Exception:
                logger.debug("DecisionImpactEngine unavailable")
        return self._decision_impact

    @property
    def outcome_learning(self) -> Any | None:
        if self._outcome_learning is None:
            try:
                from substrate.organism.outcome_learning import OutcomeLearningLoop
                self._outcome_learning = OutcomeLearningLoop()
            except Exception:
                logger.debug("OutcomeLearningLoop unavailable")
        return self._outcome_learning

    @property
    def compounding_engine(self) -> Any | None:
        if self._compounding_engine is None:
            try:
                from substrate.organism.compounding_engine import CompoundingEngine
                self._compounding_engine = CompoundingEngine()
            except Exception:
                logger.debug("CompoundingEngine unavailable")
        return self._compounding_engine

    @property
    def goal_hierarchy(self) -> Any | None:
        if self._goal_hierarchy is None:
            try:
                from substrate.organism.goal_hierarchy_engine import GoalHierarchyEngine
                self._goal_hierarchy = GoalHierarchyEngine()
            except Exception:
                logger.debug("GoalHierarchyEngine unavailable")
        return self._goal_hierarchy

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
                    pattern = DetectedPattern.from_dict(d)
                    self._patterns.append(pattern)
                    h = self._pattern_hash(pattern.pattern_type, pattern.evidence)
                    self._pattern_hashes.add(h)
        except Exception:
            logger.debug("Failed to load patterns from %s", self._store_path)

    def _append(self, pattern: DetectedPattern) -> None:
        try:
            os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
            with open(self._store_path, "a") as f:
                f.write(json.dumps(pattern.to_dict()) + "\n")
        except Exception:
            logger.debug("Failed to append pattern to %s", self._store_path)

    @staticmethod
    def _pattern_hash(pattern_type: str, evidence: list[str]) -> str:
        combined = pattern_type + "|" + "|".join(sorted(evidence))
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _store_pattern(self, pattern: DetectedPattern) -> DetectedPattern:
        h = self._pattern_hash(pattern.pattern_type, pattern.evidence)
        if h in self._pattern_hashes:
            for existing in self._patterns:
                if self._pattern_hash(existing.pattern_type, existing.evidence) == h:
                    existing.occurrences = max(existing.occurrences, pattern.occurrences)
                    existing.last_seen = max(existing.last_seen, pattern.last_seen)
                    return existing
            return pattern
        self._pattern_hashes.add(h)
        self._patterns.append(pattern)
        self._append(pattern)
        return pattern

    # ── Core detection ───────────────────────────────────────────────────

    def detect_patterns(self, window_days: float = _PATTERN_WINDOW_DAYS) -> list[DetectedPattern]:
        """Run all pattern detectors and return newly detected patterns."""
        new_patterns: list[DetectedPattern] = []

        self._detect_recurring_outcome_patterns(window_days, new_patterns)
        self._detect_decision_correlations(new_patterns)
        self._detect_capability_bottlenecks(new_patterns)
        self._detect_assumption_chain_failures(new_patterns)
        self._detect_velocity_trends(new_patterns)

        return new_patterns

    def _detect_recurring_outcome_patterns(
        self, window_days: float, results: list[DetectedPattern]
    ) -> None:
        """Group outcomes by action_type and detect recurring success/failure."""
        ol = self.outcome_learning
        if ol is None:
            return

        try:
            outcomes = ol.recent_outcomes(limit=100)
        except Exception:
            return

        cutoff = time.time() - (window_days * 86400)
        by_action: dict[str, dict[str, list[Any]]] = {}

        for rec in outcomes:
            ts = getattr(rec, "timestamp", 0.0)
            if ts < cutoff:
                continue
            action_type = getattr(rec, "action_type", "unknown")
            status = getattr(rec, "status", "")
            status_val = status.value if hasattr(status, "value") else str(status)
            if action_type not in by_action:
                by_action[action_type] = {}
            if status_val not in by_action[action_type]:
                by_action[action_type][status_val] = []
            by_action[action_type][status_val].append(rec)

        now = time.time()
        for action_type, status_groups in by_action.items():
            for status_val, recs in status_groups.items():
                if len(recs) < _MIN_OCCURRENCES:
                    continue

                evidence = [f"action_type:{action_type}", f"status:{status_val}", f"count:{len(recs)}"]
                timestamps = [getattr(r, "timestamp", 0.0) for r in recs]

                if status_val == "success":
                    ptype = PatternType.RECURRING_SUCCESS.value
                    title = f"Recurring success: {action_type}"
                    rec_text = f"Action '{action_type}' succeeds consistently ({len(recs)} times)"
                    recommendation = f"Consider promoting '{action_type}' to institutional capability"
                elif status_val in ("failure", "timeout"):
                    ptype = PatternType.RECURRING_FAILURE.value
                    title = f"Recurring failure: {action_type}"
                    rec_text = f"Action '{action_type}' fails repeatedly ({len(recs)} times)"
                    recommendation = f"Investigate root cause of '{action_type}' failures; consider alternative approach"
                else:
                    continue

                confidence = min(0.4 + (len(recs) * 0.1), 0.95)
                confidence_reason = f"{len(recs)} occurrences in {window_days:.0f}d window"

                pattern = DetectedPattern(
                    pattern_id=f"pat-{uuid.uuid4().hex[:12]}",
                    pattern_type=ptype,
                    title=title,
                    description=rec_text,
                    evidence=evidence,
                    occurrences=len(recs),
                    first_seen=min(timestamps) if timestamps else now,
                    last_seen=max(timestamps) if timestamps else now,
                    confidence=confidence,
                    confidence_reason=confidence_reason,
                    recommendation=recommendation,
                )
                results.append(self._store_pattern(pattern))

    def _detect_decision_correlations(self, results: list[DetectedPattern]) -> None:
        """Correlate decision validity with outcome patterns."""
        dv = self.decision_validity
        if dv is None:
            return

        try:
            at_risk = dv.at_risk()
            invalid = dv.invalid()
        except Exception:
            return

        # At-risk decisions with goal connections form correlation patterns
        for drec in at_risk + invalid:
            did = getattr(drec, "decision_id", "")
            dtitle = getattr(drec, "decision_title", did)
            validity = getattr(drec, "validity", "")
            validity_val = validity.value if hasattr(validity, "value") else str(validity)
            risk_factors = getattr(drec, "risk_factors", [])

            evidence = [f"decision:{did}", f"validity:{validity_val}"]
            for rf in risk_factors[:3]:
                evidence.append(f"risk:{str(rf)[:80]}")

            # Trace lineage for affected goals
            affected_goals: list[str] = []
            affected_decisions: list[str] = [did]
            dl = self.decision_lineage
            if dl is not None:
                try:
                    lineage = dl.trace(did)
                    for node in getattr(lineage, "downstream", []):
                        etype = getattr(node, "entity_type", "")
                        eid = getattr(node, "entity_id", "")
                        if etype == "goal" and eid not in affected_goals:
                            affected_goals.append(eid)
                        elif etype == "decision" and eid not in affected_decisions:
                            affected_decisions.append(eid)
                except Exception:
                    pass

            pattern = DetectedPattern(
                pattern_id=f"pat-{uuid.uuid4().hex[:12]}",
                pattern_type=PatternType.DECISION_CORRELATION.value,
                title=f"Decision at risk: {dtitle[:60]}",
                description=f"Decision '{dtitle}' is {validity_val} with {len(risk_factors)} risk factor(s)",
                evidence=evidence,
                occurrences=len(risk_factors),
                first_seen=time.time(),
                last_seen=time.time(),
                confidence=0.7 if validity_val == "invalid" else 0.5,
                confidence_reason=f"decision validity engine classified as {validity_val}",
                affected_goals=affected_goals,
                affected_decisions=affected_decisions,
                recommendation=getattr(drec, "recommendation", "review decision"),
            )
            results.append(self._store_pattern(pattern))

    def _detect_capability_bottlenecks(self, results: list[DetectedPattern]) -> None:
        """Detect capabilities that are bottlenecking execution."""
        le = self.learning_extraction
        if le is None:
            return

        try:
            gap_lessons = le.lessons_by_category("capability_gap")
        except Exception:
            return

        # Group gap lessons by capability
        by_cap: dict[str, list[Any]] = {}
        for lesson in gap_lessons:
            for cid in getattr(lesson, "related_capability_ids", []):
                if cid not in by_cap:
                    by_cap[cid] = []
                by_cap[cid].append(lesson)

        for cap_id, lessons in by_cap.items():
            if len(lessons) < 2:
                continue

            evidence = [f"capability:{cap_id}", f"gap_lessons:{len(lessons)}"]
            for l in lessons[:3]:
                evidence.append(f"lesson:{getattr(l, 'lesson_id', '')}")

            pattern = DetectedPattern(
                pattern_id=f"pat-{uuid.uuid4().hex[:12]}",
                pattern_type=PatternType.CAPABILITY_BOTTLENECK.value,
                title=f"Capability bottleneck: {cap_id}",
                description=f"Capability '{cap_id}' appears in {len(lessons)} gap lessons",
                evidence=evidence,
                occurrences=len(lessons),
                first_seen=min(getattr(l, "extracted_at", 0.0) for l in lessons),
                last_seen=max(getattr(l, "extracted_at", 0.0) for l in lessons),
                confidence=min(0.5 + (len(lessons) * 0.15), 0.9),
                confidence_reason=f"{len(lessons)} independent gap lessons reference this capability",
                affected_capabilities=[cap_id],
                recommendation=f"Prioritize building or strengthening '{cap_id}' capability",
            )
            results.append(self._store_pattern(pattern))

    def _detect_assumption_chain_failures(self, results: list[DetectedPattern]) -> None:
        """Detect when invalidated assumptions cascade through decisions."""
        le = self.learning_extraction
        if le is None:
            return

        try:
            inv_lessons = le.lessons_by_category("assumption_invalidation")
        except Exception:
            return

        # Group by decision
        by_decision: dict[str, list[Any]] = {}
        for lesson in inv_lessons:
            for did in getattr(lesson, "related_decision_ids", []):
                if did not in by_decision:
                    by_decision[did] = []
                by_decision[did].append(lesson)

        for did, lessons in by_decision.items():
            if len(lessons) < 2:
                continue

            evidence = [f"decision:{did}", f"invalidated_assumptions:{len(lessons)}"]
            assumption_ids: list[str] = []
            for l in lessons:
                for aid in getattr(l, "related_assumption_ids", []):
                    if aid not in assumption_ids:
                        assumption_ids.append(aid)

            for aid in assumption_ids[:5]:
                evidence.append(f"assumption:{aid}")

            # Check blast radius
            affected_goals: list[str] = []
            di = self.decision_impact
            if di is not None:
                try:
                    impact = di.assess(did)
                    for gid in getattr(impact, "affected_goal_ids", []):
                        if gid not in affected_goals:
                            affected_goals.append(gid)
                except Exception:
                    pass

            pattern = DetectedPattern(
                pattern_id=f"pat-{uuid.uuid4().hex[:12]}",
                pattern_type=PatternType.ASSUMPTION_CHAIN_FAILURE.value,
                title=f"Assumption chain failure for decision {did[:20]}",
                description=f"{len(lessons)} assumptions invalidated for decision '{did}', potentially cascading to {len(affected_goals)} goal(s)",
                evidence=evidence,
                occurrences=len(lessons),
                first_seen=min(getattr(l, "extracted_at", 0.0) for l in lessons),
                last_seen=max(getattr(l, "extracted_at", 0.0) for l in lessons),
                confidence=min(0.6 + (len(lessons) * 0.1), 0.95),
                confidence_reason=f"{len(lessons)} invalidated assumptions + blast radius analysis",
                affected_goals=affected_goals,
                affected_decisions=[did],
                recommendation=f"Review decision '{did}' and all dependent work; assumptions may be fundamentally flawed",
            )
            results.append(self._store_pattern(pattern))

    def _detect_velocity_trends(self, results: list[DetectedPattern]) -> None:
        """Detect trends in compounding pipeline velocity."""
        ce = self.compounding_engine
        if ce is None:
            return

        try:
            report = ce.compounding_report(days=30)
        except Exception:
            return

        promoted = report.get("promoted_count", 0)
        pending = report.get("pending_count", 0)
        rejected = report.get("rejected_count", 0)
        total = promoted + pending + rejected

        if total < _MIN_OCCURRENCES:
            return

        promotion_rate = promoted / total if total > 0 else 0.0
        evidence = [
            f"promoted:{promoted}",
            f"pending:{pending}",
            f"rejected:{rejected}",
            f"promotion_rate:{promotion_rate:.2f}",
        ]

        if promotion_rate > 0.6:
            title = "Strong compounding velocity"
            desc = f"Promotion rate {promotion_rate:.0%} — learning is converting to capability"
            recommendation = "Maintain current approach; high conversion indicates effective learning"
        elif promotion_rate < 0.2:
            title = "Weak compounding velocity"
            desc = f"Promotion rate {promotion_rate:.0%} — learning is not converting to capability"
            recommendation = "Review rejected candidates; promotion criteria may be too strict or learning quality too low"
        else:
            return

        pattern = DetectedPattern(
            pattern_id=f"pat-{uuid.uuid4().hex[:12]}",
            pattern_type=PatternType.VELOCITY_TREND.value,
            title=title,
            description=desc,
            evidence=evidence,
            occurrences=total,
            first_seen=time.time() - (30 * 86400),
            last_seen=time.time(),
            confidence=min(0.5 + (total * 0.05), 0.85),
            confidence_reason=f"{total} promotion candidates evaluated over 30d",
            recommendation=recommendation,
        )
        results.append(self._store_pattern(pattern))

    # ── Attribution ──────────────────────────────────────────────────────

    def attribute_outcome(self, outcome_id: str) -> list[AttributionLink]:
        """Trace an outcome backward to identify contributing causes."""
        links: list[AttributionLink] = []

        # Direct outcome → decision links via decision lineage
        dl = self.decision_lineage
        if dl is not None:
            try:
                # Search recent decisions for any that reference this outcome's work
                le = self.learning_extraction
                if le is not None:
                    for lesson in le.recent_lessons(limit=50):
                        if outcome_id not in getattr(lesson, "related_outcome_ids", []):
                            continue
                        for did in getattr(lesson, "related_decision_ids", []):
                            lineage = dl.trace(did)
                            depth = getattr(lineage, "chain_depth", 1)
                            strength = max(0.1, 1.0 * (_PROXIMITY_DECAY ** (depth - 1)))
                            links.append(AttributionLink(
                                source_type="decision",
                                source_id=did,
                                target_type="outcome",
                                target_id=outcome_id,
                                strength=strength,
                                evidence=f"lineage depth {depth} from decision to outcome",
                            ))
            except Exception:
                logger.debug("Failed to attribute via decision lineage")

        # Outcome → capability links via reliability
        ol = self.outcome_learning
        if ol is not None:
            try:
                for rec in ol.recent_outcomes(limit=50):
                    rec_id = getattr(rec, "plan_id", "") or getattr(rec, "step_id", "")
                    if rec_id != outcome_id:
                        continue
                    action_type = getattr(rec, "action_type", "")
                    reliability = ol.get_reliability(action_type)
                    links.append(AttributionLink(
                        source_type="capability",
                        source_id=action_type,
                        target_type="outcome",
                        target_id=outcome_id,
                        strength=reliability,
                        evidence=f"action_type reliability {reliability:.2f}",
                    ))
                    break
            except Exception:
                logger.debug("Failed to attribute via outcome learning")

        return sorted(links, key=lambda l: l.strength, reverse=True)

    def correlations(self, min_strength: float = 0.5) -> list[AttributionLink]:
        """Return all attribution links above a strength threshold."""
        all_links: list[AttributionLink] = []

        # Build links from all patterns
        for pattern in self._patterns:
            for did in pattern.affected_decisions:
                for gid in pattern.affected_goals:
                    all_links.append(AttributionLink(
                        source_type="decision",
                        source_id=did,
                        target_type="goal",
                        target_id=gid,
                        strength=pattern.confidence,
                        evidence=f"via pattern {pattern.pattern_id}",
                    ))
            for cid in pattern.affected_capabilities:
                for gid in pattern.affected_goals:
                    all_links.append(AttributionLink(
                        source_type="capability",
                        source_id=cid,
                        target_type="goal",
                        target_id=gid,
                        strength=pattern.confidence * 0.8,
                        evidence=f"via pattern {pattern.pattern_id}",
                    ))

        return [l for l in all_links if l.strength >= min_strength]

    # ── Public query API ─────────────────────────────────────────────────

    def patterns_for_goal(self, goal_id: str) -> list[DetectedPattern]:
        """Return patterns that affect a specific goal."""
        direct = [p for p in self._patterns if goal_id in p.affected_goals]

        # Also check descendant goals
        gh = self.goal_hierarchy
        if gh is not None:
            try:
                descendants = gh.descendants(goal_id)
                desc_ids = {getattr(g, "goal_id", "") for g in descendants}
                for p in self._patterns:
                    if p not in direct and any(gid in desc_ids for gid in p.affected_goals):
                        direct.append(p)
            except Exception:
                pass

        return direct

    def patterns_for_capability(self, capability_id: str) -> list[DetectedPattern]:
        """Return patterns that affect a specific capability."""
        return [p for p in self._patterns if capability_id in p.affected_capabilities]

    def patterns_by_type(self, pattern_type: str) -> list[DetectedPattern]:
        """Return patterns of a specific type."""
        pt_val = pattern_type.value if hasattr(pattern_type, "value") else str(pattern_type)
        return [p for p in self._patterns if p.pattern_type == pt_val]

    def top_patterns(self, limit: int = 10) -> list[DetectedPattern]:
        """Return highest-confidence patterns."""
        return sorted(self._patterns, key=lambda p: p.confidence, reverse=True)[:limit]

    def snapshot(self) -> PatternSnapshot:
        """Full pattern snapshot."""
        now = time.time()
        by_type: dict[str, int] = {}
        recent_7d = 0

        for p in self._patterns:
            by_type[p.pattern_type] = by_type.get(p.pattern_type, 0) + 1
            if (now - p.last_seen) < 7 * 86400:
                recent_7d += 1

        velocity = recent_7d / 7.0 if recent_7d > 0 else 0.0
        top = self.top_patterns(limit=5)
        all_corr = self.correlations(min_strength=0.6)

        return PatternSnapshot(
            total_patterns=len(self._patterns),
            by_type=by_type,
            top_patterns=[p.to_dict() for p in top],
            attribution_links=[l.to_dict() for l in all_corr[:10]],
            top_correlations=[l.to_dict() for l in all_corr[:5]],
            pattern_velocity=velocity,
            generated_at=now,
        )

    def summary(self) -> dict[str, Any]:
        """Compact summary for API consumption."""
        snap = self.snapshot()
        return snap.to_dict()

    def health(self) -> str:
        """Quick health classification."""
        snap = self.snapshot()
        if snap.total_patterns == 0:
            return "unknown"
        failure_count = snap.by_type.get(PatternType.RECURRING_FAILURE.value, 0)
        success_count = snap.by_type.get(PatternType.RECURRING_SUCCESS.value, 0)
        if failure_count > success_count * 2:
            return "critical"
        if snap.pattern_velocity >= 0.5:
            return "active"
        if snap.total_patterns > 0 and snap.pattern_velocity > 0:
            return "learning"
        return "dormant"
