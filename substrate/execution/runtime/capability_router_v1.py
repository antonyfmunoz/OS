"""Capability Router v1 for the canonical runtime spine.

Maps commands to capability domains and resolves which environments
and adapters can fulfill them. Pure lookup — no ML, no scoring.

The router answers: "What does this command need, and who can provide it?"
The governance bridge answers: "Is this command allowed?"

UMH substrate subsystem. Phase 96.8BO.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .execution_contracts_v1 import (
    CapabilityDomain,
    CapabilityResolution,
    InterpretedIntent,
    RiskClass,
    _now_iso,
)
from .environment_registry_v1 import EnvironmentDescriptor, EnvironmentRegistry


# ---------------------------------------------------------------------------
# Command → Capability mapping
# ---------------------------------------------------------------------------

COMMAND_CAPABILITY_MAP: dict[str, CapabilityDomain] = {
    # Read-only / diagnostic
    "runtime-status": CapabilityDomain.FILESYSTEM_READ,
    "capabilities": CapabilityDomain.FILESYSTEM_READ,
    "adapters": CapabilityDomain.FILESYSTEM_READ,
    "execution-queue": CapabilityDomain.FILESYSTEM_READ,
    "resume-runtime": CapabilityDomain.FILESYSTEM_READ,
    "runtime-replay": CapabilityDomain.FILESYSTEM_READ,
    "memory-query": CapabilityDomain.MEMORY_QUERY,
    "memory-lineage": CapabilityDomain.MEMORY_QUERY,
    "git-status": CapabilityDomain.GIT_INSPECTION,
    "git-log": CapabilityDomain.GIT_INSPECTION,
    "tmux-status": CapabilityDomain.SHELL_EXECUTION,
    # Reports
    "constitution-report": CapabilityDomain.REPORT_GENERATION,
    "economics-report": CapabilityDomain.REPORT_GENERATION,
    "federation-report": CapabilityDomain.REPORT_GENERATION,
    "governance-intelligence-report": CapabilityDomain.REPORT_GENERATION,
    "continuity-report": CapabilityDomain.REPORT_GENERATION,
    "orchestration-report": CapabilityDomain.REPORT_GENERATION,
    "strategy-report": CapabilityDomain.REPORT_GENERATION,
    "epistemic-report": CapabilityDomain.REPORT_GENERATION,
    "identity-report": CapabilityDomain.REPORT_GENERATION,
    "telos-report": CapabilityDomain.REPORT_GENERATION,
    "resilience-report": CapabilityDomain.REPORT_GENERATION,
    "capability-report": CapabilityDomain.REPORT_GENERATION,
    "adapter-report": CapabilityDomain.REPORT_GENERATION,
    # Ingestion
    "ingest-safe-doc-cu": CapabilityDomain.DOCUMENT_INGESTION,
    "ingest-safe-doc": CapabilityDomain.DOCUMENT_INGESTION,
    # Memory write
    "promote-safe-memory-candidate": CapabilityDomain.MEMORY_WRITE,
    # GUI
    "chrome-proof": CapabilityDomain.GUI_ACTUATION,
    "chrome-open-google-drive": CapabilityDomain.GUI_ACTUATION,
    "open-application-url": CapabilityDomain.GUI_ACTUATION,
    # Shell
    "explore-environment": CapabilityDomain.SHELL_EXECUTION,
    "ping": CapabilityDomain.SHELL_EXECUTION,
    "relay-status": CapabilityDomain.SHELL_EXECUTION,
}

# Commands that are structurally safe (read-only, no side effects)
SAFE_COMMANDS: frozenset[str] = frozenset(
    {
        "runtime-status",
        "capabilities",
        "adapters",
        "execution-queue",
        "resume-runtime",
        "runtime-replay",
        "memory-query",
        "memory-lineage",
        "git-status",
        "git-log",
        "tmux-status",
        "constitution-report",
        "economics-report",
        "federation-report",
        "governance-intelligence-report",
        "continuity-report",
        "orchestration-report",
        "strategy-report",
        "epistemic-report",
        "identity-report",
        "telos-report",
        "resilience-report",
        "capability-report",
        "adapter-report",
        "ping",
        "relay-status",
        "explore-environment",
    }
)

# Risk classification by command
COMMAND_RISK_MAP: dict[str, RiskClass] = {
    "runtime-status": RiskClass.SAFE,
    "capabilities": RiskClass.SAFE,
    "adapters": RiskClass.SAFE,
    "execution-queue": RiskClass.SAFE,
    "resume-runtime": RiskClass.SAFE,
    "runtime-replay": RiskClass.SAFE,
    "memory-query": RiskClass.SAFE,
    "memory-lineage": RiskClass.SAFE,
    "git-status": RiskClass.SAFE,
    "git-log": RiskClass.SAFE,
    "tmux-status": RiskClass.SAFE,
    "ping": RiskClass.SAFE,
    "relay-status": RiskClass.SAFE,
    "explore-environment": RiskClass.LOW,
    "constitution-report": RiskClass.LOW,
    "economics-report": RiskClass.LOW,
    "federation-report": RiskClass.LOW,
    "governance-intelligence-report": RiskClass.LOW,
    "continuity-report": RiskClass.LOW,
    "orchestration-report": RiskClass.LOW,
    "strategy-report": RiskClass.LOW,
    "epistemic-report": RiskClass.LOW,
    "identity-report": RiskClass.LOW,
    "telos-report": RiskClass.LOW,
    "resilience-report": RiskClass.LOW,
    "capability-report": RiskClass.LOW,
    "adapter-report": RiskClass.LOW,
    "ingest-safe-doc-cu": RiskClass.MEDIUM,
    "ingest-safe-doc": RiskClass.MEDIUM,
    "promote-safe-memory-candidate": RiskClass.MEDIUM,
    "chrome-proof": RiskClass.MEDIUM,
    "chrome-open-google-drive": RiskClass.MEDIUM,
    "open-application-url": RiskClass.MEDIUM,
}

FORBIDDEN_COMMANDS: frozenset[str] = frozenset(
    {
        "wallet-execution",
        "financial-execution",
        "credential-access",
        "recursive-runtime-spawning",
        "canonical-mutation-without-governance",
        "self-govern",
    }
)


# ---------------------------------------------------------------------------
# Route result
# ---------------------------------------------------------------------------


@dataclass
class CapabilityRoute:
    """Complete routing decision for a command."""

    command_name: str
    capability: CapabilityDomain | None = None
    risk_class: RiskClass = RiskClass.SAFE
    is_safe: bool = False
    is_forbidden: bool = False
    candidate_environments: list[EnvironmentDescriptor] = field(default_factory=list)
    selected_environment: EnvironmentDescriptor | None = None
    resolution_notes: list[str] = field(default_factory=list)

    @property
    def routable(self) -> bool:
        return (
            self.capability is not None
            and not self.is_forbidden
            and len(self.candidate_environments) > 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "command_name": self.command_name,
            "capability": self.capability.value if self.capability else None,
            "risk_class": self.risk_class.value,
            "is_safe": self.is_safe,
            "is_forbidden": self.is_forbidden,
            "routable": self.routable,
            "candidate_environments": [e.environment_id for e in self.candidate_environments],
            "selected_environment": (
                self.selected_environment.environment_id if self.selected_environment else None
            ),
            "resolution_notes": self.resolution_notes,
        }


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class CapabilityRouter:
    """Routes commands to capabilities, environments, and adapters."""

    def __init__(self, environment_registry: EnvironmentRegistry) -> None:
        self._env_registry = environment_registry

    def resolve(self, command_name: str) -> CapabilityRoute:
        """Resolve a command to its capability route."""
        normalized = command_name.lstrip("!").strip()

        if normalized in FORBIDDEN_COMMANDS:
            return CapabilityRoute(
                command_name=normalized,
                is_forbidden=True,
                risk_class=RiskClass.FORBIDDEN,
                resolution_notes=[f"Command {normalized} is structurally forbidden"],
            )

        capability = COMMAND_CAPABILITY_MAP.get(normalized)
        if capability is None:
            return CapabilityRoute(
                command_name=normalized,
                resolution_notes=[f"No capability mapping for command {normalized}"],
            )

        risk = COMMAND_RISK_MAP.get(normalized, RiskClass.MEDIUM)
        is_safe = normalized in SAFE_COMMANDS

        candidates = self._env_registry.find_for_capability(capability)
        selected = self._select_best_environment(candidates, capability)

        return CapabilityRoute(
            command_name=normalized,
            capability=capability,
            risk_class=risk,
            is_safe=is_safe,
            candidate_environments=candidates,
            selected_environment=selected,
            resolution_notes=[f"Resolved {normalized} → {capability.value}"],
        )

    def resolve_intent(self, intent: InterpretedIntent) -> CapabilityResolution:
        """Resolve an interpreted intent to a capability resolution."""
        route = self.resolve(intent.command_name)

        available = []
        if route.capability:
            available = [route.capability.value]

        return CapabilityResolution(
            intent_id=intent.intent_id,
            required_capabilities=intent.required_capabilities
            or ([route.capability.value] if route.capability else []),
            available_capabilities=available,
        )

    def get_risk_class(self, command_name: str) -> RiskClass:
        """Get the risk classification for a command."""
        normalized = command_name.lstrip("!").strip()
        if normalized in FORBIDDEN_COMMANDS:
            return RiskClass.FORBIDDEN
        return COMMAND_RISK_MAP.get(normalized, RiskClass.MEDIUM)

    def is_safe_command(self, command_name: str) -> bool:
        """Check if a command is structurally safe."""
        return command_name.lstrip("!").strip() in SAFE_COMMANDS

    def get_all_commands(self) -> list[str]:
        """Return all registered commands."""
        return sorted(COMMAND_CAPABILITY_MAP.keys())

    def get_safe_commands(self) -> list[str]:
        """Return all safe commands."""
        return sorted(SAFE_COMMANDS)

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_commands": len(COMMAND_CAPABILITY_MAP),
            "safe_commands": len(SAFE_COMMANDS),
            "forbidden_commands": len(FORBIDDEN_COMMANDS),
            "capabilities_in_use": len(set(COMMAND_CAPABILITY_MAP.values())),
        }

    def _select_best_environment(
        self,
        candidates: list[EnvironmentDescriptor],
        capability: CapabilityDomain,
    ) -> EnvironmentDescriptor | None:
        """Select the best environment from candidates. Prefers VPS for non-GUI."""
        if not candidates:
            return None
        if capability == CapabilityDomain.GUI_ACTUATION:
            gui_envs = [e for e in candidates if e.can_gui]
            return gui_envs[0] if gui_envs else candidates[0]
        remote = [e for e in candidates if e.is_remote]
        return remote[0] if remote else candidates[0]
