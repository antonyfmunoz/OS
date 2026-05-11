#!/usr/bin/env python3
"""
sandbox_runner.py — Safe experimentation surface for the EOS AI OS.

The sandbox runner is the operator-facing CLI for the sandbox layer.
Every command here runs against an isolated environment (sandbox or
playground), never against production. The runner is the *only*
blessed way to exercise workflows, actions, or orchestrator ticks
outside production.

What this file DOES provide:
  * `run workflow <name> --goal ...`  — run a workflow in a sandbox
  * `run action <type> --target ...`  — run a single action in a sandbox
  * `orchestrator-tick`                — simulate one orchestrator tick
  * `playground`                       — fire up an ephemeral playground
  * `replay <workflow_id>`             — replay a past workflow from logs
  * `stage <proposal_id>`              — stage an optimizer proposal
  * `list`                             — list existing sandboxes
  * `diff <sandbox_name>`              — show what changed in a sandbox
  * `clean <sandbox_name>`             — delete a sandbox tree
  * `inspect <sandbox_name>`           — show logs + state summary

What this file does NOT do:
  * Ever write to production data files directly
  * Ever bypass ActionSystem's approval gate (sandbox still enforces it)
  * Ever mutate the production graph

Every command creates (or reuses) an Environment and threads it into
ActionSystem / WorkflowEngine. Those components already know how to
respect the env thanks to phase 3 + 4 of this pass.

Usage examples:
    python3 scripts/sandbox_runner.py run workflow research --goal "graph layer"
    python3 scripts/sandbox_runner.py run action edit-file --target runtime/memory.py --content-file /tmp/new.py
    python3 scripts/sandbox_runner.py playground
    python3 scripts/sandbox_runner.py orchestrator-tick
    python3 scripts/sandbox_runner.py replay wf-research-abc12345
    python3 scripts/sandbox_runner.py stage prop-abc1234567
    python3 scripts/sandbox_runner.py list
    python3 scripts/sandbox_runner.py diff sbx-20260410-210000-abc123
    python3 scripts/sandbox_runner.py inspect sbx-...
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import os
_REPO_ROOT = Path(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.environment import (  # noqa: E402
    Environment,
    EnvMode,
    PLAYGROUND_ROOT,
    SANDBOX_ROOT,
    make_playground,
    make_sandbox,
)


# ─── Helpers ────────────────────────────────────────────────────────────────


def _dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


def _banner(env: Environment) -> None:
    """Make it impossible to forget you're in a sandbox."""
    mark = {
        EnvMode.PRODUCTION: "[PRODUCTION]",
        EnvMode.SANDBOX: "[SANDBOX]",
        EnvMode.PLAYGROUND: "[PLAYGROUND]",
    }[env.mode]
    print(f"{mark} env={env.label} workspace={env.workspace}")


def _resolve_env(args: argparse.Namespace) -> Environment:
    """Pick the environment based on --sandbox / --playground flags.

    Default is a fresh sandbox. If --sandbox <name> is given, reuse
    that tree. If --playground is set, spin up an ephemeral one.
    """
    if getattr(args, "playground", False):
        return make_playground()
    name = getattr(args, "sandbox", None)
    return make_sandbox(name=name)


def _list_sandboxes() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if SANDBOX_ROOT.exists():
        for d in sorted(SANDBOX_ROOT.iterdir()):
            if not d.is_dir():
                continue
            marker = d / ".sandbox_marker"
            info = {
                "name": d.name,
                "mode": "sandbox",
                "path": str(d),
                "size_mb": _dir_size_mb(d),
                "created_at": _parse_marker(marker).get("created_at"),
            }
            out.append(info)
    if PLAYGROUND_ROOT.exists():
        for d in sorted(PLAYGROUND_ROOT.iterdir()):
            if not d.is_dir():
                continue
            marker = d / ".sandbox_marker"
            info = {
                "name": d.name,
                "mode": "playground",
                "path": str(d),
                "size_mb": _dir_size_mb(d),
                "created_at": _parse_marker(marker).get("created_at"),
            }
            out.append(info)
    return out


def _dir_size_mb(path: Path) -> float:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return round(total / (1024 * 1024), 3)


