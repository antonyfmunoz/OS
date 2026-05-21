"""IntentCompiler — translates user intent into meta-harness configuration.

Maps natural-language goals and constraints into structured ObjectiveWeights,
risk profiles, exploration policies, and stability biases that drive the
meta-harness. Rule-based, deterministic, compositional.

No LLM. No randomness. No external calls.
"""

from __future__ import annotations

from dataclasses import dataclass


# ─── Constants ──────────────────────────────────────────────────

DEFAULT_RISK_TOLERANCE = 0.5
DEFAULT_HORIZON = 5
MAX_KEYWORDS_MATCHED = 10


# ─── Weight bounds (mirror objective_arbitration.py) ────────────

REWARD_WEIGHT_BOUNDS = (0.3, 0.7)
RISK_WEIGHT_BOUNDS = (0.1, 0.5)
STABILITY_WEIGHT_BOUNDS = (0.1, 0.5)
EXPLORATION_WEIGHT_BOUNDS = (0.0, 0.3)
NOVELTY_WEIGHT_BOUNDS = (0.0, 0.2)


# ─── Data models ───────────────────────────────────────────────


@dataclass(frozen=True)
class IntentInput:
    """Raw user intent before compilation."""

    goal: str
    constraints: tuple[str, ...] = ()
    time_horizon: int = DEFAULT_HORIZON
    risk_tolerance: float = DEFAULT_RISK_TOLERANCE
    priority_weights: dict[str, float] | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "goal": self.goal,
            "time_horizon": self.time_horizon,
            "risk_tolerance": round(self.risk_tolerance, 6),
        }
        if self.constraints:
            d["constraints"] = list(self.constraints)
        if self.priority_weights:
            d["priority_weights"] = {
                k: round(v, 6) for k, v in self.priority_weights.items()
            }
        return d


@dataclass(frozen=True)
class CompiledIntent:
    """Structured output that drives the meta-harness."""

    objective_weights: dict[str, float]
    risk_profile: float
    exploration_policy: float
    stability_bias: float
    horizon_bias: int
    matched_keywords: tuple[str, ...]
    intent_source: str

    def to_dict(self) -> dict:
        return {
            "objective_weights": {
                k: round(v, 6) for k, v in self.objective_weights.items()
            },
            "risk_profile": round(self.risk_profile, 6),
            "exploration_policy": round(self.exploration_policy, 6),
            "stability_bias": round(self.stability_bias, 6),
            "horizon_bias": self.horizon_bias,
            "matched_keywords": list(self.matched_keywords),
            "intent_source": self.intent_source,
        }


DEFAULT_COMPILED = CompiledIntent(
    objective_weights={
        "reward": 0.5,
        "risk": 0.3,
        "stability": 0.3,
        "exploration": 0.0,
        "novelty": 0.0,
    },
    risk_profile=0.5,
    exploration_policy=0.0,
    stability_bias=0.3,
    horizon_bias=DEFAULT_HORIZON,
    matched_keywords=(),
    intent_source="default",
)


# ─── Keyword → weight adjustment tables ─────────────────────


@dataclass(frozen=True)
class _WeightDelta:
    """Adjustment to apply when a keyword matches."""

    reward: float = 0.0
    risk: float = 0.0
    stability: float = 0.0
    exploration: float = 0.0
    novelty: float = 0.0
    risk_profile_adj: float = 0.0
    exploration_policy_adj: float = 0.0
    stability_bias_adj: float = 0.0


