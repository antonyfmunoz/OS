"""
observability.py — Read-only view over the EOS AI OS.

Single entry point for "what is the system doing right now?". Reads JSONL
and state files — never touches the runtime. Safe to run when the
orchestrator is not running.

Usage:
    from core.observability import Observability

    obs = Observability()
    print(obs.snapshot())              # dict summary
    print(obs.recent_workflows(10))    # last 10 workflows
    print(obs.recent_actions(10))      # last 10 actions
    print(obs.agent_status())          # persistent agents' state files
    print(obs.orchestrator_status())   # last saved orchestrator state
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import os
_REPO_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


DATA_DIR = Path(_REPO_ROOT) / "data"
AGENT_STATE_DIR = DATA_DIR / "agent_state"
SANDBOX_ROOT = DATA_DIR / "sandboxes"
PLAYGROUND_ROOT = DATA_DIR / "playgrounds"


@dataclass
class LogPaths:
    workflow: Path = DATA_DIR / "workflow_log.jsonl"
    orchestrator: Path = DATA_DIR / "orchestrator_log.jsonl"
    harness: Path = DATA_DIR / "harness_log.jsonl"
    action: Path = DATA_DIR / "action_log.jsonl"
    persistent_agents: Path = DATA_DIR / "persistent_agents_log.jsonl"
    optimizer_proposals: Path = DATA_DIR / "optimizer_proposals.jsonl"
    advisor: Path = DATA_DIR / "advisor_log.jsonl"

    orchestrator_state: Path = DATA_DIR / "orchestrator_state.json"
    optimizer_state: Path = DATA_DIR / "optimizer_state.json"
    workflow_state_dir: Path = DATA_DIR / "workflow_state"


def _read_jsonl_tail(path: Path, n: int = 50) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _paths_for_env_root(root: Path) -> LogPaths:
    """Build a LogPaths pointing at a sandbox/playground tree.

    Mirrors the layout produced by ``core.environment.make_sandbox``:
    ``<root>/logs/`` for JSONL streams, ``<root>/state/`` for
    snapshot-style JSON. Matches the attributes ``Environment`` exposes
    (``log_dir``, ``state_dir``, ``workflow_state_dir``).
    """
    root = Path(root)
    log_dir = root / "logs"
    state_dir = root / "state"
    return LogPaths(
        workflow=log_dir / "workflow_log.jsonl",
        orchestrator=log_dir / "orchestrator_log.jsonl",
        harness=log_dir / "harness_log.jsonl",
        action=log_dir / "action_log.jsonl",
        persistent_agents=log_dir / "persistent_agents_log.jsonl",
        optimizer_proposals=log_dir / "optimizer_proposals.jsonl",
        advisor=log_dir / "advisor_log.jsonl",
        orchestrator_state=state_dir / "orchestrator_state.json",
        optimizer_state=state_dir / "optimizer_state.json",
        workflow_state_dir=state_dir / "workflow_state",
    )


class Observability:
    """Pure reader over logs + state files.

    By default reads production logs under /opt/OS/data. To point at a
    sandbox or playground, pass ``env_root=`` (the sandbox tree root, e.g.
    ``/opt/OS/data/sandboxes/my-run``) or build custom ``paths``.

    Filtering by env label (``env="production"`` / ``env="sandbox:..."``)
    applies an *in-line* filter over the records — useful when one log
    file contains mixed environments (should never happen by design, but
    the filter makes that guarantee observable).
    """

    def __init__(
        self,
        *,
        paths: LogPaths | None = None,
        env_root: Path | None = None,
        env_filter: str | None = None,
    ) -> None:
        if paths is not None and env_root is not None:
            raise ValueError("pass paths OR env_root, not both")
        if env_root is not None:
            self.paths = _paths_for_env_root(Path(env_root))
            self._agent_state_dir = Path(env_root) / "state" / "agent_state"
        else:
            self.paths = paths or LogPaths()
            self._agent_state_dir = AGENT_STATE_DIR
        self.env_filter = env_filter

    def _filter_env(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.env_filter:
            return rows
        # Records written before env-tagging existed have no "env" key —
        # treat those as production for back-compat.
        target = self.env_filter
        out: list[dict[str, Any]] = []
        for r in rows:
            label = r.get("env", "production")
            if target == "production":
                if label == "production":
                    out.append(r)
            elif target == "sandbox":
                if label != "production":
                    out.append(r)
            else:
                if label == target:
                    out.append(r)
        return out

    # ── Snapshots ────────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """A single dict summarizing the whole system."""
        wf_rows = self._filter_env(_read_jsonl_tail(self.paths.workflow, 500))
        orch_rows = self._filter_env(_read_jsonl_tail(self.paths.orchestrator, 500))
        harness_rows = self._filter_env(_read_jsonl_tail(self.paths.harness, 500))

        finished = [r for r in wf_rows if r.get("event") == "workflow_finished"]
        wf_ok = sum(1 for r in finished if r.get("workflow_status") == "completed")
        wf_failed = sum(1 for r in finished if r.get("workflow_status") == "failed")
        wf_total = wf_ok + wf_failed

        # Running workflows = saved state files with status=running
        running: list[str] = []
        if self.paths.workflow_state_dir.exists():
            for f in self.paths.workflow_state_dir.glob("*.json"):
                data = _read_json(f)
                if data.get("status") == "running":
                    running.append(data.get("id", f.stem))

        harness_fail = sum(1 for r in harness_rows if r.get("ok") is False)
        harness_total = len(harness_rows)

        orch_state = _read_json(self.paths.orchestrator_state)
        opt_state = _read_json(self.paths.optimizer_state)

        # Persistent agents — last-tick summary from state files
        agents = self.agent_status()

        # Advisor stats
        advisor_rows = self._filter_env(_read_jsonl_tail(self.paths.advisor, 200))
        advisor_total = len(advisor_rows)
        advisor_escalated = sum(
            1 for r in advisor_rows if r.get("decision") in ("modify", "reject")
        )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "workflows": {
                "ok": wf_ok,
                "failed": wf_failed,
                "total": wf_total,
                "failure_rate": round(wf_failed / wf_total, 3) if wf_total else 0.0,
                "running": running,
            },
            "orchestrator": {
                "started": orch_state.get("started", False),
                "queue_depth": orch_state.get("queue_depth", 0),
                "jobs": [
                    {
                        "id": j.get("id"),
                        "status": j.get("status"),
                        "total_runs": j.get("total_runs", 0),
                        "total_failures": j.get("total_failures", 0),
                    }
                    for j in orch_state.get("jobs", [])
                ],
            },
            "harness": {
                "recent_calls": harness_total,
                "recent_failures": harness_fail,
                "failure_rate": (
                    round(harness_fail / harness_total, 3) if harness_total else 0.0
                ),
            },
            "advisor": {
                "recent_calls": advisor_total,
                "recent_escalations": advisor_escalated,
                "escalation_rate": (
                    round(advisor_escalated / advisor_total, 3)
                    if advisor_total
                    else 0.0
                ),
            },
            "agents": agents,
            "optimizer": {
                "last_run_at": opt_state.get("last_run_at"),
                "last_added": opt_state.get("last_added", 0),
                "total_added": opt_state.get("total_added", 0),
            },
        }

    def recent_workflows(self, n: int = 10) -> list[dict[str, Any]]:
        rows = self._filter_env(_read_jsonl_tail(self.paths.workflow, 1000))
        finished = [r for r in rows if r.get("event") == "workflow_finished"]
        return finished[-n:]

    def recent_actions(self, n: int = 10) -> list[dict[str, Any]]:
        rows = self._filter_env(_read_jsonl_tail(self.paths.action, 500))
        executed = [
            r
            for r in rows
            if r.get("event")
            in ("proposed", "executing", "dry_run", "failed", "succeeded")
        ]
        return executed[-n:]

    def recent_harness_calls(self, n: int = 10) -> list[dict[str, Any]]:
        return self._filter_env(_read_jsonl_tail(self.paths.harness, n))

    def recent_failures(self, n: int = 10) -> list[dict[str, Any]]:
        rows = self._filter_env(_read_jsonl_tail(self.paths.harness, 500))
        failed = [r for r in rows if r.get("ok") is False]
        return failed[-n:]

    def agent_status(self) -> list[dict[str, Any]]:
        """Read each persistent agent's state file."""
        if not self._agent_state_dir.exists():
            return []
        agents = []
        for f in sorted(self._agent_state_dir.glob("*.json")):
            data = _read_json(f)
            agents.append(
                {
                    "agent": data.get("agent", f.stem),
                    "last_tick_at": data.get("last_tick_at"),
                    "tick_count": data.get("tick_count", 0),
                    "tick_failures": data.get("tick_failures", 0),
                    "custom": data.get("custom") or {},
                }
            )
        return agents

    def orchestrator_status(self) -> dict[str, Any]:
        return _read_json(self.paths.orchestrator_state)

    def optimizer_proposals(
        self, *, pending_only: bool = True, limit: int = 20
    ) -> list[dict[str, Any]]:
        rows = _read_jsonl_tail(self.paths.optimizer_proposals, 500)
        if pending_only:
            rows = [r for r in rows if r.get("status", "pending") == "pending"]
        return rows[-limit:]

    # ── Advisor views ────────────────────────────────────────────────────

    def advisor_stats(self) -> dict[str, Any]:
        """Compute advisor usage stats from the advisor log."""
        rows = self._filter_env(_read_jsonl_tail(self.paths.advisor, 500))
        if not rows:
            return {
                "total_calls": 0,
                "decisions": {},
                "escalation_reasons": {},
                "avg_latency_ms": 0,
                "avg_confidence": 0.0,
            }

        decisions: dict[str, int] = {}
        reasons: dict[str, int] = {}
        total_latency = 0
        total_confidence = 0.0

        for r in rows:
            d = r.get("decision", "unknown")
            decisions[d] = decisions.get(d, 0) + 1
            reason = r.get("escalation_reason", "unknown")
            reasons[reason] = reasons.get(reason, 0) + 1
            total_latency += r.get("latency_ms", 0)
            total_confidence += r.get("confidence", 0.0)

        n = len(rows)
        return {
            "total_calls": n,
            "decisions": decisions,
            "escalation_reasons": reasons,
            "avg_latency_ms": round(total_latency / n) if n else 0,
            "avg_confidence": round(total_confidence / n, 3) if n else 0.0,
        }

    def recent_advisor_calls(self, n: int = 10) -> list[dict[str, Any]]:
        """Return the last N advisor log entries."""
        return self._filter_env(_read_jsonl_tail(self.paths.advisor, n))

    # ── Sandbox views ────────────────────────────────────────────────────

    @staticmethod
    def sandbox_runs() -> list[dict[str, Any]]:
        """List every sandbox tree under data/sandboxes/ with a summary."""
        return _enumerate_envs(SANDBOX_ROOT, kind="sandbox")

    @staticmethod
    def playground_runs() -> list[dict[str, Any]]:
        """List every ephemeral playground tree still on disk."""
        return _enumerate_envs(PLAYGROUND_ROOT, kind="playground")

    def compare_to_production(self) -> dict[str, Any]:
        """Compare *this* observability view to production.

        Useful when this instance is bound to a sandbox via ``env_root=``
        — you get a side-by-side of key metrics without running two
        reports manually.
        """
        prod = Observability()
        here = self.snapshot()
        there = prod.snapshot()
        return {
            "this": {
                "workflows": here["workflows"],
                "harness": here["harness"],
                "agents": len(here["agents"]),
            },
            "production": {
                "workflows": there["workflows"],
                "harness": there["harness"],
                "agents": len(there["agents"]),
            },
            "delta": {
                "workflows_total": here["workflows"]["total"]
                - there["workflows"]["total"],
                "workflows_failed": here["workflows"]["failed"]
                - there["workflows"]["failed"],
            },
        }


def _enumerate_envs(root: Path, *, kind: str) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    out: list[dict[str, Any]] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        paths = _paths_for_env_root(entry)
        wf_rows = _read_jsonl_tail(paths.workflow, 500)
        act_rows = _read_jsonl_tail(paths.action, 500)
        finished = [r for r in wf_rows if r.get("event") == "workflow_finished"]
        wf_ok = sum(1 for r in finished if r.get("workflow_status") == "completed")
        wf_failed = sum(1 for r in finished if r.get("workflow_status") == "failed")
        try:
            mtime = entry.stat().st_mtime
            last_touched = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        except OSError:
            last_touched = None
        out.append(
            {
                "kind": kind,
                "name": entry.name,
                "path": str(entry),
                "last_touched": last_touched,
                "workflows_ok": wf_ok,
                "workflows_failed": wf_failed,
                "actions": len(act_rows),
            }
        )
    return out


__all__ = ["LogPaths", "Observability"]
