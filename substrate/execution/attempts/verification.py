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

    # 2. real artifacts exist (a diff + at least one commit). The worker's
    #    narrative is NOT trusted; we require concrete git evidence.
    files = list(getattr(worker_result, "files_changed", []) or [])
    commits = list(getattr(worker_result, "commits", []) or [])
    checks.append(
        VerificationCheck(
            check_id="artifacts",
            kind="artifact",
            ok=bool(files) and bool(commits),
            detail=f"files={len(files)} commits={len(commits)}",
        )
    )

    # 3. diff-scope: changes confined to allowed paths, computed from the ACTUAL
    #    changed paths in the lease worktree — never hardcoded (finding C4).
    #
    #    This check used to be `ok=True` unconditionally, so a worker writing
    #    outside its allowed paths passed verification. The changed set is
    #    derived by diffing the worktree against its base commit; the worker's
    #    self-reported file list is NOT trusted for this.
    worktree_path = str(getattr(lease, "worktree_path", "") or "")
    raw_allowed = [p for p in (getattr(lease, "writable_paths", []) or []) if p]
    # The LeaseManager records writable_paths=[<absolute worktree>] to mean "the
    # whole worktree is writable". Git reports changed paths RELATIVE to the
    # worktree, so comparing the two directly can never match. Normalize: an
    # entry equal to the worktree root means whole-worktree scope; any other
    # entry is treated as a worktree-relative prefix.
    allowed = [
        os.path.relpath(p, worktree_path) if (worktree_path and os.path.isabs(p)) else p
        for p in raw_allowed
    ]
    whole_worktree = any(a in (".", "") for a in allowed)
    allowed = [a for a in allowed if a not in (".", "")]

    changed_paths, diff_source = _actual_changed_paths(lease, worker_result)
    outside = _paths_outside_allowlist(changed_paths, allowed)
    if whole_worktree:
        # Whole-worktree scope: the sandbox mount IS the boundary and it is
        # enforced by construction (the worker cannot write outside its bind).
        scope_ok = True
        scope_detail = f"whole-worktree scope; sandbox-enforced ({diff_source})"
    elif not allowed:
        # No declared allowlist: the lease worktree itself is the boundary, which
        # the sandbox already enforces. Record that honestly rather than implying
        # a path check ran.
        scope_ok = True
        scope_detail = f"no writable_paths declared; worktree-confined ({diff_source})"
    else:
        scope_ok = not outside
        scope_detail = (
            f"changed={len(changed_paths)} allowed={sorted(allowed)} "
            f"outside={sorted(outside)[:5]} ({diff_source})"
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
    if independent_checks is not None:
        checks.extend(independent_checks(attempt))

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


def _actual_changed_paths(lease: Any, worker_result: Any) -> tuple[list[str], str]:
    """Changed paths derived INDEPENDENTLY from the lease worktree.

    Diffs the worktree against its base commit via git. Falls back to the
    worker's self-report ONLY when the worktree cannot be inspected, and says so
    in the returned source label so a verdict can never silently rest on the
    worker's narrative while claiming an independent check.
    """
    worktree = str(getattr(lease, "worktree_path", "") or "")
    base = str(getattr(lease, "snapshot_ref", "") or "") or "HEAD"
    if worktree and os.path.isdir(worktree):
        try:
            from substrate.execution.cpu_gate import gated_subprocess_run

            result = gated_subprocess_run(
                ["git", "diff", "--name-only", base],
                caller="wave2_verify_diff_scope",
                timeout=60,
                cwd=worktree,
            )
            if result is not None and result.returncode == 0:
                paths = [ln.strip() for ln in (result.stdout or "").splitlines() if ln.strip()]
                return paths, "git diff (independent)"
        except Exception as exc:  # noqa: BLE001 - diagnostics only
            logger.debug("independent diff failed for %s: %s", worktree, exc)
    reported = [str(p) for p in (getattr(worker_result, "files_changed", []) or [])]
    return reported, "worker self-report (worktree not inspectable)"


def _paths_outside_allowlist(changed: list[str], allowed: list[str]) -> list[str]:
    """Changed paths not under any allowed prefix."""
    outside: list[str] = []
    for path in changed:
        normalized = path.lstrip("./")
        if not any(
            normalized == a.rstrip("/") or normalized.startswith(a.rstrip("/") + "/")
            for a in allowed
        ):
            outside.append(path)
    return outside


def _persist_proof(
    proof_runtime: Any,
    *,
    work_id: str,
    classification: str,
    checks: list[dict[str, Any]],
    verifier_identity: str,
    worker_result: Any,
    lineage: dict[str, Any] | None = None,
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
