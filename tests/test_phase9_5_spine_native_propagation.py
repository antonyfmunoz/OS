"""Phase 9.5 — Spine-Native Propagation + Template-Guided Campaign Tests.

60+ tests covering:
  - Spine-native propagation (automatic after governed execution)
  - Idempotency (duplicate outcome protection)
  - Failure isolation (per-target, per-wave)
  - Template-guided campaign (template confidence, agent reliability)
  - No manual propagation requirement
  - Backward compatibility (propagation engine optional)
  - Daemon wiring verification
  - OutcomeCommitted / OutcomeFailed emission
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
    EnvelopeStatus,
    ExecutionConstraints,
    RollbackStrategy,
    VerificationStrategy,
)
from substrate.organism.agent_capability_model import AgentCapabilityModel
from substrate.organism.coherence_propagation import (
    OutcomeCommitted,
    OutcomeFailed,
    ParallelPropagationEngine,
    PrimitiveRelationship,
    PropagationStatus,
    PropagationTarget,
)
from substrate.organism.event_spine import EventSpine
from substrate.organism.execution_journal import ExecutionJournal
from substrate.organism.execution_modes import ExecutionModeManager
from substrate.organism.governed_spine import GovernedExecutionSpine
from substrate.organism.memory_promotion import MemoryPromotionPipeline
from substrate.organism.mutation_registry import MutationRegistry
from substrate.organism.outcome_learning import OutcomeLearningLoop
from substrate.organism.propagation_wiring import build_propagation_engine
from substrate.organism.template_registry import TemplateRegistry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmpdir():
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def event_spine(tmpdir):
    return EventSpine(persist_path=os.path.join(tmpdir, "events.jsonl"))


@pytest.fixture
def mode_manager(event_spine):
    return ExecutionModeManager(event_spine=event_spine)


@pytest.fixture
def mutation_registry():
    return MutationRegistry()


@pytest.fixture
def journal(tmpdir):
    return ExecutionJournal(persist_path=os.path.join(tmpdir, "journal.jsonl"))


@pytest.fixture
def learning_loop(tmpdir):
    return OutcomeLearningLoop(store_path=os.path.join(tmpdir, "outcome_learning.jsonl"))


@pytest.fixture
def template_registry(tmpdir):
    return TemplateRegistry(store_dir=os.path.join(tmpdir, "templates"))


@pytest.fixture
def memory_pipeline(tmpdir):
    return MemoryPromotionPipeline(store_dir=os.path.join(tmpdir, "memory"))


@pytest.fixture
def agent_model(tmpdir):
    return AgentCapabilityModel(store_dir=os.path.join(tmpdir, "agents"))


@pytest.fixture
def propagation_engine(tmpdir, learning_loop, template_registry, memory_pipeline, agent_model):
    return build_propagation_engine(
        learning_loop=learning_loop,
        template_registry=template_registry,
        memory_pipeline=memory_pipeline,
        agent_capability_model=agent_model,
        store_dir=os.path.join(tmpdir, "propagation"),
    )


@pytest.fixture
def spine(event_spine, mode_manager, mutation_registry, journal, propagation_engine):
    return GovernedExecutionSpine(
        event_spine=event_spine,
        execution_mode=mode_manager,
        mutation_registry=mutation_registry,
        journal=journal,
        propagation_engine=propagation_engine,
    )


@pytest.fixture
def spine_no_propagation(event_spine, mode_manager, mutation_registry, journal):
    return GovernedExecutionSpine(
        event_spine=event_spine,
        execution_mode=mode_manager,
        mutation_registry=mutation_registry,
        journal=journal,
    )


def _make_envelope(
    intent: str = "test action",
    success: bool = True,
    verify: bool = False,
    verify_result: bool = True,
    risk: str = "low",
    capabilities: list[str] | None = None,
    metadata: dict | None = None,
) -> ActionEnvelope:
    output = f"Executed: {intent}"
    env = ActionEnvelope(
        intent=intent,
        action_type=ActionType.STATE,
        source="test",
        execute_fn=lambda: (output, success),
        risk_level=risk,
        required_capabilities=capabilities or ["code_search", "file_edit"],
        metadata=metadata or {"agent_type": "developer_agent"},
    )
    if verify:
        env.verification = VerificationStrategy(
            description="test verify",
            verify_fn=lambda: verify_result,
        )
    return env


# ═══════════════════════════════════════════════════════════════════════
# SPINE-NATIVE PROPAGATION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSpineNativePropagation:
    """Verify propagation fires automatically from spine execution."""

    def test_successful_envelope_emits_outcome_committed(self, spine, propagation_engine):
        env = _make_envelope("test auto propagation")
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.COMPLETED
        events = propagation_engine.recent_events(limit=10)
        assert len(events) >= 1, "No propagation event created"

    def test_verified_envelope_emits_outcome_committed(self, spine, propagation_engine):
        env = _make_envelope("test verified propagation", verify=True)
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.VERIFIED
        events = propagation_engine.recent_events(limit=10)
        assert len(events) >= 1

    def test_failed_envelope_records_failure(self, spine, propagation_engine):
        env = _make_envelope("test failure", success=False)
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.FAILED
        failures = propagation_engine.failed_outcomes(limit=10)
        assert len(failures) >= 1

    def test_verification_failure_emits_outcome_failed(self, spine, propagation_engine):
        env = _make_envelope("test verify fail", verify=True, verify_result=False)
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.VERIFICATION_FAILED
        failures = propagation_engine.failed_outcomes(limit=10)
        assert len(failures) >= 1

    def test_propagation_targets_all_fire(self, spine, propagation_engine):
        env = _make_envelope("test all targets", verify=True)
        spine.submit(env)
        events = propagation_engine.recent_events(limit=1)
        pe = events[-1]
        assert pe.succeeded_targets >= 5, f"Only {pe.succeeded_targets} targets succeeded"

    def test_propagation_has_two_waves(self, spine, propagation_engine):
        env = _make_envelope("test waves", verify=True)
        spine.submit(env)
        pe = propagation_engine.recent_events(limit=1)[-1]
        assert len(pe.waves) >= 2, f"Expected >=2 waves, got {len(pe.waves)}"

    def test_wave1_runs_before_wave2(self, spine, propagation_engine):
        env = _make_envelope("test wave order", verify=True)
        spine.submit(env)
        pe = propagation_engine.recent_events(limit=1)[-1]
        wave1 = pe.waves[0]
        wave2 = pe.waves[1]
        assert wave1.wave_number < wave2.wave_number
        assert wave1.completed_at <= wave2.started_at + 0.1

    def test_outcome_learning_records_from_propagation(self, spine, learning_loop):
        env = _make_envelope("test learning record", verify=True)
        spine.submit(env)
        outcomes = learning_loop.recent_outcomes(limit=10)
        assert len(outcomes) >= 1

    def test_template_generated_from_propagation(self, spine, template_registry):
        env = _make_envelope("test template gen", verify=True)
        spine.submit(env)
        candidates = template_registry.list_candidates()
        assert len(candidates) >= 1

    def test_memory_candidates_from_propagation(self, spine, memory_pipeline):
        env = _make_envelope("test memory gen", verify=True)
        spine.submit(env)
        candidates = memory_pipeline.list_candidates()
        assert len(candidates) >= 1

    def test_agent_capability_updated_from_propagation(self, spine, agent_model):
        env = _make_envelope("test agent cap", verify=True, capabilities=["test_capability"])
        spine.submit(env)
        profile = agent_model.get_profile("developer_agent")
        assert profile is not None
        assert profile.total_attempts >= 1

    def test_spine_reports_propagation_wired(self, spine):
        status = spine.to_dict()
        assert status["spine_native_propagation"] is True

    def test_no_manual_propagation_needed(self, spine, propagation_engine):
        pre_count = len(propagation_engine.recent_events(limit=1000))
        env = _make_envelope("no manual call")
        spine.submit(env)
        post_count = len(propagation_engine.recent_events(limit=1000))
        assert post_count > pre_count

    def test_multiple_envelopes_generate_multiple_propagations(self, spine, propagation_engine):
        for i in range(3):
            env = _make_envelope(f"batch test {i}", verify=True)
            spine.submit(env)
        events = propagation_engine.recent_events(limit=10)
        assert len(events) >= 3


# ═══════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """Verify spine works without propagation engine (optional dependency)."""

    def test_spine_without_propagation_executes(self, spine_no_propagation):
        env = _make_envelope("test no propagation")
        result = spine_no_propagation.submit(env)
        assert result.status == EnvelopeStatus.COMPLETED
        assert result.result_success is True

    def test_spine_without_propagation_reports_false(self, spine_no_propagation):
        status = spine_no_propagation.to_dict()
        assert status["spine_native_propagation"] is False

    def test_spine_without_propagation_verified_works(self, spine_no_propagation):
        env = _make_envelope("test no prop verify", verify=True)
        result = spine_no_propagation.submit(env)
        assert result.status == EnvelopeStatus.VERIFIED

    def test_spine_without_propagation_failure_works(self, spine_no_propagation):
        env = _make_envelope("test no prop fail", success=False)
        result = spine_no_propagation.submit(env)
        assert result.status == EnvelopeStatus.FAILED


# ═══════════════════════════════════════════════════════════════════════
# IDEMPOTENCY TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestIdempotency:
    """Verify duplicate OutcomeCommitted events are handled correctly."""

    def test_duplicate_outcome_ignored(self, propagation_engine):
        outcome = OutcomeCommitted(
            action_envelope_id="env-dup",
            action_type="test",
            completed_at=1000.0,
        )
        event1 = propagation_engine.handle_outcome(outcome)
        assert event1 is not None
        event2 = propagation_engine.handle_outcome(outcome)
        assert event2 is None

    def test_no_duplicate_outcome_record(self, propagation_engine, learning_loop):
        outcome = OutcomeCommitted(
            action_envelope_id="env-nodup",
            action_type="test",
            completed_at=2000.0,
        )
        propagation_engine.handle_outcome(outcome)
        count1 = len(learning_loop.recent_outcomes(limit=100))
        propagation_engine.handle_outcome(outcome)
        count2 = len(learning_loop.recent_outcomes(limit=100))
        assert count2 == count1

    def test_no_duplicate_template_candidate(self, propagation_engine, template_registry):
        outcome = OutcomeCommitted(
            action_envelope_id="env-tpldup",
            action_type="test",
            completed_at=3000.0,
        )
        propagation_engine.handle_outcome(outcome)
        count1 = len(template_registry.list_candidates())
        propagation_engine.handle_outcome(outcome)
        count2 = len(template_registry.list_candidates())
        assert count2 == count1

    def test_no_duplicate_memory_candidate(self, propagation_engine, memory_pipeline):
        outcome = OutcomeCommitted(
            action_envelope_id="env-memdup",
            action_type="test",
            completed_at=4000.0,
        )
        propagation_engine.handle_outcome(outcome)
        count1 = len(memory_pipeline.list_candidates())
        propagation_engine.handle_outcome(outcome)
        count2 = len(memory_pipeline.list_candidates())
        assert count2 == count1

    def test_no_duplicate_agent_reliability(self, propagation_engine, agent_model):
        outcome = OutcomeCommitted(
            action_envelope_id="env-agentdup",
            action_type="test",
            agent_type="test_agent",
            capabilities_used=["test_cap"],
            completed_at=5000.0,
        )
        propagation_engine.handle_outcome(outcome)
        profile1 = agent_model.get_profile("test_agent")
        attempts1 = profile1.total_attempts if profile1 else 0
        propagation_engine.handle_outcome(outcome)
        profile2 = agent_model.get_profile("test_agent")
        attempts2 = profile2.total_attempts if profile2 else 0
        assert attempts2 == attempts1

    def test_no_duplicate_template_confidence(self, propagation_engine, template_registry):
        outcome = OutcomeCommitted(
            action_envelope_id="env-confdup",
            action_type="test",
            completed_at=6000.0,
        )
        propagation_engine.handle_outcome(outcome)
        candidates1 = template_registry.list_candidates()
        if candidates1:
            conf1 = candidates1[-1].observed_success_count
        else:
            conf1 = 0
        propagation_engine.handle_outcome(outcome)
        candidates2 = template_registry.list_candidates()
        if candidates2:
            conf2 = candidates2[-1].observed_success_count
        else:
            conf2 = 0
        assert conf2 == conf1

    def test_different_outcomes_not_treated_as_duplicates(self, propagation_engine):
        o1 = OutcomeCommitted(action_envelope_id="env-a", completed_at=100.0)
        o2 = OutcomeCommitted(action_envelope_id="env-b", completed_at=200.0)
        e1 = propagation_engine.handle_outcome(o1)
        e2 = propagation_engine.handle_outcome(o2)
        assert e1 is not None
        assert e2 is not None

    def test_same_envelope_different_completion_not_duplicate(self, propagation_engine):
        o1 = OutcomeCommitted(action_envelope_id="env-same", completed_at=100.0)
        o2 = OutcomeCommitted(action_envelope_id="env-same", completed_at=200.0)
        e1 = propagation_engine.handle_outcome(o1)
        e2 = propagation_engine.handle_outcome(o2)
        assert e1 is not None
        assert e2 is not None

    def test_processed_key_persisted(self, propagation_engine, tmpdir):
        outcome = OutcomeCommitted(
            action_envelope_id="env-persist",
            completed_at=7000.0,
        )
        propagation_engine.handle_outcome(outcome)
        processed_path = os.path.join(tmpdir, "propagation", "processed_outcomes.jsonl")
        assert os.path.isfile(processed_path)
        with open(processed_path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) >= 1
        data = json.loads(lines[-1])
        assert "key" in data


# ═══════════════════════════════════════════════════════════════════════
# FAILURE ISOLATION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestFailureIsolation:
    """Verify failed targets don't block siblings."""

    def test_one_target_failure_doesnt_block_others(self, tmpdir):
        engine = ParallelPropagationEngine(store_dir=os.path.join(tmpdir, "fail_iso"))
        engine.register_target(PropagationTarget(
            name="succeeds", wave=1,
            primitive_relationship=PrimitiveRelationship.STATE,
            handler=lambda o: {"ok": True},
        ))
        engine.register_target(PropagationTarget(
            name="fails", wave=1,
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            handler=lambda o: (_ for _ in ()).throw(ValueError("intentional")),
        ))
        engine.register_target(PropagationTarget(
            name="also_succeeds", wave=1,
            primitive_relationship=PrimitiveRelationship.RESOURCE,
            handler=lambda o: {"also_ok": True},
        ))
        outcome = OutcomeCommitted(action_envelope_id="env-iso", completed_at=100.0)
        event = engine.handle_outcome(outcome)
        assert event is not None
        assert event.succeeded_targets >= 2
        assert event.failed_targets == 1

    def test_wave2_still_runs_after_wave1_failure(self, tmpdir):
        engine = ParallelPropagationEngine(store_dir=os.path.join(tmpdir, "wave_iso"))
        engine.register_target(PropagationTarget(
            name="w1_ok", wave=1,
            primitive_relationship=PrimitiveRelationship.STATE,
            handler=lambda o: {"ok": True},
        ))
        engine.register_target(PropagationTarget(
            name="w1_fail", wave=1,
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            handler=lambda o: (_ for _ in ()).throw(ValueError("fail")),
        ))
        engine.register_target(PropagationTarget(
            name="w2_ok", wave=2,
            primitive_relationship=PrimitiveRelationship.GOAL,
            handler=lambda o: {"wave2_ok": True},
        ))
        outcome = OutcomeCommitted(action_envelope_id="env-w2", completed_at=100.0)
        event = engine.handle_outcome(outcome)
        assert len(event.waves) == 2
        w2_results = event.waves[1].results
        assert any(r.status == PropagationStatus.COMPLETED for r in w2_results)

    def test_original_execution_success_preserved_on_propagation_failure(self, spine, propagation_engine):
        def failing_handler(o):
            raise RuntimeError("propagation target crash")

        propagation_engine.register_target(PropagationTarget(
            name="crashing_target", wave=1,
            primitive_relationship=PrimitiveRelationship.STATE,
            handler=failing_handler,
        ))
        env = _make_envelope("test success preserved")
        result = spine.submit(env)
        assert result.result_success is True
        assert result.status == EnvelopeStatus.COMPLETED

    def test_propagation_failure_visible_in_event(self, tmpdir):
        engine = ParallelPropagationEngine(store_dir=os.path.join(tmpdir, "vis_fail"))
        engine.register_target(PropagationTarget(
            name="failing", wave=1,
            primitive_relationship=PrimitiveRelationship.STATE,
            handler=lambda o: (_ for _ in ()).throw(RuntimeError("visible failure")),
        ))
        outcome = OutcomeCommitted(action_envelope_id="env-vis", completed_at=100.0)
        event = engine.handle_outcome(outcome)
        assert event.status == PropagationStatus.FAILED
        failed_results = [
            r for w in event.waves for r in w.results
            if r.status == PropagationStatus.FAILED
        ]
        assert len(failed_results) >= 1
        assert "visible failure" in failed_results[0].error

    def test_skipped_target_when_no_handler(self, tmpdir):
        engine = ParallelPropagationEngine(store_dir=os.path.join(tmpdir, "skip"))
        engine.register_target(PropagationTarget(
            name="no_handler", wave=1,
            primitive_relationship=PrimitiveRelationship.STATE,
            handler=None,
        ))
        outcome = OutcomeCommitted(action_envelope_id="env-skip", completed_at=100.0)
        event = engine.handle_outcome(outcome)
        assert event.skipped_targets >= 1


