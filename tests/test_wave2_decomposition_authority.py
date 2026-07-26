"""Layer 11: ONE semantic owner of the executable decomposition per Plan version.

Field run 20260726T193442Z stopped at the pre-execution graph gate: the
fixture Objective compiled ELEVEN Tasks — the four DECLARED lanes plus seven
evidence-derived ``legacy_pending`` gaps materialized as siblings. Two
producers both claimed executable Task authority for one Plan version.

Worse, the same run also produced an accidentally-correct 4-node plan at
``program_objective`` scale: the frontier cap of 5 truncated the siblings
away. Right answer, wrong reason — a bounding cap decided the semantic
outcome. Selection must precede bounding, and a cap must never hide
executable Tasks.

The closure claim these tests pin:

    DECLARED DECOMPOSITION IS THE SOLE EXECUTABLE AUTHORITY FOR THAT PLAN
    VERSION; DERIVED GAPS REMAIN PRESERVED NON-EXECUTABLE PLANNING EVIDENCE
    OR DEFERRED WORK.
"""

from __future__ import annotations

import pytest

from substrate.contracts.work_context import WorkRequirements, WorkScope
from substrate.execution.attempts.graph_shape_gate import evaluate_graph_shape
from substrate.execution.planning.archetypes import resolve_archetype
from substrate.execution.planning.compiler import (
    PlanCompilationError,
    compile_plan,
    derive_state_records,
)
from substrate.execution.planning.records import (
    DecompositionMode,
    GroundingSnapshot,
    ObjectiveLane,
    PlanningSession,
)

OBJECTIVE = "Add note search: backend endpoint + frontend box, integrated and verified."

BACKEND_SCOPE = ["app/main.py", "app/store.py", "tests/test_search_api.py"]
FRONTEND_SCOPE = ["app/static", "tests/test_ui_search.py"]
INTEGRATION_SCOPE = [
    "app/main.py",
    "app/store.py",
    "app/static",
    "tests/test_search_api.py",
    "tests/test_ui_search.py",
]

# The exact seven the candidate's own grounding evidence produced in the field.
FIELD_LEGACY_PENDING = [
    "presence",
    "execution",
    "workstation_state",
    "profile",
    "audit",
    "runtime_surface",
    "self_build",
]


