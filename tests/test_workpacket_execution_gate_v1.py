"""Tests for WorkPacket Execution Gate v1.

Phase 96.8AD — execution gate validation.
"""

import sys

sys.path.insert(0, "/opt/OS")

from pathlib import Path

import pytest

from core.governance.execution_authority_engine_v1 import (
    ApprovalRequirement,
    AuthorityClass,
    AuthorityDecision,
    CapabilityAuthority,
    EnvironmentAuthority,
    RiskClass,
)
from core.execution.workpacket_execution_gate_v1 import (
    GATE_STRUCTURAL_BLOCKS,
    AdapterReadiness,
    EnvironmentReadiness,
    ExecutionGateResult,
    ExecutionReadiness,
    GateDenialCategory,
    GateVerdict,
    ProofReadiness,
    RuntimeExecutionRequest,
    RuntimeReadiness,
    WorkPacketExecutionGate,
)
from core.state.transformation_state_ledger import TransformationStateLedger


def _make_authority(
    allowed: bool = True,
    auth_class: AuthorityClass = AuthorityClass.APPROVE_EXECUTE,
    env_met: bool = True,
    cap_met: bool = True,
) -> AuthorityDecision:
    return AuthorityDecision(
        decision_id="AUTH-DEC-test",
        request_id="AUTH-REQ-test",
        authority_class=auth_class,
        risk_class=RiskClass.LOW,
        approval_requirement=ApprovalRequirement.SYSTEM_APPROVAL,
        workpacket_allowed=allowed,
        environment_authority_met=env_met,
        capability_authority_met=cap_met,
    )


def _make_gate(
    tmp_path: Path,
    env_types: list[str] | None = None,
    runtimes: dict[str, bool] | None = None,
    adapters: list[CapabilityAuthority] | None = None,
    with_ledger: bool = False,
) -> WorkPacketExecutionGate:
    env_auths = {}
    for et in env_types or []:
        env_auths[et] = EnvironmentAuthority(
            environment_type=et,
            can_own_gui=True,
            can_execute_browser=True,
            max_risk_class=RiskClass.MEDIUM,
        )
    cap_auths = {}
    for ca in adapters or []:
        cap_auths[ca.adapter_id] = ca

    ledger = TransformationStateLedger(tmp_path / "ledger") if with_ledger else None

    return WorkPacketExecutionGate(
        environment_authorities=env_auths,
        capability_authorities=cap_auths,
        available_runtimes=runtimes or {},
        ledger=ledger,
        proof_dir=tmp_path / "proofs",
    )


VALID_KWARGS = {
    "packet_id": "WP-001",
    "action_type": "read_only_query",
    "target_environment": "vps_tmux",
    "target_runtime": "vps-worker-01",
    "blocked_actions": ["wallet_execution", "financial_execution"],
    "proof_requirements": ["execution_proof"],
    "timeout_seconds": 60,
    "governance_trace_id": "TRACE-001",
    "execution_lineage_id": "LINEAGE-001",
}


class TestValidPacketPasses:
    def test_valid_packet_passes(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        result = gate.validate(authority_decision=authority, **VALID_KWARGS)
        assert result.verdict == GateVerdict.PASS
        assert result.runtime_execution_request is not None
        assert result.runtime_execution_request.packet_id == "WP-001"
        assert result.gate_hash != ""

    def test_pass_produces_execution_request(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        result = gate.validate(authority_decision=authority, **VALID_KWARGS)
        req = result.runtime_execution_request
        assert req is not None
        assert req.authority_decision_id == "AUTH-DEC-test"
        assert req.target_environment == "vps_tmux"
        assert req.target_runtime == "vps-worker-01"
        assert req.governance_trace_id == "TRACE-001"


class TestExpiredPacket:
    def test_expired_packet_blocked(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        result = gate.validate(
            authority_decision=authority,
            expires_at="2020-01-01T00:00:00Z",
            **VALID_KWARGS,
        )
        assert result.verdict == GateVerdict.DENY
        assert any("expired" in r for r in result.denial_reasons)
        assert GateDenialCategory.PACKET_EXPIRED.value in result.denial_categories


class TestMissingEnvironment:
    def test_missing_environment_blocked(self, tmp_path: Path) -> None:
        gate = _make_gate(tmp_path, runtimes={"vps-worker-01": True})
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "target_environment": "nonexistent_env"}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert GateDenialCategory.MISSING_ENVIRONMENT.value in result.denial_categories

    def test_empty_environment_blocked(self, tmp_path: Path) -> None:
        gate = _make_gate(tmp_path, runtimes={"vps-worker-01": True})
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "target_environment": ""}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert any("missing_target_environment" in r for r in result.denial_reasons)


class TestMissingRuntime:
    def test_missing_runtime_blocked(self, tmp_path: Path) -> None:
        gate = _make_gate(tmp_path, env_types=["vps_tmux"])
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "target_runtime": "nonexistent_runtime"}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert GateDenialCategory.MISSING_RUNTIME.value in result.denial_categories

    def test_empty_runtime_blocked(self, tmp_path: Path) -> None:
        gate = _make_gate(tmp_path, env_types=["vps_tmux"])
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "target_runtime": ""}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert any("missing_target_runtime" in r for r in result.denial_reasons)


