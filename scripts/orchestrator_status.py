#!/usr/bin/env python3
"""orchestrator_status.py — operator-friendly snapshot of the Control Plane.

Prints five sections in a compact human-readable format:

  1. Pending signals (per signal name + count + oldest emission age)
  2. Deferred queue summary (count, oldest, by risk)
  3. Recent workflows (last run per registered workflow)
  4. Recent failures (today's execution log, grouped by action id)
  5. Loop activity (last orchestrator cycle report if available)

Intentionally read-only. Nothing here mutates state — no actions are
run, no signals emitted, no files written. Safe to call from cron or
a tmux status bar.

Usage:
    python3 /opt/OS/scripts/orchestrator_status.py
    python3 /opt/OS/scripts/orchestrator_status.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from core.action_system.deferred import list_deferred  # noqa: E402
from core.action_system.logging import (  # noqa: E402
    DECISION_LOG_DIR,
    EXECUTION_LOG_DIR,
)
from core.orchestrator.loop import HEARTBEAT_PATH  # noqa: E402
from core.orchestrator.orchestrator import (  # noqa: E402
    STATE_PATH,
    default_orchestrator,
)

# Loop should tick at least once per 5 minutes (cron: */5). Flag as
# stale at 3x expected cadence to tolerate a missed run without
# screaming.
LOOP_STALE_THRESHOLD_S = 15 * 60
from core.orchestrator.signals import (  # noqa: E402
    get_handlers,
    list_pending,
    list_signals,
)
from core.orchestrator.workflows import register_default_workflows  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _age_seconds(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        when = datetime.fromisoformat(iso)
    except ValueError:
        return None
    return int((_now() - when).total_seconds())


def _fmt_age(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h{(seconds % 3600) // 60}m"
    return f"{seconds // 86400}d{(seconds % 86400) // 3600}h"


def _today_execution_log() -> str:
    day = _now().strftime("%Y-%m-%d")
    return os.path.join(EXECUTION_LOG_DIR, f"{day}-execution.jsonl")


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def pending_signals_summary() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name in list_signals():
        pending = list_pending(name)
        if not pending:
            continue
        oldest = min(
            (_age_seconds(e.emitted_at) or 0 for e in pending),
            default=None,
        )
        out.append(
            {
                "signal": name,
                "pending": len(pending),
                "handlers": get_handlers(name),
                "oldest_age_seconds": oldest,
            }
        )
    return out


def deferred_summary() -> dict[str, Any]:
    entries = list_deferred()
    by_risk: dict[str, int] = {}
    oldest_age: int | None = None
    oldest_id: str | None = None
    for e in entries:
        risk = e.get("risk_level") or "unknown"
        by_risk[risk] = by_risk.get(risk, 0) + 1
        age = _age_seconds(e.get("deferred_at"))
        if age is not None and (oldest_age is None or age > oldest_age):
            oldest_age = age
            oldest_id = e.get("id")
    return {
        "count": len(entries),
        "by_risk": by_risk,
        "oldest_action_id": oldest_id,
        "oldest_age_seconds": oldest_age,
    }


def recent_workflows() -> list[dict[str, Any]]:
    orch = default_orchestrator()
    register_default_workflows(orch)
    rows: list[dict[str, Any]] = []
    for name in orch.list_workflows():
        rec = orch.get_record(name)
        if rec is None:
            continue
        rows.append(
            {
                "name": name,
                "last_run_at": rec.last_run_at,
                "last_status": rec.last_status,
                "last_duration_s": rec.last_duration_s,
                "total_runs": rec.total_runs,
                "total_failures": rec.total_failures,
                "age_seconds": _age_seconds(rec.last_run_at),
            }
        )
    # Most recently run first, never-run last.
    rows.sort(
        key=lambda r: (
            r["last_run_at"] is None,
            -(r["age_seconds"] or 10**9),
        )
    )
    return rows


def recent_failures(limit: int = 20) -> list[dict[str, Any]]:
    path = _today_execution_log()
    if not os.path.isfile(path):
        return []
    try:
        with open(path) as f:
            lines = f.readlines()
    except OSError:
        return []
    by_id: dict[str, dict[str, Any]] = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        action = record.get("action") or {}
        if action.get("status") != "failed":
            continue
        aid = action.get("id")
        if not aid:
            continue
        # Keep the most recent record per action id.
        by_id[aid] = {
            "id": aid,
            "type": action.get("type"),
            "risk_level": action.get("risk_level"),
            "source_agent": action.get("source_agent"),
            "description": action.get("description"),
            "logged_at": record.get("logged_at"),
            "returncode": (action.get("result") or {}).get("returncode"),
        }
    out = list(by_id.values())
    out.sort(key=lambda r: r["logged_at"] or "", reverse=True)
    return out[:limit]


def loop_heartbeat() -> dict[str, Any]:
    """Read the orchestrator heartbeat written by core.orchestrator.loop.

    Returns a dict with `present`, `alive`, `age_seconds`, plus the
    raw heartbeat payload if it exists. `alive` is True when the
    heartbeat was updated inside LOOP_STALE_THRESHOLD_S.
    """
    if not os.path.isfile(HEARTBEAT_PATH):
        return {"present": False, "alive": False, "age_seconds": None}
    try:
        with open(HEARTBEAT_PATH) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return {
            "present": True,
            "alive": False,
            "age_seconds": None,
            "error": f"{type(e).__name__}: {e}",
        }
    age = _age_seconds(data.get("last_ran_at"))
    return {
        "present": True,
        "alive": age is not None and age <= LOOP_STALE_THRESHOLD_S,
        "age_seconds": age,
        "payload": data,
    }


def loop_activity() -> dict[str, Any]:
    """Return summary from today's decision log of orchestrator.loop entries."""
    day = _now().strftime("%Y-%m-%d")
    path = os.path.join(DECISION_LOG_DIR, f"{day}-decisions.jsonl")
    counts: dict[str, int] = {}
    last_loop_ts: str | None = None
    if not os.path.isfile(path):
        return {
            "decisions_today": counts,
            "last_loop_decision_at": last_loop_ts,
            "orchestrator_state_path": STATE_PATH,
        }
    try:
        with open(path) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ctx = rec.get("context", "")
                if not (
                    ctx.startswith("orchestrator.loop")
                    or ctx.startswith("orchestrator.handler")
                ):
                    continue
                counts[ctx] = counts.get(ctx, 0) + 1
                ts = rec.get("timestamp")
                if ts and (last_loop_ts is None or ts > last_loop_ts):
                    last_loop_ts = ts
    except OSError:
        pass
    return {
        "decisions_today": counts,
        "last_loop_decision_at": last_loop_ts,
        "last_loop_age_seconds": _age_seconds(last_loop_ts),
        "orchestrator_state_path": STATE_PATH,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _hdr(title: str) -> str:
    return f"\n== {title} ==".ljust(60, " ")


def render_text(snapshot: dict[str, Any]) -> str:
    out: list[str] = []
    out.append(f"EOS Orchestrator Status — {snapshot['generated_at']}")

    hb = snapshot["heartbeat"]
    if not hb["present"]:
        out.append("Loop: UNKNOWN (no heartbeat file yet)")
    elif hb["alive"]:
        p = hb.get("payload", {})
        out.append(
            f"Loop: alive  last={_fmt_age(hb['age_seconds'])} ago  "
            f"v{p.get('loop_version', '?')}  "
            f"signals={p.get('signals_processed', 0)} "
            f"fails={p.get('failures_detected', 0)} "
            f"stale_deferred={p.get('deferred_stale_count', 0)}"
        )
    else:
        out.append(
            f"Loop: STALE  last={_fmt_age(hb['age_seconds'])} ago  "
            f"(threshold {LOOP_STALE_THRESHOLD_S}s)"
        )

    out.append(_hdr("Pending signals"))
    signals = snapshot["pending_signals"]
    if not signals:
        out.append("  (none)")
    else:
        for s in signals:
            handlers = ", ".join(s["handlers"]) or "(no handlers)"
            out.append(
                f"  {s['signal']:<25} pending={s['pending']:>3}  "
                f"oldest={_fmt_age(s['oldest_age_seconds'])}  → {handlers}"
            )

    out.append(_hdr("Deferred queue"))
    d = snapshot["deferred"]
    if d["count"] == 0:
        out.append("  (empty)")
    else:
        by_risk = ", ".join(f"{k}={v}" for k, v in sorted(d["by_risk"].items()))
        out.append(f"  total={d['count']}  [{by_risk}]")
        if d["oldest_action_id"]:
            out.append(
                f"  oldest: {d['oldest_action_id']}  "
                f"age={_fmt_age(d['oldest_age_seconds'])}"
            )

    out.append(_hdr("Recent workflows"))
    for row in snapshot["workflows"]:
        status = row["last_status"] or "—"
        out.append(
            f"  {row['name']:<30} {status:<10} "
            f"runs={row['total_runs']:<4} fails={row['total_failures']:<3} "
            f"last={_fmt_age(row['age_seconds'])}"
        )

    out.append(_hdr("Recent failures (today)"))
    failures = snapshot["failures"]
    if not failures:
        out.append("  (none)")
    else:
        for f in failures:
            out.append(
                f"  {f['id'][:8]}  {f['type']:<15} {f['risk_level']:<7} "
                f"rc={f['returncode']}  {f['description'][:40]}"
            )

    out.append(_hdr("Loop activity (today)"))
    la = snapshot["loop_activity"]
    if not la["decisions_today"]:
        out.append("  (no loop/handler decisions today)")
    else:
        for ctx, n in sorted(la["decisions_today"].items()):
            out.append(f"  {ctx:<42} {n}")
        out.append(
            f"  last decision: {la['last_loop_decision_at']} "
            f"({_fmt_age(la['last_loop_age_seconds'])} ago)"
        )

    return "\n".join(out) + "\n"


def build_snapshot() -> dict[str, Any]:
    return {
        "generated_at": _now().isoformat(),
        "heartbeat": loop_heartbeat(),
        "pending_signals": pending_signals_summary(),
        "deferred": deferred_summary(),
        "workflows": recent_workflows(),
        "failures": recent_failures(),
        "loop_activity": loop_activity(),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="EOS Orchestrator status snapshot")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = p.parse_args()
    snap = build_snapshot()
    if args.json:
        print(json.dumps(snap, indent=2, default=str))
    else:
        print(render_text(snap))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
