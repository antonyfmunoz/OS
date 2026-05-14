"""Canonical Platform Deployment Coordinator v1.

Coordinates governed platform deployment:
  manifests, topology, provisioning, rollout, rollback,
  observability, replay, lifecycle.

Deployment is operational infrastructure coordination —
not execution authority transfer.

It NEVER deploys autonomously.
It NEVER mutates environments silently.
It NEVER bypasses substrate governance.
It NEVER bypasses canonical spine.

UMH substrate subsystem. Phase 96.8CE.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.deployment.platform_deployment_contracts_v1 import (
    DeploymentProjection,
    _now_iso,
)
from core.deployment.deployment_lifecycle_engine_v1 import (
    DeploymentLifecycleEngine,
)
from core.deployment.deployment_manifest_engine_v1 import (
    DeploymentManifestEngine,
)
from core.deployment.deployment_topology_engine_v1 import (
    DeploymentTopologyEngine,
)
from core.deployment.provisioning_coordination_engine_v1 import (
    ProvisioningCoordinationEngine,
)
from core.deployment.rollout_coordination_engine_v1 import (
    RolloutCoordinationEngine,
)
from core.deployment.rollback_coordination_engine_v1 import (
    RollbackCoordinationEngine,
)
from core.deployment.deployment_observability_pipeline_v1 import (
    DeploymentObservabilityPipeline,
)


class CanonicalPlatformDeploymentCoordinator:
    """Coordinates all platform deployment operations.

    Cannot deploy autonomously. Cannot mutate environments silently.
    Cannot bypass substrate governance. Cannot bypass canonical spine.
    Cannot self-scale infrastructure. Cannot own cognition.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/deployments",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = DeploymentLifecycleEngine()
        self._manifests = DeploymentManifestEngine(state_dir=self._state_dir)
        self._topology = DeploymentTopologyEngine(state_dir=self._state_dir)
        self._provisioning = ProvisioningCoordinationEngine(
            state_dir=self._state_dir,
        )
        self._rollouts = RolloutCoordinationEngine(
            state_dir=self._state_dir,
        )
        self._rollbacks = RollbackCoordinationEngine(
            state_dir=self._state_dir,
        )
        self._observability = DeploymentObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )
        self._deployments: dict[str, DeploymentProjection] = {}

    def create_deployment(
        self,
        application_id: str,
        manifest_id: str = "",
        environment_id: str = "",
        trust_tier: str = "development",
    ) -> dict[str, Any]:
        deployment = DeploymentProjection(
            application_id=application_id,
            manifest_id=manifest_id,
            environment_id=environment_id,
            trust_tier=trust_tier,
        )
        self._deployments[deployment.deployment_id] = deployment

        self._observability.emit_deployment_created(
            deployment_id=deployment.deployment_id,
            app_id=application_id,
        )

        return deployment.to_dict()

    def create_manifest(
        self,
        application_id: str,
        required_capabilities: list[str] | None = None,
        environment_bindings: list[str] | None = None,
        topology_bindings: list[str] | None = None,
    ) -> dict[str, Any] | None:
        manifest = self._manifests.create(
            application_id=application_id,
            required_capabilities=required_capabilities,
            environment_bindings=environment_bindings,
            topology_bindings=topology_bindings,
        )
        return manifest.to_dict() if manifest else None

    def validate_manifest(self, manifest_id: str) -> dict[str, Any]:
        result = self._manifests.validate_manifest(manifest_id)
        if result["valid"]:
            self._observability.emit_deployment_validated(
                deployment_id=manifest_id,
            )
        else:
            self._observability.emit_deployment_denied(
                deployment_id=manifest_id,
                reason=str(result.get("issues", [])),
            )
        return result

    def register_environment(
        self,
        environment_type: str,
        trust_tier: str = "development",
        capabilities: list[str] | None = None,
    ) -> dict[str, Any] | None:
        env = self._topology.register_environment(
            environment_type=environment_type,
            trust_tier=trust_tier,
            capabilities=capabilities,
        )
        return env.to_dict() if env else None

    def validate_topology(self) -> dict[str, Any]:
        result = self._topology.validate_topology()
        if result["valid"]:
            snap = self._topology.get_topology_snapshot()
            self._observability.emit_topology_validated(
                topology_id=snap.topology_id,
            )
        return result

    def check_provisioning(
        self,
        environment_id: str,
        dependencies_met: bool = False,
        capabilities_validated: bool = False,
        topology_validated: bool = False,
    ) -> dict[str, Any]:
        state = self._provisioning.check_readiness(
            environment_id=environment_id,
            dependencies_met=dependencies_met,
            capabilities_validated=capabilities_validated,
            topology_validated=topology_validated,
        )
        return state.to_dict()

    def start_rollout(
        self,
        deployment_id: str,
        strategy: str = "sequential",
        stages_total: int = 1,
        approved_by: str = "operator",
    ) -> dict[str, Any] | None:
        rollout = self._rollouts.create_rollout(
            deployment_id=deployment_id,
            strategy=strategy,
            stages_total=stages_total,
            approved_by=approved_by,
        )
        if rollout is None:
            return None

        self._observability.emit_rollout_started(
            rollout_id=rollout.rollout_id,
            deployment_id=deployment_id,
        )

        return rollout.to_dict()

    def advance_rollout(
        self,
        rollout_id: str,
        approved_by: str = "operator",
    ) -> dict[str, Any] | None:
        rollout = self._rollouts.advance_stage(
            rollout_id=rollout_id,
            approved_by=approved_by,
        )
        if rollout is None:
            return None

        if rollout.status == "completed":
            self._observability.emit_rollout_completed(
                rollout_id=rollout.rollout_id,
                deployment_id=rollout.deployment_id,
            )

        return rollout.to_dict()

    def start_rollback(
        self,
        deployment_id: str,
        target_deployment_id: str,
        reason: str = "",
        approved_by: str = "operator",
    ) -> dict[str, Any] | None:
        rollback = self._rollbacks.create_rollback(
            deployment_id=deployment_id,
            target_deployment_id=target_deployment_id,
            reason=reason,
            approved_by=approved_by,
        )
        if rollback is None:
            return None

        self._observability.emit_rollback_started(
            rollback_id=rollback.rollback_id,
            deployment_id=deployment_id,
        )

        return rollback.to_dict()

    def complete_rollback(
        self,
        rollback_id: str,
    ) -> dict[str, Any] | None:
        rollback = self._rollbacks.complete_rollback(rollback_id)
        if rollback is None:
            return None

        self._observability.emit_rollback_completed(
            rollback_id=rollback.rollback_id,
            deployment_id=rollback.deployment_id,
        )

        return rollback.to_dict()

    def get_deployment(self, deployment_id: str) -> dict[str, Any] | None:
        dep = self._deployments.get(deployment_id)
        return dep.to_dict() if dep else None

    def get_all_deployments(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._deployments.values()]

    def get_manifests(self, app_id: str) -> list[dict[str, Any]]:
        return self._manifests.get_for_app(app_id)

    def get_topology_snapshot(self) -> dict[str, Any]:
        return self._topology.get_topology_snapshot().to_dict()

    def get_topology_hash(self) -> str:
        return self._topology.get_topology_hash()

    def get_active_rollouts(self) -> list[dict[str, Any]]:
        return self._rollouts.get_active_rollouts()

    def get_health(self) -> dict[str, Any]:
        return {
            "lifecycle_phase": self._lifecycle.current_phase,
            "manifests": self._manifests.get_stats(),
            "topology": self._topology.get_stats(),
            "provisioning": self._provisioning.get_stats(),
            "rollouts": self._rollouts.get_stats(),
            "rollbacks": self._rollbacks.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "manifests": self._manifests.get_stats(),
            "topology": self._topology.get_stats(),
            "provisioning": self._provisioning.get_stats(),
            "rollouts": self._rollouts.get_stats(),
            "rollbacks": self._rollbacks.get_stats(),
            "observability": self._observability.get_stats(),
            "deployments": len(self._deployments),
        }
