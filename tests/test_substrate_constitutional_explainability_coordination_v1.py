"""Tests for Phase 96.8CK — Substrate Constitutional Explainability Coordination.

Tests: contracts, enums, lifecycle, causal lineage, governance justification,
replay accountability, continuity accountability, provenance graphs,
constitutional reasoning, observability pipeline, replay validator,
boundary policies, continuity bridges, coordinator, constraint verification.
"""

import os
import json
import tempfile
import pytest

from core.explainability.constitutional_explainability_contracts_v1 import (
    ExplainabilityPhase,
    ExplainabilityEventType,
    ExplainabilityDomain,
    ReasoningType,
    ConstitutionalExplanationState,
    RuntimeLineageState,
    GovernanceReasoningState,
    ReplayExplanationState,
    ContinuityExplanationState,
    DeploymentExplanationState,
    ValidationExplanationState,
    CausalTraceState,
    OperationalJustificationState,
    ConstitutionalAccountabilityState,
    ProvenanceGraphState,
    RuntimeNarrativeState,
    ExplanationReplayState,
    ExplainabilityObservabilityState,
    ConstitutionalExplanationReceipt,
    _now_iso,
    _deterministic_id,
)
from core.explainability.explainability_lifecycle_engine_v1 import (
    ExplainabilityLifecycleEngine,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
)
from core.explainability.causal_lineage_reconstruction_engine_v1 import (
    CausalLineageReconstructionEngine,
    LINEAGE_DOMAINS,
    MAX_LINEAGE_ENTRIES,
    MAX_TRACES,
)
from core.explainability.governance_justification_engine_v1 import (
    GovernanceJustificationEngine,
    JUSTIFICATION_TYPES,
    MAX_JUSTIFICATIONS,
)
from core.explainability.replay_accountability_engine_v1 import (
    ReplayAccountabilityEngine,
    REPLAY_ACCOUNTABILITY_DOMAINS,
    MAX_REPLAY_EXPLANATIONS,
)
from core.explainability.continuity_accountability_engine_v1 import (
    ContinuityAccountabilityEngine,
    CONTINUITY_ACCOUNTABILITY_DOMAINS,
    MAX_CONTINUITY_EXPLANATIONS,
)
from core.explainability.operational_provenance_graph_engine_v1 import (
    OperationalProvenanceGraphEngine,
    PROVENANCE_DOMAINS,
    MAX_PROVENANCE_GRAPHS,
)
from core.explainability.constitutional_reasoning_engine_v1 import (
    ConstitutionalReasoningEngine,
    REASONING_DOMAINS,
    MAX_REASONING_TRACES,
)
from core.explainability.explainability_observability_pipeline_v1 import (
    ExplainabilityObservabilityPipeline,
    EVENT_FILE_MAP,
)
from core.explainability.constitutional_explainability_replay_validator_v1 import (
    ConstitutionalExplainabilityReplayValidator,
    REPLAY_CHECKS,
)
from core.explainability.explainability_boundary_policies_v1 import (
    ExplainabilityBoundaryPolicies,
    EXPLAINABILITY_LIMITS,
    FORBIDDEN_EXPLAINABILITY_ACTIONS,
)
from core.explainability.explainability_continuity_bridges_v1 import (
    _BaseBridge,
    GovernanceExplainabilityBridge,
    ReplayExplainabilityBridge,
    ContinuityExplainabilityBridge,
    TopologyExplainabilityBridge,
    DeploymentExplainabilityBridge,
    ValidationExplainabilityBridge,
    CertificationExplainabilityBridge,
    IntelligenceExplainabilityBridge,
    OrchestrationExplainabilityBridge,
    ALL_BRIDGE_CLASSES,
)
from core.explainability.canonical_constitutional_explainability_coordinator_v1 import (
    CanonicalConstitutionalExplainabilityCoordinator,
    MAX_EXPLANATION_RUNS,
)


# ── TestContracts ──────────────────────────────────────────


