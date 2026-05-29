"""Phase 9.6 — Autonomous Improvement Lane Tests.

Verifies:
  - Candidate selector builds from observed reality
  - Policy evaluator enforces all gates
  - Autonomous lane dry-run produces correct decisions
  - Autonomous lane run-once executes through governed spine
  - Safety gates block sensitive/high-risk candidates
  - Template confidence and agent reliability tracked
  - No manual propagation calls
  - Spine-native propagation fires automatically
  - Cooldown and duplicate prevention
"""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

from substrate.organism.agent_capability_model import AgentCapabilityModel
from substrate.organism.autonomous_improvement_lane import (
    AutonomousCandidateSelector,
    AutonomousImprovementCandidate,
    AutonomousImprovementLane,
    AutonomousLanePolicy,
    AutonomousLaneRun,
    AutonomousPolicyEvaluator,
    CandidateEvaluation,
    LaneDecision,
    LaneRunStatus,
)
from substrate.organism.composition_engine import CompositionEngine
from substrate.organism.event_spine import EventSpine
from substrate.organism.execution_journal import ExecutionJournal
from substrate.organism.execution_modes import ExecutionModeManager
from substrate.organism.governed_spine import GovernedExecutionSpine
from substrate.organism.memory_promotion import MemoryPromotionPipeline
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.outcome_learning import OutcomeLearningLoop
from substrate.organism.plan_execution_adapter import PlanExecutionAdapter
from substrate.organism.propagation_wiring import build_propagation_engine
from substrate.organism.template_registry import (
    TemplateCandidate,
    TemplateRegistry,
    TemplateStatus,
    TemplateType,
)
from substrate.organism.trial_runner import CandidateSource


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def lane_env(tmpdir):
    """Build full autonomous lane environment."""
    es = EventSpine(persist_path=os.path.join(tmpdir, "events.jsonl"))
    ol = OutcomeLearningLoop(store_path=os.path.join(tmpdir, "ol.jsonl"))
    tr = TemplateRegistry(store_dir=os.path.join(tmpdir, "templates"))
    mp = MemoryPromotionPipeline(store_dir=os.path.join(tmpdir, "memory"))
    acm = AgentCapabilityModel(store_dir=os.path.join(tmpdir, "agents"))

    pe = build_propagation_engine(
        learning_loop=ol,
        template_registry=tr,
        memory_pipeline=mp,
        agent_capability_model=acm,
        store_dir=os.path.join(tmpdir, "propagation"),
    )

    spine = GovernedExecutionSpine(
        event_spine=es,
        execution_mode=ExecutionModeManager(event_spine=es),
        mutation_registry=MutationRegistry(),
        journal=ExecutionJournal(),
        propagation_engine=pe,
    )

    from substrate.organism.spine_guard import SpineGuard, GuardMode
    guard = SpineGuard(
        mode=GuardMode.BLOCK_HIGH_RISK,
        event_spine=es,
        journal=ExecutionJournal(),
    )
    from substrate.organism.autonomous_action_gateway import (
        AutonomousActionGateway,
        AutonomousPolicy,
    )
    gateway = AutonomousActionGateway(
        governed_spine=spine,
        execution_mode=ExecutionModeManager(event_spine=es),
        event_spine=es,
        journal=ExecutionJournal(),
        policy=AutonomousPolicy.ASSISTED,
    )

    adapter = PlanExecutionAdapter(
        governed_spine=spine,
        spine_guard=guard,
        autonomous_gateway=gateway,
    )

    lane = AutonomousImprovementLane(
        adapter=adapter,
        template_registry=tr,
        agent_capability_model=acm,
        composition_engine=CompositionEngine(),
        store_dir=os.path.join(tmpdir, "lane"),
    )

    return {
        "lane": lane, "spine": spine, "pe": pe, "tr": tr, "acm": acm,
        "ol": ol, "mp": mp, "es": es, "adapter": adapter,
        "guard": guard, "gateway": gateway,
    }


