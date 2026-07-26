"""Tenth layer: the multi-lane Task graph must be PRODUCED, then PROVEN.

Field run 20260726T025143Z-p1 spent real worker quota and failed at
``w16_ab_running_concurrent`` because the objective compiled to ONE combined
Task — the execution layer never got a valid four-Task graph to schedule.

Two things are covered here:

1. **Production** (``substrate/execution/planning/compiler.py``) — a caller's
   DECLARED lane decomposition becomes four canonical packet nodes with real
   per-lane authority and resolved dependencies (C after A∧B, D after C,
   D zero-write).
2. **Proof before quota** (``substrate/execution/attempts/graph_shape_gate.py``)
   — a read-only gate that rejects every wrong shape BEFORE authorization or
   dispatch, so a mis-shaped graph can never cost a worker invocation again.

Lanes are DECLARED by the runtime that owns the workspace, never inferred from
titles, packet-id shapes, or a worker's diff.
"""

from __future__ import annotations

import json
import os

import pytest

from substrate.contracts.work_context import WorkRequirements, WorkScope
from substrate.execution.attempts.graph_shape_gate import (
    GraphShapeError,
    evaluate_graph_shape,
)
from substrate.execution.planning.archetypes import resolve_archetype
from substrate.execution.planning.compiler import (
    PlanCompilationError,
    compile_plan,
    derive_state_records,
)
from substrate.execution.planning.records import (
    GroundingSnapshot,
    ObjectiveLane,
    PlanningSession,
)

OBJECTIVE = "Add note search: backend endpoint + frontend box, integrated and verified."

# The canonical four-lane declaration for the qualification objective. Scopes
# are least-privilege and DISTINCT; the verifier declares zero writable paths.
BACKEND_SCOPE = ["app/main.py", "app/store.py", "tests/test_search_api.py"]
FRONTEND_SCOPE = ["app/static", "tests/test_ui_search.py"]
INTEGRATION_SCOPE = [
    "app/main.py",
    "app/store.py",
    "app/static",
    "tests/test_search_api.py",
    "tests/test_ui_search.py",
]


def _lanes() -> list[ObjectiveLane]:
    return [
        ObjectiveLane(
            lane_key="backend",
            title="Backend search endpoint",
            writable_path_scope=list(BACKEND_SCOPE),
            semantic_label="backend_task_id",
        ),
        ObjectiveLane(
            lane_key="frontend",
            title="Frontend search UI",
            writable_path_scope=list(FRONTEND_SCOPE),
            semantic_label="frontend_task_id",
        ),
        ObjectiveLane(
            lane_key="integration",
            title="Integrate and reconcile search branches",
            writable_path_scope=list(INTEGRATION_SCOPE),
            depends_on=["backend", "frontend"],
            semantic_label="integration_task_id",
        ),
        ObjectiveLane(
            lane_key="verification",
            title="Independently verify note search",
            writable_path_scope=[],
            depends_on=["integration"],
            semantic_label="verification_task_id",
        ),
    ]


def _compile(lanes: list[ObjectiveLane] | None, objective: str = OBJECTIVE):
    scope = WorkScope(tenant_id="t-lane", target_kind="self_build")
    snapshot = GroundingSnapshot(intent_id="int-lane")
    current, desired, gaps = derive_state_records(
        objective, snapshot, tenant_id="t-lane", scope=scope, lanes=lanes
    )
    session = PlanningSession(
        objective_id="goal-lane", objective_text=objective, conversation_id="conv-lane"
    )
    plan = compile_plan(
        session,
        scope,
        "task_objective",
        current,
        desired,
        gaps,
        snapshot.grounding_snapshot_id,
        resolve_archetype(objective, scope),
    )
    return plan


def _packet_nodes(plan) -> list[dict]:
    return [n for n in plan.nodes if n["kind"] == "packet"]


def _as_packets(plan) -> list[dict]:
    """Materialize nodes the way the compiler does: per-node declared authority."""
    nodes = _packet_nodes(plan)
    id_map = {n["node_id"]: f"wp-{i:02d}" for i, n in enumerate(nodes)}
    packets = []
    for node in nodes:
        requirements = WorkRequirements()
        requirements.declare_writable_paths(list(node["writable_path_scope"]))
        packets.append(
            {
                "packet_id": id_map[node["node_id"]],
                "dependencies": [id_map[d] for d in node["depends_on"] if d in id_map],
                "lineage": {"plan_record_id": plan.plan_record_id},
                "requirements": requirements.to_dict(),
            }
        )
    return packets


