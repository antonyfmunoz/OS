"""Control plane runtime — the top-level orchestrator that wires everything together."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from ..foundation.identity import IdentityState
from ..foundation.laws import SUBSTRATE_LAWS
from ..foundation.perspective import PerspectiveStack
from ..protocols.signal import Signal
from ..protocols.trace import Trace
from .event_bus import EventBus
from .invariants import InvariantChecker
from .router import SignalRouter

logger = logging.getLogger(__name__)


class SubstrateRuntime:
    """The top-level runtime for the Jarvis substrate.

    Wires the event bus, invariant checker, signal router, and
    identity/perspective state into a coherent operational unit.
    """

    def __init__(self) -> None:
        self._event_bus = EventBus()
        self._invariant_checker = InvariantChecker()
        self._router = SignalRouter(self._event_bus, self._invariant_checker)
        self._identity = IdentityState()
        self._perspective_stack = PerspectiveStack()
        self._started_at: datetime | None = None
        self._signal_count: int = 0

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def invariant_checker(self) -> InvariantChecker:
        return self._invariant_checker

    @property
    def router(self) -> SignalRouter:
        return self._router

    @property
    def identity(self) -> IdentityState:
        return self._identity

    @property
    def perspective_stack(self) -> PerspectiveStack:
        return self._perspective_stack

    @property
    def is_running(self) -> bool:
        return self._started_at is not None

    async def start(self) -> None:
        """Initialize the runtime."""
        self._started_at = datetime.now(timezone.utc)
        logger.info("Substrate runtime started")

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        self._started_at = None
        logger.info("Substrate runtime shut down")

    async def ingest_signal(self, signal: Signal) -> Trace:
        """The single entry point for all signals into the substrate."""
        if not self.is_running:
            raise RuntimeError("Substrate runtime is not started")

        self._signal_count += 1
        trace = await self._router.intake(signal)
        return trace

    def health(self) -> dict:
        """Health check — returns current runtime state."""
        return {
            "status": "healthy" if self.is_running else "stopped",
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "signals_processed": self._signal_count,
            "laws_loaded": len(SUBSTRATE_LAWS),
            "violations_recorded": len(self._invariant_checker.violations),
            "identity_continuity": self._identity.continuity_score,
            "active_perspectives": len(self._perspective_stack.active_perspectives()),
            "event_bus_history_size": len(self._event_bus._history),
        }
