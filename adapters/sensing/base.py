"""Sensing adapter base class for UMH perception modalities.

All 12 sensing families implement this ABC. Unlike the request/response
Adapter protocol (adapters/protocol.py), sensing adapters are continuous
producers: they start, emit SignalEnvelopes over time, and stop.

Each adapter declares its family (camera, pose, face, etc.) and which
substrate socket it routes through. The SensingAdapterRegistry wires
adapters to the correct socket at boot.

UMH substrate subsystem.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from adapters.sensing.types import (
    AdapterFamily,
    AdapterHealth,
    SensingAdapterState,
    SensingSocketType,
)


class SensingAdapter(ABC):
    """Base class for all sensing adapters.

    Subclasses implement start/stop/get_signal for their specific
    hardware or software sensor. The registry manages lifecycle
    and routes emitted signals to the substrate spine.
    """

    def __init__(self, adapter_id: str) -> None:
        self._adapter_id = adapter_id
        self._health = AdapterHealth(
            adapter_id=adapter_id,
            family=self.adapter_family,
        )

    @property
    def adapter_id(self) -> str:
        return self._adapter_id

    @property
    @abstractmethod
    def adapter_family(self) -> AdapterFamily:
        """Which of the 12 sensing families this adapter belongs to."""
        ...

    @property
    @abstractmethod
    def socket_type(self) -> SensingSocketType:
        """Which substrate socket this adapter's signals route through."""
        ...

    @abstractmethod
    def start(self) -> bool:
        """Start the adapter. Returns True if successfully started."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the adapter and release resources."""
        ...

    @abstractmethod
    def get_signal(self) -> dict[str, object] | None:
        """Poll for the next signal. Returns None if no signal available.

        The returned dict is wrapped into a SignalEnvelope by the registry.
        Keys should include at minimum 'type' and 'data'.
        """
        ...

    def health(self) -> AdapterHealth:
        """Current health snapshot."""
        return self._health

    def _mark_started(self) -> None:
        self._health.state = SensingAdapterState.RUNNING
        self._health.started_at = datetime.now(timezone.utc).isoformat()

    def _mark_stopped(self) -> None:
        self._health.state = SensingAdapterState.STOPPED

    def _mark_error(self, error: str) -> None:
        self._health.state = SensingAdapterState.ERROR
        self._health.record_error(error)

    def _mark_degraded(self) -> None:
        self._health.state = SensingAdapterState.DEGRADED

    def _record_signal(self) -> None:
        self._health.record_signal()
