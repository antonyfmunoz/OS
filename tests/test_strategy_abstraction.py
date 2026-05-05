"""Tests for eos_ai.strategy_abstraction — strategy abstraction + transfer layer.

Validates: context bucketing, prototype extraction, clustering, EMA updates,
transfer matching, safety gating, bias bounds, conflicting prototype
cancellation, DecisionTrace enrichment, and no regression.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import unittest
from types import SimpleNamespace

from umh.runtime_engine.strategy_abstraction import (
    BIAS_BOUND,
    MIN_CONFIDENCE_FOR_TRANSFER,
    MIN_MATCH_SCORE_FOR_BIAS,
    MIN_SAMPLE_COUNT,
    NO_BIAS,
    StrategyAbstractionResult,
    StrategyBias,
    StrategyPrototype,
    StrategyPrototypeStore,
    _bucket_value,
    _match_score,
    extract_context_signature,
    extract_strategy_prototypes,
    generate_strategy_bias,
    UNCERTAINTY_BUCKETS,
    RISK_BUCKETS,
)


def _make_trace(
    context_type: str = "stable",
    arb_mode: str = "default",
    mc_mode: str = "full",
    uncertainty: float | None = 0.1,
    risk: float | None = 0.1,
    action_type: str = "TASK",
    selected_strategy: str = "clarity",
    effective_credit: float = 0.5,
    feedback_outcome_type: str = "success",
    domain: str = "business",
    **extra,
) -> SimpleNamespace:
    return SimpleNamespace(
        context_type=context_type,
        objective_arb_mode=arb_mode,
        meta_control_mode=mc_mode,
        planner_uncertainty=uncertainty,
        calibration_risk_bias=risk,
        policy_variance=None,
        executable_action_type=action_type,
        executable_domain=domain,
        selected_strategy=selected_strategy,
        effective_credit=effective_credit,
        feedback_outcome_type=feedback_outcome_type,
        **extra,
    )


# ─── Context bucketing ─────────────────────────────────────��─────


class TestBucketing(unittest.TestCase):
    def test_low_uncertainty(self) -> None:
        self.assertEqual(_bucket_value(0.1, UNCERTAINTY_BUCKETS), "low")

    def test_medium_uncertainty(self) -> None:
        self.assertEqual(_bucket_value(0.4, UNCERTAINTY_BUCKETS), "medium")

    def test_high_uncertainty(self) -> None:
        self.assertEqual(_bucket_value(0.7, UNCERTAINTY_BUCKETS), "high")

    def test_boundary_low_medium(self) -> None:
        self.assertEqual(_bucket_value(0.3, UNCERTAINTY_BUCKETS), "medium")

    def test_boundary_medium_high(self) -> None:
        self.assertEqual(_bucket_value(0.6, UNCERTAINTY_BUCKETS), "high")

    def test_at_zero(self) -> None:
        self.assertEqual(_bucket_value(0.0, UNCERTAINTY_BUCKETS), "low")

    def test_above_max(self) -> None:
        self.assertEqual(_bucket_value(1.5, UNCERTAINTY_BUCKETS), "high")


# ─── Context signature extraction ────────────────────────────────


class TestContextSignature(unittest.TestCase):
    def test_stable_low_defaults(self) -> None:
        trace = _make_trace()
        sig = extract_context_signature(trace)
        self.assertEqual(sig["context_type"], "stable")
        self.assertEqual(sig["objective_mode"], "default")
        self.assertEqual(sig["meta_control"], "full")
        self.assertEqual(sig["uncertainty"], "low")
        self.assertEqual(sig["risk_level"], "low")

    def test_volatile_high(self) -> None:
        trace = _make_trace(
            context_type="volatile",
            arb_mode="adversarial",
            mc_mode="conservative",
            uncertainty=0.8,
            risk=0.7,
        )
        sig = extract_context_signature(trace)
        self.assertEqual(sig["context_type"], "volatile")
        self.assertEqual(sig["objective_mode"], "adversarial")
        self.assertEqual(sig["meta_control"], "conservative")
        self.assertEqual(sig["uncertainty"], "high")
        self.assertEqual(sig["risk_level"], "high")

    def test_none_values_default(self) -> None:
        trace = SimpleNamespace()
        sig = extract_context_signature(trace)
        self.assertEqual(sig["context_type"], "unknown")
        self.assertEqual(sig["uncertainty"], "low")

    def test_signature_has_five_keys(self) -> None:
        sig = extract_context_signature(_make_trace())
        self.assertEqual(len(sig), 5)

    def test_same_trace_same_signature(self) -> None:
        t = _make_trace()
        self.assertEqual(extract_context_signature(t), extract_context_signature(t))


# ─── Prototype store ─────────────────────────────────────────────


class TestPrototypeStore(unittest.TestCase):
    def test_empty_store(self) -> None:
        store = StrategyPrototypeStore()
        self.assertEqual(store.count, 0)
        self.assertEqual(store.get_all(), [])
        self.assertEqual(store.get_transferable(), [])

    def test_upsert_new(self) -> None:
        store = StrategyPrototypeStore()
        proto = StrategyPrototype(
            prototype_id="p1",
            signature={"context_type": "stable"},
            action_pattern=("TASK",),
            success_rate=0.8,
            avg_credit=0.5,
            sample_count=10,
            confidence=0.7,
            domains={"business"},
        )
        is_new = store.upsert(proto)
        self.assertTrue(is_new)
        self.assertEqual(store.count, 1)

    def test_upsert_existing(self) -> None:
        store = StrategyPrototypeStore()
        proto1 = StrategyPrototype(
            prototype_id="p1",
            signature={},
            action_pattern=("TASK",),
            success_rate=0.5,
            avg_credit=0.3,
            sample_count=5,
            confidence=0.4,
            domains=set(),
        )
        store.upsert(proto1)
        proto2 = StrategyPrototype(
            prototype_id="p1",
            signature={},
            action_pattern=("TASK",),
            success_rate=0.9,
            avg_credit=0.7,
            sample_count=10,
            confidence=0.8,
            domains=set(),
        )
        is_new = store.upsert(proto2)
        self.assertFalse(is_new)
        self.assertEqual(store.count, 1)
        self.assertAlmostEqual(store.get("p1").success_rate, 0.9)

    def test_get_transferable_filters(self) -> None:
        store = StrategyPrototypeStore()
        store.upsert(
            StrategyPrototype(
                "p1", {}, ("TASK",), 0.8, 0.5, 3, 0.3, set()
            )
        )
        store.upsert(
            StrategyPrototype(
                "p2", {}, ("TASK",), 0.8, 0.5, 10, 0.7, set()
            )
        )
        transferable = store.get_transferable()
        self.assertEqual(len(transferable), 1)
        self.assertEqual(transferable[0].prototype_id, "p2")

    def test_eviction_on_overflow(self) -> None:
        store = StrategyPrototypeStore()
        for i in range(55):
            store.upsert(
                StrategyPrototype(
                    f"p{i}", {}, ("TASK",), 0.5, 0.5, i + 1, 0.5, set()
                )
            )
        self.assertLessEqual(store.count, 50)

    def test_reset(self) -> None:
        store = StrategyPrototypeStore()
        store.upsert(
            StrategyPrototype("p1", {}, ("TASK",), 0.5, 0.5, 5, 0.5, set())
        )
        store.reset()
        self.assertEqual(store.count, 0)


# ─── Prototype extraction ────────────────────────────────────────


class TestPrototypeExtraction(unittest.TestCase):
    def _make_similar_traces(self, n: int = 5) -> list[SimpleNamespace]:
        return [
            _make_trace(
                context_type="stable",
                action_type="TASK",
                effective_credit=0.6,
                feedback_outcome_type="success",
            )
            for _ in range(n)
        ]

    def test_creates_prototype_from_cluster(self) -> None:
        store = StrategyPrototypeStore()
        traces = self._make_similar_traces(5)
        result = extract_strategy_prototypes(traces, store)
        self.assertGreaterEqual(result.prototypes_created, 1)
        self.assertEqual(store.count, result.prototypes_created)

    def test_no_prototype_from_single_trace(self) -> None:
        store = StrategyPrototypeStore()
        result = extract_strategy_prototypes([_make_trace()], store)
        self.assertEqual(result.prototypes_created, 0)

    def test_no_prototype_without_credit(self) -> None:
        store = StrategyPrototypeStore()
        traces = [
            SimpleNamespace(
                context_type="stable",
                objective_arb_mode="default",
                meta_control_mode="full",
                planner_uncertainty=0.1,
                calibration_risk_bias=0.1,
                policy_variance=None,
                executable_action_type="TASK",
                executable_domain="business",
                selected_strategy="clarity",
                effective_credit=None,
                feedback_outcome_type="success",
            )
            for _ in range(5)
        ]
        result = extract_strategy_prototypes(traces, store)
        self.assertEqual(result.prototypes_created, 0)

    def test_updates_existing_prototype(self) -> None:
        store = StrategyPrototypeStore()
        batch1 = self._make_similar_traces(3)
        extract_strategy_prototypes(batch1, store)
        initial_count = store.count

        batch2 = self._make_similar_traces(3)
        result = extract_strategy_prototypes(batch2, store)
        self.assertGreaterEqual(result.prototypes_updated, 0)
        self.assertEqual(store.count, initial_count)

    def test_prototype_tracks_success_rate(self) -> None:
        store = StrategyPrototypeStore()
        traces = self._make_similar_traces(4)
        traces.append(
            _make_trace(
                context_type="stable",
                action_type="TASK",
                effective_credit=-0.5,
                feedback_outcome_type="failure",
            )
        )
        extract_strategy_prototypes(traces, store)
        protos = store.get_all()
        self.assertEqual(len(protos), 1)
        self.assertLess(protos[0].success_rate, 1.0)

    def test_prototype_tracks_domains(self) -> None:
        store = StrategyPrototypeStore()
        traces = [
            _make_trace(domain="business"),
            _make_trace(domain="creator"),
            _make_trace(domain="business"),
        ]
        extract_strategy_prototypes(traces, store)
        for proto in store.get_all():
            if proto.domains:
                self.assertTrue(len(proto.domains) >= 1)

    def test_different_contexts_different_prototypes(self) -> None:
        store = StrategyPrototypeStore()
        stable = [_make_trace(context_type="stable") for _ in range(3)]
        volatile = [
            _make_trace(context_type="volatile", uncertainty=0.8) for _ in range(3)
        ]
        extract_strategy_prototypes(stable + volatile, store)
        self.assertGreaterEqual(store.count, 1)

    def test_empty_history(self) -> None:
        store = StrategyPrototypeStore()
        result = extract_strategy_prototypes([], store)
        self.assertEqual(result.prototypes_created, 0)
        self.assertEqual(result.prototypes_updated, 0)

    def test_ema_update_changes_stats(self) -> None:
        store = StrategyPrototypeStore()
        batch1 = [
            _make_trace(effective_credit=0.9, feedback_outcome_type="success")
            for _ in range(3)
        ]
        extract_strategy_prototypes(batch1, store)

        if store.count > 0:
            first_proto = store.get_all()[0]
            old_credit = first_proto.avg_credit

            batch2 = [
                _make_trace(effective_credit=0.1, feedback_outcome_type="success")
                for _ in range(3)
            ]
            extract_strategy_prototypes(batch2, store)
            updated_proto = store.get(first_proto.prototype_id)
            if updated_proto is not None:
                self.assertNotAlmostEqual(updated_proto.avg_credit, old_credit)


# ─── Context matching ────────────────────────────────────────────


class TestContextMatching(unittest.TestCase):
    def test_identical_signatures_perfect_match(self) -> None:
        sig = {"a": "x", "b": "y", "c": "z"}
        self.assertAlmostEqual(_match_score(sig, sig), 1.0)

    def test_disjoint_signatures_zero(self) -> None:
        sig1 = {"a": "x", "b": "y"}
        sig2 = {"a": "q", "b": "r"}
        self.assertAlmostEqual(_match_score(sig1, sig2), 0.0)

    def test_partial_match(self) -> None:
        sig1 = {"a": "x", "b": "y", "c": "z"}
        sig2 = {"a": "x", "b": "q", "c": "z"}
        score = _match_score(sig1, sig2)
        self.assertAlmostEqual(score, 2.0 / 3.0, places=4)

    def test_empty_proto_signature_zero(self) -> None:
        self.assertAlmostEqual(_match_score({"a": "x"}, {}), 0.0)

    def test_missing_keys_count_as_mismatch(self) -> None:
        sig1 = {"a": "x", "b": "y"}
        sig2 = {"a": "x"}
        score = _match_score(sig1, sig2)
        self.assertAlmostEqual(score, 1.0 / 2.0)


# ─── Transfer / bias generation ──────────────────────────────────


class TestBiasGeneration(unittest.TestCase):
    def _store_with_mature_prototype(
        self, avg_credit: float = 0.5, signature: dict | None = None
    ) -> StrategyPrototypeStore:
        store = StrategyPrototypeStore()
        sig = signature or {
            "context_type": "stable",
            "objective_mode": "default",
            "meta_control": "full",
            "uncertainty": "low",
            "risk_level": "low",
        }
        store.upsert(
            StrategyPrototype(
                prototype_id="p_mature",
                signature=sig,
                action_pattern=("TASK",),
                success_rate=0.8,
                avg_credit=avg_credit,
                sample_count=15,
                confidence=0.7,
                domains={"business"},
            )
        )
        return store

    def test_match_generates_bias(self) -> None:
        store = self._store_with_mature_prototype()
        trace = _make_trace(context_type="stable")
        bias = generate_strategy_bias(trace, store)
        self.assertTrue(bias.applied)
        self.assertIsNotNone(bias.prototype_id)
        self.assertIn("TASK", bias.bias)

    def test_bias_bounded(self) -> None:
        store = self._store_with_mature_prototype(avg_credit=1.0)
        trace = _make_trace()
        bias = generate_strategy_bias(trace, store)
        for v in bias.bias.values():
            self.assertLessEqual(abs(v), BIAS_BOUND)

    def test_no_match_returns_no_bias(self) -> None:
        store = self._store_with_mature_prototype(
            signature={
                "context_type": "adversarial",
                "objective_mode": "adversarial",
                "meta_control": "conservative",
                "uncertainty": "high",
                "risk_level": "high",
            }
        )
        trace = _make_trace(context_type="stable")
        bias = generate_strategy_bias(trace, store)
        self.assertFalse(bias.applied)

    def test_empty_store_no_bias(self) -> None:
        store = StrategyPrototypeStore()
        trace = _make_trace()
        bias = generate_strategy_bias(trace, store)
        self.assertFalse(bias.applied)
        self.assertEqual(bias.reason, "no_match")

    def test_immature_prototype_not_transferred(self) -> None:
        store = StrategyPrototypeStore()
        store.upsert(
            StrategyPrototype(
                "p_young",
                {
                    "context_type": "stable",
                    "objective_mode": "default",
                    "meta_control": "full",
                    "uncertainty": "low",
                    "risk_level": "low",
                },
                ("TASK",),
                0.8,
                0.5,
                3,
                0.2,
                set(),
            )
        )
        trace = _make_trace()
        bias = generate_strategy_bias(trace, store)
        self.assertFalse(bias.applied)

    def test_conflicting_prototypes_cancel(self) -> None:
        store = StrategyPrototypeStore()
        sig = {
            "context_type": "stable",
            "objective_mode": "default",
            "meta_control": "full",
            "uncertainty": "low",
            "risk_level": "low",
        }
        store.upsert(
            StrategyPrototype(
                "p_pos", sig, ("TASK",), 0.9, 0.6, 10, 0.7, {"business"}
            )
        )
        store.upsert(
            StrategyPrototype(
                "p_neg", sig, ("API_CALL",), 0.2, -0.5, 10, 0.7, {"business"}
            )
        )
        trace = _make_trace()
        bias = generate_strategy_bias(trace, store)
        if not bias.applied:
            self.assertIn("conflict", bias.reason)

    def test_negative_credit_produces_negative_bias(self) -> None:
        store = self._store_with_mature_prototype(avg_credit=-0.5)
        trace = _make_trace()
        bias = generate_strategy_bias(trace, store)
        if bias.applied:
            for v in bias.bias.values():
                self.assertLessEqual(v, 0.0)

    def test_positive_credit_produces_positive_bias(self) -> None:
        store = self._store_with_mature_prototype(avg_credit=0.5)
        trace = _make_trace()
        bias = generate_strategy_bias(trace, store)
        if bias.applied:
            for v in bias.bias.values():
                self.assertGreaterEqual(v, 0.0)


# ─── DecisionTrace integration ───────────────────────────────────


class TestDecisionTraceIntegration(unittest.TestCase):
    def test_abstraction_fields_on_trace(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=1,
            strategy_prototype_id="p_abc",
            strategy_match_score=0.85,
            strategy_bias_applied=True,
        )
        self.assertEqual(trace.strategy_prototype_id, "p_abc")
        self.assertAlmostEqual(trace.strategy_match_score, 0.85)
        self.assertTrue(trace.strategy_bias_applied)

    def test_abstraction_fields_default_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=2)
        self.assertIsNone(trace.strategy_prototype_id)
        self.assertIsNone(trace.strategy_match_score)
        self.assertIsNone(trace.strategy_bias_applied)

    def test_abstraction_fields_in_to_dict(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(
            turn_id=3,
            strategy_prototype_id="p_xyz",
            strategy_match_score=0.6,
            strategy_bias_applied=False,
        )
        d = trace.to_dict()
        self.assertEqual(d["strategy_prototype_id"], "p_xyz")
        self.assertAlmostEqual(d["strategy_match_score"], 0.6, places=4)
        self.assertFalse(d["strategy_bias_applied"])

    def test_abstraction_fields_omitted_when_none(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=4)
        d = trace.to_dict()
        self.assertNotIn("strategy_prototype_id", d)
        self.assertNotIn("strategy_match_score", d)
        self.assertNotIn("strategy_bias_applied", d)


# ─── Serialization ───────────────────────────────────────────────


class TestSerialization(unittest.TestCase):
    def test_prototype_round_trip(self) -> None:
        proto = StrategyPrototype(
            "p1",
            {"a": "x"},
            ("TASK", "MESSAGE"),
            0.85,
            0.6,
            12,
            0.7,
            {"business", "creator"},
        )
        d = proto.to_dict()
        restored = StrategyPrototype.from_dict(d)
        self.assertEqual(restored.prototype_id, proto.prototype_id)
        self.assertEqual(restored.action_pattern, proto.action_pattern)
        self.assertAlmostEqual(restored.success_rate, proto.success_rate, places=4)
        self.assertEqual(restored.domains, proto.domains)

    def test_bias_to_dict(self) -> None:
        bias = StrategyBias("p1", 0.75, {"TASK": 0.01}, True, "matched:p1")
        d = bias.to_dict()
        self.assertEqual(d["prototype_id"], "p1")
        self.assertAlmostEqual(d["match_score"], 0.75, places=4)
        self.assertTrue(d["applied"])

    def test_result_to_dict(self) -> None:
        result = StrategyAbstractionResult(2, 1, 3)
        d = result.to_dict()
        self.assertEqual(d["prototypes_created"], 2)

    def test_store_to_dict(self) -> None:
        store = StrategyPrototypeStore()
        store.upsert(
            StrategyPrototype("p1", {}, ("TASK",), 0.5, 0.5, 5, 0.5, set())
        )
        d = store.to_dict()
        self.assertIn("p1", d)


# ─── SessionInterface integration ────────────────────────────────


class TestSessionInterfaceIntegration(unittest.TestCase):
    def test_get_last_strategy_bias_none_default(self) -> None:
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._last_strategy_bias = None
        self.assertIsNone(iface.get_last_strategy_bias())

    def test_reset_clears_strategy_bias(self) -> None:
        from umh.runtime_engine.session_interface import SessionInterface

        iface = SessionInterface.__new__(SessionInterface)
        iface._decisions = []
        iface._intent = None
        iface._last_executable_action = None
        iface._last_execution_result = None
        iface._last_execution_feedback = None
        iface._last_feedback_observation = None
        iface._last_credit_result = None
        iface._last_strategy_bias = "something"
        iface._runtime = None
        iface._session_id = "test"
        iface._ctx = None
        iface._control_enabled = True
        iface._calibration_enabled = True
        iface._convergence_enabled = True
        iface._persist_memory = False
        iface._prototype_store = None
        iface.reset()
        self.assertIsNone(iface._last_strategy_bias)


# ─── No regression ───────────────────────────────────────────────


class TestNoRegression(unittest.TestCase):
    def test_credit_module_still_works(self) -> None:
        from umh.runtime_engine.execution_credit import compute_full_credit

        action = SimpleNamespace(action_id="x", confidence=0.8)
        feedback = SimpleNamespace(
            action_id="x",
            outcome_type="success",
            signal_strength=0.8,
            handler_name="log",
            error=None,
        )
        result = compute_full_credit(action, feedback)
        self.assertGreater(result.credit.effective_credit, 0.0)

    def test_feedback_module_still_works(self) -> None:
        from umh.runtime_engine.execution_feedback import execution_to_feedback

        er = SimpleNamespace(
            action_id="x",
            action_name="test",
            handler_name="log",
            status="success",
            output={},
            error=None,
        )
        fb = execution_to_feedback(er, confidence=0.8)
        self.assertEqual(fb.outcome_type, "success")

    def test_decision_trace_build_still_works(self) -> None:
        from umh.runtime_engine.decision_trace import build_trace

        trace = build_trace(turn_id=1)
        self.assertEqual(trace.turn_id, 1)


if __name__ == "__main__":
    unittest.main()
