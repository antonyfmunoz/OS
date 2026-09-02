"""Wave 2 C1 — compiler wires plan-node depends_on into WorkPacket.dependencies.

Wave 1's ``materialize_packets`` created WorkPackets but left ``dependencies``
empty even though plan nodes carried ``depends_on`` edges (``packet_predecessors``
already computed the packet-level closure, used only by assertions). Wave 2's
dependency-aware scheduler holds a fan-in Task until its predecessors' attempts
succeed — impossible if every packet ships with zero dependencies.

This drives ``materialize_packets`` directly with a hand-built fan-in plan
(A, B independent; C depends on both) and proves each packet's ``dependencies``
equals the packet_ids of its ``packet_predecessors`` closure, and that the edges
persist to the queue store. It is the guard against silently-never-blocking
scheduling.
"""

from __future__ import annotations

import pytest

from substrate.contracts.work_context import WorkScope
from substrate.execution.planning.archetypes import resolve_archetype
from substrate.execution.planning.compiler import materialize_packets, packet_predecessors
from substrate.execution.planning.records import (
    ObjectivePlanNode,
    ObjectivePlanRecord,
    PlanningSession,
)
from substrate.organism.universal_work_queue import UniversalWorkQueue


def _fanin_plan() -> ObjectivePlanRecord:
    """A: backend, B: frontend (independent); C: integration (depends on A∧B)."""
    a = ObjectivePlanNode(
        kind="packet",
        title="backend change",
        lane="build",
        writable_path_scope=["app", "tests"],
        scope_declared=True,
    )
    b = ObjectivePlanNode(
        kind="packet",
        title="frontend change",
        lane="build",
        writable_path_scope=["app", "tests"],
        scope_declared=True,
    )
    c = ObjectivePlanNode(
        kind="packet",
        title="integration",
        lane="build",
        depends_on=[a.node_id, b.node_id],
        writable_path_scope=["app", "tests"],
        scope_declared=True,
    )
    plan = ObjectivePlanRecord(
        objective_id="goal-1",
        objective_text="fan-in objective",
        conversation_id="conv-1",
        nodes=[a.to_dict(), b.to_dict(), c.to_dict()],
        edges=[
            {"from": a.node_id, "to": c.node_id},
            {"from": b.node_id, "to": c.node_id},
        ],
        lanes=["build"],
        work_scope=WorkScope(tenant_id="tenant-a", target_kind="umh_substrate").to_dict(),
    )
    return plan, a.node_id, b.node_id, c.node_id


@pytest.fixture()
def queue(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("UMH_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir()
    return UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))


def test_fanin_packet_gets_both_predecessor_dependencies(queue):
    plan, a_node, b_node, c_node = _fanin_plan()
    scope = WorkScope(tenant_id="tenant-a", target_kind="umh_substrate")
    archetype = resolve_archetype(plan.objective_text, scope)
    session = PlanningSession(conversation_id="conv-1", objective_id="goal-1", tenant_id="tenant-a")

    materialize_packets(plan, scope, archetype, session, queue)

    node_to_wp = {n["node_id"]: n["workpacket_id"] for n in plan.nodes}
    wp_a, wp_b, wp_c = node_to_wp[a_node], node_to_wp[b_node], node_to_wp[c_node]

    pkt_a = queue.get_packet(wp_a)
    pkt_b = queue.get_packet(wp_b)
    pkt_c = queue.get_packet(wp_c)

    # A and B are independent — no dependencies.
    assert pkt_a.dependencies == []
    assert pkt_b.dependencies == []
    # C (the fan-in) depends on BOTH A and B, expressed as packet_ids.
    assert sorted(pkt_c.dependencies) == sorted([wp_a, wp_b])

    # And the wiring matches packet_predecessors exactly, for every node.
    for node in plan.nodes:
        pkt = queue.get_packet(node["workpacket_id"])
        expected = [node_to_wp[p] for p in packet_predecessors(plan, node["node_id"])]
        assert sorted(pkt.dependencies) == sorted(expected)


def test_fanin_dependencies_persist_to_queue_store(queue):
    plan, _a, _b, c_node = _fanin_plan()
    scope = WorkScope(tenant_id="tenant-a", target_kind="umh_substrate")
    archetype = resolve_archetype(plan.objective_text, scope)
    session = PlanningSession(conversation_id="conv-1", objective_id="goal-1", tenant_id="tenant-a")
    materialize_packets(plan, scope, archetype, session, queue)

    wp_c = next(n["workpacket_id"] for n in plan.nodes if n["node_id"] == c_node)

    # Reload from disk — the dependency edges must be persisted, not in-memory only.
    reloaded = UniversalWorkQueue(store_path=queue._store_path)
    pkt_c = reloaded.get_packet(wp_c)
    assert pkt_c is not None
    assert len(pkt_c.dependencies) == 2


def test_chain_dependencies(queue):
    """A → B → C: B depends on A, C depends on B (transitive edges not collapsed)."""
    a = ObjectivePlanNode(
        kind="packet",
        title="a",
        lane="build",
        writable_path_scope=["app", "tests"],
        scope_declared=True,
    )
    b = ObjectivePlanNode(
        kind="packet",
        title="b",
        lane="build",
        depends_on=[a.node_id],
        writable_path_scope=["app", "tests"],
        scope_declared=True,
    )
    c = ObjectivePlanNode(
        kind="packet",
        title="c",
        lane="build",
        depends_on=[b.node_id],
        writable_path_scope=["app", "tests"],
        scope_declared=True,
    )
    plan = ObjectivePlanRecord(
        objective_id="goal-2",
        objective_text="chain objective",
        conversation_id="conv-2",
        nodes=[a.to_dict(), b.to_dict(), c.to_dict()],
        edges=[
            {"from": a.node_id, "to": b.node_id},
            {"from": b.node_id, "to": c.node_id},
        ],
        lanes=["build"],
        work_scope=WorkScope(tenant_id="tenant-a", target_kind="umh_substrate").to_dict(),
    )
    scope = WorkScope(tenant_id="tenant-a", target_kind="umh_substrate")
    archetype = resolve_archetype(plan.objective_text, scope)
    session = PlanningSession(conversation_id="conv-2", objective_id="goal-2", tenant_id="tenant-a")
    materialize_packets(plan, scope, archetype, session, queue)

    node_to_wp = {n["node_id"]: n["workpacket_id"] for n in plan.nodes}
    pkt_b = queue.get_packet(node_to_wp[b.node_id])
    pkt_c = queue.get_packet(node_to_wp[c.node_id])
    # Direct predecessors only (packet_predecessors is the immediate packet
    # closure through non-packet nodes; here edges are packet→packet).
    assert pkt_b.dependencies == [node_to_wp[a.node_id]]
    assert pkt_c.dependencies == [node_to_wp[b.node_id]]
