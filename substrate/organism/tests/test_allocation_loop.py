"""Tests for the governed runtime allocation loop."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

from substrate.organism.allocation_loop import (
    AllocationLoop,
    AllocationStrategy,
    AllocationDecision,
)
from substrate.organism.event_spine import EventDomain, EventSpine
from substrate.organism.runtime_graph import (
    AvailabilityStatus,
    CostProfile,
    RuntimeCapability,
    RuntimeClass,
    RuntimeGraph,
)
from substrate.organism.runtime_supervisor import RuntimeSupervisor
from substrate.organism.execution_economy import ExecutionEconomy
from substrate.organism.recursion_governance import RecursionGovernor


def _make_graph() -> RuntimeGraph:
    graph = RuntimeGraph()
    graph.register(
        "cc-opus", RuntimeClass.AI_CLI,
        frozenset({RuntimeCapability.CODE_WRITE, RuntimeCapability.REASON}),
        cost=CostProfile(cost_per_1k_input=0.0, is_subscription=True),
    )
    graph.register(
        "gemini-flash", RuntimeClass.AI_API,
        frozenset({RuntimeCapability.REASON, RuntimeCapability.RESEARCH}),
        cost=CostProfile(cost_per_1k_input=0.0005),
    )
    graph.register(
        "ollama-local", RuntimeClass.LOCAL_MODEL,
        frozenset({RuntimeCapability.REASON, RuntimeCapability.FAST_RESPONSE}),
        cost=CostProfile(cost_per_1k_input=0.0, is_subscription=True),
    )
    return graph


def _make_loop() -> tuple[AllocationLoop, EventSpine]:
    spine = EventSpine()
    graph = _make_graph()
    supervisor = RuntimeSupervisor(graph)
    economy = ExecutionEconomy()
    governor = RecursionGovernor()

    loop = AllocationLoop(
        spine=spine,
        graph=graph,
        supervisor=supervisor,
        economy=economy,
        governor=governor,
    )
    return loop, spine


def test_allocation_cycle():
    loop, spine = _make_loop()
    decisions = loop.allocation_cycle()
    assert isinstance(decisions, list)


def test_detect_degraded_runtime():
    loop, _ = _make_loop()
    loop._graph.update_status("gemini-flash", AvailabilityStatus.DEGRADED)

    decisions = loop.allocation_cycle()
    degraded = [d for d in decisions if d.action == "flag_degraded"]
    assert len(degraded) >= 1


def test_throttle_under_governor_kill():
    loop, _ = _make_loop()
    loop._governor.kill()

    decisions = loop.allocation_cycle()
    throttled = [d for d in decisions if d.action == "throttled"]
    assert len(throttled) >= 1


def test_emits_allocation_events():
    loop, spine = _make_loop()
    loop.allocation_cycle()

    events = spine.recent(limit=50)
    alloc_events = [e for e in events if e.domain == EventDomain.LEVERAGE]
    assert len(alloc_events) >= 1


def test_cost_spike_detection():
    loop, _ = _make_loop()
    loop._last_costs["gemini-flash"] = 0.001
    node = loop._graph.get("gemini-flash")
    assert node is not None
    node.cost = CostProfile(cost_per_1k_input=0.05, cost_per_1k_output=0.15)

    decisions = loop.allocation_cycle()
    spikes = [d for d in decisions if d.action == "cost_spike"]
    assert len(spikes) >= 1


def test_to_dict():
    loop, _ = _make_loop()
    loop.allocation_cycle()
    d = loop.to_dict()
    assert "cycle_count" in d
    assert "decisions" in d
    assert "strategy" in d
