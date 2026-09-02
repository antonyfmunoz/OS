"""Governed fan-in composition — behavioral tests on REAL git, stores and leases.

The load-bearing test here is ``test_full_a_b_c_d_production_path``: one
production-shaped A+B→C→D execution driven through the REAL AttemptScheduler,
ExecutionAttemptStore, LeaseManager, SandboxManager, composition producer,
lifecycle CAS, git plumbing, ProofRuntime and terminalization. The direct helper
tests below it are supplemental — they localize a failure once the integrated
test has proven the wiring exists at all.

Nothing here mocks composition, scheduling, lifecycle, git, Proof, retention or
sandbox semantics. Only the model worker is absent, because the whole point of a
composition attempt is that no model worker runs.
"""

from __future__ import annotations

import os
import subprocess
from copy import deepcopy
from types import SimpleNamespace

import pytest

from substrate.execution.attempts.composition import (
    COMPOSED_ROOT,
    CompositionConflict,
    CompositionError,
    assert_descends_from_all,
    compose_predecessors,
    composed_ref,
    composition_proof_action,
    existing_composition_proof,
    list_composed_refs,
    list_trusted_refs,
    mint_composition_proof,
    release_composed_refs,
    resolve_composed_commit,
    resolve_downstream_base,
    resolve_predecessor_commits,
    verify_predecessor_content,
)
from substrate.execution.attempts.field_control_plane import (
    _IMPLEMENTER_ROLE_ID,
    _default_role_resolver,
    _verifier_role_resolver,
)
from substrate.execution.attempts.lifecycle import AttemptLifecycleError, validate_transition
from substrate.execution.attempts.records import (
    AttemptExecutionKind,
    ExecutionAttempt,
    ExecutionAttemptStatus,
)
from substrate.execution.attempts.store import AttemptStoreConflict, ExecutionAttemptStore
from substrate.execution.attempts.verified_commit_retention import (
    resolve_trusted_commit,
    retain_verified_commit,
)

_S = ExecutionAttemptStatus
_K = AttemptExecutionKind

CAND = "9a8c4a30620cfde5cec7b05e7a54d625ee6cd450"
RUN = "20260805T182714Z-p1"

TASK_A = "wp-backend00001"
TASK_B = "wp-frontend0001"
TASK_C = "wp-integration1"
TASK_D = "wp-verification"


def _zero_ref_proof() -> dict:
    return {
        "ok": True,
        "zero_ref_residue": True,
        "ref_residue": [],
        "ref_inventory": [],
        "ref_enumeration_executed": True,
        "unexpected_ref_count": 0,
    }


