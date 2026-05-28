"""Projection-agnostic organism state port.

Abstract port that any projection can register against to receive
organism state updates. Follows the socket/port pattern used
throughout UMH substrate (see substrate/sockets/).

Projections register as subscribers with optional slice filtering.
The port broadcasts state updates and bridges EventSpine events
to the appropriate state slices.

No projection-specific code lives here. The port knows about
state slices, not about cockpits, EOS, or any specific consumer.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateSlice(str, Enum):
    RUNTIMES = "runtimes"
    OBJECTIVES = "objectives"
    GOVERNANCE = "governance"
    LEVERAGE = "leverage"
    WORKCELLS = "workcells"
    ECONOMY = "economy"
    OBSERVABILITY = "observability"
    SUPERVISOR = "supervisor"
    ADVISORS = "advisors"


class ProjectionSubscriber(ABC):
    """Interface that projections implement to receive state updates."""

    @property
    @abstractmethod
    def subscriber_id(self) -> str: ...

    @abstractmethod
    def accepts_slices(self) -> set[StateSlice] | None:
        """Return the set of slices this projection wants.
        None means all slices.
        """
        ...

    @abstractmethod
    def on_state_update(self, slice_type: StateSlice, data: dict[str, Any]) -> None: ...


class OrganismStatePort:
    """Projection-agnostic organism state broadcast port.

    Register any number of projections. Each receives state
    updates filtered by the slices they accept.
    Persists subscriber IDs for restart rehydration awareness.
    """

    def __init__(self, state_dir: str | None = None) -> None:
        self._subscribers: dict[str, ProjectionSubscriber] = {}
        self._state_path: Path | None = None
        if state_dir is not None:
            p = Path(state_dir)
            p.mkdir(parents=True, exist_ok=True)
            self._state_path = p / "projection_subscribers.json"

    def register(self, subscriber: ProjectionSubscriber) -> None:
        self._subscribers[subscriber.subscriber_id] = subscriber
        self._persist_registry()
        logger.debug("projection registered: %s", subscriber.subscriber_id)

    def unregister(self, subscriber_id: str) -> None:
        self._subscribers.pop(subscriber_id, None)
        self._persist_registry()
        logger.debug("projection unregistered: %s", subscriber_id)

    def registered_projections(self) -> list[str]:
        return list(self._subscribers.keys())

    def broadcast(self, slice_type: StateSlice, data: dict[str, Any]) -> None:
        for sub in self._subscribers.values():
            accepted = sub.accepts_slices()
            if accepted is not None and slice_type not in accepted:
                continue
            try:
                sub.on_state_update(slice_type, data)
            except Exception as exc:
                logger.warning(
                    "projection '%s' raised %s: %s",
                    sub.subscriber_id, type(exc).__name__, exc,
                )

    def bridge_from_spine(
        self,
        spine: Any,
        domain_to_slice: dict[Any, StateSlice],
    ) -> None:
        """Subscribe to EventSpine and forward events to projections.

        Maps EventDomains to StateSlices so projections receive
        typed state updates without knowing about the event spine.
        """
        from substrate.organism.event_spine import EventDomain, OrganismEvent

        domains = set(domain_to_slice.keys())

        def _on_event(event: OrganismEvent) -> None:
            slice_type = domain_to_slice.get(event.domain)
            if slice_type is not None:
                self.broadcast(slice_type, {
                    "event_type": event.event_type,
                    "source": event.source,
                    "data": event.data,
                    "correlation_id": event.correlation_id,
                })

        spine.subscribe("state_port_bridge", _on_event, domains=domains)

    def _persist_registry(self) -> None:
        if self._state_path is None:
            return
        try:
            data = {
                sid: {
                    "slices": sorted(s.value for s in (sub.accepts_slices() or set())),
                }
                for sid, sub in self._subscribers.items()
            }
            tmp = self._state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2))
            tmp.rename(self._state_path)
        except Exception as exc:
            logger.warning("projection registry persist failed: %s", exc)

    def known_subscriber_ids(self) -> list[str]:
        """Return subscriber IDs from persisted state (for rehydration)."""
        if self._state_path is None or not self._state_path.exists():
            return []
        try:
            data = json.loads(self._state_path.read_text())
            return list(data.keys())
        except Exception:
            return []

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_subscribers": list(self._subscribers.keys()),
            "known_subscribers": self.known_subscriber_ids(),
        }
