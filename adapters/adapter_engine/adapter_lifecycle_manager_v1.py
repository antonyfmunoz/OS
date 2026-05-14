"""Adapter Lifecycle Manager v1 for the canonical runtime spine.

Tracks adapter health, state transitions, and capability availability.
Wraps the existing AdapterRegistry with lifecycle state.

Adapter states: AVAILABLE → BUSY → AVAILABLE
                AVAILABLE → DEGRADED → AVAILABLE | OFFLINE
                AVAILABLE → OFFLINE → AVAILABLE (via explicit recovery)

UMH substrate subsystem. Phase 96.8BO.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from execution.runtime.execution_contracts_v1 import AdapterSelection, _now_iso, _new_id


class AdapterState(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class AdapterHealthRecord:
    """Health snapshot for a single adapter."""

    adapter_id: str
    adapter_type: str
    state: AdapterState = AdapterState.AVAILABLE
    capabilities: list[str] = field(default_factory=list)
    environment_type: str = ""
    last_execution_at: str = ""
    last_failure_at: str = ""
    consecutive_failures: int = 0
    total_executions: int = 0
    total_failures: int = 0
    last_heartbeat: str = ""
    notes: list[str] = field(default_factory=list)

    def is_available(self) -> bool:
        return self.state in (AdapterState.AVAILABLE, AdapterState.DEGRADED)

    def supports(self, action_type: str) -> bool:
        return action_type in self.capabilities

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_type": self.adapter_type,
            "state": self.state.value,
            "capabilities": self.capabilities,
            "environment_type": self.environment_type,
            "is_available": self.is_available(),
            "last_execution_at": self.last_execution_at,
            "last_failure_at": self.last_failure_at,
            "consecutive_failures": self.consecutive_failures,
            "total_executions": self.total_executions,
            "total_failures": self.total_failures,
            "last_heartbeat": self.last_heartbeat,
            "notes": self.notes,
        }


MAX_CONSECUTIVE_FAILURES = 3


class AdapterLifecycleManager:
    """Manages adapter lifecycle: registration, health, state transitions."""

    def __init__(self) -> None:
        self._adapters: dict[str, AdapterHealthRecord] = {}

    def register_adapter(
        self,
        adapter_id: str,
        adapter_type: str,
        capabilities: list[str] | None = None,
        environment_type: str = "",
    ) -> AdapterHealthRecord:
        """Register a new adapter or update an existing one."""
        record = AdapterHealthRecord(
            adapter_id=adapter_id,
            adapter_type=adapter_type,
            capabilities=capabilities or [],
            environment_type=environment_type,
            last_heartbeat=_now_iso(),
        )
        self._adapters[adapter_id] = record
        return record

    def get_adapter(self, adapter_id: str) -> AdapterHealthRecord | None:
        return self._adapters.get(adapter_id)

    def find_for_action(self, action_type: str) -> list[AdapterHealthRecord]:
        """Find all available adapters that support an action type."""
        return [a for a in self._adapters.values() if a.supports(action_type) and a.is_available()]

    def select_adapter(self, action_type: str, intent_id: str = "") -> AdapterSelection:
        """Select the best available adapter for an action."""
        candidates = self.find_for_action(action_type)
        if not candidates:
            return AdapterSelection(
                intent_id=intent_id,
                selected=False,
                rejection_reason=f"No available adapter for action {action_type}",
            )

        best = sorted(candidates, key=lambda a: a.consecutive_failures)[0]
        return AdapterSelection(
            intent_id=intent_id,
            adapter_id=best.adapter_id,
            adapter_type=best.adapter_type,
            capability_matched=action_type,
            environment_type=best.environment_type,
            selected=True,
        )

    def mark_busy(self, adapter_id: str) -> bool:
        adapter = self._adapters.get(adapter_id)
        if not adapter or adapter.state == AdapterState.OFFLINE:
            return False
        adapter.state = AdapterState.BUSY
        return True

    def mark_available(self, adapter_id: str) -> bool:
        adapter = self._adapters.get(adapter_id)
        if not adapter:
            return False
        adapter.state = AdapterState.AVAILABLE
        adapter.last_heartbeat = _now_iso()
        return True

    def record_execution_success(self, adapter_id: str) -> None:
        adapter = self._adapters.get(adapter_id)
        if not adapter:
            return
        adapter.total_executions += 1
        adapter.consecutive_failures = 0
        adapter.last_execution_at = _now_iso()
        if adapter.state == AdapterState.BUSY:
            adapter.state = AdapterState.AVAILABLE

    def record_execution_failure(self, adapter_id: str) -> None:
        adapter = self._adapters.get(adapter_id)
        if not adapter:
            return
        adapter.total_executions += 1
        adapter.total_failures += 1
        adapter.consecutive_failures += 1
        adapter.last_failure_at = _now_iso()
        if adapter.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            adapter.state = AdapterState.DEGRADED
            adapter.notes.append(
                f"Degraded after {adapter.consecutive_failures} consecutive failures"
            )

    def mark_offline(self, adapter_id: str, reason: str = "") -> bool:
        adapter = self._adapters.get(adapter_id)
        if not adapter:
            return False
        adapter.state = AdapterState.OFFLINE
        if reason:
            adapter.notes.append(f"Offline: {reason}")
        return True

    def recover(self, adapter_id: str) -> bool:
        """Recover an offline or degraded adapter."""
        adapter = self._adapters.get(adapter_id)
        if not adapter:
            return False
        adapter.state = AdapterState.AVAILABLE
        adapter.consecutive_failures = 0
        adapter.last_heartbeat = _now_iso()
        adapter.notes.append("Recovered")
        return True

    def heartbeat(self, adapter_id: str) -> bool:
        adapter = self._adapters.get(adapter_id)
        if not adapter:
            return False
        adapter.last_heartbeat = _now_iso()
        return True

    def get_available(self) -> list[AdapterHealthRecord]:
        return [a for a in self._adapters.values() if a.is_available()]

    def get_all(self) -> list[AdapterHealthRecord]:
        return list(self._adapters.values())

    def get_stats(self) -> dict[str, Any]:
        by_state: dict[str, int] = {}
        for a in self._adapters.values():
            by_state[a.state.value] = by_state.get(a.state.value, 0) + 1
        return {
            "total": len(self._adapters),
            "available": len(self.get_available()),
            "by_state": by_state,
            "total_executions": sum(a.total_executions for a in self._adapters.values()),
            "total_failures": sum(a.total_failures for a in self._adapters.values()),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapters": {aid: a.to_dict() for aid, a in self._adapters.items()},
            "stats": self.get_stats(),
        }
