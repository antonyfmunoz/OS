"""Tests for Phase 6B: Plan Quality + Objective Reconstruction Layer v1.

Verifies:
- Objective reconstruction from raw strings
- Plan quality scoring (dimensions, verdicts)
- Plan explainability (structured output)
- Planner integration (raw_input → plan + quality + explanation)
- API endpoints (raw_input, quality gate, enriched responses)
- Metrics include quality fields
- Events for reconstruction/quality
- Regression: no execution bypasses
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase6b")
os.environ["PYTEST_CURRENT_TEST"] = "1"

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import get_event_stream, reset_event_stream
from umh.execution.approval import get_approval_store
from umh.orchestrator.engine import reset_orchestrator, start_orchestrator
from umh.orchestrator.task import (
    TaskStatus,
    reset_tasks,
)
from umh.planning.explanation import PlanExplanation, explain_plan
from umh.planning.models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanObjective,
    PlanSource,
    PlanStatus,
    PlanValidationResult,
)
from umh.planning.objective import reconstruct_objective
from umh.planning.planner import (
    create_plan,
    create_plan_from_raw,
    execute_plan,
    get_plan,
    list_plans,
    reset_plans,
)
from umh.planning.quality import (
    PlanQualityScore,
    QualityVerdict,
    score_plan,
)
from umh.planning.validator import validate_plan

client = TestClient(app)


def _reset():
    get_approval_store().reset()
    get_identity_store().reset()
    reset_event_stream()
    reset_orchestrator()
    reset_tasks()
    reset_plans()


def _start_fresh():
    _reset()
    return start_orchestrator()


def _create_identity(name="admin", scopes=None):
    store = get_identity_store()
    identity, raw_key = store.create_identity(name, scopes or ["admin"])
    return identity, raw_key, {"X-API-Key": raw_key}


# ── A. Objective Reconstruction Tests ──────────────────────────────


class TestObjectiveReconstruction:
    def test_raw_string_creates_objective(self):
        obj = reconstruct_objective("check system health")
        assert isinstance(obj, PlanObjective)
        assert obj.raw_input == "check system health"
        assert obj.title != ""

    def test_system_health_infers_intent(self):
        obj = reconstruct_objective("check system health")
        assert obj.intent_category == "system_health"
        assert obj.title == "inspect_system_status"

    def test_inspect_file_extracts_path(self):
        obj = reconstruct_objective("inspect /tmp/foo.txt")
        assert obj.intent_category == "file_inspect"
        assert obj.context.get("path") == "/tmp/foo.txt"

    def test_summarize_extracts_text(self):
        obj = reconstruct_objective("summarize hello world")
        assert obj.intent_category == "summarize"
        assert "hello world" in obj.context.get("text", "")

    def test_screenshot_intent(self):
        obj = reconstruct_objective("take a screenshot")
        assert obj.intent_category == "screenshot"
        assert obj.title == "computer_screenshot_review"

    def test_vague_input_produces_uncertainty(self):
        obj = reconstruct_objective("do something")
        assert obj.intent_category == "unknown"
        assert len(obj.uncertainty) > 0
        assert any("intent" in u.lower() for u in obj.uncertainty)

    def test_empty_input_flagged(self):
        obj = reconstruct_objective("")
        assert obj.intent_category == "unknown"
        assert len(obj.uncertainty) > 0
        assert obj.title == ""

    def test_dry_run_detected(self):
        obj = reconstruct_objective("check system health dry run")
        assert obj.dry_run is True
        assert "dry_run" in obj.inferred_constraints

    def test_max_steps_extracted(self):
        obj = reconstruct_objective("check system health max_steps: 3")
        assert obj.max_steps == 3

    def test_click_action_flags_approval(self):
        obj = reconstruct_objective("click on the button")
        assert obj.intent_category == "computer_action"
        assert any("approval" in u.lower() for u in obj.uncertainty)

    def test_directory_list_intent(self):
        obj = reconstruct_objective("list files in /opt/OS")
        assert obj.intent_category == "directory_list"
        assert obj.context.get("path") == "/opt/OS"

    def test_raw_input_preserved(self):
        raw = "  summarize this important document  "
        obj = reconstruct_objective(raw)
        assert obj.raw_input == raw

    def test_metrics_intent(self):
        obj = reconstruct_objective("show me the current metrics")
        assert obj.intent_category == "metrics"


# ── B. Quality Scoring Tests ──────────────────────────────────────


class TestQualityScoring:
    def test_valid_template_plan_passes(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "hi"})
        plan = create_plan(obj)
        validation = validate_plan(plan)
        quality = score_plan(plan, validation)
        assert quality.verdict == QualityVerdict.PASS
        assert quality.score >= 0.7

    def test_empty_plan_fails(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(objective=obj, steps=[])
        quality = score_plan(plan)
        assert quality.verdict == QualityVerdict.FAIL
        assert quality.score == 0.0

    def test_unsupported_op_fails(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="bad",
                    operation="browser_navigate",
                    execution_class="side_effect",
                ),
            ],
        )
        quality = score_plan(plan)
        assert quality.verdict == QualityVerdict.FAIL

    def test_approval_gated_passes_with_risk(self):
        _reset()
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="click",
                    operation="computer_click",
                    inputs={"x": 10, "y": 20},
                    execution_class="side_effect",
                ),
            ],
            source=PlanSource.MANUAL,
        )
        validation = validate_plan(plan)
        quality = score_plan(plan, validation)
        assert quality.verdict in (QualityVerdict.PASS, QualityVerdict.WARN)
        assert any("approval" in r.lower() or "risk" in r.lower() for r in quality.reasons)

    def test_too_many_steps_warns(self):
        obj = PlanObjective(title="test", max_steps=10)
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(name=f"s{i}", operation="summarize", execution_class="llm_call")
                for i in range(9)
            ],
        )
        quality = score_plan(plan)
        assert quality.dimensions["minimality"] < 0.7

    def test_vague_objective_warns(self):
        obj = PlanObjective(
            title="x",
            raw_input="x",
            intent_category="unknown",
            uncertainty=("Could not determine intent category",),
        )
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(name="s", operation="summarize", execution_class="llm_call"),
            ],
        )
        quality = score_plan(plan)
        assert quality.dimensions["specificity"] < 0.7
        assert any("uncertainty" in r.lower() for r in quality.reasons)

    def test_missing_inputs_lower_score(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="read",
                    operation="file_read",
                    inputs={},
                    execution_class="side_effect",
                ),
            ],
        )
        quality = score_plan(plan)
        assert quality.dimensions["executability"] < 0.8

    def test_minimal_valid_plan_scores_high(self):
        _reset()
        obj = PlanObjective(
            title="summarize_text",
            description="summarize some text",
            context={"text": "hi"},
        )
        plan = create_plan(obj)
        validation = validate_plan(plan)
        quality = score_plan(plan, validation)
        assert quality.score >= 0.7
        assert quality.dimensions["minimality"] == 1.0

    def test_all_dimensions_present(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(name="s", operation="summarize", execution_class="llm_call"),
            ],
        )
        quality = score_plan(plan)
        expected = {
            "completeness",
            "safety",
            "specificity",
            "executability",
            "minimality",
            "constraint_alignment",
        }
        assert set(quality.dimensions.keys()) == expected

    def test_failed_validation_fails_quality(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(name="s", operation="summarize", execution_class="llm_call"),
            ],
        )
        validation = PlanValidationResult(valid=False, errors=["bad step"])
        quality = score_plan(plan, validation)
        assert quality.verdict == QualityVerdict.FAIL


# ── C. Explainability Tests ───────────────────────────────────────


class TestExplainability:
    def test_returns_objective_summary(self):
        _reset()
        obj = PlanObjective(title="summarize_text", description="test text", context={"text": "hi"})
        plan = create_plan(obj)
        validation = validate_plan(plan)
        quality = score_plan(plan, validation)
        expl = explain_plan(plan, validation, quality)
        assert "summarize_text" in expl.objective_summary

    def test_lists_steps(self):
        _reset()
        obj = PlanObjective(title="inspect_system_status")
        plan = create_plan(obj)
        expl = explain_plan(plan)
        assert len(expl.steps_summary) == len(plan.steps)
        for s in expl.steps_summary:
            assert "name" in s
            assert "operation" in s

    def test_lists_assumptions(self):
        _reset()
        obj = PlanObjective(title="inspect_system_status")
        plan = create_plan(obj)
        expl = explain_plan(plan)
        assert len(expl.assumptions) > 0

    def test_lists_risks_for_shell(self):
        _reset()
        obj = PlanObjective(title="inspect_system_status")
        plan = create_plan(obj)
        expl = explain_plan(plan)
        assert any("shell" in r.lower() for r in expl.risks)

    def test_lists_approval_requirements(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="click",
                    operation="computer_click",
                    inputs={"x": 10, "y": 20},
                    execution_class="side_effect",
                ),
            ],
        )
        expl = explain_plan(plan)
        assert len(expl.approval_requirements) > 0
        assert any("approval" in a.lower() for a in expl.approval_requirements)

    def test_includes_quality_dimensions(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "hi"})
        plan = create_plan(obj)
        validation = validate_plan(plan)
        quality = score_plan(plan, validation)
        expl = explain_plan(plan, validation, quality)
        assert "score" in expl.quality_summary
        assert "verdict" in expl.quality_summary
        assert "dimensions" in expl.quality_summary

    def test_serializable_dict(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "hi"})
        plan = create_plan(obj)
        validation = validate_plan(plan)
        quality = score_plan(plan, validation)
        expl = explain_plan(plan, validation, quality)
        d = expl.to_dict()
        assert isinstance(d, dict)
        assert "objective_summary" in d
        assert "steps_summary" in d
        assert "assumptions" in d
        assert "risks" in d
        assert "approval_requirements" in d
        assert "plan_selection_reason" in d
        assert "safety_assessment" in d
        assert "quality_summary" in d

    def test_plan_selection_reason_template(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "hi"})
        plan = create_plan(obj)
        expl = explain_plan(plan)
        assert "template" in expl.plan_selection_reason.lower()

    def test_safety_assessment_present(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "hi"})
        plan = create_plan(obj)
        expl = explain_plan(plan)
        assert expl.safety_assessment != ""


# ── D. Planner Integration Tests ──────────────────────────────────


class TestPlannerIntegration:
    def test_create_from_raw_returns_plan(self):
        _reset()
        plan = create_plan_from_raw("check system health")
        assert plan is not None
        assert plan.status == PlanStatus.VALIDATED

    def test_create_from_raw_has_quality(self):
        _reset()
        plan = create_plan_from_raw("check system health")
        assert plan.quality_score is not None
        assert "verdict" in plan.quality_score
        assert "score" in plan.quality_score

    def test_create_from_raw_has_explanation(self):
        _reset()
        plan = create_plan_from_raw("check system health")
        assert plan.explanation is not None
        assert "objective_summary" in plan.explanation

    def test_template_still_selected_before_llm(self):
        _reset()
        plan = create_plan_from_raw("check system health")
        assert plan.source == PlanSource.TEMPLATE

    def test_structured_objective_still_works(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "test"})
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED
        assert plan.quality_score is not None

    def test_invalid_plan_has_quality_fail(self):
        _reset()
        obj = PlanObjective(title="nonexistent_template")
        plan = create_plan(obj)
        assert plan.status == PlanStatus.REJECTED
        assert plan.quality_score is not None
        assert plan.quality_score["verdict"] == QualityVerdict.FAIL

    def test_low_quality_plan_cannot_execute(self):
        _reset()
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="bad",
                    operation="browser_navigate",
                    execution_class="side_effect",
                ),
            ],
            source=PlanSource.MANUAL,
            status=PlanStatus.VALIDATED,
        )
        quality = score_plan(plan)
        plan.quality_score = quality.to_dict()
        assert quality.verdict == QualityVerdict.FAIL
        try:
            execute_plan(plan)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "fail" in str(e).lower()

    def test_warn_quality_allows_execution(self):
        _reset()
        obj = PlanObjective(
            title="summarize_text",
            context={"text": "hi"},
        )
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED
        plan.quality_score["verdict"] = "warn"
        result = execute_plan(plan)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED

    def test_plan_to_dict_includes_quality(self):
        _reset()
        plan = create_plan_from_raw("check system health")
        d = plan.to_dict()
        assert "quality" in d
        assert "explanation" in d


# ── E. API Tests ──────────────────────────────────────────────────


class TestPlanAPI6B:
    def test_post_plans_with_raw_input(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"raw_input": "check system health"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "validated"
        assert "quality" in data

    def test_post_plans_with_structured_objective(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"title": "summarize_text", "context": {"text": "hi"}},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "quality" in resp.json()

    def test_post_plans_empty_rejected(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"title": "", "raw_input": ""},
            headers=headers,
        )
        assert resp.status_code == 400

    def test_get_plans_includes_quality_verdict(self):
        _reset()
        _, _, headers = _create_identity()
        client.post(
            "/plans",
            json={"raw_input": "check system health"},
            headers=headers,
        )
        resp = client.get("/plans", headers=headers)
        assert resp.status_code == 200
        plans = resp.json()
        assert len(plans) >= 1
        assert "quality_verdict" in plans[0]
        assert "quality_score_value" in plans[0]

    def test_execute_pass_plan_works(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"title": "summarize_text", "context": {"text": "hi"}},
            headers=headers,
        )
        plan_id = resp.json()["plan_id"]
        exec_resp = client.post(f"/plans/{plan_id}/execute", headers=headers)
        assert exec_resp.status_code == 200

    def test_execute_fail_plan_blocked(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"title": "summarize_text", "context": {"text": "hi"}},
            headers=headers,
        )
        plan_id = resp.json()["plan_id"]

        plan = get_plan(plan_id)
        plan.quality_score = {
            "verdict": "fail",
            "score": 0.1,
            "reasons": ["test"],
            "dimensions": {},
        }

        exec_resp = client.post(f"/plans/{plan_id}/execute", headers=headers)
        assert exec_resp.status_code == 422
        assert "fail" in exec_resp.json()["detail"].lower()

    def test_execute_warn_plan_returns_warning(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"title": "summarize_text", "context": {"text": "hi"}},
            headers=headers,
        )
        plan_id = resp.json()["plan_id"]

        plan = get_plan(plan_id)
        plan.quality_score = {
            "verdict": "warn",
            "score": 0.55,
            "reasons": ["LLM-generated plan"],
            "dimensions": {},
        }

        exec_resp = client.post(f"/plans/{plan_id}/execute", headers=headers)
        assert exec_resp.status_code == 200
        assert "quality_warnings" in exec_resp.json()

    def test_get_plan_includes_quality_and_explanation(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"raw_input": "check system health"},
            headers=headers,
        )
        plan_id = resp.json()["plan_id"]
        detail = client.get(f"/plans/{plan_id}", headers=headers)
        assert detail.status_code == 200
        data = detail.json()
        assert "quality" in data
        assert "explanation" in data

    def test_metrics_include_quality_fields(self):
        _reset()
        _, _, headers = _create_identity()
        client.post(
            "/plans",
            json={"raw_input": "check system health"},
            headers=headers,
        )
        resp = client.get("/metrics", headers=headers)
        assert resp.status_code == 200
        plans_metrics = resp.json()["plans"]
        assert "plans_by_quality_verdict" in plans_metrics
        assert "avg_plan_quality" in plans_metrics
        assert "quality_failures" in plans_metrics

    def test_raw_input_vague_still_returns(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            json={"raw_input": "do something"},
            headers=headers,
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["status"] == "rejected"


# ── F. Events Tests ───────────────────────────────────────────────


class TestPhase6BEvents:
    def test_objective_reconstructed_event(self):
        _reset()
        stream = get_event_stream()
        create_plan_from_raw("check system health")
        events = stream.list_events()
        types = [e.type for e in events]
        assert "objective.reconstructed" in types

    def test_quality_scored_event(self):
        _reset()
        stream = get_event_stream()
        create_plan_from_raw("check system health")
        events = stream.list_events()
        types = [e.type for e in events]
        assert "plan.quality_scored" in types

    def test_execution_blocked_quality_event(self):
        _reset()
        stream = get_event_stream()
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="bad",
                    operation="browser_navigate",
                    execution_class="side_effect",
                ),
            ],
            source=PlanSource.MANUAL,
            status=PlanStatus.VALIDATED,
            quality_score={"verdict": "fail", "score": 0.0, "reasons": [], "dimensions": {}},
        )
        try:
            execute_plan(plan)
        except ValueError:
            pass
        events = stream.list_events()
        types = [e.type for e in events]
        assert "plan.execution_blocked_quality" in types


# ── G. Regression Tests ───────────────────────────────────────────


class TestPhase6BRegression:
    def test_phase6a_template_still_works(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "hi"})
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED
        assert plan.source == PlanSource.TEMPLATE

    def test_phase5g_pause_still_works(self):
        _reset()
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="click",
                    operation="computer_click",
                    inputs={"x": 10, "y": 20},
                    execution_class="side_effect",
                ),
            ],
            source=PlanSource.MANUAL,
            status=PlanStatus.VALIDATED,
        )
        result = execute_plan(plan)
        assert result is not None
        assert result.status == TaskStatus.PAUSED

    def test_no_subprocess_in_planning(self):
        import subprocess

        result = subprocess.run(
            ["grep", "-rn", "subprocess.run\\|call_with_fallback\\|get_adapter", "umh/planning/"],
            capture_output=True,
            text=True,
            cwd="/opt/OS",
        )
        assert result.stdout.strip() == "", f"Found forbidden calls: {result.stdout}"

    def test_existing_plan_creation_unchanged(self):
        _reset()
        obj = PlanObjective(title="inspect_file", context={"path": "/tmp/x"})
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED
        assert plan.steps[0].operation == "file_read"