def _lanes() -> list[ObjectiveLane]:
    return [
        ObjectiveLane(
            lane_key="backend",
            title="Add the note-search backend endpoint",
            writable_path_scope=list(BACKEND_SCOPE),
            semantic_label="backend_task_id",
        ),
        ObjectiveLane(
            lane_key="frontend",
            title="Add the note-search frontend UI",
            writable_path_scope=list(FRONTEND_SCOPE),
            semantic_label="frontend_task_id",
        ),
        ObjectiveLane(
            lane_key="integration",
            title="Integrate and reconcile the search branches",
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


def _snapshot(legacy: list[str] | None = None) -> GroundingSnapshot:
    snapshot = GroundingSnapshot(intent_id="int-l11")
    if legacy:
        snapshot.sources = [
            {
                "source": "runtime-probe",
                "status": "ok",
                "summary": "runtime-state boundary probe",
                "evidence": {"legacy_pending": list(legacy)},
            }
        ]
    return snapshot


def _derive(lanes, legacy=None, scale="task_objective"):
    scope = WorkScope(tenant_id="t-l11", target_kind="self_build")
    snapshot = _snapshot(legacy)
    current, desired, gaps = derive_state_records(
        OBJECTIVE,
        snapshot,
        tenant_id="t-l11",
        scope=scope,
        writable_path_scope=["app"],
        lanes=lanes,
    )
    return scope, snapshot, current, desired, gaps, scale


def _compile(lanes, legacy=None, scale="task_objective"):
    scope, snapshot, current, desired, gaps, scale = _derive(lanes, legacy, scale)
    session = PlanningSession(
        objective_id="goal-l11", objective_text=OBJECTIVE, conversation_id="conv-l11"
    )
    plan = compile_plan(
        session,
        scope,
        scale,
        current,
        desired,
        gaps,
        snapshot.grounding_snapshot_id,
        resolve_archetype(OBJECTIVE, scope),
    )
    return plan, gaps


def _packets(plan) -> list[dict]:
    return [n for n in plan.nodes if n["kind"] == "packet"]


def _by_lane(plan) -> dict[str, dict]:
    return {
        n["gap_id"].replace("gap-lane-", ""): n
        for n in _packets(plan)
        if n["gap_id"].startswith("gap-lane-")
    }


# ── A. declared exclusive: seven evidence gaps → still exactly four Tasks ────


def test_declared_exclusive_produces_exactly_four_packets():
    plan, _ = _compile(_lanes(), legacy=FIELD_LEGACY_PENDING)
    assert len(_packets(plan)) == 4


@pytest.mark.parametrize("scale", ["task_objective", "program_objective"])
def test_exactly_four_at_every_scale_not_by_cap_accident(scale):
    """The field run got 4 at program_objective ONLY because the frontier cap
    of 5 truncated the siblings. Selection must decide it, not the cap."""
    plan, gaps = _compile(_lanes(), legacy=FIELD_LEGACY_PENDING, scale=scale)
    assert len(_packets(plan)) == 4
    assert gaps.decomposition_mode == DecompositionMode.DECLARED_EXCLUSIVE.value
    assert not (plan.decomposition.get("deferred_child_objectives") or [])


# ── B. exact dependency graph ────────────────────────────────────────────────


def test_exact_dependency_graph():
    plan, _ = _compile(_lanes(), legacy=FIELD_LEGACY_PENDING)
    lane = _by_lane(plan)
    ids = {k: v["node_id"] for k, v in lane.items()}
    assert lane["backend"]["depends_on"] == []
    assert lane["frontend"]["depends_on"] == []
    assert set(lane["integration"]["depends_on"]) == {ids["backend"], ids["frontend"]}
    assert lane["verification"]["depends_on"] == [ids["integration"]]


# ── C. exactly two initially runnable implementation Tasks ───────────────────


def test_exactly_two_initially_runnable_tasks():
    plan, _ = _compile(_lanes(), legacy=FIELD_LEGACY_PENDING)
    roots = [n for n in _packets(plan) if not n["depends_on"]]
    assert len(roots) == 2
    assert {n["gap_id"] for n in roots} == {"gap-lane-backend", "gap-lane-frontend"}


# ── D. the verifier has declared zero-write authority ────────────────────────


def test_verifier_has_zero_write_authority():
    plan, _ = _compile(_lanes(), legacy=FIELD_LEGACY_PENDING)
    verifier = _by_lane(plan)["verification"]
    assert verifier["writable_path_scope"] == []
    assert verifier["scope_declared"] is True


# ── E. evidence preserved, zero sibling Tasks ────────────────────────────────


def test_evidence_gaps_preserved_but_create_zero_sibling_tasks():
    plan, gaps = _compile(_lanes(), legacy=FIELD_LEGACY_PENDING)
    siblings = [n for n in _packets(plan) if not n["gap_id"].startswith("gap-lane-")]
    assert siblings == [], "evidence-derived gaps must create ZERO Tasks"
    preserved = {g["gap_key"] for g in gaps.derived_evidence_gaps}
    assert preserved == {f"gap-{n}" for n in FIELD_LEGACY_PENDING}
    assert any("preserved as" in a for a in gaps.assumptions)


def test_evidence_information_is_never_silently_deleted():
    _, gaps = _compile(_lanes(), legacy=FIELD_LEGACY_PENDING)
    for entry in gaps.derived_evidence_gaps:
        assert entry.get("title")
        assert entry.get("evidence_ref")


# ── F. removing exclusivity reproduces the 11-Task field shape ───────────────


def test_additive_selection_would_produce_eleven_tasks():
    """Pins the DEFECT shape: if selection went back to extend-not-replace, the
    field graph is 11 Tasks and the pre-execution gate refuses it."""
    _, _, _, _, gaps, _ = _derive(_lanes(), legacy=FIELD_LEGACY_PENDING)
    additive = list(gaps.derived_evidence_gaps) + list(gaps.gaps)
    assert len(additive) == 11
    packets = [
        {
            "packet_id": f"wp-{i:02d}",
            "dependencies": [],
            "lineage": {"plan_record_id": "opr-x"},
            "requirements": {"scope_declared": True, "writable_path_scope": ["app"]},
        }
        for i, _ in enumerate(additive)
    ]
    verdict = evaluate_graph_shape(packets=packets, plan_record_id="opr-x")
    assert not verdict.ok
    assert any("task_count" in f for f in verdict.failures)


# ── G. evidence ordering is irrelevant ───────────────────────────────────────


def test_evidence_reordering_changes_nothing():
    plan_a, _ = _compile(_lanes(), legacy=FIELD_LEGACY_PENDING)
    plan_b, _ = _compile(_lanes(), legacy=list(reversed(FIELD_LEGACY_PENDING)))

    def shape(plan):
        lane = _by_lane(plan)
        return {
            k: (
                len(v["depends_on"]),
                tuple(v["writable_path_scope"]),
                v["scope_declared"],
                v.get("semantic_label"),
            )
            for k, v in lane.items()
        }

    assert shape(plan_a) == shape(plan_b)
    assert len(_packets(plan_a)) == len(_packets(plan_b)) == 4
    # ABSOLUTE assertions: comparing two runs of the same compiler cannot catch
    # a deterministic defect that mutates both sides identically.
    assert shape(plan_a)["backend"] == (0, tuple(BACKEND_SCOPE), True, "backend_task_id")
    assert shape(plan_a)["frontend"] == (0, tuple(FRONTEND_SCOPE), True, "frontend_task_id")
    assert shape(plan_a)["integration"] == (2, tuple(INTEGRATION_SCOPE), True, "integration_task_id")
    assert shape(plan_a)["verification"] == (1, (), True, "verification_task_id")


# ── J. non-declared objectives keep the existing behavior ────────────────────


def test_derived_path_unchanged_without_a_declaration():
    plan, gaps = _compile(None, legacy=FIELD_LEGACY_PENDING)
    assert gaps.decomposition_mode == DecompositionMode.DERIVED.value
    assert len(_packets(plan)) == 7


def test_derived_path_still_caps_and_defers():
    plan, gaps = _compile(None, legacy=[f"sub{i}" for i in range(20)])
    assert gaps.decomposition_mode == DecompositionMode.DERIVED.value
    assert len(_packets(plan)) == 12
    assert len(plan.decomposition["deferred_child_objectives"]) == 8


def test_umbrella_fallback_when_nothing_actionable():
    plan, gaps = _compile(None, legacy=None)
    assert gaps.decomposition_mode == DecompositionMode.UMBRELLA_FALLBACK.value
    assert len(_packets(plan)) == 1


# ── M. the pre-execution graph validator accepts/refuses the right shapes ────


def _packet(pid, deps, scope, declared=True):
    requirements = WorkRequirements()
    requirements.declare_writable_paths(scope)
    row = requirements.to_dict()
    row["scope_declared"] = declared
    return {
        "packet_id": pid,
        "dependencies": deps,
        "lineage": {"plan_record_id": "opr-x"},
        "requirements": row,
    }


def _good():
    return [
        _packet("A", [], ["app/main.py"]),
        _packet("B", [], ["app/static"]),
        _packet("C", ["A", "B"], ["app"]),
        _packet("D", ["C"], []),
    ]


def test_gate_accepts_the_four_node_shape():
    verdict = evaluate_graph_shape(
        packets=_good(), plan_record_id="opr-x", frontier_size=4, unresolvable_tasks=[]
    )
    assert verdict.ok, verdict.failures


@pytest.mark.parametrize(
    "mutate,expect",
    [
        (lambda p: p + [_packet(f"X{i}", [], ["app"]) for i in range(7)], "task_count"),
        (lambda p: p[:3], "task_count"),
        (lambda p: p[:3] + [_packet("E", [], ["app/other"])], "fan_in"),
        (lambda p: p + [_packet("E", [], ["app/other"])], "task_count"),
        (lambda p: p[:2] + [_packet("C", ["A"], ["app"]), p[3]], "fan_in"),
        (
            lambda p: [_packet("A", [], ["app/main.py"], declared=False)] + p[1:],
            "scope_declared_everywhere",
        ),
        (lambda p: p[:3] + [_packet("D", ["C"], ["app/main.py"])], "verifier_zero_write"),
    ],
    ids=[
        "eleven-node-additive",
        "missing-lane",
        "duplicate-independent-lane",
        "extra-implementation-task",
        "wrong-fan-in",
        "undeclared-scope",
        "nonzero-verifier-scope",
    ],
)
def test_gate_rejects_wrong_shapes(mutate, expect):
    verdict = evaluate_graph_shape(packets=mutate(_good()), plan_record_id="opr-x")
    assert not verdict.ok
    assert any(expect in f for f in verdict.failures), verdict.failures


# ── N-adjacent: selection must never be title/regex guessed ──────────────────


def test_selection_is_declaration_driven_not_title_matched():
    """Lanes titled exactly like the evidence gaps still win by DECLARATION."""
    disguised = [
        ObjectiveLane(
            lane_key="backend",
            title="Migrate subsystem 'presence' to the runtime-state boundary",
            writable_path_scope=list(BACKEND_SCOPE),
        ),
        ObjectiveLane(
            lane_key="frontend",
            title="Migrate subsystem 'audit' to the runtime-state boundary",
            writable_path_scope=list(FRONTEND_SCOPE),
        ),
    ]
    plan, gaps = _compile(disguised, legacy=FIELD_LEGACY_PENDING)
    assert gaps.decomposition_mode == DecompositionMode.DECLARED_EXCLUSIVE.value
    assert len(_packets(plan)) == 2
    assert {n["gap_id"] for n in _packets(plan)} == {"gap-lane-backend", "gap-lane-frontend"}


def test_declared_lanes_exceeding_cap_fail_closed_never_truncated():
    many = [
        ObjectiveLane(lane_key=f"l{i:02d}", title=f"L{i}", writable_path_scope=[f"app/f{i}.py"])
        for i in range(13)
    ]
    with pytest.raises(PlanCompilationError) as exc:
        _compile(many, legacy=FIELD_LEGACY_PENDING)
    assert "13 lane(s)" in str(exc.value)


# ── L/H/I/K: durable reread, idempotency, revision, tenant isolation ─────────
# Every assertion below reads from FRESH store instances, never from a compiler
# return value or an in-memory fixture — validating only in-memory output is one
# of the mutations this suite must catch.

import json as _json
import os as _os


def _fresh_stores(tmp_path):
    """New PlanningStore + UniversalWorkQueue bound to the same durable files."""
    from substrate.execution.planning.store import PlanningStore
    from substrate.organism.universal_work_queue import UniversalWorkQueue

    return (
        PlanningStore(
            sessions_path=str(tmp_path / "sessions.jsonl"),
            plans_path=str(tmp_path / "plans.jsonl"),
            grounding_path=str(tmp_path / "grounding.jsonl"),
            current_path=str(tmp_path / "current.jsonl"),
            desired_path=str(tmp_path / "desired.jsonl"),
            gaps_path=str(tmp_path / "gaps.jsonl"),
        ),
        UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl")),
    )


def _compose(tmp_path, lanes, legacy=FIELD_LEGACY_PENDING, tenant="t-l11", objective=OBJECTIVE):
    """Drive the REAL compose_plan_for_session against durable stores."""
    from substrate.execution.planning.compiler import compose_plan_for_session

    store, queue = _fresh_stores(tmp_path)
    scope = WorkScope(tenant_id=tenant, target_kind="self_build")
    session = PlanningSession(
        objective_id=f"goal-{tenant}", objective_text=objective, conversation_id=f"conv-{tenant}"
    )

    class _Resp:
        def __init__(self, output):
            self.success = True
            self.output = output

    def _runner(**kw):
        fn = kw.get("execute_fn")
        out = ""
        if callable(fn):
            r = fn()
            out = r[0] if isinstance(r, tuple) else r
        return _Resp(out)

    plan = compose_plan_for_session(
        session=session,
        scope=scope,
        planning_scale="task_objective",
        snapshot=_snapshot(legacy),
        store=store,
        work_queue=queue,
        mutation_runner=_runner,
        writable_path_scope=["app"],
        lanes=lanes,
    )
    return plan, session


def _reread_packets(tmp_path, plan_record_id):
    """Re-read the PERSISTED packets from a brand-new queue instance."""
    from substrate.organism.universal_work_queue import UniversalWorkQueue

    queue = UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))
    out = []
    for packet in queue.all_packets():
        lineage = getattr(packet, "lineage", {}) or {}
        if (lineage.get("plan_record_id") or "") == plan_record_id:
            out.append(packet)
    return out


