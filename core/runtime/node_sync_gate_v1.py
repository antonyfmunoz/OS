"""Node Sync Gate v1 for the UMH substrate layer.

Mandatory version/sync gate before any local runtime execution.
Verifies code parity between VPS origin and local workstation:
  - Git commit hash parity (VPS vs local)
  - Working tree cleanliness
  - Relay script version/hash
  - Command registry version
  - Worker contract version
  - Config version

If local is behind, the gate either:
  1. Auto-syncs (if policy allows), or
  2. Returns NODE_OUT_OF_SYNC proof with exact remediation steps.

No WorkPacket crosses the VPS→local boundary unless this gate passes.

UMH substrate subsystem. Phase 96.8AF.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from core.state.transformation_state_ledger import (

    StateArtifactReference,
    StateLedgerRecord,
    TransformationStage,
    TransformationStateLedger,
    compute_hash,
    make_state_id,
    make_trace_id,
)

import os
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"



class SyncStatus(str, Enum):
    IN_SYNC = "in_sync"
    LOCAL_BEHIND = "local_behind"
    LOCAL_AHEAD = "local_ahead"
    DIVERGED = "diverged"
    DIRTY = "dirty"
    UNKNOWN = "unknown"


class SyncDecision(str, Enum):
    PASS = "pass"
    BLOCK = "block"
    AUTO_SYNC = "auto_sync"
    MANUAL_SYNC_REQUIRED = "manual_sync_required"


class SyncPolicy(str, Enum):
    STRICT = "strict"
    AUTO_PULL = "auto_pull"
    WARN_ONLY = "warn_only"


@dataclass
class RuntimeCodeHash:
    """Hash of a specific runtime artifact for version comparison."""

    artifact_name: str
    artifact_path: str
    content_hash: str
    version: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_name": self.artifact_name,
            "artifact_path": self.artifact_path,
            "content_hash": self.content_hash,
            "version": self.version,
            "timestamp": self.timestamp,
        }


@dataclass
class NodeSyncState:
    """Complete sync state between VPS and local workstation."""

    vps_commit: str
    local_commit: str
    sync_status: SyncStatus
    local_dirty: bool = False
    commits_behind: int = 0
    commits_ahead: int = 0
    relay_hash: RuntimeCodeHash | None = None
    command_registry_hash: RuntimeCodeHash | None = None
    worker_contract_hash: RuntimeCodeHash | None = None
    config_hash: RuntimeCodeHash | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def is_synced(self) -> bool:
        return self.sync_status == SyncStatus.IN_SYNC and not self.local_dirty

    def to_dict(self) -> dict[str, Any]:
        return {
            "vps_commit": self.vps_commit,
            "local_commit": self.local_commit,
            "sync_status": self.sync_status.value,
            "is_synced": self.is_synced,
            "local_dirty": self.local_dirty,
            "commits_behind": self.commits_behind,
            "commits_ahead": self.commits_ahead,
            "relay_hash": self.relay_hash.to_dict() if self.relay_hash else None,
            "command_registry_hash": (
                self.command_registry_hash.to_dict() if self.command_registry_hash else None
            ),
            "worker_contract_hash": (
                self.worker_contract_hash.to_dict() if self.worker_contract_hash else None
            ),
            "config_hash": self.config_hash.to_dict() if self.config_hash else None,
            "timestamp": self.timestamp,
        }


@dataclass
class NodeVersionReport:
    """Structured report of all version checks."""

    vps_commit: str
    local_commit: str
    commit_parity: bool
    relay_version_match: bool
    command_registry_match: bool
    worker_capability_match: bool
    config_version_match: bool
    local_dirty: bool
    requested_command: str = ""
    requested_capability: str = ""
    missing_commands: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)
    remediation_steps: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def all_checks_passed(self) -> bool:
        return (
            self.commit_parity
            and self.relay_version_match
            and self.command_registry_match
            and self.worker_capability_match
            and self.config_version_match
            and not self.local_dirty
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "vps_commit": self.vps_commit,
            "local_commit": self.local_commit,
            "commit_parity": self.commit_parity,
            "relay_version_match": self.relay_version_match,
            "command_registry_match": self.command_registry_match,
            "worker_capability_match": self.worker_capability_match,
            "config_version_match": self.config_version_match,
            "local_dirty": self.local_dirty,
            "all_checks_passed": self.all_checks_passed,
            "requested_command": self.requested_command,
            "requested_capability": self.requested_capability,
            "missing_commands": self.missing_commands,
            "missing_capabilities": self.missing_capabilities,
            "remediation_steps": self.remediation_steps,
            "timestamp": self.timestamp,
        }


@dataclass
class SyncProof:
    """Proof artifact for the node sync gate decision."""

    proof_id: str
    sync_state: NodeSyncState
    version_report: NodeVersionReport
    decision: SyncDecision
    denial_reasons: list[str] = field(default_factory=list)
    sync_actions_taken: list[str] = field(default_factory=list)
    proof_hash: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.proof_id:
            self.proof_id = f"SYNC-PROOF-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proof_hash:
            self.proof_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = json.dumps(
            {
                "proof_id": self.proof_id,
                "decision": self.decision.value,
                "vps_commit": self.sync_state.vps_commit,
                "local_commit": self.sync_state.local_commit,
                "sync_status": self.sync_state.sync_status.value,
                "all_checks_passed": self.version_report.all_checks_passed,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    @property
    def passed(self) -> bool:
        return self.decision == SyncDecision.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_id": self.proof_id,
            "sync_state": self.sync_state.to_dict(),
            "version_report": self.version_report.to_dict(),
            "decision": self.decision.value,
            "passed": self.passed,
            "denial_reasons": self.denial_reasons,
            "sync_actions_taken": self.sync_actions_taken,
            "proof_hash": self.proof_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class NodeSyncGateResult:
    """Result of the node sync gate evaluation."""

    result_id: str
    passed: bool
    decision: SyncDecision
    sync_proof: SyncProof
    denial_reasons: list[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.result_id:
            self.result_id = f"NSG-{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "passed": self.passed,
            "decision": self.decision.value,
            "sync_proof": self.sync_proof.to_dict(),
            "denial_reasons": self.denial_reasons,
            "timestamp": self.timestamp,
        }


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file's contents."""
    if not file_path.exists():
        return ""
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def get_git_head_commit(repo_path: Path) -> str:
    """Get the HEAD commit hash for a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(repo_path),
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def check_git_dirty(repo_path: Path) -> bool:
    """Check if repo has uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            cwd=str(repo_path),
            timeout=10,
        )
        return bool(result.stdout.strip()) if result.returncode == 0 else True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return True


