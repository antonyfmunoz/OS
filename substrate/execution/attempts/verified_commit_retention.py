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

# Control-plane object-promotion namespace. Invocation 40 (run
# 20260807T234550Z-p1) proved the durability gap this closes: the lease is a
# SELF-CONTAINED repo (make_lease_selfcontained copies the fixture's objects
# in), so a worker's commit objects live only in the lease's private
# ``.git/objects`` — the fixture repo that retention writes refs in never
# receives them, and ``update-ref`` fails with "nonexistent object" on every
# succeeded attempt. Promotion is the trusted control-plane step that imports
# the attempt's complete reachable object closure into the durable repo BEFORE
# verification settles, so the verifier proves an object that already durably
# exists and retention pins that same object.
PROMOTED_ROOT = "refs/umh/promoted"

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


def promoted_ref(*, candidate: str, run_id: str, task_id: str, attempt_id: str) -> str:
    """The one canonical promoted-ref path for an attempt's imported objects.

    Mirrors :func:`trusted_ref` component validation, so a crafted id cannot
    escape the namespace or be read as a git option.
    """
    return "/".join(
        [
            PROMOTED_ROOT,
            _validate_component(candidate, "candidate"),
            _validate_component(run_id, "run_id"),
            _validate_component(task_id, "task_id"),
            _validate_component(attempt_id, "attempt_id"),
        ]
    )


