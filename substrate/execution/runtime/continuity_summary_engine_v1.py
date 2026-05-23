"""Continuity Summary Engine v1.

Generates structured summaries from continuity data:
session summaries, restart summaries, operator briefings.

Deterministic. No LLM calls. Pure data aggregation.

UMH substrate subsystem.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runtime_cognition_contracts_v1 import (
    OutcomeResult,
    RuntimeSessionSummary,
    _new_id,
)
from .runtime_continuity_store_v1 import RuntimeContinuityStore
from .open_loop_registry_v1 import OpenLoopRegistry


class ContinuitySummaryEngine:
    """Generates summaries from continuity data."""

    def __init__(
        self,
        continuity_store: RuntimeContinuityStore | None = None,
        loop_registry: OpenLoopRegistry | None = None,
        summaries_dir: str | Path = "data/runtime/continuity_summaries",
    ):
        self.continuity_store = continuity_store or RuntimeContinuityStore()
        self.loop_registry = loop_registry or OpenLoopRegistry()
        self.summaries_dir = Path(summaries_dir)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

    def generate_session_summary(
        self,
        session_id: str,
        phase_name: str = "",
        started_at: str = "",
        files_modified: list[str] | None = None,
    ) -> RuntimeSessionSummary:
        """Generate a summary of the current/recent session."""
        outcomes = self.continuity_store.load_recent_outcomes(limit=100)
        traces = self.continuity_store.load_recent_traces(limit=100)
        events = self.continuity_store.load_recent_events(limit=100)

        session_outcomes = [o for o in outcomes if o.get("session_id") == session_id]
        session_traces = [t for t in traces if t.get("session_id") == session_id]

        successes = sum(
            1 for o in session_outcomes if o.get("result") == OutcomeResult.SUCCESS.value
        )
        failures = sum(
            1
            for o in session_outcomes
            if o.get("result") in (OutcomeResult.FAILURE.value, OutcomeResult.TIMEOUT.value)
        )

        open_loops = self.loop_registry.get_open_loops()
        session_loops = [l for l in open_loops if l.get("session_id") == session_id]

        key_outcomes = []
        for o in session_outcomes[-5:]:
            cmd = o.get("command", "unknown")
            result = o.get("result", "unknown")
            key_outcomes.append(f"{cmd}: {result}")

        unresolved = [l["description"] for l in session_loops]

        now = datetime.now(timezone.utc).isoformat()
        summary = RuntimeSessionSummary(
            session_id=session_id,
            summary_type="session",
            phase_name=phase_name,
            started_at=started_at or now,
            ended_at=now,
            total_events=len(events),
            total_traces=len(session_traces),
            total_outcomes=len(session_outcomes),
            successes=successes,
            failures=failures,
            open_loops_at_end=len(session_loops),
            key_outcomes=key_outcomes,
            unresolved_items=unresolved,
            files_modified=files_modified or [],
        )

        self.continuity_store.save_summary(summary.to_dict())
        self._save_to_disk(summary, "session")
        return summary

    def generate_restart_summary(self) -> dict[str, Any]:
        """Generate a summary for system restart/resume."""
        snapshot = self.continuity_store.load_latest_snapshot()
        open_loops = self.loop_registry.get_open_loops()
        recent_outcomes = self.continuity_store.load_recent_outcomes(limit=5)
        store_stats = self.continuity_store.get_stats()
        loop_stats = self.loop_registry.get_stats()

        summary = {
            "summary_type": "restart",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "last_snapshot": snapshot,
            "open_loops_count": len(open_loops),
            "open_loops": [
                {"id": l["loop_id"], "type": l["loop_type"], "description": l["description"]}
                for l in open_loops[:10]
            ],
            "recent_outcomes": [
                {"command": o.get("command", "?"), "result": o.get("result", "?")}
                for o in recent_outcomes
            ],
            "store_stats": store_stats,
            "loop_stats": loop_stats,
        }

        self._save_dict_to_disk(summary, "restart")
        return summary

    def generate_operator_briefing(self) -> dict[str, Any]:
        """Generate a high-level operator briefing."""
        store_stats = self.continuity_store.get_stats()
        loop_stats = self.loop_registry.get_stats()
        open_loops = self.loop_registry.get_open_loops()
        recent_outcomes = self.continuity_store.load_recent_outcomes(limit=10)

        failures = [o for o in recent_outcomes if o.get("result") in ("failure", "timeout")]
        successes = [o for o in recent_outcomes if o.get("result") == "success"]

        briefing = {
            "summary_type": "operator_briefing",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "health": {
                "events_ingested": store_stats.get("events", 0),
                "traces_ingested": store_stats.get("traces", 0),
                "outcomes_recorded": store_stats.get("outcomes", 0),
                "open_loops": loop_stats.get("open", 0),
                "resolved_loops": loop_stats.get("resolved", 0),
                "stale_loops": loop_stats.get("stale", 0),
            },
            "recent_failures": [
                {"command": f.get("command", "?"), "error": f.get("error_message", "?")}
                for f in failures
            ],
            "recent_successes_count": len(successes),
            "critical_open_loops": [
                l["description"]
                for l in open_loops
                if l.get("loop_type") in ("failed_execution", "pending_governance")
            ],
            "resumability": "ready" if store_stats.get("has_latest_resume") else "no_resume_packet",
        }

        self._save_dict_to_disk(briefing, "operator_briefing")
        return briefing

    def _save_to_disk(self, summary: RuntimeSessionSummary, prefix: str) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self.summaries_dir / f"{prefix}_{ts}.json"
        with open(path, "w") as f:
            json.dump(summary.to_dict(), f, indent=2)
        return path

    def _save_dict_to_disk(self, data: dict[str, Any], prefix: str) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self.summaries_dir / f"{prefix}_{ts}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path