def test_durable_reread_shows_exactly_four_packets(tmp_path):
    plan, _ = _compose(tmp_path, _lanes())
    packets = _reread_packets(tmp_path, plan.plan_record_id)
    assert len(packets) == 4, [getattr(p, "title", "") for p in packets]


def test_durable_reread_dependencies_and_scopes(tmp_path):
    plan, _ = _compose(tmp_path, _lanes())
    packets = {getattr(p, "title", ""): p for p in _reread_packets(tmp_path, plan.plan_record_id)}
    by_id = {p.packet_id: t for t, p in packets.items()}

    backend = packets["Add the note-search backend endpoint"]
    frontend = packets["Add the note-search frontend UI"]
    integration = packets["Integrate and reconcile the search branches"]
    verification = packets["Independently verify note search"]

    assert list(backend.dependencies) == []
    assert list(frontend.dependencies) == []
    assert {by_id[d] for d in integration.dependencies} == {
        "Add the note-search backend endpoint",
        "Add the note-search frontend UI",
    }
    assert [by_id[d] for d in verification.dependencies] == [
        "Integrate and reconcile the search branches"
    ]

    def scope(packet):
        req = packet.requirements
        req = req if isinstance(req, dict) else req.to_dict()
        return req.get("writable_path_scope"), req.get("scope_declared")

    assert scope(backend) == (BACKEND_SCOPE, True)
    assert scope(frontend) == (FRONTEND_SCOPE, True)
    assert scope(verification) == ([], True)