def _parse_marker(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _load_sandbox_by_name(name: str) -> Environment | None:
    """Rebind an Environment to an existing sandbox tree on disk.

    Looks in both the sandbox root and the playground root. Returns
    None if no tree with that name exists.
    """
    for base in (SANDBOX_ROOT, PLAYGROUND_ROOT):
        root = base / name
        if not root.exists():
            continue
        mode = EnvMode.SANDBOX if base == SANDBOX_ROOT else EnvMode.PLAYGROUND
        return Environment(
            mode=mode,
            name=name,
            root=root,
            workspace=root / "workspace",
            data_dir=root / "data",
            log_dir=root / "logs",
            state_dir=root / "state",
            snapshot_dir=root / "snapshots",
            ephemeral=False,
            read_through=True,
        )
    return None


def _diff_workspace(env: Environment) -> dict[str, Any]:
    """Compare every file in the sandbox workspace with its production
    counterpart. Report which files were added, modified, or removed."""
    added: list[str] = []
    modified: list[str] = []
    workspace = env.workspace
    if not workspace.exists():
        return {"added": [], "modified": [], "count": 0}
    for p in workspace.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(workspace)
        prod = _REPO_ROOT / rel
        if not prod.exists():
            added.append(str(rel))
            continue
        try:
            if p.read_bytes() != prod.read_bytes():
                modified.append(str(rel))
        except OSError:
            continue
    return {
        "added": added,
        "modified": modified,
        "count": len(added) + len(modified),
    }


# ─── Command: run workflow ──────────────────────────────────────────────────


def _cmd_run_workflow(args: argparse.Namespace) -> int:
    from scripts.workflow_engine import EXAMPLE_BUILDERS, WorkflowEngine

    env = _resolve_env(args)
    _banner(env)

    if args.name not in EXAMPLE_BUILDERS:
        print(
            f"unknown workflow: {args.name} "
            f"(available: {sorted(EXAMPLE_BUILDERS)})"
        )
        return 2
    builder = EXAMPLE_BUILDERS[args.name]
    if args.name == "refactor":
        wf = builder(args.goal, target_file=args.target or "")
    else:
        wf = builder(args.goal)

    engine = WorkflowEngine(verbose=args.verbose, env=env)
    result = engine.run_workflow(wf, dry_run=args.dry_run)
    print(_dumps(result))
    print(f"\n[sandbox] logs: {env.workflow_log_path}")
    print(f"[sandbox] state: {env.workflow_state_dir}")
    return 0 if result.get("ok") else 2


# ─── Command: run action ────────────────────────────────────────────────────


def _cmd_run_action(args: argparse.Namespace) -> int:
    from scripts.action_system import ActionSystem, ActionType

    env = _resolve_env(args)
    _banner(env)

    a = ActionSystem(verbose=args.verbose, env=env)
    type_map = {
        "edit-file": ActionType.EDIT_FILE,
        "write-file": ActionType.WRITE_FILE,
        "delete-file": ActionType.DELETE_FILE,
        "run-script": ActionType.RUN_SCRIPT,
        "run-command": ActionType.RUN_COMMAND,
        "query-graph": ActionType.QUERY_GRAPH,
    }
    if args.type not in type_map:
        print(f"unknown action type: {args.type}")
        return 2
    action_type = type_map[args.type]

    payload: dict[str, Any] = {}
    target = args.target or ""
    if action_type in (ActionType.EDIT_FILE, ActionType.WRITE_FILE):
        if args.content_file:
            payload["content_path"] = args.content_file
        elif args.content is not None:
            payload["content"] = args.content
        else:
            print("edit/write actions require --content or --content-file")
            return 2
    elif action_type == ActionType.RUN_COMMAND:
        payload["command"] = args.command or ""
        target = args.target or "sandbox-command"
    elif action_type == ActionType.RUN_SCRIPT:
        payload["args"] = list(args.script_args or [])
    elif action_type == ActionType.QUERY_GRAPH:
        payload["query"] = args.query or "dependents"

    action = a.propose(
        action_type=action_type,
        target=target,
        payload=payload,
        reason=args.reason or f"sandbox_runner:{args.type}",
    )
    print(
        _dumps(
            {
                "action_id": action.id,
                "type": action.type.value,
                "target": action.target,
                "risk": action.risk_level.value,
                "requires_approval": action.requires_approval,
                "impact": asdict(action.impact) if action.impact else None,
            }
        )
    )
    result = a.execute(action, dry_run=args.dry_run, approve=args.approve)
    print(_dumps(asdict(result)))
    return 0 if result.status.value in ("succeeded", "skipped_dry_run") else 1


# ─── Command: orchestrator-tick ─────────────────────────────────────────────


def _cmd_orchestrator_tick(args: argparse.Namespace) -> int:
    """Simulate one orchestrator scheduler tick against a sandbox.

    Loads the default job registry, rewires the Orchestrator's
    ActivityLog to point into the sandbox, runs
    `scheduler.tick_once()` exactly once, then snapshots
    `orchestrator.status()` into the sandbox state dir.

    Never enters the daemon loop. Never writes to
    /opt/OS/data/orchestrator_log.jsonl.
    """
    env = _resolve_env(args)
    _banner(env)

    from scripts.orchestrator import Orchestrator, build_default_jobs

    orch = Orchestrator(
        max_concurrent=1,
        max_queue=10,
        verbose=args.verbose,
    )
    # Redirect the activity log into the sandbox. ActivityLog writes
    # straight to `self.path`, so swapping the attribute is enough.
    env.orchestrator_log_path.parent.mkdir(parents=True, exist_ok=True)
    orch.log.path = env.orchestrator_log_path

    for j in build_default_jobs():
        orch.register(j)

    submitted = orch.scheduler.tick_once()
    time.sleep(0.2)

    # Manual state snapshot into the sandbox — don't call save_state()
    # because it's hardcoded to the production path.
    state_path = env.state_dir / "orchestrator_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(orch.status(), indent=2, default=str), encoding="utf-8"
    )

    print(
        _dumps(
            {
                "sandbox": env.label,
                "submitted": submitted,
                "jobs_registered": len(orch.jobs()),
                "log": str(env.orchestrator_log_path),
                "state": str(state_path),
            }
        )
    )
    return 0