def _git(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    """A real fixture repo in the CANONICAL candidate layout."""
    r = str(tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN / "fixture")
    os.makedirs(r)
    _git(["init", "-q", "-b", "master"], r)
    _git(["config", "user.email", "t@t"], r)
    _git(["config", "user.name", "t"], r)
    os.makedirs(f"{r}/app/static")
    os.makedirs(f"{r}/tests")
    open(f"{r}/app/main.py", "w").write("base\n")
    open(f"{r}/app/store.py", "w").write("store\n")
    open(f"{r}/app/static/index.html", "w").write("<html>\n")
    open(f"{r}/tests/test_api.py", "w").write("def test_base():\n    assert 1\n")
    _git(["add", "-A"], r)
    _git(["commit", "-qm", "fixture: base notes app (green)"], r)
    return r


def _store(tmp_path, tag="x"):
    return ExecutionAttemptStore(
        attempts_path=str(tmp_path / f"a{tag}.jsonl"),
        grants_path=str(tmp_path / f"g{tag}.jsonl"),
        readiness_path=str(tmp_path / f"r{tag}.jsonl"),
        leases_path=str(tmp_path / f"l{tag}.jsonl"),
        assignments_path=str(tmp_path / f"asn{tag}.jsonl"),
    )


def _lane(repo: str, branch: str, files: dict[str, str], *, base: str) -> str:
    """Commit one lane's slice on its own branch. Returns the commit sha."""
    _git(["checkout", "-q", base], repo)
    _git(["checkout", "-qb", branch], repo)
    for path, content in files.items():
        full = os.path.join(repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w").write(content)
    _git(["add", "-A"], repo)
    _git(["commit", "-qm", branch], repo)
    return _git(["rev-parse", "HEAD"], repo).stdout.strip()


def _succeeded(
    store,
    task_id: str,
    attempt_id: str,
    *,
    kind=_K.WORKER.value,
    commits=None,
    attempt_number: int = 1,
):
    """Persist a SUCCEEDED attempt directly (the predecessor lanes' end state).

    ``attempt_number`` is part of the store's idempotency key
    ``(task_id, execution_authorization_ref, attempt_number)``, so two records
    for one Task must differ in it — otherwise the store correctly returns the
    first record and no duplicate is ever written.
    """
    att = ExecutionAttempt(
        attempt_id=attempt_id,
        task_id=task_id,
        execution_kind=kind,
        status=_S.SUCCEEDED.value,
        proof_id=f"proof-{attempt_id}",
        commits=list(commits or []),
        attempt_number=attempt_number,
    )
    store.create_attempt_idempotent(att)
    return att


# ══════════════════════════════════════════════════════════════════════════
# 1-3, 6-7, 9-10: composition core on real git
# ══════════════════════════════════════════════════════════════════════════
def _two_lanes(repo):
    base = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    a = _lane(
        repo,
        "laneA",
        {
            "app/main.py": "base\nBACKEND\n",
            "tests/test_search_api.py": "def test_backend():\n    assert 1\n",
        },
        base=base,
    )
    b = _lane(
        repo,
        "laneB",
        {
            "app/static/index.html": "<html>ui</html>\n",
            "tests/test_ui_search.py": "def test_ui():\n    assert 1\n",
        },
        base=base,
    )
    return base, a, b


def test_parallel_predecessors_produce_distinct_verified_commits(repo):
    _base, a, b = _two_lanes(repo)
    assert a != b, "A and B must produce distinct commits"


def test_both_predecessors_retained_under_trusted_refs(repo, tmp_path):
    _base, a, b = _two_lanes(repo)
    for task, sha in ((TASK_A, a), (TASK_B, b)):
        _git(["update-ref", f"refs/umh/verified/{CAND}/{RUN}/{task}/ea-{task}", sha], repo)
    assert (
        resolve_trusted_commit(
            repo=repo, candidate=CAND, run_id=RUN, task_id=TASK_A, attempt_id=f"ea-{TASK_A}"
        )
        == a
    )
    assert (
        resolve_trusted_commit(
            repo=repo, candidate=CAND, run_id=RUN, task_id=TASK_B, attempt_id=f"ea-{TASK_B}"
        )
        == b
    )


def test_composition_includes_both_trees(repo):
    _base, a, b = _two_lanes(repo)
    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-c1",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    assert r.ok
    for path in (
        "app/main.py",
        "app/static/index.html",
        "tests/test_search_api.py",
        "tests/test_ui_search.py",
    ):
        got = _git(["rev-parse", f"{r.tree_sha}:{path}"], repo)
        assert got.returncode == 0, f"{path} missing from the composed tree"


def test_deterministic_tree_regardless_of_completion_order(repo):
    """Completion order must not change the composition.

    Both halves matter. The TREE is order-independent in git itself (measured),
    so tree equality alone would ALSO hold without canonical sorting — it cannot
    detect a lost sort. Parent ORDER is what sorting actually protects, and
    parent order changes the COMMIT sha (measured), so the canonical ordering is
    asserted directly on the recorded predecessors and on the commit's parents.
    """
    _base, a, b = _two_lanes(repo)
    forward = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-f",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    reversed_ = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-r",
        predecessor_commits={TASK_B: b, TASK_A: a},
    )
    assert forward.tree_sha == reversed_.tree_sha

    # CANONICAL ORDER: by task_id, whichever order the caller supplied.
    assert list(forward.predecessor_commits) == sorted([TASK_A, TASK_B])
    assert list(reversed_.predecessor_commits) == sorted([TASK_A, TASK_B])

    def _parents(sha):
        body = _git(["cat-file", "-p", sha], repo).stdout
        return [ln.split()[1] for ln in body.splitlines() if ln.startswith("parent ")]

    canonical = [forward.predecessor_commits[t] for t in sorted([TASK_A, TASK_B])]
    assert _parents(forward.composed_commit) == canonical
    assert _parents(reversed_.composed_commit) == canonical, (
        "reversing the caller's order must NOT reorder the commit's parents"
    )


def test_commit_identity_deterministic_within_attempt(repo):
    """COMMIT identity is deterministic for ONE attempt, and every pinned
    component is asserted individually — author metadata cannot be proven by a
    tree-determinism test, because it does not affect the tree."""
    _base, a, b = _two_lanes(repo)
    kw = dict(repo=repo, candidate=CAND, run_id=RUN, task_id=TASK_C)
    first = compose_predecessors(
        attempt_id="ea-det", predecessor_commits={TASK_A: a, TASK_B: b}, **kw
    )
    # Re-running for the SAME attempt reuses the pinned ref (idempotent).
    again = compose_predecessors(
        attempt_id="ea-det", predecessor_commits={TASK_A: a, TASK_B: b}, **kw
    )
    assert again.composed_commit == first.composed_commit
    assert again.reused_existing is True

    body = _git(["cat-file", "-p", first.composed_commit], repo).stdout
    assert "author umh-composer <composer@umh.internal> 1700000000 +0000" in body
    assert "committer umh-composer <composer@umh.internal> 1700000000 +0000" in body
    # Canonical parent ORDER: sorted by task_id, not completion order.
    parents = [ln.split()[1] for ln in body.splitlines() if ln.startswith("parent ")]
    assert parents == sorted([a, b], key=lambda s: {a: TASK_A, b: TASK_B}[s])
    assert "[attempt:ea-det]" in body

    # A DIFFERENT attempt yields a different commit over the SAME tree.
    other = compose_predecessors(
        attempt_id="ea-other", predecessor_commits={TASK_A: a, TASK_B: b}, **kw
    )
    assert other.tree_sha == first.tree_sha
    assert other.composed_commit != first.composed_commit


def test_conflict_raises_composition_conflict(repo):
    base = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    a = _lane(repo, "cA", {"app/main.py": "base\nAAA\n"}, base=base)
    c = _lane(repo, "cC", {"app/main.py": "base\nCCC\n"}, base=base)
    with pytest.raises(CompositionConflict) as ei:
        compose_predecessors(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            task_id=TASK_C,
            attempt_id="ea-x",
            predecessor_commits={TASK_A: a, TASK_B: c},
        )
    assert "app/main.py" in str(ei.value)


def test_missing_predecessor_is_error_not_conflict(repo):
    """MEASURED: git returns rc=1 for BOTH a real conflict and an unmergeable
    object. Classifying on rc alone would report a missing/GC'd verified commit
    as a content conflict — the wrong failure class entirely."""
    _base, a, _b = _two_lanes(repo)
    with pytest.raises(CompositionError) as ei:
        compose_predecessors(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            task_id=TASK_C,
            attempt_id="ea-m",
            predecessor_commits={TASK_A: a, TASK_B: "d" * 40},
        )
    assert not isinstance(ei.value, CompositionConflict), "must NOT be a conflict"
    assert "does not resolve to a commit" in str(ei.value)


def test_exactly_two_predecessors_required(repo):
    _base, a, _b = _two_lanes(repo)
    with pytest.raises(CompositionError):
        compose_predecessors(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            task_id=TASK_C,
            attempt_id="ea-1",
            predecessor_commits={TASK_A: a},
        )


def test_only_succeeded_verified_predecessors_included(repo, tmp_path):
    """Failed / unproven / unretained predecessors are excluded, not tolerated."""
    _base, a, b = _two_lanes(repo)
    store = _store(tmp_path, "excl")

    # A failed attempt for TASK_A → no SUCCEEDED attempt at all.
    store.create_attempt_idempotent(
        ExecutionAttempt(attempt_id="ea-failA", task_id=TASK_A, status=_S.FAILED.value)
    )
    _succeeded(store, TASK_B, "ea-okB")
    with pytest.raises(CompositionError, match="no SUCCEEDED attempt"):
        resolve_predecessor_commits(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=store,
            dependency_task_ids=[TASK_A, TASK_B],
        )

    # SUCCEEDED but with NO durable proof_id.
    store2 = _store(tmp_path, "excl2")
    store2.create_attempt_idempotent(
        ExecutionAttempt(attempt_id="ea-noproof", task_id=TASK_A, status=_S.SUCCEEDED.value)
    )
    _succeeded(store2, TASK_B, "ea-okB2")
    with pytest.raises(CompositionError, match="without a proof_id"):
        resolve_predecessor_commits(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=store2,
            dependency_task_ids=[TASK_A, TASK_B],
        )

    # SUCCEEDED + proof, but nothing retained under refs/umh/verified.
    store3 = _store(tmp_path, "excl3")
    _succeeded(store3, TASK_A, "ea-a3")
    _succeeded(store3, TASK_B, "ea-b3")
    with pytest.raises(CompositionError, match="no retained commit"):
        resolve_predecessor_commits(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=store3,
            dependency_task_ids=[TASK_A, TASK_B],
        )


def test_duplicate_succeeded_attempts_refused(repo, tmp_path):
    store = _store(tmp_path, "dup")
    _succeeded(store, TASK_A, "ea-dup1", attempt_number=1)
    _succeeded(store, TASK_A, "ea-dup2", attempt_number=2)
    _succeeded(store, TASK_B, "ea-b")
    with pytest.raises(CompositionError, match="ambiguous lineage"):
        resolve_predecessor_commits(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=store,
            dependency_task_ids=[TASK_A, TASK_B],
        )


# ══════════════════════════════════════════════════════════════════════════
# Content equivalence — MEASURED per-operation semantics
# ══════════════════════════════════════════════════════════════════════════
def test_predecessor_deletion_preserved_as_absence(repo):
    """A deletion must be ABSENT in the composed tree. "present with the same
    blob" is the WRONG rule for a delete and would silently lose it."""
    base = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    _git(["checkout", "-q", base], repo)
    _git(["checkout", "-qb", "delA"], repo)
    os.remove(os.path.join(repo, "app/store.py"))
    _git(["add", "-A"], repo)
    _git(["commit", "-qm", "delete"], repo)
    a = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    b = _lane(repo, "addB", {"app/newB.py": "b\n"}, base=base)

    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-del",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    assert _git(["rev-parse", f"{r.tree_sha}:app/store.py"], repo).returncode != 0

    ok, violations, produced = verify_predecessor_content(
        repo=repo,
        base=base,
        composed_tree=r.tree_sha,
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    assert ok, violations
    assert "app/newB.py" in produced


def test_mode_change_preserved(repo):
    base = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    _git(["checkout", "-q", base], repo)
    _git(["checkout", "-qb", "modeA"], repo)
    os.chmod(os.path.join(repo, "app/main.py"), 0o755)
    _git(["add", "-A"], repo)
    _git(["commit", "-qm", "mode"], repo)
    a = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    b = _lane(repo, "modeB", {"app/other.py": "o\n"}, base=base)

    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-mode",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    entry = _git(["ls-tree", r.tree_sha, "--", "app/main.py"], repo).stdout
    assert entry.startswith("100755"), f"mode change lost: {entry!r}"
    ok, violations, _ = verify_predecessor_content(
        repo=repo,
        base=base,
        composed_tree=r.tree_sha,
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    assert ok, violations


def test_rename_and_empty_file_preserved(repo):
    base = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    _git(["checkout", "-q", base], repo)
    _git(["checkout", "-qb", "renA"], repo)
    _git(["mv", "app/store.py", "app/renamed.py"], repo)
    open(os.path.join(repo, "app/empty.txt"), "w").close()
    _git(["add", "-A"], repo)
    _git(["commit", "-qm", "rename+empty"], repo)
    a = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    b = _lane(repo, "renB", {"app/bb.py": "b\n"}, base=base)

    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-ren",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    assert _git(["rev-parse", f"{r.tree_sha}:app/store.py"], repo).returncode != 0
    assert _git(["rev-parse", f"{r.tree_sha}:app/renamed.py"], repo).returncode == 0
    empty = _git(["rev-parse", f"{r.tree_sha}:app/empty.txt"], repo).stdout.strip()
    assert empty == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    ok, violations, _ = verify_predecessor_content(
        repo=repo,
        base=base,
        composed_tree=r.tree_sha,
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    assert ok, violations


def test_lost_predecessor_content_is_detected(repo):
    """The content check must FAIL when a predecessor effect is missing —
    otherwise it certifies nothing."""
    base = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    _base, a, b = _two_lanes(repo)
    # Compose, then verify A's effects against the BASE tree (which has none of
    # them) — a stand-in for a composition that dropped a lane.
    ok, violations, _ = verify_predecessor_content(
        repo=repo, base=base, composed_tree=base, predecessor_commits={TASK_A: a, TASK_B: b}
    )
    assert not ok
    assert any("ABSENT" in v for v in violations)


def test_composed_commit_descends_from_both_parents(repo):
    base = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    _base, a, b = _two_lanes(repo)
    unrelated = _lane(repo, "unrel", {"app/u.py": "u\n"}, base=base)
    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-anc",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    assert (
        assert_descends_from_all(
            repo=repo,
            composed_commit=r.composed_commit,
            predecessor_commits={TASK_A: a, TASK_B: b},
        )
        == []
    )
    failed = assert_descends_from_all(
        repo=repo,
        composed_commit=r.composed_commit,
        predecessor_commits={TASK_A: a, "wp-unrelated": unrelated},
    )
    assert failed == ["wp-unrelated"]


# ══════════════════════════════════════════════════════════════════════════
# Lifecycle: worker attempts can NEVER use the composition path
# ══════════════════════════════════════════════════════════════════════════
def test_worker_kind_cannot_transition_leased_to_verifying():
    worker = ExecutionAttempt(
        attempt_id="ea-w",
        task_id=TASK_C,
        status=_S.LEASED.value,
        execution_kind=_K.WORKER.value,
        worker_identity="cc-cli@vps-host",
    )
    with pytest.raises(AttemptLifecycleError, match="requires persisted execution_kind"):
        validate_transition(worker, _S.VERIFYING.value, "composer:control-plane", {})


def test_composition_kind_with_worker_identity_refused():
    att = ExecutionAttempt(
        attempt_id="ea-c",
        task_id=TASK_C,
        status=_S.LEASED.value,
        execution_kind=_K.CONTROL_PLANE_COMPOSITION.value,
        worker_identity="cc-cli@vps-host",
    )
    with pytest.raises(AttemptLifecycleError, match="carries NO worker identity"):
        validate_transition(att, _S.VERIFYING.value, "composer:control-plane", {})


def test_composition_leased_to_verifying_allowed():
    att = ExecutionAttempt(
        attempt_id="ea-c",
        task_id=TASK_C,
        status=_S.LEASED.value,
        execution_kind=_K.CONTROL_PLANE_COMPOSITION.value,
    )
    validate_transition(att, _S.VERIFYING.value, "composer:control-plane", {})


def test_execution_kind_immutable_via_updates(tmp_path):
    """A caller must not be able to promote a worker attempt into the
    composition lifecycle through a binding update."""
    store = _store(tmp_path, "imm")
    att = ExecutionAttempt(attempt_id="ea-imm", task_id=TASK_C, status=_S.CREATED.value)
    created, _ = store.create_attempt_idempotent(att)
    with pytest.raises(AttemptStoreConflict, match="immutable identity fields"):
        store.transition_cas(
            created.attempt_id,
            _S.READY.value,
            created.record_version,
            (_S.CREATED.value,),
            "scheduler",
            "promote",
            updates={"execution_kind": _K.CONTROL_PLANE_COMPOSITION.value},
        )


def test_updates_cannot_satisfy_the_composition_guard():
    """The guard reads PERSISTED state, so a worker attempt cannot pass by
    supplying the kind (or blanking its worker) in `updates`."""
    worker = ExecutionAttempt(
        attempt_id="ea-w2",
        task_id=TASK_C,
        status=_S.LEASED.value,
        execution_kind=_K.WORKER.value,
        worker_identity="cc-cli@vps-host",
    )
    with pytest.raises(AttemptLifecycleError):
        validate_transition(
            worker,
            _S.VERIFYING.value,
            "composer:control-plane",
            {"execution_kind": _K.CONTROL_PLANE_COMPOSITION.value, "worker_identity": ""},
        )


def test_legacy_record_without_kind_defaults_to_worker():
    att = ExecutionAttempt.from_dict(
        {"attempt_id": "ea-legacy", "task_id": TASK_C, "status": _S.LEASED.value}
    )
    assert att.execution_kind == _K.WORKER.value
    with pytest.raises(AttemptLifecycleError):
        validate_transition(att, _S.VERIFYING.value, "composer:control-plane", {})


# ══════════════════════════════════════════════════════════════════════════
# Proof: exactly ONE authoritative durable Proof per composition Attempt
# ══════════════════════════════════════════════════════════════════════════
class _Runtime:
    """The real ProofRuntime against a temp store path."""

    def __new__(cls, path):
        from substrate.organism.proof_runtime import ProofRuntime

        return ProofRuntime(store_path=str(path))


def test_two_historical_proofs_one_work_id_both_enumerable(tmp_path):
    """The restart guarantee the idempotency design rests on: `_packages` is
    keyed by proof_id, so two records sharing a work_id BOTH survive a reload.
    (Only the separate `_by_work_id` index is last-write-wins.)"""
    path = tmp_path / "proofs.jsonl"
    rt = _Runtime(path)
    rt.create_direct(TASK_C, {"attempt_id": "ea-1", "task_id": TASK_C}, operator="v")
    rt.create_direct(TASK_C, {"attempt_id": "ea-2", "task_id": TASK_C}, operator="v")

    fresh = _Runtime(path)  # simulate a process restart
    all_proofs = [p for p in fresh.all_proofs() if p.work_id == TASK_C]
    assert len(all_proofs) == 2, "both historical proofs must remain enumerable"
    for p in all_proofs:
        assert fresh.reread_durable(p.proof_id) is not None


def test_composition_proof_reused_on_restart(tmp_path, repo):
    _base, a, b = _two_lanes(repo)
    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-p",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    att = ExecutionAttempt(
        attempt_id="ea-p", task_id=TASK_C, execution_kind=_K.CONTROL_PLANE_COMPOSITION.value
    )
    action = composition_proof_action(attempt=att, result=r, predecessor_proofs={})
    path = tmp_path / "proofs.jsonl"

    first = mint_composition_proof(
        proof_runtime=_Runtime(path), attempt=att, action=action, verifier_identity="v"
    )
    # Fresh runtime == restart. Must REUSE, never mint a second authority.
    second = mint_composition_proof(
        proof_runtime=_Runtime(path), attempt=att, action=action, verifier_identity="v"
    )
    assert second.proof_id == first.proof_id

    bound = [p for p in _Runtime(path).all_proofs() if (p.action or {}).get("attempt_id") == "ea-p"]
    assert len({p.proof_id for p in bound}) == 1


def test_conflicting_proof_for_same_attempt_fails_closed(tmp_path, repo):
    _base, a, b = _two_lanes(repo)
    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-q",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    att = ExecutionAttempt(
        attempt_id="ea-q", task_id=TASK_C, execution_kind=_K.CONTROL_PLANE_COMPOSITION.value
    )
    action = composition_proof_action(attempt=att, result=r, predecessor_proofs={})
    path = tmp_path / "proofs.jsonl"
    rt = _Runtime(path)
    rt.create_direct(TASK_C, action, operator="v")

    divergent = dict(action, composed_commit="f" * 40, tree_sha="e" * 40)
    with pytest.raises(CompositionError, match="DIFFERENT composition"):
        existing_composition_proof(
            proof_runtime=_Runtime(path), attempt=att, expected_action=divergent
        )


def test_incomplete_legacy_composition_proof_for_same_attempt_is_not_reused(tmp_path, repo):
    _base, a, b = _two_lanes(repo)
    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-legacy-proof",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    att = ExecutionAttempt(
        attempt_id="ea-legacy-proof",
        task_id=TASK_C,
        execution_kind=_K.CONTROL_PLANE_COMPOSITION.value,
    )
    full = composition_proof_action(
        attempt=att,
        result=r,
        predecessor_proofs={TASK_A: "proof-a", TASK_B: "proof-b"},
        run_id=RUN,
        candidate_sha=CAND,
    )
    legacy_shallow = {
        "attempt_id": att.attempt_id,
        "task_id": TASK_C,
        "composed_commit": r.composed_commit,
        "tree_sha": r.tree_sha,
        "predecessor_commits": dict(r.predecessor_commits),
    }
    path = tmp_path / "proofs-legacy.jsonl"
    rt = _Runtime(path)
    rt.create_direct(TASK_C, legacy_shallow, operator="v")

    with pytest.raises(CompositionError, match="DIFFERENT composition"):
        mint_composition_proof(
            proof_runtime=_Runtime(path),
            attempt=att,
            action=full,
            verifier_identity="v",
        )


