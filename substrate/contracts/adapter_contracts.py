"""Adapter registry contracts — substrate-owned interface for adapter descriptors.

Canonical location for adapter type definitions. Moved from
adapters/adapter_engine/adapter_registry_contracts.py to enforce
correct dependency direction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from substrate.execution.runtime.worker_runtime_contracts import (
    AuthorityDomain,
    MessageBusType,
)


@dataclass
class CapabilityDescriptor:
    """A single action capability offered by an adapter."""

    capability_id: str
    action_type: str
    requires_gui: bool = False
    requires_local_shell: bool = False
    required_authority: AuthorityDomain = AuthorityDomain.LOCAL_SHELL
    notes: list[str] = field(default_factory=list)


@dataclass
class AdapterDescriptor:
    """Describes an adapter that bridges a worker to an execution target."""

    adapter_id: str
    adapter_type: str
    environment_type: str
    authority_domain: AuthorityDomain
    message_bus: MessageBusType
    capabilities: list[CapabilityDescriptor] = field(default_factory=list)
    modalities: list[Any] | None = None
    participant_type: Any | None = None
    version: str = "v1"
    notes: list[str] = field(default_factory=list)

    def supports(self, action_type: str) -> bool:
        return any(c.action_type == action_type for c in self.capabilities)


@dataclass
class AdapterRegistry:
    """Registry of available adapters and their capabilities."""

    workers: dict[str, dict[str, Any]] = field(default_factory=dict)
    adapters: dict[str, AdapterDescriptor] = field(default_factory=dict)

    def register_adapter(self, adapter: AdapterDescriptor) -> None:
        self.adapters[adapter.adapter_id] = adapter

    def find_adapter_for_action(self, action_type: str) -> AdapterDescriptor | None:
        for adapter in self.adapters.values():
            if adapter.supports(action_type):
                return adapter
        return None
