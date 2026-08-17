"""Independent verification + the two Proof classifications (C5).

One canonical Proof authority (``substrate.organism.proof_runtime.ProofPackage``)
carries TWO classifications (Amendment v1 clause 6):

- **AttemptProof** — required for one Task attempt to reach SUCCEEDED. Produced by
  a verifier actor DISTINCT from the implementation worker. Validates diff scope,
  commits, tests, package hash, artifact hashes, and policy compliance. The
  worker's narrative is never sufficient; exit code 0 is never sufficient;
  dispatch success is never completion.

- **PlanExecutionProof** — produced by the final independent verification Task.
  Validates reconvergence, complete tests, live HTTP/UI/browser behavior, source
  integrity, and zero production deployment.

Dependency semantics enforced by the caller/scheduler: C unlocks only after A and
B each have an AttemptProof; D only after C; the Plan outcome completes only after
a PlanExecutionProof.

The verifier here runs INDEPENDENT checks (it does not trust the worker's report)
and returns a verdict + a persisted ProofPackage. The attempt's verifying→
succeeded transition (guarded in lifecycle.py) then requires this proof_id AND a
verifier identity distinct from the worker.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

ATTEMPT_PROOF = "attempt_proof"
PLAN_EXECUTION_PROOF = "plan_execution_proof"


@dataclass
class VerificationCheck:
    check_id: str = ""
    kind: str = ""  # diff | commits | tests | package_hash | artifact | http | browser | policy
    ok: bool = False
    detail: str = ""
    evidence_ref: str = ""
    evidence_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class VerificationVerdict:
    attempt_id: str = ""
    task_id: str = ""
    classification: str = ATTEMPT_PROOF
    verifier_identity: str = ""
    verifier_role_id: str = ""
    passed: bool = False
    checks: list[dict[str, Any]] = field(default_factory=list)
    proof_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def verify_attempt(
    *,
    attempt: Any,
    assignment: Any,
    lease: Any,
    worker_result: Any,
    package_hash: str,
    verifier_identity: str,
    verifier_role_id: str,
    packet: Any = None,
    semantic_label: str = "",
    independent_checks: Callable[[Any], list[VerificationCheck]] | None = None,
    proof_runtime: Any | None = None,
) -> VerificationVerdict:
    """Independently verify one attempt and produce an AttemptProof.

    The verifier identity MUST differ from the worker identity (enforced here AND
    again by the lifecycle guard on verifying→succeeded). Checks are INDEPENDENT
    of the worker's self-report."""
    worker_identity = getattr(assignment, "worker_identity", "") or getattr(
        attempt, "worker_identity", ""
    )
    if verifier_identity and worker_identity and verifier_identity == worker_identity:
        raise ValueError(
            f"verifier {verifier_identity!r} must differ from worker {worker_identity!r} "
            f"(separation of duty — an agent cannot verify its own work)"
        )

    checks: list[VerificationCheck] = []

    # 0. VERIFICATION CONTEXT must resolve (finding C4). A missing assignment or
    #    lease meant the verifier ran blind — `_assignment_lookup` silently
    #    returned None for every attempt, so no context check could fail. Absent
    #    context is now a verification FAILURE, not a quiet pass.
    context_missing: list[str] = []
    if assignment is None:
        context_missing.append("assignment")
    if lease is None:
        context_missing.append("lease")
    if not package_hash:
        context_missing.append("package_hash")
    checks.append(
        VerificationCheck(
            check_id="verification_context",
            kind="policy",
            ok=not context_missing,
            detail=(
                "all context resolved"
                if not context_missing
                else f"missing: {', '.join(context_missing)}"
            ),
        )
    )

    # 1. package hash sealed + matches the dispatched package.
    dispatched_hash = getattr(attempt, "instruction_package_hash", "")
    checks.append(
        VerificationCheck(
            check_id="package_hash",
            kind="package_hash",
            ok=bool(package_hash) and package_hash == dispatched_hash,
            detail=f"dispatched={dispatched_hash} verified={package_hash}",
        )
    )

    # 2. artifacts match the attempt's DECLARED execution contract.
    #
    #    Invocation-42 field defect. A single artifact-production predicate
    #    (`files>0 AND commits>0`) was applied to EVERY attempt. The zero-write
    #    verification lane (Task D) is contractually forbidden to write — its
    #    sealed WorkPacket declares `scope_declared=True, writable_path_scope=[]`,
    #    "you must not create, edit, or delete any file" — so it can NEVER produce
    #    an artifact, and the generic gate made it structurally impossible to
    #    satisfy. It was unreachable in the field until composition first
    #    succeeded (invocation 41 fix) and Task D finally ran.
    #
    #    The contract is read from the SAME persisted, package_hash-sealed
    #    authority the diff-scope check uses (`allowed_paths_for` → the
    #    WorkRequirements `writable_path_scope` + `scope_declared`), NEVER inferred
    #    from empty output, the task name, or worker prose. The authenticating
    #    condition for the zero-write lane is a SUCCESSFUL scope resolution that
    #    returns `[]` — which `allowed_paths_for` grants only when
    #    `scope_declared==True`. A packet with no declared scope raises there and
    #    reaches the fallback branch as an artifact-producing worker (fail
    #    closed): an accidentally malformed empty-scope task never acquires
    #    verifier semantics.
    #
    #    Composition attempts never reach verify_attempt's artifacts path — they
    #    are settled through the composition verifier + composition Proof — so
    #    only the two model-executed shapes are distinguished here.
    files = list(getattr(worker_result, "files_changed", []) or [])
    commits = list(getattr(worker_result, "commits", []) or [])
    zero_write_contract = False
    if packet is not None:
        from substrate.execution.attempts.field_task_scope import (
            ScopeResolutionError,
            allowed_paths_for,
        )

        try:
            # A declared, undeclared, or malformed scope resolves through the
            # SAME `allowed_paths_for` authority the diff-scope check uses. Catch
            # ONLY `ScopeResolutionError` — the expected "no/invalid declared
            # scope" outcome → artifact-producing worker (fail closed). This
            # mirrors `_diff_scope_verdict`'s own narrow catch, so an UNEXPECTED
            # error is not silently reclassified as a worker but propagates to
            # the poller's containment (attempt → FAILED, never a false pass).
            zero_write_contract = allowed_paths_for(packet, semantic_label=semantic_label) == []
        except ScopeResolutionError:
            zero_write_contract = False
    if zero_write_contract:
        # ZERO-WRITE VERIFIER: zero files AND zero commits is the REQUIRED
        # outcome, not a defect. A file or commit here is a scope violation
        # (also caught independently by diff_scope). Success authority is the
        # independent confined-verifier checks + zero-diff + Attempt-bound Proof
        # + exact trusted-base binding — proven by the other checks below, never
        # by an artifact. This is NOT green-on-nothing: every other check still
        # runs and must pass.
        artifacts_ok = not files and not commits
        artifacts_detail = (
            f"zero-write verifier contract: files={len(files)} commits={len(commits)} "
            f"(both must be 0)"
        )
    else:
        # ARTIFACT-PRODUCING WORKER (unchanged): concrete git evidence required.
        # The worker's narrative is NOT trusted.
        artifacts_ok = bool(files) and bool(commits)
        artifacts_detail = f"files={len(files)} commits={len(commits)}"
    checks.append(
        VerificationCheck(
            check_id="artifacts",
            kind="artifact",
            ok=artifacts_ok,
            detail=artifacts_detail,
        )
    )

    # 2b. TRUSTED-BASE BINDING for the zero-write verifier (invocation-42 field
    #     hardening + TASK D INPUT AUTHORITY law). A zero-write verifier's only
    #     authority is its verification of a specific trusted input — for Task D
    #     that is Task C's exact composed commit, resolved by
    #     `resolve_downstream_base` and threaded onto the lease's `snapshot_ref`.
    #     Without this, a verifier could "pass on nothing": run against an
    #     empty/absent base, produce zero diff, and be accepted. Require a
    #     resolvable, non-empty trusted base. (Artifact-producing workers already
    #     have this enforced transitively by the diff-scope check, which fails
    #     closed on a missing snapshot_ref; the explicit check makes the
    #     zero-write lane's input authority first-class rather than implied.)
    if zero_write_contract:
        trusted_base = str(getattr(lease, "snapshot_ref", "") or "").strip()
        checks.append(
            VerificationCheck(
                check_id="verifier_trusted_base",
                kind="policy",
                ok=bool(trusted_base),
                detail=(
                    f"verifier inspected trusted base {trusted_base[:12]}"
                    if trusted_base
                    else "zero-write verifier has no trusted base — a verifier that "
                    "inspected no authorized input cannot attest to anything"
                ),
            )
        )

    # 3. diff-scope: changes confined to the Task's AUTHORIZED paths, computed
    #    from the ACTUAL changed paths in the lease worktree.
    #
    #    Finding C-1: this check was structurally incapable of failing. The
    #    LeaseManager recorded `writable_paths=[<absolute worktree>]`, which
    #    normalized to "." → `whole_worktree=True` → `scope_ok=True`
    #    unconditionally, and the computed `outside` list was discarded. A worker
    #    that rewrote the fixture's own tests earned a valid AttemptProof.
    #
    #    The authority is now the Task's DECLARED allowed paths (canonical
    #    WorkPacket requirements, resolved by field_task_scope), never the lease
    #    worktree. The sandbox mount is a CONTAINMENT boundary; it was never a
    #    diff-scope authority, and treating it as one is what nullified the check.
    scope_ok, scope_detail = _diff_scope_verdict(
        lease=lease,
        packet=packet,
        worker_result=worker_result,
        semantic_label=semantic_label,
    )
    checks.append(
        VerificationCheck(
            check_id="diff_scope",
            kind="diff",
            ok=scope_ok,
            detail=scope_detail,
        )
    )

    # 4. independent domain checks (tests / http / browser) — supplied by the
    #    caller so the verifier runs the packet's OWN validation, not the worker's.
    #    The production supplier (the confined verifier) returns (checks, evidence);
    #    a legacy/harness supplier may return a bare list. The structured evidence
    #    is threaded into THIS attempt's Proof (C-4a) — never a process-local field.
    verifier_evidence: Any = None
    if independent_checks is not None:
        produced = independent_checks(attempt)
        if isinstance(produced, tuple) and len(produced) == 2:
            extra_checks, verifier_evidence = produced
            checks.extend(extra_checks or [])
        else:
            checks.extend(produced or [])

    passed = all(c.ok for c in checks)

    verdict = VerificationVerdict(
        attempt_id=getattr(attempt, "attempt_id", ""),
        task_id=getattr(attempt, "task_id", ""),
        classification=ATTEMPT_PROOF,
        verifier_identity=verifier_identity,
        verifier_role_id=verifier_role_id,
        passed=passed,
        checks=[c.to_dict() for c in checks],
    )

    # Persist an AttemptProof through the canonical Proof authority ONLY when the
    # verifier passed — a failed verification produces no success proof.
    if passed and proof_runtime is not None:
        verdict.proof_id = _persist_proof(
            proof_runtime,
            work_id=verdict.task_id,
            classification=ATTEMPT_PROOF,
            checks=verdict.checks,
            verifier_identity=verifier_identity,
            worker_result=worker_result,
            # Bind the Proof to EXACTLY this attempt (order R2): a Proof must
            # identify its tenant, plan version, task, attempt, assignment,
            # verifier and package hash so it can never be credited to another.
            lineage={
                "tenant_id": getattr(attempt, "tenant_id", ""),
                "plan_record_id": getattr(attempt, "plan_record_id", ""),
                "plan_version": getattr(attempt, "plan_version", 0),
                "task_id": getattr(attempt, "task_id", ""),
                "attempt_id": getattr(attempt, "attempt_id", ""),
                "attempt_number": getattr(attempt, "attempt_number", 0),
                "assignment_id": getattr(attempt, "assignment_id", ""),
                "lease_id": getattr(attempt, "lease_id", ""),
                "verifier_role_id": verifier_role_id,
                "worker_identity": worker_identity,
                "package_hash": package_hash,
            },
            # The confined verifier's structured evidence is persisted INSIDE this
            # exact AttemptProof as one typed ProofEvidence (C-4a) — durable,
            # restart-safe, digest-bound. No process-local field is the authority.
            verifier_evidence=verifier_evidence,
        )
    return verdict


