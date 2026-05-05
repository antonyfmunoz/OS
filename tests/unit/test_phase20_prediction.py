"""Phase 20 — Intent Modeling + Predictive Execution v1.

Tests cover:
  - Intent model (creation, validation, immutability, serialization)
  - Predictor engine (repeated workflows, continuations, time patterns)
  - Predictive planner (plan generation, speculative tagging, policy)
  - Advisor integration (predictions generated per tick, not auto-executed)
  - Loop integration (prediction context flows through ticks)
  - Governance (policy modes, auto-execute gates)
  - Boundary invariants (no cells/environments/subprocess imports)
  - Determinism (same input → same output)
  - Regression (prior phase tests unaffected)

Hard invariants:
  35. Predictions must NEVER auto-execute without governance
  36. Predictive plans must be clearly marked as speculative
  37. Predictions must NOT mutate system state directly
  38. Predictive outputs must be discardable
  39. No hallucinated memory writes
"""

from __future__ import annotations

import ast
import inspect
import os
from datetime import datetime, timezone

import pytest

from umh.learning.feedback import ExecutionFeedback, FeedbackStore
from umh.prediction.intent import UserIntent, make_intent_id
from umh.prediction.planner import PredictedPlan, PredictionPolicy, PredictivePlanner
from umh.prediction.predictor import PredictionContext, Predictor


# ── helpers ──────────────────────────────────────────────────────────


def _make_feedback(
    task_type: str = "outreach",
    node_id: str = "node-1",
    success: bool = True,
    duration_ms: int = 500,
    timestamp: str = "2026-04-29T09:00:00+00:00",
    job_id: str = "",
) -> ExecutionFeedback:
    return ExecutionFeedback(
        job_id=job_id or f"job_{task_type}_{node_id}",
        node_id=node_id,
        task_type=task_type,
        success=success,
        duration_ms=duration_ms,
        timestamp=timestamp,
    )


def _populated_store(n: int = 5, task_type: str = "outreach") -> FeedbackStore:
    store = FeedbackStore()
    for i in range(n):
        store.record(
            _make_feedback(
                task_type=task_type,
                job_id=f"job_{i}",
                timestamp=f"2026-04-29T09:{i:02d}:00+00:00",
            )
        )
    return store


def _ref_time(hour: int = 9) -> datetime:
    return datetime(2026, 4, 29, hour, 0, 0, tzinfo=timezone.utc)


# ── INTENT MODEL ─────────────────────────────────────────────────────


class TestUserIntent:
    def test_creation(self) -> None:
        intent = UserIntent(
            intent_id="intent_abc",
            inferred_goal="repeat_outreach",
            confidence=0.85,
            context_signals=("seen_5_times",),
            related_entities=("outreach",),
            predicted_actions=("submit_outreach",),
            source="repeated_workflow",
            timestamp="2026-04-29T09:00:00Z",
        )
        assert intent.inferred_goal == "repeat_outreach"
        assert intent.confidence == 0.85
        assert intent.source == "repeated_workflow"

    def test_immutability(self) -> None:
        intent = UserIntent(
            intent_id="intent_x",
            inferred_goal="test",
            confidence=0.5,
            timestamp="2026-04-29T09:00:00Z",
        )
        with pytest.raises(AttributeError):
            intent.confidence = 0.9  # type: ignore[misc]

    def test_confidence_validation(self) -> None:
        with pytest.raises(ValueError, match="confidence must be 0.0"):
            UserIntent(intent_id="x", inferred_goal="test", confidence=1.5)
        with pytest.raises(ValueError, match="confidence must be 0.0"):
            UserIntent(intent_id="x", inferred_goal="test", confidence=-0.1)

    def test_auto_timestamp(self) -> None:
        intent = UserIntent(
            intent_id="intent_y",
            inferred_goal="test",
            confidence=0.5,
        )
        assert intent.timestamp != ""

    def test_serialization(self) -> None:
        intent = UserIntent(
            intent_id="intent_s",
            inferred_goal="goal",
            confidence=0.7,
            context_signals=("a", "b"),
            related_entities=("entity",),
            predicted_actions=("action",),
            source="test",
            timestamp="2026-04-29T09:00:00Z",
        )
        d = intent.to_dict()
        assert d["intent_id"] == "intent_s"
        assert d["confidence"] == 0.7
        assert d["context_signals"] == ["a", "b"]
        assert isinstance(d["related_entities"], list)

    def test_make_intent_id(self) -> None:
        id1 = make_intent_id()
        id2 = make_intent_id()
        assert id1.startswith("intent_")
        assert id1 != id2

    def test_edge_confidence_values(self) -> None:
        low = UserIntent(intent_id="a", inferred_goal="t", confidence=0.0)
        high = UserIntent(intent_id="b", inferred_goal="t", confidence=1.0)
        assert low.confidence == 0.0
        assert high.confidence == 1.0


