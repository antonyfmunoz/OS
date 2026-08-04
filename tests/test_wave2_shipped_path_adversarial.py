"""Wave 2 — adversarial proofs for the shipped package/spool/git/phase boundaries.

The authorization names a specific adversarial set. The vectors that live at the
BARRIER (forbidden edits, hooks, config, refs, renames) are proven in
``test_wave2_shipped_path_integration.py`` against real bwrap; the vectors here
are the TRANSPORT and PHASE ones: replay against the wrong Attempt or SHA, scope
widening by worker-reachable data, and the ordering guarantee that separates
trusted writes from worker capability.

Each asserts a DENIAL plus the state that must remain untouched — a fix that
reverts after the fact is explicitly not acceptable.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate.execution.attempts import worker_claude_cli as W
from substrate.execution.attempts.field_control_plane import governance_envelope_fields
from substrate.execution.attempts.spool import DispatchEnvelope, DispatchSpool

SECRET = "adversarial-secret"
SCOPE = ["app/main.py"]


def _package(scope=None, *, task_id="wp-backend"):
    class _P:
        role_instructions = "implementer"
        operation_instructions = "implement"
        ordered_context = [{"section": "contract", "payload": "c"}]
        operation_identity = {"task_id": task_id}
        governance_constraints = [f"writable_path_scope={sorted(scope or SCOPE)}"]
        verification_requirements = []

    return _P()


def _envelope(**over):
    fields = dict(
        dispatch_id="d-1",
        attempt_id="ea-1",
        task_id="wp-backend",
        authorization_ref="grant-1",
        package_hash="ph-1",
        lease_id="lease-1",
        worktree_path="/tmp/lease",
        base_commit="aaaa1111",
        nonce=os.urandom(8).hex(),
        sequence=1,
        **governance_envelope_fields(_package()),
    )
    fields.update(over)
    return DispatchEnvelope(**fields)


def _tamper(spool_root: str, mutate) -> None:
    """Rewrite the queued envelope WITHOUT re-signing (an attacker's edit)."""
    inbox = os.path.join(spool_root, "inbox")
    name = sorted(os.listdir(inbox))[0]
    path = os.path.join(inbox, name)
    with open(path, encoding="utf-8") as fh:
        record = json.load(fh)
    mutate(record["envelope"])
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh)


# ── replay / rebinding ───────────────────────────────────────────────────────


def test_package_replayed_against_the_wrong_attempt_is_rejected(tmp_path):
    """Re-pointing a signed dispatch at a DIFFERENT attempt must fail closed.

    The envelope's authority is bound to one Attempt. Rebinding it would let a
    completed (or cheaper) attempt's authorization drive work for another.
    """
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(_envelope())
    _tamper(root, lambda env: env.update(attempt_id="ea-SOMEONE-ELSE"))
    assert spool.claim_next() is None, "a replay against another Attempt must be refused"


def test_package_replayed_against_the_wrong_sha_is_rejected(tmp_path):
    """Re-pointing the authorized base commit must fail closed.

    base_commit is the anchor the worker's artifacts are attributed against;
    moving it silently re-scopes what counts as this attempt's output.
    """
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(_envelope())
    _tamper(root, lambda env: env.update(base_commit="deadbeefdeadbeef"))
    assert spool.claim_next() is None, "a replay against another SHA must be refused"


def test_a_duplicate_dispatch_cannot_be_executed_twice(tmp_path):
    """The same signed envelope must not be consumable a second time.

    Signature proves authenticity, never freshness — a byte-perfect copy
    verifies cleanly, so replay protection has to be separate.
    """
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    envelope = _envelope()
    spool.enqueue(envelope)
    assert spool.claim_next() is not None, "the first claim must succeed"
    spool.enqueue(envelope)  # byte-identical replay
    assert spool.claim_next() is None, "a replayed dispatch must be quarantined"


def test_worker_reachable_data_cannot_widen_the_scope(tmp_path):
    """Scope widening is refused even when every other field is untouched."""
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(_envelope())
    _tamper(
        root,
        lambda env: env.update(
            governance_constraints=["writable_path_scope=['app', 'tests', '.git']"]
        ),
    )
    assert spool.claim_next() is None, "a widened scope must be refused"


def test_removing_the_scope_entirely_is_refused(tmp_path):
    """Stripping the constraint must not degrade to an unconstrained run."""
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(_envelope())
    _tamper(root, lambda env: env.update(governance_constraints=[]))
    assert spool.claim_next() is None, "a stripped scope must be refused"


