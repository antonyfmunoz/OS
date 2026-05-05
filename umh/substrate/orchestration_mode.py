"""
Orchestration mode helper — single source of truth for activation state.

When ORCHESTRATION_MODE=active, the orchestration layer (IntentCoordinator,
WorkflowDriver, PlanRegistry) is wired into the production scheduler and
ingress paths emit orchestration events instead of driving legacy lifecycle
chains directly.

When ORCHESTRATION_MODE is unset or any other value, existing behavior is
unchanged.
"""

from __future__ import annotations

import os

_OVERRIDE: bool | None = None


def orchestration_mode_active() -> bool:
    """Return True when orchestration is activated."""
    if _OVERRIDE is not None:
        return _OVERRIDE
    return os.environ.get("ORCHESTRATION_MODE", "").lower() == "active"


def set_orchestration_mode_for_testing(active: bool | None) -> None:
    """Override orchestration mode for testing.  Pass None to clear."""
    global _OVERRIDE
    _OVERRIDE = active