# ═══════════════════════════════════════════════════════════════════════
# TEMPLATE-GUIDED CAMPAIGN TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestTemplateGuidedCampaign:
    """Verify template-guided trial execution through spine."""

    def test_template_guided_execution_through_spine(self, spine, template_registry):
        env = _make_envelope("template guided test", verify=True, metadata={
            "agent_type": "developer_agent",
            "template_id": "tpl-test",
        })
        result = spine.submit(env)
        assert result.status == EnvelopeStatus.VERIFIED
        candidates = template_registry.list_candidates()
        assert len(candidates) >= 1

    def test_template_confidence_updates_on_success(self, spine, template_registry):
        env = _make_envelope("seed template", verify=True)
        spine.submit(env)
        candidates = template_registry.list_candidates()
        tpl = candidates[-1]
        template_registry.approve(tpl.template_id)
        template_registry.promote(tpl.template_id)
        conf_before = tpl.confidence

        template_registry.record_usage(tpl.template_id, success=True)
        conf_after = tpl.confidence
        assert conf_after >= conf_before

    def test_agent_reliability_updates_on_success(self, spine, agent_model):
        env = _make_envelope("reliability test", verify=True, capabilities=["test_cap"])
        spine.submit(env)
        profile = agent_model.get_profile("developer_agent")
        assert profile is not None
        cap = profile.capabilities.get("test_cap")
        assert cap is not None
        assert cap.successes >= 1

    def test_agent_failure_does_not_increment_success(self, spine, agent_model):
        env = _make_envelope("failure no success", success=False, capabilities=["fail_cap"])
        spine.submit(env)
        profile = agent_model.get_profile("developer_agent")
        if profile:
            cap = profile.capabilities.get("fail_cap")
            if cap:
                assert cap.successes == 0

    def test_campaign_code_does_not_manually_trigger_propagation(self):
        import inspect
        from substrate.organism import trial_runner
        source = inspect.getsource(trial_runner)
        assert "propagation_engine" not in source
        assert ".propagate(" not in source
        assert ".handle_outcome(" not in source

    def test_world_model_updates_after_spine_execution(self, spine, propagation_engine):
        env = _make_envelope("world model test", verify=True, metadata={
            "agent_type": "developer_agent",
            "changed_entities": [],
            "affected_subsystems": ["world_model"],
        })
        spine.submit(env)
        pe = propagation_engine.recent_events(limit=1)[-1]
        wm_results = [
            r for w in pe.waves for r in w.results
            if r.target_name == "world_model_evidence"
        ]
        assert len(wm_results) >= 1
        assert wm_results[0].status == PropagationStatus.COMPLETED

    def test_contradiction_recheck_after_spine_execution(self, spine, propagation_engine):
        env = _make_envelope("contradiction recheck", verify=True)
        spine.submit(env)
        pe = propagation_engine.recent_events(limit=1)[-1]
        cr_results = [
            r for w in pe.waves for r in w.results
            if r.target_name == "contradiction_recheck"
        ]
        assert len(cr_results) >= 1
        assert cr_results[0].status == PropagationStatus.COMPLETED


