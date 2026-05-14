"""Runtime Attention System v1.

Manages dimensional attention weighting for context
prioritization across the cognition layer.

Responsibilities:
  - Compute effective attention weights per dimension
  - Apply decay based on operator mode policies
  - Suppress stale or low-priority items
  - Provide attention-weighted scoring for working window
  - Track attention reweighting history

The attention system does not generate intent or
take autonomous action. It provides weighted scores
that other components use for prioritization.

UMH substrate subsystem. Phase 96.8BT.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.cognition.persistent_operator_cognition_contracts_v1 import (
    AttentionWeightType,
    CognitionDecisionType,
    CognitiveLineageReceipt,
    MODE_COGNITION_POLICIES,
    OperatorMode,
    RuntimeAttentionMap,
    _content_hash,
    _new_id,
    _now_iso,
)


ATTENTION_DEFAULTS: dict[str, float] = {
    AttentionWeightType.CONTINUITY.value: 1.0,
    AttentionWeightType.TEMPORAL.value: 1.0,
    AttentionWeightType.WORKFLOW.value: 1.0,
    AttentionWeightType.EMBODIMENT.value: 0.5,
    AttentionWeightType.LOOP_URGENCY.value: 1.5,
    AttentionWeightType.OPERATOR_FOCUS.value: 2.0,
}


class RuntimeAttentionSystem:
    """Manages attention weighting across operational dimensions.

    Computes effective weights, applies decay, and provides
    scoring for context prioritization. Does not execute
    actions or generate intent.
    """

    def __init__(
        self,
        session_id: str = "",
        mode: OperatorMode = OperatorMode.FOCUSED_EXECUTION,
        state_dir: str | Path = "data/runtime/cognition_state",
    ) -> None:
        self._session_id = session_id or _new_id("sess")
        self._mode = mode
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._attention_map = RuntimeAttentionMap(
            session_id=self._session_id,
            mode=mode,
        )

        self._reweight_history: list[dict[str, Any]] = []
        self._total_reweights: int = 0
        self._total_scores_computed: int = 0
        self._suppressions: int = 0

    @property
    def mode(self) -> OperatorMode:
        return self._mode

    @property
    def attention_map(self) -> RuntimeAttentionMap:
        return self._attention_map

    # ------------------------------------------------------------------
    # Mode-based decay
    # ------------------------------------------------------------------

    def apply_mode_decay(self, mode: OperatorMode | None = None) -> None:
        """Apply attention decay based on operator mode policy."""
        effective_mode = mode or self._mode
        policy = MODE_COGNITION_POLICIES.get(effective_mode.value, {})
        decay = policy.get("attention_decay_factor", 0.9)

        for wt in AttentionWeightType:
            if wt == AttentionWeightType.OPERATOR_FOCUS:
                continue
            current = self._attention_map.get_weight(wt)
            decayed = current * decay
            self._attention_map.set_weight(wt, max(0.1, decayed))

        if mode and mode != self._mode:
            self._mode = mode
            self._attention_map.mode = mode

    def reset_to_defaults(self) -> None:
        """Reset all attention weights to defaults."""
        for wt_name, default_val in ATTENTION_DEFAULTS.items():
            wt = AttentionWeightType(wt_name)
            self._attention_map.set_weight(wt, default_val)

    # ------------------------------------------------------------------
    # Reweighting
    # ------------------------------------------------------------------

    def reweight(
        self,
        weight_type: AttentionWeightType,
        value: float,
    ) -> dict[str, Any]:
        """Reweight a specific attention dimension."""
        old_value = self._attention_map.get_weight(weight_type)
        self._attention_map.set_weight(weight_type, value)
        new_value = self._attention_map.get_weight(weight_type)

        record = {
            "weight_type": weight_type.value,
            "old_value": round(old_value, 4),
            "new_value": round(new_value, 4),
            "requested_value": round(value, 4),
            "clamped": abs(value - new_value) > 0.001,
            "timestamp": _now_iso(),
        }
        self._reweight_history.append(record)
        self._total_reweights += 1

        self._persist_reweight(record)
        return record

    def _persist_reweight(self, record: dict[str, Any]) -> None:
        path = self._state_dir / "attention_reweight_history.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score_item(self, item: dict[str, Any]) -> float:
        """Compute an attention-weighted score for an item.

        Items can carry dimension hints via '_dimensions' key:
        a list of AttentionWeightType values that apply.
        """
        dimensions = item.get("_dimensions", [])
        if not dimensions:
            base_weight = item.get("_weight", 1.0)
            self._total_scores_computed += 1
            return float(base_weight)

        total = 0.0
        for dim in dimensions:
            try:
                wt = AttentionWeightType(dim)
                total += self._attention_map.get_weight(wt)
            except ValueError:
                total += 1.0

        base = item.get("_weight", 1.0)
        score = base * (total / max(len(dimensions), 1))
        self._total_scores_computed += 1
        return round(score, 4)

    def score_items(self, items: list[dict[str, Any]]) -> list[tuple[float, dict[str, Any]]]:
        """Score and sort items by attention weight (descending)."""
        scored = [(self.score_item(item), item) for item in items]
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Suppression
    # ------------------------------------------------------------------

    def should_suppress(
        self,
        item: dict[str, Any],
        threshold: float = 0.3,
    ) -> bool:
        """Whether an item's score is below suppression threshold."""
        score = self.score_item(item)
        if score < threshold:
            self._suppressions += 1
            return True
        return False

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "mode": self._mode.value,
            "total_reweights": self._total_reweights,
            "total_scores_computed": self._total_scores_computed,
            "suppressions": self._suppressions,
            "current_weights": {
                k: round(v, 4)
                for k, v in self._attention_map.weights.items()
            },
        }

    def get_reweight_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._reweight_history[-limit:]
