"""Tests for Phase 94D.4 auto worker runtime and capability routing."""

import sys

sys.path.insert(0, "/opt/OS")

import pytest

from eos_ai.substrate.capability_routing_contracts import (
    Capability,
    RoutingDecision,
    RoutingOutcome,
    RoutingRequirement,
    choose_best_node,
    score_node_for_requirement,
)
from eos_ai.substrate.topology_contracts import (
    NodeProfile,
    NodeRole,
    NodeType,
    TopologyProfile,
    build_founder_current_topology,
    build_single_local_topology,
)
from eos_ai.substrate.work_order_contracts import (
    AuthorityMode,
    SensitivityLevel,
    WorkOrder,
    WorkOrderTaskType,
)
from eos_ai.substrate.worker_node_contracts import (
    WorkerAction,
    WorkerMode,
    WorkerProfile,
    WorkerRole,
    WorkerRuntimeState,
    WorkerState,
    WORKER_STATE_TRANSITIONS,
)
from eos_ai.substrate.worker_node_runtime import (
    apply_advisor_response,
    build_approval_request_for_action,
    create_worker_execution_plan,
    create_worker_feedback_event,
    next_worker_state,
    should_request_advisor_approval,
    validate_worker_can_claim,
)
from eos_ai.substrate.governance_gate_contracts import GovernancePolicy
from eos_ai.substrate.message_bus_contracts import MessageEnvelope, MessageType


class TestCapabilityRouting:
    def test_routes_gui_task_to_local_pc(self):
        topo = build_founder_current_topology()
        req = RoutingRequirement(
            required_capabilities=["gui_computer_use", "browser_session"],
            description="GUI computer use task",
        )
        decision = choose_best_node(topo, req)
        assert decision.outcome in (RoutingOutcome.ROUTED, RoutingOutcome.MULTIPLE_CANDIDATES)
        assert decision.selected_node_id == "local_pc_worker"

    def test_routes_orchestration_to_vps(self):
        topo = build_founder_current_topology()
        req = RoutingRequirement(
            required_capabilities=["orchestration", "scheduling"],
            description="Scheduling task",
        )
        decision = choose_best_node(topo, req)
        assert decision.selected_node_id == "vps_orchestrator"

    def test_setup_required_when_no_node_matches(self):
        topo = build_founder_current_topology()
        req = RoutingRequirement(
            required_capabilities=["gpu_compute"],
            description="GPU inference task",
        )
        decision = choose_best_node(topo, req)
        assert decision.outcome == RoutingOutcome.SETUP_REQUIRED
        assert decision.selected_node_id is None
        assert "gpu_compute" in decision.missing_capabilities

    def test_empty_topology_returns_no_capable_node(self):
        topo = TopologyProfile(topology_id="empty", owner_id="test", nodes=[])
        req = RoutingRequirement(required_capabilities=["anything"])
        decision = choose_best_node(topo, req)
        assert decision.outcome == RoutingOutcome.NO_CAPABLE_NODE

    def test_score_node_with_all_required(self):
        node = NodeProfile(
            node_id="n1",
            node_type=NodeType.LOCAL_WORKSTATION,
            roles=[NodeRole.WORKER],
            capabilities=["gui_computer_use", "browser_session"],
            online=True,
        )
        req = RoutingRequirement(
            required_capabilities=["gui_computer_use"],
            preferred_capabilities=["browser_session"],
        )
        score, missing = score_node_for_requirement(node, req)
        assert score > 0.0
        assert missing == []

    def test_score_node_missing_required_is_zero(self):
        node = NodeProfile(
            node_id="n1",
            node_type=NodeType.CLOUD_VPS,
            roles=[NodeRole.ORCHESTRATOR],
            capabilities=["orchestration"],
        )
        req = RoutingRequirement(required_capabilities=["gui_computer_use"])
        score, missing = score_node_for_requirement(node, req)
        assert score == 0.0
        assert "gui_computer_use" in missing

    def test_single_local_topology_routes_everything_to_itself(self):
        topo = build_single_local_topology("test_user")
        req = RoutingRequirement(
            required_capabilities=["gui_computer_use", "orchestration"],
        )
        decision = choose_best_node(topo, req)
        assert decision.selected_node_id == "local_machine"