def verify_plan_execution(
    *,
    plan_record_id: str,
    integration_task_id: str,
    verifier_identity: str,
    verifier_role_id: str,
    reconvergence_checks: Callable[[], list[VerificationCheck]],
    proof_runtime: Any | None = None,
) -> VerificationVerdict:
    """Produce the final PlanExecutionProof from the independent verification Task.

    Validates reconvergence, complete tests, live behavior, source integrity, and
    zero production deployment (checks supplied by the caller/field harness)."""
    checks = list(reconvergence_checks())
    passed = all(c.ok for c in checks)
    verdict = VerificationVerdict(
        attempt_id="",
        task_id=integration_task_id,
        classification=PLAN_EXECUTION_PROOF,
        verifier_identity=verifier_identity,
        verifier_role_id=verifier_role_id,
        passed=passed,
        checks=[c.to_dict() for c in checks],
    )
    if passed and proof_runtime is not None:
        verdict.proof_id = _persist_proof(
            proof_runtime,
            work_id=plan_record_id,
            classification=PLAN_EXECUTION_PROOF,
            checks=verdict.checks,
            verifier_identity=verifier_identity,
            worker_result=None,
        )
    return verdict


class ProofDurabilityError(RuntimeError):
    """A Proof could not be minted durably, so no transition may rely on it."""