_KEYWORD_MAP: dict[str, _WeightDelta] = {
    "grow": _WeightDelta(
        reward=0.15, exploration=0.1, risk=-0.05, exploration_policy_adj=0.1
    ),
    "growth": _WeightDelta(
        reward=0.15, exploration=0.1, risk=-0.05, exploration_policy_adj=0.1
    ),
    "scale": _WeightDelta(
        reward=0.15, exploration=0.1, risk=-0.05, exploration_policy_adj=0.1
    ),
    "revenue": _WeightDelta(reward=0.15, stability=0.05, exploration_policy_adj=0.05),
    "profit": _WeightDelta(reward=0.1, risk=-0.05, stability=0.1),
    "safe": _WeightDelta(
        risk=0.15,
        stability=0.15,
        reward=-0.1,
        risk_profile_adj=-0.2,
        stability_bias_adj=0.15,
    ),
    "safety": _WeightDelta(
        risk=0.15,
        stability=0.15,
        reward=-0.1,
        risk_profile_adj=-0.2,
        stability_bias_adj=0.15,
    ),
    "risk": _WeightDelta(
        risk=0.1, stability=0.1, risk_profile_adj=-0.15, stability_bias_adj=0.1
    ),
    "reduce": _WeightDelta(
        risk=0.1, stability=0.1, exploration=-0.05, risk_profile_adj=-0.1
    ),
    "protect": _WeightDelta(
        risk=0.15, stability=0.1, reward=-0.05, risk_profile_adj=-0.15
    ),
    "optimize": _WeightDelta(
        reward=0.05, stability=0.1, exploration=-0.05, stability_bias_adj=0.1
    ),
    "efficiency": _WeightDelta(
        stability=0.1, exploration=-0.05, stability_bias_adj=0.1
    ),
    "efficient": _WeightDelta(stability=0.1, exploration=-0.05, stability_bias_adj=0.1),
    "explore": _WeightDelta(exploration=0.2, novelty=0.1, exploration_policy_adj=0.2),
    "experiment": _WeightDelta(
        exploration=0.15, novelty=0.15, exploration_policy_adj=0.15
    ),
    "innovate": _WeightDelta(novelty=0.15, exploration=0.1, exploration_policy_adj=0.1),
    "innovation": _WeightDelta(
        novelty=0.15, exploration=0.1, exploration_policy_adj=0.1
    ),
    "stable": _WeightDelta(
        stability=0.15, risk=0.05, exploration=-0.05, stability_bias_adj=0.15
    ),
    "steady": _WeightDelta(stability=0.15, exploration=-0.05, stability_bias_adj=0.1),
    "consistent": _WeightDelta(
        stability=0.15, exploration=-0.1, stability_bias_adj=0.15
    ),
    "aggressive": _WeightDelta(
        reward=0.15,
        risk=-0.1,
        exploration=0.15,
        risk_profile_adj=0.2,
        exploration_policy_adj=0.15,
    ),
    "conservative": _WeightDelta(
        risk=0.1,
        stability=0.15,
        exploration=-0.1,
        risk_profile_adj=-0.2,
        stability_bias_adj=0.1,
    ),
    "diversify": _WeightDelta(exploration=0.1, novelty=0.1, exploration_policy_adj=0.1),
    "focus": _WeightDelta(stability=0.1, exploration=-0.1, stability_bias_adj=0.1),
    "maximize": _WeightDelta(reward=0.1, exploration=0.05),
    "minimize": _WeightDelta(risk=0.1, stability=0.1, risk_profile_adj=-0.1),
    "health": _WeightDelta(stability=0.1, risk=0.05, stability_bias_adj=0.1),
    "fast": _WeightDelta(reward=0.1, exploration=0.05, stability=-0.05),
    "slow": _WeightDelta(stability=0.1, exploration=-0.05, stability_bias_adj=0.1),
}

_CONSTRAINT_MAP: dict[str, _WeightDelta] = {
    "no_risk": _WeightDelta(
        risk=0.2,
        stability=0.15,
        exploration=-0.1,
        risk_profile_adj=-0.3,
        stability_bias_adj=0.2,
    ),
    "low_risk": _WeightDelta(
        risk=0.15, stability=0.1, risk_profile_adj=-0.2, stability_bias_adj=0.1
    ),
    "high_risk": _WeightDelta(risk=-0.1, exploration=0.1, risk_profile_adj=0.2),
    "no_exploration": _WeightDelta(
        exploration=-0.2, novelty=-0.1, exploration_policy_adj=-0.2
    ),
    "max_exploration": _WeightDelta(
        exploration=0.2, novelty=0.1, exploration_policy_adj=0.3
    ),
    "stability_first": _WeightDelta(
        stability=0.2, exploration=-0.1, stability_bias_adj=0.2
    ),
    "growth_first": _WeightDelta(
        reward=0.2, exploration=0.1, exploration_policy_adj=0.1
    ),
}


# ─── Keyword extraction ─────────────────────────────────────


def extract_keywords(goal: str) -> tuple[str, ...]:
    """Extract recognized keywords from a goal string."""
    tokens = goal.lower().replace(",", " ").replace(".", " ").split()
    matched: list[str] = []
    for token in tokens:
        if token in _KEYWORD_MAP and token not in matched:
            matched.append(token)
            if len(matched) >= MAX_KEYWORDS_MATCHED:
                break
    return tuple(matched)


# ─── Weight accumulation ─────────────────────────────────────


def _accumulate_deltas(
    deltas: list[_WeightDelta],
) -> _WeightDelta:
    """Sum a list of deltas into one combined delta."""
    r = s = st = e = n = rp = ep = sb = 0.0
    for d in deltas:
        r += d.reward
        s += d.risk
        st += d.stability
        e += d.exploration
        n += d.novelty
        rp += d.risk_profile_adj
        ep += d.exploration_policy_adj
        sb += d.stability_bias_adj
    return _WeightDelta(
        reward=r,
        risk=s,
        stability=st,
        exploration=e,
        novelty=n,
        risk_profile_adj=rp,
        exploration_policy_adj=ep,
        stability_bias_adj=sb,
    )


# ─── Clamping ───────────────────────────────────────────────


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _clamp_weights(weights: dict[str, float]) -> dict[str, float]:
    """Clamp objective weights to their valid bounds."""
    return {
        "reward": _clamp(weights.get("reward", 0.5), *REWARD_WEIGHT_BOUNDS),
        "risk": _clamp(weights.get("risk", 0.3), *RISK_WEIGHT_BOUNDS),
        "stability": _clamp(weights.get("stability", 0.3), *STABILITY_WEIGHT_BOUNDS),
        "exploration": _clamp(
            weights.get("exploration", 0.0), *EXPLORATION_WEIGHT_BOUNDS
        ),
        "novelty": _clamp(weights.get("novelty", 0.0), *NOVELTY_WEIGHT_BOUNDS),
    }


