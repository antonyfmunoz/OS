"""Canonical Live Operational Deployment Coordinator v1.

Coordinates live deployment operations across applications,
environments, workflows, cognition, ingress, scaling,
resilience, and continuity through the canonical substrate spine.

Orchestration is supervised routing and coordination —
never autonomous infrastructure authority.

It NEVER deploys autonomously.
It NEVER scales autonomously.
It NEVER mutates environments silently.
It NEVER bypasses canonical spine.

UMH substrate subsystem. Phase 96.8CF.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.orchestration.live_operational_deployment_contracts_v1 import (
    LiveDeploymentOperation,
    OperationalDeploymentReceipt,
    DeploymentOperatorIntentState,
    _now_iso,
)
from core.orchestration.deployment_orchestration_lifecycle_engine_v1 import (
    DeploymentOrchestrationLifecycleEngine,
)
from core.orchestration.deployment_execution_graph_engine_v1 import (
    DeploymentExecutionGraphEngine,
)
from core.orchestration.live_deployment_routing_engine_v1 import (
    LiveDeploymentRoutingEngine,
)
from core.orchestration.deployment_checkpoint_engine_v1 import (
    DeploymentCheckpointEngine,
)
from core.orchestration.deployment_recovery_coordination_engine_v1 import (
    DeploymentRecoveryCoordinationEngine,
)
from core.orchestration.deployment_synchronization_engine_v1 import (
    DeploymentSynchronizationEngine,
)
from core.orchestration.deployment_orchestration_observability_pipeline_v1 import (
    DeploymentOrchestrationObservabilityPipeline,
)


class CanonicalLiveOperationalDeploymentCoordinator:
    """Coordinates all live operational deployment operations.

    Cannot deploy autonomously. Cannot scale autonomously.
    Cannot mutate environments silently. Cannot bypass canonical spine.
    Cannot self-heal. Cannot self-expand topology.
    Cannot self-author objectives.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/orchestration",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = DeploymentOrchestrationLifecycleEngine()
        self._graph = DeploymentExecutionGraphEngine(state_dir=self._state_dir)
        self._routing = LiveDeploymentRoutingEngine()
        self._checkpoints = DeploymentCheckpointEngine(state_dir=self._state_dir)
        self._recovery = DeploymentRecoveryCoordinationEngine()
        self._sync = DeploymentSynchronizationEngine()
        self._observability = DeploymentOrchestrationObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )
        self._operations: dict[str, LiveDeploymentOperation] = {}
        self._intents: list[DeploymentOperatorIntentState] = []

    def create_operation(
        self,
        application_id: str,
        environment_id: str,
        deployment_id: str = "",
        trust_tier: str = "development",
        approved_by: str = "operator",
    ) -> dict[str, Any]:
        if approved_by != "operator":
            raise ValueError("Operation creation requires operator approval")

        operation = LiveDeploymentOperation(
            application_id=application_id,
            environment_id=environment_id,
            deployment_id=deployment_id,
            trust_tier=trust_tier,
            approved_by=approved_by,
        )
        self._operations[operation.operation_id] = operation

        self._graph.add_node(operation.operation_id)

        self._observability.emit_operation_started(
            operation_id=operation.operation_id,
            app_id=application_id,
        )

        return operation.to_dict()

    def complete_operation(
        self,
        operation_id: str,
        approved_by: str = "operator",
    ) -> dict[str, Any] | None:
        if approved_by != "operator":
            raise ValueError("Operation completion requires operator approval")

        op = self._operations.get(operation_id)
        if op is None:
            return None

        op.status = "completed"
        receipt = OperationalDeploymentReceipt(
            operation_id=operation_id,
            outcome="completed",
        )

        self._observability.emit_operation_completed(
            operation_id=operation_id,
        )

        return receipt.to_dict()

    def add_dependency(
        self,
        source_id: str,
        target_id: str,
    ) -> bool:
        return self._graph.add_edge(source_id, target_id)

    def route_operation(
        self,
        operation_id: str,
        source_environment: str,
        target_environment: str,
        required_trust: str = "development",
        approved_by: str = "operator",
    ) -> dict[str, Any] | None:
        route = self._routing.route(
            operation_id=operation_id,
            source_environment=source_environment,
            target_environment=target_environment,
            required_trust=required_trust,
            approved_by=approved_by,
        )
        return route.to_dict() if route else None

    def create_checkpoint(
        self,
        operation_id: str,
        state_data: str,
    ) -> dict[str, Any] | None:
        checkpoint = self._checkpoints.create_checkpoint(
            operation_id=operation_id,
            state_data=state_data,
        )
        if checkpoint is None:
            return None

        self._observability.emit_checkpoint_created(
            operation_id=operation_id,
            checkpoint_id=checkpoint.checkpoint_id,
        )

        return checkpoint.to_dict()

    def restore_checkpoint(
        self,
        checkpoint_id: str,
    ) -> dict[str, Any] | None:
        checkpoint = self._checkpoints.restore_checkpoint(checkpoint_id)
        if checkpoint is None:
            return None

        self._observability.emit_restore_started(
            operation_id=checkpoint.operation_id,
        )
        self._observability.emit_restore_completed(
            operation_id=checkpoint.operation_id,
        )

        return checkpoint.to_dict()

    def recommend_recovery(
        self,
        operation_id: str,
        action: str,
        reason: str = "",
    ) -> dict[str, Any] | None:
        rec = self._recovery.recommend(
            operation_id=operation_id,
            action=action,
            reason=reason,
        )
        if rec is None:
            return None

        self._observability.emit_recovery_recommended(
            operation_id=operation_id,
            action=action,
        )

        return rec.to_dict()

    def approve_recovery(
        self,
        recovery_id: str,
        approved_by: str = "operator",
    ) -> dict[str, Any] | None:
        rec = self._recovery.approve(
            recovery_id=recovery_id,
            approved_by=approved_by,
        )
        return rec.to_dict() if rec else None

    def synchronize(self, target: str) -> dict[str, Any] | None:
        state = self._sync.synchronize(target)
        return state.to_dict() if state else None

    def set_intent(
        self,
        intent: str,
        operation_id: str = "",
        set_by: str = "operator",
    ) -> dict[str, Any]:
        if set_by != "operator":
            raise ValueError("Intent must be set by operator")

        state = DeploymentOperatorIntentState(
            intent=intent,
            set_by=set_by,
            operation_id=operation_id,
        )
        self._intents.append(state)
        return state.to_dict()

    def get_operation(self, operation_id: str) -> dict[str, Any] | None:
        op = self._operations.get(operation_id)
        return op.to_dict() if op else None

    def get_all_operations(self) -> list[dict[str, Any]]:
        return [op.to_dict() for op in self._operations.values()]

    def get_graph_snapshot(self) -> dict[str, Any]:
        return self._graph.get_snapshot().to_dict()

    def get_graph_hash(self) -> str:
        return self._graph.get_graph_hash()

    def get_routing_stats(self) -> dict[str, object]:
        return self._routing.get_stats()

    def get_checkpoint_stats(self) -> dict[str, object]:
        return self._checkpoints.get_stats()

    def get_pending_recoveries(self) -> list[dict[str, Any]]:
        return self._recovery.get_pending()

    def get_sync_stats(self) -> dict[str, object]:
        return self._sync.get_stats()

    def get_health(self) -> dict[str, Any]:
        return {
            "lifecycle_phase": self._lifecycle.current_phase,
            "operations_count": len(self._operations),
            "graph": self._graph.get_stats(),
            "routing": self._routing.get_stats(),
            "checkpoints": self._checkpoints.get_stats(),
            "recovery": self._recovery.get_stats(),
            "sync": self._sync.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "graph": self._graph.get_stats(),
            "routing": self._routing.get_stats(),
            "checkpoints": self._checkpoints.get_stats(),
            "recovery": self._recovery.get_stats(),
            "sync": self._sync.get_stats(),
            "observability": self._observability.get_stats(),
            "operations": len(self._operations),
            "intents": len(self._intents),
        }
