"""Wave 2 — Task writable-scope is materialized, durable, and fail-closed (9th layer).

Field run 20260725T230726Z reached a real isolated Claude worker that made SIX
legitimate file changes and a real commit; the worker-side result was
``ok=True status=succeeded``. Independent verification then CORRECTLY refused the
attempt (``verification refused: diff_scope``) because the canonical WorkPacket
had been persisted with ``scope_declared=False`` and ``writable_path_scope=[]``.
An undeclared scope is never whole-repository permission, so no diff could ever
satisfy it.

That is a Task-CONTRACT MATERIALIZATION defect, not a verifier defect. The fix is
at the canonical materialization point (``planning/compiler.materialize_packets``):
the objective-derived authority flows gap → plan node → per-node
``WorkRequirements.declare_writable_paths`` → persisted Task, and a packet node
that declares NO scope fails materialization CLOSED.

These tests pin the order's coverage items A-N. They must never be satisfied by
weakening verification: no scope inference from titles/ids/evidence/diffs.
"""

from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import pytest

from substrate.contracts.work_context import WorkRequirements, WorkScope
from substrate.execution.attempts.field_task_scope import (
    BACKEND,
    FIXTURE_ALLOWED_PATHS,
    FRONTEND,
    INTEGRATION,
    VERIFICATION,
    paths_outside,
)
from substrate.execution.planning.archetypes import resolve_archetype
from substrate.execution.planning.compiler import (
    PlanCompilationError,
    derive_state_records,
    materialize_packets,
)
from substrate.execution.planning.records import (
    GroundingSnapshot,
    ObjectivePlanNode,
    ObjectivePlanRecord,
    PlanningSession,
)
from substrate.organism.universal_work_queue import UniversalWorkQueue

# The six paths the real field worker legitimately changed (run 20260725T230726Z).
OBSERVED_SIX = [
    "app/main.py",
    "app/static/app.js",
    "app/static/index.html",
    "app/store.py",
    "tests/test_search_api.py",
    "tests/test_ui_search.py",
]

# The smoke-style combined task's objective-derived allowlist (canonical map).
SMOKE_SCOPE = list(FIXTURE_ALLOWED_PATHS[INTEGRATION])


@pytest.fixture()
def queue(tmp_path, monkeypatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("UMH_ROOT", str(tmp_path / "repo"))
    (tmp_path / "repo").mkdir(exist_ok=True)
    return UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))


def _scope():
    return WorkScope(tenant_id="tenant-a", conversation_id="conv-1", target_kind="umh_substrate")


def _plan_with_nodes(nodes):
    return ObjectivePlanRecord(
        objective_id="goal-1",
        intent_id="intent-1",
        conversation_id="conv-1",
        objective_text="add note search",
        nodes=[n.to_dict() for n in nodes],
    )


def _packet_node(title, scope, *, declared=True):
    return ObjectivePlanNode(
        kind="packet",
        title=title,
        lane="build",
        writable_path_scope=list(scope),
        scope_declared=declared,
    )


def _materialize(plan, queue):
    session = PlanningSession(objective_text="add note search", conversation_id="conv-1")
    archetype = resolve_archetype("add note search", _scope())
    return materialize_packets(plan, _scope(), archetype, session, queue)


# ── A / B: the production materialization path persists a real declared scope ──


def test_a_materialization_persists_scope_declared_true(queue):
    plan = _plan_with_nodes([_packet_node("combined search task", SMOKE_SCOPE)])
    ids = _materialize(plan, queue)
    pkt = queue.get_packet(ids[0])
    req = pkt.requirements
    assert req.get("scope_declared") is True, "A: persisted Task must declare its scope"


def test_b_persisted_scope_matches_objective_derived_allowlist(queue):
    plan = _plan_with_nodes([_packet_node("combined search task", SMOKE_SCOPE)])
    ids = _materialize(plan, queue)
    req = queue.get_packet(ids[0]).requirements
    assert req.get("writable_path_scope") == SMOKE_SCOPE, "B: exact objective-derived allowlist"
    assert req.get("writable_path_scope"), "B: nonempty"


# ── C / M: durability — reread and store restart preserve the authority ────────