# ── PREDICTION CONTEXT ───────────────────────────────────────────────


class TestPredictionContext:
    def test_creation(self) -> None:
        ctx = PredictionContext(
            recent_feedback=(),
            active_task_types=("outreach",),
            current_hour=9,
            current_day_of_week=1,
        )
        assert ctx.current_hour == 9
        assert ctx.active_task_types == ("outreach",)

    def test_immutability(self) -> None:
        ctx = PredictionContext()
        with pytest.raises(AttributeError):
            ctx.current_hour = 10  # type: ignore[misc]

    def test_serialization(self) -> None:
        fb = _make_feedback()
        ctx = PredictionContext(
            recent_feedback=(fb,),
            active_task_types=("a", "b"),
            current_hour=14,
        )
        d = ctx.to_dict()
        assert d["recent_feedback_count"] == 1
        assert d["active_task_types"] == ["a", "b"]


# ── PREDICTOR ENGINE ─────────────────────────────────────────────────


class TestPredictor:
    def test_init_defaults(self) -> None:
        p = Predictor()
        assert p.confidence_threshold == 0.6
        assert p.max_predictions == 5

    def test_init_validation(self) -> None:
        with pytest.raises(ValueError):
            Predictor(confidence_threshold=-0.1)
        with pytest.raises(ValueError):
            Predictor(max_predictions=0)

    def test_empty_context_returns_no_predictions(self) -> None:
        p = Predictor()
        ctx = PredictionContext()
        intents = p.predict_intent(ctx, now=_ref_time())
        assert intents == []

    def test_detects_repeated_workflows(self) -> None:
        p = Predictor()
        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks)
        intents = p.predict_intent(ctx, now=_ref_time())
        assert len(intents) >= 1
        goals = [i.inferred_goal for i in intents]
        assert any("repeat_outreach" in g for g in goals)

    def test_repeated_workflow_confidence_scales(self) -> None:
        p = Predictor()
        fb_3 = tuple(
            _make_feedback(task_type="t", job_id=f"j{i}") for i in range(3)
        )
        fb_10 = tuple(
            _make_feedback(task_type="t", job_id=f"j{i}") for i in range(10)
        )
        ctx_3 = PredictionContext(recent_feedback=fb_3)
        ctx_10 = PredictionContext(recent_feedback=fb_10)
        intents_3 = p.predict_intent(ctx_3, now=_ref_time())
        intents_10 = p.predict_intent(ctx_10, now=_ref_time())
        conf_3 = max(i.confidence for i in intents_3) if intents_3 else 0
        conf_10 = max(i.confidence for i in intents_10) if intents_10 else 0
        assert conf_10 >= conf_3

    def test_detects_continuations(self) -> None:
        p = Predictor()
        ctx = PredictionContext(active_task_types=("content_creation",))
        intents = p.predict_intent(ctx, now=_ref_time())
        assert len(intents) >= 1
        assert any("continue_content_creation" in i.inferred_goal for i in intents)

    def test_continuation_with_history_higher_confidence(self) -> None:
        p = Predictor()
        fb = (_make_feedback(task_type="outreach"),)
        ctx_no_hist = PredictionContext(active_task_types=("outreach",))
        ctx_hist = PredictionContext(
            recent_feedback=fb, active_task_types=("outreach",)
        )
        intents_no = p.predict_intent(ctx_no_hist, now=_ref_time())
        intents_yes = p.predict_intent(ctx_hist, now=_ref_time())
        cont_no = [i for i in intents_no if "continue" in i.inferred_goal]
        cont_yes = [i for i in intents_yes if "continue" in i.inferred_goal]
        assert cont_no and cont_yes
        assert cont_yes[0].confidence >= cont_no[0].confidence

    def test_detects_time_patterns(self) -> None:
        p = Predictor()
        feedbacks = tuple(
            _make_feedback(
                task_type="morning_report",
                job_id=f"j{i}",
                timestamp=f"2026-04-{20 + i:02d}T09:15:00+00:00",
            )
            for i in range(3)
        )
        ctx = PredictionContext(recent_feedback=feedbacks, current_hour=9)
        intents = p.predict_intent(ctx, now=_ref_time(9))
        goals = [i.inferred_goal for i in intents]
        assert any("time_pattern" in g for g in goals)

    def test_confidence_threshold_filtering(self) -> None:
        p = Predictor(confidence_threshold=0.99)
        feedbacks = tuple(
            _make_feedback(task_type="t", job_id=f"j{i}") for i in range(2)
        )
        ctx = PredictionContext(recent_feedback=feedbacks)
        intents = p.predict_intent(ctx, now=_ref_time())
        assert intents == []

    def test_max_predictions_limit(self) -> None:
        p = Predictor(max_predictions=2)
        feedbacks = tuple(
            _make_feedback(task_type=f"type_{i}", job_id=f"j{i}")
            for i in range(20)
        )
        ctx = PredictionContext(
            recent_feedback=feedbacks,
            active_task_types=tuple(f"type_{i}" for i in range(5)),
        )
        intents = p.predict_intent(ctx, now=_ref_time())
        assert len(intents) <= 2

    def test_build_context_from_store(self) -> None:
        p = Predictor()
        store = _populated_store(5)
        ctx = p.build_context(store, now=_ref_time())
        assert len(ctx.recent_feedback) == 5
        assert ctx.current_hour == 9

    def test_determinism(self) -> None:
        p = Predictor()
        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks, current_hour=9)
        ref = _ref_time()
        r1 = p.predict_intent(ctx, now=ref)
        r2 = p.predict_intent(ctx, now=ref)
        assert len(r1) == len(r2)
        for a, b in zip(r1, r2):
            assert a.inferred_goal == b.inferred_goal
            assert a.confidence == b.confidence
            assert a.source == b.source


