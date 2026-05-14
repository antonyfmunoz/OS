"""Provisioning Coordination Engine v1.

Coordinates environment preparation, dependency verification,
capability validation, topology validation, and deployment
readiness verification.

Must NEVER provision hidden infrastructure, auto-create
environments, or auto-expand topology.

UMH substrate subsystem. Phase 96.8CE.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.deployment.platform_deployment_contracts_v1 import (
    ProvisioningState,
    _now_iso,
)

MAX_PROVISIONING_CHECKS = 50


class ProvisioningCoordinationEngine:
    """Coordinates provisioning readiness checks."""

    def __init__(self, state_dir: str | Path = "data/runtime/deployments") -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._checks: list[ProvisioningState] = []

    def check_readiness(
        self,
        environment_id: str,
        dependencies_met: bool = False,
        capabilities_validated: bool = False,
        topology_validated: bool = False,
    ) -> ProvisioningState:
        ready = dependencies_met and capabilities_validated and topology_validated

        state = ProvisioningState(
            environment_id=environment_id,
            dependencies_met=dependencies_met,
            capabilities_validated=capabilities_validated,
            topology_validated=topology_validated,
            ready=ready,
        )
        self._checks.append(state)

        path = self._state_dir / "provisioning_checks.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(state.to_dict(), default=str) + "\n")

        return state

    def get_latest_check(
        self,
        environment_id: str,
    ) -> ProvisioningState | None:
        for check in reversed(self._checks):
            if check.environment_id == environment_id:
                return check
        return None

    def get_all_checks(self, limit: int = 20) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._checks[-limit:]]

    def get_stats(self) -> dict[str, object]:
        ready_count = sum(1 for c in self._checks if c.ready)
        return {
            "total_checks": len(self._checks),
            "ready_count": ready_count,
            "not_ready_count": len(self._checks) - ready_count,
        }