def test_foreign_proof_is_not_accepted_for_this_attempt(tmp_path, repo):
    """Another Attempt's Proof must not satisfy this one."""
    path = tmp_path / "proofs.jsonl"
    rt = _Runtime(path)
    rt.create_direct(TASK_C, {"attempt_id": "ea-OTHER", "task_id": TASK_C}, operator="v")
    att = ExecutionAttempt(attempt_id="ea-mine", task_id=TASK_C)
    assert (
        existing_composition_proof(
            proof_runtime=_Runtime(path), attempt=att, expected_action={"attempt_id": "ea-mine"}
        )
        is None
    )


# ══════════════════════════════════════════════════════════════════════════
# Downstream trusted base
# ══════════════════════════════════════════════════════════════════════════
def _authoritative_downstream_fixture(repo, tmp_path, tag="auth"):
    _base, a, b = _two_lanes(repo)
    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id=f"ea-{tag}",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    store = _store(tmp_path, tag)
    path = tmp_path / f"proofs-{tag}.jsonl"
    rt = _Runtime(path)
    pred_a = _succeeded(store, TASK_A, f"ea-a-{tag}", commits=[a])
    pred_b = _succeeded(store, TASK_B, f"ea-b-{tag}", commits=[b])
    for task, att, sha in ((TASK_A, pred_a, a), (TASK_B, pred_b, b)):
        _git(["update-ref", f"refs/umh/verified/{CAND}/{RUN}/{task}/{att.attempt_id}", sha], repo)
    att = ExecutionAttempt(
        attempt_id=f"ea-{tag}",
        task_id=TASK_C,
        execution_kind=_K.CONTROL_PLANE_COMPOSITION.value,
        status=_S.SUCCEEDED.value,
        commits=[r.composed_commit],
        correlation_id=f"w2-{RUN}",
    )
    action = composition_proof_action(
        attempt=att,
        result=r,
        predecessor_proofs={TASK_A: pred_a.proof_id, TASK_B: pred_b.proof_id},
        run_id=RUN,
        candidate_sha=CAND,
    )
    return SimpleNamespace(
        result=r,
        store=store,
        proof_path=path,
        runtime=rt,
        attempt=att,
        action=action,
        predecessor_commits={TASK_A: a, TASK_B: b},
        predecessor_proofs={TASK_A: pred_a.proof_id, TASK_B: pred_b.proof_id},
    )


def test_downstream_base_requires_full_authority_chain(repo, tmp_path):
    fixture = _authoritative_downstream_fixture(repo, tmp_path, "base")
    proof = fixture.runtime.create_direct(TASK_C, fixture.action, operator="v")
    fixture.attempt.proof_id = proof.proof_id
    fixture.store.create_attempt_idempotent(fixture.attempt)

    assert (
        resolve_downstream_base(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=fixture.store,
            proof_runtime=_Runtime(fixture.proof_path),
            dependency_task_ids=[TASK_C],
        )
        == fixture.result.composed_commit
    )

    # A WORKER dependency contributes no composed base (→ default HEAD).
    store2 = _store(tmp_path, "base2")
    _succeeded(store2, TASK_C, "ea-worker", kind=_K.WORKER.value)
    assert (
        resolve_downstream_base(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=store2,
            proof_runtime=_Runtime(fixture.proof_path),
            dependency_task_ids=[TASK_C],
        )
        == ""
    )