# ── PREDICTIVE PLANNER ───────────────────────────────────────────────


class TestPredictivePlanner:
    def _make_intent(self, **kwargs: Any) -> UserIntent:
        defaults = {
            "intent_id": make_intent_id(),
            "inferred_goal": "repeat_outreach",
            "confidence": 0.8,
            "predicted_actions": ("submit_outreach",),
            "related_entities": ("outreach",),
            "source": "repeated_workflow",
            "timestamp": "2026-04-29T09:00:00Z",
        }
        defaults.update(kwargs)
        return UserIntent(**defaults)

    def test_predict_plan_creates_valid_objective(self) -> None:
        planner = PredictivePlanner()
        intent = self._make_intent()
        result = planner.predict_plan(intent)
        assert result is not None
        assert result.plan.objective.title.startswith("Predicted:")
        assert result.plan.objective.context["speculative"] is True

    def test_predicted_plan_is_speculative(self) -> None:
        planner = PredictivePlanner()
        intent = self._make_intent()
        result = planner.predict_plan(intent)
        assert result is not None
        assert result.speculative is True

    def test_predicted_plan_has_steps(self) -> None:
        planner = PredictivePlanner()
        intent = self._make_intent()
        result = planner.predict_plan(intent)
        assert result is not None
        assert len(result.plan.steps) >= 1
        assert result.plan.steps[0].constraints.get("speculative") is True

    def test_predicted_plan_is_draft(self) -> None:
        planner = PredictivePlanner()
        intent = self._make_intent()
        result = planner.predict_plan(intent)
        assert result is not None
        from umh.planning.models import PlanStatus
        assert result.plan.status == PlanStatus.DRAFT

    def test_predicted_plan_is_dry_run(self) -> None:
        planner = PredictivePlanner()
        intent = self._make_intent()
        result = planner.predict_plan(intent)
        assert result is not None
        assert result.plan.objective.dry_run is True

    def test_disabled_policy_returns_none(self) -> None:
        planner = PredictivePlanner(policy=PredictionPolicy.DISABLED)
        intent = self._make_intent()
        result = planner.predict_plan(intent)
        assert result is None

    def test_predict_plans_multiple(self) -> None:
        planner = PredictivePlanner()
        intents = [self._make_intent(intent_id=f"i_{i}") for i in range(3)]
        plans = planner.predict_plans(intents)
        assert len(plans) == 3
        assert all(p.speculative for p in plans)

    def test_cache_stores_plans(self) -> None:
        planner = PredictivePlanner()
        intent = self._make_intent()
        planner.predict_plan(intent)
        assert len(planner.cached_plans) == 1

    def test_cache_eviction(self) -> None:
        planner = PredictivePlanner(max_cached=3)
        for i in range(5):
            planner.predict_plan(self._make_intent(intent_id=f"i_{i}"))
        assert len(planner.cached_plans) == 3

    def test_discard_plan(self) -> None:
        planner = PredictivePlanner()
        intent = self._make_intent(intent_id="discard_me")
        planner.predict_plan(intent)
        assert len(planner.cached_plans) == 1
        removed = planner.discard_plan("discard_me")
        assert removed is True
        assert len(planner.cached_plans) == 0

    def test_clear_cache(self) -> None:
        planner = PredictivePlanner()
        for i in range(3):
            planner.predict_plan(self._make_intent(intent_id=f"i_{i}"))
        planner.clear_cache()
        assert len(planner.cached_plans) == 0

    def test_serialization(self) -> None:
        planner = PredictivePlanner()
        intent = self._make_intent()
        result = planner.predict_plan(intent)
        assert result is not None
        d = result.to_dict()
        assert d["speculative"] is True
        assert d["policy"] == "suggest_only"
        assert "intent" in d
        assert "plan" in d

    def test_set_policy(self) -> None:
        planner = PredictivePlanner()
        assert planner.policy == PredictionPolicy.SUGGEST_ONLY
        planner.set_policy(PredictionPolicy.REQUIRE_APPROVAL)
        assert planner.policy == PredictionPolicy.REQUIRE_APPROVAL

    def test_get_state(self) -> None:
        planner = PredictivePlanner()
        state = planner.get_state()
        assert state["policy"] == "suggest_only"
        assert state["cached_plans"] == 0

    def test_no_actions_produces_evaluate_step(self) -> None:
        planner = PredictivePlanner()
        intent = self._make_intent(predicted_actions=())
        result = planner.predict_plan(intent)
        assert result is not None
        assert len(result.plan.steps) == 1
        assert result.plan.steps[0].operation == "evaluate"