def promote_attempt_objects(
    *,
    repo: str,
    worktree: str,
    candidate: str,
    run_id: str,
    task_id: str,
    attempt_id: str,
    base_commit: str = "",
) -> str:
    """Import ONE attempt's commit closure into durable control-plane storage.

    THE WORKER MAY PRODUCE BYTES; IT MAY NOT DECLARE THEM TRUSTWORTHY. The
    commit is derived by the CONTROL PLANE from the attempt's own private ref
    (``refs/attempt/<id>/work`` — the only ref the isolation profile lets the
    worker move, bound to the attempt id by construction), never from
    ``worker_result.commits``. A fabricated commit list cannot cause a foreign
    object to be promoted, because nothing here reads it.

    ``git fetch <worktree> <attempt-ref>:<promoted-ref>`` transfers the COMPLETE
    reachable closure (commit + trees + blobs + parents) into ``repo`` and pins
    it under a control-plane-owned promoted ref. Fetch transfers reachable
    objects only, so loose unreachable objects a worker planted in its own
    object store are NOT imported (measured). No branch, HEAD, or other shared
    ref is touched.

    Returns the promoted commit sha, or "" when the attempt genuinely produced
    no commit above its base (nothing to promote is not an error — the
    injected-failure attempt legitimately has nothing).

    Fail-closed properties:
      * worktree HEAD must EQUAL the attempt ref — a worker that re-pointed
        HEAD elsewhere is refused, not silently promoted;
      * the commit must descend from the authorized base — a reset/foreign
        history is refused;
      * idempotent: an existing promoted ref pointing at the same sha is
        success; pointing anywhere else is refused (one attempt, one promotion);
      * a fetch that reports success but leaves the commit or its tree
        unresolvable in ``repo`` is refused (partial promotion is not success).
    """
    from substrate.execution.attempts.field_task_scope import attempt_ref_name

    # A missing worktree is a distinct fact from a CPU-gate refusal (Finding 3):
    # ``gated_subprocess_run`` returns None on FileNotFoundError too, and ``_git``
    # maps every None to CpuGateRefused ("host overloaded"), which would point an
    # operator at load when the real fault is a deleted lease. Check explicitly.
    import os as _os

    if not _os.path.isdir(worktree):
        raise RetentionError(
            f"attempt {attempt_id}: lease worktree {worktree!r} does not exist — the "
            f"objects it held cannot be promoted (the lease was removed before promotion)"
        )

    # "git is UNREADABLE" and "the attempt produced NO commit" are DIFFERENT
    # facts and must not collapse to the same "" (independent review CRITICAL).
    # A worker can corrupt its own lease git (e.g. writing .git/packed-refs), and
    # rev-parse then returns rc=128. Returning "" there made the poller — which
    # reacts only to RetentionError and discards the return value — mint a durable
    # Proof for a commit that exists only in the corrupt lease: the invocation-40
    # defect through a different door. A non-zero rc RAISES; only a clean rc=0
    # HEAD that equals the base is the legitimate no-commit case.
    rc, head, err = _git(worktree, ["rev-parse", "HEAD"], caller="promote_head")
    if rc != 0:
        raise RetentionError(
            f"attempt {attempt_id}: cannot resolve HEAD in lease {worktree!r} "
            f"(rc={rc}): {err or head} — the lease git is unreadable; refusing to "
            f"treat an unreadable repository as 'nothing to promote'"
        )
    if not _SHA_RE.match(head):
        raise RetentionError(
            f"attempt {attempt_id}: HEAD in lease {worktree!r} did not resolve to a "
            f"commit sha ({head!r}) — refusing to promote an unresolvable HEAD"
        )

    # The authorized base is MANDATORY, not optional (independent review MEDIUM).
    # Every downstream guard — the no-commit short-circuit, the descent-from-base
    # ancestry check, and the base..head authorship scan — is gated on a real
    # base. An empty base silently downgraded promotion to shape-only and let a
    # fully orphan foreign-root commit be imported (measured). The poller always
    # passes lease.snapshot_ref, which real field data shows is always populated;
    # enforce that precondition rather than trusting it, mirroring the
    # unresolved-binding fail-closed the poller now applies.
    base = str(base_commit or "").strip()
    if not _SHA_RE.match(base):
        raise RetentionError(
            f"attempt {attempt_id}: no authorized base commit supplied ({base_commit!r}) "
            f"— promotion cannot establish that {head[:12]} is this attempt's own work "
            f"without one; refusing to promote against an unknown base"
        )
    if head == base:
        logger.debug("promote: attempt %s produced no commit above its base", attempt_id)
        return ""

    ref = attempt_ref_name(attempt_id)
    rc, ref_sha, err = _git(
        worktree, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], caller="promote_ref"
    )
    if rc != 0 or not _SHA_RE.match(ref_sha):
        raise RetentionError(
            f"attempt {attempt_id}: private attempt ref {ref} does not resolve in the "
            f"lease while HEAD {head[:12]} sits above the base — the control plane "
            f"cannot derive a trusted commit for this attempt; refusing to promote"
        )
    if ref_sha != head:
        raise RetentionError(
            f"attempt {attempt_id}: lease HEAD {head[:12]} does not equal the attempt's "
            f"own ref {ref} ({ref_sha[:12]}) — a re-pointed HEAD is not this attempt's "
            f"verified work; refusing to promote"
        )

    dst = promoted_ref(candidate=candidate, run_id=run_id, task_id=task_id, attempt_id=attempt_id)

    # IDEMPOTENCY FIRST — before the authorship scan below. On a legitimate
    # re-promotion (crash recovery) THIS attempt's commit already exists durably
    # because we promoted it last time, so the "must be new to the durable repo"
    # authorship check would wrongly refuse it. Resolving the existing promoted
    # ref (which peels through the commit object, so it only succeeds when the
    # object is durable) settles the already-mine case here and returns, leaving
    # the authorship scan to run only on a FIRST promotion.
    rc, existing, _e = _git(
        repo, ["rev-parse", "--verify", "--quiet", f"{dst}^{{commit}}"], caller="promote_existing"
    )
    if rc == 0 and _SHA_RE.match(existing):
        if existing != head:
            raise RetentionError(
                f"promoted ref {dst} already pins {existing[:12]}; refusing to repoint it "
                f"to {head[:12]} — one attempt promotes exactly one commit"
            )
        return head

    # ANCESTRY FIRST — this ordering is LOAD-BEARING for the authorship scan
    # below (independent review MEDIUM). A worker can write .git/shallow (it is
    # not in the read-only barrier — a durable-side fetch renegotiates the real
    # closure, so it is harmless to promotion itself). A crafted shallow graft
    # could truncate history so an intermediate foreign commit disappears from
    # `rev-list base..head`, hiding it from the authorship walk. But every shallow
    # cut that removes an ancestor from the range ALSO severs base→head, so THIS
    # `--is-ancestor` check (run BEFORE the walk) fails closed on exactly those
    # cuts: shallow=head and shallow=F both make is-ancestor rc=1; shallow=base
    # keeps ancestry true but leaves F in the range for the walk to catch. Do not
    # reorder or remove this check, and keep it adjacent to the authorship walk.
    rc, _o, _e = _git(
        worktree, ["merge-base", "--is-ancestor", base, head], caller="promote_ancestry"
    )
    if rc != 0:
        raise RetentionError(
            f"attempt {attempt_id}: commit {head[:12]} does not descend from its "
            f"authorized base {base[:12]} — a reset or foreign history cannot be "
            f"promoted as this attempt's work"
        )

    # AUTHORSHIP, NOT MERELY SHAPE (independent review CRITICAL, invocation-40 fix).
    # RELIES ON the ancestry check immediately above to defeat a worker-written
    # .git/shallow truncation — see that comment; the two checks are one unit.
    #
    # Descent-from-base proves the commit is SHAPED like this attempt's work; it
    # does NOT prove the ATTEMPT AUTHORED it. The lease is a self-contained copy
    # of the whole durable repo (make_lease_selfcontained), so every fixture
    # branch tip, ancestor, and — once promotion ships — every previously
    # promoted commit is already resolvable inside the sandbox. A worker that
    # does zero work can point its own writable ref (refs/attempt/<id>/work — the
    # ONE surface the isolation profile leaves writable) at any such
    # foreign-but-in-scope commit; it descends from the base and every prior
    # shape guard passes. Reviewer reproduced this and the fan-in base
    # (composition.resolve_downstream_base) would then trust a commit no attempt
    # produced.
    #
    # The airtight discriminator is ORIGIN, checked BEFORE the fetch imports the
    # objects: every commit on the range base..head must be NEW to the durable
    # repo. A genuine worker authored all of them, so none pre-exist; a forger
    # either points at a commit that already exists durably (the tip pre-exists)
    # or builds atop one (a commit in the range pre-exists as a parent). Both are
    # refused. This is a BINDING to what the attempt created, not another shape
    # check a foreign object can satisfy.
    rc, revs, err = _git(worktree, ["rev-list", f"{base}..{head}"], caller="promote_authorship")
    if rc != 0:
        raise RetentionError(
            f"attempt {attempt_id}: cannot enumerate its own commit range "
            f"{base[:12]}..{head[:12]}: {err} — refusing to promote unverifiable authorship"
        )
    range_commits = [c.strip() for c in revs.splitlines() if _SHA_RE.match(c.strip())]
    if not range_commits:
        # head != base was already established above, so an empty range here is a
        # contradiction (grafts/replace) — fail closed rather than promote nothing.
        raise RetentionError(
            f"attempt {attempt_id}: commit {head[:12]} sits above base {base[:12]} yet "
            f"the range is empty — refusing an inconsistent history"
        )
    for c in range_commits:
        rc, _o, _e = _git(repo, ["cat-file", "-e", c], caller="promote_preexist")
        if rc == 0:
            raise RetentionError(
                f"attempt {attempt_id}: commit {c[:12]} in its range {base[:12]}..{head[:12]} "
                f"already exists in the durable repo BEFORE promotion — this attempt did not "
                f"author it (a worker pointed its ref at, or built atop, foreign/prior work); "
                f"refusing to promote another attempt's commit as this attempt's verified work"
            )

    # (Idempotency + repoint refusal were already settled above, BEFORE the
    # authorship scan, so a legitimate re-promotion returns early and does not
    # trip the "must be new to the durable repo" check on its own prior commit.
    # A promoted ref whose object was pruned does NOT peel above, so it falls
    # through to here and self-heals from the still-live lease.)
    rc, _out, err = _git(
        repo, ["fetch", "--no-tags", worktree, f"{ref}:{dst}"], caller="promote_fetch"
    )
    if rc != 0:
        raise RetentionError(
            f"could not promote attempt {attempt_id} objects into {repo}: git fetch failed: {err}"
        )

    # Prove the closure actually landed — a fetch that "succeeded" but left the
    # commit or its tree unresolvable is a partial promotion, which is failure.
    rc, _o, _e = _git(repo, ["cat-file", "-e", head], caller="promote_verify")
    if rc != 0:
        raise RetentionError(
            f"promotion fetch completed but commit {head[:12]} does not resolve in "
            f"{repo} — partial promotion is not success"
        )
    rc, tree, _e = _git(repo, ["rev-parse", f"{head}^{{tree}}"], caller="promote_tree")
    if rc != 0 or not tree:
        raise RetentionError(
            f"promotion fetch completed but tree of {head[:12]} does not resolve in "
            f"{repo} — incomplete object closure; refusing to report promotion"
        )
    logger.info("promoted attempt %s commit %s into %s at %s", attempt_id, head[:12], repo, dst)
    return head


