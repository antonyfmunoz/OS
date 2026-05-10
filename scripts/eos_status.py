#!/usr/bin/env python3
"""
EOS Operator Status — single inspectable surface.

Shows everything an operator needs to trust the substrate at a glance:
- provider health (with reasons)
- Docker service status
- Ollama state
- recent scheduled-job results (last 24h)
- active locks
- recent provider failures from logs

Run:
    python3 /opt/OS/scripts/eos_status.py
"""

import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
from dotenv import load_dotenv
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'eos_ai', '.env'))

from eos_ai.provider_health import check_all  # noqa: E402

LOG_DIR = Path("/opt/OS/logs")


def section(title: str) -> None:
    print(f"\n── {title} " + "─" * (60 - len(title)))


def docker_status() -> str:
    try:
        out = subprocess.check_output(
            ["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Status}}"],
            text=True, timeout=5,
        )
        intended = {"os-discord", "os-bot", "os-monitor", "os-webhook"}
        rows = []
        seen = set()
        for line in out.strip().split("\n"):
            if not line.strip():
                continue
            name, status = line.split("\t", 1)
            seen.add(name)
            mark = "✓" if status.startswith("Up") else "✗"
            rows.append(f"  {mark} {name}: {status}")
        for missing in intended - seen:
            rows.append(f"  ✗ {missing}: NOT FOUND")
        return "\n".join(rows)
    except Exception as e:
        return f"  docker query failed: {e}"


def cron_recent_runs() -> str:
    """Show last successful run + last error per LLM-dependent job."""
    targets = {
        "morning_intel": "morning_intel.log",
        "midday_checkin": "midday.log",
        "eod_sync": "eod_sync.log",
        "noshow_detector": "noshow.log",
        "call_prep": "call_prep.log",
        "nightly_consolidation": "nightly_consolidation.log",
        "post_meeting": "post_meeting.log",
        "notion_sync": "notion_sync.log",
    }
    rows = []
    for name, fname in targets.items():
        p = LOG_DIR / fname
        if not p.exists():
            rows.append(f"  • {name}: no log")
            continue
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            age = datetime.now() - mtime
            age_str = f"{int(age.total_seconds() / 60)}m ago" if age < timedelta(hours=2) \
                else f"{int(age.total_seconds() / 3600)}h ago"
            tail_lines = subprocess.check_output(
                ["tail", "-3", str(p)], text=True, timeout=2
            ).strip().split("\n")
            last_line = tail_lines[-1] if tail_lines else "(empty)"
            err_marker = "✗" if any(
                k in last_line.lower() for k in ("error", "failed", "traceback", "skip")
            ) else "✓"
            rows.append(f"  {err_marker} {name} ({age_str}): {last_line[:80]}")
        except Exception as e:
            rows.append(f"  ? {name}: {e}")
    return "\n".join(rows)


def active_locks() -> str:
    try:
        rows = []
        for p in Path("/tmp").glob("eos_*.lock"):
            try:
                age = datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)
                rows.append(f"  • {p.name} (age {int(age.total_seconds() / 60)}m)")
            except Exception:
                pass
        return "\n".join(rows) if rows else "  (none)"
    except Exception as e:
        return f"  lock query failed: {e}"


def recent_provider_errors() -> str:
    """Pull the last few provider error lines from orchestrator log."""
    log = LOG_DIR / "orchestrator.log"
    if not log.exists():
        return "  (no orchestrator log)"
    try:
        out = subprocess.check_output(
            ["tail", "-200", str(log)], text=True, timeout=3
        )
        lines = [
            line for line in out.split("\n")
            if any(k in line for k in (
                "ModelRouter] Anthropic", "ModelRouter] Gemini",
                "ModelRouter] Ollama", "ALL PROVIDERS",
            ))
        ]
        if not lines:
            return "  (no recent provider errors)"
        return "\n".join(f"  {line[:100]}" for line in lines[-5:])
    except Exception as e:
        return f"  log read failed: {e}"


def main() -> int:
    print(f"\n═══ EOS Status — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ═══")

    section("Provider Health")
    h = check_all()
    print(h.summary())
    if not h.any_healthy:
        print("\n  ⚠️  NO HEALTHY LLM PROVIDERS — substrate is degraded")
    elif not h.any_cloud_healthy:
        print("\n  ⚠️  ONLY OLLAMA AVAILABLE — cloud providers all down")

    section("Docker Services")
    print(docker_status())

    section("Recent Scheduled Jobs (LLM-dependent)")
    print(cron_recent_runs())

    section("Active Locks")
    print(active_locks())

    section("Recent Provider Errors")
    print(recent_provider_errors())

    print()
    return 0 if h.any_healthy else 2


if __name__ == "__main__":
    sys.exit(main())
