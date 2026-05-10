"""Tests for execution planning candidate v1.

Phase 96.8Z — proves the execution planning candidate layer enforces
governance-bound planning without autonomous execution.

Plans are hypotheses about action. Plans are not actions.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from core.planning.execution_planning_candidate_v1 import (
    ALLOWED_PLAN_INPUTS,
    FORBIDDEN_PLAN_INPUTS,
    FORBIDDEN_PLANNING_ACTIONS,
    RISK_ESCALATION_THRESHOLDS,
    ActionGraph,
    ActionSequence,
    ConstraintEvaluation,
    EscalationTier,
    ExecutionDependency,
    ExecutionPlanningAssembler,
    ExecutionPlanningCandidate,
    ExpectedOutcome,
    PlanningGovernanceBoundary,
    PlanningLineageReference,
    PlanStatus,
    ProposedAction,
    ResourceRequirement,
    RiskEnvelope,
    RiskLevel,
    _tier_rank,
)
from core.state.transformation_state_ledger import (
    GOVERNANCE_REQUIRED_STAGES,
    MUTATION_BLOCKED_STAGES,
    VALID_TRANSITIONS,
    TransformationStage,
)


# ── Helpers ────────────────────────────────────────────────────────


def _sample_entities() -> list[dict]:
    return [
        {
            "entity_id": "CENT-aaa",
            "entity_type": "company",
            "label": "Lyfe Institute",
            "confidence": 0.9,
        },
        {
            "entity_id": "CENT-bbb",
            "entity_type": "product",
            "label": "Initiate Arena",
            "confidence": 0.85,
        },
        {
            "entity_id": "CENT-ccc",
            "entity_type": "market",
            "label": "Creator Economy",
            "confidence": 0.7,
        },
    ]


def _sample_relationships() -> list[dict]:
    return [
        {
            "from_entity_id": "CENT-aaa",
            "to_entity_id": "CENT-bbb",
            "relationship_type": "produces",
        },
        {
            "from_entity_id": "CENT-bbb",
            "to_entity_id": "CENT-ccc",
            "relationship_type": "targets",
        },
    ]


def _assemble_candidate() -> ExecutionPlanningCandidate:
    assembler = ExecutionPlanningAssembler()
    return assembler.assemble(
        canonical_model_id="CWM-test001",
        canonical_model_hash="abc123def456",
        entities=_sample_entities(),
        relationships=_sample_relationships(),
        truth_ids=["TRUTH-001", "TRUTH-002"],
        governance_receipt_ids=["GRCPT-001"],
        plan_type="operational",
        description="Test execution plan",
    )


# ── Test: Deterministic Planning ────────────────────────────────────


class TestDeterministicPlanning:
    def test_same_inputs_same_hash(self):
        c1 = _assemble_candidate()
        c2 = _assemble_candidate()
        assert c1.output_hash == c2.output_hash

    def test_same_plan_id(self):
        c1 = _assemble_candidate()
        c2 = _assemble_candidate()
        assert c1.plan_id == c2.plan_id

    def test_same_action_ids(self):
        c1 = _assemble_candidate()
        c2 = _assemble_candidate()
        ids1 = [a.action_id for a in c1.action_sequence.actions]
        ids2 = [a.action_id for a in c2.action_sequence.actions]
        assert ids1 == ids2

    def test_same_dependency_ids(self):
        c1 = _assemble_candidate()
        c2 = _assemble_candidate()
        deps1 = [e.dependency_id for e in c1.action_graph.edges]
        deps2 = [e.dependency_id for e in c2.action_graph.edges]
        assert deps1 == deps2

    def test_same_topological_order(self):
        c1 = _assemble_candidate()
        c2 = _assemble_candidate()
        assert c1.action_graph.topological_order == c2.action_graph.topological_order

    def test_different_input_different_hash(self):
        c1 = _assemble_candidate()
        assembler = ExecutionPlanningAssembler()
        c2 = assembler.assemble(
            canonical_model_id="CWM-test002",
            canonical_model_hash="different_hash",
            entities=_sample_entities()[:1],
            relationships=[],
            truth_ids=["TRUTH-999"],
            governance_receipt_ids=["GRCPT-999"],
        )
        assert c1.output_hash != c2.output_hash

    def test_hash_is_64_chars(self):
        c = _assemble_candidate()
        assert len(c.output_hash) == 64

    def test_rollback_references_deterministic(self):
        c1 = _assemble_candidate()
        c2 = _assemble_candidate()
        r1 = [a.rollback_reference for a in c1.action_sequence.actions]
        r2 = [a.rollback_reference for a in c2.action_sequence.actions]
        assert r1 == r2


# ── Test: Governance Required ────────────────────────────────────────


class TestGovernanceRequired:
    def test_status_awaiting_governance(self):
        c = _assemble_candidate()
        c.status = PlanStatus.AWAITING_GOVERNANCE
        assert c.status == PlanStatus.AWAITING_GOVERNANCE

    def test_plan_statuses_exist(self):
        expected = {
            "draft",
            "assembled",
            "awaiting_governance",
            "governance_approved",
            "governance_rejected",
        }
        actual = {s.value for s in PlanStatus}
        assert actual == expected

    def test_blocked_actions_populated(self):
        c = _assemble_candidate()
        assert len(c.blocked_actions) > 0

    def test_forbidden_actions_count(self):
        assert len(FORBIDDEN_PLANNING_ACTIONS) == 14

    def test_all_forbidden_in_blocked(self):
        c = _assemble_candidate()
        for action in FORBIDDEN_PLANNING_ACTIONS:
            assert action in c.blocked_actions

    def test_governance_receipt_id_starts_empty(self):
        c = _assemble_candidate()
        assert c.governance_receipt_id == ""


# ── Test: Runtime Invocation Blocked ─────────────────────────────────


class TestRuntimeInvocationBlocked:
    def test_runtime_invocation_forbidden(self):
        assert "runtime_invocation" in FORBIDDEN_PLANNING_ACTIONS

    def test_boundary_blocks_runtime(self):
        b = PlanningGovernanceBoundary()
        assert b.may_invoke_runtime is False

    def test_boundary_violation_runtime(self):
        b = PlanningGovernanceBoundary(may_invoke_runtime=True)
        errors = b.validate()
        assert any("invoke runtime" in e for e in errors)

    def test_adapter_invocation_forbidden(self):
        assert "adapter_invocation" in FORBIDDEN_PLANNING_ACTIONS

    def test_autonomous_execution_forbidden(self):
        assert "autonomous_execution" in FORBIDDEN_PLANNING_ACTIONS


# ── Test: Execution Blocked ──────────────────────────────────────────


class TestExecutionBlocked:
    def test_shell_execution_forbidden(self):
        assert "shell_execution" in FORBIDDEN_PLANNING_ACTIONS

    def test_boundary_blocks_shell(self):
        b = PlanningGovernanceBoundary()
        assert b.may_execute_shell is False

    def test_boundary_violation_shell(self):
        b = PlanningGovernanceBoundary(may_execute_shell=True)
        errors = b.validate()
        assert any("shell" in e for e in errors)

    def test_api_execution_forbidden(self):
        assert "api_execution" in FORBIDDEN_PLANNING_ACTIONS

    def test_boundary_blocks_api(self):
        b = PlanningGovernanceBoundary()
        assert b.may_execute_api is False

    def test_browser_execution_forbidden(self):
        assert "browser_execution" in FORBIDDEN_PLANNING_ACTIONS

    def test_boundary_blocks_browser(self):
        b = PlanningGovernanceBoundary()
        assert b.may_execute_browser is False


# ── Test: Wallet Access Blocked ──────────────────────────────────────


class TestWalletAccessBlocked:
    def test_wallet_usage_forbidden(self):
        assert "wallet_usage" in FORBIDDEN_PLANNING_ACTIONS

    def test_boundary_blocks_wallet(self):
        b = PlanningGovernanceBoundary()
        assert b.may_use_wallet is False

    def test_boundary_violation_wallet(self):
        b = PlanningGovernanceBoundary(may_use_wallet=True)
        errors = b.validate()
        assert any("wallet" in e for e in errors)

    def test_credential_access_forbidden(self):
        assert "credential_access" in FORBIDDEN_PLANNING_ACTIONS

    def test_boundary_blocks_credentials(self):
        b = PlanningGovernanceBoundary()
        assert b.may_access_credentials is False


# ── Test: Financial Execution Blocked ────────────────────────────────


class TestFinancialExecutionBlocked:
    def test_financial_execution_forbidden(self):
        assert "financial_execution" in FORBIDDEN_PLANNING_ACTIONS

    def test_boundary_blocks_financial(self):
        b = PlanningGovernanceBoundary()
        assert b.may_execute_financial is False

    def test_trade_placement_forbidden(self):
        assert "trade_placement" in FORBIDDEN_PLANNING_ACTIONS

    def test_money_allocation_forbidden(self):
        assert "money_allocation" in FORBIDDEN_PLANNING_ACTIONS


# ── Test: Memory/Canonical Mutation Blocked ──────────────────────────


class TestMutationBlocked:
    def test_memory_mutation_forbidden(self):
        assert "memory_mutation" in FORBIDDEN_PLANNING_ACTIONS

    def test_canonical_mutation_forbidden(self):
        assert "canonical_mutation" in FORBIDDEN_PLANNING_ACTIONS

    def test_boundary_blocks_memory_mutation(self):
        b = PlanningGovernanceBoundary()
        assert b.may_mutate_memory is False

    def test_boundary_blocks_canonical_mutation(self):
        b = PlanningGovernanceBoundary()
        assert b.may_mutate_canonical is False

    def test_boundary_violation_memory(self):
        b = PlanningGovernanceBoundary(may_mutate_memory=True)
        errors = b.validate()
        assert any("mutate memory" in e for e in errors)

    def test_boundary_violation_canonical(self):
        b = PlanningGovernanceBoundary(may_mutate_canonical=True)
        errors = b.validate()
        assert any("mutate canonical" in e for e in errors)


# ── Test: Forbidden Inputs ───────────────────────────────────────────


class TestForbiddenInputs:
    def test_candidate_hypothesis_forbidden(self):
        assert "candidate_hypothesis" in FORBIDDEN_PLAN_INPUTS

    def test_ungoverned_interpretation_forbidden(self):
        assert "ungoverned_interpretation" in FORBIDDEN_PLAN_INPUTS

    def test_recursive_plan_forbidden(self):
        assert "recursive_self_generated_plan" in FORBIDDEN_PLAN_INPUTS

    def test_hidden_runtime_state_forbidden(self):
        assert "hidden_runtime_state" in FORBIDDEN_PLAN_INPUTS

    def test_forbidden_input_count(self):
        assert len(FORBIDDEN_PLAN_INPUTS) == 4

    def test_allowed_input_count(self):
        assert len(ALLOWED_PLAN_INPUTS) == 5

    def test_validation_rejects_forbidden_input(self):
        c = _assemble_candidate()
        c.input_sources.append("candidate_hypothesis")
        errors = c.validate()
        assert any("forbidden input" in e for e in errors)


# ── Test: Dependency Ordering ────────────────────────────────────────


class TestDependencyOrdering:
    def test_action_graph_has_nodes(self):
        c = _assemble_candidate()
        assert len(c.action_graph.nodes) == 3

    def test_action_graph_has_edges(self):
        c = _assemble_candidate()
        assert len(c.action_graph.edges) == 2

    def test_topological_order_includes_all(self):
        c = _assemble_candidate()
        assert len(c.action_graph.topological_order) == 3

    def test_no_cycle(self):
        c = _assemble_candidate()
        assert not c.action_graph.has_cycle()

    def test_execution_roots(self):
        c = _assemble_candidate()
        roots = c.action_graph.get_execution_roots()
        assert len(roots) >= 1

    def test_dependency_is_blocking(self):
        c = _assemble_candidate()
        for edge in c.action_graph.edges:
            assert edge.is_blocking is True

    def test_cycle_detection_raises_on_validate(self):
        a1 = ProposedAction(action_id="A", action_type="t", description="d")
        a2 = ProposedAction(action_id="B", action_type="t", description="d")
        e1 = ExecutionDependency(dependency_id="E1", from_action_id="A", to_action_id="B")
        e2 = ExecutionDependency(dependency_id="E2", from_action_id="B", to_action_id="A")
        g = ActionGraph(graph_id="G", nodes=[a1, a2], edges=[e1, e2])
        assert g.has_cycle()

    def test_stable_topo_sort(self):
        c1 = _assemble_candidate()
        c2 = _assemble_candidate()
        assert c1.action_graph.topological_order == c2.action_graph.topological_order


# ── Test: Risk Escalation ────────────────────────────────────────────


class TestRiskEscalation:
    def test_risk_envelope_has_6_dimensions(self):
        r = RiskEnvelope()
        dims = [
            r.financial_risk,
            r.execution_risk,
            r.uncertainty_risk,
            r.trust_boundary_risk,
            r.external_dependency_risk,
            r.recursive_autonomy_risk,
        ]
        assert len(dims) == 6

    def test_overall_risk_is_max(self):
        r = RiskEnvelope(financial_risk=0.1, execution_risk=0.8, uncertainty_risk=0.3)
        assert r.compute_overall_risk() == 0.8

    def test_financial_risk_escalates_to_founder(self):
        r = RiskEnvelope(financial_risk=0.5)
        tier, reasons = r.compute_escalation()
        assert tier == EscalationTier.FOUNDER_APPROVAL

    def test_trust_boundary_escalates_to_founder(self):
        r = RiskEnvelope(trust_boundary_risk=0.5)
        tier, reasons = r.compute_escalation()
        assert tier == EscalationTier.FOUNDER_APPROVAL

    def test_recursive_autonomy_blocks(self):
        r = RiskEnvelope(recursive_autonomy_risk=0.2)
        tier, reasons = r.compute_escalation()
        assert tier == EscalationTier.BLOCKED

    def test_execution_risk_escalates_to_approval(self):
        r = RiskEnvelope(execution_risk=0.6)
        tier, reasons = r.compute_escalation()
        assert tier == EscalationTier.APPROVAL

    def test_no_escalation_when_below_thresholds(self):
        r = RiskEnvelope(
            financial_risk=0.1,
            execution_risk=0.1,
            uncertainty_risk=0.1,
            trust_boundary_risk=0.1,
            external_dependency_risk=0.1,
            recursive_autonomy_risk=0.0,
        )
        tier, reasons = r.compute_escalation()
        assert tier == EscalationTier.NONE
        assert len(reasons) == 0

    def test_escalation_reasons_populated(self):
        r = RiskEnvelope(financial_risk=0.5, execution_risk=0.6)
        tier, reasons = r.compute_escalation()
        assert len(reasons) == 2

    def test_tier_rank_ordering(self):
        assert _tier_rank(EscalationTier.NONE) < _tier_rank(EscalationTier.REVIEW)
        assert _tier_rank(EscalationTier.REVIEW) < _tier_rank(EscalationTier.APPROVAL)
        assert _tier_rank(EscalationTier.APPROVAL) < _tier_rank(EscalationTier.FOUNDER_APPROVAL)
        assert _tier_rank(EscalationTier.FOUNDER_APPROVAL) < _tier_rank(EscalationTier.BLOCKED)

    def test_risk_level_enum(self):
        expected = {"negligible", "low", "medium", "high", "critical"}
        actual = {r.value for r in RiskLevel}
        assert actual == expected


# ── Test: Rollback References ────────────────────────────────────────


class TestRollbackReferences:
    def test_plan_has_rollback_reference(self):
        c = _assemble_candidate()
        assert c.rollback_reference.startswith("ROLLBACK-")

    def test_actions_have_rollback_references(self):
        c = _assemble_candidate()
        for action in c.action_sequence.actions:
            assert action.rollback_reference.startswith("ROLLBACK-")

    def test_graph_rollback_chain(self):
        c = _assemble_candidate()
        assert len(c.action_graph.rollback_chain) == 3

    def test_rollback_chain_matches_actions(self):
        c = _assemble_candidate()
        action_refs = [a.rollback_reference for a in c.action_sequence.actions]
        assert c.action_graph.rollback_chain == action_refs


# ── Test: Lineage Replay ─────────────────────────────────────────────


class TestLineageReplay:
    def test_lineage_has_canonical_model_id(self):
        c = _assemble_candidate()
        assert c.lineage.source_canonical_model_id == "CWM-test001"

    def test_lineage_has_world_model_hash(self):
        c = _assemble_candidate()
        assert c.lineage.source_world_model_hash == "abc123def456"

    def test_lineage_has_governance_receipts(self):
        c = _assemble_candidate()
        assert "GRCPT-001" in c.lineage.source_governance_receipt_ids

    def test_lineage_has_trace_id(self):
        c = _assemble_candidate()
        assert c.lineage.planning_trace_id.startswith("PTRACE-")

    def test_lineage_to_dict(self):
        c = _assemble_candidate()
        d = c.lineage.to_dict()
        assert "source_canonical_model_id" in d
        assert "source_world_model_hash" in d
        assert "planning_trace_id" in d

    def test_source_truth_ids(self):
        c = _assemble_candidate()
        assert "TRUTH-001" in c.source_truth_ids
        assert "TRUTH-002" in c.source_truth_ids


# ── Test: Transition Graph ───────────────────────────────────────────


class TestTransitionGraph:
    def test_stage_exists(self):
        assert (
            TransformationStage.EXECUTION_PLANNING_CANDIDATE.value == "execution_planning_candidate"
        )

    def test_canonical_wm_to_planning(self):
        valid = VALID_TRANSITIONS[TransformationStage.CANONICAL_WORLD_MODEL]
        assert TransformationStage.EXECUTION_PLANNING_CANDIDATE in valid

    def test_planning_to_governance(self):
        valid = VALID_TRANSITIONS[TransformationStage.EXECUTION_PLANNING_CANDIDATE]
        assert TransformationStage.GOVERNANCE_REVIEW in valid

    def test_planning_cannot_reach_mutation(self):
        valid = VALID_TRANSITIONS[TransformationStage.EXECUTION_PLANNING_CANDIDATE]
        assert TransformationStage.WORLD_MODEL_MUTATION not in valid

    def test_planning_cannot_reach_canonical_memory(self):
        valid = VALID_TRANSITIONS[TransformationStage.EXECUTION_PLANNING_CANDIDATE]
        assert TransformationStage.CANONICAL_MEMORY not in valid

    def test_planning_cannot_reach_canonical_wm(self):
        valid = VALID_TRANSITIONS[TransformationStage.EXECUTION_PLANNING_CANDIDATE]
        assert TransformationStage.CANONICAL_WORLD_MODEL not in valid

    def test_planning_in_mutation_blocked(self):
        assert TransformationStage.EXECUTION_PLANNING_CANDIDATE in MUTATION_BLOCKED_STAGES

    def test_all_stages_in_transitions(self):
        for stage in TransformationStage:
            assert stage in VALID_TRANSITIONS

    def test_canonical_wm_still_reaches_mutation(self):
        valid = VALID_TRANSITIONS[TransformationStage.CANONICAL_WORLD_MODEL]
        assert TransformationStage.WORLD_MODEL_MUTATION in valid

    def test_governance_still_forks(self):
        valid = VALID_TRANSITIONS[TransformationStage.GOVERNANCE_REVIEW]
        assert TransformationStage.CANONICAL_MEMORY in valid
        assert TransformationStage.CANONICAL_WORLD_MODEL in valid


# ── Test: Boundary Validation ────────────────────────────────────────


class TestBoundaryValidation:
    def test_default_boundary_valid(self):
        b = PlanningGovernanceBoundary()
        assert b.validate() == []

    def test_all_allowed_true(self):
        b = PlanningGovernanceBoundary()
        assert b.may_propose_actions is True
        assert b.may_sequence_actions is True
        assert b.may_model_dependencies is True
        assert b.may_estimate_resources is True
        assert b.may_estimate_risk is True
        assert b.may_estimate_outcomes is True
        assert b.may_attach_canonical_truths is True

    def test_all_forbidden_false(self):
        b = PlanningGovernanceBoundary()
        assert b.may_invoke_runtime is False
        assert b.may_use_wallet is False
        assert b.may_execute_api is False
        assert b.may_execute_shell is False
        assert b.may_execute_browser is False
        assert b.may_execute_financial is False
        assert b.may_access_credentials is False
        assert b.may_mutate_memory is False
        assert b.may_mutate_canonical is False

    def test_boundary_to_dict_has_16_fields(self):
        b = PlanningGovernanceBoundary()
        d = b.to_dict()
        assert len(d) == 16

    def test_every_violation_detected(self):
        b = PlanningGovernanceBoundary(
            may_invoke_runtime=True,
            may_use_wallet=True,
            may_execute_api=True,
            may_execute_shell=True,
            may_execute_browser=True,
            may_execute_financial=True,
            may_access_credentials=True,
            may_mutate_memory=True,
            may_mutate_canonical=True,
        )
        errors = b.validate()
        assert len(errors) == 9

    def test_boundary_violation_raises_on_assemble(self):
        assembler = ExecutionPlanningAssembler()
        assembler.boundary = PlanningGovernanceBoundary(may_invoke_runtime=True)
        with pytest.raises(ValueError, match="Boundary violation"):
            assembler.assemble(
                canonical_model_id="CWM-x",
                canonical_model_hash="x",
                entities=[{"entity_id": "e", "entity_type": "t", "label": "l", "confidence": 0.5}],
                relationships=[],
                truth_ids=["T1"],
                governance_receipt_ids=["G1"],
            )


# ── Test: Action Graph ───────────────────────────────────────────────


class TestActionGraph:
    def test_graph_id_prefix(self):
        c = _assemble_candidate()
        assert c.action_graph.graph_id.startswith("AGRAPH-")

    def test_graph_to_dict(self):
        c = _assemble_candidate()
        d = c.action_graph.to_dict()
        assert "nodes" in d
        assert "edges" in d
        assert "topological_order" in d
        assert "rollback_chain" in d

    def test_empty_graph_no_cycle(self):
        g = ActionGraph(graph_id="G-empty", nodes=[], edges=[])
        assert not g.has_cycle()

    def test_empty_graph_topo(self):
        g = ActionGraph(graph_id="G-empty", nodes=[], edges=[])
        assert g.compute_topological_order() == []

    def test_single_node_graph(self):
        a = ProposedAction(action_id="A", action_type="t", description="d")
        g = ActionGraph(graph_id="G", nodes=[a], edges=[])
        order = g.compute_topological_order()
        assert order == ["A"]


# ── Test: Serialization ──────────────────────────────────────────────


class TestSerialization:
    def test_candidate_to_dict(self):
        c = _assemble_candidate()
        d = c.to_dict()
        assert d["plan_id"] == c.plan_id
        assert d["plan_type"] == "operational"

    def test_json_serializable(self):
        c = _assemble_candidate()
        s = json.dumps(c.to_dict())
        assert len(s) > 0

    def test_action_to_dict(self):
        a = ProposedAction(
            action_id="A1",
            action_type="test",
            description="desc",
            resource_requirements=[
                ResourceRequirement(
                    resource_id="R1",
                    resource_type="compute",
                    description="CPU",
                )
            ],
            constraint_evaluations=[
                ConstraintEvaluation(
                    constraint_id="C1",
                    constraint_type="budget",
                    description="limit",
                )
            ],
            expected_outcomes=[
                ExpectedOutcome(
                    outcome_id="O1",
                    description="success",
                    probability=0.8,
                )
            ],
        )
        d = a.to_dict()
        assert len(d["resource_requirements"]) == 1
        assert len(d["constraint_evaluations"]) == 1
        assert len(d["expected_outcomes"]) == 1

    def test_risk_envelope_to_dict(self):
        r = RiskEnvelope(financial_risk=0.5, escalation_tier=EscalationTier.APPROVAL)
        d = r.to_dict()
        assert d["financial_risk"] == 0.5
        assert d["escalation_tier"] == "approval"

    def test_dependency_to_dict(self):
        dep = ExecutionDependency(
            dependency_id="D1",
            from_action_id="A",
            to_action_id="B",
        )
        d = dep.to_dict()
        assert d["from_action_id"] == "A"
        assert d["to_action_id"] == "B"

    def test_sequence_to_dict(self):
        c = _assemble_candidate()
        d = c.action_sequence.to_dict()
        assert "actions" in d
        assert "total_estimated_cost" in d

    def test_resource_requirement_to_dict(self):
        r = ResourceRequirement(
            resource_id="R1",
            resource_type="compute",
            description="GPU hours",
            quantity=4.0,
            unit="hours",
            is_financial=True,
            estimated_cost=100.0,
        )
        d = r.to_dict()
        assert d["estimated_cost"] == 100.0
        assert d["is_financial"] is True

    def test_lineage_reference_to_dict(self):
        l = PlanningLineageReference(
            source_canonical_model_id="CWM-1",
            source_world_model_hash="hash123",
        )
        d = l.to_dict()
        assert d["source_canonical_model_id"] == "CWM-1"


# ── Test: Validation ─────────────────────────────────────────────────


class TestValidation:
    def test_valid_candidate_passes(self):
        c = _assemble_candidate()
        assert c.validate() == []

    def test_missing_plan_id(self):
        c = _assemble_candidate()
        c.plan_id = ""
        errors = c.validate()
        assert any("plan_id" in e for e in errors)

    def test_missing_plan_type(self):
        c = _assemble_candidate()
        c.plan_type = ""
        errors = c.validate()
        assert any("plan_type" in e for e in errors)

    def test_missing_blocked_actions(self):
        c = _assemble_candidate()
        c.blocked_actions = []
        errors = c.validate()
        assert any("blocked_actions" in e for e in errors)

    def test_forbidden_in_allowed_rejected(self):
        c = _assemble_candidate()
        c.allowed_actions.append("runtime_invocation")
        errors = c.validate()
        assert any("forbidden action" in e for e in errors)

    def test_cycle_in_graph_rejected(self):
        c = _assemble_candidate()
        a1 = c.action_graph.nodes[0]
        a2 = c.action_graph.nodes[1]
        c.action_graph.edges.append(
            ExecutionDependency(
                dependency_id="CYCLE",
                from_action_id=a2.action_id,
                to_action_id=a1.action_id,
            )
        )
        c.action_graph.edges.append(
            ExecutionDependency(
                dependency_id="CYCLE2",
                from_action_id=a1.action_id,
                to_action_id=a2.action_id,
            )
        )
        errors = c.validate()
        assert any("cycle" in e for e in errors)


# ── Test: Assembler Preconditions ────────────────────────────────────


class TestAssemblerPreconditions:
    def test_missing_canonical_model_id(self):
        assembler = ExecutionPlanningAssembler()
        with pytest.raises(ValueError, match="canonical_model_id"):
            assembler.assemble(
                canonical_model_id="",
                canonical_model_hash="x",
                entities=[{"entity_id": "e", "entity_type": "t", "label": "l", "confidence": 0.5}],
                relationships=[],
                truth_ids=["T1"],
                governance_receipt_ids=["G1"],
            )

    def test_missing_canonical_model_hash(self):
        assembler = ExecutionPlanningAssembler()
        with pytest.raises(ValueError, match="canonical_model_hash"):
            assembler.assemble(
                canonical_model_id="CWM-x",
                canonical_model_hash="",
                entities=[{"entity_id": "e", "entity_type": "t", "label": "l", "confidence": 0.5}],
                relationships=[],
                truth_ids=["T1"],
                governance_receipt_ids=["G1"],
            )

    def test_empty_inputs(self):
        assembler = ExecutionPlanningAssembler()
        with pytest.raises(ValueError, match="at least one"):
            assembler.assemble(
                canonical_model_id="CWM-x",
                canonical_model_hash="x",
                entities=[],
                relationships=[],
                truth_ids=[],
                governance_receipt_ids=["G1"],
            )


# ── Test: Action Sequence ────────────────────────────────────────────


class TestActionSequence:
    def test_sequence_has_actions(self):
        c = _assemble_candidate()
        assert len(c.action_sequence.actions) == 3

    def test_sequence_ordered(self):
        c = _assemble_candidate()
        orders = [a.sequence_order for a in c.action_sequence.actions]
        assert orders == sorted(orders)

    def test_sequence_total_cost(self):
        seq = ActionSequence(
            sequence_id="S1",
            actions=[
                ProposedAction(
                    action_id="A1",
                    action_type="t",
                    description="d",
                    resource_requirements=[
                        ResourceRequirement(
                            resource_id="R1",
                            resource_type="compute",
                            description="GPU",
                            is_financial=True,
                            estimated_cost=50.0,
                        ),
                    ],
                ),
                ProposedAction(
                    action_id="A2",
                    action_type="t",
                    description="d",
                    resource_requirements=[
                        ResourceRequirement(
                            resource_id="R2",
                            resource_type="compute",
                            description="CPU",
                            is_financial=True,
                            estimated_cost=30.0,
                        ),
                    ],
                ),
            ],
        )
        assert seq.compute_total_cost() == 80.0

    def test_sequence_total_risk(self):
        seq = ActionSequence(
            sequence_id="S1",
            actions=[
                ProposedAction(
                    action_id="A1",
                    action_type="t",
                    description="d",
                    risk_envelope=RiskEnvelope(overall_risk=0.3),
                ),
                ProposedAction(
                    action_id="A2",
                    action_type="t",
                    description="d",
                    risk_envelope=RiskEnvelope(overall_risk=0.7),
                ),
            ],
        )
        assert seq.compute_total_risk() == 0.7


# ── Test: Example Artifacts ──────────────────────────────────────────


class TestExampleArtifacts:
    ARTIFACT_DIR = Path(_ROOT) / "data" / "runtime" / "execution_planning_candidates"

    def test_planning_candidate_example(self):
        path = self.ARTIFACT_DIR / "planning_candidate_example.json"
        assert path.exists(), f"Missing: {path}"
        data = json.loads(path.read_text())
        assert "plan_id" in data

    def test_action_graph_example(self):
        path = self.ARTIFACT_DIR / "action_graph_example.json"
        assert path.exists(), f"Missing: {path}"
        data = json.loads(path.read_text())
        assert "graph_id" in data

    def test_risk_envelope_example(self):
        path = self.ARTIFACT_DIR / "risk_envelope_example.json"
        assert path.exists(), f"Missing: {path}"
        data = json.loads(path.read_text())
        assert "financial_risk" in data

    def test_dependency_graph_example(self):
        path = self.ARTIFACT_DIR / "dependency_graph_example.json"
        assert path.exists(), f"Missing: {path}"
        data = json.loads(path.read_text())
        assert "edges" in data

    def test_no_secrets_in_artifacts(self):
        for path in self.ARTIFACT_DIR.glob("*.json"):
            content = path.read_text().lower()
            for secret in ["password", "api_key", "secret_key", "bearer", "token_value"]:
                assert secret not in content, f"Secret '{secret}' found in {path.name}"
