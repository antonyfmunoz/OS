"""MetaControl — governance layer for intelligence subsystem activation.

Decides WHICH intelligence layers are allowed to influence each decision.
Computes agreement and instability metrics from recent traces, then gates
layers based on a three-tier mode: minimal, adaptive, full.

Stateless per turn. Deterministic. No ML. No randomness.
"""

from __future__ import annotations

from dataclasses import dataclass


# ─── Constants ──────────────────────────────────────────────────

HIGH_INSTABILITY_THRESHOLD = 0.6
LOW_INSTABILITY_THRESHOLD = 0.3

HIGH_AGREEMENT_THRESHOLD = 0.7
LOW_AGREEMENT_THRESHOLD = 0.4

HIGH_CONFIDENCE_THRESHOLD = 0.7
LOW_CONFIDENCE_THRESHOLD = 0.4

MAX_LOOKBACK_TURNS = 5

VALID_MODES = ("minimal", "adaptive", "full")


# ─── Data models ───────────────────────────────────────────────


@dataclass(frozen=True)
class LayerPermissions:
    """Which intelligence layers are allowed to influence this turn."""

    allow_strategy_memory: bool
    allow_foresight: bool
    allow_planner_override: bool
    allow_dynamic_adaptation: bool
    allow_exploration_boost: bool

    def to_dict(self) -> dict:
        return {
            "allow_strategy_memory": self.allow_strategy_memory,
            "allow_foresight": self.allow_foresight,
            "allow_planner_override": self.allow_planner_override,
            "allow_dynamic_adaptation": self.allow_dynamic_adaptation,
            "allow_exploration_boost": self.allow_exploration_boost,
        }

    def enabled_count(self) -> int:
        return sum(
            [
                self.allow_strategy_memory,
                self.allow_foresight,
                self.allow_planner_override,
                self.allow_dynamic_adaptation,
                self.allow_exploration_boost,
            ]
        )

    def enabled_names(self) -> tuple[str, ...]:
        names: list[str] = []
        if self.allow_strategy_memory:
            names.append("strategy_memory")
        if self.allow_foresight:
            names.append("foresight")
        if self.allow_planner_override:
            names.append("planner_override")
        if self.allow_dynamic_adaptation:
            names.append("dynamic_adaptation")
        if self.allow_exploration_boost:
            names.append("exploration_boost")
        return tuple(names)


MINIMAL_PERMISSIONS = LayerPermissions(
    allow_strategy_memory=False,
    allow_foresight=False,
    allow_planner_override=False,
    allow_dynamic_adaptation=False,
    allow_exploration_boost=False,
)

ADAPTIVE_PERMISSIONS = LayerPermissions(
    allow_strategy_memory=False,
    allow_foresight=False,
    allow_planner_override=False,
    allow_dynamic_adaptation=True,
    allow_exploration_boost=False,
)

FULL_PERMISSIONS = LayerPermissions(
    allow_strategy_memory=True,
    allow_foresight=True,
    allow_planner_override=True,
    allow_dynamic_adaptation=True,
    allow_exploration_boost=True,
)


@dataclass(frozen=True)
class MetaControlState:
    """Per-turn governance state."""

    mode: str
    confidence_level: float
    instability_score: float
    agreement_score: float
    permissions: LayerPermissions

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "confidence_level": round(self.confidence_level, 6),
            "instability_score": round(self.instability_score, 6),
            "agreement_score": round(self.agreement_score, 6),
            "permissions": self.permissions.to_dict(),
            "enabled_count": self.permissions.enabled_count(),
        }


NO_CONTROL_STATE = MetaControlState(
    mode="full",
    confidence_level=1.0,
    instability_score=0.0,
    agreement_score=1.0,
    permissions=FULL_PERMISSIONS,
)


# ─── Signal extraction ─────────────────────────────────────────


def _extract_signal_values(trace: object) -> list[float]:
    """Extract normalized signal values from a decision trace for agreement computation."""
    values: list[float] = []

    quality = getattr(trace, "quality_score", None)
    if quality is not None:
        values.append(float(quality))

    confidence = getattr(trace, "confidence", None)
    if confidence is not None:
        values.append(float(confidence))

    cal_conf = getattr(trace, "calibration_confidence", None)
    if cal_conf is not None:
        values.append(float(cal_conf))

    planner_conf = getattr(trace, "planner_confidence", None)
    if planner_conf is not None:
        values.append(float(planner_conf))

    arb_reward = getattr(trace, "objective_arb_reward_weight", None)
    if arb_reward is not None:
        values.append(float(arb_reward))

    sp_conf = getattr(trace, "strat_pattern_confidence", None)
    if sp_conf is not None:
        values.append(float(sp_conf))

    return values


# ─── Agreement metric ──────────────────────────────────────────