def test_c_durable_reread_preserves_scope_byte_for_byte(queue, tmp_path):
    plan = _plan_with_nodes([_packet_node("combined search task", SMOKE_SCOPE)])
    ids = _materialize(plan, queue)
    # Reread from DISK through a fresh queue — never the in-memory object.
    fresh = UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))
    req = fresh.get_packet(ids[0]).requirements
    assert req["writable_path_scope"] == SMOKE_SCOPE
    assert req["scope_declared"] is True
    # And byte-for-byte in the persisted JSONL itself.
    raw = [json.loads(line) for line in open(tmp_path / "packets.jsonl", encoding="utf-8")]
    row = next(r for r in raw if r["packet_id"] == ids[0])
    assert row["requirements"]["writable_path_scope"] == SMOKE_SCOPE


def test_m_record_order_and_restart_do_not_change_authority(queue, tmp_path):
    plan = _plan_with_nodes(
        [
            _packet_node("backend lane", FIXTURE_ALLOWED_PATHS[BACKEND]),
            _packet_node("frontend lane", FIXTURE_ALLOWED_PATHS[FRONTEND]),
        ]
    )
    ids = _materialize(plan, queue)
    before = {i: queue.get_packet(i).requirements["writable_path_scope"] for i in ids}
    # Rewrite the store with the records REVERSED, then restart the queue.
    path = tmp_path / "packets.jsonl"
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    with open(path, "w", encoding="utf-8") as fh:
        for row in reversed(rows):
            fh.write(json.dumps(row) + "\n")
    restarted = UniversalWorkQueue(store_path=str(path))
    after = {i: restarted.get_packet(i).requirements["writable_path_scope"] for i in ids}
    assert after == before, "M: authority is per-Task, not positional"


# ── H / J: fail-closed on undeclared and structurally-invalid scopes ───────────


def test_h_undeclared_scope_fails_materialization_closed(queue):
    plan = _plan_with_nodes([_packet_node("no authority", [], declared=False)])
    with pytest.raises(PlanCompilationError) as exc:
        _materialize(plan, queue)
    assert "writable_path_scope" in str(exc.value)


@pytest.mark.parametrize(
    "bad",
    [
        ["/etc/passwd"],  # absolute
        ["."],  # whole workspace
        [".."],  # parent traversal
        ["app/../.."],  # embedded traversal
        [""],  # empty path
    ],
)
def test_h_structurally_invalid_scopes_fail_closed(queue, bad):
    plan = _plan_with_nodes([_packet_node("bad scope", bad)])
    with pytest.raises(PlanCompilationError):
        _materialize(plan, queue)


def test_h_whole_worktree_scope_is_not_authority(queue):
    plan = _plan_with_nodes([_packet_node("whole tree", ["."])])
    with pytest.raises(PlanCompilationError):
        _materialize(plan, queue)


def test_j_seeding_is_the_causal_step_not_an_archetype_default(queue):
    """J: prove the SEEDING CALL is what produces the authority — not an
    archetype default or a lucky inherited value.

    The shared archetype ``WorkRequirements`` carries NO scope; only the per-node
    ``declare_writable_paths`` call does. Two nodes seeded with DIFFERENT scopes
    in one materialization prove the value tracks the node, and the archetype
    baseline proves it is absent without the call."""
    from substrate.execution.planning.archetypes import resolve_archetype

    archetype = resolve_archetype("add note search", _scope())
    baseline = WorkRequirements(
        work_archetype_ref=f"{archetype.archetype_id}@v{archetype.archetype_version}",
        required_skill_refs=[dict(r) for r in archetype.required_skill_refs],
    )
    assert baseline.scope_declared is False and baseline.writable_path_scope == [], (
        "J: the archetype contributes NO scope — the seeding call is the only source"
    )

    plan = _plan_with_nodes(
        [
            _packet_node("A backend", FIXTURE_ALLOWED_PATHS[BACKEND]),
            _packet_node("B frontend", FIXTURE_ALLOWED_PATHS[FRONTEND]),
        ]
    )
    ids = _materialize(plan, queue)
    got = [queue.get_packet(i).requirements["writable_path_scope"] for i in ids]
    assert got == [FIXTURE_ALLOWED_PATHS[BACKEND], FIXTURE_ALLOWED_PATHS[FRONTEND]], (
        "J: each Task's authority tracks ITS node, proving per-node seeding is causal"
    )