@pytest.mark.parametrize(
    ("field", "value", "pattern"),
    [
        ("task_id", "wp-foreign", "task_id"),
        ("kind", _K.WORKER.value, "kind"),
        ("composed_commit", "f" * 40, "composed_commit"),
        ("tree_sha", "e" * 40, "tree_sha"),
        ("merge_base", "e" * 40, "merge_base"),
        ("run_id", "20260101T000000Z-x", "run_id"),
        ("candidate_sha", "0" * 40, "candidate_sha"),
        ("composed_ref", "refs/umh/composed/foreign/run/task/attempt", "composed_ref"),
        ("predecessor_a_commit", "e" * 40, "trusted commit"),
        ("predecessor_b_proof", "proof-substituted", "Proof ID mismatch"),
    ],
)
def test_downstream_base_rejects_tampered_composition_proof_binding(
    repo, tmp_path, field, value, pattern
):
    fixture = _authoritative_downstream_fixture(repo, tmp_path, f"tamper-{field}")
    action = deepcopy(fixture.action)
    if field == "predecessor_a_commit":
        action["predecessor_commits"][TASK_A] = value
    elif field == "predecessor_b_proof":
        action["predecessor_proof_ids"][TASK_B] = value
    else:
        action[field] = value
    proof = fixture.runtime.create_direct(TASK_C, action, operator="v")
    fixture.attempt.proof_id = proof.proof_id
    fixture.store.create_attempt_idempotent(fixture.attempt)

    with pytest.raises(CompositionError, match=pattern):
        resolve_downstream_base(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=fixture.store,
            proof_runtime=_Runtime(fixture.proof_path),
            dependency_task_ids=[TASK_C],
        )


def test_downstream_base_refuses_undurable_proof(repo, tmp_path):
    _base, a, b = _two_lanes(repo)
    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-nd",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    store = _store(tmp_path, "nd")
    store.create_attempt_idempotent(
        ExecutionAttempt(
            attempt_id="ea-nd",
            task_id=TASK_C,
            execution_kind=_K.CONTROL_PLANE_COMPOSITION.value,
            status=_S.SUCCEEDED.value,
            proof_id="proof-never-persisted",
            commits=[r.composed_commit],
        )
    )
    with pytest.raises(CompositionError, match="not durably persisted"):
        resolve_downstream_base(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=store,
            proof_runtime=_Runtime(tmp_path / "p.jsonl"),
            dependency_task_ids=[TASK_C],
        )


def test_downstream_base_refuses_missing_composed_ref(repo, tmp_path):
    store = _store(tmp_path, "mr")
    path = tmp_path / "proofs.jsonl"
    rt = _Runtime(path)
    proof = rt.create_direct(TASK_C, {"attempt_id": "ea-mr", "task_id": TASK_C}, operator="v")
    store.create_attempt_idempotent(
        ExecutionAttempt(
            attempt_id="ea-mr",
            task_id=TASK_C,
            execution_kind=_K.CONTROL_PLANE_COMPOSITION.value,
            status=_S.SUCCEEDED.value,
            proof_id=proof.proof_id,
        )
    )
    with pytest.raises(CompositionError, match="no composed ref"):
        resolve_downstream_base(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=store,
            proof_runtime=_Runtime(path),
            dependency_task_ids=[TASK_C],
        )


# ══════════════════════════════════════════════════════════════════════════
# Terminalization: composition NEVER uses worker retention
# ══════════════════════════════════════════════════════════════════════════
def test_composition_skips_worker_retention_by_kind(repo, tmp_path):
    """The composed ref is the authority; retention must not mint a rival
    refs/umh/verified ref (nor retain the pre-composition worktree HEAD)."""
    from substrate.execution.attempts.terminalization import _retain_verified

    class _Res:
        def __init__(self):
            self.attempt_id = "ea-comp"
            self.task_id = TASK_C
            self.lease_id = "lease-1"
            self.steps: list[str] = []
            self.errors: list[str] = []
            self.retained_commit = ""

    att = ExecutionAttempt(
        attempt_id="ea-comp",
        task_id=TASK_C,
        execution_kind=_K.CONTROL_PLANE_COMPOSITION.value,
        status=_S.SUCCEEDED.value,
    )
    res = _Res()
    _retain_verified(res, att, SimpleNamespace(_store=None), "succeeded")
    assert res.retained_commit == ""
    assert res.errors == []
    assert any("refs/umh/composed" in s for s in res.steps)
    assert list_trusted_refs(repo=repo, candidate=CAND, run_id=RUN) == []


def test_worker_retention_path_unchanged(repo, tmp_path):
    """Ordinary worker retention must remain behaviorally identical."""
    _base, a, _b = _two_lanes(repo)
    _git(["checkout", "-q", "laneA"], repo)
    sha = retain_verified_commit(
        repo=repo,
        worktree=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_A,
        attempt_id="ea-worker",
    )
    assert sha == a
    assert (
        resolve_trusted_commit(
            repo=repo, candidate=CAND, run_id=RUN, task_id=TASK_A, attempt_id="ea-worker"
        )
        == a
    )


# ══════════════════════════════════════════════════════════════════════════
# Cleanup + zero-residue law
# ══════════════════════════════════════════════════════════════════════════
def test_teardown_releases_both_namespaces_and_proves_zero(repo, tmp_path):
    from substrate.execution.attempts.run_teardown import sweep_run

    _base, a, b = _two_lanes(repo)
    for task, sha in ((TASK_A, a), (TASK_B, b)):
        _git(["update-ref", f"refs/umh/verified/{CAND}/{RUN}/{task}/ea-{task}", sha], repo)
    compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-td",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    assert list_trusted_refs(repo=repo, candidate=CAND, run_id=RUN)
    assert list_composed_refs(repo=repo, candidate=CAND, run_id=RUN)

    run_root = str(tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN)
    res = sweep_run(run_root, repo_root=repo, candidate=CAND, run_id=RUN)
    assert res.ref_residue == [], res.ref_residue
    assert res.zero_ref_residue is True
    assert len(res.refs_deleted) == 3
    assert list_trusted_refs(repo=repo, candidate=CAND, run_id=RUN) == []
    assert list_composed_refs(repo=repo, candidate=CAND, run_id=RUN) == []

    # Idempotent: a second sweep is a clean no-op.
    again = sweep_run(run_root, repo_root=repo, candidate=CAND, run_id=RUN)
    assert again.zero_ref_residue is True
    assert again.refs_deleted == []


def test_quarantined_ref_is_still_residue(repo, tmp_path, monkeypatch):
    """Operational teardown MAY complete with a quarantined ref; zero-residue
    qualification must still FAIL. "We wrote down that we leaked it" is not
    "we did not leak it"."""
    import substrate.execution.attempts.composition as comp
    from substrate.execution.attempts.run_teardown import sweep_run

    _base, a, b = _two_lanes(repo)
    compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-qr",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )

    def _refuse(**kw):
        raise comp.CompositionError("simulated ref-deletion failure")

    monkeypatch.setattr(comp, "release_composed_refs", _refuse)

    run_root = str(tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN)
    res = sweep_run(run_root, repo_root=repo, candidate=CAND, run_id=RUN)

    assert res.ref_residue, "surviving ref must be accounted as residue"
    assert set(res.quarantined_refs) <= set(res.ref_residue), "quarantine ⊆ residue"
    assert res.zero_ref_residue is False, "qualification must FAIL"
    assert res.ok is True, "operational teardown may still complete"


def test_qualification_gate_fails_on_ref_residue():
    """The PRODUCTION caller-side gate, not just the sweep result."""
    import importlib.util
    import sys

    name = "_w2fd_qualification"
    spec = importlib.util.spec_from_file_location(
        name,
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts",
            "wave2_field_dispatch.py",
        ),
    )
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE exec: the module defines dataclasses, and dataclass field
    # resolution looks the owning module up in sys.modules. Without this the
    # import fails with AttributeError on NoneType.__dict__.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)

    clean = {
        "run_id": "r1",
        "torn_down": [],
        "collector": {"stopped": True},
        "run_secret_shredded": True,
        "serve_restored": True,
        "homes_swept": _zero_ref_proof(),
    }
    v_ok = mod.qualification_verdict("teardown", clean)
    assert v_ok.mandatory.get("teardown:zero_ref_residue") is True
    assert v_ok.ok is True

    leaked = {
        "torn_down": [],
        "run_secret_shredded": True,
        "serve_restored": True,
        "homes_swept": {
            "ok": True,
            "zero_ref_residue": False,
            "ref_residue": [f"{COMPOSED_ROOT}/{CAND}/{RUN}/{TASK_C}/ea-1"],
            "quarantined_refs": [f"{COMPOSED_ROOT}/{CAND}/{RUN}/{TASK_C}/ea-1"],
        },
    }
    v_bad = mod.qualification_verdict("teardown", leaked)
    assert v_bad.mandatory.get("teardown:zero_ref_residue") is False
    assert v_bad.ok is False
    assert any("quarantine accounts for a leak" in r for r in v_bad.reasons)

    # A teardown result predating the field must FAIL, never hide behind absence.
    legacy = {
        "torn_down": [],
        "run_secret_shredded": True,
        "serve_restored": True,
        "homes_swept": {"ok": True},
    }
    assert mod.qualification_verdict("teardown", legacy).ok is False