# ── A. production: the declared decomposition becomes four real nodes ────────


def test_declared_lanes_produce_four_packet_nodes():
    nodes = _packet_nodes(_compile(_lanes()))
    assert len(nodes) == 4


def test_undeclared_objective_still_produces_one_umbrella_task():
    """The fallback is preserved — this is what the field run actually hit."""
    nodes = _packet_nodes(_compile(None))
    assert len(nodes) == 1


def test_dependencies_resolve_to_real_node_ids():
    nodes = _packet_nodes(_compile(_lanes()))
    by_title = {n["title"]: n for n in nodes}
    ids = {n["node_id"] for n in nodes}
    backend = by_title["Backend search endpoint"]
    frontend = by_title["Frontend search UI"]
    integration = by_title["Integrate and reconcile search branches"]
    verification = by_title["Independently verify note search"]

    assert backend["depends_on"] == []
    assert frontend["depends_on"] == []
    assert set(integration["depends_on"]) == {backend["node_id"], frontend["node_id"]}
    assert verification["depends_on"] == [integration["node_id"]]
    # every dependency names a node that exists in this plan
    for node in nodes:
        assert set(node["depends_on"]) <= ids


def test_each_lane_carries_its_own_declared_authority():
    nodes = _packet_nodes(_compile(_lanes()))
    scopes = {n["title"]: n["writable_path_scope"] for n in nodes}
    assert scopes["Backend search endpoint"] == BACKEND_SCOPE
    assert scopes["Frontend search UI"] == FRONTEND_SCOPE
    assert scopes["Independently verify note search"] == []
    assert all(n["scope_declared"] for n in nodes)


def test_implementation_lane_scopes_are_disjoint():
    nodes = _packet_nodes(_compile(_lanes()))
    scopes = {n["title"]: set(n["writable_path_scope"]) for n in nodes}
    assert not scopes["Backend search endpoint"] & scopes["Frontend search UI"]


def test_verifier_lane_is_zero_write():
    nodes = _packet_nodes(_compile(_lanes()))
    verifier = next(n for n in nodes if n["title"] == "Independently verify note search")
    assert verifier["writable_path_scope"] == []
    assert verifier["scope_declared"] is True


def test_plan_edges_encode_the_fan_in():
    plan = _compile(_lanes())
    nodes = {n["node_id"]: n for n in _packet_nodes(plan)}
    by_title = {n["title"]: n for n in nodes.values()}
    integration_id = by_title["Integrate and reconcile search branches"]["node_id"]
    incoming = {e["from"] for e in plan.edges if e["to"] == integration_id}
    assert by_title["Backend search endpoint"]["node_id"] in incoming
    assert by_title["Frontend search UI"]["node_id"] in incoming


# ── B. production fails closed on a malformed declaration ────────────────────


@pytest.mark.parametrize(
    "lanes,reason",
    [
        ([ObjectiveLane(lane_key="", writable_path_scope=[])], "lane_key"),
        (
            [
                ObjectiveLane(lane_key="dup", writable_path_scope=[]),
                ObjectiveLane(lane_key="dup", writable_path_scope=[]),
            ],
            "duplicate",
        ),
        (
            [ObjectiveLane(lane_key="a", writable_path_scope=[], depends_on=["ghost"])],
            "undeclared lane",
        ),
        (
            [ObjectiveLane(lane_key="a", writable_path_scope=[], depends_on=["a"])],
            "itself",
        ),
    ],
)
def test_malformed_lane_declaration_fails_closed(lanes, reason):
    with pytest.raises(PlanCompilationError) as exc:
        _compile(lanes)
    assert reason in str(exc.value)


def test_lane_declaration_cannot_supply_node_or_packet_identity():
    """A caller supplies lane_keys only — identity stays compiler-minted."""
    nodes = _packet_nodes(_compile(_lanes()))
    for node in nodes:
        assert node["node_id"].startswith("node-")
        # the caller's key survives only as the gap id, never as node identity
        assert node["gap_id"].startswith("gap-lane-")


# ── C. the pre-quota gate proves the shape before any dispatch ───────────────


