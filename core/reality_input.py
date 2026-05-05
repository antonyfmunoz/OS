"""Reality Input Layer — ingest external signals and convert to primitives.

Converts raw real-world inputs (text, API responses, metrics) into
L0 primitive sets with source tracking and timestamps.

This is the system's interface with reality.  Everything the system
knows about the outside world enters through this layer.

Usage:
    from core.reality_input import ingest_signal, RealitySignal

    signal = ingest_signal("reply_rate dropped to 2% this week")
    print(signal.primitives)   # {STATE, SIGNAL, FEEDBACK, OUTCOME, TIME}
    print(signal.source)       # "text"
    print(signal.timestamp)    # ISO timestamp
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from core.primitives import PrimitiveTag


# ---------------------------------------------------------------------------
# Signal classification
# ---------------------------------------------------------------------------

# Maps keyword patterns to the primitives they imply.
# Ordered by specificity — first match wins per keyword group.
_SIGNAL_PATTERNS: list[tuple[list[str], set[PrimitiveTag]]] = [
    # Metrics / outcomes
    (
        ["rate", "ratio", "percent", "%", "conversion", "ctr", "open rate"],
        {PrimitiveTag.OUTCOME, PrimitiveTag.SIGNAL, PrimitiveTag.FEEDBACK},
    ),
    # Temporal signals
    (
        [
            "today",
            "yesterday",
            "this week",
            "last week",
            "hours",
            "minutes",
            "deadline",
        ],
        {PrimitiveTag.TIME},
    ),
    # State descriptions
    (
        [
            "currently",
            "right now",
            "status",
            "is at",
            "sitting at",
            "dropped to",
            "rose to",
        ],
        {PrimitiveTag.STATE},
    ),
    # Change events
    (
        [
            "increased",
            "decreased",
            "dropped",
            "rose",
            "changed",
            "shifted",
            "grew",
            "fell",
        ],
        {PrimitiveTag.CHANGE, PrimitiveTag.STATE},
    ),
    # Goals / targets
    (
        ["target", "goal", "aim", "want", "need", "reach", "achieve", "hit"],
        {PrimitiveTag.GOAL},
    ),
    # Constraints / limits
    (
        [
            "limit",
            "budget",
            "cap",
            "maximum",
            "minimum",
            "only",
            "restricted",
            "blocked",
        ],
        {PrimitiveTag.CONSTRAINT, PrimitiveTag.RESOURCE},
    ),
    # Actions taken
    (
        [
            "sent",
            "posted",
            "launched",
            "started",
            "ran",
            "executed",
            "published",
            "messaged",
        ],
        {PrimitiveTag.ACTION},
    ),
    # Resource mentions
    (
        [
            "cost",
            "spend",
            "budget",
            "credits",
            "time spent",
            "hours",
            "money",
            "investment",
        ],
        {PrimitiveTag.RESOURCE},
    ),
    # Feedback / responses
    (
        ["replied", "responded", "feedback", "review", "reaction", "comment", "bounce"],
        {PrimitiveTag.FEEDBACK, PrimitiveTag.SIGNAL},
    ),
]


def _classify_text(text: str) -> set[PrimitiveTag]:
    """Extract primitive tags from raw text input via pattern matching."""
    text_lower = text.lower()
    tags: set[PrimitiveTag] = set()

    for keywords, primitives in _SIGNAL_PATTERNS:
        if any(kw in text_lower for kw in keywords):
            tags.update(primitives)

    # Every signal from reality is at minimum a SIGNAL
    tags.add(PrimitiveTag.SIGNAL)
    return tags


# ---------------------------------------------------------------------------
# Reality signal
# ---------------------------------------------------------------------------


@dataclass
class RealitySignal:
    """A parsed external signal with primitive decomposition and provenance."""

    raw: str
    source: str  # "text" | "api" | "metric" | "file" | "log"
    primitives: set[PrimitiveTag]
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "source": self.source,
            "primitives": sorted(t.value for t in self.primitives),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Signal memory (in-process store, feeds into memory_evolution)
# ---------------------------------------------------------------------------

_signal_history: list[RealitySignal] = []

_MAX_HISTORY = 500


def _store_signal(signal: RealitySignal) -> None:
    """Append signal to in-process history, evicting oldest if full."""
    _signal_history.append(signal)
    if len(_signal_history) > _MAX_HISTORY:
        _signal_history.pop(0)


def get_signal_history(limit: int = 50) -> list[RealitySignal]:
    """Return most recent signals, newest last."""
    return _signal_history[-limit:]


def clear_signal_history() -> None:
    """Reset signal history (useful for testing)."""
    _signal_history.clear()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def ingest_signal(
    raw_input: str,
    *,
    source: str = "text",
    metadata: dict[str, Any] | None = None,
) -> RealitySignal:
    """Parse raw external input into a RealitySignal with primitive tags.

    This is the primary entry point for the reality input layer.
    Every external signal the system receives should pass through here.

    Args:
        raw_input:  The raw text/data from the outside world.
        source:     Where the signal came from ("text", "api", "metric", "file", "log").
        metadata:   Optional extra context (e.g. API response codes, metric names).

    Returns:
        RealitySignal with classified primitives, timestamp, and provenance.
    """
    primitives = _classify_text(raw_input)

    signal = RealitySignal(
        raw=raw_input,
        source=source,
        primitives=primitives,
        timestamp=time.time(),
        metadata=metadata or {},
    )

    _store_signal(signal)
    return signal


def ingest_metric(
    name: str,
    value: float,
    *,
    target: float | None = None,
    period: str = "",
) -> RealitySignal:
    """Convenience: ingest a numeric metric as a reality signal.

    Automatically classifies with OUTCOME, SIGNAL, and adds GOAL
    if a target is provided, FEEDBACK if value < target.
    """
    primitives: set[PrimitiveTag] = {PrimitiveTag.OUTCOME, PrimitiveTag.SIGNAL}

    if target is not None:
        primitives.add(PrimitiveTag.GOAL)
        if value < target:
            primitives.add(PrimitiveTag.FEEDBACK)
        if value >= target:
            primitives.add(PrimitiveTag.STATE)  # achieved state

    if period:
        primitives.add(PrimitiveTag.TIME)

    raw = f"{name}={value}"
    if target is not None:
        raw += f" (target={target})"
    if period:
        raw += f" [{period}]"

    signal = RealitySignal(
        raw=raw,
        source="metric",
        primitives=primitives,
        timestamp=time.time(),
        metadata={
            "metric_name": name,
            "value": value,
            "target": target,
            "period": period,
        },
    )

    _store_signal(signal)
    return signal


def ingest_api_response(
    endpoint: str,
    status_code: int,
    body: dict[str, Any],
) -> RealitySignal:
    """Convenience: ingest an API response as a reality signal.

    Classifies based on status code and body content.
    """
    primitives: set[PrimitiveTag] = {PrimitiveTag.SIGNAL}

    if status_code >= 200 and status_code < 300:
        primitives.add(PrimitiveTag.OUTCOME)
    elif status_code >= 400:
        primitives.add(PrimitiveTag.FEEDBACK)
        primitives.add(PrimitiveTag.CONSTRAINT)

    # Classify body text if present
    body_text = str(body)
    primitives.update(_classify_text(body_text))

    signal = RealitySignal(
        raw=f"API {endpoint} -> {status_code}",
        source="api",
        primitives=primitives,
        timestamp=time.time(),
        metadata={
            "endpoint": endpoint,
            "status_code": status_code,
            "body": body,
        },
    )

    _store_signal(signal)
    return signal


__all__ = [
    "RealitySignal",
    "ingest_signal",
    "ingest_metric",
    "ingest_api_response",
    "get_signal_history",
    "clear_signal_history",
]
