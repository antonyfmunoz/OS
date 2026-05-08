"""Tests for Execution Authority Engine v1.

Phase 96.8AC — execution authority validation.
"""

import sys

sys.path.insert(0, "/opt/OS")

import json
import tempfile
from pathlib import Path

import pytest

from core.governance.execution_authority_engine_v1 import (
    AUTHORITY_CLASS_RANK,
    DEFAULT_DENY_ACTIONS,
    GUI_REQUIRING_ACTIONS,
    READ_ONLY_ACTIONS,
    SAFE_INGESTION_ACTIONS,
    STRUCTURALLY_DENIED_ACTIONS,
    ApprovalRequirement,
    AuthorityClass,
    AuthorityDecision,
    AuthorityProof,
    CapabilityAuthority,
    EnvironmentAuthority,
    ExecutionAuthorityEngine,
    ExecutionAuthorityRequest,
    RiskClass,
)


def _make_engine(
    env_auths: list[EnvironmentAuthority] | None = None,
    cap_auths: list[CapabilityAuthority] | None = None,
    overrides: dict[str, AuthorityClass] | None = None,
    proof_dir: Path | None = None,
) -> ExecutionAuthorityEngine:
    return ExecutionAuthorityEngine(
        environment_authorities=env_auths,
        capability_authorities=cap_auths,
        configured_overrides=overrides,
        proof_dir=proof_dir,
    )


def _make_request(
    action_type: str = "read_only_query",
    description: str = "test action",
    **kwargs: object,
) -> ExecutionAuthorityRequest:
    return ExecutionAuthorityRequest(
        request_id="",
        action_type=action_type,
        action_description=description,
        **kwargs,  # type: ignore[arg-type]
    )


class TestReadOnlyAuthority:
    def test_read_only_query_allowed(self) -> None:
        engine = _make_engine()
        request = _make_request("read_only_query", "query metadata")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.READ_ONLY
        assert decision.workpacket_allowed is True
        assert decision.risk_class == RiskClass.NEGLIGIBLE
        assert decision.approval_requirement == ApprovalRequirement.NONE

    def test_metadata_read_allowed(self) -> None:
        engine = _make_engine()
        request = _make_request("metadata_read", "read file metadata")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.READ_ONLY
        assert decision.workpacket_allowed is True

    def test_status_check_allowed(self) -> None:
        engine = _make_engine()
        request = _make_request("status_check", "check worker status")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.READ_ONLY

    def test_all_read_only_actions(self) -> None:
        engine = _make_engine()
        for action in READ_ONLY_ACTIONS:
            request = _make_request(action, f"test {action}")
            decision = engine.evaluate(request)
            assert decision.authority_class == AuthorityClass.READ_ONLY, (
                f"{action} should be read_only"
            )


class TestSafeIngestionAuthority:
    def test_safe_doc_extraction_approved(self) -> None:
        engine = _make_engine()
        request = _make_request("safe_doc_extraction", "extract safe doc")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.APPROVE_EXECUTE
        assert decision.workpacket_allowed is True
        assert decision.risk_class == RiskClass.LOW

    def test_ingestion_candidate_creation(self) -> None:
        engine = _make_engine()
        request = _make_request("ingestion_candidate_creation", "create candidate")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.APPROVE_EXECUTE
        assert decision.workpacket_allowed is True

    def test_safe_ingestion_with_adapter(self) -> None:
        cap = CapabilityAuthority(
            adapter_id="google-docs-adapter-v1",
            capabilities=["GOOGLE_DOCS_SAFE_EXTRACT"],
            is_configured=True,
            is_mature=True,
        )
        engine = _make_engine(cap_auths=[cap])
        request = _make_request(
            "safe_doc_extraction",
            "extract via docs adapter",
            required_adapter_id="google-docs-adapter-v1",
            required_capability="GOOGLE_DOCS_SAFE_EXTRACT",
        )
        decision = engine.evaluate(request)
        assert decision.workpacket_allowed is True
        assert decision.capability_authority_met is True