def _actual_changed_paths(lease: Any, worker_result: Any) -> tuple[list[str], str, bool]:
    """Changed paths derived INDEPENDENTLY from the lease worktree.

    Returns ``(paths, source_label, independent)``. ``independent`` is the
    load-bearing value: when the worktree cannot be inspected the worker's
    self-report is returned for DIAGNOSTICS only, flagged False, and the caller
    must reject. Returning a label alone was not enough — a caller could (and the
    C-1 code effectively did) ignore it and pass anyway.

    The diff covers BOTH committed and uncommitted changes: ``git diff <base>``
    alone misses untracked files, so a worker could write a new file outside its
    scope and leave no trace in the verdict.
    """
    worktree = str(getattr(lease, "worktree_path", "") or "")
    # The authorized BASE must be the lease's recorded snapshot. There is no
    # "HEAD" fallback: after a worker commits — which real workers do — HEAD IS
    # the worker's own commit, so `git diff HEAD` returns EXACTLY nothing. An
    # out-of-scope committed change would then read as a clean, "independent"
    # empty diff and pass containment. That is a deterministic false green, not
    # an edge case. A lease with no snapshot_ref cannot anchor a diff at all, so
    # it fails closed.
    base = str(getattr(lease, "snapshot_ref", "") or "").strip()
    if not base:
        return [], "missing lease snapshot_ref (no authorized base to diff against)", False
    if worktree and os.path.isdir(worktree):
        try:
            from substrate.execution.cpu_gate import gated_subprocess_run

            paths: set[str] = set()
            tracked = gated_subprocess_run(
                ["git", "diff", "--name-only", base],
                caller="wave2_verify_diff_scope",
                timeout=60,
                cwd=worktree,
            )
            if tracked is None or tracked.returncode != 0:
                return [], "git diff unavailable", False
            paths.update(ln.strip() for ln in (tracked.stdout or "").splitlines() if ln.strip())
            # Untracked files are real changes and must count against scope.
            untracked = gated_subprocess_run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                caller="wave2_verify_diff_scope_untracked",
                timeout=60,
                cwd=worktree,
            )
            if untracked is not None and untracked.returncode == 0:
                paths.update(
                    ln.strip() for ln in (untracked.stdout or "").splitlines() if ln.strip()
                )
            # THE COMMIT RANGE. `git diff <base>` compares the WORKING TREE to the
            # base, so it sees only what is on disk. The write barrier makes
            # out-of-scope files unwritable on disk — but `.git/objects` and
            # `.git/index` MUST be writable for `git add` to work at all, and
            # `git hash-object -w` + `git update-index --cacheinfo` write a tree
            # entry for ANY path without ever touching the file. The mount never
            # fires, so the barrier holds and the change is still committed.
            #
            # Reproduced against the shipped launcher: with scope ['app/main.py'],
            # a worker committed `OBJECTIVE.md` and `secret/key.txt` as "SMUGGLED"
            # while the worktree copies stayed byte-identical; the worktree diff
            # reported exactly ['app/main.py'] and the attempt PASSED containment.
            # The barrier was reachable but bypassable, which is worse than
            # unreachable: it looks enforced.
            #
            # The committed range is therefore part of the verdict, not a
            # diagnostic. A path is out of scope whether it reached the commit
            # through the filesystem or through the index.
            committed = gated_subprocess_run(
                ["git", "diff", "--name-only", f"{base}..HEAD"],
                caller="wave2_verify_diff_scope_committed",
                timeout=60,
                cwd=worktree,
            )
            if committed is None or committed.returncode != 0:
                # Fail closed: an uninspectable commit range is not an empty one.
                return [], "git commit-range diff unavailable", False
            paths.update(ln.strip() for ln in (committed.stdout or "").splitlines() if ln.strip())
            return sorted(paths), "git worktree diff + commit range + untracked (independent)", True
        except Exception as exc:  # noqa: BLE001 - diagnostics only
            logger.debug("independent diff failed for %s: %s", worktree, exc)
    reported = [str(p) for p in (getattr(worker_result, "files_changed", []) or [])]
    return reported, "worker self-report (worktree not inspectable)", False