# ─── Priority weight application ────────────────────────────


def _apply_priority_weights(
    base: dict[str, float],
    priorities: dict[str, float] | None,
) -> dict[str, float]:
    """Scale objective weights by user-supplied priority multipliers."""
    if not priorities:
        return base
    result = dict(base)
    for key, mult in priorities.items():
        if key in result:
            result[key] = result[key] * _clamp(mult, 0.0, 3.0)
    return result


# ─── Horizon → weight bias ──────────────────────────────────


def _horizon_bias(time_horizon: int) -> _WeightDelta:
    """Short horizons favor reward; long horizons favor stability/exploration."""
    if time_horizon <= 2:
        return _WeightDelta(reward=0.05, stability=-0.05, exploration=-0.05)
    if time_horizon >= 10:
        return _WeightDelta(
            reward=-0.05, stability=0.05, exploration=0.05, novelty=0.05
        )
    return _WeightDelta()


# ─── Risk tolerance → risk profile ──────────────────────────


def _risk_tolerance_to_profile(tolerance: float) -> float:
    """Map 0-1 risk tolerance to risk profile. Low tolerance = low profile."""
    return _clamp(tolerance, 0.0, 1.0)


# ─── Main compiler ──────────────────────────────────────────


def compile_intent(intent: IntentInput) -> CompiledIntent:
    """Compile a user intent into structured meta-harness configuration.

    Pipeline:
    1. Extract keywords from goal string
    2. Accumulate weight deltas from keywords
    3. Apply constraint overrides (constraints > goals)
    4. Apply horizon bias
    5. Apply risk tolerance
    6. Apply priority weight multipliers
    7. Clamp all weights to valid bounds
    """
    keywords = extract_keywords(intent.goal)

    # Step 1-2: keyword deltas
    keyword_deltas = [_KEYWORD_MAP[k] for k in keywords]

    # Step 3: constraint deltas (applied after keywords — constraints override)
    constraint_deltas = []
    for c in intent.constraints:
        if c in _CONSTRAINT_MAP:
            constraint_deltas.append(_CONSTRAINT_MAP[c])

    # Step 4: horizon bias
    h_delta = _horizon_bias(intent.time_horizon)

    all_deltas = keyword_deltas + constraint_deltas + [h_delta]
    combined = _accumulate_deltas(all_deltas)

    base_weights = {
        "reward": 0.5 + combined.reward,
        "risk": 0.3 + combined.risk,
        "stability": 0.3 + combined.stability,
        "exploration": 0.0 + combined.exploration,
        "novelty": 0.0 + combined.novelty,
    }

    # Step 6: priority multipliers
    weighted = _apply_priority_weights(base_weights, intent.priority_weights)

    # Step 7: clamp
    clamped = _clamp_weights(weighted)

    risk_profile = _clamp(
        _risk_tolerance_to_profile(intent.risk_tolerance) + combined.risk_profile_adj,
        0.0,
        1.0,
    )
    exploration_policy = _clamp(combined.exploration_policy_adj, 0.0, 1.0)
    stability_bias = _clamp(0.3 + combined.stability_bias_adj, 0.0, 1.0)

    return CompiledIntent(
        objective_weights=clamped,
        risk_profile=risk_profile,
        exploration_policy=exploration_policy,
        stability_bias=stability_bias,
        horizon_bias=intent.time_horizon,
        matched_keywords=keywords,
        intent_source=intent.goal,
    )


# ─── ObjectiveWeights bridge ────────────────────────────────


def to_objective_weights(compiled: CompiledIntent) -> object:
    """Convert CompiledIntent to an ObjectiveWeights instance.

    Returns the ObjectiveWeights or None if import fails.
    """
    try:
        from umh.objectives.arbitration import ObjectiveWeights

        w = compiled.objective_weights
        return ObjectiveWeights(
            reward_weight=w["reward"],
            risk_weight=w["risk"],
            stability_weight=w["stability"],
            exploration_weight=w["exploration"],
            novelty_weight=w["novelty"],
        )
    except Exception:
        return None


# ─── Trace field extraction ─────────────────────────────────


def get_trace_fields(compiled: CompiledIntent | None) -> dict:
    """Extract trace-compatible fields from a compiled intent."""
    if compiled is None:
        return {}
    return {
        "intent_source": compiled.intent_source,
        "intent_compiled_weights": compiled.objective_weights,
        "intent_applied_biases": {
            "risk_profile": round(compiled.risk_profile, 6),
            "exploration_policy": round(compiled.exploration_policy, 6),
            "stability_bias": round(compiled.stability_bias, 6),
            "horizon_bias": compiled.horizon_bias,
        },
    }
