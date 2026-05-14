"""Discord Spine Integration v1.

Wires Discord commands through the full governed execution spine:
  Discord command → WorkPacket → Authority → Gate → Dispatch
  → Supervisor → Worker → Proof → Ledger → Reply

This module composes existing infrastructure from Phase 96.8AE
(LiveLocalRuntimeExecution) with the Discord interface adapter.
No new abstractions — pure composition.

UMH substrate subsystem. Phase 96.8AF.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from governance.policy.execution_authority_engine_v1 import (
    CapabilityAuthority,
    EnvironmentAuthority,
    ExecutionAuthorityEngine,
    RiskClass,
)
from core.execution.workpacket_execution_gate_v1 import (
    WorkPacketExecutionGate,
)
from core.runtime.live_local_runtime_execution_v1 import (
    ExecutionSpineOutcome,
    ExecutionSpineResult,
    LiveLocalRuntimeExecution,
)
from core.runtime.node_sync_gate_v1 import (
    NodeSyncGate,
    SyncPolicy,
)
from core.runtime.local_runtime_supervisor_v1 import (
    LocalRuntimeSupervisor,
)
from core.runtime.runtime_dispatch_queue_v1 import (
    RuntimeDispatchQueue,
)
from core.runtime.runtime_recovery_v1 import (
    RuntimeRecoveryEngine,
)
from core.runtime.runtime_session_registry_v1 import (
    RuntimeSessionRegistry,
)
from state.transformation_state_ledger import (

    TransformationStateLedger,
    make_trace_id,
)

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [discord-spine] {msg}", flush=True)


@dataclass
class SpineExecutionConfig:
    """Configuration for spine-routed execution."""

    queue_dir: Path = Path("data/runtime/spine_dispatch_queue")
    ledger_dir: Path = Path("data/runtime/transformation_ledger/spine")
    proof_dir: Path = Path("data/runtime/spine_proofs")
    gate_proof_dir: Path = Path("data/runtime/spine_gate_proofs")
    worker_id: str = "local-worker-01"
    environment_id: str = "local_windows_desktop"
    max_retries: int = 3
    sync_policy: str = "strict"
    relay_script_path: str = ""
    local_repo_path: str = ""


@dataclass
class SpineRoutedResult:
    """Result of a spine-routed Discord command."""

    command: str
    spine_result: ExecutionSpineResult | None = None
    error_message: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def succeeded(self) -> bool:
        return self.spine_result is not None and self.spine_result.succeeded

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "succeeded": self.succeeded,
            "spine_result": self.spine_result.to_dict() if self.spine_result else None,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }


def build_spine_infrastructure(
    config: SpineExecutionConfig,
    base_dir: Path = Path(_ROOT),
) -> LiveLocalRuntimeExecution:
    """Build the full execution spine from configuration.

    Composes authority engine, gate, queue, supervisor, and ledger
    into a single LiveLocalRuntimeExecution instance.
    """
    queue_dir = base_dir / config.queue_dir
    ledger_dir = base_dir / config.ledger_dir
    proof_dir = base_dir / config.proof_dir
    gate_proof_dir = base_dir / config.gate_proof_dir

    env_auth = EnvironmentAuthority(
        environment_type=config.environment_id,
        can_own_gui=True,
        can_own_local_shell=True,
        can_execute_browser=True,
        max_risk_class=RiskClass.MEDIUM,
    )
    cap_auth = CapabilityAuthority(
        adapter_id="windows_interactive_desktop_relay",
        capabilities=[
            "actuator_proof",
            "browser_execution",
            "chrome_launch",
            "chrome_open_google_drive",
            "chrome_proof",
            "ingest_safe_doc",
            "ingest_safe_doc_cu",
            "open_application_url",
        ],
        is_configured=True,
        is_mature=True,
    )

    authority = ExecutionAuthorityEngine(
        environment_authorities=[env_auth],
        capability_authorities=[cap_auth],
    )

    ledger = TransformationStateLedger(ledger_dir)

    gate = WorkPacketExecutionGate(
        environment_authorities={config.environment_id: env_auth},
        capability_authorities={"windows_interactive_desktop_relay": cap_auth},
        available_runtimes={config.worker_id: True},
        ledger=ledger,
        proof_dir=gate_proof_dir,
    )

    queue = RuntimeDispatchQueue(queue_dir)
    registry = RuntimeSessionRegistry()
    recovery = RuntimeRecoveryEngine(max_retries=config.max_retries)

    supervisor = LocalRuntimeSupervisor(
        queue=queue,
        registry=registry,
        recovery=recovery,
        ledger=ledger,
        proof_dir=proof_dir,
        worker_id=config.worker_id,
        environment_id=config.environment_id,
    )
    supervisor.start()

    policy_map = {
        "strict": SyncPolicy.STRICT,
        "auto_pull": SyncPolicy.AUTO_PULL,
        "warn_only": SyncPolicy.WARN_ONLY,
    }
    sync_policy = policy_map.get(config.sync_policy, SyncPolicy.STRICT)

    from composition.registries.canonical_command_registry_v1 import get_canonical_registry

    _reg = get_canonical_registry()
    sync_gate = NodeSyncGate(
        vps_repo_path=base_dir,
        local_repo_path=Path(config.local_repo_path) if config.local_repo_path else None,
        relay_script_path=Path(config.relay_script_path) if config.relay_script_path else None,
        command_registry=_reg.command_action_map,
        worker_capabilities=list(cap_auth.capabilities),
        config_path=gate_proof_dir / "config_marker.json",
        sync_policy=sync_policy,
        ledger=ledger,
        proof_dir=base_dir / "data/runtime/sync_proofs",
        registry_hash=_reg.registry_hash(),
    )

    return LiveLocalRuntimeExecution(
        authority_engine=authority,
        gate=gate,
        queue=queue,
        supervisor=supervisor,
        ledger=ledger,
        proof_dir=proof_dir,
        sync_gate=sync_gate,
    )


def execute_spine_command(
    spine: LiveLocalRuntimeExecution,
    command: str,
    packet_id: str = "",
    action_type: str = "",
    trace_id: str = "",
) -> SpineRoutedResult:
    """Execute a Discord command through the governed execution spine."""
    if not packet_id:
        packet_id = f"DISCORD-SPINE-{uuid.uuid4().hex[:8]}"
    if not action_type:
        from composition.registries.canonical_command_registry_v1 import get_canonical_registry

        action_type = get_canonical_registry().command_action_map.get(command, "")
    if not action_type:
        return SpineRoutedResult(
            command=command,
            error_message=f"no action_type mapping for command: {command}",
        )
    if not trace_id:
        trace_id = make_trace_id("DISCORD-SPINE")

    _log(f"executing: command={command} packet={packet_id} action={action_type}")

    spine_result = spine.execute(
        packet_id=packet_id,
        action_type=action_type,
        action_description=f"Discord command: {command}",
        target_environment="local_windows_desktop",
        target_runtime="local-worker-01",
        required_adapter_id="windows_interactive_desktop_relay",
        required_capability=action_type,
        trace_id=trace_id,
    )

    _log(f"result: outcome={spine_result.outcome.value} succeeded={spine_result.succeeded}")

    return SpineRoutedResult(
        command=command,
        spine_result=spine_result,
    )


def format_spine_result(result: SpineRoutedResult) -> str:
    """Format a SpineRoutedResult into a compact Discord reply."""
    if result.error_message:
        return f"**{result.command}** -- error: {result.error_message}"

    if result.spine_result is None:
        return f"**{result.command}** -- no result"

    sr = result.spine_result
    lines = [f"**{result.command}** -- {sr.outcome.value}"]

    if sr.succeeded:
        lines.append(f"spine_id: {sr.spine_id}")
        lines.append(f"trace_id: {sr.trace_id}")
        if sr.execution_result:
            lines.append(f"proofs: {sr.execution_result.proof_count}")
    else:
        if sr.denial_reasons:
            lines.append(f"denied: {', '.join(sr.denial_reasons[:3])}")

    return "\n".join(lines)
