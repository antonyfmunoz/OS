"""
Signal orchestration — coordinate and dynamically weight adaptation signals.

Evaluates agreement across all active signals, scales influence based on
consensus, suppresses conflicting signals, and amplifies aligned ones.
Produces a single coherent combined bias from many independent sources.

NOT adding intelligence. Coordinating intelligence.

Stateless — reads signal objects, produces an OrchestratedSignal.
Deterministic. Bounded. No LLM calls. No randomness.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ─── Constants ──────────────────────────────────────────────────────

MAX_COMBINED_BIAS = 0.05
CONSENSUS_THRESHOLD = 0.3
HIGH_SCALE_MIN = 0.8
MEDIUM_SCALE_MIN = 0.4
LOW_SCALE_MAX = 0.3
ALIGNMENT_THRESHOLD = 0.2
CONFLICT_THRESHOLD = -0.2
VARIANCE_PENALTY_SCALE = 2.0
MIN_ACTIVE_SIGNALS = 2

PRIORITY_ORDER: tuple[str, ...] = (
    "stability_guard",
    "trap_recovery",
    "context_engine",
    "causal_memory",
    "credit_assignment",
    "foresight_engine",
    "meta_generalization",
    "exploration_engine",
)


# ─── Helpers ────────────────────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between two action-bias dicts."""
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    dot = 0.0
    mag_a = 0.0
    mag_b = 0.0
    for k in keys:
        va = a.get(k, 0.0)
        vb = b.get(k, 0.0)
        dot += va * vb
        mag_a += va * va
        mag_b += vb * vb
    denom = math.sqrt(mag_a) * math.sqrt(mag_b)
    if denom < 1e-12:
        return 0.0
    return dot / denom


def _sign_agreement_ratio(vectors: list[dict[str, float]]) -> float:
    """Proportion of action-sign pairs where all signals agree."""
    if len(vectors) < 2:
        return 1.0
    all_keys: set[str] = set()
    for v in vectors:
        all_keys.update(v.keys())
    if not all_keys:
        return 1.0
    agree_count = 0
    total_count = 0
    for key in all_keys:
        signs: list[int] = []
        for v in vectors:
            val = v.get(key, 0.0)
            if abs(val) > 1e-9:
                signs.append(1 if val > 0 else -1)
        if len(signs) >= 2:
            total_count += 1
            if all(s == signs[0] for s in signs):
                agree_count += 1
    if total_count == 0:
        return 1.0
    return agree_count / total_count


def _bias_variance(vectors: list[dict[str, float]]) -> float:
    """Average variance of bias values across signals per action."""
    all_keys: set[str] = set()
    for v in vectors:
        all_keys.update(v.keys())
    if not all_keys or len(vectors) < 2:
        return 0.0
    total_var = 0.0
    for key in all_keys:
        vals = [v.get(key, 0.0) for v in vectors]
        mean = sum(vals) / len(vals)
        var = sum((x - mean) ** 2 for x in vals) / len(vals)
        total_var += var
    return total_var / len(all_keys)


# ─── Data structures ───────────────────────────────────────────────


@dataclass(frozen=True)
class SignalBundle:
    """All adaptation signals collected for one decision turn.

    Each signal may be None if the source engine was not active or
    produced no output. The orchestrator handles partial availability.
    """

    meta_signal: object | None = None
    context_signal: object | None = None
    causal_signal: object | None = None
    credit_signal: object | None = None
    foresight_signal: object | None = None
    exploration_signal: object | None = None
    trap_signal: object | None = None
    stability_signal: object | None = None


@dataclass(frozen=True)
class OrchestratedSignal:
    """Output of signal orchestration: unified, scaled, conflict-resolved."""

    combined_action_bias: dict[str, float]
    total_confidence: float
    consensus_score: float
    active_signals: tuple[str, ...]
    suppressed_signals: tuple[str, ...]
    dominant_signal_source: str
    scale_factors: dict[str, float]
    reason: str

    def to_dict(self) -> dict:
        d: dict = {
            "combined_action_bias": {
                k: round(v, 6) for k, v in self.combined_action_bias.items()
            },
            "total_confidence": round(self.total_confidence, 4),
            "consensus_score": round(self.consensus_score, 4),
            "active_signals": list(self.active_signals),
            "suppressed_signals": list(self.suppressed_signals),
            "dominant_signal_source": self.dominant_signal_source,
            "reason": self.reason,
        }
        if self.scale_factors:
            d["scale_factors"] = {k: round(v, 4) for k, v in self.scale_factors.items()}
        return d


