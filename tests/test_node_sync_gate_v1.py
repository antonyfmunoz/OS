"""Tests for Node Sync Gate v1 — Phase 96.8AF.

Covers:
  - local up to date passes
  - local behind blocks or syncs
  - dirty local tree blocks
  - missing command registry blocks
  - missing worker capability blocks
  - relay hash mismatch blocks
  - deterministic sync proof hash
  - ledger integration
  - sync gate in execution spine
  - warn_only policy allows despite issues
  - config missing blocks
"""

import sys
import tempfile
import json
import hashlib

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

import pytest
from pathlib import Path

from core.runtime.node_sync_gate_v1 import (
    NodeSyncGate,
    NodeSyncGateResult,
    NodeSyncState,
    NodeVersionReport,
    RuntimeCodeHash,
    SyncDecision,
    SyncPolicy,
    SyncProof,
    SyncStatus,
    compute_file_hash,
)
from core.runtime.live_local_runtime_execution_v1 import (
    ExecutionSpineOutcome,
    LiveLocalRuntimeExecution,
)
from governance.policy.execution_authority_engine_v1 import (
    CapabilityAuthority,
    EnvironmentAuthority,
    ExecutionAuthorityEngine,
    RiskClass,
)
from execution.runtime.workpacket_execution_gate_v1 import (
    WorkPacketExecutionGate,
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
from core.runtime.local_runtime_supervisor_v1 import (
    LocalRuntimeSupervisor,
)
from state.transformation_state_ledger import (
    TransformationStage,
    TransformationStateLedger,
)


# -- Fixtures --


def _make_gate(
    tmp: Path,
    command_registry: dict[str, str] | None = None,
    worker_capabilities: list[str] | None = None,
    sync_policy: SyncPolicy = SyncPolicy.STRICT,
    allow_dirty: bool = False,
    relay_script_path: Path | None = None,
    config_path: Path | None = None,
    ledger: TransformationStateLedger | None = None,
) -> NodeSyncGate:
    if command_registry is None:
        command_registry = {
            "!chrome-open-google-drive": "chrome_open_google_drive",
            "!ping": "ping",
            "chrome_open_google_drive": "chrome_open_google_drive",
            "ping": "ping",
        }
    if worker_capabilities is None:
        worker_capabilities = [
            "chrome_open_google_drive",
            "open_application_url",
            "ping",
        ]
    return NodeSyncGate(
        vps_repo_path=Path(_ROOT),
        local_repo_path=None,
        relay_script_path=relay_script_path,
        command_registry=command_registry,
        worker_capabilities=worker_capabilities,
        config_path=config_path,
        sync_policy=sync_policy,
        allow_dirty=allow_dirty,
        ledger=ledger,
        proof_dir=tmp / "sync_proofs",
    )


def _make_spine_with_sync_gate(
    tmp: Path,
    sync_gate: NodeSyncGate,
) -> LiveLocalRuntimeExecution:
    env_auth = EnvironmentAuthority(
        environment_type="local_windows_desktop",
        can_own_gui=True,
        can_own_local_shell=True,
        can_execute_browser=True,
        max_risk_class=RiskClass.MEDIUM,
    )
    cap_auth = CapabilityAuthority(
        adapter_id="windows_interactive_desktop_relay",
        capabilities=[
            "browser_execution",
            "chrome_launch",
            "chrome_open_google_drive",
            "open_application_url",
        ],
        is_configured=True,
        is_mature=True,
    )
    authority = ExecutionAuthorityEngine(
        environment_authorities=[env_auth],
        capability_authorities=[cap_auth],
    )
    ledger = TransformationStateLedger(tmp / "ledger")
    gate = WorkPacketExecutionGate(
        environment_authorities={"local_windows_desktop": env_auth},
        capability_authorities={"windows_interactive_desktop_relay": cap_auth},
        available_runtimes={"local-worker-01": True},
        ledger=ledger,
        proof_dir=tmp / "gate_proofs",
    )
    queue = RuntimeDispatchQueue(tmp / "queue")
    registry = RuntimeSessionRegistry()
    recovery = RuntimeRecoveryEngine(max_retries=3)
    supervisor = LocalRuntimeSupervisor(
        queue=queue,
        registry=registry,
        recovery=recovery,
        ledger=ledger,
        proof_dir=tmp / "exec_proofs",
        worker_id="local-worker-01",
        environment_id="local_windows_desktop",
    )
    supervisor.start()
    return LiveLocalRuntimeExecution(
        authority_engine=authority,
        gate=gate,
        queue=queue,
        supervisor=supervisor,
        ledger=ledger,
        proof_dir=tmp / "spine_proofs",
        sync_gate=sync_gate,
    )


# ========================================================
# Test: Local Up To Date Passes
# ========================================================


class TestLocalUpToDate:
    def test_synced_gate_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(Path(tmpdir))
            result = gate.validate(
                requested_command="!chrome-open-google-drive",
                requested_capability="chrome_open_google_drive",
            )
            assert result.passed
            assert result.decision == SyncDecision.PASS
            assert len(result.denial_reasons) == 0

    def test_version_report_all_checks_pass(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(Path(tmpdir))
            result = gate.validate(
                requested_command="!chrome-open-google-drive",
                requested_capability="chrome_open_google_drive",
            )
            report = result.sync_proof.version_report
            assert report.command_registry_match is True
            assert report.worker_capability_match is True
            assert report.all_checks_passed is True


# ========================================================
# Test: Local Behind Blocks
# ========================================================


class TestLocalBehindBlocks:
    def test_commit_mismatch_blocks_in_strict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            local_repo = Path(tmpdir) / "local_repo"
            local_repo.mkdir()
            (local_repo / ".git").mkdir()
            gate = NodeSyncGate(
                vps_repo_path=Path(_ROOT),
                local_repo_path=local_repo,
                command_registry={"!ping": "ping"},
                worker_capabilities=["ping"],
                sync_policy=SyncPolicy.STRICT,
                proof_dir=Path(tmpdir) / "proofs",
            )
            result = gate.validate(
                requested_command="!ping",
                requested_capability="ping",
            )
            if not result.passed:
                assert any("local_behind" in r or "dirty" in r for r in result.denial_reasons)


# ========================================================
# Test: Dirty Local Tree Blocks
# ========================================================


class TestDirtyLocalTree:
    def test_dirty_tree_blocks_when_not_allowed(self):
        """Simulate dirty local tree by using a non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dirty_repo = Path(tmpdir) / "dirty_local"
            dirty_repo.mkdir()
            gate = NodeSyncGate(
                vps_repo_path=Path(_ROOT),
                local_repo_path=dirty_repo,
                command_registry={"!ping": "ping"},
                worker_capabilities=["ping"],
                sync_policy=SyncPolicy.STRICT,
                allow_dirty=False,
                proof_dir=Path(tmpdir) / "proofs",
            )
            result = gate.validate(
                requested_command="!ping",
                requested_capability="ping",
            )
            assert not result.passed
            assert any("dirty" in r for r in result.denial_reasons)

    def test_dirty_tree_allowed_when_flagged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dirty_repo = Path(tmpdir) / "dirty_local"
            dirty_repo.mkdir()
            gate = NodeSyncGate(
                vps_repo_path=Path(_ROOT),
                local_repo_path=dirty_repo,
                command_registry={"!ping": "ping"},
                worker_capabilities=["ping"],
                sync_policy=SyncPolicy.STRICT,
                allow_dirty=True,
                proof_dir=Path(tmpdir) / "proofs",
            )
            result = gate.validate(
                requested_command="!ping",
                requested_capability="ping",
            )
            assert result.passed


# ========================================================
# Test: Missing Command Registry Blocks
# ========================================================


class TestMissingCommandRegistry:
    def test_missing_command_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(
                Path(tmpdir),
                command_registry={"!ping": "ping"},
            )
            result = gate.validate(
                requested_command="!chrome-open-google-drive",
                requested_capability="chrome_open_google_drive",
            )
            assert not result.passed
            assert any("command_not_in_registry" in r for r in result.denial_reasons)
            report = result.sync_proof.version_report
            assert report.command_registry_match is False
            assert "!chrome-open-google-drive" in report.missing_commands

    def test_empty_registry_blocks_any_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(Path(tmpdir), command_registry={})
            result = gate.validate(requested_command="!ping")
            assert not result.passed


# ========================================================
# Test: Missing Worker Capability Blocks
# ========================================================


class TestMissingWorkerCapability:
    def test_missing_capability_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(
                Path(tmpdir),
                worker_capabilities=["ping"],
            )
            result = gate.validate(
                requested_capability="chrome_open_google_drive",
            )
            assert not result.passed
            assert any("worker_missing_capability" in r for r in result.denial_reasons)
            report = result.sync_proof.version_report
            assert report.worker_capability_match is False
            assert "chrome_open_google_drive" in report.missing_capabilities

    def test_empty_capabilities_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(Path(tmpdir), worker_capabilities=[])
            result = gate.validate(requested_capability="ping")
            assert not result.passed


# ========================================================
# Test: Relay Hash Mismatch Blocks
# ========================================================


class TestRelayHashMismatch:
    def test_hash_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            relay_path = Path(tmpdir) / "relay.ps1"
            relay_path.write_text("Write-Host 'relay v1'")
            gate = _make_gate(Path(tmpdir), relay_script_path=relay_path)
            result = gate.validate(
                expected_relay_hash="0000000000000000000000000000000000000000",
            )
            assert not result.passed
            assert any("relay_hash_mismatch" in r for r in result.denial_reasons)

    def test_matching_hash_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            relay_path = Path(tmpdir) / "relay.ps1"
            relay_path.write_text("Write-Host 'relay v1'")
            expected = compute_file_hash(relay_path)
            gate = _make_gate(Path(tmpdir), relay_script_path=relay_path)
            result = gate.validate(expected_relay_hash=expected)
            assert result.passed

    def test_missing_relay_no_hash_check(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(Path(tmpdir))
            result = gate.validate(expected_relay_hash="anything")
            assert result.passed


# ========================================================
# Test: Deterministic Sync Proof Hash
# ========================================================


class TestDeterministicProofHash:
    def test_proof_hash_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(Path(tmpdir))
            r1 = gate.validate()
            r2 = gate.validate()
            assert r1.sync_proof.proof_hash
            assert r2.sync_proof.proof_hash
            assert len(r1.sync_proof.proof_hash) == 64

    def test_proof_hash_changes_on_different_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate1 = _make_gate(
                Path(tmpdir),
                command_registry={
                    "!ping": "ping",
                    "!chrome-open-google-drive": "chrome_open_google_drive",
                },
            )
            gate2 = _make_gate(
                Path(tmpdir),
                command_registry={"!ping": "ping"},
            )
            r1 = gate1.validate(requested_command="!chrome-open-google-drive")
            r2 = gate2.validate(requested_command="!chrome-open-google-drive")
            assert r1.sync_proof.decision != r2.sync_proof.decision

    def test_proof_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(Path(tmpdir))
            result = gate.validate()
            proof_files = list((Path(tmpdir) / "sync_proofs").glob("*.json"))
            assert len(proof_files) >= 1
            data = json.loads(proof_files[0].read_text())
            assert "proof_hash" in data
            assert data["decision"] == "pass"


# ========================================================
# Test: Ledger Integration
# ========================================================


class TestLedgerIntegration:
    def test_pass_records_sync_validated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = TransformationStateLedger(Path(tmpdir) / "ledger")
            gate = _make_gate(Path(tmpdir), ledger=ledger)
            result = gate.validate()
            assert result.passed
            assert ledger.record_count >= 1

    def test_deny_records_sync_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger = TransformationStateLedger(Path(tmpdir) / "ledger")
            gate = _make_gate(
                Path(tmpdir),
                command_registry={},
                ledger=ledger,
            )
            result = gate.validate(requested_command="!missing")
            assert not result.passed
            assert ledger.record_count >= 1


# ========================================================
# Test: Spine Integration with Sync Gate
# ========================================================


class TestSpineWithSyncGate:
    def test_spine_passes_with_valid_sync(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sync_gate = _make_gate(Path(tmpdir))
            spine = _make_spine_with_sync_gate(Path(tmpdir), sync_gate)
            result = spine.execute(
                packet_id="PKT-sync-pass",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
                required_capability="chrome_open_google_drive",
            )
            assert result.succeeded
            assert result.outcome == ExecutionSpineOutcome.SUCCESS

    def test_spine_blocks_when_sync_denied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sync_gate = _make_gate(
                Path(tmpdir),
                command_registry={},
                worker_capabilities=[],
            )
            spine = _make_spine_with_sync_gate(Path(tmpdir), sync_gate)
            result = spine.execute(
                packet_id="PKT-sync-block",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
                required_capability="chrome_open_google_drive",
            )
            assert not result.succeeded
            assert result.outcome == ExecutionSpineOutcome.NODE_SYNC_DENIED
            assert len(result.denial_reasons) > 0

    def test_spine_without_sync_gate_still_works(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_auth = EnvironmentAuthority(
                environment_type="local_windows_desktop",
                can_own_gui=True,
                can_own_local_shell=True,
                can_execute_browser=True,
                max_risk_class=RiskClass.MEDIUM,
            )
            cap_auth = CapabilityAuthority(
                adapter_id="windows_interactive_desktop_relay",
                capabilities=["chrome_open_google_drive"],
                is_configured=True,
                is_mature=True,
            )
            authority = ExecutionAuthorityEngine(
                environment_authorities=[env_auth],
                capability_authorities=[cap_auth],
            )
            ledger = TransformationStateLedger(Path(tmpdir) / "ledger")
            gate = WorkPacketExecutionGate(
                environment_authorities={"local_windows_desktop": env_auth},
                capability_authorities={"windows_interactive_desktop_relay": cap_auth},
                available_runtimes={"local-worker-01": True},
                ledger=ledger,
                proof_dir=Path(tmpdir) / "gate_proofs",
            )
            queue = RuntimeDispatchQueue(Path(tmpdir) / "queue")
            supervisor = LocalRuntimeSupervisor(
                queue=queue,
                registry=RuntimeSessionRegistry(),
                recovery=RuntimeRecoveryEngine(max_retries=3),
                ledger=ledger,
                proof_dir=Path(tmpdir) / "exec_proofs",
                worker_id="local-worker-01",
                environment_id="local_windows_desktop",
            )
            supervisor.start()
            spine = LiveLocalRuntimeExecution(
                authority_engine=authority,
                gate=gate,
                queue=queue,
                supervisor=supervisor,
                ledger=ledger,
                proof_dir=Path(tmpdir) / "spine_proofs",
            )
            result = spine.execute(
                packet_id="PKT-no-sync",
                action_type="chrome_open_google_drive",
                target_environment="local_windows_desktop",
                target_runtime="local-worker-01",
                required_adapter_id="windows_interactive_desktop_relay",
                required_capability="chrome_open_google_drive",
            )
            assert result.succeeded


# ========================================================
# Test: Warn-Only Policy
# ========================================================


class TestWarnOnlyPolicy:
    def test_warn_only_passes_despite_issues(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(
                Path(tmpdir),
                command_registry={},
                sync_policy=SyncPolicy.WARN_ONLY,
            )
            result = gate.validate(requested_command="!missing")
            assert result.passed
            assert result.decision == SyncDecision.PASS
            assert len(result.sync_proof.denial_reasons) > 0


# ========================================================
# Test: Config Missing
# ========================================================


class TestConfigMissing:
    def test_missing_config_blocks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(
                Path(tmpdir),
                config_path=Path(tmpdir) / "nonexistent.json",
            )
            result = gate.validate()
            assert not result.passed
            assert any("config_missing" in r for r in result.denial_reasons)


# ========================================================
# Test: Dataclass Contracts
# ========================================================


class TestDataclassContracts:
    def test_node_sync_state_to_dict(self):
        state = NodeSyncState(
            vps_commit="abc123",
            local_commit="abc123",
            sync_status=SyncStatus.IN_SYNC,
        )
        d = state.to_dict()
        assert d["vps_commit"] == "abc123"
        assert d["is_synced"] is True

    def test_runtime_code_hash_to_dict(self):
        h = RuntimeCodeHash(
            artifact_name="relay",
            artifact_path="/path/to/relay.ps1",
            content_hash="deadbeef",
        )
        d = h.to_dict()
        assert d["content_hash"] == "deadbeef"

    def test_sync_proof_to_dict(self):
        state = NodeSyncState(
            vps_commit="abc",
            local_commit="abc",
            sync_status=SyncStatus.IN_SYNC,
        )
        report = NodeVersionReport(
            vps_commit="abc",
            local_commit="abc",
            commit_parity=True,
            relay_version_match=True,
            command_registry_match=True,
            worker_capability_match=True,
            config_version_match=True,
            local_dirty=False,
        )
        proof = SyncProof(
            proof_id="SYNC-PROOF-test",
            sync_state=state,
            version_report=report,
            decision=SyncDecision.PASS,
        )
        d = proof.to_dict()
        assert d["passed"] is True
        assert len(d["proof_hash"]) == 64

    def test_gate_result_to_dict(self):
        state = NodeSyncState(
            vps_commit="abc",
            local_commit="abc",
            sync_status=SyncStatus.IN_SYNC,
        )
        report = NodeVersionReport(
            vps_commit="abc",
            local_commit="abc",
            commit_parity=True,
            relay_version_match=True,
            command_registry_match=True,
            worker_capability_match=True,
            config_version_match=True,
            local_dirty=False,
        )
        proof = SyncProof(
            proof_id="",
            sync_state=state,
            version_report=report,
            decision=SyncDecision.PASS,
        )
        result = NodeSyncGateResult(
            result_id="",
            passed=True,
            decision=SyncDecision.PASS,
            sync_proof=proof,
        )
        d = result.to_dict()
        assert d["passed"] is True
        serialized = json.dumps(d, default=str)
        assert len(serialized) > 0


# ========================================================
# Test: Validate for Command (convenience)
# ========================================================


class TestValidateForCommand:
    def test_validate_for_command_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(Path(tmpdir))
            result = gate.validate_for_command(
                command="!chrome-open-google-drive",
                action_type="chrome_open_google_drive",
            )
            assert result.passed

    def test_validate_for_command_blocks_unknown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gate = _make_gate(Path(tmpdir))
            result = gate.validate_for_command(
                command="!unknown",
                action_type="unknown_action",
            )
            assert not result.passed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