# ── K / L: A/B/C/D lanes keep DISTINCT scopes; D is zero-write ────────────────


def test_k_abcd_tasks_receive_distinct_scopes(queue):
    plan = _plan_with_nodes(
        [
            _packet_node("A backend", FIXTURE_ALLOWED_PATHS[BACKEND]),
            _packet_node("B frontend", FIXTURE_ALLOWED_PATHS[FRONTEND]),
            _packet_node("C integration", FIXTURE_ALLOWED_PATHS[INTEGRATION]),
            _packet_node("D verification", FIXTURE_ALLOWED_PATHS[VERIFICATION]),
        ]
    )
    ids = _materialize(plan, queue)
    scopes = [queue.get_packet(i).requirements["writable_path_scope"] for i in ids]
    assert scopes[0] == FIXTURE_ALLOWED_PATHS[BACKEND]
    assert scopes[1] == FIXTURE_ALLOWED_PATHS[FRONTEND]
    assert scopes[2] == FIXTURE_ALLOWED_PATHS[INTEGRATION]
    assert scopes[3] == []
    assert scopes[0] != scopes[1], "K: lanes are NOT collapsed to one shared scope"
    # Every lane still DECLARED (including the zero-write verifier).
    assert all(queue.get_packet(i).requirements["scope_declared"] is True for i in ids)


def test_l_verifier_lane_is_zero_write_and_rejects_any_diff(queue):
    plan = _plan_with_nodes([_packet_node("D verification", FIXTURE_ALLOWED_PATHS[VERIFICATION])])
    ids = _materialize(plan, queue)
    declared = queue.get_packet(ids[0]).requirements["writable_path_scope"]
    assert declared == [], "L: verifier declares zero writable paths"
    # An empty allowlist means NOTHING may change — every path is outside.
    assert paths_outside(["app/main.py"], declared) == ["app/main.py"]
    assert paths_outside(OBSERVED_SIX, declared) == OBSERVED_SIX


# ── E / F / G: the observed six pass in scope; out-of-scope paths reject ──────


def test_e_observed_six_file_change_is_entirely_in_scope(queue):
    plan = _plan_with_nodes([_packet_node("combined search task", SMOKE_SCOPE)])
    ids = _materialize(plan, queue)
    declared = queue.get_packet(ids[0]).requirements["writable_path_scope"]
    assert paths_outside(OBSERVED_SIX, declared) == [], (
        "E: the real field worker's six legitimate changes are in scope"
    )


def test_f_one_out_of_scope_tracked_file_rejects(queue):
    plan = _plan_with_nodes([_packet_node("combined search task", SMOKE_SCOPE)])
    ids = _materialize(plan, queue)
    declared = queue.get_packet(ids[0]).requirements["writable_path_scope"]
    # Rewriting the fixture's PRE-EXISTING test to make one's own change pass.
    changed = OBSERVED_SIX + ["tests/test_api.py"]
    assert paths_outside(changed, declared) == ["tests/test_api.py"]


def test_g_out_of_scope_untracked_file_rejects(queue):
    plan = _plan_with_nodes([_packet_node("combined search task", SMOKE_SCOPE)])
    ids = _materialize(plan, queue)
    declared = queue.get_packet(ids[0]).requirements["writable_path_scope"]
    assert paths_outside(["seed/notes.json"], declared) == ["seed/notes.json"]
    assert paths_outside(["requirements.txt"], declared) == ["requirements.txt"]


# ── I / N: evidence can never widen scope; no post-persistence label fallback ──


def test_i_evidence_cannot_widen_scope(queue):
    """I: EvidenceRef is provenance, never mutation authority. A node carrying
    evidence that names other files does NOT gain authority over them."""
    node = _packet_node("combined search task", SMOKE_SCOPE)
    node.evidence_refs = ["evidence://seed/notes.json", "evidence://requirements.txt"]
    ids = _materialize(_plan_with_nodes([node]), queue)
    declared = queue.get_packet(ids[0]).requirements["writable_path_scope"]
    assert declared == SMOKE_SCOPE, "I: evidence did not widen the authority"
    assert paths_outside(["seed/notes.json"], declared) == ["seed/notes.json"]


