"""
Learning Extraction Runtime — Campaign 12.0

Extracts reusable semantic lessons from completed work, decisions,
and outcomes by cross-referencing multiple subsystems.

Operator questions answered:
  - What did we learn from this outcome?
  - What assumptions were invalidated and what does that mean?
  - Which decisions produced consequences we should remember?
  - What capability gaps keep recurring?
  - What lessons are actionable right now?

Composes:
  - OutcomeLearningLoop (mechanical outcome→reliability authority)
  - DecisionRegistry (strategic decision authority)
  - AssumptionTrackingRuntime (assumption lifecycle authority)
  - OutcomeTrackingRuntime (goal outcome authority)
  - StrategicMemoryEngine (strategic memory authority)

This runtime is the SEMANTIC learning layer. It sits above
OutcomeLearningLoop which handles mechanical reliability tracking.
It never mutates any source subsystem.
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
_DEFAULT_STORE = os.path.join(_REPO_ROOT, "data", "umh", "learning", "lessons.jsonl")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class LessonCategory(str, Enum):
    """Classification of what kind of learning a lesson represents."""
    SUCCESS_PATTERN = "success_pattern"
    FAILURE_PATTERN = "failure_pattern"
    ASSUMPTION_INVALIDATION = "assumption_invalidation"
    DECISION_CONSEQUENCE = "decision_consequence"
    CAPABILITY_GAP = "capability_gap"
    PROCESS_IMPROVEMENT = "process_improvement"


@dataclass
class ExtractedLesson:
    """A single reusable lesson extracted from cross-subsystem evidence."""
    lesson_id: str = ""
    category: str = LessonCategory.PROCESS_IMPROVEMENT.value
    title: str = ""
    description: str = ""
    evidence_sources: list[str] = field(default_factory=list)
    confidence: float = 0.0
    confidence_reason: str = ""
    source_count: int = 0
    related_decision_ids: list[str] = field(default_factory=list)
    related_goal_ids: list[str] = field(default_factory=list)
    related_capability_ids: list[str] = field(default_factory=list)
    related_assumption_ids: list[str] = field(default_factory=list)
    related_outcome_ids: list[str] = field(default_factory=list)
    extracted_at: float = 0.0
    actionable: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["confidence"] = round(self.confidence, 4)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExtractedLesson:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


@dataclass
class LessonExtractionSnapshot:
    """Aggregate view of all extracted lessons."""
    total_lessons: int = 0
    actionable_count: int = 0
    category_distribution: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    extraction_velocity: float = 0.0
    staleness_score: float = 0.0
    top_lessons: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["avg_confidence"] = round(self.avg_confidence, 4)
        d["extraction_velocity"] = round(self.extraction_velocity, 4)
        d["staleness_score"] = round(self.staleness_score, 4)
        return d


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Runtime
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class LearningExtractionRuntime:
    """Extracts semantic lessons from cross-subsystem evidence.

    OutcomeLearningLoop handles mechanical outcome→reliability.
    This runtime handles outcome→meaning→lesson→recommendation.
    """

    def __init__(
        self,
        outcome_learning: Any | None = None,
        decision_registry: Any | None = None,
        assumption_tracking: Any | None = None,
        outcome_tracking: Any | None = None,
        strategic_memory: Any | None = None,
        store_path: str = "",
    ) -> None:
        self._outcome_learning = outcome_learning
        self._decision_registry = decision_registry
        self._assumption_tracking = assumption_tracking
        self._outcome_tracking = outcome_tracking
        self._strategic_memory = strategic_memory
        self._store_path = store_path or _DEFAULT_STORE
        self._lessons: list[ExtractedLesson] = []
        self._evidence_hashes: set[str] = set()
        self._load()

    # ── Lazy subsystem access ────────────────────────────────────────────

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
    def decision_registry(self) -> Any | None:
        if self._decision_registry is None:
            try:
                from substrate.organism.decision_registry import DecisionRegistry
                self._decision_registry = DecisionRegistry()
            except Exception:
                logger.debug("DecisionRegistry unavailable")
        return self._decision_registry

    @property
    def assumption_tracking(self) -> Any | None:
        if self._assumption_tracking is None:
            try:
                from substrate.organism.assumption_tracking_runtime import AssumptionTrackingRuntime
                self._assumption_tracking = AssumptionTrackingRuntime()
            except Exception:
                logger.debug("AssumptionTrackingRuntime unavailable")
        return self._assumption_tracking

    @property
    def outcome_tracking(self) -> Any | None:
        if self._outcome_tracking is None:
            try:
                from substrate.organism.outcome_tracking_runtime import OutcomeTrackingRuntime
                self._outcome_tracking = OutcomeTrackingRuntime()
            except Exception:
                logger.debug("OutcomeTrackingRuntime unavailable")
        return self._outcome_tracking

    @property
    def strategic_memory(self) -> Any | None:
        if self._strategic_memory is None:
            try:
                from substrate.organism.strategic_memory_engine import StrategicMemoryEngine
                self._strategic_memory = StrategicMemoryEngine()
            except Exception:
                logger.debug("StrategicMemoryEngine unavailable")
        return self._strategic_memory

    # ── Persistence ──────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load existing lessons from JSONL store."""
        if not os.path.isfile(self._store_path):
            return
        try:
            with open(self._store_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    lesson = ExtractedLesson.from_dict(d)
                    self._lessons.append(lesson)
                    h = self._evidence_hash(lesson.evidence_sources)
                    self._evidence_hashes.add(h)
        except Exception:
            logger.debug("Failed to load lessons from %s", self._store_path)

    def _append(self, lesson: ExtractedLesson) -> None:
        """Append a lesson to the JSONL store."""
        try:
            os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
            with open(self._store_path, "a") as f:
                f.write(json.dumps(lesson.to_dict()) + "\n")
        except Exception:
            logger.debug("Failed to append lesson to %s", self._store_path)

    @staticmethod
    def _evidence_hash(sources: list[str]) -> str:
        """Fingerprint for deduplication."""
        combined = "|".join(sorted(sources))
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _is_duplicate(self, sources: list[str]) -> bool:
        return self._evidence_hash(sources) in self._evidence_hashes

    def _store_lesson(self, lesson: ExtractedLesson) -> ExtractedLesson:
        """Store a lesson if not duplicate, return it either way."""
        h = self._evidence_hash(lesson.evidence_sources)
        if h in self._evidence_hashes:
            for existing in self._lessons:
                if self._evidence_hash(existing.evidence_sources) == h:
                    return existing
            return lesson
        self._evidence_hashes.add(h)
        self._lessons.append(lesson)
        self._append(lesson)
        return lesson

    # ── Extraction logic ─────────────────────────────────────────────────

    def extract_from_outcome(self, outcome_id: str) -> ExtractedLesson | None:
        """Extract a lesson from a specific outcome record."""
        ol = self.outcome_learning
        if ol is None:
            return None

        target = None
        try:
            for rec in ol.recent_outcomes(limit=100):
                if getattr(rec, "plan_id", "") == outcome_id or \
                   getattr(rec, "step_id", "") == outcome_id:
                    target = rec
                    break
        except Exception:
            logger.debug("Failed to search outcomes for %s", outcome_id)
            return None

        if target is None:
            return None

        status = getattr(target, "status", "")
        status_val = status.value if hasattr(status, "value") else str(status)
        action_type = getattr(target, "action_type", "unknown")
        evidence = [f"outcome:{outcome_id}", f"action_type:{action_type}", f"status:{status_val}"]

        if self._is_duplicate(evidence):
            return None

        # Determine category
        if status_val in ("success",):
            category = LessonCategory.SUCCESS_PATTERN.value
            title = f"Successful {action_type} execution"
            description = f"Action type '{action_type}' completed successfully"
            confidence = 0.6
            confidence_reason = "single successful outcome observation"
        elif status_val in ("failure", "timeout"):
            category = LessonCategory.FAILURE_PATTERN.value
            title = f"Failed {action_type} execution"
            description = f"Action type '{action_type}' failed with status {status_val}"
            error = getattr(target, "error", "")
            if error:
                description += f": {str(error)[:200]}"
                evidence.append(f"error:{str(error)[:100]}")
            confidence = 0.5
            confidence_reason = "single failure observation; confidence increases with recurrence"
        else:
            category = LessonCategory.PROCESS_IMPROVEMENT.value
            title = f"Partial {action_type} execution"
            description = f"Action type '{action_type}' completed with status {status_val}"
            confidence = 0.3
            confidence_reason = "partial outcome provides weak signal"

        # Enrich with reliability data
        try:
            reliability = ol.get_reliability(action_type)
            if reliability < 0.3:
                confidence = min(confidence + 0.2, 1.0)
                confidence_reason += f"; reliability {reliability:.2f} confirms pattern"
                evidence.append(f"reliability:{reliability:.2f}")
        except Exception:
            pass

        # Cross-reference with decisions
        decision_ids: list[str] = []
        goal_ids: list[str] = []
        assumption_ids: list[str] = []
        self._enrich_from_decisions(evidence, decision_ids, goal_ids, assumption_ids)

        lesson = ExtractedLesson(
            lesson_id=f"lesson-{uuid.uuid4().hex[:12]}",
            category=category,
            title=title,
            description=description,
            evidence_sources=evidence,
            confidence=confidence,
            confidence_reason=confidence_reason,
            source_count=len(evidence),
            related_decision_ids=decision_ids,
            related_goal_ids=goal_ids,
            related_assumption_ids=assumption_ids,
            related_outcome_ids=[outcome_id],
            extracted_at=time.time(),
            actionable=confidence >= 0.5,
        )
        return self._store_lesson(lesson)

    def extract_from_decision(self, decision_id: str) -> list[ExtractedLesson]:
        """Extract lessons from a decision and its consequences."""
        dr = self.decision_registry
        if dr is None:
            return []

        try:
            decision = dr.get(decision_id)
        except Exception:
            logger.debug("Failed to get decision %s", decision_id)
            return []

        if decision is None:
            return []

        lessons: list[ExtractedLesson] = []
        status = getattr(decision, "status", None)
        status_val = status.value if hasattr(status, "value") else str(status)
        title_text = getattr(decision, "title", decision_id)

        # Lesson from decision status
        evidence = [f"decision:{decision_id}", f"decision_status:{status_val}"]

        if status_val == "invalidated":
            # Check which assumptions were invalidated
            inv_assumptions = self._assumptions_for_decision(decision_id)
            assumption_ids = [getattr(a, "assumption_id", "") for a in inv_assumptions]
            for aid in assumption_ids:
                evidence.append(f"invalidated_assumption:{aid}")

            if not self._is_duplicate(evidence):
                lesson = ExtractedLesson(
                    lesson_id=f"lesson-{uuid.uuid4().hex[:12]}",
                    category=LessonCategory.ASSUMPTION_INVALIDATION.value,
                    title=f"Decision '{title_text}' invalidated",
                    description=f"Decision invalidated with {len(inv_assumptions)} assumption(s) affected",
                    evidence_sources=evidence,
                    confidence=0.8,
                    confidence_reason=f"decision explicitly invalidated; {len(inv_assumptions)} assumptions provide corroboration",
                    source_count=len(evidence),
                    related_decision_ids=[decision_id],
                    related_goal_ids=list(getattr(decision, "goal_refs", [])),
                    related_assumption_ids=assumption_ids,
                    extracted_at=time.time(),
                    actionable=True,
                )
                lessons.append(self._store_lesson(lesson))

        elif status_val == "superseded":
            superseded_by = getattr(decision, "superseded_by", "")
            evidence.append(f"superseded_by:{superseded_by}")
            if not self._is_duplicate(evidence):
                lesson = ExtractedLesson(
                    lesson_id=f"lesson-{uuid.uuid4().hex[:12]}",
                    category=LessonCategory.DECISION_CONSEQUENCE.value,
                    title=f"Decision '{title_text}' superseded",
                    description=f"Original decision was replaced, indicating initial approach was suboptimal",
                    evidence_sources=evidence,
                    confidence=0.6,
                    confidence_reason="supersession implies original decision had limitations",
                    source_count=len(evidence),
                    related_decision_ids=[decision_id, superseded_by] if superseded_by else [decision_id],
                    related_goal_ids=list(getattr(decision, "goal_refs", [])),
                    extracted_at=time.time(),
                    actionable=False,
                )
                lessons.append(self._store_lesson(lesson))

        return lessons

    def extract_batch(self, since_ts: float = 0.0) -> list[ExtractedLesson]:
        """Extract lessons from all recent outcomes and decisions."""
        new_lessons: list[ExtractedLesson] = []

        # Extract from recent outcomes
        self._extract_from_outcomes(since_ts, new_lessons)

        # Extract from invalidated assumptions
        self._extract_from_assumptions(new_lessons)

        # Extract from decision consequences
        self._extract_from_decision_consequences(new_lessons)

        # Extract from capability gaps
        self._extract_from_capability_gaps(new_lessons)

        # Extract from strategic memory patterns
        self._extract_from_strategic_patterns(new_lessons)

        return new_lessons

    def _extract_from_outcomes(self, since_ts: float, results: list[ExtractedLesson]) -> None:
        """Extract lessons from recent outcome records."""
        ol = self.outcome_learning
        if ol is None:
            return
        try:
            for rec in ol.recent_outcomes(limit=50):
                ts = getattr(rec, "timestamp", 0.0)
                if ts < since_ts:
                    continue
                oid = getattr(rec, "plan_id", "") or getattr(rec, "step_id", "")
                if oid:
                    lesson = self.extract_from_outcome(oid)
                    if lesson is not None:
                        results.append(lesson)
        except Exception:
            logger.debug("Failed to extract from outcomes")

    def _extract_from_assumptions(self, results: list[ExtractedLesson]) -> None:
        """Extract lessons from invalidated assumptions."""
        at = self.assumption_tracking
        if at is None:
            return
        try:
            for assumption in at.invalidated():
                aid = getattr(assumption, "assumption_id", "")
                statement = getattr(assumption, "statement", "")
                evidence_against = getattr(assumption, "evidence_against", "")
                decision_refs = list(getattr(assumption, "decision_refs", []))

                evidence = [f"assumption:{aid}", f"status:invalidated"]
                if evidence_against:
                    evidence.append(f"counter_evidence:{str(evidence_against)[:150]}")

                if self._is_duplicate(evidence):
                    continue

                lesson = ExtractedLesson(
                    lesson_id=f"lesson-{uuid.uuid4().hex[:12]}",
                    category=LessonCategory.ASSUMPTION_INVALIDATION.value,
                    title=f"Assumption invalidated: {statement[:80]}",
                    description=f"Assumption '{statement}' was proven incorrect",
                    evidence_sources=evidence,
                    confidence=0.85,
                    confidence_reason="explicit invalidation with counter-evidence",
                    source_count=len(evidence),
                    related_decision_ids=decision_refs,
                    related_assumption_ids=[aid],
                    extracted_at=time.time(),
                    actionable=True,
                )
                results.append(self._store_lesson(lesson))
        except Exception:
            logger.debug("Failed to extract from assumptions")

    def _extract_from_decision_consequences(self, results: list[ExtractedLesson]) -> None:
        """Extract lessons from decisions with notable status changes."""
        dr = self.decision_registry
        if dr is None:
            return
        try:
            for decision in dr.list_decisions():
                status = getattr(decision, "status", None)
                status_val = status.value if hasattr(status, "value") else str(status)
                if status_val in ("invalidated", "superseded"):
                    did = getattr(decision, "decision_id", "")
                    extracted = self.extract_from_decision(did)
                    results.extend(extracted)
        except Exception:
            logger.debug("Failed to extract from decision consequences")

    def _extract_from_capability_gaps(self, results: list[ExtractedLesson]) -> None:
        """Extract lessons from recurring capability-related failures."""
        ol = self.outcome_learning
        if ol is None:
            return
        try:
            adjustments = ol.get_adjustments()
            for adj in adjustments:
                action_type = getattr(adj, "action_type", "")
                direction = getattr(adj, "direction", "")
                reliability = getattr(adj, "current_reliability", 0.0)

                if direction != "demote" and reliability >= 0.3:
                    continue

                evidence = [f"reliability_demotion:{action_type}", f"reliability:{reliability:.2f}"]
                if self._is_duplicate(evidence):
                    continue

                lesson = ExtractedLesson(
                    lesson_id=f"lesson-{uuid.uuid4().hex[:12]}",
                    category=LessonCategory.CAPABILITY_GAP.value,
                    title=f"Capability gap: {action_type} underperforming",
                    description=f"Action type '{action_type}' has reliability {reliability:.2f}, suggesting a capability gap",
                    evidence_sources=evidence,
                    confidence=0.7,
                    confidence_reason=f"reliability {reliability:.2f} from outcome history; demotion recommended",
                    source_count=len(evidence),
                    related_capability_ids=[action_type],
                    extracted_at=time.time(),
                    actionable=True,
                )
                results.append(self._store_lesson(lesson))
        except Exception:
            logger.debug("Failed to extract from capability gaps")

    def _extract_from_strategic_patterns(self, results: list[ExtractedLesson]) -> None:
        """Extract lessons from strategic memory pattern detection."""
        sm = self.strategic_memory
        if sm is None:
            return
        try:
            patterns = sm.detect_patterns()
            for pattern_str in patterns:
                evidence = [f"strategic_pattern:{pattern_str[:100]}"]
                if self._is_duplicate(evidence):
                    continue

                lesson = ExtractedLesson(
                    lesson_id=f"lesson-{uuid.uuid4().hex[:12]}",
                    category=LessonCategory.PROCESS_IMPROVEMENT.value,
                    title=f"Strategic pattern: {pattern_str[:80]}",
                    description=pattern_str,
                    evidence_sources=evidence,
                    confidence=0.5,
                    confidence_reason="detected by strategic memory engine; single pattern observation",
                    source_count=1,
                    extracted_at=time.time(),
                    actionable=False,
                )
                results.append(self._store_lesson(lesson))
        except Exception:
            logger.debug("Failed to extract from strategic patterns")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _assumptions_for_decision(self, decision_id: str) -> list[Any]:
        at = self.assumption_tracking
        if at is None:
            return []
        try:
            return at.assumptions_for_decision(decision_id)
        except Exception:
            return []

    def _enrich_from_decisions(
        self,
        evidence: list[str],
        decision_ids: list[str],
        goal_ids: list[str],
        assumption_ids: list[str],
    ) -> None:
        """Add decision/goal/assumption context to evidence."""
        dr = self.decision_registry
        if dr is None:
            return
        try:
            for decision in dr.active_decisions()[:20]:
                did = getattr(decision, "decision_id", "")
                decision_ids.append(did)
                for gid in getattr(decision, "goal_refs", []):
                    if gid not in goal_ids:
                        goal_ids.append(gid)
                for assumption in self._assumptions_for_decision(did):
                    aid = getattr(assumption, "assumption_id", "")
                    if aid not in assumption_ids:
                        assumption_ids.append(aid)
        except Exception:
            logger.debug("Failed to enrich from decisions")

    # ── Public API ────────────────────────────────────────────────────────

    def recent_lessons(self, limit: int = 20) -> list[ExtractedLesson]:
        """Return most recent lessons, newest first."""
        sorted_lessons = sorted(self._lessons, key=lambda l: l.extracted_at, reverse=True)
        return sorted_lessons[:limit]

    def lessons_by_category(self, category: str) -> list[ExtractedLesson]:
        """Return lessons of a specific category."""
        cat_val = category.value if hasattr(category, "value") else str(category)
        return [l for l in self._lessons if l.category == cat_val]

    def actionable_lessons(self) -> list[ExtractedLesson]:
        """Return only actionable lessons, sorted by confidence descending."""
        actionable = [l for l in self._lessons if l.actionable]
        return sorted(actionable, key=lambda l: l.confidence, reverse=True)

    def provenance(self, lesson_id: str) -> dict[str, Any]:
        """Full provenance trace for a lesson — every source that produced it."""
        lesson = None
        for l in self._lessons:
            if l.lesson_id == lesson_id:
                lesson = l
                break
        if lesson is None:
            return {"error": "lesson not found", "lesson_id": lesson_id}

        return {
            "lesson_id": lesson.lesson_id,
            "title": lesson.title,
            "category": lesson.category,
            "confidence": round(lesson.confidence, 4),
            "confidence_reason": lesson.confidence_reason,
            "source_count": lesson.source_count,
            "evidence_sources": lesson.evidence_sources,
            "related_decisions": lesson.related_decision_ids,
            "related_goals": lesson.related_goal_ids,
            "related_assumptions": lesson.related_assumption_ids,
            "related_capabilities": lesson.related_capability_ids,
            "related_outcomes": lesson.related_outcome_ids,
            "extracted_at": lesson.extracted_at,
        }

    def snapshot(self) -> LessonExtractionSnapshot:
        """Full extraction snapshot."""
        now = time.time()
        cat_dist: dict[str, int] = {}
        confidences: list[float] = []
        actionable_count = 0
        recent_7d = 0
        stale_7d = 0

        for l in self._lessons:
            cat_dist[l.category] = cat_dist.get(l.category, 0) + 1
            confidences.append(l.confidence)
            if l.actionable:
                actionable_count += 1
            age = now - l.extracted_at
            if age < 7 * 86400:
                recent_7d += 1
            else:
                stale_7d += 1

        total = len(self._lessons)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        velocity = recent_7d / 7.0 if recent_7d > 0 else 0.0
        staleness = stale_7d / total if total > 0 else 0.0

        top = sorted(self._lessons, key=lambda l: l.confidence, reverse=True)[:5]

        return LessonExtractionSnapshot(
            total_lessons=total,
            actionable_count=actionable_count,
            category_distribution=cat_dist,
            avg_confidence=avg_conf,
            extraction_velocity=velocity,
            staleness_score=staleness,
            top_lessons=[l.to_dict() for l in top],
            generated_at=now,
        )

    def summary(self) -> dict[str, Any]:
        """Compact summary for API consumption."""
        snap = self.snapshot()
        return snap.to_dict()

    def health(self) -> str:
        """Quick health classification."""
        snap = self.snapshot()
        if snap.total_lessons == 0:
            return "unknown"
        if snap.extraction_velocity >= 1.0 and snap.actionable_count > 0:
            return "active"
        if snap.extraction_velocity > 0:
            return "learning"
        if snap.staleness_score > 0.8:
            return "stale"
        return "dormant"
