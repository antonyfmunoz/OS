"""Signal ingestion — converts raw input into a classified SignalBundle.

Deterministic keyword-based classification. No LLM required.
Domain adapters can override classify() for richer extraction.
"""

from __future__ import annotations

import uuid
from typing import Any

from umh.signal.types import Signal, SignalBundle, SignalTier

_TIER_KEYWORDS: dict[SignalTier, list[str]] = {
    SignalTier.REALITY: [
        "happened",
        "now",
        "today",
        "result",
        "data",
        "metric",
        "error",
        "failed",
        "succeeded",
        "status",
        "actual",
    ],
    SignalTier.CONTEXT: [
        "stage",
        "beginning",
        "domain",
        "environment",
        "situation",
        "state",
        "context",
        "where",
        "when",
        "who",
    ],
    SignalTier.LEVERAGE: [
        "priority",
        "important",
        "critical",
        "blocker",
        "bottleneck",
        "constraint",
        "leverage",
        "highest impact",
    ],
    SignalTier.OPTIMIZATION: [
        "pattern",
        "optimize",
        "improve",
        "efficiency",
        "better",
        "strategy",
        "approach",
        "method",
    ],
    SignalTier.DELIVERY: [
        "format",
        "present",
        "explain",
        "summarize",
        "style",
        "tone",
        "deliver",
        "output",
    ],
}


def classify_input(
    raw_input: str,
    source: str = "user",
    metadata: dict[str, Any] | None = None,
) -> SignalBundle:
    """Classify raw input into a SignalBundle with tier-ranked signals.

    Always produces at least one signal (CONTEXT tier as fallback).
    """
    content_lower = raw_input.lower()
    signals: list[Signal] = []

    for tier, keywords in _TIER_KEYWORDS.items():
        matches = [kw for kw in keywords if kw in content_lower]
        if matches:
            confidence = min(0.5 + 0.1 * len(matches), 0.95)
            signals.append(
                Signal(
                    signal_id=f"sig_{uuid.uuid4().hex[:12]}",
                    tier=tier,
                    source=source,
                    content=raw_input[:500],
                    confidence=confidence,
                    domain="universal",
                    metadata=metadata or {},
                )
            )

    if not signals:
        signals.append(
            Signal(
                signal_id=f"sig_{uuid.uuid4().hex[:12]}",
                tier=SignalTier.CONTEXT,
                source=source,
                content=raw_input[:500],
                confidence=0.5,
                domain="universal",
                metadata=metadata or {},
            )
        )

    signals.sort(key=lambda s: s.tier.value)

    return SignalBundle(
        signals=tuple(signals),
        raw_input=raw_input,
        source=source,
    )