# ─── Command: playground ────────────────────────────────────────────────────


def _cmd_playground(args: argparse.Namespace) -> int:
    """Start a playground and drop the operator a summary + hint.

    Playgrounds are ephemeral but we still want to *keep* the tree
    around if the operator is experimenting interactively. If
    `--ephemeral` is passed, we clean up on exit. Otherwise the tree
    stays until `clean` is called.
    """
    env = make_playground(name=args.name)
    _banner(env)
    print(f"[playground] tree: {env.root}")
    print(f"[playground] workspace: {env.workspace}")
    print(f"[playground] logs: {env.log_dir}")
    print(
        "\nUse this environment by setting EOS_ENV="
        f"playground:{env.name} in your shell, or pass env= directly "
        "to ActionSystem / WorkflowEngine."
    )
    if args.ephemeral:
        print("[playground] --ephemeral set: cleaning up now")
        env.cleanup()
    return 0


# ─── Command: replay ────────────────────────────────────────────────────────


def _cmd_replay(args: argparse.Namespace) -> int:
    """Reconstruct a past workflow from logs and re-run it in a sandbox.

    Strategy:
      1. Find the saved workflow state file for <workflow_id>. These
         files live in data/workflow_state/<id>.json and hold the full
         Workflow dict (steps + inputs).
      2. Rehydrate a Workflow object with the same id + goal + steps.
      3. Spin up a sandbox env and run it.
      4. Diff the original outcome against the sandbox outcome and
         emit a comparison report.
    """
    from scripts.workflow_engine import (
        Step,
        StepType,
        Workflow,
        WorkflowEngine,
        WorkflowStatus,
    )

    # Original workflow state lives in production's state dir.
    prod_state = _REPO_ROOT / "data" / "workflow_state" / f"{args.workflow_id}.json"
    if not prod_state.exists():
        print(f"error: no saved workflow state at {prod_state}")
        return 2

    data = json.loads(prod_state.read_text())
    steps = [
        Step(
            id=s["id"],
            type=StepType(s["type"]),
            input=s.get("input", {}),
            dependencies=list(s.get("dependencies", [])),
            assigned_agent=s.get("assigned_agent", "generalist"),
        )
        for s in data.get("steps", [])
    ]
    wf = Workflow(
        id=f"{data['id']}-replay",
        name=data.get("name", "replay"),
        goal=data.get("goal", ""),
        steps=steps,
    )

    env = _resolve_env(args)
    _banner(env)
    engine = WorkflowEngine(verbose=args.verbose, env=env)
    result = engine.run_workflow(wf, dry_run=args.dry_run)

    comparison = {
        "original": {
            "id": data.get("id"),
            "status": data.get("status"),
            "result": data.get("result"),
            "finished_at": data.get("finished_at"),
        },
        "replay": {
            "id": wf.id,
            "status": result["status"],
            "result": result.get("result"),
            "ok": result.get("ok"),
        },
        "sandbox": env.label,
    }
    print(_dumps(comparison))
    return 0 if result.get("ok") else 2


# ─── Command: stage (optimizer proposal) ────────────────────────────────────


