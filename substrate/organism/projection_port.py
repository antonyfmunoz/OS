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

import logging
from abc import ABC, abstractmethod
from enum import Enum
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
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, ProjectionSubscriber] = {}

    def register(self, subscriber: ProjectionSubscriber) -> None:
        self._subscribers[subscriber.subscriber_id] = subscriber
        logger.debug("projection registered: %s", subscriber.subscriber_id)

    def unregister(self, subscriber_id: str) -> None:
        self._subscribers.pop(subscriber_id, None)
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