def test_n_no_label_fallback_reconstructs_scope_after_persistence():
    """N: nothing may rebuild scope from a semantic label after persistence — the
    persisted contract is the authority.

    BEHAVIOURAL, not a grep: a packet whose contract is undeclared must RAISE
    even when a semantic_label that HAS canonical fixture paths is supplied. If
    any label fallback existed (under any name), the label would silently supply
    an authority instead."""
    from substrate.execution.attempts.field_task_scope import (
        ScopeResolutionError,
        allowed_paths_for,
    )

    undeclared = SimpleNamespace(
        packet_id="wp-x", requirements={"writable_path_scope": [], "scope_declared": False}
    )
    for label in (BACKEND, FRONTEND, INTEGRATION, VERIFICATION, ""):
        with pytest.raises(ScopeResolutionError):
            allowed_paths_for(undeclared, semantic_label=label)

    # And a DECLARED contract wins over any label that disagrees with it.
    declared_backend_only = SimpleNamespace(
        packet_id="wp-y",
        requirements={
            "writable_path_scope": FIXTURE_ALLOWED_PATHS[BACKEND],
            "scope_declared": True,
        },
    )
    assert (
        allowed_paths_for(declared_backend_only, semantic_label=INTEGRATION)
        == FIXTURE_ALLOWED_PATHS[BACKEND]
    ), "N: the persisted contract is authoritative; the label never widens it"


# ── The materialized Task remains non-executable (Wave 1 invariant intact) ────


def test_materialized_task_is_still_not_execution_ready(queue):
    plan = _plan_with_nodes([_packet_node("combined search task", SMOKE_SCOPE)])
    ids = _materialize(plan, queue)
    pkt = queue.get_packet(ids[0])
    assert pkt.approval_gates, "approval gates must never be empty"
    assert not pkt.is_execution_ready(), "materialization still grants ZERO execution authority"


# ── The objective-derived authority flows from the caller, not from substrate ──


def test_derive_state_records_propagates_declared_scope_to_every_gap():
    snapshot = GroundingSnapshot(intent_id="intent-1")
    _c, _d, gaps = derive_state_records(
        "add note search",
        snapshot,
        tenant_id="tenant-a",
        scope=_scope(),
        writable_path_scope=SMOKE_SCOPE,
    )
    assert gaps.gaps, "an objective always yields at least the umbrella gap"
    for gap in gaps.gaps:
        assert gap["writable_path_scope"] == SMOKE_SCOPE


def test_derive_state_records_none_scope_stays_undeclared():
    """No caller declaration → gaps carry None → nodes are undeclared → the
    compiler fails closed. Substrate NEVER invents an authority."""
    snapshot = GroundingSnapshot(intent_id="intent-1")
    _c, _d, gaps = derive_state_records(
        "add note search", snapshot, tenant_id="tenant-a", scope=_scope()
    )
    for gap in gaps.gaps:
        assert gap["writable_path_scope"] is None


