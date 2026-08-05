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
from substrate.execution.attempts.field_task_scope import (
    ScopeResolutionError,
    prepare_attempt_git_capability,
    readonly_binds_for_scope,
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
    trusted_base: str = ""

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
    # STATE the declared writable scope. Telling a worker "do not touch files
    # outside the task scope" without naming that scope grades it against a
    # boundary it was never shown — a legitimate implementation then fails
    # verification for an unattributable reason. The paths come from the SEALED
    # package (which carries the Task contract's own declaration), so this is
    # the same authority the verifier enforces, never a second derivation.
    scope_line = _declared_scope_line(package)
    if scope_line:
        parts.append(scope_line)
    if _is_zero_write(package):
        # Never tell a zero-write verifier to "make the change and commit it" —
        # the closing instruction would contradict its own scope declaration and
        # invite the exact diff that fails it closed.
        parts.append(
            "Do NOT modify anything. Inspect and report only. Do not commit, push, or create PRs."
        )
    else:
        parts.append(
            "Make the change in this worktree and commit it with a descriptive "
            "message. Do not push. Do not create PRs. Do not touch files outside "
            "the task scope."
        )
    return "\n\n".join(p for p in parts if p)


_GLOBAL_OBJECTIVE = "OBJECTIVE.md"
_SHARED_CONTEXT = "SHARED_CONTEXT.md"


class LeaseGitError(RuntimeError):
    """The lease worktree's git state could not be prepared.

    Defined ABOVE its first use (``_commit_trusted_projection``). Python resolves
    the name at call time, so a later definition would still work — but the same
    shape (an exception class declared after the function that raises it) already
    produced one real defect in this module, and reading order should not depend
    on knowing that rule.
    """


def project_task_local_objective(package: Any, worktree_path: str) -> dict[str, Any]:
    """Replace the all-Tasks objective in the lease with THIS Task's contract.

    Correction A. The fixture ships one ``OBJECTIVE.md`` holding the substantive
    contracts for Tasks A, B, C AND D. In field run ``20260803T191345Z-fail``
    both workers read it and implemented the complete objective, even though
    each had received a correct, self-sufficient, task-local contract naming its
    exact allowed and forbidden paths. A document in the working tree that
    describes a small, obviously-completable feature outcompetes instructions.

    So the worker's operative objective document is now DERIVED from the same
    canonical package that defines its scope and its verification:

    - ``OBJECTIVE.md`` is rewritten to contain only this Task's contract;
    - the original multi-Task text is preserved as ``SHARED_CONTEXT.md``,
      explicitly non-authoritative and (because it is outside the writable
      scope) mounted READ-ONLY, so nothing is hidden from a worker that needs
      cross-lane interface detail;
    - Task A's and Task B's views are mutually exclusive by construction, since
      each is rendered from its own package.

    This is a PROJECTION of the canonical contract, not a second contract model:
    every line comes from ``package.ordered_context`` / the sealed constraints.

    Returns a dict describing what was written (for the attempt record). Never
    raises: a projection failure must not silently run the worker against the
    global objective, so the caller checks ``ok``.
    """
    result: dict[str, Any] = {"ok": False, "projected": False, "shared_context": False}
    try:
        global_path = os.path.join(worktree_path, _GLOBAL_OBJECTIVE)
        body = _render_task_local_objective(package)
        if not body.strip():
            result["error"] = "package produced an empty task-local objective"
            return result
        if os.path.exists(global_path):
            # Preserve the global text as clearly-subordinate context rather
            # than deleting it: a worker that genuinely needs the cross-lane
            # interface contract must still be able to read it.
            with open(global_path, encoding="utf-8") as fh:
                original = fh.read()
            shared_path = os.path.join(worktree_path, _SHARED_CONTEXT)
            with open(shared_path, "w", encoding="utf-8") as fh:
                fh.write(
                    "# Shared context — NOT AUTHORITATIVE\n\n"
                    "This is background describing the COMPLETE multi-Task objective, "
                    "including contracts owned by OTHER Tasks running concurrently. It "
                    "does NOT authorize you to widen your change surface and it is NOT "
                    "your assignment. Your assignment is `OBJECTIVE.md`.\n\n---\n\n" + original
                )
            result["shared_context"] = True
        with open(global_path, "w", encoding="utf-8") as fh:
            fh.write(body)
        result["ok"] = True
        result["projected"] = True
        return result
    except OSError as exc:
        logger.warning("task-local objective projection failed: %s", exc)
        result["error"] = str(exc)
        return result


# Files the TRUSTED phase owns. The worker is never authorized to write these
# (they are outside every Task's writable scope and mounted read-only), and the
# verifier must not attribute them to the worker.
TRUSTED_PROJECTION_PATHS = (_GLOBAL_OBJECTIVE, _SHARED_CONTEXT)


def _commit_trusted_projection(worktree_path: str, base_commit: str, projection: dict) -> str:
    """Commit the trusted projection and return the attempt's NEW base commit.

    Finding F-3. The projection is a SYSTEM write, not a worker write, but it
    landed in the working tree while the attempt was still anchored at the
    fixture base — so `git diff <base>..HEAD` reported OBJECTIVE.md and
    SHARED_CONTEXT.md as worker output and the verifier rejected the attempt for
    an out-of-scope diff. Measured directly: with the worker writing nothing at
    all, `git status` showed `M OBJECTIVE.md` + `?? SHARED_CONTEXT.md`.

    Committing the projection in the trusted phase and re-anchoring the attempt
    to that commit makes the two authorities causally separate: the system write
    becomes an ANCESTOR of the worker's base, so it cannot appear in the worker's
    diff, cannot be credited to the worker, and (being read-only in phase 2)
    cannot be silently altered by it.

    Only the projection's own paths are staged — never `git add -A`, which would
    sweep unrelated tree state into a trusted, worker-attributed-free commit.
    """
    from substrate.execution.cpu_gate import gated_subprocess_run

    if not projection.get("projected"):
        return base_commit

    def _git(args: list[str], *, check: bool = True):
        r = gated_subprocess_run(
            ["git", *args], caller="trusted_projection", timeout=60, cwd=worktree_path
        )
        if r is None:
            raise LeaseGitError("git refused by CPU gate while committing trusted projection")
        if check and r.returncode != 0:
            raise LeaseGitError(f"git {' '.join(args)} failed: {r.stderr}")
        return r

    staged = [p for p in TRUSTED_PROJECTION_PATHS if os.path.exists(os.path.join(worktree_path, p))]
    if not staged:
        return base_commit
    _git(["add", "--", *staged])
    # Nothing to commit (identical projection on a retry) is success, not failure.
    if _git(["diff", "--cached", "--quiet"], check=False).returncode == 0:
        return base_commit
    _git(
        [
            "-c",
            "user.email=system@umh.local",
            "-c",
            "user.name=UMH trusted phase",
            "commit",
            "-q",
            "-m",
            "trusted: task-local objective projection (system write, not worker output)",
        ]
    )
    new_base = (_git(["rev-parse", "HEAD"]).stdout or "").strip()
    if not new_base:
        raise LeaseGitError("trusted projection commit produced no resolvable HEAD")
    return new_base


def _render_task_local_objective(package: Any) -> str:
    """Render THIS Task's contract as its operative objective document."""
    identity = getattr(package, "operation_identity", {}) or {}
    lines = ["# Your Task", ""]
    task_id = identity.get("task_id", "")
    if task_id:
        lines += [f"Task: `{task_id}`", ""]
    for ctx in getattr(package, "ordered_context", []) or []:
        if not isinstance(ctx, dict):
            continue
        rendered = _render_context_payload(ctx.get("payload", ctx))
        if rendered:
            section = str(ctx.get("section", "context")).replace("_", " ").title()
            lines += [f"## {section}", rendered, ""]
    scope_line = _declared_scope_line(package)
    if scope_line:
        lines += [scope_line, ""]
    lines += [
        "## Boundary",
        "",
        "Implement ONLY this Task's slice. Other Tasks are being implemented "
        "CONCURRENTLY by other workers and own the paths outside your writable "
        "scope — those paths are mounted READ-ONLY and a write to them will fail. "
        "`SHARED_CONTEXT.md`, if present, is background only and cannot widen "
        "your change surface.",
        "",
    ]
    return "\n".join(lines)


def _sealed_writable_scope(package: Any) -> list[str] | None:
    """The declared writable scope sealed into the package, or None if absent.

    Reads the SAME ``writable_path_scope=`` governance constraint that
    ``_declared_scope_line`` renders for the worker and that the verifier
    enforces — the constraint list is covered by ``package_hash``, so a worker
    cannot widen its own authority by editing anything it can reach.

    An explicitly declared EMPTY list is a real policy (zero-write verifier) and
    returns ``[]``; only a MISSING constraint returns ``None``.
    """
    for constraint in getattr(package, "governance_constraints", []) or []:
        text = str(constraint)
        if not text.startswith("writable_path_scope="):
            continue
        raw = text.split("=", 1)[1].strip()
        try:
            import ast

            parsed = ast.literal_eval(raw)
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError) as exc:
            raise ScopeResolutionError(
                f"sealed writable_path_scope is unparseable ({raw[:60]!r}): {exc}"
            ) from exc
        if not isinstance(parsed, (list, tuple)):
            # A bare string would iterate CHARACTER BY CHARACTER and produce
            # nonsense one-character "paths" — fail closed instead.
            raise ScopeResolutionError(
                f"sealed writable_path_scope is not a list (got {type(parsed).__name__})"
            )
        return [str(p) for p in parsed]
    return None


