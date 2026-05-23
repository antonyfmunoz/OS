"""Actuator Maturity Model v1.

Defines 8 maturity levels (L0-L7) for GUI actuation. Each level
requires specific observed evidence. No actuator can claim maturity
above the evidence it provides.

UMH substrate subsystem.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class ActuatorMaturityLevel(IntEnum):
    L0_SIMULATED = 0
    L1_PROCESS_STARTED = 1
    L2_WINDOW_OBSERVED = 2
    L3_FOREGROUND_FOCUSED = 3
    L4_NAVIGATION_OBSERVED = 4
    L5_SCREENSHOT_VERIFIED = 5
    L6_FOUNDER_CONFIRMED = 6
    L7_REPLAYABLE_ACTUATION = 7


MATURITY_LABELS: dict[ActuatorMaturityLevel, str] = {
    ActuatorMaturityLevel.L0_SIMULATED: "simulated",
    ActuatorMaturityLevel.L1_PROCESS_STARTED: "process_started",
    ActuatorMaturityLevel.L2_WINDOW_OBSERVED: "window_observed",
    ActuatorMaturityLevel.L3_FOREGROUND_FOCUSED: "foreground_focused",
    ActuatorMaturityLevel.L4_NAVIGATION_OBSERVED: "navigation_observed",
    ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED: "screenshot_verified",
    ActuatorMaturityLevel.L6_FOUNDER_CONFIRMED: "founder_confirmed",
    ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION: "replayable_actuation",
}

MATURITY_REQUIREMENTS: dict[ActuatorMaturityLevel, list[str]] = {
    ActuatorMaturityLevel.L0_SIMULATED: [],
    ActuatorMaturityLevel.L1_PROCESS_STARTED: ["chrome_pid"],
    ActuatorMaturityLevel.L2_WINDOW_OBSERVED: ["chrome_pid", "window_handle"],
    ActuatorMaturityLevel.L3_FOREGROUND_FOCUSED: [
        "chrome_pid",
        "window_handle",
        "focused",
    ],
    ActuatorMaturityLevel.L4_NAVIGATION_OBSERVED: [
        "chrome_pid",
        "window_handle",
        "focused",
        "navigation_detected",
    ],
    ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED: [
        "chrome_pid",
        "window_handle",
        "focused",
        "navigation_detected",
        "screenshot_path",
    ],
    ActuatorMaturityLevel.L6_FOUNDER_CONFIRMED: [
        "chrome_pid",
        "window_handle",
        "focused",
        "navigation_detected",
        "screenshot_path",
        "founder_confirmed",
    ],
    ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION: [
        "chrome_pid",
        "window_handle",
        "focused",
        "navigation_detected",
        "screenshot_path",
        "founder_confirmed",
        "replay_hash",
    ],
}


def compute_maturity_level(evidence: dict[str, Any]) -> ActuatorMaturityLevel:
    """Compute the highest maturity level supported by the evidence.

    Walks down from L7 to L0. The first level whose requirements
    are fully satisfied is returned. Evidence values must be truthy
    (non-zero, non-empty, True) to count.
    """
    for level in reversed(ActuatorMaturityLevel):
        reqs = MATURITY_REQUIREMENTS[level]
        if all(_is_truthy(evidence.get(r)) for r in reqs):
            return level
    return ActuatorMaturityLevel.L0_SIMULATED


def maturity_ceiling(
    has_window_handle: bool = False,
    has_screenshot: bool = False,
    has_founder_confirmation: bool = False,
) -> ActuatorMaturityLevel:
    """Return the maximum maturity level given hard evidence caps."""
    if not has_window_handle:
        return ActuatorMaturityLevel.L1_PROCESS_STARTED
    if not has_screenshot:
        return ActuatorMaturityLevel.L4_NAVIGATION_OBSERVED
    if not has_founder_confirmation:
        return ActuatorMaturityLevel.L5_SCREENSHOT_VERIFIED
    return ActuatorMaturityLevel.L7_REPLAYABLE_ACTUATION


def validate_maturity_claim(
    claimed: ActuatorMaturityLevel,
    evidence: dict[str, Any],
) -> tuple[bool, ActuatorMaturityLevel, list[str]]:
    """Validate a claimed maturity level against evidence.

    Returns (valid, actual_level, missing_evidence).
    """
    actual = compute_maturity_level(evidence)
    missing: list[str] = []
    if claimed > actual:
        reqs = MATURITY_REQUIREMENTS[claimed]
        missing = [r for r in reqs if not _is_truthy(evidence.get(r))]
    return claimed <= actual, actual, missing


def _is_truthy(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return len(value) > 0
    return bool(value)