def test_durable_reread_no_evidence_sibling_packets(tmp_path):
    plan, _ = _compose(tmp_path, _lanes())
    titles = [getattr(p, "title", "") for p in _reread_packets(tmp_path, plan.plan_record_id)]
    assert not [t for t in titles if "Migrate subsystem" in t]


def test_recompiling_the_same_plan_version_does_not_duplicate(tmp_path):
    """H: repeated compilation is idempotent — never 4 + legacy siblings, never
    duplicate current-truth packets."""
    plan, session = _compose(tmp_path, _lanes())
    first = {p.packet_id for p in _reread_packets(tmp_path, plan.plan_record_id)}
    assert len(first) == 4

    from substrate.execution.planning.compiler import compose_plan_for_session

    store, queue = _fresh_stores(tmp_path)

    class _Resp:
        def __init__(self, output):
            self.success = True
            self.output = output

    def _runner(**kw):
        fn = kw.get("execute_fn")
        out = ""
        if callable(fn):
            r = fn()
            out = r[0] if isinstance(r, tuple) else r
        return _Resp(out)

    again = compose_plan_for_session(
        session=session,
        scope=WorkScope(tenant_id="t-l11", target_kind="self_build"),
        planning_scale="task_objective",
        snapshot=_snapshot(FIELD_LEGACY_PENDING),
        store=store,
        work_queue=queue,
        mutation_runner=_runner,
        writable_path_scope=["app"],
        lanes=_lanes(),
    )
    second = {p.packet_id for p in _reread_packets(tmp_path, again.plan_record_id)}
    assert second == first, "recompilation duplicated or re-minted packets"
    assert len(second) == 4