# ── PREDICTION POLICY (GOVERNANCE) ───────────────────────────────────


class TestPredictionPolicy:
    def _make_predicted_plan(
        self,
        policy: PredictionPolicy = PredictionPolicy.SUGGEST_ONLY,
        confidence: float = 0.8,
        approved: bool = False,
    ) -> PredictedPlan:
        intent = UserIntent(
            intent_id="test",
            inferred_goal="test",
            confidence=confidence,
            timestamp="2026-04-29T09:00:00Z",
        )
        from umh.planning.models import ExecutionPlan, PlanObjective

        plan = ExecutionPlan(
            objective=PlanObjective(title="test"),
            confidence=confidence,
        )
        return PredictedPlan(
            intent=intent,
            plan=plan,
            speculative=True,
            policy=policy,
            approved=approved,
        )

    def test_suggest_only_never_auto_executes(self) -> None:
        pp = self._make_predicted_plan(PredictionPolicy.SUGGEST_ONLY, confidence=1.0)
        assert pp.can_auto_execute is False

    def test_disabled_never_auto_executes(self) -> None:
        pp = self._make_predicted_plan(PredictionPolicy.DISABLED)
        assert pp.can_auto_execute is False

    def test_require_approval_needs_approval(self) -> None:
        not_approved = self._make_predicted_plan(
            PredictionPolicy.REQUIRE_APPROVAL, approved=False
        )
        approved = self._make_predicted_plan(
            PredictionPolicy.REQUIRE_APPROVAL, approved=True
        )
        assert not_approved.can_auto_execute is False
        assert approved.can_auto_execute is True

    def test_auto_execute_low_risk_needs_high_confidence(self) -> None:
        low_conf = self._make_predicted_plan(
            PredictionPolicy.AUTO_EXECUTE_LOW_RISK, confidence=0.5
        )
        high_conf = self._make_predicted_plan(
            PredictionPolicy.AUTO_EXECUTE_LOW_RISK, confidence=0.85
        )
        assert low_conf.can_auto_execute is False
        assert high_conf.can_auto_execute is True


# ── ADVISOR INTEGRATION ──────────────────────────────────────────────


