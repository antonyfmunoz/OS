"""Governance protocol — decisions about whether and how to execute."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class GovernanceDecision(str, Enum):
    """The outcome of a governance evaluation."""

    APPROVE = "approve"
    DENY = "deny"
    DEFER = "defer"
    ESCALATE = "escalate"
    CONDITIONAL = "conditional"


class RiskLevel(str, Enum):
    """Assessed risk of the proposed action."""

    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GovernanceCondition(BaseModel):
    """A condition that must be met for conditional approval."""

    condition: str = Field(max_length=200)
    verified: bool = False
    verified_at: datetime | None = None


class GovernanceRequest(BaseModel):
    """A request for governance decision on a proposed action."""

    id: UUID = Field(default_factory=uuid4)
    decomposition_id: UUID
    component_id: UUID
    proposed_action: str = Field(max_length=300)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    reversible: bool = True
    affects_external: bool = False
    requires_resources: list[str] = Field(default_factory=list)
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GovernanceVerdict(BaseModel):
    """The governance layer's decision on a request."""

    id: UUID = Field(default_factory=uuid4)
    request_id: UUID
    decision: GovernanceDecision
    risk_level: RiskLevel
    rationale: str = Field(max_length=300)
    conditions: list[GovernanceCondition] = Field(default_factory=list)
    expires_at: datetime | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by: str = Field(default="substrate", max_length=80)

    def is_executable(self) -> bool:
        if self.decision == GovernanceDecision.APPROVE:
            return True
        if self.decision == GovernanceDecision.CONDITIONAL:
            return all(c.verified for c in self.conditions)
        return False
