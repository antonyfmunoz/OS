"""UMH Protocol — Adapter Boundary Layer (Layer 8).

Covers adapter protocol (§14.1) and adapter packages (§14.3).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from .common import (
    AdapterCategory,
    CapabilityRef,
    EnvironmentType,
    GovernancePolicyRef,
    MasteryRef,
    MaturityStatus,
    ProofRequirement,
)


# ---------------------------------------------------------------------------
# §14.1 — Adapter Protocol
# ---------------------------------------------------------------------------


class Connection(BaseModel):
    """Result of adapter.connect(). Referenced in §14.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    connected: bool
    adapter_id: str
    session_id: str = ""
    metadata: dict[str, Any] = {}


class ValidationResult(BaseModel):
    """Result of adapter validation. Referenced in §14.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class ExternalRequest(BaseModel):
    """Translated request for an external system. Referenced in §14.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    request_id: str
    method: str
    target: str
    payload: dict[str, Any] = {}
    headers: dict[str, str] = {}
    metadata: dict[str, Any] = {}


class ExternalResponse(BaseModel):
    """Raw response from an external system. Referenced in §14.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    status_code: int
    body: Any = None
    headers: dict[str, str] = {}
    metadata: dict[str, Any] = {}


class NormalizedResult(BaseModel):
    """Normalized result after adapter processing. Referenced in §14.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    success: bool
    data: Any = None
    errors: list[str] = []
    metadata: dict[str, Any] = {}


class StateSnapshot(BaseModel):
    """Observed state from an external system. Referenced in §14.1."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    adapter_id: str
    timestamp: int
    state: dict[str, Any] = {}
    healthy: bool = True


@runtime_checkable
class Adapter(Protocol):
    """Adapter boundary protocol. Defined in canonical synthesis §14.1.

    Adapters translate external systems into UMH-readable contracts.
    Adapters do NOT independently execute. Workers execute.
    """

    def connect(self) -> Connection: ...
    def validate_connection(self) -> ValidationResult: ...
    def describe_capabilities(self) -> list[CapabilityRef]: ...
    def translate_request(self, work_packet: Any) -> ExternalRequest: ...
    def validate_operation(self, request: ExternalRequest) -> ValidationResult: ...
    def normalize_result(self, raw: ExternalResponse) -> NormalizedResult: ...
    def observe_state(self) -> StateSnapshot: ...
    def disconnect(self) -> None: ...


# ---------------------------------------------------------------------------
# §14.3 — Adapter Package
# ---------------------------------------------------------------------------


class AccessPath(BaseModel):
    """Specific method used through an adapter. Referenced in §14.4."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    path_id: str
    method: str
    description: str = ""


class AdapterPackage(BaseModel):
    """Adapter package definition. Defined in canonical synthesis §14.3."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    package_id: str
    name: str
    external_system: str
    category: AdapterCategory
    capabilities: list[CapabilityRef] = []
    access_paths: list[AccessPath] = []
    governance_policy: GovernancePolicyRef | None = None
    mastery_requirements: list[MasteryRef] = []
    supported_environments: list[EnvironmentType] = []
    proof_requirements: list[ProofRequirement] = []
    maturity_status: MaturityStatus = MaturityStatus.EXPERIMENTAL
    version: str = "0.1.0"