def _is_zero_write(package: Any) -> bool:
    """True when the package seals an EXPLICIT empty writable-path scope."""
    for constraint in getattr(package, "governance_constraints", []) or []:
        text = str(constraint)
        if text.startswith("writable_path_scope="):
            return text.split("=", 1)[1].strip() in ("[]", "()")
    return False


def _declared_scope_line(package: Any) -> str:
    """The sealed ``writable_path_scope`` constraint as worker-facing text.

    An EMPTY declared scope is meaningful, not missing: it is the independent
    verifier's zero-write authority, and the worker must be told explicitly that
    it may change nothing — otherwise it "helpfully" edits and fails closed.
    """
    for constraint in getattr(package, "governance_constraints", []) or []:
        text = str(constraint)
        if not text.startswith("writable_path_scope="):
            continue
        raw = text.split("=", 1)[1].strip()
        try:
            import ast

            parsed = ast.literal_eval(raw)
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            return ""
        # A non-sequence (int) would raise on iteration; a bare string would be
        # iterated CHARACTER BY CHARACTER, handing the worker one-character
        # "paths" so every real edit reads as out of scope.
        if not isinstance(parsed, (list, tuple)):
            return ""
        paths = [str(p) for p in parsed]
        if not paths:
            return (
                "## Writable Scope\n"
                "This task is READ-ONLY: it declares ZERO writable paths. Do not "
                "create, edit, or delete any file. Any change is out of scope and "
                "fails verification."
            )
        listed = "\n".join(f"- {p}" for p in paths)
        return (
            "## Writable Scope\n"
            "You may change ONLY these paths (verification rejects anything "
            f"outside them):\n{listed}"
        )
    return ""


