"""
umh.substrate.workstation_profile_contract — Adapter-facing contract
for external workstation boot/restore logic.

This module defines the declarative contract that external workstation
runtime adapters consume. It does NOT launch anything, open any apps,
set up audio devices, or interact with OS processes.

Wake phrase, clap detection, remote commands are represented as
trigger_type identifiers — not implemented here.

All state transitions expressed as SET-only mutations for replay safety.

Public API:
    WorkstationProfileBinding       — frozen binding record
    WorkstationActivationRequest    — frozen activation request
    WorkstationRuntimeAdapter       — Protocol for external adapters
    compute_workstation_binding_id  — deterministic binding ID
    compute_workstation_activation_id — deterministic activation ID
    build_workstation_profile_binding — construct a binding
    build_workstation_activation_request — construct an activation request
    binding_to_mutations            — persistence mutations for binding
    load_workstation_profile_binding — reconstruct from state

Separation note:
    This module is harness-only. External adapters implement
    WorkstationRuntimeAdapter to execute the actual boot/restore/suspend
    logic on the target machine.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

_LOG_PREFIX = "[substrate.workstation_profile_contract]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Trigger type constants
# ---------------------------------------------------------------------------
TRIGGER_MANUAL = "manual"
TRIGGER_WAKE_PHRASE = "wake_phrase"
TRIGGER_CLAP = "clap"
TRIGGER_REMOTE_COMMAND = "remote_command"

_VALID_TRIGGERS = frozenset(
    {
        TRIGGER_MANUAL,
        TRIGGER_WAKE_PHRASE,
        TRIGGER_CLAP,
        TRIGGER_REMOTE_COMMAND,
    }
)


# ---------------------------------------------------------------------------
# State key helpers
# ---------------------------------------------------------------------------
_BINDING_KEY_PREFIX = "workstation_profile_binding."
_ACTIVATION_KEY_PREFIX = "workstation_activation_request."


def _binding_key(binding_id: str) -> str:
    return f"{_BINDING_KEY_PREFIX}{binding_id}"


def _activation_key(activation_id: str) -> str:
    return f"{_ACTIVATION_KEY_PREFIX}{activation_id}"


# ---------------------------------------------------------------------------
# WorkstationProfileBinding — frozen binding record
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WorkstationProfileBinding:
    """Declares how a runtime profile binds to a workstation session.

    Fields:
        binding_id:         deterministic binding identifier
        runtime_session_id: owning session
        profile_id:         runtime profile being bound
        transport:          transport identifier for this binding
        startup_actions:    symbolic action identifiers (from profile)
        continuity_policy:  continuity behavior tag
        execution_policy:   execution behavior tag
        created_at:         ISO timestamp
        correlation_id:     links to upstream event chain
    """

    binding_id: str
    runtime_session_id: str
    profile_id: str
    transport: str
    startup_actions: tuple[str, ...]
    continuity_policy: str
    execution_policy: str
    created_at: str
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(self, "created_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "binding_id": self.binding_id,
            "continuity_policy": self.continuity_policy,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "execution_policy": self.execution_policy,
            "profile_id": self.profile_id,
            "runtime_session_id": self.runtime_session_id,
            "startup_actions": list(self.startup_actions),
            "transport": self.transport,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> WorkstationProfileBinding:
        """Reconstruct from plain dict."""
        return WorkstationProfileBinding(
            binding_id=str(d.get("binding_id", "")),
            runtime_session_id=str(d.get("runtime_session_id", "")),
            profile_id=str(d.get("profile_id", "")),
            transport=str(d.get("transport", "")),
            startup_actions=tuple(d.get("startup_actions", ())),
            continuity_policy=str(d.get("continuity_policy", "")),
            execution_policy=str(d.get("execution_policy", "")),
            created_at=str(d.get("created_at", "")),
            correlation_id=str(d.get("correlation_id", "")),
        )


# ---------------------------------------------------------------------------
# WorkstationActivationRequest — frozen activation request
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WorkstationActivationRequest:
    """Request to activate/boot a workstation profile binding.

    Fields:
        activation_id:      deterministic activation identifier
        runtime_session_id: owning session
        binding_id:         which binding to activate
        requested_at:       ISO timestamp
        trigger_type:       manual | wake_phrase | clap | remote_command
        entry_transport:    transport through which activation was triggered
        correlation_id:     links to upstream event chain
    """

    activation_id: str
    runtime_session_id: str
    binding_id: str
    requested_at: str
    trigger_type: str
    entry_transport: str
    correlation_id: str = ""

    def __post_init__(self) -> None:
        if not self.requested_at:
            object.__setattr__(self, "requested_at", _utcnow())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict — deterministic key order."""
        return {
            "activation_id": self.activation_id,
            "binding_id": self.binding_id,
            "correlation_id": self.correlation_id,
            "entry_transport": self.entry_transport,
            "requested_at": self.requested_at,
            "runtime_session_id": self.runtime_session_id,
            "trigger_type": self.trigger_type,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> WorkstationActivationRequest:
        """Reconstruct from plain dict."""
        return WorkstationActivationRequest(
            activation_id=str(d.get("activation_id", "")),
            runtime_session_id=str(d.get("runtime_session_id", "")),
            binding_id=str(d.get("binding_id", "")),
            requested_at=str(d.get("requested_at", "")),
            trigger_type=str(d.get("trigger_type", "")),
            entry_transport=str(d.get("entry_transport", "")),
            correlation_id=str(d.get("correlation_id", "")),
        )


# ---------------------------------------------------------------------------
# Protocol — adapter seam for external workstation runtimes
# ---------------------------------------------------------------------------


class WorkstationRuntimeAdapter(Protocol):
    """Protocol that external workstation adapters must implement.

    The harness never calls these directly — they exist for type
    checking and documentation. An adapter implementing this protocol
    lives OUTSIDE the substrate.
    """

    def activate_profile(
        self,
        request: WorkstationActivationRequest,
    ) -> Any:
        """Boot the workstation according to the activation request."""
        ...

    def suspend_profile(
        self,
        runtime_session_id: str,
        at: str,
    ) -> Any:
        """Suspend the active workstation profile for a session."""
        ...

    def restore_profile(
        self,
        runtime_session_id: str,
        at: str,
    ) -> Any:
        """Restore a previously suspended workstation profile."""
        ...


# ---------------------------------------------------------------------------
# Deterministic IDs
# ---------------------------------------------------------------------------


def compute_workstation_binding_id(
    runtime_session_id: str,
    profile_id: str,
    transport: str,
) -> str:
    """Deterministic binding ID: same session + profile + transport -> same ID."""
    canonical = json.dumps(
        {
            "profile_id": profile_id,
            "runtime_session_id": runtime_session_id,
            "transport": transport,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"wpb_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


def compute_workstation_activation_id(
    runtime_session_id: str,
    binding_id: str,
    requested_at: str,
) -> str:
    """Deterministic activation ID: same session + binding + time -> same ID."""
    canonical = json.dumps(
        {
            "binding_id": binding_id,
            "requested_at": requested_at,
            "runtime_session_id": runtime_session_id,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"wpa_{hashlib.sha256(canonical.encode()).hexdigest()[:12]}"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def build_workstation_profile_binding(
    *,
    runtime_session_id: str,
    profile_id: str,
    transport: str,
    startup_actions: tuple[str, ...] = (),
    continuity_policy: str = "",
    execution_policy: str = "",
    correlation_id: str = "",
    binding_id: str | None = None,
) -> WorkstationProfileBinding:
    """Construct a WorkstationProfileBinding with deterministic ID."""
    bid = binding_id or compute_workstation_binding_id(
        runtime_session_id,
        profile_id,
        transport,
    )
    return WorkstationProfileBinding(
        binding_id=bid,
        runtime_session_id=runtime_session_id,
        profile_id=profile_id,
        transport=transport,
        startup_actions=startup_actions,
        continuity_policy=continuity_policy,
        execution_policy=execution_policy,
        created_at=_utcnow(),
        correlation_id=correlation_id,
    )


def build_workstation_activation_request(
    *,
    runtime_session_id: str,
    binding_id: str,
    trigger_type: str,
    entry_transport: str,
    correlation_id: str = "",
    requested_at: str = "",
    activation_id: str | None = None,
) -> WorkstationActivationRequest:
    """Construct a WorkstationActivationRequest with deterministic ID."""
    ts = requested_at or _utcnow()
    aid = activation_id or compute_workstation_activation_id(
        runtime_session_id,
        binding_id,
        ts,
    )
    return WorkstationActivationRequest(
        activation_id=aid,
        runtime_session_id=runtime_session_id,
        binding_id=binding_id,
        requested_at=ts,
        trigger_type=trigger_type,
        entry_transport=entry_transport,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Mutation builders — SET only
# ---------------------------------------------------------------------------


def binding_to_mutations(
    binding: WorkstationProfileBinding,
) -> list[dict[str, Any]]:
    """Build mutations to persist a workstation profile binding.

    Writes:
        1. Binding record: workstation_profile_binding.{binding_id}
    """
    return [
        {
            "op": "SET",
            "key": _binding_key(binding.binding_id),
            "value": binding.to_dict(),
        },
    ]


# ---------------------------------------------------------------------------
# Load helper
# ---------------------------------------------------------------------------


def load_workstation_profile_binding(
    state: dict[str, Any],
    binding_id: str,
) -> WorkstationProfileBinding | None:
    """Reconstruct a WorkstationProfileBinding from state, or None if missing."""
    raw = state.get(_binding_key(binding_id))
    if not isinstance(raw, dict):
        return None
    return WorkstationProfileBinding.from_dict(raw)
