"""Trusted retention of verifier-approved commits.

Why this module exists
----------------------
Field run ``20260805T182714Z-p1`` proved governed dependency ORDERING works and
dependency CONTENT propagation does not. Backend and frontend Tasks each produced
a verifier-approved commit; **56 ms** after the backend attempt reached SUCCEEDED,
terminalization released its lease, which ran ``SandboxManager.cleanup_sandbox``
→ ``git branch -D``. The commit became unreachable:

    1785954665.640  ea-504fc3e29496  backend      succeeded   ← verified
    1785954665.696  ea-1bedcbdb4aa1  integration  leased      ← content already gone

Retention closes exactly that window. When an attempt is verifier-approved,
trusted control-plane code pins its accepted commit under a protected ref
**before** the lease is released. The worker branch and worktree are then cleaned
normally; the commit stays reachable because a ref points at it.

Scope (truthful)
----------------
This module retains commits and hands out an explicit trusted base. It does NOT
compose multiple predecessors into one base, and nothing in the shipped path
consumes retained commits as a dependent Task's base yet — deterministic fan-in
composition is a separate, unimplemented work packet requiring a producer, poller
integration, verification integration, and a legal lifecycle path. Nothing here
should be read as implying fan-in consumption exists.

What retention is NOT
---------------------
It is not "keep the worker worktree alive", and it does not depend on reflogs or
unreachable-object grace periods. A ref is the only thing that keeps a commit
alive across ``gc --prune=now``.
"""

from __future__ import annotations

import logging
import re

from substrate.execution.cpu_gate import gated_subprocess_run

logger = logging.getLogger(__name__)

# Protected trusted ref namespace. Deliberately OUTSIDE refs/heads: a worker
# lease can create/delete refs/heads/* (measured — see field_task_scope.py), so a
# retention ref living there would be worker-forgeable.
TRUSTED_ROOT = "refs/umh/verified"

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
# Ref path components must not be able to escape the namespace or inject flags.
_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")


class RetentionError(RuntimeError):
    """A retention operation failed closed."""


class CpuGateRefused(RetentionError):
    """The CPU gate refused a git subprocess (host overloaded).

    TRANSIENT INFRASTRUCTURE, not a git answer, and it must never collapse into a
    benign empty result. It did: mapping a refusal to ``rc=1`` made every
    ``rc != 0`` consumer read "no commit to retain" / "no such ref" / "nothing to
    delete". Under load the verified commit was therefore NOT retained, the lease
    was released, ``git branch -D`` ran, and the commit became unreachable —
    silently reproducing the original field defect exactly when the host is busy.
    Found by adversarial review and reproduced before this fix.

    Same discipline as ``worktree_sandbox.CpuGatedGitError``: raise, so the caller
    records a real error and destructive cleanup is blocked.
    """


