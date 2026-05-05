#!/usr/bin/env python3
"""
eos_os.py — Unified operator CLI for the EOS AI Operating System.

This is the single surface an operator uses to drive the system. Every
command in here maps 1:1 to something in the architecture doc
(core/ARCHITECTURE_FINAL.md).

Commands:
    status                  — full system snapshot
    agents                  — persistent agent state
    workflows [--recent N]  — recent workflow runs
    actions [--recent N]    — recent action executions
    harness [--recent N]    — recent harness calls
    failures [--recent N]   — recent harness failures
    optimizer run           — run one optimizer pass
    optimizer list          — list pending proposals
    workflow run <name>     — run one workflow synchronously
    tick-agents             — tick every persistent agent once
    start [--once]          — start the orchestrator (foreground)
    verify                  — run the smoke test
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.observability import Observability  # noqa: E402


# ---------------------------------------------------------------------------
# Pretty-printers
# ---------------------------------------------------------------------------


def _dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


def _header(text: str) -> str:
    bar = "─" * len(text)
    return f"\n{text}\n{bar}"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _cmd_status(args: argparse.Namespace) -> int:
    obs = Observability()
    snap = obs.snapshot()
    print(_header("EOS AI OS — STATUS"))
    wf = snap["workflows"]
    print(
        f"Workflows  ok={wf['ok']}  failed={wf['failed']}  "
        f"rate={wf['failure_rate']:.0%}  running={len(wf['running'])}"
    )
    orch = snap["orchestrator"]
    print(
        f"Orchestrator  started={orch['started']}  "
        f"queue_depth={orch['queue_depth']}  jobs={len(orch['jobs'])}"
    )
    h = snap["harness"]
    print(
        f"Harness  recent_calls={h['recent_calls']}  "
        f"failures={h['recent_failures']}  rate={h['failure_rate']:.0%}"
    )
    opt = snap["optimizer"]
    print(
        f"Optimizer  last_run={opt['last_run_at']}  "
        f"total_proposals={opt['total_added']}"
    )

    print(_header("Persistent agents"))
    agents = snap["agents"]
    if not agents:
        print("  (none yet — run `eos_os tick-agents` to seed)")
    for a in agents:
        print(
            f"  {a['agent']:11s} ticks={a['tick_count']:4d} "
            f"failures={a['tick_failures']:2d}  last={a['last_tick_at']}"
        )

    print(_header("Jobs"))
    for j in orch["jobs"]:
        print(
            f"  {j['id']:22s} status={j['status']:10s} "
            f"runs={j['total_runs']}  fails={j['total_failures']}"
        )
    if not orch["jobs"]:
        print("  (no jobs in saved state — orchestrator hasn't been started)")

    return 0


def _cmd_agents(args: argparse.Namespace) -> int:
    obs = Observability()
    for a in obs.agent_status():
        print(_header(f"AGENT: {a['agent']}"))
        print(f"  last_tick_at: {a['last_tick_at']}")
        print(f"  tick_count:   {a['tick_count']}")
        print(f"  tick_failures: {a['tick_failures']}")
        custom = a.get("custom") or {}
        if custom:
            print("  custom:")
            for k, v in custom.items():
                print(f"    {k}: {v}")
    return 0


def _cmd_workflows(args: argparse.Namespace) -> int:
    obs = Observability()
    for r in obs.recent_workflows(args.recent):
        print(
            f"  {r.get('workflow_name','?'):12s} "
            f"{r.get('workflow_id','?'):24s} "
            f"→ {r.get('workflow_status','?')}"
        )
    return 0


def _cmd_actions(args: argparse.Namespace) -> int:
    obs = Observability()
    for r in obs.recent_actions(args.recent):
        print(
            f"  {r.get('event','?'):10s} "
            f"{r.get('type','?'):12s} "
            f"risk={r.get('risk','?'):8s} "
            f"target={r.get('target','?')}"
        )
    return 0


def _cmd_harness(args: argparse.Namespace) -> int:
    obs = Observability()
    for r in obs.recent_harness_calls(args.recent):
        status = "ok" if r.get("ok") else "FAIL"
        print(
            f"  {status:4s}  "
            f"{r.get('agent','?'):11s} "
            f"{r.get('operation','?'):16s} "
            f"{r.get('provider',''):15s} "
            f"{r.get('error') or ''}"
        )
    return 0


def _cmd_failures(args: argparse.Namespace) -> int:
    obs = Observability()
    for r in obs.recent_failures(args.recent):
        print(
            f"  {r.get('agent','?'):11s} "
            f"{r.get('operation','?'):16s} "
            f"→ {r.get('error','')}"
        )
    return 0


def _cmd_optimizer(args: argparse.Namespace) -> int:
    if args.op == "run":
        from core.optimizer import Optimizer

        opt = Optimizer(verbose=args.verbose)
        print(_dumps(opt.run_once()))
        return 0
    if args.op == "list":
        obs = Observability()
        rows = obs.optimizer_proposals(pending_only=True, limit=args.limit)
        if not rows:
            print("no pending proposals")
            return 0
        for r in rows:
            print(
                f"  [{r.get('kind','?'):24s}] "
                f"{r.get('target','?'):48s} — "
                f"{r.get('reason','')[:80]}"
            )
        return 0
    return 2


def _cmd_workflow_run(args: argparse.Namespace) -> int:
    from scripts.workflow_engine import (
        EXAMPLE_BUILDERS,
        WorkflowEngine,
    )

    if args.name not in EXAMPLE_BUILDERS:
        print(f"unknown workflow: {args.name} (available: {sorted(EXAMPLE_BUILDERS)})")
        return 2
    builder = EXAMPLE_BUILDERS[args.name]
    wf = (
        builder(args.goal, target_file=args.target)
        if args.name == "refactor"
        else builder(args.goal)
    )
    engine = WorkflowEngine(verbose=args.verbose)
    result = engine.run_workflow(wf, dry_run=args.dry_run)
    print(_dumps(result))
    return 0 if result.get("ok") else 2


def _cmd_tick_agents(args: argparse.Namespace) -> int:
    from core.persistent_agents import default_agents

    agents = default_agents()
    for a in agents:
        r = a.tick()
        status = "ok" if r.ok else "FAIL"
        print(f"  {status:4s} {a.name:11s} — {r.summary}")
        if r.alerts:
            for alert in r.alerts:
                print(f"        ALERT: {alert}")
    return 0


def _cmd_start(args: argparse.Namespace) -> int:
    """Delegates to scripts.orchestrator — same code, single entry point."""
    from scripts.orchestrator import (
        Orchestrator,
        _install_signal_handlers,
        build_default_jobs,
    )

    orch = Orchestrator(
        max_concurrent=args.max_concurrent,
        max_queue=args.max_queue,
        verbose=args.verbose,
    )
    for j in build_default_jobs():
        orch.register(j)
    _install_signal_handlers(orch)
    orch.start()
    print(
        f"[eos_os] orchestrator started with {len(orch.jobs())} jobs "
        f"(max_concurrent={args.max_concurrent})"
    )
    print("[eos_os] Ctrl-C to stop")

    if args.once:
        orch.scheduler.tick_once()
        time.sleep(2.0)
        orch.save_state()
        orch.stop()
        return 0

    try:
        while orch._started:
            time.sleep(5.0)
            orch.save_state()
    except KeyboardInterrupt:
        pass
    orch.stop()
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Run the EOS OS smoke test."""
    from subprocess import run

    r = run(
        [sys.executable, str(Path(_REPO_ROOT) / "scripts" / "eos_os_smoke_test.py")],
        cwd=_REPO_ROOT,
    )
    return r.returncode


