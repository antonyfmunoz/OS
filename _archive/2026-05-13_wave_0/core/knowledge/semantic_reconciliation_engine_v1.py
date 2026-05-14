"""Semantic Reconciliation Engine v1.

Reconciles instance knowledge against canonical knowledge.
Detects conflicts, measures corroboration, tracks lineage.
Never fabricates reconciliation outcomes.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import (
    KnowledgeConflictState,
    SemanticLineageState,
    ConflictSeverity,
    _new_id,
    _now_iso,
)

MAX_PENDING_RECONCILIATIONS = 50
MAX_CONFLICTS = 100
MAX_LINEAGE_ENTRIES = 100


class SemanticReconciliationEngine:
    """Reconciles instance knowledge with canonical knowledge."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._conflicts: list[KnowledgeConflictState] = []
        self._lineage: list[SemanticLineageState] = []
        self._reconciliations: list[dict[str, Any]] = []
        self._total_reconciliations = 0
        self._total_conflicts_detected = 0

    def reconcile(
        self,
        instance_node_id: str,
        canonical_node_id: str,
        instance_content_hash: str = "",
        canonical_content_hash: str = "",
    ) -> dict[str, Any]:
        is_conflict = bool(
            instance_content_hash
            and canonical_content_hash
            and instance_content_hash != canonical_content_hash
        )

        reconciliation_id = _new_id("recon")
        raw = f"{reconciliation_id}:{instance_node_id}:{canonical_node_id}"
        reconciliation_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

        result: dict[str, Any] = {
            "reconciliation_id": reconciliation_id,
            "instance_node_id": instance_node_id,
            "canonical_node_id": canonical_node_id,
            "conflict_detected": is_conflict,
            "reconciliation_hash": reconciliation_hash,
            "timestamp": _now_iso(),
        }

        if is_conflict:
            conflict = KnowledgeConflictState(
                node_a=instance_node_id,
                node_b=canonical_node_id,
                conflict_type="content_mismatch",
                severity="medium",
            )
            if len(self._conflicts) < MAX_CONFLICTS:
                self._conflicts.append(conflict)
            self._total_conflicts_detected += 1
            result["conflict_id"] = conflict.conflict_id

        lineage = SemanticLineageState(
            node_id=instance_node_id,
            transitions=[{
                "action": "reconciled",
                "against": canonical_node_id,
                "timestamp": _now_iso(),
            }],
            current_tier="reconciled" if not is_conflict else "instance",
        )
        if len(self._lineage) < MAX_LINEAGE_ENTRIES:
            self._lineage.append(lineage)

        if len(self._reconciliations) < MAX_PENDING_RECONCILIATIONS:
            self._reconciliations.append(result)
        self._total_reconciliations += 1

        return result

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
    ) -> KnowledgeConflictState | None:
        for conflict in self._conflicts:
            if conflict.conflict_id == conflict_id:
                conflict.resolved = True
                conflict.resolution = resolution
                return conflict
        return None

    def get_conflicts(self, unresolved_only: bool = False) -> list[dict[str, Any]]:
        conflicts = self._conflicts
        if unresolved_only:
            conflicts = [c for c in conflicts if not c.resolved]
        return [c.to_dict() for c in conflicts]

    def get_lineage(self, node_id: str) -> list[dict[str, Any]]:
        return [
            ln.to_dict() for ln in self._lineage if ln.node_id == node_id
        ]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_reconciliations": self._total_reconciliations,
            "total_conflicts_detected": self._total_conflicts_detected,
            "active_conflicts": sum(1 for c in self._conflicts if not c.resolved),
            "resolved_conflicts": sum(1 for c in self._conflicts if c.resolved),
            "lineage_entries": len(self._lineage),
        }