class TestContracts:
    def test_constitutional_explanation_state(self):
        s = ConstitutionalExplanationState(domain="governance", decision_id="d1")
        d = s.to_dict()
        assert d["domain"] == "governance"
        assert d["explanation_id"].startswith("cexp-")

    def test_runtime_lineage_state(self):
        s = RuntimeLineageState(source_id="s1", target_id="t1")
        d = s.to_dict()
        assert d["lineage_type"] == "causal"
        assert d["lineage_id"].startswith("rlin-")

    def test_governance_reasoning_state(self):
        s = GovernanceReasoningState(decision_id="d1", rule_applied="r1")
        d = s.to_dict()
        assert d["outcome"] == "allowed"
        assert d["reasoning_id"].startswith("greas-")

    def test_replay_explanation_state(self):
        s = ReplayExplanationState(replay_id="r1")
        d = s.to_dict()
        assert d["deterministic"] is True
        assert d["replay_explanation_id"].startswith("rexp-")

    def test_continuity_explanation_state(self):
        s = ContinuityExplanationState(checkpoint_id="c1")
        d = s.to_dict()
        assert d["restoration_valid"] is True
        assert d["continuity_explanation_id"].startswith("ctexp-")

    def test_deployment_explanation_state(self):
        s = DeploymentExplanationState(deployment_id="d1")
        d = s.to_dict()
        assert d["governed"] is True
        assert d["deployment_explanation_id"].startswith("dexp-")

    def test_validation_explanation_state(self):
        s = ValidationExplanationState(validation_id="v1")
        d = s.to_dict()
        assert d["outcome"] == "sovereign"
        assert d["validation_explanation_id"].startswith("vexp-")

    def test_causal_trace_state(self):
        s = CausalTraceState(trace_name="test", steps=5)
        d = s.to_dict()
        assert d["steps"] == 5
        assert d["trace_id"].startswith("ctrace-")

    def test_operational_justification_state(self):
        s = OperationalJustificationState(operation_id="op1", evidence_count=3)
        d = s.to_dict()
        assert d["justified"] is True
        assert d["justification_id"].startswith("ojust-")

    def test_constitutional_accountability_state(self):
        s = ConstitutionalAccountabilityState(domain="governance", decisions_explained=10)
        d = s.to_dict()
        assert d["all_accountable"] is True
        assert d["accountability_id"].startswith("cacct-")

    def test_provenance_graph_state(self):
        s = ProvenanceGraphState(graph_name="exec", nodes=5, edges=4)
        d = s.to_dict()
        assert d["deterministic"] is True
        assert d["provenance_id"].startswith("prov-")

    def test_runtime_narrative_state(self):
        s = RuntimeNarrativeState(narrative_type="governance", source_count=3)
        d = s.to_dict()
        assert d["fabricated"] is False
        assert d["narrative_id"].startswith("rnarr-")

    def test_explanation_replay_state(self):
        s = ExplanationReplayState(check_name="test")
        d = s.to_dict()
        assert d["deterministic"] is True
        assert d["replay_id"].startswith("exrplay-")

    def test_explainability_observability_state(self):
        s = ExplainabilityObservabilityState(events_emitted=20)
        d = s.to_dict()
        assert d["all_persisted"] is True
        assert d["observability_id"].startswith("exobs-")

    def test_constitutional_explanation_receipt(self):
        s = ConstitutionalExplanationReceipt(run_id="r1", explanations_generated=15)
        d = s.to_dict()
        assert d["outcome"] == "explained"
        assert d["receipt_id"].startswith("exrcpt-")


# ── TestEnums ──────────────────────────────────────────────


class TestEnums:
    def test_explainability_phase_count(self):
        assert len(ExplainabilityPhase) == 5

    def test_explainability_event_type_count(self):
        assert len(ExplainabilityEventType) == 8

    def test_explainability_domain_count(self):
        assert len(ExplainabilityDomain) == 8

    def test_reasoning_type_count(self):
        assert len(ReasoningType) == 6

    def test_deterministic_id(self):
        a = _deterministic_id("t-", "x", "y")
        b = _deterministic_id("t-", "x", "y")
        assert a == b

    def test_reasoning_type_values(self):
        assert ReasoningType.RULE_REFERENCE.value == "rule_reference"
        assert ReasoningType.RECEIPT_REFERENCE.value == "receipt_reference"


# ── TestLifecycleEngine ───────────────────────────────────


