"""Proof protocol — verifiable evidence that operations occurred correctly."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ProofType(str, Enum):
    """What is being proven."""

    EXECUTION = "execution"
    GOVERNANCE = "governance"
    INVARIANT = "invariant"
    STATE_TRANSITION = "state_transition"
    CAPABILITY_USE = "capability_use"


class ProofStatus(str, Enum):
    """Verification status of the proof."""

    VERIFIED = "verified"
    PENDING = "pending"
    FAILED = "failed"
    EXPIRED = "expired"


class Proof(BaseModel):
    """Verifiable evidence that an operation occurred correctly."""

    id: UUID = Field(default_factory=uuid4)
    proof_type: ProofType
    status: ProofStatus = ProofStatus.PENDING
    claim: str = Field(max_length=300)
    evidence: dict[str, Any] = Field(default_factory=dict)
    trace_id: UUID | None = None
    verified_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verified_at: datetime | None = None
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_valid(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if self.status != ProofStatus.VERIFIED:
            return False
        if self.expires_at and self.expires_at < now:
            return False
        return True
