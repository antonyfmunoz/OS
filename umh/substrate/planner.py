"""
Planner — deterministic plan generation and step emission.

The planner implements DecisionStrategy so it plugs directly into the
existing DecisionEngine.  When active intents exist in state, the
planner takes precedence.  When no intents exist, it yields None so
the engine can fall back to rule-based matching.

Design:
- Plan derivation is a pure function: intent_type + state → Plan.
- Plan step selection is deterministic: current_step index into the
  derived plan.
- The planner emits one action event per evaluation (the next step).
- Observability events (PLAN_STEP_EMITTED etc.) are bundled as
  additional_events on the DecisionOutput for the caller to emit.

Plan derivation registry:
    PLAN_GENERATORS maps IntentType → generator function.
    Each generator takes (intent, state) and returns a tuple of PlanSteps.
    New intent types are supported by registering a generator.

Invariants:
- Same state + same intents → same plan → same next step.
- No randomness anywhere in the derivation or selection path.
- The planner never modifies state — it returns DecisionOutput only.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any, Callable

from umh.substrate.decision_engine import DecisionOutput, _compute_state_hash
try:
    from umh.substrate.intent_models import (
        Intent,
        IntentStatus,
        IntentType,
        Plan,
        PlanStep,
        compute_plan_id,
        get_active_intents_from_state,
        intent_store_key,
    )
except ImportError:
    Intent = Any
    IntentStatus = Any
    IntentType = Any
    Plan = Any
    PlanStep = Any
    compute_plan_id = None
    get_active_intents_from_state = None
    intent_store_key = None

_LOG_PREFIX = "[substrate.planner]"


def _log(msg: str) -> None:
    print(f"{_LOG_PREFIX} {msg}", file=sys.stderr)


# ─── Plan generation registry ─────────────────────────────────────────

PlanGenerator = Callable[[Intent, dict[str, Any]], tuple[PlanStep, ...]]

_PLAN_GENERATORS: dict[IntentType, PlanGenerator] = {}


def register_plan_generator(intent_type: IntentType, generator: PlanGenerator) -> None:
    """Register a plan generator for an intent type.

    Generators must be deterministic: same intent + state → same steps.
    """
    _PLAN_GENERATORS[intent_type] = generator


def get_plan_generator(intent_type: IntentType) -> PlanGenerator | None:
    """Look up the registered generator for an intent type."""
    return _PLAN_GENERATORS.get(intent_type)


# ─── Built-in plan generators ─────────────────────────────────────────


def _generate_lifecycle_finalize_plan(
    intent: Intent, state: dict[str, Any]
) -> tuple[PlanStep, ...]:
    """Generate plan for LIFECYCLE_FINALIZE intent.

    Steps: finalization_succeeded → publication_confirmed → clear_requested
    """
    session = intent.session_name or state.get("session_name", "")
    return (
        PlanStep(
            step_index=0,
            event_type="finalization_succeeded",
            payload={
                "session_name": session,
                "finalization_result": intent.goal.get(
                    "finalization_result", {"success": True}
                ),
            },
            description="Trigger finalization",
        ),
        PlanStep(
            step_index=1,
            event_type="publication_confirmed",
            payload={"session_name": session},
            description="Confirm publication",
        ),
        PlanStep(
            step_index=2,
            event_type="clear_requested",
            payload={"session_name": session},
            description="Request context clear",
        ),
    )


def _generate_lifecycle_publish_plan(
    intent: Intent, state: dict[str, Any]
) -> tuple[PlanStep, ...]:
    """Generate plan for LIFECYCLE_PUBLISH intent."""
    session = intent.session_name or state.get("session_name", "")
    return (
        PlanStep(
            step_index=0,
            event_type="publication_confirmed",
            payload={"session_name": session},
            description="Confirm publication",
        ),
    )


def _generate_lifecycle_clear_plan(
    intent: Intent, state: dict[str, Any]
) -> tuple[PlanStep, ...]:
    """Generate plan for LIFECYCLE_CLEAR intent."""
    session = intent.session_name or state.get("session_name", "")
    return (
        PlanStep(
            step_index=0,
            event_type="clear_requested",
            payload={"session_name": session},
            description="Request context clear",
        ),
        PlanStep(
            step_index=1,
            event_type="clear_confirmed",
            payload={"session_name": session},
            description="Confirm context clear",
        ),
    )


def _generate_execution_request_plan(
    intent: Intent, state: dict[str, Any]
) -> tuple[PlanStep, ...]:
    """Generate plan for EXECUTION_REQUEST intent.

    Single-step: emit an execution_requested event with the goal payload.
    """
    session = intent.session_name or state.get("session_name", "")
    return (
        PlanStep(
            step_index=0,
            event_type="execution_requested",
            payload={
                "session_name": session,
                "request": intent.goal.get("request", {}),
            },
            description="Request execution",
        ),
    )


def _generate_custom_plan(
    intent: Intent, state: dict[str, Any]
) -> tuple[PlanStep, ...]:
    """Generate plan for CUSTOM intent.

    Steps are provided directly in the intent goal under "steps" key.
    Each step dict must have: event_type, payload, description (optional).
    """
    raw_steps = intent.goal.get("steps", [])
    steps: list[PlanStep] = []
    for i, raw in enumerate(raw_steps):
        steps.append(
            PlanStep(
                step_index=i,
                event_type=raw["event_type"],
                payload=raw.get("payload", {}),
                description=raw.get("description", ""),
            )
        )
    return tuple(steps)


# Register built-in generators (only when intent_models is available)
if compute_plan_id is not None:
    register_plan_generator(
        IntentType.LIFECYCLE_FINALIZE, _generate_lifecycle_finalize_plan
    )
    register_plan_generator(IntentType.LIFECYCLE_PUBLISH, _generate_lifecycle_publish_plan)
    register_plan_generator(IntentType.LIFECYCLE_CLEAR, _generate_lifecycle_clear_plan)
    register_plan_generator(IntentType.EXECUTION_REQUEST, _generate_execution_request_plan)
    register_plan_generator(IntentType.CUSTOM, _generate_custom_plan)


# ─── Plan derivation ──────────────────────────────────────────────────


def derive_plan(intent: Intent, state: dict[str, Any]) -> Plan | None:
    """Derive a plan for the given intent.

    Returns None if no generator is registered for the intent type.
    Deterministic: same intent + state → same Plan.
    """
    generator = get_plan_generator(intent.intent_type)
    if generator is None:
        _log(f"no plan generator for intent type: {intent.intent_type.value}")
        return None

    steps = generator(intent, state)
    if not steps:
        return None

    plan_id = compute_plan_id(intent.intent_id, steps)
    return Plan(plan_id=plan_id, intent_id=intent.intent_id, steps=steps)


# ─── Planner strategy ────────────────────────────────────────────────


class PlannerStrategy:
    """DecisionStrategy implementation that drives intents through plans.

    Evaluation flow:
    1. Read active intents from state (sorted by priority).
    2. For the highest-priority active intent, derive its plan.
    3. Look up the next step (intent.current_step).
    4. Return a DecisionOutput for that step.
    5. If no active intents or no steps remaining, return None.

    The caller (DecisionEngine or IntentAwareStrategy) is responsible
    for emitting the returned events and advancing intent state.
    """

    @property
    def name(self) -> str:
        return "planner"

    def evaluate(self, state: dict[str, Any]) -> DecisionOutput | None:
        """Evaluate active intents and return next planned action."""
        intents = get_active_intents_from_state(state)
        if not intents:
            return None

        state_hash = _compute_state_hash(state)

        for intent in intents:
            plan = derive_plan(intent, state)
            if plan is None:
                continue

            step = plan.step_at(intent.current_step)
            if step is None:
                # All steps exhausted — intent should be completed
                # Return a completion decision
                return self._build_completion_output(intent, plan, state_hash)

            return self._build_step_output(intent, plan, step, state_hash)

        return None

    def _build_step_output(
        self,
        intent: Intent,
        plan: Plan,
        step: PlanStep,
        state_hash: str,
    ) -> DecisionOutput:
        """Build DecisionOutput for emitting a plan step."""
        decision_id = _deterministic_decision_id(
            self.name, intent.intent_id, step.step_index, state_hash
        )
        return DecisionOutput(
            decision_id=decision_id,
            event_type=step.event_type,
            payload={
                **step.payload,
                "session_name": intent.session_name,
                "_intent_id": intent.intent_id,
                "_plan_id": plan.plan_id,
                "_step_index": step.step_index,
            },
            reasoning=(
                f"Intent [{intent.intent_id}] step {step.step_index}/{plan.step_count}: "
                f"{step.description or step.event_type}"
            ),
            state_hash=state_hash,
            strategy_name=self.name,
        )

    def _build_completion_output(
        self,
        intent: Intent,
        plan: Plan,
        state_hash: str,
    ) -> DecisionOutput:
        """Build DecisionOutput to mark an intent as completed."""
        decision_id = _deterministic_decision_id(
            self.name, intent.intent_id, -1, state_hash
        )
        return DecisionOutput(
            decision_id=decision_id,
            event_type="intent_completion_requested",
            payload={
                "session_name": intent.session_name,
                "_intent_id": intent.intent_id,
                "_plan_id": plan.plan_id,
                "steps_executed": intent.current_step,
            },
            reasoning=(
                f"Intent [{intent.intent_id}] all {plan.step_count} steps complete"
            ),
            state_hash=state_hash,
            strategy_name=self.name,
        )


# ─── Composite strategy ──────────────────────────────────────────────


class IntentAwareStrategy:
    """Composite strategy: LLM planner → deterministic planner → rules.

    Priority chain:
    1. LLM replayable strategy (if present and enabled).
    2. Deterministic PlannerStrategy (intent-driven).
    3. RuleBasedStrategy fallback.

    If LLM returns terminal sentinel → stop chain.
    If LLM returns None → fall through silently.
    """

    def __init__(
        self,
        planner: PlannerStrategy | None = None,
        fallback: Any | None = None,
        llm_planner: Any | None = None,
    ) -> None:
        self._planner = planner or PlannerStrategy()
        self._fallback = fallback  # DecisionStrategy (typically RuleBasedStrategy)
        self._llm_planner = (
            llm_planner  # ReplayableStrategy, typed Any to avoid circular import
        )

    @property
    def name(self) -> str:
        return "intent_aware"

    @property
    def planner(self) -> PlannerStrategy:
        return self._planner

    @property
    def fallback(self) -> Any:
        return self._fallback

    @property
    def llm_planner(self) -> Any:
        """The LLM planning layer (ReplayableStrategy), or None."""
        return self._llm_planner

    def evaluate(self, state: dict[str, Any]) -> DecisionOutput | None:
        """Try LLM planner first, then deterministic planner, then rules."""
        # 1. LLM planner (if present)
        if self._llm_planner is not None:
            result = self._llm_planner.evaluate(state)
            if result is not None:
                return result

        # 2. Deterministic planner
        result = self._planner.evaluate(state)
        if result is not None:
            return result

        # 3. Rule-based fallback
        if self._fallback is not None:
            return self._fallback.evaluate(state)

        return None


# ─── Intent lifecycle mutations ───────────────────────────────────────
#
# Pure functions that produce state mutations for intent progression.
# These are used by scheduler handlers that process plan step completion.
# ──────────────────────────────────────────────────────────────────────


def build_step_advance_mutations(
    intent: Intent,
) -> list[dict[str, Any]]:
    """Build mutations to advance an intent to its next step.

    Sets intent status to ACTIVE and increments current_step.
    """
    advanced = intent.with_step_advanced().with_status(IntentStatus.ACTIVE)
    return [
        {
            "op": "SET",
            "key": intent_store_key(intent.intent_id),
            "value": advanced.to_dict(),
        },
    ]


def build_intent_complete_mutations(
    intent: Intent,
) -> list[dict[str, Any]]:
    """Build mutations to mark an intent as completed.

    Removes from active_intents list via status change.
    """
    completed = intent.with_status(IntentStatus.COMPLETED)
    return [
        {
            "op": "SET",
            "key": intent_store_key(intent.intent_id),
            "value": completed.to_dict(),
        },
    ]


def build_intent_fail_mutations(
    intent: Intent,
) -> list[dict[str, Any]]:
    """Build mutations to mark an intent as failed."""
    failed = intent.with_status(IntentStatus.FAILED)
    return [
        {
            "op": "SET",
            "key": intent_store_key(intent.intent_id),
            "value": failed.to_dict(),
        },
    ]


# ─── Helpers ──────────────────────────────────────────────────────────


def _deterministic_decision_id(
    strategy: str, intent_id: str, step_index: int, state_hash: str
) -> str:
    """Deterministic decision ID from strategy + intent + step + state."""
    seed = f"{strategy}:{intent_id}:{step_index}:{state_hash}"
    return f"dec_{hashlib.sha256(seed.encode()).hexdigest()[:12]}"
