"""
Cross-scenario meta-learning — learns reusable adaptation patterns.

Computes a ScenarioSignature from bounded history, matches it against
learned ScenarioPrototypes, and produces bounded priors that accelerate
adaptation when a new scenario resembles one already seen.

If no prototype matches, behavior is identical to the system without
this layer — zero priors, zero bias, full backward compatibility.

Deterministic. Bounded. No LLM calls. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ─── Constants ──────────────────────────────────────────────────────

SIGNATURE_WINDOW = 50
LONG_SIGNATURE_WINDOW = 200
MIN_OBSERVATIONS_FOR_SIGNATURE = 15
MAX_PROTOTYPES = 12
PROTOTYPE_EMA_ALPHA = 0.1
SIMILARITY_THRESHOLD = 0.70
MERGE_SIMILARITY_THRESHOLD = 0.90
MIN_PROTOTYPE_USAGE = 3

PRIOR_BOUND_STRATEGY = 0.05
PRIOR_BOUND_POLICY = 0.03
PRIOR_BOUND_EXPLORATION = 0.05
PRIOR_BOUND_CONFIDENCE = 0.03

SIGNATURE_DIMS = 8


# ─── Helpers ────────────────────────────────────────────────────────


def _clamp(v: float, lo: float, hi: float) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def _linear_slope(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = 0.0
    den = 0.0
    for i, y in enumerate(values):
        dx = i - x_mean
        num += dx * (y - y_mean)
        den += dx * dx
    if den == 0.0:
        return 0.0
    return num / den


def _switch_rate(actions: list[str]) -> float:
    if len(actions) < 2:
        return 0.0
    switches = sum(1 for i in range(1, len(actions)) if actions[i] != actions[i - 1])
    return switches / (len(actions) - 1)


def _variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def _unique_ratio(actions: list[str]) -> float:
    if not actions:
        return 0.0
    return len(set(actions)) / len(actions)


# ─── Data structures ───────────────────────────────────────────────


@dataclass(frozen=True)
class ScenarioSignature:
    """Fixed-dimension fingerprint of an environment class.

    All dimensions normalized to [0, 1].
    """

    avg_reward: float
    reward_volatility: float
    reward_trend: float
    action_switch_rate: float
    action_diversity: float
    peak_drop: float
    recent_vs_long_avg: float
    trend_reversal_count: float

    def to_tuple(self) -> tuple[float, ...]:
        return (
            self.avg_reward,
            self.reward_volatility,
            self.reward_trend,
            self.action_switch_rate,
            self.action_diversity,
            self.peak_drop,
            self.recent_vs_long_avg,
            self.trend_reversal_count,
        )

    def to_dict(self) -> dict:
        return {
            "avg_reward": round(self.avg_reward, 4),
            "reward_volatility": round(self.reward_volatility, 4),
            "reward_trend": round(self.reward_trend, 4),
            "action_switch_rate": round(self.action_switch_rate, 4),
            "action_diversity": round(self.action_diversity, 4),
            "peak_drop": round(self.peak_drop, 4),
            "recent_vs_long_avg": round(self.recent_vs_long_avg, 4),
            "trend_reversal_count": round(self.trend_reversal_count, 4),
        }


@dataclass
class ScenarioPrototype:
    """Learned cluster representing a class of environments."""

    prototype_id: int
    centroid: list[float]
    usage_count: int = 0
    total_reward: float = 0.0
    success_profile: dict[str, float] = field(default_factory=dict)
    learned_priors: dict[str, float] = field(default_factory=dict)

    @property
    def avg_reward(self) -> float:
        if self.usage_count == 0:
            return 0.0
        return self.total_reward / self.usage_count

    def to_dict(self) -> dict:
        return {
            "prototype_id": self.prototype_id,
            "centroid": [round(c, 6) for c in self.centroid],
            "usage_count": self.usage_count,
            "total_reward": round(self.total_reward, 6),
            "success_profile": {
                k: round(v, 6) for k, v in self.success_profile.items()
            },
            "learned_priors": {k: round(v, 6) for k, v in self.learned_priors.items()},
        }


@dataclass(frozen=True)
class GeneralizationResult:
    """Output of meta-generalization: matched prototype + bounded priors."""

    matched: bool
    prototype_id: int | None
    similarity: float
    signature: ScenarioSignature | None
    priors: dict[str, float]
    prototype_usage_count: int
    prototype_avg_reward: float

    def to_dict(self) -> dict:
        d: dict = {
            "matched": self.matched,
            "similarity": round(self.similarity, 4),
        }
        if self.matched:
            d["prototype_id"] = self.prototype_id
            d["prototype_usage_count"] = self.prototype_usage_count
            d["prototype_avg_reward"] = round(self.prototype_avg_reward, 4)
        if self.priors:
            d["priors"] = {k: round(v, 6) for k, v in self.priors.items()}
        if self.signature is not None:
            d["signature"] = self.signature.to_dict()
        return d


NO_GENERALIZATION = GeneralizationResult(
    matched=False,
    prototype_id=None,
    similarity=0.0,
    signature=None,
    priors={},
    prototype_usage_count=0,
    prototype_avg_reward=0.0,
)


# ─── Signature computation ──────────────────────────────────────────


def compute_scenario_signature(
    recent_actions: list[str],
    recent_rewards: list[float],
) -> ScenarioSignature | None:
    """Compute a fixed-dimension scenario fingerprint from bounded history."""
    if len(recent_rewards) < MIN_OBSERVATIONS_FOR_SIGNATURE:
        return None

    window_rewards = recent_rewards[-SIGNATURE_WINDOW:]
    window_actions = recent_actions[-SIGNATURE_WINDOW:]
    long_rewards = recent_rewards[-LONG_SIGNATURE_WINDOW:]

    avg_r = sum(window_rewards) / len(window_rewards)
    avg_reward = _clamp(avg_r, 0.0, 1.0)

    var = _variance(window_rewards)
    reward_volatility = _clamp(var * 4.0, 0.0, 1.0)

    slope = _linear_slope(window_rewards)
    reward_trend = _clamp((slope * 10.0 + 1.0) / 2.0, 0.0, 1.0)

    sr = _switch_rate(window_actions)
    action_switch_rate = _clamp(sr, 0.0, 1.0)

    action_diversity = _clamp(_unique_ratio(window_actions), 0.0, 1.0)

    peak = max(long_rewards) if long_rewards else 1.0
    if peak <= 0.0:
        peak = 1.0
    peak_drop = _clamp(1.0 - (avg_r / peak), 0.0, 1.0)

    if len(long_rewards) >= SIGNATURE_WINDOW:
        long_avg = sum(long_rewards) / len(long_rewards)
        if long_avg > 0.0:
            recent_vs_long_avg = _clamp(avg_r / long_avg, 0.0, 2.0) / 2.0
        else:
            recent_vs_long_avg = 0.5
    else:
        recent_vs_long_avg = 0.5

    reversals = 0
    if len(window_rewards) >= 6:
        chunk_size = max(3, len(window_rewards) // 6)
        prev_direction = 0
        for ci in range(0, len(window_rewards) - chunk_size, chunk_size):
            chunk = window_rewards[ci : ci + chunk_size]
            chunk_avg = sum(chunk) / len(chunk)
            next_chunk = window_rewards[ci + chunk_size : ci + 2 * chunk_size]
            if not next_chunk:
                break
            next_avg = sum(next_chunk) / len(next_chunk)
            direction = (
                1
                if next_avg > chunk_avg + 0.01
                else (-1 if next_avg < chunk_avg - 0.01 else 0)
            )
            if prev_direction != 0 and direction != 0 and direction != prev_direction:
                reversals += 1
            if direction != 0:
                prev_direction = direction
    max_possible_reversals = max(1, len(window_rewards) // 6)
    trend_reversal_count = _clamp(reversals / max_possible_reversals, 0.0, 1.0)

    return ScenarioSignature(
        avg_reward=avg_reward,
        reward_volatility=reward_volatility,
        reward_trend=reward_trend,
        action_switch_rate=action_switch_rate,
        action_diversity=action_diversity,
        peak_drop=peak_drop,
        recent_vs_long_avg=recent_vs_long_avg,
        trend_reversal_count=trend_reversal_count,
    )


# ─── Similarity ─────────────────────────────────────────────────────


def _cosine_similarity(
    a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]
) -> float:
    dot = sum(ai * bi for ai, bi in zip(a, b))
    mag_a = sum(ai * ai for ai in a) ** 0.5
    mag_b = sum(bi * bi for bi in b) ** 0.5
    if mag_a < 1e-12 or mag_b < 1e-12:
        return 0.0
    return dot / (mag_a * mag_b)


def _euclidean_similarity(
    a: list[float] | tuple[float, ...], b: list[float] | tuple[float, ...]
) -> float:
    dist_sq = sum((ai - bi) ** 2 for ai, bi in zip(a, b))
    dist = dist_sq**0.5
    max_dist = len(a) ** 0.5
    if max_dist < 1e-12:
        return 0.0
    return _clamp(1.0 - dist / max_dist, 0.0, 1.0)


def compute_similarity(sig: ScenarioSignature, centroid: list[float]) -> float:
    sig_vec = sig.to_tuple()
    cos = _cosine_similarity(sig_vec, centroid)
    euc = _euclidean_similarity(sig_vec, centroid)
    return 0.5 * cos + 0.5 * euc


# ─── Engine ─────────────────────────────────────────────────────────


class MetaGeneralizationEngine:
    """Learns and matches scenario prototypes for cross-scenario transfer.

    Bounded to MAX_PROTOTYPES prototypes. EMA centroid updates.
    Deterministic similarity matching. All priors hard-capped.
    """

    def __init__(self) -> None:
        self._prototypes: list[ScenarioPrototype] = []
        self._next_id: int = 0
        self._observations: int = 0

    @property
    def prototype_count(self) -> int:
        return len(self._prototypes)

    def classify(
        self,
        recent_actions: list[str],
        recent_rewards: list[float],
    ) -> GeneralizationResult:
        """Match current environment against learned prototypes."""
        sig = compute_scenario_signature(recent_actions, recent_rewards)
        if sig is None:
            return NO_GENERALIZATION

        if not self._prototypes:
            return GeneralizationResult(
                matched=False,
                prototype_id=None,
                similarity=0.0,
                signature=sig,
                priors={},
                prototype_usage_count=0,
                prototype_avg_reward=0.0,
            )

        best_proto: ScenarioPrototype | None = None
        best_sim = 0.0
        for proto in self._prototypes:
            sim = compute_similarity(sig, proto.centroid)
            if sim > best_sim:
                best_sim = sim
                best_proto = proto

        if best_sim < SIMILARITY_THRESHOLD or best_proto is None:
            return GeneralizationResult(
                matched=False,
                prototype_id=None,
                similarity=best_sim,
                signature=sig,
                priors={},
                prototype_usage_count=0,
                prototype_avg_reward=0.0,
            )

        if best_proto.usage_count < MIN_PROTOTYPE_USAGE:
            return GeneralizationResult(
                matched=False,
                prototype_id=best_proto.prototype_id,
                similarity=best_sim,
                signature=sig,
                priors={},
                prototype_usage_count=best_proto.usage_count,
                prototype_avg_reward=best_proto.avg_reward,
            )

        priors = self._compute_bounded_priors(best_proto, best_sim)

        return GeneralizationResult(
            matched=True,
            prototype_id=best_proto.prototype_id,
            similarity=best_sim,
            signature=sig,
            priors=priors,
            prototype_usage_count=best_proto.usage_count,
            prototype_avg_reward=best_proto.avg_reward,
        )

    def learn(
        self,
        recent_actions: list[str],
        recent_rewards: list[float],
        outcome_reward: float,
        success_profile: dict[str, float] | None = None,
    ) -> None:
        """Update or create a prototype from the current scenario outcome."""
        sig = compute_scenario_signature(recent_actions, recent_rewards)
        if sig is None:
            return

        self._observations += 1
        sig_vec = list(sig.to_tuple())

        matched_proto = self._find_closest(sig_vec)

        if matched_proto is not None:
            sim = compute_similarity(sig, matched_proto.centroid)
            if sim >= SIMILARITY_THRESHOLD:
                self._update_prototype(
                    matched_proto, sig_vec, outcome_reward, success_profile
                )
                self._try_merge()
                return

        if len(self._prototypes) < MAX_PROTOTYPES:
            proto = ScenarioPrototype(
                prototype_id=self._next_id,
                centroid=sig_vec,
                usage_count=1,
                total_reward=outcome_reward,
                success_profile=dict(success_profile) if success_profile else {},
                learned_priors={},
            )
            self._prototypes.append(proto)
            self._next_id += 1
            self._try_merge()
            return

        weakest = min(self._prototypes, key=lambda p: p.usage_count)
        if weakest.usage_count < MIN_PROTOTYPE_USAGE:
            self._prototypes.remove(weakest)
            proto = ScenarioPrototype(
                prototype_id=self._next_id,
                centroid=sig_vec,
                usage_count=1,
                total_reward=outcome_reward,
                success_profile=dict(success_profile) if success_profile else {},
                learned_priors={},
            )
            self._prototypes.append(proto)
            self._next_id += 1
            self._try_merge()
            return

        closest = self._find_closest(sig_vec)
        if closest is not None:
            self._update_prototype(closest, sig_vec, outcome_reward, success_profile)
        self._try_merge()

    def _find_closest(self, sig_vec: list[float]) -> ScenarioPrototype | None:
        if not self._prototypes:
            return None
        best: ScenarioPrototype | None = None
        best_sim = -1.0
        for proto in self._prototypes:
            sim = _euclidean_similarity(sig_vec, proto.centroid)
            if sim > best_sim:
                best_sim = sim
                best = proto
        return best

    def _update_prototype(
        self,
        proto: ScenarioPrototype,
        sig_vec: list[float],
        outcome_reward: float,
        success_profile: dict[str, float] | None,
    ) -> None:
        alpha = PROTOTYPE_EMA_ALPHA
        for i in range(len(proto.centroid)):
            proto.centroid[i] = alpha * sig_vec[i] + (1.0 - alpha) * proto.centroid[i]

        proto.usage_count += 1
        proto.total_reward += outcome_reward

        if success_profile:
            for key, val in success_profile.items():
                old = proto.success_profile.get(key, 0.5)
                proto.success_profile[key] = alpha * val + (1.0 - alpha) * old

        self._update_learned_priors(proto)

    def _update_learned_priors(self, proto: ScenarioPrototype) -> None:
        if proto.usage_count < MIN_PROTOTYPE_USAGE:
            proto.learned_priors = {}
            return

        avg_r = proto.avg_reward

        strategy_prior = _clamp(
            (avg_r - 0.5) * 0.1, -PRIOR_BOUND_STRATEGY, PRIOR_BOUND_STRATEGY
        )
        exploration_prior = _clamp(
            (1.0 - avg_r) * 0.1 - 0.03,
            -PRIOR_BOUND_EXPLORATION,
            PRIOR_BOUND_EXPLORATION,
        )

        volatility = proto.centroid[1] if len(proto.centroid) > 1 else 0.0
        confidence_prior = _clamp(
            (avg_r - 0.5) * 0.06 - volatility * 0.02,
            -PRIOR_BOUND_CONFIDENCE,
            PRIOR_BOUND_CONFIDENCE,
        )

        switch_rate = proto.centroid[3] if len(proto.centroid) > 3 else 0.0
        policy_prior = _clamp(
            (0.5 - switch_rate) * 0.06, -PRIOR_BOUND_POLICY, PRIOR_BOUND_POLICY
        )

        proto.learned_priors = {
            "strategy": strategy_prior,
            "exploration": exploration_prior,
            "confidence": confidence_prior,
            "policy": policy_prior,
        }

    def _compute_bounded_priors(
        self, proto: ScenarioPrototype, similarity: float
    ) -> dict[str, float]:
        if not proto.learned_priors:
            return {}

        scale = _clamp(
            (similarity - SIMILARITY_THRESHOLD) / (1.0 - SIMILARITY_THRESHOLD + 1e-9),
            0.0,
            1.0,
        )

        result: dict[str, float] = {}
        for key, val in proto.learned_priors.items():
            scaled = val * scale
            if key == "strategy":
                scaled = _clamp(scaled, -PRIOR_BOUND_STRATEGY, PRIOR_BOUND_STRATEGY)
            elif key == "policy":
                scaled = _clamp(scaled, -PRIOR_BOUND_POLICY, PRIOR_BOUND_POLICY)
            elif key == "exploration":
                scaled = _clamp(
                    scaled, -PRIOR_BOUND_EXPLORATION, PRIOR_BOUND_EXPLORATION
                )
            elif key == "confidence":
                scaled = _clamp(scaled, -PRIOR_BOUND_CONFIDENCE, PRIOR_BOUND_CONFIDENCE)
            if abs(scaled) > 1e-9:
                result[key] = scaled

        return result

    def _try_merge(self) -> None:
        """Merge prototypes with centroids closer than MERGE_SIMILARITY_THRESHOLD."""
        merged = True
        while merged:
            merged = False
            for i in range(len(self._prototypes)):
                for j in range(i + 1, len(self._prototypes)):
                    sim = _euclidean_similarity(
                        self._prototypes[i].centroid,
                        self._prototypes[j].centroid,
                    )
                    if sim >= MERGE_SIMILARITY_THRESHOLD:
                        self._merge_pair(i, j)
                        merged = True
                        break
                if merged:
                    break

    def _merge_pair(self, i: int, j: int) -> None:
        a = self._prototypes[i]
        b = self._prototypes[j]

        total = a.usage_count + b.usage_count
        if total == 0:
            total = 1
        wa = a.usage_count / total
        wb = b.usage_count / total

        merged_centroid = [
            wa * a.centroid[k] + wb * b.centroid[k] for k in range(len(a.centroid))
        ]

        all_keys = set(a.success_profile) | set(b.success_profile)
        merged_profile: dict[str, float] = {}
        for key in all_keys:
            va = a.success_profile.get(key, 0.5)
            vb = b.success_profile.get(key, 0.5)
            merged_profile[key] = wa * va + wb * vb

        keep = a if a.usage_count >= b.usage_count else b
        remove = b if keep is a else a

        keep.centroid = merged_centroid
        keep.usage_count = total
        keep.total_reward = a.total_reward + b.total_reward
        keep.success_profile = merged_profile
        self._update_learned_priors(keep)

        self._prototypes.remove(remove)

    # ─── Persistence ────────────────────────────────────────────────

    def snapshot(self) -> dict:
        return {
            "version": 1,
            "next_id": self._next_id,
            "observations": self._observations,
            "prototypes": [p.to_dict() for p in self._prototypes],
        }

    def restore(self, data: dict | None) -> None:
        if not data or not isinstance(data, dict):
            return

        self._next_id = int(data.get("next_id", 0))
        self._observations = int(data.get("observations", 0))

        self._prototypes = []
        for pd in data.get("prototypes", []):
            if not isinstance(pd, dict):
                continue
            proto = ScenarioPrototype(
                prototype_id=int(pd.get("prototype_id", 0)),
                centroid=list(pd.get("centroid", [0.0] * SIGNATURE_DIMS)),
                usage_count=int(pd.get("usage_count", 0)),
                total_reward=float(pd.get("total_reward", 0.0)),
                success_profile={
                    k: float(v) for k, v in pd.get("success_profile", {}).items()
                },
                learned_priors={
                    k: float(v) for k, v in pd.get("learned_priors", {}).items()
                },
            )
            self._prototypes.append(proto)

    def reset(self) -> None:
        self.__init__()


# ─── Pipeline integration helpers ───────────────────────────────────


def apply_strategy_priors(
    strategy_scores: dict[str, float],
    result: GeneralizationResult,
) -> dict[str, float]:
    """Apply bounded strategy priors from meta-generalization to scores."""
    if not result.matched or not result.priors:
        return strategy_scores

    prior = result.priors.get("strategy", 0.0)
    if abs(prior) < 1e-9:
        return strategy_scores

    adjusted = dict(strategy_scores)
    for name in adjusted:
        adjusted[name] = adjusted[name] + prior
    return adjusted


def apply_confidence_prior(
    plan_confidence: float | None,
    result: GeneralizationResult,
) -> float | None:
    """Apply bounded confidence prior from meta-generalization."""
    if plan_confidence is None:
        return None
    if not result.matched or not result.priors:
        return plan_confidence

    prior = result.priors.get("confidence", 0.0)
    if abs(prior) < 1e-9:
        return plan_confidence

    return _clamp(plan_confidence + prior, 0.0, 1.0)


def apply_exploration_prior(
    exploration_rate: float | None,
    result: GeneralizationResult,
) -> float | None:
    """Apply bounded exploration prior from meta-generalization."""
    if exploration_rate is None:
        return None
    if not result.matched or not result.priors:
        return exploration_rate

    prior = result.priors.get("exploration", 0.0)
    if abs(prior) < 1e-9:
        return exploration_rate

    return _clamp(exploration_rate + prior, 0.0, 1.0)
