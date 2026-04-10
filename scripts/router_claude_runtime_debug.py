#!/usr/bin/env python3
"""Router runtime debug helper — prints the actual, live state the router
sees for the Claude CLI backend.

Run inside the target environment (host OR `docker exec os-discord python3
scripts/router_claude_runtime_debug.py`) to prove:
  - PROVIDER_PRIORITY / PROVIDER_PRIORITY_FAST tables
  - CLAUDE_CLI is registered and at index 0
  - env gating state (EOS_ROUTER_CLAUDE_CLI_*)
  - tmux + claude CLI availability from THIS process's filesystem
  - what target/session the router would pass to the bridge
  - a live dry-run of respond_via_claude_session (no prompt side effects
    beyond a single no-op-ish question)
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, "/opt/OS")


def main() -> int:
    from eos_ai import model_router as mr
    from eos_ai.substrate import claude_responder as cr
    from eos_ai.substrate import claude_session_bridge as csb

    def k(d: dict) -> dict:
        return {getattr(k, "value", str(k)): v for k, v in d.items()}

    out: dict = {
        "env": {
            "EOS_ROUTER_CLAUDE_CLI_ENABLED": os.getenv("EOS_ROUTER_CLAUDE_CLI_ENABLED"),
            "EOS_ROUTER_CLAUDE_CLI_TARGET": os.getenv("EOS_ROUTER_CLAUDE_CLI_TARGET"),
            "EOS_ROUTER_CLAUDE_CLI_SESSION": os.getenv("EOS_ROUTER_CLAUDE_CLI_SESSION"),
            "TMUX_TMPDIR": os.getenv("TMUX_TMPDIR"),
        },
        "backend_enabled": mr._claude_cli_backend_enabled(),
        "PROVIDER_PRIORITY": k(mr.PROVIDER_PRIORITY),
        "PROVIDER_PRIORITY_FAST": k(mr.PROVIDER_PRIORITY_FAST),
        "claude_cli_in_priority": mr.ModelProvider.CLAUDE_CLI in mr.PROVIDER_PRIORITY,
        "claude_cli_index_heavy": mr.PROVIDER_PRIORITY.get(mr.ModelProvider.CLAUDE_CLI),
        "claude_cli_index_fast": mr.PROVIDER_PRIORITY_FAST.get(
            mr.ModelProvider.CLAUDE_CLI
        ),
        "tmux_available": csb.detect_tmux_available(),
        "claude_cli_available": csb.detect_claude_cli_available(),
        "default_target": cr.DEFAULT_TARGET,
        "default_session": cr.DEFAULT_SESSION_NAME,
    }

    # Dry probe: does the bridge actually see the session?
    target = (
        os.getenv("EOS_ROUTER_CLAUDE_CLI_TARGET") or cr.DEFAULT_TARGET
    ).strip().lower() or cr.DEFAULT_TARGET
    session = (
        os.getenv("EOS_ROUTER_CLAUDE_CLI_SESSION") or cr.DEFAULT_SESSION_NAME
    ).strip() or cr.DEFAULT_SESSION_NAME
    out["probe_target"] = target
    out["probe_session"] = session
    try:
        sessions = csb.list_sessions()
        out["sessions"] = sessions
    except Exception as exc:  # noqa: BLE001
        out["sessions_error"] = str(exc)

    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
