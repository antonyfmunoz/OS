"""Propagation Planner — creates wave-based propagation plans.

Takes a ChangeEvent, PropagationGraph, and ImpactAnalysis to produce
ordered propagation waves with parallel action groups, reconvergence
points, validation checkpoints, and governance gates.

Phase 12.0. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import uuid4

from substrate.organism.propagation_graph import (
    PropagationGraph,
    PropagationNodeType,
    PropagationEdgeType,
    PropagationMode,
)
from substrate.organism.change_event import (
    ChangeEvent,
    PropagationAction,
    PropagationActionStatus,
    PropagationWave,
    PropagationPlan,
)
from substrate.organism.impact_analyzer import ImpactAnalysis, ImpactedNode

logger = logging.getLogger(__name__)

_MODE_TO_ACTION = {
    "no_op": "no_op",
    "notify_only": "notify",
    "recompute": "recompute",
    "revalidate": "revalidate",
    "regenerate": "regenerate",
    "create_candidate": "create_candidate",
    "create_work_packet": "create_work_packet",
    "require_approval": "require_approval",
    "queue_work": "queue_work",
    "update_memory": "update_memory",
    "update_template": "update_template",
    "update_reliability": "update_reliability",
    "update_projection": "update_projection",
    "block_until_review": "block_until_review",
}

_SAFE_ACTIONS = frozenset({"no_op", "notify", "recompute", "revalidate"})

_WAVE_ASSIGNMENT = {
    PropagationNodeType.WORK_PACKET: 1,
    PropagationNodeType.WORKCELL: 1,
    PropagationNodeType.ADVISOR_BRANCH: 1,
    PropagationNodeType.SELF_BUILD_ITEM: 1,
    PropagationNodeType.ROADMAP_PHASE: 2,
    PropagationNodeType.ROLE_CONTRACT: 2,
    PropagationNodeType.KNOWLEDGE_MODEL: 2,
    PropagationNodeType.TEMPLATE: 3,
    PropagationNodeType.AGENT_CAPABILITY: 3,
    PropagationNodeType.PRODUCTION_TRUTH_DELTA: 2,
    PropagationNodeType.OUTCOME: 2,
    PropagationNodeType.API_ROUTE: 3,
    PropagationNodeType.COCKPIT_PANEL: 3,
    PropagationNodeType.WORLD_MODEL_ENTITY: 2,
    PropagationNodeType.DEPENDENCY_GRAPH_NODE: 2,
    PropagationNodeType.MEMORY_ENTRY: 4,
    PropagationNodeType.CANDIDATE: 4,
    PropagationNodeType.COMPANY: 2,
    PropagationNodeType.ENTITY: 2,
    PropagationNodeType.PRODUCT: 2,
    PropagationNodeType.OFFER: 2,
    PropagationNodeType.PORTFOLIO: 2,
    PropagationNodeType.HUMAN_ACTION: 4,
    PropagationNodeType.APPROVAL_PACKET: 4,
    PropagationNodeType.SANDBOX: 4,
    PropagationNodeType.PULL_REQUEST: 4,
    PropagationNodeType.CONFIG_FILE: 3,
    PropagationNodeType.DATA_STORE: 3,
    PropagationNodeType.CLIENT: 2,
    PropagationNodeType.CONTENT_ASSET: 3,
}


class PropagationPlanner:
    """Creates wave-based propagation plans from impact analysis."""

    def __init__(self, graph: PropagationGraph) -> None:
        self._graph = graph

    def plan(self, event: ChangeEvent, analysis: ImpactAnalysis) -> PropagationPlan:
        plan = PropagationPlan(
            plan_id=f"pp-{uuid4().hex[:12]}",
            change_event_id=event.change_id,
            root_node_id=event.source_node_id,
            affected_nodes=[n.node_id for n in analysis.affected_nodes],
            execution_mode="dry_run",
        )

        wave_buckets: dict[int, list[ImpactedNode]] = {}
        for impacted in analysis.affected_nodes:
            node = self._graph.nodes.get(impacted.node_id)
            if not node:
                continue
            nt = node.node_type if isinstance(node.node_type, PropagationNodeType) else PropagationNodeType.WORK_PACKET
            wave_num = _WAVE_ASSIGNMENT.get(nt, 4)
            wave_buckets.setdefault(wave_num, []).append(impacted)

        for wave_num in sorted(wave_buckets.keys()):
            impacted_nodes = wave_buckets[wave_num]
            wave = self._build_wave(wave_num, impacted_nodes, event, analysis)
            plan.propagation_waves.append(wave)

        for impacted in analysis.affected_nodes:
            if impacted.is_blocked:
                plan.blocked_nodes.append(impacted.node_id)
            if impacted.requires_approval:
                plan.approval_required_nodes.append(impacted.node_id)
            if impacted.requires_human:
                plan.human_required_nodes.append(impacted.node_id)
            if impacted.requires_validation:
                plan.validation_required_nodes.append(impacted.node_id)
            if impacted.is_no_op:
                plan.no_op_nodes.append(impacted.node_id)

        plan.expected_updates = sum(
            len(w.actions) for w in plan.propagation_waves
            if any(a.status != PropagationActionStatus.BLOCKED for a in w.actions)
        )
        plan.risk_summary = analysis.risk_summary

        return plan

    def _build_wave(
        self,
        wave_num: int,
        impacted_nodes: list[ImpactedNode],
        event: ChangeEvent,
        analysis: ImpactAnalysis,
    ) -> PropagationWave:
        wave = PropagationWave(
            wave_id=f"pw-{uuid4().hex[:12]}",
            wave_number=wave_num,
            nodes=[n.node_id for n in impacted_nodes],
            can_run_parallel=True,
        )

        if wave_num > 1:
            wave.dependencies = [f"wave-{wave_num - 1}"]

        has_parallel_branches = len(impacted_nodes) > 1
        wave.reconvergence_required = has_parallel_branches and any(
            n.node_id in analysis.reconvergence_required for n in impacted_nodes
        )

        for impacted in impacted_nodes:
            action = self._create_action(impacted, event)
            wave.actions.append(action)

        return wave

    def _create_action(self, impacted: ImpactedNode, event: ChangeEvent) -> PropagationAction:
        action_type = _MODE_TO_ACTION.get(impacted.propagation_mode, "notify")

        is_safe = action_type in _SAFE_ACTIONS
        is_medium_risk = event.risk_class == "medium" or impacted.risk_class == "medium"

        status = PropagationActionStatus.PENDING
        if impacted.is_blocked or (is_medium_risk and not is_safe):
            status = PropagationActionStatus.BLOCKED
        elif impacted.requires_approval:
            status = PropagationActionStatus.APPROVAL_REQUIRED
        elif impacted.requires_human:
            status = PropagationActionStatus.HUMAN_REQUIRED

        return PropagationAction(
            action_id=f"pa-{uuid4().hex[:12]}",
            node_id=impacted.node_id,
            action_type=action_type,
            reason=f"Propagation from change {event.change_id}: {event.title}",
            input_evidence=[{
                "change_event_id": event.change_id,
                "change_type": event.change_type.value if hasattr(event.change_type, "value") else event.change_type,
                "impact_depth": impacted.impact_depth,
                "impact_score": impacted.impact_score,
            }],
            output_expected=f"Update {impacted.node_type} {impacted.title}",
            approval_required=impacted.requires_approval,
            validation_required=impacted.requires_validation,
            human_required=impacted.requires_human,
            risk_class=impacted.risk_class,
            idempotency_key=f"idem-{event.change_id}-{impacted.node_id}",
            status=status,
        )
