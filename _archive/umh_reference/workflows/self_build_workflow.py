"""North Star self-build workflow — UMH/EOS self-build operating loop.

Encodes the 11-stage self-build loop for operator-assisted UMH development.
No autonomous infinite loop. No governance bypass.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from umh.workflows.contracts import (
    KPIName,
    SelfBuildStage,
    WorkflowDefinition,
    WorkflowStage,
    WorkflowStageDefinition,
    WorkflowTask,
    WorkflowTrack,
    _wf_id,
)


def build_umh_self_build_workflow() -> WorkflowDefinition:
    stages = _build_self_build_stages()
    kpis = [
        KPIName.FILES_CHANGED.value,
        KPIName.TESTS_ADDED.value,
        KPIName.TESTS_PASSED.value,
        KPIName.REGRESSION_STATUS.value,
        KPIName.SAFETY_VIOLATIONS.value,
        KPIName.PHASE_COMPLETION.value,
        KPIName.ARCHITECTURE_DRIFT_FOUND.value,
        KPIName.TEMPLATE_CANDIDATES_FOUND.value,
        KPIName.MANUAL_HOURS_SPENT.value,
        KPIName.BOTTLENECKS_FOUND.value,
    ]
    return WorkflowDefinition(
        workflow_id=_wf_id("wkfl"),
        track=WorkflowTrack.SELF_BUILD,
        name="UMH Self-Build Operating Loop",
        purpose=(
            "Systematically improve UMH/EOS through operator-assisted build cycles. "
            "Each cycle selects a phase, implements scoped changes, validates safety, "
            "detects drift, and recommends next steps. No autonomous code execution."
        ),
        stages=stages,
        primary_company="ost",
        product="umh_eos",
        owner="antony",
        success_criteria=[
            "One scoped phase completed per build cycle",
            "All tests pass after each change",
            "No safety violations introduced",
            "Architecture drift detected and documented",
            "Template candidates identified for operationalization",
            "Phase report written",
        ],
        kpis=kpis,
        metadata={
            "version": "v1",
            "source": "phase88_north_star",
            "entities_touched": ["ost", "umh", "eos"],
        },
    )


def _build_self_build_stages() -> list[WorkflowStageDefinition]:
    return [
        WorkflowStageDefinition(
            stage=WorkflowStage.CONTEXT_LOAD,
            name="Phase Selection",
            objective="Select the next build target from roadmap or backlog",
            expected_output="Selected phase with rationale",
            kpi=KPIName.PHASE_COMPLETION.value,
            common_bottlenecks=[
                "Too many candidate phases",
                "Unclear priority ordering",
                "Scope creep in phase definition",
            ],
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.CONTEXT_LOAD,
            name="Doc Context Load",
            objective="Read required context docs for selected phase",
            expected_output="Context loaded and understood",
            kpi=KPIName.PHASE_COMPLETION.value,
            common_bottlenecks=[
                "Missing docs",
                "Stale docs",
                "Docs contradict each other",
            ],
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.STRATEGY_REVIEW,
            name="Architecture Review",
            objective="Review current architecture for selected phase",
            expected_output="Architecture assessment and change plan",
            kpi=KPIName.ARCHITECTURE_DRIFT_FOUND.value,
            common_bottlenecks=[
                "Architecture unclear",
                "Multiple approaches possible",
                "Drift already present",
            ],
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.PLAN_GENERATION,
            name="Implementation Plan",
            objective="Generate a scoped implementation plan",
            expected_output="Implementation plan with files and tests",
            kpi=KPIName.PHASE_COMPLETION.value,
            common_bottlenecks=[
                "Plan too large",
                "Unclear acceptance criteria",
                "Dependencies not identified",
            ],
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.MANUAL_EXECUTION,
            name="Code Change",
            objective="Implement the scoped change",
            expected_output="Code changes committed",
            kpi=KPIName.FILES_CHANGED.value,
            common_bottlenecks=[
                "Scope creep during implementation",
                "Unexpected dependencies",
                "Breaking existing tests",
            ],
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.MANUAL_EXECUTION,
            name="Testing",
            objective="Run tests and validate changes",
            expected_output="All tests passing",
            kpi=KPIName.TESTS_PASSED.value,
            common_bottlenecks=[
                "Test failures unrelated to change",
                "Missing test coverage",
                "Flaky tests",
            ],
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.MANUAL_EXECUTION,
            name="Safety Validation",
            objective="Run safety checks on changed modules",
            expected_output="Safety scan clean",
            kpi=KPIName.SAFETY_VIOLATIONS.value,
            common_bottlenecks=[
                "Forbidden imports introduced",
                "Execution patterns in advisory code",
                "Governance boundary violation",
            ],
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.REVIEW,
            name="Reporting",
            objective="Write phase completion report",
            expected_output="Phase report document",
            kpi=KPIName.PHASE_COMPLETION.value,
            common_bottlenecks=[
                "Report not written",
                "Report missing test results",
                "Report missing safety status",
            ],
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.REVIEW,
            name="Roadmap Update",
            objective="Update roadmap with phase completion status",
            expected_output="Roadmap updated",
            kpi=KPIName.PHASE_COMPLETION.value,
            common_bottlenecks=[
                "Roadmap stale",
                "Phase not reflected in roadmap",
            ],
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.REVIEW,
            name="Drift Detection",
            objective="Detect architecture or doctrine drift from changes",
            expected_output="Drift assessment",
            kpi=KPIName.ARCHITECTURE_DRIFT_FOUND.value,
            common_bottlenecks=[
                "No baseline to compare against",
                "Drift introduced intentionally but undocumented",
            ],
        ),
        WorkflowStageDefinition(
            stage=WorkflowStage.NEXT_DAY_RECOMMENDATION,
            name="Next Phase Recommendation",
            objective="Recommend next build action based on results",
            expected_output="Next phase recommendation with rationale",
            kpi=KPIName.PHASE_COMPLETION.value,
            common_bottlenecks=[
                "Unclear priority after completion",
                "Multiple viable next phases",
            ],
        ),
    ]


def generate_self_build_test_tasks(
    context: dict[str, Any] | None = None,
) -> list[WorkflowTask]:
    return [
        WorkflowTask(
            task_id=_wf_id("sbtask"),
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.CONTEXT_LOAD,
            title="Select next build target",
            description="Review roadmap and backlog. Pick the highest-leverage next phase.",
            priority="high",
            estimated_minutes=15,
            leverage_type="knowledge",
            owner="antony",
            manual_only=True,
            expected_output="Selected phase name and rationale",
        ),
        WorkflowTask(
            task_id=_wf_id("sbtask"),
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.CONTEXT_LOAD,
            title="Read required context docs",
            description="Load strategy docs, phase reports, and architecture docs for the selected phase.",
            priority="high",
            estimated_minutes=20,
            leverage_type="knowledge",
            owner="antony",
            manual_only=True,
            expected_output="Context loaded",
        ),
        WorkflowTask(
            task_id=_wf_id("sbtask"),
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.STRATEGY_REVIEW,
            title="Identify smallest useful next build",
            description="Scope the build to the minimum viable change that advances the phase.",
            priority="high",
            estimated_minutes=15,
            leverage_type="knowledge",
            owner="antony",
            manual_only=True,
            expected_output="Scoped build description",
        ),
        WorkflowTask(
            task_id=_wf_id("sbtask"),
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.PLAN_GENERATION,
            title="Generate build plan",
            description="Create implementation plan with files, tests, and acceptance criteria.",
            priority="high",
            estimated_minutes=20,
            leverage_type="systems_process",
            owner="antony",
            manual_only=True,
            expected_output="Implementation plan document",
        ),
        WorkflowTask(
            task_id=_wf_id("sbtask"),
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.MANUAL_EXECUTION,
            title="Implement only scoped change",
            description="Write code. Do not scope-creep. Stay within the plan.",
            priority="high",
            estimated_minutes=60,
            leverage_type="code_software",
            owner="antony",
            manual_only=True,
            expected_output="Code changes committed",
        ),
        WorkflowTask(
            task_id=_wf_id("sbtask"),
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.MANUAL_EXECUTION,
            title="Run tests",
            description="Run pytest for the phase test file and regression tests.",
            priority="high",
            estimated_minutes=10,
            leverage_type="systems_process",
            owner="antony",
            manual_only=True,
            expected_output="Test results recorded",
        ),
        WorkflowTask(
            task_id=_wf_id("sbtask"),
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.MANUAL_EXECUTION,
            title="Run safety checks",
            description="Run workflow safety scan on changed modules.",
            priority="high",
            estimated_minutes=5,
            leverage_type="systems_process",
            owner="antony",
            manual_only=True,
            expected_output="Safety scan results",
        ),
        WorkflowTask(
            task_id=_wf_id("sbtask"),
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.REVIEW,
            title="Write phase report",
            description="Document what was built, tested, and learned.",
            priority="high",
            estimated_minutes=15,
            leverage_type="knowledge",
            owner="antony",
            manual_only=True,
            expected_output="Phase report written",
        ),
        WorkflowTask(
            task_id=_wf_id("sbtask"),
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.REVIEW,
            title="Detect roadmap/doctrine drift",
            description="Compare build results to roadmap and doctrine. Flag any divergence.",
            priority="medium",
            estimated_minutes=10,
            leverage_type="knowledge",
            owner="antony",
            manual_only=True,
            expected_output="Drift assessment",
        ),
        WorkflowTask(
            task_id=_wf_id("sbtask"),
            track=WorkflowTrack.SELF_BUILD,
            stage=WorkflowStage.NEXT_DAY_RECOMMENDATION,
            title="Recommend next build action",
            description="Based on results, recommend the next phase or improvement.",
            priority="medium",
            estimated_minutes=10,
            leverage_type="knowledge",
            owner="antony",
            manual_only=True,
            expected_output="Next build recommendation",
        ),
    ]
