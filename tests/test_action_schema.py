"""Tests for ActionSchema — determinism, classification, normalization, safety."""

import sys
import types

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.action_schema import (
    ActionBatch,
    ActionNormalizationResult,
    ActionType,
    ExecutableAction,
    classify_action_type,
    normalize_full_plan,
    to_action_batch,
    to_executable_action,
    _build_intent,
    _build_no_op,
    _compute_action_id,
    _extract_target,
    _normalize_action_name,
)
from umh.runtime_engine.domain_adapter import (
    ActionPlan,
    ActionStep,
    DomainType,
    adapt_output,
)


# ─── Helpers ─────────────────────────────────────────────────────


def _make_step(
    instruction="Test 3 new marketing channels this week.",
    category="outreach",
    priority=1,
    source_keyword="increase exploration",
):
    return ActionStep(
        instruction=instruction,
        category=category,
        priority=priority,
        source_keyword=source_keyword,
    )


def _make_plan(
    steps=None,
    domain="business",
    confidence=0.8,
    risk_score=0.3,
    raw_action="increase exploration",
    unmapped=(),
):
    if steps is None:
        steps = (_make_step(),)
    return ActionPlan(
        domain=domain,
        steps=steps,
        confidence=confidence,
        risk_score=risk_score,
        raw_action=raw_action,
        unmapped_keywords=unmapped,
    )


# ─── Test: Action type classification ────────────────────────────


class TestClassifyActionType:
    def test_message_keywords(self):
        assert classify_action_type("Send email to the team") == ActionType.MESSAGE
        assert classify_action_type("Send DM to prospect") == ActionType.MESSAGE
        assert (
            classify_action_type("Notify team about the update") == ActionType.MESSAGE
        )
        assert classify_action_type("Message the client") == ActionType.MESSAGE

    def test_api_call_keywords(self):
        assert (
            classify_action_type("Update CRM with new lead data") == ActionType.API_CALL
        )
        assert (
            classify_action_type("Sync data from the pipeline") == ActionType.API_CALL
        )
        assert (
            classify_action_type("Create record in the database") == ActionType.API_CALL
        )
        assert (
            classify_action_type("Post to the analytics endpoint")
            == ActionType.API_CALL
        )

    def test_human_instruction_keywords(self):
        assert (
            classify_action_type("Talk to the investor about terms")
            == ActionType.HUMAN_INSTRUCTION
        )
        assert (
            classify_action_type("Manually review the contract")
            == ActionType.HUMAN_INSTRUCTION
        )
        assert (
            classify_action_type("Decide on the pricing strategy")
            == ActionType.HUMAN_INSTRUCTION
        )
        assert (
            classify_action_type("Reflect on the week's outcomes")
            == ActionType.HUMAN_INSTRUCTION
        )
        assert (
            classify_action_type("Journal about progress")
            == ActionType.HUMAN_INSTRUCTION
        )

    def test_task_keywords(self):
        assert classify_action_type("Create task for follow up") == ActionType.TASK
        assert classify_action_type("Review the sales page headline") == ActionType.TASK
        assert (
            classify_action_type("Draft a proposal for the client") == ActionType.TASK
        )
        assert classify_action_type("Plan the content calendar") == ActionType.TASK
        assert classify_action_type("Analyze top 5 performing posts") == ActionType.TASK
        assert classify_action_type("Follow up with leads") == ActionType.TASK

    def test_no_op_empty(self):
        assert classify_action_type("") == ActionType.NO_OP
        assert classify_action_type("   ") == ActionType.NO_OP

    def test_fallback_to_task(self):
        assert (
            classify_action_type("Do something unexpected and novel") == ActionType.TASK
        )

    def test_case_insensitive(self):
        assert classify_action_type("SEND EMAIL") == ActionType.MESSAGE
        assert classify_action_type("Update CRM") == ActionType.API_CALL


# ─── Test: Target extraction ────────────────────────────────────


class TestTargetExtraction:
    def test_email_target(self):
        assert _extract_target("Send report to user@example.com") == "user@example.com"

    def test_platform_target(self):
        assert _extract_target("Post on Instagram daily") == "instagram"
        assert _extract_target("Update the CRM records") == "crm"
        assert _extract_target("Check Slack for messages") == "slack"

    def test_entity_target(self):
        assert _extract_target("Contact every customer this week") == "customer"
        assert _extract_target("Follow up with the lead") == "lead"
        assert _extract_target("Coordinate with the team") == "team"

    def test_self_target(self):
        assert _extract_target("Reflect on self improvement") == "self"

    def test_no_target(self):
        assert _extract_target("Do something general") is None
        assert _extract_target("") is None

    def test_email_takes_priority(self):
        assert (
            _extract_target("Send to team at admin@co.com on slack") == "admin@co.com"
        )