class TestLifecycleEngine:
    def test_initial_phase(self):
        e = ExplainabilityLifecycleEngine()
        assert e.current_phase == "defined"

    def test_linear_progression(self):
        e = ExplainabilityLifecycleEngine()
        e.transition("reconstructing")
        e.transition("validating")
        e.transition("explained")
        e.transition("archived")
        assert e.current_phase == "archived"
        assert e.is_terminal

    def test_invalid_transition(self):
        e = ExplainabilityLifecycleEngine()
        with pytest.raises(ValueError):
            e.transition("archived")

    def test_terminal_no_transition(self):
        e = ExplainabilityLifecycleEngine()
        for p in ["reconstructing", "validating", "explained", "archived"]:
            e.transition(p)
        with pytest.raises(ValueError):
            e.transition("defined")

    def test_history_tracking(self):
        e = ExplainabilityLifecycleEngine()
        e.transition("reconstructing")
        h = e.get_history()
        assert len(h) == 1
        assert h[0]["from"] == "defined"
        assert h[0]["to"] == "reconstructing"

    def test_can_transition(self):
        e = ExplainabilityLifecycleEngine()
        assert e.can_transition("reconstructing") is True
        assert e.can_transition("archived") is False

    def test_stats(self):
        e = ExplainabilityLifecycleEngine()
        e.transition("reconstructing")
        s = e.get_stats()
        assert s["current_phase"] == "reconstructing"
        assert s["transitions"] == 1

    def test_five_valid_transitions(self):
        assert len(VALID_TRANSITIONS) == 5

    def test_terminal_states(self):
        assert TERMINAL_STATES == {"archived"}


# ── TestCausalLineageReconstructionEngine ─────────────────


class TestCausalLineageReconstructionEngine:
    def test_add_lineage(self):
        e = CausalLineageReconstructionEngine()
        r = e.add_lineage("s1", "t1")
        assert r["lineage_type"] == "causal"

    def test_reconstruct_trace(self):
        e = CausalLineageReconstructionEngine()
        r = e.reconstruct_trace("test_chain", steps=3)
        assert r["deterministic"] is True

    def test_reconstruct_all_domains(self):
        e = CausalLineageReconstructionEngine()
        r = e.reconstruct_all_domains()
        assert r["all_deterministic"] is True
        assert r["total"] == 7

    def test_all_deterministic_empty(self):
        e = CausalLineageReconstructionEngine()
        assert e.all_deterministic() is True

    def test_max_lineage(self):
        e = CausalLineageReconstructionEngine()
        for i in range(MAX_LINEAGE_ENTRIES):
            e.add_lineage(f"s{i}", f"t{i}")
        with pytest.raises(ValueError):
            e.add_lineage("overflow_s", "overflow_t")

    def test_max_traces(self):
        e = CausalLineageReconstructionEngine()
        for i in range(MAX_TRACES):
            e.reconstruct_trace(f"trace-{i}")
        with pytest.raises(ValueError):
            e.reconstruct_trace("overflow")

    def test_lineage_domains_count(self):
        assert len(LINEAGE_DOMAINS) == 7

    def test_stats(self):
        e = CausalLineageReconstructionEngine()
        e.add_lineage("s1", "t1")
        e.reconstruct_trace("t1")
        s = e.get_stats()
        assert s["total_lineage"] == 1
        assert s["total_traces"] == 1


# ── TestGovernanceJustificationEngine ─────────────────────


class TestGovernanceJustificationEngine:
    def test_justify_single(self):
        e = GovernanceJustificationEngine()
        r = e.justify("d1", "rule1")
        assert r["outcome"] == "allowed"

    def test_justify_all_types(self):
        e = GovernanceJustificationEngine()
        r = e.justify_all_types()
        assert r["all_justified"] is True
        assert r["total"] == 9

    def test_all_justified_empty(self):
        e = GovernanceJustificationEngine()
        assert e.all_justified() is True

    def test_unjustified(self):
        e = GovernanceJustificationEngine()
        e.justify("d1", "rule1", outcome="unjustified")
        assert e.all_justified() is False

    def test_max_justifications(self):
        e = GovernanceJustificationEngine()
        for i in range(MAX_JUSTIFICATIONS):
            e.justify(f"d-{i}", f"r-{i}")
        with pytest.raises(ValueError):
            e.justify("overflow", "rule")

    def test_types_count(self):
        assert len(JUSTIFICATION_TYPES) == 9

    def test_stats(self):
        e = GovernanceJustificationEngine()
        e.justify_all_types()
        s = e.get_stats()
        assert s["total_justifications"] == 9
        assert s["all_justified"] is True


# ── TestReplayAccountabilityEngine ────────────────────────