NO_ORCHESTRATED_SIGNAL = OrchestratedSignal(
    combined_action_bias={},
    total_confidence=0.0,
    consensus_score=0.0,
    active_signals=(),
    suppressed_signals=(),
    dominant_signal_source="",
    scale_factors={},
    reason="no_signals",
)


# ─── Signal extraction ─────────────────────────────────────────────


def _extract_action_bias(name: str, signal: object | None) -> dict[str, float] | None:
    """Normalize heterogeneous signals into action→bias dicts."""
    if signal is None:
        return None

    if name == "meta_generalization":
        priors = getattr(signal, "priors", None)
        if priors and isinstance(priors, dict) and getattr(signal, "matched", False):
            return dict(priors)
        return None

    if name == "context_engine":
        return None

    if name == "causal_memory":
        ab = getattr(signal, "action_bias", None)
        if ab and isinstance(ab, dict):
            return dict(ab)
        return None

    if name == "credit_assignment":
        ac = getattr(signal, "action_credit", None)
        if ac and isinstance(ac, dict):
            return dict(ac)
        return None

    if name == "foresight_engine":
        ab = getattr(signal, "action_bias", None)
        if ab and isinstance(ab, dict):
            return dict(ab)
        return None

    if name == "exploration_engine":
        adj = getattr(signal, "exploration_adjustments", None)
        if adj and isinstance(adj, dict):
            active = getattr(signal, "exploration_active", False)
            if active:
                return dict(adj)
        return None

    if name == "trap_recovery":
        active = getattr(signal, "active", False)
        dominant = getattr(signal, "dominant_action", None)
        adj = getattr(signal, "trap_adjustment", 0.0)
        if active and dominant and abs(adj) > 1e-9:
            return {dominant: -adj}
        return None

    if name == "stability_guard":
        active = getattr(signal, "active", False)
        if not active:
            return None
        exp_adj = getattr(signal, "exploration_adjustment", 0.0)
        if abs(exp_adj) > 1e-9:
            return {"__stability_dampen__": exp_adj}
        return None

    return None


def _extract_confidence(name: str, signal: object | None) -> float:
    """Extract confidence from a signal, defaulting to a moderate value."""
    if signal is None:
        return 0.0

    conf = getattr(signal, "confidence", None)
    if conf is not None and isinstance(conf, (int, float)):
        return float(conf)

    if name == "trap_recovery":
        if getattr(signal, "active", False):
            mismatch = getattr(signal, "reward_mismatch", 0.0)
            return _clamp(float(mismatch), 0.0, 1.0) if mismatch else 0.5
        return 0.0

    if name == "stability_guard":
        if getattr(signal, "active", False):
            sr = getattr(signal, "switch_rate", 0.0)
            return _clamp(float(sr), 0.0, 1.0) if sr else 0.5
        return 0.0

    if name == "exploration_engine":
        return getattr(signal, "activation_strength", 0.0) or 0.0

    if name == "meta_generalization":
        return getattr(signal, "similarity", 0.0) or 0.0

    return 0.0


# ─── Engine ─────────────────────────────────────────────────────────


