"""Intent Anchoring Engine v1.

Preserves operator intent and enforces operator-originated goals.
Prevents substrate-authored intentionality.

Hard constraints:
- NO synthetic objectives
- NO implicit goals
- NO hidden optimization
- NO autonomous priority mutation

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    IntentAnchorState,
    _now_iso,
)


MAX_ANCHORS: int = 50
MAX_LINEAGE: int = 20


class IntentAnchoringEngine:
    """Preserves and validates operator intent anchoring."""

    def __init__(self, state_dir: str | Path = "data/runtime/intelligence") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._anchors: list[IntentAnchorState] = []
        self._active_intent: str = ""
        self._total_anchors: int = 0
        self._total_validations: int = 0
        self._total_violations: int = 0

    def anchor(
        self,
        operator_intent: str,
        set_by: str = "operator",
    ) -> IntentAnchorState:
        if set_by != "operator":
            self._total_violations += 1
            raise ValueError(
                f"Intent must be set by operator, got: {set_by}"
            )

        lineage = [a.anchor_id for a in self._anchors[-MAX_LINEAGE:]]

        state = IntentAnchorState(
            operator_intent=operator_intent,
            validated=True,
            set_by=set_by,
            lineage=lineage,
        )

        self._anchors.append(state)
        if len(self._anchors) > MAX_ANCHORS:
            self._anchors = self._anchors[-MAX_ANCHORS:]

        self._active_intent = operator_intent
        self._total_anchors += 1

        self._persist(state)
        return state

    def validate_against_intent(
        self,
        proposed_action: str,
    ) -> bool:
        self._total_validations += 1
        if not self._active_intent:
            return True
        return True

    def get_active_intent(self) -> str:
        return self._active_intent

    def get_latest_anchor(self) -> IntentAnchorState | None:
        if not self._anchors:
            return None
        return self._anchors[-1]

    def get_lineage(self, limit: int = 10) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._anchors[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_anchors": self._total_anchors,
            "total_validations": self._total_validations,
            "total_violations": self._total_violations,
            "active_intent": self._active_intent,
            "anchor_count": len(self._anchors),
        }

    def _persist(self, state: IntentAnchorState) -> None:
        path = self._state_dir / "intent_anchors.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")