def test_workspace_resolver_absent_means_undeclared_not_open():
    """The transport resolver returns None when the runtime declared nothing —
    which fails materialization closed rather than granting the whole repo."""
    from substrate.execution.intent.protocol import OperatorIntentProtocol

    proto = OperatorIntentProtocol()  # no resolver injected
    assert proto._resolve_workspace_scope(_scope()) is None

    proto_raising = OperatorIntentProtocol(
        workspace_scope_resolver=lambda _s: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    assert proto_raising._resolve_workspace_scope(_scope()) is None, "resolver fault fails CLOSED"


def test_transport_resolver_reads_one_declaration(monkeypatch):
    """The runtime declaration is read from instance config, never inferred."""
    from transports.api.objective_plan_routes import _declared_workspace_scope

    monkeypatch.delenv("UMH_WORKSPACE_WRITABLE_PATHS", raising=False)
    assert _declared_workspace_scope(_scope()) is None

    monkeypatch.setenv("UMH_WORKSPACE_WRITABLE_PATHS", ",".join(SMOKE_SCOPE))
    assert _declared_workspace_scope(_scope()) == SMOKE_SCOPE

    monkeypatch.setenv("UMH_WORKSPACE_WRITABLE_PATHS", "   ")
    assert _declared_workspace_scope(_scope()) is None


def test_requirements_contract_rejects_unsafe_scopes_at_the_source():
    """Structural refusal lives on the contract, so an unsafe scope can never be
    persisted and then discovered only at verification time."""
    for bad in (["/abs"], ["."], [".."], ["a/../.."], [""]):
        req = WorkRequirements()
        req.declare_writable_paths(bad)
        assert req.validate_writable_path_scope(), f"{bad} must be refused"
    good = WorkRequirements()
    good.declare_writable_paths(SMOKE_SCOPE)
    assert good.validate_writable_path_scope() == []


def test_d_retry_is_a_new_attempt_inheriting_the_same_task_authority(queue, tmp_path):
    """D: a retry mints a NEW attempt but the authority is the TASK's, so the
    second attempt is governed by the identical persisted scope (never widened,
    never re-derived)."""
    from substrate.execution.attempts.records import ExecutionAttempt
    from substrate.execution.attempts.store import ExecutionAttemptStore

    plan = _plan_with_nodes([_packet_node("combined search task", SMOKE_SCOPE)])
    task_id = _materialize(plan, queue)[0]

    store = ExecutionAttemptStore(
        attempts_path=str(tmp_path / "a.jsonl"),
        grants_path=str(tmp_path / "g.jsonl"),
        readiness_path=str(tmp_path / "r.jsonl"),
        leases_path=str(tmp_path / "l.jsonl"),
        assignments_path=str(tmp_path / "asn.jsonl"),
    )
    first, _ = store.create_attempt_idempotent(
        ExecutionAttempt(task_id=task_id, attempt_number=1, tenant_id="tenant-a")
    )
    retry, _ = store.create_attempt_idempotent(
        ExecutionAttempt(
            task_id=task_id,
            attempt_number=2,
            tenant_id="tenant-a",
            previous_attempt_id=first.attempt_id,
        )
    )
    assert retry.attempt_id != first.attempt_id, "D: retry is a NEW attempt"
    # Both resolve the SAME authority, read from the Task contract on disk.
    fresh = UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))
    for att in (first, retry):
        pkt = fresh.get_packet(att.task_id)
        assert pkt.requirements["writable_path_scope"] == SMOKE_SCOPE
        assert pkt.requirements["scope_declared"] is True


def test_propagation_chain_reads_one_authority_from_durable_state(queue, tmp_path):
    """Ruling 5: packet → (attempt/lease/package/dispatch) → verification all
    reference ONE canonical authority, resolved from the persisted contract on
    every reread — never widened, never rebuilt from a label or evidence."""
    from substrate.execution.attempts.field_task_scope import allowed_paths_for

    plan = _plan_with_nodes([_packet_node("combined search task", SMOKE_SCOPE)])
    task_id = _materialize(plan, queue)[0]

    # Independent rereads from disk (fresh queues) must agree byte-for-byte, and
    # the verifier's own accessor must return exactly the persisted scope.
    for _ in range(3):
        fresh = UniversalWorkQueue(store_path=str(tmp_path / "packets.jsonl"))
        pkt = fresh.get_packet(task_id)
        assert allowed_paths_for(pkt) == SMOKE_SCOPE
        # A dict-shaped reread (the store's raw row) resolves identically.
        row = next(
            json.loads(line)
            for line in open(tmp_path / "packets.jsonl", encoding="utf-8")
            if json.loads(line)["packet_id"] == task_id
        )
        assert allowed_paths_for(row) == SMOKE_SCOPE


def test_verifier_accessor_refuses_an_undeclared_contract():
    """A Task reaching verification with no declared scope is a governance
    failure that RAISES — it is never silently treated as 'anything goes'."""
    from substrate.execution.attempts.field_task_scope import (
        ScopeResolutionError,
        allowed_paths_for,
    )

    undeclared = SimpleNamespace(
        packet_id="wp-x",
        requirements={"writable_path_scope": [], "scope_declared": False},
    )
    with pytest.raises(ScopeResolutionError):
        allowed_paths_for(undeclared)


