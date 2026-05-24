"""AutoReconciler — closes the gap between promoted memories and canonical store.

Called automatically after each successful promotion. Runs the
reconciliation engine against the single new memory, applies the
decision, and persists the receipt. No manual script needed.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from substrate.memory.candidate_generator import MemoryCandidate
from substrate.state.memory.contracts.canonical_memory_store_v1 import (
    CanonicalMemoryStore,
)
from substrate.state.memory.contracts.canonical_memory_reconciliation_engine_v1 import (
    ReconciliationAction,
    ReconciliationEngine,
)
from substrate.state.memory.contracts.memory_conflict_governance_v1 import (
    ConflictGovernance,
)

logger = logging.getLogger(__name__)


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class AutoReconciler:
    """Automatically reconciles promoted memories into canonical store.

    Wired into the execution pipeline after promotion. Each promoted
    memory is immediately reconciled against the canonical store —
    new memories are promoted, duplicates are skipped, conflicts are
    surfaced for governance.
    """

    def __init__(
        self,
        store: CanonicalMemoryStore | None = None,
        engine: ReconciliationEngine | None = None,
        conflict_gov: ConflictGovernance | None = None,
    ) -> None:
        self._store = store or CanonicalMemoryStore()
        self._engine = engine or ReconciliationEngine()
        self._conflict_gov = conflict_gov or ConflictGovernance()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self._engine.load_existing_memories()
            self._loaded = True

    def reconcile_promoted(
        self,
        candidate: MemoryCandidate,
        promotion_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Reconcile a single promoted memory into canonical store.

        Returns summary of what happened: promoted_to_canonical, skipped,
        strengthened, or conflicted.
        """
        if not promotion_result.get("promoted"):
            return {"action": "skip", "reason": "not promoted"}

        self._ensure_loaded()

        store_candidate = {
            "candidate_id": candidate.candidate_id,
            "content": candidate.content,
            "label": candidate.content[:80],
            "memory_type": "instance",
            "primitive_type": _infer_primitive_type(candidate),
            "confidence": candidate.confidence,
            "source_document_id": f"pipeline-{candidate.source_trace_id}",
            "source_content_hash": _content_hash(candidate.content),
            "source_decomposition_id": candidate.candidate_id,
            "classification_reason": candidate.reason,
        }

        decision = self._engine.reconcile_candidate(store_candidate)

        if decision.action == ReconciliationAction.NEW:
            entry, receipt = self._store.promote_candidate(
                store_candidate,
                reason="auto-reconciliation:new",
                promoter="auto_reconciler_v1",
            )
            self._engine._register_identity(entry, store_candidate)
            logger.info(
                "Memory auto-promoted to canonical: %s (%s)",
                entry.memory_id,
                candidate.content[:60],
            )
            return {
                "action": "promoted_to_canonical",
                "memory_id": entry.memory_id,
                "receipt_id": receipt.receipt_id,
            }

        elif decision.action == ReconciliationAction.DUPLICATE_SKIP:
            logger.debug(
                "Memory duplicate skipped: %s matches %s",
                candidate.candidate_id,
                decision.matched_memory_id,
            )
            return {
                "action": "duplicate_skip",
                "matched_memory_id": decision.matched_memory_id,
            }

        elif decision.action == ReconciliationAction.STRENGTHEN:
            self._engine._apply_strengthening(decision)
            logger.info(
                "Memory strengthened: %s (strength %d → %d)",
                decision.matched_memory_id,
                decision.strength_before,
                decision.strength_after,
            )
            return {
                "action": "strengthened",
                "matched_memory_id": decision.matched_memory_id,
                "strength": decision.strength_after,
            }

        elif decision.action == ReconciliationAction.CONFLICT:
            self._conflict_gov.record_conflict(
                store_candidate,
                {"memory_id": decision.matched_memory_id, "content": ""},
                receipt_id="auto-reconciliation",
            )
            logger.warning(
                "Memory conflict detected: %s vs %s",
                candidate.candidate_id,
                decision.matched_memory_id,
            )
            return {
                "action": "conflict",
                "matched_memory_id": decision.matched_memory_id,
            }

        return {"action": decision.action.value}

    def invalidate_cache(self) -> None:
        """Force reload of existing memories on next reconciliation."""
        self._loaded = False


def _infer_primitive_type(candidate: MemoryCandidate) -> str:
    """Infer primitive type from candidate tags and content."""
    tags = set(candidate.tags)
    content_lower = candidate.content.lower()

    if "feedback" in tags or "feedback" in content_lower:
        return "feedback"
    if "outcome" in tags:
        return "outcome"
    if "error" in content_lower or "failure" in content_lower:
        return "signal"
    if "goal" in content_lower or "target" in content_lower:
        return "goal"
    if any(w in content_lower for w in ("rule", "constraint", "must", "never")):
        return "constraint"
    return "state"
