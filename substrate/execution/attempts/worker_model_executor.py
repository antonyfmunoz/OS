"""Provider-neutral governed worktree worker.

This is the Wave 2 production worker entry point. It owns the substrate-side
lease preparation, prompt projection, hard write-scope barrier, credential
boundary, artifact extraction, and terminal result normalization. Provider
specifics live behind :mod:`model_executor_contract`.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
from dataclasses import dataclass, field
from typing import Any

from substrate.execution.attempts.field_task_scope import (
    ScopeResolutionError,
    paths_outside as _paths_outside,
    prepare_attempt_git_capability,
    readonly_binds_for_scope,
)
from substrate.execution.attempts.host_isolation import (
    IsolationProfile,
    IsolationUnavailable,
    build_isolated_command,
    scrub_worker_env,
)
from substrate.execution.attempts.model_executor_contract import ModelWorkPacketInput
from substrate.execution.attempts.model_executor_selection import build_model_executor
from substrate.execution.attempts.worker_credential_boundary import (
    CredentialBoundaryError,
    close_attempt_credential_home,
    open_attempt_credential_home,
)

# Reuse the audited Wave 2 substrate mechanics. These helpers are not Claude
# semantics; they are package rendering, trusted projection, git anchoring, and
# artifact extraction. Keeping the compatibility module intact preserves the old
# exact-SHA evidence while this module becomes the provider-neutral entry point.
from substrate.execution.attempts.worker_claude_cli import (  # noqa: E402
    LeaseGitError,
    _capture_git,
    _close_home_or_fail,
    _is_zero_write,
    _mark_projection_execution_context,
    make_lease_selfcontained,
    project_task_local_objective,
    render_prompt,
)
from substrate.execution.attempts.scope_contract import (
    TRUSTED_PROJECTION_PATHS,
    sealed_writable_scope,
)

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 600.0
_DEFAULT_MAX_TURNS = 30


def _run_isolated_with_tree_timeout(
    cmd: list[str],
    *,
    caller: str,
    timeout: float,
    cwd: str,
    env: dict[str, str],
    input_text: str,
) -> subprocess.CompletedProcess[str] | None:
    """Run the isolated worker command with owned process-tree cancellation."""

    from substrate.execution.cpu_gate import gated_popen

    proc = gated_popen(
        cmd,
        caller=caller,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    if proc is None:
        return None
    try:
        stdout, stderr = proc.communicate(input=input_text, timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout, output=stdout, stderr=stderr)


@dataclass
class WorkerResult:
    ok: bool = False
    status: str = "failed"
    summary: str = ""
    stdout: str = ""
    files_changed: list[str] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    diff: str = ""
    exit_code: int | None = None
    error: str = ""
    duration_seconds: float = 0.0
    isolated: bool = False
    cost_usd: float | None = None
    cost_status: str = "unknown"
    trusted_base: str = ""
    executor: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    retry_class: str = "unknown"
    proof_binding: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["stdout"] = self.stdout[-4000:]
        d["diff"] = self.diff[-8000:]
        return d


def _proof_binding(package: Any, base_commit: str, provider: str) -> dict[str, Any]:
    identity = dict(getattr(package, "operation_identity", None) or {})
    return {
        "attempt_id": identity.get("attempt_id", ""),
        "task_id": identity.get("task_id", ""),
        "package_hash": getattr(package, "package_hash", ""),
        "authorized_base": base_commit,
        "executor_provider": provider,
    }


def _credential_env_key(provider: str) -> str:
    if provider == "codex":
        return "CODEX_ACCESS_TOKEN"
    return "MODEL_EXECUTOR_TOKEN"


def run_worker_in_lease(
    *,
    package: Any,
    lease: Any,
    timeout: float = _DEFAULT_TIMEOUT,
    max_turns: int = _DEFAULT_MAX_TURNS,
    disallowed_tools: list[str] | None = None,
    oauth_token: str | None = None,
    attempt_id: str = "",
    run_root: str = "",
    provider: str | None = None,
) -> WorkerResult:
    """Run the configured model executor in one isolated lease worktree."""

    import time as _time

    worktree_path = getattr(lease, "worktree_path", "")
    base_commit = str(getattr(lease, "snapshot_ref", "") or "").strip()
    if not worktree_path or not os.path.isdir(worktree_path):
        return WorkerResult(error=f"lease worktree missing: {worktree_path}")
    if not base_commit:
        return WorkerResult(
            error="lease has no snapshot_ref (authorized base commit) — refusing to "
            "run: artifacts could not be attributed to this attempt"
        )

    try:
        executor = build_model_executor(provider)
    except ValueError as exc:
        return WorkerResult(error=str(exc), retry_class="configuration")
    executor_identity = executor.identity

    try:
        make_lease_selfcontained(worktree_path)
    except LeaseGitError as exc:
        return WorkerResult(error=f"lease git could not be made self-contained: {exc}")

    if not attempt_id:
        return WorkerResult(error="attempt_id is required to bind a credential home")
    if not run_root:
        return WorkerResult(error="run_root is required to place a credential home")
    try:
        attempt_home = open_attempt_credential_home(
            attempt_id=attempt_id,
            run_root=run_root,
            provider=executor_identity.provider,
        )
    except CredentialBoundaryError as exc:
        return WorkerResult(error=f"credential boundary unavailable: {exc}")

    extra_allow: dict[str, str] = {}
    if oauth_token:
        extra_allow[_credential_env_key(executor_identity.provider)] = oauth_token
    env = scrub_worker_env(dict(os.environ), extra_allow=extra_allow)
    env.update(attempt_home.env_overrides())

    readiness = executor.readiness(env=env)
    if not readiness.ok:
        _close_home_or_fail(attempt_home)
        return WorkerResult(
            error=f"model executor not ready: {readiness.reason}",
            executor=readiness.identity.proof_metadata(),
            retry_class="owner_auth_or_provider",
            trusted_base=base_commit,
        )

    projection = project_task_local_objective(package, worktree_path)
    if not projection.get("ok"):
        _close_home_or_fail(attempt_home)
        return WorkerResult(
            error=f"task-local objective projection failed: {projection.get('error', 'unknown')}"
        )
    try:
        _mark_projection_execution_context(worktree_path, projection)
    except LeaseGitError as exc:
        _close_home_or_fail(attempt_home)
        return WorkerResult(error=f"projection could not be made execution-context: {exc}")

    try:
        attempt_ref_dir = prepare_attempt_git_capability(worktree_path, attempt_id)
    except ScopeResolutionError as exc:
        _close_home_or_fail(attempt_home)
        return WorkerResult(error=f"attempt git capability unavailable: {exc}")

    try:
        declared_scope = sealed_writable_scope(package)
    except ScopeResolutionError as exc:
        _close_home_or_fail(attempt_home)
        return WorkerResult(error=f"write-scope enforcement unavailable: {exc}")
    if declared_scope is None:
        _close_home_or_fail(attempt_home)
        return WorkerResult(
            error="sealed package declares no writable_path_scope — refusing to run "
            "a worker whose write authority cannot be enforced"
        )

    from substrate.execution.attempts.field_task_scope import (
        normalize_allowed_paths as _normalize_allowed_paths,
    )

    try:
        normalized_scope = _normalize_allowed_paths(declared_scope, lease_root=worktree_path)
    except ScopeResolutionError as exc:
        _close_home_or_fail(attempt_home)
        return WorkerResult(
            error=f"sealed writable_path_scope could not be normalized for the "
            f"system-owned-path check: {exc}"
        )
    contradicted = [
        p for p in TRUSTED_PROJECTION_PATHS if not _paths_outside([p], normalized_scope)
    ]
    if contradicted:
        _close_home_or_fail(attempt_home)
        return WorkerResult(
            error=(
                f"sealed writable_path_scope grants worker authority over system "
                f"projection path(s) {contradicted!r} — refusing a scope that lets a "
                f"worker version control-plane execution context"
            )
        )
    try:
        readonly_subpaths = readonly_binds_for_scope(declared_scope, lease_root=worktree_path)
    except ScopeResolutionError as exc:
        _close_home_or_fail(attempt_home)
        return WorkerResult(error=f"write-scope enforcement could not be built: {exc}")

    prompt = render_prompt(package)
    if _is_zero_write(package):
        prompt += "\n\nVerifier mode: do not write files; return an independent verification report."
    profile = IsolationProfile(
        worktree_path=worktree_path,
        worker_home=attempt_home.home_path,
        tmp_path=attempt_home.tmp_path,
        env_overrides=attempt_home.env_overrides(),
        readonly_subpaths=readonly_subpaths,
        writable_subpaths=[attempt_ref_dir],
        scope_enforced=True,
    )

    binding = _proof_binding(package, base_commit, readiness.identity.provider)
    packet = ModelWorkPacketInput(
        prompt=prompt,
        worktree_path=worktree_path,
        timeout_seconds=float(timeout),
        max_turns=int(max_turns),
        disallowed_tools=tuple(disallowed_tools or ()),
        attempt_id=attempt_id,
        package_hash=str(getattr(package, "package_hash", "") or ""),
        operation_identity=dict(getattr(package, "operation_identity", None) or {}),
        proof_binding=binding,
    )
    try:
        invocation = executor.build_invocation(packet)
        if not invocation.argv:
            _close_home_or_fail(attempt_home)
            return WorkerResult(
                error="model executor did not provide a runnable invocation",
                executor=readiness.identity.proof_metadata(),
                retry_class="owner_auth_or_provider",
                trusted_base=base_commit,
            )
        cmd = build_isolated_command(invocation.argv, profile)
        isolated = True
    except IsolationUnavailable as exc:
        _close_home_or_fail(attempt_home)
        return WorkerResult(error=f"host isolation unavailable: {exc}")
    except AttributeError:
        _close_home_or_fail(attempt_home)
        return WorkerResult(
            error="model executor does not implement isolated invocation contract",
            executor=readiness.identity.proof_metadata(),
            retry_class="adapter_or_worker",
            trusted_base=base_commit,
        )

    start = _time.monotonic()
    try:
        from subprocess import TimeoutExpired

        timed_out = False
        try:
            completed = _run_isolated_with_tree_timeout(
                cmd,
                caller=f"wave2_model_executor_{readiness.identity.provider}",
                timeout=float(timeout),
                cwd=invocation.cwd or worktree_path,
                env=env,
                input_text=invocation.stdin,
            )
        except TimeoutExpired:
            completed = None
            timed_out = True
        duration = _time.monotonic() - start
        if timed_out:
            terminal = executor.collect_result(packet, None, duration_seconds=duration)
            terminal.timed_out = True
            terminal.retry_class = "external_transient"
        else:
            terminal = executor.collect_result(packet, completed, duration_seconds=duration)
        files, commits, diff = _capture_git(worktree_path, base_commit)
        produced = bool(commits) and bool(files)
        ok = terminal.ok and terminal.has_real_content and (produced or _is_zero_write(package))
        return WorkerResult(
            ok=ok,
            status="succeeded" if ok else "failed",
            summary=(terminal.summary or terminal.stdout)[-500:],
            stdout=terminal.stdout,
            files_changed=files,
            commits=commits,
            diff=diff,
            exit_code=terminal.exit_code,
            error=terminal.stderr[-500:] if not terminal.ok else "",
            duration_seconds=duration,
            isolated=isolated,
            cost_usd=terminal.cost.get("amount_usd"),
            cost_status=str(terminal.cost.get("status", "unknown")),
            trusted_base=base_commit,
            executor=(terminal.identity or readiness.identity).proof_metadata(),
            usage=dict(terminal.usage),
            retry_class=terminal.retry_class,
            proof_binding=dict(terminal.proof_binding or binding),
        )
    finally:
        close_attempt_credential_home(attempt_home)


__all__ = ["WorkerResult", "run_worker_in_lease", "render_prompt"]