def _base_is_ancestor_of_head(lease: Any) -> tuple[bool, str]:
    """Is the lease's authorized base still reachable from HEAD?

    The worker owns its own attempt ref (that is what makes committing possible
    at all), so it can move that ref anywhere — including BELOW the authorized
    base. `reset --soft` and `commit --amend` both do this, and neither touches
    a protected file, so the write barrier is silent and the scope diff still
    reads clean.

    Checking ancestry converts "system writes are an ancestor of the worker's
    base" from a comment into an enforced property. Fails closed: an ancestry
    question that cannot be answered is not an answer of yes.
    """
    worktree = str(getattr(lease, "worktree_path", "") or "")
    base = str(getattr(lease, "snapshot_ref", "") or "").strip()
    if not base:
        return False, "lease has no snapshot_ref"
    if not worktree or not os.path.isdir(worktree):
        return False, f"lease worktree not inspectable: {worktree!r}"
    try:
        from substrate.execution.cpu_gate import gated_subprocess_run

        result = gated_subprocess_run(
            ["git", "merge-base", "--is-ancestor", base, "HEAD"],
            caller="wave2_verify_base_ancestry",
            timeout=60,
            cwd=worktree,
        )
    except Exception as exc:  # noqa: BLE001 - an unanswerable check fails closed
        return False, f"ancestry check failed: {exc}"
    if result is None:
        return False, "ancestry check refused by CPU gate"
    if result.returncode == 0:
        return True, f"base {base[:12]} is an ancestor of HEAD"
    return False, (
        f"base {base[:12]} is NOT an ancestor of HEAD (rc={result.returncode}) — "
        "the attempt's history is not the one that was authorized"
    )