# ─── Test: Action name normalization ─────────────────────────────


class TestNormalizeActionName:
    def test_basic(self):
        assert _normalize_action_name("increase exploration") == "increase_exploration"

    def test_special_chars_removed(self):
        assert _normalize_action_name("follow-up!") == "followup"

    def test_empty_returns_default(self):
        assert _normalize_action_name("") == "unknown_action"
        assert _normalize_action_name("   ") == "unknown_action"

    def test_truncation(self):
        long_name = "a " * 100
        result = _normalize_action_name(long_name)
        assert len(result) <= 80


# ─── Test: Stable action ID ─────────────────────────────────────


class TestStableActionId:
    def test_deterministic(self):
        id1 = _compute_action_id("TASK", "follow_up", "crm", {"a": 1}, {}, "business")
        id2 = _compute_action_id("TASK", "follow_up", "crm", {"a": 1}, {}, "business")
        assert id1 == id2

    def test_different_inputs_different_ids(self):
        id1 = _compute_action_id("TASK", "follow_up", "crm", {}, {}, "business")
        id2 = _compute_action_id("TASK", "follow_up", "crm", {}, {}, "creator")
        assert id1 != id2

    def test_dict_order_independent(self):
        id1 = _compute_action_id("TASK", "x", None, {"a": 1, "b": 2}, {}, "business")
        id2 = _compute_action_id("TASK", "x", None, {"b": 2, "a": 1}, {}, "business")
        assert id1 == id2

    def test_length(self):
        aid = _compute_action_id("TASK", "test", None, {}, {}, "business")
        assert len(aid) == 16
        assert all(c in "0123456789abcdef" for c in aid)


# ─── Test: Intent builder ───────────────────────────────────────


class TestBuildIntent:
    def test_with_target(self):
        intent = _build_intent("follow_up", "TASK", "business", "crm")
        assert "follow up" in intent
        assert "crm" in intent
        assert "business" in intent

    def test_without_target(self):
        intent = _build_intent("explore", "TASK", "creator", None)
        assert "targeting" not in intent
        assert "creator" in intent


# ─── Test: to_executable_action ──────────────────────────────────


class TestToExecutableAction:
    def test_basic_normalization(self):
        plan = _make_plan()
        result = to_executable_action(plan, domain="business", confidence=0.85)
        assert isinstance(result, ActionNormalizationResult)
        action = result.executable_action
        assert isinstance(action, ExecutableAction)
        assert action.domain == "business"
        assert action.confidence == 0.85
        assert action.action_name == "increase_exploration"
        assert action.action_type == ActionType.TASK.value

    def test_payload_populated(self):
        plan = _make_plan()
        result = to_executable_action(plan, domain="business", confidence=0.8)
        action = result.executable_action
        assert (
            action.payload["instruction"] == "Test 3 new marketing channels this week."
        )
        assert action.payload["category"] == "outreach"
        assert action.payload["source_keyword"] == "increase exploration"
        assert action.payload["plan_confidence"] == 0.8
        assert action.payload["plan_risk_score"] == 0.3

    def test_priority_normalized(self):
        step1 = _make_step(priority=1)
        step5 = _make_step(priority=5)
        plan1 = _make_plan(steps=(step1,))
        plan5 = _make_plan(steps=(step5,))
        r1 = to_executable_action(plan1, "business", 0.8)
        r5 = to_executable_action(plan5, "business", 0.8)
        assert r1.executable_action.priority == 1.0
        assert r5.executable_action.priority > 0.4
        assert r5.executable_action.priority < 0.7

    def test_confidence_clamped(self):
        plan = _make_plan()
        r_high = to_executable_action(plan, "business", confidence=1.5)
        r_low = to_executable_action(plan, "business", confidence=-0.3)
        assert r_high.executable_action.confidence == 1.0
        assert r_low.executable_action.confidence == 0.0

    def test_trace_id_preserved(self):
        plan = _make_plan()
        result = to_executable_action(plan, "business", 0.8, trace_id="trace_42")
        assert result.executable_action.trace_id == "trace_42"

    def test_explanation_present(self):
        plan = _make_plan(raw_action="increase exploration")
        result = to_executable_action(plan, "business", 0.8)
        assert result.executable_action.explanation is not None
        assert "increase exploration" in result.executable_action.explanation

    def test_normalized_from_recorded(self):
        plan = _make_plan()
        result = to_executable_action(plan, "business", 0.8)
        assert result.normalized_from == "increase exploration"

    def test_step_index(self):
        step_a = _make_step(
            instruction="Send email to team", source_keyword="outreach", priority=1
        )
        step_b = _make_step(
            instruction="Review the contract", source_keyword="review", priority=2
        )
        plan = _make_plan(steps=(step_a, step_b))
        r0 = to_executable_action(plan, "business", 0.8, step_index=0)
        r1 = to_executable_action(plan, "business", 0.8, step_index=1)
        assert r0.executable_action.action_type == ActionType.MESSAGE.value
        assert r1.executable_action.action_type == ActionType.TASK.value

    def test_message_action_gets_target(self):
        step = _make_step(
            instruction="Send email to the team about progress",
            source_keyword="send email",
        )
        plan = _make_plan(steps=(step,))
        result = to_executable_action(plan, "business", 0.8)
        assert result.executable_action.target == "team"
        assert result.executable_action.action_type == ActionType.MESSAGE.value


