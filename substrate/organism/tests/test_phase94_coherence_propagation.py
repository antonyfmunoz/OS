"""Phase 9.4 tests — Template Registry, Agent Capability Model, Coherence Propagation.

60+ tests covering:
  - TemplateRegistry (creation, serialization, approval, rejection, promotion, evidence, confidence, reuse)
  - AgentCapabilityModel (profile, reliability, tracking, serialization)
  - CoherencePropagation (event creation, target registration, wave ordering, parallel execution,
    failure isolation, idempotency, persistence)
  - Integration (outcome→template, outcome→memory, agent reliability from outcome,
    composition template reuse, template-guided plan, governance preservation)
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ---------------------------------------------------------------------------
# TemplateRegistry tests
# ---------------------------------------------------------------------------

class TestTemplateRegistry:
    def _make_registry(self, tmpdir: str):
        from substrate.organism.template_registry import TemplateRegistry
        return TemplateRegistry(store_dir=tmpdir)

    def _sample_outcome(self, **overrides) -> dict:
        base = {
            "outcome_id": "out-001",
            "action_type": "resolve_missing_files",
            "description": "Fix missing file contradiction",
            "success": True,
            "agent_type": "developer_agent",
            "capabilities_used": ["code_search", "file_edit"],
            "risk_class": "low",
            "evidence": ["file found at alternate path"],
            "trial_id": "trial-001",
            "envelope_id": "env-001",
        }
        base.update(overrides)
        return base

    def test_create_candidate_from_outcome(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        outcome = self._sample_outcome()
        tpl = reg.generate_candidate_from_outcome(outcome)
        assert tpl.template_id.startswith("tpl-")
        assert tpl.observed_success_count == 1
        assert tpl.observed_failure_count == 0
        assert tpl.confidence > 0

    def test_candidate_serialization_roundtrip(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        data = tpl.to_dict()
        assert data["template_type"] == "world_model_accuracy_fix"
        assert isinstance(data["reusable_steps"], list)
        assert isinstance(data["evidence"], list)
        json_str = json.dumps(data, default=str)
        parsed = json.loads(json_str)
        assert parsed["template_id"] == tpl.template_id

    def test_candidate_persisted_to_jsonl(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        reg.generate_candidate_from_outcome(self._sample_outcome())
        path = os.path.join(str(tmp_path), "template_candidates.jsonl")
        assert os.path.isfile(path)
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert "template_id" in data

    def test_submit_prebuilt_candidate(self, tmp_path):
        from substrate.organism.template_registry import TemplateCandidate, TemplateType, TemplateStatus
        reg = self._make_registry(str(tmp_path))
        c = TemplateCandidate(template_type=TemplateType.TEST_REPAIR, status=TemplateStatus.RAW)
        result = reg.submit_candidate(c)
        assert reg.get_candidate(result.template_id) is not None

    def test_promote_to_candidate_status(self, tmp_path):
        from substrate.organism.template_registry import TemplateStatus
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        assert tpl.status == TemplateStatus.RAW
        assert reg.promote_to_candidate(tpl.template_id)
        assert tpl.status == TemplateStatus.CANDIDATE

    def test_approve_candidate(self, tmp_path):
        from substrate.organism.template_registry import TemplateStatus
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        assert reg.approve(tpl.template_id, decided_by="operator")
        assert tpl.status == TemplateStatus.APPROVED

    def test_promote_to_canonical(self, tmp_path):
        from substrate.organism.template_registry import TemplateStatus
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        reg.approve(tpl.template_id)
        assert reg.promote(tpl.template_id)
        assert tpl.status == TemplateStatus.PROMOTED
        assert len(reg.list_promoted()) == 1

    def test_reject_candidate(self, tmp_path):
        from substrate.organism.template_registry import TemplateStatus
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        assert reg.reject(tpl.template_id, reason="Not reusable")
        assert tpl.status == TemplateStatus.REJECTED

    def test_supersede_template(self, tmp_path):
        from substrate.organism.template_registry import TemplateStatus
        reg = self._make_registry(str(tmp_path))
        old = reg.generate_candidate_from_outcome(self._sample_outcome())
        new = reg.generate_candidate_from_outcome(self._sample_outcome(outcome_id="out-002"))
        assert reg.supersede(old.template_id, new.template_id)
        assert old.status == TemplateStatus.SUPERSEDED

    def test_deprecate_template(self, tmp_path):
        from substrate.organism.template_registry import TemplateStatus
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        assert reg.deprecate(tpl.template_id)
        assert tpl.status == TemplateStatus.DEPRECATED

    def test_record_usage_updates_confidence(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        initial = tpl.confidence
        reg.record_usage(tpl.template_id, success=True)
        assert tpl.observed_success_count == 2
        assert tpl.confidence >= initial

    def test_record_usage_failure_reduces_confidence(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        reg.record_usage(tpl.template_id, success=False)
        assert tpl.observed_failure_count == 1
        assert tpl.confidence < 1.0

    def test_find_matching_promoted_first(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        reg.approve(tpl.template_id)
        reg.promote(tpl.template_id)
        matches = reg.find_matching("resolve_missing_files")
        assert len(matches) >= 1
        assert matches[0].template_id == tpl.template_id

    def test_find_matching_no_match(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        matches = reg.find_matching("nonexistent_action")
        assert matches == []

    def test_pending_approvals(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        approvals = reg.pending_approvals()
        assert len(approvals) >= 1
        assert any(a.template_id == tpl.template_id for a in approvals)

    def test_summary_structure(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        reg.generate_candidate_from_outcome(self._sample_outcome())
        s = reg.summary()
        assert "total_candidates" in s
        assert "by_status" in s
        assert "promoted_count" in s

    def test_safe_dict_no_internal_details(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        reg.generate_candidate_from_outcome(self._sample_outcome())
        safe = reg.to_safe_dict()
        assert "candidates" in safe
        for c in safe["candidates"]:
            assert "source_outcome_ids" not in c

    def test_failure_outcome_low_confidence(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome(success=False))
        assert tpl.observed_failure_count == 1
        assert tpl.confidence < 0.5

    def test_template_type_inference(self):
        from substrate.organism.template_registry import _infer_template_type, TemplateType
        assert _infer_template_type("resolve_missing_files") == TemplateType.WORLD_MODEL_ACCURACY_FIX
        assert _infer_template_type("run_probes") == TemplateType.MAINTENANCE_ACTION
        assert _infer_template_type("", "fix contradiction") == TemplateType.CONTRADICTION_FIX
        assert _infer_template_type("", "improve readiness") == TemplateType.READINESS_IMPROVEMENT

    def test_decisions_persisted(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        tpl = reg.generate_candidate_from_outcome(self._sample_outcome())
        reg.approve(tpl.template_id)
        path = os.path.join(str(tmp_path), "template_decisions.jsonl")
        assert os.path.isfile(path)

    def test_multiple_candidates_independent(self, tmp_path):
        reg = self._make_registry(str(tmp_path))
        t1 = reg.generate_candidate_from_outcome(self._sample_outcome(outcome_id="o1"))
        t2 = reg.generate_candidate_from_outcome(self._sample_outcome(outcome_id="o2"))
        reg.reject(t1.template_id, reason="bad")
        assert t2.status.value == "raw"


# ---------------------------------------------------------------------------
# AgentCapabilityModel tests
# ---------------------------------------------------------------------------

class TestAgentCapabilityModel:
    def _make_model(self, tmpdir: str):
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        return AgentCapabilityModel(store_dir=tmpdir)

    def test_update_reliability_creates_profile(self, tmp_path):
        model = self._make_model(str(tmp_path))
        records = model.update_reliability("developer_agent", ["file_edit"], True)
        assert len(records) == 1
        profile = model.get_profile("developer_agent")
        assert profile is not None
        assert profile.total_attempts == 1
        assert profile.total_successes == 1

    def test_capability_confidence_after_success(self, tmp_path):
        model = self._make_model(str(tmp_path))
        model.update_reliability("developer_agent", ["file_edit"], True)
        cap = model.get_capability("developer_agent", "file_edit")
        assert cap is not None
        assert cap.confidence == 1.0

    def test_capability_confidence_after_failure(self, tmp_path):
        model = self._make_model(str(tmp_path))
        model.update_reliability("developer_agent", ["file_edit"], True)
        model.update_reliability("developer_agent", ["file_edit"], False)
        cap = model.get_capability("developer_agent", "file_edit")
        assert cap.confidence == 0.5

    def test_multiple_capabilities_single_call(self, tmp_path):
        model = self._make_model(str(tmp_path))
        records = model.update_reliability("developer_agent", ["file_edit", "code_search", "test_run"], True)
        assert len(records) == 3
        profile = model.get_profile("developer_agent")
        assert len(profile.capabilities) == 3

    def test_average_duration_tracking(self, tmp_path):
        model = self._make_model(str(tmp_path))
        model.update_reliability("developer_agent", ["file_edit"], True, duration_ms=100)
        model.update_reliability("developer_agent", ["file_edit"], True, duration_ms=200)
        cap = model.get_capability("developer_agent", "file_edit")
        assert cap.average_duration_ms == 150.0

    def test_linked_ids_tracked(self, tmp_path):
        model = self._make_model(str(tmp_path))
        model.update_reliability(
            "developer_agent", ["file_edit"], True,
            outcome_id="out-1", action_envelope_id="env-1", template_id="tpl-1",
        )
        cap = model.get_capability("developer_agent", "file_edit")
        assert "out-1" in cap.linked_outcome_ids
        assert "env-1" in cap.linked_action_envelope_ids
        assert "tpl-1" in cap.linked_template_ids

    def test_risk_classes_tracked(self, tmp_path):
        model = self._make_model(str(tmp_path))
        model.update_reliability("developer_agent", ["file_edit"], True, risk_class="low")
        model.update_reliability("developer_agent", ["file_edit"], True, risk_class="medium")
        cap = model.get_capability("developer_agent", "file_edit")
        assert "low" in cap.risk_classes_handled
        assert "medium" in cap.risk_classes_handled

    def test_get_reliability_unknown_returns_zero(self, tmp_path):
        model = self._make_model(str(tmp_path))
        assert model.get_reliability("unknown_agent", "unknown_cap") == 0.0

    def test_persistence_roundtrip(self, tmp_path):
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        model = self._make_model(str(tmp_path))
        model.update_reliability("dev", ["search"], True)
        model.update_reliability("dev", ["search"], False)
        model2 = AgentCapabilityModel(store_dir=str(tmp_path))
        assert model2.get_reliability("dev", "search") == 0.5

    def test_list_profiles(self, tmp_path):
        model = self._make_model(str(tmp_path))
        model.update_reliability("dev", ["a"], True)
        model.update_reliability("auditor", ["b"], True)
        profiles = model.list_profiles()
        assert len(profiles) == 2

    def test_summary_structure(self, tmp_path):
        model = self._make_model(str(tmp_path))
        model.update_reliability("dev", ["a"], True)
        s = model.summary()
        assert "total_profiles" in s
        assert "total_records" in s
        assert "profiles" in s

    def test_safe_dict_structure(self, tmp_path):
        model = self._make_model(str(tmp_path))
        model.update_reliability("dev", ["a", "b"], True)
        safe = model.to_safe_dict()
        assert "profiles" in safe
        assert "dev" in safe["profiles"]
        assert "a" in safe["profiles"]["dev"]["capabilities"]

    def test_overall_reliability_multiple_caps(self, tmp_path):
        model = self._make_model(str(tmp_path))
        model.update_reliability("dev", ["a"], True)
        model.update_reliability("dev", ["b"], False)
        profile = model.get_profile("dev")
        assert profile.overall_reliability == 0.5

    def test_last_success_failure_timestamps(self, tmp_path):
        model = self._make_model(str(tmp_path))
        model.update_reliability("dev", ["a"], True)
        model.update_reliability("dev", ["a"], False)
        cap = model.get_capability("dev", "a")
        assert cap.last_success_at > 0
        assert cap.last_failure_at > 0


# ---------------------------------------------------------------------------
# CoherencePropagation tests
# ---------------------------------------------------------------------------

class TestCoherencePropagation:
    def _make_outcome(self, **overrides):
        from substrate.organism.coherence_propagation import OutcomeCommitted
        defaults = dict(
            action_envelope_id="env-001",
            trial_id="trial-001",
            action_type="resolve_missing_files",
            risk_class="low",
            agent_type="developer_agent",
            capabilities_used=["code_search", "file_edit"],
            validation_result="passed",
            evidence=["file exists at path"],
        )
        defaults.update(overrides)
        return OutcomeCommitted(**defaults)

    def _make_engine(self, tmpdir: str):
        from substrate.organism.coherence_propagation import ParallelPropagationEngine
        return ParallelPropagationEngine(store_dir=tmpdir)

    def test_outcome_committed_serialization(self):
        oc = self._make_outcome()
        d = oc.to_dict()
        assert d["event_type"] == "outcome_committed"
        assert d["validation_result"] == "passed"

    def test_outcome_failed_serialization(self):
        from substrate.organism.coherence_propagation import OutcomeFailed
        of = OutcomeFailed(failure_reason="validation_failed")
        d = of.to_dict()
        assert d["event_type"] == "outcome_failed"
        assert d["failure_reason"] == "validation_failed"

    def test_outcome_to_outcome_dict(self):
        oc = self._make_outcome()
        d = oc.to_outcome_dict()
        assert d["success"] is True
        assert d["action_type"] == "resolve_missing_files"

    def test_register_target(self, tmp_path):
        from substrate.organism.coherence_propagation import PropagationTarget, PrimitiveRelationship
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="test_target",
            primitive_relationship=PrimitiveRelationship.OUTCOME,
            wave=1,
            handler=lambda oc: {"ok": True},
        ))
        assert len(engine._targets) == 1

    def test_propagate_single_target(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship, PropagationStatus,
        )
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="outcome_learning",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: {"recorded": True},
        ))
        event = engine.propagate(self._make_outcome())
        assert event.status == PropagationStatus.COMPLETED
        assert event.succeeded_targets == 1
        assert event.failed_targets == 0

    def test_propagate_parallel_wave(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship, PropagationStatus,
        )
        engine = self._make_engine(str(tmp_path))
        for name in ["t1", "t2", "t3"]:
            engine.register_target(PropagationTarget(
                name=name,
                primitive_relationship=PrimitiveRelationship.STATE,
                wave=1,
                handler=lambda oc: {"name": "done"},
            ))
        event = engine.propagate(self._make_outcome())
        assert event.succeeded_targets == 3
        assert len(event.waves) == 1

    def test_two_waves_ordered(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship,
        )
        order = []
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="wave1",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: (order.append(1), {"w": 1})[1],
        ))
        engine.register_target(PropagationTarget(
            name="wave2",
            primitive_relationship=PrimitiveRelationship.STATE,
            wave=2,
            handler=lambda oc: (order.append(2), {"w": 2})[1],
        ))
        engine.propagate(self._make_outcome())
        assert order == [1, 2]

    def test_failed_target_does_not_block_siblings(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship, PropagationStatus,
        )
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="good",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: {"ok": True},
        ))
        def failing_handler(oc):
            raise RuntimeError("intentional failure")
        engine.register_target(PropagationTarget(
            name="bad",
            primitive_relationship=PrimitiveRelationship.STATE,
            wave=1,
            handler=failing_handler,
        ))
        event = engine.propagate(self._make_outcome())
        assert event.succeeded_targets == 1
        assert event.failed_targets == 1
        assert event.status == PropagationStatus.FAILED

    def test_skipped_target_no_handler(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship, PropagationStatus,
        )
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="no_handler",
            primitive_relationship=PrimitiveRelationship.SIGNAL,
            wave=1,
        ))
        event = engine.propagate(self._make_outcome())
        assert event.skipped_targets == 1

    def test_event_persisted_to_jsonl(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship,
        )
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="t",
            primitive_relationship=PrimitiveRelationship.OUTCOME,
            wave=1,
            handler=lambda oc: {},
        ))
        engine.propagate(self._make_outcome())
        events_path = os.path.join(str(tmp_path), "events.jsonl")
        assert os.path.isfile(events_path)
        with open(events_path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 1

    def test_results_persisted_to_jsonl(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship,
        )
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="t",
            primitive_relationship=PrimitiveRelationship.OUTCOME,
            wave=1,
            handler=lambda oc: {"x": 1},
        ))
        engine.propagate(self._make_outcome())
        results_path = os.path.join(str(tmp_path), "results.jsonl")
        assert os.path.isfile(results_path)

    def test_get_event_by_id(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship,
        )
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="t", primitive_relationship=PrimitiveRelationship.OUTCOME,
            wave=1, handler=lambda oc: {},
        ))
        event = engine.propagate(self._make_outcome())
        found = engine.get_event(event.event_id)
        assert found is not None
        assert found.event_id == event.event_id

    def test_recent_events(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship,
        )
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="t", primitive_relationship=PrimitiveRelationship.OUTCOME,
            wave=1, handler=lambda oc: {},
        ))
        engine.propagate(self._make_outcome())
        engine.propagate(self._make_outcome())
        assert len(engine.recent_events()) == 2

    def test_summary_structure(self, tmp_path):
        engine = self._make_engine(str(tmp_path))
        s = engine.summary()
        assert "total_events" in s
        assert "total_targets_processed" in s
        assert "registered_targets" in s

    def test_safe_dict_structure(self, tmp_path):
        engine = self._make_engine(str(tmp_path))
        safe = engine.to_safe_dict()
        assert "summary" in safe
        assert "recent_events" in safe
        assert "registered_targets" in safe

    def test_idempotent_target(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship,
        )
        call_count = [0]
        def idempotent_handler(oc):
            call_count[0] += 1
            return {"count": call_count[0]}
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="idempotent", primitive_relationship=PrimitiveRelationship.STATE,
            wave=1, handler=idempotent_handler,
        ))
        oc = self._make_outcome()
        engine.propagate(oc)
        engine.propagate(oc)
        assert call_count[0] == 2

    def test_propagation_result_has_evidence(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            PropagationTarget, PrimitiveRelationship,
        )
        engine = self._make_engine(str(tmp_path))
        engine.register_target(PropagationTarget(
            name="t", primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1, handler=lambda oc: {"result": "ok"},
        ))
        event = engine.propagate(self._make_outcome())
        result = event.waves[0].results[0]
        assert result.input_evidence
        assert result.output_artifact


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_outcome_to_template_to_composition(self, tmp_path):
        """Full flow: outcome → template → composition plan uses template."""
        from substrate.organism.template_registry import TemplateRegistry
        from substrate.organism.composition_engine import (
            CompositionEngine, CompositionIntent, PlanSourceType,
        )

        reg = TemplateRegistry(store_dir=str(tmp_path / "templates"))

        outcome = {
            "outcome_id": "int-001",
            "action_type": "run_contradiction_engine",
            "description": "Detect and fix contradictions",
            "success": True,
            "agent_type": "developer_agent",
            "capabilities_used": ["contradiction_detection"],
            "risk_class": "low",
            "evidence": ["contradictions reduced"],
        }
        tpl = reg.generate_candidate_from_outcome(outcome)
        reg.approve(tpl.template_id)
        reg.promote(tpl.template_id)

        engine = CompositionEngine(template_registry=reg)
        intent = CompositionIntent(description="fix contradictions in world model")
        plan = engine.compose(intent)

        assert plan.source_type == PlanSourceType.TEMPLATE_GUIDED
        assert plan.template_id == tpl.template_id
        assert plan.reused_template is True

    def test_outcome_to_memory_candidates(self, tmp_path):
        from substrate.organism.memory_promotion import MemoryPromotionPipeline
        pipeline = MemoryPromotionPipeline(store_dir=str(tmp_path))
        outcome = {
            "action_type": "fix_deployment_state",
            "description": "Aligned deployment hash",
            "success": True,
            "agent_type": "deployment_agent",
            "risk_class": "medium",
            "evidence": ["hash matches"],
            "governance_mode": "assisted",
        }
        candidates = pipeline.generate_candidate_from_outcome(outcome)
        assert len(candidates) >= 2
        contents = [c.content for c in candidates]
        assert any("pattern" in c.lower() for c in contents)
        assert any("lesson" in c.lower() for c in contents)

    def test_outcome_to_memory_failure_mode(self, tmp_path):
        from substrate.organism.memory_promotion import MemoryPromotionPipeline
        pipeline = MemoryPromotionPipeline(store_dir=str(tmp_path))
        outcome = {
            "action_type": "deploy",
            "description": "Deploy failed",
            "success": False,
            "agent_type": "deployment_agent",
            "risk_class": "high",
            "error": "container crash on startup",
        }
        candidates = pipeline.generate_candidate_from_outcome(outcome)
        contents = [c.content for c in candidates]
        assert any("failure mode" in c.lower() for c in contents)

    def test_agent_reliability_update_from_outcome(self, tmp_path):
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        model = AgentCapabilityModel(store_dir=str(tmp_path))
        model.update_reliability(
            "developer_agent", ["code_search", "file_edit"], True,
            outcome_id="out-x", risk_class="low",
        )
        assert model.get_reliability("developer_agent", "code_search") == 1.0
        assert model.get_reliability("developer_agent", "file_edit") == 1.0

    def test_composition_deterministic_when_no_templates(self, tmp_path):
        from substrate.organism.template_registry import TemplateRegistry
        from substrate.organism.composition_engine import (
            CompositionEngine, CompositionIntent, PlanSourceType,
        )
        reg = TemplateRegistry(store_dir=str(tmp_path / "tpl"))
        engine = CompositionEngine(template_registry=reg)
        plan = engine.compose(CompositionIntent(description="run safe maintenance"))
        assert plan.source_type == PlanSourceType.DETERMINISTIC_GENERATED
        assert plan.template_id == ""

    def test_template_confidence_increases_on_reuse(self, tmp_path):
        from substrate.organism.template_registry import TemplateRegistry
        reg = TemplateRegistry(store_dir=str(tmp_path))
        tpl = reg.generate_candidate_from_outcome({
            "outcome_id": "o1", "action_type": "run_probes",
            "description": "probes", "success": True,
            "agent_type": "developer_agent", "capabilities_used": ["test_run"],
        })
        before = tpl.confidence
        reg.record_usage(tpl.template_id, success=True)
        assert tpl.confidence >= before

    def test_full_propagation_with_real_targets(self, tmp_path):
        from substrate.organism.coherence_propagation import (
            ParallelPropagationEngine, PropagationTarget, PrimitiveRelationship,
            OutcomeCommitted, PropagationStatus,
        )
        from substrate.organism.template_registry import TemplateRegistry
        from substrate.organism.agent_capability_model import AgentCapabilityModel
        from substrate.organism.memory_promotion import MemoryPromotionPipeline

        tpl_dir = str(tmp_path / "templates")
        agent_dir = str(tmp_path / "agents")
        mem_dir = str(tmp_path / "memory")
        prop_dir = str(tmp_path / "propagation")

        reg = TemplateRegistry(store_dir=tpl_dir)
        acm = AgentCapabilityModel(store_dir=agent_dir)
        mpp = MemoryPromotionPipeline(store_dir=mem_dir)

        engine = ParallelPropagationEngine(store_dir=prop_dir)

        engine.register_target(PropagationTarget(
            name="template_gen",
            primitive_relationship=PrimitiveRelationship.ACTION,
            wave=1,
            handler=lambda oc: reg.generate_candidate_from_outcome(oc.to_outcome_dict()).to_dict(),
        ))
        engine.register_target(PropagationTarget(
            name="agent_reliability",
            primitive_relationship=PrimitiveRelationship.RESOURCE,
            wave=1,
            handler=lambda oc: {
                "records": len(acm.update_reliability(
                    oc.agent_type, oc.capabilities_used, oc.validation_result == "passed",
                    outcome_id=oc.event_id, risk_class=oc.risk_class,
                ))
            },
        ))
        engine.register_target(PropagationTarget(
            name="memory_gen",
            primitive_relationship=PrimitiveRelationship.FEEDBACK,
            wave=1,
            handler=lambda oc: {
                "candidates": len(mpp.generate_candidate_from_outcome(oc.to_outcome_dict()))
            },
        ))

        oc = OutcomeCommitted(
            action_type="resolve_missing_files",
            agent_type="developer_agent",
            capabilities_used=["code_search", "file_edit"],
            validation_result="passed",
            evidence=["file found"],
        )
        event = engine.propagate(oc)

        assert event.succeeded_targets == 3
        assert event.failed_targets == 0
        assert len(reg.list_candidates()) == 1
        assert acm.get_reliability("developer_agent", "code_search") == 1.0
        assert mpp.summary()["total_candidates"] > 0

    def test_governance_preserved_in_template_guided_plan(self, tmp_path):
        """Template-guided plan must preserve governance mode and risk from template."""
        from substrate.organism.template_registry import TemplateRegistry
        from substrate.organism.composition_engine import CompositionEngine, CompositionIntent

        reg = TemplateRegistry(store_dir=str(tmp_path / "tpl"))
        outcome = {
            "action_type": "fix_deployment_state",
            "description": "fix deployment state",
            "success": True,
            "agent_type": "deployment_agent",
            "capabilities_used": ["endpoint_verify"],
            "risk_class": "high",
            "governance_mode": "operator_required",
            "steps": [
                {"action": "check", "description": "Check state", "risk": "low", "gov": "autonomous", "verify": "ok"},
                {"action": "deploy", "description": "Deploy", "risk": "high", "gov": "operator_required", "verify": "hash"},
            ],
        }
        tpl = reg.generate_candidate_from_outcome(outcome)
        reg.approve(tpl.template_id)
        reg.promote(tpl.template_id)

        engine = CompositionEngine(template_registry=reg)
        plan = engine.compose(CompositionIntent(description="fix deployment state"))
        assert plan.reused_template is True
        assert any(s.governance_mode.value == "operator_required" for s in plan.steps)


# ---------------------------------------------------------------------------
# Primitive relationship coverage
# ---------------------------------------------------------------------------

class TestPrimitiveRelationships:
    def test_all_primitives_exist(self):
        from substrate.organism.coherence_propagation import PrimitiveRelationship
        expected = {"state", "change", "constraint", "resource", "time",
                    "signal", "feedback", "goal", "action", "outcome"}
        actual = {p.value for p in PrimitiveRelationship}
        assert expected == actual

    def test_all_template_types_exist(self):
        from substrate.organism.template_registry import TemplateType
        assert len(TemplateType) == 15

    def test_all_agent_types_exist(self):
        from substrate.organism.template_registry import AgentType
        assert len(AgentType) == 6

    def test_all_capability_names_exist(self):
        from substrate.organism.template_registry import CapabilityName
        assert len(CapabilityName) == 13
