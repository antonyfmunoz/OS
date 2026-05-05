"""Phase 77 operator profile — identity-scoped workstation state.

This is the Phase 77 identity-scoped profile, distinct from the existing
profile.py which describes environment capabilities.  The operator profile
aggregates devices, environments, sessions, modes, and preferences for
a specific user.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from umh.core.clock import iso_now as _iso_now


@dataclass
class ExecutionPreference:
    """Advisory execution preference — does NOT override governance."""

    preferred_environment: str = "local"
    preferred_device: str = "default_vps"
    preferred_backend: str = ""
    fallback_environment: str = "simulation"
    allow_simulation_fallback: bool = True
    max_risk_without_approval: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "preferred_environment": self.preferred_environment,
            "preferred_device": self.preferred_device,
            "preferred_backend": self.preferred_backend,
            "fallback_environment": self.fallback_environment,
            "allow_simulation_fallback": self.allow_simulation_fallback,
            "max_risk_without_approval": self.max_risk_without_approval,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionPreference:
        return cls(
            preferred_environment=data.get("preferred_environment", "local"),
            preferred_device=data.get("preferred_device", "default_vps"),
            preferred_backend=data.get("preferred_backend", ""),
            fallback_environment=data.get("fallback_environment", "simulation"),
            allow_simulation_fallback=data.get("allow_simulation_fallback", True),
            max_risk_without_approval=data.get("max_risk_without_approval", "medium"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class OperatorProfile:
    """Identity-scoped workstation profile."""

    user_id: str
    workstation_id: str = ""
    active_mode: str = "command_center"
    active_session_id: str = ""
    active_tasks: list[str] = field(default_factory=list)
    active_traces: list[str] = field(default_factory=list)
    pending_approvals: list[str] = field(default_factory=list)
    execution_preference: ExecutionPreference = field(default_factory=ExecutionPreference)
    boot_sequences: list[str] = field(default_factory=list)
    continuity_state: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "workstation_id": self.workstation_id,
            "active_mode": self.active_mode,
            "active_session_id": self.active_session_id,
            "active_tasks": self.active_tasks,
            "active_traces": self.active_traces,
            "pending_approvals": self.pending_approvals,
            "execution_preference": self.execution_preference.to_dict(),
            "boot_sequences": self.boot_sequences,
            "continuity_state": self.continuity_state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatorProfile:
        pref_data = data.get("execution_preference", {})
        return cls(
            user_id=data["user_id"],
            workstation_id=data.get("workstation_id", ""),
            active_mode=data.get("active_mode", "command_center"),
            active_session_id=data.get("active_session_id", ""),
            active_tasks=data.get("active_tasks", []),
            active_traces=data.get("active_traces", []),
            pending_approvals=data.get("pending_approvals", []),
            execution_preference=ExecutionPreference.from_dict(pref_data)
            if pref_data
            else ExecutionPreference(),
            boot_sequences=data.get("boot_sequences", []),
            continuity_state=data.get("continuity_state", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata", {}),
        )


def create_default_profile(user_id: str) -> OperatorProfile:
    now = _iso_now()
    return OperatorProfile(
        user_id=user_id,
        workstation_id=f"ws_{uuid.uuid4().hex[:12]}",
        active_mode="command_center",
        execution_preference=ExecutionPreference(),
        created_at=now,
        updated_at=now,
    )


def load_or_create_profile(
    user_id: str,
    store: Any | None = None,
) -> OperatorProfile:
    """Load profile from store or create default."""
    if store is not None:
        data = store.get(f"profile:{user_id}")
        if data is not None:
            return OperatorProfile.from_dict(data)

    profile = create_default_profile(user_id)

    if store is not None:
        store.put(f"profile:{user_id}", profile.to_dict())

    return profile


def save_profile(profile: OperatorProfile, store: Any) -> None:
    profile.updated_at = _iso_now()
    store.put(f"profile:{profile.user_id}", profile.to_dict())