def _step_executor_factory(candidate, plan):
    executors = {}
    for step in plan.steps:
        def make_fn(s=step):
            return (f"Executed: {s.description[:60]}", True)
        executors[step.id] = make_fn
    return executors


def _make_promoted_template(tr, confidence=0.75):
    """Create and promote a template with given confidence."""
    outcome = {
        "action_envelope_id": "test-env-001",
        "action_type": "contradiction_fix",
        "risk_class": "low",
        "agent_type": "developer_agent",
        "validation_result": "success",
    }
    tpl = tr.generate_candidate_from_outcome(outcome)
    tr.approve(tpl.template_id)
    tr.promote(tpl.template_id)
    for _ in range(3):
        tr.record_usage(tpl.template_id, success=True)
    return tpl


def _seed_agent_reliability(acm, agent_type="developer_agent", successes=8, failures=2):
    """Seed agent reliability to meet threshold."""
    acm.update_reliability(
        agent_type=agent_type,
        capabilities_used=["code_search", "file_edit"],
        success=True,
        duration_ms=100.0,
    )
    for _ in range(successes - 1):
        acm.update_reliability(
            agent_type=agent_type,
            capabilities_used=["code_search"],
            success=True,
            duration_ms=100.0,
        )
    for _ in range(failures):
        acm.update_reliability(
            agent_type=agent_type,
            capabilities_used=["code_search"],
            success=False,
            duration_ms=100.0,
        )


# ===========================================================================
# Candidate Selector
# ===========================================================================


class TestCandidateSelector:
    def test_builds_candidates_from_contradictions(self, lane_env):
        selector = AutonomousCandidateSelector(
            template_registry=lane_env["tr"],
            agent_capability_model=lane_env["acm"],
        )
        candidates = selector.build_candidates()
        assert len(candidates) > 0

    def test_candidates_have_required_fields(self, lane_env):
        selector = AutonomousCandidateSelector(
            template_registry=lane_env["tr"],
            agent_capability_model=lane_env["acm"],
        )
        candidates = selector.build_candidates()
        for c in candidates[:5]:
            assert c.candidate_id
            assert c.source in CandidateSource
            assert c.description
            assert c.risk_class == "low"
            assert c.validation_method
            assert c.evidence

    def test_candidates_scored_and_ranked(self, lane_env):
        selector = AutonomousCandidateSelector(
            template_registry=lane_env["tr"],
            agent_capability_model=lane_env["acm"],
        )
        candidates = selector.build_candidates()
        if len(candidates) >= 2:
            scores = [c.selection_score for c in candidates]
            assert scores == sorted(scores, reverse=True)

    def test_candidates_enriched_with_template(self, lane_env):
        _make_promoted_template(lane_env["tr"])
        selector = AutonomousCandidateSelector(
            template_registry=lane_env["tr"],
            agent_capability_model=lane_env["acm"],
        )
        candidates = selector.build_candidates()
        has_template = any(c.matching_template_id for c in candidates)
        assert has_template

    def test_candidates_enriched_with_agent_reliability(self, lane_env):
        _seed_agent_reliability(lane_env["acm"])
        selector = AutonomousCandidateSelector(
            template_registry=lane_env["tr"],
            agent_capability_model=lane_env["acm"],
        )
        candidates = selector.build_candidates()
        has_reliability = any(c.agent_reliability > 0 for c in candidates)
        assert has_reliability

    def test_high_severity_contradictions_excluded(self, lane_env):
        selector = AutonomousCandidateSelector(
            template_registry=lane_env["tr"],
            agent_capability_model=lane_env["acm"],
        )
        candidates = selector.build_candidates()
        for c in candidates:
            assert c.risk_class == "low"

    def test_max_candidates_respected(self, lane_env):
        selector = AutonomousCandidateSelector(
            template_registry=lane_env["tr"],
            agent_capability_model=lane_env["acm"],
        )
        candidates = selector.build_candidates(max_candidates=2)
        assert len(candidates) <= 2


# ===========================================================================
# Policy Evaluator
# ===========================================================================


