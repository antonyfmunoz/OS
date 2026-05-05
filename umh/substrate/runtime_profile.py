"""
umh.substrate.runtime_profile — User-defined startup/runtime profile
contracts for the harness layer.

These are NOT hardcoded profession/persona profiles. They are declarative
environment/runtime boot recipes owned by the user instance. The harness
stores and resolves them; external adapters consume startup_actions as
symbolic identifiers — no app launching or process control here.

All state transitions expressed as SET/REMOVE mutations for replay safety.

Public API:
    RuntimeProfile                  — frozen profile record
    compute_runtime_profile_id      — deterministic profile ID
    build_runtime_profile           — construct a new profile
    profile_to_dict                 — serialize to plain dict
    profile_from_dict               — reconstruct from plain dict
    load_runtime_profile            — load from state
    list_runtime_profiles           — enumerate profile IDs from state
    build_runtime_profile_mutations — persistence mutations

Separation note:
    This module is harness-only. No app-specific assumptions, no
    Discord/Notion/VSCode/OBS/browser logic. Profiles are generic
    and instance-defined.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

_LOG_PREFIX = "[substrate.runtime_profile]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_PROFILE_KEY_PREFIX = "runtime_profile."
_PROFILE_INDEX_PREFIX = "runtime_profile_index."


def _profile_key(profile_id: str) -> str:
    return f"{_PROFILE_KEY_PREFIX}{profile_id}"


def _profile_index_key(profile_id: str) -> str:
    return f"{_PROFILE_INDEX_PREFIX}{profile_id}"


# ---------------------------------------------------------------------------
# RuntimeProfile — frozen profile record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RuntimeProfile:
    """Immutable user-defined startup/runtime profile.

    Fields:
        profile_id:            deterministic profile identifier
        name:                  human-readable profile name
        default_mode:          runtime mode to activate on profile load
        default_presence:      presence state to set on profile load
        startup_actions:       symbolic action identifiers (NOT app launchers)
        activation_rules:      symbolic rule identifiers for auto-activation
        delivery_policy:       delivery behavior tag for this profile
        continuity_policy:     continuity behavior tag for this profile
        transport_preferences: ordered transport preference identifiers
        execution_policy:      execution behavior tag for this profile
        created_at:            ISO timestamp of creation
        updated_at:            ISO timestamp of last update
    """

    profile_id: str
    name: str
    default_mode: str
    default_presence: str
    startup_actions: tuple[str, ...] = ()
    activation_rules: tuple[str, ...] = ()
    delivery_policy: str = ""
    continuity_policy: str = ""
    transport_preferences: tuple[str, ...] = ()
    execution_policy: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        now = _utcnow()
        if not self.created_at:
            object.__setattr__(self, "created_at", now)
        if not self.updated_at:
            object.__setattr__(self, "updated_at", now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "activation_rules": list(self.activation_rules),
            "continuity_policy": self.continuity_policy,
            "created_at": self.created_at,
            "default_mode": self.default_mode,
            "default_presence": self.default_presence,
            "delivery_policy": self.delivery_policy,
            "execution_policy": self.execution_policy,
            "name": self.name,
            "profile_id": self.profile_id,
            "startup_actions": list(self.startup_actions),
            "transport_preferences": list(self.transport_preferences),
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> RuntimeProfile:
        """Reconstruct from plain dict."""
        return RuntimeProfile(
            profile_id=str(d.get("profile_id", "")),
            name=str(d.get("name", "")),
            default_mode=str(d.get("default_mode", "")),
            default_presence=str(d.get("default_presence", "")),
            startup_actions=tuple(d.get("startup_actions", ())),
            activation_rules=tuple(d.get("activation_rules", ())),
            delivery_policy=str(d.get("delivery_policy", "")),
            continuity_policy=str(d.get("continuity_policy", "")),
            transport_preferences=tuple(d.get("transport_preferences", ())),
            execution_policy=str(d.get("execution_policy", "")),
            created_at=str(d.get("created_at", "")),
            updated_at=str(d.get("updated_at", "")),
        )


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_runtime_profile_id(name: str) -> str:
    """Deterministic profile ID from name.

    Uses SHA-256 of canonical JSON. Same name always yields the same ID.
    """
    canonical = json.dumps(
        {"name": name},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"prof_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def build_runtime_profile(
    *,
    name: str,
    default_mode: str,
    default_presence: str,
    startup_actions: tuple[str, ...] = (),
    activation_rules: tuple[str, ...] = (),
    delivery_policy: str = "",
    continuity_policy: str = "",
    transport_preferences: tuple[str, ...] = (),
    execution_policy: str = "",
    profile_id: str | None = None,
) -> RuntimeProfile:
    """Construct a new RuntimeProfile with deterministic ID."""
    pid = profile_id or compute_runtime_profile_id(name)
    return RuntimeProfile(
        profile_id=pid,
        name=name,
        default_mode=default_mode,
        default_presence=default_presence,
        startup_actions=startup_actions,
        activation_rules=activation_rules,
        delivery_policy=delivery_policy,
        continuity_policy=continuity_policy,
        transport_preferences=transport_preferences,
        execution_policy=execution_policy,
    )


# ---------------------------------------------------------------------------
# Serialization aliases
# ---------------------------------------------------------------------------

profile_to_dict = RuntimeProfile.to_dict
profile_from_dict = RuntimeProfile.from_dict


# ---------------------------------------------------------------------------
# Mutation builders — SET / REMOVE only
# ---------------------------------------------------------------------------


def build_runtime_profile_mutations(
    profile: RuntimeProfile,
) -> list[dict[str, Any]]:
    """Build mutations to persist a runtime profile.

    Writes:
        1. Profile record: runtime_profile.{profile_id}
        2. Profile index: runtime_profile_index.{profile_id}
    """
    return [
        {
            "op": "SET",
            "key": _profile_key(profile.profile_id),
            "value": profile.to_dict(),
        },
        {
            "op": "SET",
            "key": _profile_index_key(profile.profile_id),
            "value": {
                "name": profile.name,
                "default_mode": profile.default_mode,
                "default_presence": profile.default_presence,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
            },
        },
    ]


# ---------------------------------------------------------------------------
# Load / list helpers
# ---------------------------------------------------------------------------


def load_runtime_profile(
    state: dict[str, Any],
    profile_id: str,
) -> RuntimeProfile | None:
    """Reconstruct a RuntimeProfile from state, or None if missing."""
    raw = state.get(_profile_key(profile_id))
    if not isinstance(raw, dict):
        return None
    return RuntimeProfile.from_dict(raw)


def list_runtime_profiles(
    state: dict[str, Any],
) -> tuple[str, ...]:
    """Return sorted tuple of all runtime profile IDs from state.

    Scans keys matching ``runtime_profile_index.{id}``.
    """
    ids = sorted(
        k[len(_PROFILE_INDEX_PREFIX) :]
        for k in state
        if k.startswith(_PROFILE_INDEX_PREFIX)
    )
    return tuple(ids)
