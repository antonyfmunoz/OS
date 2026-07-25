"""Real Claude-CLI worktree worker — the one real execution path (C4 part 2).

A worker receives a sealed :class:`ModelExecutionPackage`, runs the Claude Code
CLI inside its lease worktree under ENFORCED host isolation (bwrap), and returns
a machine-readable result. It NEVER marks its own attempt complete — completion
is Proof-gated in the verifier (Amendment v1 clause 6). It has no dispatch/result
signing secret and a scrubbed env (no /opt/OS, no production credentials).

There is NO simulation fallback here: if the CLI is unavailable or isolation
cannot be established, the worker returns a failure — never a fabricated success.
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from typing import Any

from substrate.execution.attempts.host_isolation import (
    IsolationProfile,
    IsolationUnavailable,
    build_isolated_command,
    scrub_worker_env,
)
from substrate.execution.attempts.worker_credential_boundary import (
    CredentialBoundaryError,
    close_attempt_credential_home,
    open_attempt_credential_home,
)

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 600.0
_DEFAULT_MAX_TURNS = 30


@dataclass
class WorkerResult:
    """Machine-readable outcome of a real worker run. NOT a completion verdict."""

    ok: bool = False
    status: str = "failed"  # "succeeded" | "failed" (worker's self-report only)
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

    def to_dict(self) -> dict[str, Any]:
        d = dict(self.__dict__)
        d["stdout"] = self.stdout[-4000:]  # bound
        d["diff"] = self.diff[-8000:]
        return d


def _resolve_cli_path() -> str:
    for c in (
        os.path.expanduser("~/.claude/local/claude"),
        "/usr/local/bin/claude",
        os.path.expanduser("~/.npm-global/bin/claude"),
    ):
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return shutil.which("claude") or ""


def render_prompt(package: Any) -> str:
    """Render the sealed package into the worker prompt. The worker cannot alter
    tenant/scope/authority/verification — those are sealed in the package hash;
    this only assembles the human-facing instruction text."""
    parts: list[str] = []
    if getattr(package, "role_instructions", ""):
        parts.append(package.role_instructions)
    if getattr(package, "operation_instructions", ""):
        parts.append(package.operation_instructions)
    identity = getattr(package, "operation_identity", {}) or {}
    if identity.get("task_id"):
        parts.append(f"Task: {identity.get('task_id')}")
    # Render the ordered context (the ACTUAL task spec: title / intent /
    # desired_end_state / constraints / success_criteria). compile_instruction_
    # package nests each section as {"section": name, "payload": {...}}. This was
    # previously accumulated into a local `frame` dict and then DROPPED — the
    # worker only ever saw "Execute task <id>" with no description of what to
    # build, so every worker produced files=0 and failed verification
    # (field run 20260725T210642Z, seventh layer). Render the payloads so the
    # worker knows the objective.
    for ctx in getattr(package, "ordered_context", []) or []:
        if not isinstance(ctx, dict):
            continue
        payload = ctx.get("payload", ctx)
        rendered = _render_context_payload(payload)
        if rendered:
            section = str(ctx.get("section", "context")).replace("_", " ").title()
            parts.append(f"## {section}\n{rendered}")
    parts.append(
        "Make the change in this worktree and commit it with a descriptive "
        "message. Do not push. Do not create PRs. Do not touch files outside "
        "the task scope."
    )
    return "\n\n".join(p for p in parts if p)


def _render_context_payload(payload: Any) -> str:
    """Flatten one context payload into readable prompt text. A dict becomes
    ``key: value`` lines (lists joined); a scalar becomes its string. Empty
    values are skipped so the worker sees only substantive task content."""
    if isinstance(payload, dict):
        lines: list[str] = []
        for key, value in payload.items():
            if value in ("", None, [], {}):
                continue
            if isinstance(value, (list, tuple)):
                value = "; ".join(str(v) for v in value if str(v))
                if not value:
                    continue
            label = str(key).replace("_", " ")
            lines.append(f"- {label}: {value}")
        return "\n".join(lines)
    text = str(payload).strip()
    return text if text else ""


class LeaseGitError(RuntimeError):
    """The lease worktree could not be made a self-contained git repo."""


def make_lease_selfcontained(worktree_path: str) -> None:
    """Turn a linked git worktree into a STANDALONE repo inside the lease dir.

    ``git worktree add`` gives the lease a ``.git`` FILE pointing at
    ``<fixture>/.git/worktrees/<id>`` (with objects in ``<fixture>/.git``). Both
    live OUTSIDE the lease directory. The worker runs under bwrap, which binds
    ONLY the lease dir — so inside the sandbox the gitdir target does not exist,
    every git command fails, and the worker (correctly, from its blind POV) ran
    ``git init`` to make a fresh repo, orphaning its commit from the fixture base.
    ``git diff base..HEAD`` then saw nothing → files=0 on every attempt
    (field run 20260725T220643Z, eighth layer).

    Fix: before the worker runs, absorb the external gitdir INTO the lease as a
    real ``.git`` directory (objects + refs + HEAD), so the lease is a complete,
    self-contained repository. This preserves the base-commit ancestry (so
    ``git diff base..HEAD`` and commit lineage still work) AND keeps everything
    the worker needs inside the single bound writable dir. Idempotent: a lease
    whose ``.git`` is already a directory is left as-is. Raises LeaseGitError on
    failure (dispatch must fail closed, not run a worker that cannot commit)."""
    import shutil as _shutil
    import subprocess as _sp

    from substrate.execution.cpu_gate import gated_subprocess_run

    dot_git = os.path.join(worktree_path, ".git")
    if os.path.isdir(dot_git):
        return  # already standalone
    if not os.path.isfile(dot_git):
        raise LeaseGitError(f"lease has no .git at {worktree_path}")

    # Resolve the external gitdir and the shared common (objects) dir via git
    # itself — robust against layout differences.
    def _git(args: list[str], cwd: str) -> str:
        r = gated_subprocess_run(["git", *args], caller="lease_selfcontain", timeout=30, cwd=cwd)
        if r is None:
            raise LeaseGitError("git refused by CPU gate while self-containing lease")
        if r.returncode != 0:
            raise LeaseGitError(f"git {' '.join(args)} failed: {r.stderr}")
        return (r.stdout or "").strip()

    gitdir = _git(["rev-parse", "--absolute-git-dir"], worktree_path)
    commondir = _git(["rev-parse", "--git-common-dir"], worktree_path)
    if not os.path.isabs(commondir):
        commondir = os.path.abspath(os.path.join(gitdir, commondir))

    tmp_git = dot_git + ".standalone"
    if os.path.exists(tmp_git):
        _shutil.rmtree(tmp_git, ignore_errors=True)
    # Start from the shared common dir (objects, packed-refs, config, refs), then
    # overlay the per-worktree gitdir (HEAD, index, this worktree's refs).
    _shutil.copytree(commondir, tmp_git, symlinks=True, ignore=_shutil.ignore_patterns("worktrees"))
    for entry in ("HEAD", "index", "ORIG_HEAD", "packed-refs"):
        src = os.path.join(gitdir, entry)
        if os.path.exists(src):
            _shutil.copy2(src, os.path.join(tmp_git, entry))
    wt_refs = os.path.join(gitdir, "refs")
    if os.path.isdir(wt_refs):
        _sp.run(
            ["cp", "-rn", wt_refs + "/.", os.path.join(tmp_git, "refs")],
            check=False,
            capture_output=True,
        )
    # Swap the pointer file for the real dir and drop worktree-only config.
    os.remove(dot_git)
    os.rename(tmp_git, dot_git)
    for key in ("core.worktree", "core.bare"):
        gated_subprocess_run(
            ["git", "config", "--unset", key],
            caller="lease_selfcontain",
            timeout=15,
            cwd=worktree_path,
        )
    # Prove it: the standalone repo must resolve HEAD to the base commit's tree.
    _git(["rev-parse", "HEAD"], worktree_path)


def _capture_git(worktree_path: str, base_commit: str) -> tuple[list[str], list[str], str]:
    """Return (files_changed, commits, diff) against the lease base commit."""
    from substrate.execution.cpu_gate import gated_subprocess_run

    def _run(args: list[str]) -> str:
        r = gated_subprocess_run(["git", *args], caller="worker_git", timeout=30, cwd=worktree_path)
        return (r.stdout or "").strip() if r else ""

    files = [f for f in _run(["diff", "--name-only", f"{base_commit}..HEAD"]).splitlines() if f]
    commits = [c for c in _run(["log", "--oneline", f"{base_commit}..HEAD"]).splitlines() if c]
    diff = _run(["diff", f"{base_commit}..HEAD"])
    return files, commits, diff


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
) -> WorkerResult:
    """Run the real Claude CLI worker for one attempt, isolated in its lease
    worktree. Returns a WorkerResult (never raises for a normal failure).

    ``attempt_id`` + ``run_root`` are REQUIRED: they bind this invocation's
    private credential home (``<run_root>/worker-homes/<attempt_id>/``). A retry
    is a new attempt_id, so A2 provably receives a different home than A1.
    """
    import time as _time

    from substrate.execution.cpu_gate import gated_subprocess_run

    worktree_path = getattr(lease, "worktree_path", "")
    # No "HEAD" fallback: artifacts are captured as `<base>..HEAD`, and
    # `HEAD..HEAD` is empty BY DEFINITION — the worker would report zero files
    # and zero commits for genuinely successful work, failing the artifacts
    # check on every attempt. A lease with no recorded base cannot anchor a diff.
    base_commit = str(getattr(lease, "snapshot_ref", "") or "").strip()
    if not worktree_path or not os.path.isdir(worktree_path):
        return WorkerResult(error=f"lease worktree missing: {worktree_path}")
    if not base_commit:
        return WorkerResult(
            error="lease has no snapshot_ref (authorized base commit) — refusing to "
            "run: artifacts could not be attributed to this attempt"
        )

    # Resolve the worker CLI FIRST — the cheapest, most fundamental precondition.
    # No point preparing a lease for a worker that cannot run, and this keeps the
    # no-simulation-fallback guarantee the earliest failure.
    cli = _resolve_cli_path()
    if not cli:
        return WorkerResult(error="Claude Code CLI not found — no simulation fallback")

    # Make the lease a SELF-CONTAINED git repo before isolating it: a linked
    # worktree's gitdir lives outside the lease dir and is invisible under bwrap,
    # so the worker cannot commit and every attempt reports files=0 (eighth
    # layer). Fail closed if it cannot be done — a worker that cannot commit is
    # useless and would only burn quota.
    try:
        make_lease_selfcontained(worktree_path)
    except LeaseGitError as exc:
        return WorkerResult(error=f"lease git could not be made self-contained: {exc}")

    prompt = render_prompt(package)
    inner = [
        cli,
        "--print",
        "--output-format",
        "text",
        "--max-turns",
        str(max_turns),
        "--permission-mode",
        "auto",
    ]
    for tool in disallowed_tools or []:
        inner += ["--disallowedTools", tool]
    inner += [prompt]

    # ATTEMPT-PRIVATE home (R1 / SEC-C2). The previous derivation
    # `dirname(worktree_path)` resolved to the SAME directory for every lease in
    # a run: two concurrent workers shared one home, the real ~/.claude
    # credential was copied into it, and nothing ever deleted it. The home is now
    # derived from attempt_id and destroyed on every terminal path below.
    if not attempt_id:
        return WorkerResult(error="attempt_id is required to bind a credential home")
    if not run_root:
        return WorkerResult(error="run_root is required to place a credential home")
    try:
        attempt_home = open_attempt_credential_home(attempt_id=attempt_id, run_root=run_root)
    except CredentialBoundaryError as exc:
        # Fail closed: never run a worker without its own credential boundary.
        return WorkerResult(error=f"credential boundary unavailable: {exc}")

    profile = IsolationProfile(
        worktree_path=worktree_path,
        worker_home=attempt_home.home_path,
        tmp_path=attempt_home.tmp_path,
        env_overrides=attempt_home.env_overrides(),
    )
    try:
        cmd = build_isolated_command(inner, profile)
        isolated = True
    except IsolationUnavailable as exc:
        # Fail closed: no unconfined worker — and destroy the credential we just
        # placed, since no worker will consume it.
        _close_home_or_fail(attempt_home)
        return WorkerResult(error=f"host isolation unavailable: {exc}")

    # The model credential (OAuth token) is INJECTED by the caller (the host
    # attempt runner, which lives outside substrate and may resolve it). Substrate
    # never reaches up into adapters/ to fetch it — dependency-direction law. If
    # the token is absent, the confined ~/.claude credentials file (copied above)
    # is the CLI's auth path.
    extra_allow = {}
    if oauth_token:
        extra_allow["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token
    elif os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        extra_allow["CLAUDE_CODE_OAUTH_TOKEN"] = os.environ["CLAUDE_CODE_OAUTH_TOKEN"]
    # scrub_worker_env is an ALLOWLIST: only keep_keys survive, and
    # ANTHROPIC_API_KEY is additionally denied. The candidate control plane's API
    # key is a DIFFERENT authority domain and must never reach the worker just
    # because both take part in the same run.
    env = scrub_worker_env(dict(os.environ), extra_allow=extra_allow)
    # Attempt-private HOME/XDG/CLAUDE_CONFIG_DIR/TMPDIR — applied AFTER the scrub
    # so no inherited value can point config lookup outside the boundary.
    env.update(attempt_home.env_overrides())

    start = _time.monotonic()
    try:
        result = gated_subprocess_run(
            cmd,
            caller="wave2_worker_claude_cli",
            timeout=timeout,
            cwd=worktree_path,
            env=env,
        )
        duration = _time.monotonic() - start

        if result is None:
            return WorkerResult(
                error="worker skipped by CPU gate (blocked_cpu)",
                isolated=isolated,
                duration_seconds=duration,
            )

        files, commits, diff = _capture_git(worktree_path, base_commit)
        exit_ok = result.returncode == 0
        produced = bool(commits) and bool(files)
        return WorkerResult(
            ok=exit_ok and produced,
            status="succeeded" if (exit_ok and produced) else "failed",
            summary=(result.stdout or "")[-500:],
            stdout=result.stdout or "",
            files_changed=files,
            commits=commits,
            diff=diff,
            exit_code=result.returncode,
            error="" if exit_ok else (result.stderr or "")[-500:],
            duration_seconds=duration,
            isolated=isolated,
            cost_usd=None,  # clause 8: no trustworthy USD figure available
            cost_status="unknown",
        )
    finally:
        # EVERY terminal path destroys the attempt's credential home: success,
        # failure, timeout, CPU-gate skip, cancellation (KeyboardInterrupt) and
        # any unexpected exception. Residue is a SECURITY failure, so a cleanup
        # that cannot complete raises out of here rather than being swallowed.
        _close_home_or_fail(attempt_home)


def _close_home_or_fail(attempt_home: Any) -> None:
    """Destroy an attempt credential home; surface residue as a security failure.

    Cleanup failure must be visible, never a warning: if credential material
    survives, the caller (and the run) must know.
    """
    try:
        close_attempt_credential_home(attempt_home)
    except CredentialBoundaryError:
        logger.error(
            "SECURITY: credential residue left for attempt %s at %s",
            getattr(attempt_home, "attempt_id", "?"),
            getattr(attempt_home, "home_path", "?"),
        )
        raise


__all__ = ["WorkerResult", "run_worker_in_lease", "render_prompt"]