def count_commits_behind_ahead(
    repo_path: Path, local_ref: str = "HEAD", remote_ref: str = "origin/main"
) -> tuple[int, int]:
    """Count commits behind and ahead between local and remote."""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"{remote_ref}...{local_ref}"],
            capture_output=True,
            text=True,
            cwd=str(repo_path),
            timeout=10,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
        return 0, 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
        return 0, 0


class NodeSyncGate:
    """Mandatory sync gate before local runtime dispatch.

    Verifies code parity between VPS and local workstation before
    allowing WorkPackets to cross the VPS→local boundary.
    """

    VERSION = "v1"

    def __init__(
        self,
        vps_repo_path: Path = Path(_ROOT),
        local_repo_path: Path | None = None,
        relay_script_path: Path | None = None,
        command_registry: dict[str, str] | None = None,
        worker_capabilities: list[str] | None = None,
        config_path: Path | None = None,
        sync_policy: SyncPolicy = SyncPolicy.STRICT,
        allow_dirty: bool = False,
        ledger: TransformationStateLedger | None = None,
        proof_dir: Path | None = None,
        registry_hash: str = "",
    ) -> None:
        self._vps_repo = vps_repo_path
        self._local_repo = local_repo_path
        self._relay_script = relay_script_path
        self._command_registry = command_registry or {}
        self._known_actions = set(self._command_registry.values())
        self._worker_capabilities = worker_capabilities or []
        self._registry_hash = registry_hash
        self._config_path = config_path
        self._sync_policy = sync_policy
        self._allow_dirty = allow_dirty
        self._ledger = ledger
        self._proof_dir = proof_dir or Path("data/runtime/sync_proofs")
        self._proof_dir.mkdir(parents=True, exist_ok=True)

    def _get_vps_commit(self) -> str:
        return get_git_head_commit(self._vps_repo)

    def _get_local_commit(self) -> str:
        if self._local_repo:
            return get_git_head_commit(self._local_repo)
        return ""

    def _check_local_dirty(self) -> bool:
        if self._local_repo:
            return check_git_dirty(self._local_repo)
        return False

    def _compute_relay_hash(self) -> RuntimeCodeHash | None:
        if not self._relay_script:
            return None
        h = compute_file_hash(self._relay_script)
        return RuntimeCodeHash(
            artifact_name="relay_script",
            artifact_path=str(self._relay_script),
            content_hash=h,
        )

    def _compute_config_hash(self) -> RuntimeCodeHash | None:
        if not self._config_path:
            return None
        h = compute_file_hash(self._config_path)
        return RuntimeCodeHash(
            artifact_name="runtime_config",
            artifact_path=str(self._config_path),
            content_hash=h,
        )

    def _compute_command_registry_hash(self) -> RuntimeCodeHash:
        payload = json.dumps(self._command_registry, sort_keys=True)
        h = hashlib.sha256(payload.encode()).hexdigest()
        return RuntimeCodeHash(
            artifact_name="command_registry",
            artifact_path="in_memory",
            content_hash=h,
        )

    def _compute_worker_contract_hash(self) -> RuntimeCodeHash:
        payload = json.dumps(sorted(self._worker_capabilities))
        h = hashlib.sha256(payload.encode()).hexdigest()
        return RuntimeCodeHash(
            artifact_name="worker_contract",
            artifact_path="in_memory",
            content_hash=h,
        )

    def _determine_sync_status(
        self, vps_commit: str, local_commit: str, local_dirty: bool
    ) -> SyncStatus:
        if local_dirty:
            return SyncStatus.DIRTY
        if not vps_commit or not local_commit:
            return SyncStatus.UNKNOWN
        if vps_commit == local_commit:
            return SyncStatus.IN_SYNC
        behind, ahead = count_commits_behind_ahead(self._vps_repo)
        if behind > 0 and ahead == 0:
            return SyncStatus.LOCAL_BEHIND
        if ahead > 0 and behind == 0:
            return SyncStatus.LOCAL_AHEAD
        if behind > 0 and ahead > 0:
            return SyncStatus.DIVERGED
        if vps_commit != local_commit:
            return SyncStatus.LOCAL_BEHIND
        return SyncStatus.IN_SYNC

    def _try_auto_sync(self) -> list[str]:
        """Attempt safe auto-sync if policy allows. Returns actions taken."""
        if self._sync_policy != SyncPolicy.AUTO_PULL:
            return []
        if not self._local_repo:
            return []
        actions: list[str] = []
        try:
            fetch = subprocess.run(
                ["git", "fetch", "origin"],
                capture_output=True,
                text=True,
                cwd=str(self._local_repo),
                timeout=30,
            )
            if fetch.returncode == 0:
                actions.append("git_fetch_origin")

            pull = subprocess.run(
                ["git", "pull", "--ff-only", "origin", "main"],
                capture_output=True,
                text=True,
                cwd=str(self._local_repo),
                timeout=30,
            )
            if pull.returncode == 0:
                actions.append("git_pull_ff_only")
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            actions.append("auto_sync_failed")

        return actions

    def validate(
        self,
        requested_command: str = "",
        requested_capability: str = "",
        expected_relay_hash: str = "",
        trace_id: str = "",
    ) -> NodeSyncGateResult:
        """Run the full node sync gate validation."""
        if not trace_id:
            trace_id = make_trace_id("SYNC")

        vps_commit = self._get_vps_commit()
        local_commit = self._get_local_commit()
        local_dirty = self._check_local_dirty()

        sync_status = self._determine_sync_status(vps_commit, local_commit, local_dirty)

        relay_hash = self._compute_relay_hash()
        cmd_reg_hash = self._compute_command_registry_hash()
        worker_hash = self._compute_worker_contract_hash()
        config_hash = self._compute_config_hash()

        sync_state = NodeSyncState(
            vps_commit=vps_commit,
            local_commit=local_commit,
            sync_status=sync_status,
            local_dirty=local_dirty,
            relay_hash=relay_hash,
            command_registry_hash=cmd_reg_hash,
            worker_contract_hash=worker_hash,
            config_hash=config_hash,
        )

        denial_reasons: list[str] = []
        sync_actions: list[str] = []

        commit_parity = (vps_commit == local_commit) if (vps_commit and local_commit) else True

        if local_dirty and not self._allow_dirty:
            denial_reasons.append("local_working_tree_dirty")

        if not commit_parity:
            if self._sync_policy == SyncPolicy.AUTO_PULL:
                sync_actions = self._try_auto_sync()
                new_local = self._get_local_commit()
                if new_local == vps_commit:
                    commit_parity = True
                    sync_state.local_commit = new_local
                    sync_state.sync_status = SyncStatus.IN_SYNC
                else:
                    denial_reasons.append(
                        f"local_behind_vps: local={local_commit[:8]} vps={vps_commit[:8]}"
                    )
            elif self._sync_policy == SyncPolicy.STRICT:
                denial_reasons.append(
                    f"local_behind_vps: local={local_commit[:8]} vps={vps_commit[:8]}"
                )

        relay_match = True
        if expected_relay_hash and relay_hash:
            if relay_hash.content_hash != expected_relay_hash:
                relay_match = False
                denial_reasons.append(
                    f"relay_hash_mismatch: expected={expected_relay_hash[:16]} "
                    f"got={relay_hash.content_hash[:16]}"
                )

        cmd_match = True
        missing_commands: list[str] = []
        if requested_command and (
            requested_command not in self._command_registry
            and requested_command not in self._known_actions
        ):
            cmd_match = False
            missing_commands.append(requested_command)
            denial_reasons.append(f"command_not_in_registry: {requested_command}")

        cap_match = True
        missing_caps: list[str] = []
        if requested_capability and requested_capability not in self._worker_capabilities:
            cap_match = False
            missing_caps.append(requested_capability)
            denial_reasons.append(f"worker_missing_capability: {requested_capability}")

        config_match = True
        if self._config_path and not self._config_path.exists():
            config_match = False
            denial_reasons.append(f"config_missing: {self._config_path}")

        remediation: list[str] = []
        if not commit_parity:
            remediation.append("cd <local_repo> && git pull origin main")
        if local_dirty:
            remediation.append("cd <local_repo> && git stash or git commit")
        if not relay_match:
            remediation.append("update relay script to match VPS version")
        if missing_commands:
            remediation.append(f"add commands to registry: {missing_commands}")
        if missing_caps:
            remediation.append(f"add capabilities to worker: {missing_caps}")

        version_report = NodeVersionReport(
            vps_commit=vps_commit,
            local_commit=sync_state.local_commit,
            commit_parity=commit_parity,
            relay_version_match=relay_match,
            command_registry_match=cmd_match,
            worker_capability_match=cap_match,
            config_version_match=config_match,
            local_dirty=local_dirty,
            requested_command=requested_command,
            requested_capability=requested_capability,
            missing_commands=missing_commands,
            missing_capabilities=missing_caps,
            remediation_steps=remediation,
        )

        if denial_reasons:
            if self._sync_policy == SyncPolicy.WARN_ONLY:
                decision = SyncDecision.PASS
            else:
                decision = SyncDecision.BLOCK
        else:
            decision = SyncDecision.PASS

        sync_proof = SyncProof(
            proof_id="",
            sync_state=sync_state,
            version_report=version_report,
            decision=decision,
            denial_reasons=denial_reasons,
            sync_actions_taken=sync_actions,
        )

        proof_path = self._proof_dir / f"{sync_proof.proof_id}.json"
        proof_path.write_text(json.dumps(sync_proof.to_dict(), indent=2, default=str))

        if self._ledger:
            stage = (
                TransformationStage.NODE_SYNC_VALIDATED
                if decision == SyncDecision.PASS
                else TransformationStage.NODE_SYNC_DENIED
            )
            record = StateLedgerRecord(
                state_id=make_state_id(),
                trace_id=trace_id,
                parent_state_id="",
                stage=stage,
                input_artifact_ref=StateArtifactReference(
                    artifact_id=sync_proof.proof_id,
                    artifact_type="sync_proof",
                ),
                output_artifact_ref=StateArtifactReference(
                    artifact_id=sync_proof.proof_id,
                    artifact_type="sync_gate_result",
                ),
                transformer_name="NodeSyncGate",
                transformer_version=self.VERSION,
                runtime_id="vps",
                adapter_id="node_sync",
                policy_envelope={
                    "sync_policy": self._sync_policy.value,
                    "allow_dirty": self._allow_dirty,
                },
                confidence="structural",
                input_hash=compute_hash(json.dumps(sync_state.to_dict(), sort_keys=True)),
                output_hash=sync_proof.proof_hash,
                allowed_next_actions=(
                    ["dispatch_to_runtime"] if decision == SyncDecision.PASS else []
                ),
                blocked_next_actions=(denial_reasons if decision != SyncDecision.PASS else []),
            )
            self._ledger.append(record)

        return NodeSyncGateResult(
            result_id="",
            passed=decision == SyncDecision.PASS,
            decision=decision,
            sync_proof=sync_proof,
            denial_reasons=denial_reasons,
        )

    def validate_for_command(
        self,
        command: str,
        action_type: str,
        expected_relay_hash: str = "",
        trace_id: str = "",
    ) -> NodeSyncGateResult:
        """Convenience wrapper for command-level validation."""
        return self.validate(
            requested_command=command,
            requested_capability=action_type,
            expected_relay_hash=expected_relay_hash,
            trace_id=trace_id,
        )