def test_gate_accepts_the_graph_the_compiler_produces():
    plan = _compile(_lanes())
    verdict = evaluate_graph_shape(
        packets=_as_packets(plan), plan_record_id=plan.plan_record_id, attempt_count=0
    )
    assert verdict.ok, verdict.failures
    assert len(verdict.checks) == 11
    assert all(c["ok"] for c in verdict.checks)


def test_gate_rejects_the_single_umbrella_task_that_failed_in_the_field():
    plan = _compile(None)
    verdict = evaluate_graph_shape(
        packets=_as_packets(plan), plan_record_id=plan.plan_record_id, attempt_count=0
    )
    assert not verdict.ok
    assert any("task_count" in f for f in verdict.failures)


def _good_packets() -> list[dict]:
    def packet(pid, deps, scope):
        requirements = WorkRequirements()
        requirements.declare_writable_paths(scope)
        return {
            "packet_id": pid,
            "dependencies": deps,
            "lineage": {"plan_record_id": "opr-x"},
            "requirements": requirements.to_dict(),
        }

    return [
        packet("wp-a", [], ["app/main.py"]),
        packet("wp-b", [], ["app/static"]),
        packet("wp-c", ["wp-a", "wp-b"], ["app/main.py", "app/static"]),
        packet("wp-d", ["wp-c"], []),
    ]


def test_gate_rejects_write_authorized_verifier():
    packets = _good_packets()
    packets[3]["requirements"]["writable_path_scope"] = ["app/main.py"]
    verdict = evaluate_graph_shape(packets=packets, plan_record_id="opr-x", attempt_count=0)
    assert not verdict.ok
    assert any("verifier_zero_write" in f for f in verdict.failures)


def test_gate_rejects_identical_implementation_scopes():
    packets = _good_packets()
    packets[1]["requirements"]["writable_path_scope"] = ["app/main.py"]
    verdict = evaluate_graph_shape(packets=packets, plan_record_id="opr-x", attempt_count=0)
    assert not verdict.ok
    assert any("distinct_implementation_scopes" in f for f in verdict.failures)


def test_gate_rejects_partial_fan_in():
    packets = _good_packets()
    packets[2]["dependencies"] = ["wp-a"]
    verdict = evaluate_graph_shape(packets=packets, plan_record_id="opr-x", attempt_count=0)
    assert not verdict.ok
    assert any("fan_in_depends_on_both" in f for f in verdict.failures)


def test_gate_rejects_undeclared_scope():
    packets = _good_packets()
    packets[1]["requirements"]["scope_declared"] = False
    verdict = evaluate_graph_shape(packets=packets, plan_record_id="opr-x", attempt_count=0)
    assert not verdict.ok
    assert any("scope_declared_everywhere" in f for f in verdict.failures)


def test_gate_rejects_out_of_plan_task():
    packets = _good_packets()
    packets[2]["lineage"] = {"plan_record_id": "opr-other"}
    verdict = evaluate_graph_shape(packets=packets, plan_record_id="opr-x", attempt_count=0)
    assert not verdict.ok
    assert any("plan_binding" in f for f in verdict.failures)


def test_gate_rejects_duplicate_task_ids():
    packets = _good_packets()
    packets[1]["packet_id"] = "wp-a"
    verdict = evaluate_graph_shape(packets=packets, plan_record_id="opr-x", attempt_count=0)
    assert not verdict.ok
    assert any("unique_task_ids" in f for f in verdict.failures)


def test_gate_rejects_pre_existing_attempts():
    verdict = evaluate_graph_shape(
        packets=_good_packets(), plan_record_id="opr-x", attempt_count=1
    )
    assert not verdict.ok
    assert any("zero_attempts_pre_dispatch" in f for f in verdict.failures)


def test_gate_stops_the_campaign_rather_than_warning():
    verdict = evaluate_graph_shape(packets=[], plan_record_id="opr-x", attempt_count=0)
    assert not verdict.ok
    with pytest.raises(GraphShapeError) as exc:
        verdict.raise_if_failed()
    assert "zero quota spent" in str(exc.value)


def test_gate_is_read_only_over_its_inputs():
    packets = _good_packets()
    before = [dict(p) for p in packets]
    evaluate_graph_shape(packets=packets, plan_record_id="opr-x", attempt_count=0)
    assert packets == before


# ── D. resume must never widen a lane's authority ────────────────────────────