# ─── Test: NO_OP safety ─────────────────────────────────────────


class TestNoOpSafety:
    def test_empty_plan_returns_no_op(self):
        plan = _make_plan(steps=())
        result = to_executable_action(plan, "business", 0.5)
        assert result.executable_action.action_type == ActionType.NO_OP.value
        assert result.executable_action.action_name == "no_op"
        assert result.executable_action.priority == 0.0
        assert len(result.warnings) > 0

    def test_out_of_range_step_returns_no_op(self):
        plan = _make_plan(steps=(_make_step(),))
        result = to_executable_action(plan, "business", 0.5, step_index=5)
        assert result.executable_action.action_type == ActionType.NO_OP.value

    def test_empty_instruction_returns_no_op(self):
        step = _make_step(instruction="", source_keyword="")
        plan = _make_plan(steps=(step,))
        result = to_executable_action(plan, "business", 0.5)
        assert result.executable_action.action_type == ActionType.NO_OP.value

    def test_no_op_has_empty_payload(self):
        plan = _make_plan(steps=())
        result = to_executable_action(plan, "business", 0.5)
        assert result.executable_action.payload == {}

    def test_no_op_preserves_domain(self):
        plan = _make_plan(steps=())
        result = to_executable_action(plan, "creator", 0.5)
        assert result.executable_action.domain == "creator"

    def test_no_op_stable_id(self):
        plan = _make_plan(steps=())
        r1 = to_executable_action(plan, "business", 0.5)
        r2 = to_executable_action(plan, "business", 0.5)
        assert r1.executable_action.action_id == r2.executable_action.action_id


# ─── Test: Warning behavior ─────────────────────────────────────


class TestWarnings:
    def test_no_target_warning(self):
        step = _make_step(instruction="Do something general and abstract")
        plan = _make_plan(steps=(step,))
        result = to_executable_action(plan, "business", 0.8)
        assert any("no target" in w for w in result.warnings)

    def test_fallback_classification_warning(self):
        step = _make_step(
            instruction="Completely novel action with no keywords",
            source_keyword="completely_novel",
        )
        plan = _make_plan(steps=(step,))
        result = to_executable_action(plan, "business", 0.8)
        assert any("TASK fallback" in w for w in result.warnings)

    def test_no_warnings_for_clean_action(self):
        step = _make_step(instruction="Send email to the customer about the update")
        plan = _make_plan(steps=(step,))
        result = to_executable_action(plan, "business", 0.8)
        assert len(result.warnings) == 0


# ─── Test: Batch support ────────────────────────────────────────


