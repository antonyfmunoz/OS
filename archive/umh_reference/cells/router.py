"""Signal router — deterministic routing of cell signals to actions.

Routes append-only signals to structured routing decisions. The router
does NOT execute anything — it produces RoutingDecision objects that
the orchestrator can act on.

No imports from execution, adapters, tools, or shell.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Callable

from umh.cells.models import CellType, _gen_id
from umh.core.clock import iso_now as _iso_now


@unique
class RoutingAction(str, Enum):
    SPAWN_CELL = "spawn_cell"
    RESUME_CELL = "resume_cell"
    COMPLETE_STEP = "complete_step"
    FAIL_STEP = "fail_step"
    NOTIFY = "notify"
    NONE = "none"


@dataclass(frozen=True)
class SignalRoute:
    """A route that maps a signal type to an action."""

    route_id: str
    source_signal_type: str
    action: RoutingAction = RoutingAction.NONE
    target_cell_type: CellType | None = None
    target_cell_id: str | None = None
    workflow_id: str | None = None
    condition: dict[str, Any] | None = None
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "source_signal_type": self.source_signal_type,
            "action": self.action.value,
            "target_cell_type": self.target_cell_type.value if self.target_cell_type else None,
            "target_cell_id": self.target_cell_id,
            "workflow_id": self.workflow_id,
            "condition": self.condition,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class RoutingDecision:
    """Result of routing a signal — what action to take."""

    route_id: str
    action: RoutingAction
    signal_type: str
    signal_payload: dict[str, Any]
    target_cell_type: CellType | None = None
    target_cell_id: str | None = None
    workflow_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "action": self.action.value,
            "signal_type": self.signal_type,
            "signal_payload": self.signal_payload,
            "target_cell_type": self.target_cell_type.value if self.target_cell_type else None,
            "target_cell_id": self.target_cell_id,
            "workflow_id": self.workflow_id,
            "metadata": self.metadata,
        }


def _matches_condition(condition: dict[str, Any] | None, payload: dict[str, Any]) -> bool:
    """Check if signal payload matches a simple condition dict.

    Each key in condition must exist in payload with matching value.
    None condition always matches.
    """
    if condition is None:
        return True
    for key, value in condition.items():
        if payload.get(key) != value:
            return False
    return True


class SignalRouter:
    """Deterministic signal router. Routes signals to structured decisions."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._routes: dict[str, SignalRoute] = {}

    def register_route(self, route: SignalRoute) -> None:
        with self._lock:
            self._routes[route.route_id] = route

    def unregister_route(self, route_id: str) -> bool:
        with self._lock:
            return self._routes.pop(route_id, None) is not None

    def list_routes(self) -> list[SignalRoute]:
        with self._lock:
            return list(self._routes.values())

    def route_signal(
        self,
        signal_type: str,
        payload: dict[str, Any],
    ) -> list[RoutingDecision]:
        """Route a signal through all matching routes.

        Returns a list of RoutingDecision objects. Does NOT execute
        any actions — the caller (orchestrator) decides what to do.
        Deterministic: same signal always produces same decisions
        for the same route set.
        """
        with self._lock:
            routes = list(self._routes.values())

        decisions: list[RoutingDecision] = []
        for route in routes:
            if not route.enabled:
                continue
            if route.source_signal_type != signal_type:
                continue
            if not _matches_condition(route.condition, payload):
                continue

            decisions.append(
                RoutingDecision(
                    route_id=route.route_id,
                    action=route.action,
                    signal_type=signal_type,
                    signal_payload=payload,
                    target_cell_type=route.target_cell_type,
                    target_cell_id=route.target_cell_id,
                    workflow_id=route.workflow_id,
                    metadata=route.metadata,
                )
            )

        return decisions

    def clear(self) -> None:
        """Reset all routes — for testing only."""
        with self._lock:
            self._routes.clear()
