"""Canonical Command Registry v1.

Single source of truth for all substrate command definitions.
Every runtime system that needs command information reads from
this registry — surface display, router dispatch, execution
gate, node sync, and supervisor.

Phase 96.8AL. UMH substrate.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RoutingMode(Enum):
    SPINE = "spine"
    ROUTER = "router"


class ExecutionMode(Enum):
    GUI = "gui"
    SHELL = "shell"
    HEADLESS = "headless"


@dataclass(frozen=True)
class CommandEntry:
    """A single canonical command definition."""

    command_name: str
    canonical_action: str
    routing_mode: RoutingMode
    governance_policy: str
    execution_mode: ExecutionMode
    foreground_required: bool = False
    readonly: bool = True
    require_screenshot_proof: bool = False
    required_runtime_state: str = "bootstrap_ready"
    required_proof_state: str = "initialized"
    required_environment: str = "local_windows_desktop"
    required_worker: str = "windows_interactive_desktop_relay"
    adapter_id: str = "windows_interactive_desktop_relay"
    capability_type: str = "WINDOWS_GUI_EXECUTION"

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_name": self.command_name,
            "canonical_action": self.canonical_action,
            "routing_mode": self.routing_mode.value,
            "governance_policy": self.governance_policy,
            "execution_mode": self.execution_mode.value,
            "foreground_required": self.foreground_required,
            "readonly": self.readonly,
            "require_screenshot_proof": self.require_screenshot_proof,
            "required_runtime_state": self.required_runtime_state,
            "required_proof_state": self.required_proof_state,
            "required_environment": self.required_environment,
            "required_worker": self.required_worker,
            "adapter_id": self.adapter_id,
            "capability_type": self.capability_type,
        }


CANONICAL_COMMANDS: tuple[CommandEntry, ...] = (
    CommandEntry(
        command_name="!ping",
        canonical_action="ping",
        routing_mode=RoutingMode.ROUTER,
        governance_policy="local_shell",
        execution_mode=ExecutionMode.SHELL,
        required_environment="local_wsl",
        capability_type="SHELL_EXECUTION",
    ),
    CommandEntry(
        command_name="!chrome",
        canonical_action="open_application_url",
        routing_mode=RoutingMode.ROUTER,
        governance_policy="local_gui",
        execution_mode=ExecutionMode.GUI,
    ),
    CommandEntry(
        command_name="!chrome-open-google-drive",
        canonical_action="chrome_open_google_drive",
        routing_mode=RoutingMode.SPINE,
        governance_policy="FOUNDER_APPROVAL",
        execution_mode=ExecutionMode.GUI,
    ),
    CommandEntry(
        command_name="!chrome-proof",
        canonical_action="chrome_proof",
        routing_mode=RoutingMode.SPINE,
        governance_policy="FOUNDER_APPROVAL",
        execution_mode=ExecutionMode.GUI,
        foreground_required=True,
        require_screenshot_proof=True,
    ),
    CommandEntry(
        command_name="!doc",
        canonical_action="drive_open_safe_test_doc",
        routing_mode=RoutingMode.ROUTER,
        governance_policy="local_gui",
        execution_mode=ExecutionMode.GUI,
    ),
    CommandEntry(
        command_name="!extract",
        canonical_action="doc_extract_safe_test_doc",
        routing_mode=RoutingMode.ROUTER,
        governance_policy="local_gui",
        execution_mode=ExecutionMode.GUI,
    ),
    CommandEntry(
        command_name="!ingest-candidate",
        canonical_action="doc_ingestion_candidate_safe_test_doc",
        routing_mode=RoutingMode.ROUTER,
        governance_policy="local_shell",
        execution_mode=ExecutionMode.SHELL,
        capability_type="DOCUMENT_EXTRACTION",
    ),
    CommandEntry(
        command_name="!ingest-safe-doc",
        canonical_action="ingest_safe_doc",
        routing_mode=RoutingMode.SPINE,
        governance_policy="FOUNDER_APPROVAL",
        execution_mode=ExecutionMode.GUI,
        capability_type="DOCUMENT_EXTRACTION",
    ),
    CommandEntry(
        command_name="!ingest-safe-doc-cu",
        canonical_action="ingest_safe_doc_cu",
        routing_mode=RoutingMode.SPINE,
        governance_policy="FOUNDER_APPROVAL",
        execution_mode=ExecutionMode.GUI,
        foreground_required=True,
        capability_type="DOCUMENT_EXTRACTION",
    ),
    CommandEntry(
        command_name="!explore-environment",
        canonical_action="explore_environment",
        routing_mode=RoutingMode.SPINE,
        governance_policy="FOUNDER_APPROVAL",
        execution_mode=ExecutionMode.GUI,
        foreground_required=True,
        require_screenshot_proof=True,
        capability_type="ENVIRONMENT_DISCOVERY",
    ),
    CommandEntry(
        command_name="!promote-memory",
        canonical_action="promote_safe_memory_candidate",
        routing_mode=RoutingMode.ROUTER,
        governance_policy="local_shell",
        execution_mode=ExecutionMode.SHELL,
        capability_type="MEMORY_GOVERNANCE",
    ),
    CommandEntry(
        command_name="!query-memory",
        canonical_action="query_safe_memory_reference",
        routing_mode=RoutingMode.ROUTER,
        governance_policy="local_shell",
        execution_mode=ExecutionMode.SHELL,
        capability_type="MEMORY_GOVERNANCE",
    ),
    CommandEntry(
        command_name="!actuator-proof",
        canonical_action="actuator_proof",
        routing_mode=RoutingMode.SPINE,
        governance_policy="FOUNDER_APPROVAL",
        execution_mode=ExecutionMode.GUI,
        foreground_required=True,
        require_screenshot_proof=True,
    ),
    CommandEntry(
        command_name="!adapter-report",
        canonical_action="adapter_report",
        routing_mode=RoutingMode.SPINE,
        governance_policy="FOUNDER_APPROVAL",
        execution_mode=ExecutionMode.SHELL,
        foreground_required=False,
        require_screenshot_proof=False,
        capability_type="ADAPTER_SYNTHESIS",
    ),
    CommandEntry(
        command_name="!relay-status",
        canonical_action="relay_status",
        routing_mode=RoutingMode.ROUTER,
        governance_policy="local_shell",
        execution_mode=ExecutionMode.SHELL,
        foreground_required=False,
        require_screenshot_proof=False,
        required_environment="local_wsl",
        required_worker="local_wsl_worker",
        adapter_id="local_wsl_worker",
        capability_type="SHELL_EXECUTION",
    ),
)


class CanonicalCommandRegistryV1:
    """The single canonical registry for all substrate commands.

    Constructed once, used everywhere. Every lookup — surface display,
    router dispatch, execution gate, node sync — reads from this object.
    """

    def __init__(self, entries: tuple[CommandEntry, ...] = CANONICAL_COMMANDS) -> None:
        self._entries = {e.command_name: e for e in entries}
        self._by_action = {e.canonical_action: e for e in entries}

    @property
    def commands(self) -> frozenset[str]:
        return frozenset(self._entries.keys())

    @property
    def actions(self) -> frozenset[str]:
        return frozenset(self._by_action.keys())

    def get(self, command: str) -> CommandEntry | None:
        return self._entries.get(command)

    def get_by_action(self, action: str) -> CommandEntry | None:
        return self._by_action.get(action)

    def contains(self, command: str) -> bool:
        return command in self._entries

    def contains_action(self, action: str) -> bool:
        return action in self._by_action

    @property
    def command_action_map(self) -> dict[str, str]:
        return {e.command_name: e.canonical_action for e in self._entries.values()}

    @property
    def spine_routed_commands(self) -> frozenset[str]:
        return frozenset(
            e.command_name for e in self._entries.values() if e.routing_mode == RoutingMode.SPINE
        )

    @property
    def router_routed_commands(self) -> frozenset[str]:
        return frozenset(
            e.command_name for e in self._entries.values() if e.routing_mode == RoutingMode.ROUTER
        )

    @property
    def allowed_action_types(self) -> list[str]:
        return sorted(e.canonical_action for e in self._entries.values())

    @property
    def command_contracts(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for e in self._entries.values():
            if e.routing_mode == RoutingMode.SPINE:
                result[e.command_name] = {
                    "command": e.command_name,
                    "capability": e.capability_type,
                    "adapter": e.adapter_id,
                    "environment": e.required_environment,
                    "authority_required": e.governance_policy,
                    "proof_required": True,
                    "mutation_allowed": not e.readonly,
                    "require_foreground_gui": e.foreground_required,
                    "require_screenshot_proof": e.require_screenshot_proof,
                    "require_foreground_cu": (e.foreground_required and "cu" in e.canonical_action),
                }
        return result

    def registry_hash(self) -> str:
        data = {
            e.command_name: e.to_dict()
            for e in sorted(self._entries.values(), key=lambda x: x.command_name)
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]

    def surface_hash(self) -> str:
        return hashlib.sha256(json.dumps(sorted(self._entries.keys())).encode()).hexdigest()[:12]

    def to_dict(self) -> dict[str, Any]:
        return {
            "commands": {name: e.to_dict() for name, e in sorted(self._entries.items())},
            "registry_hash": self.registry_hash(),
            "surface_hash": self.surface_hash(),
            "command_count": len(self._entries),
        }

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self):
        return iter(self._entries.values())


_GLOBAL_REGISTRY: CanonicalCommandRegistryV1 | None = None


def get_canonical_registry() -> CanonicalCommandRegistryV1:
    """Get the singleton canonical command registry."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = CanonicalCommandRegistryV1()
    return _GLOBAL_REGISTRY
