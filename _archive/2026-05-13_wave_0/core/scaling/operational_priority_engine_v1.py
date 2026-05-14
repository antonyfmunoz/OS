"""Operational Priority Engine v1.

Priority classes: critical, high, standard, deferred, suspended.
Supports deterministic arbitration, explicit operator overrides,
bounded reprioritization.

Prevents: hidden priority mutation, autonomous reprioritization.

UMH substrate subsystem. Phase 96.8BY.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.scaling.operational_scaling_contracts_v1 import (
    OperationalPriorityState,
    PriorityClass,
    _content_hash,
    _now_iso,
)


PRIORITY_ORDER: list[str] = [
    PriorityClass.CRITICAL.value,
    PriorityClass.HIGH.value,
    PriorityClass.STANDARD.value,
    PriorityClass.DEFERRED.value,
    PriorityClass.SUSPENDED.value,
]


class OperationalPriorityEngine:
    """Manages deterministic priority arbitration."""

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/scaling",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._priorities: dict[str, OperationalPriorityState] = {}
        self._arbitration_log: list[dict[str, Any]] = []
        self._total_arbitrations: int = 0

    def set_priority(
        self,
        item_id: str,
        priority_class: str = PriorityClass.STANDARD.value,
        set_by: str = "operator",
    ) -> OperationalPriorityState:
        state = OperationalPriorityState(
            item_id=item_id,
            priority_class=priority_class,
            set_by=set_by,
        )
        self._priorities[item_id] = state
        self._persist_priority(state)
        return state

    def get_priority(self, item_id: str) -> OperationalPriorityState | None:
        return self._priorities.get(item_id)

    def override_priority(
        self,
        item_id: str,
        new_priority: str,
        overridden_by: str = "operator",
    ) -> bool:
        state = self._priorities.get(item_id)
        if not state:
            return False

        old = state.priority_class
        state.priority_class = new_priority
        state.set_by = overridden_by
        state.override_allowed = True
        state.timestamp = _now_iso()

        self._log_arbitration(item_id, old, new_priority, overridden_by)
        self._persist_priority(state)
        return True

    def arbitrate(self, item_ids: list[str]) -> list[str]:
        items_with_priority = []
        for item_id in item_ids:
            state = self._priorities.get(item_id)
            if state and state.priority_class != PriorityClass.SUSPENDED.value:
                rank = PRIORITY_ORDER.index(state.priority_class)
                items_with_priority.append((rank, item_id))
            elif not state:
                rank = PRIORITY_ORDER.index(PriorityClass.STANDARD.value)
                items_with_priority.append((rank, item_id))

        items_with_priority.sort(key=lambda x: x[0])
        result = [item_id for _, item_id in items_with_priority]

        self._total_arbitrations += 1
        self._log_arbitration_result(item_ids, result)
        return result

    def get_priority_hash(self) -> str:
        return _content_hash(self._arbitration_log)

    def _log_arbitration(
        self,
        item_id: str,
        old_priority: str,
        new_priority: str,
        by: str,
    ) -> None:
        entry = {
            "type": "override",
            "item_id": item_id,
            "old": old_priority,
            "new": new_priority,
            "by": by,
            "timestamp": _now_iso(),
        }
        self._arbitration_log.append(entry)

    def _log_arbitration_result(
        self,
        input_ids: list[str],
        output_ids: list[str],
    ) -> None:
        entry = {
            "type": "arbitration",
            "input": input_ids,
            "output": output_ids,
            "timestamp": _now_iso(),
        }
        self._arbitration_log.append(entry)

    def _persist_priority(self, state: OperationalPriorityState) -> None:
        path = self._state_dir / "priority_decisions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_items": len(self._priorities),
            "total_arbitrations": self._total_arbitrations,
        }
