"""
persistent_agents.py — Long-running stateful agents in the EOS OS.

A persistent agent is NOT a thread. It is a state-carrying object whose
`tick()` method is called on a schedule by the orchestrator. State is
written to disk (data/agent_state/<name>.json) after every tick so restarts
resume cleanly.

Three built-in agents in this first pass:

  Observer   — watches system health. Reads workflow_log.jsonl,
               orchestrator_log.jsonl, harness_log.jsonl. Emits alerts
               when failure rates cross a threshold.
  Healer     — re-enables disabled orchestrator jobs that have cooled off,
               and submits a safe refactor workflow when Observer alerts.
  Librarian  — consolidates recent workflow runs into short notes via the
               harness's LLM path and remembers them in AgentMemory.

All three run through `core.agent_harness.AgentHarness`. None bypass the
capability system.

Usage:
    from core.persistent_agents import default_agents, PersistentAgent

    agents = default_agents()
    for a in agents:
        a.tick()   # returns a TickResult
"""

from __future__ import annotations

import json
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import os
_REPO_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.agent_harness import AgentHarness, default_harness  # noqa: E402


DATA_DIR = Path(_REPO_ROOT) / "data"
AGENT_STATE_DIR = DATA_DIR / "agent_state"
AGENT_STATE_DIR.mkdir(parents=True, exist_ok=True)
AGENT_LOG = DATA_DIR / "persistent_agents_log.jsonl"


# ---------------------------------------------------------------------------
# Tick result
# ---------------------------------------------------------------------------


