"""Phase 10.0 — Template Library, Candidate Supply, and Cockpit Route Extraction tests.

Covers:
  TST-01: TemplateSeeder (15 tests)
  TST-02: TemplateGovernance (25 tests)
  TST-03: CandidateSupplyEngine (20 tests)
  TST-04: AutonomousCadence integration (10 tests)
  TST-05: Route extraction verification (10 tests)

80+ tests total. Python 3.11 compatible. No external network calls.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, "/opt/OS/.claude/worktrees/phase10-0-template-library")

from substrate.organism.template_registry import (
    AgentCapabilityBinding,
    AgentType,
    CapabilityName,
    TemplateCandidate,
    TemplateEvidence,
    TemplateRollback,
    TemplateStatus,
    TemplateStep,
    TemplateType,
    TemplateValidation,
)
from substrate.organism.template_seeder import SeedResult, TemplateSeeder
from substrate.organism.template_governance import (
    DimensionScore,
    GovernanceDecision,
    TemplateGovernance,
    TemplateGovernanceScore,
)
from substrate.organism.candidate_supply_engine import (
    CandidateSupplyEngine,
    SupplyCandidate,
    SupplyResult,
)
from substrate.organism.autonomous_cadence import (
    AutonomousCadence,
    CadenceMode,
    CadencePolicy,
    CadenceRunResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_store(tmp_path):
    """Temporary directory for template store files."""
    return str(tmp_path)


@pytest.fixture
def seeder(tmp_store):
    return TemplateSeeder(store_dir=tmp_store)


@pytest.fixture
def governance():
    return TemplateGovernance()


def _make_strong_template(**overrides) -> TemplateCandidate:
    """Build a well-scored LOW risk template with all fields populated."""
    defaults = dict(
        template_id="tpl-test-strong-01",
        template_type=TemplateType.CONTRADICTION_FIX,
        trigger_conditions=[
            "contradiction engine reports gap",
            "severity=medium for a declared entity",
        ],
        required_context=["world model entity"],
        required_capabilities=[CapabilityName.FILE_EDIT.value],
        required_agent_type=AgentType.DEVELOPER_AGENT,
        reusable_steps=[
            TemplateStep(order=0, description="Scan", action="scan",
                         requires_capability="code_search", verification="OK"),
            TemplateStep(order=1, description="Fix", action="fix",
                         requires_capability="file_edit", verification="OK"),
            TemplateStep(order=2, description="Verify", action="verify",
                         requires_capability="evidence_verification", verification="OK"),
        ],
        risk_class="low",
        governance_mode="autonomous",
        validation=TemplateValidation(
            description="Run py_compile on target file and confirm exit code 0",
            method="assertion",
        ),
        rollback=TemplateRollback(
            description="git checkout -- <path> to restore prior file state",
            method="revert",
        ),
        evidence_requirements=["contradiction report"],
        known_failure_modes=["entity has multiple contradictions"],
        expected_outcome="Contradiction resolved",
        observed_success_count=5,
        observed_failure_count=0,
        confidence=0.90,
        source_outcome_ids=[],
        source_trial_ids=["phase9_6"],
        source_action_envelope_ids=[],
        evidence=[
            TemplateEvidence(source="phase9_6_evidence.json", detail="run passed", confidence=0.9),
        ],
        agent_capability_binding=AgentCapabilityBinding(
            agent_type=AgentType.DEVELOPER_AGENT,
            capabilities=[CapabilityName.FILE_EDIT.value, CapabilityName.CODE_SEARCH.value],
            confidence=0.88,
        ),
        status=TemplateStatus.PROMOTED,
    )
    defaults.update(overrides)
    return TemplateCandidate(**defaults)


# ===========================================================================
# TST-01: TemplateSeeder (15 tests)
# ===========================================================================

class TestTemplateSeeder:

    def test_seed_creates_templates_file(self, seeder, tmp_store):
        seeder.seed()
        assert os.path.isfile(os.path.join(tmp_store, "templates.jsonl"))

    def test_seed_writes_exactly_10_templates(self, seeder, tmp_store):
        seeder.seed()
        path = os.path.join(tmp_store, "templates.jsonl")
        with open(path) as f:
            lines = [line for line in f if line.strip()]
        assert len(lines) == 10

    def test_all_10_template_types_covered(self, seeder):
        expected_types = {
            "contradiction_fix", "readiness_improvement", "observation_accuracy_fix",
            "world_model_accuracy_fix", "api_contract_fix", "test_repair",
            "cockpit_panel_fix", "route_extraction_fix", "dependency_graph_fix",
            "maintenance_action",
        }
        templates = seeder._build_all_templates()
        actual_types = {t.template_type.value for t in templates}
        assert actual_types == expected_types

    def test_every_template_has_status_promoted(self, seeder):
        for tpl in seeder._build_all_templates():
            assert tpl.status == TemplateStatus.PROMOTED, f"{tpl.template_id} not promoted"

    def test_every_template_has_confidence_gte_070(self, seeder):
        for tpl in seeder._build_all_templates():
            assert tpl.confidence >= 0.70, f"{tpl.template_id} confidence={tpl.confidence}"

    def test_every_template_has_nonempty_evidence(self, seeder):
        for tpl in seeder._build_all_templates():
            assert len(tpl.evidence) > 0, f"{tpl.template_id} has no evidence"

    def test_every_template_has_nongeneric_validation(self, seeder):
        for tpl in seeder._build_all_templates():
            assert tpl.validation is not None, f"{tpl.template_id} has no validation"
            assert tpl.validation.description != "Re-run verification after action", (
                f"{tpl.template_id} has generic validation"
            )

    def test_every_template_has_nongeneric_rollback(self, seeder):
        for tpl in seeder._build_all_templates():
            assert tpl.rollback is not None, f"{tpl.template_id} has no rollback"
            assert tpl.rollback.description != "Revert to pre-execution state", (
                f"{tpl.template_id} has generic rollback"
            )

    def test_every_template_id_starts_with_tpl_seed(self, seeder):
        for tpl in seeder._build_all_templates():
            assert tpl.template_id.startswith("tpl-seed-"), (
                f"{tpl.template_id} does not start with tpl-seed-"
            )

    def test_every_template_has_risk_class_low(self, seeder):
        for tpl in seeder._build_all_templates():
            assert tpl.risk_class == "low", f"{tpl.template_id} risk_class={tpl.risk_class}"

    def test_every_template_has_nonempty_reusable_steps(self, seeder):
        for tpl in seeder._build_all_templates():
            assert len(tpl.reusable_steps) > 0, f"{tpl.template_id} has no steps"

    def test_every_template_has_source_trial_ids_referencing_phase9(self, seeder):
        for tpl in seeder._build_all_templates():
            assert any("phase9" in tid for tid in tpl.source_trial_ids), (
                f"{tpl.template_id} source_trial_ids={tpl.source_trial_ids}"
            )

    def test_idempotency_no_duplicates(self, seeder, tmp_store):
        seeder.seed()
        # Create a fresh seeder that will reload existing IDs
        seeder2 = TemplateSeeder(store_dir=tmp_store)
        result2 = seeder2.seed()
        assert result2.seeded_count == 0
        assert result2.skipped_count == 10
        # Verify file still has exactly 10 lines
        path = os.path.join(tmp_store, "templates.jsonl")
        with open(path) as f:
            lines = [line for line in f if line.strip()]
        assert len(lines) == 10

    def test_seed_result_to_dict(self, seeder):
        result = seeder.seed()
        d = result.to_dict()
        assert "seeded_count" in d
        assert "skipped_count" in d
        assert "error_count" in d
        assert "template_ids" in d
        assert "errors" in d
        assert d["seeded_count"] == 10

    def test_build_all_templates_returns_exactly_10(self, seeder):
        templates = seeder._build_all_templates()
        assert len(templates) == 10


# ===========================================================================
# TST-02: TemplateGovernance (25 tests)
# ===========================================================================

class TestTemplateGovernance:

    def test_evaluate_returns_9_dimensions(self, governance):
        tpl = _make_strong_template()
        score = governance.evaluate(tpl)
        assert len(score.dimensions) == 9

    def test_dimension_names_are_exact(self, governance):
        tpl = _make_strong_template()
        score = governance.evaluate(tpl)
        names = {d.name for d in score.dimensions}
        expected = {
            "evidence", "validation", "rollback", "risk", "reliability",
            "specificity", "reversibility", "blast_radius", "agent_capability",
        }
        assert names == expected

    def test_low_risk_strong_scores_cadence_eligible(self, governance):
        tpl = _make_strong_template()
        score = governance.evaluate(tpl)
        assert score.decision == GovernanceDecision.CADENCE_ELIGIBLE

    def test_validation_below_080_gets_operator_review(self, governance):
        tpl = _make_strong_template(
            validation=TemplateValidation(description="Re-run verification after action"),
        )
        score = governance.evaluate(tpl)
        assert score.decision in (
            GovernanceDecision.OPERATOR_REVIEW_REQUIRED,
            GovernanceDecision.CANDIDATE_ONLY,
        )

    def test_evidence_below_070_not_cadence_eligible(self, governance):
        tpl = _make_strong_template(evidence=[])
        score = governance.evaluate(tpl)
        assert score.decision != GovernanceDecision.CADENCE_ELIGIBLE

    def test_template_referencing_env_path_gets_blocked(self, governance):
        tpl = _make_strong_template(
            trigger_conditions=["read secrets from services/.env"],
        )
        score = governance.evaluate(tpl)
        assert score.decision == GovernanceDecision.BLOCKED

    def test_template_with_credential_keyword_gets_blocked(self, governance):
        tpl = _make_strong_template(
            known_failure_modes=["credential leak in config file"],
        )
        score = governance.evaluate(tpl)
        assert score.decision == GovernanceDecision.BLOCKED

    def test_template_with_api_key_keyword_gets_blocked(self, governance):
        tpl = _make_strong_template(
            evidence_requirements=["api_key from environment"],
        )
        score = governance.evaluate(tpl)
        assert score.decision == GovernanceDecision.BLOCKED

    def test_template_with_dns_mutation_gets_blocked(self, governance):
        tpl = _make_strong_template(
            reusable_steps=[
                TemplateStep(order=0, description="update dns records",
                             action="dns_update", verification="done"),
            ],
        )
        score = governance.evaluate(tpl)
        assert score.decision == GovernanceDecision.BLOCKED

    def test_template_with_container_mutation_gets_blocked(self, governance):
        tpl = _make_strong_template(
            reusable_steps=[
                TemplateStep(order=0, description="start container service",
                             action="container_start", verification="done"),
            ],
        )
        score = governance.evaluate(tpl)
        assert score.decision == GovernanceDecision.BLOCKED

    def test_template_with_rm_rf_gets_blocked(self, governance):
        tpl = _make_strong_template(
            rollback=TemplateRollback(description="rm -rf / to clean up"),
        )
        score = governance.evaluate(tpl)
        assert score.decision == GovernanceDecision.BLOCKED

    def test_template_with_drop_table_gets_blocked(self, governance):
        tpl = _make_strong_template(
            known_failure_modes=["drop table migration fails silently"],
        )
        score = governance.evaluate(tpl)
        assert score.decision == GovernanceDecision.BLOCKED

    def test_blocked_decision_has_reason_codes(self, governance):
        tpl = _make_strong_template(risk_class="high")
        score = governance.evaluate(tpl)
        assert score.decision == GovernanceDecision.BLOCKED
        assert len(score.reason_codes) > 0

    def test_non_eligible_decision_has_reason_codes(self, governance):
        tpl = _make_strong_template(evidence=[])
        score = governance.evaluate(tpl)
        assert len(score.reason_codes) > 0

    def test_high_risk_template_gets_blocked(self, governance):
        tpl = _make_strong_template(risk_class="high")
        score = governance.evaluate(tpl)
        assert score.decision == GovernanceDecision.BLOCKED
        assert any("risk_class_not_low" in rc for rc in score.reason_codes)

    def test_no_evidence_scores_zero(self, governance):
        tpl = _make_strong_template(evidence=[])
        score = governance.evaluate(tpl)
        evidence_dim = next(d for d in score.dimensions if d.name == "evidence")
        assert evidence_dim.score == 0.0

    def test_no_validation_scores_zero(self, governance):
        tpl = _make_strong_template(validation=None)
        score = governance.evaluate(tpl)
        validation_dim = next(d for d in score.dimensions if d.name == "validation")
        assert validation_dim.score == 0.0

    def test_no_rollback_scores_zero(self, governance):
        tpl = _make_strong_template(rollback=None)
        score = governance.evaluate(tpl)
        rollback_dim = next(d for d in score.dimensions if d.name == "rollback")
        assert rollback_dim.score == 0.0

    def test_non_destructive_rollback_scores_one(self, governance):
        tpl = _make_strong_template(
            rollback=TemplateRollback(
                description="Non-destructive read. No rollback required.",
            ),
        )
        score = governance.evaluate(tpl)
        rollback_dim = next(d for d in score.dimensions if d.name == "rollback")
        assert rollback_dim.score == 1.0

    def test_git_checkout_rollback_specificity_bonus(self, governance):
        tpl = _make_strong_template(
            rollback=TemplateRollback(
                description="git checkout -- <path> to restore file",
            ),
        )
        score = governance.evaluate(tpl)
        rollback_dim = next(d for d in score.dimensions if d.name == "rollback")
        assert rollback_dim.score == pytest.approx(0.9)  # base 0.7 + 0.2 specificity

    def test_no_agent_binding_scores_low(self, governance):
        tpl = _make_strong_template(agent_capability_binding=None)
        score = governance.evaluate(tpl)
        agent_dim = next(d for d in score.dimensions if d.name == "agent_capability")
        assert agent_dim.score == 0.3

    def test_two_trigger_conditions_specificity_bonus(self, governance):
        tpl = _make_strong_template(
            trigger_conditions=["condition one", "condition two"],
        )
        score = governance.evaluate(tpl)
        spec_dim = next(d for d in score.dimensions if d.name == "specificity")
        assert spec_dim.score >= 0.3  # at least the trigger bonus

    def test_evaluate_batch_returns_all(self, governance):
        templates = [_make_strong_template(template_id=f"tpl-batch-{i}") for i in range(5)]
        scores = governance.evaluate_batch(templates)
        assert len(scores) == 5
        for s in scores:
            assert isinstance(s, TemplateGovernanceScore)

    def test_governance_decision_enum_has_4_values(self):
        values = [e.value for e in GovernanceDecision]
        assert len(values) == 4
        assert set(values) == {"cadence_eligible", "candidate_only", "operator_review_required", "blocked"}

    def test_dimension_score_to_dict(self):
        ds = DimensionScore(name="evidence", score=0.85, weight=1.0, reason="good")
        d = ds.to_dict()
        assert d["name"] == "evidence"
        assert d["score"] == 0.85
        assert d["weight"] == 1.0
        assert d["reason"] == "good"

    def test_governance_score_to_dict(self, governance):
        tpl = _make_strong_template()
        score = governance.evaluate(tpl)
        d = score.to_dict()
        assert "template_id" in d
        assert "dimensions" in d
        assert "decision" in d
        assert "reason_codes" in d
        assert "weighted_score" in d
        assert isinstance(d["dimensions"], list)
        assert isinstance(d["decision"], str)


# ===========================================================================
# TST-03: CandidateSupplyEngine (20 tests)
# ===========================================================================

class TestCandidateSupplyEngine:

    def test_discover_returns_supply_result(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        result = engine.discover()
        assert isinstance(result, SupplyResult)

    def test_supply_result_has_source_scan_proof_for_all_6_sources(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        result = engine.discover()
        expected_sources = {
            "contradiction_engine", "world_model", "dependency_graph",
            "readiness_model", "bottleneck_engine", "template_audit_gaps",
        }
        assert set(result.source_scan_proof.keys()) == expected_sources

    def test_every_source_shows_scanned_key(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        result = engine.discover()
        for source_name, proof in result.source_scan_proof.items():
            # scanned is True if the scan succeeded, False if it raised an exception
            assert "scanned" in proof, f"{source_name} missing scanned key"

    def test_every_candidate_has_nonempty_evidence(self, tmp_store):
        # Seed templates first so matching can work
        seeder = TemplateSeeder(store_dir=tmp_store)
        seeder.seed()
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        result = engine.discover()
        for c in result.candidates:
            assert len(c.evidence) > 0, f"{c.candidate_id} has no evidence"

    def test_every_candidate_has_non_pending_decision(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        result = engine.discover()
        for c in result.candidates:
            assert c.policy_decision != "pending", (
                f"{c.candidate_id} has pending policy_decision"
            )

    def test_candidates_sorted_by_confidence_reliability_desc(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        result = engine.discover()
        if len(result.candidates) >= 2:
            for i in range(len(result.candidates) - 1):
                a = result.candidates[i]
                b = result.candidates[i + 1]
                assert (a.template_confidence, a.agent_reliability) >= (
                    b.template_confidence, b.agent_reliability
                )

    def test_supply_candidate_to_dict_includes_required_fields(self):
        c = SupplyCandidate(
            source="test_source",
            title="test title",
            description="test desc",
            evidence=[{"source": "test", "detail": "d"}],
            risk_class="low",
            matching_templates=["tpl-x"],
            policy_decision="cadence_eligible",
            template_confidence=0.9,
            agent_reliability=0.8,
            validation_method="assertion",
            rollback_method="revert",
        )
        d = c.to_dict()
        required = {
            "candidate_id", "source", "title", "description", "evidence",
            "affected_files", "risk_class", "matching_templates", "policy_decision",
            "blocked_reasons", "expected_delta", "recommended_next_step",
            "template_confidence", "agent_reliability", "validation_method",
            "rollback_method", "non_mutating", "created_at",
        }
        assert required.issubset(set(d.keys()))

    def test_supply_candidate_to_cadence_dict_includes_required_fields(self):
        c = SupplyCandidate(
            source="contradiction_engine",
            matching_templates=["tpl-seed-contradiction-fix-01"],
            template_confidence=0.9,
            agent_reliability=0.85,
            validation_method="assertion",
        )
        d = c.to_cadence_dict()
        required = {
            "candidate_id", "source", "risk_class", "template_id",
            "template_confidence", "agent_reliability", "validation_method",
        }
        assert required.issubset(set(d.keys()))

    def test_discover_for_cadence_returns_list_of_dicts(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        items = engine.discover_for_cadence()
        assert isinstance(items, list)
        for item in items:
            assert isinstance(item, dict)

    def test_each_cadence_dict_has_required_keys(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        items = engine.discover_for_cadence()
        required = {"candidate_id", "source", "risk_class", "template_id"}
        for item in items:
            assert required.issubset(set(item.keys())), f"Missing keys in {item}"

    def test_supply_result_to_dict(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        result = engine.discover()
        d = result.to_dict()
        assert "candidate_count" in d
        assert "candidates" in d
        assert "source_scan_proof" in d
        assert "scan_duration_seconds" in d
        assert isinstance(d["candidate_count"], int)

    def test_summary_returns_sources_scanned(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        engine.discover()
        s = engine.summary()
        assert "sources_scanned" in s
        assert isinstance(s["sources_scanned"], dict)

    def test_no_candidate_has_pending_decision(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        result = engine.discover()
        for c in result.candidates:
            assert c.policy_decision != "pending"

    def test_blocked_candidates_have_nonempty_reasons(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        result = engine.discover()
        for c in result.candidates:
            if c.policy_decision == "blocked":
                assert len(c.blocked_reasons) > 0, (
                    f"{c.candidate_id} blocked but no reasons"
                )

    def test_supply_candidate_default_values(self):
        c = SupplyCandidate()
        assert c.source == ""
        assert c.title == ""
        assert c.description == ""
        assert c.evidence == []
        assert c.affected_files == []
        assert c.risk_class == "low"
        assert c.matching_templates == []
        assert c.policy_decision == "pending"
        assert c.blocked_reasons == []
        assert c.template_confidence == 0.0
        assert c.agent_reliability == 0.0
        assert c.validation_method == ""
        assert c.rollback_method == ""
        assert c.non_mutating is False

    def test_discover_completes_without_error(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        result = engine.discover()
        # Should complete and have scan proof for all 6 sources
        assert len(result.source_scan_proof) == 6

    def test_engine_custom_template_registry(self, tmp_store):
        from substrate.organism.template_registry import TemplateRegistry
        registry = TemplateRegistry(store_dir=tmp_store)
        engine = CandidateSupplyEngine(template_registry=registry, state_dir=tmp_store)
        assert engine._registry is registry

    def test_engine_custom_governance(self, tmp_store):
        gov = TemplateGovernance()
        engine = CandidateSupplyEngine(governance=gov, state_dir=tmp_store)
        assert engine._governance is gov

    def test_engine_custom_state_dir(self, tmp_store):
        engine = CandidateSupplyEngine(state_dir=tmp_store)
        assert engine._state_dir == tmp_store

    def test_to_cadence_dict_uses_first_matching_template(self):
        c = SupplyCandidate(
            matching_templates=["tpl-first", "tpl-second", "tpl-third"],
        )
        d = c.to_cadence_dict()
        assert d["template_id"] == "tpl-first"


# ===========================================================================
# TST-04: Cadence Integration (10 tests)
# ===========================================================================

class TestCadenceIntegration:

    def _make_supply_callback(self, candidates: list[dict] | None = None):
        """Return a callback that returns canned candidate dicts."""
        if candidates is None:
            candidates = [
                {
                    "candidate_id": "cse-abc12345",
                    "source": "contradiction_engine",
                    "title": "Contradiction fix",
                    "description": "test candidate",
                    "evidence": [{"source": "test", "detail": "detail"}],
                    "risk_class": "low",
                    "template_id": "tpl-seed-contradiction-fix-01",
                    "template_confidence": 0.9,
                    "agent_reliability": 0.85,
                    "validation_method": "assertion",
                    "rollback_method": "revert",
                    "non_mutating": False,
                    "policy_decision": "cadence_eligible",
                    "blocked_reasons": [],
                    "affected_files": [],
                    "expected_delta": "fix contradiction",
                    "recommended_next_step": "run template",
                },
            ]
        return lambda: candidates

    def test_cadence_with_supply_discovers_candidates(self):
        cb = self._make_supply_callback()
        cadence = AutonomousCadence(
            policy=CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0),
            candidate_discovery_fn=cb,
        )
        result = cadence.run_cycle()
        assert result.candidates_found > 0

    def test_cadence_dry_run_does_not_create_prs(self):
        cb = self._make_supply_callback()
        cadence = AutonomousCadence(
            policy=CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0),
            candidate_discovery_fn=cb,
        )
        result = cadence.run_cycle()
        assert result.pr_created is False

    def test_run_cycle_shows_candidates_found(self):
        cb = self._make_supply_callback()
        cadence = AutonomousCadence(
            policy=CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0),
            candidate_discovery_fn=cb,
        )
        result = cadence.run_cycle()
        assert result.candidates_found == 1

    def test_run_cycle_adds_to_run_history(self):
        cb = self._make_supply_callback()
        cadence = AutonomousCadence(
            policy=CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0),
            candidate_discovery_fn=cb,
        )
        assert len(cadence._run_history) == 0
        cadence.run_cycle()
        assert len(cadence._run_history) == 1

    def test_run_cycle_populates_dry_run_results(self):
        cb = self._make_supply_callback()
        cadence = AutonomousCadence(
            policy=CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0),
            candidate_discovery_fn=cb,
        )
        result = cadence.run_cycle()
        assert len(result.dry_run_results) > 0

    def test_prs_today_remains_zero_in_dry_run(self):
        cb = self._make_supply_callback()
        cadence = AutonomousCadence(
            policy=CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0),
            candidate_discovery_fn=cb,
        )
        cadence.run_cycle()
        assert cadence._prs_today == 0

    def test_empty_supply_returns_truthful_result(self):
        cadence = AutonomousCadence(
            policy=CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0),
            candidate_discovery_fn=lambda: [],
        )
        result = cadence.run_cycle()
        assert result.candidates_found == 0

    def test_cadence_mode_off_skips(self):
        cadence = AutonomousCadence(
            policy=CadencePolicy(mode=CadenceMode.OFF),
        )
        tick_result = cadence.tick()
        assert tick_result.get("skipped") is True

    def test_cadence_dry_run_never_mutates(self):
        cb = self._make_supply_callback()
        cadence = AutonomousCadence(
            policy=CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=0),
            candidate_discovery_fn=cb,
        )
        result = cadence.run_cycle()
        assert result.pr_created is False
        assert result.pr_queued is False
        assert cadence._prs_today == 0

    def test_should_run_respects_interval(self):
        cadence = AutonomousCadence(
            policy=CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY, interval_seconds=3600),
        )
        # Initially should_run is True (last_run_at=0)
        assert cadence.should_run() is True
        cadence._last_run_at = time.time()
        # Immediately after a run, should_run is False
        assert cadence.should_run() is False


# ===========================================================================
# TST-05: Route Extraction Verification (10 tests)
# ===========================================================================

class TestRouteExtraction:

    def test_cockpit_autonomous_routes_imports_cleanly(self):
        import transports.api.cockpit_autonomous_routes as mod
        assert hasattr(mod, "configure")

    def test_cockpit_organism_routes_imports_cleanly(self):
        import transports.api.cockpit_organism_routes as mod
        assert hasattr(mod, "configure")

    def test_cockpit_entity_routes_imports_cleanly(self):
        import transports.api.cockpit_entity_routes as mod
        assert hasattr(mod, "configure")

    def test_cockpit_economy_routes_imports_cleanly(self):
        import transports.api.cockpit_economy_routes as mod
        assert hasattr(mod, "configure")

    def test_each_route_module_has_configure_function(self):
        import transports.api.cockpit_autonomous_routes as auto
        import transports.api.cockpit_organism_routes as org
        import transports.api.cockpit_entity_routes as ent
        import transports.api.cockpit_economy_routes as eco
        for mod in [auto, org, ent, eco]:
            assert callable(getattr(mod, "configure", None)), (
                f"{mod.__name__} missing callable configure()"
            )

    def test_each_route_module_exposes_router(self):
        import transports.api.cockpit_autonomous_routes as auto
        import transports.api.cockpit_organism_routes as org
        import transports.api.cockpit_entity_routes as ent
        import transports.api.cockpit_economy_routes as eco
        from fastapi import APIRouter
        assert isinstance(auto.autonomous_router, APIRouter)
        assert isinstance(org.organism_router, APIRouter)
        assert isinstance(ent.entity_router, APIRouter)
        assert isinstance(eco.economy_router, APIRouter)

    def test_cockpit_py_imports_cleanly(self):
        import transports.api.cockpit as mod
        assert hasattr(mod, "router")

    def test_cockpit_py_under_3000_lines(self):
        cockpit_path = os.path.join(
            "/opt/OS/.claude/worktrees/phase10-0-template-library",
            "transports", "api", "cockpit.py",
        )
        with open(cockpit_path) as f:
            line_count = sum(1 for _ in f)
        assert line_count < 3000, f"cockpit.py has {line_count} lines, exceeds 3000"

    def test_py_compile_on_all_route_modules(self):
        base = "/opt/OS/.claude/worktrees/phase10-0-template-library/transports/api"
        modules = [
            "cockpit_autonomous_routes.py",
            "cockpit_organism_routes.py",
            "cockpit_entity_routes.py",
            "cockpit_economy_routes.py",
        ]
        import py_compile
        for mod in modules:
            path = os.path.join(base, mod)
            # py_compile.compile raises on error
            py_compile.compile(path, doraise=True)

    def test_total_route_count_across_modules_gte_60(self):
        """Count route handler registrations across all cockpit modules."""
        base = "/opt/OS/.claude/worktrees/phase10-0-template-library/transports/api"
        files = [
            "cockpit.py",
            "cockpit_autonomous_routes.py",
            "cockpit_organism_routes.py",
            "cockpit_entity_routes.py",
            "cockpit_economy_routes.py",
        ]
        import re
        total = 0
        pattern = re.compile(r"router\.(get|post|put|delete|patch)\(|@\w+\.(get|post|put|delete|patch)\(")
        for fname in files:
            fpath = os.path.join(base, fname)
            if os.path.isfile(fpath):
                with open(fpath) as f:
                    content = f.read()
                total += len(pattern.findall(content))
        assert total >= 60, f"Total route count {total} is below 60"