class TestWorkerStateMachine:
    def test_boot_to_idle(self):
        assert next_worker_state(WorkerState.BOOTING, "boot_complete") == WorkerState.IDLE

    def test_idle_to_claiming(self):
        assert next_worker_state(WorkerState.IDLE, "work_available") == WorkerState.CLAIMING_WORK

    def test_executing_to_observing(self):
        assert next_worker_state(WorkerState.EXECUTING, "action_complete") == WorkerState.OBSERVING

    def test_executing_needs_approval(self):
        assert (
            next_worker_state(WorkerState.EXECUTING, "approval_needed")
            == WorkerState.WAITING_FOR_ADVISOR_APPROVAL
        )

    def test_invalid_event_stays_same_state(self):
        assert next_worker_state(WorkerState.IDLE, "nonsense") == WorkerState.IDLE

    def test_terminal_states_cannot_transition(self):
        assert WORKER_STATE_TRANSITIONS[WorkerState.FAILED] == set()
        assert WORKER_STATE_TRANSITIONS[WorkerState.COMPLETE] == set()

    def test_runtime_state_transition_enforces_allowed(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.BOOTING,
            mode=WorkerMode.AUTO,
        )
        state.transition(WorkerState.IDLE)
        assert state.state == WorkerState.IDLE

    def test_runtime_state_rejects_invalid_transition(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.BOOTING,
            mode=WorkerMode.AUTO,
        )
        with pytest.raises(ValueError):
            state.transition(WorkerState.COMPLETE)


class TestWorkerClaimValidation:
    def test_disabled_worker_cannot_claim(self):
        wo = WorkOrder(
            work_order_id="wo_test",
            created_by_node="vps",
            assigned_to_node="local",
            task_type=WorkOrderTaskType.LOCAL_SOURCE_INVENTORY,
            objective="Test",
            source_targets=[],
            allowed_actions=["inventory_files"],
            blocked_actions=[],
            authority_mode=AuthorityMode.READ_ONLY,
            sensitivity_level=SensitivityLevel.PUBLIC,
            evidence_required=False,
            expected_outputs=["inventory.json"],
            timeout_minutes=30,
        )
        profile = WorkerProfile(
            worker_id="w1",
            node_id="local",
            roles=[WorkerRole.FILE_WORKER],
            capabilities=["local_files"],
            mode=WorkerMode.DISABLED,
        )
        can_claim, reason = validate_worker_can_claim(wo, profile)
        assert can_claim is False
        assert "disabled" in reason.lower()

    def test_capable_auto_worker_can_claim(self):
        wo = WorkOrder(
            work_order_id="wo_test",
            created_by_node="vps",
            assigned_to_node="local",
            task_type=WorkOrderTaskType.LOCAL_SOURCE_INVENTORY,
            objective="Test",
            source_targets=[],
            allowed_actions=["inventory_files"],
            blocked_actions=[],
            authority_mode=AuthorityMode.READ_ONLY,
            sensitivity_level=SensitivityLevel.PUBLIC,
            evidence_required=False,
            expected_outputs=["inventory.json"],
            timeout_minutes=30,
        )
        profile = WorkerProfile(
            worker_id="w1",
            node_id="local",
            roles=[WorkerRole.FILE_WORKER],
            capabilities=["local_files"],
            mode=WorkerMode.AUTO,
        )
        can_claim, reason = validate_worker_can_claim(wo, profile)
        assert can_claim is True


class TestAdvisorResponseApplication:
    def test_approve_moves_to_executing(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.WAITING_FOR_ADVISOR_APPROVAL,
            mode=WorkerMode.AUTO,
            pending_approval_id="apr_123",
        )
        response = MessageEnvelope(
            message_type=MessageType.APPROVAL_RESPONSE,
            sender="founder",
            recipient="advisor",
            payload={"decision": "APPROVE"},
        )
        result = apply_advisor_response(response, state)
        assert result.state == WorkerState.EXECUTING
        assert result.pending_approval_id is None

    def test_deny_moves_to_blocked(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.WAITING_FOR_ADVISOR_APPROVAL,
            mode=WorkerMode.AUTO,
            pending_approval_id="apr_456",
        )
        response = MessageEnvelope(
            message_type=MessageType.APPROVAL_RESPONSE,
            sender="founder",
            recipient="advisor",
            payload={"decision": "DENY", "reason": "Too risky"},
        )
        result = apply_advisor_response(response, state)
        assert result.state == WorkerState.BLOCKED
        assert "denied" in result.error_detail.lower()

    def test_stop_moves_to_failed(self):
        state = WorkerRuntimeState(
            worker_id="w1",
            state=WorkerState.WAITING_FOR_ADVISOR_APPROVAL,
            mode=WorkerMode.AUTO,
        )
        response = MessageEnvelope(
            message_type=MessageType.APPROVAL_RESPONSE,
            sender="founder",
            recipient="advisor",
            payload={"decision": "STOP"},
        )
        result = apply_advisor_response(response, state)
        assert result.state == WorkerState.FAILED