class _ResumeStore:
    """Minimal PlanningStore stand-in that returns ONE persisted plan."""

    def __init__(self, plan):
        self._plan = plan
        self.appended: list[object] = []

    def get_plan(self, plan_record_id):
        return self._plan if plan_record_id == self._plan.plan_record_id else None

    def append_grounding(self, record):
        self.appended.append(record)

    append_current_state = append_desired_state = append_gap_model = append_grounding
    append_plan = append_grounding

    def update_plan_cas(self, *args, **kwargs):
        return self._plan

    def update_session(self, session):
        self.appended.append(session)
        return session


class _GovernedResponse:
    """Shape the compiler expects back from a governed mutation."""

    def __init__(self, output):
        self.success = True
        self.output = output


def _governed_ok(*args, **kwargs):
    """Run the governed mutation's execute_fn inline and report success."""
    execute_fn = kwargs.get("execute_fn")
    output = ""
    if callable(execute_fn):
        result = execute_fn()
        output = result[0] if isinstance(result, tuple) else result
    return _GovernedResponse(output)


class _NoQueue:
    """Materialization sink — the resume branch is what is under test."""

    def __init__(self):
        self.ingested: list[object] = []

    def ingest_work_packet(self, packet):
        self.ingested.append(packet)

    def update_packet_status(self, *args, **kwargs):
        return None


def test_resume_reseeds_per_lane_not_from_the_flat_scope():
    """The zero-write verifier must stay zero-write across a REAL resume.

    Re-seeding every packet node from the single flat scope would silently
    grant the verifier write authority on every retry. This drives the actual
    ``compose_plan_for_session`` resume branch, not a reimplementation of it.
    """
    from substrate.execution.planning.compiler import compose_plan_for_session

    plan = _compile(_lanes())
    verifier_before = next(
        n
        for n in _packet_nodes(plan)
        if n["title"] == "Independently verify note search"
    )
    assert verifier_before["writable_path_scope"] == []

    session = PlanningSession(
        objective_id="goal-lane",
        objective_text=OBJECTIVE,
        conversation_id="conv-lane",
    )
    session.active_plan_record_id = plan.plan_record_id
    session.operation_stage = ""  # not committed → takes the RESUME branch

    resumed = compose_plan_for_session(
        session,
        WorkScope(tenant_id="t-lane", target_kind="self_build"),
        "task_objective",
        GroundingSnapshot(intent_id="int-lane"),
        _ResumeStore(plan),
        _NoQueue(),
        mutation_runner=_governed_ok,
        # The FLAT scope deliberately differs from the verifier's zero-write
        # lane: if resume re-seeded from it, the verifier would gain writes.
        writable_path_scope=list(INTEGRATION_SCOPE),
        lanes=_lanes(),
    )

    verifier_after = next(
        n
        for n in resumed.nodes
        if n["kind"] == "packet" and n["title"] == "Independently verify note search"
    )
    assert verifier_after["writable_path_scope"] == [], "resume widened the zero-write lane"
    assert verifier_after["scope_declared"] is True

    backend_after = next(
        n
        for n in resumed.nodes
        if n["kind"] == "packet" and n["title"] == "Backend search endpoint"
    )
    assert backend_after["writable_path_scope"] == BACKEND_SCOPE


# ── E. THE PRODUCTION PATH (the test that would have caught the unwired seam) ─
# Adversarial review of 2600641d0f62: every test above calls the compiler
# DIRECTLY, so all of them passed while no production caller ever supplied
# `lanes` — the field run still compiled one umbrella Task. These tests drive
# the real transport → protocol → compiler chain instead.

FIELD_LANES_JSON = json.dumps(
    [
        {
            "lane_key": "backend",
            "title": "Add the note-search backend endpoint",
            "writable_path_scope": BACKEND_SCOPE,
            "depends_on": [],
            "semantic_label": "backend_task_id",
        },
        {
            "lane_key": "frontend",
            "title": "Add the note-search frontend UI",
            "writable_path_scope": FRONTEND_SCOPE,
            "depends_on": [],
            "semantic_label": "frontend_task_id",
        },
        {
            "lane_key": "integration",
            "title": "Integrate and reconcile the search branches",
            "writable_path_scope": INTEGRATION_SCOPE,
            "depends_on": ["backend", "frontend"],
            "semantic_label": "integration_task_id",
        },
        {
            "lane_key": "verification",
            "title": "Independently verify note search",
            "writable_path_scope": [],
            "depends_on": ["integration"],
            "semantic_label": "verification_task_id",
        },
    ]
)


