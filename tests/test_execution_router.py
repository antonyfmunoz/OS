"""Tests for runtime.substrate.execution_router — data-driven routing decisions."""

from __future__ import annotations

import dataclasses
import sys

import pytest

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.execution_contract import (
    ExecutionClass,
    RoutingContext,
    RoutingDecision,
    RoutingReasonCode,
)
from runtime.substrate.execution_router import ExecutionRouter
from runtime.substrate.nodes import (
    Node,
    NodeRegistry,
    NodeRole,
    NodeStatus,
    NodeType,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_registry() -> NodeRegistry:
    """Build a test registry with orchestrator + workstation nodes."""
    reg = NodeRegistry(persist=False)
    reg.upsert(
        Node(
            node_id="vps-primary",
            node_type=NodeType.VPS,
            role=NodeRole.ORCHESTRATOR,
            capabilities=["reasoning", "run_shell", "run_python"],
            status=NodeStatus.ONLINE,
        )
    )
    reg.upsert(
        Node(
            node_id="test-workstation",
            node_type=NodeType.LOCAL_STATION,
            role=NodeRole.WORKSTATION,
            capabilities=["speak_text", "play_sound", "open_url"],
            status=NodeStatus.ONLINE,
        )
    )
    return reg


@pytest.fixture()
def registry() -> NodeRegistry:
    return _make_registry()


@pytest.fixture()
def router(registry: NodeRegistry) -> ExecutionRouter:
    return ExecutionRouter(registry)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pure_prefers_local(router: ExecutionRouter) -> None:
    """PURE class routes to orchestrator node (low latency local)."""
    ctx = RoutingContext(execution_class=ExecutionClass.PURE)
    decision = router.route(ctx)
    assert decision.target.node_id == "vps-primary"
    assert decision.target.transport == "direct"
    assert decision.reason_code == RoutingReasonCode.EXECUTION_CLASS_POLICY


def test_side_effect_prefers_workstation(router: ExecutionRouter) -> None:
    """SIDE_EFFECT class routes to workstation when online."""
    ctx = RoutingContext(
        execution_class=ExecutionClass.SIDE_EFFECT,
        required_capabilities=frozenset({"speak_text"}),
    )
    decision = router.route(ctx)
    assert decision.target.node_id == "test-workstation"
    assert decision.target.transport == "http"
    assert decision.target.fallback_node_id == "vps-primary"
    assert decision.target.fallback_transport == "direct"


def test_transport_prefers_workstation(router: ExecutionRouter) -> None:
    """TRANSPORT class routes to workstation when online."""
    ctx = RoutingContext(
        execution_class=ExecutionClass.TRANSPORT,
        required_capabilities=frozenset({"open_url"}),
    )
    decision = router.route(ctx)
    assert decision.target.node_id == "test-workstation"
    assert decision.target.transport == "http"


def test_force_node_override(router: ExecutionRouter) -> None:
    """force_node_id bypasses all policy logic."""
    ctx = RoutingContext(
        execution_class=ExecutionClass.PURE,
        force_node_id="test-workstation",
    )
    decision = router.route(ctx)
    assert decision.target.node_id == "test-workstation"
    assert decision.reason_code == RoutingReasonCode.EXPLICIT_OVERRIDE


def test_fallback_when_primary_offline(registry: NodeRegistry) -> None:
    """Workstation offline triggers local fallback."""
    # Take workstation offline
    registry.upsert(
        Node(
            node_id="test-workstation",
            node_type=NodeType.LOCAL_STATION,
            role=NodeRole.WORKSTATION,
            capabilities=["speak_text", "play_sound", "open_url"],
            status=NodeStatus.OFFLINE,
        )
    )
    router = ExecutionRouter(registry)
    ctx = RoutingContext(
        execution_class=ExecutionClass.SIDE_EFFECT,
        required_capabilities=frozenset({"speak_text"}),
        allow_fallback=True,
    )
    decision = router.route(ctx)
    assert decision.target.node_id == "vps-primary"
    assert decision.target.transport == "direct"
    assert decision.reason_code == RoutingReasonCode.FALLBACK_PRIMARY_UNAVAILABLE


def test_no_route_when_fallback_disabled(registry: NodeRegistry) -> None:
    """No capable nodes + allow_fallback=False returns empty target."""
    registry.upsert(
        Node(
            node_id="test-workstation",
            node_type=NodeType.LOCAL_STATION,
            role=NodeRole.WORKSTATION,
            capabilities=["speak_text", "play_sound", "open_url"],
            status=NodeStatus.OFFLINE,
        )
    )
    router = ExecutionRouter(registry)
    ctx = RoutingContext(
        execution_class=ExecutionClass.SIDE_EFFECT,
        required_capabilities=frozenset({"speak_text"}),
        allow_fallback=False,
    )
    decision = router.route(ctx)
    assert decision.target.node_id == ""
    assert decision.target.transport == ""


def test_degraded_accepted_for_pure(registry: NodeRegistry) -> None:
    """DEGRADED node accepted for PURE but not for SIDE_EFFECT."""
    # Make both nodes degraded — orchestrator degraded, workstation offline
    registry.upsert(
        Node(
            node_id="vps-primary",
            node_type=NodeType.VPS,
            role=NodeRole.ORCHESTRATOR,
            capabilities=["reasoning", "run_shell", "run_python"],
            status=NodeStatus.DEGRADED,
        )
    )
    registry.upsert(
        Node(
            node_id="test-workstation",
            node_type=NodeType.LOCAL_STATION,
            role=NodeRole.WORKSTATION,
            capabilities=["speak_text", "play_sound", "open_url"],
            status=NodeStatus.DEGRADED,
        )
    )
    router = ExecutionRouter(registry)

    # PURE should accept the degraded orchestrator
    pure_ctx = RoutingContext(execution_class=ExecutionClass.PURE)
    pure_decision = router.route(pure_ctx)
    assert pure_decision.target.node_id == "vps-primary"

    # SIDE_EFFECT should NOT accept degraded nodes — falls back
    se_ctx = RoutingContext(
        execution_class=ExecutionClass.SIDE_EFFECT,
        required_capabilities=frozenset({"speak_text"}),
        allow_fallback=True,
    )
    se_decision = router.route(se_ctx)
    assert se_decision.reason_code == RoutingReasonCode.FALLBACK_PRIMARY_UNAVAILABLE


def test_routing_decision_immutable(router: ExecutionRouter) -> None:
    """Cannot modify returned RoutingDecision (frozen dataclass)."""
    ctx = RoutingContext(execution_class=ExecutionClass.PURE)
    decision = router.route(ctx)

    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.reason_detail = "mutated"  # type: ignore[misc]

    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.target = None  # type: ignore[misc]
