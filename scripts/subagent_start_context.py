#!/usr/bin/env python3
"""
SubagentStart hook.
Injects agent-type-specific context when
a CC native subagent starts.
"""
import sys
import os
import json

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    agent_type = hook_input.get(
        'agent_type', ''
    ).lower()

    context = []

    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
        from substrate.state.context.context import (
            load_context_from_env
        )
        ctx = load_context_from_env()

        context.append(
            f"[Venture Context]\n"
            f"Stage: {getattr(ctx, 'stage', '?')}\n"
            f"North Star: "
            f"{getattr(ctx, 'north_star', '?')}\n"
            f"Binding Constraint: "
            f"{getattr(ctx, 'binding_constraint', 'leads')}\n"
            f"Active Venture: "
            f"{getattr(ctx, 'active_venture_id', '?')}\n"
        )

        if any(x in agent_type for x in
               ['ea', 'executive']):
            try:
                from substrate.state.storage.db import get_conn
                with get_conn() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM tasks "
                        "WHERE status='pending'"
                    )
                    pending = cur.fetchone()["count"]
                    context.append(
                        f"[EA Context]\n"
                        f"Pending tasks: {pending}\n"
                    )
            except Exception:
                pass

    except Exception as e:
        context.append(
            f"[Context load error: {e}]"
        )

    if context:
        print('\n'.join(context))


if __name__ == '__main__':
    main()
