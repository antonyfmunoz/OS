"""Tests for the decision quality optimization layer (Layer 3).

Validates:
1. Intent objectives section: deterministic, sorted, structured.
2. Enhanced outcome summary: failure_rate, most_common_error.
3. Prompt structure: all sections present in correct order.
4. Prompt determinism: same inputs = identical prompt.
5. Prompt differentiation: different intents/outcomes = different prompt.
6. Config gating: outcome sections respect include_outcomes_in_prompt.
7. Quality constraints always present.
8. Event selection guidance gated on outcomes.
9. Empty/missing intent handling.
10. Prompt hash reflects all inputs (state + intents + registry + config + outcomes).
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/opt/OS")

from umh.substrate.llm_outcomes import OutcomeStore, EventOutcome
from umh.substrate.llm_planner import (
    EventSchema,
    EventTypeRegistry,
    LLMPlannerConfig,
    _build_intent_objectives,
    _canonical_json,
    build_llm_prompt,
    compute_prompt_hash,
)


# ─── Fixtures ────────────────────────────────────────────────────────


def _make_registry() -> EventTypeRegistry:
    reg = EventTypeRegistry()
    reg.register(
        EventSchema(
            event_type="send_notification",
            required_fields=frozenset({"user_id", "message"}),
            optional_fields=frozenset({"channel"}),
            field_types={"user_id": str, "message": str},
        )
    )
    reg.register(
        EventSchema(
            event_type="create_user",
            required_fields=frozenset({"username", "email"}),
            optional_fields=frozenset({"role"}),
        )
    )
    return reg


def _make_config(**overrides) -> LLMPlannerConfig:
    defaults = {"enabled": True, "model_name": "test-model"}
    defaults.update(overrides)
    return LLMPlannerConfig(**defaults)


def _make_intent(
    intent_type: str = "execution_request",
    intent_id: str = "int_001",
    goal_desc: str = "achieve the objective",
    constraints: list[str] | None = None,
    priority: int = 100,
) -> dict:
    goal: dict = {"description": goal_desc}
    if constraints:
        goal["constraints"] = constraints
    return {
        "intent_id": intent_id,
        "intent_type": intent_type,
        "goal": goal,
        "priority": priority,
        "status": "active",
        "session_name": "s1",
    }


def _make_outcome(
    event_type: str = "send_notification",
    success: bool = True,
    latency_ms: int = 100,
    error_type: str | None = None,
) -> EventOutcome:
    return EventOutcome(
        proposal_id="prop_test",
        event_type=event_type,
        success=success,
        latency_ms=latency_ms,
        error_type=error_type,
        timestamp="2026-01-01T00:00:00Z",
    )


# ─── Intent objectives tests ────────────────────────────────────────


class TestIntentObjectives:
    def test_empty_intents(self):
        result = _build_intent_objectives([])
        assert result == ""

    def test_single_intent(self):
        intent = _make_intent(
            intent_type="lifecycle_finalize",
            goal_desc="finalize the session",
        )
        result = _build_intent_objectives([intent])
        assert "- type: lifecycle_finalize" in result
        assert "goal: finalize the session" in result

    def test_intent_with_constraints(self):
        intent = _make_intent(
            constraints=["must be fast", "avoid duplicates"],
        )
        result = _build_intent_objectives([intent])
        assert "constraints: must be fast, avoid duplicates" in result

    def test_intent_with_non_default_priority(self):
        intent = _make_intent(priority=10)
        result = _build_intent_objectives([intent])
        assert "priority: 10" in result

    def test_intent_default_priority_suppressed(self):
        intent = _make_intent(priority=100)
        result = _build_intent_objectives([intent])
        assert "priority:" not in result

    def test_deterministic_ordering(self):
        intents = [
            _make_intent(intent_type="workflow_run", intent_id="b"),
            _make_intent(intent_type="execution_request", intent_id="a"),
            _make_intent(intent_type="execution_request", intent_id="c"),
        ]
        result = _build_intent_objectives(intents)
        lines = result.split("\n")
        type_lines = [l for l in lines if l.startswith("- type:")]
        # execution_request comes before workflow_run (alphabetical)
        assert type_lines[0] == "- type: execution_request"
        assert type_lines[1] == "- type: execution_request"
        assert type_lines[2] == "- type: workflow_run"

    def test_ordering_stability(self):
        """Same intents in different input order → same output."""
        intents_a = [
            _make_intent(intent_type="b_type", intent_id="id2"),
            _make_intent(intent_type="a_type", intent_id="id1"),
        ]
        intents_b = [
            _make_intent(intent_type="a_type", intent_id="id1"),
            _make_intent(intent_type="b_type", intent_id="id2"),
        ]
        assert _build_intent_objectives(intents_a) == _build_intent_objectives(
            intents_b
        )

    def test_structured_goal_fallback(self):
        """Goal without 'description' falls back to canonical JSON."""
        intent = {
            "intent_id": "int_001",
            "intent_type": "custom",
            "goal": {"target": "user_123", "action": "notify"},
            "priority": 100,
            "status": "active",
        }
        result = _build_intent_objectives([intent])
        assert "- type: custom" in result
        # Should contain canonical JSON of the goal
        assert '"action":"notify"' in result or '"target":"user_123"' in result

    def test_empty_goal(self):
        """Empty goal dict produces no goal line."""
        intent = {
            "intent_id": "int_001",
            "intent_type": "custom",
            "goal": {},
            "priority": 100,
        }
        result = _build_intent_objectives([intent])
        assert "- type: custom" in result
        assert "goal:" not in result

    def test_string_constraints(self):
        """Single string constraint (not list) is handled."""
        intent = _make_intent()
        intent["goal"]["constraints"] = "must complete within 5s"
        result = _build_intent_objectives([intent])
        assert "constraints: must complete within 5s" in result


# ─── Enhanced outcome summary tests ─────────────────────────────────


class TestEnhancedOutcomeSummary:
    def test_failure_rate_present(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(success=True))
        store.record_outcome(_make_outcome(success=False, error_type="Timeout"))
        summary = store.build_outcome_summary()
        assert "failure_rate: 0.5" in summary

    def test_most_common_error_present(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(success=False, error_type="ValidationError"))
        store.record_outcome(_make_outcome(success=False, error_type="ValidationError"))
        store.record_outcome(_make_outcome(success=False, error_type="Timeout"))
        summary = store.build_outcome_summary()
        assert "most_common_error: ValidationError" in summary

    def test_other_failures_present(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(success=False, error_type="ValidationError"))
        store.record_outcome(_make_outcome(success=False, error_type="ValidationError"))
        store.record_outcome(_make_outcome(success=False, error_type="Timeout"))
        store.record_outcome(_make_outcome(success=False, error_type="IOError"))
        summary = store.build_outcome_summary()
        assert "other_failures:" in summary
        assert "Timeout" in summary

    def test_single_failure_type_no_other_failures(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(success=False, error_type="ValidationError"))
        summary = store.build_outcome_summary()
        assert "most_common_error: ValidationError" in summary
        assert "other_failures:" not in summary

    def test_all_success_no_error_lines(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(success=True))
        summary = store.build_outcome_summary()
        assert "failure_rate: 0.0" in summary
        assert "most_common_error" not in summary

    def test_failure_rate_zero_success(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome(success=False, error_type="Err"))
        summary = store.build_outcome_summary()
        assert "failure_rate: 1.0" in summary


# ─── Prompt structure tests ──────────────────────────────────────────


class TestPromptStructure:
    def test_system_role_updated(self):
        prompt = build_llm_prompt('{"a":1}', [], _make_registry(), _make_config())
        assert "minimal, valid sequence of events" in prompt
        assert "satisfy the active intents" in prompt

    def test_constraints_include_ordering(self):
        prompt = build_llm_prompt('{"a":1}', [], _make_registry(), _make_config())
        assert "Events must be ordered logically" in prompt
        assert "Do not propose redundant" in prompt

    def test_quality_constraints_always_present(self):
        prompt = build_llm_prompt('{"a":1}', [], _make_registry(), _make_config())
        assert "QUALITY CONSTRAINTS:" in prompt
        assert "likely to fail based on past outcomes" in prompt
        assert "Prefer simpler valid solutions" in prompt

    def test_intent_section_present_with_intents(self):
        intents = [_make_intent(goal_desc="test goal")]
        prompt = build_llm_prompt('{"a":1}', intents, _make_registry(), _make_config())
        assert "INTENT OBJECTIVES:" in prompt
        assert "test goal" in prompt

    def test_intent_section_absent_without_intents(self):
        prompt = build_llm_prompt('{"a":1}', [], _make_registry(), _make_config())
        assert "INTENT OBJECTIVES:" not in prompt

    def test_outcome_section_present_with_data(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        summary = store.build_outcome_summary()
        prompt = build_llm_prompt(
            '{"a":1}', [], _make_registry(), _make_config(), outcome_summary=summary
        )
        assert "EVENT PERFORMANCE:" in prompt

    def test_guidance_section_present_with_outcomes(self):
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        summary = store.build_outcome_summary()
        prompt = build_llm_prompt(
            '{"a":1}', [], _make_registry(), _make_config(), outcome_summary=summary
        )
        assert "EVENT SELECTION GUIDANCE:" in prompt
        assert "Prefer events with higher success_rate" in prompt

    def test_guidance_section_absent_without_outcomes(self):
        prompt = build_llm_prompt('{"a":1}', [], _make_registry(), _make_config())
        assert "EVENT SELECTION GUIDANCE:" not in prompt

    def test_section_ordering(self):
        """Verify sections appear in the correct order."""
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        summary = store.build_outcome_summary()
        intents = [_make_intent(goal_desc="do the thing")]
        prompt = build_llm_prompt(
            '{"a":1}',
            intents,
            _make_registry(),
            _make_config(),
            outcome_summary=summary,
        )
        # Verify ordering: CONSTRAINTS < INTENT < CATALOG < STATE < PERFORMANCE < GUIDANCE < QUALITY < OUTPUT
        idx_constraints = prompt.index("CONSTRAINTS:")
        idx_intent = prompt.index("INTENT OBJECTIVES:")
        idx_catalog = prompt.index("EVENT CATALOG:")
        idx_state = prompt.index("CURRENT STATE:")
        idx_perf = prompt.index("EVENT PERFORMANCE:")
        idx_guidance = prompt.index("EVENT SELECTION GUIDANCE:")
        idx_quality = prompt.index("QUALITY CONSTRAINTS:")
        idx_output = prompt.index("OUTPUT FORMAT:")

        assert idx_constraints < idx_intent
        assert idx_intent < idx_catalog
        assert idx_catalog < idx_state
        assert idx_state < idx_perf
        assert idx_perf < idx_guidance
        assert idx_guidance < idx_quality
        assert idx_quality < idx_output


# ─── Prompt determinism tests ────────────────────────────────────────


class TestPromptDeterminism:
    def test_same_inputs_identical_prompt(self):
        reg = _make_registry()
        cfg = _make_config()
        intents = [_make_intent()]
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        summary = store.build_outcome_summary()

        p1 = build_llm_prompt('{"a":1}', intents, reg, cfg, outcome_summary=summary)
        p2 = build_llm_prompt('{"a":1}', intents, reg, cfg, outcome_summary=summary)
        assert p1 == p2

    def test_different_intents_different_prompt(self):
        reg = _make_registry()
        cfg = _make_config()
        intents_a = [_make_intent(goal_desc="goal A")]
        intents_b = [_make_intent(goal_desc="goal B")]

        p1 = build_llm_prompt('{"a":1}', intents_a, reg, cfg)
        p2 = build_llm_prompt('{"a":1}', intents_b, reg, cfg)
        assert p1 != p2

    def test_different_outcomes_different_prompt(self):
        reg = _make_registry()
        cfg = _make_config()

        store1 = OutcomeStore()
        store1.record_outcome(_make_outcome(success=True))

        store2 = OutcomeStore()
        store2.record_outcome(_make_outcome(success=False, error_type="Err"))

        p1 = build_llm_prompt(
            '{"a":1}', [], reg, cfg, outcome_summary=store1.build_outcome_summary()
        )
        p2 = build_llm_prompt(
            '{"a":1}', [], reg, cfg, outcome_summary=store2.build_outcome_summary()
        )
        assert p1 != p2

    def test_intent_ordering_doesnt_affect_prompt(self):
        """Intents are sorted internally — input order doesn't matter."""
        reg = _make_registry()
        cfg = _make_config()
        i1 = _make_intent(intent_type="a_type", intent_id="id1")
        i2 = _make_intent(intent_type="b_type", intent_id="id2")

        p1 = build_llm_prompt('{"a":1}', [i1, i2], reg, cfg)
        p2 = build_llm_prompt('{"a":1}', [i2, i1], reg, cfg)
        assert p1 == p2


