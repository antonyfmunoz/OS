"""Integration tests for the LLM planning layer priority chain.

Validates the full three-layer composite strategy:
  IntentAwareStrategy → ReplayableStrategy → PlannerStrategy → RuleBasedStrategy

Test groups:
1. Priority chain: LLM valid stops chain, LLM None → planner, disabled → planner
2. Sentinel behavior: terminal flag, suppress_downstream, no mutation side effects
3. End-to-end: propose → emit → replay → compare
4. Event metadata: proposal_id, proposal_step_index, source on emitted events
5. Fallback safety: LLM failure/timeout never blocks deterministic path
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.decision_engine import DecisionOutput, Rule, RuleBasedStrategy
from eos_ai.substrate.event_scheduler import EventScheduler, SchedulerEvent
from eos_ai.substrate.intent_models import (
    Intent,
    IntentStatus,
    IntentType,
    intent_store_key,
)
from eos_ai.substrate.llm_planner import (
    EventSchema,
    EventTypeRegistry,
    LLMPlannerConfig,
    LLMPlanningStrategy,
    ProposedEvent,
    SelectionPolicy,
    _canonical_json,
    _sha256_prefix,
)
from eos_ai.substrate.llm_replay import LLMDecisionRecord, ReplayableStrategy
from eos_ai.substrate.planner import IntentAwareStrategy, PlannerStrategy
from eos_ai.substrate.runtime_state_store import RuntimeStateStore


# ─── Fixtures ────────────────────────────────────────────────────────


def _make_registry() -> EventTypeRegistry:
    reg = EventTypeRegistry()
    reg.register(
        EventSchema(
            event_type="test_action",
            required_fields=frozenset({"session_name", "action"}),
            optional_fields=frozenset({"metadata"}),
            field_types={"session_name": str, "action": str},
            is_mutation=True,
        )
    )
    reg.register(
        EventSchema(
            event_type="test_mutation",
            required_fields=frozenset({"key", "value"}),
            optional_fields=frozenset(),
            is_mutation=True,
        )
    )
    return reg


def _make_config(**overrides) -> LLMPlannerConfig:
    defaults = {"enabled": True, "model_name": "test-model"}
    defaults.update(overrides)
    return LLMPlannerConfig(**defaults)


def _make_scheduler() -> tuple[EventScheduler, RuntimeStateStore]:
    store = RuntimeStateStore()
    scheduler = EventScheduler(store=store)
    return scheduler, store


VALID_RESPONSE = json.dumps(
    {
        "events": [
            {
                "event_type": "test_action",
                "payload": {"session_name": "s1", "action": "go"},
            },
        ],
        "reasoning": "Integration test reasoning",
    }
)

MULTI_EVENT_RESPONSE = json.dumps(
    {
        "events": [
            {
                "event_type": "test_action",
                "payload": {"session_name": "s1", "action": "a"},
            },
            {"event_type": "test_mutation", "payload": {"key": "k", "value": "v"}},
        ],
    }
)


def _make_llm_fn(response: str):
    call_count = [0]

    def fn(prompt: str) -> str:
        call_count[0] += 1
        return response

    fn.call_count = call_count
    return fn


def _collect_emitted_events(scheduler: EventScheduler) -> list[SchedulerEvent]:
    events = []
    while scheduler._queue:
        events.append(scheduler._queue.popleft())
    return events


def _make_rule_based() -> RuleBasedStrategy:
    """Build a RuleBasedStrategy with a simple fallback rule."""
    rule = Rule(
        rule_id="fallback_rule",
        description="Always-true fallback for testing",
        condition=lambda state: True,
        event_type="fallback_fired",
        build_payload=lambda state: {
            "session_name": state.get("session_name", ""),
            "from": "rules",
        },
        priority=100,
    )
    return RuleBasedStrategy(rules=[rule])


def _make_full_stack(
    llm_fn=None,
    llm_enabled: bool = True,
    config_overrides: dict | None = None,
) -> tuple[IntentAwareStrategy, EventScheduler, ReplayableStrategy | None]:
    """Build the full three-layer strategy stack.

    Returns (composite_strategy, scheduler, replayable_or_none).
    """
    scheduler, _ = _make_scheduler()
    registry = _make_registry()
    overrides = {"enabled": llm_enabled}
    if config_overrides:
        overrides.update(config_overrides)
    config = _make_config(**overrides)

    replayable = None
    if llm_fn is not None or llm_enabled:
        inner = LLMPlanningStrategy(
            llm_fn=llm_fn or _make_llm_fn(VALID_RESPONSE),
            registry=registry,
            config=config,
        )
        replayable = ReplayableStrategy(
            inner=inner,
            scheduler=scheduler,
            config=config,
            registry=registry,
        )

    fallback = _make_rule_based()
    composite = IntentAwareStrategy(
        planner=PlannerStrategy(),
        fallback=fallback,
        llm_planner=replayable,
    )
    return composite, scheduler, replayable


def _make_state(session_name: str = "s1", **extra) -> dict:
    return {"session_name": session_name, **extra}


# ─── Priority chain ─────────────────────────────────────────────────


class TestPriorityChain:
    """The composite strategy tries LLM → planner → rules in order."""

    def test_llm_valid_stops_chain(self):
        """When LLM produces a valid proposal, planner and rules never run."""
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        composite, scheduler, _ = _make_full_stack(llm_fn=llm_fn)
        state = _make_state()
        result = composite.evaluate(state)
        assert result is not None
        assert result.event_type == "llm_proposal_accepted"
        assert result.is_terminal is True

    def test_llm_none_falls_to_rules(self):
        """When LLM is disabled, chain falls through to rule-based."""
        composite, scheduler, _ = _make_full_stack(llm_enabled=False)
        state = _make_state()
        result = composite.evaluate(state)
        assert result is not None
        # No intents → planner returns None → rules fire
        assert result.event_type == "fallback_fired"
        assert result.strategy_name == "rule_based"

    def test_llm_disabled_falls_through(self):
        """Disabled LLM emits SKIPPED and falls through."""
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        composite, scheduler, _ = _make_full_stack(
            llm_fn=llm_fn,
            llm_enabled=False,
        )
        state = _make_state()
        result = composite.evaluate(state)
        assert result is not None
        assert result.event_type == "fallback_fired"
        events = _collect_emitted_events(scheduler)
        skipped = [e for e in events if e.event_type == "llm_decision_skipped"]
        assert len(skipped) == 1

    def test_llm_failure_falls_to_rules(self):
        """When LLM returns invalid JSON, chain falls through."""
        bad_fn = _make_llm_fn("not json {{")
        composite, scheduler, _ = _make_full_stack(llm_fn=bad_fn)
        state = _make_state()
        result = composite.evaluate(state)
        assert result is not None
        assert result.event_type == "fallback_fired"

    def test_llm_all_rejected_falls_to_rules(self):
        """When all proposed events are rejected, chain falls through."""
        bad_response = json.dumps(
            {
                "events": [{"event_type": "nonexistent", "payload": {}}],
            }
        )
        bad_fn = _make_llm_fn(bad_response)
        composite, scheduler, _ = _make_full_stack(llm_fn=bad_fn)
        state = _make_state()
        result = composite.evaluate(state)
        assert result is not None
        assert result.event_type == "fallback_fired"

    def test_no_llm_layer_planner_then_rules(self):
        """When LLM layer is None, only planner and rules are active."""
        composite = IntentAwareStrategy(
            planner=PlannerStrategy(),
            fallback=_make_rule_based(),
            llm_planner=None,
        )
        state = _make_state()
        result = composite.evaluate(state)
        assert result is not None
        assert result.event_type == "fallback_fired"


# ─── Sentinel behavior ──────────────────────────────────────────────


class TestSentinelBehavior:
    """The LLM sentinel is a control signal, not a domain decision."""

    def test_sentinel_is_terminal(self):
        composite, scheduler, _ = _make_full_stack()
        result = composite.evaluate(_make_state())
        assert result is not None
        assert result.is_terminal is True
        assert result.suppress_downstream is True

    def test_sentinel_strategy_name(self):
        composite, scheduler, _ = _make_full_stack()
        result = composite.evaluate(_make_state())
        assert result is not None
        assert result.strategy_name == "llm_replayable"

    def test_sentinel_event_type(self):
        composite, scheduler, _ = _make_full_stack()
        result = composite.evaluate(_make_state())
        assert result is not None
        assert result.event_type == "llm_proposal_accepted"

    def test_sentinel_payload_contains_proposal_id(self):
        composite, scheduler, _ = _make_full_stack()
        result = composite.evaluate(_make_state())
        assert result is not None
        assert "proposal_id" in result.payload
        assert "emitted_event_count" in result.payload


# ─── End-to-end propose → emit → replay ─────────────────────────────


class TestEndToEnd:
    """Full pipeline: propose events, replay from cache, verify identical."""

    def test_propose_emit_replay_roundtrip(self):
        llm_fn = _make_llm_fn(MULTI_EVENT_RESPONSE)
        config_overrides = {"selection_policy": SelectionPolicy.ALL}
        composite, scheduler, replayable = _make_full_stack(
            llm_fn=llm_fn,
            config_overrides=config_overrides,
        )
        state = _make_state()

        # First call (cache miss)
        result1 = composite.evaluate(state)
        assert result1 is not None
        first_events = _collect_emitted_events(scheduler)
        first_domain = [
            e
            for e in first_events
            if e.source == "llm_planner"
            and e.event_type in ("test_action", "test_mutation")
        ]

        # Replay (cache hit)
        result2 = composite.evaluate(state)
        assert result2 is not None
        replay_events = _collect_emitted_events(scheduler)
        replay_domain = [
            e
            for e in replay_events
            if e.source == "llm_planner"
            and e.event_type in ("test_action", "test_mutation")
        ]

        # Same count, same types, same payloads, same ordering
        assert len(first_domain) == len(replay_domain)
        for a, b in zip(first_domain, replay_domain):
            assert a.event_type == b.event_type
            assert a.payload == b.payload
            assert a.metadata["proposal_id"] == b.metadata["proposal_id"]
            assert (
                a.metadata["proposal_step_index"] == b.metadata["proposal_step_index"]
            )

    def test_replay_does_not_call_llm(self):
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        composite, scheduler, _ = _make_full_stack(llm_fn=llm_fn)
        state = _make_state()

        composite.evaluate(state)
        _collect_emitted_events(scheduler)
        assert llm_fn.call_count[0] == 1

        composite.evaluate(state)
        assert llm_fn.call_count[0] == 1  # still 1

    def test_different_state_triggers_new_call(self):
        llm_fn = _make_llm_fn(VALID_RESPONSE)
        composite, scheduler, _ = _make_full_stack(llm_fn=llm_fn)

        composite.evaluate(_make_state("s1"))
        composite.evaluate(_make_state("s2"))
        assert llm_fn.call_count[0] == 2


# ─── Event metadata verification ────────────────────────────────────


class TestEventMetadata:
    """Verify emitted SchedulerEvents carry correct metadata."""

    def test_emitted_events_have_proposal_id(self):
        composite, scheduler, _ = _make_full_stack()
        composite.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        domain = [
            e
            for e in events
            if e.source == "llm_planner" and e.event_type == "test_action"
        ]
        assert len(domain) == 1
        assert "proposal_id" in domain[0].metadata

    def test_emitted_events_have_step_index(self):
        llm_fn = _make_llm_fn(MULTI_EVENT_RESPONSE)
        config_overrides = {"selection_policy": SelectionPolicy.ALL}
        composite, scheduler, _ = _make_full_stack(
            llm_fn=llm_fn,
            config_overrides=config_overrides,
        )
        composite.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        domain = [
            e
            for e in events
            if e.source == "llm_planner"
            and e.event_type in ("test_action", "test_mutation")
        ]
        indices = [e.metadata["proposal_step_index"] for e in domain]
        assert indices == [0, 1]

    def test_emitted_events_source(self):
        composite, scheduler, _ = _make_full_stack()
        composite.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        domain = [e for e in events if e.event_type == "test_action"]
        assert all(e.source == "llm_planner" for e in domain)

    def test_observability_events_present(self):
        composite, scheduler, _ = _make_full_stack()
        composite.evaluate(_make_state())
        events = _collect_emitted_events(scheduler)
        types = {e.event_type for e in events}
        assert "llm_decision_requested" in types
        assert "llm_decision_received" in types
        assert "llm_decision_accepted" in types


# ─── Fallback safety ────────────────────────────────────────────────


class TestFallbackSafety:
    """LLM failure never blocks the deterministic path."""

    def test_timeout_falls_to_rules(self):
        import time

        def slow_fn(prompt):
            time.sleep(5.0)
            return VALID_RESPONSE

        composite, scheduler, _ = _make_full_stack(
            llm_fn=slow_fn,
            config_overrides={"timeout_ms": 100},
        )
        result = composite.evaluate(_make_state())
        assert result is not None
        assert result.event_type == "fallback_fired"

    def test_exception_falls_to_rules(self):
        def exploding_fn(prompt):
            raise RuntimeError("LLM service down")

        composite, scheduler, _ = _make_full_stack(llm_fn=exploding_fn)
        result = composite.evaluate(_make_state())
        assert result is not None
        assert result.event_type == "fallback_fired"

    def test_empty_events_list_falls_to_rules(self):
        empty_response = json.dumps({"events": [], "reasoning": "nothing to do"})
        llm_fn = _make_llm_fn(empty_response)
        composite, scheduler, _ = _make_full_stack(llm_fn=llm_fn)
        result = composite.evaluate(_make_state())
        assert result is not None
        # Empty events list → no accepted events → rejected → falls through
        assert result.event_type == "fallback_fired"


# ─── Import verification ────────────────────────────────────────────


class TestImports:
    """Verify all LLM planning layer symbols are importable from __init__."""

    def test_public_api_importable(self):
        from eos_ai.substrate import (
            EventSchema,
            EventTypeRegistry,
            LLMDecisionRecord,
            LLMEventProposal,
            LLMPlannerConfig,
            LLMPlanningStrategy,
            LLMProposalResult,
            ProposedEvent,
            ReplayableStrategy,
            SelectionPolicy,
            ValidationResult,
        )

        assert EventSchema is not None
        assert EventTypeRegistry is not None
        assert LLMDecisionRecord is not None
        assert LLMEventProposal is not None
        assert LLMPlannerConfig is not None
        assert LLMPlanningStrategy is not None
        assert LLMProposalResult is not None
        assert ProposedEvent is not None
        assert ReplayableStrategy is not None
        assert SelectionPolicy is not None
        assert ValidationResult is not None

    def test_event_builders_importable(self):
        from eos_ai.substrate import (
            build_llm_decision_accepted_event,
            build_llm_decision_received_event,
            build_llm_decision_rejected_event,
            build_llm_decision_requested_event,
            build_llm_decision_skipped_event,
            build_llm_response_drift_event,
        )

        assert build_llm_decision_accepted_event is not None
        assert build_llm_decision_received_event is not None
        assert build_llm_decision_rejected_event is not None
        assert build_llm_decision_requested_event is not None
        assert build_llm_decision_skipped_event is not None
        assert build_llm_response_drift_event is not None
