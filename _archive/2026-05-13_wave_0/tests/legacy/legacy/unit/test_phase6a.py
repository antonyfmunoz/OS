"""Tests for Phase 6A: Deterministic Planning Layer v1.

Verifies:
- PlanObjective, ExecutionPlanStep, ExecutionPlan models
- Template-based plan generation
- Plan validator (allowlist, shell, deps, classes)
- Plan-to-task conversion
- Plan execution through task system
- Approval-gated steps pause task (Phase 5G integration)
- API endpoints (POST/GET /plans, execute)
- Metrics include plan data
- Events emitted for plan lifecycle
- Regression: no execution bypasses
"""

import sys
import os

sys.path.insert(0, "/opt/OS")

os.environ.setdefault("UMH_API_KEY", "test-key-phase5a")
os.environ["PYTEST_CURRENT_TEST"] = "1"

from fastapi.testclient import TestClient

from umh.control.api import app
from umh.control.identity import get_identity_store
from umh.events.stream import get_event_stream, reset_event_stream
from umh.execution.approval import get_approval_store
from umh.orchestrator.engine import reset_orchestrator, start_orchestrator
from umh.orchestrator.task import (
    TaskStatus,
    StepStatus,
    get_task,
    reset_tasks,
)
from umh.planning.models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanObjective,
    PlanSource,
    PlanStatus,
    PlanValidationResult,
)
from umh.planning.planner import (
    create_plan,
    execute_plan,
    get_plan,
    list_plans,
    plan_to_task,
    reset_plans,
)
from umh.planning.templates import get_template, list_templates
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


# ── A. Model Tests ──────────────────────────────────────────────────


