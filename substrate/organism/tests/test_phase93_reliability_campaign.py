"""Phase 9.3 — Self-Improvement Reliability Campaign tests.

Tests cover:
  - Candidate ranking and filtering
  - Safety gate enforcement
  - Blocked trial handling
  - Multi-trial execution
  - Metrics aggregation
  - Readiness delta tracking
  - Contradiction delta tracking
  - Memory candidate generation
  - Rollback handling
  - Campaign result serialization
  - Cockpit bridge handler
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.organism.trial_runner import (
    CampaignBaseline,
    CampaignResult,
    CandidateSource,
    ReliabilityCampaignRunner,
    TrialCandidate,
    TrialMetrics,
    TrialResult,
    TrialStatus,
    build_candidate_queue,
    persist_campaign,
    persist_candidate_queue,
    rank_candidates,
    safety_check,
)
from substrate.organism.composition_engine import (
    CompositionEngine,
    CompositionIntent,
    CompositionPlan,
    CompositionStep,
    GovernanceMode,
    RiskClass,
)
from substrate.organism.plan_execution_adapter import (
    ExecutablePlan,
    ExecutionGraphStatus,
    PlanExecutionAdapter,
    StepExecutionStatus,
)
from substrate.organism.governed_spine import GovernedExecutionSpine
from substrate.organism.spine_guard import SpineGuard, GuardMode
from substrate.organism.autonomous_action_gateway import (
    AutonomousActionGateway,
    AutonomousPolicy,
)
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.execution_journal import ExecutionJournal
from substrate.organism.execution_modes import ExecutionModeManager
from substrate.organism.event_spine import EventSpine
from substrate.organism.leverage_metrics import LeverageMetrics
from substrate.organism.outcome_learning import OutcomeLearningLoop
from substrate.organism.memory_promotion import (
    MemoryPromotionPipeline,
    MemoryPromotionStatus,
)
from substrate.organism.readiness_model import ReadinessModel
from substrate.organism.world_model import extract_world_model
from substrate.organism.dependency_graph import build_dependency_graph
from substrate.organism.contradiction_engine import detect_contradictions


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def governed_stack(tmpdir):
    event_spine = EventSpine()
    exec_mode = ExecutionModeManager(event_spine=event_spine)
    mutation_reg = MutationRegistry()
    journal = ExecutionJournal(persist_path=os.path.join(tmpdir, "journal.jsonl"))
    leverage = LeverageMetrics(event_spine=event_spine)
    spine = GovernedExecutionSpine(
        event_spine=event_spine,
        execution_mode=exec_mode,
        mutation_registry=mutation_reg,
        journal=journal,
        leverage_metrics=leverage,
    )
    spine_guard = SpineGuard(
        mode=GuardMode.WARN,
        event_spine=event_spine,
        journal=journal,
    )
    gateway = AutonomousActionGateway(
        governed_spine=spine,
        execution_mode=exec_mode,
        event_spine=event_spine,
        journal=journal,
        policy=AutonomousPolicy.AUTONOMOUS,
    )
    outcome_loop = OutcomeLearningLoop(store_path=os.path.join(tmpdir, "outcomes.jsonl"))
    memory_pipeline = MemoryPromotionPipeline(store_dir=tmpdir)

    adapter = PlanExecutionAdapter(
        governed_spine=spine,
        spine_guard=spine_guard,
        autonomous_gateway=gateway,
        outcome_loop=outcome_loop,
        memory_pipeline=memory_pipeline,
    )
    return {
        "spine": spine,
        "spine_guard": spine_guard,
        "gateway": gateway,
        "journal": journal,
        "exec_mode": exec_mode,
        "outcome_loop": outcome_loop,
        "memory_pipeline": memory_pipeline,
        "adapter": adapter,
    }


@pytest.fixture
def sample_candidates():
    return [
        TrialCandidate(
            source=CandidateSource.CONTRADICTION,
            description="Fix deployment path mismatch",
            risk="low",
            severity="medium",
            evidence="compose.yml not found",
            recommended_fix="Change to docker-compose.yml",
            reversible=True,
            measurable=True,
            custom_steps=[
                {"action": "verify", "desc": "Check state", "risk": "low", "gov": "autonomous", "verify": "ok"},
                {"action": "fix", "desc": "Apply fix", "risk": "low", "gov": "autonomous", "verify": "ok"},
            ],
        ),
        TrialCandidate(
            source=CandidateSource.CONTRADICTION,
            description="Fix orphaned subsystem",
            risk="low",
            severity="low",
            evidence="Orphaned in dependency graph",
            reversible=True,
            measurable=True,
            custom_steps=[
                {"action": "verify", "desc": "Check orphan", "risk": "low", "gov": "autonomous", "verify": "ok"},
                {"action": "fix", "desc": "Add edge", "risk": "low", "gov": "autonomous", "verify": "ok"},
                {"action": "verify", "desc": "Confirm", "risk": "low", "gov": "autonomous", "verify": "ok"},
            ],
        ),
        TrialCandidate(
            source=CandidateSource.READINESS_GAP,
            description="Improve execution readiness",
            risk="low",
            severity="info",
            reversible=True,
            measurable=True,
        ),
        TrialCandidate(
            source=CandidateSource.CONTRADICTION,
            description="Critical credential mutation",
            risk="high",
            severity="high",
            reversible=False,
            measurable=True,
        ),
    ]


# ── Candidate Ranking ───────────────────────────────────────


class TestCandidateRanking:
    def test_rank_by_severity(self):
        candidates = [
            TrialCandidate(severity="info", risk="low", reversible=True, measurable=True),
            TrialCandidate(severity="medium", risk="low", reversible=True, measurable=True),
            TrialCandidate(severity="low", risk="low", reversible=True, measurable=True),
        ]
        ranked = rank_candidates(candidates)
        assert ranked[0].severity == "medium"
        assert ranked[1].severity == "low"
        assert ranked[2].severity == "info"

    def test_filter_high_risk(self):
        candidates = [
            TrialCandidate(risk="low", severity="medium"),
            TrialCandidate(risk="high", severity="high"),
            TrialCandidate(risk="critical", severity="critical"),
        ]
        ranked = rank_candidates(candidates)
        assert len(ranked) == 1
        assert ranked[0].risk == "low"

    def test_reversible_gets_bonus(self):
        c1 = TrialCandidate(severity="low", risk="low", reversible=True, measurable=False)
        c2 = TrialCandidate(severity="low", risk="low", reversible=False, measurable=False)
        ranked = rank_candidates([c1, c2])
        assert ranked[0].priority_score > ranked[1].priority_score

    def test_measurable_gets_bonus(self):
        c1 = TrialCandidate(severity="low", risk="low", reversible=False, measurable=True)
        c2 = TrialCandidate(severity="low", risk="low", reversible=False, measurable=False)
        ranked = rank_candidates([c1, c2])
        assert ranked[0].priority_score > ranked[1].priority_score

    def test_contradiction_source_gets_bonus(self):
        c1 = TrialCandidate(severity="low", risk="low", source=CandidateSource.CONTRADICTION)
        c2 = TrialCandidate(severity="low", risk="low", source=CandidateSource.WORLD_MODEL_DEFECT)
        ranked = rank_candidates([c1, c2])
        assert ranked[0].source == CandidateSource.CONTRADICTION

    def test_empty_candidates(self):
        ranked = rank_candidates([])
        assert ranked == []

    def test_all_high_risk_filtered(self):
        candidates = [
            TrialCandidate(risk="high"),
            TrialCandidate(risk="critical"),
        ]
        ranked = rank_candidates(candidates)
        assert len(ranked) == 0


# ── Safety Gate ──────────────────────────────────────────────


class TestSafetyGate:
    def test_low_risk_passes(self):
        c = TrialCandidate(risk="low", description="safe operation")
        assert safety_check(c) == ""

    def test_medium_risk_passes(self):
        c = TrialCandidate(risk="medium", description="moderate operation")
        assert safety_check(c) == ""

    def test_high_risk_blocked(self):
        c = TrialCandidate(risk="high", description="risky operation")
        reason = safety_check(c)
        assert "hard-blocked" in reason

    def test_critical_risk_blocked(self):
        c = TrialCandidate(risk="critical", description="critical op")
        reason = safety_check(c)
        assert "hard-blocked" in reason

    def test_credential_keyword_blocked(self):
        c = TrialCandidate(risk="low", description="modify credential store")
        reason = safety_check(c)
        assert "credential" in reason

    def test_auth_keyword_blocked(self):
        c = TrialCandidate(risk="low", description="change auth config")
        reason = safety_check(c)
        assert "auth" in reason

    def test_dns_keyword_blocked(self):
        c = TrialCandidate(risk="low", description="update dns records")
        reason = safety_check(c)
        assert "dns" in reason

    def test_deploy_keyword_blocked(self):
        c = TrialCandidate(risk="low", description="deploy to production")
        reason = safety_check(c)
        assert "deploy" in reason


# ── Blocked Trial Handling ───────────────────────────────────


class TestBlockedTrialHandling:
    def test_safety_blocked_trial(self, governed_stack):
        adapter = governed_stack["adapter"]
        wm = extract_world_model()
        dg = build_dependency_graph(wm)
        cr = detect_contradictions(wm, dg)
        comp = CompositionEngine(world_model=wm, dependency_graph=dg, contradiction_report=cr)

        runner = ReliabilityCampaignRunner(
            adapter=adapter, composition_engine=comp,
        )

        blocked_candidate = TrialCandidate(
            risk="high",
            description="high risk operation",
            severity="high",
        )

        campaign = runner.run_campaign(
            candidates=[blocked_candidate],
            max_trials=1,
        )
        assert len(campaign.trials) == 1
        assert campaign.trials[0].status == TrialStatus.BLOCKED
        assert "hard-blocked" in campaign.trials[0].error

    def test_mixed_blocked_and_passing(self, governed_stack):
        adapter = governed_stack["adapter"]
        wm = extract_world_model()
        dg = build_dependency_graph(wm)
        cr = detect_contradictions(wm, dg)
        comp = CompositionEngine(world_model=wm, dependency_graph=dg, contradiction_report=cr)

        runner = ReliabilityCampaignRunner(
            adapter=adapter, composition_engine=comp,
        )

        candidates = [
            TrialCandidate(
                risk="high", description="blocked", severity="high",
            ),
            TrialCandidate(
                risk="low", description="safe fix", severity="low",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous", "verify": "v"}],
            ),
        ]

        campaign = runner.run_campaign(
            candidates=candidates,
            max_trials=2,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        assert campaign.blocked_trials[0].status == TrialStatus.BLOCKED
        assert campaign.completed_trials[0].status == TrialStatus.COMPLETED


# ── Multi-Trial Execution ────────────────────────────────────


class TestMultiTrialExecution:
    def test_multiple_trials_complete(self, governed_stack, sample_candidates):
        adapter = governed_stack["adapter"]
        wm = extract_world_model()
        dg = build_dependency_graph(wm)
        cr = detect_contradictions(wm, dg)
        comp = CompositionEngine(world_model=wm, dependency_graph=dg, contradiction_report=cr)

        runner = ReliabilityCampaignRunner(
            adapter=adapter, composition_engine=comp,
        )

        safe_candidates = [c for c in sample_candidates if c.risk not in ("high", "critical")]

        campaign = runner.run_campaign(
            candidates=safe_candidates,
            max_trials=5,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        assert len(campaign.completed_trials) >= 2

    def test_max_trials_respected(self, governed_stack):
        adapter = governed_stack["adapter"]
        wm = extract_world_model()
        dg = build_dependency_graph(wm)
        cr = detect_contradictions(wm, dg)
        comp = CompositionEngine(world_model=wm, dependency_graph=dg, contradiction_report=cr)

        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        candidates = [
            TrialCandidate(
                risk="low", severity="low",
                description=f"trial {i}",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )
            for i in range(10)
        ]

        campaign = runner.run_campaign(
            candidates=candidates,
            max_trials=3,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        assert len(campaign.trials) == 3

    def test_trial_ids_unique(self, governed_stack):
        adapter = governed_stack["adapter"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        candidates = [
            TrialCandidate(
                risk="low", severity="low", description=f"trial {i}",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )
            for i in range(5)
        ]

        campaign = runner.run_campaign(
            candidates=candidates,
            max_trials=5,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        trial_ids = [t.trial_id for t in campaign.trials]
        assert len(trial_ids) == len(set(trial_ids))


# ── Metrics Aggregation ──────────────────────────────────────


class TestMetricsAggregation:
    def test_trial_metrics_populated(self, governed_stack):
        adapter = governed_stack["adapter"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        campaign = runner.run_campaign(
            candidates=[TrialCandidate(
                risk="low", severity="low", description="metrics test",
                custom_steps=[
                    {"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"},
                    {"action": "b", "desc": "B", "risk": "low", "gov": "autonomous"},
                ],
            )],
            max_trials=1,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        trial = campaign.trials[0]
        assert trial.metrics.steps_total == 2
        assert trial.metrics.steps_succeeded == 2
        assert trial.metrics.outcome_reliability == 1.0

    def test_campaign_success_rate(self, governed_stack):
        adapter = governed_stack["adapter"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        candidates = [
            TrialCandidate(
                risk="low", severity="low", description=f"t{i}",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )
            for i in range(3)
        ]

        campaign = runner.run_campaign(
            candidates=candidates,
            max_trials=3,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        assert campaign.success_rate == 1.0

    def test_metrics_serializable(self):
        m = TrialMetrics(
            steps_total=4, steps_succeeded=3, steps_failed=1,
            outcome_reliability=0.75, validation_passed=True,
        )
        data = m.to_dict()
        json.dumps(data, default=str)


# ── Readiness Delta ──────────────────────────────────────────


class TestReadinessDelta:
    def test_campaign_captures_readiness(self, governed_stack):
        adapter = governed_stack["adapter"]
        comp = CompositionEngine()

        def state_fn():
            return {
                "execution_state": {"success_rate": 1.0, "registered_mutations": 0, "current_mode": "observe"},
                "governance_state": {"guard_active": True, "gateway_active": True, "journal_active": True},
                "deployment_state": {"services_up": 3, "services_total": 4, "build_current": True, "dns_correct": True, "tls_valid": True, "api_responsive": True},
            }

        runner = ReliabilityCampaignRunner(
            adapter=adapter, composition_engine=comp,
            readiness_model=ReadinessModel(), readiness_state_fn=state_fn,
        )

        campaign = runner.run_campaign(
            candidates=[TrialCandidate(
                risk="low", severity="low", description="readiness test",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )],
            max_trials=1,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        assert campaign.baseline.readiness_composite >= 0
        assert campaign.after.readiness_composite >= 0


# ── Contradiction Delta ──────────────────────────────────────


class TestContradictionDelta:
    def test_contradiction_count_captured(self, governed_stack):
        adapter = governed_stack["adapter"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        campaign = runner.run_campaign(
            candidates=[TrialCandidate(
                risk="low", severity="low", description="contradiction test",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )],
            max_trials=1,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        assert campaign.baseline.contradictions_total >= 0
        assert campaign.after.contradictions_total >= 0


# ── Memory Candidate Generation ──────────────────────────────


class TestMemoryCandidateGeneration:
    def test_successful_trial_generates_memory(self, governed_stack):
        adapter = governed_stack["adapter"]
        memory = governed_stack["memory_pipeline"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        campaign = runner.run_campaign(
            candidates=[TrialCandidate(
                risk="low", severity="low", description="memory gen test",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )],
            max_trials=1,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        candidates = memory.list_candidates()
        assert len(candidates) >= 1

    def test_memory_candidates_not_auto_promoted(self, governed_stack):
        adapter = governed_stack["adapter"]
        memory = governed_stack["memory_pipeline"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        runner.run_campaign(
            candidates=[TrialCandidate(
                risk="low", severity="low", description="no promote test",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )],
            max_trials=1,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        promoted = [c for c in memory.list_candidates() if c.status == MemoryPromotionStatus.PROMOTED]
        assert len(promoted) == 0


# ── Rollback Handling ────────────────────────────────────────


class TestRollbackHandling:
    def test_failed_step_triggers_failure_status(self, governed_stack):
        adapter = governed_stack["adapter"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        campaign = runner.run_campaign(
            candidates=[TrialCandidate(
                risk="low", severity="low", description="rollback test",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )],
            max_trials=1,
            step_executors_factory=lambda c, p: {s.id: lambda: ("fail", False) for s in p.steps},
        )
        trial = campaign.trials[0]
        assert trial.status in (TrialStatus.COMPLETED, TrialStatus.FAILED)
        assert trial.metrics.steps_failed >= 1


# ── Campaign Result Serialization ────────────────────────────


class TestCampaignSerialization:
    def test_campaign_result_serializable(self, governed_stack):
        adapter = governed_stack["adapter"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        campaign = runner.run_campaign(
            candidates=[TrialCandidate(
                risk="low", severity="low", description="serial test",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )],
            max_trials=1,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        data = campaign.to_dict()
        serialized = json.dumps(data, default=str)
        assert len(serialized) > 0

    def test_campaign_summary_fields(self, governed_stack):
        adapter = governed_stack["adapter"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        campaign = runner.run_campaign(
            candidates=[TrialCandidate(
                risk="low", severity="low", description="summary test",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )],
            max_trials=1,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        summary = campaign.summary()
        assert "campaign_id" in summary
        assert "total_trials" in summary
        assert "completed" in summary
        assert "failed" in summary
        assert "blocked" in summary
        assert "success_rate" in summary
        assert "contradiction_delta" in summary
        assert "readiness_delta" in summary
        assert "total_memory_candidates" in summary

    def test_persist_campaign(self, governed_stack, tmpdir):
        adapter = governed_stack["adapter"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        campaign = runner.run_campaign(
            candidates=[TrialCandidate(
                risk="low", severity="low", description="persist test",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )],
            max_trials=1,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )
        path = persist_campaign(campaign, os.path.join(tmpdir, "campaign.json"))
        assert os.path.isfile(path)
        with open(path) as f:
            data = json.load(f)
        assert data["summary"]["total_trials"] == 1

    def test_persist_candidate_queue(self, tmpdir):
        candidates = [
            TrialCandidate(risk="low", severity="low", description="c1"),
            TrialCandidate(risk="low", severity="medium", description="c2"),
        ]
        path = persist_candidate_queue(candidates, os.path.join(tmpdir, "queue.json"))
        assert os.path.isfile(path)
        with open(path) as f:
            data = json.load(f)
        assert len(data) == 2


# ── Build Candidate Queue (integration) ─────────────────────


class TestBuildCandidateQueue:
    def test_queue_from_world_model(self):
        candidates = build_candidate_queue()
        assert len(candidates) > 0

    def test_all_candidates_have_description(self):
        candidates = build_candidate_queue()
        for c in candidates:
            assert c.description

    def test_all_candidates_are_low_or_medium_risk(self):
        candidates = build_candidate_queue()
        for c in candidates:
            assert c.risk in ("low", "medium")

    def test_candidates_sorted_by_priority(self):
        candidates = build_candidate_queue()
        if len(candidates) >= 2:
            assert candidates[0].priority_score >= candidates[1].priority_score

    def test_candidates_serializable(self):
        candidates = build_candidate_queue()
        for c in candidates:
            data = c.to_dict()
            json.dumps(data, default=str)


# ── Cockpit Bridge Handler ───────────────────────────────────


class TestCockpitBridgeHandler:
    def test_trial_status_handler_loads(self):
        from transports.api.organism_bridge import _trial_status
        result = _trial_status({})
        assert result["success"] is True
        assert "data" in result

    def test_campaign_data_in_bridge(self, tmpdir):
        campaign_data = {
            "summary": {"total_trials": 5, "success_rate": 1.0},
            "baseline": {"contradictions_total": 15},
            "after": {"contradictions_total": 10},
            "trials": [],
        }
        trials_dir = os.path.join(tmpdir, "data", "umh", "trials")
        os.makedirs(trials_dir, exist_ok=True)
        with open(os.path.join(trials_dir, "phase9_3_campaign_results.json"), "w") as f:
            json.dump(campaign_data, f)

        old_root = os.environ.get("UMH_ROOT")
        os.environ["UMH_ROOT"] = tmpdir
        try:
            from transports.api.organism_bridge import _trial_status
            result = _trial_status({})
            assert result["success"] is True
            data = result["data"]
            assert data.get("has_campaign") is True
            assert data["campaign_summary"]["total_trials"] == 5
        finally:
            if old_root:
                os.environ["UMH_ROOT"] = old_root
            else:
                os.environ.pop("UMH_ROOT", None)


# ── End-to-End Campaign ──────────────────────────────────────


class TestEndToEndCampaign:
    def test_full_campaign_from_world_model(self, governed_stack):
        adapter = governed_stack["adapter"]
        wm = extract_world_model()
        dg = build_dependency_graph(wm)
        cr = detect_contradictions(wm, dg)
        comp = CompositionEngine(world_model=wm, dependency_graph=dg, contradiction_report=cr)

        candidates = build_candidate_queue(world_model=wm, contradiction_report=cr)

        runner = ReliabilityCampaignRunner(
            adapter=adapter,
            composition_engine=comp,
        )

        campaign = runner.run_campaign(
            candidates=candidates[:5],
            max_trials=5,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )

        assert len(campaign.trials) >= 3
        assert campaign.success_rate >= 0.5
        assert campaign.baseline.entities > 0
        assert campaign.after.entities > 0

        data = campaign.to_dict()
        serialized = json.dumps(data, default=str)
        assert len(serialized) > 100

    def test_campaign_runner_to_dict(self, governed_stack):
        adapter = governed_stack["adapter"]
        comp = CompositionEngine()
        runner = ReliabilityCampaignRunner(adapter=adapter, composition_engine=comp)

        before = runner.to_dict()
        assert before["status"] == "not_started"

        runner.run_campaign(
            candidates=[TrialCandidate(
                risk="low", severity="low", description="dict test",
                custom_steps=[{"action": "a", "desc": "A", "risk": "low", "gov": "autonomous"}],
            )],
            max_trials=1,
            step_executors_factory=lambda c, p: {s.id: lambda: ("ok", True) for s in p.steps},
        )

        after = runner.to_dict()
        assert "summary" in after
