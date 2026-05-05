"""StrategyAbstraction — cross-context strategy transfer for UMH.

Transforms low-level execution experience into reusable strategy
prototypes that can influence future decisions across different contexts.

This is NOT more bias tuning. This IS:
- pattern extraction from execution history
- abstraction into context-generalized prototypes
- transfer via bounded bias generation

Pipeline position:
    StrategyPatternMemory → StrategyAbstraction → MultiWorldPolicy

All bias outputs are bounded to [-0.05, +0.05], additive, and
gated by confidence thresholds.

Usage::

    from umh.runtime_engine.strategy_abstraction import (
        StrategyPrototypeStore,
        extract_strategy_prototypes,
        generate_strategy_bias,
    )

    store = StrategyPrototypeStore()
    result = extract_strategy_prototypes(recent_traces, store)
    bias = generate_strategy_bias(current_trace, store)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


# ─── Constants ────────────────────────────────────────────────────

MIN_SAMPLE_COUNT = 5
MIN_CONFIDENCE_FOR_TRANSFER = 0.4
MIN_MATCH_SCORE_FOR_BIAS = 0.5
BIAS_BOUND = 0.05
BIAS_SCALE = 0.02
EMA_ALPHA = 0.2
MAX_PROTOTYPES = 50

UNCERTAINTY_BUCKETS = {"low": (0.0, 0.3), "medium": (0.3, 0.6), "high": (0.6, 1.0)}
RISK_BUCKETS = {"low": (0.0, 0.3), "medium": (0.3, 0.6), "high": (0.6, 1.0)}


# ─── Context signature ───────────────────────────────────────────


def _bucket_value(value: float, buckets: dict[str, tuple[float, float]]) -> str:
    for label, (lo, hi) in buckets.items():
        if lo <= value < hi:
            return label
    return list(buckets.keys())[-1]


def extract_context_signature(trace: object) -> dict[str, str]:
    """Extract a generalized context signature from a DecisionTrace.

    Converts continuous values to categorical buckets for clustering.
    """
    context_type = getattr(trace, "context_type", None) or "unknown"
    arb_mode = getattr(trace, "objective_arb_mode", None) or "default"
    mc_mode = getattr(trace, "meta_control_mode", None) or "full"

    uncertainty_raw = getattr(trace, "planner_uncertainty", None)
    uncertainty = _bucket_value(
        uncertainty_raw if uncertainty_raw is not None else 0.0,
        UNCERTAINTY_BUCKETS,
    )

    risk_raw = getattr(trace, "calibration_risk_bias", None)
    if risk_raw is None:
        risk_raw = getattr(trace, "policy_variance", None)
    risk = _bucket_value(
        risk_raw if risk_raw is not None else 0.0,
        RISK_BUCKETS,
    )

    return {
        "context_type": context_type,
        "objective_mode": arb_mode,
        "meta_control": mc_mode,
        "uncertainty": uncertainty,
        "risk_level": risk,
    }


def _signature_id(signature: dict[str, str]) -> str:
    canonical = json.dumps(signature, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


# ─── Data models ─────────────────────────────────────────────────


@dataclass
class StrategyPrototype:
    """A generalized strategy pattern extracted from execution history."""

    prototype_id: str
    signature: dict[str, str]
    action_pattern: tuple[str, ...]
    success_rate: float
    avg_credit: float
    sample_count: int
    confidence: float
    domains: set[str]

    def to_dict(self) -> dict:
        return {
            "prototype_id": self.prototype_id,
            "signature": dict(self.signature),
            "action_pattern": list(self.action_pattern),
            "success_rate": round(self.success_rate, 4),
            "avg_credit": round(self.avg_credit, 4),
            "sample_count": self.sample_count,
            "confidence": round(self.confidence, 4),
            "domains": sorted(self.domains),
        }

    @classmethod
    def from_dict(cls, d: dict) -> StrategyPrototype:
        return cls(
            prototype_id=d["prototype_id"],
            signature=d["signature"],
            action_pattern=tuple(d.get("action_pattern", ())),
            success_rate=d.get("success_rate", 0.0),
            avg_credit=d.get("avg_credit", 0.0),
            sample_count=d.get("sample_count", 0),
            confidence=d.get("confidence", 0.0),
            domains=set(d.get("domains", ())),
        )


@dataclass(frozen=True)
class StrategyAbstractionResult:
    """Output from extract_strategy_prototypes()."""

    prototypes_created: int
    prototypes_updated: int
    signals_generated: int

    def to_dict(self) -> dict:
        return {
            "prototypes_created": self.prototypes_created,
            "prototypes_updated": self.prototypes_updated,
            "signals_generated": self.signals_generated,
        }


@dataclass(frozen=True)
class StrategyBias:
    """Bounded bias output from transfer matching."""

    prototype_id: str | None
    match_score: float
    bias: dict[str, float]
    applied: bool
    reason: str

    def to_dict(self) -> dict:
        return {
            "prototype_id": self.prototype_id,
            "match_score": round(self.match_score, 4),
            "bias": {k: round(v, 6) for k, v in self.bias.items()},
            "applied": self.applied,
            "reason": self.reason,
        }


NO_BIAS = StrategyBias(
    prototype_id=None,
    match_score=0.0,
    bias={},
    applied=False,
    reason="no_match",
)


# ─── Prototype store ─────────────────────────────────────────────


class StrategyPrototypeStore:
    """In-memory store for strategy prototypes."""

    def __init__(self) -> None:
        self._prototypes: dict[str, StrategyPrototype] = {}

    @property
    def count(self) -> int:
        return len(self._prototypes)

    def get(self, prototype_id: str) -> StrategyPrototype | None:
        return self._prototypes.get(prototype_id)

    def get_all(self) -> list[StrategyPrototype]:
        return list(self._prototypes.values())

    def get_transferable(self) -> list[StrategyPrototype]:
        """Return prototypes that meet minimum thresholds for transfer."""
        return [
            p
            for p in self._prototypes.values()
            if p.sample_count >= MIN_SAMPLE_COUNT
            and p.confidence >= MIN_CONFIDENCE_FOR_TRANSFER
        ]

    def upsert(self, prototype: StrategyPrototype) -> bool:
        """Insert or update a prototype. Returns True if new."""
        is_new = prototype.prototype_id not in self._prototypes
        self._prototypes[prototype.prototype_id] = prototype
        if len(self._prototypes) > MAX_PROTOTYPES:
            self._evict_weakest()
        return is_new

    def _evict_weakest(self) -> None:
        if not self._prototypes:
            return
        weakest_id = min(
            self._prototypes,
            key=lambda pid: (
                self._prototypes[pid].sample_count,
                self._prototypes[pid].confidence,
            ),
        )
        del self._prototypes[weakest_id]

    def to_dict(self) -> dict:
        return {pid: p.to_dict() for pid, p in self._prototypes.items()}

    def reset(self) -> None:
        self._prototypes.clear()


# ─── Prototype extraction ─────────────────────────────────────────


def _extract_action_type(trace: object) -> str:
    at = getattr(trace, "executable_action_type", None)
    if at:
        return at
    strategy = getattr(trace, "selected_strategy", "")
    return strategy or "unknown"


def _extract_domain(trace: object) -> str:
    return getattr(trace, "executable_domain", None) or "unknown"


def _trace_has_credit(trace: object) -> bool:
    ec = getattr(trace, "effective_credit", None)
    return ec is not None


def _compute_prototype_id(
    signature: dict[str, str], action_pattern: tuple[str, ...]
) -> str:
    canonical = json.dumps(
        {"sig": signature, "pat": list(action_pattern)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def extract_strategy_prototypes(
    recent_history: list[object],
    store: StrategyPrototypeStore,
) -> StrategyAbstractionResult:
    """Extract and update strategy prototypes from recent execution history.

    Groups traces by context signature + action type, compresses
    repeated patterns into prototypes with EMA-updated statistics.
    """
    created = 0
    updated = 0

    groups: dict[str, list[object]] = {}
    for trace in recent_history:
        if not _trace_has_credit(trace):
            continue
        sig = extract_context_signature(trace)
        action_type = _extract_action_type(trace)
        key = _signature_id(sig) + ":" + action_type
        groups.setdefault(key, []).append(trace)

    for key, traces in groups.items():
        if len(traces) < 2:
            continue

        representative = traces[0]
        signature = extract_context_signature(representative)
        action_type = _extract_action_type(representative)
        action_pattern = tuple(sorted(set(_extract_action_type(t) for t in traces)))

        credits = [getattr(t, "effective_credit", 0.0) or 0.0 for t in traces]
        outcomes = [getattr(t, "feedback_outcome_type", "unknown") for t in traces]

        successes = sum(1 for o in outcomes if o == "success")
        batch_success_rate = successes / len(outcomes) if outcomes else 0.0
        batch_avg_credit = sum(credits) / len(credits) if credits else 0.0

        domains = set()
        for t in traces:
            d = _extract_domain(t)
            if d != "unknown":
                domains.add(d)

        prototype_id = _compute_prototype_id(signature, action_pattern)
        existing = store.get(prototype_id)

        if existing is not None:
            new_count = existing.sample_count + len(traces)
            new_success_rate = (
                1.0 - EMA_ALPHA
            ) * existing.success_rate + EMA_ALPHA * batch_success_rate
            new_avg_credit = (
                1.0 - EMA_ALPHA
            ) * existing.avg_credit + EMA_ALPHA * batch_avg_credit
            new_confidence = min(1.0, new_count / (new_count + 10.0))
            new_domains = existing.domains | domains

            proto = StrategyPrototype(
                prototype_id=prototype_id,
                signature=signature,
                action_pattern=action_pattern,
                success_rate=new_success_rate,
                avg_credit=new_avg_credit,
                sample_count=new_count,
                confidence=new_confidence,
                domains=new_domains,
            )
            store.upsert(proto)
            updated += 1
        else:
            confidence = min(1.0, len(traces) / (len(traces) + 10.0))
            proto = StrategyPrototype(
                prototype_id=prototype_id,
                signature=signature,
                action_pattern=action_pattern,
                success_rate=batch_success_rate,
                avg_credit=batch_avg_credit,
                sample_count=len(traces),
                confidence=confidence,
                domains=domains,
            )
            store.upsert(proto)
            created += 1

    return StrategyAbstractionResult(
        prototypes_created=created,
        prototypes_updated=updated,
        signals_generated=created + updated,
    )


# ─── Context matching ────────────────────────────────────────────


def _match_score(current_sig: dict[str, str], proto_sig: dict[str, str]) -> float:
    """Compute match score between current context and prototype signature.

    Exact categorical match on each dimension scores 1/N.
    Total is [0.0, 1.0].
    """
    if not proto_sig:
        return 0.0
    keys = set(current_sig.keys()) | set(proto_sig.keys())
    if not keys:
        return 0.0
    matches = sum(1 for k in keys if current_sig.get(k) == proto_sig.get(k))
    return matches / len(keys)


# ─── Transfer / bias generation ───────────────────────────────────


def _clamp_bias(v: float) -> float:
    return max(-BIAS_BOUND, min(BIAS_BOUND, v))


def generate_strategy_bias(
    current_trace: object,
    store: StrategyPrototypeStore,
) -> StrategyBias:
    """Generate bounded strategy bias from prototype matching.

    Matches current context against transferable prototypes.
    If best match exceeds threshold, generates additive bias
    for strategies in the matching action pattern.

    Conflicting prototypes (positive and negative avg_credit
    with similar match scores) cancel out.
    """
    current_sig = extract_context_signature(current_trace)
    transferable = store.get_transferable()

    if not transferable:
        return NO_BIAS

    scored: list[tuple[float, StrategyPrototype]] = []
    for proto in transferable:
        score = _match_score(current_sig, proto.signature)
        if score >= MIN_MATCH_SCORE_FOR_BIAS:
            scored.append((score, proto))

    if not scored:
        return NO_BIAS

    scored.sort(key=lambda x: (-x[0], -x[1].confidence))

    if len(scored) >= 2:
        top_score, top_proto = scored[0]
        second_score, second_proto = scored[1]
        if abs(top_score - second_score) < 0.1:
            if (top_proto.avg_credit > 0) != (second_proto.avg_credit > 0):
                return StrategyBias(
                    prototype_id=None,
                    match_score=top_score,
                    bias={},
                    applied=False,
                    reason="conflicting_prototypes_cancelled",
                )

    best_score, best_proto = scored[0]

    bias: dict[str, float] = {}
    for action_type in best_proto.action_pattern:
        raw = best_proto.avg_credit * BIAS_SCALE * best_proto.confidence
        bias[action_type] = _clamp_bias(raw)

    return StrategyBias(
        prototype_id=best_proto.prototype_id,
        match_score=best_score,
        bias=bias,
        applied=True,
        reason=f"matched:{best_proto.prototype_id}",
    )


if __name__ == "__main__":
    print("strategy_abstraction import OK")