class TestActionBatch:
    def test_batch_construction(self):
        plan = _make_plan()
        r = to_executable_action(plan, "business", 0.8)
        batch = to_action_batch((r.executable_action,), domain="business")
        assert isinstance(batch, ActionBatch)
        assert batch.count == 1
        assert batch.domain == "business"
        assert len(batch.actions) == 1

    def test_batch_deterministic_id(self):
        plan = _make_plan()
        r = to_executable_action(plan, "business", 0.8)
        b1 = to_action_batch((r.executable_action,), "business")
        b2 = to_action_batch((r.executable_action,), "business")
        assert b1.batch_id == b2.batch_id

    def test_multi_action_batch(self):
        step_a = _make_step(instruction="Send email to lead", source_keyword="outreach")
        step_b = _make_step(
            instruction="Review the proposal", source_keyword="review", priority=2
        )
        plan = _make_plan(steps=(step_a, step_b))
        results = normalize_full_plan(plan, "business", 0.8)
        actions = tuple(r.executable_action for r in results)
        batch = to_action_batch(actions, "business")
        assert batch.count == 2
        assert len(batch.actions) == 2

    def test_empty_batch(self):
        batch = to_action_batch((), "business")
        assert batch.count == 0
        assert batch.actions == ()

    def test_batch_different_domains_different_ids(self):
        plan = _make_plan()
        r = to_executable_action(plan, "business", 0.8)
        b1 = to_action_batch((r.executable_action,), "business")
        b2 = to_action_batch((r.executable_action,), "creator")
        assert b1.batch_id != b2.batch_id


# ─── Test: Determinism ──────────────────────────────────────────


class TestDeterminism:
    def test_same_input_same_output(self):
        plan = _make_plan()
        r1 = to_executable_action(plan, "business", 0.8)
        r2 = to_executable_action(plan, "business", 0.8)
        assert r1.executable_action.action_id == r2.executable_action.action_id
        assert r1.executable_action.to_dict() == r2.executable_action.to_dict()

    def test_same_input_same_warnings(self):
        step = _make_step(
            instruction="Completely novel weirdness", source_keyword="novel"
        )
        plan = _make_plan(steps=(step,))
        r1 = to_executable_action(plan, "business", 0.8)
        r2 = to_executable_action(plan, "business", 0.8)
        assert r1.warnings == r2.warnings

    def test_normalize_full_plan_deterministic(self):
        step_a = _make_step(instruction="Send email to lead", source_keyword="outreach")
        step_b = _make_step(instruction="Review the proposal", source_keyword="review")
        plan = _make_plan(steps=(step_a, step_b))
        r1 = normalize_full_plan(plan, "business", 0.8)
        r2 = normalize_full_plan(plan, "business", 0.8)
        for a, b in zip(r1, r2):
            assert a.executable_action.action_id == b.executable_action.action_id


# ─── Test: Serialization ────────────────────────────────────────


class TestSerialization:
    def test_executable_action_roundtrip(self):
        plan = _make_plan()
        result = to_executable_action(plan, "business", 0.8, trace_id="t1")
        d = result.executable_action.to_dict()
        restored = ExecutableAction.from_dict(d)
        assert restored.action_id == result.executable_action.action_id
        assert restored.action_type == result.executable_action.action_type
        assert restored.domain == result.executable_action.domain
        assert restored.trace_id == "t1"

    def test_action_batch_roundtrip(self):
        plan = _make_plan()
        r = to_executable_action(plan, "business", 0.8)
        batch = to_action_batch((r.executable_action,), "business")
        d = batch.to_dict()
        restored = ActionBatch.from_dict(d)
        assert restored.batch_id == batch.batch_id
        assert restored.count == batch.count
        assert len(restored.actions) == 1

    def test_normalization_result_to_dict(self):
        plan = _make_plan()
        result = to_executable_action(plan, "business", 0.8)
        d = result.to_dict()
        assert "executable_action" in d
        assert "warnings" in d
        assert "normalized_from" in d


# ─── Test: normalize_full_plan ───────────────────────────────────


class TestNormalizeFullPlan:
    def test_multi_step(self):
        step_a = _make_step(
            instruction="Send email to the team", source_keyword="outreach"
        )
        step_b = _make_step(instruction="Review contract", source_keyword="review")
        plan = _make_plan(steps=(step_a, step_b))
        results = normalize_full_plan(plan, "business", 0.8)
        assert len(results) == 2
        assert results[0].executable_action.action_type == ActionType.MESSAGE.value
        assert results[1].executable_action.action_type == ActionType.TASK.value

    def test_empty_plan_returns_no_op(self):
        plan = _make_plan(steps=())
        results = normalize_full_plan(plan, "business", 0.5)
        assert len(results) == 1
        assert results[0].executable_action.action_type == ActionType.NO_OP.value


# ─── Test: Domain adapter integration ────────────────────────────


