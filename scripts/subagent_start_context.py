#!/usr/bin/env python3
"""
SubagentStart hook.
Injects agent-type-specific context when
a CC native subagent starts.
"""
import sys
import os
import json

sys.path.insert(0, '/opt/OS')


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
        load_dotenv('/opt/OS/eos_ai/.env')
        from eos_ai.context import (
            load_context_from_env
        )
        ctx = load_context_from_env()

        if any(x in agent_type for x in
               ['ceo', 'lyfe', 'empyrean',
                'brand']):
            context.append(
                f"[Venture Context]\n"
                f"Stage: {getattr(ctx, 'stage', '?')}\n"
                f"North Star: "
                f"{getattr(ctx, 'north_star', '?')}\n"
                f"Binding Constraint: "
                f"{getattr(ctx, 'binding_constraint', 'leads')}\n"
            )

        elif 'research' in agent_type or \
             'researcher' in agent_type:
            context.append(
                "[Research Context]\n"
                "ICP: Men 18-25, fitness/self-improvement\n"
                "Primary channel: Instagram DMs\n"
                "Current offer: Initiate Arena $750/90-day\n"
            )

        elif 'ea' in agent_type or \
             'executive' in agent_type:
            import psycopg2
            try:
                conn = psycopg2.connect(
                    os.getenv('DATABASE_URL', '')
                )
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(*) FROM tasks "
                    "WHERE status='pending'"
                )
                pending = cur.fetchone()[0]
                conn.close()
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
