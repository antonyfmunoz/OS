#!/usr/bin/env python3
"""
sandbox_smoke_test.py — End-to-end proof that the sandbox layer works.

Runs, in order:

  1. Create a sandbox, write a file through ActionSystem, confirm
     production is untouched.
  2. Edit an existing production hub (eos/memory.py) through a
     sandbox — CoW must land in the sandbox workspace and prod bytes
     must not change.
  3. Run a dry-run workflow in the sandbox — workflow logs must land
     under the sandbox tree, not /opt/OS/data/workflow_log.jsonl.
  4. Tick the orchestrator in the sandbox — the orchestrator log must
     land under the sandbox tree.
  5. Use Observability with env_root= to inspect the sandbox, and with
     env_filter= to isolate production entries from the shared logs.
  6. Run the adversarial safety verifier as a subprocess.
  7. Clean up every sandbox/playground created during the run.

Exits non-zero if any step fails. This is the test you run before
declaring the sandbox layer shippable.

    python3 scripts/sandbox_smoke_test.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path("/opt/OS")
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.environment import make_playground, make_sandbox  # noqa: E402
from core.observability import Observability  # noqa: E402
from scripts.action_system import ActionSystem, ActionType  # noqa: E402
from scripts.workflow_engine import (  # noqa: E402
    WorkflowEngine,
    build_research_workflow,
)


STEPS: list[dict[str, str]] = []


def _step(name: str, ok: bool, detail: str = "") -> None:
    STEPS.append({"name": name, "ok": "yes" if ok else "no", "detail": detail})
    tag = "[PASS]" if ok else "[FAIL]"
    print(f"  {tag} {name}" + (f" — {detail}" if detail else ""))


def _fail(name: str, detail: str) -> None:
    _step(name, False, detail)


# ─── Steps ──────────────────────────────────────────────────────────────────


def step_write_file_in_sandbox() -> None:
    env = make_sandbox(name="smoke-write", ephemeral=True)
    try:
        a = ActionSystem(env=env)
        action = a.propose(
            action_type=ActionType.WRITE_FILE,
            target="smoke_artifact.txt",
            payload={"content": "sandbox smoke\n"},
            reason="smoke test",
        )
        result = a.execute(action, approve=True)
        ok = result.status.value == "succeeded"
        sbx_file = env.workspace / "smoke_artifact.txt"
        prod_file = _REPO_ROOT / "smoke_artifact.txt"
        _step(
            "write file lands in sandbox workspace",
            ok
            and sbx_file.exists()
            and sbx_file.read_text() == "sandbox smoke\n"
            and not prod_file.exists(),
            f"sbx_exists={sbx_file.exists()} prod_exists={prod_file.exists()}",
        )
    finally:
        env.cleanup()


def step_edit_production_hub_in_sandbox() -> None:
    prod = _REPO_ROOT / "eos" / "memory.py"
    before = prod.read_bytes()
    env = make_sandbox(name="smoke-edit", ephemeral=True)
    try:
        a = ActionSystem(env=env)
        action = a.propose(
            action_type=ActionType.EDIT_FILE,
            target="eos/memory.py",
            payload={"content": "# stubbed in smoke\n"},
            reason="smoke test",
        )
        result = a.execute(action, approve=True)
        after = prod.read_bytes()
        sbx_copy = env.workspace / "eos" / "memory.py"
        ok = (
            result.status.value == "succeeded"
            and before == after
            and sbx_copy.exists()
            and sbx_copy.read_bytes() == b"# stubbed in smoke\n"
        )
        _step(
            "CoW edit: prod unchanged, sandbox copy stubbed",
            ok,
            f"prod_changed={(before != after)} sbx_copy_ok={sbx_copy.exists()}",
        )
    finally:
        env.cleanup()


def step_workflow_logs_isolated() -> None:
    prod_log = _REPO_ROOT / "data" / "workflow_log.jsonl"
    before_size = prod_log.stat().st_size if prod_log.exists() else 0

    env = make_sandbox(name="smoke-workflow", ephemeral=True)
    try:
        eng = WorkflowEngine(env=env)
        wf = build_research_workflow("smoke research")
        result = eng.run_workflow(wf, dry_run=True)
        after_size = prod_log.stat().st_size if prod_log.exists() else 0
        sbx_log = env.workflow_log_path
        ok = (
            result.get("ok")
            and before_size == after_size
            and sbx_log.exists()
            and sbx_log.stat().st_size > 0
        )
        _step(
            "workflow logs stay in sandbox",
            ok,
            f"prod_delta={after_size - before_size} sbx_log_size={sbx_log.stat().st_size if sbx_log.exists() else 0}",
        )
    finally:
        env.cleanup()


def step_orchestrator_tick_in_sandbox() -> None:
    prod_log = _REPO_ROOT / "data" / "orchestrator_log.jsonl"
    before_size = prod_log.stat().st_size if prod_log.exists() else 0

    # Use the sandbox_runner command to prove the CLI path works end-to-end.
    # --playground gives us an ephemeral env that cleans itself up.
    r = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "scripts" / "sandbox_runner.py"),
            "orchestrator-tick",
            "--playground",
        ],
        capture_output=True,
        text=True,
    )
    after_size = prod_log.stat().st_size if prod_log.exists() else 0
    ok = r.returncode == 0 and before_size == after_size
    _step(
        "orchestrator tick leaves prod log alone",
        ok,
        f"rc={r.returncode} prod_delta={after_size - before_size}",
    )


def step_observability_env_views() -> None:
    # Bind to a fresh sandbox, write something so there's a log row,
    # then inspect via env_root=.
    env = make_sandbox(name="smoke-obs", ephemeral=False)
    try:
        a = ActionSystem(env=env)
        action = a.propose(
            action_type=ActionType.WRITE_FILE,
            target="obs_probe.txt",
            payload={"content": "probe"},
            reason="obs probe",
        )
        a.execute(action, approve=True)

        obs_sbx = Observability(env_root=env.root)
        actions = obs_sbx.recent_actions(10)
        has_action = any(r.get("target") == "obs_probe.txt" for r in actions)

        # Production-filter must NOT surface this sandbox row.
        obs_prod = Observability(env_filter="production")
        prod_actions = obs_prod.recent_actions(200)
        leaked = any(r.get("target") == "obs_probe.txt" for r in prod_actions)

        _step(
            "observability shows sandbox via env_root",
            has_action and not leaked,
            f"sbx_visible={has_action} leaked_to_prod_filter={leaked}",
        )

        # sandbox_runs() must enumerate it.
        runs = Observability.sandbox_runs()
        named = [r for r in runs if r["name"] == "smoke-obs"]
        _step(
            "sandbox_runs enumerates smoke-obs",
            bool(named),
            f"found={len(named)}",
        )
    finally:
        env.cleanup()


def step_playground_is_ephemeral() -> None:
    env = make_playground(name="smoke-play-e2e")
    root = env.root
    with env as e:
        (e.workspace / "throwaway.txt").write_text("hi")
        existed = (e.workspace / "throwaway.txt").exists()
    _step(
        "playground context manager cleans up",
        existed and not root.exists(),
        f"root_existed_before={existed} root_exists_after={root.exists()}",
    )


def step_run_safety_verifier() -> None:
    r = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "scripts" / "sandbox_safety_verifier.py"),
        ],
        capture_output=True,
        text=True,
    )
    ok = r.returncode == 0
    _step(
        "adversarial safety verifier passes (10/10)",
        ok,
        "" if ok else r.stdout[-400:] + "\n" + r.stderr[-400:],
    )


# ─── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    print("Sandbox smoke test — full isolation proof")
    print("─" * 60)
    start = time.time()

    steps = [
        step_write_file_in_sandbox,
        step_edit_production_hub_in_sandbox,
        step_workflow_logs_isolated,
        step_orchestrator_tick_in_sandbox,
        step_observability_env_views,
        step_playground_is_ephemeral,
        step_run_safety_verifier,
    ]
    for fn in steps:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            _fail(fn.__name__, f"unexpected: {exc}")

    dur = time.time() - start
    print("─" * 60)
    failed = [s for s in STEPS if s["ok"] != "yes"]
    print(
        f"Summary: {len(STEPS) - len(failed)}/{len(STEPS)} passed in {dur:.2f}s"
    )
    if failed:
        print("\nFailures:")
        for s in failed:
            print(f"  - {s['name']}: {s['detail']}")
        return 1

    # Write a JSON report for CI / state capture
    report = {
        "kind": "sandbox_smoke",
        "duration_s": round(dur, 3),
        "total": len(STEPS),
        "passed": len(STEPS) - len(failed),
        "steps": STEPS,
    }
    report_path = _REPO_ROOT / "data" / "sandbox_smoke_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
