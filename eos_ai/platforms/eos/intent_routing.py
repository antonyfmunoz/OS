"""
Founder intent parsing — deterministic classification of founder messages.

Classifies raw founder text into intent types and suggests which EOS role
should handle it.  All classification is keyword-based — zero LLM cost.
The founder never directly addresses CEO or Portfolio Advisor; the parser
only suggests delegation beneath EA.

Design rules:
- Deterministic — regex heuristics only, no LLM.
- The suggested_role is advisory — EA always mediates.
- Confidence is rule-based (1.0 for strong match, 0.7 for weak, 0.5 fallback).
- extracted_directives captures actionable fragments for downstream use.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from eos_ai.platforms.eos.roles import EOSRole


# ─── Intent types ────────────────────────────────────────────────────────────


class FounderIntentType(str, Enum):
    """What the founder wants to accomplish."""

    DIRECT_EA = "direct_ea"  # communication, coordination, scheduling
    STRATEGY = "strategy"  # business direction, priorities, revenue
    PORTFOLIO = "portfolio"  # investments, capital, risk analysis
    EXECUTION = "execution"  # build, draft, create, prepare work
    REVIEW = "review"  # review work, approve outputs, QA
    STATUS = "status"  # catch me up, what's happening, summarize
    UNKNOWN = "unknown"  # couldn't classify


# ─── Classification rules ────────────────────────────────────────────────────

# Each rule: (compiled regex, FounderIntentType, suggested EOSRole, confidence)
# Evaluated top-to-bottom; first match wins.

_RULES: list[tuple[re.Pattern, FounderIntentType, EOSRole, float]] = [
    # Portfolio / investment (highest specificity)
    (
        re.compile(
            r"\b(portfolio|allocation|risk\s+assess\w*|investment|capital\s+"
            r"allocation|asset|dividend|equity|valuation|IRR|ROI\s+on"
            r"|net\s+worth|diversif\w*)\b",
            re.IGNORECASE,
        ),
        FounderIntentType.PORTFOLIO,
        EOSRole.PORTFOLIO_ADVISOR,
        1.0,
    ),
    # Strategy / CEO domain
    (
        re.compile(
            r"\b(strategy|priorities|business\s+direction|offer\s+ladder"
            r"|revenue\s+model|pricing\s+strateg\w*|company\s+direction"
            r"|growth\s+plan|market\s+position|competitive|moat"
            r"|resource\s+allocat\w*|north\s+star|roadmap|milestone)\b",
            re.IGNORECASE,
        ),
        FounderIntentType.STRATEGY,
        EOSRole.CEO,
        1.0,
    ),
    # Status / briefing (EA handles directly)
    (
        re.compile(
            r"\b(status|catch\s+me\s+up|what.?s\s+(happening|blocked|next)"
            r"|summarize|brief\s+me|morning\s+brief|overnight|report"
            r"|dashboard|how\s+are\s+(things|we)|update\s+me|sitrep)\b",
            re.IGNORECASE,
        ),
        FounderIntentType.STATUS,
        EOSRole.EA,
        1.0,
    ),
    # Review / QA (EA handles directly)
    (
        re.compile(
            r"\b(review|approve|sign\s*off|validate|check\s+this"
            r"|look\s+at|evaluate|audit|inspect|QA|quality)\b",
            re.IGNORECASE,
        ),
        FounderIntentType.REVIEW,
        EOSRole.EA,
        0.9,
    ),
    # Execution requests (EA intake, may create substrate work)
    (
        re.compile(
            r"\b(build|execute|draft|create|prepare|implement|deploy"
            r"|fix|ship|launch|write|design|code|test|migrate"
            r"|set\s+up|configure|install|automate)\b",
            re.IGNORECASE,
        ),
        FounderIntentType.EXECUTION,
        EOSRole.EA,
        0.8,
    ),
    # Direct EA communication (weak signals)
    (
        re.compile(
            r"\b(schedule|remind|tell|notify|send|forward|follow\s+up"
            r"|coordinate|arrange|plan\s+(my|the)|check\s+in)\b",
            re.IGNORECASE,
        ),
        FounderIntentType.DIRECT_EA,
        EOSRole.EA,
        0.7,
    ),
]


# ─── Directive extraction ────────────────────────────────────────────────────

# Simple heuristics to pull actionable fragments from founder text.
_DIRECTIVE_RE = re.compile(
    r"(?:^|\.\s+|\n)"  # sentence start
    r"("
    r"[A-Z][^.!?\n]{10,120}"  # capitalized sentence, 10-120 chars
    r"[.!?]?"  # optional terminator
    r")",
)


def _extract_directives(text: str) -> list[str]:
    """Pull actionable sentence fragments from founder text."""
    matches = _DIRECTIVE_RE.findall(text)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        stripped = m.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            result.append(stripped)
    return result[:5]  # cap at 5 directives


# ─── Intent model ────────────────────────────────────────────────────────────


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"intent_{uuid.uuid4().hex[:12]}"


@dataclass
class FounderIntent:
    """Parsed founder intent — the output of deterministic classification."""

    intent_id: str
    raw_text: str
    intent_type: FounderIntentType
    suggested_role: EOSRole
    confidence: float
    extracted_directives: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict:
        return {
            "intent_id": self.intent_id,
            "raw_text": self.raw_text,
            "intent_type": self.intent_type.value,
            "suggested_role": self.suggested_role.value,
            "confidence": self.confidence,
            "extracted_directives": self.extracted_directives,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FounderIntent":
        return cls(
            intent_id=d["intent_id"],
            raw_text=d["raw_text"],
            intent_type=FounderIntentType(d["intent_type"]),
            suggested_role=EOSRole(d["suggested_role"]),
            confidence=d["confidence"],
            extracted_directives=d.get("extracted_directives", []),
            created_at=d.get("created_at", _utcnow()),
        )


# ─── Parser ──────────────────────────────────────────────────────────────────


def parse_founder_intent(text: str) -> FounderIntent:
    """
    Classify founder text into a FounderIntent.

    Rules evaluated top-to-bottom; first match wins.
    Falls back to UNKNOWN / EA / 0.5 if nothing matches.
    """
    text_stripped = text.strip()
    if not text_stripped:
        return FounderIntent(
            intent_id=_new_id(),
            raw_text=text,
            intent_type=FounderIntentType.UNKNOWN,
            suggested_role=EOSRole.EA,
            confidence=0.0,
            extracted_directives=[],
        )

    for pattern, intent_type, role, confidence in _RULES:
        if pattern.search(text_stripped):
            return FounderIntent(
                intent_id=_new_id(),
                raw_text=text,
                intent_type=intent_type,
                suggested_role=role,
                confidence=confidence,
                extracted_directives=_extract_directives(text_stripped),
            )

    # Fallback — EA handles unknown intent
    return FounderIntent(
        intent_id=_new_id(),
        raw_text=text,
        intent_type=FounderIntentType.UNKNOWN,
        suggested_role=EOSRole.EA,
        confidence=0.5,
        extracted_directives=_extract_directives(text_stripped),
    )
