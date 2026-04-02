#!/usr/bin/env python3
"""
SessionStart hook.
Injects dynamic context into every CC session.
Boris: "Dynamically load context each time
you start Claude (SessionStart)"

Outputs to stdout — CC adds it to context.
Detects CC version change — triggers update alert.
"""
import sys
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, '/opt/OS')
PDT = ZoneInfo('America/Los_Angeles')


def get_cc_version() -> str:
    try:
        result = subprocess.run(
            ['claude', '--version'],
            capture_output=True, text=True,
            timeout=5
        )
        return result.stdout.strip().split()[0] \
            if result.stdout else 'unknown'
    except Exception:
        return 'unknown'


def check_version_change(current: str) -> bool:
    """Returns True if version changed."""
    version_file = '/opt/OS/.claude/last_cc_version'
    try:
        if os.path.exists(version_file):
            with open(version_file) as f:
                last = f.read().strip()
            if last != current:
                with open(version_file, 'w') as f:
                    f.write(current)
                return True
        else:
            with open(version_file, 'w') as f:
                f.write(current)
    except Exception:
        pass
    return False


def get_pending_tasks() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv('/opt/OS/eos_ai/.env')
        import psycopg2
        db_url = os.getenv('DATABASE_URL', '')
        if not db_url:
            return 0
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE status = 'pending'
        """)
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def get_venture_stage() -> str:
    try:
        from dotenv import load_dotenv
        load_dotenv('/opt/OS/eos_ai/.env')
        from eos_ai.context import (
            load_context_from_env
        )
        ctx = load_context_from_env()
        return getattr(ctx, 'stage', 'unknown')
    except Exception:
        return 'unknown'


def main():
    now = datetime.now(PDT)
    cc_version = get_cc_version()
    version_changed = check_version_change(
        cc_version
    )
    pending = get_pending_tasks()
    stage = get_venture_stage()

    context_lines = [
        f"[EOS Session Context — "
        f"{now.strftime('%a %b %d %I:%M %p')} PDT]",
        f"CC Version: {cc_version}",
        f"Venture Stage: {stage}",
        f"Pending Tasks: {pending}",
    ]

    if version_changed:
        context_lines.append(
            "!! CC VERSION CHANGED — "
            "run /check-cc-updates before "
            "any infrastructure work"
        )

    if pending > 0:
        context_lines.append(
            f"{pending} pending tasks — "
            "run /constraint-check to prioritize"
        )

    # Output to stdout — CC injects into context
    print('\n'.join(context_lines))

    # Also log to sessions file
    try:
        os.makedirs('/opt/OS/logs', exist_ok=True)
        with open('/opt/OS/logs/sessions.log', 'a') as f:
            f.write(
                f"{now.isoformat()} "
                f"CC:{cc_version} "
                f"Stage:{stage} "
                f"Pending:{pending}\n"
            )
    except Exception:
        pass


if __name__ == '__main__':
    main()
