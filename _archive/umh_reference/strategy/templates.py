"""UMH Strategy Templates — deterministic decomposition patterns.

Each template maps a goal pattern to a fixed set of StrategySteps.
Templates are matched by keyword analysis — no LLM involved.
Deterministic: same objective → same template → same steps.
"""

from __future__ import annotations

import re

from umh.strategy.models import (
    ApproachType,
    StepComplexity,
    StepType,
    Strategy,
    StrategyStep,
)


def _kw(text: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in text (case-insensitive)."""
    lower = text.lower()
    return any(k in lower for k in keywords)


# ── Template definitions ─────────────────────────────────────────


def _build_system_template(goal_id: str, objective: str) -> Strategy:
    """build/create/implement X system"""
    return Strategy(
        goal_id=goal_id,
        objective=objective,
        approach_type=ApproachType.LINEAR,
        confidence=0.9,
        reasoning="Matched 'build system' template: research → design → implement → validate → deploy",
        template_used="build_system",
        steps=[
            StrategyStep(
                description=f"Research requirements and constraints for: {objective}",
                type=StepType.RESEARCH,
                estimated_complexity=StepComplexity.LOW,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Design architecture and interfaces for: {objective}",
                type=StepType.DECISION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Implement core functionality for: {objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.HIGH,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Validate and test implementation for: {objective}",
                type=StepType.VALIDATION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Deploy and activate: {objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.LOW,
                generates_tasks=True,
            ),
        ],
    )


def _monitor_template(goal_id: str, objective: str) -> Strategy:
    """monitor/observe/track X"""
    return Strategy(
        goal_id=goal_id,
        objective=objective,
        approach_type=ApproachType.LINEAR,
        confidence=0.9,
        reasoning="Matched 'monitor' template: define metrics → collect data → evaluate → alert",
        template_used="monitor",
        steps=[
            StrategyStep(
                description=f"Define metrics and thresholds for: {objective}",
                type=StepType.RESEARCH,
                estimated_complexity=StepComplexity.LOW,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Set up data collection for: {objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Evaluate baseline and patterns for: {objective}",
                type=StepType.VALIDATION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Configure alerts and responses for: {objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.LOW,
                generates_tasks=True,
            ),
        ],
    )


def _automate_template(goal_id: str, objective: str) -> Strategy:
    """automate/schedule/recurring X"""
    return Strategy(
        goal_id=goal_id,
        objective=objective,
        approach_type=ApproachType.LINEAR,
        confidence=0.9,
        reasoning="Matched 'automate' template: identify steps → define triggers → implement → test",
        template_used="automate",
        steps=[
            StrategyStep(
                description=f"Identify manual steps to automate for: {objective}",
                type=StepType.RESEARCH,
                estimated_complexity=StepComplexity.LOW,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Define triggers and conditions for: {objective}",
                type=StepType.DECISION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Implement automation pipeline for: {objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.HIGH,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Test and validate automation for: {objective}",
                type=StepType.VALIDATION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
        ],
    )


def _analyze_template(goal_id: str, objective: str) -> Strategy:
    """analyze/investigate/audit/review X"""
    return Strategy(
        goal_id=goal_id,
        objective=objective,
        approach_type=ApproachType.LINEAR,
        confidence=0.85,
        reasoning="Matched 'analyze' template: gather data → analyze → synthesize → report",
        template_used="analyze",
        steps=[
            StrategyStep(
                description=f"Gather data and context for: {objective}",
                type=StepType.RESEARCH,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Analyze patterns and findings for: {objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.HIGH,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Synthesize insights and recommendations for: {objective}",
                type=StepType.DECISION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Generate report for: {objective}",
                type=StepType.VALIDATION,
                estimated_complexity=StepComplexity.LOW,
                generates_tasks=True,
            ),
        ],
    )


def _fix_template(goal_id: str, objective: str) -> Strategy:
    """fix/repair/resolve/debug X"""
    return Strategy(
        goal_id=goal_id,
        objective=objective,
        approach_type=ApproachType.LINEAR,
        confidence=0.85,
        reasoning="Matched 'fix' template: diagnose → identify root cause → implement fix → verify",
        template_used="fix",
        steps=[
            StrategyStep(
                description=f"Diagnose and reproduce issue for: {objective}",
                type=StepType.RESEARCH,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Identify root cause for: {objective}",
                type=StepType.DECISION,
                estimated_complexity=StepComplexity.HIGH,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Implement fix for: {objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Verify fix and regression test for: {objective}",
                type=StepType.VALIDATION,
                estimated_complexity=StepComplexity.LOW,
                generates_tasks=True,
            ),
        ],
    )


def _migrate_template(goal_id: str, objective: str) -> Strategy:
    """migrate/upgrade/transition X"""
    return Strategy(
        goal_id=goal_id,
        objective=objective,
        approach_type=ApproachType.PHASED,
        confidence=0.85,
        reasoning="Matched 'migrate' template: assess → plan → execute → validate → cutover",
        template_used="migrate",
        steps=[
            StrategyStep(
                description=f"Assess current state and requirements for: {objective}",
                type=StepType.RESEARCH,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Plan migration path for: {objective}",
                type=StepType.DECISION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Execute migration for: {objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.HIGH,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Validate migration results for: {objective}",
                type=StepType.VALIDATION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Cutover and decommission old system for: {objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.LOW,
                generates_tasks=True,
            ),
        ],
    )


def _optimize_template(goal_id: str, objective: str) -> Strategy:
    """optimize/improve/enhance/speed up X"""
    return Strategy(
        goal_id=goal_id,
        objective=objective,
        approach_type=ApproachType.LINEAR,
        confidence=0.8,
        reasoning="Matched 'optimize' template: baseline → identify bottlenecks → optimize → measure",
        template_used="optimize",
        steps=[
            StrategyStep(
                description=f"Establish baseline metrics for: {objective}",
                type=StepType.RESEARCH,
                estimated_complexity=StepComplexity.LOW,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Identify bottlenecks and opportunities for: {objective}",
                type=StepType.DECISION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Implement optimizations for: {objective}",
                type=StepType.EXECUTION,
                estimated_complexity=StepComplexity.HIGH,
                generates_tasks=True,
            ),
            StrategyStep(
                description=f"Measure improvement and validate for: {objective}",
                type=StepType.VALIDATION,
                estimated_complexity=StepComplexity.MEDIUM,
                generates_tasks=True,
            ),
        ],
    )


# ── Template registry ────────────────────────────────────────────

_TEMPLATES: list[tuple[list[str], callable]] = [
    (
        ["build", "create", "implement", "develop", "set up", "setup"],
        _build_system_template,
    ),
    (["monitor", "observe", "track", "watch", "alert"], _monitor_template),
    (
        ["automate", "schedule", "recurring", "cron", "periodic"],
        _automate_template,
    ),
    (
        ["analyze", "investigate", "audit", "review", "assess", "evaluate"],
        _analyze_template,
    ),
    (
        ["fix", "repair", "resolve", "debug", "patch", "hotfix"],
        _fix_template,
    ),
    (
        ["migrate", "upgrade", "transition", "move", "convert"],
        _migrate_template,
    ),
    (
        ["optimize", "improve", "enhance", "speed up", "performance", "tune"],
        _optimize_template,
    ),
]


def match_template(goal_id: str, objective: str) -> Strategy | None:
    """Match an objective against known templates.

    Returns a Strategy if a template matches, None otherwise.
    Deterministic: same objective → same template → same steps.
    """
    for keywords, builder in _TEMPLATES:
        if _kw(objective, keywords):
            strategy = builder(goal_id, objective)
            # Wire up sequential dependencies for LINEAR strategies
            if strategy.approach_type == ApproachType.LINEAR and len(strategy.steps) > 1:
                for i in range(1, len(strategy.steps)):
                    strategy.steps[i].dependencies = [strategy.steps[i - 1].id]
            elif strategy.approach_type == ApproachType.PHASED and len(strategy.steps) > 1:
                for i in range(1, len(strategy.steps)):
                    strategy.steps[i].dependencies = [strategy.steps[i - 1].id]
            return strategy
    return None


def list_templates() -> list[dict]:
    """Return metadata about available templates."""
    result = []
    for keywords, builder in _TEMPLATES:
        name = builder.__name__.replace("_template", "").lstrip("_")
        doc = builder.__doc__ or ""
        result.append(
            {
                "name": name,
                "keywords": keywords,
                "description": doc.strip(),
            }
        )
    return result
