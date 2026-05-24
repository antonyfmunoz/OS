"""Sensing adapter type definitions for the UMH substrate.

Defines the 12 sensing adapter families, health model, and socket
routing type. Each family represents a distinct perception modality
that feeds signals into the substrate spine.

UMH substrate subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class AdapterFamily(str, Enum):
    """The 12 sensing modality families.

    Each family groups adapters that share a perception domain.
    A single physical device may host multiple families (e.g.,
    a webcam feeds both CAMERA and FACE families).
    """

    CAMERA = "camera"
    POSE = "pose"
    FACE = "face"
    GAZE = "gaze"
    TRACKING = "tracking"
    REID = "reid"
    WIFI_SENSING = "wifi_sensing"
    AUDIO = "audio"
    BIOMETRIC = "biometric"
    DRONE_DETECTION = "drone_detection"
    GESTURE = "gesture"
    COMPUTER_USE = "computer_use"


class SensingSocketType(str, Enum):
    """Which substrate socket a sensing adapter routes through."""

    SIGNAL = "signal"
    CAPABILITY = "capability"
    OUTCOME = "outcome"
    VIEW = "view"


class SensingAdapterState(str, Enum):
    """Lifecycle states for sensing adapters.

    Mirrors AdapterState from adapter_lifecycle_manager but scoped
    to the continuous-producer model of sensing adapters.
    """

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    ERROR = "error"


@dataclass
class AdapterHealth:
    """Health snapshot for a sensing adapter."""

    adapter_id: str
    family: AdapterFamily
    state: SensingAdapterState = SensingAdapterState.STOPPED
    last_signal_at: str = ""
    signals_emitted: int = 0
    errors: int = 0
    last_error: str = ""
    started_at: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return self.state in (SensingAdapterState.RUNNING, SensingAdapterState.STARTING)

    def record_signal(self) -> None:
        self.signals_emitted += 1
        self.last_signal_at = datetime.now(timezone.utc).isoformat()

    def record_error(self, error: str) -> None:
        self.errors += 1
        self.last_error = error

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "family": self.family.value,
            "state": self.state.value,
            "last_signal_at": self.last_signal_at,
            "signals_emitted": self.signals_emitted,
            "errors": self.errors,
            "last_error": self.last_error,
            "started_at": self.started_at,
            "metadata": dict(self.metadata),
        }
