"""Operational Workflow Registry v1.

Registry of all canonical operational workflows.
11 registered workflow types, 6 with real step implementations:

  1. Operational Repository Briefing (REAL)
  2. Operational Resume (REAL)
  3. Governed Runtime Inspection (REAL)
  4. Governed Planning (REAL)
  5. Governed Browser Inspection (REAL)
  6. Governed Workstation Inspection (REAL)
  7. Governed Analysis (STUB)
  8-11. Reserved (STUB)

Each real workflow defines concrete steps that execute
exclusively through the canonical spine.

UMH substrate subsystem. Phase 96.8BS.
"""

from __future__ import annotations

from typing import Any

from core.workflows.operational_workflow_contracts_v1 import (
    OperationalWorkflow,
    SupervisedOperationalMode,
    WorkflowBoundary,
    WorkflowStep,
    WorkflowStepType,
    WorkflowType,
    _new_id,
)
from core.workflows.workflow_boundary_policies_v1 import (
    WorkflowBoundaryEnforcer,
)


class OperationalWorkflowRegistry:
    """Registry of canonical operational workflows.

    Provides factory methods for each workflow type.
    All workflows are bounded, governed, and execute
    through the canonical spine.
    """

    def __init__(
        self,
        boundary_enforcer: WorkflowBoundaryEnforcer | None = None,
    ) -> None:
        self._enforcer = boundary_enforcer or WorkflowBoundaryEnforcer()
        self._registry: dict[str, dict[str, Any]] = {}
        self._register_all()

    def _register_all(self) -> None:
        """Register all known workflow types."""
        self._registry = {
            "operational_briefing": {
                "type": WorkflowType.OPERATIONAL_BRIEFING,
                "name": "Operational Repository Briefing",
                "description": "Inspect repo, runtime, continuity, open loops, embodiment, generate briefing",
                "mode": SupervisedOperationalMode.INSPECT_ONLY,
                "factory": self._build_operational_briefing,
                "implemented": True,
            },
            "operational_resume": {
                "type": WorkflowType.OPERATIONAL_RESUME,
                "name": "Operational Resume",
                "description": "Restore continuity, context, open loops, active workflows, generate next actions",
                "mode": SupervisedOperationalMode.INSPECT_ONLY,
                "factory": self._build_operational_resume,
                "implemented": True,
            },
            "runtime_inspection": {
                "type": WorkflowType.RUNTIME_INSPECTION,
                "name": "Governed Runtime Inspection",
                "description": "Inspect spine, orchestration, governance, observability, continuity",
                "mode": SupervisedOperationalMode.INSPECT_ONLY,
                "factory": self._build_runtime_inspection,
                "implemented": True,
            },
            "governed_planning": {
                "type": WorkflowType.GOVERNED_PLANNING,
                "name": "Governed Planning Workflow",
                "description": "Receive objective, expand domains, retrieve continuity/memory, generate plan",
                "mode": SupervisedOperationalMode.GOVERNED_ANALYSIS,
                "factory": self._build_governed_planning,
                "implemented": True,
            },
            "browser_inspection": {
                "type": WorkflowType.BROWSER_INSPECTION,
                "name": "Governed Browser Inspection",
                "description": "Inspect browser, tabs, navigation lineage, summary, no external mutation",
                "mode": SupervisedOperationalMode.INSPECT_ONLY,
                "factory": self._build_browser_inspection,
                "implemented": True,
            },
            "workstation_inspection": {
                "type": WorkflowType.WORKSTATION_INSPECTION,
                "name": "Governed Workstation Inspection",
                "description": "Inspect tmux, shell, modes, execution history, continuity",
                "mode": SupervisedOperationalMode.INSPECT_ONLY,
                "factory": self._build_workstation_inspection,
                "implemented": True,
            },
            "governed_analysis": {
                "type": WorkflowType.GOVERNED_ANALYSIS,
                "name": "Governed Analysis",
                "description": "General governed analysis workflow",
                "mode": SupervisedOperationalMode.GOVERNED_ANALYSIS,
                "factory": self._build_governed_analysis_stub,
                "implemented": False,
            },
        }

    def create_workflow(
        self,
        workflow_type: str,
        session_id: str = "",
        initiated_by: str = "",
        mode_override: SupervisedOperationalMode | None = None,
    ) -> OperationalWorkflow | None:
        """Create a workflow instance from the registry."""
        entry = self._registry.get(workflow_type)
        if not entry:
            return None

        mode = mode_override or entry["mode"]
        factory = entry["factory"]

        workflow = factory(session_id=session_id, initiated_by=initiated_by, mode=mode)
        return workflow

    def list_workflows(self) -> list[dict[str, Any]]:
        """List all registered workflows."""
        return [
            {
                "type": entry["type"].value,
                "name": entry["name"],
                "description": entry["description"],
                "mode": entry["mode"].value,
                "implemented": entry["implemented"],
            }
            for entry in self._registry.values()
        ]

    def list_implemented(self) -> list[dict[str, Any]]:
        """List only implemented workflows."""
        return [w for w in self.list_workflows() if w["implemented"]]

    def get_workflow_info(self, workflow_type: str) -> dict[str, Any] | None:
        """Get info about a specific workflow type."""
        entry = self._registry.get(workflow_type)
        if not entry:
            return None
        return {
            "type": entry["type"].value,
            "name": entry["name"],
            "description": entry["description"],
            "mode": entry["mode"].value,
            "implemented": entry["implemented"],
        }

    # ------------------------------------------------------------------
    # Real workflow factories
    # ------------------------------------------------------------------

    def _build_operational_briefing(
        self,
        session_id: str = "",
        initiated_by: str = "",
        mode: SupervisedOperationalMode = SupervisedOperationalMode.INSPECT_ONLY,
    ) -> OperationalWorkflow:
        """Operational Repository Briefing workflow.

        Steps: runtime-status -> runtime-context -> runtime-open-loops ->
               context retrieval -> aggregation -> report generation
        """
        boundary = self._enforcer.create_boundary(mode)

        steps = [
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-status",
                description="Inspect current runtime spine status",
                target_domain="runtime",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-context",
                description="Retrieve current runtime context and lifecycle",
                target_domain="runtime",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.CONTINUITY_CHECK,
                command="check-open-loops",
                description="Check for open loops and unresolved items",
                target_domain="continuity",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.CONTEXT_RETRIEVAL,
                command="retrieve-context",
                description="Retrieve accumulated operational context",
                target_domain="internal",
                governance_required=False,
            ),
            WorkflowStep(
                step_type=WorkflowStepType.AGGREGATION,
                command="aggregate-briefing",
                description="Aggregate all collected data",
                target_domain="internal",
                governance_required=False,
            ),
            WorkflowStep(
                step_type=WorkflowStepType.REPORT_GENERATION,
                command="generate-briefing",
                description="Generate operational briefing report",
                target_domain="internal",
                governance_required=False,
                checkpoint_after=True,
            ),
        ]

        return OperationalWorkflow(
            workflow_type=WorkflowType.OPERATIONAL_BRIEFING,
            name="Operational Repository Briefing",
            description="Full operational briefing: runtime, context, continuity, report",
            steps=steps,
            boundary=boundary,
            operational_mode=mode,
            session_id=session_id,
            initiated_by=initiated_by,
        )

    def _build_operational_resume(
        self,
        session_id: str = "",
        initiated_by: str = "",
        mode: SupervisedOperationalMode = SupervisedOperationalMode.INSPECT_ONLY,
    ) -> OperationalWorkflow:
        """Operational Resume workflow.

        Steps: runtime-resume -> runtime-open-loops -> runtime-context ->
               context retrieval -> report generation
        """
        boundary = self._enforcer.create_boundary(mode)

        steps = [
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-resume",
                description="Generate runtime resume packet",
                target_domain="runtime",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.CONTINUITY_CHECK,
                command="check-continuity",
                description="Check open loops and continuity state",
                target_domain="continuity",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-context",
                description="Retrieve current runtime context",
                target_domain="runtime",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.CONTEXT_RETRIEVAL,
                command="retrieve-context",
                description="Retrieve accumulated context for resume",
                target_domain="internal",
                governance_required=False,
            ),
            WorkflowStep(
                step_type=WorkflowStepType.REPORT_GENERATION,
                command="generate-resume-report",
                description="Generate operational resume report with next actions",
                target_domain="internal",
                governance_required=False,
            ),
        ]

        return OperationalWorkflow(
            workflow_type=WorkflowType.OPERATIONAL_RESUME,
            name="Operational Resume",
            description="Restore continuity, context, and generate next actions",
            steps=steps,
            boundary=boundary,
            operational_mode=mode,
            session_id=session_id,
            initiated_by=initiated_by,
        )

    def _build_runtime_inspection(
        self,
        session_id: str = "",
        initiated_by: str = "",
        mode: SupervisedOperationalMode = SupervisedOperationalMode.INSPECT_ONLY,
    ) -> OperationalWorkflow:
        """Governed Runtime Inspection workflow.

        Steps: runtime-status -> runtime-governance -> runtime-observe ->
               aggregation -> report generation
        """
        boundary = self._enforcer.create_boundary(mode)

        steps = [
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-status",
                description="Inspect runtime spine status",
                target_domain="runtime",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-governance",
                description="Inspect recent governance decisions",
                target_domain="runtime",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-observe",
                description="Inspect recent observability traces",
                target_domain="runtime",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.AGGREGATION,
                command="aggregate-inspection",
                description="Aggregate inspection results",
                target_domain="internal",
                governance_required=False,
            ),
            WorkflowStep(
                step_type=WorkflowStepType.REPORT_GENERATION,
                command="generate-inspection-report",
                description="Generate runtime inspection report",
                target_domain="internal",
                governance_required=False,
            ),
        ]

        return OperationalWorkflow(
            workflow_type=WorkflowType.RUNTIME_INSPECTION,
            name="Governed Runtime Inspection",
            description="Inspect spine, governance, and observability",
            steps=steps,
            boundary=boundary,
            operational_mode=mode,
            session_id=session_id,
            initiated_by=initiated_by,
        )

    def _build_governed_planning(
        self,
        session_id: str = "",
        initiated_by: str = "",
        mode: SupervisedOperationalMode = SupervisedOperationalMode.GOVERNED_ANALYSIS,
    ) -> OperationalWorkflow:
        """Governed Planning workflow.

        Steps: runtime-context -> runtime-open-loops -> governance check ->
               continuity check -> aggregation -> report generation
        """
        boundary = self._enforcer.create_boundary(mode)

        steps = [
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-context",
                description="Retrieve current context for planning",
                target_domain="runtime",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.CONTINUITY_CHECK,
                command="check-continuity",
                description="Check open loops relevant to planning",
                target_domain="continuity",
                checkpoint_after=True,
            ),
            WorkflowStep(
                step_type=WorkflowStepType.GOVERNANCE_CHECK,
                command="check-governance",
                description="Check governance state for plan constraints",
                target_domain="governance",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.CONTEXT_RETRIEVAL,
                command="retrieve-planning-context",
                description="Retrieve all accumulated context for plan generation",
                target_domain="internal",
                governance_required=False,
            ),
            WorkflowStep(
                step_type=WorkflowStepType.AGGREGATION,
                command="aggregate-planning-data",
                description="Aggregate all planning inputs",
                target_domain="internal",
                governance_required=False,
            ),
            WorkflowStep(
                step_type=WorkflowStepType.REPORT_GENERATION,
                command="generate-plan",
                description="Generate governed operational plan",
                target_domain="internal",
                governance_required=False,
                checkpoint_after=True,
            ),
        ]

        return OperationalWorkflow(
            workflow_type=WorkflowType.GOVERNED_PLANNING,
            name="Governed Planning Workflow",
            description="Governed multi-step planning with continuity and context",
            steps=steps,
            boundary=boundary,
            operational_mode=mode,
            session_id=session_id,
            initiated_by=initiated_by,
        )

    def _build_browser_inspection(
        self,
        session_id: str = "",
        initiated_by: str = "",
        mode: SupervisedOperationalMode = SupervisedOperationalMode.INSPECT_ONLY,
    ) -> OperationalWorkflow:
        """Governed Browser Inspection workflow.

        Steps: browser-status -> runtime-context -> aggregation -> report
        No external mutation permitted.
        """
        boundary = self._enforcer.create_boundary(mode)

        steps = [
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="browser-status",
                description="Inspect current browser state",
                target_domain="browser",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-context",
                description="Retrieve runtime context for browser correlation",
                target_domain="runtime",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.CONTEXT_RETRIEVAL,
                command="retrieve-browser-context",
                description="Retrieve accumulated browser context",
                target_domain="internal",
                governance_required=False,
            ),
            WorkflowStep(
                step_type=WorkflowStepType.REPORT_GENERATION,
                command="generate-browser-report",
                description="Generate browser inspection report",
                target_domain="internal",
                governance_required=False,
            ),
        ]

        return OperationalWorkflow(
            workflow_type=WorkflowType.BROWSER_INSPECTION,
            name="Governed Browser Inspection",
            description="Inspect browser state, tabs, navigation lineage",
            steps=steps,
            boundary=boundary,
            operational_mode=mode,
            session_id=session_id,
            initiated_by=initiated_by,
        )

    def _build_workstation_inspection(
        self,
        session_id: str = "",
        initiated_by: str = "",
        mode: SupervisedOperationalMode = SupervisedOperationalMode.INSPECT_ONLY,
    ) -> OperationalWorkflow:
        """Governed Workstation Inspection workflow.

        Steps: workstation-status -> runtime-context -> continuity check ->
               aggregation -> report
        """
        boundary = self._enforcer.create_boundary(mode)

        steps = [
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="workstation-status",
                description="Inspect current workstation state",
                target_domain="workstation",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-context",
                description="Retrieve runtime context for workstation correlation",
                target_domain="runtime",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.CONTINUITY_CHECK,
                command="check-workstation-continuity",
                description="Check workstation continuity and open loops",
                target_domain="continuity",
            ),
            WorkflowStep(
                step_type=WorkflowStepType.AGGREGATION,
                command="aggregate-workstation-data",
                description="Aggregate workstation inspection data",
                target_domain="internal",
                governance_required=False,
            ),
            WorkflowStep(
                step_type=WorkflowStepType.REPORT_GENERATION,
                command="generate-workstation-report",
                description="Generate workstation inspection report",
                target_domain="internal",
                governance_required=False,
            ),
        ]

        return OperationalWorkflow(
            workflow_type=WorkflowType.WORKSTATION_INSPECTION,
            name="Governed Workstation Inspection",
            description="Inspect tmux, shell, modes, execution history, continuity",
            steps=steps,
            boundary=boundary,
            operational_mode=mode,
            session_id=session_id,
            initiated_by=initiated_by,
        )

    # ------------------------------------------------------------------
    # Stub workflows (registered but not implemented)
    # ------------------------------------------------------------------

    def _build_governed_analysis_stub(
        self,
        session_id: str = "",
        initiated_by: str = "",
        mode: SupervisedOperationalMode = SupervisedOperationalMode.GOVERNED_ANALYSIS,
    ) -> OperationalWorkflow:
        """Stub for governed analysis workflow."""
        boundary = self._enforcer.create_boundary(mode)

        steps = [
            WorkflowStep(
                step_type=WorkflowStepType.SPINE_TRAVERSAL,
                command="runtime-status",
                description="Placeholder: inspect runtime",
                target_domain="runtime",
            ),
        ]

        return OperationalWorkflow(
            workflow_type=WorkflowType.GOVERNED_ANALYSIS,
            name="Governed Analysis (stub)",
            description="Stub workflow for governed analysis",
            steps=steps,
            boundary=boundary,
            operational_mode=mode,
            session_id=session_id,
            initiated_by=initiated_by,
        )

    def get_stats(self) -> dict[str, Any]:
        total = len(self._registry)
        implemented = sum(1 for e in self._registry.values() if e["implemented"])
        return {
            "total_registered": total,
            "implemented": implemented,
            "stub": total - implemented,
            "workflow_types": list(self._registry.keys()),
        }