class TestDomainAdapterIntegration:
    def test_adapt_output_to_executable(self):
        decision = types.SimpleNamespace(
            action="increase exploration and follow up",
            confidence=0.8,
            risk_score=0.3,
        )
        plan = adapt_output(decision, DomainType.BUSINESS)
        result = to_executable_action(plan, "business", 0.8)
        assert result.executable_action.domain == "business"
        assert result.executable_action.action_type in (
            ActionType.TASK.value,
            ActionType.MESSAGE.value,
            ActionType.API_CALL.value,
            ActionType.HUMAN_INSTRUCTION.value,
        )

    def test_all_domains_produce_valid_actions(self):
        for domain in DomainType:
            decision = types.SimpleNamespace(
                action="optimize and stabilize",
                confidence=0.7,
                risk_score=0.4,
            )
            plan = adapt_output(decision, domain)
            if plan.steps:
                result = to_executable_action(plan, domain.value, 0.7)
                assert result.executable_action.action_type != ""
                assert result.executable_action.domain == domain.value

    def test_empty_action_safe(self):
        decision = types.SimpleNamespace(
            action="",
            confidence=0.5,
            risk_score=0.5,
        )
        plan = adapt_output(decision, DomainType.BUSINESS)
        result = to_executable_action(plan, "business", 0.5)
        assert result.executable_action.action_type == ActionType.NO_OP.value


# ─── Test: DecisionTrace enrichment ─────────────────────────────


class TestDecisionTraceEnrichment:
    def test_trace_fields_exist(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        trace = DecisionTrace(
            turn_id=1,
            strategies_considered=(),
            strategy_scores={},
            selected_strategy="",
            quality_score=0.0,
            confidence=0.0,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
            executable_action_id="abc123",
            executable_action_type="TASK",
            executable_action_name="follow_up",
            executable_target="crm",
            executable_domain="business",
            executable_warnings=("no target",),
        )
        assert trace.executable_action_id == "abc123"
        assert trace.executable_action_type == "TASK"
        assert trace.executable_action_name == "follow_up"
        assert trace.executable_target == "crm"
        assert trace.executable_domain == "business"
        assert trace.executable_warnings == ("no target",)

    def test_trace_to_dict_includes_action_fields(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        trace = DecisionTrace(
            turn_id=1,
            strategies_considered=(),
            strategy_scores={},
            selected_strategy="",
            quality_score=0.0,
            confidence=0.0,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
            executable_action_id="x",
            executable_action_type="MESSAGE",
            executable_action_name="send_email",
            executable_target="team",
            executable_domain="business",
            executable_warnings=(),
        )
        d = trace.to_dict()
        assert d["executable_action_id"] == "x"
        assert d["executable_action_type"] == "MESSAGE"
        assert d["executable_action_name"] == "send_email"
        assert d["executable_target"] == "team"
        assert d["executable_domain"] == "business"
        assert d["executable_warnings"] == []

    def test_trace_omits_action_fields_when_none(self):
        from umh.runtime_engine.decision_trace import DecisionTrace

        trace = DecisionTrace(
            turn_id=1,
            strategies_considered=(),
            strategy_scores={},
            selected_strategy="",
            quality_score=0.0,
            confidence=0.0,
            signals={},
            attributed_signals={},
            horizon={},
            directives_applied=(),
            model_used="test",
            latency_ms=0,
            tokens_used=None,
            was_enhanced=False,
        )
        d = trace.to_dict()
        assert "executable_action_id" not in d
        assert "executable_action_type" not in d

    def test_build_trace_with_action_fields(self):
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            executable_action_id="abc",
            executable_action_type="TASK",
            executable_action_name="test",
            executable_target="crm",
            executable_domain="business",
            executable_warnings=("warn1",),
        )
        assert trace.executable_action_id == "abc"
        assert trace.executable_warnings == ("warn1",)


# ─── Test: SessionInterface integration ──────────────────────────


class TestSessionInterfaceIntegration:
    def test_get_last_executable_action_none_by_default(self):
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._session_id = "test"
        iface._decisions = []
        iface._intent = None
        iface._runtime = None
        iface._builder = None
        iface._last_adapted_input = None
        iface._last_executable_action = None
        iface._ctx = None
        iface._control_enabled = True
        iface._calibration_enabled = True
        iface._convergence_enabled = True
        iface._persist_memory = False
        assert iface.get_last_executable_action() is None

    def test_reset_clears_executable_action(self):
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._session_id = "test"
        iface._decisions = []
        iface._intent = None
        iface._runtime = None
        iface._builder = None
        iface._last_adapted_input = None
        iface._last_executable_action = "something"
        iface._ctx = None
        iface._control_enabled = True
        iface._calibration_enabled = True
        iface._convergence_enabled = True
        iface._persist_memory = False
        iface.reset()
        assert iface._last_executable_action is None


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