# ═══════════════════════════════════════════════════════════════════════
# OUTCOME EVENT TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestOutcomeEvents:
    """Verify OutcomeCommitted / OutcomeFailed event structure."""

    def test_outcome_committed_has_all_fields(self):
        oc = OutcomeCommitted(
            action_envelope_id="env-123",
            execution_graph_id="eg-456",
            trial_id="trial-789",
            action_type="test",
            mutation_type="state_update",
            risk_class="low",
            agent_type="developer_agent",
            capabilities_used=["code_search"],
            validation_result="passed",
            rollback_result="not_needed",
            duration_ms=42.0,
            changed_files=["a.py"],
            changed_entities=["entity_1"],
            affected_subsystems=["world_model"],
            evidence=["test evidence"],
            completed_at=1000.0,
        )
        d = oc.to_dict()
        assert d["event_type"] == "outcome_committed"
        assert d["action_envelope_id"] == "env-123"
        assert d["execution_graph_id"] == "eg-456"
        assert d["trial_id"] == "trial-789"
        assert d["action_type"] == "test"
        assert d["mutation_type"] == "state_update"
        assert d["risk_class"] == "low"
        assert d["agent_type"] == "developer_agent"
        assert d["capabilities_used"] == ["code_search"]
        assert d["validation_result"] == "passed"
        assert d["rollback_result"] == "not_needed"
        assert d["duration_ms"] == 42.0
        assert d["changed_files"] == ["a.py"]
        assert d["changed_entities"] == ["entity_1"]
        assert d["affected_subsystems"] == ["world_model"]
        assert d["evidence"] == ["test evidence"]
        assert d["completed_at"] == 1000.0

    def test_outcome_committed_idempotency_key(self):
        oc = OutcomeCommitted(action_envelope_id="env-a", completed_at=100.0)
        assert oc.idempotency_key == "env-a:100.0"

    def test_outcome_committed_to_outcome_dict(self):
        oc = OutcomeCommitted(
            action_envelope_id="env-dict",
            action_type="test_action",
            validation_result="passed",
        )
        d = oc.to_outcome_dict()
        assert d["success"] is True
        assert d["action_type"] == "test_action"

    def test_outcome_failed_has_all_fields(self):
        of = OutcomeFailed(
            action_envelope_id="env-fail",
            execution_graph_id="eg-fail",
            trial_id="trial-fail",
            action_type="test",
            risk_class="low",
            agent_type="developer_agent",
            failure_reason="test failure",
            validation_result="execution_failed",
            evidence=["failure evidence"],
        )
        d = of.to_dict()
        assert d["event_type"] == "outcome_failed"
        assert d["failure_reason"] == "test failure"
        assert d["validation_result"] == "execution_failed"

    def test_outcome_failed_not_verified(self):
        of = OutcomeFailed(validation_result="verification_failed")
        assert of.to_dict()["validation_result"] == "verification_failed"


