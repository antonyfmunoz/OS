"""Adapter registry contracts for the UMH substrate layer.

Typed descriptors for adapters and capabilities. An adapter is
a component that bridges a worker runtime to a specific execution
environment. The registry maps capabilities to adapters.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from execution.runtime.worker_runtime_contracts import (
    AuthorityDomain,
    MessageBusType,
)

from adapters.adapter_engine.modality import ModalityType
from adapters.adapter_engine.participant import ParticipantType


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
    modalities: list[ModalityType] | None = None
    participant_type: ParticipantType | None = None
    version: str = "v1"
    notes: list[str] = field(default_factory=list)

    def supports(self, action_type: str) -> bool:
        return any(c.action_type == action_type for c in self.capabilities)

    def get_capability(self, action_type: str) -> CapabilityDescriptor | None:
        for c in self.capabilities:
            if c.action_type == action_type:
                return c
        return None


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

    def register_manifest(self, manifest: "AdapterManifest") -> None:
        """Register an adapter from a Layer 3 AdapterManifest."""
        from adapters.adapter_engine.adapter_manifest import AdapterManifest

        descriptor = AdapterDescriptor(
            adapter_id=manifest.adapter_id,
            adapter_type=manifest.adapter_type,
            environment_type="",
            authority_domain=AuthorityDomain.LOCAL_SHELL,
            message_bus=MessageBusType.DIRECT_CALL,
            capabilities=list(manifest.capabilities),
            modalities=list(manifest.modalities),
            participant_type=manifest.participant_type,
            version=manifest.version,
            notes=list(manifest.notes),
        )
        self.adapters[manifest.adapter_id] = descriptor

    def find_gui_adapter(self) -> AdapterDescriptor | None:
        for adapter in self.adapters.values():
            if adapter.authority_domain == AuthorityDomain.LOCAL_GUI:
                return adapter
        return None

    def find_by_modality(self, modality: ModalityType) -> list[AdapterDescriptor]:
        """Find all adapters that use a given communication modality."""
        return [a for a in self.adapters.values() if a.modalities and modality in a.modalities]

    def find_by_participant_type(
        self,
        participant_type: ParticipantType,
    ) -> list[AdapterDescriptor]:
        """Find all adapters of a given participant type."""
        return [a for a in self.adapters.values() if a.participant_type == participant_type]

    @classmethod
    def from_json_file(cls, path: Path | str) -> AdapterRegistry:
        """Load registry from a JSON fixture file."""
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)

        registry = cls()
        registry.workers = data.get("workers", {})

        for adapter_id, adata in data.get("adapters", {}).items():
            caps = []
            for cdata in adata.get("capabilities", []):
                caps.append(
                    CapabilityDescriptor(
                        capability_id=cdata["capability_id"],
                        action_type=cdata["action_type"],
                        requires_gui=cdata.get("requires_gui", False),
                        requires_local_shell=cdata.get("requires_local_shell", False),
                        required_authority=AuthorityDomain(
                            cdata.get("required_authority", "local_shell")
                        ),
                        notes=cdata.get("notes", []),
                    )
                )
            raw_modalities = adata.get("modalities")
            modalities = [ModalityType(m) for m in raw_modalities] if raw_modalities else None
            raw_participant = adata.get("participant_type")
            participant_type = ParticipantType(raw_participant) if raw_participant else None

            registry.adapters[adapter_id] = AdapterDescriptor(
                adapter_id=adapter_id,
                adapter_type=adata["adapter_type"],
                environment_type=adata["environment_type"],
                authority_domain=AuthorityDomain(adata["authority_domain"]),
                message_bus=MessageBusType(adata["message_bus"]),
                capabilities=caps,
                modalities=modalities,
                participant_type=participant_type,
                version=adata.get("version", "v1"),
                notes=adata.get("notes", []),
            )

        return registry
