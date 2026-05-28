"""Tests for composition engine."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from substrate.organism.composition_engine import (
    CapabilityMatch,
    CompositionConstraint,
    CompositionContext,
    CompositionEngine,
    CompositionIntent,
    CompositionPlan,
    CompositionRisk,
    CompositionStep,
    GovernanceMode,
    RiskClass,
    StepStatus,
    compose_plan,
    persist_plan,
)


class TestCompositionIntent:
    def test_creation(self):
        intent = CompositionIntent(description="fix deployment truth")
        assert intent.description == "fix deployment truth"
        assert intent.category == "general"

    def test_to_dict(self):
        intent = CompositionIntent(description="test", priority="high")
        d = intent.to_dict()
        assert d["priority"] == "high"


class TestCompositionStep:
    def test_creation(self):
        step = CompositionStep(
            description="Run probe",
            action="run_probes",
            risk_class=RiskClass.LOW,
            governance_mode=GovernanceMode.AUTONOMOUS,
        )
        assert step.action == "run_probes"
        assert step.status == StepStatus.PENDING
        assert step.id

    def test_to_dict(self):
        step = CompositionStep(
            description="Test step",
            action="test",
            depends_on=["abc"],
            verification="Check output",
        )
        d = step.to_dict()
        assert d["action"] == "test"
        assert d["depends_on"] == ["abc"]
        assert d["verification"] == "Check output"


class TestCompositionPlan:
    def _make_plan(self) -> CompositionPlan:
        plan = CompositionPlan(
            intent=CompositionIntent(description="test plan"),
        )
        s1 = CompositionStep(id="s1", description="Step 1", action="assess")
        s2 = CompositionStep(id="s2", description="Step 2", action="execute", depends_on=["s1"])
        s3 = CompositionStep(id="s3", description="Step 3", action="verify", depends_on=["s2"])
        plan.steps = [s1, s2, s3]
        return plan

    def test_ready_steps_initial(self):
        plan = self._make_plan()
        ready = plan.ready_steps()
        assert len(ready) == 1
        assert ready[0].id == "s1"

    def test_ready_steps_after_completion(self):
        plan = self._make_plan()
        plan.steps[0].status = StepStatus.COMPLETED
        ready = plan.ready_steps()
        assert len(ready) == 1
        assert ready[0].id == "s2"

    def test_summary(self):
        plan = self._make_plan()
        s = plan.summary()
        assert s["total_steps"] == 3
        assert s["step_status"]["pending"] == 3
        assert "plan_id" in s

    def test_to_dict_serialization(self):
        plan = self._make_plan()
        plan.risks.append(CompositionRisk(description="test risk", risk_class=RiskClass.MEDIUM))
        plan.constraints.append(CompositionConstraint(name="no_restart", description="Don't restart services"))
        d = plan.to_dict()
        serialized = json.dumps(d, default=str)
        parsed = json.loads(serialized)
        assert "summary" in parsed
        assert "steps" in parsed
        assert "risks" in parsed
        assert len(parsed["risks"]) == 1


class TestIntentClassification:
    def test_contradiction_intent(self):
        plan = compose_plan("fix deployment truth")
        assert plan.intent.category == "fix_contradictions"

    def test_readiness_intent(self):
        plan = compose_plan("improve readiness")
        assert plan.intent.category == "improve_readiness"

    def test_panel_intent(self):
        plan = compose_plan("wire missing panel")
        assert plan.intent.category == "wire_missing_panel"

    def test_maintenance_intent(self):
        plan = compose_plan("run safe maintenance")
        assert plan.intent.category == "safe_maintenance"

    def test_general_intent(self):
        plan = compose_plan("prepare autonomous low-risk execution")
        assert plan.intent.category == "general"


class TestCapabilityMatching:
    def test_capability_match(self):
        match = CapabilityMatch(
            capability_name="event_transport",
            entity_id="event_spine",
            status="available",
            confidence=0.9,
        )
        d = match.to_dict()
        assert d["capability"] == "event_transport"
        assert d["confidence"] == 0.9


class TestMissingDependencyDetection:
    def test_plan_has_evidence(self):
        plan = compose_plan("fix contradictions")
        assert len(plan.evidence) > 0
        assert any("entities" in e for e in plan.evidence)


class TestRiskClassification:
    def test_high_risk_plan(self):
        plan = compose_plan("fix deployment truth")
        assert plan.overall_risk in (RiskClass.HIGH, RiskClass.CRITICAL)

    def test_low_risk_plan(self):
        plan = compose_plan("improve readiness")
        assert plan.overall_risk in (RiskClass.LOW, RiskClass.MEDIUM)


class TestGovernanceRequirement:
    def test_operator_required_for_deployment(self):
        plan = compose_plan("fix deployment truth")
        assert plan.governance_required == GovernanceMode.OPERATOR_REQUIRED

    def test_assisted_for_maintenance(self):
        plan = compose_plan("run safe maintenance")
        assert plan.governance_required in (GovernanceMode.ASSISTED, GovernanceMode.OPERATOR_REQUIRED)


class TestCompositionEngine:
    def test_engine_compose(self):
        engine = CompositionEngine()
        intent = CompositionIntent(description="test")
        plan = engine.compose(intent)
        assert len(plan.steps) > 0
        assert plan.intent is not None


class TestPersistence:
    def test_persist_plan(self):
        plan = CompositionPlan(
            intent=CompositionIntent(description="test"),
        )
        plan.steps.append(CompositionStep(description="s1", action="a1"))
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            result = persist_plan(plan, path=path)
            assert os.path.isfile(result)
            with open(result) as f:
                data = json.loads(f.readline())
            assert "steps" in data
        finally:
            os.unlink(path)