def compute_agreement_score(traces: list[object]) -> float:
    """Compute agreement across recent signal outputs.

    agreement = 1 - variance(normalized_signal_values)
    Returns 1.0 when all signals agree, lower when they diverge.
    Clamped to [0, 1].
    """
    if not traces:
        return 1.0

    all_values: list[float] = []
    for trace in traces[-MAX_LOOKBACK_TURNS:]:
        all_values.extend(_extract_signal_values(trace))

    if len(all_values) < 2:
        return 1.0

    mean = sum(all_values) / len(all_values)
    variance = sum((v - mean) ** 2 for v in all_values) / len(all_values)

    return max(0.0, min(1.0, 1.0 - variance))


# ─── Instability metric ───────────────────────────────────────


def compute_instability_score(traces: list[object]) -> float:
    """Compute instability from recent trace history.

    Combines:
    - context_type volatility (regime changes)
    - calibration error magnitude
    - quality score variance

    Returns 0.0 (fully stable) to 1.0 (highly unstable).
    """
    if not traces:
        return 0.0

    recent = traces[-MAX_LOOKBACK_TURNS:]
    components: list[float] = []

    context_types: list[str] = []
    for t in recent:
        ct = getattr(t, "context_type", None)
        if ct is not None:
            context_types.append(ct)
    if len(context_types) >= 2:
        changes = sum(
            1
            for i in range(1, len(context_types))
            if context_types[i] != context_types[i - 1]
        )
        regime_volatility = changes / (len(context_types) - 1)
        components.append(regime_volatility)

    cal_errors: list[float] = []
    for t in recent:
        ce = getattr(t, "calibration_error", None)
        if ce is not None:
            cal_errors.append(float(ce))
    if cal_errors:
        avg_cal_error = sum(cal_errors) / len(cal_errors)
        components.append(min(1.0, avg_cal_error * 2.0))

    quality_scores: list[float] = []
    for t in recent:
        qs = getattr(t, "quality_score", None)
        if qs is not None:
            quality_scores.append(float(qs))
    if len(quality_scores) >= 2:
        q_mean = sum(quality_scores) / len(quality_scores)
        q_var = sum((q - q_mean) ** 2 for q in quality_scores) / len(quality_scores)
        components.append(min(1.0, q_var * 4.0))

    if not components:
        return 0.0

    return max(0.0, min(1.0, sum(components) / len(components)))


# ─── Confidence computation ───────────────────────────────────


def compute_confidence_level(traces: list[object]) -> float:
    """Compute overall confidence from recent traces.

    Averages the confidence field of recent traces.
    Returns 0.5 default when no data available.
    """
    if not traces:
        return 0.5

    recent = traces[-MAX_LOOKBACK_TURNS:]
    confidences: list[float] = []
    for t in recent:
        c = getattr(t, "confidence", None)
        if c is not None:
            confidences.append(float(c))

    if not confidences:
        return 0.5

    return sum(confidences) / len(confidences)


# ─── Mode selection ────────────────────────────────────────────


def select_mode(
    confidence: float,
    instability: float,
    agreement: float,
) -> str:
    """Select the governance mode based on metrics.

    minimal:  high instability OR low agreement OR low confidence
    adaptive: moderate conditions
    full:     stable + high agreement + high confidence
    """
    if instability > HIGH_INSTABILITY_THRESHOLD:
        return "minimal"
    if agreement < LOW_AGREEMENT_THRESHOLD:
        return "minimal"
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        return "minimal"

    if (
        instability < LOW_INSTABILITY_THRESHOLD
        and agreement > HIGH_AGREEMENT_THRESHOLD
        and confidence > HIGH_CONFIDENCE_THRESHOLD
    ):
        return "full"

    return "adaptive"


# ─── Permissions from mode ─────────────────────────────────────


def permissions_for_mode(mode: str) -> LayerPermissions:
    """Return the layer permissions for a given mode."""
    if mode == "minimal":
        return MINIMAL_PERMISSIONS
    if mode == "adaptive":
        return ADAPTIVE_PERMISSIONS
    return FULL_PERMISSIONS


# ─── Main entry point ─────────────────────────────────────────


def compute_meta_control(
    traces: list[object],
) -> MetaControlState:
    """Compute the meta-control state for the current turn.

    Stateless — evaluates fresh from recent trace history each call.
    """
    agreement = compute_agreement_score(traces)
    instability = compute_instability_score(traces)
    confidence = compute_confidence_level(traces)

    mode = select_mode(confidence, instability, agreement)
    permissions = permissions_for_mode(mode)

    return MetaControlState(
        mode=mode,
        confidence_level=confidence,
        instability_score=instability,
        agreement_score=agreement,
        permissions=permissions,
    )
