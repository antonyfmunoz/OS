"""Conceptual Integrity Engine v1.

Validates conceptual integrity across the knowledge fabric.
Measures coherence, detects ontology drift, enforces boundaries.
Never auto-corrects — reports integrity state for operator review.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import (
    ConceptualIntegrityState,
    _now_iso,
)

INTEGRITY_THRESHOLD = 0.7
DRIFT_THRESHOLD = 0.3


class ConceptualIntegrityEngine:
    """Validates knowledge fabric conceptual integrity."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._canonical_count = 0
        self._instance_count = 0
        self._conflict_count = 0
        self._total_validations = 0
        self._drift_events: list[dict[str, Any]] = []

    def validate(
        self,
        canonical_count: int = 0,
        instance_count: int = 0,
        conflict_count: int = 0,
    ) -> dict[str, Any]:
        self._canonical_count = canonical_count
        self._instance_count = instance_count
        self._conflict_count = conflict_count
        total = canonical_count + instance_count

        if total == 0:
            score = 1.0
        else:
            conflict_ratio = conflict_count / total
            canonical_ratio = canonical_count / total if total > 0 else 0.0
            score = max(0.0, min(1.0, (1.0 - conflict_ratio) * (0.5 + 0.5 * canonical_ratio)))

        coherent = score >= INTEGRITY_THRESHOLD

        state = ConceptualIntegrityState(
            total_nodes=total,
            canonical_count=canonical_count,
            instance_count=instance_count,
            conflict_count=conflict_count,
            integrity_score=round(score, 4),
            coherent=coherent,
        )
        self._total_validations += 1

        return state.to_dict()

    def detect_drift(
        self,
        concept: str,
        expected_tier: str,
        actual_tier: str,
    ) -> dict[str, Any] | None:
        if expected_tier == actual_tier:
            return None

        drift = {
            "concept": concept,
            "expected_tier": expected_tier,
            "actual_tier": actual_tier,
            "drift_detected": True,
            "timestamp": _now_iso(),
        }
        self._drift_events.append(drift)
        return drift

    def get_drift_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._drift_events[-limit:]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_validations": self._total_validations,
            "canonical_count": self._canonical_count,
            "instance_count": self._instance_count,
            "conflict_count": self._conflict_count,
            "drift_events": len(self._drift_events),
        }