# ═══════════════════════════════════════════════════════════════════════
# DAEMON WIRING TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestDaemonWiring:
    """Verify daemon properly wires propagation engine."""

    def test_daemon_creates_propagation_engine(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        assert daemon.propagation_engine is not None

    def test_daemon_wires_propagation_into_spine(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        assert daemon.governed_spine.propagation_engine is not None
        assert daemon.governed_spine.propagation_engine is daemon.propagation_engine

    def test_daemon_propagation_has_targets(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        targets = daemon.propagation_engine._targets
        assert len(targets) >= 8

    def test_daemon_propagation_has_wave1_and_wave2(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        waves = set(t.wave for t in daemon.propagation_engine._targets)
        assert 1 in waves
        assert 2 in waves

    def test_daemon_exposes_subsystem_properties(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        assert daemon.outcome_learning is not None
        assert daemon.template_registry is not None
        assert daemon.memory_pipeline is not None
        assert daemon.agent_capability_model is not None

    def test_daemon_status_includes_propagation(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        daemon.start()
        status = daemon.status()
        assert "propagation_engine" in status
        assert "outcome_learning" in status
        assert "template_registry" in status
        assert "memory_pipeline" in status
        assert "agent_capability_model" in status

    def test_daemon_spine_status_shows_native(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        spine_dict = daemon.governed_spine.to_dict()
        assert spine_dict["spine_native_propagation"] is True

    def test_daemon_end_to_end_propagation(self, tmpdir):
        from substrate.organism.daemon import OrganismDaemon
        daemon = OrganismDaemon(store_dir=tmpdir)
        daemon.start()
        env = _make_envelope("daemon e2e", verify=True)
        result = daemon.governed_spine.submit(env)
        assert result.result_success is True
        events = daemon.propagation_engine.recent_events(limit=10)
        assert len(events) >= 1
        assert events[-1].succeeded_targets >= 5


# ═══════════════════════════════════════════════════════════════════════
# PROPAGATION WIRING MODULE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestPropagationWiring:
    """Verify the propagation_wiring module builds correctly."""

    def test_build_creates_engine_with_targets(self, tmpdir):
        engine = build_propagation_engine(
            learning_loop=OutcomeLearningLoop(store_path=os.path.join(tmpdir, "ol.jsonl")),
            template_registry=TemplateRegistry(store_dir=os.path.join(tmpdir, "tpl")),
            memory_pipeline=MemoryPromotionPipeline(store_dir=os.path.join(tmpdir, "mem")),
            agent_capability_model=AgentCapabilityModel(store_dir=os.path.join(tmpdir, "agent")),
            store_dir=os.path.join(tmpdir, "prop"),
        )
        assert len(engine._targets) >= 8

    def test_wave1_targets_are_independent(self, propagation_engine):
        w1 = [t for t in propagation_engine._targets if t.wave == 1]
        names = {t.name for t in w1}
        assert "outcome_learning" in names
        assert "template_generation" in names
        assert "memory_generation" in names
        assert "agent_capability_update" in names
        assert "world_model_evidence" in names

    def test_wave2_targets_are_derived(self, propagation_engine):
        w2 = [t for t in propagation_engine._targets if t.wave == 2]
        names = {t.name for t in w2}
        assert "contradiction_recheck" in names
        assert "composition_template_refresh" in names

    def test_all_targets_have_handlers(self, propagation_engine):
        for t in propagation_engine._targets:
            assert t.handler is not None, f"Target {t.name} has no handler"

    def test_all_targets_have_primitive_relationships(self, propagation_engine):
        for t in propagation_engine._targets:
            assert t.primitive_relationship is not None
            assert isinstance(t.primitive_relationship, PrimitiveRelationship)

    def test_optional_subsystems_skipped_when_none(self, tmpdir):
        engine = build_propagation_engine(
            learning_loop=OutcomeLearningLoop(store_path=os.path.join(tmpdir, "ol.jsonl")),
            template_registry=TemplateRegistry(store_dir=os.path.join(tmpdir, "tpl")),
            memory_pipeline=MemoryPromotionPipeline(store_dir=os.path.join(tmpdir, "mem")),
            agent_capability_model=AgentCapabilityModel(store_dir=os.path.join(tmpdir, "agent")),
            readiness_model=None,
            bottleneck_engine=None,
            store_dir=os.path.join(tmpdir, "prop2"),
        )
        names = {t.name for t in engine._targets}
        assert "readiness_recalculate" not in names
        assert "bottleneck_recalculate" not in names
        assert len(engine._targets) >= 7


# ═══════════════════════════════════════════════════════════════════════
# PROPAGATION ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestPropagationEngine:
    """Verify ParallelPropagationEngine behavior."""

    def test_engine_summary(self, propagation_engine):
        s = propagation_engine.summary()
        assert "total_events" in s
        assert "registered_targets" in s

    def test_engine_to_dict(self, propagation_engine):
        d = propagation_engine.to_dict()
        assert "summary" in d
        assert "recent_events" in d
        assert "registered_targets" in d

    def test_engine_to_safe_dict(self, propagation_engine):
        d = propagation_engine.to_safe_dict()
        assert "spine_native" in d
        assert d["spine_native"] is True
        assert "processed_outcome_count" in d

    def test_engine_get_event(self, propagation_engine):
        outcome = OutcomeCommitted(action_envelope_id="env-get", completed_at=100.0)
        event = propagation_engine.handle_outcome(outcome)
        found = propagation_engine.get_event(event.event_id)
        assert found is not None
        assert found.event_id == event.event_id

    def test_engine_get_event_not_found(self, propagation_engine):
        found = propagation_engine.get_event("nonexistent")
        assert found is None

    def test_handle_failure_records(self, propagation_engine):
        failed = OutcomeFailed(
            action_envelope_id="env-hf",
            failure_reason="test fail",
        )
        propagation_engine.handle_failure(failed)
        failures = propagation_engine.failed_outcomes(limit=10)
        assert len(failures) >= 1
        assert failures[-1].action_envelope_id == "env-hf"

    def test_failure_does_not_generate_success_template(self, tmpdir):
        engine = ParallelPropagationEngine(store_dir=os.path.join(tmpdir, "fail_tpl"))
        tpl_reg = TemplateRegistry(store_dir=os.path.join(tmpdir, "tpl"))
        engine.register_target(PropagationTarget(
            name="test_tpl", wave=1,
            primitive_relationship=PrimitiveRelationship.ACTION,
            handler=lambda o: tpl_reg.generate_candidate_from_outcome(o.to_outcome_dict()),
        ))
        failed = OutcomeFailed(
            action_envelope_id="env-nogen",
            failure_reason="should not gen template",
        )
        engine.handle_failure(failed)
        assert len(tpl_reg.list_candidates()) == 0