def _cmd_sandbox(args: argparse.Namespace) -> int:
    """Delegate sandbox subcommand to scripts/sandbox_runner.py."""
    from subprocess import run

    runner = Path(_REPO_ROOT) / "scripts" / "sandbox_runner.py"
    r = run(
        [sys.executable, str(runner), *args.sandbox_args],
        cwd=_REPO_ROOT,
    )
    return r.returncode


def _cmd_sandboxes(args: argparse.Namespace) -> int:
    """List sandbox and playground runs currently on disk."""
    sandboxes = Observability.sandbox_runs()
    playgrounds = Observability.playground_runs()

    print(_header(f"SANDBOX RUNS ({len(sandboxes)})"))
    if not sandboxes:
        print("  (none — `eos_os sandbox run workflow ...` creates one)")
    for r in sandboxes:
        print(
            f"  {r['name']:28s} "
            f"wf_ok={r['workflows_ok']:3d} "
            f"wf_fail={r['workflows_failed']:3d} "
            f"actions={r['actions']:3d}  "
            f"{r['last_touched']}"
        )

    print(_header(f"PLAYGROUND RUNS ({len(playgrounds)})"))
    if not playgrounds:
        print("  (none)")
    for r in playgrounds:
        print(
            f"  {r['name']:28s} "
            f"wf_ok={r['workflows_ok']:3d} "
            f"wf_fail={r['workflows_failed']:3d} "
            f"actions={r['actions']:3d}  "
            f"{r['last_touched']}"
        )
    return 0


# ---------------------------------------------------------------------------
# Argparse wiring
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="eos_os",
        description="EOS AI OS — unified operator CLI.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("status", help="full system snapshot")
    p.set_defaults(func=_cmd_status)

    p = sub.add_parser("agents", help="persistent agent state")
    p.set_defaults(func=_cmd_agents)

    p = sub.add_parser("workflows", help="recent workflow runs")
    p.add_argument("--recent", type=int, default=10)
    p.set_defaults(func=_cmd_workflows)

    p = sub.add_parser("actions", help="recent action executions")
    p.add_argument("--recent", type=int, default=10)
    p.set_defaults(func=_cmd_actions)

    p = sub.add_parser("harness", help="recent harness calls")
    p.add_argument("--recent", type=int, default=10)
    p.set_defaults(func=_cmd_harness)

    p = sub.add_parser("failures", help="recent harness failures")
    p.add_argument("--recent", type=int, default=10)
    p.set_defaults(func=_cmd_failures)

    p = sub.add_parser("optimizer", help="run or list optimizer proposals")
    p.add_argument("op", choices=["run", "list"])
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=_cmd_optimizer)

    p = sub.add_parser("workflow", help="run one workflow synchronously")
    p.add_argument("name")
    p.add_argument("--goal", default="")
    p.add_argument("--target", default="")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=_cmd_workflow_run)

    p = sub.add_parser("tick-agents", help="tick every persistent agent once")
    p.set_defaults(func=_cmd_tick_agents)

    p = sub.add_parser("start", help="start the orchestrator in foreground")
    p.add_argument("--max-concurrent", type=int, default=2)
    p.add_argument("--max-queue", type=int, default=100)
    p.add_argument("--once", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=_cmd_start)

    p = sub.add_parser("verify", help="run the EOS OS smoke test")
    p.set_defaults(func=_cmd_verify)

    p = sub.add_parser(
        "sandbox",
        help="delegate to scripts/sandbox_runner.py (pass args after --)",
    )
    p.add_argument("sandbox_args", nargs=argparse.REMAINDER)
    p.set_defaults(func=_cmd_sandbox)

    p = sub.add_parser("sandboxes", help="list sandbox and playground runs")
    p.set_defaults(func=_cmd_sandboxes)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