class TestGUIExecutionAuthority:
    def test_gui_requires_environment(self) -> None:
        engine = _make_engine()
        request = _make_request("browser_execution", "launch chrome")
        decision = engine.evaluate(request)
        assert decision.workpacket_allowed is False
        assert "gui_action_requires_environment_specification" in decision.denial_reasons

    def test_gui_with_environment_authority(self) -> None:
        env = EnvironmentAuthority(
            environment_type="local_windows_desktop",
            can_own_gui=True,
            can_execute_browser=True,
            max_risk_class=RiskClass.MEDIUM,
        )
        engine = _make_engine(env_auths=[env])
        request = _make_request(
            "browser_execution",
            "launch chrome",
            required_environment_type="local_windows_desktop",
        )
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.SUPERVISED_EXECUTE
        assert decision.workpacket_allowed is True
        assert decision.approval_requirement == ApprovalRequirement.FOUNDER_APPROVAL
        assert decision.environment_authority_met is True

    def test_gui_without_gui_capability(self) -> None:
        env = EnvironmentAuthority(
            environment_type="vps_tmux",
            can_own_gui=False,
            can_execute_browser=False,
            max_risk_class=RiskClass.LOW,
        )
        engine = _make_engine(env_auths=[env])
        request = _make_request(
            "browser_execution",
            "launch chrome on VPS",
            required_environment_type="vps_tmux",
        )
        decision = engine.evaluate(request)
        assert decision.workpacket_allowed is False
        assert any("gui_authority" in r for r in decision.denial_reasons)

    def test_all_gui_actions_require_environment(self) -> None:
        engine = _make_engine()
        for action in GUI_REQUIRING_ACTIONS:
            request = _make_request(action, f"test {action}")
            decision = engine.evaluate(request)
            assert decision.workpacket_allowed is False, f"{action} should require environment"


class TestFinancialDenial:
    def test_financial_execution_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("financial_execution", "process payment")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY
        assert decision.workpacket_allowed is False
        assert decision.risk_class == RiskClass.FORBIDDEN

    def test_wallet_execution_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("wallet_execution", "use wallet")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY
        assert decision.workpacket_allowed is False

    def test_trade_placement_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("trade_placement", "place trade")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY
        assert decision.workpacket_allowed is False

    def test_money_allocation_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("money_allocation", "allocate funds")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY

    def test_payment_processing_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("payment_processing", "process payment")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY

    def test_all_financial_actions_structurally_denied(self) -> None:
        engine = _make_engine()
        financial_actions = [
            "wallet_execution",
            "financial_execution",
            "trade_placement",
            "money_allocation",
            "payment_processing",
        ]
        for action in financial_actions:
            request = _make_request(action, f"test {action}")
            decision = engine.evaluate(request)
            assert decision.authority_class == AuthorityClass.DENY, f"{action} must be denied"
            assert decision.workpacket_allowed is False, f"{action} workpacket must be blocked"


class TestCredentialDenial:
    def test_credential_access_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("credential_access", "access credentials")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY
        assert decision.workpacket_allowed is False

    def test_token_extraction_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("token_extraction", "extract tokens")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY

    def test_key_extraction_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("key_extraction", "extract API keys")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY


class TestRecursiveAutonomyDenial:
    def test_recursive_execution_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("autonomous_recursive_execution", "self-replicate")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY
        assert decision.workpacket_allowed is False

    def test_high_recursive_risk_denied(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "some_action",
            "action with recursive risk",
            recursive_autonomy_risk=0.5,
        )
        decision = engine.evaluate(request)
        assert decision.risk_class == RiskClass.CRITICAL


class TestMissingAuthority:
    def test_missing_environment_blocks(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "browser_execution",
            "launch chrome",
            required_environment_type="nonexistent_env",
        )
        decision = engine.evaluate(request)
        assert decision.workpacket_allowed is False
        assert any("missing_environment" in r for r in decision.denial_reasons)

    def test_missing_adapter_blocks(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "safe_doc_extraction",
            "extract doc",
            required_adapter_id="nonexistent-adapter",
        )
        decision = engine.evaluate(request)
        assert decision.workpacket_allowed is False
        assert any("missing_capability" in r for r in decision.denial_reasons)

    def test_unconfigured_adapter_blocks(self) -> None:
        cap = CapabilityAuthority(
            adapter_id="test-adapter",
            capabilities=["some_cap"],
            is_configured=False,
        )
        engine = _make_engine(cap_auths=[cap])
        request = _make_request(
            "safe_doc_extraction",
            "extract",
            required_adapter_id="test-adapter",
        )
        decision = engine.evaluate(request)
        assert decision.workpacket_allowed is False
        assert any("not_configured" in r for r in decision.denial_reasons)

    def test_adapter_lacks_required_capability(self) -> None:
        cap = CapabilityAuthority(
            adapter_id="test-adapter",
            capabilities=["cap_a"],
            is_configured=True,
        )
        engine = _make_engine(cap_auths=[cap])
        request = _make_request(
            "safe_doc_extraction",
            "extract",
            required_adapter_id="test-adapter",
            required_capability="cap_b",
        )
        decision = engine.evaluate(request)
        assert decision.workpacket_allowed is False
        assert any("lacks_capability" in r for r in decision.denial_reasons)


