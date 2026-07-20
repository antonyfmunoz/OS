"""Planning workflow — governed strategic planning with outcome tracking.

Steps: assess_current_state → identify_gaps → generate_options → create_plan

Deterministic-first: state assessment and gap identification use file-based
data. AI enhances option generation when available.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from projections.eos.workflows.types import WorkflowStep

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")


def _runtime_state_file(subsystem: str, filename: str) -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(runtime_state_path(subsystem, filename, create_parent=False))


_PLANS_DIR = os.path.join(_REPO_ROOT, "data", "umh", "plans")


@dataclass
class StateAssessment:
    velocity: dict[str, Any] = field(default_factory=dict)
    recent_outcomes: list[dict[str, Any]] = field(default_factory=list)
    active_tasks: int = 0
    blockers: list[str] = field(default_factory=list)


@dataclass
class PlanOption:
    name: str
    description: str
    effort: str = "medium"
    impact: str = "medium"
    tradeoffs: str = ""


class PlanningWorkflow:
    """Multi-step planning workflow through governed mutation."""

    def __init__(self, org_id: str = "", venture_id: str = "") -> None:
        self._org_id = org_id
        self._venture_id = venture_id
        self._goal: str = ""
        self._assessment: StateAssessment | None = None
        self._gaps: list[str] = []
        self._options: list[PlanOption] = []
        self._plan: str = ""

    def steps(self, goal: str) -> list[WorkflowStep]:
        return [
            WorkflowStep(
                name="assess_current_state",
                mutation_name="command_submit",
                intent=f"Assess current state for planning: {goal[:80]}",
                execute_fn=lambda: self._assess_state(goal),
            ),
            WorkflowStep(
                name="identify_gaps",
                mutation_name="command_submit",
                intent=f"Identify gaps toward: {goal[:80]}",
                execute_fn=self._identify_gaps,
            ),
            WorkflowStep(
                name="generate_options",
                mutation_name="command_submit",
                intent=f"Generate strategic options for: {goal[:80]}",
                execute_fn=self._generate_options,
            ),
            WorkflowStep(
                name="create_plan",
                mutation_name="file_write",
                intent=f"Create plan for: {goal[:80]}",
                execute_fn=self._create_plan,
            ),
        ]

    def _assess_state(self, goal: str) -> tuple[str, bool]:
        self._goal = goal
        self._assessment = StateAssessment()

        velocity_path = _runtime_state_file("work_portfolio", "velocity.jsonl")
        if os.path.exists(velocity_path):
            try:
                with open(velocity_path) as f:
                    lines = f.readlines()
                if lines:
                    last = json.loads(lines[-1])
                    self._assessment.velocity = last
            except (json.JSONDecodeError, OSError):
                pass

        outcomes_path = _runtime_state_file("organism", "outcome_learning.jsonl")
        if os.path.exists(outcomes_path):
            try:
                with open(outcomes_path) as f:
                    lines = f.readlines()
                recent = lines[-10:] if len(lines) >= 10 else lines
                for line in recent:
                    try:
                        self._assessment.recent_outcomes.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            except OSError:
                pass

        journal_path = _runtime_state_file("organism", "execution_journal.jsonl")
        if os.path.exists(journal_path):
            try:
                with open(journal_path) as f:
                    lines = f.readlines()
                active = sum(
                    1 for line in lines[-50:] if '"PROPOSED"' in line or '"IN_PROGRESS"' in line
                )
                self._assessment.active_tasks = active
            except OSError:
                pass

        summary = (
            f"State assessed: "
            f"{len(self._assessment.recent_outcomes)} recent outcomes, "
            f"{self._assessment.active_tasks} active tasks"
        )
        return (summary, True)

    def _identify_gaps(self) -> tuple[str, bool]:
        if not self._goal:
            return ("no goal defined", False)

        self._gaps = []

        if self._assessment:
            if self._assessment.active_tasks == 0:
                self._gaps.append("No active tasks — need to define work")
            if not self._assessment.recent_outcomes:
                self._gaps.append("No recent outcome data — need execution history")
            if not self._assessment.velocity:
                self._gaps.append("No velocity data — need portfolio tracking")

        goal_lower = self._goal.lower()
        if "revenue" in goal_lower or "sale" in goal_lower:
            self._gaps.append("Revenue goal — need lead pipeline and outreach cadence")
        if "content" in goal_lower or "brand" in goal_lower:
            self._gaps.append("Content goal — need content calendar and publishing cadence")
        if "build" in goal_lower or "ship" in goal_lower:
            self._gaps.append("Build goal — need clear deliverables and timeline")

        if not self._gaps:
            self._gaps.append("No obvious gaps detected — goal may need decomposition")

        return (f"Identified {len(self._gaps)} gaps", True)

    def _generate_options(self) -> tuple[str, bool]:
        if not self._goal or not self._gaps:
            return ("no gaps to address", False)

        self._options = [
            PlanOption(
                name="focused_sprint",
                description=f"Focus exclusively on '{self._goal}' for 7 days. Drop all non-essential work.",
                effort="high",
                impact="high",
                tradeoffs="High intensity, risk of burnout. Other priorities paused.",
            ),
            PlanOption(
                name="parallel_track",
                description=f"Allocate 50% capacity to '{self._goal}', maintain existing work.",
                effort="medium",
                impact="medium",
                tradeoffs="Balanced but slower progress. No major disruption.",
            ),
            PlanOption(
                name="quick_wins_first",
                description=f"Identify 3 quick wins toward '{self._goal}' and execute them this week.",
                effort="low",
                impact="low",
                tradeoffs="Fast momentum but may not address root gaps.",
            ),
        ]

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Given goal: {self._goal}\n"
                    f"Gaps: {'; '.join(self._gaps)}\n"
                    f"Suggest one additional strategic option (2 sentences max)."
                ),
                system="Strategic planning advisor. Be specific and actionable.",
                task_type="fast_response",
            )
            if result.output and len(result.output.strip()) > 20:
                self._options.append(
                    PlanOption(
                        name="ai_suggested",
                        description=result.output.strip()[:300],
                        effort="medium",
                        impact="high",
                        tradeoffs="AI-generated — validate before committing.",
                    )
                )
        except Exception:
            pass

        return (f"Generated {len(self._options)} strategic options", True)

    def _create_plan(self) -> tuple[str, bool]:
        if not self._goal or not self._options:
            return ("no options to create plan from", False)

        os.makedirs(_PLANS_DIR, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug = re.sub(r"[^a-z0-9]+", "_", self._goal.lower())[:40]
        filename = f"{date_str}_{slug}.md"
        filepath = os.path.join(_PLANS_DIR, filename)

        lines = [
            f"# Plan: {self._goal}",
            f"\n**Created**: {date_str}",
            "**Status**: DRAFT",
            "",
            "## Current State",
        ]

        if self._assessment:
            lines.append(f"- Recent outcomes: {len(self._assessment.recent_outcomes)}")
            lines.append(f"- Active tasks: {self._assessment.active_tasks}")

        lines.append("\n## Gaps")
        for gap in self._gaps:
            lines.append(f"- {gap}")

        lines.append("\n## Options")
        for opt in self._options:
            lines.append(f"\n### {opt.name}")
            lines.append(f"{opt.description}")
            lines.append(f"- Effort: {opt.effort} | Impact: {opt.impact}")
            if opt.tradeoffs:
                lines.append(f"- Tradeoffs: {opt.tradeoffs}")

        self._plan = "\n".join(lines)
        with open(filepath, "w") as f:
            f.write(self._plan)

        return (f"Plan created: {filepath}", True)