class SignalOrchestrator:
    """Stateless signal coordination engine.

    Evaluates agreement across active adaptation signals, computes
    per-signal scaling factors, resolves conflicts by priority,
    and produces a single unified action bias.
    """

    def orchestrate(
        self,
        bundle: SignalBundle,
        strategy_scores: dict[str, float] | None = None,
    ) -> OrchestratedSignal:
        """Coordinate all signals in the bundle into a unified output."""

        signal_map = {
            "meta_generalization": bundle.meta_signal,
            "context_engine": bundle.context_signal,
            "causal_memory": bundle.causal_signal,
            "credit_assignment": bundle.credit_signal,
            "foresight_engine": bundle.foresight_signal,
            "exploration_engine": bundle.exploration_signal,
            "trap_recovery": bundle.trap_signal,
            "stability_guard": bundle.stability_signal,
        }

        # ── 1. Extract action biases from all signals ──────────────
        bias_vectors: dict[str, dict[str, float]] = {}
        confidences: dict[str, float] = {}

        for name, signal in signal_map.items():
            bias = _extract_action_bias(name, signal)
            if bias is not None:
                bias_vectors[name] = bias
                confidences[name] = _extract_confidence(name, signal)

        if not bias_vectors:
            return NO_ORCHESTRATED_SIGNAL

        if len(bias_vectors) == 1:
            name = next(iter(bias_vectors))
            single_bias = bias_vectors[name]
            conf = confidences.get(name, 0.0)
            combined = self._clamp_combined(single_bias, strategy_scores)
            return OrchestratedSignal(
                combined_action_bias=combined,
                total_confidence=conf,
                consensus_score=1.0,
                active_signals=(name,),
                suppressed_signals=(),
                dominant_signal_source=name,
                scale_factors={name: 1.0},
                reason="single_signal",
            )

        # ── 2. Agreement analysis ──────────────────────────────────
        action_biases = list(bias_vectors.values())
        names = list(bias_vectors.keys())

        avg_similarity = self._avg_pairwise_similarity(action_biases)
        sign_agree = _sign_agreement_ratio(action_biases)
        variance = _bias_variance(action_biases)
        variance_penalty = _clamp(
            1.0 / (1.0 + variance * VARIANCE_PENALTY_SCALE), 0.0, 1.0
        )

        # ── 3. Consensus score ─────────────────────────────────────
        consensus_score = _clamp(
            0.4 * avg_similarity + 0.35 * sign_agree + 0.25 * variance_penalty,
            0.0,
            1.0,
        )

        # ── 4. Compute per-signal alignment with consensus ─────────
        consensus_vector = self._compute_consensus_vector(action_biases)
        alignments: dict[str, float] = {}
        for i, name in enumerate(names):
            alignments[name] = _cosine_similarity(action_biases[i], consensus_vector)

        # ── 5. Scale factors ───────────────────────────────────────
        scale_factors: dict[str, float] = {}
        suppressed: list[str] = []

        for name in names:
            alignment = alignments.get(name, 0.0)
            conf = confidences.get(name, 0.0)

            if alignment > ALIGNMENT_THRESHOLD:
                base_scale = HIGH_SCALE_MIN + (1.0 - HIGH_SCALE_MIN) * alignment
            elif alignment < CONFLICT_THRESHOLD:
                base_scale = LOW_SCALE_MAX * max(0.0, 1.0 + alignment)
            else:
                base_scale = MEDIUM_SCALE_MIN + (HIGH_SCALE_MIN - MEDIUM_SCALE_MIN) * (
                    (alignment - CONFLICT_THRESHOLD)
                    / (ALIGNMENT_THRESHOLD - CONFLICT_THRESHOLD)
                )

            scale = base_scale * max(consensus_score, 0.1)

            if scale < 0.05 and alignment < CONFLICT_THRESHOLD:
                suppressed.append(name)
                scale_factors[name] = 0.0
            else:
                scale_factors[name] = _clamp(scale, 0.0, 1.0)

        # ── 6. Conflict resolution by priority ─────────────────────
        if (
            consensus_score < CONSENSUS_THRESHOLD
            and len(bias_vectors) >= MIN_ACTIVE_SIGNALS
        ):
            suppressed = self._suppress_by_priority(
                names, confidences, scale_factors, suppressed
            )
            for name in names:
                if name not in suppressed and scale_factors.get(name, 0.0) < 0.05:
                    scale_factors[name] = _clamp(
                        confidences.get(name, 0.0) * 0.3, 0.05, 0.3
                    )

        # ── 7. Combine scaled biases ───────────────────────────────
        combined: dict[str, float] = {}
        active: list[str] = []
        dominant_source = ""
        max_contribution = 0.0

        for name in names:
            if name in suppressed:
                continue
            sf = scale_factors.get(name, 0.0)
            if sf < 1e-9:
                continue

            active.append(name)
            bias = bias_vectors[name]
            contribution = 0.0

            for action, val in bias.items():
                if action.startswith("__"):
                    continue
                scaled_val = val * sf
                combined[action] = combined.get(action, 0.0) + scaled_val
                contribution += abs(scaled_val)

            if contribution > max_contribution:
                max_contribution = contribution
                dominant_source = name

        # ── 8. Apply combined bias cap + leader protection ─────────
        combined = self._clamp_combined(combined, strategy_scores)

        if not combined:
            return OrchestratedSignal(
                combined_action_bias={},
                total_confidence=0.0,
                consensus_score=consensus_score,
                active_signals=tuple(active),
                suppressed_signals=tuple(suppressed),
                dominant_signal_source=dominant_source,
                scale_factors=scale_factors,
                reason="biases_cancelled",
            )

        # ── 9. Total confidence ────────────────────────────────────
        total_confidence = self._compute_total_confidence(
            active, confidences, consensus_score
        )

        # ── 10. Low consensus reduction ────────────────────────────
        if consensus_score < CONSENSUS_THRESHOLD:
            reduction = consensus_score / CONSENSUS_THRESHOLD
            combined = {k: v * reduction for k, v in combined.items()}
            combined = {k: v for k, v in combined.items() if abs(v) > 1e-9}
            total_confidence *= reduction

        if not combined:
            return OrchestratedSignal(
                combined_action_bias={},
                total_confidence=total_confidence,
                consensus_score=consensus_score,
                active_signals=tuple(active),
                suppressed_signals=tuple(suppressed),
                dominant_signal_source=dominant_source,
                scale_factors=scale_factors,
                reason="consensus_too_low",
            )

        return OrchestratedSignal(
            combined_action_bias=combined,
            total_confidence=total_confidence,
            consensus_score=consensus_score,
            active_signals=tuple(active),
            suppressed_signals=tuple(suppressed),
            dominant_signal_source=dominant_source,
            scale_factors=scale_factors,
            reason="orchestrated",
        )

    # ─── Internal methods ──────────────────────────────────────────

    def _avg_pairwise_similarity(self, vectors: list[dict[str, float]]) -> float:
        n = len(vectors)
        if n < 2:
            return 1.0
        total = 0.0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                total += _cosine_similarity(vectors[i], vectors[j])
                count += 1
        return total / count if count > 0 else 0.0

    def _compute_consensus_vector(
        self, vectors: list[dict[str, float]]
    ) -> dict[str, float]:
        """Mean of all bias vectors — the centroid direction."""
        if not vectors:
            return {}
        all_keys: set[str] = set()
        for v in vectors:
            all_keys.update(v.keys())
        consensus: dict[str, float] = {}
        for key in all_keys:
            total = sum(v.get(key, 0.0) for v in vectors)
            avg = total / len(vectors)
            if abs(avg) > 1e-9:
                consensus[key] = avg
        return consensus

    def _suppress_by_priority(
        self,
        names: list[str],
        confidences: dict[str, float],
        scale_factors: dict[str, float],
        already_suppressed: list[str],
    ) -> list[str]:
        """When consensus is low, suppress lower-priority weaker signals."""
        suppressed = list(already_suppressed)

        priority_rank: dict[str, int] = {
            name: i for i, name in enumerate(PRIORITY_ORDER)
        }

        ranked = sorted(
            [n for n in names if n not in suppressed],
            key=lambda n: (priority_rank.get(n, 99), -confidences.get(n, 0.0)),
        )

        if len(ranked) <= 1:
            return suppressed

        keep_count = max(1, len(ranked) // 2)
        for name in ranked[keep_count:]:
            conf = confidences.get(name, 0.0)
            sf = scale_factors.get(name, 0.0)
            if conf < 0.3 or sf < 0.2:
                suppressed.append(name)
                scale_factors[name] = 0.0

        return suppressed

    def _clamp_combined(
        self,
        combined: dict[str, float],
        strategy_scores: dict[str, float] | None,
    ) -> dict[str, float]:
        """Cap total bias magnitude and protect leader."""
        result: dict[str, float] = {}
        for action, val in combined.items():
            if action.startswith("__"):
                continue
            clamped = _clamp(val, -MAX_COMBINED_BIAS, MAX_COMBINED_BIAS)
            if abs(clamped) > 1e-9:
                result[action] = clamped

        if strategy_scores and result:
            sorted_scores = sorted(strategy_scores.values(), reverse=True)
            if len(sorted_scores) >= 2:
                leader_gap = sorted_scores[0] - sorted_scores[1]
                if leader_gap > MAX_COMBINED_BIAS:
                    leader_action = None
                    for act, sc in strategy_scores.items():
                        if sc == sorted_scores[0]:
                            leader_action = act
                            break
                    if leader_action and leader_action in result:
                        if result[leader_action] < 0:
                            del result[leader_action]

        return result

    def _compute_total_confidence(
        self,
        active: list[str],
        confidences: dict[str, float],
        consensus_score: float,
    ) -> float:
        if not active:
            return 0.0
        avg_conf = sum(confidences.get(n, 0.0) for n in active) / len(active)
        signal_count_factor = _clamp(len(active) / 4.0, 0.0, 1.0)
        return _clamp(
            0.5 * avg_conf + 0.3 * consensus_score + 0.2 * signal_count_factor,
            0.0,
            1.0,
        )


# ─── Pipeline integration ──────────────────────────────────────────


def apply_orchestrated_signal(
    strategy_scores: dict[str, float],
    signal: OrchestratedSignal,
) -> dict[str, float]:
    """Apply orchestrated combined biases to strategy scores.

    Rules:
    - additive only
    - bounded ±MAX_COMBINED_BIAS
    - cannot invert clear winner
    - scaled by total confidence
    """
    if not signal.combined_action_bias:
        return strategy_scores
    if not strategy_scores:
        return strategy_scores

    adjusted = dict(strategy_scores)
    for action, bias in signal.combined_action_bias.items():
        if action in adjusted:
            adjusted[action] = adjusted[action] + bias

    return adjusted