def test_an_envelope_that_never_carried_a_scope_is_refused(tmp_path):
    """Not a tamper — a correctly-signed envelope with no authority at all.

    This is the shape the runner used to build for EVERY dispatch (F-2). It is
    refused at the transport, before any launch decision.
    """
    root = str(tmp_path)
    spool = DispatchSpool(root, SECRET)
    spool.enqueue(
        DispatchEnvelope(
            dispatch_id="d-noscope",
            attempt_id="ea-1",
            task_id="wp-backend",
            nonce=os.urandom(8).hex(),
            sequence=1,
        )
    )
    assert spool.claim_next() is None, "an envelope with no scope must be refused"
    quarantine = os.listdir(os.path.join(root, "quarantine"))
    assert any("governance" in q for q in quarantine), (
        f"it must be quarantined for the governance defect, got {quarantine}"
    )


# ── phase separation ─────────────────────────────────────────────────────────


def _real_lease(root: str) -> tuple[str, str]:
    repo = os.path.join(root, "fixture")
    os.makedirs(os.path.join(repo, "app"))

    def g(*a):
        return subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, timeout=60)

    with open(os.path.join(repo, "app", "main.py"), "w", encoding="utf-8") as fh:
        fh.write("# base\n")
    with open(os.path.join(repo, "OBJECTIVE.md"), "w", encoding="utf-8") as fh:
        fh.write("# ALL TASKS\n")
    g("init", "-q", "-b", "main")
    g("config", "user.email", "t@t.t")
    g("config", "user.name", "t")
    g("add", "-A")
    g("commit", "-qm", "base")
    base = g("rev-parse", "HEAD").stdout.strip()
    lease = os.path.join(root, "lease")
    g("worktree", "add", "-q", "-b", "b", lease, "HEAD")
    W.make_lease_selfcontained(lease)
    return lease, base


def test_trusted_writes_precede_the_worker_and_are_committed():
    """Proof: the trusted phase completes BEFORE worker confinement begins.

    Ordering is the whole of F-3. If the projection were written after the
    worker's base was anchored, its two files would be attributed to the worker;
    if it were written INSIDE the sandbox, it would need worker write authority
    over paths the worker must never hold.
    """
    root = tempfile.mkdtemp()
    lease, base = _real_lease(root)
    projection = W.project_task_local_objective(_package(), lease)
    assert projection.get("ok")
    new_base = W._commit_trusted_projection(lease, base, projection)

    assert new_base != base, "the trusted phase must re-anchor the attempt base"
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, new_base],
        cwd=lease, capture_output=True, timeout=60,
    )
    assert ancestry.returncode == 0, "the fixture base must remain an ancestor"
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=lease, capture_output=True, text=True, timeout=60
    ).stdout.strip()
    assert status == "", f"the trusted phase must leave a clean tree, got: {status!r}"


def test_projection_paths_are_never_inside_a_workers_writable_scope():
    """The worker must not gain write authority over trusted artifacts.

    "The worker must never receive permission to write projection or evidence
    paths merely because the orchestrator needs them later."
    """
    from substrate.execution.attempts.field_task_scope import (
        FIXTURE_ALLOWED_PATHS,
        readonly_binds_for_scope,
    )

    root = tempfile.mkdtemp()
    for rel in ("OBJECTIVE.md", "SHARED_CONTEXT.md"):
        with open(os.path.join(root, rel), "w", encoding="utf-8") as fh:
            fh.write("x")
    os.makedirs(os.path.join(root, "app"))
    with open(os.path.join(root, "app", "main.py"), "w", encoding="utf-8") as fh:
        fh.write("x")

    for label, scope in FIXTURE_ALLOWED_PATHS.items():
        for trusted in W.TRUSTED_PROJECTION_PATHS:
            assert trusted not in scope, (
                f"{label} must not hold write authority over {trusted}"
            )
        rel = {os.path.relpath(b, root) for b in readonly_binds_for_scope(scope, lease_root=root)}
        for trusted in W.TRUSTED_PROJECTION_PATHS:
            assert trusted in rel, f"{label}: {trusted} must be read-only to the worker"


@pytest.mark.parametrize("attempt_id", ["", "   ", "../escape", "a/b"])
def test_a_malformed_attempt_id_cannot_mint_a_ref(attempt_id):
    """An attempt id must never be able to traverse out of its namespace."""
    from substrate.execution.attempts.field_task_scope import (
        ScopeResolutionError,
        attempt_ref_name,
    )

    with pytest.raises(ScopeResolutionError):
        attempt_ref_name(attempt_id)