def test_transport_resolver_declares_four_lanes_from_env(monkeypatch):
    """The transport seam must actually hand lanes to the protocol."""
    from transports.api.objective_plan_routes import _declared_lanes

    monkeypatch.setenv("UMH_WORKSPACE_LANES", FIELD_LANES_JSON)
    lanes = _declared_lanes(None, OBJECTIVE)

    assert lanes is not None and len(lanes) == 4
    by_key = {lane.lane_key: lane for lane in lanes}
    assert by_key["backend"].writable_path_scope == BACKEND_SCOPE
    assert by_key["verification"].writable_path_scope == []
    assert by_key["integration"].depends_on == ["backend", "frontend"]


def test_transport_resolver_returns_none_when_undeclared(monkeypatch):
    from transports.api.objective_plan_routes import _declared_lanes

    monkeypatch.delenv("UMH_WORKSPACE_LANES", raising=False)
    assert _declared_lanes(None, OBJECTIVE) is None


@pytest.mark.parametrize("raw", ["not json", "{}", "[]", "[1, 2]", '"a string"'])
def test_transport_resolver_refuses_malformed_declaration(monkeypatch, raw):
    """Malformed → None (never a partial or invented decomposition)."""
    from transports.api.objective_plan_routes import _declared_lanes

    monkeypatch.setenv("UMH_WORKSPACE_LANES", raw)
    assert _declared_lanes(None, OBJECTIVE) is None


def test_protocol_forwards_declared_lanes_to_the_compiler(monkeypatch):
    """OperatorIntentProtocol must pass `lanes` through to compose_plan_for_session.

    This is the seam that was missing: the protocol had no lane parameter at
    all, so the declaration could never reach the compiler.
    """
    from substrate.execution.intent.protocol import OperatorIntentProtocol
    from substrate.execution.planning import compiler as compiler_module

    seen: dict[str, object] = {}

    class _Captured(RuntimeError):
        pass

    def _capture(**kwargs):
        seen.update(kwargs)
        raise _Captured()

    # protocol.py imports compose_plan_for_session INSIDE the function, so patch
    # it at its source module — patching the protocol module would silently
    # no-op and make this test vacuous.
    monkeypatch.setattr(compiler_module, "compose_plan_for_session", _capture)

    from substrate.contracts.work_context import PrincipalContext
    from substrate.execution.intent.protocol import ContextFrame

    proto = OperatorIntentProtocol(lane_resolver=lambda _scope, _text: _lanes())
    resolution = proto.resolve(
        OBJECTIVE,
        PrincipalContext(tenant_id="t-lane", principal_id="u", membership_id="m"),
        WorkScope(tenant_id="t-lane", target_kind="self_build"),
        ContextFrame(),
    )
    with pytest.raises(_Captured):
        proto.plan_objective(resolution, OBJECTIVE, "conv-lane", work_queue=_NoQueue())

    # The REAL call reached the compiler carrying the declared lanes.
    forwarded = seen.get("lanes")
    assert forwarded is not None, "plan_objective did not forward lanes to the compiler"
    assert [lane.lane_key for lane in forwarded] == [
        "backend",
        "frontend",
        "integration",
        "verification",
    ]


def test_protocol_lane_resolver_failure_does_not_crash_planning():
    """A broken resolver degrades to 'not decomposed', never an exception."""
    from substrate.execution.intent.protocol import OperatorIntentProtocol

    def _boom(_scope, _text):
        raise RuntimeError("resolver exploded")

    proto = OperatorIntentProtocol(lane_resolver=_boom)
    assert proto._resolve_lanes(None, OBJECTIVE) is None


def test_field_runner_arms_the_gate_when_lanes_are_declared(monkeypatch):
    """The gate must be ON for the multi-lane protocol — it was dark before."""
    monkeypatch.setenv("UMH_WORKSPACE_LANES", FIELD_LANES_JSON)
    assert bool(os.environ.get("UMH_WORKSPACE_LANES", "").strip()) is True
    monkeypatch.delenv("UMH_WORKSPACE_LANES", raising=False)
    assert bool(os.environ.get("UMH_WORKSPACE_LANES", "").strip()) is False