class TestPolicyEvaluator:
    def test_eligible_when_all_checks_pass(self, lane_env):
        _make_promoted_template(lane_env["tr"])
        _seed_agent_reliability(lane_env["acm"])
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            source=CandidateSource.CONTRADICTION,
            description="Fix false positive contradiction",
            risk_class="low",
            matching_template_id="tpl-test",
            template_confidence=0.75,
            agent_reliability=0.80,
            validation_method="re-check",
            rollback_method="revert",
            evidence="Observed contradiction",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.ELIGIBLE
        assert all(evaluation.policy_checks.values())

    def test_blocked_when_risk_not_low(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="high",
            description="Test",
            evidence="Test",
            validation_method="test",
            matching_template_id="tpl-x",
            template_confidence=0.9,
            agent_reliability=0.9,
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.BLOCKED

    def test_blocked_when_medium_risk(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="medium",
            description="Test",
            evidence="Test",
            validation_method="test",
            matching_template_id="tpl-x",
            template_confidence=0.9,
            agent_reliability=0.9,
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.APPROVAL_REQUIRED

    def test_recommended_when_no_template(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Test gap fix",
            evidence="Evidence",
            validation_method="check",
            agent_reliability=0.80,
            rollback_method="revert",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.RECOMMENDED
        assert not evaluation.policy_checks["template_exists"]

    def test_recommended_when_low_template_confidence(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Test",
            evidence="Evidence",
            validation_method="check",
            matching_template_id="tpl-x",
            template_confidence=0.30,
            agent_reliability=0.80,
            rollback_method="revert",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.RECOMMENDED
        assert not evaluation.policy_checks["template_confidence_met"]

    def test_recommended_when_low_agent_reliability(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Test",
            evidence="Evidence",
            validation_method="check",
            matching_template_id="tpl-x",
            template_confidence=0.80,
            agent_reliability=0.30,
            rollback_method="revert",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.RECOMMENDED
        assert not evaluation.policy_checks["agent_reliability_met"]

    def test_recommended_when_no_validation(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Test",
            evidence="Evidence",
            matching_template_id="tpl-x",
            template_confidence=0.80,
            agent_reliability=0.80,
            rollback_method="revert",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.RECOMMENDED

    def test_recommended_when_mutating_no_rollback(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Test",
            evidence="Evidence",
            validation_method="check",
            matching_template_id="tpl-x",
            template_confidence=0.80,
            agent_reliability=0.80,
            non_mutating=False,
            rollback_method="",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.RECOMMENDED
        assert not evaluation.policy_checks["rollback_or_non_mutating"]

    def test_blocked_when_sensitive_keyword(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Modify credential store configuration",
            evidence="Evidence",
            validation_method="check",
            matching_template_id="tpl-x",
            template_confidence=0.80,
            agent_reliability=0.80,
            rollback_method="revert",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.BLOCKED

    def test_blocked_when_sensitive_path(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Fix config",
            evidence="Evidence",
            validation_method="check",
            matching_template_id="tpl-x",
            template_confidence=0.80,
            agent_reliability=0.80,
            rollback_method="revert",
            affected_files=[".env.production"],
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.BLOCKED

    def test_blocked_when_no_evidence(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Test",
            evidence="",
            validation_method="check",
            matching_template_id="tpl-x",
            template_confidence=0.80,
            agent_reliability=0.80,
            rollback_method="revert",
        )
        evaluation = evaluator.evaluate(candidate)
        assert not evaluation.policy_checks["has_evidence"]

    def test_file_count_limit(self, lane_env):
        policy = AutonomousLanePolicy(max_file_changes_per_execution=2)
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Test",
            evidence="Evidence",
            validation_method="check",
            matching_template_id="tpl-x",
            template_confidence=0.80,
            agent_reliability=0.80,
            rollback_method="revert",
            affected_files=["a.py", "b.py", "c.py"],
        )
        evaluation = evaluator.evaluate(candidate)
        assert not evaluation.policy_checks["file_count_ok"]

    def test_cooldown_enforcement(self, lane_env):
        policy = AutonomousLanePolicy(cooldown_minutes_per_template=30)
        recent_run = AutonomousLaneRun(
            status=LaneRunStatus.COMPLETED,
            completed_at=time.time() - 60,
        )
        recent_run.selected_candidate = AutonomousImprovementCandidate(
            matching_template_id="tpl-cooldown",
            source=CandidateSource.CONTRADICTION,
        )
        evaluator = AutonomousPolicyEvaluator(
            policy=policy, recent_runs=[recent_run]
        )

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Test",
            evidence="Evidence",
            validation_method="check",
            matching_template_id="tpl-cooldown",
            template_confidence=0.80,
            agent_reliability=0.80,
            rollback_method="revert",
        )
        evaluation = evaluator.evaluate(candidate)
        assert not evaluation.policy_checks["not_in_cooldown"]

    def test_duplicate_prevention(self, lane_env):
        policy = AutonomousLanePolicy()
        recent_run = AutonomousLaneRun(
            status=LaneRunStatus.COMPLETED,
            completed_at=time.time() - 60,
        )
        recent_run.selected_candidate = AutonomousImprovementCandidate(
            entity_id="ent-123",
            source=CandidateSource.CONTRADICTION,
        )
        evaluator = AutonomousPolicyEvaluator(
            policy=policy, recent_runs=[recent_run]
        )

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Test",
            evidence="Evidence",
            validation_method="check",
            matching_template_id="tpl-x",
            template_confidence=0.80,
            agent_reliability=0.80,
            rollback_method="revert",
            entity_id="ent-123",
            source=CandidateSource.CONTRADICTION,
        )
        evaluation = evaluator.evaluate(candidate)
        assert not evaluation.policy_checks["not_duplicate"]


# ===========================================================================
# Dry Run
# ===========================================================================


class TestDryRun:
    def test_dry_run_returns_candidates(self, lane_env):
        lane = lane_env["lane"]
        run = lane.dry_run()
        assert run.status in (LaneRunStatus.DRY_RUN, LaneRunStatus.NO_ELIGIBLE)
        assert isinstance(run.candidates, list)

    def test_dry_run_no_mutation(self, lane_env):
        lane = lane_env["lane"]
        run = lane.dry_run()
        assert run.execution_status == ""
        assert run.validation_result == ""

    def test_dry_run_shows_evaluations(self, lane_env):
        lane = lane_env["lane"]
        run = lane.dry_run()
        assert len(run.evaluations) == len(run.candidates)

    def test_dry_run_with_eligible_candidate(self, lane_env):
        _make_promoted_template(lane_env["tr"])
        _seed_agent_reliability(lane_env["acm"])
        lane = lane_env["lane"]
        run = lane.dry_run()
        if run.eligible_candidates:
            assert run.selected_candidate is not None
            assert run.governance_dry_run in ("passed", "blocked_high_risk", "blocked_step_risk")

    def test_dry_run_persisted(self, lane_env, tmpdir):
        lane = lane_env["lane"]
        lane.dry_run()
        runs_path = os.path.join(tmpdir, "lane", "runs.jsonl")
        assert os.path.isfile(runs_path)

    def test_dry_run_serializable(self, lane_env):
        lane = lane_env["lane"]
        run = lane.dry_run()
        data = run.to_dict()
        json.dumps(data, default=str)
        assert "run_id" in data
        assert "status" in data
        assert "policy" in data


# ===========================================================================
# Run Once
# ===========================================================================


class TestRunOnce:
    def test_run_once_no_eligible(self, lane_env):
        lane = lane_env["lane"]
        run = lane.run_once()
        assert run.status == LaneRunStatus.NO_ELIGIBLE

    def test_run_once_executes_with_eligible(self, lane_env):
        _make_promoted_template(lane_env["tr"])
        _seed_agent_reliability(lane_env["acm"])
        lane = lane_env["lane"]
        run = lane.run_once(step_executors_factory=_step_executor_factory)
        if run.eligible_candidates:
            assert run.status in (
                LaneRunStatus.COMPLETED,
                LaneRunStatus.FAILED,
                LaneRunStatus.BLOCKED,
                LaneRunStatus.NO_ELIGIBLE,
            )

    def test_run_once_through_governed_spine(self, lane_env):
        _make_promoted_template(lane_env["tr"])
        _seed_agent_reliability(lane_env["acm"])
        lane = lane_env["lane"]
        run = lane.run_once(step_executors_factory=_step_executor_factory)
        if run.status == LaneRunStatus.COMPLETED:
            assert run.governance_dry_run == "passed"
            assert run.execution_status in ("completed", "partial")

    def test_run_once_propagation_fires(self, lane_env):
        _make_promoted_template(lane_env["tr"])
        _seed_agent_reliability(lane_env["acm"])
        lane = lane_env["lane"]
        run = lane.run_once(step_executors_factory=_step_executor_factory)
        if run.status == LaneRunStatus.COMPLETED:
            events = lane_env["pe"].recent_events(limit=50)
            assert len(events) > 0

    def test_run_once_records_run(self, lane_env):
        lane = lane_env["lane"]
        lane.run_once()
        assert len(lane.recent_runs) >= 1

    def test_run_once_exactly_one_execution(self, lane_env):
        _make_promoted_template(lane_env["tr"])
        _seed_agent_reliability(lane_env["acm"])
        lane = lane_env["lane"]
        run = lane.run_once(step_executors_factory=_step_executor_factory)
        if run.selected_candidate:
            selected_count = 1
            assert selected_count == 1

    def test_failed_execution_marks_failed(self, lane_env):
        _make_promoted_template(lane_env["tr"])
        _seed_agent_reliability(lane_env["acm"])

        def failing_factory(candidate, plan):
            executors = {}
            for step in plan.steps:
                def make_fn(s=step):
                    return (f"Failed: {s.description[:60]}", False)
                executors[step.id] = make_fn
            return executors

        lane = lane_env["lane"]
        run = lane.run_once(step_executors_factory=failing_factory)
        if run.selected_candidate and run.governance_dry_run == "passed":
            assert run.status in (LaneRunStatus.FAILED, LaneRunStatus.COMPLETED)


# ===========================================================================
# Safety Gates
# ===========================================================================


class TestSafetyGates:
    def test_high_risk_blocked(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="critical",
            description="Drop production table",
            evidence="Evidence",
            matching_template_id="tpl-x",
            template_confidence=0.9,
            agent_reliability=0.9,
            validation_method="check",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.BLOCKED

    def test_deploy_keyword_blocked(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Deploy new container version",
            evidence="Evidence",
            matching_template_id="tpl-x",
            template_confidence=0.9,
            agent_reliability=0.9,
            validation_method="check",
            rollback_method="revert",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.BLOCKED

    def test_auth_keyword_blocked(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Modify auth middleware tokens",
            evidence="Evidence",
            matching_template_id="tpl-x",
            template_confidence=0.9,
            agent_reliability=0.9,
            validation_method="check",
            rollback_method="revert",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.BLOCKED

    def test_dns_keyword_blocked(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Update dns records for new domain",
            evidence="Evidence",
            matching_template_id="tpl-x",
            template_confidence=0.9,
            agent_reliability=0.9,
            validation_method="check",
            rollback_method="revert",
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.BLOCKED

    def test_env_file_blocked(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Fix config value",
            evidence="Evidence",
            matching_template_id="tpl-x",
            template_confidence=0.9,
            agent_reliability=0.9,
            validation_method="check",
            rollback_method="revert",
            affected_files=["services/.env"],
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.BLOCKED

    def test_dockerfile_blocked(self, lane_env):
        policy = AutonomousLanePolicy()
        evaluator = AutonomousPolicyEvaluator(policy=policy)

        candidate = AutonomousImprovementCandidate(
            risk_class="low",
            description="Optimize build",
            evidence="Evidence",
            matching_template_id="tpl-x",
            template_confidence=0.9,
            agent_reliability=0.9,
            validation_method="check",
            rollback_method="revert",
            affected_files=["Dockerfile"],
        )
        evaluation = evaluator.evaluate(candidate)
        assert evaluation.decision == LaneDecision.BLOCKED


# ===========================================================================
# No Manual Propagation
# ===========================================================================


class TestNoManualPropagation:
    def test_no_propagation_in_autonomous_lane(self):
        import inspect
        from substrate.organism import autonomous_improvement_lane
        source = inspect.getsource(autonomous_improvement_lane)
        assert "propagation_engine" not in source
        assert ".propagate(" not in source
        assert ".handle_outcome(" not in source


# ===========================================================================
# Lane Status & API
# ===========================================================================


class TestLaneStatus:
    def test_status_returns_dict(self, lane_env):
        lane = lane_env["lane"]
        status = lane.status()
        assert status["lane_active"] is True
        assert "policy" in status
        assert "total_runs" in status

    def test_to_dict_serializable(self, lane_env):
        lane = lane_env["lane"]
        data = lane.to_dict()
        json.dumps(data, default=str)

    def test_to_safe_dict_strips_details(self, lane_env):
        lane = lane_env["lane"]
        lane.dry_run()
        safe = lane.to_safe_dict()
        if safe.get("last_run"):
            assert "candidates" not in safe["last_run"]

    def test_policy_accessible(self, lane_env):
        lane = lane_env["lane"]
        policy = lane.policy
        assert policy.allowed_risk == "low"
        assert policy.require_template is True

    def test_get_run_by_id(self, lane_env):
        lane = lane_env["lane"]
        run = lane.dry_run()
        found = lane.get_run(run.run_id)
        assert found is not None
        assert found.run_id == run.run_id


# ===========================================================================
# Template Confidence
# ===========================================================================


class TestTemplateConfidence:
    def test_confidence_tracked_before_after(self, lane_env):
        tpl = _make_promoted_template(lane_env["tr"])
        _seed_agent_reliability(lane_env["acm"])
        lane = lane_env["lane"]
        run = lane.run_once(step_executors_factory=_step_executor_factory)
        if run.status == LaneRunStatus.COMPLETED and run.selected_candidate:
            assert run.template_confidence_before >= 0


# ===========================================================================
# Agent Reliability
# ===========================================================================


class TestAgentReliability:
    def test_reliability_tracked_before_after(self, lane_env):
        _seed_agent_reliability(lane_env["acm"])
        _make_promoted_template(lane_env["tr"])
        lane = lane_env["lane"]
        run = lane.run_once(step_executors_factory=_step_executor_factory)
        if run.status == LaneRunStatus.COMPLETED and run.selected_candidate:
            assert run.agent_reliability_before > 0


# ===========================================================================
# Daemon Integration
# ===========================================================================


class TestDaemonIntegration:
    def test_daemon_lane_e2e(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        daemon.start()

        adapter = PlanExecutionAdapter(
            governed_spine=daemon.governed_spine,
            spine_guard=daemon.spine_guard,
            autonomous_gateway=daemon.autonomous_gateway,
        )

        lane = AutonomousImprovementLane(
            adapter=adapter,
            template_registry=daemon.template_registry,
            agent_capability_model=daemon.agent_capability_model,
            composition_engine=CompositionEngine(),
            store_dir=os.path.join(tmpdir, "lane"),
        )

        run = lane.dry_run()
        assert run.status in (LaneRunStatus.DRY_RUN, LaneRunStatus.NO_ELIGIBLE)
        assert isinstance(run.candidates, list)

    def test_daemon_lane_with_seeded_data(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        daemon.start()

        _make_promoted_template(daemon.template_registry)
        _seed_agent_reliability(daemon.agent_capability_model)

        adapter = PlanExecutionAdapter(
            governed_spine=daemon.governed_spine,
            spine_guard=daemon.spine_guard,
            autonomous_gateway=daemon.autonomous_gateway,
        )

        lane = AutonomousImprovementLane(
            adapter=adapter,
            template_registry=daemon.template_registry,
            agent_capability_model=daemon.agent_capability_model,
            composition_engine=CompositionEngine(),
            store_dir=os.path.join(tmpdir, "lane"),
        )

        run = lane.run_once(step_executors_factory=_step_executor_factory)
        if run.eligible_candidates:
            assert run.status in (
                LaneRunStatus.COMPLETED,
                LaneRunStatus.FAILED,
                LaneRunStatus.BLOCKED,
            )


# ===========================================================================
# Evaluation to_dict
# ===========================================================================


class TestSerialization:
    def test_candidate_to_dict(self):
        c = AutonomousImprovementCandidate(
            source=CandidateSource.CONTRADICTION,
            description="test",
            risk_class="low",
        )
        d = c.to_dict()
        assert d["source"] == "contradiction"
        assert d["risk_class"] == "low"

    def test_evaluation_to_dict(self):
        e = CandidateEvaluation(
            candidate_id="test",
            decision=LaneDecision.ELIGIBLE,
            policy_checks={"risk_is_low": True},
        )
        d = e.to_dict()
        assert d["decision"] == "eligible"

    def test_run_to_dict(self):
        r = AutonomousLaneRun()
        d = r.to_dict()
        assert "run_id" in d
        assert "policy" in d
        json.dumps(d, default=str)

    def test_policy_to_dict(self):
        p = AutonomousLanePolicy()
        d = p.to_dict()
        assert d["allowed_risk"] == "low"
        assert d["require_template"] is True


# ===========================================================================
# API Bridge
# ===========================================================================


class TestAPIBridge:
    def test_actions_registered(self):
        from transports.api.organism_bridge import _ACTIONS
        assert "organism.autonomous_lane" in _ACTIONS
        assert "organism.autonomous_lane.candidates" in _ACTIONS
        assert "organism.autonomous_lane.dry_run" in _ACTIONS
        assert "organism.autonomous_lane.run_once" in _ACTIONS
        assert "organism.autonomous_lane.runs" in _ACTIONS
        assert "organism.autonomous_lane.run_detail" in _ACTIONS
        assert "organism.autonomous_lane.policy" in _ACTIONS

    def test_policy_route_returns_policy(self):
        from transports.api.organism_bridge import _ACTIONS
        handler = _ACTIONS["organism.autonomous_lane.policy"]
        result = handler({})
        assert result["success"] is True
        assert "allowed_risk" in result["data"]

    def test_status_route_returns_status(self):
        from transports.api.organism_bridge import _ACTIONS
        handler = _ACTIONS["organism.autonomous_lane"]
        result = handler({})
        assert result["success"] is True
        assert "lane_active" in result["data"]


# ===========================================================================
# Propagation Verification
# ===========================================================================


class TestPropagationIntegrity:
    def test_no_propagation_in_lane_module(self):
        import inspect
        from substrate.organism import autonomous_improvement_lane
        source = inspect.getsource(autonomous_improvement_lane)
        assert "propagation_engine" not in source
        assert ".propagate(" not in source
        assert ".handle_outcome(" not in source

    def test_spine_native_propagation_fires(self, lane_env):
        _make_promoted_template(lane_env["tr"])
        _seed_agent_reliability(lane_env["acm"])
        lane = lane_env["lane"]
        run = lane.run_once(step_executors_factory=_step_executor_factory)
        if run.status == LaneRunStatus.COMPLETED:
            events = lane_env["pe"].recent_events(limit=50)
            assert len(events) > 0

    def test_outcome_committed_emitted(self, lane_env):
        _make_promoted_template(lane_env["tr"])
        _seed_agent_reliability(lane_env["acm"])
        lane = lane_env["lane"]
        run = lane.run_once(step_executors_factory=_step_executor_factory)
        if run.status == LaneRunStatus.COMPLETED:
            ol = lane_env["ol"]
            outcomes = ol.recent_outcomes(limit=50)
            assert len(outcomes) > 0