class TestReplayAccountabilityEngine:
    def test_explain_single(self):
        e = ReplayAccountabilityEngine()
        r = e.explain_replay("r1")
        assert r["deterministic"] is True

    def test_explain_all_domains(self):
        e = ReplayAccountabilityEngine()
        r = e.explain_all_domains()
        assert r["all_deterministic"] is True
        assert r["total"] == 5

    def test_all_deterministic_empty(self):
        e = ReplayAccountabilityEngine()
        assert e.all_deterministic() is True

    def test_non_deterministic(self):
        e = ReplayAccountabilityEngine()
        e.explain_replay("r1", deterministic=False)
        assert e.all_deterministic() is False

    def test_max_explanations(self):
        e = ReplayAccountabilityEngine()
        for i in range(MAX_REPLAY_EXPLANATIONS):
            e.explain_replay(f"r-{i}")
        with pytest.raises(ValueError):
            e.explain_replay("overflow")

    def test_domains_count(self):
        assert len(REPLAY_ACCOUNTABILITY_DOMAINS) == 5

    def test_stats(self):
        e = ReplayAccountabilityEngine()
        e.explain_all_domains()
        s = e.get_stats()
        assert s["total_explanations"] == 5


# ── TestContinuityAccountabilityEngine ────────────────────


class TestContinuityAccountabilityEngine:
    def test_explain_single(self):
        e = ContinuityAccountabilityEngine()
        r = e.explain_continuity("c1")
        assert r["restoration_valid"] is True

    def test_explain_all_domains(self):
        e = ContinuityAccountabilityEngine()
        r = e.explain_all_domains()
        assert r["all_valid"] is True
        assert r["total"] == 5

    def test_all_valid_empty(self):
        e = ContinuityAccountabilityEngine()
        assert e.all_valid() is True

    def test_invalid(self):
        e = ContinuityAccountabilityEngine()
        e.explain_continuity("c1", restoration_valid=False)
        assert e.all_valid() is False

    def test_max_explanations(self):
        e = ContinuityAccountabilityEngine()
        for i in range(MAX_CONTINUITY_EXPLANATIONS):
            e.explain_continuity(f"c-{i}")
        with pytest.raises(ValueError):
            e.explain_continuity("overflow")

    def test_domains_count(self):
        assert len(CONTINUITY_ACCOUNTABILITY_DOMAINS) == 5

    def test_stats(self):
        e = ContinuityAccountabilityEngine()
        e.explain_all_domains()
        s = e.get_stats()
        assert s["total_explanations"] == 5
        assert s["all_valid"] is True


# ── TestOperationalProvenanceGraphEngine ──────────────────


class TestOperationalProvenanceGraphEngine:
    def test_generate_single(self):
        e = OperationalProvenanceGraphEngine()
        r = e.generate_graph("test", nodes=3, edges=2)
        assert r["deterministic"] is True

    def test_generate_all_domains(self):
        e = OperationalProvenanceGraphEngine()
        r = e.generate_all_domains()
        assert r["all_deterministic"] is True
        assert r["total"] == 6

    def test_all_deterministic_empty(self):
        e = OperationalProvenanceGraphEngine()
        assert e.all_deterministic() is True

    def test_max_graphs(self):
        e = OperationalProvenanceGraphEngine()
        for i in range(MAX_PROVENANCE_GRAPHS):
            e.generate_graph(f"g-{i}")
        with pytest.raises(ValueError):
            e.generate_graph("overflow")

    def test_domains_count(self):
        assert len(PROVENANCE_DOMAINS) == 6

    def test_stats(self):
        e = OperationalProvenanceGraphEngine()
        e.generate_all_domains()
        s = e.get_stats()
        assert s["total_graphs"] == 6
        assert s["total_nodes"] == 18
        assert s["total_edges"] == 12


# ── TestConstitutionalReasoningEngine ─────────────────────