def test_harness_lane_declaration_matches_the_canonical_scope_map():
    """The harness must declare lanes from the ONE canonical map, not literals."""
    from substrate.execution.attempts.field_task_scope import (
        BACKEND,
        FIXTURE_ALLOWED_PATHS,
        FRONTEND,
        VERIFICATION,
    )

    assert FIXTURE_ALLOWED_PATHS[BACKEND] == BACKEND_SCOPE
    assert FIXTURE_ALLOWED_PATHS[FRONTEND] == FRONTEND_SCOPE
    assert FIXTURE_ALLOWED_PATHS[VERIFICATION] == []


# ── F. RESUME without lanes must not widen persisted authority ───────────────


def test_resume_without_lanes_never_widens_a_declared_node():
    """CRITICAL: with lanes=None the old code re-seeded EVERY node from the flat
    scope, silently granting the zero-write verifier write authority on the
    whole union — on every retry, with scope_declared still True."""
    from substrate.execution.planning.compiler import compose_plan_for_session

    plan = _compile(_lanes())
    session = PlanningSession(
        objective_id="goal-lane", objective_text=OBJECTIVE, conversation_id="conv-lane"
    )
    session.active_plan_record_id = plan.plan_record_id
    session.operation_stage = ""

    resumed = compose_plan_for_session(
        session,
        WorkScope(tenant_id="t-lane", target_kind="self_build"),
        "task_objective",
        GroundingSnapshot(intent_id="int-lane"),
        _ResumeStore(plan),
        _NoQueue(),
        mutation_runner=_governed_ok,
        writable_path_scope=list(INTEGRATION_SCOPE),
        lanes=None,  # the ONLY reachable production state before lane wiring
    )

    verifier = next(
        n
        for n in resumed.nodes
        if n["kind"] == "packet" and n["title"] == "Independently verify note search"
    )
    assert verifier["writable_path_scope"] == [], "resume widened the zero-write lane"

    backend = next(
        n
        for n in resumed.nodes
        if n["kind"] == "packet" and n["title"] == "Backend search endpoint"
    )
    assert backend["writable_path_scope"] == BACKEND_SCOPE, "resume widened an impl lane"


# ── G. remaining adversarial-review findings ────────────────────────────────


def test_gate_refuses_a_partially_evaluated_frontier():
    """MAJOR-5: skipping unresolvable Tasks let a 6-Task grant present exactly
    the required 4 and PASS while two unexamined Tasks dispatched."""
    verdict = evaluate_graph_shape(
        packets=_good_packets(),
        plan_record_id="opr-x",
        frontier_size=6,
        unresolvable_tasks=["wp-e", "wp-f"],
    )
    assert not verdict.ok
    assert any("frontier_fully_evaluated" in f for f in verdict.failures)


def test_gate_accepts_a_fully_evaluated_frontier():
    verdict = evaluate_graph_shape(
        packets=_good_packets(),
        plan_record_id="opr-x",
        frontier_size=4,
        unresolvable_tasks=[],
    )
    assert verdict.ok, verdict.failures


@pytest.mark.parametrize("bad", [".", "/etc", "../..", "app/../.."])
def test_gate_refuses_scopes_the_contract_would_reject(bad):
    """MINOR-8: the gate is the last proof before quota — it must not certify a
    scope the contract layer rejects (repo root, absolute, parent traversal)."""
    packets = _good_packets()
    packets[0]["requirements"]["writable_path_scope"] = [bad]
    verdict = evaluate_graph_shape(packets=packets, plan_record_id="opr-x")
    assert not verdict.ok
    assert any("scopes_pass_contract_validation" in f for f in verdict.failures)


def test_declared_lanes_exceeding_the_cap_fail_closed():
    """MAJOR-4: the generic cap silently deferred trailing lanes — a declared
    graph could lose its independent-verification lane and compile clean."""
    many = [
        ObjectiveLane(
            lane_key=f"l{i:02d}", title=f"L{i}", writable_path_scope=[f"app/f{i}.py"]
        )
        for i in range(13)
    ]
    with pytest.raises(PlanCompilationError) as exc:
        _compile(many)
    assert "cap" in str(exc.value)


