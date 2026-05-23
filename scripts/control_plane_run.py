#!/usr/bin/env python3
"""control_plane_run.py — run a shell command or script through the Control Plane.

This is the reference integration for orchestration hooks. Instead of
calling subprocess directly, agents (and humans) should route meaningful
work through this entry point so every execution is validated, approved,
and logged.

Usage:
    python3 scripts/control_plane_run.py shell "echo hello from control plane"
    python3 scripts/control_plane_run.py script scripts/query_skills.py count
    python3 scripts/control_plane_run.py shell "ls /opt/OS" --agent developer --risk low
"""

from __future__ import annotations

import argparse
import json
import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from substrate.control_plane.actions.control_plane import run_action, log_decision


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)

    s = sub.add_parser("shell", help="Run a shell command")
    s.add_argument("command", help="Shell command to run")

    r = sub.add_parser("script", help="Run a .py or .sh script")
    r.add_argument("path", help="Absolute or relative script path")
    r.add_argument("args", nargs="*", help="Script args")

    for sp in (s, r):
        sp.add_argument("--agent", default="cli")
        sp.add_argument("--risk", default="low", choices=("low", "medium", "high"))
        sp.add_argument(
            "--approve",
            action="store_true",
            help="Grant explicit approval for medium/high risk",
        )
        sp.add_argument(
            "--consult-tme",
            action="store_true",
            help="Query the Tool Mastery Engine before executing",
        )
        sp.add_argument("--description", default="")

    args = p.parse_args()

    if args.mode == "shell":
        action = run_action(
            type="shell_command",
            description=args.description or f"shell: {args.command}",
            inputs={"command": args.command},
            risk_level=args.risk,
            source_agent=args.agent,
            explicit_approval=args.approve,
            consult_tme=args.consult_tme,
        )
    else:
        action = run_action(
            type="run_script",
            description=args.description or f"script: {args.path}",
            inputs={"path": args.path, "args": args.args},
            risk_level=args.risk,
            source_agent=args.agent,
            explicit_approval=args.approve,
            consult_tme=args.consult_tme,
        )

    # Capture why we ran it (even if the 'why' is just 'CLI invocation').
    log_decision(
        context=f"Control Plane CLI invocation by {args.agent}",
        options_considered=["direct subprocess", "Control Plane"],
        chosen_option="Control Plane",
        reasoning="Route all meaningful actions through the Control Plane "
        "so they are validated, approved, and logged.",
        related_action_id=action.id,
        source_agent=args.agent,
    )

    print(
        json.dumps(
            {
                "id": action.id,
                "status": action.status,
                "validation": action.validation,
                "approval": action.approval,
                "result": action.result,
            },
            indent=2,
            default=str,
        )
    )

    return 0 if action.status == "executed" else 1


if __name__ == "__main__":
    sys.exit(main())
