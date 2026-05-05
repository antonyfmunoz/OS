"""Phase 8B — Strategy model tests."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from umh.strategy.models import (
    ApproachType,
    StepComplexity,
    StepStatus,
    StepType,
    Strategy,
    StrategyStep,
)


class TestStrategyStep:
    def test_default_values(self):
        step = StrategyStep(description="test step")
        assert step.id.startswith("step_")
        assert step.type == StepType.EXECUTION
        assert step.estimated_complexity == StepComplexity.MEDIUM
        assert step.generates_tasks is True
        assert step.status == StepStatus.PENDING
        assert step.dependencies == []
        assert step.task_ids == []

    def test_custom_values(self):
        step = StrategyStep(
            description="research",
            type=StepType.RESEARCH,
            estimated_complexity=StepComplexity.LOW,
            generates_tasks=False,
        )
        assert step.type == StepType.RESEARCH
        assert step.estimated_complexity == StepComplexity.LOW
        assert step.generates_tasks is False

    def test_to_dict(self):
        step = StrategyStep(description="test", id="step_abc")
        d = step.to_dict()
        assert d["id"] == "step_abc"
        assert d["description"] == "test"
        assert d["type"] == "execution"
        assert d["status"] == "pending"
        assert d["generates_tasks"] is True

    def test_unique_ids(self):
        s1 = StrategyStep(description="a")
        s2 = StrategyStep(description="b")
        assert s1.id != s2.id

    def test_dependencies_list(self):
        step = StrategyStep(description="test", dependencies=["step_1", "step_2"])
        assert len(step.dependencies) == 2


class TestStrategy:
    def test_default_values(self):
        s = Strategy(goal_id="goal_abc", objective="test objective")
        assert s.id.startswith("strat_")
        assert s.approach_type == ApproachType.LINEAR
        assert s.confidence == 1.0
        assert s.steps == []
        assert s.created_at != ""
        assert s.updated_at != ""

    def test_to_dict(self):
        s = Strategy(goal_id="goal_abc", objective="build a system", id="strat_test")
        d = s.to_dict()
        assert d["id"] == "strat_test"
        assert d["goal_id"] == "goal_abc"
        assert d["objective"] == "build a system"
        assert d["approach_type"] == "linear"
        assert isinstance(d["steps"], list)

    def test_pending_steps(self):
        steps = [
            StrategyStep(description="a", status=StepStatus.PENDING, generates_tasks=True),
            StrategyStep(description="b", status=StepStatus.COMPLETED, generates_tasks=True),
            StrategyStep(description="c", status=StepStatus.PENDING, generates_tasks=False),
            StrategyStep(description="d", status=StepStatus.PENDING, generates_tasks=True),
        ]
        s = Strategy(goal_id="g", objective="o", steps=steps)
        pending = s.pending_steps()
        assert len(pending) == 2
        assert pending[0].description == "a"
        assert pending[1].description == "d"

    def test_ready_steps_no_deps(self):
        steps = [
            StrategyStep(description="a", id="s1", generates_tasks=True),
            StrategyStep(description="b", id="s2", generates_tasks=True),
        ]
        s = Strategy(goal_id="g", objective="o", steps=steps)
        ready = s.ready_steps()
        assert len(ready) == 2

    def test_ready_steps_with_deps(self):
        steps = [
            StrategyStep(description="a", id="s1", status=StepStatus.COMPLETED),
            StrategyStep(description="b", id="s2", dependencies=["s1"], generates_tasks=True),
            StrategyStep(description="c", id="s3", dependencies=["s2"], generates_tasks=True),
        ]
        s = Strategy(goal_id="g", objective="o", steps=steps)
        ready = s.ready_steps()
        assert len(ready) == 1
        assert ready[0].id == "s2"

    def test_ready_steps_unsatisfied_deps(self):
        steps = [
            StrategyStep(description="a", id="s1", dependencies=["s2"], generates_tasks=True),
            StrategyStep(description="b", id="s2", dependencies=["s1"], generates_tasks=True),
        ]
        s = Strategy(goal_id="g", objective="o", steps=steps)
        ready = s.ready_steps()
        assert len(ready) == 0

    def test_progress_empty(self):
        s = Strategy(goal_id="g", objective="o")
        assert s.progress() == 0.0

    def test_progress_partial(self):
        steps = [
            StrategyStep(description="a", status=StepStatus.COMPLETED),
            StrategyStep(description="b", status=StepStatus.PENDING),
            StrategyStep(description="c", status=StepStatus.PENDING),
        ]
        s = Strategy(goal_id="g", objective="o", steps=steps)
        assert abs(s.progress() - 1 / 3) < 0.01

    def test_progress_complete(self):
        steps = [
            StrategyStep(description="a", status=StepStatus.COMPLETED),
            StrategyStep(description="b", status=StepStatus.SKIPPED),
        ]
        s = Strategy(goal_id="g", objective="o", steps=steps)
        assert s.progress() == 1.0

    def test_mark_step_completed(self):
        step = StrategyStep(description="a", id="s1")
        s = Strategy(goal_id="g", objective="o", steps=[step])
        assert s.mark_step_completed("s1") is True
        assert step.status == StepStatus.COMPLETED

    def test_mark_step_completed_not_found(self):
        s = Strategy(goal_id="g", objective="o", steps=[])
        assert s.mark_step_completed("s999") is False

    def test_mark_step_failed(self):
        step = StrategyStep(description="a", id="s1")
        s = Strategy(goal_id="g", objective="o", steps=[step])
        assert s.mark_step_failed("s1") is True
        assert step.status == StepStatus.FAILED

    def test_add_task_to_step(self):
        step = StrategyStep(description="a", id="s1")
        s = Strategy(goal_id="g", objective="o", steps=[step])
        assert s.add_task_to_step("s1", "task_123") is True
        assert "task_123" in step.task_ids
        assert step.status == StepStatus.IN_PROGRESS

    def test_add_task_to_step_not_found(self):
        s = Strategy(goal_id="g", objective="o", steps=[])
        assert s.add_task_to_step("s999", "task_123") is False


class TestEnums:
    def test_approach_types(self):
        assert ApproachType.LINEAR.value == "linear"
        assert ApproachType.PARALLEL.value == "parallel"
        assert ApproachType.PHASED.value == "phased"

    def test_step_types(self):
        assert StepType.RESEARCH.value == "research"
        assert StepType.EXECUTION.value == "execution"
        assert StepType.VALIDATION.value == "validation"
        assert StepType.DECISION.value == "decision"

    def test_step_complexities(self):
        assert StepComplexity.LOW.value == "low"
        assert StepComplexity.MEDIUM.value == "medium"
        assert StepComplexity.HIGH.value == "high"

    def test_step_statuses(self):
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.IN_PROGRESS.value == "in_progress"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.SKIPPED.value == "skipped"
        assert StepStatus.FAILED.value == "failed"