class TestConstitutionalReasoningEngine:
    def test_generate_single(self):
        e = ConstitutionalReasoningEngine()
        r = e.generate_reasoning("op1", evidence_count=2)
        assert r["justified"] is True

    def test_generate_all_domains(self):
        e = ConstitutionalReasoningEngine()
        r = e.generate_all_domains()
        assert r["all_justified"] is True
        assert r["total"] == 6

    def test_all_justified_empty(self):
        e = ConstitutionalReasoningEngine()
        assert e.all_justified() is True

    def test_no_fabricated(self):
        e = ConstitutionalReasoningEngine()
        e.generate_reasoning("op1", evidence_count=1)
        assert e.no_fabricated() is True

    def test_zero_evidence_rejected(self):
        e = ConstitutionalReasoningEngine()
        with pytest.raises(ValueError):
            e.generate_reasoning("op1", evidence_count=0)

    def test_max_traces(self):
        e = ConstitutionalReasoningEngine()
        for i in range(MAX_REASONING_TRACES):
            e.generate_reasoning(f"op-{i}")
        with pytest.raises(ValueError):
            e.generate_reasoning("overflow")

    def test_domains_count(self):
        assert len(REASONING_DOMAINS) == 6

    def test_stats(self):
        e = ConstitutionalReasoningEngine()
        e.generate_all_domains()
        s = e.get_stats()
        assert s["total_traces"] == 6
        assert s["no_fabricated"] is True


# ── TestObservabilityPipeline ─────────────────────────────


class TestObservabilityPipeline:
    def test_emit_explanation_requested(self):
        p = ExplainabilityObservabilityPipeline()
        e = p.emit_explanation_requested({"run_id": "r1"})
        assert e["event_type"] == "explanation_requested"

    def test_emit_lineage_reconstructed(self):
        p = ExplainabilityObservabilityPipeline()
        e = p.emit_lineage_reconstructed()
        assert e["event_type"] == "lineage_reconstructed"

    def test_emit_governance_reasoning_reconstructed(self):
        p = ExplainabilityObservabilityPipeline()
        e = p.emit_governance_reasoning_reconstructed()
        assert e["event_type"] == "governance_reasoning_reconstructed"

    def test_emit_replay_explanation_generated(self):
        p = ExplainabilityObservabilityPipeline()
        e = p.emit_replay_explanation_generated()
        assert e["event_type"] == "replay_explanation_generated"

    def test_emit_continuity_explanation_generated(self):
        p = ExplainabilityObservabilityPipeline()
        e = p.emit_continuity_explanation_generated()
        assert e["event_type"] == "continuity_explanation_generated"

    def test_emit_provenance_graph_generated(self):
        p = ExplainabilityObservabilityPipeline()
        e = p.emit_provenance_graph_generated()
        assert e["event_type"] == "provenance_graph_generated"

    def test_emit_constitutional_reasoning_generated(self):
        p = ExplainabilityObservabilityPipeline()
        e = p.emit_constitutional_reasoning_generated()
        assert e["event_type"] == "constitutional_reasoning_generated"

    def test_emit_explanation_completed(self):
        p = ExplainabilityObservabilityPipeline()
        e = p.emit_explanation_completed()
        assert e["event_type"] == "explanation_completed"

    def test_event_file_map(self):
        assert len(EVENT_FILE_MAP) == 8
        for k, v in EVENT_FILE_MAP.items():
            assert v.endswith(".jsonl")

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            p = ExplainabilityObservabilityPipeline(output_dir=td)
            p.emit_explanation_requested({"run_id": "r1"})
            path = os.path.join(td, "explanation_requested.jsonl")
            assert os.path.exists(path)
            with open(path) as f:
                line = json.loads(f.readline())
            assert line["event_type"] == "explanation_requested"

    def test_get_events_by_type(self):
        p = ExplainabilityObservabilityPipeline()
        p.emit_explanation_requested()
        p.emit_explanation_completed()
        p.emit_explanation_requested()
        starts = p.get_events_by_type("explanation_requested")
        assert len(starts) == 2

    def test_stats(self):
        p = ExplainabilityObservabilityPipeline()
        p.emit_explanation_requested()
        p.emit_explanation_completed()
        s = p.get_stats()
        assert s["total_events"] == 2
        assert s["all_persisted"] is True


# ── TestReplayValidator ───────────────────────────────────


class TestReplayValidator:
    def test_validate_single(self):
        v = ConstitutionalExplainabilityReplayValidator()
        r = v.validate_replay("test", "in", "out")
        assert r["deterministic"] is True

    def test_validate_all(self):
        v = ConstitutionalExplainabilityReplayValidator()
        r = v.validate_all()
        assert r["all_deterministic"] is True
        assert r["total"] == 7

    def test_all_deterministic_empty(self):
        v = ConstitutionalExplainabilityReplayValidator()
        assert v.all_deterministic() is True

    def test_replay_checks_count(self):
        assert len(REPLAY_CHECKS) == 7

    def test_stats(self):
        v = ConstitutionalExplainabilityReplayValidator()
        v.validate_all()
        s = v.get_stats()
        assert s["total_checks"] == 7
        assert s["deterministic"] == 7

    def test_deterministic_hashing(self):
        v = ConstitutionalExplainabilityReplayValidator()
        r1 = v.validate_replay("c", "same", "same")
        r2 = v.validate_replay("c", "same", "same")
        assert r1["input_hash"] == r2["input_hash"]
        assert r1["output_hash"] == r2["output_hash"]