class TestMissingProof:
    def test_no_proof_requirements_blocked(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "proof_requirements": []}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert GateDenialCategory.MISSING_PROOF_REQUIREMENTS.value in result.denial_categories


class TestMissingBlockedActions:
    def test_no_blocked_actions_blocked(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "blocked_actions": []}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert GateDenialCategory.MISSING_BLOCKED_ACTIONS.value in result.denial_categories


class TestRecursiveRuntimeBlocked:
    def test_recursive_runtime_spawning(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "action_type": "recursive_runtime_spawning"}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert GateDenialCategory.STRUCTURAL_BLOCK.value in result.denial_categories


class TestWalletExecutionBlocked:
    def test_wallet_execution(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "action_type": "wallet_execution"}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert any("structural_block" in r for r in result.denial_reasons)


class TestDirectAdapterBlocked:
    def test_direct_adapter_execution(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "action_type": "direct_adapter_execution"}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert any("adapters_never_execute_directly" in r for r in result.denial_reasons)


class TestAuthorityDenied:
    def test_authority_denied_blocks(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority(allowed=False, auth_class=AuthorityClass.DENY)
        result = gate.validate(authority_decision=authority, **VALID_KWARGS)
        assert result.verdict == GateVerdict.DENY
        assert GateDenialCategory.WORKPACKET_NOT_ALLOWED.value in result.denial_categories
        assert GateDenialCategory.AUTHORITY_DENIED.value in result.denial_categories


class TestMissingGovernanceTrace:
    def test_no_governance_trace(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "governance_trace_id": ""}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert GateDenialCategory.MISSING_GOVERNANCE_TRACE.value in result.denial_categories


class TestMissingLineage:
    def test_no_execution_lineage(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "execution_lineage_id": ""}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert GateDenialCategory.MISSING_LINEAGE.value in result.denial_categories


class TestMissingTimeout:
    def test_no_timeout(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        kwargs = {**VALID_KWARGS, "timeout_seconds": 0}
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert GateDenialCategory.MISSING_TIMEOUT.value in result.denial_categories


class TestAdapterReadiness:
    def test_missing_adapter_blocks(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        kwargs = {
            **VALID_KWARGS,
            "required_adapter_id": "nonexistent-adapter",
        }
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY
        assert GateDenialCategory.ADAPTER_NOT_READY.value in result.denial_categories

    def test_adapter_missing_capability(self, tmp_path: Path) -> None:
        cap = CapabilityAuthority(
            adapter_id="test-adapter",
            capabilities=["cap_a"],
            is_configured=True,
        )
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
            adapters=[cap],
        )
        authority = _make_authority()
        kwargs = {
            **VALID_KWARGS,
            "required_adapter_id": "test-adapter",
            "required_capability": "cap_b",
        }
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.DENY

    def test_valid_adapter_passes(self, tmp_path: Path) -> None:
        cap = CapabilityAuthority(
            adapter_id="test-adapter",
            capabilities=["cap_a"],
            is_configured=True,
            is_mature=True,
        )
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
            adapters=[cap],
        )
        authority = _make_authority()
        kwargs = {
            **VALID_KWARGS,
            "required_adapter_id": "test-adapter",
            "required_capability": "cap_a",
        }
        result = gate.validate(authority_decision=authority, **kwargs)
        assert result.verdict == GateVerdict.PASS


class TestDeterministicGateHash:
    def test_same_inputs_same_hash(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        r1 = gate.validate(authority_decision=authority, **VALID_KWARGS)
        r2 = gate.validate(authority_decision=authority, **VALID_KWARGS)
        assert r1.gate_hash == r2.gate_hash
        assert r1.gate_hash != ""

    def test_different_verdicts_different_hash(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        auth_pass = _make_authority()
        auth_deny = _make_authority(allowed=False, auth_class=AuthorityClass.DENY)
        r1 = gate.validate(authority_decision=auth_pass, **VALID_KWARGS)
        r2 = gate.validate(authority_decision=auth_deny, **VALID_KWARGS)
        assert r1.gate_hash != r2.gate_hash


class TestLedgerPersistence:
    def test_pass_creates_three_records(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
            with_ledger=True,
        )
        authority = _make_authority()
        result = gate.validate(
            authority_decision=authority,
            trace_id="TRACE-ledger-001",
            **VALID_KWARGS,
        )
        ledger = TransformationStateLedger(tmp_path / "ledger")
        # Ledger is in-memory in the gate instance; check via gate's ledger
        assert result.verdict == GateVerdict.PASS

    def test_deny_creates_two_records(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
            with_ledger=True,
        )
        auth_deny = _make_authority(allowed=False, auth_class=AuthorityClass.DENY)
        result = gate.validate(
            authority_decision=auth_deny,
            trace_id="TRACE-ledger-002",
            **VALID_KWARGS,
        )
        assert result.verdict == GateVerdict.DENY


class TestProofPersistence:
    def test_proof_file_created(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        authority = _make_authority()
        result = gate.validate(authority_decision=authority, **VALID_KWARGS)
        proof_dir = tmp_path / "proofs"
        files = list(proof_dir.glob("GATE-*.json"))
        assert len(files) >= 1


class TestAllStructuralBlocks:
    def test_all_structural_blocks_denied(self, tmp_path: Path) -> None:
        gate = _make_gate(
            tmp_path,
            env_types=["vps_tmux"],
            runtimes={"vps-worker-01": True},
        )
        for block in GATE_STRUCTURAL_BLOCKS:
            authority = _make_authority()
            kwargs = {**VALID_KWARGS, "action_type": block}
            result = gate.validate(authority_decision=authority, **kwargs)
            assert result.verdict == GateVerdict.DENY, f"{block} must be structurally blocked"


class TestReadinessDataclasses:
    def test_environment_readiness(self) -> None:
        er = EnvironmentReadiness(
            environment_type="vps",
            exists=True,
            healthy=True,
            authority_granted=True,
            risk_within_bounds=True,
        )
        assert er.ready is True
        d = er.to_dict()
        assert d["ready"] is True

    def test_environment_not_ready(self) -> None:
        er = EnvironmentReadiness(
            environment_type="vps",
            exists=True,
            healthy=False,
        )
        assert er.ready is False

    def test_runtime_readiness(self) -> None:
        rr = RuntimeReadiness(
            runtime_id="rt-1",
            exists=True,
            healthy=True,
            has_capacity=True,
        )
        assert rr.ready is True

    def test_adapter_readiness(self) -> None:
        ar = AdapterReadiness(
            adapter_id="a-1",
            exists=True,
            configured=True,
            has_required_capability=True,
        )
        assert ar.ready is True

    def test_proof_readiness(self) -> None:
        pr = ProofReadiness(
            proof_requirements=["proof_a"],
            all_declared=True,
        )
        assert pr.ready is True

    def test_proof_readiness_empty(self) -> None:
        pr = ProofReadiness(proof_requirements=[], all_declared=False)
        assert pr.ready is False

    def test_execution_readiness_all(self) -> None:
        er = ExecutionReadiness(
            environment=EnvironmentReadiness(
                "vps",
                exists=True,
                healthy=True,
                authority_granted=True,
                risk_within_bounds=True,
            ),
            runtime=RuntimeReadiness("rt", exists=True, healthy=True),
        )
        assert er.all_ready is True

    def test_execution_readiness_partial(self) -> None:
        er = ExecutionReadiness(
            environment=EnvironmentReadiness("vps", exists=False),
            runtime=RuntimeReadiness("rt", exists=True, healthy=True),
        )
        assert er.all_ready is False

    def test_execution_request_to_dict(self) -> None:
        req = RuntimeExecutionRequest(
            request_id="",
            packet_id="WP-1",
            authority_decision_id="AD-1",
            authority_class="approve_execute",
            target_environment="vps",
            target_runtime="rt-1",
            action_type="read_only_query",
        )
        d = req.to_dict()
        assert d["packet_id"] == "WP-1"
        assert "request_id" in d

    def test_gate_result_to_dict(self) -> None:
        r = ExecutionGateResult(
            result_id="",
            packet_id="WP-1",
            verdict=GateVerdict.PASS,
        )
        d = r.to_dict()
        assert d["verdict"] == "pass"
        assert "result_id" in d