def _cmd_stage(args: argparse.Namespace) -> int:
    """Stage an optimizer proposal: run it through the sandbox and
    produce a report with success/failure, diff preview, and risk.

    Proposals carry a `suggested_action` dict with action_type + target
    + payload. We turn that into a real Action in a sandbox env and
    let the sandbox ActionSystem execute it. The production proposals
    log is never modified.
    """
    from scripts.action_system import ActionSystem, ActionType

    proposals_log = _REPO_ROOT / "data" / "optimizer_proposals.jsonl"
    if not proposals_log.exists():
        print(f"error: no proposals log at {proposals_log}")
        return 2

    target_prop: dict[str, Any] | None = None
    for line in proposals_log.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("id") == args.proposal_id:
            target_prop = row
            break
    if target_prop is None:
        print(f"error: proposal {args.proposal_id!r} not found")
        return 2

    suggested = target_prop.get("suggested_action") or {}
    if suggested.get("action_type") in (None, "", "none"):
        print(
            _dumps(
                {
                    "proposal_id": args.proposal_id,
                    "kind": target_prop.get("kind"),
                    "stage_result": "no_executable_action",
                    "reason": (
                        "proposal is informational — no sandbox execution needed"
                    ),
                    "suggested_action": suggested,
                }
            )
        )
        return 0

    try:
        action_type = ActionType(suggested["action_type"])
    except Exception as exc:
        print(f"error: bad action_type {suggested.get('action_type')!r}: {exc}")
        return 2

    env = _resolve_env(args)
    _banner(env)
    a = ActionSystem(verbose=args.verbose, env=env)

    action = a.propose(
        action_type=action_type,
        target=str(suggested.get("target", "")),
        payload=dict(suggested.get("payload") or {}),
        reason=(
            f"stage proposal {args.proposal_id}: "
            f"{target_prop.get('reason', '')[:140]}"
        ),
    )
    result = a.execute(action, dry_run=args.dry_run, approve=args.approve)

    diff = _diff_workspace(env) if not args.dry_run else {
        "added": [],
        "modified": [],
        "count": 0,
    }

    report = {
        "proposal_id": args.proposal_id,
        "proposal_kind": target_prop.get("kind"),
        "sandbox": env.label,
        "action": {
            "id": action.id,
            "type": action.type.value,
            "target": action.target,
            "risk": action.risk_level.value,
            "requires_approval": action.requires_approval,
        },
        "result": {
            "status": result.status.value,
            "output": (result.output or "")[:400],
            "error": result.error,
            "duration_seconds": result.duration_seconds,
        },
        "diff_preview": diff,
        "verdict": (
            "ready_to_apply"
            if result.status.value == "succeeded" and not result.error
            else "blocked"
        ),
        "staged_at": datetime.now(timezone.utc).isoformat(),
    }
    # Write the report into the sandbox so the operator can pick it up.
    report_path = env.state_dir / f"proposal_staging_{args.proposal_id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_dumps(report), encoding="utf-8")

    print(_dumps(report))
    print(f"\n[sandbox] staging report: {report_path}")
    return 0 if report["verdict"] == "ready_to_apply" else 1


# ─── Command: list / diff / clean / inspect ────────────────────────────────


def _cmd_list(args: argparse.Namespace) -> int:
    rows = _list_sandboxes()
    if not rows:
        print("no sandboxes or playgrounds yet")
        return 0
    for r in rows:
        print(
            f"  [{r['mode']:10s}] {r['name']:40s} "
            f"{r['size_mb']:6.2f} MiB  created={r.get('created_at') or '?'}"
        )
    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    env = _load_sandbox_by_name(args.name)
    if env is None:
        print(f"no sandbox named {args.name!r}")
        return 2
    _banner(env)
    report = _diff_workspace(env)
    print(_dumps(report))
    return 0


def _cmd_clean(args: argparse.Namespace) -> int:
    env = _load_sandbox_by_name(args.name)
    if env is None:
        print(f"no sandbox named {args.name!r}")
        return 2
    if not args.yes:
        print(
            f"refusing to clean {env.root} without --yes (sandbox cleanup "
            "is destructive)"
        )
        return 2
    env.cleanup()
    print(f"cleaned {env.root}")
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    env = _load_sandbox_by_name(args.name)
    if env is None:
        print(f"no sandbox named {args.name!r}")
        return 2
    _banner(env)

    def _tail(p: Path, n: int = 5) -> list[dict[str, Any]]:
        if not p.exists():
            return []
        out: list[dict[str, Any]] = []
        for line in p.read_text().splitlines()[-n:]:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
        return out

    report = {
        "env": env.to_dict(),
        "tail": {
            "actions": _tail(env.action_log_path),
            "workflows": _tail(env.workflow_log_path),
            "orchestrator": _tail(env.orchestrator_log_path),
        },
        "workspace_diff": _diff_workspace(env),
        "state_files": [
            p.name for p in env.state_dir.rglob("*.json")
        ] if env.state_dir.exists() else [],
    }
    print(_dumps(report))
    return 0


