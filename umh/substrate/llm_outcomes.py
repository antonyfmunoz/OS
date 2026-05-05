"""
Outcome-aware learning layer for LLM planning.

Records execution outcomes AFTER the scheduler processes events,
computes aggregate statistics, and produces deterministic summaries
for prompt augmentation.  This is a forward-looking observational
layer — it never affects validation, selection policy, or replay.

Design constraints:
- EventOutcome is frozen.  Immutable once created.
- OutcomeStore is thread-safe via threading.Lock.
- Bounded history per event_type (configurable).
- Summary output is deterministic: sorted by event_type,
  no timestamps, no non-deterministic values.
- Outcome data flows into prompts ONLY.  Never into:
  - Validation
  - Selection policy
  - Replay logic
"""

from __future__ import annotations

import hashlib
import sys
import threading
from collections import Counter
from dataclasses import dataclass
from typing import Any

_LOG_PREFIX = "[substrate.llm_outcomes]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── Data model ────────────────────────────────────────────────────


@dataclass(frozen=True)
class EventOutcome:
    """Immutable record of what happened after the scheduler executed an event.

    Attributes:
        proposal_id: Ties back to the LLMDecisionRecord that proposed this event.
        event_type: The event type that was executed.
        success: True if the handler completed without exception.
        latency_ms: Wall-clock handler execution time, or None if not measured.
        error_type: Exception class name on failure, or None on success.
        timestamp: ISO 8601 UTC timestamp of outcome recording.
    """

    proposal_id: str
    event_type: str
    success: bool
    latency_ms: int | None
    error_type: str | None
    timestamp: str


# ─── Stats computation ──────────────────────────────────────────────


@dataclass(frozen=True)
class EventTypeStats:
    """Aggregate statistics for a single event type.

    Computed from the most recent N outcomes (bounded by history limit).
    All fields are deterministic given the same input sequence.
    """

    event_type: str
    total: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_latency_ms: int | None
    common_failures: tuple[str, ...]

    def to_summary_dict(self) -> dict[str, Any]:
        """Deterministic dict for prompt inclusion."""
        d: dict[str, Any] = {
            "success_rate": round(self.success_rate, 2),
        }
        if self.avg_latency_ms is not None:
            d["avg_latency_ms"] = self.avg_latency_ms
        if self.common_failures:
            d["common_failures"] = list(self.common_failures)
        return d


def _compute_stats(event_type: str, outcomes: list[EventOutcome]) -> EventTypeStats:
    """Compute aggregate stats from a list of outcomes for one event type."""
    total = len(outcomes)
    if total == 0:
        return EventTypeStats(
            event_type=event_type,
            total=0,
            success_count=0,
            failure_count=0,
            success_rate=0.0,
            avg_latency_ms=None,
            common_failures=(),
        )

    successes = sum(1 for o in outcomes if o.success)
    failures = total - successes

    # Latency: only from outcomes that have it
    latencies = [o.latency_ms for o in outcomes if o.latency_ms is not None]
    avg_latency = int(sum(latencies) / len(latencies)) if latencies else None

    # Failure modes: top 3 by frequency, deterministic ordering
    error_counter: Counter[str] = Counter()
    for o in outcomes:
        if o.error_type is not None:
            error_counter[o.error_type] += 1
    # Sort by (-count, name) for determinism
    common = tuple(
        name
        for name, _ in sorted(error_counter.items(), key=lambda x: (-x[1], x[0]))[:3]
    )

    return EventTypeStats(
        event_type=event_type,
        total=total,
        success_count=successes,
        failure_count=failures,
        success_rate=successes / total,
        avg_latency_ms=avg_latency,
        common_failures=common,
    )


# ─── Outcome store ──────────────────────────────────────────────────


class OutcomeStore:
    """Thread-safe, bounded store for execution outcomes.

    Keyed by event_type.  Each event_type retains at most
    `max_history` outcomes (FIFO eviction).

    Thread-safety: single threading.Lock guards all mutations.
    Same pattern as ReplayableStrategy's replay store.
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._max_history = max_history
        self._store: dict[str, list[EventOutcome]] = {}
        self._lock = threading.Lock()

    @property
    def max_history(self) -> int:
        return self._max_history

    def record_outcome(self, outcome: EventOutcome) -> None:
        """Record an execution outcome. Thread-safe, bounded."""
        with self._lock:
            outcomes = self._store.get(outcome.event_type)
            if outcomes is None:
                outcomes = []
                self._store[outcome.event_type] = outcomes
            outcomes.append(outcome)
            # FIFO eviction
            if len(outcomes) > self._max_history:
                del outcomes[: len(outcomes) - self._max_history]

    def get_event_stats(self, event_type: str) -> EventTypeStats:
        """Compute stats for a single event type. Thread-safe."""
        with self._lock:
            outcomes = list(self._store.get(event_type, []))
        return _compute_stats(event_type, outcomes)

    def get_all_stats(self) -> dict[str, EventTypeStats]:
        """Compute stats for all recorded event types. Thread-safe.

        Returns dict sorted by event_type for determinism.
        """
        with self._lock:
            snapshot = {et: list(outcomes) for et, outcomes in self._store.items()}
        return {
            et: _compute_stats(et, outcomes)
            for et, outcomes in sorted(snapshot.items())
        }

    def build_outcome_summary(self) -> str:
        """Build deterministic outcome summary string for prompt inclusion.

        Format matches the EVENT PERFORMANCE section spec.
        Deterministic: sorted by event_type, no timestamps,
        no non-deterministic values.

        Returns empty string if no outcomes recorded.
        """
        all_stats = self.get_all_stats()
        if not all_stats:
            return ""

        lines: list[str] = []
        for event_type, stats in all_stats.items():
            if stats.total == 0:
                continue
            lines.append(f"- {event_type}:")
            lines.append(f"  success_rate: {round(stats.success_rate, 2)}")
            failure_rate = round(1.0 - stats.success_rate, 2)
            lines.append(f"  failure_rate: {failure_rate}")
            if stats.avg_latency_ms is not None:
                lines.append(f"  avg_latency_ms: {stats.avg_latency_ms}")
            if stats.common_failures:
                lines.append(f"  most_common_error: {stats.common_failures[0]}")
                if len(stats.common_failures) > 1:
                    lines.append(f"  other_failures: {list(stats.common_failures[1:])}")
        return "\n".join(lines)

    def build_outcome_summary_hash(self) -> str:
        """Deterministic hash of the outcome summary.

        Used to include in composite prompt hash so that
        same state + same outcomes = same prompt hash.
        """
        summary = self.build_outcome_summary()
        return hashlib.sha256(summary.encode("utf-8")).hexdigest()[:16]

    def outcome_count(self, event_type: str | None = None) -> int:
        """Count stored outcomes. For testing/diagnostics."""
        with self._lock:
            if event_type is not None:
                return len(self._store.get(event_type, []))
            return sum(len(v) for v in self._store.values())

    def clear(self) -> None:
        """Clear all outcomes. For testing."""
        with self._lock:
            self._store.clear()