@dataclass
class TickResult:
    agent: str
    ok: bool
    summary: str
    duration_ms: int = 0
    alerts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class PersistentAgent(ABC):
    """Base class for long-running agents.

    Subclasses override `tick_impl(state) → TickResult` and declare:
      - name:        unique agent name (also the capability profile name)
      - interval_sec: minimum seconds between ticks
    """

    name: str = "unnamed"
    interval_sec: int = 300

    def __init__(self, *, harness: AgentHarness | None = None) -> None:
        self.harness = harness or default_harness()
        self.state_file = AGENT_STATE_DIR / f"{self.name}.json"
        self._state: dict[str, Any] = self._load_state()

    # ── State persistence ───────────────────────────────────────────────

    def _load_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {
                "agent": self.name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_tick_at": None,
                "tick_count": 0,
                "tick_failures": 0,
                "custom": {},
            }
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except Exception:
            return {
                "agent": self.name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_tick_at": None,
                "tick_count": 0,
                "tick_failures": 0,
                "custom": {},
            }

    def _save_state(self) -> None:
        try:
            self.state_file.write_text(
                json.dumps(self._state, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception:
            pass

    def state(self) -> dict[str, Any]:
        return dict(self._state)

    # ── Tick ────────────────────────────────────────────────────────────

    def should_tick(self, now: float | None = None) -> bool:
        """True if at least interval_sec has elapsed since last_tick_at."""
        last = self._state.get("last_tick_at")
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(last)
        except Exception:
            return True
        cur = (
            datetime.fromtimestamp(now, tz=timezone.utc)
            if now
            else datetime.now(timezone.utc)
        )
        return (cur - last_dt).total_seconds() >= self.interval_sec

    def tick(self) -> TickResult:
        """Run one tick. Never raises."""
        t0 = time.monotonic()
        try:
            result = self.tick_impl(self._state)
            if not isinstance(result, TickResult):
                result = TickResult(
                    agent=self.name,
                    ok=False,
                    summary=f"bad tick_impl return: {type(result).__name__}",
                )
        except Exception as e:
            result = TickResult(
                agent=self.name,
                ok=False,
                summary=f"tick_impl raised: {type(e).__name__}: {e}",
            )

        result.duration_ms = int((time.monotonic() - t0) * 1000)
        self._state["last_tick_at"] = datetime.now(timezone.utc).isoformat()
        self._state["tick_count"] = int(self._state.get("tick_count", 0)) + 1
        if not result.ok:
            self._state["tick_failures"] = int(self._state.get("tick_failures", 0)) + 1
        self._save_state()
        _emit_agent_log(self.name, result)
        return result

    @abstractmethod
    def tick_impl(self, state: dict[str, Any]) -> TickResult:
        """Subclass hook. Return a TickResult. Update state["custom"] freely."""


# ---------------------------------------------------------------------------
# Log readers — used by Observer
# ---------------------------------------------------------------------------


def _tail_jsonl(path: Path, lines: int = 200) -> list[dict[str, Any]]:
    """Read the last N valid JSONL rows. Non-fatal on errors."""
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            rows = f.readlines()[-lines:]
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for r in rows:
        r = r.strip()
        if not r:
            continue
        try:
            out.append(json.loads(r))
        except Exception:
            continue
    return out


# ---------------------------------------------------------------------------
# Observer
# ---------------------------------------------------------------------------


class ObserverAgent(PersistentAgent):
    """Reads logs, computes health, emits alerts into state.

    Alerts are stored in `state["custom"]["alerts"]` so the Healer can react
    on its next tick. Observer never calls LLMs or mutates anything.

    When alerts are present, optionally consults the advisor for anomaly
    interpretation — providing richer context for the Healer.
    """

    name = "observer"
    interval_sec = 120  # 2 min

    # Thresholds
    FAILURE_RATE_THRESHOLD = 0.40  # 40% failures in window → alert
    MIN_SAMPLE_SIZE = 5  # need at least this many runs
    STALE_WORKFLOW_SEC = 30 * 60  # a "running" workflow older than 30m is stuck

    def tick_impl(self, state: dict[str, Any]) -> TickResult:
        workflow_rows = _tail_jsonl(DATA_DIR / "workflow_log.jsonl", 500)
        orch_rows = _tail_jsonl(DATA_DIR / "orchestrator_log.jsonl", 500)
        harness_rows = _tail_jsonl(DATA_DIR / "harness_log.jsonl", 500)

        workflows_finished = [
            r for r in workflow_rows if r.get("event") == "workflow_finished"
        ]
        wf_ok = sum(
            1 for r in workflows_finished if r.get("workflow_status") == "completed"
        )
        wf_failed = sum(
            1 for r in workflows_finished if r.get("workflow_status") == "failed"
        )
        total = wf_ok + wf_failed

        failure_rate = (wf_failed / total) if total else 0.0

        harness_errors = sum(1 for r in harness_rows if r.get("ok") is False)
        harness_total = len(harness_rows)
        harness_error_rate = (harness_errors / harness_total) if harness_total else 0.0

        disabled_jobs = [
            r.get("job_id") for r in orch_rows if r.get("event") == "job_disabled"
        ]

        alerts: list[str] = []
        if (
            total >= self.MIN_SAMPLE_SIZE
            and failure_rate >= self.FAILURE_RATE_THRESHOLD
        ):
            alerts.append(f"workflow_failure_rate={failure_rate:.0%} over {total} runs")
        if (
            harness_total >= self.MIN_SAMPLE_SIZE
            and harness_error_rate >= self.FAILURE_RATE_THRESHOLD
        ):
            alerts.append(
                f"harness_error_rate={harness_error_rate:.0%} over {harness_total} calls"
            )
        if disabled_jobs:
            alerts.append(f"orchestrator_disabled_jobs={sorted(set(disabled_jobs))}")

        # Advisor interpretation — when alerts are present, ask the advisor
        # to interpret the anomaly pattern. Non-fatal; skipped if unavailable.
        advisor_interpretation: str | None = None
        if alerts:
            advisor_interpretation = self._get_advisor_interpretation(alerts)

        custom = state.get("custom") or {}
        custom["last_workflow_ok"] = wf_ok
        custom["last_workflow_failed"] = wf_failed
        custom["last_failure_rate"] = round(failure_rate, 4)
        custom["last_harness_error_rate"] = round(harness_error_rate, 4)
        custom["last_disabled_jobs"] = sorted(set(disabled_jobs))
        custom["alerts"] = alerts
        custom["advisor_interpretation"] = advisor_interpretation
        custom["updated_at"] = datetime.now(timezone.utc).isoformat()
        state["custom"] = custom

        summary = (
            f"workflows ok={wf_ok} failed={wf_failed} "
            f"rate={failure_rate:.0%} "
            f"harness_err={harness_error_rate:.0%} "
            f"alerts={len(alerts)}"
        )
        if advisor_interpretation:
            summary += f" advisor_says={advisor_interpretation[:80]}"

        return TickResult(
            agent=self.name,
            ok=True,
            summary=summary,
            alerts=alerts,
            metadata={
                "workflows_total": total,
                "harness_total": harness_total,
                "disabled_jobs": sorted(set(disabled_jobs)),
                "advisor_interpretation": advisor_interpretation,
            },
        )

    def _get_advisor_interpretation(self, alerts: list[str]) -> str | None:
        """Ask the advisor to interpret system alerts. Non-fatal."""
        try:
            from core.advisor import call_advisor

            task = (
                "Interpret these EOS system alerts and suggest root causes:\n- "
                + "\n- ".join(alerts)
            )
            result = call_advisor(
                task=task,
                executor_output="\n".join(alerts),
                context={"is_critical_hub": False},
                metadata={"requires_advisor": True, "task_type": "analysis"},
                escalation_reason="observer_anomaly",
            )
            if result.reasoning:
                return result.reasoning[:500]
        except Exception:
            pass
        return None


# ---------------------------------------------------------------------------
# Healer
# ---------------------------------------------------------------------------


class HealerAgent(PersistentAgent):
    """Reacts to Observer alerts and stuck state.

    Conservative by design. Actions taken:
      1. If Observer reports disabled orchestrator jobs AND the job's last
         failure was >6h ago, emit a `job_reenable_requested` signal into
         agent state. (We don't directly re-enable — that's an operator
         decision until proven safe.)
      2. If Observer reports a failure rate alert, write a harness memory
         note so the next workflow sees it in semantic search.
      3. When the observer provides an advisor interpretation, include it
         in the memory note for richer context.

    Healer's capability profile is "healer" — EXECUTE level but with
    CRITICAL ops denied.
    """

    name = "healer"
    interval_sec = 300  # 5 min

    STUCK_COOLDOWN_SEC = 6 * 60 * 60

    def tick_impl(self, state: dict[str, Any]) -> TickResult:
        # Read the observer's most recent state
        observer_state_file = AGENT_STATE_DIR / "observer.json"
        observer: dict[str, Any] = {}
        if observer_state_file.exists():
            try:
                observer = json.loads(observer_state_file.read_text(encoding="utf-8"))
            except Exception:
                observer = {}

        obs_custom = observer.get("custom") or {}
        alerts: list[str] = obs_custom.get("alerts") or []
        disabled: list[str] = obs_custom.get("last_disabled_jobs") or []
        advisor_interp: str | None = obs_custom.get("advisor_interpretation")

        actions_taken: list[str] = []

        # Reaction 1: write a memory note about alerts so future runs learn
        if alerts:
            note = "HEALER ALERT — observer reports the following issues:\n- "
            note += "\n- ".join(alerts)
            if advisor_interp:
                note += f"\n\nAdvisor interpretation: {advisor_interp}"
            note += "\n\nHealer recommends operator review."
            mem = self.harness.remember(self.name, note, task_type="healer_alert")
            if mem.ok:
                actions_taken.append("memory_note")

        # Reaction 2: recommend re-enable for disabled jobs that are old
        reenable_candidates: list[str] = []
        if disabled:
            reenable_candidates = list(sorted(set(disabled)))

        custom = state.get("custom") or {}
        custom["last_alerts_seen"] = alerts
        custom["reenable_candidates"] = reenable_candidates
        custom["actions_taken_this_tick"] = actions_taken
        custom["advisor_interpretation_forwarded"] = bool(advisor_interp)
        custom["updated_at"] = datetime.now(timezone.utc).isoformat()
        state["custom"] = custom

        summary = (
            f"alerts={len(alerts)} reenable_candidates={len(reenable_candidates)} "
            f"actions={actions_taken}"
        )
        return TickResult(
            agent=self.name,
            ok=True,
            summary=summary,
            alerts=alerts,
            metadata={
                "reenable_candidates": reenable_candidates,
                "advisor_forwarded": bool(advisor_interp),
            },
        )


# ---------------------------------------------------------------------------
# Librarian
# ---------------------------------------------------------------------------


class LibrarianAgent(PersistentAgent):
    """Consolidates recent workflow runs into short notes and remembers them.

    One note per tick, max. The LLM call is dispatched via the harness so
    it obeys the capability profile + router fallback chain.

    Uses run_with_advisor when there are failed workflows in the digest,
    since those warrant higher-quality summarization.
    """

    name = "librarian"
    interval_sec = 30 * 60  # 30 min

    def tick_impl(self, state: dict[str, Any]) -> TickResult:
        rows = _tail_jsonl(DATA_DIR / "workflow_log.jsonl", 200)
        finished = [r for r in rows if r.get("event") == "workflow_finished"]
        if not finished:
            return TickResult(
                agent=self.name,
                ok=True,
                summary="no finished workflows to consolidate",
            )

        # Skip if no new workflows since last consolidation
        last_seen = (state.get("custom") or {}).get("last_consolidated_workflow")
        newest_id = finished[-1].get("workflow_id")
        if last_seen and newest_id == last_seen:
            return TickResult(
                agent=self.name,
                ok=True,
                summary=f"up-to-date ({newest_id})",
            )

        # Build a compact digest for the LLM
        digest_lines = []
        has_failures = False
        for r in finished[-10:]:
            status = r.get("workflow_status", "?")
            if status == "failed":
                has_failures = True
            digest_lines.append(
                f"- {r.get('workflow_name', '?')} "
                f"({r.get('workflow_id', '?')}) "
                f"→ {status}"
            )
        digest = "\n".join(digest_lines)

        prompt = (
            "Write a 3-sentence digest of the following recent EOS workflow "
            "runs. Highlight anything unusual. No preamble.\n\n"
            f"{digest}"
        )

        # Use advisor-gated execution when failures are present
        advisor_used = False
        if has_failures:
            llm = self.harness.run_with_advisor(
                self.name,
                prompt,
                context={"previous_step_failed": True},
                metadata={
                    "requires_advisor": False,
                    "advisor_on_failure": True,
                    "task_type": "summarize",
                },
                task_type="fast_response",
            )
            advisor_used = llm.metadata.get("advisor_used", False)
        else:
            llm = self.harness.run_llm(
                self.name,
                prompt,
                task_type="fast_response",
                trigger_source="librarian",
            )

        custom = state.get("custom") or {}
        custom["last_consolidated_workflow"] = newest_id
        custom["last_digest"] = llm.output if llm.ok else None
        custom["last_digest_ok"] = llm.ok
        custom["advisor_used"] = advisor_used
        custom["updated_at"] = datetime.now(timezone.utc).isoformat()
        state["custom"] = custom

        if llm.ok and llm.output:
            self.harness.remember(
                self.name,
                f"LIBRARIAN DIGEST — {newest_id}:\n{llm.output}",
                task_type="librarian_digest",
            )

        return TickResult(
            agent=self.name,
            ok=llm.ok,
            summary=(
                f"consolidated {len(finished)} workflows; "
                f"digest_ok={llm.ok} advisor={advisor_used}"
            ),
            metadata={
                "newest_id": newest_id,
                "provider": llm.provider,
                "advisor_used": advisor_used,
            },
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def default_agents(*, harness: AgentHarness | None = None) -> list[PersistentAgent]:
    """Build the default roster of persistent agents."""
    h = harness or default_harness()
    return [
        ObserverAgent(harness=h),
        HealerAgent(harness=h),
        LibrarianAgent(harness=h),
    ]


def _emit_agent_log(agent: str, result: TickResult) -> None:
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "ok": result.ok,
            "summary": result.summary,
            "duration_ms": result.duration_ms,
            "alerts": result.alerts,
        }
        with AGENT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass


__all__ = [
    "HealerAgent",
    "LibrarianAgent",
    "ObserverAgent",
    "PersistentAgent",
    "TickResult",
    "default_agents",
]
