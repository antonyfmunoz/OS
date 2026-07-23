"""Intent Router — deterministic-first classification of operator intent.

Classifies incoming operator text into one of five route types:
  conversation  — pure chat/question (Path A: spine)
  work_packet   — build/deploy/create (Path B: organism loop)
  hybrid        — conversation that may need work
  observation   — status check, no execution
  approval      — approve/reject existing work packet

The router classifies and routes ONLY. It does NOT perform execution,
governance, memory writes, or reality writes. All execution flows through
either the existing ConcreteExecutionSpine (conversation) or the Phase 17
OrganismLoopEngine (governed work).

Deterministic-first: regex/keyword patterns run first. The existing
IntentClassifier is used for domain/work_type refinement when patterns
are ambiguous. No LLM call for clear intents.

Phase 18. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class RouteType(str, Enum):
    CONVERSATION = "conversation"
    WORK_PACKET = "work_packet"
    HYBRID = "hybrid"
    OBSERVATION = "observation"
    APPROVAL = "approval"


@dataclass
class RouteClassification:
    route_type: RouteType
    confidence: float
    extracted_entities: dict[str, str] = field(default_factory=dict)
    reasoning: str = ""
    domain: str = ""
    work_type: str = ""
    risk_class: str = "low"


_APPROVAL_PATTERNS = re.compile(
    r"\b(approve|reject|accept|deny|confirm)\b.*\b(packet|deployment|request|change)\b"
    r"|\b(approve|reject|accept|deny)\s+(it|this|that|the)\b",
    re.IGNORECASE,
)

_OBSERVATION_PATTERNS = re.compile(
    r"^(what(?:'s| is| are) the (?:status|progress|state))"
    r"|^(show me|what(?:'s| is) happening|how is|how are|list (?:all|the)|check (?:the|on))"
    r"|\b(status|progress)\s+(?:of|on|for)\b"
    r"|^what (?:changed|happened)",
    re.IGNORECASE,
)

_WORK_IMPERATIVE_PATTERNS = re.compile(
    r"^(build|deploy|create|implement|fix|patch|repair|refactor|migrate|launch|ship|release"
    r"|set up|configure|install|remove|delete|update|upgrade|add|write|generate)\b",
    re.IGNORECASE,
)

_WORK_RESEARCH_PATTERNS = re.compile(
    r"^(research|plan|analyze|investigate|design|architect|audit|evaluate|assess)\b",
    re.IGNORECASE,
)

_CONVERSATION_PATTERNS = re.compile(
    r"^(what do you think|help me think|brainstorm|discuss|explain|tell me about)"
    r"|^(why (?:do|does|did|is|are|should|would|can))"
    r"|^(how does|how do|how can|how should|how would)"
    r"|^(what (?:is|are) (?:the |a |an )?(?!status|progress|state))",
    re.IGNORECASE,
)

_RECALL_PATTERNS = re.compile(
    r"\b(remember|last time|what did (?:we|you|I)|previously|recall|what was)\b",
    re.IGNORECASE,
)

_REALITY_QUERY_PATTERNS = re.compile(
    r"^(why (?:did|does|is|was|were|has|have))"
    r"|^(what (?:changed|happened|is different))"
    r"|\b(show me evidence|find evidence|evidence for|evidence against)\b"
    r"|\b(contradictions?|conflicting)\s+(?:in|for|about|between)\b"
    r"|\b(trace|lineage|chain of|how did we get to|what led to)\b"
    r"|\b(summarize|summary of)\s+(?:the\s+)?(?:domain|area|topic)\b"
    r"|\b(what are the priorities|prioriti[sz]e|top priorities|most urgent)\b",
    re.IGNORECASE,
)

_HYBRID_QUALIFIERS = re.compile(
    r"^(should (?:we|I)|what if (?:we|I)|could (?:we|I)|would it make sense to|do you think we should)\b",
    re.IGNORECASE,
)

_ACTION_VERBS = re.compile(
    r"\b(build|deploy|create|implement|fix|patch|repair|refactor|migrate|launch|ship|release"
    r"|configure|install|remove|delete|update|upgrade|add|write|generate"
    r"|research|plan|analyze|investigate|design|architect|audit)\b",
    re.IGNORECASE,
)


class IntentRouter:
    """Classifies operator intent into route types. No execution side effects."""

    def __init__(self) -> None:
        self._classifier = None

    def _get_classifier(self) -> Any:
        if self._classifier is None:
            from substrate.organism.intent_classifier import IntentClassifier

            self._classifier = IntentClassifier()
        return self._classifier

    def classify(self, intent: str) -> RouteClassification:
        """Deterministic-first classification. No execution, no side effects."""
        text = intent.strip()
        if not text:
            return RouteClassification(
                route_type=RouteType.CONVERSATION,
                confidence=0.50,
                reasoning="empty input defaults to conversation",
            )

        matches = self._match_patterns(text)

        high_confidence = [m for m in matches if m[1] >= 0.80]
        if len(high_confidence) == 1:
            route_type, confidence, reasoning = high_confidence[0]
            entities = self._extract_entities(text)
            return RouteClassification(
                route_type=route_type,
                confidence=confidence,
                extracted_entities=entities,
                reasoning=reasoning,
            )

        if high_confidence:
            return self._refine_with_classifier(text, high_confidence)

        if matches:
            return self._refine_with_classifier(text, matches)

        return self._fallback_classify(text)

    def _match_patterns(self, text: str) -> list[tuple[RouteType, float, str]]:
        matches: list[tuple[RouteType, float, str]] = []

        if _APPROVAL_PATTERNS.search(text):
            matches.append((RouteType.APPROVAL, 0.95, "approval verb + target detected"))

        if _REALITY_QUERY_PATTERNS.search(text):
            matches.append((RouteType.OBSERVATION, 0.92, "reality intelligence query detected"))

        if _OBSERVATION_PATTERNS.search(text):
            matches.append((RouteType.OBSERVATION, 0.90, "status/observation query detected"))

        if _HYBRID_QUALIFIERS.search(text):
            matches.append((RouteType.HYBRID, 0.75, "conversational qualifier + potential work"))

        if not _HYBRID_QUALIFIERS.search(text) and _WORK_IMPERATIVE_PATTERNS.search(text):
            matches.append((RouteType.WORK_PACKET, 0.85, "imperative work verb detected"))

        if not _HYBRID_QUALIFIERS.search(text) and _WORK_RESEARCH_PATTERNS.search(text):
            matches.append((RouteType.WORK_PACKET, 0.80, "research/planning verb detected"))

        if _CONVERSATION_PATTERNS.search(text):
            matches.append((RouteType.CONVERSATION, 0.85, "conversational pattern detected"))

        if _RECALL_PATTERNS.search(text):
            matches.append((RouteType.CONVERSATION, 0.80, "recall/memory pattern detected"))

        return matches

    def _refine_with_classifier(
        self,
        text: str,
        candidates: list[tuple[RouteType, float, str]],
    ) -> RouteClassification:
        classifier = self._get_classifier()
        classification = classifier.classify(text)

        best = max(candidates, key=lambda c: c[1])
        route_type, confidence, reasoning = best

        return RouteClassification(
            route_type=route_type,
            confidence=confidence,
            extracted_entities=self._extract_entities(text),
            reasoning=reasoning,
            domain=classification.domain,
            work_type=classification.work_type,
            risk_class=classification.risk_class,
        )

    def _fallback_classify(self, text: str) -> RouteClassification:
        words = text.split()
        has_action_verb = bool(_ACTION_VERBS.search(text))

        if len(words) < 8 and not has_action_verb:
            return RouteClassification(
                route_type=RouteType.CONVERSATION,
                confidence=0.50,
                extracted_entities=self._extract_entities(text),
                reasoning="short input without action verbs, defaulting to conversation",
            )

        if has_action_verb:
            classifier = self._get_classifier()
            classification = classifier.classify(text)
            return RouteClassification(
                route_type=RouteType.HYBRID,
                confidence=0.45,
                extracted_entities=self._extract_entities(text),
                reasoning="action verb present but no clear pattern match",
                domain=classification.domain,
                work_type=classification.work_type,
                risk_class=classification.risk_class,
            )

        return RouteClassification(
            route_type=RouteType.CONVERSATION,
            confidence=0.50,
            extracted_entities=self._extract_entities(text),
            reasoning="no clear pattern, defaulting to conversation",
        )

    def _extract_entities(self, text: str) -> dict[str, str]:
        classifier = self._get_classifier()
        classification = classifier.classify(text)
        entities: dict[str, str] = {}
        if classification.entity:
            entities["entity"] = classification.entity
        if classification.company:
            entities["company"] = classification.company
        if classification.product:
            entities["product"] = classification.product
        if classification.project:
            entities["project"] = classification.project
        return entities
