"""Tests for PlanRegistry — deterministic plan derivation.

Validates:
1. Registration and lookup of plan generators.
2. derive_plan returns correct Plan for known intent types.
3. derive_plan returns None for unknown types and empty generators.
4. with_defaults() loads built-in generators from planner.py.
5. Plan determinism: same inputs always produce the same plan.
6. Generator exceptions produce None, not crashes.
"""

from __future__ import annotations

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from umh.substrate.intent_models import (
    Intent,
    IntentStatus,
    IntentType,
    PlanStep,
)
from umh.substrate.plan_registry import PlanRegistry


def _make_intent(
    intent_type: IntentType = IntentType.LIFECYCLE_FINALIZE,
    goal: dict | None = None,
    session_name: str = "test_session",
) -> Intent:
    from umh.substrate.intent_models import compute_intent_id

    goal = goal or {"session_name": session_name}
    return Intent(
        intent_id=compute_intent_id(intent_type, goal),
        intent_type=intent_type,
        goal=goal,
        session_name=session_name,
        created_at="2026-04-17T00:00:00+00:00",
    )


def _finalize_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    return (
        PlanStep(step_index=0, event_type="run_completion_proposed", payload={}),
        PlanStep(step_index=1, event_type="finalization_succeeded", payload={}),
    )


def _empty_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    return ()


def _crashing_generator(intent: Intent, state: dict) -> tuple[PlanStep, ...]:
    raise RuntimeError("generator crashed")


class TestPlanRegistry(unittest.TestCase):
    def test_register_and_has_generator(self):
        reg = PlanRegistry()
        self.assertFalse(reg.has_generator(IntentType.LIFECYCLE_FINALIZE))
        reg.register(IntentType.LIFECYCLE_FINALIZE, _finalize_generator)
        self.assertTrue(reg.has_generator(IntentType.LIFECYCLE_FINALIZE))

    def test_derive_plan_known_type(self):
        reg = PlanRegistry()
        reg.register(IntentType.LIFECYCLE_FINALIZE, _finalize_generator)
        intent = _make_intent()
        plan = reg.derive_plan(intent, {})
        self.assertIsNotNone(plan)
        self.assertEqual(plan.step_count, 2)
        self.assertEqual(plan.steps[0].event_type, "run_completion_proposed")
        self.assertEqual(plan.intent_id, intent.intent_id)

    def test_derive_plan_unknown_type(self):
        reg = PlanRegistry()
        intent = _make_intent(IntentType.CUSTOM, goal={"x": 1})
        plan = reg.derive_plan(intent, {})
        self.assertIsNone(plan)

    def test_derive_plan_empty_steps(self):
        reg = PlanRegistry()
        reg.register(IntentType.LIFECYCLE_FINALIZE, _empty_generator)
        intent = _make_intent()
        plan = reg.derive_plan(intent, {})
        self.assertIsNone(plan)

    def test_derive_plan_generator_crash(self):
        reg = PlanRegistry()
        reg.register(IntentType.LIFECYCLE_FINALIZE, _crashing_generator)
        intent = _make_intent()
        plan = reg.derive_plan(intent, {})
        self.assertIsNone(plan)

    def test_plan_determinism(self):
        reg = PlanRegistry()
        reg.register(IntentType.LIFECYCLE_FINALIZE, _finalize_generator)
        intent = _make_intent()
        plan1 = reg.derive_plan(intent, {})
        plan2 = reg.derive_plan(intent, {})
        self.assertEqual(plan1.plan_id, plan2.plan_id)
        self.assertEqual(plan1.to_dict(), plan2.to_dict())

    def test_with_defaults_loads_builtin_generators(self):
        reg = PlanRegistry.with_defaults()
        # planner.py has generators for at least LIFECYCLE_FINALIZE
        self.assertTrue(reg.has_generator(IntentType.LIFECYCLE_FINALIZE))
        intent = _make_intent()
        plan = reg.derive_plan(intent, {})
        self.assertIsNotNone(plan)
        self.assertGreater(plan.step_count, 0)


if __name__ == "__main__":
    unittest.main()