# ─── Prompt hash tests ──────────────────────────────────────────────


class TestPromptHash:
    def test_same_everything_same_hash(self):
        reg = _make_registry()
        cfg = _make_config()
        intents = [_make_intent()]
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        summary = store.build_outcome_summary()
        summary_hash = store.build_outcome_summary_hash()

        prompt = build_llm_prompt('{"a":1}', intents, reg, cfg, outcome_summary=summary)
        h1 = compute_prompt_hash(
            prompt,
            "test-model",
            0.0,
            1,
            reg.version,
            outcome_summary_hash=summary_hash,
        )
        h2 = compute_prompt_hash(
            prompt,
            "test-model",
            0.0,
            1,
            reg.version,
            outcome_summary_hash=summary_hash,
        )
        assert h1 == h2

    def test_different_intents_different_hash(self):
        reg = _make_registry()
        cfg = _make_config()

        p1 = build_llm_prompt('{"a":1}', [_make_intent(goal_desc="A")], reg, cfg)
        p2 = build_llm_prompt('{"a":1}', [_make_intent(goal_desc="B")], reg, cfg)

        h1 = compute_prompt_hash(p1, "test-model", 0.0, 1, reg.version)
        h2 = compute_prompt_hash(p2, "test-model", 0.0, 1, reg.version)
        assert h1 != h2

    def test_different_outcomes_different_hash(self):
        reg = _make_registry()
        cfg = _make_config()

        store1 = OutcomeStore()
        store1.record_outcome(_make_outcome(success=True))
        store2 = OutcomeStore()
        store2.record_outcome(_make_outcome(success=False, error_type="E"))

        p1 = build_llm_prompt(
            '{"a":1}',
            [],
            reg,
            cfg,
            outcome_summary=store1.build_outcome_summary(),
        )
        p2 = build_llm_prompt(
            '{"a":1}',
            [],
            reg,
            cfg,
            outcome_summary=store2.build_outcome_summary(),
        )

        h1 = compute_prompt_hash(
            p1,
            "test-model",
            0.0,
            1,
            reg.version,
            outcome_summary_hash=store1.build_outcome_summary_hash(),
        )
        h2 = compute_prompt_hash(
            p2,
            "test-model",
            0.0,
            1,
            reg.version,
            outcome_summary_hash=store2.build_outcome_summary_hash(),
        )
        assert h1 != h2