class TestPlanModels:
    def test_plan_objective_creation(self):
        obj = PlanObjective(title="test", description="desc")
        assert obj.objective_id.startswith("obj_")
        assert obj.title == "test"
        assert obj.max_steps == 10

    def test_plan_objective_to_dict(self):
        obj = PlanObjective(title="t", constraints=["no file writes"])
        d = obj.to_dict()
        assert d["title"] == "t"
        assert "no file writes" in d["constraints"]
        assert d["dry_run"] is False

    def test_execution_plan_step_creation(self):
        step = ExecutionPlanStep(name="s1", operation="summarize")
        assert step.step_id.startswith("pstep_")
        assert step.execution_class == "llm_call"
        assert step.inputs == {}

    def test_execution_plan_step_to_dict(self):
        step = ExecutionPlanStep(name="s1", operation="file_read", inputs={"path": "/tmp/x"})
        d = step.to_dict()
        assert d["operation"] == "file_read"
        assert d["inputs"]["path"] == "/tmp/x"

    def test_execution_plan_creation(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(objective=obj)
        assert plan.plan_id.startswith("eplan_")
        assert plan.status == PlanStatus.DRAFT
        assert plan.source == PlanSource.TEMPLATE

    def test_execution_plan_to_dict(self):
        obj = PlanObjective(title="test")
        step = ExecutionPlanStep(name="s1", operation="summarize")
        plan = ExecutionPlan(objective=obj, steps=[step])
        d = plan.to_dict()
        assert d["plan_id"].startswith("eplan_")
        assert d["status"] == "draft"
        assert len(d["steps"]) == 1
        assert d["objective"]["title"] == "test"

    def test_plan_validation_result(self):
        r = PlanValidationResult(valid=True, warnings=["might be slow"])
        d = r.to_dict()
        assert d["valid"] is True
        assert len(d["warnings"]) == 1

    def test_plan_status_enum(self):
        assert PlanStatus.VALIDATED.value == "validated"
        assert PlanStatus.REJECTED.value == "rejected"

    def test_plan_source_enum(self):
        assert PlanSource.TEMPLATE.value == "template"
        assert PlanSource.LLM.value == "llm"
        assert PlanSource.MANUAL.value == "manual"


# ── B. Template Planner Tests ────��──────────────────────────────────


class TestTemplatePlanner:
    def test_templates_registered(self):
        names = list_templates()
        assert "inspect_system_status" in names
        assert "inspect_file" in names
        assert "list_directory" in names
        assert "summarize_text" in names
        assert "shell_health_check" in names
        assert "computer_screenshot_review" in names

    def test_inspect_system_status_creates_shell_steps(self):
        obj = PlanObjective(title="inspect_system_status")
        fn = get_template("inspect_system_status")
        plan = fn(obj)
        assert len(plan.steps) == 4
        for step in plan.steps:
            assert step.operation == "shell_command"
            assert step.execution_class == "side_effect"

    def test_inspect_file_creates_file_read_step(self):
        obj = PlanObjective(title="inspect_file", context={"path": "/opt/OS/README.md"})
        fn = get_template("inspect_file")
        plan = fn(obj)
        assert len(plan.steps) == 1
        assert plan.steps[0].operation == "file_read"
        assert plan.steps[0].inputs["path"] == "/opt/OS/README.md"

    def test_list_directory_creates_file_list_step(self):
        obj = PlanObjective(title="list_directory", context={"path": "/opt/OS/umh"})
        fn = get_template("list_directory")
        plan = fn(obj)
        assert len(plan.steps) == 1
        assert plan.steps[0].operation == "file_list"

    def test_summarize_text_creates_llm_step(self):
        obj = PlanObjective(
            title="summarize_text",
            context={"text": "Hello world, this is a test."},
        )
        fn = get_template("summarize_text")
        plan = fn(obj)
        assert len(plan.steps) == 1
        assert plan.steps[0].operation == "summarize"
        assert plan.steps[0].execution_class == "llm_call"

    def test_max_steps_respected(self):
        obj = PlanObjective(title="inspect_system_status", max_steps=2)
        fn = get_template("inspect_system_status")
        plan = fn(obj)
        assert len(plan.steps) == 2

    def test_template_source_is_template(self):
        obj = PlanObjective(title="inspect_file", context={"path": "/tmp/x"})
        fn = get_template("inspect_file")
        plan = fn(obj)
        assert plan.source == PlanSource.TEMPLATE

    def test_nonexistent_template_returns_none(self):
        fn = get_template("totally_bogus_template")
        assert fn is None


# ── C. Validator Tests ─────────���────────────────────────────────────


class TestPlanValidator:
    def test_valid_plan_passes(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(name="s", operation="summarize"),
            ],
        )
        result = validate_plan(plan)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_empty_plan_fails(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(objective=obj, steps=[])
        result = validate_plan(plan)
        assert result.valid is False
        assert any("no steps" in e.lower() for e in result.errors)

    def test_duplicate_step_ids_fail(self):
        obj = PlanObjective(title="test")
        s1 = ExecutionPlanStep(name="a", operation="summarize", step_id="dup")
        s2 = ExecutionPlanStep(name="b", operation="summarize", step_id="dup")
        plan = ExecutionPlan(objective=obj, steps=[s1, s2])
        result = validate_plan(plan)
        assert result.valid is False
        assert any("duplicate" in e.lower() for e in result.errors)

    def test_unknown_operation_fails(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(name="s", operation="launch_missiles"),
            ],
        )
        result = validate_plan(plan)
        assert result.valid is False
        assert any("unknown operation" in e.lower() for e in result.errors)

    def test_invalid_execution_class_fails(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(name="s", operation="summarize", execution_class="nope"),
            ],
        )
        result = validate_plan(plan)
        assert result.valid is False
        assert any("execution_class" in e.lower() for e in result.errors)

    def test_non_allowlisted_shell_command_fails(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="s",
                    operation="shell_command",
                    inputs={"command": "rm -rf /"},
                    execution_class="side_effect",
                ),
            ],
        )
        result = validate_plan(plan)
        assert result.valid is False
        assert any("allowlist" in e.lower() for e in result.errors)

    def test_allowlisted_shell_command_passes(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="s",
                    operation="shell_command",
                    inputs={"command": "uptime"},
                    execution_class="side_effect",
                ),
            ],
        )
        result = validate_plan(plan)
        assert result.valid is True

    def test_unsupported_browser_op_fails(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(name="s", operation="browser_navigate"),
            ],
        )
        result = validate_plan(plan)
        assert result.valid is False
        assert any("unsupported" in e.lower() for e in result.errors)

    def test_dependency_on_missing_step_fails(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="s",
                    operation="summarize",
                    depends_on=["nonexistent_step"],
                ),
            ],
        )
        result = validate_plan(plan)
        assert result.valid is False
        assert any("depends_on" in e.lower() for e in result.errors)

    def test_approval_gated_op_warns(self):
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
        result = validate_plan(plan)
        assert result.valid is True
        assert any("require approval" in w.lower() for w in result.warnings)

    def test_approval_gated_op_wrong_class_fails(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="click",
                    operation="computer_click",
                    inputs={"x": 10, "y": 20},
                    execution_class="llm_call",
                ),
            ],
        )
        result = validate_plan(plan)
        assert result.valid is False

    def test_max_steps_exceeded_fails(self):
        obj = PlanObjective(title="test", max_steps=2)
        plan = ExecutionPlan(
            objective=obj,
            steps=[ExecutionPlanStep(name=f"s{i}", operation="summarize") for i in range(5)],
        )
        result = validate_plan(plan)
        assert result.valid is False
        assert any("max" in e.lower() for e in result.errors)

    def test_capability_restriction_enforced(self):
        obj = PlanObjective(title="test", allowed_capabilities=["summarize"])
        plan = ExecutionPlan(
            objective=obj,
            steps=[
                ExecutionPlanStep(
                    name="s",
                    operation="shell_command",
                    inputs={"command": "uptime"},
                    execution_class="side_effect",
                ),
            ],
        )
        result = validate_plan(plan)
        assert result.valid is False
        assert any("allowed_capabilities" in e.lower() for e in result.errors)