def test_cross_tenant_tasks_are_not_aliased_in_one_shared_store(tmp_path):
    """K: two tenants, ONE shared store, IDENTICAL objective text.

    The previous version of this test used two separate tmp dirs, so its
    assertions were guaranteed by uuid4 and filesystem separation — it
    exercised zero isolation logic. Dedupe keyed on user_intent alone aliased
    Tasks across tenants: the second tenant's plan durably recorded packet ids
    owned by the first, making its objective permanently undispatchable.
    """
    plan_a, _ = _compose(tmp_path, _lanes(), tenant="tenant-a")
    plan_b, _ = _compose(tmp_path, _lanes(), tenant="tenant-b")

    ids_a = {p.packet_id for p in _reread_packets(tmp_path, plan_a.plan_record_id)}
    ids_b = {p.packet_id for p in _reread_packets(tmp_path, plan_b.plan_record_id)}

    assert len(ids_a) == 4, "tenant-a lost packets to aliasing"
    assert len(ids_b) == 4, "tenant-b lost packets to aliasing"
    assert not (ids_a & ids_b), "packets aliased ACROSS TENANTS"

    # Every id a plan claims must actually resolve in the store.
    from substrate.organism.universal_work_queue import UniversalWorkQueue

    queue = UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))
    stored = {p.packet_id for p in queue.all_packets()}
    for plan in (plan_a, plan_b):
        claimed = set(plan.workpacket_ids)
        assert claimed and claimed <= stored, f"plan claims phantom packet ids: {claimed - stored}"

    # Each stored packet belongs to exactly the tenant that declared it.
    by_id = {p.packet_id: p for p in queue.all_packets()}
    for pid in ids_a:
        assert (by_id[pid].work_scope or {}).get("tenant_id") == "tenant-a"
    for pid in ids_b:
        assert (by_id[pid].work_scope or {}).get("tenant_id") == "tenant-b"


