"""Attention Aggregation Runtime — Campaign 18.2.

Merges attention items from 4 sources into one ranked queue.
Pure collection + normalization + ranking. No business logic.

Reuses AttentionItem from substrate.operator.operator_attention_engine.
Reuses _CATEGORY_PRIORITY and _SEVERITY_PRIORITY for ranking.

Target: <250 LOC. If larger, logic is leaking upward.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ─────────────────────────────────────────────────────────────────


@dataclass
class AttentionQueueSnapshot:
    items: list[dict[str, Any]] = field(default_factory=list)
    total_count: int = 0
    critical_count: int = 0
    top_category: str = ""
    generated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": self.items,
            "total_count": self.total_count,
            "critical_count": self.critical_count,
            "top_category": self.top_category,
            "generated_at": self.generated_at,
        }


# ── Ranking constants (mirrored from OperatorAttentionEngine) ────────

_CATEGORY_PRIORITY = {
    "failure": 0,
    "approval": 1,
    "misalignment": 2,
    "blocked": 3,
    "recovery": 4,
    "drift": 5,
    "change": 6,
}

_SEVERITY_PRIORITY = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


# ── Runtime ─────────────────────────────────────────────────────────


class AttentionAggregationRuntime:
    """Merges attention from 4 sources into one ranked queue.

    Sources:
    - OperatorAttentionEngine (Gate 4): ranked priority items
    - OrganismStateRuntime (C16.1): attention_items from organism health
    - GovernedExecutionRuntime (C16.0): execution blockers
    - OrganismPortfolioRuntime (C15.3): subsystem health degradations
    """

    def __init__(
        self,
        attention_engine: Any | None = None,
        organism_state: Any | None = None,
        governed_execution: Any | None = None,
        organism_portfolio: Any | None = None,
    ) -> None:
        self._attention_engine_dep = attention_engine
        self._organism_state_dep = organism_state
        self._governed_execution_dep = governed_execution
        self._organism_portfolio_dep = organism_portfolio

    # ── Lazy subsystem access ────────────────────────────────────

    @property
    def _attention_engine(self) -> Any:
        if self._attention_engine_dep is None:
            try:
                from substrate.operator.operator_attention_engine import (
                    OperatorAttentionEngine,
                )
                self._attention_engine_dep = OperatorAttentionEngine()
            except Exception:
                logger.debug("OperatorAttentionEngine unavailable")
        return self._attention_engine_dep

    @property
    def _organism_state(self) -> Any:
        if self._organism_state_dep is None:
            try:
                from substrate.organism.organism_state_runtime import (
                    OrganismStateRuntime,
                )
                self._organism_state_dep = OrganismStateRuntime()
            except Exception:
                logger.debug("OrganismStateRuntime unavailable")
        return self._organism_state_dep

    @property
    def _governed_execution(self) -> Any:
        if self._governed_execution_dep is None:
            try:
                from substrate.organism.governed_execution_runtime import (
                    GovernedExecutionRuntime,
                )
                self._governed_execution_dep = GovernedExecutionRuntime()
            except Exception:
                logger.debug("GovernedExecutionRuntime unavailable")
        return self._governed_execution_dep

    @property
    def _organism_portfolio(self) -> Any:
        if self._organism_portfolio_dep is None:
            try:
                from substrate.organism.organism_portfolio_runtime import (
                    OrganismPortfolioRuntime,
                )
                self._organism_portfolio_dep = OrganismPortfolioRuntime()
            except Exception:
                logger.debug("OrganismPortfolioRuntime unavailable")
        return self._organism_portfolio_dep

    # ── Helpers ──────────────────────────────────────────────────

    def _safe_call(self, obj: Any, method: str, *args: Any) -> Any:
        if obj is None:
            return None
        try:
            fn = getattr(obj, method, None)
            return fn(*args) if fn else None
        except Exception:
            logger.debug("safe_call %s.%s failed", type(obj).__name__, method)
            return None

    def _normalize_item(self, raw: dict[str, Any], source: str) -> dict[str, Any]:
        return {
            "priority": raw.get("priority", 99),
            "category": raw.get("category", "change"),
            "severity": raw.get("severity", "medium"),
            "title": raw.get("title", ""),
            "description": raw.get("description", ""),
            "action_hint": raw.get("action_hint", ""),
            "source_id": raw.get("source_id", ""),
            "source_system": raw.get("source_system", source),
            "capability_link": raw.get("capability_link", ""),
            "timestamp": raw.get("timestamp", time.time()),
        }

    def _rank_key(self, item: dict[str, Any]) -> tuple[int, int, float]:
        cat = _CATEGORY_PRIORITY.get(item.get("category", "change"), 99)
        sev = _SEVERITY_PRIORITY.get(item.get("severity", "medium"), 99)
        ts = -item.get("timestamp", 0)
        return (cat, sev, ts)

    def _collect_from_attention_engine(self) -> list[dict[str, Any]]:
        result = self._safe_call(self._attention_engine, "attention_queue")
        if not result:
            return []
        items = []
        for item in result:
            d = item.to_dict() if hasattr(item, "to_dict") else item
            items.append(self._normalize_item(d, "attention_engine"))
        return items

    def _collect_from_organism_state(self) -> list[dict[str, Any]]:
        snap = self._safe_call(self._organism_state, "snapshot")
        if snap is None:
            return []
        d = snap.to_dict() if hasattr(snap, "to_dict") else {}
        items = []
        for raw in d.get("attention_items", []):
            items.append(self._normalize_item(raw, "organism_state"))
        return items

    def _collect_from_governed_execution(self) -> list[dict[str, Any]]:
        assess = self._safe_call(self._governed_execution, "assess")
        if assess is None:
            return []
        d = assess.to_dict() if hasattr(assess, "to_dict") else {}
        items = []
        for blocker in d.get("top_blockers", []):
            items.append(self._normalize_item({
                "category": "blocked",
                "severity": "high",
                "title": blocker.get("blocker", "Execution blocked"),
                "description": blocker.get("detail", ""),
                "source_system": "governed_execution",
            }, "governed_execution"))
        if d.get("pending_approval_count", 0) > 0:
            items.append(self._normalize_item({
                "category": "approval",
                "severity": "medium",
                "title": f"{d['pending_approval_count']} pending approvals",
                "source_system": "governed_execution",
            }, "governed_execution"))
        return items

    def _collect_from_organism_portfolio(self) -> list[dict[str, Any]]:
        snap = self._safe_call(self._organism_portfolio, "snapshot")
        if snap is None:
            return []
        d = snap.to_dict() if hasattr(snap, "to_dict") else {}
        items = []
        for warning in d.get("drift_warnings", []):
            items.append(self._normalize_item({
                "category": "drift",
                "severity": warning.get("severity", "low"),
                "title": warning.get("description", "Subsystem drift"),
                "source_system": "organism_portfolio",
            }, "organism_portfolio"))
        return items

    # ── Public API ───────────────────────────────────────────────

    def queue(self) -> AttentionQueueSnapshot:
        all_items: list[dict[str, Any]] = []
        all_items.extend(self._collect_from_attention_engine())
        all_items.extend(self._collect_from_organism_state())
        all_items.extend(self._collect_from_governed_execution())
        all_items.extend(self._collect_from_organism_portfolio())

        all_items.sort(key=self._rank_key)

        critical = sum(1 for i in all_items if i.get("severity") == "critical")
        top_cat = all_items[0].get("category", "") if all_items else ""

        return AttentionQueueSnapshot(
            items=all_items,
            total_count=len(all_items),
            critical_count=critical,
            top_category=top_cat,
            generated_at=time.time(),
        )

    def count(self) -> dict[str, int]:
        q = self.queue()
        return {
            "total": q.total_count,
            "critical": q.critical_count,
        }
