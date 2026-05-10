"""Exploration vs exploitation — bounded candidate selection policy.

Selects between exploiting the best-scoring candidate and exploring
alternatives when confidence is low. Exploration is opt-in, bounded,
and deterministic unless a seed is explicitly provided.

Pure computation — no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SelectionMode(Enum):
    EXPLOIT = "exploit"
    EXPLORE = "explore"


@dataclass(frozen=True)
class ExplorationPolicy:
    """Policy controlling exploration vs exploitation."""

    enabled: bool = False
    exploration_rate: float = 0.05
    min_confidence_for_exploitation: float = 0.7
    seed: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "exploration_rate", max(0.0, min(0.25, self.exploration_rate)))
        object.__setattr__(
            self,
            "min_confidence_for_exploitation",
            max(0.0, min(1.0, self.min_confidence_for_exploitation)),
        )


@dataclass(frozen=True)
class ExplorationDecision:
    """Result of candidate selection."""

    selected_index: int
    selected_candidate: str
    mode: SelectionMode
    reason: str
    confidence: float
    exploration_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_index": self.selected_index,
            "selected_candidate": self.selected_candidate,
            "mode": self.mode.value,
            "reason": self.reason,
            "confidence": round(self.confidence, 4),
            "exploration_rate": round(self.exploration_rate, 4),
        }


def select_candidate(
    candidates: list[str],
    scores: list[float],
    confidence: float,
    policy: ExplorationPolicy | None = None,
) -> ExplorationDecision:
    p = policy or ExplorationPolicy()

    if not candidates:
        return ExplorationDecision(
            selected_index=-1,
            selected_candidate="",
            mode=SelectionMode.EXPLOIT,
            reason="no candidates",
            confidence=confidence,
            exploration_rate=p.exploration_rate,
        )

    if len(scores) < len(candidates):
        scores = list(scores) + [0.0] * (len(candidates) - len(scores))
    elif len(scores) > len(candidates):
        scores = scores[: len(candidates)]

    best_idx = 0
    best_score = scores[0]
    for i in range(1, len(candidates)):
        if scores[i] > best_score:
            best_score = scores[i]
            best_idx = i

    if not p.enabled:
        return ExplorationDecision(
            selected_index=best_idx,
            selected_candidate=candidates[best_idx],
            mode=SelectionMode.EXPLOIT,
            reason="exploration disabled, selecting best",
            confidence=confidence,
            exploration_rate=p.exploration_rate,
        )

    if confidence >= p.min_confidence_for_exploitation:
        return ExplorationDecision(
            selected_index=best_idx,
            selected_candidate=candidates[best_idx],
            mode=SelectionMode.EXPLOIT,
            reason=f"high confidence ({confidence:.2f} >= {p.min_confidence_for_exploitation:.2f}), exploiting best",
            confidence=confidence,
            exploration_rate=p.exploration_rate,
        )

    if len(candidates) < 2:
        return ExplorationDecision(
            selected_index=best_idx,
            selected_candidate=candidates[best_idx],
            mode=SelectionMode.EXPLOIT,
            reason="only one candidate, cannot explore",
            confidence=confidence,
            exploration_rate=p.exploration_rate,
        )

    if p.seed is not None:
        explore_idx = p.seed % (len(candidates) - 1)
        non_best = [i for i in range(len(candidates)) if i != best_idx]
        selected_idx = non_best[explore_idx % len(non_best)]
    else:
        non_best = [i for i in range(len(candidates)) if i != best_idx]
        ranked = sorted(non_best, key=lambda i: scores[i], reverse=True)
        selected_idx = ranked[0]

    return ExplorationDecision(
        selected_index=selected_idx,
        selected_candidate=candidates[selected_idx],
        mode=SelectionMode.EXPLORE,
        reason=(
            f"low confidence ({confidence:.2f} < {p.min_confidence_for_exploitation:.2f}), "
            f"exploring alternative (rate={p.exploration_rate:.2f})"
        ),
        confidence=confidence,
        exploration_rate=p.exploration_rate,
    )