def test_plan_record_persists_the_selected_mode(tmp_path):
    """The selection must be auditable from durable state, not inferred."""
    plan, _ = _compose(tmp_path, _lanes())
    rows = [
        _json.loads(line)
        for line in open(tmp_path / "gaps.jsonl", encoding="utf-8")
        if line.strip()
    ]
    assert rows, "gap model was not persisted"
    latest = rows[-1]
    assert latest.get("decomposition_mode") == DecompositionMode.DECLARED_EXCLUSIVE.value
    preserved = {g["gap_key"] for g in latest.get("derived_evidence_gaps") or []}
    assert preserved == {f"gap-{n}" for n in FIELD_LEGACY_PENDING}
    assert _os.path.exists(tmp_path / "plans.jsonl")


def test_a_second_producer_re_entering_the_executable_set_fails_closed():
    """The exclusivity invariant is ENFORCED at compile, not merely produced.

    Selection replaces the gap set, but nothing structurally prevents a future
    edit from re-adding evidence gaps between selection and materialization.
    compile_plan asserts the invariant, so such a regression fails closed
    instead of silently compiling an additive graph again.
    """
    scope, snapshot, current, desired, gaps, scale = _derive(
        _lanes(), legacy=FIELD_LEGACY_PENDING
    )
    assert gaps.decomposition_mode == DecompositionMode.DECLARED_EXCLUSIVE.value

    # Simulate a second producer re-entering AFTER selection.
    gaps.gaps = list(gaps.gaps) + list(gaps.derived_evidence_gaps)

    session = PlanningSession(
        objective_id="goal-l11", objective_text=OBJECTIVE, conversation_id="conv-l11"
    )
    with pytest.raises(PlanCompilationError) as exc:
        compile_plan(
            session,
            scope,
            scale,
            current,
            desired,
            gaps,
            snapshot.grounding_snapshot_id,
            resolve_archetype(OBJECTIVE, scope),
        )
    message = str(exc.value)
    assert "exclusive" in message
    assert "gap-presence" in message


