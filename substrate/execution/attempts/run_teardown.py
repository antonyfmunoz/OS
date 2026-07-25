"""One run-level teardown authority + durable manifest + crash recovery (SEC-C1).

C-2's ``terminalize`` owns the end of ONE attempt. SEC-C1 is the RUN-level layer
the C-2 ledger deferred: the single authority that destroys everything a
qualification run created — worker homes, verifier homes, credential material,
run-scoped secrets, environment leases, fixture worktrees, unprocessed spool
envelopes, preview processes — and PROVES zero residue afterward.

Why this exists (the finding): the host attempt runner installed NO signal
handler, so ``stop_runner``'s SIGTERM killed it with the process's default
disposition — immediate termination, no unwinding. Any worker/verifier credential
home created under the run root survived on disk indefinitely, and dispatch
``teardown`` never referenced ``worker-homes``/``verifier-homes`` at all. The
operator's real OAuth credential outlived the run. ``assert_no_credential_residue``
existed, was exported, was tested — and was called from NOWHERE in production.

The four guarantees this module provides:

1. **One idempotent authority.** :func:`sweep_run` destroys every run resource and
   returns a typed :class:`RunSweepResult` whose ``.ok`` is False on ANY residue
   or unsafe-path refusal. A second call on an already-clean run is a verified
   no-op. Every exit path (normal / failure / exception / SIGINT / SIGTERM)
   converges here; the runner's signal handler triggers a ``finally`` that calls
   it — it does not maintain a second cleanup implementation. NOTE: runtime lease
   release is the POLLER's authority (it terminalizes each attempt and re-drives a
   revoke on a release fault); this sweep releases leases only as a CRASH BACKSTOP
   when an explicit ``lease_manager`` is supplied (e.g. :func:`recover_stale_runs`).

2. **Durable registration.** :func:`register_resource` appends each resource to
   ``<run_root>/run_manifest.jsonl`` the moment it is created, with the owning
   PID. A partially started run that then dies leaves enough manifest state to
   identify every home, lease, worktree, secret file, PID and serve mutation.

3. **Scope-safe deletion.** :func:`_safe_run_descendant` realpath-validates that a
   target is a true descendant of the exact run root before any ``rmtree``.
   Symlinks, ``..``, ``/``, empty paths and anything outside the run directory
   FAIL CLOSED — a cleanup bug can never delete outside the run's own tree. The
   run secret lives OUTSIDE the run root (host-only, by design) and is shredded
   through its own realpath+basename-pinned path, never a descendant walk.

4. **Crash recovery, honestly scoped.** :func:`recover_stale_runs` sweeps prior
   dead runs' residue at the next startup and REFUSES any run whose owner PID is
   still alive. This is next-start stale-resource recovery — NOT Wave-3 supervisor
   restoration, and NOT a claim that SIGKILL / kernel panic / power loss run
   in-process cleanup (they cannot; the honest guarantee is the next-start sweep).

Imports only downward (substrate + same-package).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import Any

from substrate.execution.attempts.worker_credential_boundary import (
    assert_no_credential_residue,
    assert_no_verifier_home_residue,
    verifier_homes_root,
    worker_homes_root,
)

logger = logging.getLogger(__name__)

_MANIFEST_NAME = "run_manifest.jsonl"

# The resource kinds the manifest records. A run that dies must be reconstructible
# from these entries alone.
RESOURCE_KINDS = frozenset(
    {
        "run_owner",  # the owning process pid; NOT a swept resource — a liveness
        #               anchor read by recover_stale_runs (never killed/deleted)
        "worker_home",  # <run_root>/worker-homes/<attempt-id>
        "verifier_home",  # <run_root>/verifier-homes/<attempt-id>
        "lease",  # an ExecutionEnvironmentLease id (released via LeaseManager)
        "worktree",  # a git worktree path under the run root
        "secret_file",  # a run-scoped secret file OUTSIDE the run root (host-only)
        "preview_pid",  # a fixture preview process (uvicorn) pid
        "serve_mutation",  # a tailscale serve mutation (restored, not deleted)
    }
)


class RunTeardownError(RuntimeError):
    """A run-level teardown left a security-blocking condition."""


# ─────────────────────────────────────────────────────────────────────────────
# Durable manifest
# ─────────────────────────────────────────────────────────────────────────────
def manifest_path(run_root: str) -> str:
    return os.path.join(run_root, _MANIFEST_NAME)


def register_resource(
    run_root: str, *, kind: str, ident: str, owner_pid: int | None = None, detail: str = ""
) -> None:
    """Durably record a resource the instant it is created.

    Append-only: the manifest is a recovery log, not current-state authority.
    Never raises into the caller — a manifest write must not break the hot path —
    but it logs on failure so a silent registration gap is visible.
    """
    if kind not in RESOURCE_KINDS:
        logger.error("register_resource: unknown kind %r (ident=%s)", kind, ident)
        return
    if not run_root or not ident:
        logger.error("register_resource: empty run_root/ident (kind=%s)", kind)
        return
    entry = {
        "kind": kind,
        "ident": ident,
        "owner_pid": int(owner_pid) if owner_pid is not None else os.getpid(),
        "detail": detail,
        # ts is diagnostic only — recovery keys on liveness of owner_pid, not age.
        "ts": time.time(),
    }
    try:
        os.makedirs(run_root, exist_ok=True)
        with open(manifest_path(run_root), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    except OSError as exc:
        logger.error("register_resource: manifest append failed for %s/%s: %s", kind, ident, exc)


def read_manifest(run_root: str) -> list[dict[str, Any]]:
    """Every recorded resource entry (dedup is the caller's concern)."""
    path = manifest_path(run_root)
    if not os.path.isfile(path):
        return []
    out: list[dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and obj.get("kind") in RESOURCE_KINDS:
                    out.append(obj)
    except OSError as exc:
        logger.error("read_manifest: %s: %s", path, exc)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Scope-safe deletion (the security-critical predicate)
# ─────────────────────────────────────────────────────────────────────────────
def _safe_run_descendant(target: str, run_root: str) -> tuple[bool, str]:
    """True only if ``target`` is a real descendant of the exact ``run_root``.

    FAIL CLOSED for every unsafe shape:
      * empty target or run_root;
      * a symlink anywhere on the target path (realpath would escape the root);
      * ``..`` traversal;
      * ``/`` or the run_root itself (we delete CONTENTS, never the root as a
        `..`-reachable parent, and never `/`);
      * any realpath that is not strictly under the realpath of the run_root.

    Both sides are realpath-resolved so a symlinked component cannot smuggle a
    delete outside the run tree. Returns ``(ok, reason)``.
    """
    if not target or not run_root:
        return False, "empty target or run_root"
    if target in ("/", os.sep):
        return False, "refusing to operate on filesystem root"
    if ".." in target.split(os.sep):
        return False, "'..' in target path"
    # A symlink AT the target is refused outright: we must not follow it out of
    # the tree, and rmtree on a symlink dir would traverse it.
    if os.path.islink(target):
        return False, "target is a symlink"
    real_root = os.path.realpath(run_root)
    real_target = os.path.realpath(target)
    if real_target == real_root:
        return False, "target resolves to the run root itself"
    prefix = real_root.rstrip(os.sep) + os.sep
    if not real_target.startswith(prefix):
        return False, f"target {real_target} is outside run root {real_root}"
    return True, "ok"


def _rmtree_safe(target: str, run_root: str, result: RunSweepResult) -> bool:
    """rmtree ``target`` only if it is a validated descendant of ``run_root``."""
    ok, reason = _safe_run_descendant(target, run_root)
    if not ok:
        result.unsafe_paths.append(f"{target}: {reason}")
        result.errors.append(f"SECURITY: refused unsafe delete {target}: {reason}")
        logger.error("run_teardown: refused unsafe delete %s: %s", target, reason)
        return False
    if not os.path.exists(target):
        return True
    shutil.rmtree(target, ignore_errors=True)
    if os.path.exists(target):
        shutil.rmtree(target, ignore_errors=True)
        if os.path.exists(target):
            result.errors.append(f"SECURITY: {target} survived rmtree")
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# The typed run-sweep result
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class RunSweepResult:
    """Truthful record of one run-level teardown. ``.ok`` gates qualification."""

    run_root: str = ""
    homes_destroyed: int = 0
    verifier_homes_destroyed: int = 0
    leases_released: int = 0
    worktrees_removed: int = 0
    previews_killed: int = 0
    secret_shredded: bool = True
    credential_residue: list[str] = field(default_factory=list)
    worker_home_residue: list[str] = field(default_factory=list)
    verifier_home_residue: list[str] = field(default_factory=list)
    spool_inflight_residue: int = 0
    unsafe_paths: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Clean ONLY when zero residue of every kind AND zero errors.

        A cleanup FAILURE is a security failure (closure bar §5): it makes the
        whole run NOT-QUALIFIED even when execution and verification otherwise
        succeeded. There is no partial pass.
        """
        return not (
            self.errors
            or self.credential_residue
            or self.worker_home_residue
            or self.verifier_home_residue
            or self.unsafe_paths
            or self.spool_inflight_residue
            or not self.secret_shredded
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_root": self.run_root,
            "homes_destroyed": self.homes_destroyed,
            "verifier_homes_destroyed": self.verifier_homes_destroyed,
            "leases_released": self.leases_released,
            "worktrees_removed": self.worktrees_removed,
            "previews_killed": self.previews_killed,
            "secret_shredded": self.secret_shredded,
            "credential_residue": list(self.credential_residue),
            "worker_home_residue": list(self.worker_home_residue),
            "verifier_home_residue": list(self.verifier_home_residue),
            "spool_inflight_residue": self.spool_inflight_residue,
            "unsafe_paths": list(self.unsafe_paths),
            "steps": list(self.steps),
            "errors": list(self.errors),
            "ok": self.ok,
        }


# ─────────────────────────────────────────────────────────────────────────────
# The run-level teardown authority
# ─────────────────────────────────────────────────────────────────────────────
def sweep_run(
    run_root: str,
    *,
    lease_manager: Any | None = None,
    spool: Any | None = None,
    secret_path: str = "",
    preview_pids: list[int] | None = None,
    kill_process: Any | None = None,
) -> RunSweepResult:
    """Destroy every resource a run created and PROVE zero residue.

    Idempotent: a second call on an already-clean run finds nothing to destroy
    and returns ``ok=True``. Every destruction is scope-safe (descendants of the
    exact ``run_root`` only); the run secret — which lives OUTSIDE the run root by
    design — is shredded through ``secret_path`` with an overwrite, never a
    descendant walk.

    ``kill_process`` defaults to ``os.kill``; injectable for tests.
    """
    result = RunSweepResult(run_root=run_root or "")
    if not run_root:
        result.errors.append("no run_root supplied — cannot sweep")
        return result

    killer = kill_process or os.kill

    # (1) Lease release. RUNTIME lease release is the POLLER's authority: on every
    # terminal transition it terminalizes the attempt and, on a release fault,
    # re-drives a revoke so retry can never deadlock (RV-HIGH-2, poller._terminalize).
    # This sweep is the CRASH BACKSTOP: when an explicit LeaseManager is supplied
    # (e.g. recover_stale_runs for a dead run), it revokes every manifest-recorded
    # lease — idempotent, so revoking an already-released lease is a no-op. When NO
    # manager is supplied (the normal runner-finally / dispatch-teardown sweep,
    # which have no store handle), recorded leases are NOT an error: the poller
    # already owns their release, and a lease record carries no credential material.
    manifest = read_manifest(run_root)
    lease_ids = _dedup(e["ident"] for e in manifest if e.get("kind") == "lease")
    if lease_manager is not None:
        for lid in lease_ids:
            try:
                lease_manager.revoke(lid, "run_teardown")
                result.leases_released += 1
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"lease {lid} release failed: {exc}")
    elif lease_ids:
        result.steps.append(
            f"{len(lease_ids)} recorded lease(s) not swept here — poller owns runtime "
            f"release; pass a lease_manager for crash-recovery revoke"
        )

    # (2) Remove recorded worktrees that survived lease release (defense in depth).
    for wt in _dedup(e["ident"] for e in manifest if e.get("kind") == "worktree"):
        if os.path.exists(wt) and _rmtree_safe(wt, run_root, result):
            result.worktrees_removed += 1

    # (3) Destroy worker homes and verifier homes as DIRECTORIES. The credential
    # overwrite already happened per-attempt on the graceful path; here we take
    # the whole home tree down (worker-homes/<id>, verifier-homes/<id>) so an
    # abandoned-run home never survives. Empty leftover dirs count as residue for
    # the §6 "0 homes" bar, so we remove the directories, not just credential files.
    for root_fn, counter in (
        (worker_homes_root, "homes_destroyed"),
        (verifier_homes_root, "verifier_homes_destroyed"),
    ):
        root = root_fn(run_root)
        if os.path.isdir(root):
            for name in sorted(os.listdir(root)):
                home = os.path.join(root, name)
                if _rmtree_safe(home, run_root, result):
                    setattr(result, counter, getattr(result, counter) + 1)
            # Remove the now-empty homes root too (a surviving root dir is residue).
            _rmtree_safe(root, run_root, result)

    # (4) Kill any recorded preview processes. NOTE (truthful): the current Wave 2
    # pipeline runs the fixture as a Docker CONTAINER torn down by name, not a host
    # preview process, so no preview pid is registered today and this loop is a
    # capability-present no-op. It exists so that if a host preview is ever added
    # (e.g. a uvicorn launched via gated_popen), registering its pid as
    # ``preview_pid`` makes it swept here — no false claim that one runs now.
    pids = list(preview_pids or [])
    pids += [
        int(e["ident"]) for e in manifest if e.get("kind") == "preview_pid" and _isint(e["ident"])
    ]
    for pid in _dedup_ints(pids):
        try:
            killer(pid, _sigterm())
            result.previews_killed += 1
        except ProcessLookupError:
            pass  # already dead
        except OSError as exc:
            result.errors.append(f"preview pid {pid} kill failed: {exc}")

    # (5) Shred the run-scoped secret (OUTSIDE the run root, host-only). Overwrite
    # then unlink; a shred failure while the file still exists is a security error.
    if secret_path:
        result.secret_shredded = _shred_secret(secret_path, result)

    # (6) Reconcile spool: count anything still unprocessed. The ledger is truth,
    # but a run reported clean must not leave inflight/inbox envelopes dangling.
    if spool is not None:
        try:
            pending = spool.pending_dispatch_ids()
            result.spool_inflight_residue = len(pending)
            if pending:
                result.errors.append(f"spool still holds {len(pending)} unprocessed dispatch(es)")
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"spool reconcile failed: {exc}")

    # (7) AUTHORITATIVE residue proof — 'destroyed' is a verified claim.
    result.credential_residue = assert_no_credential_residue(run_root)
    result.worker_home_residue = _surviving_homes(worker_homes_root(run_root))
    result.verifier_home_residue = assert_no_verifier_home_residue(run_root)
    if result.credential_residue:
        result.errors.append(f"SECURITY: credential residue: {result.credential_residue}")
    if result.worker_home_residue:
        result.errors.append(f"SECURITY: worker home residue: {result.worker_home_residue}")
    if result.verifier_home_residue:
        result.errors.append(f"SECURITY: verifier home residue: {result.verifier_home_residue}")

    result.steps.append(
        f"swept run_root={run_root} homes={result.homes_destroyed} "
        f"verifier_homes={result.verifier_homes_destroyed} leases={result.leases_released} "
        f"worktrees={result.worktrees_removed} previews={result.previews_killed} "
        f"secret_shredded={result.secret_shredded}"
    )
    return result


def _shred_secret(secret_path: str, result: RunSweepResult) -> bool:
    """Overwrite + unlink a secret file. Not a descendant of the run root — it is
    validated by being a regular file at the exact given path (no symlink)."""
    try:
        if os.path.islink(secret_path):
            result.errors.append(f"SECURITY: secret path is a symlink: {secret_path}")
            return False
        if not os.path.exists(secret_path):
            return True  # already gone
        length = os.path.getsize(secret_path)
        with open(secret_path, "r+b", buffering=0) as fh:
            fh.write(b"\0" * length)
            fh.flush()
            os.fsync(fh.fileno())
        os.unlink(secret_path)
        if os.path.exists(secret_path):
            result.errors.append(f"SECURITY: secret {secret_path} survived shred")
            return False
        return True
    except OSError as exc:
        result.errors.append(f"SECURITY: secret shred failed: {exc}")
        return False


def _surviving_homes(root: str) -> list[str]:
    """Any surviving home DIRECTORY under a homes root (dir residue, not just
    credential-file residue — the §6 '0 worker homes' bar counts directories)."""
    if not os.path.isdir(root):
        return []
    return [os.path.join(root, name) for name in sorted(os.listdir(root))]


# ─────────────────────────────────────────────────────────────────────────────
# Crash recovery — next-start stale-resource sweep
# ─────────────────────────────────────────────────────────────────────────────
def recover_stale_runs(
    runs_root: str,
    *,
    live_pids: set[int] | None = None,
    pid_is_alive: Any | None = None,
    lease_manager: Any | None = None,
) -> list[RunSweepResult]:
    """Sweep prior runs' residue whose owner process is dead (closure bar §8).

    ``runs_root`` holds one subdirectory per run (each a ``run_root`` with its own
    ``run_manifest.jsonl``). For each, if EVERY owner PID recorded in its manifest
    is dead, the run is abandoned → sweep it. If ANY owner PID is still alive, the
    run is REFUSED (a live run's resources are never destroyed). This is security
    cleanup of dead runs, NOT supervisor restoration.

    Liveness is checked via ``pid_is_alive`` (injectable) or, by default,
    ``os.kill(pid, 0)``. ``live_pids`` is an optional explicit allowlist merged in.
    """
    results: list[RunSweepResult] = []
    if not runs_root or not os.path.isdir(runs_root):
        return results
    alive = pid_is_alive or _default_pid_is_alive
    explicit_live = set(live_pids or set())

    for name in sorted(os.listdir(runs_root)):
        run_root = os.path.join(runs_root, name)
        if not os.path.isdir(run_root):
            continue
        manifest = read_manifest(run_root)
        if not manifest:
            continue  # no manifest → nothing durably recorded to recover
        # The run's owner is the pid anchored by 'run_owner' entries — the process
        # that owns this run. Its liveness governs the run: a live owner means the
        # run is still in progress and its resources must NEVER be swept. Fall back
        # to the writing owner_pid of entries only when no run_owner was recorded
        # (an older/partial manifest), so we still refuse a run written by a live
        # process.
        owner_idents = {
            int(e["ident"])
            for e in manifest
            if e.get("kind") == "run_owner" and _isint(e.get("ident"))
        }
        if not owner_idents:
            owner_idents = {int(e["owner_pid"]) for e in manifest if _isint(e.get("owner_pid"))}
        live_owner = any((pid in explicit_live) or alive(pid) for pid in owner_idents)
        if live_owner:
            logger.info("recover_stale_runs: %s has a LIVE owner — refusing to sweep", run_root)
            continue
        logger.warning("recover_stale_runs: sweeping abandoned run %s", run_root)
        results.append(sweep_run(run_root, lease_manager=lease_manager))
    return results


def _default_pid_is_alive(pid: int) -> bool:
    """os.kill(pid, 0): True if the process exists (and we may signal it)."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Exists but owned by another user — still LIVE, so refuse to sweep it.
        return True
    except OSError:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# small helpers
# ─────────────────────────────────────────────────────────────────────────────
def _sigterm() -> int:
    import signal

    return int(signal.SIGTERM)


def _isint(v: Any) -> bool:
    try:
        int(v)
        return True
    except (TypeError, ValueError):
        return False


def _dedup(it: Any) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in it:
        s = str(x)
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _dedup_ints(it: Any) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for x in it:
        try:
            i = int(x)
        except (TypeError, ValueError):
            continue
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


__all__ = [
    "RESOURCE_KINDS",
    "RunSweepResult",
    "RunTeardownError",
    "manifest_path",
    "read_manifest",
    "recover_stale_runs",
    "register_resource",
    "sweep_run",
]