# ── D. Task Conversion Tests ──────────��─────────────────────────────


class TestPlanToTask:
    def test_valid_plan_converts_to_task(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "hi"})
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED
        task = plan_to_task(plan)
        assert task is not None
        assert len(task.steps) == len(plan.steps)

    def test_step_order_preserved(self):
        _reset()
        obj = PlanObjective(title="inspect_system_status")
        plan = create_plan(obj)
        task = plan_to_task(plan)
        for i, (ps, ts) in enumerate(zip(plan.steps, task.steps)):
            assert ts.operation == ps.operation

    def test_execution_class_preserved(self):
        _reset()
        obj = PlanObjective(title="inspect_system_status")
        plan = create_plan(obj)
        task = plan_to_task(plan)
        for ps, ts in zip(plan.steps, task.steps):
            assert ts.execution_class == ps.execution_class

    def test_non_validated_plan_raises(self):
        obj = PlanObjective(title="test")
        plan = ExecutionPlan(objective=obj, status=PlanStatus.DRAFT)
        try:
            plan_to_task(plan)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_plan_metadata_in_task_context(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "hi"})
        plan = create_plan(obj)
        task = plan_to_task(plan)
        assert task.context["plan_id"] == plan.plan_id
        assert task.context["objective_id"] == obj.objective_id


# ── E. Execution Integration ────────────────────────────────────────


class TestPlanExecution:
    def test_summarize_plan_executes_to_completion(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "testing"})
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED

        result = execute_plan(plan)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED

    def test_plan_task_id_set_after_execution(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "testing"})
        plan = create_plan(obj)
        execute_plan(plan)
        assert plan.task_id != ""
        assert plan.task_id.startswith("task_")

    def test_plan_status_completed_after_execution(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "testing"})
        plan = create_plan(obj)
        execute_plan(plan)
        assert plan.status == PlanStatus.COMPLETED

    def test_approval_gated_plan_pauses_task(self):
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

    def test_approval_gated_plan_resumes_via_5g(self):
        _start_fresh()
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
        assert result.status == TaskStatus.PAUSED

        task = get_task(plan.task_id)
        approval_id = task.paused_approval_id
        get_approval_store().approve(approval_id, approved_by="tester")

        stored = get_task(plan.task_id)
        assert stored.status == TaskStatus.COMPLETED

    def test_rejected_plan_cannot_execute(self):
        _reset()
        obj = PlanObjective(title="nonexistent_template")
        plan = create_plan(obj)
        assert plan.status == PlanStatus.REJECTED

        try:
            execute_plan(plan)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_dry_run_does_not_execute(self):
        _reset()
        obj = PlanObjective(
            title="summarize_text",
            context={"text": "test"},
            dry_run=True,
        )
        plan = create_plan(obj)
        assert plan.status == PlanStatus.VALIDATED

        result = execute_plan(plan)
        assert result is None

    def test_plan_stored_after_create(self):
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "x"})
        plan = create_plan(obj)
        stored = get_plan(plan.plan_id)
        assert stored is not None
        assert stored.plan_id == plan.plan_id

    def test_list_plans_returns_all(self):
        _reset()
        create_plan(PlanObjective(title="summarize_text", context={"text": "a"}))
        create_plan(PlanObjective(title="inspect_file", context={"path": "/tmp/x"}))
        assert len(list_plans()) == 2


# ── F. API Tests ───���────────────────────────────────────────────────


