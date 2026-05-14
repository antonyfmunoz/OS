"""Canonical Environment Coordination Engine v1.

Coordinates multi-environment operational execution:
  - coordinates environments and execution territories
  - coordinates environment routing
  - coordinates environment synchronization
  - coordinates delegation boundaries
  - coordinates environment continuity

All execution dispatches ONLY through spine.process().
The coordinator CANNOT execute adapters directly.
The operator still owns intent and authority.

UMH substrate subsystem. Phase 96.8BX.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.environments.live_environment_topology_contracts_v1 import (
    EnvironmentCoordinationReceipt,
    EnvironmentLifecycleState,
    TrustTier,
    _new_id,
    _now_iso,
)
from core.environments.environment_lifecycle_engine_v1 import (
    EnvironmentLifecycleEngine,
)
from core.environments.environment_topology_engine_v1 import (
    EnvironmentTopologyEngine,
)
from core.environments.environment_routing_engine_v1 import (
    EnvironmentRoutingEngine,
)
from core.environments.environment_delegation_engine_v1 import (
    EnvironmentDelegationEngine,
)
from core.environments.environment_synchronization_engine_v1 import (
    EnvironmentSynchronizationEngine,
)
from core.environments.environment_observability_pipeline_v1 import (
    EnvironmentObservabilityPipeline,
)
from core.environments.environment_execution_graph_engine_v1 import (
    EnvironmentExecutionGraphEngine,
)


class CanonicalEnvironmentCoordinationEngine:
    """Coordinates multi-environment operational execution.

    Cannot execute adapters directly. Cannot create environments
    autonomously. Cannot bypass governance. All execution through
    canonical spine only.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/environment_coordination",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = EnvironmentLifecycleEngine(state_dir=self._state_dir)
        self._topology = EnvironmentTopologyEngine(
            state_dir=self._state_dir / "topology",
        )
        self._routing = EnvironmentRoutingEngine(
            topology=self._topology, state_dir=self._state_dir,
        )
        self._delegation = EnvironmentDelegationEngine(
            topology=self._topology, state_dir=self._state_dir,
        )
        self._sync = EnvironmentSynchronizationEngine(
            topology=self._topology, state_dir=self._state_dir,
        )
        self._observability = EnvironmentObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )
        self._graph = EnvironmentExecutionGraphEngine(state_dir=self._state_dir)
        self._receipts: list[EnvironmentCoordinationReceipt] = []

    def register_environment(
        self,
        name: str,
        environment_type: str = "",
        trust_tier: str = TrustTier.GOVERNED.value,
        capabilities: list[str] | None = None,
        parent_id: str = "",
    ) -> dict[str, Any]:
        node = self._topology.register_environment(
            name=name,
            environment_type=environment_type,
            trust_tier=trust_tier,
            capabilities=capabilities,
            parent_id=parent_id,
        )
        self._lifecycle.register(node.environment_id)
        self._lifecycle.transition(
            node.environment_id, EnvironmentLifecycleState.AVAILABLE,
        )
        node.state = EnvironmentLifecycleState.AVAILABLE.value

        self._graph.create_graph(node.environment_id)
        self._graph.add_node(
            node.environment_id, "environment", node.environment_id,
            label=name,
        )

        self._observability.emit_registered(node.environment_id, name=name)
        self._emit_receipt(node.environment_id, "register", "", "available")

        return node.to_dict()

    def route_execution(
        self,
        command: str,
        required_capability: str = "",
        preferred_environment: str = "",
        min_trust: str = TrustTier.RESTRICTED.value,
    ) -> dict[str, Any]:
        decision = self._routing.route(
            command=command,
            required_capability=required_capability,
            preferred_environment=preferred_environment,
            min_trust=min_trust,
        )

        if decision.governance_passed:
            self._observability.emit_selected(
                decision.selected_environment, command=command,
            )
        else:
            self._observability.emit_denied("", command=command, reason=decision.reason)

        return decision.to_dict()

    def delegate_execution(
        self,
        from_environment: str,
        to_environment: str,
        delegation_type: str = "execution",
        campaign_id: str = "",
        current_depth: int = 0,
    ) -> dict[str, Any] | None:
        delegation = self._delegation.delegate(
            from_environment=from_environment,
            to_environment=to_environment,
            delegation_type=delegation_type,
            campaign_id=campaign_id,
            current_depth=current_depth,
        )
        if not delegation:
            self._observability.emit_denied(
                from_environment, reason="delegation_rejected",
            )
            return None

        self._observability.emit_delegated(
            from_environment,
            to_environment=to_environment,
            delegation_id=delegation.delegation_id,
        )
        self._emit_receipt(
            from_environment, "delegate", "", "delegated",
            delegation_id=delegation.delegation_id,
        )
        return delegation.to_dict()

    def approve_delegation(
        self,
        delegation_id: str,
        approved_by: str = "operator",
    ) -> bool:
        return self._delegation.approve(delegation_id, approved_by)

    def complete_delegation(self, delegation_id: str) -> bool:
        return self._delegation.complete(delegation_id)

    def synchronize_environments(
        self,
        source_environment: str,
        target_environment: str,
        sync_type: str = "full",
    ) -> dict[str, Any] | None:
        sync = self._sync.synchronize(
            source_environment, target_environment, sync_type,
        )
        if not sync:
            return None

        self._lifecycle.transition(
            source_environment, EnvironmentLifecycleState.SYNCHRONIZED,
        )
        self._lifecycle.transition(
            target_environment, EnvironmentLifecycleState.SYNCHRONIZED,
        )

        self._observability.emit_synchronized(
            source_environment, target=target_environment,
        )
        self._emit_receipt(source_environment, "synchronize", "", "synchronized")
        return sync.to_dict()

    def checkpoint_environment(
        self,
        environment_id: str,
        checkpoint_id: str = "",
    ) -> dict[str, Any] | None:
        cont = self._sync.checkpoint_environment(environment_id, checkpoint_id)
        if not cont:
            return None

        self._observability.emit_checkpointed(environment_id)
        self._graph.persist_graph(environment_id)
        self._emit_receipt(environment_id, "checkpoint", "", "")
        return cont.to_dict()

    def restore_environment(
        self,
        environment_id: str,
    ) -> bool:
        cont = self._sync.get_continuity(environment_id)
        if not cont:
            return False

        ok = self._lifecycle.transition(
            environment_id, EnvironmentLifecycleState.RESTORED,
        )
        if ok:
            self._lifecycle.transition(
                environment_id, EnvironmentLifecycleState.AVAILABLE,
            )
            self._observability.emit_restored(environment_id)
            self._emit_receipt(environment_id, "restore", "unavailable", "available")
        return ok

    def pause_environment(
        self,
        environment_id: str,
        reason: str = "",
    ) -> bool:
        ok = self._lifecycle.transition(
            environment_id, EnvironmentLifecycleState.PAUSED, reason,
        )
        if ok:
            self._emit_receipt(environment_id, "pause", "", "paused")
        return ok

    def terminate_environment(
        self,
        environment_id: str,
        reason: str = "",
    ) -> bool:
        ok = self._lifecycle.transition(
            environment_id, EnvironmentLifecycleState.TERMINATED, reason,
        )
        if ok:
            self._emit_receipt(environment_id, "terminate", "", "terminated")
        return ok

    def update_health(
        self,
        environment_id: str,
        healthy: bool,
        reason: str = "",
    ) -> bool:
        ok = self._topology.update_health(environment_id, healthy, reason)
        if ok and not healthy:
            health = self._topology.get_health(environment_id)
            if health and health.degraded:
                self._lifecycle.transition(
                    environment_id, EnvironmentLifecycleState.UNAVAILABLE,
                )
                self._observability.emit_unavailable(environment_id, reason=reason)
        return ok

    def get_topology(self) -> dict[str, Any]:
        return self._topology.build_topology().to_dict()

    def get_environment(self, environment_id: str) -> dict[str, Any] | None:
        node = self._topology.get_node(environment_id)
        return node.to_dict() if node else None

    def get_environment_by_name(self, name: str) -> dict[str, Any] | None:
        node = self._topology.get_node_by_name(name)
        return node.to_dict() if node else None

    def get_health(self, environment_id: str) -> dict[str, Any] | None:
        health = self._topology.get_health(environment_id)
        return health.to_dict() if health else None

    def get_execution_graph(self, environment_id: str) -> dict[str, Any] | None:
        return self._graph.get_graph(environment_id)

    def get_recent_receipts(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._receipts[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "topology": self._topology.get_stats(),
            "lifecycle": self._lifecycle.get_stats(),
            "routing": self._routing.get_stats(),
            "delegation": self._delegation.get_stats(),
            "sync": self._sync.get_stats(),
            "observability": self._observability.get_stats(),
            "graph": self._graph.get_stats(),
        }

    def _emit_receipt(
        self,
        environment_id: str,
        operation: str,
        from_state: str,
        to_state: str,
        delegation_id: str = "",
        campaign_id: str = "",
    ) -> EnvironmentCoordinationReceipt:
        receipt = EnvironmentCoordinationReceipt(
            environment_id=environment_id,
            operation=operation,
            from_state=from_state,
            to_state=to_state,
            campaign_id=campaign_id,
            delegation_id=delegation_id,
        )
        self._receipts.append(receipt)

        path = self._state_dir / "environment_coordination_receipts.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_dict(), default=str) + "\n")

        return receipt