def test_composed_ref_cas_blocks_double_write(repo):
    _base, a, b = _two_lanes(repo)
    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-cas",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    ref = composed_ref(candidate=CAND, run_id=RUN, task_id=TASK_C, attempt_id="ea-cas")
    assert r.composed_ref == ref
    # A rival value cannot claim the same ref (CAS must-not-exist).
    rc = _git(["update-ref", ref, a, ""], repo)
    assert rc.returncode != 0
    assert (
        resolve_composed_commit(
            repo=repo, candidate=CAND, run_id=RUN, task_id=TASK_C, attempt_id="ea-cas"
        )
        == r.composed_commit
    )


# ══════════════════════════════════════════════════════════════════════════
# THE LOAD-BEARING TEST: production-shaped A+B → C → D
# ══════════════════════════════════════════════════════════════════════════
def _prod_grant(tmp_path, frontier: list[str]):
    import time as _t

    from substrate.execution.attempts.records import ExecutionAuthorizationGrant

    grant = ExecutionAuthorizationGrant(
        decision_ref="objective_plan:opr-fanin:execution_authorization:v1",
        tenant_id="tenant-A",
        plan_record_id="opr-fanin",
        plan_version=1,
        task_frontier=list(frontier),
        objective_id="goal-fanin",
        expires_at=_t.time() + 3600,
        max_attempts_per_task=2,
        environment_classes=["git_worktree"],
        verification_obligations=["independent verification"],
        # The PRODUCTION role ids, from the same resolvers the driver uses —
        # admission check 8 judges the packet's role against these, so an empty
        # list here would refuse every attempt (as it correctly did first time).
        role_ids=[_IMPLEMENTER_ROLE_ID],
    )
    grant.status = "active"
    return grant


def _prod_packet(pid: str, deps: list[str], scope: list[str]):
    return SimpleNamespace(
        packet_id=pid,
        status=SimpleNamespace(value="approved"),
        dependencies=list(deps),
        work_scope={"tenant_id": "tenant-A", "target_kind": "umh_substrate"},
        lineage={"plan_record_id": "opr-fanin"},
        requirements={"writable_path_scope": list(scope), "scope_declared": True},
        desired_end_state="",
        required_role_contracts=[],
        required_tools=[],
        required_templates=[],
        required_workflows=[],
        required_knowledge_models=[],
        risk_class="low",
    )


def _permit(**kw):
    fn = kw.get("execute_fn")
    out = fn() if callable(fn) else ("", True)
    return SimpleNamespace(success=True, output=out[0] if isinstance(out, tuple) else out)


def test_full_a_b_c_d_production_path(repo, tmp_path, monkeypatch):
    """A+B → C → D through the REAL scheduler, store, leases, sandbox, git,
    lifecycle CAS, ProofRuntime and terminalization.

    Proves, in one flow:
      A verified + B verified → both commits retained under refs/umh/verified
      → C is created as a control-plane composition Attempt (persisted kind)
      → NO worker is dispatched for C, NO instruction package is compiled
      → deterministic composed tree containing BOTH slices
      → Attempt-bound durable Proof, C SUCCEEDED
      → D's lease is based on C's EXACT composed commit
      → D's sandbox observes BOTH predecessor slices
      → teardown leaves ZERO trusted/composed refs
    """
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.execution.attempts.run_teardown import sweep_run
    from substrate.execution.attempts.scheduler import AttemptScheduler
    from substrate.execution.attempts.terminalization import terminalize
    from substrate.organism.worktree_sandbox import SandboxManager

    # The lifecycle's verifying→succeeded guard rereads the CANONICAL
    # ProofRuntime store from disk (there is deliberately no injection hatch —
    # an env bypass was removed as unsafe). Production points that store at the
    # candidate state root via UMH_STATE_DIR, so the test does the same rather
    # than weakening the guard.
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.state.runtime_paths import runtime_state_path

    store = _store(tmp_path, "prod")
    proofs = _Runtime(runtime_state_path("organism", "proof_packages.jsonl"))
    sandbox = SandboxManager(
        repo_root=repo,
        worktree_base=str(tmp_path / "leases"),
        store_dir=str(tmp_path / "sandboxes"),
        max_parallel=8,
    )
    leases = LeaseManager(store, sandbox, mutation_runner=_permit)

    # ── A and B: real worker lanes that really succeeded and were retained ──
    _base, a_sha, b_sha = _two_lanes(repo)
    _succeeded(store, TASK_A, "ea-A", commits=[a_sha])
    _succeeded(store, TASK_B, "ea-B", commits=[b_sha])
    for task, attempt_id, sha in ((TASK_A, "ea-A", a_sha), (TASK_B, "ea-B", b_sha)):
        _git(["update-ref", f"refs/umh/verified/{CAND}/{RUN}/{task}/{attempt_id}", sha], repo)
    assert len(list_trusted_refs(repo=repo, candidate=CAND, run_id=RUN)) == 2

    union_scope = ["app", "tests"]
    packet_c = _prod_packet(TASK_C, [TASK_A, TASK_B], union_scope)
    packet_d = _prod_packet(TASK_D, [TASK_C], union_scope)
    packets = {TASK_C: packet_c, TASK_D: packet_d}

    class _Q:
        def get_packet(self, pid):
            return packets.get(pid)

    # ── the injected trusted callables, as the driver builds them ──────────
    from substrate.execution.attempts.composition import (
        compose_predecessors as _compose,
    )
    from substrate.execution.attempts.composition import (
        composition_proof_action as _action,
    )
    from substrate.execution.attempts.composition import (
        mint_composition_proof as _mint,
    )
    from substrate.execution.attempts.composition import (
        resolve_downstream_base as _base_resolver,
    )
    from substrate.execution.attempts.composition import (
        resolve_predecessor_commits as _resolve_preds,
    )

    def _is_composition(packet):
        # Stands in for the driver's validate_against_run-gated lookup; the
        # scenario-map authority itself is covered by its own tests.
        return str(getattr(packet, "packet_id", "")) == TASK_C

    accepted: dict = {}

    def _accept(attempt, *, composed_commit, predecessor_commits, packet):
        """The acceptance verifier: content equivalence + collection floor +
        both-parent ancestry, run against the composed commit."""
        from substrate.execution.attempts.composition import (
            verify_predecessor_content,
        )
        from substrate.execution.attempts.verification import VerificationCheck

        base_sha = _git(["merge-base", *predecessor_commits.values()], repo).stdout.strip()
        ok, violations, produced = verify_predecessor_content(
            repo=repo,
            base=base_sha,
            composed_tree=composed_commit,
            predecessor_commits=predecessor_commits,
        )
        missing = assert_descends_from_all(
            repo=repo,
            composed_commit=composed_commit,
            predecessor_commits=predecessor_commits,
        )
        accepted["produced"] = produced
        return (
            [
                VerificationCheck(check_id="content", kind="diff", ok=ok, detail=str(violations)),
                VerificationCheck(
                    check_id="collection_floor",
                    kind="artifact",
                    ok=bool(produced),
                    detail=f"{len(produced)} predecessor files",
                ),
                VerificationCheck(
                    check_id="ancestry", kind="commits", ok=not missing, detail=str(missing)
                ),
            ],
            None,
        )

    def _producer(*, attempt, packet, lease, grant):
        preds = _resolve_preds(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=store,
            dependency_task_ids=list(packet.dependencies),
        )
        result = _compose(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            task_id=attempt.task_id,
            attempt_id=attempt.attempt_id,
            predecessor_commits=preds,
        )
        verifying = store.transition_cas(
            attempt.attempt_id,
            _S.VERIFYING.value,
            attempt.record_version,
            (_S.LEASED.value,),
            "composer:control-plane",
            "composed",
            updates={"commits": [result.composed_commit]},
        )
        checks, _ev = _accept(
            verifying,
            composed_commit=result.composed_commit,
            predecessor_commits=result.predecessor_commits,
            packet=packet,
        )
        assert all(c.ok for c in checks), [c.detail for c in checks if not c.ok]
        predecessor_proofs = {
            task: str(getattr(a, "proof_id", ""))
            for task in packet.dependencies
            for a in store.attempts_for_task(str(task))
            if str(getattr(a, "status", "")) == _S.SUCCEEDED.value
        }
        proof = _mint(
            proof_runtime=proofs,
            attempt=verifying,
            action=_action(
                attempt=verifying,
                result=result,
                predecessor_proofs=predecessor_proofs,
                run_id=RUN,
                candidate_sha=CAND,
            ),
            verifier_identity="verifier:role-integrator-op",
        )
        return store.transition_cas(
            verifying.attempt_id,
            _S.SUCCEEDED.value,
            verifying.record_version,
            (_S.VERIFYING.value,),
            "verifier:role-integrator-op",
            "composition verified",
            updates={
                "proof_id": proof.proof_id,
                "verifier_identity": "verifier:role-integrator-op",
                "verifier_role_id": "role-integrator-op",
                "commits": [result.composed_commit],
            },
        )

    def _downstream_base(packet, deps):
        return _base_resolver(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            store=store,
            proof_runtime=proofs,
            dependency_task_ids=[str(d) for d in deps],
        )

    dispatched: list = []

    def _placement(**kw):
        return SimpleNamespace(
            assignment_id=f"asn-{kw['attempt_id']}",
            worker_identity="cc-cli@vps-host",
            verifier_role_id="role-verifier-op",
            compute_node_id="node-1",
            environment_class="git_worktree",
            worker_agent_type="developer_agent",
            tool_profile=[],
        )

    def _compile(**kw):
        return SimpleNamespace(package_hash=f"pkg-{kw['attempt'].attempt_id}")

    scheduler = AttemptScheduler(
        store,
        work_queue=_Q(),
        placement_fn=_placement,
        lease_manager=leases,
        compile_fn=_compile,
        dispatch_fn=lambda **kw: dispatched.append(kw["attempt"].attempt_id),
        lock_dir=str(tmp_path / "locks"),
        mutation_runner=_permit,
        latest_plan_lookup=lambda _o: SimpleNamespace(
            plan_record_id="opr-fanin", status="approved"
        ),
        composition_task_predicate=_is_composition,
        composition_producer=_producer,
        downstream_base_resolver=_downstream_base,
    )

    # ── PASS 1: Task C becomes a composition attempt and completes ─────────
    grant_c = _prod_grant(tmp_path, [TASK_C, TASK_D])
    store.create_grant_idempotent(grant_c)
    scheduler.run_scheduler_pass(
        grant_c,
        role_resolver=_default_role_resolver,
        verifier_role_resolver=_verifier_role_resolver,
    )

    c_attempts = store.attempts_for_task(TASK_C)
    assert len(c_attempts) == 1, [a.attempt_id for a in c_attempts]
    c = c_attempts[0]

    # persisted composition authority + no worker
    assert c.execution_kind == _K.CONTROL_PLANE_COMPOSITION.value
    assert c.worker_identity == "", "a composition attempt must carry NO worker identity"
    assert c.instruction_package_hash == "", "no instruction package may be sealed for C"
    assert c.attempt_id not in dispatched, "NO worker may be dispatched for a composition"
    assert c.status == _S.SUCCEEDED.value, c.blocked_reason

    # it went LEASED → VERIFYING, never DISPATCHED/RUNNING
    seen = [t["to_status"] for t in c.transitions]
    assert _S.VERIFYING.value in seen
    assert _S.DISPATCHED.value not in seen
    assert _S.RUNNING.value not in seen

    # Attempt-bound durable Proof
    durable = proofs.reread_durable(c.proof_id)
    assert durable is not None
    assert durable.action["attempt_id"] == c.attempt_id
    assert durable.action["task_id"] == TASK_C

    # the composed commit is pinned and contains BOTH slices
    composed = resolve_composed_commit(
        repo=repo, candidate=CAND, run_id=RUN, task_id=TASK_C, attempt_id=c.attempt_id
    )
    assert composed and c.commits == [composed]
    for path in (
        "app/main.py",
        "app/static/index.html",
        "tests/test_search_api.py",
        "tests/test_ui_search.py",
    ):
        assert _git(["rev-parse", f"{composed}:{path}"], repo).returncode == 0, path
    assert (
        assert_descends_from_all(
            repo=repo,
            composed_commit=composed,
            predecessor_commits={TASK_A: a_sha, TASK_B: b_sha},
        )
        == []
    )

    # C's lease is released by the ONE terminalization authority, and worker
    # verified-commit retention is NOT used (no rival refs/umh/verified for C).
    term = terminalize(
        attempt=c,
        reason="succeeded",
        lease_manager=leases,
        run_root=str(tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN),
        raise_on_security_failure=False,
    )
    assert term.retained_commit == "", "composition must NOT use worker retention"
    assert term.lease_released is True, "the composition lease must really be released"
    assert not any(
        f"/{TASK_C}/" in r for r in list_trusted_refs(repo=repo, candidate=CAND, run_id=RUN)
    ), "composition must not mint a rival refs/umh/verified ref"

    # ── PASS 2: Task D leases from C's EXACT composed commit ───────────────
    grant_d = grant_c
    scheduler.run_scheduler_pass(
        grant_d,
        role_resolver=_default_role_resolver,
        verifier_role_resolver=_verifier_role_resolver,
    )

    d_attempts = store.attempts_for_task(TASK_D)
    assert len(d_attempts) == 1
    d = d_attempts[0]
    assert d.execution_kind == _K.WORKER.value, "D is an ordinary worker Task"
    assert d.attempt_id in dispatched, "D MUST be dispatched to a real worker"

    d_lease = store.get_lease(d.lease_id)
    assert d_lease is not None
    assert d_lease["snapshot_ref"] == composed, (
        f"D must be based on C's composed commit {composed[:12]}, "
        f"got {d_lease['snapshot_ref'][:12]}"
    )

    # D's sandbox really contains BOTH predecessor slices.
    wt = d_lease["worktree_path"]
    assert "BACKEND" in open(os.path.join(wt, "app/main.py")).read()
    assert "ui" in open(os.path.join(wt, "app/static/index.html")).read()
    assert os.path.exists(os.path.join(wt, "tests/test_search_api.py"))
    assert os.path.exists(os.path.join(wt, "tests/test_ui_search.py"))

    # ── teardown: zero trusted/composed refs ───────────────────────────────
    leases.release(d.lease_id, cleanup=True)
    run_root = str(tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN)
    swept = sweep_run(run_root, repo_root=repo, candidate=CAND, run_id=RUN)
    assert swept.ref_residue == [], swept.ref_residue
    assert swept.zero_ref_residue is True
    assert list_trusted_refs(repo=repo, candidate=CAND, run_id=RUN) == []
    assert list_composed_refs(repo=repo, candidate=CAND, run_id=RUN) == []


