"""Control Plane Router v1.

Deterministic, stateless router that:
  1. Validates incoming WorkPackets
  2. Resolves capability requirements
  3. Selects the correct adapter via the AdapterRegistry
  4. Delegates execution to the worker runtime daemon
  5. Wraps the RuntimeProof into a normalized RouterResult

The router does NOT execute actions, call LLMs, mutate memory,
plan, or make autonomous decisions. It routes.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.runtime.adapter_registry_contracts import AdapterDescriptor, AdapterRegistry
from core.runtime.worker_runtime_contracts import ProofStatus

from .router_contracts import (
    ALLOWED_ACTION_TYPES,
    CapabilityRequirement,
    CapabilityType,
    RouterDecision,
    RouterResult,
    RouterStatus,
    RuntimeProofReference,
    WorkPacket,
)


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [control-plane] {msg}", flush=True)


def _log_error(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [control-plane] ERROR: {msg}", flush=True)


ACTION_CAPABILITY_MAP: dict[str, CapabilityRequirement] = {
    "ping": CapabilityRequirement(
        action_type="ping",
        capability_type=CapabilityType.SHELL_EXECUTION,
        requires_gui=False,
        requires_local_shell=False,
        authority_required="local_shell",
    ),
    "open_application_url": CapabilityRequirement(
        action_type="open_application_url",
        capability_type=CapabilityType.WINDOWS_GUI_EXECUTION,
        requires_gui=True,
        requires_local_shell=False,
        authority_required="local_gui",
    ),
    "chrome_open_google_drive": CapabilityRequirement(
        action_type="chrome_open_google_drive",
        capability_type=CapabilityType.WINDOWS_GUI_EXECUTION,
        requires_gui=True,
        requires_local_shell=False,
        authority_required="local_gui",
    ),
    "drive_open_safe_test_doc": CapabilityRequirement(
        action_type="drive_open_safe_test_doc",
        capability_type=CapabilityType.WINDOWS_GUI_EXECUTION,
        requires_gui=True,
        requires_local_shell=False,
        authority_required="local_gui",
    ),
    "doc_extract_safe_test_doc": CapabilityRequirement(
        action_type="doc_extract_safe_test_doc",
        capability_type=CapabilityType.DOCUMENT_EXTRACTION,
        requires_gui=True,
        requires_local_shell=False,
        authority_required="local_gui",
    ),
    "doc_ingestion_candidate_safe_test_doc": CapabilityRequirement(
        action_type="doc_ingestion_candidate_safe_test_doc",
        capability_type=CapabilityType.INGESTION_CANDIDACY,
        requires_gui=False,
        requires_local_shell=False,
        authority_required="local_shell",
    ),
    "promote_safe_memory_candidate": CapabilityRequirement(
        action_type="promote_safe_memory_candidate",
        capability_type=CapabilityType.MEMORY_PROMOTION,
        requires_gui=False,
        requires_local_shell=False,
        authority_required="local_shell",
    ),
    "query_safe_memory_reference": CapabilityRequirement(
        action_type="query_safe_memory_reference",
        capability_type=CapabilityType.CANONICAL_MEMORY_QUERY,
        requires_gui=False,
        requires_local_shell=False,
        authority_required="local_shell",
    ),
    "ingest_safe_doc": CapabilityRequirement(
        action_type="ingest_safe_doc",
        capability_type=CapabilityType.DOCUMENT_EXTRACTION,
        requires_gui=True,
        requires_local_shell=False,
        authority_required="local_gui",
    ),
    "ingest_safe_doc_cu": CapabilityRequirement(
        action_type="ingest_safe_doc_cu",
        capability_type=CapabilityType.DOCUMENT_EXTRACTION,
        requires_gui=True,
        requires_local_shell=False,
        authority_required="local_gui",
    ),
    "chrome_proof": CapabilityRequirement(
        action_type="chrome_proof",
        capability_type=CapabilityType.WINDOWS_GUI_EXECUTION,
        requires_gui=True,
        requires_local_shell=False,
        authority_required="local_gui",
    ),
    "actuator_proof": CapabilityRequirement(
        action_type="actuator_proof",
        capability_type=CapabilityType.WINDOWS_GUI_EXECUTION,
        requires_gui=True,
        requires_local_shell=False,
        authority_required="local_gui",
    ),
    "relay_status": CapabilityRequirement(
        action_type="relay_status",
        capability_type=CapabilityType.SHELL_EXECUTION,
        requires_gui=False,
        requires_local_shell=False,
        authority_required="local_shell",
    ),
}


DEFAULT_CONFIG_PATH = "/opt/OS/config/control_plane_router_v1.json"


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    with open(config_path, encoding="utf-8-sig") as f:
        return json.load(f)


class ControlPlaneRouterV1:
    """Stateless, deterministic control plane router."""

    def __init__(
        self,
        registry: AdapterRegistry,
        config: dict[str, Any] | None = None,
        base_dir: Path = Path("/opt/OS"),
    ) -> None:
        self.registry = registry
        self.config = config or {}
        self.base_dir = base_dir

        self.default_runtime: str = self.config.get(
            "default_runtime_target", "local_worker_runtime_daemon"
        )
        self.default_timeout: int = self.config.get("default_timeout_seconds", 60)
        self.allowed_actions: set[str] = set(
            self.config.get("allowed_action_types", sorted(ALLOWED_ACTION_TYPES))
        )
        self.proof_required: bool = self.config.get("proof_required", True)

        self.work_inbox = base_dir / self.config.get(
            "work_inbox", "data/runtime/local_worker_runtime/inbox"
        )
        self.proof_dir = base_dir / self.config.get("proof_dir", "data/runtime/runtime_proofs")

    def validate_packet(self, packet: WorkPacket) -> str | None:
        """Return an error message if the packet is invalid, else None."""
        if not packet.packet_id:
            return "missing packet_id"
        if not packet.action_type:
            return "missing action_type"
        if packet.action_type not in self.allowed_actions:
            return f"action_type '{packet.action_type}' not allowed"
        return None

    def resolve_capability(self, action_type: str) -> CapabilityRequirement | None:
        """Resolve the capability requirement for an action type."""
        return ACTION_CAPABILITY_MAP.get(action_type)

    def resolve_adapter(self, action_type: str) -> AdapterDescriptor | None:
        """Find the adapter that can handle this action type."""
        return self.registry.find_adapter_for_action(action_type)

    def resolve_runtime(self, packet: WorkPacket) -> str:
        """Determine which runtime target should execute this packet."""
        if packet.requested_runtime:
            return packet.requested_runtime
        return self.default_runtime

    def build_router_result(
        self,
        status: RouterStatus,
        decision: RouterDecision | None = None,
        proof_ref: RuntimeProofReference | None = None,
        error_message: str = "",
        started_at: str = "",
    ) -> RouterResult:
        """Construct a normalized RouterResult."""
        completed_at = datetime.now(timezone.utc).isoformat()
        return RouterResult(
            router_status=status,
            router_decision=decision,
            runtime_target=decision.runtime_target if decision else "",
            adapter_selected=decision.adapter_selected if decision else "",
            runtime_proof_reference=proof_ref,
            execution_trace_id=decision.packet_id if decision else "",
            normalized_status=status.value,
            error_message=error_message,
            started_at=started_at or completed_at,
            completed_at=completed_at,
        )

    def route_work_packet(self, packet: WorkPacket) -> RouterResult:
        """Route a WorkPacket through the control plane.

        Validates, resolves capability and adapter, writes packet
        to the daemon inbox, polls for proof, returns RouterResult.
        """
        started_at = datetime.now(timezone.utc).isoformat()
        trace_id = packet.trace_id or f"CPR-{uuid.uuid4().hex[:12]}"
        _log(f"routing: packet_id={packet.packet_id} action={packet.action_type} trace={trace_id}")

        validation_error = self.validate_packet(packet)
        if validation_error:
            _log_error(f"invalid packet: {validation_error}")
            return self.build_router_result(
                RouterStatus.INVALID_PACKET,
                error_message=validation_error,
                started_at=started_at,
            )

        capability = self.resolve_capability(packet.action_type)
        if capability is None:
            _log_error(f"no capability mapping for: {packet.action_type}")
            return self.build_router_result(
                RouterStatus.REJECTED,
                error_message=f"no capability mapping for '{packet.action_type}'",
                started_at=started_at,
            )

        adapter = self.resolve_adapter(packet.action_type)
        if adapter is None:
            _log_error(f"no adapter for: {packet.action_type}")
            return self.build_router_result(
                RouterStatus.NO_ADAPTER,
                error_message=f"no adapter registered for '{packet.action_type}'",
                started_at=started_at,
            )

        runtime_target = self.resolve_runtime(packet)

        decision = RouterDecision(
            packet_id=packet.packet_id,
            action_type=packet.action_type,
            runtime_target=runtime_target,
            adapter_selected=adapter.adapter_id,
            capability_matched=capability.capability_type.value,
            authority_satisfied=True,
        )
        _log(
            f"decision: runtime={runtime_target} adapter={adapter.adapter_id} "
            f"capability={capability.capability_type.value}"
        )

        daemon_packet = {**packet.payload}
        daemon_packet["request_id"] = packet.packet_id
        daemon_packet["action_type"] = packet.action_type
        daemon_packet["trace_id"] = trace_id

        packet_path = self._write_to_inbox(daemon_packet)
        if packet_path is None:
            _log_error("failed to write packet to inbox")
            return self.build_router_result(
                RouterStatus.FAILED,
                decision=decision,
                error_message="failed to write packet to daemon inbox",
                started_at=started_at,
            )

        timeout = packet.timeout_seconds or self.default_timeout
        proof_data = self._poll_for_proof(packet.packet_id, timeout)

        if proof_data is None:
            _log(f"timeout waiting for proof: {packet.packet_id}")
            return self.build_router_result(
                RouterStatus.TIMEOUT,
                decision=decision,
                error_message="proof timeout",
                started_at=started_at,
            )

        proof_ref = RuntimeProofReference(
            proof_id=proof_data.get("proof_id", ""),
            proof_status=proof_data.get("proof_status", ""),
            adapter_status=proof_data.get("adapter_status", ""),
            request_id=proof_data.get("request_id", ""),
            trace_id=proof_data.get("trace_id", ""),
        )

        proof_status_str = proof_data.get("proof_status", "")
        if proof_status_str == ProofStatus.COMPLETED.value:
            router_status = RouterStatus.COMPLETED
        elif proof_status_str == ProofStatus.TIMEOUT.value:
            router_status = RouterStatus.TIMEOUT
        else:
            router_status = RouterStatus.FAILED

        _log(f"result: router_status={router_status.value} proof_status={proof_status_str}")

        return self.build_router_result(
            router_status,
            decision=decision,
            proof_ref=proof_ref,
            started_at=started_at,
        )

    def _write_to_inbox(self, packet: dict[str, Any]) -> Path | None:
        """Write a daemon work packet to the inbox directory."""
        try:
            self.work_inbox.mkdir(parents=True, exist_ok=True)
            request_id = packet.get("request_id", f"unknown-{uuid.uuid4().hex[:8]}")
            filename = f"{request_id}.json"
            path = self.work_inbox / filename
            with open(path, "w") as f:
                json.dump(packet, f, indent=2)
            _log(f"packet written: {path.name}")
            return path
        except OSError as e:
            _log_error(f"inbox write failed: {e}")
            return None

    def _poll_for_proof(
        self,
        request_id: str,
        timeout_seconds: int,
        poll_interval: float = 2.0,
    ) -> dict[str, Any] | None:
        """Poll the proof directory for a matching proof."""
        deadline = time.time() + timeout_seconds
        _log(f"polling proof: request_id={request_id} timeout={timeout_seconds}s")

        while time.time() < deadline:
            for proof_file in self.proof_dir.glob("PROOF-*.json"):
                try:
                    with open(proof_file, encoding="utf-8-sig") as f:
                        data = json.load(f)
                    if data.get("request_id") == request_id:
                        _log(f"proof found: {proof_file.name}")
                        return data
                except (json.JSONDecodeError, OSError):
                    continue
            time.sleep(poll_interval)

        return None

    def route_dry_run(self, packet: WorkPacket) -> RouterResult:
        """Route without writing to inbox or polling for proof.

        Returns the routing decision only — useful for testing
        and validation without side effects.
        """
        started_at = datetime.now(timezone.utc).isoformat()

        validation_error = self.validate_packet(packet)
        if validation_error:
            return self.build_router_result(
                RouterStatus.INVALID_PACKET,
                error_message=validation_error,
                started_at=started_at,
            )

        capability = self.resolve_capability(packet.action_type)
        if capability is None:
            return self.build_router_result(
                RouterStatus.REJECTED,
                error_message=f"no capability mapping for '{packet.action_type}'",
                started_at=started_at,
            )

        adapter = self.resolve_adapter(packet.action_type)
        if adapter is None:
            return self.build_router_result(
                RouterStatus.NO_ADAPTER,
                error_message=f"no adapter registered for '{packet.action_type}'",
                started_at=started_at,
            )

        runtime_target = self.resolve_runtime(packet)

        decision = RouterDecision(
            packet_id=packet.packet_id,
            action_type=packet.action_type,
            runtime_target=runtime_target,
            adapter_selected=adapter.adapter_id,
            capability_matched=capability.capability_type.value,
            authority_satisfied=True,
        )

        return self.build_router_result(
            RouterStatus.ROUTED,
            decision=decision,
            started_at=started_at,
        )