# ─── Config gating tests ────────────────────────────────────────────


class TestConfigGating:
    def test_outcomes_disabled_suppresses_performance(self):
        cfg = _make_config(include_outcomes_in_prompt=False)
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        prompt = build_llm_prompt(
            '{"a":1}',
            [],
            _make_registry(),
            cfg,
            outcome_summary=store.build_outcome_summary(),
        )
        assert "EVENT PERFORMANCE:" not in prompt
        assert "EVENT SELECTION GUIDANCE:" not in prompt

    def test_outcomes_enabled_includes_both(self):
        cfg = _make_config(include_outcomes_in_prompt=True)
        store = OutcomeStore()
        store.record_outcome(_make_outcome())
        prompt = build_llm_prompt(
            '{"a":1}',
            [],
            _make_registry(),
            cfg,
            outcome_summary=store.build_outcome_summary(),
        )
        assert "EVENT PERFORMANCE:" in prompt
        assert "EVENT SELECTION GUIDANCE:" in prompt

    def test_quality_constraints_present_regardless_of_config(self):
        """Quality constraints are always present, even without outcomes."""
        for include in [True, False]:
            cfg = _make_config(include_outcomes_in_prompt=include)
            prompt = build_llm_prompt('{"a":1}', [], _make_registry(), cfg)
            assert "QUALITY CONSTRAINTS:" in prompt
