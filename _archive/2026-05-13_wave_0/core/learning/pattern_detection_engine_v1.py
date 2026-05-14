"""Pattern Detection Engine v1.

Detects recurring patterns from learning signals:
  repeated failures, corrections, denials, successful routes,
  retrieval misses, workflow bottlenecks, environment instability.

Bounded detection. Cannot execute. Reports patterns only.

UMH substrate subsystem. Phase 96.8CC.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from core.learning.adaptive_learning_contracts_v1 import (
    PatternCandidate,
    LearningConfidenceState,
    PatternType,
    _new_id,
    _now_iso,
)

MAX_PATTERNS = 100
MAX_SIGNALS_PER_PATTERN = 50
OCCURRENCE_THRESHOLD = 3
KNOWN_PATTERN_TYPES = {pt.value for pt in PatternType}

SOURCE_TO_PATTERN: dict[str, str] = {
    "workflow_failure": "repeated_failure",
    "operator_correction": "repeated_correction",
    "action_denied": "repeated_denial",
    "workflow_success": "recurring_success_route",
    "reconciliation_result": "recurring_retrieval_miss",
    "scaling_pressure": "recurring_workflow_bottleneck",
    "resilience_event": "recurring_environment_instability",
}


class PatternDetectionEngine:
    """Detects recurring patterns from learning signals."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._patterns: list[PatternCandidate] = []
        self._counters: dict[str, dict[str, int]] = {}
        self._signal_buckets: dict[str, list[str]] = {}
        self._total_detected = 0

    def ingest_signal(
        self,
        signal_id: str,
        source: str,
        content: str,
    ) -> PatternCandidate | None:
        pattern_type = SOURCE_TO_PATTERN.get(source)
        if pattern_type is None:
            return None

        key = f"{pattern_type}:{content}"

        if key not in self._counters:
            self._counters[key] = {"count": 0, "pattern_type": 0}
            self._signal_buckets[key] = []

        self._counters[key]["count"] += 1
        count = self._counters[key]["count"]

        if len(self._signal_buckets[key]) < MAX_SIGNALS_PER_PATTERN:
            self._signal_buckets[key].append(signal_id)

        if count >= OCCURRENCE_THRESHOLD:
            existing = self._find_pattern(key)
            if existing:
                existing.occurrence_count = count
                existing.confidence = min(1.0, count / 10.0)
                if signal_id not in existing.signal_ids:
                    if len(existing.signal_ids) < MAX_SIGNALS_PER_PATTERN:
                        existing.signal_ids.append(signal_id)
                return existing

            if len(self._patterns) >= MAX_PATTERNS:
                return None

            raw = f"{pattern_type}:{content}"
            pattern_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

            candidate = PatternCandidate(
                pattern_type=pattern_type,
                description=content,
                occurrence_count=count,
                confidence=min(1.0, count / 10.0),
                signal_ids=list(self._signal_buckets[key]),
                pattern_hash=pattern_hash,
            )
            self._patterns.append(candidate)
            self._total_detected += 1
            return candidate

        return None

    def _find_pattern(self, key: str) -> PatternCandidate | None:
        parts = key.split(":", 1)
        if len(parts) != 2:
            return None
        ptype, desc = parts
        for p in self._patterns:
            if p.pattern_type == ptype and p.description == desc:
                return p
        return None

    def get_patterns(self, limit: int = 50) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._patterns[-limit:]]

    def get_patterns_by_type(
        self,
        pattern_type: str,
    ) -> list[dict[str, Any]]:
        return [
            p.to_dict()
            for p in self._patterns
            if p.pattern_type == pattern_type
        ]

    def get_high_confidence(
        self,
        threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        return [
            p.to_dict()
            for p in self._patterns
            if p.confidence >= threshold
        ]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_detected": self._total_detected,
            "active_patterns": len(self._patterns),
            "tracked_keys": len(self._counters),
            "patterns_by_type": {
                pt: sum(1 for p in self._patterns if p.pattern_type == pt)
                for pt in KNOWN_PATTERN_TYPES
            },
        }
