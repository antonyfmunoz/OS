"""Intent compiler — transforms a SignalBundle into structured intent.

Intent represents the system's understanding of what should happen:
what operation to perform, what constraints apply, and what the
objective is. This is the bridge between perception and action.

No LLM calls. Deterministic keyword-to-intent mapping.
Domain adapters can inject richer intent resolution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from umh.signal.types import SignalBundle, SignalTier

if TYPE_CHECKING:
    from umh.brains.context import BrainContext


class IntentType:
    QUERY = "query"
    ACTION = "action"
    ANALYSIS = "analysis"
    CREATION = "creation"
    MONITORING = "monitoring"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Intent:
    """Structured intent compiled from signals."""

    intent_id: str
    intent_type: str
    operation: str
    description: str
    constraints: dict[str, Any] = field(default_factory=dict)
    objective: str = ""
    confidence: float = 0.5
    source_signal_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "intent_type": self.intent_type,
            "operation": self.operation,
            "description": self.description,
            "constraints": self.constraints,
            "objective": self.objective,
            "confidence": round(self.confidence, 4),
            "source_signal_ids": list(self.source_signal_ids),
        }


_ACTION_KEYWORDS = [
    "do",
    "run",
    "execute",
    "create",
    "build",
    "deploy",
    "send",
    "start",
    "stop",
    "delete",
    "update",
    "change",
    "fix",
    "move",
]
_QUERY_KEYWORDS = [
    "what",
    "how",
    "why",
    "when",
    "where",
    "who",
    "show",
    "list",
    "find",
    "search",
    "tell",
    "explain",
    "describe",
]
_ANALYSIS_KEYWORDS = [
    "analyze",
    "compare",
    "evaluate",
    "assess",
    "measure",
    "review",
    "audit",
    "diagnose",
    "investigate",
]
_CREATION_KEYWORDS = [
    "write",
    "draft",
    "compose",
    "generate",
    "design",
    "plan",
    "outline",
    "sketch",
    "propose",
]
_MONITORING_KEYWORDS = [
    "watch",
    "monitor",
    "track",
    "alert",
    "notify",
    "check",
    "status",
    "health",
]


def compile_intent(
    bundle: SignalBundle,
    brain_context: "BrainContext | None" = None,
) -> Intent:
    """Compile a SignalBundle into a single structured Intent.

    Uses the primary signal's content for keyword classification.
    When brain_context is provided, amplified/silenced concepts
    adjust keyword match weights (epigenetic effect).
    Falls back to UNKNOWN if no classification matches.
    """
    import uuid

    primary = bundle.primary
    if primary is None:
        return Intent(
            intent_id=f"int_{uuid.uuid4().hex[:12]}",
            intent_type=IntentType.UNKNOWN,
            operation="noop",
            description="No signal to interpret",
            confidence=0.0,
        )

    content_lower = primary.content.lower()
    signal_ids = tuple(s.signal_id for s in bundle.signals)

    intent_type = IntentType.UNKNOWN
    best_score: float = 0.0

    for itype, keywords in [
        (IntentType.ACTION, _ACTION_KEYWORDS),
        (IntentType.QUERY, _QUERY_KEYWORDS),
        (IntentType.ANALYSIS, _ANALYSIS_KEYWORDS),
        (IntentType.CREATION, _CREATION_KEYWORDS),
        (IntentType.MONITORING, _MONITORING_KEYWORDS),
    ]:
        score = 0.0
        for kw in keywords:
            if kw in content_lower:
                weight = brain_context.weight_for_concept(kw) if brain_context else 1.0
                score += weight
        if score > best_score:
            best_score = score
            intent_type = itype

    # Brain can suppress entire intent types
    if brain_context and brain_context.should_suppress_intent(intent_type):
        intent_type = IntentType.UNKNOWN
        best_score = 0.0

    operation = _derive_operation(intent_type, content_lower)
    confidence = min(primary.confidence + 0.1 * best_score, 0.95)

    constraints: dict[str, Any] = {}
    if bundle.highest_tier == SignalTier.REALITY:
        constraints["grounded"] = True
    if any(s.tier == SignalTier.LEVERAGE for s in bundle.signals):
        constraints["high_leverage"] = True

    metadata: dict[str, Any] = {}
    if brain_context and brain_context.brain_id:
        metadata["brain_id"] = brain_context.brain_id

    return Intent(
        intent_id=f"int_{uuid.uuid4().hex[:12]}",
        intent_type=intent_type,
        operation=operation,
        description=primary.content[:200],
        constraints=constraints,
        objective=_derive_objective(intent_type, primary.content),
        confidence=confidence,
        source_signal_ids=signal_ids,
        metadata=metadata,
    )


def _derive_operation(intent_type: str, content: str) -> str:
    """Map intent type to a generic operation name."""
    return {
        IntentType.ACTION: "execute_action",
        IntentType.QUERY: "answer_query",
        IntentType.ANALYSIS: "run_analysis",
        IntentType.CREATION: "create_artifact",
        IntentType.MONITORING: "check_status",
        IntentType.UNKNOWN: "process_input",
    }.get(intent_type, "process_input")


def _derive_objective(intent_type: str, content: str) -> str:
    """Generate a one-line objective from intent type and content."""
    prefix = {
        IntentType.ACTION: "Execute",
        IntentType.QUERY: "Answer",
        IntentType.ANALYSIS: "Analyze",
        IntentType.CREATION: "Create",
        IntentType.MONITORING: "Monitor",
        IntentType.UNKNOWN: "Process",
    }.get(intent_type, "Process")
    return f"{prefix}: {content[:100]}"
