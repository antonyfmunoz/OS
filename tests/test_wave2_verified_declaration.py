"""Wave 2 — the VERIFIED EXECUTION DECLARATION and the single write boundary.

WHY THIS FILE EXISTS
--------------------
Seven successive adversarial review rounds each found a NEW way for the Task
declared as the run's integration Task to become durable as
``execution_kind="worker"``. Six of them were closed pointwise, in a consumer of
"which Task is the integration Task". The seventh showed why that could never
converge:

    AUTHORITY was integrity-checked, but the DECLARATION identifying what that
    authority governs was re-read from mutable state at every consumer.

``scenario_map.json``'s ``integration_task_id`` is an unauthenticated field,
while the authority path digest-verifies that same field. Move it, and the
DECLARATION moves while the AUTHORITY correctly refuses — so every gate keyed off
the declaration silently skips, the store guard disarms for the real Task C, and
a worker row is persisted. ``execution_kind`` is immutable, so it is permanent
and it dispatches to a real model worker.

The fix is structural, not pointwise:

    A VERIFIED TASK-EXECUTION DECLARATION IS CREATED ONCE FROM AUTHENTICATED RUN
    AUTHORITY AND CARRIED INTO ATTEMPT CREATION.

``VerifiedExecutionDeclaration`` is built once per run from RECOMPUTED canonical
plan/packet lineage — never by reading the map's field — and is a frozen value,
not an accessor, so no later write can retarget it.

DECLARATION IS NOT AUTHORIZATION. A grant that is expired, revoked, truncated or
unreadable may stop composition from RUNNING; it may never transform Task C into
a worker Task. That separation is load-bearing and is pinned here: an earlier
version of the builder gated on ``resolve_canonical_grant`` and was measured
against the real field fixture, whose grant is ACTIVE but 0.1 days past
``expires_at`` — declaration construction failed, Task C became UNDECLARED, and a
``C + worker`` row persisted. Same defect, reached through the expiry door.

Every test enters through REAL production objects: the real fixture records under
their real filenames, the real driver, the real store, the real scheduler.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "wave2_field_grant_defect"

CAND = "131549ee4d1775a55953ecb9ff5d30fc720d20b1"
RUN = "20260807T005250Z-p1"
TASK_C = "wp-7c7ffd5be3fc"  # the real integration_task_id
TASK_A = "wp-5013927ed089"
TASK_B = "wp-6442c7ba99fc"

GRANTS_FILENAME = "execution_authorization_grants.jsonl"
COMPOSITION = "control_plane_composition"
WORKER = "worker"


# ─────────────────────────────────────────────────────────────────────────────
# Real candidate tree — production layout, real persisted field records
# ─────────────────────────────────────────────────────────────────────────────
def _tree(tmp_path: Path) -> tuple[str, Path]:
    base = tmp_path / "candidates" / "wave2" / CAND
    targets = base / "targets" / RUN
    targets.mkdir(parents=True, exist_ok=True)
    state = base / "state" / "umh"
    (state / "operator" / "objective_planning").mkdir(parents=True, exist_ok=True)
    (state / "universal_work").mkdir(parents=True, exist_ok=True)
    (state / "operator" / "execution_attempts").mkdir(parents=True, exist_ok=True)

    shutil.copy(
        FIXTURE / "objective_plans.jsonl",
        state / "operator" / "objective_planning" / "objective_plans.jsonl",
    )
    shutil.copy(FIXTURE / "work_packets.jsonl", state / "universal_work" / "work_packets.jsonl")
    shutil.copy(
        FIXTURE / GRANTS_FILENAME,
        state / "operator" / "execution_attempts" / GRANTS_FILENAME,
    )
    shutil.copy(FIXTURE / "scenario_map.json", targets / "scenario_map.json")
    shutil.copy(FIXTURE / "execution_binding.json", targets / "execution_binding.json")
    return str(targets), state / "operator" / "execution_attempts"


def _store(ea_dir: Path, **kw):
    from substrate.execution.attempts.store import ExecutionAttemptStore

    return ExecutionAttemptStore(
        attempts_path=str(ea_dir / "execution_attempts.jsonl"),
        grants_path=str(ea_dir / GRANTS_FILENAME),
        readiness_path=str(ea_dir / "readiness.jsonl"),
        leases_path=str(ea_dir / "leases.jsonl"),
        assignments_path=str(ea_dir / "assignments.jsonl"),
        # SEALED BY DEFAULT, exactly as the production runner constructs it.
        governed_run=kw.pop("governed_run", True),
        **kw,
    )


def _driver(targets_dir: str, store):
    """A REAL driver — the production constructor, which builds and attaches."""
    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver

    return FieldControlPlaneDriver(
        store=store,
        work_queue=SimpleNamespace(get_packet=lambda t: None),
        spool=None,
        sandbox_manager=None,
        targets_dir=targets_dir,
    )


def _attempt(task_id: str, kind: str, *, attempt_id: str = "", number: int = 1):
    from substrate.execution.attempts.records import ExecutionAttempt

    kw = {"attempt_id": attempt_id} if attempt_id else {}
    return ExecutionAttempt(
        task_id=task_id,
        execution_authorization_ref="ref-1",
        attempt_number=number,
        execution_kind=kind,
        **kw,
    )


def _sm(targets_dir: str, fn):
    p = Path(targets_dir) / "scenario_map.json"
    data = json.loads(p.read_text())
    fn(data)
    p.write_text(json.dumps(data))


@pytest.fixture()
def wired(tmp_path):
    """Real tree + real store + real driver, declaration built and attached."""
    targets, ea = _tree(tmp_path)
    store = _store(ea)
    driver = _driver(targets, store)
    return SimpleNamespace(targets=targets, ea=ea, store=store, driver=driver)


# ─────────────────────────────────────────────────────────────────────────────
# The declaration is built, authenticated, and attached by PRODUCTION wiring
# ─────────────────────────────────────────────────────────────────────────────
def test_driver_builds_and_attaches_the_declaration(wired):
    """The production constructor wires the store — not the test."""
    decl = wired.store._verified_declaration
    assert decl is not None, "the driver did not attach a verified declaration"
    assert decl.run_id == RUN
    assert decl.candidate_sha == CAND
    assert decl.execution_class_for(TASK_C) == COMPOSITION


def test_declaration_carries_the_binding_digest(wired):
    """The digest covers the run binding AND the semantic mapping."""
    from substrate.execution.attempts.field_scenario_map import (
        binding_digest,
        read_execution_binding,
    )

    binding = read_execution_binding(wired.targets)
    mapping = json.loads((Path(wired.targets) / "scenario_map.json").read_text())
    expected = binding_digest({k: str(v) for k, v in mapping.items()}, binding)
    assert wired.store._verified_declaration.digest == expected


def test_ordinary_tasks_are_undeclared(wired):
    """A/B/D carry no declaration — their behaviour is untouched."""
    decl = wired.store._verified_declaration
    for task in (TASK_A, TASK_B, "wp-does-not-exist", ""):
        assert decl.execution_class_for(task) is None


def test_declaration_is_immutable(wired):
    """The snapshot is frozen — no consumer can retarget it in place."""
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        wired.store._verified_declaration.execution_classes = ()


def test_declaration_is_DEEPLY_immutable(wired):
    """Frozen is not enough — a mutable MEMBER would still be retargetable.

    A ``frozen=True`` dataclass holding a list/dict can be edited in place
    through the aliased member without ever assigning to a field, which would
    restore exactly the retargeting the snapshot exists to remove. Every level
    must be an immutable tuple/str; hashability proves it deeply.
    """
    decl = wired.store._verified_declaration
    assert isinstance(decl.execution_classes, tuple)
    for entry in decl.execution_classes:
        assert isinstance(entry, tuple)
        assert all(isinstance(v, str) for v in entry)
    assert isinstance(hash(decl), int), "declaration is not deeply immutable"


def test_matches_run_rejects_foreign_run_and_candidate(wired):
    decl = wired.store._verified_declaration
    assert decl.matches_run(run_id=RUN, candidate_sha=CAND)
    assert not decl.matches_run(run_id="OTHER", candidate_sha=CAND)
    assert not decl.matches_run(run_id=RUN, candidate_sha="deadbeef")


# ─────────────────────────────────────────────────────────────────────────────
# THE CRITICAL BYPASS — a retargeted declaration
# ─────────────────────────────────────────────────────────────────────────────
def test_retargeting_the_map_field_cannot_move_the_declaration(tmp_path):
    """THE seventh-round bypass, pinned.

    Moving ``integration_task_id`` to Task A previously made the accessor return
    None for the real Task C, disarming the store guard so a worker row
    persisted. The declaration is now derived from RECOMPUTED lineage, so the
    field is not the source and moving it changes nothing.
    """
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    _sm(targets, lambda m: m.update(integration_task_id=TASK_A))

    store = _store(ea)
    _driver(targets, store)

    assert store._verified_declaration.execution_class_for(TASK_C) == COMPOSITION
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


@pytest.mark.parametrize("moved_to", [TASK_A, TASK_B, "wp-fabricated", ""])
def test_declaration_survives_every_retarget_target(tmp_path, moved_to):
    targets, ea = _tree(tmp_path)
    _sm(targets, lambda m: m.update(integration_task_id=moved_to))
    store = _store(ea)
    _driver(targets, store)
    assert store._verified_declaration.execution_class_for(TASK_C) == COMPOSITION


def test_deleting_the_map_field_cannot_undeclare_task_c(tmp_path):
    targets, ea = _tree(tmp_path)
    _sm(targets, lambda m: m.pop("integration_task_id", None))
    store = _store(ea)
    _driver(targets, store)
    assert store._verified_declaration.execution_class_for(TASK_C) == COMPOSITION


# ─────────────────────────────────────────────────────────────────────────────
# DECLARATION ≠ AUTHORIZATION — grant state may never change execution class
# ─────────────────────────────────────────────────────────────────────────────
def _grants(ea: Path, fn):
    p = ea / GRANTS_FILENAME
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    out = [r for r in (fn(r) for r in rows) if r]
    p.write_text("".join(json.dumps(r) + "\n" for r in out))


def test_expired_grant_does_not_change_execution_class(tmp_path):
    """THE regression that a grant-gated builder introduced.

    The real fixture grant is ACTIVE but past ``expires_at``. A builder that
    gated on ``resolve_canonical_grant`` failed to construct, Task C became
    UNDECLARED, and a ``C + worker`` row persisted — the original defect through
    a new door. Declaration must be derived from lineage, which does not expire.
    """
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    _grants(ea, lambda r: {**r, "expires_at": 1.0})
    store = _store(ea)
    _driver(targets, store)

    assert store._verified_declaration.execution_class_for(TASK_C) == COMPOSITION
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


@pytest.mark.parametrize(
    "label,mutate",
    [
        ("revoked", lambda ea: _grants(ea, lambda r: {**r, "status": "revoked"})),
        ("not_yet_valid", lambda ea: _grants(ea, lambda r: {**r, "not_before": 4e9})),
        ("truncated", lambda ea: (ea / GRANTS_FILENAME).write_text("")),
        ("deleted", lambda ea: (ea / GRANTS_FILENAME).unlink()),
        (
            "renamed",
            lambda ea: (ea / GRANTS_FILENAME).rename(ea / "execution_grants.jsonl"),
        ),
        (
            "frontier_drops_c",
            lambda ea: _grants(
                ea,
                lambda r: {
                    **r,
                    "task_frontier": [t for t in (r.get("task_frontier") or []) if t != TASK_C],
                },
            ),
        ),
    ],
)
def test_grant_state_never_transforms_task_c_into_a_worker(tmp_path, label, mutate):
    """Every authority failure mode: C stays DECLARED, and C+worker is refused."""
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    mutate(ea)
    store = _store(ea)
    _driver(targets, store)

    assert store._verified_declaration.execution_class_for(TASK_C) == COMPOSITION, (
        f"{label}: authority state changed the DECLARED execution class"
    )
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


# ─────────────────────────────────────────────────────────────────────────────
# THE WRITE BOUNDARY — new inserts
# ─────────────────────────────────────────────────────────────────────────────
def test_direct_c_worker_persistence_is_refused(wired):
    """Bypassing the scheduler entirely still cannot persist C as a worker."""
    from substrate.execution.attempts.store import AttemptStoreConflict

    with pytest.raises(AttemptStoreConflict) as exc:
        wired.store.create_attempt_idempotent(_attempt(TASK_C, WORKER))
    assert COMPOSITION in str(exc.value)
    assert not Path(wired.ea / "execution_attempts.jsonl").exists() or not [
        r for r in Path(wired.ea / "execution_attempts.jsonl").read_text().splitlines() if r.strip()
    ], "a refused attempt must leave NO durable row"


def test_declared_composition_attempt_is_allowed(wired):
    got, created = wired.store.create_attempt_idempotent(_attempt(TASK_C, COMPOSITION))
    assert created and got.execution_kind == COMPOSITION


@pytest.mark.parametrize("task", [TASK_A, TASK_B, "wp-unrelated"])
def test_ordinary_worker_attempts_unchanged(wired, task):
    """A/B/D regression — the invariant must not disturb ordinary work."""
    got, created = wired.store.create_attempt_idempotent(_attempt(task, WORKER))
    assert created and got.execution_kind == WORKER


@pytest.mark.parametrize("task", [TASK_A, TASK_B])
def test_undeclared_task_cannot_be_promoted_to_composition(wired, task):
    """The MIRROR defect: an ordinary Task minted as a composition attempt."""
    from substrate.execution.attempts.store import AttemptStoreConflict

    with pytest.raises(AttemptStoreConflict):
        wired.store.create_attempt_idempotent(_attempt(task, COMPOSITION))


# ─────────────────────────────────────────────────────────────────────────────
# THE WRITE BOUNDARY — idempotent return of an EXISTING row (review A HIGH-1)
# ─────────────────────────────────────────────────────────────────────────────
def test_poisoned_existing_row_is_never_returned_as_success(tmp_path):
    """Idempotency must never legitimize an invalid historical record.

    A pre-existing ``C + worker`` row was returned as ``(attempt, False)`` — a
    successful result the caller then dispatches, exactly as if freshly created,
    and ``execution_kind`` is immutable so it can never be repaired.
    """
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    # Seed the poison through an UNGUARDED store (no declaration attached).
    # Seeded through a NON-governed store: this models a historical row written
    # before the invariant existed (legacy data), which is exactly the case the
    # idempotent-return guard must catch. A governed store would refuse it.
    _store(ea, governed_run=False).create_attempt_idempotent(
        _attempt(TASK_C, WORKER, attempt_id="poison-1")
    )

    store = _store(ea)
    _driver(targets, store)
    with pytest.raises(AttemptStoreConflict) as exc:
        store.create_attempt_idempotent(_attempt(TASK_C, COMPOSITION))
    assert "EXISTING" in str(exc.value)


def test_poisoned_row_is_preserved_as_evidence(tmp_path):
    """A corrupt row is refused, never silently mutated into composition."""
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    # Seeded through a NON-governed store: this models a historical row written
    # before the invariant existed (legacy data), which is exactly the case the
    # idempotent-return guard must catch. A governed store would refuse it.
    _store(ea, governed_run=False).create_attempt_idempotent(
        _attempt(TASK_C, WORKER, attempt_id="poison-1")
    )
    store = _store(ea)
    _driver(targets, store)
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, COMPOSITION))

    rows = [
        json.loads(x)
        for x in (ea / "execution_attempts.jsonl").read_text().splitlines()
        if x.strip()
    ]
    assert len(rows) == 1
    assert rows[0]["attempt_id"] == "poison-1"
    assert rows[0]["execution_kind"] == WORKER, "the evidence row was mutated"


def test_valid_existing_row_still_returns_idempotently(wired):
    """Ordinary idempotency is unaffected."""
    first, created = wired.store.create_attempt_idempotent(_attempt(TASK_A, WORKER))
    again, created2 = wired.store.create_attempt_idempotent(_attempt(TASK_A, WORKER))
    assert created and not created2
    assert again.attempt_id == first.attempt_id


# ─────────────────────────────────────────────────────────────────────────────
# RACE — mutate every source AFTER the declaration exists
# ─────────────────────────────────────────────────────────────────────────────
def test_mutation_after_declaration_cannot_change_execution_class(tmp_path):
    """t0 build → t1 mutate every source → t2 create. Must never yield worker."""
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    store = _store(ea)
    _driver(targets, store)
    t0 = store._verified_declaration.execution_class_for(TASK_C)

    # t1 — retarget the map, destroy the grants, destroy the packets.
    _sm(targets, lambda m: m.update(integration_task_id=TASK_A))
    (ea / GRANTS_FILENAME).write_text("")
    state = Path(targets).parent.parent / "state" / "umh"
    (state / "universal_work" / "work_packets.jsonl").write_text("")
    (state / "operator" / "objective_planning" / "objective_plans.jsonl").write_text("")

    # t2 — the declaration is unchanged and the write is still refused.
    assert store._verified_declaration.execution_class_for(TASK_C) == t0 == COMPOSITION
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_declaration_cannot_be_replaced_or_cleared(wired):
    """A replaceable snapshot is a mutable truth source wearing a frozen type."""
    from substrate.execution.attempts.records import (
        DeclarationResult,
        VerifiedExecutionDeclaration,
    )
    from substrate.execution.attempts.store import AttemptStoreConflict

    evil = VerifiedExecutionDeclaration(
        run_id="EVIL", candidate_sha="x", digest="y", execution_classes=()
    )
    # A FOREIGN declaration now SEALS rather than raising — strictly stronger,
    # because it fails closed without depending on the caller catching. The
    # installed declaration is untouched and the boundary is shut.
    wired.store.apply_declaration_result(
        DeclarationResult.declared(evil), run_id=RUN, candidate_sha=CAND
    )
    assert wired.store._creation_sealed
    assert wired.store._verified_declaration.run_id == RUN
    with pytest.raises(AttemptStoreConflict):
        wired.store.create_attempt_idempotent(_attempt(TASK_C, WORKER))
    # A DECLARED store may not be downgraded to NO_COMPOSITION either — that
    # would disarm the invariant just as effectively as a replacement. Both
    # shapes are covered: an UNBOUND proof seals (it can't be verified at all),
    # and a correctly-BOUND one raises (it is verified, then refused).
    wired.store.apply_declaration_result(DeclarationResult.no_composition("unbound"))
    assert wired.store._creation_sealed
    wired.store._creation_sealed = ""  # re-open to exercise the bound path
    with pytest.raises(AttemptStoreConflict):
        wired.store.apply_declaration_result(
            DeclarationResult.no_composition("bound", run_id=RUN, candidate_sha=CAND),
            run_id=RUN,
            candidate_sha=CAND,
        )
    # Still enforcing after the refused swaps.
    assert wired.store._verified_declaration.execution_class_for(TASK_C) == COMPOSITION


def test_reattaching_the_same_declaration_is_idempotent(wired):
    """Idempotent wiring must not be mistaken for a retarget attempt."""
    from substrate.execution.attempts.records import DeclarationResult

    wired.store.apply_declaration_result(
        DeclarationResult.declared(wired.store._verified_declaration),
        run_id=RUN,
        candidate_sha=CAND,
    )
    assert wired.store._verified_declaration.execution_class_for(TASK_C) == COMPOSITION


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTION PATH — the real scheduler, driven end to end
# ─────────────────────────────────────────────────────────────────────────────
def _packet(pid, tenant="tenant-A", plan="opr-A"):
    return SimpleNamespace(
        packet_id=pid,
        status=SimpleNamespace(value="approved"),
        dependencies=[],
        work_scope={"tenant_id": tenant, "target_kind": "umh_substrate"},
        lineage={"plan_record_id": plan},
    )


def _scheduler(tmp_path, store, packets, *, predicate=None):
    """The REAL AttemptScheduler over a REAL store, with a PERMITTING runner.

    The default runner fails closed on ``execution_attempt_create`` in-process,
    which would make every assertion here vacuously true — a mutant that records
    a block but returns success would ship green. So the runner really executes.
    """
    import time

    from substrate.execution.attempts.records import ExecutionAuthorizationGrant
    from substrate.execution.attempts.scheduler import AttemptScheduler

    by_id = {p.packet_id: p for p in packets}
    grant = ExecutionAuthorizationGrant(
        decision_ref="ref-1",
        tenant_id="tenant-A",
        plan_record_id="opr-A",
        plan_version=1,
        task_frontier=list(by_id),
        objective_id="goal-1",
        expires_at=time.time() + 3600,
        max_attempts_per_task=2,
        environment_classes=["git_worktree"],
        verification_obligations=["independent verification"],
    )
    grant.status = "active"
    created, _ = store.create_grant_idempotent(grant)

    def _permit(**kw):
        fn = kw.get("execute_fn")
        out = fn() if callable(fn) else ("", True)
        return SimpleNamespace(success=True, output=out[0] if isinstance(out, tuple) else out)

    scheduler = AttemptScheduler(
        store,
        work_queue=SimpleNamespace(get_packet=by_id.get),
        placement_fn=lambda *a, **k: None,
        lease_manager=SimpleNamespace(acquire=lambda *a, **k: None),
        compile_fn=lambda *a, **k: None,
        lock_dir=str(tmp_path / "locks"),
        mutation_runner=_permit,
        latest_plan_lookup=lambda _o: SimpleNamespace(plan_record_id="opr-A", status="approved"),
        composition_task_predicate=predicate,
    )
    return scheduler, created


def test_production_scheduler_never_persists_c_as_worker(tmp_path):
    """END TO END through the real scheduler, with NO composition predicate.

    This is the exact production shape of the field defect: the predicate is
    absent (or returns False), so ``_create_attempt`` stamps
    ``execution_kind="worker"`` for Task C. The write boundary must still refuse
    — the invariant may not depend on the predicate being wired.
    """
    targets, ea = _tree(tmp_path)
    store = _store(ea)
    _driver(targets, store)

    scheduler, grant = _scheduler(tmp_path, store, [_packet(TASK_C)], predicate=None)
    report = scheduler.run_scheduler_pass(grant)

    assert not report.attempts_created, "a worker attempt was created for the integration Task"
    assert TASK_C in report.authority_unresolved, report.authority_unresolved
    rows = (
        [
            json.loads(x)
            for x in (ea / "execution_attempts.jsonl").read_text().splitlines()
            if x.strip()
        ]
        if (ea / "execution_attempts.jsonl").exists()
        else []
    )
    assert not [r for r in rows if r["task_id"] == TASK_C], "a durable C row was persisted"


def test_one_task_refusal_does_not_abort_the_whole_pass(tmp_path):
    """REVIEW A HIGH-2, reproduced then closed.

    The store refusal (``AttemptStoreConflict``) escaped ``_create_attempt``,
    escaped the frontier loop, and aborted the pass — killing work for every
    other Task. A Task-local governed refusal must never become a fleet-wide
    outage.
    """
    targets, ea = _tree(tmp_path)
    store = _store(ea)
    _driver(targets, store)

    packets = [_packet(TASK_C), _packet(TASK_A), _packet(TASK_B)]
    scheduler, grant = _scheduler(tmp_path, store, packets, predicate=None)
    report = scheduler.run_scheduler_pass(grant)  # must NOT raise

    assert TASK_C in report.authority_unresolved
    created_tasks = {
        json.loads(x)["task_id"]
        for x in (ea / "execution_attempts.jsonl").read_text().splitlines()
        if x.strip()
    }
    assert TASK_A in created_tasks, "an independent Task was lost to another Task's refusal"
    assert TASK_B in created_tasks, "an independent Task was lost to another Task's refusal"
    assert TASK_C not in created_tasks


def test_refusal_is_reported_not_idle(tmp_path):
    """OBSERVABILITY: a refusal must not degrade into a generic empty result."""
    targets, ea = _tree(tmp_path)
    store = _store(ea)
    _driver(targets, store)

    scheduler, grant = _scheduler(tmp_path, store, [_packet(TASK_C)], predicate=None)
    report = scheduler.run_scheduler_pass(grant)

    assert TASK_C in report.authority_unresolved
    assert TASK_C in report.attempts_blocked
    # NOT idle and NOT a generic empty result: the refusal is a distinct,
    # durable field an operator can read, separate from "never reached".
    assert report.authority_unresolved != []
    assert not report.attempts_created


def test_refusal_survives_a_swallowing_governed_spine(tmp_path):
    """REVIEW B MEDIUM: the store refusal must not be absorbed by the spine.

    ``runner`` is the governed mutation path and does NOT necessarily propagate
    an exception raised inside ``execute_fn`` — under the degraded/fail-closed
    gate it returns a MutationResponse and the caller sees only "nothing was
    created", indistinguishable from an ordinary not-admissible Task. Measured:
    the native runner returns a MutationResponse and never re-raises.

    So the refusal is captured inside ``execute_fn`` and re-raised outside the
    runner. This drives a genuinely SWALLOWING runner to prove that.
    """
    import time

    from substrate.execution.attempts.records import ExecutionAuthorizationGrant
    from substrate.execution.attempts.scheduler import AttemptScheduler

    targets, ea = _tree(tmp_path)
    store = _store(ea)
    _driver(targets, store)

    pkt = _packet(TASK_C)
    grant = ExecutionAuthorizationGrant(
        decision_ref="ref-swallow",
        tenant_id="tenant-A",
        plan_record_id="opr-A",
        plan_version=1,
        task_frontier=[pkt.packet_id],
        objective_id="goal-1",
        expires_at=time.time() + 3600,
        max_attempts_per_task=2,
        environment_classes=["git_worktree"],
        verification_obligations=["independent verification"],
    )
    grant.status = "active"
    created, _ = store.create_grant_idempotent(grant)

    def _swallowing(**kw):
        """The DEGRADED governed spine: absorbs whatever execute_fn raises."""
        try:
            kw["execute_fn"]()
        except Exception:  # noqa: BLE001 - deliberately modelling the swallow
            pass
        return SimpleNamespace(success=False, output="")

    scheduler = AttemptScheduler(
        store,
        work_queue=SimpleNamespace(get_packet=lambda p: pkt if p == pkt.packet_id else None),
        placement_fn=lambda *a, **k: None,
        lease_manager=SimpleNamespace(acquire=lambda *a, **k: None),
        compile_fn=lambda *a, **k: None,
        lock_dir=str(tmp_path / "locks"),
        mutation_runner=_swallowing,
        latest_plan_lookup=lambda _o: SimpleNamespace(plan_record_id="opr-A", status="approved"),
    )
    report = scheduler.run_scheduler_pass(created)

    assert TASK_C in report.authority_unresolved, (
        "the store refusal was absorbed by the governed spine and became a "
        "generic empty result — the operator cannot see it"
    )
    assert not report.attempts_created


def test_declared_composition_attempt_is_created_by_the_real_scheduler(tmp_path):
    """The VALID path: predicate wired, C admitted AS a composition attempt."""
    targets, ea = _tree(tmp_path)
    store = _store(ea)
    _driver(targets, store)

    scheduler, grant = _scheduler(
        tmp_path,
        store,
        [_packet(TASK_C)],
        predicate=lambda pkt: str(getattr(pkt, "packet_id", "")) == TASK_C,
    )
    report = scheduler.run_scheduler_pass(grant)

    assert report.attempts_created, report.attempts_blocked
    rows = [
        json.loads(x)
        for x in (ea / "execution_attempts.jsonl").read_text().splitlines()
        if x.strip()
    ]
    c_rows = [r for r in rows if r["task_id"] == TASK_C]
    assert len(c_rows) == 1
    assert c_rows[0]["execution_kind"] == COMPOSITION


def test_ordinary_tasks_run_normally_through_the_real_scheduler(tmp_path):
    """A/B/D regression through production: unchanged worker attempts."""
    targets, ea = _tree(tmp_path)
    store = _store(ea)
    _driver(targets, store)

    packets = [_packet(TASK_A), _packet(TASK_B)]
    scheduler, grant = _scheduler(tmp_path, store, packets, predicate=None)
    report = scheduler.run_scheduler_pass(grant)

    assert len(report.attempts_created) == 2
    assert not report.authority_unresolved
    rows = [
        json.loads(x)
        for x in (ea / "execution_attempts.jsonl").read_text().splitlines()
        if x.strip()
    ]
    assert {r["execution_kind"] for r in rows} == {WORKER}


# ─────────────────────────────────────────────────────────────────────────────
# AN UNANSWERABLE DECLARATION IS A REFUSAL, NEVER AN ABSENCE
# ─────────────────────────────────────────────────────────────────────────────
def test_unbuildable_declaration_refuses_rather_than_returning_none(tmp_path):
    """A build failure must NOT collapse into "this run has no composition".

    Swallowing it to None is the exact shape of the original defect: the
    integration Task becomes UNDECLARED, the store guard has nothing to enforce,
    and a worker row persists. So an unanswerable declaration raises.
    """
    from substrate.execution.attempts.records import CompositionAuthorityUnresolved

    targets, ea = _tree(tmp_path)
    # Destroy the lineage: the map still DECLARES a composition run, but the
    # plan records it must be recomputed from are gone.
    state = Path(targets).parent.parent / "state" / "umh"
    (state / "operator" / "objective_planning" / "objective_plans.jsonl").write_text("")

    store = _store(ea)
    driver = _driver(targets, store)

    from substrate.execution.attempts.records import DeclarationOutcome

    assert store._verified_declaration is None
    assert driver._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    assert driver._declaration_result.reason, "the failure reason was not recorded"
    assert store._creation_sealed, "an UNANSWERABLE run left the boundary open"
    with pytest.raises(CompositionAuthorityUnresolved):
        driver._declared_execution_class_for(TASK_C)
    with pytest.raises(CompositionAuthorityUnresolved):
        driver._declared_integration_packet_id()


def test_unbuildable_declaration_seals_the_write_boundary(tmp_path):
    """RUN-AUTHORITY CORRUPTION seals attempt creation entirely.

    Measured hole (round 8): with the plan ledger destroyed the declaration
    cannot be built, so the store had NOTHING to enforce and a DIRECT write
    persisted ``C + worker`` — the original defect's exact end state. The
    scheduler refusal alone does not cover a caller that bypasses the scheduler.

    "We cannot tell what this Task is" must refuse every creation, not permit
    them all. Note this is strictly narrower than refusing on any missing file:
    a run with NO scenario map has no declaration ERROR, so it never seals.
    """
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    state = Path(targets).parent.parent / "state" / "umh"
    (state / "operator" / "objective_planning" / "objective_plans.jsonl").unlink()

    store = _store(ea)
    _driver(targets, store)

    assert store._verified_declaration is None
    assert store._creation_sealed, "the write boundary was left unarmed"

    # Neither the integration Task nor ANY task may be created while sealed —
    # an unclassifiable run cannot safely create anything.
    for task, kind in ((TASK_C, WORKER), (TASK_C, COMPOSITION), (TASK_A, WORKER)):
        with pytest.raises(AttemptStoreConflict):
            store.create_attempt_idempotent(_attempt(task, kind))

    assert not (ea / "execution_attempts.jsonl").exists() or not [
        x for x in (ea / "execution_attempts.jsonl").read_text().splitlines() if x.strip()
    ]


@pytest.mark.parametrize(
    "break_it",
    ["delete_plans", "empty_plans", "delete_packets", "empty_packets"],
)
def test_every_lineage_source_failure_seals(tmp_path, break_it):
    """Any destroyed DECLARATION SOURCE seals — none silently unarms the store."""
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    state = Path(targets).parent.parent / "state" / "umh"
    plans = state / "operator" / "objective_planning" / "objective_plans.jsonl"
    packets = state / "universal_work" / "work_packets.jsonl"
    {
        "delete_plans": lambda: plans.unlink(),
        "empty_plans": lambda: plans.write_text(""),
        "delete_packets": lambda: packets.unlink(),
        "empty_packets": lambda: packets.write_text(""),
    }[break_it]()

    store = _store(ea)
    _driver(targets, store)

    assert store._creation_sealed, f"{break_it} left the write boundary unarmed"
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_absent_map_in_a_governed_run_is_unanswerable(tmp_path):
    """A GOVERNED run with no scenario map is UNANSWERABLE — sealed.

    The over-refusal CONTROL (a genuinely ordinary non-field run still works) is
    ``test_plain_run_is_positively_no_composition`` below.
    """
    targets, ea = _tree(tmp_path)
    (Path(targets) / "scenario_map.json").unlink()

    store = _store(ea)
    driver = _driver(targets, store)

    from substrate.execution.attempts.records import (
        CompositionAuthorityUnresolved,
        DeclarationOutcome,
    )

    # SUPERSEDED (round 9): inside a CANDIDATE-SHAPED governed run a missing
    # scenario map is UNANSWERABLE, not "no composition" — file absence is what
    # an rsync, a cleanup, or an attacker produces, and reviewer A reproduced a
    # durable C+worker row through exactly that reading.
    assert store._verified_declaration is None
    assert driver._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    assert store._creation_sealed
    with pytest.raises(CompositionAuthorityUnresolved):
        driver._declared_execution_class_for(TASK_C)
    # NOTHING may be created — not even an ordinary Task. With the run's
    # structure unreadable we cannot know which Task is which.
    from substrate.execution.attempts.store import AttemptStoreConflict

    for task in (TASK_A, TASK_C):
        with pytest.raises(AttemptStoreConflict):
            store.create_attempt_idempotent(_attempt(task, WORKER))


def test_binding_naming_a_rejected_plan_is_unanswerable(tmp_path):
    """REVIEWER B's CRITICAL, pinned.

    ``select_plan`` refuses only SUPERSEDED; the ``status == approved`` check
    lived in ``resolve_canonical_grant``. Removing the grant gate (the correct
    DECLARATION ≠ AUTHORIZATION fix) removed it too, so a binding naming the
    fixture's REAL rejected prior revision built a declaration from the WRONG
    plan — whose integration node is a DIFFERENT packet — leaving the real Task
    C UNDECLARED and persisting it as a worker.

    The declaration-side allowlist is deliberately WIDER than the grant's
    (a plan may be structurally authoritative without being execution-authorized)
    but excludes states a decision positively rejected.
    """
    from substrate.execution.attempts.records import DeclarationOutcome
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    # The fixture's real rejected prior revision; its integration node names a
    # DIFFERENT packet (wp-5deae4d21c6a), so selecting it undeclares Task C.
    binding_path = Path(targets) / "execution_binding.json"
    data = json.loads(binding_path.read_text())
    data["plan_record_id"] = "opr-a719f7df9e91"
    binding_path.write_text(json.dumps(data))

    store = _store(ea)
    driver = _driver(targets, store)

    assert driver._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    assert store._creation_sealed
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


@pytest.mark.parametrize("status", ["rejected", "cancelled", "superseded", "bogus", ""])
def test_non_structural_plan_states_are_refused(tmp_path, status):
    """Only structurally-authoritative plan states may declare a run."""
    from substrate.execution.attempts.field_scenario_map import (
        ScenarioMapError,
        build_verified_declaration,
        read_execution_binding,
    )

    targets, ea = _tree(tmp_path)
    state = Path(targets).parent.parent / "state" / "umh"
    plans = state / "operator" / "objective_planning" / "objective_plans.jsonl"
    rows = [json.loads(x) for x in plans.read_text().splitlines() if x.strip()]
    for row in rows:
        if row.get("plan_record_id") == "opr-8dc31659d548":
            row["status"] = status
    plans.write_text("".join(json.dumps(r) + "\n" for r in rows))

    records = []
    for rel in (
        ("operator", "objective_planning", "objective_plans.jsonl"),
        ("universal_work", "work_packets.jsonl"),
    ):
        p = state.joinpath(*rel)
        records.extend(json.loads(x) for x in p.read_text().splitlines() if x.strip())

    with pytest.raises(ScenarioMapError):
        build_verified_declaration(records, binding=read_execution_binding(targets))


@pytest.mark.parametrize("status", ["approved", "awaiting_approval", "draft"])
def test_structural_plan_states_declare_normally(tmp_path, status):
    """A plan may be STRUCTURALLY authoritative without being execution-authorized.

    The counterweight to the test above: narrowing the allowlist to APPROVED
    only (copying the grant path) would refuse legitimate revisable versions.
    """
    from substrate.execution.attempts.field_scenario_map import (
        build_verified_declaration,
        read_execution_binding,
    )

    targets, ea = _tree(tmp_path)
    state = Path(targets).parent.parent / "state" / "umh"
    plans = state / "operator" / "objective_planning" / "objective_plans.jsonl"
    rows = [json.loads(x) for x in plans.read_text().splitlines() if x.strip()]
    for row in rows:
        if row.get("plan_record_id") == "opr-8dc31659d548":
            row["status"] = status
    plans.write_text("".join(json.dumps(r) + "\n" for r in rows))

    records = []
    for rel in (
        ("operator", "objective_planning", "objective_plans.jsonl"),
        ("universal_work", "work_packets.jsonl"),
    ):
        p = state.joinpath(*rel)
        records.extend(json.loads(x) for x in p.read_text().splitlines() if x.strip())

    decl = build_verified_declaration(records, binding=read_execution_binding(targets))
    assert decl.execution_class_for(TASK_C) == COMPOSITION


def _rewrite_plans(targets, fn):
    state = Path(targets).parent.parent / "state" / "umh"
    p = state / "operator" / "objective_planning" / "objective_plans.jsonl"
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    for row in rows:
        fn(row)
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return state


@pytest.mark.parametrize("consistent", [False, True])
def test_in_place_plan_node_retarget_is_refused(tmp_path, consistent):
    """`update_plan_cas` REWRITES a whole plan row at the SAME graph_version.

    So a plan version's NODES are mutable in place — status is not the only
    thing that can move. If the declaration trusted node contents blindly, an
    attacker (or a buggy revision path) could repoint the integration node at
    Task A without touching the binding, silently undeclaring the real Task C.

    Both shapes are covered: retargeting the NODE alone (caught by the
    node↔packet agreement cross-check) and retargeting the node AND the packet's
    lineage CONSISTENTLY (caught by lineage cardinality — the target packet then
    claims two nodes).
    """
    from substrate.execution.attempts.records import DeclarationOutcome
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    node_c = {}

    def _retarget(row):
        if row.get("plan_record_id") != "opr-8dc31659d548":
            return
        for node in row.get("nodes") or []:
            if node.get("semantic_label") == "integration_task_id":
                node_c["id"] = node["node_id"]
                node["workpacket_id"] = TASK_A

    state = _rewrite_plans(targets, _retarget)

    if consistent:
        wp = state / "universal_work" / "work_packets.jsonl"
        rows = [json.loads(x) for x in wp.read_text().splitlines() if x.strip()]
        for row in rows:
            if row.get("packet_id") == TASK_A:
                row["source_evidence"] = [
                    {"type": "plan_node", "node_id": node_c["id"], "evidence_refs": []}
                ]
        wp.write_text("".join(json.dumps(r) + "\n" for r in rows))

    store = _store(ea)
    driver = _driver(targets, store)

    assert driver._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    assert store._creation_sealed
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_production_runner_constructs_a_governed_store(tmp_path):
    """SEALED BY DEFAULT must be wired at the real production entry point.

    ``governed_run=True`` protects the window where the store EXISTS but has not
    yet been armed — in ``_build_control_plane_driver`` that window spans the
    queue, sandbox and host-control-plane registration between store
    construction and driver construction. Removing the flag left every test
    green (measured), so the wiring is asserted directly.
    """
    import ast

    src = Path(__file__).resolve().parent.parent / "scripts/wave2_attempt_runner.py"
    tree = ast.parse(src.read_text())
    constructions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ExecutionAttemptStore"
    ]
    assert constructions, "the runner no longer constructs an ExecutionAttemptStore"
    for call in constructions:
        governed = [
            kw
            for kw in call.keywords
            if kw.arg == "governed_run"
            and isinstance(kw.value, ast.Constant)
            and kw.value.value is True
        ]
        assert governed, (
            f"wave2_attempt_runner.py:{call.lineno} constructs an ExecutionAttemptStore "
            f"without governed_run=True — the boundary would start PERMISSIVE"
        )


def test_unarmed_governed_store_refuses_everything(tmp_path):
    """The behavioural half of sealed-by-default: unarmed ⇒ nothing is created.

    Without this, ``governed_run=True`` could be deleted and every other test
    would still pass (measured) — the flag would be untested defence-in-depth.
    """
    from substrate.execution.attempts.store import AttemptStoreConflict

    _targets, ea = _tree(tmp_path)
    store = _store(ea)  # governed, and deliberately NEVER armed

    assert store._creation_sealed, "a governed store did not start sealed"
    for task, kind in ((TASK_C, WORKER), (TASK_C, COMPOSITION), (TASK_A, WORKER)):
        with pytest.raises(AttemptStoreConflict):
            store.create_attempt_idempotent(_attempt(task, kind))


def test_arming_requires_a_matching_run_context(tmp_path):
    """A declaration must be PROVEN to govern this store, never assumed.

    The run context was previously checked only ``if (run_id or candidate_sha)``,
    so omitting both SKIPPED the check and any declaration armed any governed
    store (reproduced). Absence of context must SEAL — treating it as "skip" is
    the same absence-means-two-things defect one layer up.
    """
    from substrate.execution.attempts.records import (
        DeclarationResult,
        VerifiedExecutionDeclaration,
    )
    from substrate.execution.attempts.store import AttemptStoreConflict

    foreign = VerifiedExecutionDeclaration(
        run_id="OTHER-RUN",
        candidate_sha="deadbeef",
        digest="x",
        execution_classes=((TASK_C, COMPOSITION),),
    )
    _targets, ea = _tree(tmp_path)

    for kwargs in ({}, {"run_id": RUN, "candidate_sha": CAND}, {"run_id": RUN}):
        store = _store(ea)
        store.apply_declaration_result(DeclarationResult.declared(foreign), **kwargs)
        assert store._creation_sealed, f"a foreign declaration armed the store ({kwargs})"
        with pytest.raises(AttemptStoreConflict):
            store.create_attempt_idempotent(_attempt(TASK_C, WORKER))

    # A declaration that WOULD match, applied with NO context. Only the
    # mandatory-context rule can catch this — ``matches_run`` is never reached,
    # so a version that treats absence as "skip the check" arms the store.
    matching = VerifiedExecutionDeclaration(
        run_id=RUN,
        candidate_sha=CAND,
        digest="x",
        execution_classes=((TASK_C, COMPOSITION),),
    )
    for kwargs in ({}, {"run_id": RUN}, {"candidate_sha": CAND}):
        store = _store(ea)
        store.apply_declaration_result(DeclarationResult.declared(matching), **kwargs)
        assert store._creation_sealed, (
            f"a declaration armed the store with an incomplete run context "
            f"({kwargs}) — absence must SEAL, never skip the check"
        )
        with pytest.raises(AttemptStoreConflict):
            store.create_attempt_idempotent(_attempt(TASK_C, WORKER))

    # THE CASE ONLY THE MANDATORY-CONTEXT RULE CAN CATCH.
    #
    # A declaration whose OWN run/candidate are empty satisfies
    # ``matches_run("", "")``, so the equality check waves it through — the
    # mandatory-context rule is the only thing standing between it and an armed
    # store. The production builder cannot emit such a declaration (an empty
    # binding is refused before one is built), but a direct caller can, and
    # "no caller does this today" is what every prior round assumed.
    contextless = VerifiedExecutionDeclaration(
        run_id="", candidate_sha="", digest="", execution_classes=()
    )
    store = _store(ea)
    store.apply_declaration_result(DeclarationResult.declared(contextless))
    assert store._creation_sealed, (
        "a declaration with an EMPTY run/candidate armed the store — "
        "matches_run('','') is True, so only the mandatory-context rule can refuse it"
    )
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_subclassed_result_or_declaration_cannot_arm(tmp_path):
    """A subclass inherits the TAG, not the guarantees.

    ``isinstance`` accepted ``Evil(DeclarationResult)`` and a
    ``VerifiedExecutionDeclaration`` subclass overriding ``execution_class_for``
    to lie — both unsealed the store and persisted ``C + worker`` (reproduced).
    """
    from substrate.execution.attempts.records import (
        DeclarationOutcome,
        DeclarationResult,
        VerifiedExecutionDeclaration,
    )
    from substrate.execution.attempts.store import AttemptStoreConflict

    _targets, ea = _tree(tmp_path)

    class _EvilResult(DeclarationResult):
        pass

    store = _store(ea)
    with pytest.raises(AttemptStoreConflict):
        store.apply_declaration_result(_EvilResult(DeclarationOutcome.NO_COMPOSITION, reason="pwn"))
    assert store._creation_sealed

    class _LyingDeclaration(VerifiedExecutionDeclaration):
        def execution_class_for(self, task_id):  # noqa: D102 - deliberately lies
            return None

    store2 = _store(ea)
    store2.apply_declaration_result(
        DeclarationResult.declared(
            _LyingDeclaration(
                run_id=RUN,
                candidate_sha=CAND,
                digest="x",
                execution_classes=((TASK_C, COMPOSITION),),
            )
        ),
        run_id=RUN,
        candidate_sha=CAND,
    )
    # The guard reads the frozen tuple, not the overridable method.
    with pytest.raises(AttemptStoreConflict):
        store2.create_attempt_idempotent(_attempt(TASK_C, WORKER))


@pytest.mark.parametrize(
    "keep_map,keep_binding",
    [(False, True), (True, False), (True, True)],
    ids=["map-deleted", "binding-deleted", "both-present"],
)
def test_wave2_evidence_without_a_binding_is_unanswerable(tmp_path, keep_map, keep_binding):
    """FILE ABSENCE IS NOT PROOF (reviewer A, CRITICAL).

    ``NO_COMPOSITION`` was decided by path shape plus ``os.path.exists`` — both
    unauthenticated. Deleting the scenario map from a non-candidate-shaped run
    yielded NO_COMPOSITION and persisted a durable ``C + worker`` row through the
    real scheduler, with ``authority_unresolved == []`` (the field defect's
    invisible signature verbatim).

    Note the asymmetry that made it dangerous: an unreadable map SEALED, while a
    DELETED one unsealed — the more destructive mutation was the permissive one.

    A run is positively ordinary only when it presents NO Wave 2 evidence at all.
    Any residue, with no binding to evaluate it against, is UNANSWERABLE.
    """
    from substrate.execution.attempts.records import DeclarationOutcome
    from substrate.execution.attempts.store import AttemptStoreConflict

    governed, ea = _tree(tmp_path)
    flat = tmp_path / "flat"
    flat.mkdir()
    if keep_map:
        shutil.copy(Path(governed) / "scenario_map.json", flat / "scenario_map.json")
    if keep_binding:
        shutil.copy(Path(governed) / "execution_binding.json", flat / "execution_binding.json")

    store = _store(ea)
    driver = _driver(str(flat), store)

    assert driver._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    assert store._creation_sealed
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


@pytest.mark.parametrize(
    "reason,result_kw,apply_kw",
    [
        ("unbound proof, no context", {}, {}),
        ("unbound proof, with context", {}, {"run_id": RUN, "candidate_sha": CAND}),
        (
            "proof for ANOTHER run",
            {"run_id": "OTHER", "candidate_sha": "X"},
            {"run_id": RUN, "candidate_sha": CAND},
        ),
    ],
)
def test_no_composition_must_prove_which_run_it_is_about(tmp_path, reason, result_kw, apply_kw):
    """NO_COMPOSITION IS VERIFIED IDENTICALLY TO DECLARED (reviewer A, CRITICAL).

    DECLARED required a matching run context while NO_COMPOSITION ignored it
    entirely, so a result that provably governs NOTHING unsealed any governed
    store (reproduced). Asymmetric verification across the branches of one enum
    is itself the defect — a positive proof must name the run it is about.
    """
    from substrate.execution.attempts.records import DeclarationResult
    from substrate.execution.attempts.store import AttemptStoreConflict

    _targets, ea = _tree(tmp_path)
    store = _store(ea)
    store.apply_declaration_result(
        DeclarationResult.no_composition(reason, **result_kw), **apply_kw
    )

    assert store._creation_sealed, f"an unverifiable NO_COMPOSITION unsealed the store ({reason})"
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_lifecycle_cannot_advance_a_poisoned_row(tmp_path):
    """THE DECLARATION GOVERNS `transition_cas` TOO (reviewer A, HIGH).

    ``create_attempt_idempotent`` guards insert and idempotent return, but
    ``transition_cas`` is the OTHER durable write path and had no check. A
    poisoned ``Task C + worker`` row already on disk — legacy data, a restored
    backup, a concurrent writer — advanced through the lifecycle toward a real
    model worker without the guarded method ever being called (reproduced to
    LEASED). Refusing at creation while permitting advancement is a guard with a
    door next to it.
    """
    from substrate.execution.attempts.records import ExecutionAttempt
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    store = _store(ea)
    _driver(targets, store)

    poisoned = ExecutionAttempt(
        attempt_id="poison-lifecycle",
        task_id=TASK_C,
        execution_authorization_ref="ref-1",
        attempt_number=1,
        execution_kind=WORKER,
        status="ready",
        assignment_id="asn-1",
    )
    (ea / "execution_attempts.jsonl").write_text(json.dumps(poisoned.to_dict()) + "\n")

    on_disk = store.get_attempt("poison-lifecycle")
    assert on_disk.execution_kind == WORKER
    with pytest.raises(AttemptStoreConflict):
        store.transition_cas(
            "poison-lifecycle",
            "leased",
            expected_record_version=on_disk.record_version,
            expected_statuses=("ready",),
            actor="test",
            reason="advance the poisoned row",
        )


def test_lifecycle_still_advances_legitimate_rows(tmp_path):
    """CONTROL for the guard above — it must not freeze ordinary work."""
    targets, ea = _tree(tmp_path)
    store = _store(ea)
    _driver(targets, store)

    for task, kind in ((TASK_C, COMPOSITION), (TASK_A, WORKER)):
        created, _ = store.create_attempt_idempotent(_attempt(task, kind))
        moved = store.transition_cas(
            created.attempt_id,
            "ready",
            expected_record_version=created.record_version,
            expected_statuses=("created",),
            actor="test",
            reason="normal promotion",
        )
        assert moved.status == "ready"
        assert moved.execution_kind == kind


def _place(targets: Path, name: str, mode: str, source: Path, scratch: Path):
    """Put ``name`` into ``targets`` in one of the shapes a real tree can have."""
    import os

    dest = targets / name
    if mode == "real":
        shutil.copy(source, dest)
    elif mode == "dangling":
        os.symlink(str(scratch / "never-existed" / name), dest)
    elif mode == "validlink":
        real = scratch / f"real-{name}"
        shutil.copy(source, real)
        os.symlink(str(real), dest)
    elif mode != "absent":  # pragma: no cover - guards a typo in a param id
        raise AssertionError(f"unknown placement mode {mode!r}")


@pytest.mark.parametrize(
    "map_mode,binding_mode,expect_sealed",
    [
        ("dangling", "real", True),
        ("real", "dangling", True),
        ("dangling", "dangling", True),
        ("validlink", "validlink", True),
        ("real", "real", True),
        ("absent", "absent", False),
    ],
    ids=[
        "map-dangling-binding-real",
        "binding-dangling-map-real",
        "both-dangling",
        "both-valid-symlinks",
        "both-real-files",
        "both-genuinely-absent",
    ],
)
def test_dangling_wave2_names_are_evidence_not_absence(
    tmp_path, map_mode, binding_mode, expect_sealed
):
    """`os.path.exists` FOLLOWS SYMLINKS — a dangling name reads as absent.

    THE REPRODUCED HIGH. A targets dir visibly listing ``scenario_map.json`` and
    ``execution_binding.json`` as dangling symlinks reported "no Wave 2 evidence",
    took the NO_COMPOSITION branch, unsealed the store, and persisted an
    immutable ``Task C + worker`` row through the real driver. The code comment
    on that branch already named "a dangling symlink" as the case to defend
    against; ``exists`` is the one primitive that cannot see it.

    A name present but unresolvable is the STRONGEST signal of a mutated
    governed run — an interrupted rsync, a moved candidate tree, an attacker —
    so it must weigh toward UNANSWERABLE. Only a total absence of Wave 2 names
    is positive proof of an ordinary run.

    The earlier self-test missed this because it varied ONE file at a time; the
    permissive branch needs BOTH to read absent.
    """
    from substrate.execution.attempts.records import DeclarationOutcome
    from substrate.execution.attempts.store import AttemptStoreConflict

    governed, _governed_ea = _tree(tmp_path)
    # ORDINARY ledger: this test is about a run that is NOT a governed candidate.
    # Using the candidate's own ledger here would be the round-12 bypass shape
    # (governed ledger + foreign-subject declaration), which now correctly seals.
    ea = tmp_path / "ordinary-store"
    ea.mkdir()
    flat = tmp_path / "flat"
    flat.mkdir()
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    _place(flat, "scenario_map.json", map_mode, Path(governed) / "scenario_map.json", scratch)
    _place(
        flat,
        "execution_binding.json",
        binding_mode,
        Path(governed) / "execution_binding.json",
        scratch,
    )

    store = _store(ea)
    driver = _driver(str(flat), store)

    if expect_sealed:
        assert driver._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
        assert store._creation_sealed, (
            f"map={map_mode} binding={binding_mode}: Wave 2 evidence was read as "
            f"absence and the boundary opened"
        )
        with pytest.raises(AttemptStoreConflict):
            store.create_attempt_idempotent(_attempt(TASK_C, WORKER))
    else:
        # THE OVER-REFUSAL CONTROL: genuine absence is still positive proof.
        assert driver._declaration_result.outcome is DeclarationOutcome.NO_COMPOSITION
        assert not store._creation_sealed


@pytest.mark.parametrize(
    "node",
    ["dev-null-symlink", "fifo", "symlink-loop", "symlink-to-dir", "chardev", "directory"],
)
def test_every_wave2_node_type_is_evidence(tmp_path, node):
    """A directory ENTRY is evidence, whatever kind of node it is.

    ``lexists`` asks the right question — "is there an entry with this name?" —
    so every node type that is not a readable regular file must still weigh
    toward UNANSWERABLE rather than reading as absence. Enumerated because the
    original defect was one specific node type (a dangling symlink) slipping
    through a check that only understood regular files.
    """
    import os

    from substrate.execution.attempts.records import DeclarationOutcome
    from substrate.execution.attempts.store import AttemptStoreConflict

    _governed, ea = _tree(tmp_path)
    flat = tmp_path / "flat"
    flat.mkdir()
    for name in ("scenario_map.json", "execution_binding.json"):
        dest = flat / name
        if node == "dev-null-symlink":
            os.symlink("/dev/null", dest)
        elif node == "fifo":
            os.mkfifo(dest)
        elif node == "symlink-loop":
            os.symlink(f"{dest}.link", dest)
            os.symlink(str(dest), f"{dest}.link")
        elif node == "symlink-to-dir":
            os.symlink(str(tmp_path), dest)
        elif node == "chardev":
            os.symlink("/dev/zero", dest)
        else:
            dest.mkdir()

    store = _store(ea)
    driver = _driver(str(flat), store)

    assert driver._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    assert store._creation_sealed, f"{node}: a Wave 2 entry was read as absence"
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_ordinary_run_bindings_do_not_collide(tmp_path):
    """Two different ordinary runs must not share one unseal token.

    An ordinary run's NO_COMPOSITION proof binds to its targets dir. If two
    distinct directories produced the same binding, either run's proof would
    unseal the other's store — an unseal-everything token wearing a narrow name.
    """
    a = tmp_path / "run-a"
    a.mkdir()
    b = tmp_path / "run-b"
    b.mkdir()
    ea_a = tmp_path / "store-a"
    ea_a.mkdir()
    ea_b = tmp_path / "store-b"
    ea_b.mkdir()

    driver_a = _driver(str(a), _store(ea_a))
    driver_b = _driver(str(b), _store(ea_b))

    assert (
        driver_a._declaration_result.candidate_sha != driver_b._declaration_result.candidate_sha
    ), "two distinct ordinary runs share one NO_COMPOSITION binding"


def test_unrelated_entries_do_not_create_declaration_authority(tmp_path):
    """Only the canonical Wave 2 names are evidence — not lookalikes.

    Guards the fix against over-reach: widening "is there evidence?" to any file
    in the directory would seal every ordinary run that happens to hold a
    ``.bak`` or a README.
    """
    from substrate.execution.attempts.records import DeclarationOutcome

    _tree(tmp_path)
    # ORDINARY ledger — see the note in the dangling-names test above.
    ea = tmp_path / "ordinary-store"
    ea.mkdir()
    flat = tmp_path / "flat"
    flat.mkdir()
    for junk in (
        "README.md",
        "notes.txt",
        "scenario_map.json.bak",
        "execution_binding.json.old",
        ".hidden",
    ):
        (flat / junk).write_text("x")

    store = _store(ea)
    driver = _driver(str(flat), store)

    assert driver._declaration_result.outcome is DeclarationOutcome.NO_COMPOSITION
    assert not store._creation_sealed
    created, is_new = store.create_attempt_idempotent(_attempt("T-ordinary", WORKER))
    assert is_new and created.execution_kind == WORKER


@pytest.mark.parametrize(
    "shape",
    ["dangling-symlink", "symlink-to-dir", "symlink-loop", "directory", "zero-bytes"],
)
def test_exotic_map_shapes_never_read_as_no_composition(tmp_path, shape):
    """`os.path.exists` is not a truth oracle.

    The permissive branch keys on file presence, so every way a filesystem can
    make presence ambiguous is an attack surface: a dangling symlink and a
    renamed file both make `exists()` False, which is exactly what an rsync, a
    cleanup, or an attacker produces. Each must be UNANSWERABLE, never
    "positively no composition".
    """
    import os

    from substrate.execution.attempts.records import DeclarationOutcome
    from substrate.execution.attempts.store import AttemptStoreConflict

    governed, ea = _tree(tmp_path)
    flat = tmp_path / "flat"
    flat.mkdir()
    shutil.copy(Path(governed) / "execution_binding.json", flat / "execution_binding.json")
    target = flat / "scenario_map.json"
    if shape == "dangling-symlink":
        os.symlink(str(tmp_path / "does-not-exist"), target)
    elif shape == "symlink-to-dir":
        os.symlink(str(flat), target)
    elif shape == "symlink-loop":
        os.symlink(str(target), str(flat / "loop"))
        os.symlink(str(flat / "loop"), target)
    elif shape == "directory":
        target.mkdir()
    else:
        target.write_text("")

    store = _store(ea)
    driver = _driver(str(flat), store)

    assert driver._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    assert store._creation_sealed
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_one_ordinary_runs_proof_cannot_unseal_another(tmp_path):
    """Even the ordinary-run proof is run-scoped.

    An ordinary run has no candidate/run identity, so its NO_COMPOSITION proof
    binds to its targets dir. If that binding were a shared constant, ANY
    ordinary proof would unseal ANY store — an unseal-everything token wearing a
    narrower name.
    """
    from substrate.execution.attempts.store import AttemptStoreConflict

    def _plain(name):
        targets = tmp_path / name
        targets.mkdir()
        ea = tmp_path / f"{name}-store"
        ea.mkdir()
        store = _store(ea)
        return store, _driver(str(targets), store)

    store_x, driver_x = _plain("run-x")
    store_y, driver_y = _plain("run-y")

    # Each unsealed its OWN store.
    assert not store_x._creation_sealed
    assert not store_y._creation_sealed
    assert driver_x._declaration_result.candidate_sha != (
        driver_y._declaration_result.candidate_sha
    )

    # X's proof cannot unseal a store armed under Y's context.
    fresh_dir = tmp_path / "fresh-store"
    fresh_dir.mkdir()
    fresh = _store(fresh_dir)
    fresh.apply_declaration_result(
        driver_x._declaration_result,
        run_id=driver_y._declaration_result.run_id,
        candidate_sha=driver_y._declaration_result.candidate_sha,
    )
    assert fresh._creation_sealed
    with pytest.raises(AttemptStoreConflict):
        fresh.create_attempt_idempotent(_attempt(TASK_C, WORKER))


# ─────────────────────────────────────────────────────────────────────────────
# SUBJECT BINDING — the boundary owns the identity it protects
# ─────────────────────────────────────────────────────────────────────────────
def _foreign_tree(tmp_path: Path, *, candidate: str, run: str) -> str:
    """A complete candidate tree for a DIFFERENT subject, returning its targets."""
    base = tmp_path / "foreign" / "candidates" / "wave2" / candidate
    targets = base / "targets" / run
    targets.mkdir(parents=True)
    state = base / "state" / "umh"
    (state / "operator" / "objective_planning").mkdir(parents=True)
    (state / "universal_work").mkdir(parents=True)
    (state / "operator" / "execution_attempts").mkdir(parents=True)
    shutil.copy(
        FIXTURE / "objective_plans.jsonl",
        state / "operator" / "objective_planning" / "objective_plans.jsonl",
    )
    shutil.copy(FIXTURE / "work_packets.jsonl", state / "universal_work" / "work_packets.jsonl")
    shutil.copy(
        FIXTURE / GRANTS_FILENAME,
        state / "operator" / "execution_attempts" / GRANTS_FILENAME,
    )
    shutil.copy(FIXTURE / "scenario_map.json", targets / "scenario_map.json")
    shutil.copy(FIXTURE / "execution_binding.json", targets / "execution_binding.json")
    return str(targets)


@pytest.mark.parametrize("node", ["fifo", "symlink-to-fifo", "chardev", "dev-null", "directory"])
def test_special_file_authority_input_refuses_without_hanging(tmp_path, node):
    """A HANG IS NOT FAIL-CLOSED (reviewer HIGH, both reviewers).

    ``open()`` on a FIFO with no writer blocks in the kernel BEFORE any exception
    can be raised, so ``except OSError`` structurally cannot catch it. A named
    pipe called ``execution_binding.json`` hung the production runner forever:
    it never sealed, never reported, never dispatched. The entire three-state
    machinery is bypassed by a process that is simply stuck (reproduced: the
    reader blocked until an 8s alarm fired).

    Authority files must be regular files, checked by type BEFORE opening —
    consistent with the ``lexists`` rule that a present-but-unusable name is
    evidence of a mutated run, not absence. The alarm below is the assertion: if
    the read blocks, the test dies rather than passing slowly.
    """
    import os
    import signal

    from substrate.execution.attempts.records import DeclarationOutcome
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    binding = Path(targets) / "execution_binding.json"
    binding.unlink()
    if node == "fifo":
        os.mkfifo(binding)
    elif node == "symlink-to-fifo":
        real = tmp_path / "pipe"
        os.mkfifo(real)
        os.symlink(str(real), binding)
    elif node == "chardev":
        os.symlink("/dev/zero", binding)
    elif node == "dev-null":
        os.symlink("/dev/null", binding)
    else:
        binding.mkdir()

    def _hang(*_a):  # pragma: no cover - fires only on regression
        raise AssertionError(f"{node}: reading the authority file BLOCKED (hang, not refusal)")

    previous = signal.signal(signal.SIGALRM, _hang)
    signal.alarm(10)
    try:
        store = _store(ea)
        driver = _driver(targets, store)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)

    assert driver._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    assert store._creation_sealed
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_store_derives_its_own_governed_subject(tmp_path):
    """The ledger's own path says which candidate it belongs to.

    ``run_id`` is deliberately NOT derived — it is not encoded in the store path
    (it lives under ``targets/<run>/``), so the store must never pretend to know
    it. Overclaiming derivable identity is its own defect.
    """
    from substrate.execution.attempts.store import governed_subject

    _targets, ea = _tree(tmp_path)
    store = _store(ea)
    assert store._governed_subject == ("wave2", CAND)

    # Ordinary ledgers have no governed subject, so they are unconstrained.
    assert governed_subject(str(tmp_path / "ordinary" / "a.jsonl")) is None
    assert governed_subject("/opt/OS/data/runtime/umh/operator/x/a.jsonl") is None


@pytest.mark.parametrize(
    "shape",
    ["ordinary-temp-tree", "foreign-candidate", "same-candidate-wrong-run"],
)
def test_foreign_declaration_cannot_unseal_a_governed_ledger(tmp_path, shape):
    """THE ROUND-12 BYPASS, pinned.

    The store's ledger came from ``UMH_STATE_DIR`` while the declaration came
    from an independently supplied ``--targets-dir``. Pointed at an ordinary
    directory, a NO_COMPOSITION proven about THAT directory unsealed the governed
    candidate's ledger and persisted an immutable ``Task C + worker`` row
    (reproduced end to end).

    The proof was valid. It was about the wrong subject — the same shape as every
    prior round. Production derives both from one SHA today, so they agreed by
    CONVENTION; this makes it an INVARIANT the store itself enforces.
    """
    from substrate.execution.attempts.store import AttemptStoreConflict

    _targets, ea = _tree(tmp_path)
    if shape == "ordinary-temp-tree":
        foreign = tmp_path / "ordinary"
        foreign.mkdir()
        foreign = str(foreign)
    elif shape == "foreign-candidate":
        foreign = _foreign_tree(tmp_path, candidate="0" * 40, run=RUN)
    else:
        foreign = _foreign_tree(tmp_path, candidate=CAND, run="99999999T000000Z-p9")

    store = _store(ea)  # governed ledger for CAND
    _driver(foreign, store)  # declaration about a DIFFERENT subject

    assert store._creation_sealed, f"{shape}: a foreign-subject proof unsealed the ledger"
    for task, kind in ((TASK_C, WORKER), (TASK_C, COMPOSITION), (TASK_A, WORKER)):
        with pytest.raises(AttemptStoreConflict):
            store.create_attempt_idempotent(_attempt(task, kind))


@pytest.mark.parametrize(
    "outcome_kind", ["declared", "no-composition"], ids=["DECLARED", "NO_COMPOSITION"]
)
def test_store_refuses_authority_about_another_candidate(tmp_path, outcome_kind):
    """The STORE's own comparison, exercised directly at the boundary.

    The driver seals foreign trees upstream (the binding check fires first), so
    driving through it would test the wrong mechanism and leave the store's own
    comparison unexercised — measured: mutating it away kept the suite green.
    This applies the authority straight to the boundary, which is also exactly
    what a direct-construction caller does.
    """
    from substrate.execution.attempts.records import (
        DeclarationResult,
        VerifiedExecutionDeclaration,
    )
    from substrate.execution.attempts.store import AttemptStoreConflict

    _targets, ea = _tree(tmp_path)
    other = "0" * 40
    store = _store(ea)  # governed ledger for CAND

    if outcome_kind == "declared":
        result = DeclarationResult.declared(
            VerifiedExecutionDeclaration(
                run_id=RUN,
                candidate_sha=other,
                digest="x",
                execution_classes=((TASK_C, COMPOSITION),),
            )
        )
    else:
        result = DeclarationResult.no_composition("foreign", run_id=RUN, candidate_sha=other)

    # The caller even claims the RIGHT context — only the authority's own
    # subject is foreign, so nothing but the store's comparison can catch it.
    store.apply_declaration_result(result, run_id=RUN, candidate_sha=other)
    assert store._creation_sealed, "authority about another candidate unsealed this ledger"
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_store_refuses_a_caller_context_that_contradicts_its_own_path(tmp_path):
    """A caller may not relabel the ledger's subject.

    The authority is internally consistent and names the right candidate, but the
    caller supplies a DIFFERENT run context. The store derives the truth from its
    own path, so the caller's claim cannot override it.
    """
    from substrate.execution.attempts.records import (
        DeclarationResult,
        VerifiedExecutionDeclaration,
    )
    from substrate.execution.attempts.store import AttemptStoreConflict

    _targets, ea = _tree(tmp_path)
    store = _store(ea)
    other = "0" * 40

    store.apply_declaration_result(
        DeclarationResult.declared(
            VerifiedExecutionDeclaration(
                run_id=RUN,
                candidate_sha=CAND,  # honest authority
                digest="x",
                execution_classes=((TASK_C, COMPOSITION),),
            )
        ),
        run_id=RUN,
        candidate_sha=other,  # dishonest caller context
    )
    assert store._creation_sealed
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_matching_subject_still_arms_normally(tmp_path):
    """THE CONTROL — subject binding must not break the healthy path."""
    targets, ea = _tree(tmp_path)
    store = _store(ea)
    _driver(targets, store)

    assert not store._creation_sealed
    assert store._verified_declaration.execution_class_for(TASK_C) == COMPOSITION
    created, _ = store.create_attempt_idempotent(_attempt(TASK_A, WORKER))
    assert created.execution_kind == WORKER


def test_subject_derivation_resolves_relative_ledger_paths(tmp_path, monkeypatch):
    """A RELATIVE ledger path must still derive its governed subject.

    Normalization is not cosmetic here: without ``abspath`` a relative path
    contains no ``candidates/`` prefix to find, so the store derives NO subject
    and silently SKIPS its own guard — the boundary disarms exactly where it
    should engage. Measured: raw splitting returns None for this path while the
    normalized form resolves it correctly.
    """
    from substrate.execution.attempts.store import governed_subject

    root = tmp_path / "candidates" / "wave2" / CAND / "state" / "umh"
    (root / "operator" / "execution_attempts").mkdir(parents=True)
    monkeypatch.chdir(tmp_path / "candidates" / "wave2")

    relative = f"{CAND}/state/umh/operator/execution_attempts/execution_attempts.jsonl"
    assert governed_subject(relative) == ("wave2", CAND)


@pytest.mark.parametrize("suffix", ["", "/", "//", "/.", "/./"])
def test_subject_derivation_is_normalization_stable(tmp_path, suffix):
    """Lexically different spellings of one ledger derive ONE subject.

    A reproduced divergence: ``dirname(dirname(...))`` answers differently for a
    trailing slash, so two parsers disagreed about which tree a run belonged to.
    Subject derivation normalizes once and compares structured identity.
    """
    from substrate.execution.attempts.store import governed_subject

    base = f"{tmp_path}/candidates/wave2/{CAND}/state/umh/operator/execution_attempts"
    assert governed_subject(f"{base}{suffix}/execution_attempts.jsonl") == ("wave2", CAND)


def test_plain_run_is_positively_no_composition(tmp_path):
    """THE OVER-REFUSAL CONTROL — NO_COMPOSITION is real, reachable, and POSITIVE.

    A run that is neither candidate-shaped NOR claims a scenario map is
    positively proven to be an ordinary non-Wave-2 scheduler. It must NOT seal:
    the fail-closed rule may not starve legitimate work.

    This is the state that distinguishes "positive absence" from "failure to
    determine" — without it, "unanswerable ⇒ seal" could be satisfied by sealing
    everything.
    """
    from substrate.execution.attempts.records import DeclarationOutcome

    plain = tmp_path / "plain"
    plain.mkdir()
    ea = tmp_path / "store"
    ea.mkdir()
    store = _store(ea)
    driver = _driver(str(plain), store)

    assert driver._declaration_result.outcome is DeclarationOutcome.NO_COMPOSITION
    assert not store._creation_sealed, "a legitimate ordinary run was starved"
    got, created = store.create_attempt_idempotent(_attempt("T-ordinary", WORKER))
    assert created and got.execution_kind == WORKER


def test_unevaluable_composition_claim_is_never_no_composition(tmp_path):
    """A composition CLAIM that cannot be evaluated must SEAL, not pass.

    ``--targets-dir`` is free-form (``scripts/wave2_attempt_runner.py``), so a
    REAL Wave 2 run can be pointed at a non-candidate-shaped path. Reading that
    as "no composition" — which path shape alone would imply — lets a genuine
    composition run persist ``C + worker``.
    """
    from substrate.execution.attempts.records import DeclarationOutcome
    from substrate.execution.attempts.store import AttemptStoreConflict

    targets, ea = _tree(tmp_path)
    odd = tmp_path / "odd"
    odd.mkdir()
    shutil.copy(Path(targets) / "scenario_map.json", odd / "scenario_map.json")
    shutil.copy(Path(targets) / "execution_binding.json", odd / "execution_binding.json")

    store = _store(ea)
    driver = _driver(str(odd), store)

    assert driver._declaration_result.outcome is DeclarationOutcome.UNANSWERABLE
    assert store._creation_sealed
    with pytest.raises(AttemptStoreConflict):
        store.create_attempt_idempotent(_attempt(TASK_C, WORKER))


def test_node_packet_disagreement_fails_closed(tmp_path):
    """Lineage must AGREE: a node and the packet it resolves to name each other.

    Without the cross-check a tampered plan node could point the declaration at
    a different packet — retargeting one layer deeper than the map field.
    """
    from substrate.execution.attempts.field_scenario_map import (
        ScenarioMapError,
        build_verified_declaration,
        read_execution_binding,
    )

    targets, ea = _tree(tmp_path)
    state = Path(targets).parent.parent / "state" / "umh"
    plans_path = state / "operator" / "objective_planning" / "objective_plans.jsonl"

    rows = [json.loads(x) for x in plans_path.read_text().splitlines() if x.strip()]
    retargeted = False
    for row in rows:
        for node in row.get("nodes") or []:
            if str(node.get("workpacket_id", "")) == TASK_C:
                node["workpacket_id"] = TASK_A  # node now disagrees with its packet
                retargeted = True
    assert retargeted, "fixture drift: no plan node declares Task C"
    plans_path.write_text("".join(json.dumps(r) + "\n" for r in rows))

    records = []
    for rel in (
        ("operator", "objective_planning", "objective_plans.jsonl"),
        ("universal_work", "work_packets.jsonl"),
        ("operator", "execution_attempts", GRANTS_FILENAME),
    ):
        p = state.joinpath(*rel)
        if p.exists():
            records.extend(json.loads(x) for x in p.read_text().splitlines() if x.strip())

    binding = read_execution_binding(targets)
    with pytest.raises(ScenarioMapError):
        build_verified_declaration(records, binding=binding)


# ─────────────────────────────────────────────────────────────────────────────
# NO SECOND TRUTH MODEL
# ─────────────────────────────────────────────────────────────────────────────
def test_store_never_reads_declaration_state_from_disk():
    """The store must not learn a second way to decide the integration Task."""
    import ast

    src = Path(__file__).resolve().parent.parent / "substrate/execution/attempts/store.py"
    tree = ast.parse(src.read_text())
    banned = {"scenario_map", "integration_task_id", "read_scenario_map", "task_frontier"}

    # Docstrings are documentation, not code — and this invariant's rationale
    # legitimately names the artifacts it forbids READING. Forbidding the prose
    # would push the institutional memory out of the file that needs it most, so
    # only executable string constants are scanned.
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                doc_nodes.add(id(body[0].value))

    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        if id(node) in doc_nodes:
            continue
        assert not any(b in node.value for b in banned), (
            f"store.py names declaration state on line {node.lineno}: {node.value!r}"
        )


def test_attempt_creation_has_exactly_one_durable_write_path():
    """The invariant is only structural if there is ONE place to enforce it."""
    import ast

    src = Path(__file__).resolve().parent.parent / "substrate/execution/attempts/store.py"
    tree = ast.parse(src.read_text())
    writers = set()
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        for call in ast.walk(fn):
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "_append_line"
                and call.args
                and "_attempts_path" in ast.unparse(call.args[0])
            ):
                writers.add(fn.name)
    assert writers == {"create_attempt_idempotent"}, (
        f"attempt persistence is no longer a single boundary: {sorted(writers)} — "
        f"the structural invariant must be re-established at every writer"
    )


def test_no_unarmed_store_can_create_attempts():
    """DIRECT-PERSISTENCE LAW.

    Several production sites construct an ``ExecutionAttemptStore`` with no
    declaration (grant/read surfaces). That is only safe while none of them can
    CREATE an Attempt — otherwise they are an accidental bypass with no
    declaration to enforce. Pinned so a future edit cannot quietly add one.
    """
    import ast

    root = Path(__file__).resolve().parent.parent
    offenders = []
    for sub in ("substrate", "transports", "services", "scripts"):
        for path in (root / sub).rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "create_attempt_idempotent" not in text:
                continue
            rel = str(path.relative_to(root))
            # The scheduler is THE production creator and uses the armed store.
            if rel == "substrate/execution/attempts/scheduler.py":
                continue
            if rel == "substrate/execution/attempts/store.py":
                continue  # the definition itself
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for call in ast.walk(tree):
                if (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "create_attempt_idempotent"
                ):
                    offenders.append(f"{rel}:{call.lineno}")
    assert not offenders, (
        f"a production path outside the scheduler creates Attempts: {offenders} — "
        f"prove it cannot run in the Wave 2 governed namespace, or arm its store"
    )


def test_declaration_is_not_derived_from_the_map_field():
    """The builder must resolve lineage, never read ``integration_task_id``."""
    import ast

    src = (
        Path(__file__).resolve().parent.parent
        / "substrate/execution/attempts/field_scenario_map.py"
    )
    tree = ast.parse(src.read_text())
    fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "build_verified_declaration"
    )
    # It must resolve lineage...
    called = {
        n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "resolve_scenario_map" in called, "the declaration is not lineage-derived"
    # ...and never read the persisted map.
    assert "read_scenario_map" not in called


def test_declaration_builder_does_not_gate_on_grant_validity():
    """DECLARATION ≠ AUTHORIZATION, enforced structurally.

    Gating here would let an expired/revoked grant change a Task's durable
    execution CLASS — measured to reproduce the original defect.
    """
    import ast

    src = (
        Path(__file__).resolve().parent.parent
        / "substrate/execution/attempts/field_scenario_map.py"
    )
    tree = ast.parse(src.read_text())
    fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "build_verified_declaration"
    )
    called = {
        n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert "resolve_canonical_grant" not in called
    assert "build_from_records" not in called, "build_from_records gates on the grant"


def test_no_production_path_reads_the_declaration_field_for_safety():
    """Category-3 re-derivation (unsafe) must be ZERO in the control plane.

    Diagnostics may still read disk; nothing that decides execution_kind or
    worker eligibility may.
    """
    import ast

    src = (
        Path(__file__).resolve().parent.parent
        / "substrate/execution/attempts/field_control_plane.py"
    )
    tree = ast.parse(src.read_text())
    safety = {
        "_declared_integration_packet_id",
        "_declared_execution_class_for",
        "_validated_integration_packet_id",
        "_build_verified_declaration",
    }
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in safety):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and sub.value == "integration_task_id":
                pytest.fail(f"{node.name} reads the mutable declaration field at line {sub.lineno}")


# ─────────────────────────────────────────────────────────────────────────────
# MEDIUM FINDING CLOSURE — outcome/payload consistency, builder exception sealing
# ─────────────────────────────────────────────────────────────────────────────
def test_no_composition_with_declaration_payload_is_rejected():
    """NO_COMPOSITION must not carry a declaration — the payload is incoherent.

    A NO_COMPOSITION is a positive proof of ABSENCE. Attaching a declaration to
    it creates a value that claims "no composition Task exists" while
    simultaneously naming one, and any consumer that reads the declaration
    instead of the outcome tag gets a completely different answer.
    """
    from substrate.execution.attempts.records import (
        DeclarationOutcome,
        DeclarationResult,
        VerifiedExecutionDeclaration,
    )

    decl = VerifiedExecutionDeclaration(
        run_id="r",
        candidate_sha="c",
        digest="x",
        execution_classes=(("t", "worker"),),
    )
    with pytest.raises(ValueError, match="NO_COMPOSITION.*must not carry a declaration"):
        DeclarationResult(DeclarationOutcome.NO_COMPOSITION, declaration=decl)


def test_declared_without_declaration_payload_is_rejected():
    """DECLARED must carry a declaration — the payload is structurally required."""
    from substrate.execution.attempts.records import (
        DeclarationOutcome,
        DeclarationResult,
    )

    with pytest.raises(ValueError, match="DECLARED.*must carry a declaration"):
        DeclarationResult(DeclarationOutcome.DECLARED, declaration=None)


def test_builder_exception_inside_apply_propagates(tmp_path):
    """An AttributeError INSIDE apply_declaration_result must not be swallowed.

    The driver catches method-absence (getattr None) to tolerate stores that
    predate the invariant. But a bug INSIDE the method (None-access,
    field rename) must propagate — silent swallowing would leave the store
    sealed while the driver logs a benign warning, hiding a real defect.
    """
    from unittest.mock import MagicMock

    targets, ea = _tree(tmp_path)
    store = _store(ea)
    store.apply_declaration_result = MagicMock(
        side_effect=AttributeError("simulated bug inside apply")
    )
    with pytest.raises(AttributeError, match="simulated bug inside apply"):
        _driver(targets, store)
