"""Phase 76 MVP capability definitions.

Maps capability IDs to metadata: risk level, authority required,
allowed environments, default timeout, and notes.

These definitions are consumed by the governance gate to make
allow/deny/approve decisions based on capability + environment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from umh.capabilities.spec import RiskLevel
from umh.governance.authority import AuthorityLevel


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    name: str
    risk_level: RiskLevel
    authority_required: AuthorityLevel
    allowed_environments: frozenset[str]
    default_timeout_s: int = 30
    requires_approval: bool = False
    expected_inputs: tuple[str, ...] = ()
    expected_outputs: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "risk_level": self.risk_level.value,
            "authority_required": self.authority_required.name,
            "allowed_environments": sorted(self.allowed_environments),
            "default_timeout_s": self.default_timeout_s,
            "requires_approval": self.requires_approval,
            "expected_inputs": list(self.expected_inputs),
            "expected_outputs": list(self.expected_outputs),
            "notes": self.notes,
        }


MVP_CAPABILITIES: dict[str, CapabilityDefinition] = {
    "cli.command": CapabilityDefinition(
        capability_id="cli.command",
        name="CLI Command",
        risk_level=RiskLevel.HIGH,
        authority_required=AuthorityLevel.ACT,
        allowed_environments=frozenset({"local", "vps", "sandbox"}),
        default_timeout_s=30,
        requires_approval=True,
        expected_inputs=("command",),
        expected_outputs=("exit_code", "stdout", "stderr"),
        notes="Approval required unless command is in safe allowlist",
    ),
    "filesystem.read": CapabilityDefinition(
        capability_id="filesystem.read",
        name="Filesystem Read",
        risk_level=RiskLevel.LOW,
        authority_required=AuthorityLevel.ANALYZE,
        allowed_environments=frozenset({"local", "vps", "filesystem"}),
        default_timeout_s=10,
        expected_inputs=("path",),
        expected_outputs=("content", "size", "exists"),
    ),
    "filesystem.write": CapabilityDefinition(
        capability_id="filesystem.write",
        name="Filesystem Write",
        risk_level=RiskLevel.MEDIUM,
        authority_required=AuthorityLevel.ACT,
        allowed_environments=frozenset({"local", "vps", "filesystem"}),
        default_timeout_s=10,
        requires_approval=True,
        expected_inputs=("path", "content"),
        expected_outputs=("path", "bytes_written"),
        notes="Writes restricted to configured safe roots",
    ),
    "filesystem.list": CapabilityDefinition(
        capability_id="filesystem.list",
        name="Filesystem List",
        risk_level=RiskLevel.LOW,
        authority_required=AuthorityLevel.ANALYZE,
        allowed_environments=frozenset({"local", "vps", "filesystem"}),
        default_timeout_s=10,
        expected_inputs=("path",),
        expected_outputs=("entries", "count"),
    ),
    "http.get": CapabilityDefinition(
        capability_id="http.get",
        name="HTTP GET",
        risk_level=RiskLevel.MEDIUM,
        authority_required=AuthorityLevel.ANALYZE,
        allowed_environments=frozenset({"local", "vps", "http"}),
        default_timeout_s=15,
        expected_inputs=("url",),
        expected_outputs=("status_code", "body", "headers"),
    ),
    "http.post": CapabilityDefinition(
        capability_id="http.post",
        name="HTTP POST",
        risk_level=RiskLevel.HIGH,
        authority_required=AuthorityLevel.ACT,
        allowed_environments=frozenset({"local", "vps", "http"}),
        default_timeout_s=15,
        requires_approval=True,
        expected_inputs=("url", "body"),
        expected_outputs=("status_code", "body", "headers"),
    ),
    "browser.search": CapabilityDefinition(
        capability_id="browser.search",
        name="Browser Search",
        risk_level=RiskLevel.MEDIUM,
        authority_required=AuthorityLevel.ANALYZE,
        allowed_environments=frozenset({"local", "browser", "simulation"}),
        default_timeout_s=10,
        expected_inputs=("query",),
        expected_outputs=("results",),
    ),
    "browser.open": CapabilityDefinition(
        capability_id="browser.open",
        name="Browser Open URL",
        risk_level=RiskLevel.MEDIUM,
        authority_required=AuthorityLevel.ANALYZE,
        allowed_environments=frozenset({"local", "browser", "simulation"}),
        default_timeout_s=15,
        expected_inputs=("url",),
        expected_outputs=("title", "text_preview"),
    ),
    "browser.extract_text": CapabilityDefinition(
        capability_id="browser.extract_text",
        name="Browser Extract Text",
        risk_level=RiskLevel.MEDIUM,
        authority_required=AuthorityLevel.ANALYZE,
        allowed_environments=frozenset({"local", "browser", "simulation"}),
        default_timeout_s=15,
        expected_inputs=("url",),
        expected_outputs=("text", "title"),
    ),
}


def get_capability(capability_id: str) -> CapabilityDefinition | None:
    return MVP_CAPABILITIES.get(capability_id)


def list_capabilities() -> list[CapabilityDefinition]:
    return list(MVP_CAPABILITIES.values())
