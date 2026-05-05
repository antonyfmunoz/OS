"""Tradeoff resolution — multi-objective balancing and deterministic arbitration.

Resolves conflicts between meta-goal scores by normalizing dimensions
into [0,1] space, applying weighted scoring, Pareto filtering, and
deterministic tie-breaking.

Scoring:
    normalized = (value - min_val) / (max_val - min_val)  [maximize]
    normalized = 1.0 - (value - min_val) / (max_val - min_val)  [minimize]
    weighted_score = Σ(normalized_i × weight_i) / Σ(weight_i)

Pareto filtering:
    A candidate is dominated if another candidate is >= in all
    dimensions and strictly > in at least one.

Pure computation — no I/O, no subprocess, no state mutation.
No imports from umh/cells, umh/environments, umh/adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from umh.runtime.context import ExecutionContext
    from umh.runtime.weighting import WeightAdapter, WeightAdaptationResult


_MIN_WEIGHT = 0.0
_MAX_WEIGHT = 10.0
_DEFAULT_TOLERANCE = 0.0
_MAX_TOLERANCE = 1.0
_EPSILON = 1e-9


@dataclass(frozen=True)
class TradeoffDimension:
    """A single scoring dimension for tradeoff resolution."""

    name: str
    direction: str = "maximize"
    weight: float = 1.0
    tolerance: float = _DEFAULT_TOLERANCE

    def __post_init__(self) -> None:
        if self.direction not in ("maximize", "minimize"):
            object.__setattr__(self, "direction", "maximize")
        w = max(_MIN_WEIGHT, min(_MAX_WEIGHT, self.weight))
        object.__setattr__(self, "weight", w)
        t = max(0.0, min(_MAX_TOLERANCE, self.tolerance))
        object.__setattr__(self, "tolerance", t)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "direction": self.direction,
            "weight": round(self.weight, 4),
            "tolerance": round(self.tolerance, 4),
        }


@dataclass(frozen=True)
class TradeoffProfile:
    """A collection of dimensions defining the tradeoff space."""

    dimensions: tuple[TradeoffDimension, ...]
    name: str = ""

    @property
    def dimension_count(self) -> int:
        return len(self.dimensions)

    @property
    def dimension_names(self) -> list[str]:
        return [d.name for d in self.dimensions]

    def total_weight(self) -> float:
        return sum(d.weight for d in self.dimensions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dimension_count": self.dimension_count,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "total_weight": round(self.total_weight(), 4),
        }


@dataclass(frozen=True)
class CandidateScore:
    """A candidate with its raw and normalized dimension values."""

    candidate_id: str
    raw_values: dict[str, float]
    normalized_values: dict[str, float]
    weighted_score: float
    dimension_contributions: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "raw_values": {k: round(v, 4) for k, v in sorted(self.raw_values.items())},
            "normalized_values": {
                k: round(v, 4) for k, v in sorted(self.normalized_values.items())
            },
            "weighted_score": round(self.weighted_score, 4),
            "dimension_contributions": {
                k: round(v, 4) for k, v in sorted(self.dimension_contributions.items())
            },
        }


@dataclass(frozen=True)
class TradeoffResult:
    """Complete tradeoff resolution output."""

    best: CandidateScore
    ranked: tuple[CandidateScore, ...]
    pareto_frontier: tuple[str, ...]
    dominated: tuple[str, ...]
    profile: TradeoffProfile
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "best_candidate": self.best.candidate_id,
            "best_score": round(self.best.weighted_score, 4),
            "ranked": [c.to_dict() for c in self.ranked],
            "pareto_frontier": list(self.pareto_frontier),
            "dominated": list(self.dominated),
            "profile": self.profile.to_dict(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class TradeoffInfluence:
    """Result of applying tradeoff resolution to the scoring chain."""

    factor: float
    tradeoff_result: TradeoffResult | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "factor": round(self.factor, 4),
            "reason": self.reason,
        }
        if self.tradeoff_result is not None:
            result["tradeoff"] = self.tradeoff_result.to_dict()
        return result


_MIN_TRADEOFF_FACTOR = 0.85
_MAX_TRADEOFF_FACTOR = 1.15


def normalize_value(
    value: float,
    min_val: float,
    max_val: float,
    direction: str,
) -> float:
    """Normalize a value to [0,1] based on direction.

    maximize: higher raw → higher normalized
    minimize: lower raw → higher normalized
    """
    if max_val - min_val < _EPSILON:
        return 0.5

    ratio = (value - min_val) / (max_val - min_val)
    ratio = max(0.0, min(1.0, ratio))

    if direction == "minimize":
        return 1.0 - ratio
    return ratio


def compute_weighted_score(
    normalized: dict[str, float],
    dimensions: tuple[TradeoffDimension, ...],
) -> tuple[float, dict[str, float]]:
    """Compute weighted score from normalized values. Returns (score, contributions)."""
    total_weight = sum(d.weight for d in dimensions)
    if total_weight < _EPSILON:
        return 0.5, {}

    contributions: dict[str, float] = {}
    weighted_sum = 0.0

    for dim in dimensions:
        val = normalized.get(dim.name, 0.5)
        contribution = val * dim.weight / total_weight
        contributions[dim.name] = contribution
        weighted_sum += contribution

    return weighted_sum, contributions


def is_dominated(
    a_vals: dict[str, float],
    b_vals: dict[str, float],
    dimensions: tuple[TradeoffDimension, ...],
) -> bool:
    """Check if candidate A is dominated by candidate B.

    B dominates A if B >= A in all normalized dimensions
    and B > A in at least one.
    """
    all_geq = True
    any_strictly_greater = False

    for dim in dimensions:
        a_v = a_vals.get(dim.name, 0.5)
        b_v = b_vals.get(dim.name, 0.5)

        if b_v < a_v - _EPSILON:
            all_geq = False
            break
        if b_v > a_v + _EPSILON:
            any_strictly_greater = True

    return all_geq and any_strictly_greater


def pareto_filter(
    candidates: dict[str, dict[str, float]],
    dimensions: tuple[TradeoffDimension, ...],
) -> tuple[list[str], list[str]]:
    """Separate candidates into Pareto frontier and dominated sets.

    Returns (frontier_ids, dominated_ids), both sorted for determinism.
    """
    ids = sorted(candidates.keys())
    dominated_set: set[str] = set()

    for i, cid_a in enumerate(ids):
        if cid_a in dominated_set:
            continue
        for cid_b in ids[i + 1 :]:
            if cid_b in dominated_set:
                continue

            a_vals = candidates[cid_a]
            b_vals = candidates[cid_b]

            if is_dominated(a_vals, b_vals, dimensions):
                dominated_set.add(cid_a)
                break
            elif is_dominated(b_vals, a_vals, dimensions):
                dominated_set.add(cid_b)

    frontier = sorted(cid for cid in ids if cid not in dominated_set)
    dominated = sorted(dominated_set)
    return frontier, dominated


class TradeoffEngine:
    """Resolves multi-objective tradeoffs through normalization, Pareto
    filtering, weighted scoring, tolerance filtering, and deterministic
    tie-breaking.

    Pure — all inputs provided per call, no internal state mutation.
    """

    def __init__(
        self,
        *,
        profile: TradeoffProfile | None = None,
        enable_pareto: bool = True,
    ) -> None:
        self._profile = profile or TradeoffProfile(dimensions=())
        self._enable_pareto = enable_pareto

    @property
    def profile(self) -> TradeoffProfile:
        return self._profile

    @property
    def pareto_enabled(self) -> bool:
        return self._enable_pareto

    def resolve(
        self,
        candidates: dict[str, dict[str, float]],
        *,
        profile: TradeoffProfile | None = None,
        context: ExecutionContext | None = None,
        adapter: WeightAdapter | None = None,
    ) -> TradeoffResult | None:
        """Resolve tradeoffs across candidates.

        candidates: mapping of candidate_id → {dimension_name: raw_value}
        profile: optional override for the engine's default profile
        context: optional execution context for weight adaptation
        adapter: optional weight adapter (created if context provided without one)

        Returns None if no candidates provided.
        """
        if not candidates:
            return None

        active_profile = profile or self._profile

        if context is not None:
            from umh.runtime.weighting import WeightAdapter as _WA
            from umh.runtime.weighting import apply_context_weights

            actual_adapter = adapter or _WA()
            active_profile, _adaptation = apply_context_weights(
                active_profile, context, actual_adapter
            )

        dims = active_profile.dimensions

        if not dims:
            return self._score_without_dimensions(candidates, active_profile)

        min_vals, max_vals = self._compute_bounds(candidates, dims)

        all_normalized: dict[str, dict[str, float]] = {}
        for cid in sorted(candidates.keys()):
            raw = candidates[cid]
            norm: dict[str, float] = {}
            for dim in dims:
                val = raw.get(dim.name, 0.0)
                norm[dim.name] = normalize_value(
                    val, min_vals[dim.name], max_vals[dim.name], dim.direction
                )
            all_normalized[cid] = norm

        if self._enable_pareto and len(candidates) > 1:
            frontier_ids, dominated_ids = pareto_filter(all_normalized, dims)
        else:
            frontier_ids = sorted(candidates.keys())
            dominated_ids = []

        scored: list[CandidateScore] = []
        for cid in sorted(candidates.keys()):
            raw = candidates[cid]
            norm = all_normalized[cid]
            w_score, contribs = compute_weighted_score(norm, dims)

            scored.append(
                CandidateScore(
                    candidate_id=cid,
                    raw_values=dict(raw),
                    normalized_values=dict(norm),
                    weighted_score=w_score,
                    dimension_contributions=contribs,
                )
            )

        scored = self._apply_tolerance_filter(scored, dims)

        scored.sort(key=lambda c: (-c.weighted_score, c.candidate_id))

        best = scored[0]
        reason = self._build_reason(best, scored, frontier_ids, dominated_ids, active_profile)

        return TradeoffResult(
            best=best,
            ranked=tuple(scored),
            pareto_frontier=tuple(frontier_ids),
            dominated=tuple(dominated_ids),
            profile=active_profile,
            reason=reason,
        )

    def _score_without_dimensions(
        self,
        candidates: dict[str, dict[str, float]],
        profile: TradeoffProfile,
    ) -> TradeoffResult:
        """Fallback when no dimensions are defined — score by average of raw values."""
        scored: list[CandidateScore] = []
        for cid in sorted(candidates.keys()):
            raw = candidates[cid]
            vals = list(raw.values())
            avg = sum(vals) / len(vals) if vals else 0.5
            scored.append(
                CandidateScore(
                    candidate_id=cid,
                    raw_values=dict(raw),
                    normalized_values={},
                    weighted_score=avg,
                    dimension_contributions={},
                )
            )

        scored.sort(key=lambda c: (-c.weighted_score, c.candidate_id))
        best = scored[0]

        return TradeoffResult(
            best=best,
            ranked=tuple(scored),
            pareto_frontier=tuple(c.candidate_id for c in scored),
            dominated=(),
            profile=profile,
            reason="no dimensions defined; scored by raw average",
        )

    def _compute_bounds(
        self,
        candidates: dict[str, dict[str, float]],
        dims: tuple[TradeoffDimension, ...],
    ) -> tuple[dict[str, float], dict[str, float]]:
        min_vals: dict[str, float] = {}
        max_vals: dict[str, float] = {}

        for dim in dims:
            values = [c.get(dim.name, 0.0) for c in candidates.values()]
            min_vals[dim.name] = min(values)
            max_vals[dim.name] = max(values)

        return min_vals, max_vals

    def _apply_tolerance_filter(
        self,
        scored: list[CandidateScore],
        dims: tuple[TradeoffDimension, ...],
    ) -> list[CandidateScore]:
        """Filter out candidates that fail tolerance thresholds in any dimension."""
        tolerant_dims = [d for d in dims if d.tolerance > 0.0]
        if not tolerant_dims:
            return scored

        filtered: list[CandidateScore] = []
        for cs in scored:
            passes = True
            for dim in tolerant_dims:
                norm_val = cs.normalized_values.get(dim.name, 0.5)
                if norm_val < dim.tolerance:
                    passes = False
                    break
            if passes:
                filtered.append(cs)

        return filtered if filtered else scored

    def _build_reason(
        self,
        best: CandidateScore,
        all_scored: list[CandidateScore],
        frontier: list[str],
        dominated: list[str],
        profile: TradeoffProfile,
    ) -> str:
        parts: list[str] = []

        parts.append(f"best: '{best.candidate_id}' (score={best.weighted_score:.4f})")

        if len(frontier) < len(all_scored):
            parts.append(f"pareto: {len(frontier)}/{len(all_scored)} on frontier")

        if dominated:
            parts.append(f"dominated: {', '.join(dominated[:3])}")

        if len(all_scored) > 1:
            runner = all_scored[1]
            margin = best.weighted_score - runner.weighted_score
            if margin < 0.02:
                parts.append(f"narrow margin ({margin:.4f})")

        top_dims = sorted(
            best.dimension_contributions.items(),
            key=lambda x: -x[1],
        )[:2]
        if top_dims:
            dim_strs = [f"{name}={val:.4f}" for name, val in top_dims]
            parts.append(f"top contributions: {', '.join(dim_strs)}")

        return "; ".join(parts)


class TradeoffScorer:
    """Computes tradeoff influence factor for the scoring chain.

    Collects meta-goal scores as tradeoff dimensions and resolves
    conflicts through the TradeoffEngine. Produces a multiplicative
    factor in [_MIN_TRADEOFF_FACTOR, _MAX_TRADEOFF_FACTOR].

    Pure — no state mutation, no I/O.
    """

    def __init__(
        self,
        *,
        engine: TradeoffEngine | None = None,
        profile: TradeoffProfile | None = None,
        enabled: bool = False,
    ) -> None:
        self._engine = engine or TradeoffEngine()
        self._profile = profile
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def engine(self) -> TradeoffEngine:
        return self._engine

    @property
    def profile(self) -> TradeoffProfile | None:
        return self._profile

    def compute_factor(
        self,
        *,
        meta_goal_scores: dict[str, float] | None = None,
        candidate_id: str = "",
        context: ExecutionContext | None = None,
    ) -> TradeoffInfluence:
        """Compute tradeoff-based scoring factor. Pure, no side effects."""
        if not self._enabled:
            return TradeoffInfluence(
                factor=1.0,
                tradeoff_result=None,
                reason="tradeoff scoring disabled",
            )

        if not meta_goal_scores or not candidate_id:
            return TradeoffInfluence(
                factor=1.0,
                tradeoff_result=None,
                reason="no meta-goal scores or candidate provided",
            )

        profile = self._profile
        if profile is None or profile.dimension_count == 0:
            profile = self._auto_profile(meta_goal_scores)

        candidates = {candidate_id: meta_goal_scores}
        result = self._engine.resolve(candidates, profile=profile, context=context)

        if result is None:
            return TradeoffInfluence(
                factor=1.0,
                tradeoff_result=None,
                reason="tradeoff engine returned no result",
            )

        deviation = result.best.weighted_score - 0.5
        raw_factor = 1.0 + deviation * 0.3
        factor = max(
            _MIN_TRADEOFF_FACTOR,
            min(_MAX_TRADEOFF_FACTOR, raw_factor),
        )

        return TradeoffInfluence(
            factor=factor,
            tradeoff_result=result,
            reason=result.reason,
        )

    def _auto_profile(self, scores: dict[str, float]) -> TradeoffProfile:
        """Generate a profile from score keys when none is configured."""
        dims = tuple(
            TradeoffDimension(name=name, direction="maximize", weight=1.0)
            for name in sorted(scores.keys())
        )
        return TradeoffProfile(dimensions=dims, name="auto")
