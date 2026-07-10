"""Daily rhythm workflow — governed morning brief and end-of-day.

Wraps existing daily ritual commands in governed mutation so the
organism tracks the operator's daily cycle.

Steps vary by ritual:
- morning_brief: gather_state → generate_brief
- end_of_day: summarize_day → log_outcomes
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from projections.eos.workflows.types import WorkflowStep

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


@dataclass
class DayState:
    date: str = ""
    recent_outcomes: list[dict[str, Any]] = field(default_factory=list)
    active_tasks: int = 0
    velocity: dict[str, Any] = field(default_factory=dict)
    energy_score: int = 0


class DailyRhythmWorkflow:
    """Daily rhythm workflow through governed mutation."""

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._state: DayState | None = None
        self._brief: str = ""
        self._eod_summary: str = ""

    def brief_steps(self) -> list[WorkflowStep]:
        """Steps for morning brief."""
        return [
            WorkflowStep(
                name="gather_state",
                mutation_name="command_submit",
                intent="Gather state for morning brief",
                execute_fn=self._gather_state,
            ),
            WorkflowStep(
                name="generate_brief",
                mutation_name="command_submit",
                intent="Generate morning brief",
                execute_fn=self._generate_brief,
            ),
        ]

    def eod_steps(self) -> list[WorkflowStep]:
        """Steps for end-of-day."""
        return [
            WorkflowStep(
                name="summarize_day",
                mutation_name="command_submit",
                intent="Summarize today's work",
                execute_fn=self._summarize_day,
            ),
            WorkflowStep(
                name="log_outcomes",
                mutation_name="outcome_record",
                intent="Log end-of-day outcomes",
                execute_fn=self._log_outcomes,
            ),
        ]

    def _gather_state(self) -> tuple[str, bool]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._state = DayState(date=today)

        outcomes_path = os.path.join(
            _REPO_ROOT, "data", "umh", "organism", "outcome_learning.jsonl"
        )
        if os.path.exists(outcomes_path):
            try:
                with open(outcomes_path) as f:
                    lines = f.readlines()
                for line in lines[-20:]:
                    try:
                        entry = json.loads(line)
                        if entry.get("ts", "").startswith(today):
                            self._state.recent_outcomes.append(entry)
                    except json.JSONDecodeError:
                        continue
            except OSError:
                pass

        journal_path = os.path.join(
            _REPO_ROOT, "data", "umh", "organism", "execution_journal.jsonl"
        )
        if os.path.exists(journal_path):
            try:
                with open(journal_path) as f:
                    lines = f.readlines()
                active = 0
                for line in lines[-100:]:
                    try:
                        entry = json.loads(line)
                        if entry.get("ts", "").startswith(today):
                            if entry.get("event") == "workflow_start":
                                active += 1
                            elif entry.get("event") == "workflow_complete":
                                active -= 1
                    except json.JSONDecodeError:
                        continue
                self._state.active_tasks = max(0, active)
            except OSError:
                pass

        velocity_path = os.path.join(
            _REPO_ROOT, "data", "umh", "work_portfolio", "velocity.jsonl"
        )
        if os.path.exists(velocity_path):
            try:
                with open(velocity_path) as f:
                    lines = f.readlines()
                if lines:
                    self._state.velocity = json.loads(lines[-1])
            except (json.JSONDecodeError, OSError):
                pass

        return (
            f"State gathered for {today}: "
            f"{len(self._state.recent_outcomes)} outcomes today, "
            f"{self._state.active_tasks} active tasks",
            True,
        )

    def _generate_brief(self) -> tuple[str, bool]:
        if not self._state:
            return ("no state gathered", False)

        parts = [f"# Morning Brief — {self._state.date}\n"]

        if self._state.recent_outcomes:
            parts.append(f"**Yesterday's outcomes**: {len(self._state.recent_outcomes)}")
            for outcome in self._state.recent_outcomes[:5]:
                desc = outcome.get("description", outcome.get("type", "unknown"))
                parts.append(f"  - {desc[:80]}")
        else:
            parts.append("**No recent outcomes recorded.**")

        parts.append(f"\n**Active tasks**: {self._state.active_tasks}")

        if self._state.velocity:
            vel = self._state.velocity
            parts.append(
                f"**Velocity**: {vel.get('completed', 0)} completed, "
                f"{vel.get('in_progress', 0)} in progress"
            )

        from projections.eos import instance

        _offer = instance.offer_name(instance.load_bis(self._org_id, self._venture_id))
        parts.append(
            f"\n**Focus today**: Check {_offer} pipeline. Execute highest-leverage task."
        )

        self._brief = "\n".join(parts)

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Given this operator state, suggest the single most important "
                    f"thing to focus on today (1-2 sentences):\n\n{self._brief}"
                ),
                system="Strategic advisor. Be direct. One priority only.",
                task_type="fast_response",
            )
            if result.output and len(result.output.strip()) > 10:
                self._brief += f"\n\n**AI Priority**: {result.output.strip()[:200]}"
        except Exception:
            pass

        return (self._brief, True)

    def _summarize_day(self) -> tuple[str, bool]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        journal_path = os.path.join(
            _REPO_ROOT, "data", "umh", "organism", "execution_journal.jsonl"
        )
        workflows_today: list[dict[str, Any]] = []
        if os.path.exists(journal_path):
            try:
                with open(journal_path) as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if (entry.get("ts", "").startswith(today)
                                    and entry.get("event") == "workflow_complete"):
                                workflows_today.append(entry)
                        except json.JSONDecodeError:
                            continue
            except OSError:
                pass

        succeeded = sum(1 for w in workflows_today if w.get("success"))
        failed = len(workflows_today) - succeeded

        self._eod_summary = (
            f"EOD {today}: "
            f"{len(workflows_today)} workflows "
            f"({succeeded} succeeded, {failed} failed)"
        )

        return (self._eod_summary, True)

    def _log_outcomes(self) -> tuple[str, bool]:
        if not self._eod_summary:
            return ("no day summary", False)

        outcome_path = os.path.join(
            _REPO_ROOT, "data", "umh", "organism", "outcome_learning.jsonl"
        )
        os.makedirs(os.path.dirname(outcome_path), exist_ok=True)

        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": "eod_summary",
            "summary": self._eod_summary,
        }

        try:
            with open(outcome_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as exc:
            logger.debug("outcome write failed: %s", exc)

        return (f"EOD logged: {self._eod_summary}", True)