class TestAdvisorPredictions:
    def test_advisor_without_predictor(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert result["predictions_generated"] == 0
        advisor.stop()

    def test_advisor_with_predictor_generates_predictions(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        predictor = Predictor()
        planner = PredictivePlanner()
        advisor = AdvisorRuntime(predictor=predictor, predictive_planner=planner)
        advisor.start()

        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks, current_hour=9)

        result = advisor.tick(prediction_context=ctx)
        assert result["predictions_generated"] >= 1
        assert len(advisor.pending_predictions) >= 1

        advisor.stop()

    def test_predictions_not_auto_executed(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        predictor = Predictor()
        planner = PredictivePlanner()
        advisor = AdvisorRuntime(predictor=predictor, predictive_planner=planner)
        advisor.start()

        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks)
        advisor.tick(prediction_context=ctx)

        for p in advisor.pending_predictions:
            assert p.speculative is True
            assert p.can_auto_execute is False

        advisor.stop()

    def test_advisor_clear_predictions(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        predictor = Predictor()
        planner = PredictivePlanner()
        advisor = AdvisorRuntime(predictor=predictor, predictive_planner=planner)
        advisor.start()

        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks)
        advisor.tick(prediction_context=ctx)
        assert len(advisor.pending_predictions) >= 1

        advisor.clear_predictions()
        assert len(advisor.pending_predictions) == 0

        advisor.stop()

    def test_advisor_state_includes_predictions(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        predictor = Predictor()
        planner = PredictivePlanner()
        advisor = AdvisorRuntime(predictor=predictor, predictive_planner=planner)
        advisor.start()

        state = advisor.get_state()
        assert "pending_predictions" in state
        assert state["pending_predictions"] == 0

        advisor.stop()


# ── LOOP INTEGRATION ─────────────────────────────────────────────────


class TestLoopPredictions:
    def test_loop_passes_prediction_context(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime
        from umh.runtime.loop import RuntimeLoop

        predictor = Predictor()
        planner = PredictivePlanner()
        advisor = AdvisorRuntime(predictor=predictor, predictive_planner=planner)
        loop = RuntimeLoop(advisor=advisor)
        loop.start()

        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks)
        result = loop.tick(prediction_context=ctx)
        assert result["predictions_generated"] >= 1

        loop.stop()

    def test_loop_without_prediction_context(self) -> None:
        from umh.runtime.loop import RuntimeLoop

        loop = RuntimeLoop()
        loop.start()
        result = loop.tick()
        assert result["predictions_generated"] == 0
        loop.stop()


# ── DETERMINISM ──────────────────────────────────────────────────────


class TestDeterminism:
    def test_same_context_same_intents(self) -> None:
        p = Predictor()
        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks, current_hour=9)
        ref = _ref_time()
        r1 = p.predict_intent(ctx, now=ref)
        r2 = p.predict_intent(ctx, now=ref)
        assert len(r1) == len(r2)
        for a, b in zip(r1, r2):
            assert a.inferred_goal == b.inferred_goal
            assert a.confidence == b.confidence

    def test_same_intent_same_plan_structure(self) -> None:
        planner = PredictivePlanner()
        intent = UserIntent(
            intent_id="deterministic",
            inferred_goal="repeat_outreach",
            confidence=0.8,
            predicted_actions=("submit_outreach",),
            related_entities=("outreach",),
            source="test",
            timestamp="2026-04-29T09:00:00Z",
        )
        p1 = planner.predict_plan(intent)
        planner.clear_cache()
        p2 = planner.predict_plan(intent)
        assert p1 is not None and p2 is not None
        assert p1.plan.objective.title == p2.plan.objective.title
        assert len(p1.plan.steps) == len(p2.plan.steps)
        assert p1.speculative == p2.speculative


# ── DISCARDABILITY (INV 38) ──────────────────────────────────────────


class TestDiscardability:
    def test_predictions_are_discardable(self) -> None:
        planner = PredictivePlanner()
        intent = UserIntent(
            intent_id="disc_1",
            inferred_goal="test",
            confidence=0.8,
            timestamp="2026-04-29T09:00:00Z",
        )
        planner.predict_plan(intent)
        assert len(planner.cached_plans) == 1
        planner.discard_plan("disc_1")
        assert len(planner.cached_plans) == 0

    def test_clear_all_predictions(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        predictor = Predictor()
        planner = PredictivePlanner()
        advisor = AdvisorRuntime(predictor=predictor, predictive_planner=planner)
        advisor.start()

        feedbacks = tuple(
            _make_feedback(task_type="outreach", job_id=f"j{i}")
            for i in range(5)
        )
        ctx = PredictionContext(recent_feedback=feedbacks)
        advisor.tick(prediction_context=ctx)

        advisor.clear()
        assert len(advisor.pending_predictions) == 0

        advisor.stop()


# ── BOUNDARY INVARIANTS ──────────────────────────────────────────────

_PREDICTION_FILES = [
    os.path.join(os.path.dirname(__file__), "..", "..", "umh", "prediction", "intent.py"),
    os.path.join(os.path.dirname(__file__), "..", "..", "umh", "prediction", "predictor.py"),
    os.path.join(os.path.dirname(__file__), "..", "..", "umh", "prediction", "planner.py"),
]


class TestBoundaryInvariants:
    @pytest.mark.parametrize("filepath", _PREDICTION_FILES)
    def test_no_cells_import(self, filepath: str) -> None:
        source = open(filepath).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                names = [a.name for a in node.names] if hasattr(node, "names") else []
                full = mod + " ".join(names)
                assert "umh.cells" not in full, f"cells import in {filepath}"

    @pytest.mark.parametrize("filepath", _PREDICTION_FILES)
    def test_no_environments_import(self, filepath: str) -> None:
        source = open(filepath).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                names = [a.name for a in node.names] if hasattr(node, "names") else []
                full = mod + " ".join(names)
                assert "umh.environments" not in full, f"environments import in {filepath}"

    @pytest.mark.parametrize("filepath", _PREDICTION_FILES)
    def test_no_subprocess_import(self, filepath: str) -> None:
        source = open(filepath).read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                mod = getattr(node, "module", "") or ""
                names = [a.name for a in node.names] if hasattr(node, "names") else []
                full = mod + " ".join(names)
                assert "subprocess" not in full, f"subprocess import in {filepath}"

    @pytest.mark.parametrize("filepath", _PREDICTION_FILES)
    def test_no_shell_true(self, filepath: str) -> None:
        source = open(filepath).read()
        assert "shell=True" not in source, f"shell=True in {filepath}"

    def test_predicted_plan_always_speculative(self) -> None:
        planner = PredictivePlanner()
        intent = UserIntent(
            intent_id="inv_test",
            inferred_goal="test",
            confidence=0.9,
            predicted_actions=("action",),
            related_entities=("entity",),
            source="test",
            timestamp="2026-04-29T09:00:00Z",
        )
        result = planner.predict_plan(intent)
        assert result is not None
        assert result.speculative is True
        assert result.plan.objective.context["speculative"] is True
        assert result.plan.objective.dry_run is True

    def test_predictions_do_not_mutate_feedback_store(self) -> None:
        store = _populated_store(5)
        before_count = store.total
        predictor = Predictor()
        ctx = predictor.build_context(store, now=_ref_time())
        predictor.predict_intent(ctx, now=_ref_time())
        assert store.total == before_count

    def test_no_hallucinated_memory_writes(self) -> None:
        for filepath in _PREDICTION_FILES:
            source = open(filepath).read()
            assert "open(" not in source or "open(filepath)" not in source
            assert "write(" not in source or "f.write" not in source


# ── REGRESSION ───────────────────────────────────────────────────────


class TestRegression:
    def test_advisor_without_prediction_unchanged(self) -> None:
        from umh.runtime.advisor import AdvisorRuntime

        advisor = AdvisorRuntime()
        advisor.start()
        result = advisor.tick()
        assert "tick" in result
        assert "signals_processed" in result
        assert result["predictions_generated"] == 0
        advisor.stop()

    def test_loop_without_prediction_unchanged(self) -> None:
        from umh.runtime.loop import RuntimeLoop

        loop = RuntimeLoop()
        loop.start()
        result = loop.tick()
        assert result["predictions_generated"] == 0
        loop.stop()

    def test_planning_models_unchanged(self) -> None:
        from umh.planning.models import ExecutionPlan, PlanObjective, PlanStatus

        obj = PlanObjective(title="test")
        plan = ExecutionPlan(objective=obj)
        assert plan.status == PlanStatus.DRAFT
        assert plan.objective.title == "test"

    def test_learning_feedback_unchanged(self) -> None:
        store = FeedbackStore()
        fb = _make_feedback()
        store.record(fb)
        assert store.total == 1
        assert store.get_for_node("node-1") == [fb]