def resolve_promoted_commit(
    *,
    repo: str,
    candidate: str,
    run_id: str,
    task_id: str,
    attempt_id: str,
) -> str:
    """Resolve one promoted commit, or "" when no promoted ref exists.

    A CPU-gate refusal RAISES rather than reporting a real ref as absent.
    """
    ref = promoted_ref(candidate=candidate, run_id=run_id, task_id=task_id, attempt_id=attempt_id)
    rc, out, _err = _git(
        repo, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], caller="resolve_promoted"
    )
    if rc != 0 or not _SHA_RE.match(out):
        return ""
    return out


def list_promoted_refs(*, repo: str, candidate: str, run_id: str) -> list[str]:
    """Every promoted ref for ONE run (authoritative enumeration, raises on failure)."""
    prefix = (
        f"{PROMOTED_ROOT}/{_validate_component(candidate, 'candidate')}/"
        f"{_validate_component(run_id, 'run_id')}/"
    )
    rc, out, err = _git(
        repo, ["for-each-ref", "--format=%(refname)", prefix], caller="list_promoted"
    )
    if rc != 0:
        raise RetentionError(f"could not enumerate promoted refs under {prefix}: {err or rc}")
    return [r.strip() for r in out.splitlines() if r.strip()]


def release_promoted_refs(*, repo: str, candidate: str, run_id: str) -> list[str]:
    """Delete every promoted ref for ONE run at graph teardown.

    Scoped by candidate AND run. Idempotent. The promoted OBJECTS stay in the
    object database until git prunes unreachables — deleting the ref only ends
    the control plane's durability guarantee, which is correct once the run's
    retained/composed authority has itself been released.
    """
    deleted: list[str] = []
    for ref in list_promoted_refs(repo=repo, candidate=candidate, run_id=run_id):
        rc, _o, err = _git(repo, ["update-ref", "-d", ref], caller="release_promoted")
        if rc == 0:
            deleted.append(ref)
        else:
            logger.warning("could not delete promoted ref %s: %s", ref, err)
    return deleted


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
    import os as _os

    # A missing worktree is a distinct fact from a CPU-gate refusal (independent
    # review MEDIUM): ``gated_subprocess_run`` returns None on FileNotFoundError,
    # which ``_git`` maps to CpuGateRefused ("host overloaded") — a load diagnosis
    # for a filesystem fault. Name it correctly. This raises (rather than the
    # benign "" below) because a lease that vanished before retention is an error,
    # not a legitimate no-commit attempt.
    if not _os.path.isdir(worktree):
        raise RetentionError(
            f"attempt {attempt_id}: lease worktree {worktree!r} does not exist at "
            f"retention — the verified commit cannot be read (the lease was removed early)"
        )
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

    # VERIFIED == PROMOTED == RETAINED (invocation 40). When a promotion ran for
    # this attempt, the retained target must be exactly the promoted commit — a
    # divergence means the verifier proved one object and retention is about to
    # publish another, which is the two-object split this law forbids.
    promoted = resolve_promoted_commit(
        repo=repo, candidate=candidate, run_id=run_id, task_id=task_id, attempt_id=attempt_id
    )
    if promoted and promoted != head:
        raise RetentionError(
            f"attempt {attempt_id}: worktree HEAD {head[:12]} does not equal its promoted "
            f"commit {promoted[:12]} — verified/promoted/retained must be ONE object; "
            f"refusing to retain a divergent commit"
        )

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
