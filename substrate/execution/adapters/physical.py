"""Physical Adapter Framework — hardware and IoT extension points.

Provides the contract and registry for physical-world adapters:
home automation, vehicle systems, health monitors, smart devices.

Each physical adapter:
  1. Implements the PhysicalAdapter protocol
  2. Registers with the PhysicalAdapterRegistry
  3. Gets governance-gated through the standard execution pipeline
  4. Produces typed observations for the reality model

Adapters are discovery-based: the registry scans for available
hardware at startup and registers what it finds. Missing hardware
is not an error — the system degrades gracefully.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PhysicalDomain(str, Enum):
    HOME_AUTOMATION = "home_automation"
    VEHICLE = "vehicle"
    HEALTH = "health"
    AUDIO_VIDEO = "audio_video"
    CLIMATE = "climate"
    SECURITY_PHYSICAL = "security_physical"
    LIGHTING = "lighting"
    CUSTOM = "custom"


class PhysicalCapability(str, Enum):
    READ_SENSOR = "read_sensor"
    WRITE_ACTUATOR = "write_actuator"
    STREAM_DATA = "stream_data"
    TRIGGER_ACTION = "trigger_action"
    QUERY_STATE = "query_state"
    SET_SCHEDULE = "set_schedule"
    OBSERVE = "observe"


class ConnectionType(str, Enum):
    HTTP_API = "http_api"
    MQTT = "mqtt"
    BLUETOOTH = "bluetooth"
    ZIGBEE = "zigbee"
    ZWAVE = "zwave"
    USB = "usb"
    GPIO = "gpio"
    LOCAL_NETWORK = "local_network"


@dataclass
class PhysicalDeviceInfo:
    device_id: str
    name: str
    domain: PhysicalDomain
    capabilities: list[PhysicalCapability]
    connection_type: ConnectionType
    location: str = ""
    manufacturer: str = ""
    model: str = ""
    firmware_version: str = ""
    online: bool = True
    last_seen: str = ""

    def __post_init__(self) -> None:
        if not self.last_seen:
            self.last_seen = datetime.now(timezone.utc).isoformat()


@dataclass
class PhysicalActionResult:
    success: bool
    device_id: str
    action: str
    result_data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class SensorReading:
    device_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: str = ""
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_observation(self) -> dict[str, Any]:
        return {
            "content": f"{self.sensor_type}: {self.value}{self.unit} from {self.device_id}",
            "domain": "physical",
            "confidence": self.confidence,
            "metadata": {
                "device_id": self.device_id,
                "sensor_type": self.sensor_type,
                "value": self.value,
                "unit": self.unit,
            },
        }


class PhysicalAdapter(ABC):
    """Base contract for physical-world adapters."""

    @abstractmethod
    def domain(self) -> PhysicalDomain:
        ...

    @abstractmethod
    def discover_devices(self) -> list[PhysicalDeviceInfo]:
        ...

    @abstractmethod
    def execute_action(
        self, device_id: str, action: str, params: dict[str, Any] | None = None
    ) -> PhysicalActionResult:
        ...

    @abstractmethod
    def read_sensor(self, device_id: str, sensor_type: str) -> SensorReading | None:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class HomeAssistantAdapter(PhysicalAdapter):
    """Home Assistant integration via REST API.

    Connects to a Home Assistant instance for home automation control.
    Requires HA_URL and HA_TOKEN environment variables.
    """

    def __init__(self, base_url: str = "", token: str = "") -> None:
        import os
        self._url = base_url or os.environ.get("HA_URL", "")
        self._token = token or os.environ.get("HA_TOKEN", "")
        self._devices: list[PhysicalDeviceInfo] = []

    def domain(self) -> PhysicalDomain:
        return PhysicalDomain.HOME_AUTOMATION

    def discover_devices(self) -> list[PhysicalDeviceInfo]:
        if not self.is_available():
            return []

        try:
            import urllib.request
            import json
            req = urllib.request.Request(
                f"{self._url}/api/states",
                headers={"Authorization": f"Bearer {self._token}"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                states = json.loads(resp.read())

            self._devices = []
            for state in states[:50]:
                entity_id = state.get("entity_id", "")
                domain_part = entity_id.split(".")[0] if "." in entity_id else ""

                domain_map = {
                    "light": PhysicalDomain.LIGHTING,
                    "switch": PhysicalDomain.HOME_AUTOMATION,
                    "climate": PhysicalDomain.CLIMATE,
                    "sensor": PhysicalDomain.HOME_AUTOMATION,
                    "lock": PhysicalDomain.SECURITY_PHYSICAL,
                    "media_player": PhysicalDomain.AUDIO_VIDEO,
                }

                self._devices.append(PhysicalDeviceInfo(
                    device_id=entity_id,
                    name=state.get("attributes", {}).get("friendly_name", entity_id),
                    domain=domain_map.get(domain_part, PhysicalDomain.CUSTOM),
                    capabilities=[PhysicalCapability.QUERY_STATE, PhysicalCapability.TRIGGER_ACTION],
                    connection_type=ConnectionType.HTTP_API,
                ))

            return self._devices
        except Exception as e:
            logger.debug("home assistant discovery failed: %s", e)
            return []

    def execute_action(
        self, device_id: str, action: str, params: dict[str, Any] | None = None
    ) -> PhysicalActionResult:
        if not self.is_available():
            return PhysicalActionResult(
                success=False, device_id=device_id, action=action,
                error="Home Assistant not available",
            )

        import json
        import time
        import urllib.request

        t0 = time.monotonic()
        domain_part = device_id.split(".")[0] if "." in device_id else ""
        service = action or "toggle"

        try:
            payload = json.dumps({"entity_id": device_id, **(params or {})}).encode()
            req = urllib.request.Request(
                f"{self._url}/api/services/{domain_part}/{service}",
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result_data = json.loads(resp.read()) if resp.status == 200 else {}

            return PhysicalActionResult(
                success=True,
                device_id=device_id,
                action=f"{domain_part}/{service}",
                result_data=result_data if isinstance(result_data, dict) else {"states": result_data},
                duration_ms=(time.monotonic() - t0) * 1000,
            )
        except Exception as e:
            return PhysicalActionResult(
                success=False, device_id=device_id, action=action,
                error=str(e),
                duration_ms=(time.monotonic() - t0) * 1000,
            )

    def read_sensor(self, device_id: str, sensor_type: str) -> SensorReading | None:
        if not self.is_available():
            return None

        import json
        import urllib.request

        try:
            req = urllib.request.Request(
                f"{self._url}/api/states/{device_id}",
                headers={"Authorization": f"Bearer {self._token}"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                state = json.loads(resp.read())

            value = state.get("state", "")
            try:
                numeric_value = float(value)
            except (ValueError, TypeError):
                return None

            unit = state.get("attributes", {}).get("unit_of_measurement", "")
            return SensorReading(
                device_id=device_id,
                sensor_type=sensor_type or state.get("attributes", {}).get("device_class", "unknown"),
                value=numeric_value,
                unit=unit,
            )
        except Exception as e:
            logger.debug("sensor read failed for %s: %s", device_id, e)
            return None

    def is_available(self) -> bool:
        return bool(self._url and self._token)


class PhysicalAdapterRegistry:
    """Registry for physical-world adapters.

    Mirrors the actuator backend registry pattern but for
    hardware/IoT devices. Discovery-based — only registers
    what's actually available.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, PhysicalAdapter] = {}
        self._devices: list[PhysicalDeviceInfo] = []

    def register(self, name: str, adapter: PhysicalAdapter) -> None:
        if adapter.is_available():
            self._adapters[name] = adapter
            logger.info("physical adapter registered: %s (%s)", name, adapter.domain().value)
        else:
            logger.debug("physical adapter %s not available, skipping", name)

    def discover_all(self) -> list[PhysicalDeviceInfo]:
        self._devices = []
        for name, adapter in self._adapters.items():
            try:
                devices = adapter.discover_devices()
                self._devices.extend(devices)
                logger.info("discovered %d devices from %s", len(devices), name)
            except Exception as e:
                logger.warning("discovery failed for %s: %s", name, e)
        return self._devices

    def execute(
        self, device_id: str, action: str, params: dict[str, Any] | None = None
    ) -> PhysicalActionResult:
        for adapter in self._adapters.values():
            devices = adapter.discover_devices()
            if any(d.device_id == device_id for d in devices):
                return adapter.execute_action(device_id, action, params)

        return PhysicalActionResult(
            success=False, device_id=device_id, action=action,
            error=f"No adapter found for device {device_id}",
        )

    def read_sensor(self, device_id: str, sensor_type: str = "") -> SensorReading | None:
        for adapter in self._adapters.values():
            reading = adapter.read_sensor(device_id, sensor_type)
            if reading is not None:
                return reading
        return None

    def list_adapters(self) -> dict[str, str]:
        return {name: adapter.domain().value for name, adapter in self._adapters.items()}

    def device_count(self) -> int:
        return len(self._devices)


def build_default_registry() -> PhysicalAdapterRegistry:
    """Build registry with auto-discovered adapters."""
    registry = PhysicalAdapterRegistry()
    registry.register("home_assistant", HomeAssistantAdapter())
    return registry
