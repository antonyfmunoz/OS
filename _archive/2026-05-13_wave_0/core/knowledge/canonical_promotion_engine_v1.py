"""Canonical Promotion Engine v1.

Governs promotion of instance knowledge to canonical tier.
Promotion requires corroboration threshold and operator approval.
The engine CANNOT auto-promote — all promotion is operator-governed.

UMH substrate subsystem. Phase 96.8CB.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.knowledge.knowledge_fabric_contracts_v1 import (
    KnowledgePromotionReceipt,
    CanonicalPromotionState,
    _now_iso,
)

CORROBORATION_THRESHOLD = 2
MAX_PENDING_PROMOTIONS = 50


class CanonicalPromotionEngine:
    """Governs knowledge promotion to canonical tier."""

    def __init__(self, state_dir: str | Path | None = None) -> None:
        self._pending: list[KnowledgePromotionReceipt] = []
        self._completed: list[KnowledgePromotionReceipt] = []
        self._total_promoted = 0
        self._total_denied = 0
        self._corroboration_threshold = CORROBORATION_THRESHOLD

    def request_promotion(
        self,
        node_id: str,
        from_tier: str,
        corroboration_count: int,
        promoted_by: str = "operator",
    ) -> KnowledgePromotionReceipt:
        if promoted_by != "operator":
            raise ValueError(
                f"Only operator can request promotion. Got: {promoted_by}"
            )

        receipt = KnowledgePromotionReceipt(
            node_id=node_id,
            from_tier=from_tier,
            to_tier="canonical",
            promoted_by=promoted_by,
            corroboration_count=corroboration_count,
            approved=False,
        )

        if len(self._pending) < MAX_PENDING_PROMOTIONS:
            self._pending.append(receipt)

        return receipt

    def approve_promotion(self, receipt_id: str) -> KnowledgePromotionReceipt | None:
        for i, receipt in enumerate(self._pending):
            if receipt.receipt_id == receipt_id:
                if receipt.corroboration_count < self._corroboration_threshold:
                    return None
                receipt.approved = True
                self._pending.pop(i)
                self._completed.append(receipt)
                self._total_promoted += 1
                return receipt
        return None

    def deny_promotion(self, receipt_id: str) -> KnowledgePromotionReceipt | None:
        for i, receipt in enumerate(self._pending):
            if receipt.receipt_id == receipt_id:
                receipt.approved = False
                self._pending.pop(i)
                self._completed.append(receipt)
                self._total_denied += 1
                return receipt
        return None

    def get_pending(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._pending]

    def get_promotion_state(self) -> dict[str, Any]:
        state = CanonicalPromotionState(
            pending_promotions=len(self._pending),
            total_promoted=self._total_promoted,
            total_denied=self._total_denied,
            corroboration_threshold=self._corroboration_threshold,
        )
        return state.to_dict()

    def get_stats(self) -> dict[str, object]:
        return {
            "pending_promotions": len(self._pending),
            "total_promoted": self._total_promoted,
            "total_denied": self._total_denied,
            "corroboration_threshold": self._corroboration_threshold,
        }
