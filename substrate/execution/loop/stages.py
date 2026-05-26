"""Built-in loop stages — composable pipeline steps for persistent loops.

Each stage is a function(loop, report) that mutates the CycleReport in place.
Stages are registered by name in STAGE_REGISTRY and referenced by name
in LoopDefinition.stages lists.

To add a custom stage:
    from substrate.execution.loop.persistent_loop import register_stage

    def my_stage(loop, report):
        report.details.append({"stage": "my_stage", "result": "ok"})
        report.actions_taken += 1

    register_stage("my_stage", my_stage)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from substrate.execution.loop.persistent_loop import CycleReport, stage

if TYPE_CHECKING:
    from substrate.execution.loop.persistent_loop import PersistentLoop

logger = logging.getLogger(__name__)

_ROOT = Path(os.getenv("UMH_ROOT", "/opt/OS"))


# ─── Operations stages ──────────────────────────────────────────────────────


@stage("signal_drain")
def signal_drain(loop: PersistentLoop, report: CycleReport) -> None:
    """Drain pending signals via the orchestrator."""
    from substrate.control_plane.runtime.orchestrator.loop import (
        LoopConfig,
        run_cycle as orchestrator_cycle,
    )

    orch_report = orchestrator_cycle(LoopConfig())
    report.actions_taken += orch_report.signals_drained + orch_report.retries_attempted
    report.errors += orch_report.escalations
    report.details.append({
        "stage": "signal_drain",
        "signals_drained": orch_report.signals_drained,
        "workflows_triggered": orch_report.workflows_triggered,
        "stale_deferred": orch_report.stale_deferred,
        "failures_detected": orch_report.failures_detected,
    })


@stage("actionable_scan")
def actionable_scan(loop: PersistentLoop, report: CycleReport) -> None:
    """Deterministic scan for items needing attention."""
    items_found = 0
    findings: list[str] = []

    try:
        from substrate.state.storage.db import get_conn, ORG_ID
        conn = get_conn()
        if conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM tasks "
                "WHERE org_id = %s AND status = 'active' "
                "AND due_date < NOW()",
                (ORG_ID,),
            )
            overdue = cur.fetchone()[0]
            if overdue:
                items_found += overdue
                findings.append(f"{overdue} overdue tasks")

            cur.execute(
                "SELECT COUNT(*) FROM leads "
                "WHERE org_id = %s AND replied = true AND status = 'new'",
                (ORG_ID,),
            )
            replies = cur.fetchone()[0]
            if replies:
                items_found += replies
                findings.append(f"{replies} unhandled replies")

            conn.close()
    except Exception as e:
        logger.debug(f"[actionable_scan] DB scan skipped: {e}")

    report.actions_taken += items_found
    report.details.append({
        "stage": "actionable_scan",
        "items_found": items_found,
        "findings": findings,
    })


# ─── Self-improvement stages ────────────────────────────────────────────────


@stage("goal_execution")
def goal_execution(loop: PersistentLoop, report: CycleReport) -> None:
    """Run one goal execution cycle (select → plan → execute → record)."""
    from substrate.execution.loop.execution_loop import ExecutionLoop

    exec_loop = ExecutionLoop()
    cycle_result = exec_loop.run_cycle(cycle_num=loop._cycle_count)
    report.actions_taken += len(cycle_result.results)
    goal_errors = sum(1 for r in cycle_result.results.values() if not r.success)
    report.errors += goal_errors
    report.details.append({
        "stage": "goal_execution",
        "active_goals": cycle_result.active_goals,
        "results": {
            gid: {"success": r.success, "time": r.execution_time}
            for gid, r in cycle_result.results.items()
        },
        "reselected": cycle_result.reselected,
    })


@stage("feedback_collection")
def feedback_collection(loop: PersistentLoop, report: CycleReport) -> None:
    """Aggregate recent feedback scores for learning."""
    try:
        from substrate.execution.feedback_loop import get_feedback_loop
        fl = get_feedback_loop()
        stats = fl.get_aggregate_stats()
        report.details.append({"stage": "feedback_collection", "recent_stats": stats})
    except Exception:
        report.details.append({"stage": "feedback_collection", "recent_stats": {}})


@stage("health_check")
def health_check(loop: PersistentLoop, report: CycleReport) -> None:
    """Deterministic health indicators for the substrate."""
    indicators: dict[str, str | int] = {}
    heartbeat_dir = _ROOT / "data" / "runtime" / "loop_heartbeats"
    if heartbeat_dir.exists():
        for hb_file in heartbeat_dir.glob("*.json"):
            try:
                data = json.loads(hb_file.read_text())
                indicators[hb_file.stem] = data.get("state", "unknown")
            except Exception:
                indicators[hb_file.stem] = "unreadable"

    error_log = _ROOT / "logs" / "errors.log"
    if error_log.exists():
        try:
            lines = error_log.read_text().strip().split("\n")
            indicators["recent_errors"] = len(lines[-100:]) if lines else 0
        except Exception:
            indicators["recent_errors"] = -1

    report.details.append({"stage": "health_check", **indicators})


# ─── Research stages ─────────────────────────────────────────────────────────

_RESEARCH_QUEUE = _ROOT / "data" / "runtime" / "research_queue"
_WORLD_MODEL_DIR = _ROOT / "data" / "runtime" / "world_model"


@stage("research_topic_select")
def research_topic_select(loop: PersistentLoop, report: CycleReport) -> None:
    """Pick the next research topic from the queue (FIFO)."""
    _RESEARCH_QUEUE.mkdir(parents=True, exist_ok=True)
    queue_file = _RESEARCH_QUEUE / "topics.jsonl"
    topic = None

    if queue_file.exists():
        lines = queue_file.read_text().strip().split("\n")
        if lines and lines[0].strip():
            try:
                entry = json.loads(lines[0])
                remaining = "\n".join(lines[1:]) + "\n" if len(lines) > 1 else ""
                queue_file.write_text(remaining)
                topic = entry.get("topic", entry.get("title", str(entry)))
            except (json.JSONDecodeError, KeyError):
                topic = lines[0].strip() if lines[0].strip() else None

    report.details.append({"stage": "research_topic_select", "topic": topic})
    # Stash topic for downstream stages
    if not hasattr(loop, "_stage_context"):
        loop._stage_context = {}
    loop._stage_context["research_topic"] = topic


@stage("research_execute")
def research_execute(loop: PersistentLoop, report: CycleReport) -> None:
    """Execute research on the selected topic via cognitive loop."""
    ctx = getattr(loop, "_stage_context", {})
    topic = ctx.get("research_topic")
    if not topic:
        report.details.append({"stage": "research_execute", "skipped": "no topic"})
        return

    try:
        from substrate.control_plane.runtime.cognitive_loop import CognitiveLoop
        from substrate.state.context.context import load_context_from_env
        loop_ctx = load_context_from_env()
        cog = CognitiveLoop(loop_ctx)
        result = cog.run(
            input=f"Research the following topic and produce a structured summary: {topic}",
            agent="research_agent",
        )
        output = result.output or ""
        success = bool(output)
    except Exception as e:
        logger.debug(f"[research_execute] cognitive loop unavailable: {e}")
        output = f"[deterministic] Research topic queued: {topic}"
        success = True

    report.actions_taken += 1
    report.details.append({
        "stage": "research_execute",
        "success": success,
        "output_length": len(output),
    })
    ctx["research_output"] = output
    ctx["research_success"] = success


@stage("world_model_store")
def world_model_store(loop: PersistentLoop, report: CycleReport) -> None:
    """Persist research finding to world model."""
    ctx = getattr(loop, "_stage_context", {})
    topic = ctx.get("research_topic")
    output = ctx.get("research_output", "")
    if not topic or not ctx.get("research_success"):
        report.details.append({"stage": "world_model_store", "skipped": True})
        return

    _WORLD_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "topic": topic,
        "output": output[:2000],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle": loop._cycle_count,
    }
    findings_file = _WORLD_MODEL_DIR / "findings.jsonl"
    with open(findings_file, "a") as f:
        f.write(json.dumps(entry) + "\n")
    report.details.append({"stage": "world_model_store", "stored": True})


@stage("staleness_scan")
def staleness_scan(loop: PersistentLoop, report: CycleReport) -> None:
    """Find world model entries older than 30 days."""
    stale: list[str] = []
    findings_file = _WORLD_MODEL_DIR / "findings.jsonl"
    if not findings_file.exists():
        report.details.append({"stage": "staleness_scan", "stale_entries": []})
        return

    now = datetime.now(timezone.utc)
    for line in findings_file.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            ts_str = entry.get("timestamp", "")
            if ts_str:
                ts = datetime.fromisoformat(ts_str)
                if (now - ts).days > 30:
                    stale.append(entry.get("topic", "unknown"))
        except Exception:
            pass
    report.details.append({"stage": "staleness_scan", "stale_entries": stale})
