"""Windows Interactive Desktop Adapter Contracts.

Typed contracts for GUI action requests routed through the Windows
Interactive Desktop Adapter. The adapter runs in the logged-in
Windows user session and has real desktop access — WSL/tmux does not.

Supported v1 actions:
  - PING                                 — relay health check
  - OPEN_APPLICATION_URL                 — launch Chrome with URL
  - FOCUS_APPLICATION                    — bring app to foreground
  - REQUEST_FOUNDER_VISUAL_CONFIRMATION  — ask founder to confirm

The adapter communicates via file-based inbox/outbox protocol.
JSON request files are written to the relay inbox, and result
files appear in the relay outbox.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class WindowsDesktopActionType(str, Enum):
    PING = "ping"
    OPEN_APPLICATION_URL = "open_application_url"
    FOCUS_APPLICATION = "focus_application"
    CHROME_PROOF = "chrome_proof"
    INGEST_SAFE_DOC_CU = "ingest_safe_doc_cu"
    EXPLORE_ENVIRONMENT = "explore_environment"
    ADAPTER_REPORT = "adapter_report"
    CAPABILITY_REPORT = "capability_report"
    ORCHESTRATION_REPORT = "orchestration_report"
    CONTINUITY_REPORT = "continuity_report"
    GOVERNANCE_INTELLIGENCE_REPORT = "governance_intelligence_report"
    CONSTITUTION_REPORT = "constitution_report"
    FEDERATION_REPORT = "federation_report"
    ECONOMICS_REPORT = "economics_report"
    STRATEGY_REPORT = "strategy_report"
    EPISTEMIC_REPORT = "epistemic_report"
    IDENTITY_REPORT = "identity_report"
    REQUEST_FOUNDER_VISUAL_CONFIRMATION = "request_founder_visual_confirmation"


class WindowsDesktopAdapterStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    PONG = "pong"
    PENDING_FOUNDER_VISUAL_CONFIRMATION = "pending_founder_visual_confirmation"


class WindowsDesktopProofStatus(str, Enum):
    NO_PROOF = "no_proof"
    PROCESS_DETECTED = "process_detected"
    WINDOW_METADATA_DETECTED = "window_metadata_detected"
    PENDING_FOUNDER_VISUAL_CONFIRMATION = "pending_founder_visual_confirmation"
    FOUNDER_CONFIRMED_VISIBLE = "founder_confirmed_visible"
    FOUNDER_DENIED_VISIBLE = "founder_denied_visible"


BLOCKED_LAUNCH_METHODS = frozenset(
    {
        "explorer_url",
        "default_browser",
        "shell_url_open",
        "generic_start_url",
        "unknown_browser",
    }
)


@dataclass
class WindowsDesktopActionRequest:
    request_id: str = ""
    trace_id: str = ""
    work_order_id: str = ""
    action_type: str = ""
    environment_id: str = ""
    execution_surface_id: str = ""
    application_id: str = ""
    executable_path: str = ""
    launch_method: str = ""
    url: str = ""
    blocked_launch_methods: list[str] = field(default_factory=list)
    proof_required: str = ""
    no_secret_capture: bool = True
    no_mutation: bool = True
    timestamp: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "work_order_id": self.work_order_id,
            "action_type": self.action_type,
            "environment_id": self.environment_id,
            "execution_surface_id": self.execution_surface_id,
            "application_id": self.application_id,
            "executable_path": self.executable_path,
            "launch_method": self.launch_method,
            "url": self.url,
            "blocked_launch_methods": self.blocked_launch_methods,
            "proof_required": self.proof_required,
            "no_secret_capture": self.no_secret_capture,
            "no_mutation": self.no_mutation,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class WindowsDesktopActionResult:
    request_id: str = ""
    trace_id: str = ""
    work_order_id: str = ""
    action_type: str = ""
    adapter_status: str = ""
    command_issued: str = ""
    process_detected: bool = False
    process_id: int = 0
    window_metadata: dict[str, Any] = field(default_factory=dict)
    visible_proof_status: str = WindowsDesktopProofStatus.NO_PROOF.value
    founder_visual_confirmation_required: bool = True
    error: str = ""
    timestamp: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "work_order_id": self.work_order_id,
            "action_type": self.action_type,
            "adapter_status": self.adapter_status,
            "command_issued": self.command_issued,
            "process_detected": self.process_detected,
            "process_id": self.process_id,
            "window_metadata": self.window_metadata,
            "visible_proof_status": self.visible_proof_status,
            "founder_visual_confirmation_required": self.founder_visual_confirmation_required,
            "error": self.error,
            "timestamp": self.timestamp,
            "notes": self.notes,
        }


@dataclass
class WindowsDesktopProofArtifact:
    trace_id: str = ""
    work_order_id: str = ""
    proof_status: str = WindowsDesktopProofStatus.NO_PROOF.value
    process_detected: bool = False
    window_metadata: dict[str, Any] = field(default_factory=dict)
    founder_visual_confirmation_required: bool = True
    founder_visual_confirmation_received: bool = False
    founder_confirmed: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "work_order_id": self.work_order_id,
            "proof_status": self.proof_status,
            "process_detected": self.process_detected,
            "window_metadata": self.window_metadata,
            "founder_visual_confirmation_required": self.founder_visual_confirmation_required,
            "founder_visual_confirmation_received": self.founder_visual_confirmation_received,
            "founder_confirmed": self.founder_confirmed,
            "notes": self.notes,
        }


@dataclass
class WindowsDesktopRelayPaths:
    relay_inbox: Path = field(default_factory=lambda: Path.home() / "eos_relay" / "inbox")
    relay_outbox: Path = field(default_factory=lambda: Path.home() / "eos_relay" / "outbox")

    def ensure_dirs(self) -> None:
        self.relay_inbox.mkdir(parents=True, exist_ok=True)
        self.relay_outbox.mkdir(parents=True, exist_ok=True)

    def to_dict(self) -> dict[str, str]:
        return {
            "relay_inbox": str(self.relay_inbox),
            "relay_outbox": str(self.relay_outbox),
        }
