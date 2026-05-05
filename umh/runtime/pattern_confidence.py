"""Pattern confidence evolution — belief persistence for pattern reliability.

Tracks evolving confidence per pattern: confidence grows with repeated
reliable outcomes, shrinks with noisy outcomes, and decays toward neutral
when a pattern goes unused. This is belief persistence, not causal learning.

Design principles:
    - Off by default (enabled must be explicitly True, inv 393)
    - Confidence bounded [0, 1] (inv 383)
    - Low-sample patterns remain low/neutral confidence (inv 384)
    - Reliable repeated outcomes increase confidence (inv 385)
    - Noisy outcomes decrease confidence (inv 386)
    - Unused patterns decay toward neutral (inv 387)
    - Deterministic updates only (inv 388)
    - No mutation of historical PatternRecords (inv 389)
    - No scoring feedback loop (inv 390)
    - Missing pattern data → neutral confidence (inv 391)
    - Confidence evolution must be explainable (inv 392)

Invariants 383-393.

Pure computation — no I/O, no child processes.
No imports from cell, environment, or adapter layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.runtime.pattern_half_life import compute_pattern_noise, compute_pattern_reliability


@dataclass(frozen=True)
class PatternConfidenceConfig:
    """Configuration for pattern confidence evolution."""

    enabled: bool = False
    neutral_confidence: float = 0.5
    min_samples: int = 10
    reinforcement_rate: float = 0.05
    decay_rate: float = 0.98
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    noise_threshold: float = 0.30
    reliability_threshold: float = 0.70

    def __post_init__(self) -> None:
        object.__setattr__(self, "neutral_confidence", max(0.0, min(1.0, self.neutral_confidence)))
        object.__setattr__(self, "min_samples", max(1, self.min_samples))
        object.__setattr__(self, "reinforcement_rate", max(0.0, min(1.0, self.reinforcement_rate)))
        object.__setattr__(self, "decay_rate", max(0.0, min(1.0, self.decay_rate)))
        object.__setattr__(self, "min_confidence", max(0.0, min(1.0, self.min_confidence)))
        object.__setattr__(
            self,
            "max_confidence",
            max(self.min_confidence, min(1.0, self.max_confidence)),
        )
        object.__setattr__(self, "noise_threshold", max(0.0, min(1.0, self.noise_threshold)))
        object.__setattr__(
            self, "reliability_threshold", max(0.0, min(1.0, self.reliability_threshold))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "neutral_confidence": round(self.neutral_confidence, 4),
            "min_samples": self.min_samples,
            "reinforcement_rate": round(self.reinforcement_rate, 4),
            "decay_rate": round(self.decay_rate, 4),
            "min_confidence": round(self.min_confidence, 4),
            "max_confidence": round(self.max_confidence, 4),
            "noise_threshold": round(self.noise_threshold, 4),
            "reliability_threshold": round(self.reliability_threshold, 4),
        }


@dataclass(frozen=True)
class PatternConfidenceState:
    """Current confidence state for one pattern (inv 392)."""

    pattern_key: str = ""
    confidence: float = 0.5
    sample_count: int = 0
    last_seen_index: int = 0
    reliability: float = 0.0
    noise: float = 0.0
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))
        object.__setattr__(self, "sample_count", max(0, self.sample_count))
        object.__setattr__(self, "last_seen_index", max(0, self.last_seen_index))
        object.__setattr__(self, "reliability", max(0.0, min(1.0, self.reliability)))
        object.__setattr__(self, "noise", max(0.0, min(1.0, self.noise)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_key": self.pattern_key,
            "confidence": round(self.confidence, 6),
            "sample_count": self.sample_count,
            "last_seen_index": self.last_seen_index,
            "reliability": round(self.reliability, 6),
            "noise": round(self.noise, 6),
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class PatternConfidenceResult:
    """Result of a single confidence evolution step (inv 392)."""

    pattern_key: str = ""
    previous_confidence: float = 0.5
    new_confidence: float = 0.5
    sample_count: int = 0
    reliability: float = 0.0
    noise: float = 0.0
    delta: float = 0.0
    used_fallback: bool = True
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "previous_confidence", max(0.0, min(1.0, self.previous_confidence))
        )
        object.__setattr__(self, "new_confidence", max(0.0, min(1.0, self.new_confidence)))
        object.__setattr__(self, "sample_count", max(0, self.sample_count))
        object.__setattr__(self, "reliability", max(0.0, min(1.0, self.reliability)))
        object.__setattr__(self, "noise", max(0.0, min(1.0, self.noise)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_key": self.pattern_key,
            "previous_confidence": round(self.previous_confidence, 6),
            "new_confidence": round(self.new_confidence, 6),
            "sample_count": self.sample_count,
            "reliability": round(self.reliability, 6),
            "noise": round(self.noise, 6),
            "delta": round(self.delta, 6),
            "used_fallback": self.used_fallback,
            "explanation": self.explanation,
        }


def update_pattern_confidence(
    pattern_key: str,
    pattern_scores: list[float],
    previous_confidence: float,
    current_index: int,
    last_seen_index: int,
    config: PatternConfidenceConfig | None = None,
) -> PatternConfidenceResult:
    """Compute evolved confidence for a single pattern.

    pattern_scores: historical outcome scores for this pattern.
    previous_confidence: confidence from the last update.
    current_index: current observation index.
    last_seen_index: observation index when pattern was last seen.
    config: confidence evolution config (defaults to disabled).

    Returns PatternConfidenceResult with new confidence and explanation.
    """
    cfg = config or PatternConfidenceConfig()
    n = len(pattern_scores)

    if not cfg.enabled:
        return PatternConfidenceResult(
            pattern_key=pattern_key,
            previous_confidence=previous_confidence,
            new_confidence=previous_confidence,
            sample_count=n,
            used_fallback=True,
            explanation="pattern confidence evolution disabled",
        )

    if n == 0:
        return PatternConfidenceResult(
            pattern_key=pattern_key,
            previous_confidence=previous_confidence,
            new_confidence=cfg.neutral_confidence,
            sample_count=0,
            delta=cfg.neutral_confidence - previous_confidence,
            used_fallback=True,
            explanation="no pattern scores available",
        )

    noise = compute_pattern_noise(pattern_scores)
    reliability = compute_pattern_reliability(pattern_scores)

    if n < cfg.min_samples:
        capped = min(previous_confidence, cfg.neutral_confidence)
        clamped = max(cfg.min_confidence, min(cfg.max_confidence, capped))
        return PatternConfidenceResult(
            pattern_key=pattern_key,
            previous_confidence=previous_confidence,
            new_confidence=clamped,
            sample_count=n,
            reliability=reliability,
            noise=noise,
            delta=clamped - previous_confidence,
            used_fallback=True,
            explanation=f"insufficient samples ({n} < {cfg.min_samples})",
        )

    confidence_target = reliability
    delta = cfg.reinforcement_rate * (confidence_target - previous_confidence)
    new_conf = previous_confidence + delta

    age = max(0, current_index - last_seen_index)
    decay_explanation = ""
    if age > 0:
        decay_factor = cfg.decay_rate**age
        new_conf = cfg.neutral_confidence + (new_conf - cfg.neutral_confidence) * decay_factor
        decay_explanation = f"; decay age={age}, factor={decay_factor:.6f}"

    new_conf = max(cfg.min_confidence, min(cfg.max_confidence, new_conf))
    final_delta = new_conf - previous_confidence

    if reliability >= cfg.reliability_threshold:
        category = "reliable"
    elif noise >= cfg.noise_threshold:
        category = "noisy"
    else:
        category = "neutral"

    explanation = (
        f"{category} (reliability={reliability:.4f}, noise={noise:.4f}, "
        f"samples={n}, target={confidence_target:.4f}){decay_explanation}"
    )

    return PatternConfidenceResult(
        pattern_key=pattern_key,
        previous_confidence=previous_confidence,
        new_confidence=new_conf,
        sample_count=n,
        reliability=reliability,
        noise=noise,
        delta=final_delta,
        used_fallback=False,
        explanation=explanation,
    )


def update_all_pattern_confidences(
    pattern_keys: list[str],
    pattern_scores_map: dict[str, list[float]],
    previous_confidences: dict[str, float],
    current_index: int,
    last_seen_map: dict[str, int],
    config: PatternConfidenceConfig | None = None,
) -> list[PatternConfidenceResult]:
    """Compute evolved confidence for a batch of patterns."""
    results: list[PatternConfidenceResult] = []
    cfg = config or PatternConfidenceConfig()
    for key in pattern_keys:
        scores = pattern_scores_map.get(key, [])
        prev = previous_confidences.get(key, cfg.neutral_confidence)
        last_seen = last_seen_map.get(key, current_index)
        results.append(update_pattern_confidence(key, scores, prev, current_index, last_seen, cfg))
    return results


class PatternConfidenceMemory:
    """In-memory confidence state tracker.

    Never mutates PatternRecords (inv 389). Only tracks confidence states.
    Deterministic ordering: sorted by pattern_key (inv 388).
    """

    def __init__(self, neutral_confidence: float = 0.5) -> None:
        self._states: dict[str, PatternConfidenceState] = {}
        self._neutral: float = max(0.0, min(1.0, neutral_confidence))

    @property
    def size(self) -> int:
        return len(self._states)

    def get(self, pattern_key: str) -> PatternConfidenceState:
        """Get current confidence state for a pattern.

        Returns neutral state if pattern has never been updated (inv 391).
        """
        if pattern_key in self._states:
            return self._states[pattern_key]
        return PatternConfidenceState(
            pattern_key=pattern_key,
            confidence=self._neutral,
            explanation="no prior state",
        )

    def update(
        self,
        pattern_key: str,
        pattern_scores: list[float],
        current_index: int,
        config: PatternConfidenceConfig | None = None,
    ) -> PatternConfidenceResult:
        """Update confidence for a single pattern and store new state."""
        cfg = config or PatternConfidenceConfig()
        prev_state = self.get(pattern_key)

        result = update_pattern_confidence(
            pattern_key=pattern_key,
            pattern_scores=pattern_scores,
            previous_confidence=prev_state.confidence,
            current_index=current_index,
            last_seen_index=prev_state.last_seen_index,
            config=cfg,
        )

        new_last_seen = current_index if len(pattern_scores) > 0 else prev_state.last_seen_index

        self._states[pattern_key] = PatternConfidenceState(
            pattern_key=pattern_key,
            confidence=result.new_confidence,
            sample_count=result.sample_count,
            last_seen_index=new_last_seen,
            reliability=result.reliability,
            noise=result.noise,
            explanation=result.explanation,
        )

        return result

    def decay_unused(
        self,
        current_index: int,
        config: PatternConfidenceConfig | None = None,
    ) -> list[PatternConfidenceResult]:
        """Decay all patterns not seen at current_index toward neutral."""
        cfg = config or PatternConfidenceConfig()
        if not cfg.enabled:
            return []

        results: list[PatternConfidenceResult] = []
        for key in sorted(self._states):
            state = self._states[key]
            if state.last_seen_index >= current_index:
                continue

            age = current_index - state.last_seen_index
            if age <= 0:
                continue

            decay_factor = cfg.decay_rate**age
            decayed = (
                cfg.neutral_confidence + (state.confidence - cfg.neutral_confidence) * decay_factor
            )
            decayed = max(cfg.min_confidence, min(cfg.max_confidence, decayed))

            delta = decayed - state.confidence

            result = PatternConfidenceResult(
                pattern_key=key,
                previous_confidence=state.confidence,
                new_confidence=decayed,
                sample_count=state.sample_count,
                reliability=state.reliability,
                noise=state.noise,
                delta=delta,
                used_fallback=False,
                explanation=f"decay-only: age={age}, factor={decay_factor:.6f}",
            )
            results.append(result)

            self._states[key] = PatternConfidenceState(
                pattern_key=key,
                confidence=decayed,
                sample_count=state.sample_count,
                last_seen_index=state.last_seen_index,
                reliability=state.reliability,
                noise=state.noise,
                explanation=f"decayed at index {current_index}",
            )

        return results

    def snapshot(self) -> dict[str, PatternConfidenceState]:
        """Return a deterministic snapshot of all confidence states (inv 388)."""
        return {k: self._states[k] for k in sorted(self._states)}

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "states": {k: v.to_dict() for k, v in self.snapshot().items()},
        }
