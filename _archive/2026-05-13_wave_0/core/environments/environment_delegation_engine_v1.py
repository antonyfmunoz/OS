"""Environment Delegation Engine v1.

Bounded delegation with:
  explicit approvals, delegation lineage,
  delegation replayability, continuation restoration.

Prevents:
  recursive delegation, uncontrolled fanout,
  hidden delegation trees.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.environments.live_environment_topology_contracts_v1 import (
    EnvironmentDelegationState,
    _content_hash,
    _now_iso,
)
from core.environments.environment_topology_engine_v1 import (
    EnvironmentTopologyEngine,
)


DEFAULT_MAX_DELEGATION_DEPTH: int = 3
DEFAULT_MAX_ACTIVE_DELEGATIONS: int = 5


class EnvironmentDelegationEngine:
    """Manages bounded cross-environment delegation."""

    def __init__(
        self,
        topology: EnvironmentTopologyEngine,
        state_dir: str | Path = "data/runtime/environment_coordination",
        max_depth: int = DEFAULT_MAX_DELEGATION_DEPTH,
        max_active: int = DEFAULT_MAX_ACTIVE_DELEGATIONS,
    ) -> None:
        self._topology = topology
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._delegations: dict[str, EnvironmentDelegationState] = {}
        self._max_depth = max_depth
        self._max_active = max_active
        self._total_delegations: int = 0
        self._total_denials: int = 0

    def delegate(
        self,
        from_environment: str,
        to_environment: str,
        delegation_type: str = "execution",
        campaign_id: str = "",
        current_depth: int = 0,
    ) -> EnvironmentDelegationState | None:
        if current_depth >= self._max_depth:
            self._total_denials += 1
            return None

        if from_environment == to_environment:
            self._total_denials += 1
            return None

        active = sum(
            1 for d in self._delegations.values()
            if d.state == "active"
        )
        if active >= self._max_active:
            self._total_denials += 1
            return None

        from_trust = self._topology.get_trust(from_environment)
        if from_trust and not from_trust.can_delegate:
            self._total_denials += 1
            return None

        if self._would_create_cycle(from_environment, to_environment):
            self._total_denials += 1
            return None

        delegation = EnvironmentDelegationState(
            from_environment=from_environment,
            to_environment=to_environment,
            delegation_type=delegation_type,
            campaign_id=campaign_id,
            depth=current_depth,
            max_depth=self._max_depth,
            state="pending",
        )
        self._delegations[delegation.delegation_id] = delegation
        self._total_delegations += 1
        self._persist(delegation)
        return delegation

    def approve(
        self,
        delegation_id: str,
        approved_by: str = "operator",
    ) -> bool:
        delegation = self._delegations.get(delegation_id)
        if not delegation:
            return False
        if delegation.state != "pending":
            return False

        delegation.approved = True
        delegation.approved_by = approved_by
        delegation.state = "active"
        self._persist(delegation)
        return True

    def complete(self, delegation_id: str) -> bool:
        delegation = self._delegations.get(delegation_id)
        if not delegation:
            return False
        if delegation.state != "active":
            return False

        delegation.state = "completed"
        delegation.completed_at = _now_iso()
        self._persist(delegation)
        return True

    def fail(self, delegation_id: str, reason: str = "") -> bool:
        delegation = self._delegations.get(delegation_id)
        if not delegation:
            return False

        delegation.state = "failed"
        delegation.completed_at = _now_iso()
        self._persist(delegation)
        return True

    def get_delegation(self, delegation_id: str) -> EnvironmentDelegationState | None:
        return self._delegations.get(delegation_id)

    def get_active_delegations(self) -> list[EnvironmentDelegationState]:
        return [d for d in self._delegations.values() if d.state == "active"]

    def get_delegation_chain(self, environment_id: str) -> list[str]:
        chain: list[str] = []
        visited: set[str] = set()
        current = environment_id
        while current and current not in visited:
            visited.add(current)
            chain.append(current)
            for d in self._delegations.values():
                if d.to_environment == current and d.state == "active":
                    current = d.from_environment
                    break
            else:
                break
        return chain

    def get_delegation_hash(self) -> str:
        return _content_hash([d.to_dict() for d in self._delegations.values()])

    def _would_create_cycle(self, from_env: str, to_env: str) -> bool:
        visited: set[str] = set()
        stack = [to_env]
        while stack:
            current = stack.pop()
            if current == from_env:
                return True
            if current in visited:
                continue
            visited.add(current)
            for d in self._delegations.values():
                if d.from_environment == current and d.state in ("pending", "active"):
                    stack.append(d.to_environment)
        return False

    def _persist(self, delegation: EnvironmentDelegationState) -> None:
        path = self._state_dir / "environment_delegations.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(delegation.to_dict(), default=str) + "\n")

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_delegations": self._total_delegations,
            "total_denials": self._total_denials,
            "active": sum(1 for d in self._delegations.values() if d.state == "active"),
            "completed": sum(1 for d in self._delegations.values() if d.state == "completed"),
        }
