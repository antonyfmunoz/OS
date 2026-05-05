"""Strategy — behavior-aware execution strategy derived from user traits.

Reads the UserBehaviorModel and produces an ExecutionStrategy that
downstream planners use to adjust scheduling decisions. The strategy
is immutable once built, and every adjustment carries an explanation.

Pure computation — no state mutation, no I/O, no subprocess.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.model.behavior import UserBehaviorModel
from umh.model.traits import TraitValue


_DEFAULT_BATCH_SIZE = 5
_DEFAULT_PACING = 1.0
_DEFAULT_PRIORITY_BIAS = 0.0
_MIN_BATCH_SIZE = 1
_MAX_BATCH_SIZE = 20


@dataclass(frozen=True)
class StrategyAdjustment:
    """One explainable adjustment made by the strategy builder."""

    trait_name: str
    trait_value: float
    trait_confidence: float
    adjustment: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "trait_name": self.trait_name,
            "trait_value": round(self.trait_value, 4),
            "trait_confidence": round(self.trait_confidence, 4),
            "adjustment": self.adjustment,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ExecutionStrategy:
    """Immutable execution strategy derived from behavior traits."""

    batch_size: int = _DEFAULT_BATCH_SIZE
    pacing: float = _DEFAULT_PACING
    retry_budget: int = 2
    priority_bias: float = _DEFAULT_PRIORITY_BIAS
    prefer_morning: bool = False
    prefer_clustering: bool = False
    adjustments: tuple[StrategyAdjustment, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_size": self.batch_size,
            "pacing": round(self.pacing, 4),
            "retry_budget": self.retry_budget,
            "priority_bias": round(self.priority_bias, 4),
            "prefer_morning": self.prefer_morning,
            "prefer_clustering": self.prefer_clustering,
            "adjustments": [a.to_dict() for a in self.adjustments],
        }

    @property
    def explanation(self) -> list[str]:
        return [a.reason for a in self.adjustments]


_CONFIDENCE_THRESHOLD = 0.2


class StrategyBuilder:
    """Builds an ExecutionStrategy from a UserBehaviorModel.

    All decisions are rule-based and deterministic. Each rule
    checks a trait value against a threshold, applies an adjustment
    only when confidence exceeds the minimum, and records the reason.
    """

    def __init__(self, *, confidence_threshold: float = _CONFIDENCE_THRESHOLD) -> None:
        self._confidence_threshold = max(0.0, min(1.0, confidence_threshold))

    @property
    def confidence_threshold(self) -> float:
        return self._confidence_threshold

    def build_strategy(
        self,
        model: UserBehaviorModel | None = None,
        objective: str = "",
    ) -> ExecutionStrategy:
        """Derive an execution strategy from the behavior model.

        Returns the default strategy when model is None or has
        insufficient confidence, ensuring graceful degradation.
        """
        if model is None:
            return ExecutionStrategy()

        batch_size = _DEFAULT_BATCH_SIZE
        pacing = _DEFAULT_PACING
        retry_budget = 2
        priority_bias = _DEFAULT_PRIORITY_BIAS
        prefer_morning = False
        prefer_clustering = False
        adjustments: list[StrategyAdjustment] = []

        batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering = (
            self._apply_completion_rate(
                model, batch_size, pacing, retry_budget, priority_bias,
                prefer_morning, prefer_clustering, adjustments,
            )
        )

        batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering = (
            self._apply_consistency_score(
                model, batch_size, pacing, retry_budget, priority_bias,
                prefer_morning, prefer_clustering, adjustments,
            )
        )

        batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering = (
            self._apply_latency_score(
                model, batch_size, pacing, retry_budget, priority_bias,
                prefer_morning, prefer_clustering, adjustments,
            )
        )

        batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering = (
            self._apply_time_preference(
                model, batch_size, pacing, retry_budget, priority_bias,
                prefer_morning, prefer_clustering, adjustments,
            )
        )

        batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering = (
            self._apply_pattern_stability(
                model, batch_size, pacing, retry_budget, priority_bias,
                prefer_morning, prefer_clustering, adjustments,
            )
        )

        batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering = (
            self._apply_volatility_index(
                model, batch_size, pacing, retry_budget, priority_bias,
                prefer_morning, prefer_clustering, adjustments,
            )
        )

        batch_size = max(_MIN_BATCH_SIZE, min(_MAX_BATCH_SIZE, batch_size))

        return ExecutionStrategy(
            batch_size=batch_size,
            pacing=pacing,
            retry_budget=retry_budget,
            priority_bias=priority_bias,
            prefer_morning=prefer_morning,
            prefer_clustering=prefer_clustering,
            adjustments=tuple(adjustments),
        )

    def _trait_active(self, trait: TraitValue | None) -> bool:
        if trait is None:
            return False
        return trait.confidence >= self._confidence_threshold

    def _apply_completion_rate(
        self,
        model: UserBehaviorModel,
        batch_size: int,
        pacing: float,
        retry_budget: int,
        priority_bias: float,
        prefer_morning: bool,
        prefer_clustering: bool,
        adjustments: list[StrategyAdjustment],
    ) -> tuple[int, float, int, float, bool, bool]:
        trait = model.get_trait("completion_rate")
        if not self._trait_active(trait):
            return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

        assert trait is not None
        if trait.value < 0.5:
            batch_size = max(_MIN_BATCH_SIZE, batch_size - 2)
            retry_budget = min(5, retry_budget + 1)
            adjustments.append(StrategyAdjustment(
                trait_name="completion_rate",
                trait_value=trait.value,
                trait_confidence=trait.confidence,
                adjustment="batch_size -2, retry_budget +1",
                reason=f"Low completion rate ({trait.value:.0%}) — smaller batches, more retries",
            ))
        elif trait.value > 0.8:
            batch_size += 2
            adjustments.append(StrategyAdjustment(
                trait_name="completion_rate",
                trait_value=trait.value,
                trait_confidence=trait.confidence,
                adjustment="batch_size +2",
                reason=f"High completion rate ({trait.value:.0%}) — larger batches safe",
            ))

        return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

    def _apply_consistency_score(
        self,
        model: UserBehaviorModel,
        batch_size: int,
        pacing: float,
        retry_budget: int,
        priority_bias: float,
        prefer_morning: bool,
        prefer_clustering: bool,
        adjustments: list[StrategyAdjustment],
    ) -> tuple[int, float, int, float, bool, bool]:
        trait = model.get_trait("consistency_score")
        if not self._trait_active(trait):
            return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

        assert trait is not None
        if trait.value > 0.7:
            prefer_clustering = True
            batch_size += 1
            adjustments.append(StrategyAdjustment(
                trait_name="consistency_score",
                trait_value=trait.value,
                trait_confidence=trait.confidence,
                adjustment="prefer_clustering=True, batch_size +1",
                reason=f"High consistency ({trait.value:.0%}) — cluster tasks, allow larger batches",
            ))
        elif trait.value < 0.3:
            pacing *= 1.3
            adjustments.append(StrategyAdjustment(
                trait_name="consistency_score",
                trait_value=trait.value,
                trait_confidence=trait.confidence,
                adjustment="pacing *1.3",
                reason=f"Low consistency ({trait.value:.0%}) — slower pacing to accommodate variability",
            ))

        return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

    def _apply_latency_score(
        self,
        model: UserBehaviorModel,
        batch_size: int,
        pacing: float,
        retry_budget: int,
        priority_bias: float,
        prefer_morning: bool,
        prefer_clustering: bool,
        adjustments: list[StrategyAdjustment],
    ) -> tuple[int, float, int, float, bool, bool]:
        trait = model.get_trait("latency_score")
        if not self._trait_active(trait):
            return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

        assert trait is not None
        if trait.value < 0.3:
            pacing *= 1.5
            adjustments.append(StrategyAdjustment(
                trait_name="latency_score",
                trait_value=trait.value,
                trait_confidence=trait.confidence,
                adjustment="pacing *1.5",
                reason=f"Slow responses ({trait.value:.0%}) — increase time buffers",
            ))
        elif trait.value > 0.8:
            pacing *= 0.8
            adjustments.append(StrategyAdjustment(
                trait_name="latency_score",
                trait_value=trait.value,
                trait_confidence=trait.confidence,
                adjustment="pacing *0.8",
                reason=f"Fast responses ({trait.value:.0%}) — tighter pacing safe",
            ))

        return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

    def _apply_time_preference(
        self,
        model: UserBehaviorModel,
        batch_size: int,
        pacing: float,
        retry_budget: int,
        priority_bias: float,
        prefer_morning: bool,
        prefer_clustering: bool,
        adjustments: list[StrategyAdjustment],
    ) -> tuple[int, float, int, float, bool, bool]:
        trait = model.get_trait("time_preference")
        if not self._trait_active(trait):
            return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

        assert trait is not None
        if trait.value > 0.7:
            prefer_morning = True
            adjustments.append(StrategyAdjustment(
                trait_name="time_preference",
                trait_value=trait.value,
                trait_confidence=trait.confidence,
                adjustment="prefer_morning=True",
                reason=f"Morning preference ({trait.value:.0%}) — schedule early execution windows",
            ))

        return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

    def _apply_pattern_stability(
        self,
        model: UserBehaviorModel,
        batch_size: int,
        pacing: float,
        retry_budget: int,
        priority_bias: float,
        prefer_morning: bool,
        prefer_clustering: bool,
        adjustments: list[StrategyAdjustment],
    ) -> tuple[int, float, int, float, bool, bool]:
        trait = model.get_trait("pattern_stability")
        if not self._trait_active(trait):
            return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

        assert trait is not None
        if trait.value > 0.6:
            priority_bias += 0.2
            adjustments.append(StrategyAdjustment(
                trait_name="pattern_stability",
                trait_value=trait.value,
                trait_confidence=trait.confidence,
                adjustment="priority_bias +0.2",
                reason=f"Stable patterns ({trait.value:.0%}) — favor established task types",
            ))

        return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

    def _apply_volatility_index(
        self,
        model: UserBehaviorModel,
        batch_size: int,
        pacing: float,
        retry_budget: int,
        priority_bias: float,
        prefer_morning: bool,
        prefer_clustering: bool,
        adjustments: list[StrategyAdjustment],
    ) -> tuple[int, float, int, float, bool, bool]:
        trait = model.get_trait("volatility_index")
        if not self._trait_active(trait):
            return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering

        assert trait is not None
        if trait.value > 0.7:
            batch_size = max(_MIN_BATCH_SIZE, batch_size - 1)
            retry_budget = min(5, retry_budget + 1)
            adjustments.append(StrategyAdjustment(
                trait_name="volatility_index",
                trait_value=trait.value,
                trait_confidence=trait.confidence,
                adjustment="batch_size -1, retry_budget +1",
                reason=f"High volatility ({trait.value:.0%}) — smaller batches, more retries for unpredictability",
            ))

        return batch_size, pacing, retry_budget, priority_bias, prefer_morning, prefer_clustering
