"""Predictive planner — generates speculative execution plans from intents.

Converts UserIntent predictions into PlanObjective + ExecutionPlan
structures that are structurally identical to real plans but tagged
as speculative. Predicted plans NEVER execute automatically.

Pure computation — no I/O, no state mutation, no subprocess.

No imports from umh/cells, umh/environments, umh/adapters, subprocess, or shell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any

from umh.planning.models import (
    ExecutionPlan,
    ExecutionPlanStep,
    PlanObjective,
    PlanSource,
    PlanStatus,
)
from umh.prediction.intent import UserIntent


@unique
class PredictionPolicy(str, Enum):
    """Governance policy for predictive execution."""

    DISABLED = "disabled"
    SUGGEST_ONLY = "suggest_only"
    AUTO_EXECUTE_LOW_RISK = "auto_execute_low_risk"
    REQUIRE_APPROVAL = "require_approval"


_DEFAULT_POLICY = PredictionPolicy.SUGGEST_ONLY
_MAX_CACHED_PREDICTIONS = 20


@dataclass(frozen=True)
class PredictedPlan:
    """A speculative plan derived from an intent prediction.

    Always tagged speculative=True. Discardable at any time.
    Never mutates system state directly.
    """

    intent: UserIntent
    plan: ExecutionPlan
    speculative: bool = True
    policy: PredictionPolicy = PredictionPolicy.SUGGEST_ONLY
    approved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "plan": self.plan.to_dict(),
            "speculative": self.speculative,
            "policy": self.policy.value,
            "approved": self.approved,
        }

    @property
    def can_auto_execute(self) -> bool:
        if self.policy == PredictionPolicy.DISABLED:
            return False
        if self.policy == PredictionPolicy.SUGGEST_ONLY:
            return False
        if self.policy == PredictionPolicy.REQUIRE_APPROVAL:
            return self.approved
        if self.policy == PredictionPolicy.AUTO_EXECUTE_LOW_RISK:
            return self.intent.confidence >= 0.8
        return False


class PredictivePlanner:
    """Generates speculative plans from predicted intents.

    Plans follow the full decomposition pipeline and are
    structurally identical to real plans. The only difference
    is the speculative tag and governance policy gate.
    """

    def __init__(
        self,
        *,
        policy: PredictionPolicy = _DEFAULT_POLICY,
        max_cached: int = _MAX_CACHED_PREDICTIONS,
    ) -> None:
        self._policy = policy
        self._max_cached = max_cached
        self._cache: list[PredictedPlan] = []

    @property
    def policy(self) -> PredictionPolicy:
        return self._policy

    @property
    def cached_plans(self) -> list[PredictedPlan]:
        return list(self._cache)

    def set_policy(self, policy: PredictionPolicy) -> None:
        self._policy = policy

    def predict_plan(self, intent: UserIntent) -> PredictedPlan | None:
        """Generate a speculative plan from a predicted intent.

        Returns None if policy is DISABLED.
        """
        if self._policy == PredictionPolicy.DISABLED:
            return None

        objective = PlanObjective(
            title=f"Predicted: {intent.inferred_goal}",
            description=f"Speculative objective from intent {intent.intent_id}",
            constraints=["speculative — do not auto-execute without governance"],
            context={
                "source": "prediction",
                "intent_id": intent.intent_id,
                "confidence": intent.confidence,
                "speculative": True,
            },
            requested_by="prediction_engine",
            dry_run=True,
        )

        steps = self._decompose_intent(intent)

        plan = ExecutionPlan(
            objective=objective,
            steps=steps,
            source=PlanSource.TEMPLATE,
            confidence=intent.confidence,
            assumptions=[
                f"Based on intent: {intent.inferred_goal}",
                f"Confidence: {intent.confidence:.2f}",
                f"Source: {intent.source}",
            ],
            status=PlanStatus.DRAFT,
        )

        predicted = PredictedPlan(
            intent=intent,
            plan=plan,
            speculative=True,
            policy=self._policy,
        )

        self._cache_plan(predicted)
        return predicted

    def predict_plans(self, intents: list[UserIntent]) -> list[PredictedPlan]:
        """Generate plans for multiple intents. Filters None results."""
        plans: list[PredictedPlan] = []
        for intent in intents:
            predicted = self.predict_plan(intent)
            if predicted is not None:
                plans.append(predicted)
        return plans

    def clear_cache(self) -> None:
        self._cache.clear()

    def discard_plan(self, intent_id: str) -> bool:
        """Remove a cached predicted plan by intent_id."""
        before = len(self._cache)
        self._cache = [p for p in self._cache if p.intent.intent_id != intent_id]
        return len(self._cache) < before

    def get_state(self) -> dict[str, Any]:
        return {
            "policy": self._policy.value,
            "cached_plans": len(self._cache),
            "max_cached": self._max_cached,
        }

    def _decompose_intent(self, intent: UserIntent) -> list[ExecutionPlanStep]:
        """Break an intent into execution steps. Heuristic decomposition."""
        steps: list[ExecutionPlanStep] = []

        for i, action in enumerate(intent.predicted_actions):
            steps.append(
                ExecutionPlanStep(
                    name=f"step_{i + 1}_{action}",
                    operation=action,
                    inputs={
                        "task_type": intent.related_entities[0]
                        if intent.related_entities
                        else "unknown",
                        "speculative": True,
                    },
                    execution_class="predicted",
                    constraints={"speculative": True, "requires_governance": True},
                    rationale=f"Predicted from {intent.source}: {intent.inferred_goal}",
                )
            )

        if not steps:
            steps.append(
                ExecutionPlanStep(
                    name="evaluate_intent",
                    operation="evaluate",
                    inputs={"goal": intent.inferred_goal, "speculative": True},
                    execution_class="predicted",
                    constraints={"speculative": True, "requires_governance": True},
                    rationale=f"Evaluate predicted goal: {intent.inferred_goal}",
                )
            )

        return steps

    def _cache_plan(self, plan: PredictedPlan) -> None:
        self._cache.append(plan)
        if len(self._cache) > self._max_cached:
            self._cache = self._cache[-self._max_cached :]