class TestPlanAPI:
    def test_post_plans_valid_template(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            headers=headers,
            json={
                "title": "summarize_text",
                "context": {"text": "hello world"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "validated"
        assert data["plan_id"].startswith("eplan_")
        assert len(data["steps"]) == 1

    def test_post_plans_unknown_template_rejected(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            headers=headers,
            json={"title": "totally_bogus"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["status"] == "rejected"

    def test_post_plans_empty_title_400(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post("/plans", headers=headers, json={"title": ""})
        assert resp.status_code == 400

    def test_post_plans_max_steps_invalid_400(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            headers=headers,
            json={"title": "summarize_text", "max_steps": 0},
        )
        assert resp.status_code == 400

    def test_get_plans(self):
        _reset()
        _, _, headers = _create_identity()
        client.post(
            "/plans",
            headers=headers,
            json={"title": "summarize_text", "context": {"text": "x"}},
        )
        resp = client.get("/plans", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_plan_by_id(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            headers=headers,
            json={"title": "summarize_text", "context": {"text": "x"}},
        )
        plan_id = resp.json()["plan_id"]
        resp2 = client.get(f"/plans/{plan_id}", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["plan_id"] == plan_id

    def test_get_plan_not_found(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.get("/plans/eplan_nonexistent", headers=headers)
        assert resp.status_code == 404

    def test_post_plans_execute(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            headers=headers,
            json={"title": "summarize_text", "context": {"text": "x"}},
        )
        plan_id = resp.json()["plan_id"]
        resp2 = client.post(f"/plans/{plan_id}/execute", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "completed"

    def test_execute_rejected_plan_409(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post("/plans", headers=headers, json={"title": "bogus"})
        plan_id = resp.json()["plan_id"]
        resp2 = client.post(f"/plans/{plan_id}/execute", headers=headers)
        assert resp2.status_code == 409

    def test_validate_endpoint(self):
        _reset()
        _, _, headers = _create_identity()
        resp = client.post(
            "/plans",
            headers=headers,
            json={"title": "summarize_text", "context": {"text": "x"}},
        )
        plan_id = resp.json()["plan_id"]
        resp2 = client.post(f"/plans/{plan_id}/validate", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["valid"] is True

    def test_auth_required(self):
        _reset()
        resp = client.get("/plans")
        assert resp.status_code == 401


# ── G. Metrics Tests ────────────────────────────────────────────────


class TestPlanMetrics:
    def test_metrics_includes_plan_data(self):
        _reset()
        _, _, headers = _create_identity()
        client.post(
            "/plans",
            headers=headers,
            json={"title": "summarize_text", "context": {"text": "x"}},
        )
        resp = client.get("/metrics", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "plans" in data
        assert data["plans"]["total_plans"] >= 1

    def test_metrics_validation_failures(self):
        _reset()
        _, _, headers = _create_identity()
        client.post("/plans", headers=headers, json={"title": "bogus"})
        resp = client.get("/metrics", headers=headers)
        data = resp.json()
        assert data["plans"]["validation_failures"] >= 1


# ── H. Events Tests ─────────────────────────────────────────────────


class TestPlanEvents:
    def test_plan_created_event(self):
        _reset()
        stream = get_event_stream()
        obj = PlanObjective(title="summarize_text", context={"text": "x"})
        create_plan(obj)
        events = stream.list_events(limit=200)
        created = [e for e in events if e.type == "plan.created"]
        assert len(created) >= 1

    def test_plan_validated_event(self):
        _reset()
        stream = get_event_stream()
        obj = PlanObjective(title="summarize_text", context={"text": "x"})
        create_plan(obj)
        events = stream.list_events(limit=200)
        validated = [e for e in events if e.type == "plan.validated"]
        assert len(validated) >= 1

    def test_plan_rejected_event(self):
        _reset()
        stream = get_event_stream()
        obj = PlanObjective(title="nonexistent_template")
        create_plan(obj)
        events = stream.list_events(limit=200)
        rejected = [e for e in events if e.type == "plan.rejected"]
        assert len(rejected) >= 1

    def test_plan_executed_event(self):
        _reset()
        stream = get_event_stream()
        obj = PlanObjective(title="summarize_text", context={"text": "x"})
        plan = create_plan(obj)
        execute_plan(plan)
        events = stream.list_events(limit=200)
        executed = [e for e in events if e.type == "plan.executed"]
        assert len(executed) >= 1


# ── I. Regression Tests ─────────────────────────────────────────────


class TestPlanRegression:
    def test_existing_tasks_still_work(self):
        from umh.orchestrator.task import Task, TaskStep, execute_task

        _reset()
        task = Task(
            steps=[
                TaskStep(
                    operation="classify_intent",
                    inputs_template={
                        "prompt": "hi",
                        "system_prompt": "",
                        "max_tokens": 100,
                    },
                )
            ]
        )
        result = execute_task(task)
        assert result.status == TaskStatus.COMPLETED

    def test_plan_uses_execute_not_bypass(self):
        """Plan execution routes through execute_task, not direct adapter."""
        _reset()
        obj = PlanObjective(title="summarize_text", context={"text": "x"})
        plan = create_plan(obj)
        result = execute_plan(plan)
        assert result.status == TaskStatus.COMPLETED
        stream = get_event_stream()
        events = stream.list_events(limit=200)
        exec_events = [e for e in events if e.type == "execution.started"]
        assert len(exec_events) >= 1

    def test_import_ok(self):
        import umh

        assert umh is not None