def test_content_check_detects_lost_deletion(repo):
    """The DELETE rule must FAIL when a deletion is lost. Asserting `ok` on a
    correct tree cannot detect a weakened check — this drives the negative."""
    base = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    _git(["checkout", "-q", base], repo)
    _git(["checkout", "-qb", "delOnly"], repo)
    os.remove(os.path.join(repo, "app/store.py"))
    _git(["add", "-A"], repo)
    _git(["commit", "-qm", "del"], repo)
    a = _git(["rev-parse", "HEAD"], repo).stdout.strip()

    # Verify A's deletion against the BASE tree, where app/store.py still EXISTS.
    ok, violations, _ = verify_predecessor_content(
        repo=repo, base=base, composed_tree=base, predecessor_commits={TASK_A: a}
    )
    assert not ok
    assert any("PRESENT in the composed tree" in v for v in violations), violations


def test_content_check_detects_lost_mode_change(repo):
    """A mode regression must FAIL the check, with the blob still identical —
    so only the MODE comparison can catch it."""
    base = _git(["rev-parse", "HEAD"], repo).stdout.strip()
    _git(["checkout", "-q", base], repo)
    _git(["checkout", "-qb", "modeOnly"], repo)
    os.chmod(os.path.join(repo, "app/main.py"), 0o755)
    _git(["add", "-A"], repo)
    _git(["commit", "-qm", "mode"], repo)
    a = _git(["rev-parse", "HEAD"], repo).stdout.strip()

    # The BASE tree has the same BLOB but mode 100644 — a pure mode regression.
    assert (
        _git(["rev-parse", f"{base}:app/main.py"], repo).stdout.strip()
        == _git(["rev-parse", f"{a}:app/main.py"], repo).stdout.strip()
    ), "blob must be identical so only the mode differs"
    ok, violations, _ = verify_predecessor_content(
        repo=repo, base=base, composed_tree=base, predecessor_commits={TASK_A: a}
    )
    assert not ok
    assert any("composed mode" in v for v in violations), violations


def test_composed_ref_cas_survives_a_toctou_race(repo, monkeypatch):
    """The `""` old-value is CAS-against-must-not-exist, and it is load-bearing
    ONLY under concurrency.

    Single-process, the pre-flight `resolve_composed_commit` returns first, so
    `update-ref` never runs on an existing ref — dropping the old-value looks
    harmless. The window is between that read and the write: a second composer
    creating the ref in between. Simulated by forcing the pre-flight to report
    "absent" while the ref really exists (the same technique the retention suite
    uses for its own CAS race). Without the old-value this silently REPOINTS
    another composer's trusted base.
    """
    import substrate.execution.attempts.composition as comp

    _base, a, b = _two_lanes(repo)
    kw = dict(repo=repo, candidate=CAND, run_id=RUN, task_id=TASK_C)
    first = compose_predecessors(
        attempt_id="ea-race", predecessor_commits={TASK_A: a, TASK_B: b}, **kw
    )
    ref = composed_ref(candidate=CAND, run_id=RUN, task_id=TASK_C, attempt_id="ea-race")

    # TOCTOU: pre-flight says "absent" though the ref exists and pins `first`.
    monkeypatch.setattr(comp, "resolve_composed_commit", lambda **_k: "")
    with pytest.raises(CompositionError, match="could not pin composed ref"):
        compose_predecessors(attempt_id="ea-race", predecessor_commits={TASK_A: a, TASK_B: b}, **kw)
    assert _git(["rev-parse", ref], repo).stdout.strip() == first.composed_commit, (
        "the racing composer must NOT have repointed the existing composed ref"
    )


def test_composed_ref_cannot_be_overwritten_by_the_module(repo):
    """The pin uses CAS-against-must-not-exist. Without the `""` old-value a
    plain `update-ref` would silently REPOINT an existing composed ref, so a
    second composition for the same attempt could replace the trusted base."""
    _base, a, b = _two_lanes(repo)
    r = compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-cas2",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    ref = composed_ref(candidate=CAND, run_id=RUN, task_id=TASK_C, attempt_id="ea-cas2")

    # Point the ref somewhere else, then re-compose: the module must REFUSE to
    # trust (and must not silently repoint), because the pinned commit's tree no
    # longer matches the recomputed composition.
    _git(["update-ref", ref, a], repo)
    assert _git(["rev-parse", ref], repo).stdout.strip() == a
    with pytest.raises(CompositionError, match="divergent composition"):
        compose_predecessors(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            task_id=TASK_C,
            attempt_id="ea-cas2",
            predecessor_commits={TASK_A: a, TASK_B: b},
        )
    assert r.composed_commit != a