# ── TestBoundaryPolicies ─────────────────────────────────


class TestBoundaryPolicies:
    def test_check_within_limit(self):
        bp = ExplainabilityBoundaryPolicies()
        r = bp.check_limit("max_explanations", 100)
        assert r["exceeded"] is False

    def test_check_exceeded(self):
        bp = ExplainabilityBoundaryPolicies()
        r = bp.check_limit("max_explanations", 201)
        assert r["exceeded"] is True

    def test_override_capping(self):
        bp = ExplainabilityBoundaryPolicies()
        r = bp.check_limit("max_explanations", 150, override=300)
        assert r["max_value"] == 200
        assert r["exceeded"] is False

    def test_override_lower(self):
        bp = ExplainabilityBoundaryPolicies()
        r = bp.check_limit("max_explanations", 60, override=50)
        assert r["max_value"] == 50
        assert r["exceeded"] is True

    def test_forbidden_action(self):
        bp = ExplainabilityBoundaryPolicies()
        assert bp.is_forbidden("fabricated_explanations") is True
        assert bp.is_forbidden("allowed_action") is False

    def test_check_all_limits(self):
        bp = ExplainabilityBoundaryPolicies()
        vals = {k: 0 for k in EXPLAINABILITY_LIMITS}
        r = bp.check_all_limits(vals)
        assert r["any_exceeded"] is False
        assert r["total"] == 8

    def test_limits_count(self):
        assert len(EXPLAINABILITY_LIMITS) == 8

    def test_forbidden_count(self):
        assert len(FORBIDDEN_EXPLAINABILITY_ACTIONS) == 8

    def test_get_exceeded(self):
        bp = ExplainabilityBoundaryPolicies()
        bp.check_limit("max_explanations", 300)
        assert len(bp.get_exceeded()) == 1

    def test_stats(self):
        bp = ExplainabilityBoundaryPolicies()
        bp.check_limit("max_explanations", 50)
        s = bp.get_stats()
        assert s["total_checks"] == 1

    def test_all_forbidden_actions_listed(self):
        expected = [
            "fabricated_explanations",
            "hallucinated_causality",
            "hidden_provenance_mutation",
            "unstored_reasoning_synthesis",
            "explanation_owned_execution",
            "governance_bypass",
            "replay_bypass",
            "recursive_explainability_loops",
        ]
        assert FORBIDDEN_EXPLAINABILITY_ACTIONS == expected

    def test_unknown_limit(self):
        bp = ExplainabilityBoundaryPolicies()
        r = bp.check_limit("nonexistent", 1)
        assert r["max_value"] == 0
        assert r["exceeded"] is True

    def test_at_exact_limit(self):
        bp = ExplainabilityBoundaryPolicies()
        r = bp.check_limit("max_explanations", 200)
        assert r["exceeded"] is False

    def test_one_over(self):
        bp = ExplainabilityBoundaryPolicies()
        r = bp.check_limit("max_explanations", 201)
        assert r["exceeded"] is True

    def test_override_equal_default(self):
        bp = ExplainabilityBoundaryPolicies()
        r = bp.check_limit("max_explanations", 100, override=200)
        assert r["max_value"] == 200
        assert r["exceeded"] is False

    def test_override_zero(self):
        bp = ExplainabilityBoundaryPolicies()
        r = bp.check_limit("max_explanations", 1, override=0)
        assert r["max_value"] == 0
        assert r["exceeded"] is True


# ── TestContinuityBridges ────────────────────────────────


