"""Phase 9.5B — Real Template-Guided Improvement Campaign Tests.

Verifies end-to-end template-guided campaign through spine-native propagation:
  - Campaign runs through GovernedExecutionSpine (not manual)
  - Template candidates generated automatically from propagation
  - Template lifecycle: raw → approved → promoted
  - Template reuse via find_matching() with confidence tracking
  - Agent capability profiles created from propagation
  - Memory candidates generated from propagation
  - Outcome learning records created from propagation
  - No manual propagation calls anywhere
"""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

from substrate.organism.action_envelope import (
    ActionEnvelope,
    ActionType,
    ExecutionConstraints,
    VerificationStrategy,
)
from substrate.organism.agent_capability_model import AgentCapabilityModel
from substrate.organism.coherence_propagation import (
    OutcomeCommitted,
    ParallelPropagationEngine,
    PrimitiveRelationship,
    PropagationTarget,
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
from substrate.organism.template_registry import TemplateRegistry, TemplateStatus
from substrate.organism.trial_runner import (
    CandidateSource,
    ReliabilityCampaignRunner,
    TrialCandidate,
    TrialStatus,
    build_candidate_queue,
    rank_candidates,
)


@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def campaign_env(tmpdir):
    """Build full campaign environment with daemon-equivalent wiring."""
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
    from substrate.organism.autonomous_action_gateway import AutonomousActionGateway, AutonomousPolicy
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

    return {
        "spine": spine, "pe": pe, "tr": tr, "acm": acm,
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


class TestCampaignExecution:
    """Campaign runs through spine with auto-propagation."""

    def test_campaign_completes_with_successes(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:3]
        result = runner.run_campaign(
            candidates=candidates,
            max_trials=3,
            step_executors_factory=_step_executor_factory,
        )
        assert result.success_rate > 0

    def test_propagation_fires_automatically(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:2]
        runner.run_campaign(
            candidates=candidates,
            max_trials=2,
            step_executors_factory=_step_executor_factory,
        )
        events = campaign_env["pe"].recent_events(limit=50)
        assert len(events) > 0

    def test_no_manual_propagation_in_trial_runner(self):
        import inspect
        from substrate.organism import trial_runner
        source = inspect.getsource(trial_runner)
        assert "propagation_engine" not in source
        assert ".propagate(" not in source
        assert ".handle_outcome(" not in source


class TestTemplateGeneration:
    """Templates generated automatically from propagation."""

    def test_templates_generated_from_campaign(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:2]
        runner.run_campaign(
            candidates=candidates,
            max_trials=2,
            step_executors_factory=_step_executor_factory,
        )
        templates = campaign_env["tr"].list_candidates()
        assert len(templates) > 0

    def test_template_has_correct_initial_status(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:1]
        runner.run_campaign(
            candidates=candidates,
            max_trials=1,
            step_executors_factory=_step_executor_factory,
        )
        templates = campaign_env["tr"].list_candidates()
        assert all(t.status == TemplateStatus.RAW for t in templates)


class TestTemplateLifecycle:
    """Template promotion and reuse lifecycle."""

    def test_template_approve_promote_lifecycle(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:1]
        runner.run_campaign(
            candidates=candidates,
            max_trials=1,
            step_executors_factory=_step_executor_factory,
        )
        tr = campaign_env["tr"]
        templates = tr.list_candidates()
        assert len(templates) > 0

        tpl = templates[0]
        assert tpl.status == TemplateStatus.RAW

        tr.approve(tpl.template_id)
        assert tpl.status == TemplateStatus.APPROVED

        tr.promote(tpl.template_id)
        assert tpl.status == TemplateStatus.PROMOTED
        assert len(tr.list_promoted()) >= 1

    def test_template_confidence_updates_on_reuse(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:1]
        runner.run_campaign(
            candidates=candidates,
            max_trials=1,
            step_executors_factory=_step_executor_factory,
        )
        tr = campaign_env["tr"]
        tpl = tr.list_candidates()[0]
        initial_confidence = tpl.confidence

        tr.approve(tpl.template_id)
        tr.promote(tpl.template_id)

        tr.record_usage(tpl.template_id, success=True)
        tr.record_usage(tpl.template_id, success=True)
        assert tpl.confidence >= initial_confidence

    def test_find_matching_returns_promoted(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:1]
        runner.run_campaign(
            candidates=candidates,
            max_trials=1,
            step_executors_factory=_step_executor_factory,
        )
        tr = campaign_env["tr"]
        tpl = tr.list_candidates()[0]
        tr.approve(tpl.template_id)
        tr.promote(tpl.template_id)

        matches = tr.find_matching(tpl.template_type.value)
        assert len(matches) >= 1
        assert matches[0].status == TemplateStatus.PROMOTED


class TestAgentCapability:
    """Agent capability profiles created from propagation."""

    def test_agent_profile_created(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:2]
        runner.run_campaign(
            candidates=candidates,
            max_trials=2,
            step_executors_factory=_step_executor_factory,
        )
        acm = campaign_env["acm"]
        profile = acm.get_profile("developer_agent")
        assert profile is not None
        assert profile.total_attempts > 0

    def test_agent_capabilities_tracked(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:1]
        runner.run_campaign(
            candidates=candidates,
            max_trials=1,
            step_executors_factory=_step_executor_factory,
        )
        acm = campaign_env["acm"]
        profile = acm.get_profile("developer_agent")
        if profile:
            assert len(profile.capabilities) > 0


class TestOutcomeLearning:
    """Outcome records created from propagation."""

    def test_outcomes_recorded(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:2]
        runner.run_campaign(
            candidates=candidates,
            max_trials=2,
            step_executors_factory=_step_executor_factory,
        )
        ol = campaign_env["ol"]
        outcomes = ol.recent_outcomes(limit=50)
        assert len(outcomes) > 0


class TestMemoryPromotion:
    """Memory candidates generated from propagation."""

    def test_memory_candidates_created(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        candidates = build_candidate_queue()[:2]
        runner.run_campaign(
            candidates=candidates,
            max_trials=2,
            step_executors_factory=_step_executor_factory,
        )
        mp = campaign_env["mp"]
        mem_cands = mp.list_candidates()
        assert len(mem_cands) > 0


class TestCandidateQueue:
    """Candidate queue built from real codebase state."""

    def test_queue_builds_from_codebase(self):
        candidates = build_candidate_queue()
        assert len(candidates) > 0

    def test_candidates_ranked_by_priority(self):
        candidates = build_candidate_queue()
        scores = [c.priority_score for c in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_high_risk_candidates_filtered(self):
        candidates = build_candidate_queue()
        for c in candidates:
            assert c.risk not in ("high", "critical")

    def test_candidates_have_required_fields(self):
        candidates = build_candidate_queue()
        for c in candidates[:5]:
            assert c.description
            assert c.source in CandidateSource
            assert c.risk in ("low", "medium")


class TestSafetyGates:
    """Campaign safety gates enforced."""

    def test_high_risk_blocked(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        dangerous = TrialCandidate(
            source=CandidateSource.CONTRADICTION,
            description="Deploy production changes",
            risk="high",
            severity="critical",
        )
        result = runner.run_campaign(
            candidates=[dangerous],
            max_trials=1,
            step_executors_factory=_step_executor_factory,
        )
        assert result.trials[0].status == TrialStatus.BLOCKED

    def test_blocked_keywords_rejected(self, campaign_env):
        runner = ReliabilityCampaignRunner(
            adapter=campaign_env["adapter"],
            composition_engine=CompositionEngine(),
        )
        dangerous = TrialCandidate(
            source=CandidateSource.CONTRADICTION,
            description="Modify credential store configuration",
            risk="low",
            severity="info",
        )
        result = runner.run_campaign(
            candidates=[dangerous],
            max_trials=1,
            step_executors_factory=_step_executor_factory,
        )
        assert result.trials[0].status == TrialStatus.BLOCKED


class TestDaemonCampaignIntegration:
    """Full daemon integration — campaign through daemon's wired spine."""

    def test_daemon_campaign_e2e(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        daemon.start()

        adapter = PlanExecutionAdapter(
            governed_spine=daemon.governed_spine,
            spine_guard=daemon.spine_guard,
            autonomous_gateway=daemon.autonomous_gateway,
        )

        runner = ReliabilityCampaignRunner(
            adapter=adapter,
            composition_engine=CompositionEngine(),
        )

        candidates = build_candidate_queue()[:2]
        result = runner.run_campaign(
            candidates=candidates,
            max_trials=2,
            step_executors_factory=_step_executor_factory,
        )

        assert result.success_rate > 0
        assert len(daemon.propagation_engine.recent_events(limit=50)) > 0
        assert len(daemon.template_registry.list_candidates()) > 0
        assert daemon.agent_capability_model.get_profile("developer_agent") is not None
        assert len(daemon.outcome_learning.recent_outcomes(limit=50)) > 0
        assert len(daemon.memory_pipeline.list_candidates()) > 0
