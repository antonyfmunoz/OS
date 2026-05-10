#!/usr/bin/env python3
"""
Stop hook handler.
Boris Cherny: exit 2 to keep Claude working.
EOS: conditional — check if current task
requires continuation before deciding.

Exit 0: allow Claude to stop (task done)
Exit 2: prevent stop (keep working)

Reads task state from Neon to determine
if active tasks are still pending.
Falls back to allow stop if DB unavailable.
"""
import sys
import os
import json

sys.path.insert(0, '/opt/OS')


def should_continue() -> bool:
    """
    Returns True if Claude should keep working.
    Returns False if Claude can stop.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv('/opt/OS/umh/.env')

        import psycopg2
        db_url = os.getenv('DATABASE_URL', '')
        if not db_url:
            return False

        conn = psycopg2.connect(db_url)
        cur = conn.cursor()

        # Check for tasks marked KEEP_RUNNING
        # or tasks created but not completed
        cur.execute("""
            SELECT COUNT(*) FROM tasks
            WHERE status IN ('in_progress', 'pending')
            AND created_at > NOW() - INTERVAL '2 hours'
            AND metadata->>'keep_running' = 'true'
        """)
        row = cur.fetchone()
        conn.close()

        return (row[0] if row else 0) > 0

    except Exception:
        # DB unavailable — allow stop
        return False


def main():
    # Read hook input from stdin if provided
    try:
        hook_input = json.load(sys.stdin)
        # Check if task explicitly marked
        stop_reason = hook_input.get(
            'stop_reason', ''
        )
        # If Claude stopped due to error
        # always allow
        if stop_reason in ('error', 'interrupt'):
            sys.exit(0)
    except Exception:
        pass

    if should_continue():
        # Exit 2 = prevent Claude from stopping
        print(
            '[Stop] Active tasks pending — '
            'continuing...',
            file=sys.stderr
        )
        sys.exit(2)
    else:
        # Exit 0 = allow stop
        print('[Stop] Session complete.')
        sys.exit(0)


if __name__ == '__main__':
    main()
