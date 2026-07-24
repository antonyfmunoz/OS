"""Confined independent verifier (C-4) — one canonical verifier-isolation authority.

Every verification check that executes code from the worker-controlled integration
tree (pytest, ``conftest.py``, worker-authored test modules, scripts, imports,
binaries) MUST run through this seam. No verifier may execute worker-authored code
directly in the runner host environment.

The defect this closes: ``field_control_plane._independent_checks_for`` ran
``python3 -m pytest`` with ``cwd=<lease worktree>`` via ``gated_subprocess_run`` —
no bwrap, no env scrub, the full host env including ``CLAUDE_CODE_OAUTH_TOKEN``. A
worktree ``conftest.py`` is arbitrary Python that pytest imports and executes, so
the verifier ran untrusted worker code unconfined moments after the worker runner
itself refused to start without bwrap.

The seam (``run_confined_verifier_checks``):

- mints a DISTINCT verifier lease + identity/role for the run (never the worker
  lease/identity/home/credential);
- runs worker-authored code ONLY inside bubblewrap — bwrap absent / launch failure
  / preflight unproven all FAIL CLOSED, never an unconfined fallback;
- exposes the integration source READ-ONLY, a credential-free private HOME, and a
  private TMPDIR — /opt/OS, /root/.claude, worker homes, the dispatch secret file,
  and candidate state are simply not in the namespace;
- unshares the network for worker-authored code;
- strips every credential (OAuth token, dispatch secret, API keys, mesh/Fly/GitHub/
  1Password, worker CLAUDE_CONFIG_DIR) from the subprocess env;
- proves ZERO source mutation with a PARENT-SIDE pre/post integrity check
  (rev-parse + status --porcelain + file hashes) — never trusts the subprocess to
  self-report it changed nothing;
- persists hashed, name-only evidence bound to the AttemptProof lineage;
- destroys the verifier lease/home/tmp on EVERY terminal path (pass, failure,
  timeout, cancellation, exception, teardown); cleanup failure is a BLOCKING
  security failure, never a warning.

``verify_attempt`` (verification.py) CONSUMES the resulting
``VerificationCheck`` list; it never invokes worker-tree callbacks on the host.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from substrate.execution.attempts.host_isolation import (
    IsolationUnavailable,
    VerifierIsolationProfile,
    build_isolated_verifier_command,
    isolation_primitive,
    preflight_isolation,
    scrub_verifier_env,
)
from substrate.execution.attempts.worker_credential_boundary import (
    AttemptHome,
    CredentialBoundaryError,
    close_attempt_credential_home,
    open_verifier_home,
)

logger = logging.getLogger(__name__)


class VerifierIsolationError(RuntimeError):
    """Verification could not be run confined. Always fail closed."""


@dataclass
class VerifierLease:
    """The distinct verifier lease for one verification run.

    Never the implementation worker lease. Carries its own identity/role, the
    exact commit being verified, and the private HOME/XDG/TMP the confined
    subprocess uses. ``home`` holds NO credential.
    """

    verifier_lease_id: str
    attempt_id: str
    task_id: str
    verifier_identity: str
    verifier_role_id: str
    source_commit: str
    home: AttemptHome
    source_ro_path: str
    created_at: float = field(default_factory=time.time)
    closed: bool = False

    def env_overrides(self) -> dict[str, str]:
        """HOME/XDG/TMPDIR pointing ONLY at verifier-private directories."""
        return self.home.env_overrides()

    def to_dict(self) -> dict[str, Any]:
        return {
            "verifier_lease_id": self.verifier_lease_id,
            "attempt_id": self.attempt_id,
            "task_id": self.task_id,
            "verifier_identity": self.verifier_identity,
            "verifier_role_id": self.verifier_role_id,
            "source_commit": self.source_commit,
            "home_path": self.home.home_path,
            "tmp_path": self.home.tmp_path,
            "source_ro_path": self.source_ro_path,
            "closed": self.closed,
        }


@dataclass
class VerifierEvidence:
    """Parent-side, hashed, name-only evidence for one confined verification.

    Bound to the AttemptProof lineage by the caller. Contains NO secret values —
    env is names only, the bwrap argv is redaction-safe (no secret ever transits
    it), and file hashes prove integrity without exposing content.
    """

    verifier_lease: dict[str, Any]
    verified_commit: str
    bwrap_argv: list[str]
    env_var_names: list[str]
    mount_policy: dict[str, Any]
    isolation_probe: dict[str, Any]
    source_hashes_before: dict[str, str]
    source_hashes_after: dict[str, str]
    zero_diff: bool
    tests_ok: bool
    tests_detail: str
    started_at: float
    ended_at: float
    verifier_pid: int = 0
    evidence_sha256: str = ""

    def finalize(self) -> "VerifierEvidence":
        self.evidence_sha256 = _hash_json(
            {
                "verifier_lease": self.verifier_lease,
                "verified_commit": self.verified_commit,
                "bwrap_argv": self.bwrap_argv,
                "env_var_names": sorted(self.env_var_names),
                "mount_policy": self.mount_policy,
                "isolation_probe": self.isolation_probe,
                "source_hashes_before": self.source_hashes_before,
                "source_hashes_after": self.source_hashes_after,
                "zero_diff": self.zero_diff,
                "tests_ok": self.tests_ok,
                "tests_detail": self.tests_detail,
            }
        )
        return self

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _hash_json(obj: Any) -> str:
    import json

    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return "unreadable"
    return h.hexdigest()


def _source_tree_hashes(source: str) -> dict[str, str]:
    """SHA-256 of every tracked+untracked source file (parent-side integrity).

    Order-independent map ``relpath -> sha256``. Excludes ``.git`` internals (the
    verifier never touches them and their churn is not a source mutation).
    """
    hashes: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(source):
        if ".git" in dirnames:
            dirnames.remove(".git")
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, source)
            hashes[rel] = _hash_file(full)
    return hashes


def _git(source: str, args: list[str]) -> tuple[int, str]:
    """Run a git command in ``source`` via the gated subprocess. (int rc, stdout)."""
    from substrate.execution.cpu_gate import gated_subprocess_run

    result = gated_subprocess_run(
        ["git", *args],
        caller="wave2_verifier_source_integrity",
        timeout=60,
        cwd=source,
    )
    if result is None:
        return 1, ""
    return result.returncode, (result.stdout or "")


# ── lifecycle ────────────────────────────────────────────────────────────────
def open_verifier_lease(
    *,
    attempt_id: str,
    task_id: str,
    run_root: str,
    source_ro_path: str,
    verifier_role_id: str,
    worker_identity: str,
    source_commit: str = "",
) -> VerifierLease:
    """Create the distinct verifier lease + credential-free private home.

    Fails closed if the verifier identity would collide with the worker (an agent
    can never verify its own work), or if the private home cannot be created.
    """
    if not attempt_id:
        raise VerifierIsolationError("attempt_id is required for a verifier lease")
    if not source_ro_path or not os.path.isdir(source_ro_path):
        raise VerifierIsolationError(
            f"verifier source path {source_ro_path!r} is not a directory — refusing"
        )
    verifier_identity = f"verifier:{verifier_role_id}:{attempt_id}"
    if worker_identity and verifier_identity == worker_identity:
        raise VerifierIsolationError(
            f"verifier identity {verifier_identity!r} collides with worker "
            f"{worker_identity!r} — separation of duty violated"
        )
    home = open_verifier_home(attempt_id=attempt_id, run_root=run_root)
    return VerifierLease(
        verifier_lease_id=f"vlease-{uuid.uuid4().hex[:12]}",
        attempt_id=attempt_id,
        task_id=task_id,
        verifier_identity=verifier_identity,
        verifier_role_id=verifier_role_id,
        source_commit=source_commit,
        home=home,
        source_ro_path=os.path.realpath(source_ro_path),
    )


def close_verifier_lease(lease: VerifierLease | None) -> None:
    """Destroy the verifier private home/tmp. Cleanup failure is a SECURITY failure.

    Reuses ``close_attempt_credential_home`` (idempotent, raises on residue). Safe
    on every terminal path.
    """
    if lease is None or lease.closed:
        return
    close_attempt_credential_home(lease.home)  # raises CredentialBoundaryError on residue
    lease.closed = True


# ── the one confined verification entry point ─────────────────────────────────
def run_confined_verifier_checks(
    *,
    attempt: Any,
    run_root: str,
    source_path: str,
    verifier_role_id: str,
    worker_identity: str,
    source_commit: str = "",
    test_argv: list[str] | None = None,
    timeout_s: int = 300,
) -> tuple[list[Any], VerifierEvidence]:
    """Run the verifier's worker-code checks CONFINED, returning (checks, evidence).

    ``checks`` are ``VerificationCheck`` objects ``verify_attempt`` consumes. The
    integration ``source_path`` is mounted READ-ONLY inside bwrap; pytest (which
    imports the worker's ``conftest.py``) runs with the network unshared, a
    credential-free HOME, and a scrubbed env. Parent-side pre/post hashes + git
    status prove zero source mutation. Every terminal path destroys the lease.

    FAIL CLOSED: bwrap absent, launch failure, preflight unproven, or a
    verifier-produced source diff each yields a FAILED check (never an unconfined
    run and never a self-reported clean).
    """
    from substrate.execution.attempts.verification import VerificationCheck

    started = time.time()
    lease: VerifierLease | None = None
    checks: list[Any] = []

    # 1. bwrap must be present. No fallback to a coarser primitive or host subprocess.
    prim = isolation_primitive()
    if prim != "bwrap":
        checks.append(
            VerificationCheck(
                check_id="verifier_isolation",
                kind="policy",
                ok=False,
                detail=f"bwrap unavailable (primitive={prim!r}) — refusing to verify unconfined",
            )
        )
        return checks, _fail_evidence(source_commit, started, f"no bwrap (prim={prim})")

    # 2. preflight: prove the sandbox genuinely hides a forbidden path.
    probe_ok, probe_detail = preflight_isolation("/opt/OS")
    if not probe_ok:
        checks.append(
            VerificationCheck(
                check_id="verifier_isolation",
                kind="policy",
                ok=False,
                detail=f"isolation preflight not proven: {probe_detail}",
            )
        )
        return checks, _fail_evidence(source_commit, started, f"preflight failed: {probe_detail}")

    try:
        lease = open_verifier_lease(
            attempt_id=getattr(attempt, "attempt_id", "") or "",
            task_id=getattr(attempt, "task_id", "") or "",
            run_root=run_root,
            source_ro_path=source_path,
            verifier_role_id=verifier_role_id,
            worker_identity=worker_identity,
            source_commit=source_commit,
        )

        source = lease.source_ro_path
        # 3. PARENT-SIDE integrity snapshot BEFORE running worker code.
        before_hashes = _source_tree_hashes(source)
        rc_head_before, head_before = _git(source, ["rev-parse", "HEAD"])
        head_before = head_before.strip()

        # 4. build the confined command. pytest imports the worker's conftest.py,
        #    so it runs INSIDE bwrap with network unshared + scrubbed env. The
        #    subprocess wall-clock is bounded by ``timeout_s`` below, so the default
        #    argv does NOT depend on the pytest-timeout plugin (a fixture that
        #    lacks it would otherwise error rc=4 — a false verification failure).
        inner = test_argv or ["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        profile = VerifierIsolationProfile(
            source_ro_path=source,
            verifier_home=lease.home.home_path,
            tmp_path=lease.home.tmp_path,
            allow_network=False,  # worker-authored code gets NO network
            env_overrides=lease.env_overrides(),
        )
        argv = build_isolated_verifier_command(inner, profile)
        scrubbed_env = scrub_verifier_env(dict(os.environ))
        # HOME/XDG/TMPDIR come from the profile (bwrap --setenv); pass them in the
        # subprocess env too so any pre-exec lookup is already private.
        scrubbed_env.update(lease.env_overrides())

        from substrate.execution.cpu_gate import gated_subprocess_run

        result = gated_subprocess_run(
            argv,
            caller="wave2_confined_verifier_tests",
            timeout=timeout_s,
            env=scrubbed_env,
        )

        # 5. PARENT-SIDE integrity check AFTER — never trust the subprocess.
        after_hashes = _source_tree_hashes(source)
        rc_head_after, head_after = _git(source, ["rev-parse", "HEAD"])
        head_after = head_after.strip()
        rc_status, status_out = _git(source, ["status", "--porcelain"])
        dirty = bool(status_out.strip())
        hashes_changed = before_hashes != after_hashes
        head_moved = head_before != head_after
        zero_diff = not dirty and not hashes_changed and not head_moved

        if result is None:
            tests_ok = False
            tests_detail = "verifier test run skipped by CPU gate — cannot confirm"
        else:
            tests_ok = result.returncode == 0
            tests_detail = f"pytest rc={result.returncode} (confined, net-unshared)"
        verifier_pid = 0  # gated_subprocess_run does not surface the child pid

        # The zero-diff verdict is ITS OWN check — a verifier that mutated the
        # source fails verification even if the tests "passed".
        checks.append(
            VerificationCheck(
                check_id="verifier_zero_diff",
                kind="policy",
                ok=zero_diff,
                detail=(
                    "source unchanged (hashes + HEAD + status all clean)"
                    if zero_diff
                    else f"SOURCE MUTATED: dirty={dirty} hashes_changed={hashes_changed} "
                    f"head_moved={head_moved}"
                ),
            )
        )
        checks.append(
            VerificationCheck(
                check_id="independent_tests",
                kind="tests",
                ok=tests_ok and zero_diff,  # tests only count if the source is intact
                detail=tests_detail,
            )
        )

        evidence = VerifierEvidence(
            verifier_lease=lease.to_dict(),
            verified_commit=source_commit or head_before,
            bwrap_argv=argv,
            env_var_names=sorted(scrubbed_env.keys()),
            mount_policy={
                "source_ro": source,
                "writable": [lease.home.home_path, lease.home.tmp_path],
                "network": "unshared",
                "opt_os_bound": False,
                "root_claude_bound": False,
            },
            isolation_probe={"ok": probe_ok, "detail": probe_detail},
            source_hashes_before=before_hashes,
            source_hashes_after=after_hashes,
            zero_diff=zero_diff,
            tests_ok=tests_ok,
            tests_detail=tests_detail,
            started_at=started,
            ended_at=time.time(),
            verifier_pid=verifier_pid,
        ).finalize()
        return checks, evidence

    except (VerifierIsolationError, IsolationUnavailable) as exc:
        checks.append(
            VerificationCheck(
                check_id="verifier_isolation",
                kind="policy",
                ok=False,
                detail=f"confined verification unavailable: {exc}",
            )
        )
        return checks, _fail_evidence(source_commit, started, str(exc))
    finally:
        # Destroy the verifier lease on EVERY terminal path. A cleanup failure is a
        # BLOCKING security failure: surface it as a failed check AND re-raise so no
        # caller can treat a leaked verifier home as a pass.
        if lease is not None:
            try:
                close_verifier_lease(lease)
            except CredentialBoundaryError as exc:
                checks.append(
                    VerificationCheck(
                        check_id="verifier_cleanup",
                        kind="policy",
                        ok=False,
                        detail=f"SECURITY: verifier home not destroyed: {exc}",
                    )
                )
                raise VerifierIsolationError(
                    f"verifier cleanup failed (blocking security failure): {exc}"
                ) from exc


def _fail_evidence(source_commit: str, started: float, reason: str) -> VerifierEvidence:
    """Evidence for a verification that never ran confined (fail-closed record)."""
    return VerifierEvidence(
        verifier_lease={},
        verified_commit=source_commit,
        bwrap_argv=[],
        env_var_names=[],
        mount_policy={"reason": reason},
        isolation_probe={"ok": False, "detail": reason},
        source_hashes_before={},
        source_hashes_after={},
        zero_diff=False,
        tests_ok=False,
        tests_detail=reason,
        started_at=started,
        ended_at=time.time(),
    ).finalize()


__all__ = [
    "VerifierIsolationError",
    "VerifierLease",
    "VerifierEvidence",
    "open_verifier_lease",
    "close_verifier_lease",
    "run_confined_verifier_checks",
]
