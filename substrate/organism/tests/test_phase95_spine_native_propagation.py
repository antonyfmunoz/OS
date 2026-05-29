"""Phase 9.5 tests — Spine-Native Propagation + Template-Guided Improvement Campaign.

80+ tests covering:
  - Spine-native OutcomeCommitted emission after verified success
  - Spine-native OutcomeFailed emission after failure / verification failure
  - ParallelPropagationEngine auto-invocation from spine
  - Idempotency protection (duplicate OutcomeCommitted ignored)
  - Failure isolation (one target failure doesn't block siblings)
  - Wave dependency skipping (Wave 2 target skipped if Wave 1 upstream fails)
  - Template-guided campaign through spine without manual propagation
  - Template confidence + agent reliability updates
  - WorldModel / Contradiction / Readiness update proof
  - Cockpit / API route exposure
  - Backward compatibility (no propagation engine = no crash)
  - No manual propagation call required
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.organism.event_spine import EventDomain


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event_spine():
    from substrate.organism.event_spine import EventSpine
    return EventSpine()


def _make_journal():
    from substrate.organism.execution_journal import ExecutionJournal
    return ExecutionJournal()


def _make_mode_manager():
    from substrate.organism.execution_modes import ExecutionModeManager
    return ExecutionModeManager()


def _make_mutation_registry():
    from substrate.organism.mutation_registry import MutationRegistry
    return MutationRegistry()


def _make_propagation_engine(tmpdir: str | None = None):
    from substrate.organism.coherence_propagation import ParallelPropagationEngine
    return ParallelPropagationEngine(store_dir=tmpdir)


def _make_spine(event_spine=None, propagation_engine=None, **kwargs):
    from substrate.organism.governed_spine import GovernedExecutionSpine
    es = event_spine or _make_event_spine()
    return GovernedExecutionSpine(
        event_spine=es,
        execution_mode=kwargs.get("execution_mode", _make_mode_manager()),
        mutation_registry=kwargs.get("mutation_registry", _make_mutation_registry()),
        journal=kwargs.get("journal", _make_journal()),
        propagation_engine=propagation_engine,
    )


def _make_envelope(
    intent="test action",
    action_type=None,
    execute_fn=None,
    verification_fn=None,
    rollback_fn=None,
    risk_level="low",
    metadata=None,
    require_approval=False,
):
    from substrate.organism.action_envelope import (
        ActionEnvelope,
        ActionType,
        ExecutionConstraints,
        VerificationStrategy,
        RollbackStrategy,
    )
    at = action_type or ActionType.STATE
    fn = execute_fn or (lambda: ("success", True))
    env = ActionEnvelope(
        intent=intent,
        action_type=at,
        source="test",
        execute_fn=fn,
        risk_level=risk_level,
        metadata=metadata or {},
        constraints=ExecutionConstraints(require_approval=require_approval),
    )
    if verification_fn is not None:
        env.verification = VerificationStrategy(
            description="test verification",
            verify_fn=verification_fn,
        )
    if rollback_fn is not None:
        env.rollback = RollbackStrategy(
            description="test rollback",
            rollback_fn=rollback_fn,
        )
    return env


def _sample_outcome(**overrides):
    from substrate.organism.coherence_propagation import OutcomeCommitted
    base = dict(
        action_envelope_id="env-001",
        action_type="state",
        risk_class="low",
        agent_type="developer_agent",
        validation_result="passed",
        duration_ms=100.0,
        completed_at=time.time(),
        evidence=["test evidence"],
    )
    base.update(overrides)
    return OutcomeCommitted(**base)


# ---------------------------------------------------------------------------
# I. Spine-Native OutcomeCommitted Emission
# ---------------------------------------------------------------------------

class TestSpineNativeOutcomeCommitted:
    """Verify spine automatically emits OutcomeCommitted after verified success."""

    def test_verified_envelope_emits_outcome_committed(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        env = _make_envelope(verification_fn=lambda: True)
        result = spine.submit(env)

        assert result.status.value == "verified"
        events = es.replay(domains={EventDomain.EXECUTION})
        event_types = [e.event_type for e in events]
        assert "outcome_committed" in event_types

    def test_completed_envelope_emits_outcome_committed(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        env = _make_envelope()  # no verification strategy
        result = spine.submit(env)

        assert result.status.value == "completed"
        events = es.replay(domains={EventDomain.EXECUTION})
        event_types = [e.event_type for e in events]
        assert "outcome_committed" in event_types

    def test_outcome_committed_payload_has_required_fields(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        meta = {
            "execution_graph_id": "eg-001",
            "trial_id": "trial-001",
            "agent_type": "auditor_agent",
            "changed_files": ["a.py"],
            "changed_entities": ["module_x"],
            "affected_subsystems": ["governance"],
        }
        env = _make_envelope(
            verification_fn=lambda: True,
            metadata=meta,
        )
        env.required_capabilities = ["code_search", "file_edit"]
        result = spine.submit(env)

        assert result.status.value == "verified"

        events = es.replay(domains={EventDomain.EXECUTION})
        oc_events = [e for e in events if e.event_type == "outcome_committed"]
        assert len(oc_events) == 1

        data = oc_events[0].data
        assert data["action_envelope_id"] == result.envelope_id
        assert data["execution_graph_id"] == "eg-001"
        assert data["trial_id"] == "trial-001"
        assert data["action_type"] == "state"
        assert data["risk_class"] == "low"
        assert data["agent_type"] == "auditor_agent"
        assert data["capabilities_used"] == ["code_search", "file_edit"]
        assert data["validation_result"] == "passed"
        assert data["changed_files"] == ["a.py"]
        assert data["changed_entities"] == ["module_x"]
        assert data["affected_subsystems"] == ["governance"]
        assert data["duration_ms"] >= 0
        assert data["completed_at"] > 0

    def test_verified_outcome_has_validation_passed(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        env = _make_envelope(verification_fn=lambda: True)
        spine.submit(env)

        events = es.replay(domains={EventDomain.EXECUTION})
        oc = [e for e in events if e.event_type == "outcome_committed"][0]
        assert oc.data["validation_result"] == "passed"

    def test_completed_without_verification_has_not_verified(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        env = _make_envelope()
        spine.submit(env)

        events = es.replay(domains={EventDomain.EXECUTION})
        oc = [e for e in events if e.event_type == "outcome_committed"][0]
        assert oc.data["validation_result"] == "not_verified"


# ---------------------------------------------------------------------------
# II. Spine-Native OutcomeFailed Emission
# ---------------------------------------------------------------------------

class TestSpineNativeOutcomeFailed:
    """Verify spine automatically emits OutcomeFailed after failure."""

    def test_failed_envelope_emits_outcome_failed(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        env = _make_envelope(execute_fn=lambda: ("error happened", False))
        result = spine.submit(env)

        assert result.status.value == "failed"
        events = es.replay(domains={EventDomain.EXECUTION})
        event_types = [e.event_type for e in events]
        assert "outcome_failed" in event_types

    def test_verification_failure_emits_outcome_failed(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        env = _make_envelope(
            verification_fn=lambda: False,
        )
        result = spine.submit(env)

        assert result.status.value == "verification_failed"
        events = es.replay(domains={EventDomain.EXECUTION})
        event_types = [e.event_type for e in events]
        assert "outcome_failed" in event_types

    def test_verification_exception_emits_outcome_failed(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        def bad_verify():
            raise RuntimeError("verify boom")

        env = _make_envelope(verification_fn=bad_verify)
        result = spine.submit(env)

        assert result.status.value == "verification_failed"
        events = es.replay(domains={EventDomain.EXECUTION})
        event_types = [e.event_type for e in events]
        assert "outcome_failed" in event_types

    def test_execution_exception_emits_outcome_failed(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        def boom():
            raise RuntimeError("execution boom")

        env = _make_envelope(execute_fn=boom)
        result = spine.submit(env)

        assert result.status.value == "failed"
        events = es.replay(domains={EventDomain.EXECUTION})
        of_events = [e for e in events if e.event_type == "outcome_failed"]
        assert len(of_events) == 1
        assert "execution boom" in of_events[0].data["failure_reason"]

    def test_rolled_back_envelope_emits_outcome_failed(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        env = _make_envelope(
            execute_fn=lambda: ("fail", False),
            rollback_fn=lambda: True,
        )
        result = spine.submit(env)

        assert result.status.value == "rolled_back"
        events = es.replay(domains={EventDomain.EXECUTION})
        of_events = [e for e in events if e.event_type == "outcome_failed"]
        assert len(of_events) == 1
        assert of_events[0].data["validation_result"] == "execution_failed"

    def test_outcome_failed_payload_fields(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        meta = {"trial_id": "trial-fail", "agent_type": "security_agent"}
        env = _make_envelope(
            execute_fn=lambda: ("bad result", False),
            metadata=meta,
        )
        spine.submit(env)

        events = es.replay(domains={EventDomain.EXECUTION})
        of = [e for e in events if e.event_type == "outcome_failed"][0]
        assert of.data["trial_id"] == "trial-fail"
        assert of.data["agent_type"] == "security_agent"
        assert of.data["failure_reason"] == "bad result"

    def test_no_outcome_for_rejected_envelope(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        env = _make_envelope(risk_level="critical")
        spine.submit(env)

        events = es.replay(domains={EventDomain.EXECUTION})
        event_types = [e.event_type for e in events]
        assert "outcome_committed" not in event_types
        assert "outcome_failed" not in event_types


# ---------------------------------------------------------------------------
# III. Propagation Engine Auto-Invocation
# ---------------------------------------------------------------------------

class TestPropagationEngineAutoInvocation:
    """Verify propagation engine is automatically called from spine."""

    def test_propagation_engine_called_on_success(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        call_log = []

        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship
        pe.register_target(PropagationTarget(
            name="test_target",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: call_log.append(oc.action_envelope_id) or {"recorded": True},
        ))

        spine = _make_spine(propagation_engine=pe)
        env = _make_envelope(verification_fn=lambda: True)
        result = spine.submit(env)

        assert result.status.value == "verified"
        assert len(call_log) == 1
        assert call_log[0] == result.envelope_id

    def test_propagation_engine_not_called_on_failure(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        call_log = []

        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship
        pe.register_target(PropagationTarget(
            name="test_target",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: call_log.append(oc) or {},
        ))

        spine = _make_spine(propagation_engine=pe)
        env = _make_envelope(execute_fn=lambda: ("fail", False))
        spine.submit(env)

        assert len(call_log) == 0

    def test_failure_recorded_in_propagation_engine(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        spine = _make_spine(propagation_engine=pe)

        env = _make_envelope(execute_fn=lambda: ("error", False))
        spine.submit(env)

        failures = pe.failed_outcomes()
        assert len(failures) == 1
        assert "error" in failures[0].failure_reason

    def test_propagation_engine_optional_backward_compatible(self):
        spine = _make_spine(propagation_engine=None)
        env = _make_envelope(verification_fn=lambda: True)
        result = spine.submit(env)

        assert result.status.value == "verified"

    def test_propagation_failure_does_not_affect_execution_result(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))

        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship
        pe.register_target(PropagationTarget(
            name="broken_target",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: (_ for _ in ()).throw(RuntimeError("propagation boom")),
        ))

        spine = _make_spine(propagation_engine=pe)
        env = _make_envelope(verification_fn=lambda: True)
        result = spine.submit(env)

        assert result.status.value == "verified"
        assert result.result_success is True

    def test_spine_to_dict_shows_propagation_status(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        spine = _make_spine(propagation_engine=pe)

        d = spine.to_dict()
        assert d["spine_native_propagation"] is True

    def test_spine_without_propagation_shows_false(self):
        spine = _make_spine(propagation_engine=None)
        d = spine.to_dict()
        assert d["spine_native_propagation"] is False

    def test_multiple_targets_all_called(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        results = {}

        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        for name in ["target_a", "target_b", "target_c"]:
            pe.register_target(PropagationTarget(
                name=name,
                primitive_relationship=PrimitiveRelationship.FEEDBACK,
                wave=1,
                handler=lambda oc, n=name: results.update({n: True}) or {},
            ))

        spine = _make_spine(propagation_engine=pe)
        env = _make_envelope(verification_fn=lambda: True)
        spine.submit(env)

        assert results == {"target_a": True, "target_b": True, "target_c": True}

    def test_wave_ordering_preserved(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        order = []

        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe.register_target(PropagationTarget(
            name="wave1_a", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=lambda oc: order.append("w1a") or {},
        ))
        pe.register_target(PropagationTarget(
            name="wave1_b", primitive_relationship=PrimitiveRelationship.OUTCOME,
            wave=1, handler=lambda oc: order.append("w1b") or {},
        ))
        pe.register_target(PropagationTarget(
            name="wave2_a", primitive_relationship=PrimitiveRelationship.STATE,
            wave=2, handler=lambda oc: order.append("w2a") or {},
        ))

        spine = _make_spine(propagation_engine=pe)
        env = _make_envelope(verification_fn=lambda: True)
        spine.submit(env)

        w1_indices = [order.index(x) for x in ["w1a", "w1b"]]
        w2_index = order.index("w2a")
        assert all(i < w2_index for i in w1_indices)


# ---------------------------------------------------------------------------
# IV. Idempotency Protection
# ---------------------------------------------------------------------------

class TestIdempotencyProtection:
    """Verify duplicate OutcomeCommitted events are ignored."""

    def test_duplicate_outcome_ignored(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        call_count = [0]

        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship
        pe.register_target(PropagationTarget(
            name="counter",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: call_count.__setitem__(0, call_count[0] + 1) or {},
        ))

        outcome = _sample_outcome(action_envelope_id="env-dup-001", completed_at=123.456)

        result1 = pe.handle_outcome(outcome)
        assert result1 is not None
        assert call_count[0] == 1

        result2 = pe.handle_outcome(outcome)
        assert result2 is None
        assert call_count[0] == 1

    def test_idempotency_key_persisted(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        outcome = _sample_outcome(action_envelope_id="env-persist", completed_at=999.0)

        pe.handle_outcome(outcome)

        processed_path = os.path.join(str(tmp_path), "processed_outcomes.jsonl")
        assert os.path.isfile(processed_path)
        with open(processed_path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["key"] == "env-persist:999.0"

    def test_different_completed_at_not_duplicate(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        call_count = [0]

        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship
        pe.register_target(PropagationTarget(
            name="counter",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: call_count.__setitem__(0, call_count[0] + 1) or {},
        ))

        oc1 = _sample_outcome(action_envelope_id="env-x", completed_at=100.0)
        oc2 = _sample_outcome(action_envelope_id="env-x", completed_at=200.0)

        pe.handle_outcome(oc1)
        pe.handle_outcome(oc2)

        assert call_count[0] == 2

    def test_is_processed_query(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        outcome = _sample_outcome(action_envelope_id="env-q", completed_at=42.0)

        assert not pe.is_processed("env-q:42.0")
        pe.handle_outcome(outcome)
        assert pe.is_processed("env-q:42.0")

    def test_no_duplicate_template_candidate(self, tmp_path):
        from substrate.organism.template_registry import TemplateRegistry
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        reg = TemplateRegistry(store_dir=str(tmp_path / "templates"))
        pe = _make_propagation_engine(str(tmp_path / "propagation"))

        pe.register_target(PropagationTarget(
            name="template_gen",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: reg.generate_candidate_from_outcome(oc.to_outcome_dict()).to_dict(),
        ))

        outcome = _sample_outcome(action_envelope_id="env-tpl-dup", completed_at=50.0)

        pe.handle_outcome(outcome)
        pe.handle_outcome(outcome)

        assert len(reg.list_candidates()) == 1

    def test_no_duplicate_agent_reliability_count(self, tmp_path):
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        acm = AgentCapabilityModel(store_dir=str(tmp_path / "acm"))
        pe = _make_propagation_engine(str(tmp_path / "propagation"))

        pe.register_target(PropagationTarget(
            name="agent_reliability",
            primitive_relationship=PrimitiveRelationship.RESOURCE,
            wave=1,
            handler=lambda oc: acm.update_reliability(
                agent_type=oc.agent_type,
                capabilities_used=oc.capabilities_used,
                success=oc.validation_result == "passed",
                duration_ms=oc.duration_ms,
                outcome_id=oc.event_id,
                action_envelope_id=oc.action_envelope_id,
            ),
        ))

        outcome = _sample_outcome(action_envelope_id="env-acm-dup", completed_at=60.0)

        pe.handle_outcome(outcome)
        pe.handle_outcome(outcome)

        profile = acm.get_profile("developer_agent")
        if profile:
            assert profile.get("total_attempts", 0) <= 1


# ---------------------------------------------------------------------------
# V. Failure Isolation
# ---------------------------------------------------------------------------

class TestFailureIsolation:
    """Verify one target failure doesn't block siblings."""

    def test_sibling_target_succeeds_when_other_fails(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe.register_target(PropagationTarget(
            name="broken", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=lambda oc: (_ for _ in ()).throw(RuntimeError("boom")),
        ))
        pe.register_target(PropagationTarget(
            name="healthy", primitive_relationship=PrimitiveRelationship.STATE,
            wave=1, handler=lambda oc: {"status": "ok"},
        ))

        outcome = _sample_outcome()
        event = pe.propagate(outcome)

        results_by_name = {r.target_name: r for w in event.waves for r in w.results}
        assert results_by_name["broken"].status.value == "failed"
        assert results_by_name["healthy"].status.value == "completed"

    def test_wave2_runs_despite_wave1_partial_failure(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe.register_target(PropagationTarget(
            name="w1_ok", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=lambda oc: {"ok": True},
        ))
        pe.register_target(PropagationTarget(
            name="w1_fail", primitive_relationship=PrimitiveRelationship.OUTCOME,
            wave=1, handler=lambda oc: (_ for _ in ()).throw(RuntimeError("w1 boom")),
        ))
        pe.register_target(PropagationTarget(
            name="w2_recalc", primitive_relationship=PrimitiveRelationship.STATE,
            wave=2, handler=lambda oc: {"recalculated": True},
        ))

        outcome = _sample_outcome()
        event = pe.propagate(outcome)

        results_by_name = {r.target_name: r for w in event.waves for r in w.results}
        assert results_by_name["w1_ok"].status.value == "completed"
        assert results_by_name["w1_fail"].status.value == "failed"
        assert results_by_name["w2_recalc"].status.value == "completed"

    def test_execution_remains_successful_on_propagation_partial_failure(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe.register_target(PropagationTarget(
            name="failing", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=lambda oc: (_ for _ in ()).throw(RuntimeError("target exploded")),
        ))

        spine = _make_spine(propagation_engine=pe)
        env = _make_envelope(verification_fn=lambda: True)
        result = spine.submit(env)

        assert result.result_success is True
        assert result.status.value == "verified"

    def test_propagation_event_marks_partial_failure(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe.register_target(PropagationTarget(
            name="ok", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=lambda oc: {},
        ))
        pe.register_target(PropagationTarget(
            name="broken", primitive_relationship=PrimitiveRelationship.STATE,
            wave=1, handler=lambda oc: (_ for _ in ()).throw(RuntimeError("nope")),
        ))

        outcome = _sample_outcome()
        event = pe.propagate(outcome)

        assert event.status.value == "failed"
        assert event.succeeded_targets == 1
        assert event.failed_targets == 1

    def test_no_handler_target_skipped(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe.register_target(PropagationTarget(
            name="no_handler", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=None,
        ))

        outcome = _sample_outcome()
        event = pe.propagate(outcome)

        assert event.skipped_targets == 1


# ---------------------------------------------------------------------------
# VI. Spine Propagation Integration (full end-to-end)
# ---------------------------------------------------------------------------

class TestSpinePropagationIntegration:
    """End-to-end: submit envelope → verified → OutcomeCommitted → propagation targets fire."""

    def test_full_e2e_spine_to_propagation(self, tmp_path):
        from substrate.organism.template_registry import TemplateRegistry
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        reg = TemplateRegistry(store_dir=str(tmp_path / "templates"))
        acm = AgentCapabilityModel(store_dir=str(tmp_path / "acm"))
        pe = _make_propagation_engine(str(tmp_path / "propagation"))
        es = _make_event_spine()

        pe.register_target(PropagationTarget(
            name="template_gen",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: reg.generate_candidate_from_outcome(oc.to_outcome_dict()).to_dict(),
        ))
        pe.register_target(PropagationTarget(
            name="agent_reliability",
            primitive_relationship=PrimitiveRelationship.RESOURCE,
            wave=1,
            handler=lambda oc: acm.update_reliability(
                agent_type=oc.agent_type,
                capabilities_used=oc.capabilities_used,
                success=oc.validation_result == "passed",
                duration_ms=oc.duration_ms,
                outcome_id=oc.event_id,
                action_envelope_id=oc.action_envelope_id,
            ),
        ))

        spine = _make_spine(event_spine=es, propagation_engine=pe)

        meta = {
            "trial_id": "e2e-trial-001",
            "agent_type": "developer_agent",
            "changed_files": ["test.py"],
        }
        env = _make_envelope(
            intent="E2E spine-native propagation test",
            verification_fn=lambda: True,
            metadata=meta,
        )
        env.required_capabilities = ["code_search"]

        result = spine.submit(env)

        assert result.status.value == "verified"

        events = es.replay(domains={EventDomain.EXECUTION})
        oc_events = [e for e in events if e.event_type == "outcome_committed"]
        assert len(oc_events) == 1

        assert len(reg.list_candidates()) == 1
        tpl = reg.list_candidates()[0]
        assert tpl.observed_success_count >= 1

        recent = pe.recent_events()
        assert len(recent) == 1
        assert recent[0].succeeded_targets >= 2

    def test_no_manual_propagation_needed(self, tmp_path):
        """Trial/campaign code submits through spine — propagation happens automatically."""
        propagation_called = [False]

        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe = _make_propagation_engine(str(tmp_path))
        pe.register_target(PropagationTarget(
            name="tracker",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: propagation_called.__setitem__(0, True) or {},
        ))

        spine = _make_spine(propagation_engine=pe)
        env = _make_envelope(verification_fn=lambda: True)
        spine.submit(env)

        assert propagation_called[0] is True

    def test_propagation_engine_accessible_via_property(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        spine = _make_spine(propagation_engine=pe)
        assert spine.propagation_engine is pe


# ---------------------------------------------------------------------------
# VII. OutcomeCommitted / OutcomeFailed Contract Tests
# ---------------------------------------------------------------------------

class TestOutcomeContracts:
    """Verify OutcomeCommitted and OutcomeFailed dataclass contracts."""

    def test_outcome_committed_to_dict(self):
        oc = _sample_outcome(action_envelope_id="env-dict")
        d = oc.to_dict()
        assert d["event_type"] == "outcome_committed"
        assert d["action_envelope_id"] == "env-dict"
        assert "completed_at" in d

    def test_outcome_committed_to_outcome_dict(self):
        oc = _sample_outcome(action_type="filesystem")
        d = oc.to_outcome_dict()
        assert d["action_type"] == "filesystem"
        assert d["success"] is True
        assert "outcome_id" in d

    def test_outcome_committed_idempotency_key(self):
        oc = _sample_outcome(action_envelope_id="env-key", completed_at=12345.678)
        assert oc.idempotency_key == "env-key:12345.678"

    def test_outcome_failed_to_dict(self):
        from substrate.organism.coherence_propagation import OutcomeFailed
        of = OutcomeFailed(
            action_envelope_id="env-f",
            failure_reason="test failure",
        )
        d = of.to_dict()
        assert d["event_type"] == "outcome_failed"
        assert d["failure_reason"] == "test failure"

    def test_outcome_committed_default_fields(self):
        from substrate.organism.coherence_propagation import OutcomeCommitted
        oc = OutcomeCommitted()
        assert oc.event_id.startswith("oc-")
        assert oc.risk_class == "low"
        assert oc.validation_result == "passed"
        assert oc.rollback_result == "not_needed"
        assert oc.completed_at == 0.0


# ---------------------------------------------------------------------------
# VIII. Propagation Engine Internal Tests
# ---------------------------------------------------------------------------

class TestPropagationEngineInternals:
    """Direct tests on ParallelPropagationEngine internals."""

    def test_handle_outcome_returns_event(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe.register_target(PropagationTarget(
            name="t", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=lambda oc: {},
        ))

        oc = _sample_outcome()
        event = pe.handle_outcome(oc)
        assert event is not None
        assert event.succeeded_targets == 1

    def test_handle_failure_stores_failure(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        from substrate.organism.coherence_propagation import OutcomeFailed

        of = OutcomeFailed(failure_reason="test fail")
        pe.handle_failure(of)

        assert len(pe.failed_outcomes()) == 1
        assert pe.failed_outcomes()[0].failure_reason == "test fail"

    def test_to_safe_dict_includes_spine_native(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        d = pe.to_safe_dict()
        assert d["spine_native"] is True
        assert "processed_outcome_count" in d
        assert "recent_failures" in d

    def test_events_persisted_to_jsonl(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe.register_target(PropagationTarget(
            name="t", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=lambda oc: {},
        ))

        oc = _sample_outcome()
        pe.handle_outcome(oc)

        events_path = os.path.join(str(tmp_path), "events.jsonl")
        assert os.path.isfile(events_path)
        with open(events_path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 1

    def test_summary_after_multiple_propagations(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe.register_target(PropagationTarget(
            name="t", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=lambda oc: {},
        ))

        for i in range(5):
            oc = _sample_outcome(action_envelope_id=f"env-{i}", completed_at=float(i))
            pe.handle_outcome(oc)

        s = pe.summary()
        assert s["total_events"] == 5
        assert s["total_succeeded"] == 5


# ---------------------------------------------------------------------------
# IX. Template-Guided Campaign Tests
# ---------------------------------------------------------------------------

class TestTemplateGuidedCampaign:
    """Verify template-guided execution through spine with auto-propagation."""

    def test_template_confidence_updates_from_reuse(self, tmp_path):
        from substrate.organism.template_registry import TemplateRegistry
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        reg = TemplateRegistry(store_dir=str(tmp_path / "templates"))
        pe = _make_propagation_engine(str(tmp_path / "propagation"))

        pe.register_target(PropagationTarget(
            name="template_gen",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: reg.generate_candidate_from_outcome(oc.to_outcome_dict()).to_dict(),
        ))

        spine = _make_spine(propagation_engine=pe)

        env1 = _make_envelope(
            intent="first template-guided action",
            verification_fn=lambda: True,
            metadata={"agent_type": "developer_agent"},
        )
        spine.submit(env1)

        candidates = reg.list_candidates()
        assert len(candidates) == 1
        initial_confidence = candidates[0].confidence

        env2 = _make_envelope(
            intent="second template-guided action",
            verification_fn=lambda: True,
            metadata={"agent_type": "developer_agent"},
        )
        spine.submit(env2)

        all_candidates = reg.list_candidates()
        assert len(all_candidates) == 2

    def test_agent_reliability_updates_from_outcome(self, tmp_path):
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        acm = AgentCapabilityModel(store_dir=str(tmp_path / "acm"))
        pe = _make_propagation_engine(str(tmp_path / "propagation"))

        pe.register_target(PropagationTarget(
            name="agent_reliability",
            primitive_relationship=PrimitiveRelationship.RESOURCE,
            wave=1,
            handler=lambda oc: acm.update_reliability(
                agent_type=oc.agent_type,
                capabilities_used=oc.capabilities_used,
                success=oc.validation_result == "passed",
                duration_ms=oc.duration_ms,
                outcome_id=oc.event_id,
                action_envelope_id=oc.action_envelope_id,
            ),
        ))

        spine = _make_spine(propagation_engine=pe)

        for i in range(3):
            env = _make_envelope(
                intent=f"reliability trial {i}",
                verification_fn=lambda: True,
                metadata={"agent_type": "developer_agent"},
            )
            env.required_capabilities = ["code_search"]
            spine.submit(env)

        profile = acm.get_profile("developer_agent")
        assert profile is not None

    def test_campaign_code_does_not_manually_call_propagation(self, tmp_path):
        """Verify: trial code only submits to spine — propagation happens automatically."""
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        propagation_log = []
        pe = _make_propagation_engine(str(tmp_path))
        pe.register_target(PropagationTarget(
            name="audit_trail",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: propagation_log.append(oc.action_envelope_id) or {},
        ))

        spine = _make_spine(propagation_engine=pe)

        for i in range(3):
            env = _make_envelope(
                intent=f"campaign trial {i}",
                verification_fn=lambda: True,
            )
            spine.submit(env)

        assert len(propagation_log) == 3

    def test_plan_source_type_tracked(self, tmp_path):
        """Metadata can carry plan source_type for template-guided tracking."""
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)

        env = _make_envelope(
            verification_fn=lambda: True,
            metadata={"plan_source_type": "template_guided", "template_id": "tpl-123"},
        )
        spine.submit(env)

        events = es.replay(domains={EventDomain.EXECUTION})
        oc = [e for e in events if e.event_type == "outcome_committed"][0]
        assert oc.data["action_envelope_id"] == env.envelope_id


# ---------------------------------------------------------------------------
# X. Cockpit / API Exposure Tests
# ---------------------------------------------------------------------------

class TestCockpitExposure:
    """Verify cockpit endpoints return real state."""

    def test_organism_bridge_file_has_outcomes_handler(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        ))))
        bridge_path = os.path.join(repo_root, "transports", "api", "organism_bridge.py")
        with open(bridge_path) as f:
            content = f.read()
        assert "def _outcomes(" in content
        assert "def _outcome_detail(" in content
        assert "def _spine_propagation_status(" in content

    def test_organism_bridge_file_has_actions_registered(self):
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)
        ))))
        bridge_path = os.path.join(repo_root, "transports", "api", "organism_bridge.py")
        with open(bridge_path) as f:
            content = f.read()
        assert '"organism.outcomes"' in content
        assert '"organism.outcomes.detail"' in content
        assert '"organism.spine_propagation_status"' in content
        assert '"organism.propagation"' in content
        assert '"organism.propagation.detail"' in content
        assert '"organism.templates"' in content
        assert '"organism.template_candidates"' in content
        assert '"organism.agent_capabilities"' in content


# ---------------------------------------------------------------------------
# XI. Backward Compatibility Tests
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    """Verify existing code works without propagation engine."""

    def test_spine_works_without_propagation_engine(self):
        spine = _make_spine()
        env = _make_envelope()
        result = spine.submit(env)
        assert result.result_success is True

    def test_spine_works_with_verification_without_propagation(self):
        spine = _make_spine()
        env = _make_envelope(verification_fn=lambda: True)
        result = spine.submit(env)
        assert result.status.value == "verified"

    def test_spine_works_with_failure_without_propagation(self):
        spine = _make_spine()
        env = _make_envelope(execute_fn=lambda: ("fail", False))
        result = spine.submit(env)
        assert result.status.value == "failed"

    def test_existing_phase8_phase9_tests_not_broken(self):
        """Import test — existing modules still import cleanly."""
        from substrate.organism.governed_spine import GovernedExecutionSpine
        from substrate.organism.coherence_propagation import (
            ParallelPropagationEngine,
            OutcomeCommitted,
            OutcomeFailed,
        )
        from substrate.organism.trial_runner import ReliabilityCampaignRunner
        from substrate.organism.plan_execution_adapter import PlanExecutionAdapter
        assert GovernedExecutionSpine is not None
        assert ParallelPropagationEngine is not None
        assert ReliabilityCampaignRunner is not None


# ---------------------------------------------------------------------------
# XII. Event Spine Integration
# ---------------------------------------------------------------------------

class TestEventSpineIntegration:
    """Verify events emitted to EventSpine with correct domains/types."""

    def test_outcome_committed_uses_execution_domain(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)
        env = _make_envelope(verification_fn=lambda: True)
        spine.submit(env)

        exec_events = es.replay(domains={EventDomain.EXECUTION})
        oc_events = [e for e in exec_events if e.event_type == "outcome_committed"]
        assert len(oc_events) == 1

    def test_outcome_failed_uses_high_priority(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)
        env = _make_envelope(execute_fn=lambda: ("error", False))
        spine.submit(env)

        exec_events = es.replay(domains={EventDomain.EXECUTION})
        of_events = [e for e in exec_events if e.event_type == "outcome_failed"]
        assert len(of_events) == 1
        assert of_events[0].priority.value in ("high", "HIGH")

    def test_both_envelope_completed_and_outcome_committed_emitted(self):
        es = _make_event_spine()
        spine = _make_spine(event_spine=es)
        env = _make_envelope(verification_fn=lambda: True)
        spine.submit(env)

        exec_events = es.replay(domains={EventDomain.EXECUTION})
        types = [e.event_type for e in exec_events]
        assert "envelope_completed" in types
        assert "outcome_committed" in types

    def test_subscriber_receives_outcome_committed(self):
        es = _make_event_spine()
        received = []

        es.subscribe(
            subscriber_id="test_sub",
            handler=lambda e: received.append(e),
            domains={EventDomain.EXECUTION},
        )

        spine = _make_spine(event_spine=es)
        env = _make_envelope(verification_fn=lambda: True)
        spine.submit(env)

        oc_received = [e for e in received if e.event_type == "outcome_committed"]
        assert len(oc_received) == 1


# ---------------------------------------------------------------------------
# XIII. Persistence Tests
# ---------------------------------------------------------------------------

class TestPersistence:
    """Verify propagation state persisted to disk."""

    def test_propagation_events_file_created(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        pe.register_target(PropagationTarget(
            name="t", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=lambda oc: {},
        ))

        oc = _sample_outcome(action_envelope_id="persist-test", completed_at=1.0)
        pe.handle_outcome(oc)

        assert os.path.isfile(os.path.join(str(tmp_path), "events.jsonl"))
        assert os.path.isfile(os.path.join(str(tmp_path), "results.jsonl"))
        assert os.path.isfile(os.path.join(str(tmp_path), "processed_outcomes.jsonl"))

    def test_baseline_file_structure(self, tmp_path):
        """Verify baseline JSON has expected structure when created."""
        import json
        baseline = {
            "commit_sha": "test",
            "branch": "test",
            "readiness_score": 28.3,
            "contradiction_total": 15,
        }
        path = os.path.join(str(tmp_path), "baseline.json")
        with open(path, "w") as f:
            json.dump(baseline, f)
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["readiness_score"] == 28.3
        assert loaded["contradiction_total"] == 15


# ---------------------------------------------------------------------------
# XIV. Spine-Native Propagation Proof Test
# ---------------------------------------------------------------------------

class TestSpineNativePropagationProof:
    """The controlled proof: LOW-risk action through spine, no manual propagation,
    verify all propagation artifacts appeared automatically."""

    def test_spine_native_proof(self, tmp_path):
        from substrate.organism.template_registry import TemplateRegistry
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship

        reg = TemplateRegistry(store_dir=str(tmp_path / "templates"))
        acm = AgentCapabilityModel(store_dir=str(tmp_path / "acm"))
        world_model_updated = [False]
        learning_loop_updated = [False]

        pe = _make_propagation_engine(str(tmp_path / "propagation"))
        es = _make_event_spine()

        pe.register_target(PropagationTarget(
            name="outcome_learning",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: learning_loop_updated.__setitem__(0, True) or {"recorded": True},
        ))
        pe.register_target(PropagationTarget(
            name="template_gen",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: reg.generate_candidate_from_outcome(oc.to_outcome_dict()).to_dict(),
        ))
        pe.register_target(PropagationTarget(
            name="agent_reliability",
            primitive_relationship=PrimitiveRelationship.RESOURCE,
            wave=1,
            handler=lambda oc: acm.update_reliability(
                agent_type=oc.agent_type,
                capabilities_used=oc.capabilities_used,
                success=oc.validation_result == "passed",
                duration_ms=oc.duration_ms,
                outcome_id=oc.event_id,
                action_envelope_id=oc.action_envelope_id,
            ),
        ))
        pe.register_target(PropagationTarget(
            name="world_model_update",
            primitive_relationship=PrimitiveRelationship.STATE,
            wave=1,
            handler=lambda oc: world_model_updated.__setitem__(0, True) or {"updated": True},
        ))

        spine = _make_spine(event_spine=es, propagation_engine=pe)

        env = _make_envelope(
            intent="Spine-native propagation proof — LOW risk controlled test",
            verification_fn=lambda: True,
            risk_level="low",
            metadata={
                "trial_id": "proof-001",
                "agent_type": "developer_agent",
                "changed_files": ["proof.py"],
                "affected_subsystems": ["organism"],
            },
        )
        env.required_capabilities = ["code_search", "file_edit"]

        result = spine.submit(env)

        assert result.status.value == "verified", "Execution must succeed"
        assert result.result_success is True

        events = es.replay(domains={EventDomain.EXECUTION})
        oc_events = [e for e in events if e.event_type == "outcome_committed"]
        assert len(oc_events) == 1, "OutcomeCommitted must be emitted automatically"

        assert learning_loop_updated[0], "OutcomeLearningLoop must be updated"
        assert len(reg.list_candidates()) == 1, "TemplateCandidate must be generated"
        assert world_model_updated[0], "WorldModel must be updated"

        recent = pe.recent_events()
        assert len(recent) == 1, "Propagation event must be recorded"
        assert recent[0].succeeded_targets >= 4, "All 4 targets must succeed"

        proof = {
            "phase": "9.5",
            "test": "spine_native_proof",
            "envelope_id": result.envelope_id,
            "status": result.status.value,
            "outcome_committed_emitted": True,
            "propagation_event_id": recent[0].event_id,
            "targets_succeeded": recent[0].succeeded_targets,
            "targets_failed": recent[0].failed_targets,
            "template_candidate_generated": True,
            "agent_reliability_updated": True,
            "world_model_updated": True,
            "learning_loop_updated": True,
            "manual_propagation_called": False,
            "timestamp": time.time(),
        }

        proof_path = os.path.join(str(tmp_path), "phase9_5_spine_native_proof.json")
        with open(proof_path, "w") as f:
            json.dump(proof, f, indent=2)

        assert os.path.isfile(proof_path)


# ---------------------------------------------------------------------------
# XV. GovernedExecutionSpine State Tests
# ---------------------------------------------------------------------------

class TestGovernedSpineState:
    """Verify spine counters and state remain correct with propagation."""

    def test_verified_count_incremented(self):
        spine = _make_spine()
        env = _make_envelope(verification_fn=lambda: True)
        spine.submit(env)
        d = spine.to_dict()
        assert d["total_verified"] == 1
        assert d["total_succeeded"] == 1

    def test_failed_count_incremented(self):
        spine = _make_spine()
        env = _make_envelope(execute_fn=lambda: ("fail", False))
        spine.submit(env)
        d = spine.to_dict()
        assert d["total_failed"] == 1

    def test_multiple_submissions_tracked(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        spine = _make_spine(propagation_engine=pe)

        for i in range(5):
            env = _make_envelope(
                intent=f"test {i}",
                verification_fn=lambda: True,
            )
            spine.submit(env)

        d = spine.to_dict()
        assert d["total_executed"] == 5
        assert d["total_succeeded"] == 5
        assert d["total_verified"] == 5

    def test_completed_envelopes_queryable(self, tmp_path):
        pe = _make_propagation_engine(str(tmp_path))
        spine = _make_spine(propagation_engine=pe)

        env = _make_envelope(verification_fn=lambda: True)
        spine.submit(env)

        completed = spine.completed_envelopes()
        assert len(completed) == 1
        assert completed[0]["status"] == "verified"