def reanchor_is_authorized(*, worktree: str, original_base: str, new_base: str) -> tuple[bool, str]:
    """May the attempt's diff base move from ``original_base`` to ``new_base``?

    Moving a diff base FORWARD monotonically shrinks the observed change set, so
    an unvalidated re-anchor is a scope-check bypass, not a bookkeeping detail.
    Anchoring at the worker's own HEAD yields ``changed=0`` and PASSES with
    out-of-scope files sitting in the tree — reproduced directly against this
    module: with scope ``['app/']`` and a smuggled ``secret/key.txt``, base C0
    rejected, the trusted base C1 correctly rejected (catching the smuggle), and
    a forward base at the worker's commit returned ``changed=0 outside=[]``.

    ``_base_is_ancestor_of_head`` does NOT constrain this. It asks only whether
    the base is reachable from HEAD, which every commit on the branch satisfies —
    including the worker's own. It guards the base moving OFF the branch
    (``reset --soft``), never the base moving forward along it.

    So the re-anchor is authorized only when all three hold:

    1. ``new_base`` resolves to a real commit named by its FULL SHA (a branch
       name like ``main`` resolves and is an ancestor of HEAD, and a ref can be
       moved after the fact);
    2. ``original_base`` is an ancestor of ``new_base`` — the base may only move
       FORWARD from the authorized one, never sideways onto another history;
    3. the commits being skipped touch ONLY ``TRUSTED_PROJECTION_PATHS``. This is
       the load-bearing one: it bounds what the re-anchor may hide to exactly the
       system writes the trusted phase is permitted to make. Any worker-authored
       path in that range means the re-anchor would erase a change the scope
       check exists to see.

    Fails CLOSED — an unanswerable question is never an answer of yes. The caller
    keeps the original base on refusal, which is a scope rejection (the pre-fix
    behaviour), never a pass.
    """
    from substrate.execution.attempts.scope_contract import TRUSTED_PROJECTION_PATHS

    original_base = (original_base or "").strip()
    new_base = (new_base or "").strip()
    if not new_base:
        return False, "no trusted_base supplied"
    if not original_base:
        return False, "lease has no original snapshot_ref to move from"
    if new_base == original_base:
        return True, "base unchanged"
    if not worktree or not os.path.isdir(worktree):
        return False, f"lease worktree not inspectable: {worktree!r}"

    try:
        from substrate.execution.cpu_gate import gated_subprocess_run

        def _git(args: list[str]):
            return gated_subprocess_run(
                ["git", *args],
                caller="wave2_verify_reanchor_authorized",
                timeout=60,
                cwd=worktree,
            )

        # (1) a real commit, named by its full SHA — never a movable ref.
        resolved = _git(["rev-parse", "--verify", f"{new_base}^{{commit}}"])
        if resolved is None:
            return False, "re-anchor check refused by CPU gate"
        if resolved.returncode != 0:
            return False, f"trusted_base {new_base[:12]} does not resolve to a commit"
        resolved_sha = (resolved.stdout or "").strip()
        if resolved_sha != new_base:
            return False, (
                f"trusted_base {new_base!r} is not a full commit SHA (resolves to "
                f"{resolved_sha[:12]}) — a movable ref may not anchor a scope diff"
            )

        # (2) forward-only along the authorized history.
        fwd = _git(["merge-base", "--is-ancestor", original_base, new_base])
        if fwd is None:
            return False, "re-anchor ancestry check refused by CPU gate"
        if fwd.returncode != 0:
            return False, (
                f"original base {original_base[:12]} is NOT an ancestor of "
                f"trusted_base {new_base[:12]} — the re-anchor leaves the "
                f"authorized history"
            )

        # (3) the skipped range contains ONLY trusted system writes.
        skipped = _git(["diff", "--name-only", f"{original_base}..{new_base}"])
        if skipped is None:
            return False, "re-anchor range diff refused by CPU gate"
        if skipped.returncode != 0:
            return False, "re-anchor range diff unavailable — refusing to move the base"
        changed = [ln.strip() for ln in (skipped.stdout or "").splitlines() if ln.strip()]
        outside = [p for p in changed if p not in TRUSTED_PROJECTION_PATHS]
        if outside:
            return False, (
                f"re-anchor would skip non-trusted paths {sorted(outside)[:5]} — only "
                f"{sorted(TRUSTED_PROJECTION_PATHS)} may be moved past the worker's base"
            )
    except Exception as exc:  # noqa: BLE001 - an unanswerable check fails closed
        return False, f"re-anchor authorization failed: {exc}"

    return True, (
        f"re-anchor {original_base[:12]}..{new_base[:12]} authorized "
        f"({len(changed)} trusted path(s))"
    )