def _render_context_payload(payload: Any) -> str:
    """Flatten one context payload into readable prompt text. A dict becomes
    ``key: value`` lines (lists joined); a scalar becomes its string. Empty
    values are skipped so the worker sees only substantive task content."""
    if isinstance(payload, dict):
        lines: list[str] = []
        for key, value in payload.items():
            if value in ("", None, [], {}):
                continue
            label = str(key).replace("_", " ")
            if isinstance(value, (list, tuple)):
                # A LIST is a list of separate obligations (constraints, the
                # precedence order). Joining with "; " collapsed an ordered,
                # multi-clause contract into one run-on line, where a numbered
                # precedence rule stops reading as an order and the last
                # constraint hides mid-sentence (review F-5). Render one bullet
                # per item and keep their declared order.
                items = [str(v).strip() for v in value if str(v).strip()]
                if not items:
                    continue
                lines.append(f"- {label}:")
                for item in items:
                    # An item may itself be multi-line (a task contract or the
                    # precedence note). Indent every line so the block stays
                    # visually subordinate to its bullet instead of dedenting
                    # back to the top level and reading as a new section.
                    first, *rest = item.split("\n")
                    lines.append(f"  - {first}")
                    lines.extend(f"    {line}" if line.strip() else "" for line in rest)
                continue
            text = str(value)
            if "\n" in text:
                # Same reason for a multi-line scalar: preserve its structure
                # rather than letting it collapse onto the label line.
                lines.append(f"- {label}:")
                lines.extend(f"  {line}" if line.strip() else "" for line in text.split("\n"))
                continue
            lines.append(f"- {label}: {text}")
        return "\n".join(lines)
    text = str(payload).strip()
    return text if text else ""


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

    # HARD WRITE-SCOPE ENFORCEMENT. Turn the Task's declared writable scope into
    # an actual capability: every other existing path in the lease is re-bound
    # READ-ONLY, so an out-of-scope write fails at the mount before the target
    # changes. The scope is read from the SEALED package (its
    # `writable_path_scope=` governance constraint is covered by package_hash),
    # so no worker-controlled input can widen it, and it is the SAME declaration
    # the verifier reads — one authority, two enforcement points.
    #
    # Field run 20260803T191345Z-fail is why this exists: correct, distinct,
    # self-sufficient contracts naming exact allowed AND forbidden paths did not
    # stop either worker from writing the complete six-file objective.
    # CORRECTION A — project the task-local objective BEFORE the read-only binds
    # are computed (it rewrites OBJECTIVE.md, which is outside every Task's
    # writable scope and therefore about to become read-only). Fail closed: a
    # worker must never run against the all-Tasks objective.
    # PHASE 1 — TRUSTED SYSTEM PHASE (finding F-3). This runs in the ORCHESTRATOR
    # process, BEFORE the worker sandbox exists, and its writes are committed and
    # made the attempt's new base. Previously the projection wrote OBJECTIVE.md +
    # SHARED_CONTEXT.md into the tree while the attempt stayed anchored at the
    # fixture base, so those two system files sat inside `<base>..HEAD` and the
    # verifier rejected the attempt for an out-of-scope diff — even when the
    # worker wrote nothing at all.
    #
    # Committing them and re-anchoring separates the two authorities cleanly:
    # system bookkeeping is an ANCESTOR of the worker's base, so it can never be
    # attributed to the worker, and the worker can never silently alter it (the
    # files are outside its writable scope and mounted read-only in phase 2).
    projection = project_task_local_objective(package, worktree_path)
    if not projection.get("ok"):
        _close_home_or_fail(attempt_home)
        return WorkerResult(
            error=f"task-local objective projection failed: {projection.get('error', 'unknown')}"
        )
    try:
        base_commit = _commit_trusted_projection(worktree_path, base_commit, projection)
    except LeaseGitError as exc:
        _close_home_or_fail(attempt_home)
        return WorkerResult(error=f"trusted projection could not be committed: {exc}")

    # GIT COMMIT CAPABILITY (finding F-1). Give this attempt a PRIVATE ref
    # namespace it alone may write, so `git add`/`git commit` work while every
    # shared git authority surface stays read-only. Without this the barrier made
    # `.git` wholly read-only and no worker could commit at all.
    try:
        attempt_ref_dir = prepare_attempt_git_capability(worktree_path, attempt_id)
    except ScopeResolutionError as exc:
        _close_home_or_fail(attempt_home)
        return WorkerResult(error=f"attempt git capability unavailable: {exc}")

    try:
        declared_scope = _sealed_writable_scope(package)
    except ScopeResolutionError as exc:
        _close_home_or_fail(attempt_home)
        return WorkerResult(error=f"write-scope enforcement unavailable: {exc}")
    if declared_scope is None:
        # No sealed scope at all — refuse rather than run with a fully writable
        # worktree. An unenforceable scope is a governance failure, not a
        # default-open condition.
        _close_home_or_fail(attempt_home)
        return WorkerResult(
            error="sealed package declares no writable_path_scope — refusing to run "
            "a worker whose write authority cannot be enforced"
        )
    try:
        # Returns the COMPLETE barrier: unauthorized source paths AND the git
        # authority surfaces (hooks/config/HEAD/refs/packed-refs/...). One call,
        # one canonical answer — see the note in readonly_binds_for_scope on why
        # this is not two functions.
        readonly_subpaths = readonly_binds_for_scope(declared_scope, lease_root=worktree_path)
    except ScopeResolutionError as exc:
        _close_home_or_fail(attempt_home)
        return WorkerResult(error=f"write-scope enforcement could not be built: {exc}")

    profile = IsolationProfile(
        worktree_path=worktree_path,
        worker_home=attempt_home.home_path,
        tmp_path=attempt_home.tmp_path,
        env_overrides=attempt_home.env_overrides(),
        readonly_subpaths=readonly_subpaths,
        # Re-opened AFTER every read-only bind (bwrap applies left-to-right, so
        # the last bind on a path wins). This is the ONE writable ref location:
        # the attempt's own namespace. `refs` as a whole is read-only above.
        writable_subpaths=[attempt_ref_dir],
        scope_enforced=True,
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
                trusted_base=base_commit,
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
            trusted_base=base_commit,
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
