"""Duplicate Subsystem Detection Engine v1.

Detects duplicate orchestrators, runtimes, memory systems,
ingestion systems, workflow coordinators, topology engines,
governance layers. Classifies as canonical/deprecated/quarantined/
experimental/dead/conflicting.

UMH substrate subsystem. Phase 96.8CO.
"""

from __future__ import annotations

from typing import Any

from core.convergence.repository_topology_contracts_v1 import (
    DuplicateSubsystemState,
    SubsystemClassification,
    _now_iso,
    _deterministic_id,
)


MAX_DETECTIONS = 200

SUBSYSTEM_TYPES = [
    "orchestrator",
    "runtime",
    "memory",
    "ingestion",
    "workflow",
    "topology",
    "governance",
    "cognition",
]


class DuplicateSubsystemDetectionEngine:
    """Detects and classifies duplicate subsystems."""

    def __init__(self) -> None:
        self._detections: list[DuplicateSubsystemState] = []

    def detect_duplicate(
        self,
        subsystem_type: str,
        instances_found: list[str],
        canonical_instance: str = "",
        classification: str = "canonical",
    ) -> dict[str, Any]:
        if len(self._detections) >= MAX_DETECTIONS:
            raise ValueError("Max detections reached")

        state = DuplicateSubsystemState(
            detection_id=_deterministic_id("dupss-", subsystem_type, _now_iso()),
            subsystem_type=subsystem_type,
            instances_found=instances_found,
            canonical_instance=canonical_instance,
            classification=classification,
        )
        self._detections.append(state)
        return state.to_dict()

    def get_duplicates(self) -> list[dict[str, Any]]:
        return [
            d.to_dict() for d in self._detections
            if len(d.instances_found) > 1
        ]

    def get_by_classification(self, classification: str) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._detections if d.classification == classification]

    def no_duplicates(self) -> bool:
        return all(len(d.instances_found) <= 1 for d in self._detections) if self._detections else True

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_detections": len(self._detections),
            "duplicates_found": len(self.get_duplicates()),
            "no_duplicates": self.no_duplicates(),
        }
