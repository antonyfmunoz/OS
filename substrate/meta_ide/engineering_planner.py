"""Engineering Planner — deterministic planning from high-level intent.

Decomposes operator engineering intent into reviewable plans enriched
with workspace health, roadmap context, and engineering risk assessment.
Plans are review artifacts — no execution, no mutation, no LLM calls.

Phase 22. UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from substrate.meta_ide.engineering_intent import (
    EngineeringIntent,
    EngineeringIntentType,
    EngineeringPlan,
    EngineeringTask,
    classify_engineering_intent,
    extract_goal,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

_TASK_TEMPLATES: dict[str, list[tuple[str, str, str]]] = {
    "feature": [
        ("research", "Research", "Analyze requirements and existing code"),
        ("planning", "Design", "Design implementation approach"),
        ("implementation", "Implement", "Write the implementation"),
        ("testing", "Test", "Write and run tests"),
        ("verification", "Verify", "Verify integration and quality"),
    ],
    "bugfix": [
        ("research", "Diagnose", "Identify root cause"),
        ("implementation", "Fix", "Implement the fix"),
        ("testing", "Test", "Verify fix and add regression test"),
    ],
    "refactor": [
        ("research", "Analyze", "Analyze current state and plan changes"),
        ("implementation", "Refactor", "Apply refactoring"),
        ("testing", "Test", "Verify behavior preserved"),
        ("verification", "Verify", "Run full gate checks"),
    ],
    "infrastructure": [
        ("planning", "Plan", "Plan infrastructure change"),
        ("implementation", "Implement", "Apply infrastructure change"),
        ("verification", "Verify", "Verify deployment and health"),
    ],
    "research": [
        ("research", "Research", "Investigate the topic"),
        ("planning", "Synthesize", "Synthesize findings"),
        ("verification", "Recommend", "Produce recommendations"),
    ],
}

_LOW_RISK_TASK_TYPES = frozenset({"research", "testing", "verification", "planning"})

_RISK_ORDER = ["low", "medium", "high", "critical"]

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "engineering": ["code", "api", "endpoint", "module", "function", "class", "test"],
    "infrastructure": ["deploy", "docker", "server", "database", "config", "ci", "cd"],
    "security": ["auth", "permission", "token", "credential", "encrypt", "ssl"],
    "frontend": ["ui", "cockpit", "panel", "component", "react", "css", "layout"],
    "backend": ["route", "handler", "middleware", "service", "worker", "queue"],
    "data": ["schema", "migration", "table", "query", "index", "backup"],
}


class EngineeringPlanner:
    """Deterministic engineering planner. No LLM calls, no execution."""

    def __init__(
        self,
        workspace_engine: Any | None = None,
        roadmap_intelligence: Any | None = None,
        reality_engine: Any | None = None,
    ) -> None:
        self._workspace = workspace_engine
        self._roadmap = roadmap_intelligence
        self._reality = reality_engine
        self._plans: dict[str, EngineeringPlan] = {}

    def create_plan(
        self,
        raw_input: str,
        desired_end_state: str = "",
        constraints: list[str] | None = None,
    ) -> EngineeringPlan:
        """Create an engineering plan from high-level intent.

        All deterministic: regex classification, template decomposition,
        context enrichment from MetaIDE/Roadmap/Reality engines.
        """
        intent_type = classify_engineering_intent(raw_input)
        goal = extract_goal(raw_input)

        intent = EngineeringIntent(
            raw_input=raw_input,
            intent_type=intent_type,
            goal=goal,
            scope=self._detect_scope(raw_input),
            constraints=constraints or [],
            success_criteria=self._generate_success_criteria(goal, intent_type),
            affected_repos=self._detect_affected_repos(raw_input),
            affected_domains=self._detect_affected_domains(raw_input),
            estimated_risk=self._estimate_intent_risk(intent_type, raw_input),
        )

        if desired_end_state:
            intent.success_criteria.insert(0, desired_end_state)

        tasks = self._build_tasks(intent)
        dep_graph = self._build_dependency_graph(tasks)

        roadmap_ctx = self._get_roadmap_context()
        ws_health = self._get_workspace_health()
        eng_risks = self._get_engineering_risks()

        total_risk = self._assess_plan_risk(tasks, ws_health)

        plan = EngineeringPlan(
            intent=intent,
            tasks=tasks,
            dependency_graph=dep_graph,
            estimated_total_risk=total_risk,
            roadmap_context=roadmap_ctx,
            workspace_health=ws_health,
            engineering_risks=eng_risks,
        )

        self._plans[plan.plan_id] = plan
        return plan

    def get_plan(self, plan_id: str) -> EngineeringPlan | None:
        return self._plans.get(plan_id)

    def list_plans(self) -> list[EngineeringPlan]:
        return list(self._plans.values())

    def update_plan_status(self, plan_id: str, status: str) -> bool:
        plan = self._plans.get(plan_id)
        if not plan:
            return False
        plan.status = status
        return True

    def assess_risk(self, plan: EngineeringPlan) -> str:
        return self._assess_plan_risk(plan.tasks, plan.workspace_health)

    # ── Private helpers ─────────────────────────────────────────────────

    def _build_tasks(self, intent: EngineeringIntent) -> list[EngineeringTask]:
        templates = _TASK_TEMPLATES.get(
            intent.intent_type.value,
            _TASK_TEMPLATES["feature"],
        )
        tasks: list[EngineeringTask] = []
        for task_type, label, desc_template in templates:
            task = EngineeringTask(
                title=f"{label}: {intent.goal}",
                description=f"{desc_template} for: {intent.raw_input}",
                task_type=task_type,
                risk_class=self._assess_task_risk(task_type, intent.estimated_risk),
                validation_requirements=self._task_validation(task_type),
            )
            tasks.append(task)
        return tasks

    @staticmethod
    def _build_dependency_graph(
        tasks: list[EngineeringTask],
    ) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {}
        for i, task in enumerate(tasks):
            if i == 0:
                graph[task.task_id] = []
            else:
                graph[task.task_id] = [tasks[i - 1].task_id]
                task.dependencies = [tasks[i - 1].task_id]
        return graph

    @staticmethod
    def _assess_task_risk(task_type: str, intent_risk: str) -> str:
        if task_type in _LOW_RISK_TASK_TYPES:
            return "low"
        return intent_risk

    @staticmethod
    def _assess_plan_risk(
        tasks: list[EngineeringTask],
        workspace_health: dict[str, Any],
    ) -> str:
        worst = "low"
        for task in tasks:
            if _RISK_ORDER.index(task.risk_class) > _RISK_ORDER.index(worst):
                worst = task.risk_class

        ws_risk = workspace_health.get("overall_risk", "none")
        if ws_risk in _RISK_ORDER:
            if _RISK_ORDER.index(ws_risk) > _RISK_ORDER.index(worst):
                worst = ws_risk

        return worst

    @staticmethod
    def _task_validation(task_type: str) -> list[str]:
        validations: dict[str, list[str]] = {
            "research": ["findings documented"],
            "planning": ["approach documented", "risks identified"],
            "implementation": ["py_compile passes", "imports clean", "gate checks pass"],
            "testing": ["tests pass", "coverage adequate"],
            "verification": ["integration verified", "no regressions"],
        }
        return validations.get(task_type, ["output reviewed"])

    def _detect_scope(self, raw_input: str) -> list[str]:
        scope: list[str] = []
        text_lower = raw_input.lower()
        scope_keywords = {
            "substrate": ["substrate", "core", "types", "execution"],
            "transports": ["api", "route", "endpoint", "http", "discord"],
            "adapters": ["adapter", "model", "router", "llm"],
            "cockpit": ["cockpit", "panel", "ui", "frontend", "dashboard"],
            "tests": ["test", "coverage", "verification"],
        }
        for area, keywords in scope_keywords.items():
            if any(kw in text_lower for kw in keywords):
                scope.append(area)
        return scope or ["general"]

    def _detect_affected_repos(self, raw_input: str) -> list[str]:
        if not self._workspace:
            return [_REPO_ROOT]
        try:
            summary = self._workspace.workspace_summary()
            return (
                [r.get("path", _REPO_ROOT) for r in summary.repositories]
                if hasattr(summary, "repositories")
                else [_REPO_ROOT]
            )
        except Exception:
            return [_REPO_ROOT]

    @staticmethod
    def _detect_affected_domains(raw_input: str) -> list[str]:
        text_lower = raw_input.lower()
        domains: list[str] = []
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                domains.append(domain)
        return domains or ["engineering"]

    @staticmethod
    def _estimate_intent_risk(
        intent_type: EngineeringIntentType,
        raw_input: str,
    ) -> str:
        high_risk_signals = re.compile(
            r"\b(production|deploy|migrate|database|schema|delete|remove|drop)\b",
            re.IGNORECASE,
        )
        if high_risk_signals.search(raw_input):
            return "high"
        risk_map: dict[str, str] = {
            "feature": "medium",
            "bugfix": "medium",
            "refactor": "medium",
            "infrastructure": "high",
            "research": "low",
        }
        return risk_map.get(intent_type.value, "medium")

    @staticmethod
    def _generate_success_criteria(
        goal: str,
        intent_type: EngineeringIntentType,
    ) -> list[str]:
        base = [f"{goal} complete"]
        type_criteria: dict[str, list[str]] = {
            "feature": ["tests written and passing", "imports clean", "gate checks pass"],
            "bugfix": ["bug no longer reproducible", "regression test added"],
            "refactor": ["behavior preserved", "code quality improved", "tests pass"],
            "infrastructure": ["deployment verified", "health checks pass"],
            "research": ["findings documented", "recommendations provided"],
        }
        base.extend(type_criteria.get(intent_type.value, []))
        return base

    def _get_roadmap_context(self) -> dict[str, Any]:
        if not self._roadmap:
            return {}
        try:
            status = self._roadmap.status()
            current = self._roadmap.current_phase()
            return {
                "total_phases": status.total_phases if hasattr(status, "total_phases") else 0,
                "completed_phases": status.completed_phases
                if hasattr(status, "completed_phases")
                else 0,
                "current_phase": current.phase_number
                if current and hasattr(current, "phase_number")
                else "",
                "current_phase_title": current.title
                if current and hasattr(current, "title")
                else "",
            }
        except Exception:
            return {}

    def _get_workspace_health(self) -> dict[str, Any]:
        if not self._workspace:
            return {}
        try:
            summary = self._workspace.engineering_summary()
            return summary if isinstance(summary, dict) else {}
        except Exception:
            return {}

    def _get_engineering_risks(self) -> list[dict[str, Any]]:
        if not self._workspace:
            return []
        try:
            summary = self._workspace.engineering_summary()
            if isinstance(summary, dict):
                return summary.get("risks", [])
            return []
        except Exception:
            return []