# ── Review findings: a plan VERSION is also minted by compile_revision ───────
# The closure claim is "sole executable authority FOR THAT PLAN VERSION".
# compile_revision mints v(n+1) of the same objective and originally performed
# none of the layer-11 checks — a second unguarded producer, the exact defect
# shape of the prior layers.


def _revision(plan, edits, tmp_path):
    from substrate.execution.planning.compiler import compile_revision
    from substrate.execution.planning.records import RevisionEditSet

    store, _ = _fresh_stores(tmp_path)

    class _Resp:
        def __init__(self, output):
            self.success = True
            self.output = output

    def _runner(**kw):
        fn = kw.get("execute_fn")
        out = ""
        if callable(fn):
            r = fn()
            out = r[0] if isinstance(r, tuple) else r
        return _Resp(out)

    return compile_revision(plan, RevisionEditSet(edits=edits), store, _runner)


def test_plan_version_records_the_decomposition_mode(tmp_path):
    """The mode must live on the PLAN, not only on a transient gap snapshot —
    compile_revision never loads a gap snapshot."""
    plan, _ = _compose(tmp_path, _lanes())
    assert plan.decomposition_mode == DecompositionMode.DECLARED_EXCLUSIVE.value

    from substrate.execution.planning.store import PlanningStore

    store = PlanningStore(
        sessions_path=str(tmp_path / "sessions.jsonl"),
        plans_path=str(tmp_path / "plans.jsonl"),
        grounding_path=str(tmp_path / "grounding.jsonl"),
        current_path=str(tmp_path / "current.jsonl"),
        desired_path=str(tmp_path / "desired.jsonl"),
        gaps_path=str(tmp_path / "gaps.jsonl"),
    )
    reread = store.get_plan(plan.plan_record_id)
    assert reread is not None
    assert reread.decomposition_mode == DecompositionMode.DECLARED_EXCLUSIVE.value


def test_revision_cannot_add_an_executable_task_to_a_declared_plan(tmp_path):
    """CRITICAL: add_node minted a 5th executable packet node with no lane, no
    scope, and no exclusivity check."""
    plan, _ = _compose(tmp_path, _lanes())
    with pytest.raises(PlanCompilationError) as exc:
        _revision(plan, [{"op": "add_node", "title": "INJECTED sibling"}], tmp_path)
    assert "DECLARED_EXCLUSIVE" in str(exc.value)


def test_revision_cannot_delete_the_zero_write_verification_lane(tmp_path):
    """CRITICAL: one chat sentence deleted the independent-verification lane —
    the lane whose whole purpose is that it cannot be weakened — and the plan
    compiled clean with three Tasks."""
    plan, _ = _compose(tmp_path, _lanes())
    verifier = next(
        n for n in plan.nodes if n.get("gap_id") == "gap-lane-verification"
    )
    with pytest.raises(PlanCompilationError) as exc:
        _revision(plan, [{"op": "remove_node", "node_id": verifier["node_id"]}], tmp_path)
    assert "atomic" in str(exc.value)


def test_removing_a_node_never_silently_unblocks_its_dependents(tmp_path):
    """CRITICAL: remove_node cleaned edges but left a stale depends_on, so the
    integration Task declared to fan in on A AND B materialized with ONE
    dependency and the scheduler admitted it once B alone succeeded."""
    from substrate.execution.planning.records import ObjectivePlanRecord

    plan, _ = _compose(tmp_path, _lanes())
    # A DERIVED plan (no exclusivity guard) still must not orphan a dependent.
    derived = ObjectivePlanRecord.from_dict(plan.to_dict())
    derived.decomposition_mode = DecompositionMode.DERIVED.value
    backend = next(n for n in derived.nodes if n.get("gap_id") == "gap-lane-backend")

    with pytest.raises(PlanCompilationError) as exc:
        _revision(derived, [{"op": "remove_node", "node_id": backend["node_id"]}], tmp_path)
    assert "silently unblock" in str(exc.value)


