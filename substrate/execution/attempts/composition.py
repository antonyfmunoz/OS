"""Deterministic governed fan-in composition for a control-plane Task.

When Task C depends on verified Tasks A and B, something must turn two protected
retained commits into ONE conflict-free base that Task D can build on. Before
this module, ``retain_verified_commit`` pinned those commits and **nothing
consumed them**: the scheduler had no way to compose them, no way to create an
attempt without a model worker, and no way to hand the result downstream.

The composition is performed by the CONTROL PLANE, not by a worker:

    verified predecessor Attempts
      → protected refs/umh/verified commits
      → deterministic conflict-free merge-tree composition
      → Attempt-bound integration verification
      → Attempt-bound Proof
      → refs/umh/composed (the downstream trusted base)
      → bounded cleanup

WHY GIT PLUMBING AND NOT ``git merge``
--------------------------------------
``git merge`` needs a checkout, mutates an index, and leaves a working tree that
another attempt could observe mid-flight. ``merge-tree --write-tree`` computes
the merged tree as a pure function of (base, A, B) — no checkout, no index, no
worktree — and ``commit-tree`` seals it. The only checkout this module ever makes
is a throwaway detached worktree used to RUN the acceptance suite, removed on
every terminal path.

MEASURED GIT SEMANTICS (git 2.43.0, probed — not assumed)
---------------------------------------------------------
Every rule below was measured against a real repository before being encoded:

* ``rc == 0``  → clean merge; stdout line 1 is the merged tree OID.
* ``rc == 1``  → **AMBIGUOUS**. It is a real content conflict *only* when stdout
  line 1 is a 40-hex OID (followed by stage-1/2/3 entries). A bad or unmergeable
  commit argument ALSO returns ``rc == 1``, with stdout
  ``"merge-tree: <sha> - not something we can merge"`` and no tree OID.
  Distinguishing these by return code alone would report a MISSING verified
  commit — a corrupted or garbage-collected trusted ref — as a content conflict,
  which is the wrong failure class entirely. So the shape of stdout, not the
  return code, is the authority.
* ``rc > 1``   → git error (measured: a bad ``--merge-base`` yields 128).
* Trees are order-independent: ``merge-tree(A,B) == merge-tree(B,A)`` (measured).
* Commits are NOT: parent order, message and dates each change the commit SHA
  (measured), which is why identity is pinned and parents are canonically sorted.
* Predecessor effects survive exactly: an added/modified blob keeps its SHA, a
  DELETED path is ABSENT (so "present with the same blob" is the wrong rule for
  deletions), a mode change carries ``100644 → 100755`` with an unchanged blob,
  a rename leaves the old path absent and the new path present with the same
  blob, and an empty file is the canonical empty blob
  ``e69de29bb2d1d6434b8b29ae775ad8c2e48c5391``.

DETERMINISM CONTRACT (truthful)
-------------------------------
* TREE identity is deterministic **globally**: identical canonical predecessor
  inputs always yield the identical tree SHA, regardless of completion order.
* COMMIT identity is deterministic **within one composition Attempt**: the
  message embeds the attempt id for audit binding, so a different Attempt
  legitimately produces a different commit pointing at the SAME tree.

Scope: exactly two predecessors — the canonical A∧B→C diamond. The graph-shape
gate fixes ``IMPLEMENTATION_LANES = 2``, so a wider fan-in is unreachable today
and is refused rather than silently half-supported.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from typing import Any

from substrate.execution.attempts.verified_commit_retention import (
    CpuGateRefused,
    resolve_trusted_commit,
)
from substrate.execution.cpu_gate import gated_subprocess_run

logger = logging.getLogger(__name__)

#: The protected namespace a composed commit is pinned under. Mirrors
#: ``verified_commit_retention.TRUSTED_ROOT`` and is equally authoritative: a
#: composition Attempt's output lives here, NEVER under refs/umh/verified.
COMPOSED_ROOT = "refs/umh/composed"

#: Pinned composer identity. Fixed so the commit SHA is a pure function of its
#: inputs — measured: unsetting the dates alone changes the commit id.
_COMPOSER_NAME = "umh-composer"
_COMPOSER_EMAIL = "composer@umh.internal"
_COMPOSER_DATE = "@1700000000 +0000"

#: Exactly two predecessors. Not a soft preference: ``IMPLEMENTATION_LANES = 2``
#: in the graph-shape gate, so anything else is a malformed graph, and a
#: silently-partial fan-in would compose SOME of the verified work and report
#: success.
REQUIRED_PREDECESSORS = 2

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_EMPTY_BLOB = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"


class CompositionError(RuntimeError):
    """Composition could not be performed. Fail closed.

    Distinct from :class:`CompositionConflict`: this is an INFRASTRUCTURE or
    INPUT failure (missing commit, git error, unresolvable base). Reporting it as
    a conflict would blame the predecessors' content for a broken ref.
    """


class CompositionConflict(CompositionError):
    """The predecessors' content genuinely conflicts.

    Raised ONLY when git produced a real merge result with conflicted stages —
    never merely because the return code was 1 (see the module docstring).
    """


@dataclass
class CompositionResult:
    """Truthful record of one composition. No side effects, no self-report."""

    ok: bool = False
    composed_commit: str = ""
    composed_ref: str = ""
    tree_sha: str = ""
    merge_base: str = ""
    #: task_id → the retained commit that task contributed (canonically ordered).
    predecessor_commits: dict[str, str] = field(default_factory=dict)
    conflict_paths: list[str] = field(default_factory=list)
    reused_existing: bool = False
    steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "composed_commit": self.composed_commit,
            "composed_ref": self.composed_ref,
            "tree_sha": self.tree_sha,
            "merge_base": self.merge_base,
            "predecessor_commits": dict(self.predecessor_commits),
            "conflict_paths": list(self.conflict_paths),
            "reused_existing": self.reused_existing,
            "steps": list(self.steps),
            "errors": list(self.errors),
        }


# ── git plumbing ─────────────────────────────────────────────────────────────
def _git(repo: str, args: list[str], *, caller: str) -> tuple[int, str, str]:
    """Run one git command under the CPU gate. Returns (rc, stdout, stderr).

    A gate refusal RAISES. It is not a git answer, and collapsing it into one
    would let host load look like "no conflict" or "no such ref".
    """
    proc = gated_subprocess_run(
        ["git", *args],
        caller=f"composition.{caller}",
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


def _assert_is_commit(repo: str, sha: str, *, what: str) -> str:
    """Prove ``sha`` names a real commit object BEFORE it is fed to merge-tree.

    This pre-flight is load-bearing, not defensive decoration. Measured: passing
    a well-formed but non-existent sha to ``merge-tree --write-tree`` returns
    rc=1 — the SAME code as a genuine conflict. Catching it here means a
    corrupted or garbage-collected trusted ref surfaces as a CompositionError
    ("this commit does not exist") instead of a CompositionConflict ("your two
    Tasks disagree"), which is the difference between fixing retention and
    hunting a phantom merge conflict.
    """
    if not _SHA_RE.match(str(sha or "")):
        raise CompositionError(f"{what} {sha!r} is not a 40-hex commit sha")
    rc, out, err = _git(repo, ["cat-file", "-t", sha], caller="cat_file_type")
    if rc != 0 or out != "commit":
        raise CompositionError(
            f"{what} {sha[:12]} does not resolve to a commit object in {repo} "
            f"(type={out!r} rc={rc} {err}) — refusing to compose from a missing commit"
        )
    return sha


def _merge_tree(repo: str, *, base: str, left: str, right: str) -> tuple[str, list[str]]:
    """Compute the merged tree. Returns (tree_sha, conflict_paths).

    Classification is by (rc, stdout SHAPE) because rc alone is ambiguous — see
    the module docstring. ``rc == 1`` with a tree OID on line 1 is a real
    conflict; ``rc == 1`` without one is git refusing an input.
    """
    rc, out, err = _git(
        repo,
        ["merge-tree", "--write-tree", f"--merge-base={base}", left, right],
        caller="merge_tree",
    )
    lines = [ln for ln in (out or "").splitlines()]
    head = lines[0].strip() if lines else ""

    if rc == 0:
        if not _SHA_RE.match(head):
            raise CompositionError(
                f"merge-tree reported success but produced no tree oid "
                f"(stdout={out[:200]!r} stderr={err[:200]!r})"
            )
        return head, []

    if rc == 1:
        if not _SHA_RE.match(head):
            # NOT a conflict — git rejected an argument. Measured shape:
            # "merge-tree: <sha> - not something we can merge".
            raise CompositionError(
                f"merge-tree could not merge the supplied commits (rc=1 with no tree oid): "
                f"{out[:200]!r} {err[:200]!r} — this is an input/infrastructure failure, "
                f"not a content conflict"
            )
        # Conflicted-file info follows the tree oid as stage lines:
        #   "<mode> <oid> <stage>\t<path>"
        paths: list[str] = []
        for ln in lines[1:]:
            if "\t" not in ln:
                continue
            path = ln.split("\t", 1)[1].strip()
            if path and path not in paths:
                paths.append(path)
        raise CompositionConflict(
            f"predecessors conflict on {paths or ['<unknown>']} — refusing to compose "
            f"a conflicted tree (Task C cannot complete on unresolved content)"
        )

    raise CompositionError(f"git merge-tree failed (rc={rc}): {err[:300]!r} {out[:200]!r}")


def _validate_component(value: str, what: str) -> str:
    """One ref-path component, or refuse. Mirrors the retention validator."""
    v = str(value or "").strip()
    if not v or not re.match(r"^[A-Za-z0-9._-]+$", v):
        raise CompositionError(f"unsafe {what} for a composed ref: {value!r}")
    if v.startswith("-"):
        raise CompositionError(
            f"unsafe {what} for a composed ref: {value!r} would be parsed as a git option"
        )
    if v == "." or v == ".." or ".." in v:
        raise CompositionError(
            f"unsafe {what} for a composed ref: {value!r} traverses the ref namespace"
        )
    return v


def composed_ref(*, candidate: str, run_id: str, task_id: str, attempt_id: str) -> str:
    """The one canonical composed-ref path for a composition attempt."""
    return "/".join(
        [
            COMPOSED_ROOT,
            _validate_component(candidate, "candidate"),
            _validate_component(run_id, "run_id"),
            _validate_component(task_id, "task_id"),
            _validate_component(attempt_id, "attempt_id"),
        ]
    )


def resolve_composed_commit(
    *, repo: str, candidate: str, run_id: str, task_id: str, attempt_id: str
) -> str:
    """Resolve one composed commit, or "" when no composed ref exists."""
    ref = composed_ref(candidate=candidate, run_id=run_id, task_id=task_id, attempt_id=attempt_id)
    rc, out, _err = _git(
        repo, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], caller="resolve"
    )
    if rc != 0 or not _SHA_RE.match(out):
        return ""
    return out


def release_composed_refs(*, repo: str, candidate: str, run_id: str) -> list[str]:
    """Delete every composed ref for one completed run. Idempotent.

    Mirrors ``release_trusted_refs``. Returns the refs actually deleted, so a
    caller can PROVE the namespace is empty rather than assume it.
    """
    prefix = "/".join(
        [
            COMPOSED_ROOT,
            _validate_component(candidate, "candidate"),
            _validate_component(run_id, "run_id"),
        ]
    )
    rc, out, err = _git(
        repo, ["for-each-ref", "--format=%(refname)", prefix], caller="release_list"
    )
    if rc != 0:
        raise CompositionError(f"cannot enumerate composed refs under {prefix}: {err}")
    deleted: list[str] = []
    for ref in [ln.strip() for ln in (out or "").splitlines() if ln.strip()]:
        rc2, _o, err2 = _git(repo, ["update-ref", "-d", ref], caller="release_delete")
        if rc2 != 0:
            raise CompositionError(f"cannot delete composed ref {ref}: {err2}")
        deleted.append(ref)
    return deleted


def resolve_run_binding(run_root: str) -> tuple[str, str, str]:
    """``(repo, candidate, run_id)`` for a run root, or ``("", "", "")``.

    Canonical layout: ``.../candidates/<lane>/<candidate>/targets/<run>/``, and
    the run's protected refs live in ``<run_root>/fixture``.

    BOTH components come from ONE anchor match. Resolving them from independent
    anchors is what previously produced silently misattributed refs: on
    ``.../candidates/wave2/<sha>/targets/A/targets/B/f`` the candidate came from
    the last ``candidates`` while the run came from the last ``targets``, so the
    two named different levels of the same path. Ambiguity is refused, never
    guessed.

    This is the ONE binding resolver every teardown caller uses, so a caller
    cannot accidentally sweep with a partial binding and then report zero
    residue over refs it never looked at.
    """
    parts = [p for p in str(run_root or "").split(os.sep) if p]
    found: tuple[str, str] | None = None
    for i, seg in enumerate(parts):
        if seg != "candidates" or len(parts) <= i + 4 or parts[i + 3] != "targets":
            continue
        cand, run = parts[i + 2], parts[i + 4]
        if cand in ("candidates", "targets") or run in ("candidates", "targets"):
            continue
        if found is not None and found != (cand, run):
            logger.warning("ambiguous candidate/run binding in %r — refusing to guess", run_root)
            return "", "", ""
        found = (cand, run)
    if found is None:
        return "", "", ""
    return os.path.join(run_root, "fixture"), found[0], found[1]


def _list_refs_under(
    repo: str, root: str, candidate: str, run_id: str, *, caller: str
) -> list[str]:
    """Refs still present under one protected namespace for one run.

    Read-only residue accounting. A failed enumeration RAISES rather than
    returning ``[]`` — "I could not look" must never be reported as "nothing is
    there", which is exactly how a leak becomes a green zero-residue claim.
    """
    prefix = "/".join(
        [
            root,
            _validate_component(candidate, "candidate"),
            _validate_component(run_id, "run_id"),
        ]
    )
    rc, out, err = _git(repo, ["for-each-ref", "--format=%(refname)", prefix], caller=caller)
    if rc != 0:
        raise CompositionError(
            f"could not enumerate refs under {prefix}: {err or rc} — refusing to report "
            f"an unknown namespace as empty"
        )
    return [ln.strip() for ln in (out or "").splitlines() if ln.strip()]


def list_composed_refs(*, repo: str, candidate: str, run_id: str) -> list[str]:
    """Composed refs still present for a run (residue accounting, no mutation)."""
    return _list_refs_under(repo, COMPOSED_ROOT, candidate, run_id, caller="list_composed")


def list_trusted_refs(*, repo: str, candidate: str, run_id: str) -> list[str]:
    """Trusted retention refs still present for a run (residue accounting).

    Lives here rather than in ``verified_commit_retention`` because that module
    ships the WRITE authority for retention and is not part of this packet's
    authorized surface. This is a pure read over the same namespace constant, so
    there is no second authority — only a second reader.
    """
    from substrate.execution.attempts.verified_commit_retention import TRUSTED_ROOT

    return _list_refs_under(repo, TRUSTED_ROOT, candidate, run_id, caller="list_trusted")


# ── predecessor authority ────────────────────────────────────────────────────
def resolve_predecessor_commits(
    *,
    repo: str,
    candidate: str,
    run_id: str,
    store: Any,
    dependency_task_ids: list[str],
) -> dict[str, str]:
    """The trusted retained commit each predecessor Task contributed.

    Authority chain, every link required:

        canonical dependency
          → a SUCCEEDED attempt for that Task
          → carrying a durable Attempt-bound proof_id
          → whose refs/umh/verified ref resolves to a real commit

    Excluded by construction: failed, blocked, cancelled, superseded and
    unverified attempts have no trusted ref to find; a worker's self-reported
    ``commits`` list is never consulted. A retry that later succeeded retains
    under its OWN attempt ref, so retry-success lineage supersedes the failed
    attempt with no special case.

    Duplicates are refused rather than collapsed: two SUCCEEDED attempts for one
    Task is ambiguous lineage, and picking either could compose the wrong slice.
    """
    resolved: dict[str, str] = {}
    for task_id in sorted(dependency_task_ids):
        succeeded = [
            a
            for a in store.attempts_for_task(task_id)
            if str(getattr(a, "status", "")) == "succeeded"
        ]
        if not succeeded:
            raise CompositionError(
                f"dependency {task_id} has no SUCCEEDED attempt — refusing to compose "
                f"from unverified work"
            )
        if len(succeeded) > 1:
            raise CompositionError(
                f"dependency {task_id} has {len(succeeded)} SUCCEEDED attempts "
                f"{sorted(a.attempt_id for a in succeeded)} — ambiguous lineage, refusing "
                f"to pick one"
            )
        attempt = succeeded[0]
        if not getattr(attempt, "proof_id", ""):
            raise CompositionError(
                f"dependency {task_id} attempt {attempt.attempt_id} is SUCCEEDED without a "
                f"proof_id — refusing to compose from unproven work"
            )
        commit = resolve_trusted_commit(
            repo=repo,
            candidate=candidate,
            run_id=run_id,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
        )
        if not commit:
            raise CompositionError(
                f"dependency {task_id} attempt {attempt.attempt_id} has no retained commit "
                f"under refs/umh/verified — the verified commit was never pinned or was "
                f"released early"
            )
        resolved[task_id] = commit

    if len(resolved) != REQUIRED_PREDECESSORS:
        raise CompositionError(
            f"composition requires exactly {REQUIRED_PREDECESSORS} verified predecessors, "
            f"resolved {len(resolved)} ({sorted(resolved)}) — a partial fan-in would compose "
            f"only some of the verified work and report success"
        )
    return resolved


# ── composition ──────────────────────────────────────────────────────────────
def _commit_message(task_id: str, attempt_id: str, predecessors: dict[str, str]) -> str:
    """Canonical commit message. Deterministic for a given attempt.

    The attempt id is deliberately included: it binds the commit to the Attempt
    that produced it for audit, at the cost of making the COMMIT (not the tree)
    run-scoped. That trade is stated in the module docstring rather than hidden.
    """
    lanes = "+".join(sorted(predecessors))
    return f"composed: {lanes} for {task_id} [attempt:{attempt_id}]"


def compose_predecessors(
    *,
    repo: str,
    candidate: str,
    run_id: str,
    task_id: str,
    attempt_id: str,
    predecessor_commits: dict[str, str],
) -> CompositionResult:
    """Deterministically compose two verified commits into one protected commit.

    Idempotent by construction: if this attempt's composed ref already exists,
    the existing commit is VALIDATED and reused rather than recomputed, so a
    restart mid-flight can never produce a second composition commit for one
    Attempt.
    """
    result = CompositionResult()

    if len(predecessor_commits) != REQUIRED_PREDECESSORS:
        raise CompositionError(
            f"compose_predecessors requires exactly {REQUIRED_PREDECESSORS} predecessors, "
            f"got {len(predecessor_commits)}"
        )

    # Canonical order by task_id — NOT completion order. This is what makes the
    # result independent of which lane happened to finish first.
    ordered = sorted(predecessor_commits.items())
    left_task, left = ordered[0]
    right_task, right = ordered[1]
    result.predecessor_commits = dict(ordered)

    ref = composed_ref(candidate=candidate, run_id=run_id, task_id=task_id, attempt_id=attempt_id)
    result.composed_ref = ref

    # Every predecessor must be a REAL commit before merge-tree sees it (a
    # missing one would otherwise masquerade as a conflict — measured).
    _assert_is_commit(repo, left, what=f"predecessor {left_task}")
    _assert_is_commit(repo, right, what=f"predecessor {right_task}")

    rc, base, err = _git(repo, ["merge-base", left, right], caller="merge_base")
    if rc != 0 or not _SHA_RE.match(base):
        raise CompositionError(
            f"no common ancestor for {left[:12]} and {right[:12]}: {err} — the predecessors "
            f"are not from one repository history"
        )
    result.merge_base = base
    result.steps.append(f"merge-base={base[:12]}")

    tree, conflicts = _merge_tree(repo, base=base, left=left, right=right)
    result.tree_sha = tree
    result.conflict_paths = conflicts
    result.steps.append(f"merged tree={tree[:12]}")

    # An existing composed ref for THIS attempt is prior work by this same
    # Attempt, not a rival: validate it and reuse. Recomposing would mint a
    # second commit for one Attempt on every restart.
    existing = resolve_composed_commit(
        repo=repo, candidate=candidate, run_id=run_id, task_id=task_id, attempt_id=attempt_id
    )
    if existing:
        rc, body, _e = _git(repo, ["cat-file", "-p", existing], caller="cat_existing")
        if rc != 0:
            raise CompositionError(f"composed ref {ref} points at unreadable {existing[:12]}")
        parsed = _parse_commit(body)
        if parsed["tree"] != tree:
            raise CompositionError(
                f"composed ref {ref} pins {existing[:12]} whose tree {parsed['tree'][:12]} "
                f"≠ recomputed {tree[:12]} — refusing to trust a divergent composition"
            )
        if parsed["parents"] != [left, right]:
            raise CompositionError(
                f"composed ref {ref} pins {existing[:12]} with parents {parsed['parents']} "
                f"≠ canonical {[left, right]} — refusing to trust a divergent composition"
            )
        result.composed_commit = existing
        result.reused_existing = True
        result.ok = True
        result.steps.append(f"reused existing composed commit {existing[:12]}")
        return result

    message = _commit_message(task_id, attempt_id, result.predecessor_commits)
    proc = gated_subprocess_run(
        ["git", "commit-tree", tree, "-p", left, "-p", right, "-m", message],
        caller="composition.commit_tree",
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": _COMPOSER_NAME,
            "GIT_AUTHOR_EMAIL": _COMPOSER_EMAIL,
            "GIT_AUTHOR_DATE": _COMPOSER_DATE,
            "GIT_COMMITTER_NAME": _COMPOSER_NAME,
            "GIT_COMMITTER_EMAIL": _COMPOSER_EMAIL,
            "GIT_COMMITTER_DATE": _COMPOSER_DATE,
        },
    )
    if proc is None:
        raise CpuGateRefused(
            "git commit-tree refused by the CPU gate — refusing to treat an "
            "infrastructure refusal as a composition failure"
        )
    commit = (proc.stdout or "").strip()
    if proc.returncode != 0 or not _SHA_RE.match(commit):
        raise CompositionError(
            f"git commit-tree failed (rc={proc.returncode}): {(proc.stderr or '')[:300]!r}"
        )

    # CAS against "must not exist": two concurrent composers cannot both create
    # the ref, so the composed artifact is race-free.
    rc, _o, err = _git(repo, ["update-ref", ref, commit, ""], caller="pin_composed")
    if rc != 0:
        raise CompositionError(f"could not pin composed ref {ref}: {err}")

    result.composed_commit = commit
    result.ok = True
    result.steps.append(f"composed commit {commit[:12]} pinned at {ref}")
    logger.info(
        "composed %s from %s + %s → %s at %s",
        task_id,
        left[:12],
        right[:12],
        commit[:12],
        ref,
    )
    return result


def _parse_commit(body: str) -> dict[str, Any]:
    """Parse ``cat-file -p <commit>`` into tree/parents/author/committer/message."""
    tree = ""
    parents: list[str] = []
    author = ""
    committer = ""
    lines = (body or "").splitlines()
    idx = 0
    for idx, line in enumerate(lines):
        if not line.strip():
            break
        if line.startswith("tree "):
            tree = line[5:].strip()
        elif line.startswith("parent "):
            parents.append(line[7:].strip())
        elif line.startswith("author "):
            author = line[7:].strip()
        elif line.startswith("committer "):
            committer = line[10:].strip()
    message = "\n".join(lines[idx + 1 :]).strip()
    return {
        "tree": tree,
        "parents": parents,
        "author": author,
        "committer": committer,
        "message": message,
    }


# ── content equivalence (MEASURED semantics) ─────────────────────────────────
def _name_status(repo: str, left: str, right: str) -> list[tuple[str, str, str]]:
    """``diff-tree -r -M`` as (status, path, renamed_to). Rename detection ON.

    Status is git's own letter: A/M/D/T/R. Encoding these separately matters —
    "the file is present with the same blob" is the WRONG rule for a deletion,
    which must be ABSENT, and for a rename, whose old path must be absent while
    the new one is present.
    """
    rc, out, err = _git(
        repo, ["diff-tree", "-r", "-M", "--name-status", left, right], caller="name_status"
    )
    if rc != 0:
        raise CompositionError(f"diff-tree {left[:12]}..{right[:12]} failed: {err}")
    entries: list[tuple[str, str, str]] = []
    for line in (out or "").splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0].strip()
        if status.startswith("R") and len(parts) >= 3:
            entries.append(("R", parts[1].strip(), parts[2].strip()))
        else:
            entries.append((status[:1], parts[1].strip(), ""))
    return entries


def _tree_entry(repo: str, tree: str, path: str) -> tuple[str, str]:
    """``(mode, blob_sha)`` for one path in a tree, or ``("", "")`` when absent."""
    rc, out, _err = _git(repo, ["ls-tree", tree, "--", path], caller="ls_tree")
    if rc != 0 or not (out or "").strip():
        return "", ""
    fields = out.split()
    if len(fields) < 3:
        return "", ""
    return fields[0], fields[2]


def verify_predecessor_content(
    *, repo: str, base: str, composed_tree: str, predecessor_commits: dict[str, str]
) -> tuple[bool, list[str], list[str]]:
    """Prove every predecessor EFFECT survives in the composed tree.

    Returns ``(ok, violations, produced_paths)``. ``produced_paths`` is the union
    of paths the predecessors added or modified — the collection floor is derived
    from THIS, never from a hardcoded fixture filename.

    Per-operation contract, each rule measured against git 2.43.0:

    ==========  ==================================================================
    A (add)     path present, blob AND mode equal
    M (modify)  path present, blob AND mode equal
    D (delete)  path ABSENT — presence would mean the deletion was lost
    T (type)    path present, mode equal (blob compared too)
    R (rename)  old path ABSENT and new path present with equal blob+mode
    empty file  no special case — equality on the canonical empty blob SHA
    ==========  ==================================================================
    """
    violations: list[str] = []
    produced: list[str] = []

    for task_id, commit in sorted(predecessor_commits.items()):
        for status, path, renamed_to in _name_status(repo, base, commit):
            if status == "D":
                mode, blob = _tree_entry(repo, composed_tree, path)
                if blob:
                    violations.append(
                        f"{task_id} deleted {path} but it is PRESENT in the composed tree "
                        f"({blob[:12]}) — the deletion was lost"
                    )
                continue

            if status == "R":
                old_mode, old_blob = _tree_entry(repo, composed_tree, path)
                if old_blob:
                    violations.append(
                        f"{task_id} renamed {path}→{renamed_to} but the OLD path is still "
                        f"present in the composed tree"
                    )
                target = renamed_to
            else:
                target = path

            want_mode, want_blob = _tree_entry(repo, commit, target)
            got_mode, got_blob = _tree_entry(repo, composed_tree, target)
            if not got_blob:
                violations.append(
                    f"{task_id} produced {target} ({status}) but it is ABSENT from the "
                    f"composed tree"
                )
                continue
            if got_blob != want_blob:
                violations.append(
                    f"{task_id} {target}: composed blob {got_blob[:12]} ≠ predecessor "
                    f"{want_blob[:12]}"
                )
            if got_mode != want_mode:
                violations.append(
                    f"{task_id} {target}: composed mode {got_mode} ≠ predecessor {want_mode}"
                )
            if target not in produced:
                produced.append(target)

    return (not violations), violations, produced


def verify_composed_scope(
    *, repo: str, base: str, composed_tree: str, allowed_paths: list[str]
) -> tuple[bool, list[str]]:
    """Every composed delta must be inside the Task's PERSISTED union scope.

    Uses the same ``paths_outside`` authority the worker diff-scope check uses, so
    composition cannot introduce content a worker would have been refused for.
    """
    from substrate.execution.attempts.field_task_scope import (
        normalize_allowed_paths,
        paths_outside,
    )

    changed: list[str] = []
    for status, path, renamed_to in _name_status(repo, base, composed_tree):
        changed.append(path)
        if status == "R" and renamed_to:
            changed.append(renamed_to)
    allowed = normalize_allowed_paths(list(allowed_paths or []), lease_root="")
    outside = paths_outside(changed, allowed)
    return (not outside), outside


def assert_descends_from_all(
    *, repo: str, composed_commit: str, predecessor_commits: dict[str, str]
) -> list[str]:
    """Every predecessor must be a real ancestor of the composed commit.

    A composed commit that does not descend from a predecessor cannot contain
    that predecessor's history no matter what its tree looks like. Returns the
    task ids that FAILED (empty means all pass).
    """
    failed: list[str] = []
    for task_id, commit in sorted(predecessor_commits.items()):
        rc, _o, _e = _git(
            repo, ["merge-base", "--is-ancestor", commit, composed_commit], caller="ancestry"
        )
        if rc != 0:
            failed.append(task_id)
    return failed


# ── Attempt-bound Proof, exactly one per composition Attempt ─────────────────
def composition_proof_action(
    *, attempt: Any, result: CompositionResult, predecessor_proofs: dict[str, str]
) -> dict[str, Any]:
    """The canonical ``action`` payload of a composition Proof.

    Carries every identity a later reader needs to decide whether an existing
    durable Proof describes THIS composition or a different one.
    """
    return {
        "attempt_id": str(getattr(attempt, "attempt_id", "")),
        "task_id": str(getattr(attempt, "task_id", "")),
        "kind": "control_plane_composition",
        "composed_commit": result.composed_commit,
        "composed_ref": result.composed_ref,
        "tree_sha": result.tree_sha,
        "merge_base": result.merge_base,
        "predecessor_commits": dict(result.predecessor_commits),
        "predecessor_proof_ids": dict(predecessor_proofs),
    }


def _composition_identity(action: dict[str, Any]) -> tuple:
    """The subset of a Proof action that decides "same composition or not"."""
    return (
        str(action.get("composed_commit", "")),
        str(action.get("tree_sha", "")),
        tuple(sorted((action.get("predecessor_commits") or {}).items())),
    )


def existing_composition_proof(
    *, proof_runtime: Any, attempt: Any, expected_action: dict[str, Any]
) -> Any:
    """The ONE durable Proof already bound to this composition Attempt, or None.

    Restart safety rests on this. ``ProofRuntime.create_direct`` mints a new
    proof_id unconditionally, so without a search-before-create a crash between
    "Proof persisted" and "attempt SUCCEEDED" would leave two durable records for
    one Attempt on the next pass.

    Enumeration is sound after a restart: ``_load_from_disk`` replays every JSONL
    line into ``_packages`` keyed by proof_id, and ``all_proofs()`` returns those
    values — so two records sharing one work_id both appear. (Only the SEPARATE
    ``_by_work_id`` index is last-write-wins, and it is not used here.)

    Fails closed on conflict rather than preferring one: two authoritative Proofs
    for one Attempt is corruption, not something to resolve by picking.
    """
    attempt_id = str(getattr(attempt, "attempt_id", ""))
    if not attempt_id:
        raise CompositionError("cannot resolve a composition Proof for an attempt with no id")

    matches = [
        p
        for p in proof_runtime.all_proofs()
        if str((getattr(p, "action", {}) or {}).get("attempt_id", "")) == attempt_id
    ]
    if not matches:
        return None

    want = _composition_identity(expected_action)
    for pkg in matches:
        got = _composition_identity(getattr(pkg, "action", {}) or {})
        if got != want:
            raise CompositionError(
                f"attempt {attempt_id}: durable Proof {pkg.proof_id} attests to a DIFFERENT "
                f"composition (commit/tree/inputs {got} ≠ {want}) — refusing to mint a second "
                f"authoritative Proof for one Attempt"
            )
    unique = {p.proof_id for p in matches}
    if len(unique) > 1:
        raise CompositionError(
            f"attempt {attempt_id}: {len(unique)} durable Proofs already bound "
            f"{sorted(unique)} — fail closed rather than choose an authority"
        )

    durable = proof_runtime.reread_durable(matches[0].proof_id)
    if durable is None:
        raise CompositionError(
            f"attempt {attempt_id}: Proof {matches[0].proof_id} is in-memory only — "
            f"not a durable Proof"
        )
    return durable


def mint_composition_proof(
    *, proof_runtime: Any, attempt: Any, action: dict[str, Any], verifier_identity: str
) -> Any:
    """Reuse the Attempt's existing durable Proof, or create exactly one."""
    existing = existing_composition_proof(
        proof_runtime=proof_runtime, attempt=attempt, expected_action=action
    )
    if existing is not None:
        logger.info(
            "reusing durable composition Proof %s for attempt %s",
            existing.proof_id,
            action.get("attempt_id"),
        )
        return existing
    return proof_runtime.create_direct(
        str(getattr(attempt, "task_id", "")),
        action,
        outcome="success",
        operator=verifier_identity or "verifier:composition",
    )


# ── downstream trusted base ──────────────────────────────────────────────────
def resolve_downstream_base(
    *,
    repo: str,
    candidate: str,
    run_id: str,
    store: Any,
    proof_runtime: Any,
    dependency_task_ids: list[str],
) -> str:
    """The exact composed commit a dependent Task must branch from, or "".

    ``attempt.commits[0]`` alone is NOT authority — ``commits`` is a mutable
    binding field. Every condition below must hold together:

      1. the dependency is a SUCCEEDED attempt,
      2. whose persisted ``execution_kind`` is the composition kind,
      3. carrying a proof_id that rereads DURABLY and binds to that attempt,
      4. whose composed ref (candidate/run/task/attempt scoped) resolves,
      5. and equals the commit recorded on the attempt.

    Returns "" when the dependency is not a composition — the caller then uses
    the default HEAD base, exactly as before this packet.
    """
    from substrate.execution.attempts.records import AttemptExecutionKind

    for task_id in sorted(dependency_task_ids):
        succeeded = [
            a
            for a in store.attempts_for_task(task_id)
            if str(getattr(a, "status", "")) == "succeeded"
            and str(getattr(a, "execution_kind", ""))
            == AttemptExecutionKind.CONTROL_PLANE_COMPOSITION.value
        ]
        if not succeeded:
            continue
        if len(succeeded) > 1:
            raise CompositionError(
                f"dependency {task_id} has {len(succeeded)} SUCCEEDED composition attempts — "
                f"ambiguous downstream base"
            )
        attempt = succeeded[0]

        proof_id = str(getattr(attempt, "proof_id", "") or "")
        if not proof_id:
            raise CompositionError(
                f"composition attempt {attempt.attempt_id} is SUCCEEDED with no proof_id"
            )
        durable = proof_runtime.reread_durable(proof_id)
        if durable is None:
            raise CompositionError(
                f"composition attempt {attempt.attempt_id} names Proof {proof_id} which is "
                f"not durably persisted — refusing to hand an unproven base downstream"
            )
        bound = str((getattr(durable, "action", {}) or {}).get("attempt_id", ""))
        if bound != attempt.attempt_id:
            raise CompositionError(
                f"Proof {proof_id} is bound to attempt {bound!r}, not "
                f"{attempt.attempt_id!r} — refusing a foreign Proof as base authority"
            )

        commit = resolve_composed_commit(
            repo=repo,
            candidate=candidate,
            run_id=run_id,
            task_id=task_id,
            attempt_id=attempt.attempt_id,
        )
        if not commit:
            raise CompositionError(
                f"composition attempt {attempt.attempt_id} has no composed ref — the "
                f"trusted base was never pinned or was released early"
            )
        recorded = list(getattr(attempt, "commits", []) or [])
        if recorded and recorded[0] != commit:
            raise CompositionError(
                f"composition attempt {attempt.attempt_id} records commit "
                f"{recorded[0][:12]} but its composed ref pins {commit[:12]} — refusing an "
                f"ambiguous downstream base"
            )
        return commit

    return ""


# ── isolated verification checkout ───────────────────────────────────────────
def verification_worktree(repo: str, commit: str, path: str) -> None:
    """Materialize ``commit`` at ``path`` as a detached throwaway worktree.

    The composed commit is never checked out anywhere else; the acceptance suite
    needs a real tree to run against. The caller MUST remove it on every terminal
    path (see ``remove_verification_worktree``).
    """
    _assert_is_commit(repo, commit, what="composed commit")
    rc, _o, err = _git(
        repo, ["worktree", "add", "--detach", path, commit], caller="verify_worktree_add"
    )
    if rc != 0:
        raise CompositionError(f"cannot create verification worktree at {path}: {err}")


def remove_verification_worktree(repo: str, path: str) -> None:
    """Remove the verification worktree. Never raises — cleanup is best-effort
    here, but the registry prune is always attempted so no stale entry survives."""
    try:
        _git(repo, ["worktree", "remove", "--force", path], caller="verify_worktree_rm")
    except Exception as exc:  # noqa: BLE001 - recorded, never silently swallowed
        logger.warning("verification worktree remove failed for %s: %s", path, exc)
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    try:
        _git(repo, ["worktree", "prune"], caller="verify_worktree_prune")
    except Exception as exc:  # noqa: BLE001
        logger.debug("worktree prune failed: %s", exc)


__all__ = [
    "COMPOSED_ROOT",
    "REQUIRED_PREDECESSORS",
    "CompositionError",
    "CompositionConflict",
    "CompositionResult",
    "composed_ref",
    "resolve_composed_commit",
    "release_composed_refs",
    "list_composed_refs",
    "list_trusted_refs",
    "resolve_predecessor_commits",
    "compose_predecessors",
    "verify_predecessor_content",
    "verify_composed_scope",
    "assert_descends_from_all",
    "composition_proof_action",
    "existing_composition_proof",
    "mint_composition_proof",
    "resolve_downstream_base",
    "verification_worktree",
    "remove_verification_worktree",
]