# ─── CLI wiring ─────────────────────────────────────────────────────────────


def _add_env_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--sandbox",
        help="reuse a named sandbox (default: create a new one)",
    )
    p.add_argument(
        "--playground",
        action="store_true",
        help="use an ephemeral playground instead of a sandbox",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="sandbox_runner",
        description="EOS AI OS sandbox runner — safe experimentation layer.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # run ..........................................................
    p_run = sub.add_parser("run", help="run a workflow or action in a sandbox")
    run_sub = p_run.add_subparsers(dest="run_cmd", required=True)

    p_run_wf = run_sub.add_parser("workflow", help="run a workflow")
    p_run_wf.add_argument("name", help="workflow builder name (e.g. research)")
    p_run_wf.add_argument("--goal", default="sandbox test")
    p_run_wf.add_argument("--target", default="")
    p_run_wf.add_argument("--dry-run", action="store_true")
    p_run_wf.add_argument("-v", "--verbose", action="store_true")
    _add_env_flags(p_run_wf)
    p_run_wf.set_defaults(func=_cmd_run_workflow)

    p_run_act = run_sub.add_parser("action", help="run a single action")
    p_run_act.add_argument(
        "type",
        choices=[
            "edit-file",
            "write-file",
            "delete-file",
            "run-script",
            "run-command",
            "query-graph",
        ],
    )
    p_run_act.add_argument("--target", default="")
    p_run_act.add_argument("--content")
    p_run_act.add_argument("--content-file")
    p_run_act.add_argument("--command")
    p_run_act.add_argument("--script-args", nargs="*", default=[])
    p_run_act.add_argument("--query", default="dependents")
    p_run_act.add_argument("--reason", default="")
    p_run_act.add_argument("--dry-run", action="store_true")
    p_run_act.add_argument("--approve", action="store_true")
    p_run_act.add_argument("-v", "--verbose", action="store_true")
    _add_env_flags(p_run_act)
    p_run_act.set_defaults(func=_cmd_run_action)

    # orchestrator-tick ............................................
    p_orch = sub.add_parser(
        "orchestrator-tick", help="simulate one orchestrator tick"
    )
    p_orch.add_argument("-v", "--verbose", action="store_true")
    _add_env_flags(p_orch)
    p_orch.set_defaults(func=_cmd_orchestrator_tick)

    # playground ...................................................
    p_play = sub.add_parser(
        "playground", help="create a lightweight playground env"
    )
    p_play.add_argument("--name", default=None)
    p_play.add_argument(
        "--ephemeral",
        action="store_true",
        help="delete the playground tree immediately (smoke-test only)",
    )
    p_play.set_defaults(func=_cmd_playground)

    # replay .......................................................
    p_rep = sub.add_parser("replay", help="replay a past workflow in a sandbox")
    p_rep.add_argument("workflow_id")
    p_rep.add_argument("--dry-run", action="store_true")
    p_rep.add_argument("-v", "--verbose", action="store_true")
    _add_env_flags(p_rep)
    p_rep.set_defaults(func=_cmd_replay)

    # stage ........................................................
    p_stage = sub.add_parser(
        "stage", help="stage an optimizer proposal in a sandbox"
    )
    p_stage.add_argument("proposal_id")
    p_stage.add_argument("--approve", action="store_true")
    p_stage.add_argument("--dry-run", action="store_true")
    p_stage.add_argument("-v", "--verbose", action="store_true")
    _add_env_flags(p_stage)
    p_stage.set_defaults(func=_cmd_stage)

    # list / diff / clean / inspect ................................
    p_list = sub.add_parser("list", help="list existing sandboxes")
    p_list.set_defaults(func=_cmd_list)

    p_diff = sub.add_parser(
        "diff", help="diff a sandbox workspace against production"
    )
    p_diff.add_argument("name")
    p_diff.set_defaults(func=_cmd_diff)

    p_clean = sub.add_parser("clean", help="delete a sandbox tree")
    p_clean.add_argument("name")
    p_clean.add_argument(
        "--yes",
        action="store_true",
        help="required confirmation flag",
    )
    p_clean.set_defaults(func=_cmd_clean)

    p_inspect = sub.add_parser(
        "inspect", help="show logs + state summary for a sandbox"
    )
    p_inspect.add_argument("name")
    p_inspect.set_defaults(func=_cmd_inspect)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