def test_resume_refuses_to_seed_authority_onto_a_node_minted_outside_compilation(
    tmp_path,
):
    """CRITICAL: a revision-added node (no gap_id, scope_declared=False) fell
    through the lane guard on resume and was granted the caller's FULL flat
    scope — becoming a 5th executable Task with undeclared write access."""
    from substrate.execution.planning.compiler import compose_plan_for_session
    from substrate.execution.planning.records import ObjectivePlanNode

    from substrate.execution.planning.records import ObjectivePlanRecord

    plan, session = _compose(tmp_path, _lanes())
    sneaky = ObjectivePlanNode(kind="packet", title="Sneaky", lane="development")
    assert sneaky.gap_id == "" and sneaky.scope_declared is False

    # Mint a NEW version carrying the extra node — this is the shape a
    # revision leaves behind (append_plan will not overwrite an existing id).
    revised = ObjectivePlanRecord.from_dict(plan.to_dict())
    revised.plan_record_id = ObjectivePlanRecord().plan_record_id
    revised.nodes = list(plan.nodes) + [sneaky.to_dict()]

    store, queue = _fresh_stores(tmp_path)
    store.append_plan(revised)
    session.active_plan_record_id = revised.plan_record_id
    # A COMMITTED session returns its plan unchanged; the resume branch is the
    # partial-failure recovery path, which runs at an earlier stage.
    session.operation_stage = ""
    session.stage = "compiled"

    class _Resp:
        def __init__(self, output):
            self.success = True
            self.output = output

    def _runner(**kw):
        fn = kw.get("execute_fn")
        out = ""
        if callable(fn):
            r = fn()
            out = r[0] if isinstance(r, tuple) else r
        return _Resp(out)

    with pytest.raises(PlanCompilationError) as exc:
        compose_plan_for_session(
            session=session,
            scope=WorkScope(tenant_id="t-l11", target_kind="self_build"),
            planning_scale="task_objective",
            snapshot=_snapshot(FIELD_LEGACY_PENDING),
            store=store,
            work_queue=queue,
            mutation_runner=_runner,
            writable_path_scope=["app", "secrets"],
            lanes=_lanes(),
        )
    assert "minted outside compilation" in str(exc.value)


def test_cross_projection_gaps_are_preserved_not_executable(tmp_path):
    """HIGH: a declared plan with 2+ projection targets must still yield only
    the declared lanes; the cross-projection gaps are preserved evidence."""
    scope = WorkScope(tenant_id="t-l11", target_kind="self_build")
    scope.projection_ids = ["eos", "creatoros"]
    snapshot = _snapshot(FIELD_LEGACY_PENDING)
    _, _, gaps = derive_state_records(
        OBJECTIVE,
        snapshot,
        tenant_id="t-l11",
        scope=scope,
        writable_path_scope=["app"],
        lanes=_lanes(),
    )
    assert gaps.decomposition_mode == DecompositionMode.DECLARED_EXCLUSIVE.value
    assert [g["gap_key"] for g in gaps.gaps] == [
        "gap-lane-backend",
        "gap-lane-frontend",
        "gap-lane-integration",
        "gap-lane-verification",
    ]
    preserved = {g["gap_key"] for g in gaps.derived_evidence_gaps}
    assert "gap-substrate-contract" in preserved
    assert "gap-projection-eos" in preserved


def test_preserved_evidence_is_not_an_alias_of_the_executable_set():
    """LOW: the defensive copy is load-bearing — if the executable set were
    ever mutated in place, preservation would silently alias it."""
    _, _, _, _, gaps, _ = _derive(_lanes(), legacy=FIELD_LEGACY_PENDING)
    assert gaps.derived_evidence_gaps is not gaps.gaps
    assert not ({g["gap_key"] for g in gaps.gaps} & {g["gap_key"] for g in gaps.derived_evidence_gaps})
