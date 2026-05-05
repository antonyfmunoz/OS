"""UMH System Controls — operator-tunable behavior modifiers.

Controls influence scoring, strategy refinement, and goal decomposition.
They are pure configuration: no execution, no planning, no side effects
beyond storing the control values themselves.

Three execution modes shape all behavior:
  - balanced: default weights, standard thresholds
  - aggressive: boost high-impact, more retries, lower cost penalty
  - conservative: penalize risky, fewer retries, favor stable strategies
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum

from umh.core.clock import iso_now as _iso_now


class ExecutionMode(str, Enum):
    """Execution mode controlling scoring weight biases."""

    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    CONSERVATIVE = "conservative"


class RetryPolicy(str, Enum):
    """Retry policy controlling max retry counts."""

    STRICT = "strict"
    NORMAL = "normal"
    LENIENT = "lenient"


@dataclass
class SystemControls:
    """Global system behavior controls.

    All float fields are clamped to [0.0, 1.0] on mutation via
    ``update_system_control``.
    """

    execution_mode: ExecutionMode = ExecutionMode.BALANCED
    max_concurrent_tasks: int = 5
    retry_policy: RetryPolicy = RetryPolicy.NORMAL
    cost_sensitivity: float = 0.5  # 0.0 (ignore cost) to 1.0 (maximize savings)
    failure_tolerance: float = 0.5  # 0.0 (zero tolerance) to 1.0 (very tolerant)
    exploration_factor: float = 0.3  # 0.0 (exploit known) to 1.0 (explore new)
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.updated_at:
            self.updated_at = _iso_now()

    def to_dict(self) -> dict:
        """Serialize to plain dict (JSON-safe)."""
        return {
            "execution_mode": self.execution_mode.value,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "retry_policy": self.retry_policy.value,
            "cost_sensitivity": round(self.cost_sensitivity, 2),
            "failure_tolerance": round(self.failure_tolerance, 2),
            "exploration_factor": round(self.exploration_factor, 2),
            "updated_at": self.updated_at,
        }


@dataclass
class ControlInfluence:
    """Explains how controls affected a specific scoring decision."""

    mode: str = "balanced"
    priority_adjustment: float = 0.0
    retry_policy: str = "normal"
    cost_modifier: float = 0.0
    failure_modifier: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to plain dict (JSON-safe)."""
        return {
            "mode": self.mode,
            "priority_adjustment": round(self.priority_adjustment, 3),
            "retry_policy": self.retry_policy,
            "cost_modifier": round(self.cost_modifier, 3),
            "failure_modifier": round(self.failure_modifier, 3),
        }


# ── Pure functions ──────────────────────────────────────────────────────


def compute_weight_modifiers(controls: SystemControls) -> dict:
    """Compute scoring weight modifiers based on current controls.

    Returns dict with keys matching scorer weights:
    importance_mod, recency_mod, failure_mod, dependency_mod, cost_mod.
    All modifiers are multiplicative: 1.0 = no change.
    """
    if controls.execution_mode == ExecutionMode.AGGRESSIVE:
        return {
            "importance_mod": 1.3,  # boost high-impact
            "recency_mod": 1.2,  # prefer newer
            "failure_mod": 0.7,  # less failure pressure
            "dependency_mod": 1.2,  # unlock more
            "cost_mod": 0.5,  # lower cost penalty
        }
    elif controls.execution_mode == ExecutionMode.CONSERVATIVE:
        return {
            "importance_mod": 0.8,  # flatten importance
            "recency_mod": 0.8,  # less urgency
            "failure_mod": 1.4,  # more failure pressure
            "dependency_mod": 0.9,
            "cost_mod": 1.5,  # higher cost penalty
        }
    else:  # BALANCED
        return {
            "importance_mod": 1.0,
            "recency_mod": 1.0,
            "failure_mod": 1.0,
            "dependency_mod": 1.0,
            "cost_mod": 1.0,
        }


def compute_control_influence(
    controls: SystemControls,
    base_score: float,
    adjusted_score: float,
) -> ControlInfluence:
    """Create explainability record showing how controls influenced scoring."""
    mods = compute_weight_modifiers(controls)
    cost_mod = mods["cost_mod"]
    failure_mod = mods["failure_mod"]

    return ControlInfluence(
        mode=controls.execution_mode.value,
        priority_adjustment=round(adjusted_score - base_score, 3),
        retry_policy=controls.retry_policy.value,
        cost_modifier=cost_mod - 1.0,  # delta from neutral
        failure_modifier=failure_mod - 1.0,
    )


def get_max_retries(controls: SystemControls) -> int:
    """Return max retries based on retry policy."""
    return {
        RetryPolicy.STRICT: 1,
        RetryPolicy.NORMAL: 3,
        RetryPolicy.LENIENT: 5,
    }.get(controls.retry_policy, 3)


def get_refinement_bias(controls: SystemControls) -> str:
    """Return strategy refinement bias based on controls.

    aggressive -> "complex" (allow more steps, deeper decomposition)
    conservative -> "simple" (fewer steps, simpler strategies)
    balanced -> "neutral"
    """
    return {
        ExecutionMode.AGGRESSIVE: "complex",
        ExecutionMode.CONSERVATIVE: "simple",
        ExecutionMode.BALANCED: "neutral",
    }.get(controls.execution_mode, "neutral")


# ── Singleton store ─────────────────────────────────────────────────────

_controls = SystemControls()
_controls_lock = threading.Lock()


def get_system_controls() -> SystemControls:
    """Return the current system controls."""
    with _controls_lock:
        return _controls


def set_system_controls(controls: SystemControls) -> SystemControls:
    """Replace system controls. Returns the new controls."""
    global _controls
    controls.updated_at = _iso_now()
    with _controls_lock:
        _controls = controls
    return _controls


def update_system_control(key: str, value: object) -> SystemControls:
    """Update a single control field by name. Returns updated controls."""
    global _controls
    with _controls_lock:
        if key == "execution_mode":
            _controls.execution_mode = ExecutionMode(value)
        elif key == "max_concurrent_tasks":
            _controls.max_concurrent_tasks = int(value)  # type: ignore[arg-type]
        elif key == "retry_policy":
            _controls.retry_policy = RetryPolicy(value)
        elif key == "cost_sensitivity":
            _controls.cost_sensitivity = max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
        elif key == "failure_tolerance":
            _controls.failure_tolerance = max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
        elif key == "exploration_factor":
            _controls.exploration_factor = max(0.0, min(1.0, float(value)))  # type: ignore[arg-type]
        else:
            raise ValueError(f"Unknown control key: {key}")
        _controls.updated_at = _iso_now()
        return _controls


def reset_system_controls() -> SystemControls:
    """Reset to defaults (for testing)."""
    global _controls
    with _controls_lock:
        _controls = SystemControls()
    return _controls