def test_merge_tree_rc1_without_tree_oid_is_error_not_conflict(repo):
    """The SECOND layer of the rc=1 disambiguation, driven directly.

    ``_assert_is_commit`` normally catches a bad predecessor first, so the
    stdout-shape branch inside ``_merge_tree`` is unreachable through
    ``compose_predecessors``. It is defense in depth, not dead code — git can
    return rc=1 with no tree oid for inputs that pass a type check — so it is
    exercised at its own seam.
    """
    from substrate.execution.attempts.composition import _merge_tree

    _base, a, b = _two_lanes(repo)
    base = _git(["merge-base", a, b], repo).stdout.strip()
    with pytest.raises(CompositionError) as ei:
        _merge_tree(repo, base=base, left=a, right="d" * 40)
    assert not isinstance(ei.value, CompositionConflict)
    assert "not a content conflict" in str(ei.value)

    # And a REAL conflict still classifies as a conflict at the same seam.
    c = _lane(repo, "shapeC", {"app/main.py": "base\nZZZ\n"}, base=base)
    with pytest.raises(CompositionConflict):
        _merge_tree(repo, base=base, left=a, right=c)


def test_real_driver_producer_terminalizes_the_composition_attempt(repo, tmp_path, monkeypatch):
    """Drive the REAL FieldControlPlaneDriver._composition_producer.

    This exists because the E2E test injects a behaviorally-equivalent local
    producer, and that substitution hid a CRITICAL wiring defect: nothing called
    ``terminalize()`` on a composition attempt. A composition never enters the
    spool, so the poller — the only OTHER production terminalize caller — can
    never see it. The lease stayed ACTIVE forever, its sandbox slot was never
    freed (at the production ``max_parallel=2`` that starves the rest of the
    run), and the credential home was never destroyed.

    So this test drives the driver's own closure and asserts the RESOURCE
    OUTCOME, not merely that the attempt succeeded.
    """
    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.organism.worktree_sandbox import SandboxManager

    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    targets = str(tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN)
    os.makedirs(targets, exist_ok=True)

    store = _store(tmp_path, "drv")
    sandbox = SandboxManager(
        repo_root=repo,
        worktree_base=str(tmp_path / "leases"),
        store_dir=str(tmp_path / "sandboxes"),
        max_parallel=2,
    )

    driver = FieldControlPlaneDriver.__new__(FieldControlPlaneDriver)
    driver._targets_dir = targets
    driver._store = store
    driver._sandbox = sandbox
    driver._spool = None
    driver._mutation_runner = _permit
    driver._lease_mgr = LeaseManager(store, sandbox, mutation_runner=_permit)
    from substrate.organism.proof_runtime import ProofRuntime

    driver._proof_runtime = ProofRuntime()

    # The driver's binding + acceptance closure must both resolve for a
    # candidate-shaped path; otherwise the producer is None and this test is
    # vacuous. Assert that explicitly.
    assert driver._composition_binding() == (os.path.join(targets, "fixture"), CAND, RUN)
    produce = driver._composition_producer()
    assert produce is not None, "the real driver must build a producer"

    # Predecessors: real lanes, real SUCCEEDED attempts, real retained refs.
    _base, a_sha, b_sha = _two_lanes(repo)
    _succeeded(store, TASK_A, "ea-dA", commits=[a_sha])
    _succeeded(store, TASK_B, "ea-dB", commits=[b_sha])
    for task, aid, sha in ((TASK_A, "ea-dA", a_sha), (TASK_B, "ea-dB", b_sha)):
        _git(["update-ref", f"refs/umh/verified/{CAND}/{RUN}/{task}/{aid}", sha], repo)

    packet = _prod_packet(TASK_C, [TASK_A, TASK_B], ["app", "tests"])
    att = ExecutionAttempt(
        attempt_id="ea-drv-c",
        task_id=TASK_C,
        execution_kind=_K.CONTROL_PLANE_COMPOSITION.value,
        status=_S.CREATED.value,
    )
    created, _ = store.create_attempt_idempotent(att)
    created = store.transition_cas(
        created.attempt_id,
        _S.READY.value,
        created.record_version,
        (_S.CREATED.value,),
        "scheduler",
        "ready",
    )
    assignment = SimpleNamespace(
        assignment_id="asn-drv",
        worker_identity="",
        verifier_role_id="role-verifier-op",
        compute_node_id="node-1",
        environment_class="git_worktree",
        worker_agent_type="developer_agent",
        tool_profile=[],
    )
    grant = _prod_grant(tmp_path, [TASK_C])
    lease = driver._lease_mgr.acquire(attempt=created, assignment=assignment, grant=grant)
    leased = store.transition_cas(
        created.attempt_id,
        _S.LEASED.value,
        created.record_version,
        (_S.READY.value,),
        "scheduler",
        "leased",
        updates={"assignment_id": "asn-drv", "lease_id": lease.lease_id},
    )
    assert store.active_lease_for_task(TASK_C) is not None, "precondition: lease is ACTIVE"

    # The acceptance verifier runs a CONFINED pytest, which needs bwrap and the
    # fixture; unavailable here. Substitute ONLY that boundary — every other
    # step (composition, lifecycle CAS, Proof, terminalization) stays real.
    monkeypatch.setattr(
        driver,
        "_composition_acceptance_verifier",
        lambda: lambda attempt, **kw: ([SimpleNamespace(check_id="stub", ok=True)], None),
    )
    produce = driver._composition_producer()

    settled = produce(attempt=leased, packet=packet, lease=lease, grant=grant)

    assert settled.status == _S.SUCCEEDED.value, settled.blocked_reason
    assert settled.commits and settled.commits[0]

    # THE ASSERTION THAT WAS MISSING: the composition terminalized itself.
    assert store.active_lease_for_task(TASK_C) is None, (
        "the composition lease is STILL ACTIVE — it leaked, and at "
        "max_parallel=2 that starves the rest of the run"
    )
    row = store.get_lease(lease.lease_id)
    assert row["status"] in ("released", "revoked"), row["status"]
    assert not os.path.isdir(row["worktree_path"]), "the composition worktree leaked"


def _driver_for(repo, tmp_path, store, sandbox):
    """A real FieldControlPlaneDriver over a candidate-shaped targets dir."""
    from substrate.execution.attempts.field_control_plane import FieldControlPlaneDriver
    from substrate.execution.attempts.leases import LeaseManager
    from substrate.organism.proof_runtime import ProofRuntime

    targets = str(tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN)
    os.makedirs(targets, exist_ok=True)
    d = FieldControlPlaneDriver.__new__(FieldControlPlaneDriver)
    d._targets_dir = targets
    d._store = store
    d._sandbox = sandbox
    d._spool = None
    d._mutation_runner = _permit
    d._lease_mgr = LeaseManager(store, sandbox, mutation_runner=_permit)
    d._proof_runtime = ProofRuntime()
    return d


def _leased_composition(repo, tmp_path, store, driver):
    """A real LEASED composition attempt with real verified predecessors."""
    _base, a_sha, b_sha = _two_lanes(repo)
    _succeeded(store, TASK_A, "ea-nA", commits=[a_sha])
    _succeeded(store, TASK_B, "ea-nB", commits=[b_sha])
    for task, aid, sha in ((TASK_A, "ea-nA", a_sha), (TASK_B, "ea-nB", b_sha)):
        _git(["update-ref", f"refs/umh/verified/{CAND}/{RUN}/{task}/{aid}", sha], repo)

    packet = _prod_packet(TASK_C, [TASK_A, TASK_B], ["app", "tests"])
    created, _ = store.create_attempt_idempotent(
        ExecutionAttempt(
            attempt_id="ea-neg-c",
            task_id=TASK_C,
            execution_kind=_K.CONTROL_PLANE_COMPOSITION.value,
            status=_S.CREATED.value,
        )
    )
    created = store.transition_cas(
        created.attempt_id,
        _S.READY.value,
        created.record_version,
        (_S.CREATED.value,),
        "scheduler",
        "ready",
    )
    assignment = SimpleNamespace(
        assignment_id="asn-neg",
        worker_identity="",
        verifier_role_id="role-verifier-op",
        compute_node_id="node-1",
        environment_class="git_worktree",
        worker_agent_type="developer_agent",
        tool_profile=[],
    )
    grant = _prod_grant(tmp_path, [TASK_C])
    lease = driver._lease_mgr.acquire(attempt=created, assignment=assignment, grant=grant)
    leased = store.transition_cas(
        created.attempt_id,
        _S.LEASED.value,
        created.record_version,
        (_S.READY.value,),
        "scheduler",
        "leased",
        updates={"assignment_id": "asn-neg", "lease_id": lease.lease_id},
    )
    return leased, packet, lease, grant