class TestProofRequirements:
    def test_proof_requirements_recorded(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "safe_doc_extraction",
            "extract with proof",
            proof_requirements=["adapter_maturity_proof", "environment_proof"],
        )
        decision = engine.evaluate(request)
        assert "adapter_maturity_proof" in decision.required_proofs
        assert "environment_proof" in decision.required_proofs

    def test_proof_creation(self, tmp_path: Path) -> None:
        engine = _make_engine(proof_dir=tmp_path)
        request = _make_request("read_only_query", "test")
        decision = engine.evaluate(request)
        proof = engine.create_proof(decision)
        assert proof.proof_id.startswith("AUTH-PROOF-")
        assert proof.decision_hash == decision.decision_hash
        proof_files = list(tmp_path.glob("AUTH-PROOF-*.json"))
        assert len(proof_files) == 1


class TestConfidenceThreshold:
    def test_low_confidence_blocked(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "safe_doc_extraction",
            "low confidence extraction",
            confidence=0.3,
        )
        decision = engine.evaluate(request)
        assert decision.workpacket_allowed is False
        assert any("confidence_below_threshold" in r for r in decision.denial_reasons)

    def test_high_confidence_passes(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "safe_doc_extraction",
            "high confidence extraction",
            confidence=0.9,
        )
        decision = engine.evaluate(request)
        assert decision.confidence_met is True
        assert decision.workpacket_allowed is True


class TestDeterministicDecisionHash:
    def test_same_inputs_same_hash(self) -> None:
        engine = _make_engine()
        request1 = _make_request("read_only_query", "query A")
        request1.request_id = "REQ-001"
        request2 = _make_request("read_only_query", "query A")
        request2.request_id = "REQ-001"
        d1 = engine.evaluate(request1)
        d2 = engine.evaluate(request2)
        assert d1.decision_hash == d2.decision_hash
        assert d1.decision_hash != ""

    def test_different_inputs_different_hash(self) -> None:
        engine = _make_engine()
        r1 = _make_request("read_only_query", "query A")
        r1.request_id = "REQ-001"
        r2 = _make_request("safe_doc_extraction", "extract B")
        r2.request_id = "REQ-002"
        d1 = engine.evaluate(r1)
        d2 = engine.evaluate(r2)
        assert d1.decision_hash != d2.decision_hash


class TestRiskClassification:
    def test_high_financial_risk(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "some_action",
            "high financial",
            financial_risk=0.8,
        )
        decision = engine.evaluate(request)
        assert decision.risk_class == RiskClass.CRITICAL

    def test_high_credential_risk(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "some_action",
            "high cred risk",
            credential_risk=0.7,
        )
        decision = engine.evaluate(request)
        assert decision.risk_class == RiskClass.CRITICAL

    def test_external_mutation_high_risk(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "some_action",
            "external mutation",
            external_mutation=True,
        )
        decision = engine.evaluate(request)
        assert decision.risk_class == RiskClass.HIGH

    def test_irreversible_high_risk(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "some_action",
            "irreversible",
            reversibility="irreversible",
        )
        decision = engine.evaluate(request)
        assert decision.risk_class == RiskClass.HIGH

    def test_high_cost_high_risk(self) -> None:
        engine = _make_engine()
        request = _make_request(
            "some_action",
            "expensive",
            estimated_cost=500.0,
        )
        decision = engine.evaluate(request)
        assert decision.risk_class == RiskClass.HIGH


class TestEnvironmentRiskBounds:
    def test_environment_rejects_high_risk(self) -> None:
        env = EnvironmentAuthority(
            environment_type="restricted_env",
            can_own_gui=True,
            can_execute_browser=True,
            max_risk_class=RiskClass.LOW,
        )
        engine = _make_engine(env_auths=[env])
        request = _make_request(
            "browser_execution",
            "risky gui action",
            required_environment_type="restricted_env",
        )
        decision = engine.evaluate(request)
        assert decision.workpacket_allowed is False
        assert any("risk_exceeds" in r for r in decision.denial_reasons)


