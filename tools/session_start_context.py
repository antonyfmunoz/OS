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

EAGAIN resilience: after /clear, the CC harness may spawn this
subprocess before the stdout pipe is fully ready. All output is
buffered and flushed with retry to tolerate transient EAGAIN/EWOULDBLOCK.
"""

import sys
import os
import errno
import signal
import subprocess
import fcntl
import time
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, "/opt/OS")
PDT = ZoneInfo("America/Los_Angeles")

# ─── EAGAIN-resilient output ────────────────────────────────────────────────
_MAX_WRITE_RETRIES = 10
_WRITE_RETRY_INTERVAL = 0.15  # 150ms between retries, ~1.5s total max


def _safe_write(text: str) -> bool:
    """Write to stdout with bounded retry on EAGAIN/EWOULDBLOCK.

    Returns True on success, False if pipe never became ready.
    Real errors (EPIPE, EBADF, etc.) are raised immediately.
    """
    for attempt in range(_MAX_WRITE_RETRIES):
        try:
            sys.stdout.write(text)
            sys.stdout.flush()
            return True
        except OSError as e:
            if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                # Pipe not ready — transient, retry
                _log_hook_event("startup_hook_retrying_eagain", attempt=attempt + 1)
                time.sleep(_WRITE_RETRY_INTERVAL)
                continue
            # Real I/O error — propagate
            raise
        except BrokenPipeError:
            # Parent closed the read end — nothing we can do
            return False
    # Exhausted retries — pipe never became ready
    _log_hook_event("startup_hook_not_ready")
    return False


def _log_hook_event(event: str, **kwargs) -> None:
    """Log hook lifecycle events to file (never stdout — that's for CC context)."""
    try:
        os.makedirs("/opt/OS/logs", exist_ok=True)
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        line = f"{datetime.now(PDT).isoformat()} {event} {extra}\n"
        with open("/opt/OS/logs/session_hook.log", "a") as f:
            f.write(line)
    except Exception:
        pass  # Logging failure must never break the hook


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
    try:
        result = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip().split()[0] if result.stdout else "unknown"
    except Exception:
        return "unknown"


def check_version_change(current: str) -> bool:
    """Returns True if version changed."""
    version_file = "/opt/OS/.claude/last_cc_version"
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

        load_dotenv("/opt/OS/umh/.env")
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

        load_dotenv("/opt/OS/umh/.env")
        from umh.environments.system_context import load_context_from_env

        ctx = load_context_from_env()
        return getattr(ctx, "stage", "unknown")
    except Exception:
        return "unknown"


def get_system_health_summary() -> str:
    """Quick system health for SessionStart context."""
    try:
        from umh.runtime_engine.system_health import get_system_health

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
            "!! CC VERSION CHANGED — "
            "run /check-cc-updates before "
            "any infrastructure work"
        )

    if pending > 0:
        context_lines.append(
            f"{pending} pending tasks — run /constraint-check to prioritize"
        )

    # Buffer all output, then flush once with EAGAIN resilience.
    # After /clear, the CC harness pipe may not be ready immediately.
    output = "\n".join(context_lines) + "\n"

    # Start Remote Control for phone access
    # Boris: "Enable Remote Control for all sessions"
    try:
        rc_result = subprocess.run(
            ["claude", "remote-control", "--background"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if rc_result.returncode == 0:
            output += "[Remote] Control active — access from iPhone at claude.ai\n"
    except Exception:
        pass  # Remote Control unavailable

    # Single buffered write with retry — tolerates EAGAIN
    if _safe_write(output):
        _log_hook_event("startup_hook_succeeded")
    # If _safe_write returned False, event was already logged

    # Also log to sessions file
    try:
        os.makedirs("/opt/OS/logs", exist_ok=True)
        with open("/opt/OS/logs/sessions.log", "a") as f:
            f.write(
                f"{now.isoformat()} CC:{cc_version} Stage:{stage} Pending:{pending}\n"
            )
    except Exception:
        pass


if __name__ == "__main__":
    lock = _acquire_lock()
    if lock is None:
        # Another instance already running — exit silently
        sys.exit(0)
    try:
        main()
    except OSError as e:
        # Top-level guard: if stdout pipe fails entirely (EAGAIN, EPIPE),
        # exit cleanly so CC doesn't surface a hook error.
        if e.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EPIPE):
            _log_hook_event("startup_hook_pipe_failed", errno=e.errno)
            sys.exit(0)
        _log_hook_event("startup_hook_failed_real_error", error=str(e))
        raise
    except BrokenPipeError:
        _log_hook_event("startup_hook_pipe_broken")
        sys.exit(0)
    except Exception as e:
        _log_hook_event("startup_hook_failed_real_error", error=str(e))
        raise
    finally:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()
            os.unlink(_LOCKFILE)
        except Exception:
            pass