class TestContinuityBridges:
    def test_bridge_count(self):
        assert len(ALL_BRIDGE_CLASSES) == 9

    def test_bridge_names(self):
        with tempfile.TemporaryDirectory() as td:
            names = [cls(state_dir=td)._bridge_name for cls in ALL_BRIDGE_CLASSES]
            assert "governance_explainability" in names
            assert "replay_explainability" in names
            assert "orchestration_explainability" in names

    def test_record_and_retrieve(self):
        with tempfile.TemporaryDirectory() as td:
            b = GovernanceExplainabilityBridge(state_dir=td)
            r = b.record("test_action", {"key": "value"})
            assert r["bridge"] == "governance_explainability"
            assert r["key"] == "value"

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            b = ReplayExplainabilityBridge(state_dir=td)
            b.record("test_persist")
            path = os.path.join(td, "replay_explainability.jsonl")
            assert os.path.exists(path)

    def test_stats(self):
        with tempfile.TemporaryDirectory() as td:
            b = ContinuityExplainabilityBridge(state_dir=td)
            b.record("a1")
            b.record("a2")
            s = b.get_stats()
            assert s["total_records"] == 2

    def test_get_records(self):
        with tempfile.TemporaryDirectory() as td:
            b = TopologyExplainabilityBridge(state_dir=td)
            b.record("r1")
            b.record("r2")
            b.record("r3")
            assert len(b.get_records()) == 3

    def test_all_bridges_instantiate(self):
        with tempfile.TemporaryDirectory() as td:
            for cls in ALL_BRIDGE_CLASSES:
                b = cls(state_dir=td)
                assert b._bridge_name != ""

    def test_certification_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = CertificationExplainabilityBridge(state_dir=td)
            r = b.record("certify")
            assert r["bridge"] == "certification_explainability"

    def test_intelligence_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = IntelligenceExplainabilityBridge(state_dir=td)
            r = b.record("intel")
            assert r["bridge"] == "intelligence_explainability"

    def test_orchestration_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            b = OrchestrationExplainabilityBridge(state_dir=td)
            r = b.record("orch")
            assert r["bridge"] == "orchestration_explainability"


# ── TestCoordinator ──────────────────────────────────────


