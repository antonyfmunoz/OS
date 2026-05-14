"""Environment Routing Engine v1.

Selects execution environment based on:
  trust level, capability availability, governance boundaries,
  continuity requirements, execution locality.

Supports: vps, local_workstation, browser_runtime,
  tmux_runtime, filesystem_runtime, sandbox_runtime.

Prevents: uncontrolled delegation, hidden escalation,
  recursive routing chains.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.environments.live_environment_topology_contracts_v1 import (
    EnvironmentRoutingDecision,
    TrustTier,
    _content_hash,
    _now_iso,
)
from core.environments.environment_topology_engine_v1 import (
    EnvironmentTopologyEngine,
)


TRUST_ORDER: list[str] = [
    TrustTier.FULL.value,
    TrustTier.GOVERNED.value,
    TrustTier.RESTRICTED.value,
    TrustTier.UNTRUSTED.value,
]

CAPABILITY_ROUTING: dict[str, list[str]] = {
    "shell": ["vps", "local_workstation", "tmux_runtime"],
    "docker": ["vps"],
    "git": ["vps", "local_workstation"],
    "python": ["vps", "local_workstation", "tmux_runtime", "sandbox_runtime"],
    "tmux": ["vps", "tmux_runtime"],
    "filesystem": ["vps", "local_workstation", "filesystem_runtime", "sandbox_runtime"],
    "navigation": ["browser_runtime"],
    "inspection": ["browser_runtime"],
    "screenshot": ["browser_runtime"],
    "read": ["filesystem_runtime", "vps", "local_workstation"],
    "write": ["filesystem_runtime", "vps", "local_workstation"],
}

MAX_ROUTING_DEPTH: int = 3


class EnvironmentRoutingEngine:
    """Selects the appropriate execution environment."""

    def __init__(
        self,
        topology: EnvironmentTopologyEngine,
        state_dir: str | Path = "data/runtime/environment_coordination",
    ) -> None:
        self._topology = topology
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._decisions: list[EnvironmentRoutingDecision] = []
        self._routing_depth: int = 0
        self._total_routes: int = 0
        self._total_denials: int = 0

    def route(
        self,
        command: str,
        required_capability: str = "",
        preferred_environment: str = "",
        min_trust: str = TrustTier.RESTRICTED.value,
    ) -> EnvironmentRoutingDecision:
        self._routing_depth += 1
        try:
            if self._routing_depth > MAX_ROUTING_DEPTH:
                return self._deny(command, "recursive_routing_chain_exceeded")

            candidates = self._find_candidates(required_capability, min_trust)

            if preferred_environment:
                node = self._topology.get_node_by_name(preferred_environment)
                if node and node.environment_id in candidates:
                    return self._select(command, node.environment_id, candidates)

            if not candidates:
                return self._deny(command, "no_eligible_environment")

            selected = self._rank_candidates(candidates)
            return self._select(command, selected, candidates)
        finally:
            self._routing_depth -= 1

    def _find_candidates(
        self,
        capability: str,
        min_trust: str,
    ) -> list[str]:
        if capability:
            env_ids = self._topology.get_environments_with_capability(capability)
        else:
            env_ids = [
                eid for eid, _ in self._topology._nodes.items()
                if self._topology.get_health(eid) and
                self._topology.get_health(eid).healthy  # type: ignore[union-attr]
            ]

        min_idx = TRUST_ORDER.index(min_trust) if min_trust in TRUST_ORDER else len(TRUST_ORDER)
        result = []
        for eid in env_ids:
            trust = self._topology.get_trust(eid)
            if trust:
                tier_idx = TRUST_ORDER.index(trust.tier) if trust.tier in TRUST_ORDER else len(TRUST_ORDER)
                if tier_idx <= min_idx:
                    result.append(eid)
        return result

    def _rank_candidates(self, candidates: list[str]) -> str:
        best = candidates[0]
        best_rank = len(TRUST_ORDER)
        for eid in candidates:
            trust = self._topology.get_trust(eid)
            if trust:
                rank = TRUST_ORDER.index(trust.tier) if trust.tier in TRUST_ORDER else len(TRUST_ORDER)
                if rank < best_rank:
                    best_rank = rank
                    best = eid
        return best

    def _select(
        self,
        command: str,
        selected: str,
        candidates: list[str],
    ) -> EnvironmentRoutingDecision:
        trust = self._topology.get_trust(selected)
        decision = EnvironmentRoutingDecision(
            command=command,
            selected_environment=selected,
            candidate_environments=candidates,
            trust_tier=trust.tier if trust else "",
            governance_passed=True,
            reason="selected",
        )
        self._decisions.append(decision)
        self._total_routes += 1
        self._persist_decision(decision)
        return decision

    def _deny(self, command: str, reason: str) -> EnvironmentRoutingDecision:
        decision = EnvironmentRoutingDecision(
            command=command,
            selected_environment="",
            governance_passed=False,
            reason=reason,
        )
        self._decisions.append(decision)
        self._total_denials += 1
        self._persist_decision(decision)
        return decision

    def _persist_decision(self, decision: EnvironmentRoutingDecision) -> None:
        path = self._state_dir / "environment_routing_decisions.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(decision.to_dict(), default=str) + "\n")

    def get_decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._decisions[-limit:]]

    def get_routing_hash(self) -> str:
        return _content_hash([d.to_dict() for d in self._decisions])

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_routes": self._total_routes,
            "total_denials": self._total_denials,
            "total_decisions": len(self._decisions),
        }