def _diff_scope_verdict(
    *, lease: Any, packet: Any, worker_result: Any, semantic_label: str = ""
) -> tuple[bool, str]:
    """Fail-closed diff-scope verdict for one attempt (finding C-1).

    The authority is the Task's DECLARED allowed paths — canonical WorkPacket
    requirements — normalized relative to the lease root. The lease worktree is
    NOT the authority: it is the containment boundary, and using it as the scope
    is precisely what made this check unable to fail.

    Every failure mode is a REJECTION:

    - no packet / no declared scope → cannot verify containment → fail;
    - an unsafe policy (``.``, absolute, parent traversal) → fail;
    - the diff cannot be computed independently → fail (a verdict must never
      rest on the worker's self-report while claiming to be independent);
    - any changed path outside the allowlist → fail.
    """
    from substrate.execution.attempts.field_task_scope import (
        ScopeResolutionError,
        allowed_paths_for,
        normalize_allowed_paths,
        paths_outside,
    )

    worktree_path = str(getattr(lease, "worktree_path", "") or "")

    if packet is None:
        return False, (
            "no canonical WorkPacket supplied — the authorized path scope cannot be "
            "resolved, so containment is unverifiable (refusing to pass)"
        )
    try:
        declared = allowed_paths_for(packet, semantic_label=semantic_label)
        allowed = normalize_allowed_paths(declared, lease_root=worktree_path)
    except ScopeResolutionError as exc:
        return False, f"unusable path scope: {exc}"

    changed_paths, diff_source, independent = _actual_changed_paths(lease, worker_result)
    logger.debug(
        "diff_scope: paths=%s source=%r independent=%s lease_wt=%r",
        changed_paths[:10],
        diff_source,
        independent,
        str(getattr(lease, "worktree_path", "")),
    )
    if not independent:
        return False, (
            f"changed paths could not be computed independently ({diff_source}) — "
            f"a diff-scope verdict may not rest on the worker's own report"
        )

    # THE AUTHORIZED BASE MUST STILL BE AN ANCESTOR OF HEAD.
    #
    # The authorized base anchors everything the diff verdict attributes to the
    # worker. That invariant was ASSERTED but never CHECKED — and the worker
    # owns its own ref, so `git reset --soft HEAD~1` or `git commit --amend`
    # moves its history below the base entirely. The worker then re-commits any
    # path with content of its choosing while the scope verdict still reads
    # clean. (Since invocation 41 the base is the CANONICAL governed base — the
    # projection is execution context, never a commit — but the detach vector is
    # base-independent.)
    #
    # An unchecked invariant is not an invariant. This makes it load-bearing:
    # if the base is no longer reachable from HEAD, the attempt's history is not
    # the one that was authorized, whatever its diff happens to say.
    #
    # ORDERED AFTER the independence check on purpose. Both refuse the same
    # cases, but a missing snapshot_ref / uninspectable worktree is FIRST a
    # "cannot observe" problem, and reporting it as "not an ancestor" tells the
    # operator to look at git history when the real fault is the lease. The
    # diagnostic is part of the contract: whoever reads this verdict has to be
    # able to act on it.
    ancestry_ok, ancestry_detail = _base_is_ancestor_of_head(lease)
    if not ancestry_ok:
        return False, f"authorized base is not an ancestor of HEAD: {ancestry_detail}"

    outside = paths_outside(changed_paths, allowed)
    detail = (
        f"changed={len(changed_paths)} allowed={sorted(allowed)} "
        f"outside={sorted(outside)[:5]} ({diff_source})"
    )
    if outside:
        return False, f"changes outside authorized scope: {detail}"
    return True, detail


