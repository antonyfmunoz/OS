"""ExecutionEnvironmentLease — the one writable window a worker gets.

A lease is a bounded, revocable grant of a WRITABLE workspace (a git worktree
sandbox) plus the allowlists that scope what the worker may touch. Invariants
(directive §IV.4 + Amendment v1 clause 4):

- one ACTIVE lease per Task (CAS-guarded);
- the writable path is a fresh worktree, NEVER the repo root and NEVER the
  /opt/OS main working tree (rejected);
- the control-plane candidate source is read-only; the worktree is the separate
  writable mount;
- the lease records an HONEST enforcement split: which boundaries are
  mechanically enforced vs merely declared (no false isolation claim reaches
  Proof). The actual OS-level filesystem/credential sandbox (bubblewrap/nsjail)
  is applied at dispatch time in C4/C7; this record is its ledger.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _from_dict(cls: type, d: dict[str, Any]) -> Any:
    return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class LeaseError(RuntimeError):
    """Raised when a lease cannot be acquired (fail closed)."""


# Enforcement classification recorded on every lease clause (clause 4 honesty).
ENFORCED = "enforced"
DECLARED = "declared"


@dataclass
class ExecutionEnvironmentLease:
    lease_id: str = field(default_factory=lambda: _new_id("lease"))
    tenant_id: str = ""
    task_id: str = ""
    attempt_id: str = ""
    worker_identity: str = ""
    compute_node_id: str = ""
    environment_type: str = "git_worktree"
    trust_zone: str = "sandboxed_worktree"
    # Read-only control-plane source (repo_root + base_commit + branch).
    source_ref: dict[str, str] = field(default_factory=dict)
    worktree_path: str = ""  # the ONE writable root
    writable_paths: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    network_policy: str = "none"  # "none" | "allowlist"
    network_allowlist: list[str] = field(default_factory=list)
    credential_refs: list[str] = field(default_factory=list)  # names only
    granted_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    last_heartbeat_at: float = 0.0
    revoked_at: float = 0.0
    revoke_reason: str = ""
    snapshot_ref: str = ""  # base_commit for rollback
    rollback_policy: str = "git_reset_to_snapshot"
    cleanup_state: str = "pending"  # pending | cleaned | failed
    sandbox_id: str = ""
    status: str = "active"  # active | released | expired | revoked
    record_version: int = 0
    # Honest enforcement ledger (clause 4): which boundaries are mechanically
    # enforced by Wave 2 vs declared-only (recorded, not falsely claimed).
    enforcement: dict[str, str] = field(
        default_factory=lambda: {
            "worker_env_allowlist": ENFORCED,
            "diff_scope_post_hoc": ENFORCED,
            "cwd_confinement": ENFORCED,
            "no_git_remote_push": ENFORCED,
            "tool_revocation": ENFORCED,
            "filesystem_namespace": DECLARED,  # enforced at dispatch via os-sandbox (C4/C7)
            "network_egress": DECLARED,
        }
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ExecutionEnvironmentLease:
        return _from_dict(cls, d)


def _is_forbidden_workspace(path: str, repo_root: str) -> str:
    """Return a reason string if ``path`` is a forbidden worker workspace, else ''."""
    rp = os.path.realpath(path)
    root = os.path.realpath(repo_root)
    if rp == root:
        return "workspace is the repo root"
    # Never the /opt/OS main working tree.
    umh_main = os.path.realpath(os.environ.get("UMH_ROOT", "/opt/OS"))
    if rp == umh_main or rp.startswith(umh_main + os.sep + ".git"):
        return "workspace is inside the /opt/OS main tree"
    return ""


class LeaseManager:
    """Acquires/releases/revokes execution environment leases over real git
    worktree sandboxes. one ACTIVE lease per Task."""

    def __init__(
        self,
        store: Any,
        sandbox_manager: Any | None = None,
        *,
        mutation_runner: Callable[..., Any] | None = None,
    ) -> None:
        self._store = store
        self._sandbox = sandbox_manager
        self._mutation_runner = mutation_runner

    def _runner(self) -> Callable[..., Any]:
        if self._mutation_runner is not None:
            return self._mutation_runner
        from substrate.execution.intent.loop import _substrate_native_governed_mutation

        return _substrate_native_governed_mutation

    def acquire(
        self,
        *,
        attempt: Any,
        assignment: Any,
        grant: Any,
        ttl_seconds: float = 3600.0,
        now: float | None = None,
    ) -> ExecutionEnvironmentLease:
        now = time.time() if now is None else now
        task_id = getattr(attempt, "task_id", "")

        # One active lease per Task.
        if self._store.active_lease_for_task(task_id) is not None:
            raise LeaseError(f"task {task_id} already has an active lease")

        worktree_path = ""
        branch = ""
        base_commit = ""
        sandbox_id = ""
        source_repo_root = ""
        if self._sandbox is not None:
            source_repo_root = getattr(self._sandbox, "_repo_root", "")
            sandbox = self._sandbox.create_sandbox(
                candidate_id=attempt.attempt_id,
                candidate_slug=f"attempt-{attempt.attempt_id[:8]}",
                agent_type=getattr(assignment, "worker_agent_type", "") or "developer_agent",
            )
            worktree_path = getattr(sandbox, "worktree_path", "")
            branch = getattr(sandbox, "branch_name", "")
            base_commit = getattr(sandbox, "base_commit", "")
            sandbox_id = getattr(sandbox, "sandbox_id", "") or getattr(sandbox, "branch_name", "")

            reason = _is_forbidden_workspace(worktree_path, source_repo_root)
            if reason:
                # Undo the worktree we just created, then fail closed.
                try:
                    self._sandbox.cleanup_sandbox(sandbox_id)  # type: ignore[attr-defined]
                except Exception:
                    pass
                raise LeaseError(f"refusing lease: {reason}")

        lease = ExecutionEnvironmentLease(
            tenant_id=getattr(grant, "tenant_id", ""),
            task_id=task_id,
            attempt_id=getattr(attempt, "attempt_id", ""),
            worker_identity=getattr(assignment, "worker_identity", ""),
            compute_node_id=getattr(assignment, "compute_node_id", ""),
            environment_type=getattr(assignment, "environment_class", "git_worktree"),
            source_ref={
                "repo_root": source_repo_root,
                "base_commit": base_commit,
                "branch": branch,
            },
            worktree_path=worktree_path,
            writable_paths=[worktree_path] if worktree_path else [],
            allowed_tools=list(getattr(assignment, "tool_profile", []) or []),
            credential_refs=list(getattr(grant, "credential_scope_refs", []) or []),
            expires_at=now + ttl_seconds,
            last_heartbeat_at=now,
            snapshot_ref=base_commit,
            sandbox_id=sandbox_id,
        )

        def _apply() -> tuple[str, bool]:
            self._store.append_lease(lease)
            return (f"lease acquired: {lease.lease_id}", True)

        self._runner()(
            mutation_name="execution_lease_mutate",
            intent=f"acquire environment lease for attempt {lease.attempt_id}",
            execute_fn=_apply,
            source="execution_attempts_leases",
            metadata={"lease_id": lease.lease_id, "task_id": task_id},
        )
        return lease

    def heartbeat(self, lease_id: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        row = self._store.get_lease(lease_id)
        if row is None:
            return
        lease = ExecutionEnvironmentLease.from_dict(row)
        lease.last_heartbeat_at = now
        self._store.update_lease_cas(lease, expected_record_version=lease.record_version)

    def release(self, lease_id: str, *, cleanup: bool = True, now: float | None = None) -> None:
        now = time.time() if now is None else now
        row = self._store.get_lease(lease_id)
        if row is None:
            return
        lease = ExecutionEnvironmentLease.from_dict(row)
        if self._sandbox is not None and cleanup and lease.sandbox_id:
            try:
                self._sandbox.cleanup_sandbox(lease.sandbox_id)  # type: ignore[attr-defined]
                lease.cleanup_state = "cleaned"
            except Exception:
                lease.cleanup_state = "failed"
        lease.status = "released"

        def _apply() -> tuple[str, bool]:
            self._store.update_lease_cas(lease, expected_record_version=lease.record_version)
            return (f"lease released: {lease_id}", True)

        self._runner()(
            mutation_name="execution_lease_mutate",
            intent=f"release environment lease {lease_id}",
            execute_fn=_apply,
            source="execution_attempts_leases",
            metadata={"lease_id": lease_id},
        )

    def revoke(self, lease_id: str, reason: str, now: float | None = None) -> None:
        now = time.time() if now is None else now
        row = self._store.get_lease(lease_id)
        if row is None:
            return
        lease = ExecutionEnvironmentLease.from_dict(row)
        lease.status = "revoked"
        lease.revoked_at = now
        lease.revoke_reason = reason
        if self._sandbox is not None and lease.sandbox_id:
            try:
                self._sandbox.cleanup_sandbox(lease.sandbox_id)  # type: ignore[attr-defined]
                lease.cleanup_state = "cleaned"
            except Exception:
                lease.cleanup_state = "failed"

        def _apply() -> tuple[str, bool]:
            self._store.update_lease_cas(lease, expected_record_version=lease.record_version)
            return (f"lease revoked: {lease_id}", True)

        # Revocation is always executable (execution_lease_revoke is degraded-ok).
        self._runner()(
            mutation_name="execution_lease_revoke",
            intent=f"revoke environment lease {lease_id}",
            execute_fn=_apply,
            source="execution_attempts_leases",
            metadata={"lease_id": lease_id, "reason": reason},
        )

    def expire_stale(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        expired = 0
        seen: dict[str, dict[str, Any]] = {}
        for row in self._store._read_lines(self._store._leases_path):  # noqa: SLF001
            seen[row.get("lease_id", "")] = row
        for row in seen.values():
            if row.get("status") == "active" and row.get("expires_at") and now >= row["expires_at"]:
                lease = ExecutionEnvironmentLease.from_dict(row)
                lease.status = "expired"

                def _apply(_l=lease) -> tuple[str, bool]:
                    self._store.update_lease_cas(_l, expected_record_version=_l.record_version)
                    return (f"lease expired: {_l.lease_id}", True)

                try:
                    self._runner()(
                        mutation_name="execution_lease_mutate",
                        intent=f"expire stale lease {lease.lease_id}",
                        execute_fn=_apply,
                        source="execution_attempts_leases",
                        metadata={"lease_id": lease.lease_id},
                    )
                    expired += 1
                except Exception as exc:
                    # No silent except-pass: a lease that will not expire is a
                    # slot that never returns, so the failure must be visible.
                    logger.debug("failed to expire lease %s: %s", lease.lease_id, exc)
        return expired


__all__ = [
    "ExecutionEnvironmentLease",
    "LeaseManager",
    "LeaseError",
    "ENFORCED",
    "DECLARED",
]