class TestAuthorityClassRanking:
    def test_deny_is_lowest(self) -> None:
        assert AUTHORITY_CLASS_RANK[AuthorityClass.DENY] == 0

    def test_autonomous_is_highest(self) -> None:
        assert AUTHORITY_CLASS_RANK[AuthorityClass.AUTONOMOUS_EXECUTE] == 6

    def test_supervised_higher_than_approve(self) -> None:
        assert (
            AUTHORITY_CLASS_RANK[AuthorityClass.SUPERVISED_EXECUTE]
            > AUTHORITY_CLASS_RANK[AuthorityClass.APPROVE_EXECUTE]
        )


class TestPlanningCandidateIntegration:
    def test_evaluate_from_plan(self) -> None:
        engine = _make_engine()
        decision = engine.evaluate_planning_candidate(
            plan_id="EPLAN-abc",
            plan_hash="hash123",
            action_type="read_only_query",
            action_description="query from plan",
            trace_id="T1",
        )
        assert decision.authority_class == AuthorityClass.READ_ONLY
        assert decision.workpacket_allowed is True

    def test_plan_financial_denied(self) -> None:
        engine = _make_engine()
        decision = engine.evaluate_planning_candidate(
            plan_id="EPLAN-abc",
            plan_hash="hash123",
            action_type="financial_execution",
            action_description="pay from plan",
        )
        assert decision.authority_class == AuthorityClass.DENY
        assert decision.workpacket_allowed is False

    def test_plan_with_risk_envelope(self) -> None:
        engine = _make_engine()
        decision = engine.evaluate_planning_candidate(
            plan_id="EPLAN-abc",
            plan_hash="hash123",
            action_type="safe_doc_extraction",
            action_description="extract from plan",
            risk_envelope={"financial_risk": 0.0, "credential_risk": 0.0},
        )
        assert decision.workpacket_allowed is True


class TestDestructiveOperations:
    def test_destructive_file_ops_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("destructive_file_operation", "rm -rf")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY

    def test_database_drop_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("database_drop", "DROP TABLE")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY

    def test_production_deployment_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("production_deployment", "deploy to prod")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY

    def test_permission_escalation_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("permission_escalation", "escalate perms")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY

    def test_broad_drive_ingestion_denied(self) -> None:
        engine = _make_engine()
        request = _make_request("broad_drive_ingestion", "ingest all drive")
        decision = engine.evaluate(request)
        assert decision.authority_class == AuthorityClass.DENY


class TestDataclassSerialization:
    def test_environment_authority_to_dict(self) -> None:
        env = EnvironmentAuthority(
            environment_type="test",
            can_own_gui=True,
            max_risk_class=RiskClass.MEDIUM,
        )
        d = env.to_dict()
        assert d["environment_type"] == "test"
        assert d["can_own_gui"] is True
        assert d["max_risk_class"] == "medium"

    def test_capability_authority_to_dict(self) -> None:
        cap = CapabilityAuthority(
            adapter_id="test-adapter",
            capabilities=["cap_a", "cap_b"],
            is_configured=True,
        )
        d = cap.to_dict()
        assert d["adapter_id"] == "test-adapter"
        assert "cap_a" in d["capabilities"]

    def test_request_to_dict(self) -> None:
        req = _make_request("read_only_query", "test")
        d = req.to_dict()
        assert d["action_type"] == "read_only_query"
        assert "request_id" in d
        assert "timestamp" in d

    def test_decision_to_dict(self) -> None:
        engine = _make_engine()
        request = _make_request("read_only_query", "test")
        decision = engine.evaluate(request)
        d = decision.to_dict()
        assert d["authority_class"] == "read_only"
        assert "decision_hash" in d

    def test_proof_to_dict(self, tmp_path: Path) -> None:
        engine = _make_engine(proof_dir=tmp_path)
        request = _make_request("read_only_query", "test")
        decision = engine.evaluate(request)
        proof = engine.create_proof(decision)
        d = proof.to_dict()
        assert d["authority_class"] == "read_only"
        assert d["workpacket_allowed"] is True
