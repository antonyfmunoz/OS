"""Canonical Application Projection Coordinator v1.

Coordinates governed application projection:
  registration, capability binding, domain contexts,
  continuity, topology, observability, replay.

Applications are NOT intelligence systems.
Applications are interfaces + domain surfaces + orchestration views
over substrate capabilities.

It NEVER executes outside spine.
It NEVER allows application-owned orchestration.
It NEVER allows application-owned governance.
It NEVER allows application-owned cognition.

UMH substrate subsystem. Phase 96.8CD.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.applications.application_projection_contracts_v1 import (
    ApplicationProjection,
    _now_iso,
)
from core.applications.application_lifecycle_engine_v1 import (
    ApplicationLifecycleEngine,
)
from core.applications.application_registry_engine_v1 import (
    ApplicationRegistryEngine,
)
from core.applications.capability_projection_engine_v1 import (
    CapabilityProjectionEngine,
)
from core.applications.domain_runtime_context_engine_v1 import (
    DomainRuntimeContextEngine,
)
from core.applications.application_continuity_engine_v1 import (
    ApplicationContinuityEngine,
)
from core.applications.application_observability_pipeline_v1 import (
    ApplicationObservabilityPipeline,
)
from core.applications.application_topology_engine_v1 import (
    ApplicationTopologyEngine,
)


class CanonicalApplicationProjectionCoordinator:
    """Coordinates all application projection operations.

    Cannot execute outside spine. Cannot allow application-owned
    orchestration. Cannot allow application-owned governance.
    Cannot allow application-owned cognition.
    Cannot allow application-owned canonical memory.
    Cannot allow application-owned learning mutation.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/applications",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = ApplicationLifecycleEngine()
        self._registry = ApplicationRegistryEngine(state_dir=self._state_dir)
        self._capabilities = CapabilityProjectionEngine(
            state_dir=self._state_dir,
        )
        self._contexts = DomainRuntimeContextEngine(
            state_dir=self._state_dir,
        )
        self._continuity = ApplicationContinuityEngine(
            state_dir=self._state_dir,
        )
        self._observability = ApplicationObservabilityPipeline(
            state_dir=self._state_dir / "observability",
        )
        self._topology = ApplicationTopologyEngine(
            state_dir=self._state_dir,
        )

    def register_application(
        self,
        app_id: str,
        name: str = "",
        trust_tier: str = "restricted",
        default_domain: str = "business",
    ) -> dict[str, Any]:
        app = self._registry.register(
            app_id=app_id,
            name=name,
            trust_tier=trust_tier,
            default_domain=default_domain,
        )

        self._topology.register_node(
            app_id=app_id,
            domain_context=app.get("default_domain", default_domain),
            capabilities=[],
        )

        self._observability.emit_application_registered(
            app_id=app_id,
            trust_tier=app["trust_tier"],
        )

        return app

    def bind_capability(
        self,
        app_id: str,
        capability_category: str,
    ) -> dict[str, Any] | None:
        app = self._registry.get(app_id)
        if app is None:
            return None

        trust_tier = app["trust_tier"]
        surface = self._capabilities.project_capability(
            app_id=app_id,
            capability_category=capability_category,
            trust_tier=trust_tier,
        )

        if surface is None:
            self._observability.emit_projection_denied(
                app_id=app_id,
                reason=f"capability {capability_category} denied for tier {trust_tier}",
            )
            return None

        self._registry.add_capability(app_id, capability_category)

        self._observability.emit_capability_bound(
            app_id=app_id,
            capability=capability_category,
        )

        return surface.to_dict()

    def create_projection(
        self,
        app_id: str,
        domain_context: str = "",
        capabilities: list[str] | None = None,
    ) -> dict[str, Any] | None:
        app = self._registry.get(app_id)
        if app is None:
            return None

        domain = domain_context or app.get("default_domain", "business")

        projection = ApplicationProjection(
            application_id=app_id,
            domain_context=domain,
            capabilities_bound=capabilities or app.get("capabilities", []),
            trust_tier=app["trust_tier"],
        )

        self._observability.emit_projection_created(
            app_id=app_id,
            projection_id=projection.projection_id,
        )

        return projection.to_dict()

    def start_context(
        self,
        app_id: str,
        domain_context: str = "",
        session_id: str = "",
    ) -> dict[str, Any] | None:
        app = self._registry.get(app_id)
        if app is None:
            return None

        domain = domain_context or app.get("default_domain", "business")
        ctx = self._contexts.start_context(
            app_id=app_id,
            domain_context=domain,
            session_id=session_id,
        )
        if ctx is None:
            return None

        self._observability.emit_application_context_started(
            app_id=app_id,
            domain_context=domain,
        )

        return ctx.to_dict()

    def restore_context(
        self,
        app_id: str,
        context_id: str,
    ) -> dict[str, Any] | None:
        ctx = self._contexts.restore_context(context_id)
        if ctx is None:
            return None

        self._observability.emit_application_context_restored(
            app_id=app_id,
            context_id=context_id,
        )

        return ctx.to_dict()

    def create_checkpoint(
        self,
        app_id: str,
        session_id: str = "",
        state_data: str = "",
    ) -> dict[str, Any]:
        return self._continuity.create_checkpoint(
            app_id=app_id,
            session_id=session_id,
            state_data=state_data,
        )

    def restore_continuity(self, app_id: str) -> dict[str, Any] | None:
        return self._continuity.restore(app_id)

    def get_application(self, app_id: str) -> dict[str, Any] | None:
        return self._registry.get(app_id)

    def get_all_applications(self) -> list[dict[str, Any]]:
        return self._registry.get_all()

    def get_capability_surfaces(
        self,
        app_id: str,
    ) -> list[dict[str, Any]]:
        return self._capabilities.get_surfaces_for_app(app_id)

    def get_capability_bindings(
        self,
        app_id: str,
    ) -> list[dict[str, Any]]:
        return self._capabilities.get_bindings_for_app(app_id)

    def get_contexts(self, app_id: str) -> list[dict[str, Any]]:
        return self._contexts.get_contexts_for_app(app_id)

    def get_domain_state(self, domain_context: str) -> dict[str, Any] | None:
        return self._contexts.get_domain_state(domain_context)

    def get_topology_snapshot(self) -> dict[str, Any]:
        return self._topology.get_topology_snapshot().to_dict()

    def get_topology_hash(self) -> str:
        return self._topology.get_topology_hash()

    def add_topology_edge(
        self,
        from_app: str,
        to_app: str,
        relationship: str = "shares_substrate",
    ) -> dict[str, Any] | None:
        return self._topology.add_edge(from_app, to_app, relationship)

    def verify_domain_isolation(
        self,
        domain_a: str,
        domain_b: str,
    ) -> bool:
        return self._topology.verify_domain_isolation(domain_a, domain_b)

    def get_health(self) -> dict[str, Any]:
        return {
            "lifecycle_state": self._lifecycle.current_state,
            "registry": self._registry.get_stats(),
            "capabilities": self._capabilities.get_stats(),
            "contexts": self._contexts.get_stats(),
            "topology": self._topology.get_stats(),
        }

    def get_stats(self) -> dict[str, Any]:
        return {
            "lifecycle": self._lifecycle.get_stats(),
            "registry": self._registry.get_stats(),
            "capabilities": self._capabilities.get_stats(),
            "contexts": self._contexts.get_stats(),
            "continuity": self._continuity.get_stats(),
            "observability": self._observability.get_stats(),
            "topology": self._topology.get_stats(),
        }