@pytest.mark.parametrize(
    "verifier,why",
    [
        (lambda attempt, **kw: ([], None), "EMPTY checks — all([]) is vacuously True"),
        (
            lambda attempt, **kw: (
                [SimpleNamespace(check_id="x", ok=False)],
                None,
            ),
            "a FAILING check",
        ),
        (None, "the verifier RAISES"),
    ],
)
def test_real_producer_refuses_to_succeed_without_real_acceptance(
    repo, tmp_path, monkeypatch, verifier, why
):
    """The PRODUCTION acceptance gate, driven through the real driver closure.

    Without this, `passed = True` (acceptance disabled entirely) and dropping the
    `bool(checks)` guard (so an EMPTY check list passes vacuously) both survived a
    fully green suite — the E2E test substitutes its own producer, so ~445 lines
    of driver wiring were dead to the tests. A Task C could then reach SUCCEEDED
    with a durable Proof and pin refs/umh/composed with ZERO verification, and
    Task D would lease from that unverified commit as a trusted base.
    """
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.organism.worktree_sandbox import SandboxManager

    store = _store(tmp_path, "neg")
    sandbox = SandboxManager(
        repo_root=repo,
        worktree_base=str(tmp_path / "leases"),
        store_dir=str(tmp_path / "sandboxes"),
        max_parallel=2,
    )
    driver = _driver_for(repo, tmp_path, store, sandbox)
    leased, packet, lease, grant = _leased_composition(repo, tmp_path, store, driver)

    def _raises(attempt, **kw):
        raise RuntimeError("verifier exploded")

    monkeypatch.setattr(driver, "_composition_acceptance_verifier", lambda: verifier or _raises)
    produce = driver._composition_producer()
    assert produce is not None

    settled = produce(attempt=leased, packet=packet, lease=lease, grant=grant)

    assert settled.status != _S.SUCCEEDED.value, (
        f"composition SUCCEEDED despite {why} — the acceptance gate is not enforcing"
    )
    # VERIFYING has no BLOCKED target, so a rejected acceptance settles FAILED —
    # the same terminal the poller uses for verification_rejected. Either way it
    # is terminal and its lease must be gone.
    assert settled.status in (_S.FAILED.value, _S.BLOCKED.value), settled.status
    assert not settled.proof_id, "no Proof may be minted without real acceptance"
    assert store.active_lease_for_task(TASK_C) is None, (
        "a refused composition must not hold its lease/sandbox slot"
    )


def test_real_acceptance_verifier_refuses_out_of_scope_composition(repo, tmp_path, monkeypatch):
    """Drive the REAL `_composition_acceptance_verifier` check assembly.

    The union-scope check is the only thing preventing composition — a
    control-plane-performed mutation — from putting content into the trusted
    downstream base that a WORKER attempt would have been refused for. It shipped
    dead (zero callers of `verify_composed_scope`) until this test forced it to
    be wired.

    The confined pytest run needs bwrap + the fixture, so only THAT boundary is
    stubbed; the packet-identity, contract hash-match, ancestry, content
    equivalence, collection-floor and scope-union checks are all real.
    """
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    from substrate.execution.attempts import verifier_isolation as vi
    from substrate.organism.worktree_sandbox import SandboxManager

    store = _store(tmp_path, "scope")
    sandbox = SandboxManager(
        repo_root=repo,
        worktree_base=str(tmp_path / "leases"),
        store_dir=str(tmp_path / "sandboxes"),
        max_parallel=2,
    )
    driver = _driver_for(repo, tmp_path, store, sandbox)
    leased, packet, lease, grant = _leased_composition(repo, tmp_path, store, driver)

    # Stub ONLY the confined suite boundary (needs bwrap + fixture).
    monkeypatch.setattr(
        vi,
        "run_confined_verifier_checks",
        lambda **kw: ([SimpleNamespace(check_id="confined_suite", ok=True)], None),
    )
    # The persisted contract must hash-match the canonical Task C contract.
    from substrate.execution.attempts import field_task_scope as fts

    packet.desired_end_state = fts.task_contract_for(fts.INTEGRATION)
    # And the validated map must name THIS packet as the integration Task.
    monkeypatch.setattr(driver, "_validated_integration_packet_id", lambda: TASK_C)

    accept = driver._composition_acceptance_verifier()
    assert accept is not None

    composed = (
        resolve_composed_commit(
            repo=repo, candidate=CAND, run_id=RUN, task_id=TASK_C, attempt_id=leased.attempt_id
        )
        or compose_predecessors(
            repo=repo,
            candidate=CAND,
            run_id=RUN,
            task_id=TASK_C,
            attempt_id=leased.attempt_id,
            predecessor_commits=resolve_predecessor_commits(
                repo=repo,
                candidate=CAND,
                run_id=RUN,
                store=store,
                dependency_task_ids=[TASK_A, TASK_B],
            ),
        ).composed_commit
    )
    preds = resolve_predecessor_commits(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        store=store,
        dependency_task_ids=[TASK_A, TASK_B],
    )

    # (1) In-scope: every real check passes.
    checks, _ev = accept(leased, composed_commit=composed, predecessor_commits=preds, packet=packet)
    ids = {c.check_id for c in checks}
    assert "composition_scope_union" in ids, "the scope-union check must actually run"
    assert all(c.ok for c in checks), [c.detail for c in checks if not c.ok]

    # (2) NARROW the persisted scope so the composed delta falls outside it.
    packet.requirements = {"writable_path_scope": ["docs"], "scope_declared": True}
    checks2, _ev2 = accept(
        leased, composed_commit=composed, predecessor_commits=preds, packet=packet
    )
    scope_check = next(c for c in checks2 if c.check_id == "composition_scope_union")
    assert not scope_check.ok, (
        "a composed delta outside the declared union scope must FAIL — otherwise "
        "composition can write where a worker would have been refused"
    )
    assert not all(c.ok for c in checks2)


def test_sweep_derives_the_binding_when_the_caller_omits_it(repo, tmp_path):
    """A caller that does NOT pass repo/candidate/run must STILL release refs.

    Two of the three production callers (`wave2_attempt_runner._run_teardown`,
    the run's own authoritative teardown, and `recover_stale_runs`) do not know
    the candidate sha. An explicit-args-only design left them reporting
    `zero_ref_residue=True` over refs they never looked at — a leak reported as
    clean. The run root already encodes the binding, so the sweep derives it.
    """
    from substrate.execution.attempts.run_teardown import sweep_run

    _base, a, b = _two_lanes(repo)
    compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-nb",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    run_root = str(tmp_path / "candidates" / "wave2" / CAND / "targets" / RUN)

    unbound = sweep_run(run_root)  # the OLD call shape the runner still uses
    assert unbound.refs_deleted, "the sweep must derive the binding and delete the refs"
    assert unbound.zero_ref_residue is True
    assert list_composed_refs(repo=repo, candidate=CAND, run_id=RUN) == []


def test_sweep_on_a_non_candidate_path_is_a_clean_noop(tmp_path):
    """A genuinely non-candidate run root has no protected refs — not an error."""
    from substrate.execution.attempts.run_teardown import sweep_run

    res = sweep_run(str(tmp_path / "plain" / "run"))
    assert res.refs_deleted == []
    assert res.ref_residue == []
    assert res.zero_ref_residue is True


def test_run_binding_resolution_refuses_ambiguity():
    """Both components must come from ONE anchor match — resolving them from
    independent anchors is what produced silently misattributed refs."""
    from substrate.execution.attempts.composition import resolve_run_binding

    repo, cand, run = resolve_run_binding(f"/var/lib/umh/candidates/wave2/{CAND}/targets/{RUN}")
    assert (cand, run) == (CAND, RUN)
    assert repo.endswith("fixture")

    ambiguous = f"/x/candidates/wave2/{CAND}/targets/runA/candidates/wave2/other/targets/runB"
    assert resolve_run_binding(ambiguous) == ("", "", "")
    assert resolve_run_binding("/not/a/candidate/path") == ("", "", "")
    assert list_composed_refs(repo=repo, candidate=CAND, run_id=RUN) == []


def test_production_caller_passes_the_repo_binding_to_sweep(tmp_path, monkeypatch):
    """The PRODUCTION caller must supply repo_root/candidate/run_id.

    Without them the sweep cannot see the refs at all, so ref cleanup would ship
    unreachable — the exact "helper with no production caller" failure this
    packet exists to avoid. Asserted at the real caller
    (``_sweep_run_homes`` → ``sweep_run``), not at the sweep's own signature.
    """
    import importlib.util
    import sys

    name = "_w2fd_sweepargs"
    spec = importlib.util.spec_from_file_location(
        name,
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "scripts",
            "wave2_field_dispatch.py",
        ),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)

    seen: dict = {}

    def _spy(run_root, **kw):
        seen["run_root"] = run_root
        seen.update(kw)
        return SimpleNamespace(to_dict=lambda: {"ok": True, "zero_ref_residue": True})

    import substrate.execution.attempts.run_teardown as rt

    monkeypatch.setattr(rt, "sweep_run", _spy)
    mod._sweep_run_homes(CAND, RUN)

    assert seen.get("candidate") == CAND, "the caller must bind the candidate"
    assert seen.get("run_id") == RUN, "the caller must bind the run"
    assert str(seen.get("repo_root", "")).endswith("fixture"), (
        f"the caller must bind the FIXTURE repo (where the refs live), "
        f"got {seen.get('repo_root')!r}"
    )
    assert CAND in str(seen["repo_root"]) and RUN in str(seen["repo_root"])


def test_release_is_run_scoped(repo):
    """One run's teardown must never free another run's refs."""
    _base, a, b = _two_lanes(repo)
    other_run = "20260806T000000Z-p9"
    compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=RUN,
        task_id=TASK_C,
        attempt_id="ea-r1",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    compose_predecessors(
        repo=repo,
        candidate=CAND,
        run_id=other_run,
        task_id=TASK_C,
        attempt_id="ea-r2",
        predecessor_commits={TASK_A: a, TASK_B: b},
    )
    release_composed_refs(repo=repo, candidate=CAND, run_id=RUN)
    assert list_composed_refs(repo=repo, candidate=CAND, run_id=RUN) == []
    assert list_composed_refs(repo=repo, candidate=CAND, run_id=other_run)