def _git(repo: str, args: list[str], *, caller: str) -> tuple[int, str, str]:
    """Run one git command under the CPU gate. Returns (rc, stdout, stderr).

    Raises :class:`CpuGateRefused` when the gate refuses — a refusal is NOT a git
    result and no caller may interpret it as one.
    """
    proc = gated_subprocess_run(
        ["git", *args],
        caller=f"verified_commit_retention.{caller}",
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc is None:
        raise CpuGateRefused(
            f"git {' '.join(args[:2])} refused by the CPU gate (host overloaded) — "
            f"refusing to treat an infrastructure refusal as a git answer"
        )
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def _validate_component(value: str, what: str) -> str:
    """One ref-path component, or refuse.

    The character class alone is not sufficient: ``..`` matches it but traverses
    out of the namespace, and a leading ``-`` matches it but is read by git as an
    option. Both are refused explicitly — measured, not assumed.
    """
    v = str(value or "").strip()
    if not v or not _SAFE_COMPONENT.match(v):
        raise RetentionError(f"unsafe {what} for a trusted ref: {value!r}")
    if v.startswith("-"):
        raise RetentionError(
            f"unsafe {what} for a trusted ref: {value!r} would be parsed as a git option"
        )
    if v == "." or v == ".." or ".." in v:
        raise RetentionError(
            f"unsafe {what} for a trusted ref: {value!r} traverses the ref namespace"
        )
    return v


def trusted_ref(*, candidate: str, run_id: str, task_id: str, attempt_id: str) -> str:
    """The one canonical trusted-ref path for a verified attempt's commit.

    Every component is validated, so a crafted id cannot escape the namespace
    (e.g. ``../heads/master``) or start with ``-`` and be read as a git flag.
    """
    return "/".join(
        [
            TRUSTED_ROOT,
            _validate_component(candidate, "candidate"),
            _validate_component(run_id, "run_id"),
            _validate_component(task_id, "task_id"),
            _validate_component(attempt_id, "attempt_id"),
        ]
    )


def retain_verified_commit(
    *,
    repo: str,
    worktree: str,
    candidate: str,
    run_id: str,
    task_id: str,
    attempt_id: str,
    base_commit: str = "",
) -> str:
    """Pin the verifier-approved commit of ONE attempt under a trusted ref.

    Called by trusted control-plane code at terminalization, BEFORE the lease is
    released (release deletes the worker branch). Returns the retained commit
    sha, or "" when there is genuinely nothing to retain.

    The commit is read from the attempt's own worktree HEAD — the same object the
    verifier just diffed and approved — NEVER from worker self-report.

    Idempotent: re-running for the same attempt lands on the same commit. A
    retained commit is IMMUTABLE — rewriting the ref to a different commit is
    refused, because a dependent may already have been told to trust that name.
    """
    rc, head, err = _git(worktree, ["rev-parse", "HEAD"], caller="retain")
    if rc != 0 or not _SHA_RE.match(head):
        # Nothing verifiable to retain. Not an error: an attempt that never
        # committed (the injected-failure case) legitimately has nothing.
        logger.debug("retain: no resolvable HEAD in %s: %s", worktree, err or head)
        return ""

    # An attempt that produced NO COMMIT still has a resolvable HEAD — its own
    # base. Retaining that would publish the pre-existing base as if it were this
    # attempt's verified output. Measured: the first version did exactly that.
    base = str(base_commit or "").strip()
    if base and head == base:
        logger.debug("retain: attempt %s produced no commit above its base", attempt_id)
        return ""

    ref = trusted_ref(candidate=candidate, run_id=run_id, task_id=task_id, attempt_id=attempt_id)

    existing = resolve_trusted_commit(
        repo=repo, candidate=candidate, run_id=run_id, task_id=task_id, attempt_id=attempt_id
    )
    if existing and existing != head:
        raise RetentionError(
            f"trusted ref {ref} already pins {existing[:12]}; refusing to rewrite it to "
            f"{head[:12]} — a verified commit is immutable once retained"
        )
    if existing == head:
        return head

    # Compare-and-swap against "must not exist": two concurrent terminalizations
    # cannot both create the ref, so retention is race-free.
    rc, _out, err = _git(repo, ["update-ref", ref, head, ""], caller="retain_update")
    if rc != 0:
        raise RetentionError(f"could not write trusted ref {ref}: {err}")
    logger.info("retained verified commit %s for attempt %s at %s", head[:12], attempt_id, ref)
    return head


def resolve_trusted_commit(
    *,
    repo: str,
    candidate: str,
    run_id: str,
    task_id: str,
    attempt_id: str,
) -> str:
    """Resolve one retained commit, or "" when no trusted ref exists.

    A CPU-gate refusal RAISES rather than reporting a real ref as absent.
    """
    ref = trusted_ref(candidate=candidate, run_id=run_id, task_id=task_id, attempt_id=attempt_id)
    rc, out, _err = _git(
        repo, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], caller="resolve"
    )
    if rc != 0 or not _SHA_RE.match(out):
        return ""
    return out


def release_trusted_refs(*, repo: str, candidate: str, run_id: str) -> list[str]:
    """Delete every trusted retention ref for ONE run.

    Called only at graph teardown / authorized cleanup, when no dependent can
    still need a retained commit. Returns the refs deleted. Idempotent: deleting
    nothing is success. Scoped by candidate AND run, so one run's teardown can
    never free another run's retained commits.
    """
    deleted: list[str] = []
    prefix = (
        f"{TRUSTED_ROOT}/{_validate_component(candidate, 'candidate')}/"
        f"{_validate_component(run_id, 'run_id')}/"
    )
    rc, out, err = _git(
        repo, ["for-each-ref", "--format=%(refname)", prefix], caller="release_list"
    )
    if rc != 0:
        # A failed LISTING means we cannot know what to delete. Returning the refs
        # deleted so far would report a release that never happened, and the
        # caller would treat the graph as torn down while refs leaked.
        raise RetentionError(
            f"could not enumerate trusted refs under {prefix}: {err or rc} — "
            f"refusing to report a release that did not happen"
        )
    for ref in [r.strip() for r in out.splitlines() if r.strip()]:
        rc2, _o, err2 = _git(repo, ["update-ref", "-d", ref], caller="release_delete")
        if rc2 == 0:
            deleted.append(ref)
        else:
            logger.warning("could not delete trusted ref %s: %s", ref, err2)
    return deleted