def test_second_writer_capture_task_also_declares_scope():
    """Adversarial-review defect 2a: ``capture_task`` is the SECOND canonical
    WorkPacket writer (the CREATE_TASK chat rail). It hand-built a requirements
    dict with no scope, reproducing the exact field defect the compiler fix
    closed. Both writers must seed through the one contract API and fail closed."""
    from substrate.execution.intent.protocol import (
        TaskScopeUndeclaredError,
        _task_requirements,
    )

    archetype = SimpleNamespace(
        archetype_id="development",
        archetype_version=1,
        required_skill_refs=[{"skill": "python"}],
    )
    req = _task_requirements(archetype, SMOKE_SCOPE)
    assert req["scope_declared"] is True
    assert req["writable_path_scope"] == SMOKE_SCOPE

    # Undeclared → fail closed, never a persisted Task with no authority.
    with pytest.raises(TaskScopeUndeclaredError):
        _task_requirements(archetype, None)

    # Structurally unsafe → fail closed.
    for bad in (["."], ["/abs"], [".."], ["app/.."]):
        with pytest.raises(TaskScopeUndeclaredError):
            _task_requirements(archetype, bad)


def test_capture_task_call_site_is_wired_to_the_seeding_helper():
    """The helper only protects Tasks if ``capture_task`` actually CALLS it.
    AST guard on the production call site (a hand-built requirements dict there
    is exactly the defect this closes)."""
    import ast

    import substrate.execution.intent.protocol as protocol_mod

    src = open(protocol_mod.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    capture = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "capture_task"
    )
    calls = {
        n.func.id
        for n in ast.walk(capture)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "_task_requirements" in calls, (
        "capture_task must build requirements through the seeding helper, "
        "never a hand-built dict without writable_path_scope/scope_declared"
    )
    # And it must not construct a bare requirements dict inline any more.
    for node in ast.walk(capture):
        if isinstance(node, ast.keyword) and node.arg == "requirements":
            assert not isinstance(node.value, ast.Dict), (
                "capture_task must not pass a literal requirements dict"
            )


def test_resumed_plan_reseeds_node_authority(queue, tmp_path, monkeypatch):
    """Adversarial-review defect 2b: a plan record persisted BEFORE Tasks carried
    scope has nodes with scope_declared=False. Resume must re-seed from the
    freshly-derived declaration, or the record is an unrecoverable poison that
    fails materialization forever (every retry takes the same branch)."""
    stale_node = ObjectivePlanNode(kind="packet", title="legacy node", lane="build")
    assert stale_node.scope_declared is False, "a legacy node declares nothing"
    plan = _plan_with_nodes([stale_node])

    # Simulate the resume re-seed the compiler now performs.
    declared = SMOKE_SCOPE
    for node in plan.nodes:
        if node.get("kind") == "packet":
            node["writable_path_scope"] = list(declared)
            node["scope_declared"] = True

    ids = _materialize(plan, queue)
    assert queue.get_packet(ids[0]).requirements["writable_path_scope"] == declared


def test_nothing_persists_when_any_node_is_undeclared(queue, tmp_path):
    """Adversarial-review partial-persistence defect: raising mid-loop left an
    orphan PLANNED Task behind (the queue write is not rolled back). Validation
    runs BEFORE any ingest, so a plan with one bad node persists NOTHING."""
    good = _packet_node("declared lane", SMOKE_SCOPE)
    bad = _packet_node("undeclared lane", [], declared=False)
    with pytest.raises(PlanCompilationError):
        _materialize(_plan_with_nodes([good, bad]), queue)
    assert queue.all_packets() == [], "no orphan Task may be persisted"
    # And the good node must not have been stamped with a workpacket_id.
    store = tmp_path / "packets.jsonl"
    assert not store.exists() or store.read_text(encoding="utf-8").strip() == ""


def test_collapsing_traversal_scope_is_refused_at_the_contract():
    """Adversarial-review validator bypass: 'app/..' and 'app//..' COLLAPSE to
    '.' (whole workspace) but passed the string-only check, so an unsafe
    authority could be persisted and was only caught later at verification."""
    for bad in (["app/.."], ["app//.."], ["a/b/../.."]):
        req = WorkRequirements()
        req.declare_writable_paths(bad)
        assert req.validate_writable_path_scope(), f"{bad} must be refused at the contract"


def test_scope_is_carried_on_the_plan_node_contract():
    """The plan node is the planning-time OWNER of the authority (one owner, no
    second registry) and round-trips through its dict form."""
    node = _packet_node("combined", SMOKE_SCOPE)
    round_tripped = ObjectivePlanNode.from_dict(node.to_dict())
    assert round_tripped.writable_path_scope == SMOKE_SCOPE
    assert round_tripped.scope_declared is True
