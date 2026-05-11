"""
Deterministic task decomposition — breaks tasks into ordered pipeline steps.

Uses keyword heuristics (zero LLM cost) to infer an agent role and select
a template pipeline. Three templates for v1:

  builder  (4 steps): analyze → execute → verify → summarize
  product  (3 steps): analyze → produce → summarize
  ceo/portfolio (3 steps): analyze → recommend → summarize

Design rules (mirror substrate conventions):
- Deterministic — same input always produces same template.
- No LLM calls — pure regex matching for role inference.
- Additive only — never imported on the hot path.
"""

from __future__ import annotations

import re
import sys
from typing import TYPE_CHECKING

from eos_ai.transport.task_pipeline import (
    PipelineAgentRole,
    PipelineStep,
    PipelineStatus,
    StepStatus,
    TaskPipeline,
)

if TYPE_CHECKING:
    from eos_ai.transport.task_system import Task


def _log(msg: str) -> None:
    print(f"[substrate.task_decomposition] {msg}", file=sys.stderr)


# ─── Agent Role Inference ─────────────────────────────────────────────────────

_BUILDER_RE = re.compile(
    r"\b(build|code|debug|fix|patch|repo|script|test|deploy|refactor"
    r"|schema|docker|tmux|api|module|class|function|migration|lint)\b",
    re.IGNORECASE,
)

_PORTFOLIO_RE = re.compile(
    r"\b(portfolio|investment|capital|allocation|watchlist|risk|asset"
    r"|fund|equity|dividend|return)\b",
    re.IGNORECASE,
)

_CEO_RE = re.compile(
    r"\b(strategy|company|priorities|offer|business|revenue|growth"
    r"|roadmap|hire|budget|decision|direction)\b",
    re.IGNORECASE,
)

_PRODUCT_RE = re.compile(
    r"\b(product|content|message|customer|market|launch|campaign"
    r"|outreach|audience|brand|copy|email|social)\b",
    re.IGNORECASE,
)


def infer_agent_role(task: "Task") -> PipelineAgentRole:
    """Infer the pipeline agent role from task title + description.

    Priority order: builder > portfolio > ceo > product > general.
    Uses combined text of title + description for matching.
    """
    text = task.title
    if task.description:
        text = f"{text} {task.description}"

    if _BUILDER_RE.search(text):
        return PipelineAgentRole.BUILDER
    if _PORTFOLIO_RE.search(text):
        return PipelineAgentRole.PORTFOLIO
    if _CEO_RE.search(text):
        return PipelineAgentRole.CEO
    if _PRODUCT_RE.search(text):
        return PipelineAgentRole.PRODUCT
    return PipelineAgentRole.GENERAL


# ─── Pipeline Templates ──────────────────────────────────────────────────────


def _builder_steps(role: PipelineAgentRole) -> list[PipelineStep]:
    """4-step template for builder/code tasks."""
    return [
        PipelineStep.new(
            "Analyze task",
            step_index=0,
            agent_role=role,
            description="Read current state of affected files, understand scope, identify constraints.",
            status=StepStatus.READY,
        ),
        PipelineStep.new(
            "Execute change",
            step_index=1,
            agent_role=role,
            description="Implement the required code change, configuration, or fix.",
        ),
        PipelineStep.new(
            "Verify result",
            step_index=2,
            agent_role=role,
            description="Run import checks, tests, or verification commands to confirm correctness.",
        ),
        PipelineStep.new(
            "Summarize outcome",
            step_index=3,
            agent_role=role,
            description="Produce a concise summary of what changed, what was verified, and any follow-ups.",
        ),
    ]


def _product_steps(role: PipelineAgentRole) -> list[PipelineStep]:
    """3-step template for product/general execution tasks."""
    return [
        PipelineStep.new(
            "Analyze request",
            step_index=0,
            agent_role=role,
            description="Understand the request, gather context, identify deliverables.",
            status=StepStatus.READY,
        ),
        PipelineStep.new(
            "Produce output",
            step_index=1,
            agent_role=role,
            description="Create the requested deliverable — content, analysis, or action.",
        ),
        PipelineStep.new(
            "Summarize outcome",
            step_index=2,
            agent_role=role,
            description="Summarize what was produced and any next steps.",
        ),
    ]


def _ceo_portfolio_steps(role: PipelineAgentRole) -> list[PipelineStep]:
    """3-step template for CEO/portfolio strategy tasks."""
    return [
        PipelineStep.new(
            "Analyze context",
            step_index=0,
            agent_role=role,
            description="Review current state, constraints, and relevant data points.",
            status=StepStatus.READY,
        ),
        PipelineStep.new(
            "Generate recommendation",
            step_index=1,
            agent_role=role,
            description="Produce a structured recommendation or decision framework.",
        ),
        PipelineStep.new(
            "Summarize decision points",
            step_index=2,
            agent_role=role,
            description="Summarize key findings, recommended action, and trade-offs.",
        ),
    ]


# ─── Template Selection ──────────────────────────────────────────────────────

_TEMPLATE_MAP = {
    PipelineAgentRole.BUILDER: _builder_steps,
    PipelineAgentRole.CEO: _ceo_portfolio_steps,
    PipelineAgentRole.PORTFOLIO: _ceo_portfolio_steps,
    PipelineAgentRole.PRODUCT: _product_steps,
    PipelineAgentRole.GENERAL: _product_steps,
}


# ─── Public API ───────────────────────────────────────────────────────────────


def decompose_task(task: "Task") -> TaskPipeline:
    """Decompose a task into a linear pipeline of typed steps.

    Uses deterministic keyword matching to select the template.
    Step 0 is always READY; subsequent steps start as PENDING.
    The pipeline starts in READY status.

    Args:
        task: The task to decompose.

    Returns:
        A new TaskPipeline with steps populated from the template.
    """
    role = infer_agent_role(task)
    template_fn = _TEMPLATE_MAP.get(role, _product_steps)
    steps = template_fn(role)

    pipeline = TaskPipeline.new(
        task_id=task.task_id,
        title=task.title,
        agent_owner=role,
        steps=steps,
        day_session_id=task.day_session_id,
        queue_name=task.queue_name,
        priority=task.priority,
    )

    _log(
        f"decomposed {task.task_id} → {pipeline.pipeline_id} "
        f"role={role.value} steps={len(steps)}"
    )
    return pipeline


# ─── Exports ──────────────────────────────────────────────────────────────────

__all__ = [
    "infer_agent_role",
    "decompose_task",
]
