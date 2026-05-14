"""Operational Reasoning Composition Engine v1.

Composes reasoning state with transparent lineage.
Constructs operational explanations with explicit chains.

Cannot create hidden chain-of-thought mutation.
Cannot create opaque reasoning. Cannot plan autonomously.

UMH substrate subsystem. Phase 96.8CA.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from core.intelligence.operational_intelligence_contracts_v1 import (
    OperationalReasoningState,
    ReasoningType,
    _now_iso,
)


KNOWN_REASONING_TYPES: list[str] = [r.value for r in ReasoningType]
MAX_REASONING_DEPTH: int = 5
MAX_REASONING_CHAIN: int = 10
MAX_REASONING_HISTORY: int = 50


class OperationalReasoningCompositionEngine:
    """Composes transparent operational reasoning."""

    def __init__(self, state_dir: str | Path = "data/runtime/intelligence") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._history: list[OperationalReasoningState] = []
        self._total_compositions: int = 0

    def compose(
        self,
        reasoning_type: str,
        inputs: list[str],
        conclusion: str,
        confidence: float = 0.0,
        reasoning_chain: list[str] | None = None,
        set_by: str = "operator",
    ) -> OperationalReasoningState:
        if reasoning_type not in KNOWN_REASONING_TYPES:
            reasoning_type = "operational_status"

        chain = (reasoning_chain or [])[:MAX_REASONING_CHAIN]
        bounded_confidence = max(0.0, min(1.0, confidence))

        state = OperationalReasoningState(
            reasoning_type=reasoning_type,
            inputs=inputs[:MAX_REASONING_DEPTH],
            conclusion=conclusion,
            confidence=round(bounded_confidence, 4),
            reasoning_chain=chain,
            set_by=set_by,
        )

        self._history.append(state)
        if len(self._history) > MAX_REASONING_HISTORY:
            self._history = self._history[-MAX_REASONING_HISTORY:]

        self._total_compositions += 1
        self._persist(state)
        return state

    def get_latest(self) -> OperationalReasoningState | None:
        if not self._history:
            return None
        return self._history[-1]

    def get_by_type(self, reasoning_type: str) -> list[OperationalReasoningState]:
        return [r for r in self._history if r.reasoning_type == reasoning_type]

    def get_lineage(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._history[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_compositions": self._total_compositions,
            "history_length": len(self._history),
        }

    def _persist(self, state: OperationalReasoningState) -> None:
        path = self._state_dir / "reasoning_compositions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")
