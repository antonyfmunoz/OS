"""Canonical Long-Horizon Execution Coordinator v1.

Coordinates staged execution of operational campaigns.
Composes lifecycle, dependency, deferred, continuation,
chronology, and execution graph engines.

The coordinator:
  - coordinates staged execution
  - manages deferred execution
  - manages operational sequencing
  - manages dependency progression
  - manages bounded continuation
  - manages resumable execution
  - dispatches ONLY through spine.process()

The coordinator CANNOT execute adapters directly.
The operator still owns intentionality.

UMH substrate subsystem. Phase 96.8BW.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.operations.long_horizon_operational_contracts_v1 import (
    ExecutionStage,
    OperationalApprovalState,
    OperationalCampaign,
    OperationalExecutionReceipt,
    OperationalLifecycleState,
    OperationalObjective,
    OperationalProgressState,
    _content_hash,
    _new_id,
    _now_iso,
)
from core.operations.operational_chronology_engine_v1 import (
    OperationalChronologyEngine,
)
from core.operations.operational_continuation_engine_v1 import (
    OperationalContinuationEngine,
)
from core.operations.operational_dependency_engine_v1 import (
    OperationalDependencyEngine,
)
from core.operations.deferred_execution_engine_v1 import DeferredExecutionEngine
from core.operations.operational_execution_graph_engine_v1 import (
    OperationalExecutionGraphEngine,
)
from core.operations.operational_lifecycle_engine_v1 import (
    OperationalLifecycleEngine,
)


class CanonicalLongHorizonExecutionCoordinator:
    """Coordinates long-horizon operational execution.

    Cannot execute adapters directly. Cannot generate objectives.
    Cannot create autonomous campaigns. All execution through
    canonical spine only.
    """

    def __init__(
        self,
        state_dir: str | Path = "data/runtime/operations",
    ) -> None:
        self._state_dir = Path(state_dir)
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._lifecycle = OperationalLifecycleEngine(state_dir=self._state_dir)
        self._dependencies = OperationalDependencyEngine(state_dir=self._state_dir)
        self._deferred = DeferredExecutionEngine(
            state_dir=self._state_dir / "deferred",
        )
        self._continuation = OperationalContinuationEngine(state_dir=self._state_dir)
        self._chronology = OperationalChronologyEngine(
            state_dir=self._state_dir / "lineage",
        )
        self._graph = OperationalExecutionGraphEngine(state_dir=self._state_dir)

        self._objectives: dict[str, OperationalObjective] = {}
        self._campaigns: dict[str, OperationalCampaign] = {}
        self._approvals: dict[str, OperationalApprovalState] = {}
        self._receipts: list[OperationalExecutionReceipt] = []

    def create_objective(
        self,
        operator_id: str,
        description: str,
        success_criteria: list[str] | None = None,
        max_stages: int = 10,
        max_duration_hours: int = 72,
    ) -> OperationalObjective:
        """Create an operator-defined objective. set_by is always 'operator'."""
        obj = OperationalObjective(
            operator_id=operator_id,
            description=description,
            success_criteria=success_criteria or [],
            max_stages=max_stages,
            max_duration_hours=max_duration_hours,
            set_by="operator",
        )
        self._objectives[obj.objective_id] = obj
        return obj

    def create_campaign(
        self,
        objective_id: str,
        operator_id: str,
        session_id: str = "",
        stages: list[dict[str, Any]] | None = None,
        max_fanout: int = 3,
    ) -> OperationalCampaign | None:
        """Create a bounded campaign from an objective."""
        obj = self._objectives.get(objective_id)
        if not obj:
            return None

        stage_objs: list[ExecutionStage] = []
        for i, s_def in enumerate(stages or []):
            stage = ExecutionStage(
                campaign_id="",
                name=s_def.get("name", f"stage-{i}"),
                description=s_def.get("description", ""),
                sequence=i,
                depends_on=s_def.get("depends_on", []),
                requires_approval=s_def.get("requires_approval", False),
            )
            stage_objs.append(stage)

        campaign = OperationalCampaign(
            objective_id=objective_id,
            operator_id=operator_id,
            session_id=session_id,
            stages=stage_objs,
            max_fanout=max_fanout,
        )

        for stage in stage_objs:
            stage.campaign_id = campaign.campaign_id

        campaign.content_hash = _content_hash(campaign.to_dict())
        self._campaigns[campaign.campaign_id] = campaign

        self._lifecycle.register(campaign.campaign_id)
        self._lifecycle.transition(
            campaign.campaign_id, OperationalLifecycleState.STAGED,
        )

        self._graph.create_graph(
            campaign.campaign_id, objective_id, operator_id,
        )
        self._graph.add_node(
            campaign.campaign_id, "objective", objective_id,
            label=obj.description,
        )
        self._graph.add_node(
            campaign.campaign_id, "campaign", campaign.campaign_id,
        )
        self._graph.add_edge(
            campaign.campaign_id, objective_id, campaign.campaign_id,
            edge_type="defines",
        )

        for stage in stage_objs:
            self._lifecycle.register(stage.stage_id)
            self._graph.add_node(
                campaign.campaign_id, "stage", stage.stage_id,
                label=stage.name,
            )
            self._graph.add_edge(
                campaign.campaign_id, campaign.campaign_id, stage.stage_id,
                edge_type="contains",
            )

            for dep_id in stage.depends_on:
                self._dependencies.add_dependency(dep_id, stage.stage_id)
                self._graph.add_edge(
                    campaign.campaign_id, dep_id, stage.stage_id,
                    edge_type="depends_on",
                )

        self._chronology.record_objective_creation(
            campaign.campaign_id, objective_id,
        )
        self._chronology.record_campaign_creation(
            campaign.campaign_id, operator_id,
        )

        self._emit_receipt(campaign.campaign_id, "", "create_campaign",
                           "", OperationalLifecycleState.STAGED.value)

        return campaign

    def start_stage(
        self,
        campaign_id: str,
        stage_id: str,
    ) -> bool:
        """Start executing a stage (after dependencies met)."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False

        stage = self._find_stage(campaign, stage_id)
        if not stage:
            return False

        if not self._dependencies.are_dependencies_met(stage_id):
            return False

        if stage.requires_approval and not stage.approved:
            return False

        self._lifecycle.transition(
            stage_id, OperationalLifecycleState.EXECUTING,
        )
        stage.state = OperationalLifecycleState.EXECUTING.value
        stage.started_at = _now_iso()

        self._chronology.record_stage_transition(
            campaign_id, stage_id, "staged", "executing",
        )

        self._emit_receipt(campaign_id, stage_id, "start_stage",
                           "staged", "executing")
        return True

    def complete_stage(
        self,
        campaign_id: str,
        stage_id: str,
    ) -> bool:
        """Mark a stage as completed."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False

        stage = self._find_stage(campaign, stage_id)
        if not stage:
            return False

        self._lifecycle.transition(
            stage_id, OperationalLifecycleState.COMPLETED,
        )
        stage.state = OperationalLifecycleState.COMPLETED.value
        stage.completed_at = _now_iso()

        self._dependencies.satisfy(stage_id)

        self._chronology.record_stage_completion(campaign_id, stage_id)

        self._emit_receipt(campaign_id, stage_id, "complete_stage",
                           "executing", "completed")

        self._update_campaign_progress(campaign)
        return True

    def fail_stage(
        self,
        campaign_id: str,
        stage_id: str,
        reason: str = "",
    ) -> bool:
        """Mark a stage as failed."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False

        stage = self._find_stage(campaign, stage_id)
        if not stage:
            return False

        self._lifecycle.transition(
            stage_id, OperationalLifecycleState.FAILED, reason,
        )
        stage.state = OperationalLifecycleState.FAILED.value

        self._chronology.record_stage_transition(
            campaign_id, stage_id, "executing", "failed",
        )

        self._emit_receipt(campaign_id, stage_id, "fail_stage",
                           "executing", "failed")
        return True

    def defer_stage(
        self,
        campaign_id: str,
        stage_id: str,
        reason: str = "",
        resume_condition: str = "",
    ) -> dict[str, Any] | None:
        """Defer execution of a stage."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None

        stage = self._find_stage(campaign, stage_id)
        if not stage:
            return None

        self._lifecycle.transition(
            stage_id, OperationalLifecycleState.DEFERRED, reason,
        )
        stage.state = OperationalLifecycleState.DEFERRED.value

        deferred = self._deferred.defer_stage(
            campaign_id, stage_id, reason, resume_condition,
        )

        self._chronology.record_deferred_execution(
            campaign_id, stage_id, reason,
        )

        self._emit_receipt(campaign_id, stage_id, "defer_stage",
                           "executing", "deferred")
        return deferred.to_dict()

    def request_approval(
        self,
        campaign_id: str,
        stage_id: str,
        requested_by: str = "",
    ) -> OperationalApprovalState:
        """Request approval for a stage."""
        approval = OperationalApprovalState(
            campaign_id=campaign_id,
            stage_id=stage_id,
            requested_by=requested_by,
        )
        self._approvals[approval.approval_id] = approval

        self._chronology.record_approval(
            campaign_id, stage_id, approved_by="",
        )

        return approval

    def grant_approval(
        self,
        approval_id: str,
        approved_by: str = "operator",
    ) -> bool:
        """Grant approval for a stage."""
        approval = self._approvals.get(approval_id)
        if not approval:
            return False

        approval.approved = True
        approval.approved_by = approved_by
        approval.approved_at = _now_iso()

        campaign = self._campaigns.get(approval.campaign_id)
        if campaign:
            stage = self._find_stage(campaign, approval.stage_id)
            if stage:
                stage.approved = True

        self._chronology.record_approval(
            approval.campaign_id, approval.stage_id, approved_by,
        )

        return True

    def suspend_campaign(
        self,
        campaign_id: str,
        reason: str = "",
    ) -> bool:
        """Suspend a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False

        ok = self._lifecycle.transition(
            campaign_id, OperationalLifecycleState.SUSPENDED, reason,
        )
        if ok:
            campaign.state = OperationalLifecycleState.SUSPENDED.value
            self._chronology.record_execution_suspension(campaign_id, reason)
            self._emit_receipt(campaign_id, "", "suspend",
                               "", "suspended")
        return ok

    def resume_campaign(
        self,
        campaign_id: str,
    ) -> bool:
        """Resume a suspended campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False

        ok = self._lifecycle.transition(
            campaign_id, OperationalLifecycleState.RESUMED,
        )
        if ok:
            self._lifecycle.transition(
                campaign_id, OperationalLifecycleState.EXECUTING,
            )
            campaign.state = OperationalLifecycleState.EXECUTING.value
            self._emit_receipt(campaign_id, "", "resume",
                               "suspended", "executing")
        return ok

    def terminate_campaign(
        self,
        campaign_id: str,
        reason: str = "",
    ) -> bool:
        """Terminate a campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False

        ok = self._lifecycle.transition(
            campaign_id, OperationalLifecycleState.TERMINATED, reason,
        )
        if ok:
            campaign.state = OperationalLifecycleState.TERMINATED.value
            self._chronology.record_execution_termination(campaign_id, reason)
            self._emit_receipt(campaign_id, "", "terminate",
                               "", "terminated")
        return ok

    def checkpoint_campaign(
        self,
        campaign_id: str,
    ) -> dict[str, Any] | None:
        """Create a checkpoint for the campaign."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None

        stage_states = [s.to_dict() for s in campaign.stages]
        cp = self._continuation.create_checkpoint(
            campaign_id=campaign_id,
            stage_index=campaign.current_stage_index,
            campaign_state=campaign.state,
            stage_states=stage_states,
        )

        self._graph.persist_graph(campaign_id)

        self._emit_receipt(campaign_id, "", "checkpoint", "", "")
        return cp.to_dict()

    def get_progress(self, campaign_id: str) -> OperationalProgressState | None:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None

        completed = sum(1 for s in campaign.stages
                        if s.state == "completed")
        failed = sum(1 for s in campaign.stages
                     if s.state == "failed")
        deferred = sum(1 for s in campaign.stages
                       if s.state == "deferred")

        current_stage = ""
        for s in campaign.stages:
            if s.state == "executing":
                current_stage = s.stage_id
                break

        return OperationalProgressState(
            campaign_id=campaign_id,
            total_stages=len(campaign.stages),
            completed_stages=completed,
            failed_stages=failed,
            deferred_stages=deferred,
            current_stage_id=current_stage,
        )

    def get_campaign(self, campaign_id: str) -> OperationalCampaign | None:
        return self._campaigns.get(campaign_id)

    def get_objective(self, objective_id: str) -> OperationalObjective | None:
        return self._objectives.get(objective_id)

    def get_chronology(
        self, campaign_id: str, limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self._chronology.get_chronology(campaign_id, limit)

    def get_execution_graph(self, campaign_id: str) -> dict[str, Any] | None:
        return self._graph.get_graph(campaign_id)

    def get_recent_receipts(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._receipts[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_objectives": len(self._objectives),
            "total_campaigns": len(self._campaigns),
            "lifecycle": self._lifecycle.get_stats(),
            "dependencies": self._dependencies.get_stats(),
            "deferred": self._deferred.get_stats(),
            "continuation": self._continuation.get_stats(),
            "chronology": self._chronology.get_stats(),
            "graph": self._graph.get_stats(),
        }

    def _find_stage(
        self, campaign: OperationalCampaign, stage_id: str,
    ) -> ExecutionStage | None:
        for s in campaign.stages:
            if s.stage_id == stage_id:
                return s
        return None

    def _update_campaign_progress(self, campaign: OperationalCampaign) -> None:
        all_done = all(
            s.state in ("completed", "failed")
            for s in campaign.stages
        )
        if all_done and campaign.stages:
            any_failed = any(s.state == "failed" for s in campaign.stages)
            if any_failed:
                self._lifecycle.transition(
                    campaign.campaign_id, OperationalLifecycleState.FAILED,
                )
                campaign.state = OperationalLifecycleState.FAILED.value
            else:
                self._lifecycle.transition(
                    campaign.campaign_id, OperationalLifecycleState.COMPLETED,
                )
                campaign.state = OperationalLifecycleState.COMPLETED.value

    def _emit_receipt(
        self,
        campaign_id: str,
        stage_id: str,
        operation: str,
        from_state: str,
        to_state: str,
    ) -> OperationalExecutionReceipt:
        receipt = OperationalExecutionReceipt(
            campaign_id=campaign_id,
            stage_id=stage_id,
            operation=operation,
            from_state=from_state,
            to_state=to_state,
        )
        self._receipts.append(receipt)

        path = self._state_dir / "operational_receipts.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(receipt.to_dict(), default=str) + "\n")

        return receipt