class TestCoordinator:
    def test_start_explanation(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        r = c.start_explanation("test-run")
        assert r["run_id"] == "test-run"
        assert r["status"] == "started"

    def test_reconstruct_lineage(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        r = c.reconstruct_lineage()
        assert r["all_deterministic"] is True
        assert r["total"] == 7

    def test_justify_governance(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        r = c.justify_governance()
        assert r["all_justified"] is True
        assert r["total"] == 9

    def test_explain_replay(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        r = c.explain_replay()
        assert r["all_deterministic"] is True
        assert r["total"] == 5

    def test_explain_continuity(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        r = c.explain_continuity()
        assert r["all_valid"] is True
        assert r["total"] == 5

    def test_generate_provenance(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        r = c.generate_provenance()
        assert r["all_deterministic"] is True
        assert r["total"] == 6

    def test_generate_reasoning(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        r = c.generate_reasoning()
        assert r["all_justified"] is True
        assert r["total"] == 6

    def test_validate_replay_determinism(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        r = c.validate_replay_determinism()
        assert r["all_deterministic"] is True

    def test_check_boundary(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        r = c.check_boundary("max_explanations", 50)
        assert r["exceeded"] is False

    def test_complete_explanation(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        c.start_explanation("r1")
        c.reconstruct_lineage()
        c.justify_governance()
        c.explain_replay()
        c.explain_continuity()
        c.generate_provenance()
        c.generate_reasoning()
        c.validate_replay_determinism()
        r = c.complete_explanation("r1")
        assert r["outcome"] == "explained"

    def test_get_explainability_report(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        c.reconstruct_lineage()
        c.justify_governance()
        c.explain_replay()
        c.explain_continuity()
        c.generate_provenance()
        c.generate_reasoning()
        r = c.get_explainability_report()
        assert r["all_explained"] is True

    def test_get_stats(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        s = c.get_stats()
        assert "lifecycle" in s
        assert "lineage" in s
        assert s["explanations"] == 0

    def test_max_explanation_runs(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        for i in range(MAX_EXPLANATION_RUNS):
            c.start_explanation(f"r-{i}")
        with pytest.raises(ValueError):
            c.start_explanation("overflow")

    def test_auto_run_id(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        r = c.start_explanation()
        assert r["run_id"].startswith("exprun-")

    def test_full_explainability_flow(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        c.start_explanation("full-flow")
        lin = c.reconstruct_lineage()
        assert lin["all_deterministic"] is True
        gov = c.justify_governance()
        assert gov["all_justified"] is True
        rep = c.explain_replay()
        assert rep["all_deterministic"] is True
        cont = c.explain_continuity()
        assert cont["all_valid"] is True
        prov = c.generate_provenance()
        assert prov["all_deterministic"] is True
        reas = c.generate_reasoning()
        assert reas["all_justified"] is True
        rv = c.validate_replay_determinism()
        assert rv["all_deterministic"] is True
        receipt = c.complete_explanation("full-flow")
        assert receipt["outcome"] == "explained"
        report = c.get_explainability_report()
        assert report["all_explained"] is True


# ── TestConstraintVerification ───────────────────────────


class TestConstraintVerification:
    def test_deterministic_explanation_reconstruction(self):
        e = CausalLineageReconstructionEngine()
        r = e.reconstruct_all_domains()
        assert r["all_deterministic"] is True

    def test_deterministic_provenance_generation(self):
        e = OperationalProvenanceGraphEngine()
        r = e.generate_all_domains()
        assert r["all_deterministic"] is True

    def test_deterministic_governance_justification(self):
        e = GovernanceJustificationEngine()
        r = e.justify_all_types()
        assert r["all_justified"] is True

    def test_deterministic_replay_accountability(self):
        e = ReplayAccountabilityEngine()
        r = e.explain_all_domains()
        assert r["all_deterministic"] is True

    def test_deterministic_continuity_accountability(self):
        e = ContinuityAccountabilityEngine()
        r = e.explain_all_domains()
        assert r["all_valid"] is True

    def test_no_fabricated_reasoning(self):
        e = ConstitutionalReasoningEngine()
        e.generate_all_domains()
        assert e.no_fabricated() is True

    def test_no_zero_evidence_reasoning(self):
        e = ConstitutionalReasoningEngine()
        with pytest.raises(ValueError):
            e.generate_reasoning("op", evidence_count=0)

    def test_no_hallucinated_lineage(self):
        bp = ExplainabilityBoundaryPolicies()
        assert bp.is_forbidden("hallucinated_causality") is True

    def test_no_governance_bypass(self):
        bp = ExplainabilityBoundaryPolicies()
        assert bp.is_forbidden("governance_bypass") is True

    def test_no_execution_outside_spine(self):
        bp = ExplainabilityBoundaryPolicies()
        assert bp.is_forbidden("explanation_owned_execution") is True

    def test_no_recursive_explainability_loops(self):
        bp = ExplainabilityBoundaryPolicies()
        assert bp.is_forbidden("recursive_explainability_loops") is True

    def test_explanation_replay_determinism(self):
        v = ConstitutionalExplainabilityReplayValidator()
        r = v.validate_all()
        assert r["all_deterministic"] is True

    def test_override_capping_enforced(self):
        bp = ExplainabilityBoundaryPolicies()
        r = bp.check_limit("max_explanations", 100, override=300)
        assert r["max_value"] == 200

    def test_coordinator_cannot_invent(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        assert not hasattr(c, "invent")
        assert not hasattr(c, "hallucinate")
        assert not hasattr(c, "fabricate")

    def test_lifecycle_linear_progression(self):
        e = ExplainabilityLifecycleEngine()
        for p in ["reconstructing", "validating", "explained", "archived"]:
            e.transition(p)
        assert e.is_terminal

    def test_lifecycle_terminal_absorbing(self):
        e = ExplainabilityLifecycleEngine()
        for p in ["reconstructing", "validating", "explained", "archived"]:
            e.transition(p)
        with pytest.raises(ValueError):
            e.transition("defined")

    def test_8_explainability_domains_defined(self):
        assert len(ExplainabilityDomain) == 8

    def test_6_reasoning_types_defined(self):
        assert len(ReasoningType) == 6

    def test_no_fabricated_explanations_forbidden(self):
        bp = ExplainabilityBoundaryPolicies()
        assert bp.is_forbidden("fabricated_explanations") is True

    def test_full_explainability_flow(self):
        c = CanonicalConstitutionalExplainabilityCoordinator()
        c.start_explanation("constraint-flow")
        c.reconstruct_lineage()
        c.justify_governance()
        c.explain_replay()
        c.explain_continuity()
        c.generate_provenance()
        c.generate_reasoning()
        c.validate_replay_determinism()
        receipt = c.complete_explanation("constraint-flow")
        assert receipt["outcome"] == "explained"
        report = c.get_explainability_report()
        assert report["all_explained"] is True
