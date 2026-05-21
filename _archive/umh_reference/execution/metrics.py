"""UMH Execution Metrics CLI — surface scoring and capability status.

Usage:
    python3 -m umh.execution.metrics
    python3 -m umh.execution.metrics --json
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/opt/OS")


def _capability_status_map() -> list[dict]:
    """Build the current capability status map."""
    return [
        {
            "capability": "llm_call",
            "operations": "12 operation types",
            "status": "ACTIVE",
            "guard": "bypass (PURE/LLM_CALL)",
            "environment": "local (REAL)",
            "adapter": "built-in",
        },
        {
            "capability": "shell_command",
            "operations": "12 allowlisted",
            "status": "ACTIVE",
            "guard": "allowlist + metachar",
            "environment": "local (REAL)",
            "adapter": "built-in",
        },
        {
            "capability": "file_operation",
            "operations": "read/list/stat",
            "status": "ACTIVE",
            "guard": "path sandbox",
            "environment": "local (REAL)",
            "adapter": "built-in",
        },
        {
            "capability": "file_operation",
            "operations": "write/delete",
            "status": "STUB",
            "guard": "path sandbox",
            "environment": "local (REAL)",
            "adapter": "built-in",
        },
        {
            "capability": "computer_use",
            "operations": "screenshot/screen_size/active_window",
            "status": "ACTIVE",
            "guard": "read-only ALLOW",
            "environment": "local (REAL)",
            "adapter": "computer_use_adapter",
        },
        {
            "capability": "computer_use",
            "operations": "click/type/key/scroll/drag",
            "status": "ACTIVE (approved)",
            "guard": "REQUIRES_APPROVAL → approved bypass",
            "environment": "local (REAL)",
            "adapter": "computer_use_adapter",
        },
        {
            "capability": "browser_action",
            "operations": "navigate/click/type/screenshot/extract",
            "status": "STUB",
            "guard": "DENY",
            "environment": "container (NOT_IMPLEMENTED)",
            "adapter": "browser_adapter",
        },
        {
            "capability": "os_interaction",
            "operations": "*",
            "status": "NOT_WIRED",
            "guard": "DENY",
            "environment": "—",
            "adapter": "—",
        },
    ]


def _environment_status() -> list[dict]:
    """Build environment status list."""
    from umh.execution.environment import list_environments

    result = []
    for env in list_environments():
        result.append(
            {
                "id": env.id,
                "type": env.env_type.value,
                "security": env.security_level.value,
                "execution_mode": env.execution_mode.value,
                "capabilities": sorted(env.supported_capabilities),
            }
        )
    return result


def _scoring_stats() -> dict:
    """Gather current scoring statistics."""
    from umh.execution.scoring import get_capability_scorer

    scorer = get_capability_scorer()
    return {
        "aggregate": scorer.get_all_stats(),
        "per_environment": scorer.get_all_env_stats(),
    }


def _approval_stats() -> dict:
    """Gather approval store statistics."""
    from umh.execution.approval import get_approval_store

    store = get_approval_store()
    pending = store.list_pending()
    counters = store.get_counters()
    return {
        "pending_count": len(pending),
        "pending": [r.to_dict() for r in pending],
        "approvals_consumed": counters["consumed"],
        "approvals_denied": counters["denied"],
        "approvals_expired": counters["expired"],
    }


def get_worker_metrics() -> dict:
    """Return worker heartbeat metrics. Empty dict with is_running=False if no worker."""
    try:
        from umh.orchestrator.worker import get_worker

        worker = get_worker()
        if worker.is_running:
            return worker.heartbeat()
    except Exception:
        pass
    return {
        "worker_id": "",
        "started_at": "",
        "last_heartbeat": "",
        "current_task_id": None,
        "tasks_processed": 0,
        "poll_cycles": 0,
        "is_running": False,
    }


def get_extended_metrics() -> dict:
    """Extended metrics including worker and task duration stats."""
    base = get_metrics()

    # Worker metrics
    try:
        from umh.orchestrator.worker import get_worker

        worker = get_worker()
        base["worker"] = worker.heartbeat()
    except Exception:
        base["worker"] = {"is_running": False}

    # Task duration stats
    try:
        from umh.orchestrator.task import TaskStatus, list_tasks
        from datetime import datetime

        tasks = list_tasks()
        durations: list[float] = []
        failed_recent = 0
        retry_total = 0

        for t in tasks:
            if t.status == TaskStatus.COMPLETED and t.created_at and t.updated_at:
                try:
                    start = datetime.fromisoformat(t.created_at)
                    end = datetime.fromisoformat(t.updated_at)
                    durations.append((end - start).total_seconds())
                except (ValueError, TypeError):
                    pass
            if t.status == TaskStatus.FAILED:
                failed_recent += 1
            for step in t.steps:
                retry_total += getattr(step, "retry_count", 0)

        base["task_stats"] = {
            "avg_task_duration_s": round(sum(durations) / len(durations), 2) if durations else 0,
            "failed_tasks_total": failed_recent,
            "total_retries": retry_total,
        }
    except Exception:
        base["task_stats"] = {}

    return base


def get_metrics() -> dict:
    """Return all execution metrics as a structured dict."""
    return {
        "capabilities": _capability_status_map(),
        "environments": _environment_status(),
        "scoring": _scoring_stats(),
        "approvals": _approval_stats(),
    }


def print_report(as_json: bool = False) -> None:
    """Print a human-readable or JSON metrics report."""
    metrics = get_metrics()

    if as_json:
        print(json.dumps(metrics, indent=2))
        return

    print("=" * 60)
    print("UMH EXECUTION METRICS")
    print("=" * 60)

    print("\n--- Capability Status ---")
    for cap in metrics["capabilities"]:
        print(f"  {cap['capability']:20s} {cap['status']:10s} {cap['operations']}")

    print("\n--- Environments ---")
    for env in metrics["environments"]:
        caps = ", ".join(env["capabilities"])
        print(
            f"  {env['id']:12s} mode={env['execution_mode']:16s} "
            f"security={env['security']:10s} caps=[{caps}]"
        )

    scoring = metrics["scoring"]
    agg = scoring["aggregate"]
    print("\n--- Scoring (Aggregate) ---")
    if agg:
        for cap_type, stats in agg.items():
            print(
                f"  {cap_type:20s} calls={stats['total_calls']:4d} "
                f"success={stats['success_rate']:.2%} "
                f"fail={stats['failure_rate']:.2%} "
                f"timeout={stats['timeout_rate']:.2%} "
                f"avg_latency={stats['avg_latency_ms']:.0f}ms "
                f"cost=${stats['total_cost_usd']:.6f}"
            )
    else:
        print("  (no data)")

    env_stats = scoring["per_environment"]
    print("\n--- Scoring (Per Environment) ---")
    if env_stats:
        for key, stats in env_stats.items():
            print(
                f"  {key:30s} calls={stats['total_calls']:4d} success={stats['success_rate']:.2%}"
            )
    else:
        print("  (no data)")

    approvals = metrics["approvals"]
    print(f"\n--- Approvals (pending={approvals['pending_count']}) ---")
    print(
        f"  consumed={approvals['approvals_consumed']} "
        f"denied={approvals['approvals_denied']} "
        f"expired={approvals['approvals_expired']}"
    )
    for req in approvals["pending"]:
        print(
            f"  {req['id']} op={req['operation']} "
            f"risk={req['risk_level']} expires={req['expires_at']}"
        )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    as_json = "--json" in sys.argv
    print_report(as_json=as_json)
