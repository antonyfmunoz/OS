"""
umh.substrate.profile_resolution — Determine which RuntimeProfile is
active for a runtime session.

Pure resolution logic. No side effects, no adapter imports, no UI.
All state transitions expressed as SET-only mutations for replay safety.

Resolution priority:
    1. Explicit requested_profile_id → load it
    2. Existing binding in state → use binding.profile_id
    3. Exactly one profile exists → use it (singleton default)
    4. Otherwise → None (explicit selection required)

Public API:
    ActiveProfile                    — frozen record of resolved profile binding
    compute_active_profile_id        — deterministic binding ID
    resolve_active_profile           — resolve which profile to activate
    build_active_profile_mutations   — persistence mutations
    load_active_profile              — reconstruct from state

State keys:
    runtime_active_profile.{runtime_session_id}  — current binding
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from umh.substrate.runtime_profile import (
    RuntimeProfile,
    list_runtime_profiles,
    load_runtime_profile,
)

_LOG_PREFIX = "[substrate.profile_resolution]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_ACTIVE_PROFILE_KEY_PREFIX = "runtime_active_profile."


def _active_profile_key(runtime_session_id: str) -> str:
    return f"{_ACTIVE_PROFILE_KEY_PREFIX}{runtime_session_id}"


# ---------------------------------------------------------------------------
# ActiveProfile — frozen binding record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ActiveProfile:
    """Immutable record binding a runtime session to a resolved profile.

    Fields:
        binding_id:          deterministic binding identifier
        runtime_session_id:  owning session
        profile_id:          resolved profile identifier
        resolved_at:         ISO timestamp of resolution
        source:              how the profile was resolved
                             (explicit | binding | singleton)
    """

    binding_id: str
    runtime_session_id: str
    profile_id: str
    resolved_at: str
    source: str

    def __post_init__(self) -> None:
        if not self.resolved_at:
            object.__setattr__(self, "resolved_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "binding_id": self.binding_id,
            "profile_id": self.profile_id,
            "resolved_at": self.resolved_at,
            "runtime_session_id": self.runtime_session_id,
            "source": self.source,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ActiveProfile:
        """Reconstruct from plain dict."""
        return ActiveProfile(
            binding_id=str(d.get("binding_id", "")),
            runtime_session_id=str(d.get("runtime_session_id", "")),
            profile_id=str(d.get("profile_id", "")),
            resolved_at=str(d.get("resolved_at", "")),
            source=str(d.get("source", "")),
        )


# ---------------------------------------------------------------------------
# Deterministic ID
# ---------------------------------------------------------------------------


def compute_active_profile_id(
    runtime_session_id: str,
    resolved_at: str,
) -> str:
    """Deterministic binding ID: same inputs -> same ID."""
    canonical = json.dumps(
        {
            "resolved_at": resolved_at,
            "runtime_session_id": runtime_session_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"apb_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Resolution logic
# ---------------------------------------------------------------------------


def resolve_active_profile(
    state: dict[str, Any],
    runtime_session_id: str,
    requested_profile_id: str = "",
    resolved_at: str = "",
) -> tuple[RuntimeProfile | None, ActiveProfile | None]:
    """Resolve which RuntimeProfile is active for a runtime session.

    Returns (profile, active_profile_binding) or (None, None) when
    resolution fails (no profiles, ambiguous selection).

    Resolution priority:
        1. Explicit requested_profile_id → load it
        2. Existing binding in state → use binding.profile_id
        3. Exactly one profile in state → use it (singleton)
        4. Otherwise → (None, None)
    """
    ts = resolved_at or _utcnow()

    # Path 1: explicit request
    if requested_profile_id:
        profile = load_runtime_profile(state, requested_profile_id)
        if profile is not None:
            binding = ActiveProfile(
                binding_id=compute_active_profile_id(runtime_session_id, ts),
                runtime_session_id=runtime_session_id,
                profile_id=requested_profile_id,
                resolved_at=ts,
                source="explicit",
            )
            return profile, binding
        _log(f"requested profile {requested_profile_id} not found in state")
        return None, None

    # Path 2: existing binding
    existing = load_active_profile(state, runtime_session_id)
    if existing is not None:
        profile = load_runtime_profile(state, existing.profile_id)
        if profile is not None:
            # Re-bind with fresh timestamp
            binding = ActiveProfile(
                binding_id=compute_active_profile_id(runtime_session_id, ts),
                runtime_session_id=runtime_session_id,
                profile_id=existing.profile_id,
                resolved_at=ts,
                source="binding",
            )
            return profile, binding

    # Path 3: singleton — exactly one profile exists
    all_ids = list_runtime_profiles(state)
    if len(all_ids) == 1:
        profile = load_runtime_profile(state, all_ids[0])
        if profile is not None:
            binding = ActiveProfile(
                binding_id=compute_active_profile_id(runtime_session_id, ts),
                runtime_session_id=runtime_session_id,
                profile_id=all_ids[0],
                resolved_at=ts,
                source="singleton",
            )
            return profile, binding

    # Path 4: cannot resolve
    return None, None


# ---------------------------------------------------------------------------
# Mutation builders — SET only
# ---------------------------------------------------------------------------


def build_active_profile_mutations(
    active_profile: ActiveProfile,
) -> list[dict[str, Any]]:
    """Build mutations to persist the active profile binding.

    Writes single key: runtime_active_profile.{runtime_session_id}
    This is a SET-only overwrite — one binding per session.
    """
    return [
        {
            "op": "SET",
            "key": _active_profile_key(active_profile.runtime_session_id),
            "value": active_profile.to_dict(),
        },
    ]


# ---------------------------------------------------------------------------
# Load helper
# ---------------------------------------------------------------------------


def load_active_profile(
    state: dict[str, Any],
    runtime_session_id: str,
) -> ActiveProfile | None:
    """Reconstruct current ActiveProfile from state, or None if missing."""
    raw = state.get(_active_profile_key(runtime_session_id))
    if not isinstance(raw, dict):
        return None
    return ActiveProfile.from_dict(raw)