def test_dispatch_refuses_a_task_with_undeclared_authority():
    """MAJOR-7: an undeclared Task silently regressed to the pre-fix prompt."""
    from types import SimpleNamespace

    from substrate.execution.attempts.dispatch import (
        DispatchBlocked,
        compile_attempt_package,
    )

    def _build(requirements):
        return compile_attempt_package(
            attempt=SimpleNamespace(
                attempt_id="ea-1", task_id="wp-test", attempt_number=1, plan_record_id="opr-1"
            ),
            packet=SimpleNamespace(
                packet_id="wp-test",
                title="Add note search",
                user_intent="Add a search endpoint.",
                desired_end_state="GET /api/notes/search?q= works.",
                constraints=[],
                validation_plan="pytest green",
                requirements=requirements,
            ),
            assignment=SimpleNamespace(
                role_contract_id="role-impl-op",
                tool_profile=["Edit", "Write"],
                model_profile={"model": "claude-opus"},
                environment_class="git_worktree",
            ),
            grant=SimpleNamespace(
                tenant_id="tenant-a",
                decision_ref="objective_plan:opr-1:execution_authorization:v1",
                authorized_scope_hash="h",
                risk_ceiling="high",
                task_frontier=["wp-test"],
                verification_obligations=["verify"],
            ),
        )

    # Declared → compiles and seals the scope.
    package = _build({"scope_declared": True, "writable_path_scope": ["app/main.py"]})
    assert any(
        str(c).startswith("writable_path_scope=")
        for c in getattr(package, "governance_constraints", [])
    )

    # Undeclared → refused, never silently dispatched with an unnamed scope.
    with pytest.raises(DispatchBlocked) as exc:
        _build({"scope_declared": False, "writable_path_scope": []})
    assert "undeclared mutation authority" in str(exc.value)


@pytest.mark.parametrize(
    "raw", ["writable_path_scope=1", 'writable_path_scope="app"', "writable_path_scope=None"]
)
def test_malformed_sealed_scope_never_crashes_or_mis_parses(raw):
    """MAJOR-6: literal_eval returned an int (TypeError on iteration) or a bare
    string (iterated character-by-character into one-character 'paths')."""
    from types import SimpleNamespace

    from substrate.execution.attempts.worker_claude_cli import render_prompt

    package = SimpleNamespace(
        role_instructions="",
        operation_instructions="Execute task wp-1.",
        operation_identity={"task_id": "wp-1"},
        ordered_context=[],
        governance_constraints=[raw],
    )
    prompt = render_prompt(package)
    assert "Execute task wp-1." in prompt
    assert "Writable Scope" not in prompt


# ── H. the lane DECLARATION boundary type-checks and least-privilege-checks ──
# Self-hunted after the review: _lane_gaps validated keys and dependency refs
# but not the scope's TYPE. A bare string is iterable, so "app/main.py" became
# ['a','p','p',...] — eleven VALID relative paths that pass every downstream
# check, yielding a Task whose declared authority is nonsense.


@pytest.mark.parametrize(
    "entries,reason",
    [
        ([{"lane_key": "a", "writable_path_scope": "app/main.py"}], "must be a list of paths"),
        (
            [
                {"lane_key": "a", "writable_path_scope": []},
                {"lane_key": "b", "writable_path_scope": [], "depends_on": "a"},
            ],
            "must be a list of lane keys",
        ),
        ([{"lane_key": "a", "writable_path_scope": ["/etc/passwd"]}], "invalid"),
        ([{"lane_key": "a", "writable_path_scope": ["../.."]}], "invalid"),
        ([{"lane_key": "a", "writable_path_scope": ["."]}], "invalid"),
    ],
)
def test_malformed_lane_scope_fails_closed_at_declaration(entries, reason):
    lanes = [ObjectiveLane.from_dict(e) for e in entries]
    with pytest.raises(PlanCompilationError) as exc:
        _compile(lanes)
    assert reason in str(exc.value)


def test_lane_scope_string_is_never_iterated_into_characters():
    """The specific silent-corruption case: valid-looking one-character paths."""
    lanes = [ObjectiveLane.from_dict({"lane_key": "a", "writable_path_scope": "app"})]
    with pytest.raises(PlanCompilationError):
        _compile(lanes)


def test_valid_declaration_still_compiles_after_the_type_check():
    nodes = _packet_nodes(_compile(_lanes()))
    assert len(nodes) == 4
