"""UMH Protocol — Governance Layer (Layer 6).

Defined in canonical synthesis §12.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .common import (
    AuthorityLevel,
    Constraint,
    EnvironmentType,
    Permission,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# §12 — Governance
# ---------------------------------------------------------------------------


class EscalationRule(BaseModel):
    """Rule for when to escalate. Referenced in §12."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    condition: str
    escalate_to: str
    description: str = ""


class ApprovalRequirement(BaseModel):
    """When approval is required. Referenced in §12."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    requirement_id: str
    condition: str
    approver: str = ""
    description: str = ""


class EnvironmentLimit(BaseModel):
    """Limit on actions within an environment. Referenced in §12."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    limit_id: str
    environment_type: EnvironmentType
    max_actions_per_hour: int | None = None
    allowed_risk_levels: list[RiskLevel] = []
    description: str = ""


class RiskModel(BaseModel):
    """Risk assessment model. Referenced in §12."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    risk_level: RiskLevel
    reversible: bool = True
    financial_exposure: float = 0.0
    data_sensitivity: str = ""
    description: str = ""


class GovernancePolicy(BaseModel):
    """Governance policy for an action or domain. Defined in canonical synthesis §12."""

    SCHEMA_VERSION: str = "1.0.0"
    model_config = ConfigDict(extra="forbid")

    authority_level: AuthorityLevel
    risk_model: RiskModel | None = None
    constraints: list[Constraint] = []
    permissions: list[Permission] = []
    escalation_rules: list[EscalationRule] = []
    approval_requirements: list[ApprovalRequirement] = []
    environment_limits: list[EnvironmentLimit] = []