def _persist_proof(
    proof_runtime: Any,
    *,
    work_id: str,
    classification: str,
    checks: list[dict[str, Any]],
    verifier_identity: str,
    worker_result: Any,
    lineage: dict[str, Any] | None = None,
    verifier_evidence: Any = None,
) -> str:
    """Persist a ProofPackage (the ONE canonical Proof authority) tagged with the
    classification. Returns the proof_id.

    ``lineage`` binds the Proof to exactly what it proves — tenant, plan record +
    version, task, attempt, assignment, verifier role and package hash — so a
    Proof cannot be mistaken for one belonging to a different attempt.
    """
    from substrate.organism.proof_runtime import ProofEvidence

    evidence = [
        ProofEvidence(
            evidence_type=f"verification_check:{c.get('kind', '')}",
            description=c.get("detail", ""),
            data=c,
        )
        for c in checks
    ]
    if worker_result is not None:
        evidence.append(
            ProofEvidence(
                evidence_type="worker_artifacts",
                description="git artifacts produced by the implementation worker",
                data={
                    "files_changed": list(getattr(worker_result, "files_changed", []) or []),
                    "commits": list(getattr(worker_result, "commits", []) or []),
                },
            )
        )
    # EXACTLY-ONE confined-verifier evidence record (C-4a): the structured
    # VerifierEvidence is persisted inside THIS Proof as one typed entry, so a
    # reread from disk reconstructs the full binding (lease id, attempt/task/
    # assignment, verifier/worker identity, package hash, base + verified commits,
    # isolation results, timestamps, trusted process identity, digest) without any
    # process-local field.
    if verifier_evidence is not None:
        from substrate.execution.attempts.verifier_isolation import VERIFIER_EVIDENCE_TYPE

        evidence.append(
            ProofEvidence(
                evidence_type=VERIFIER_EVIDENCE_TYPE,
                description="confined verifier run (bwrap; source read-only; net unshared)",
                data=verifier_evidence.to_dict(),
            )
        )
    # DURABLE persistence through the canonical ProofRuntime seam (finding C1).
    #
    # The previous code looked for `store_package`/`persist` — neither of which
    # ProofRuntime exposes — and silently fell back to poking its private
    # in-memory `_packages` dict. Nothing ever reached disk, so every SUCCEEDED
    # attempt carried a proof_id that referenced an object which died with the
    # process. `create_direct` is the real durable entry point: it appends to
    # <runtime-state>/organism/proof_packages.jsonl under an exclusive lock and
    # raises ProofPersistenceError if the write fails.
    #
    # No fallback: if the Proof cannot be persisted the attempt must NOT become
    # SUCCEEDED, so the error propagates to the caller.
    creator = getattr(proof_runtime, "create_direct", None)
    if not callable(creator):
        raise ProofDurabilityError(
            f"proof runtime {type(proof_runtime).__name__} exposes no durable "
            f"create_direct() — refusing to mint a non-durable Proof"
        )
    package = creator(
        work_id=work_id,
        action={
            "classification": classification,
            "verifier_identity": verifier_identity,
            # Full lineage binding: a Proof must identify exactly what it proves.
            **{k: v for k, v in (lineage or {}).items() if v not in (None, "")},
        },
        outcome=f"{classification}:passed",
        operator=verifier_identity,
    )
    # Attach the verification evidence to the persisted package and re-persist so
    # the durable record carries the checks, not just the verdict header.
    try:
        package.evidence.extend(evidence)
        proof_runtime._persist_package(package)  # noqa: SLF001 - canonical seam
    except Exception as exc:  # persistence is load-bearing — never swallow
        raise ProofDurabilityError(
            f"proof {package.proof_id} evidence could not be persisted: {exc}"
        ) from exc
    return package.proof_id


__all__ = [
    "ATTEMPT_PROOF",
    "PLAN_EXECUTION_PROOF",
    "VerificationCheck",
    "VerificationVerdict",
    "verify_attempt",
    "verify_plan_execution",
]
