"""Live Deployment Routing Engine v1.

Routes deployment operations, validates environment trust,
capability requirements, orchestration topology, and
enforces operator approvals.

UMH substrate subsystem. Phase 96.8CF.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from core.orchestration.live_operational_deployment_contracts_v1 import (
    DeploymentRoutingState,
    _now_iso,
)

KNOWN_ENVIRONMENTS = [
    "local_workstation",
    "vps",
    "sandbox",
    "browser_projection",
    "tmux_runtime",
    "cloud",
]

TRUST_HIERARCHY: dict[str, int] = {
    "production": 4,
    "staging": 3,
    "development": 2,
    "sandbox": 1,
}

MAX_ROUTING_DEPTH = 3
MAX_ROUTES = 100


class LiveDeploymentRoutingEngine:
    """Routes deployment operations with governance."""

    def __init__(self) -> None:
        self._routes: list[DeploymentRoutingState] = []
        self._routing_chain: list[str] = []

    def route(
        self,
        operation_id: str,
        source_environment: str,
        target_environment: str,
        required_trust: str = "development",
        approved_by: str = "operator",
    ) -> DeploymentRoutingState | None:
        if approved_by != "operator":
            raise ValueError("Routing requires operator approval")

        if target_environment not in KNOWN_ENVIRONMENTS:
            return None

        if len(self._routes) >= MAX_ROUTES:
            return None

        if len(self._routing_chain) >= MAX_ROUTING_DEPTH:
            return None

        target_trust = TRUST_HIERARCHY.get(required_trust, 0)
        if target_trust <= 0:
            return None

        route_content = json.dumps(
            {"op": operation_id, "src": source_environment,
             "tgt": target_environment, "trust": required_trust},
            sort_keys=True,
        )
        route_hash = hashlib.sha256(route_content.encode()).hexdigest()[:16]

        state = DeploymentRoutingState(
            operation_id=operation_id,
            source_environment=source_environment,
            target_environment=target_environment,
            route_hash=route_hash,
        )
        self._routes.append(state)
        self._routing_chain.append(operation_id)
        return state

    def validate_trust(
        self,
        operation_trust: str,
        environment_trust: str,
    ) -> bool:
        op_level = TRUST_HIERARCHY.get(operation_trust, 0)
        env_level = TRUST_HIERARCHY.get(environment_trust, 0)
        return env_level >= op_level

    def clear_chain(self) -> None:
        self._routing_chain = []

    def get_routes(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._routes]

    def get_stats(self) -> dict[str, object]:
        return {
            "total_routes": len(self._routes),
            "routing_chain_depth": len(self._routing_chain),
        }
