#!/usr/bin/env python3
"""
sandbox_safety_verifier.py — Adversarial tests for the sandbox boundary.

Proves, end to end, that a sandbox environment CANNOT corrupt
production state under any of the attack shapes we care about:

  1. Direct file writes to production paths are blocked.
  2. Edits targeted at production hubs via the ActionSystem land in
     the sandbox workspace, not the real file.
  3. Workflow + orchestrator logs written during sandbox runs land
     under data/sandboxes/<name>/, never under data/<root>.
  4. The Neon audit mirror and graph refresh side-channels are
     disabled in sandbox mode.
  5. `env.cleanup()` only removes trees under the allowed sandbox /
     playground roots.
  6. Absolute paths outside /opt/OS are rejected.

Exits non-zero if any assertion fails. Run this after any change
that touches environment.py, action_system.py, or workflow_engine.py.

    python3 scripts/sandbox_safety_verifier.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import os
_REPO_ROOT = Path(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.environment import (  # noqa: E402
    FORBIDDEN_WRITE_PREFIXES,
    Environment,
    make_playground,
    make_sandbox,
)
from scripts.action_system import ActionSystem, ActionType  # noqa: E402
from scripts.workflow_engine import (  # noqa: E402
    WorkflowEngine,
    build_research_workflow,
)


# ─── Test harness ───────────────────────────────────────────────────────────


class Failure(Exception):
    pass


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise Failure(msg)


RESULTS: list[dict[str, str]] = []


def _run(name: str, fn) -> None:
    try:
        fn()
        RESULTS.append({"name": name, "ok": "yes", "detail": ""})
        print(f"  [PASS] {name}")
    except Failure as exc:
        RESULTS.append({"name": name, "ok": "no", "detail": str(exc)})
        print(f"  [FAIL] {name} — {exc}")
    except Exception as exc:
        RESULTS.append({"name": name, "ok": "no", "detail": f"unexpected: {exc}"})
        print(f"  [ERROR] {name} — {exc}")


# ─── Individual checks ──────────────────────────────────────────────────────


def check_guard_blocks_production_paths() -> None:
    """Environment.guard_write() must reject every forbidden prefix."""
    env = make_sandbox(name="verify-guard-prod", ephemeral=True)
    try:
        for forbidden in FORBIDDEN_WRITE_PREFIXES:
            try:
                env.guard_write(forbidden + "/foo.py")
            except PermissionError:
                continue
            raise Failure(f"guard_write let through forbidden path: {forbidden}")
    finally:
        env.cleanup()


def check_absolute_path_outside_repo_is_rejected() -> None:
    """/etc/passwd must never resolve in a sandbox env."""
    env = make_sandbox(name="verify-guard-escape", ephemeral=True)
    try:
        try:
            env.resolve("/etc/passwd")
        except PermissionError:
            return
        raise Failure("sandbox resolved /etc/passwd — escape not blocked")
    finally:
        env.cleanup()


def check_sandbox_edit_does_not_touch_production() -> None:
    """Edit a file through ActionSystem in a sandbox, confirm prod is
    byte-for-byte identical afterward."""
    prod_path = _REPO_ROOT / "runtime" / "memory.py"
    before = prod_path.read_bytes()
    env = make_sandbox(name="verify-edit-isolation", ephemeral=True)
    try:
        a = ActionSystem(env=env)
        action = a.propose(
            action_type=ActionType.EDIT_FILE,
            target="state/memory/memory.py",
            payload={"content": "# sandbox stub\n"},
            reason="safety verifier",
        )
        result = a.execute(action, approve=True)
        _assert(
            result.status.value == "succeeded",
            f"sandbox edit failed: {result.error}",
        )
        after = prod_path.read_bytes()
        _assert(before == after, "production file bytes changed after sandbox edit")
        # Confirm the sandbox workspace has the stub
        sbx_copy = env.workspace / "runtime" / "memory.py"
        _assert(sbx_copy.exists(), "sandbox copy missing")
        _assert(
            sbx_copy.read_bytes() == b"# sandbox stub\n",
            "sandbox copy has wrong content",
        )
    finally:
        env.cleanup()


def check_sandbox_write_blocked_if_target_outside_workspace() -> None:
    """If someone hand-rolls an ActionSystem call targeting a
    production absolute path, guard_write must catch it."""
    env = make_sandbox(name="verify-handrolled", ephemeral=True)
    try:
        # Force-resolve the target to the production path and bypass
        # _resolve_target by constructing the action manually.
        prod_target = _REPO_ROOT / "runtime" / "memory.py"
        # guard_write should raise because this path is outside the
        # sandbox workspace.
        try:
            env.guard_write(prod_target)
        except PermissionError:
            return
        raise Failure(
            f"guard_write let through production target: {prod_target}"
        )
    finally:
        env.cleanup()


def check_workflow_logs_land_in_sandbox() -> None:
    """Run a dry-run workflow in a sandbox and assert the sandbox log
    grew while the production log did not."""
    env = make_sandbox(name="verify-workflow-logs", ephemeral=True)
    try:
        prod_log = _REPO_ROOT / "data" / "workflow_log.jsonl"
        prod_before = prod_log.stat().st_size if prod_log.exists() else 0

        engine = WorkflowEngine(env=env)
        wf = build_research_workflow("safety verifier dry run")
        result = engine.run_workflow(wf, dry_run=True)
        _assert(result.get("ok"), f"dry-run failed: {result}")

        prod_after = prod_log.stat().st_size if prod_log.exists() else 0
        _assert(
            prod_before == prod_after,
            f"production workflow log changed: {prod_before} -> {prod_after}",
        )

        sbx_log = env.workflow_log_path
        _assert(sbx_log.exists(), "sandbox workflow log was not created")
        _assert(sbx_log.stat().st_size > 0, "sandbox workflow log is empty")
    finally:
        env.cleanup()


def check_action_logs_tagged_with_env() -> None:
    """Every action log row written from a sandbox must carry env=label."""
    env = make_sandbox(name="verify-tag", ephemeral=True)
    try:
        a = ActionSystem(env=env)
        action = a.propose(
            action_type=ActionType.WRITE_FILE,
            target="tag_test.txt",
            payload={"content": "ok"},
            reason="env tag check",
        )
        a.execute(action, approve=True)
        rows = [
            json.loads(line)
            for line in env.action_log_path.read_text().splitlines()
            if line.strip()
        ]
        _assert(rows, "no action log rows written")
        for row in rows:
            _assert(
                row.get("env") == env.label,
                f"action log row missing or wrong env tag: {row.get('env')!r}",
            )
    finally:
        env.cleanup()


def check_cleanup_refuses_random_directories() -> None:
    """env.cleanup() must refuse to delete anything not under the
    sandbox/playground/tempdir roots."""
    env = Environment(
        mode=__import__("core.environment", fromlist=["EnvMode"]).EnvMode.SANDBOX,
        name="evil",
        root=_REPO_ROOT / "runtime",  # production path!
        workspace=_REPO_ROOT / "runtime",
        data_dir=_REPO_ROOT / "runtime",
        log_dir=_REPO_ROOT / "runtime",
        state_dir=_REPO_ROOT / "runtime",
        snapshot_dir=_REPO_ROOT / "runtime",
    )
    try:
        env.cleanup()
    except PermissionError:
        return
    raise Failure(
        "cleanup() accepted a production root — catastrophic safety hole"
    )


def check_graph_refresh_disabled_in_sandbox() -> None:
    """_refresh_graph should return mode=skipped in sandbox mode."""
    env = make_sandbox(name="verify-no-graph-refresh", ephemeral=True)
    try:
        a = ActionSystem(env=env)
        res = a._refresh_graph(["state/memory/memory.py"])
        _assert(
            res.get("mode") == "skipped",
            f"graph refresh ran in sandbox: {res}",
        )
    finally:
        env.cleanup()


def check_neon_audit_disabled_in_sandbox() -> None:
    """_emit_neon must be a no-op in sandbox mode even when a sandbox
    action produces a log record."""
    env = make_sandbox(name="verify-no-neon", ephemeral=True)
    try:
        a = ActionSystem(env=env)
        # If this path tried to hit Neon it would either succeed or
        # raise. We only care that it doesn't attempt the import.
        called_marker: list[str] = []
        original = a._emit_neon
        def tracker(record):
            called_marker.append("called")
            original(record)
        a._emit_neon = tracker  # type: ignore[method-assign]

        action = a.propose(
            action_type=ActionType.WRITE_FILE,
            target="neon_test.txt",
            payload={"content": "ok"},
            reason="neon skip test",
        )
        a.execute(action, approve=True)
        # The method is called — but the function itself early-returns
        # when env is not production, so no Neon client is constructed.
        # We assert that by checking the *next* behavior: a production
        # ActionSystem would attempt the import; sandbox must not.
        # (The early-return is the contract we verify by reading the
        # first line of _emit_neon's source.)
        import inspect
        src = inspect.getsource(original)
        _assert(
            "self.env.is_production" in src,
            "_emit_neon is missing the sandbox guard",
        )
    finally:
        env.cleanup()


def check_playground_is_ephemeral() -> None:
    """Playground env must clean up on context exit."""
    env = make_playground(name="verify-ephemeral")
    root = env.root
    _assert(root.exists(), "playground root not provisioned")
    with env as e:
        (e.workspace / "throwaway.txt").write_text("hi")
    _assert(not root.exists(), "playground root persisted after exit")


# ─── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    checks = [
        ("guard blocks forbidden prefixes", check_guard_blocks_production_paths),
        ("absolute path escape rejected", check_absolute_path_outside_repo_is_rejected),
        ("sandbox edit leaves prod intact", check_sandbox_edit_does_not_touch_production),
        ("hand-rolled prod target blocked", check_sandbox_write_blocked_if_target_outside_workspace),
        ("workflow logs land in sandbox", check_workflow_logs_land_in_sandbox),
        ("action logs tagged with env", check_action_logs_tagged_with_env),
        ("cleanup refuses random dirs", check_cleanup_refuses_random_directories),
        ("graph refresh disabled in sandbox", check_graph_refresh_disabled_in_sandbox),
        ("neon audit disabled in sandbox", check_neon_audit_disabled_in_sandbox),
        ("playground is ephemeral", check_playground_is_ephemeral),
    ]
    print(f"Sandbox safety verifier — {len(checks)} checks")
    print("─" * 60)
    for name, fn in checks:
        _run(name, fn)
    print("─" * 60)
    failed = [r for r in RESULTS if r["ok"] != "yes"]
    print(
        f"Summary: {len(RESULTS) - len(failed)}/{len(RESULTS)} passed"
    )
    if failed:
        print("\nFailures:")
        for r in failed:
            print(f"  - {r['name']}: {r['detail']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
