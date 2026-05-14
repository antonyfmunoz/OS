#!/usr/bin/env python3
"""
SessionStart hook.
Injects dynamic context into every CC session.
Boris: "Dynamically load context each time
you start Claude (SessionStart)"

Outputs to stdout — CC adds it to context.
Detects CC version change — triggers update alert.

Singleton: only one instance runs at a time via lockfile.
Hard timeout: exits after 15s to prevent zombie accumulation.
"""

import sys
import os
import signal
import subprocess
import fcntl
from datetime import datetime
from zoneinfo import ZoneInfo
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
PDT = ZoneInfo("America/Los_Angeles")

# ─── Singleton + timeout guard ───────────────────────────────────────────────
_LOCKFILE = "/tmp/eos_session_start.lock"
_HARD_TIMEOUT = 15  # seconds — kill self if stuck


def _timeout_handler(signum, frame):
    """Hard kill on timeout — prevents zombie accumulation."""
    print("[EOS Session Context — timed out]")
    sys.exit(0)


signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm(_HARD_TIMEOUT)


def _acquire_lock():
    """Non-blocking lockfile. Returns file handle or None if another instance running."""
    try:
        fh = open(_LOCKFILE, "w")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fh.write(str(os.getpid()))
        fh.flush()
        return fh
    except (OSError, IOError):
        return None


def get_cc_version() -> str:
    pkg = "/usr/lib/node_modules/@anthropic-ai/claude-code/package.json"
    try:
        import json

        with open(pkg) as f:
            return json.load(f).get("version", "unknown")
    except Exception:
        pass
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
        return result.stdout.strip().split()[0] if result.stdout else "unknown"
    except Exception:
        return "unknown"


def check_version_change(current: str) -> bool:
    """Returns True if version changed."""
    version_file = f"{_ROOT}/.claude/last_cc_version"
    try:
        if os.path.exists(version_file):
            with open(version_file) as f:
                last = f.read().strip()
            if last != current:
                with open(version_file, "w") as f:
                    f.write(current)
                return True
        else:
            with open(version_file, "w") as f:
                f.write(current)
    except Exception:
        pass
    return False


def get_pending_tasks() -> int:
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
        import psycopg2

        db_url = os.getenv("DATABASE_URL", "")
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

        load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
        from state.context.context import load_context_from_env

        ctx = load_context_from_env()
        return getattr(ctx, "stage", "unknown")
    except Exception:
        return "unknown"


def get_system_health_summary() -> str:
    """Quick system health for SessionStart context."""
    try:
        from observability.health.system_health import get_system_health

        sh = get_system_health()
        return sh.system_check()
    except Exception as e:
        return f"System health: error ({e})"


def main():
    now = datetime.now(PDT)
    cc_version = get_cc_version()
    version_changed = check_version_change(cc_version)
    pending = get_pending_tasks()
    stage = get_venture_stage()
    health = get_system_health_summary()

    context_lines = [
        f"[EOS Session Context — {now.strftime('%a %b %d %I:%M %p')} PDT]",
        f"CC Version: {cc_version}",
        f"Venture Stage: {stage}",
        f"Pending Tasks: {pending}",
        f"System Health:\n{health}",
    ]

    if version_changed:
        context_lines.append(
            "!! CC VERSION CHANGED — run /check-cc-updates before any infrastructure work"
        )

    if pending > 0:
        context_lines.append(f"{pending} pending tasks — run /constraint-check to prioritize")

    # Output to stdout — CC injects into context
    print("\n".join(context_lines))

    # Also log to sessions file
    try:
        os.makedirs(f"{_ROOT}/logs", exist_ok=True)
        with open(f"{_ROOT}/logs/sessions.log", "a") as f:
            f.write(f"{now.isoformat()} CC:{cc_version} Stage:{stage} Pending:{pending}\n")
    except Exception:
        pass

    # Start Remote Control for phone access
    # Boris: "Enable Remote Control for all sessions"
    try:
        rc_result = subprocess.run(
            ["npx", "@anthropic-ai/claude-code", "remote-control", "--background"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if rc_result.returncode == 0:
            print("[Remote] Control active — access from iPhone at claude.ai")
    except Exception:
        pass  # Remote Control unavailable

    # TME staleness flag (lightweight — no imports from _tme_common)
    try:
        import datetime
        import re as _re

        _tools_dir = f"{_ROOT}/skills/tools"
        _today = datetime.date.today()
        _stale = []
        _WINDOWS = {"fast": 14, "medium": 45, "stable": 90, "slow": 120}
        for _d in os.listdir(_tools_dir):
            _skill = os.path.join(_tools_dir, _d, "SKILL.md")
            if not os.path.isfile(_skill):
                continue
            with open(_skill) as _f:
                _head = _f.read(500)
            _lr = _re.search(r'last_researched:\s*["\']?(\d{4}-\d{2}-\d{2})', _head)
            _sc = _re.search(r'speed_category:\s*["\']?(\w+)', _head)
            if not _lr:
                continue
            _age = (_today - datetime.date.fromisoformat(_lr.group(1))).days
            _window = _WINDOWS.get(_sc.group(1) if _sc else "medium", 60)
            if _age > _window:
                _stale.append(_d)
        if _stale:
            print(
                f"[TME] {len(_stale)} stale tool skills: {' '.join(_stale[:5])}"
                f"{'...' if len(_stale) > 5 else ''}"
            )
    except Exception:
        pass  # TME check is best-effort — never block session start


if __name__ == "__main__":
    lock = _acquire_lock()
    if lock is None:
        # Another instance already running — exit silently
        sys.exit(0)
    try:
        main()
    finally:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()
            os.unlink(_LOCKFILE)
        except Exception:
            pass
