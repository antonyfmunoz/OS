"""C15.2 — Institutional Memory Runtime.

Governed organizational memory — determines what becomes institutional
truth vs local observation. Manages the knowledge promotion lifecycle:
PROPOSED → VALIDATED → CANONICAL → SUPERSEDED → RETIRED.

This is NOT memory storage (that already exists in StrategicMemoryEngine).
This layer governs what knowledge gets promoted, validated, and retired.

No execution authority. No mutation authority. No direct mutation of
goals, work, decisions, memory, capabilities, allocations, or approvals.
"""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────


class KnowledgeState(str, Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    CANONICAL = "canonical"
    SUPERSEDED = "superseded"
    RETIRED = "retired"


class InstitutionalMemoryHealth(str, Enum):
    THRIVING = "thriving"
    GROWING = "growing"
    STAGNANT = "stagnant"
    DECAYING = "decaying"
    CRITICAL = "critical"


class MemoryDriftType(str, Enum):
    STALE_CANONICAL = "stale_canonical"
    CONTRADICTED_MEMORY = "contradicted_memory"
    UNVALIDATED_BACKLOG = "unvalidated_backlog"
    LESSON_LOSS = "lesson_loss"


@dataclass
class InstitutionalKnowledge:
    knowledge_id: str = ""
    content: str = ""
    source_type: str = ""
    source_id: str = ""
    state: str = KnowledgeState.PROPOSED.value
    confidence: float = 0.5
    validations: int = 0
    promoted_at: float = 0.0
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InstitutionalMemoryDriftWarning:
    drift_type: str = MemoryDriftType.STALE_CANONICAL.value
    severity: str = "low"
    description: str = ""
    affected_ids: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InstitutionalMemorySnapshot:
    memory_health: str = InstitutionalMemoryHealth.GROWING.value
    knowledge_by_state: dict[str, int] = field(default_factory=dict)
    total_knowledge: int = 0
    canonical_count: int = 0
    validation_rate: float = 0.0
    drift_warnings: list[dict[str, Any]] = field(default_factory=list)
    recent_promotions: list[dict[str, Any]] = field(default_factory=list)
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Helpers ──────────────────────────────────────────────────────────


def _knowledge_id(source_type: str, source_id: str) -> str:
    raw = f"{source_type}:{source_id}:{time.time()}"
    return f"know-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


_STALE_THRESHOLD_SECONDS = 30 * 24 * 3600  # 30 days


# ── Runtime ──────────────────────────────────────────────────────────


class InstitutionalMemoryRuntime:
    """Governed organizational memory with knowledge promotion lifecycle.

    Composes StrategicMemoryEngine, DecisionRegistry, OutcomeLearningLoop,
    and LearningPortfolioRuntime to surface, validate, and promote
    institutional knowledge.
    """

    def __init__(
        self,
        governance_runtime: Any | None = None,
        strategic_memory: Any | None = None,
        decision_registry: Any | None = None,
        outcome_learning: Any | None = None,
        learning_portfolio: Any | None = None,
    ) -> None:
        self._governance_runtime = governance_runtime
        self._strategic_memory = strategic_memory
        self._decision_registry = decision_registry
        self._outcome_learning = outcome_learning
        self._learning_portfolio = learning_portfolio
        self._knowledge: list[InstitutionalKnowledge] = []
        self._synthesized = False

    # ── Lazy Properties ──────────────────────────────────────────────

    @property
    def _governance(self) -> Any:
        if self._governance_runtime is None:
            try:
                from substrate.organism.governance_runtime import GovernanceRuntime

                self._governance_runtime = GovernanceRuntime()
            except Exception:
                logger.debug("Failed to init GovernanceRuntime", exc_info=True)
        return self._governance_runtime

    @property
    def _memory(self) -> Any:
        if self._strategic_memory is None:
            try:
                from substrate.organism.strategic_memory_engine import (
                    StrategicMemoryEngine,
                )

                self._strategic_memory = StrategicMemoryEngine()
            except Exception:
                logger.debug("Failed to init StrategicMemoryEngine", exc_info=True)
        return self._strategic_memory

    @property
    def _decisions(self) -> Any:
        if self._decision_registry is None:
            try:
                from substrate.organism.decision_registry import DecisionRegistry

                self._decision_registry = DecisionRegistry()
            except Exception:
                logger.debug("Failed to init DecisionRegistry", exc_info=True)
        return self._decision_registry

    @property
    def _outcomes(self) -> Any:
        if self._outcome_learning is None:
            try:
                from substrate.organism.outcome_learning import OutcomeLearningLoop

                self._outcome_learning = OutcomeLearningLoop()
            except Exception:
                logger.debug("Failed to init OutcomeLearningLoop", exc_info=True)
        return self._outcome_learning

    @property
    def _learning(self) -> Any:
        if self._learning_portfolio is None:
            try:
                from substrate.organism.learning_portfolio_runtime import (
                    LearningPortfolioRuntime,
                )

                self._learning_portfolio = LearningPortfolioRuntime()
            except Exception:
                logger.debug("Failed to init LearningPortfolioRuntime", exc_info=True)
        return self._learning_portfolio

    # ── Synthesis ────────────────────────────────────────────────────

    def _ensure_synthesized(self) -> None:
        """Populate knowledge store from composition targets on first access."""
        if self._synthesized:
            return
        self._synthesized = True
        self._synthesize_from_memory()
        self._synthesize_from_decisions()
        self._synthesize_from_outcomes()
        self._synthesize_from_learning()

    def _synthesize_from_memory(self) -> None:
        """Strategic memories become CANONICAL knowledge."""
        try:
            mem = self._memory
            if mem is None:
                return
            current = mem.get_current() if hasattr(mem, "get_current") else None
            if current is None:
                return
            patterns = mem.detect_patterns() if hasattr(mem, "detect_patterns") else []
            for i, pattern in enumerate(patterns):
                if isinstance(pattern, str) and pattern:
                    self._knowledge.append(InstitutionalKnowledge(
                        knowledge_id=_knowledge_id("memory", f"pattern-{i}"),
                        content=pattern,
                        source_type="memory",
                        source_id=f"pattern-{i}",
                        state=KnowledgeState.CANONICAL.value,
                        confidence=0.8,
                        validations=3,
                        promoted_at=time.time(),
                        created_at=time.time(),
                    ))
        except Exception:
            logger.debug("Error synthesizing from memory", exc_info=True)

    def _synthesize_from_decisions(self) -> None:
        """Active decisions become VALIDATED knowledge."""
        try:
            decisions = self._decisions
            if decisions is None:
                return
            active = decisions.active_decisions() if hasattr(decisions, "active_decisions") else []
            for d in active:
                did = ""
                desc = ""
                if hasattr(d, "decision_id"):
                    did = d.decision_id
                    desc = getattr(d, "description", "") or getattr(d, "rationale", "")
                elif isinstance(d, dict):
                    did = d.get("decision_id", d.get("id", ""))
                    desc = d.get("description", d.get("rationale", ""))
                if did and desc:
                    self._knowledge.append(InstitutionalKnowledge(
                        knowledge_id=_knowledge_id("decision", did),
                        content=desc,
                        source_type="decision",
                        source_id=did,
                        state=KnowledgeState.VALIDATED.value,
                        confidence=0.7,
                        validations=2,
                        created_at=time.time(),
                    ))
        except Exception:
            logger.debug("Error synthesizing from decisions", exc_info=True)

    def _synthesize_from_outcomes(self) -> None:
        """Reliable outcomes become VALIDATED knowledge."""
        try:
            outcomes = self._outcomes
            if outcomes is None:
                return
            recent = outcomes.recent_outcomes(limit=20) if hasattr(outcomes, "recent_outcomes") else []
            for o in recent:
                action_type = ""
                if hasattr(o, "action_type"):
                    action_type = o.action_type
                elif isinstance(o, dict):
                    action_type = o.get("action_type", "")
                if not action_type:
                    continue
                reliability = outcomes.get_reliability(action_type) if hasattr(outcomes, "get_reliability") else 0.0
                if reliability > 0.7:
                    oid = getattr(o, "outcome_id", "") or (o.get("outcome_id", "") if isinstance(o, dict) else "")
                    desc = getattr(o, "description", "") or (o.get("description", "") if isinstance(o, dict) else "")
                    if oid:
                        self._knowledge.append(InstitutionalKnowledge(
                            knowledge_id=_knowledge_id("outcome", oid),
                            content=desc or f"Reliable outcome for {action_type}",
                            source_type="outcome",
                            source_id=oid,
                            state=KnowledgeState.VALIDATED.value,
                            confidence=reliability,
                            validations=2,
                            created_at=time.time(),
                        ))
        except Exception:
            logger.debug("Error synthesizing from outcomes", exc_info=True)

    def _synthesize_from_learning(self) -> None:
        """Learning portfolio lessons become PROPOSED knowledge."""
        try:
            learning = self._learning
            if learning is None:
                return
            snap = learning.snapshot() if hasattr(learning, "snapshot") else None
            if snap is None:
                return
            lessons = []
            if hasattr(snap, "top_lessons"):
                lessons = snap.top_lessons or []
            elif isinstance(snap, dict):
                lessons = snap.get("top_lessons", [])

            for lesson in lessons:
                lid = ""
                content = ""
                if isinstance(lesson, dict):
                    lid = lesson.get("lesson_id", lesson.get("id", ""))
                    content = lesson.get("content", lesson.get("description", ""))
                elif hasattr(lesson, "lesson_id"):
                    lid = lesson.lesson_id
                    content = getattr(lesson, "content", "") or getattr(lesson, "description", "")
                if lid and content:
                    self._knowledge.append(InstitutionalKnowledge(
                        knowledge_id=_knowledge_id("lesson", lid),
                        content=content,
                        source_type="lesson",
                        source_id=lid,
                        state=KnowledgeState.PROPOSED.value,
                        confidence=0.4,
                        validations=0,
                        created_at=time.time(),
                    ))
        except Exception:
            logger.debug("Error synthesizing from learning", exc_info=True)

    # ── Public API ───────────────────────────────────────────────────

    def propose(
        self, content: str, source_type: str, source_id: str
    ) -> InstitutionalKnowledge:
        """Propose new institutional knowledge."""
        self._ensure_synthesized()
        k = InstitutionalKnowledge(
            knowledge_id=_knowledge_id(source_type, source_id),
            content=content,
            source_type=source_type,
            source_id=source_id,
            state=KnowledgeState.PROPOSED.value,
            confidence=0.3,
            validations=0,
            created_at=time.time(),
        )
        self._knowledge.append(k)
        return k

    def validate(self, knowledge_id: str) -> InstitutionalKnowledge | None:
        """Increment validation count. Promote to VALIDATED when validations >= 2."""
        self._ensure_synthesized()
        for k in self._knowledge:
            if k.knowledge_id == knowledge_id:
                k.validations += 1
                if k.validations >= 2 and k.state == KnowledgeState.PROPOSED.value:
                    k.state = KnowledgeState.VALIDATED.value
                    k.confidence = max(k.confidence, 0.6)
                return k
        return None

    def promote(self, knowledge_id: str) -> InstitutionalKnowledge | None:
        """Promote to CANONICAL if validations >= 3 and confidence >= 0.7."""
        self._ensure_synthesized()
        for k in self._knowledge:
            if k.knowledge_id == knowledge_id:
                if k.validations >= 3 and k.confidence >= 0.7:
                    k.state = KnowledgeState.CANONICAL.value
                    k.promoted_at = time.time()
                return k
        return None

    def supersede(
        self, knowledge_id: str, replacement_id: str
    ) -> InstitutionalKnowledge | None:
        """Mark knowledge as SUPERSEDED by another entry."""
        self._ensure_synthesized()
        for k in self._knowledge:
            if k.knowledge_id == knowledge_id:
                k.state = KnowledgeState.SUPERSEDED.value
                return k
        return None

    def retire(self, knowledge_id: str) -> InstitutionalKnowledge | None:
        """Mark knowledge as RETIRED."""
        self._ensure_synthesized()
        for k in self._knowledge:
            if k.knowledge_id == knowledge_id:
                k.state = KnowledgeState.RETIRED.value
                return k
        return None

    def knowledge_by_state(
        self, state: str | None = None
    ) -> list[InstitutionalKnowledge]:
        """Return knowledge filtered by state, or all if state is None."""
        self._ensure_synthesized()
        if state is None:
            return list(self._knowledge)
        return [k for k in self._knowledge if k.state == state]

    def canonical_knowledge(self) -> list[InstitutionalKnowledge]:
        """Return only CANONICAL knowledge."""
        return self.knowledge_by_state(KnowledgeState.CANONICAL.value)

    def drift_warnings(self) -> list[InstitutionalMemoryDriftWarning]:
        """Detect institutional memory drift."""
        self._ensure_synthesized()
        warnings: list[InstitutionalMemoryDriftWarning] = []
        warnings.extend(self._detect_stale_canonical())
        warnings.extend(self._detect_unvalidated_backlog())
        warnings.extend(self._detect_lesson_loss())
        return warnings

    def health(self) -> InstitutionalMemoryHealth:
        """Classify institutional memory health."""
        self._ensure_synthesized()
        canonical = self.canonical_knowledge()
        total = len(self._knowledge)
        validated_or_above = [
            k for k in self._knowledge
            if k.state in (
                KnowledgeState.VALIDATED.value,
                KnowledgeState.CANONICAL.value,
            )
        ]
        validation_rate = len(validated_or_above) / total if total > 0 else 0.0
        drift = self.drift_warnings()
        superseded = [
            k for k in self._knowledge
            if k.state == KnowledgeState.SUPERSEDED.value
        ]

        if len(canonical) == 0 and total > 0:
            return InstitutionalMemoryHealth.CRITICAL
        if total == 0:
            return InstitutionalMemoryHealth.CRITICAL
        if len(drift) > 5 or len(superseded) > len(canonical):
            return InstitutionalMemoryHealth.DECAYING
        if validation_rate < 0.3:
            return InstitutionalMemoryHealth.STAGNANT
        if len(canonical) > 5 and validation_rate > 0.7 and len(drift) == 0:
            return InstitutionalMemoryHealth.THRIVING
        if len(canonical) > 2 and validation_rate > 0.5 and len(drift) <= 2:
            return InstitutionalMemoryHealth.GROWING
        return InstitutionalMemoryHealth.STAGNANT

    def snapshot(self) -> InstitutionalMemorySnapshot:
        """Full institutional memory snapshot."""
        self._ensure_synthesized()
        by_state: dict[str, int] = {}
        for k in self._knowledge:
            by_state[k.state] = by_state.get(k.state, 0) + 1

        canonical = self.canonical_knowledge()
        total = len(self._knowledge)
        validated_or_above = [
            k for k in self._knowledge
            if k.state in (KnowledgeState.VALIDATED.value, KnowledgeState.CANONICAL.value)
        ]
        recent = [
            k for k in self._knowledge
            if k.state == KnowledgeState.CANONICAL.value and k.promoted_at > 0
        ]
        recent.sort(key=lambda k: k.promoted_at, reverse=True)

        return InstitutionalMemorySnapshot(
            memory_health=self.health().value,
            knowledge_by_state=by_state,
            total_knowledge=total,
            canonical_count=len(canonical),
            validation_rate=round(len(validated_or_above) / total, 4) if total > 0 else 0.0,
            drift_warnings=[w.to_dict() for w in self.drift_warnings()],
            recent_promotions=[k.to_dict() for k in recent[:5]],
            generated_at=time.time(),
        )

    def summary(self) -> dict[str, Any]:
        """Quick summary dict."""
        self._ensure_synthesized()
        return {
            "memory_health": self.health().value,
            "total_knowledge": len(self._knowledge),
            "canonical_count": len(self.canonical_knowledge()),
            "drift_warning_count": len(self.drift_warnings()),
        }

    # ── Drift Detectors ──────────────────────────────────────────────

    def _detect_stale_canonical(self) -> list[InstitutionalMemoryDriftWarning]:
        """Canonical knowledge older than 30 days without re-validation."""
        stale: list[str] = []
        now = time.time()
        for k in self._knowledge:
            if k.state == KnowledgeState.CANONICAL.value:
                age = now - k.promoted_at if k.promoted_at > 0 else now - k.created_at
                if age > _STALE_THRESHOLD_SECONDS:
                    stale.append(k.knowledge_id)
        if stale:
            return [InstitutionalMemoryDriftWarning(
                drift_type=MemoryDriftType.STALE_CANONICAL.value,
                severity="medium" if len(stale) < 3 else "high",
                description=f"{len(stale)} canonical knowledge entries older than 30 days",
                affected_ids=stale,
                recommendation="Re-validate or retire stale canonical knowledge",
            )]
        return []

    def _detect_unvalidated_backlog(self) -> list[InstitutionalMemoryDriftWarning]:
        """>10 proposed entries awaiting validation."""
        proposed = [
            k for k in self._knowledge
            if k.state == KnowledgeState.PROPOSED.value
        ]
        if len(proposed) > 10:
            return [InstitutionalMemoryDriftWarning(
                drift_type=MemoryDriftType.UNVALIDATED_BACKLOG.value,
                severity="medium",
                description=f"{len(proposed)} proposed knowledge entries awaiting validation",
                affected_ids=[k.knowledge_id for k in proposed],
                recommendation="Review and validate proposed knowledge entries",
            )]
        return []

    def _detect_lesson_loss(self) -> list[InstitutionalMemoryDriftWarning]:
        """Learning portfolio has lessons not captured as knowledge."""
        try:
            learning = self._learning
            if learning is None:
                return []
            snap = learning.snapshot() if hasattr(learning, "snapshot") else None
            if snap is None:
                return []

            lesson_count = 0
            if hasattr(snap, "lesson_count"):
                lesson_count = snap.lesson_count
            elif isinstance(snap, dict):
                lesson_count = snap.get("lesson_count", 0)

            knowledge_from_lessons = [
                k for k in self._knowledge if k.source_type == "lesson"
            ]

            if lesson_count > 0 and len(knowledge_from_lessons) == 0:
                return [InstitutionalMemoryDriftWarning(
                    drift_type=MemoryDriftType.LESSON_LOSS.value,
                    severity="medium",
                    description=f"{lesson_count} lessons in learning portfolio with no institutional knowledge entry",
                    affected_ids=[],
                    recommendation="Review learning portfolio lessons for institutional knowledge candidates",
                )]
        except Exception:
            logger.debug("Error detecting lesson loss", exc_info=True)
        return []
