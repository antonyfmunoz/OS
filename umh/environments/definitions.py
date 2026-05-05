"""Phase 76 MVP environment definitions.

Defines the environments the adapter pack supports: what capabilities
each environment enables, what constraints apply, and what safe roots
are configured for filesystem access.

Consumed by the governance gate and backend registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EnvironmentDefinition:
    environment_id: str
    description: str
    capabilities: frozenset[str]
    safe_roots: tuple[str, ...] = ()
    network_policy: str = "deny"
    available: bool = True
    constraints: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "description": self.description,
            "capabilities": sorted(self.capabilities),
            "safe_roots": list(self.safe_roots),
            "network_policy": self.network_policy,
            "available": self.available,
        }


MVP_ENVIRONMENTS: dict[str, EnvironmentDefinition] = {
    "local": EnvironmentDefinition(
        environment_id="local",
        description="Local machine — CLI + filesystem + network",
        capabilities=frozenset(
            {
                "cli.command",
                "filesystem.read",
                "filesystem.write",
                "filesystem.list",
                "http.get",
                "http.post",
                "browser.search",
                "browser.open",
                "browser.extract_text",
            }
        ),
        safe_roots=("/opt/OS", "/tmp/umh"),
        network_policy="allow_https",
    ),
    "vps": EnvironmentDefinition(
        environment_id="vps",
        description="VPS server — same as local for MVP",
        capabilities=frozenset(
            {
                "cli.command",
                "filesystem.read",
                "filesystem.write",
                "filesystem.list",
                "http.get",
                "http.post",
            }
        ),
        safe_roots=("/opt/OS", "/tmp/umh"),
        network_policy="allow_https",
    ),
    "filesystem": EnvironmentDefinition(
        environment_id="filesystem",
        description="Filesystem-only environment",
        capabilities=frozenset(
            {
                "filesystem.read",
                "filesystem.write",
                "filesystem.list",
            }
        ),
        safe_roots=("/opt/OS", "/tmp/umh"),
        network_policy="deny",
    ),
    "http": EnvironmentDefinition(
        environment_id="http",
        description="HTTP-only environment",
        capabilities=frozenset(
            {
                "http.get",
                "http.post",
            }
        ),
        network_policy="allow_https",
    ),
    "browser": EnvironmentDefinition(
        environment_id="browser",
        description="Browser environment (simulated in MVP)",
        capabilities=frozenset(
            {
                "browser.search",
                "browser.open",
                "browser.extract_text",
            }
        ),
        network_policy="simulated",
    ),
    "sandbox": EnvironmentDefinition(
        environment_id="sandbox",
        description="Sandbox — CLI only with restricted commands",
        capabilities=frozenset({"cli.command"}),
        safe_roots=("/tmp/umh",),
        network_policy="deny",
    ),
    "simulation": EnvironmentDefinition(
        environment_id="simulation",
        description="Simulated environment — no real execution",
        capabilities=frozenset(
            {
                "browser.search",
                "browser.open",
                "browser.extract_text",
            }
        ),
        network_policy="simulated",
    ),
}


def get_environment(env_id: str) -> EnvironmentDefinition | None:
    return MVP_ENVIRONMENTS.get(env_id)


def list_environments() -> list[EnvironmentDefinition]:
    return list(MVP_ENVIRONMENTS.values())
