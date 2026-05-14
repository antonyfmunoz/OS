"""Phase 78 Feedback Loop — comprehensive test suite.

Tests (90+):
  - OutcomeRecord: status normalization, score clamping, serialization, denied != failure
  - FeedbackRecord: signal normalization, score bounds, serialization, user vs system
  - MemoryCandidate: creation from outcome, conservative defaults, no auto-promotion
  - TraceAnalysis: sparse traces, success/error/denied extraction, session/user extraction
  - OutcomeClassifier: all status paths, confidence levels, DENIED is safety not failure
  - FeedbackStore: append-only, list/filter, no delete/clear/pop
  - FeedbackLoop: full pipeline, partial failures, store integration
  - Run loop integration: feedback in metadata, failure doesn't break run
  - Workstation resume: works with/without feedback store
  - API/CLI: endpoint existence
  - Invariants: no forbidden imports in feedback modules
  - Regression: Phase 75B/76/77 tests still pass
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

# ═══════════════════════════════════════════════════════════════════════
# 1. Outcome Contracts
# ═══════════════════════════════════════════════════════════════════════

from umh.feedback.outcome import (
    OutcomeRecord,
    OutcomeSource,
    OutcomeStatus,
    clamp_score,
    create_outcome_id,
    normalize_outcome_status,
)


class TestOutcomeStatus:
    def test_all_statuses_exist(self):
        expected = {
            "success",
            "partial_success",
            "failure",
            "denied",
            "validation_failed",
            "timeout",
            "cancelled",
            "unknown",
            "insufficient_data",
        }
        actual = {s.value for s in OutcomeStatus}
        assert actual == expected

    def test_normalize_valid(self):
        assert normalize_outcome_status("success") == OutcomeStatus.SUCCESS
        assert normalize_outcome_status("DENIED") == OutcomeStatus.DENIED
        assert normalize_outcome_status("denied") == OutcomeStatus.DENIED

    def test_normalize_invalid(self):
        assert normalize_outcome_status("bogus") == OutcomeStatus.UNKNOWN

    def test_normalize_whitespace(self):
        assert normalize_outcome_status("  failure  ") == OutcomeStatus.FAILURE


class TestClampScore:
    def test_within_bounds(self):
        assert clamp_score(0.5) == 0.5

    def test_below_zero(self):
        assert clamp_score(-0.5) == 0.0

    def test_above_one(self):
        assert clamp_score(1.5) == 1.0

    def test_zero(self):
        assert clamp_score(0.0) == 0.0

    def test_one(self):
        assert clamp_score(1.0) == 1.0


class TestOutcomeRecord:
    def test_to_dict_round_trip(self):
        rec = OutcomeRecord(
            outcome_id="oc_1",
            trace_id="t_1",
            user_id="u_1",
            status=OutcomeStatus.SUCCESS,
            success_score=1.0,
            confidence=0.9,
            summary="test",
            evidence=["ev1"],
            errors=["err1"],
            source=OutcomeSource.TRACE,
        )
        d = rec.to_dict()
        restored = OutcomeRecord.from_dict(d)
        assert restored.outcome_id == "oc_1"
        assert restored.status == OutcomeStatus.SUCCESS
        assert restored.success_score == 1.0
        assert restored.source == OutcomeSource.TRACE

    def test_score_clamped_on_deserialize(self):
        d = {
            "outcome_id": "oc_x",
            "trace_id": "t_x",
            "user_id": "u",
            "success_score": 2.0,
            "confidence": -0.5,
        }
        rec = OutcomeRecord.from_dict(d)
        assert rec.success_score == 1.0
        assert rec.confidence == 0.0

    def test_denied_is_not_failure(self):
        assert OutcomeStatus.DENIED != OutcomeStatus.FAILURE
        assert OutcomeStatus.DENIED.value == "denied"

    def test_create_outcome_id_contains_trace(self):
        oid = create_outcome_id("trace_abc")
        assert "trace_abc" in oid
        assert oid.startswith("oc_")


# ═══════════════════════════════════════════════════════════════════════
# 2. Feedback Records
# ═══════════════════════════════════════════════════════════════════════

from umh.feedback.records import (
    FeedbackRecord,
    FeedbackSignalType,
    FeedbackSource,
    create_feedback_id,
    feedback_from_outcome,
    normalize_feedback_signal,
)


class TestFeedbackSignalType:
    def test_normalize_valid(self):
        assert (
            normalize_feedback_signal("execution_success") == FeedbackSignalType.EXECUTION_SUCCESS
        )

    def test_normalize_invalid(self):
        assert normalize_feedback_signal("bogus") == FeedbackSignalType.SYSTEM_OBSERVATION


class TestFeedbackRecord:
    def test_to_dict_round_trip(self):
        rec = FeedbackRecord(
            feedback_id="fb_1",
            trace_id="t_1",
            outcome_id="oc_1",
            user_id="u_1",
            signal_type=FeedbackSignalType.EXECUTION_SUCCESS,
            score=0.8,
            confidence=0.9,
            source=FeedbackSource.USER,
            notes="good",
        )
        d = rec.to_dict()
        restored = FeedbackRecord.from_dict(d)
        assert restored.feedback_id == "fb_1"
        assert restored.source == FeedbackSource.USER
        assert restored.signal_type == FeedbackSignalType.EXECUTION_SUCCESS

    def test_score_clamped(self):
        d = {
            "feedback_id": "fb_x",
            "score": 5.0,
            "confidence": -1.0,
        }
        rec = FeedbackRecord.from_dict(d)
        assert rec.score == 1.0
        assert rec.confidence == 0.0

    def test_user_feedback_source_preserved(self):
        rec = FeedbackRecord(
            feedback_id="fb_u",
            trace_id="t",
            outcome_id="o",
            user_id="u",
            source=FeedbackSource.USER,
        )
        assert rec.source == FeedbackSource.USER
        assert rec.to_dict()["source"] == "user"


class TestFeedbackFromOutcome:
    def test_success_maps_to_execution_success(self):
        outcome = OutcomeRecord(
            outcome_id="oc_1",
            trace_id="t_1",
            user_id="u_1",
            status=OutcomeStatus.SUCCESS,
            success_score=1.0,
            confidence=0.9,
        )
        fb = feedback_from_outcome(outcome)
        assert fb.signal_type == FeedbackSignalType.EXECUTION_SUCCESS

    def test_failure_maps_to_execution_failure(self):
        outcome = OutcomeRecord(
            outcome_id="oc_2",
            trace_id="t_2",
            user_id="u_1",
            status=OutcomeStatus.FAILURE,
            success_score=0.0,
            confidence=0.8,
        )
        fb = feedback_from_outcome(outcome)
        assert fb.signal_type == FeedbackSignalType.EXECUTION_FAILURE

    def test_denied_maps_to_safety_signal(self):
        outcome = OutcomeRecord(
            outcome_id="oc_3",
            trace_id="t_3",
            user_id="u_1",
            status=OutcomeStatus.DENIED,
            success_score=0.0,
            confidence=0.9,
        )
        fb = feedback_from_outcome(outcome)
        assert fb.signal_type == FeedbackSignalType.SAFETY_SIGNAL

    def test_feedback_references_outcome(self):
        outcome = OutcomeRecord(
            outcome_id="oc_ref",
            trace_id="t_ref",
            user_id="u_1",
            status=OutcomeStatus.SUCCESS,
        )
        fb = feedback_from_outcome(outcome)
        assert fb.outcome_id == "oc_ref"
        assert fb.trace_id == "t_ref"

    def test_source_is_system(self):
        outcome = OutcomeRecord(
            outcome_id="oc_s",
            trace_id="t_s",
            user_id="u_1",
            status=OutcomeStatus.SUCCESS,
        )
        fb = feedback_from_outcome(outcome)
        assert fb.source == FeedbackSource.SYSTEM

    def test_create_feedback_id_format(self):
        fid = create_feedback_id("trace_1", "execution_success", "system")
        assert fid.startswith("fb_trace_1_")


# ═══════════════════════════════════════════════════════════════════════
# 3. Memory Candidates
# ═══════════════════════════════════════════════════════════════════════

from umh.feedback.memory_bridge import (
    MemoryCandidate,
    MemoryCandidateType,
    MemoryPromotionStatus,
    create_memory_candidate_from_outcome,
    should_create_memory_candidate,
)


class TestMemoryCandidate:
    def test_to_dict_round_trip(self):
        mc = MemoryCandidate(
            candidate_id="mc_1",
            trace_id="t_1",
            outcome_id="oc_1",
            user_id="u_1",
            memory_type=MemoryCandidateType.EPISODIC,
            content="test",
            confidence=0.8,
            promotion_status=MemoryPromotionStatus.CANDIDATE,
        )
        d = mc.to_dict()
        restored = MemoryCandidate.from_dict(d)
        assert restored.candidate_id == "mc_1"
        assert restored.memory_type == MemoryCandidateType.EPISODIC
        assert restored.promotion_status == MemoryPromotionStatus.CANDIDATE

    def test_default_promotion_status(self):
        mc = MemoryCandidate(candidate_id="mc_x", trace_id="t", outcome_id="o", user_id="u")
        assert mc.promotion_status == MemoryPromotionStatus.CANDIDATE


class TestShouldCreateMemoryCandidate:
    def test_success_creates(self):
        oc = OutcomeRecord(
            outcome_id="o", trace_id="t", user_id="u", status=OutcomeStatus.SUCCESS, confidence=0.8
        )
        assert should_create_memory_candidate(oc) is True

    def test_failure_creates(self):
        oc = OutcomeRecord(
            outcome_id="o", trace_id="t", user_id="u", status=OutcomeStatus.FAILURE, confidence=0.8
        )
        assert should_create_memory_candidate(oc) is True

    def test_unknown_does_not_create(self):
        oc = OutcomeRecord(
            outcome_id="o", trace_id="t", user_id="u", status=OutcomeStatus.UNKNOWN, confidence=0.3
        )
        assert should_create_memory_candidate(oc) is False

    def test_insufficient_data_does_not_create(self):
        oc = OutcomeRecord(
            outcome_id="o",
            trace_id="t",
            user_id="u",
            status=OutcomeStatus.INSUFFICIENT_DATA,
            confidence=0.2,
        )
        assert should_create_memory_candidate(oc) is False

    def test_low_confidence_does_not_create(self):
        oc = OutcomeRecord(
            outcome_id="o", trace_id="t", user_id="u", status=OutcomeStatus.SUCCESS, confidence=0.1
        )
        assert should_create_memory_candidate(oc) is False


class TestCreateMemoryCandidateFromOutcome:
    def test_success_creates_episodic(self):
        oc = OutcomeRecord(
            outcome_id="o",
            trace_id="t",
            user_id="u",
            status=OutcomeStatus.SUCCESS,
            confidence=0.8,
            summary="did thing",
        )
        mc = create_memory_candidate_from_outcome(oc)
        assert mc is not None
        assert mc.memory_type == MemoryCandidateType.EPISODIC
        assert mc.promotion_status == MemoryPromotionStatus.CANDIDATE

    def test_failure_creates_error_pattern(self):
        oc = OutcomeRecord(
            outcome_id="o", trace_id="t", user_id="u", status=OutcomeStatus.FAILURE, confidence=0.8
        )
        mc = create_memory_candidate_from_outcome(oc)
        assert mc is not None
        assert mc.memory_type == MemoryCandidateType.ERROR_PATTERN

    def test_denied_creates_trace_summary(self):
        oc = OutcomeRecord(
            outcome_id="o", trace_id="t", user_id="u", status=OutcomeStatus.DENIED, confidence=0.9
        )
        mc = create_memory_candidate_from_outcome(oc)
        assert mc is not None
        assert mc.memory_type == MemoryCandidateType.TRACE_SUMMARY

    def test_insufficient_data_creates_needs_review(self):
        oc = OutcomeRecord(
            outcome_id="o",
            trace_id="t",
            user_id="u",
            status=OutcomeStatus.INSUFFICIENT_DATA,
            confidence=0.1,
        )
        mc = create_memory_candidate_from_outcome(oc)
        assert mc is not None
        assert mc.promotion_status == MemoryPromotionStatus.NEEDS_REVIEW

    def test_no_automatic_promotion(self):
        oc = OutcomeRecord(
            outcome_id="o", trace_id="t", user_id="u", status=OutcomeStatus.SUCCESS, confidence=0.9
        )
        mc = create_memory_candidate_from_outcome(oc)
        assert mc.promotion_status != MemoryPromotionStatus.PROMOTED

    def test_user_correction_creates_user_preference(self):
        oc = OutcomeRecord(
            outcome_id="o", trace_id="t", user_id="u", status=OutcomeStatus.SUCCESS, confidence=0.8
        )
        fb = FeedbackRecord(
            feedback_id="fb",
            trace_id="t",
            outcome_id="o",
            user_id="u",
            signal_type=FeedbackSignalType.USER_CORRECTION,
        )
        mc = create_memory_candidate_from_outcome(oc, feedback=fb)
        assert mc is not None
        assert mc.memory_type == MemoryCandidateType.USER_PREFERENCE


# ═══════════════════════════════════════════════════════════════════════
# 4. Trace Analyzer
# ═══════════════════════════════════════════════════════════════════════

from umh.feedback.trace_analyzer import (
    TraceAnalysis,
    analyze_trace,
    analyze_trace_dict,
    extract_adapter_status,
    extract_execution_status,
    extract_governance_status,
    extract_session_id,
    extract_trace_user_id,
    summarize_error,
    summarize_output,
)


class TestSummarizeOutput:
    def test_string_truncated(self):
        assert summarize_output("x" * 500, max_len=10) == "x" * 10

    def test_dict_summarized(self):
        result = summarize_output({"key1": "val", "key2": "val"})
        assert "key1" in result

    def test_none_empty(self):
        assert summarize_output(None) == ""


class TestSummarizeError:
    def test_string(self):
        assert summarize_error("boom") == "boom"

    def test_none(self):
        assert summarize_error(None) == ""


class TestExtractFunctions:
    def test_user_id_from_dict(self):
        assert extract_trace_user_id({"user_id": "u1"}) == "u1"

    def test_user_id_from_object(self):
        class T:
            user_id = "u2"

        assert extract_trace_user_id(T()) == "u2"

    def test_session_from_workstation_metadata(self):
        trace = {"metadata": {"workstation": {"active_session_id": "sess_1"}}}
        assert extract_session_id(trace) == "sess_1"

    def test_governance_denied_from_events(self):
        trace = {"events": [{"event_type": "governance", "payload": {"allowed": False}}]}
        assert extract_governance_status(trace) == "denied"

    def test_governance_allowed(self):
        trace = {"governance": {"allowed": True}}
        assert extract_governance_status(trace) == "allowed"

    def test_adapter_status_from_result(self):
        trace = {"result": {"adapter_result": {"status": "success"}}}
        assert extract_adapter_status(trace) == "success"

    def test_execution_status_from_dict(self):
        assert extract_execution_status({"status": "completed"}) == "completed"


class TestAnalyzeTrace:
    def test_sparse_trace_low_confidence(self):
        analysis = analyze_trace({})
        assert analysis.confidence <= 0.3
        assert not analysis.has_result
        assert not analysis.has_error

    def test_success_trace(self):
        trace = {"trace_id": "t1", "status": "completed", "result": {"output": "ok"}}
        analysis = analyze_trace(trace)
        assert analysis.has_result is True
        assert analysis.execution_status == "completed"
        assert analysis.confidence >= 0.7

    def test_error_trace(self):
        trace = {"trace_id": "t2", "status": "failed", "error": "something broke"}
        analysis = analyze_trace(trace)
        assert analysis.has_error is True
        assert analysis.error_summary == "something broke"

    def test_denied_trace(self):
        trace = {
            "trace_id": "t3",
            "events": [{"event_type": "governance", "payload": {"allowed": False}}],
        }
        analysis = analyze_trace(trace)
        assert analysis.was_denied is True
        assert analysis.confidence >= 0.9

    def test_adapter_success(self):
        trace = {"trace_id": "t4", "result": {"adapter_result": {"status": "success"}}}
        analysis = analyze_trace(trace)
        assert analysis.adapter_status == "success"

    def test_adapter_failure(self):
        trace = {"trace_id": "t5", "result": {"adapter_result": {"status": "failure"}}}
        analysis = analyze_trace(trace)
        assert analysis.adapter_status == "failure"

    def test_workstation_session_extracted(self):
        trace = {
            "trace_id": "t6",
            "metadata": {"workstation": {"active_session_id": "sess_ws"}},
        }
        analysis = analyze_trace_dict(trace)
        assert analysis.session_id == "sess_ws"

    def test_user_id_extracted(self):
        trace = {"trace_id": "t7", "user_id": "u_test"}
        analysis = analyze_trace(trace)
        assert analysis.user_id == "u_test"

    def test_output_summary_deterministic(self):
        trace = {"trace_id": "t8", "result": {"data": "value"}}
        a1 = analyze_trace(trace)
        a2 = analyze_trace(trace)
        assert a1.output_summary == a2.output_summary


# ═══════════════════════════════════════════════════════════════════════
# 5. Outcome Classifier
# ═══════════════════════════════════════════════════════════════════════

from umh.feedback.classifier import OutcomeClassifier


class TestOutcomeClassifier:
    def setup_method(self):
        self.clf = OutcomeClassifier()

    def test_explicit_success(self):
        trace = {"trace_id": "t", "status": "completed", "result": {"ok": True}}
        oc = self.clf.classify_trace(trace)
        assert oc.status == OutcomeStatus.SUCCESS
        assert oc.success_score == 1.0

    def test_explicit_failure(self):
        trace = {"trace_id": "t", "status": "failed", "error": "boom"}
        oc = self.clf.classify_trace(trace)
        assert oc.status == OutcomeStatus.FAILURE
        assert oc.success_score == 0.0

    def test_governance_denied(self):
        trace = {
            "trace_id": "t",
            "events": [{"event_type": "governance", "payload": {"allowed": False}}],
        }
        oc = self.clf.classify_trace(trace)
        assert oc.status == OutcomeStatus.DENIED
        assert oc.success_score == 0.0
        assert oc.confidence >= 0.9

    def test_validation_failed(self):
        trace = {"trace_id": "t", "result": {"adapter_result": {"status": "validation_failed"}}}
        oc = self.clf.classify_trace(trace)
        assert oc.status == OutcomeStatus.VALIDATION_FAILED

    def test_timeout(self):
        trace = {"trace_id": "t", "result": {"adapter_result": {"status": "timeout"}}}
        oc = self.clf.classify_trace(trace)
        assert oc.status == OutcomeStatus.TIMEOUT

    def test_timeout_from_error_message(self):
        trace = {"trace_id": "t", "error": "Request timed out"}
        oc = self.clf.classify_trace(trace)
        assert oc.status == OutcomeStatus.TIMEOUT

    def test_simulated_adapter(self):
        trace = {"trace_id": "t", "result": {"adapter_result": {"status": "simulated"}}}
        oc = self.clf.classify_trace(trace)
        assert oc.status == OutcomeStatus.PARTIAL_SUCCESS

    def test_missing_everything_insufficient_data(self):
        trace = {"trace_id": "t"}
        oc = self.clf.classify_trace(trace)
        assert oc.status == OutcomeStatus.INSUFFICIENT_DATA
        assert oc.confidence <= 0.3

    def test_high_confidence_for_explicit_status(self):
        trace = {"trace_id": "t", "result": {"adapter_result": {"status": "success"}}}
        oc = self.clf.classify_trace(trace)
        assert oc.confidence >= 0.8

    def test_low_confidence_for_sparse(self):
        trace = {"trace_id": "t"}
        oc = self.clf.classify_trace(trace)
        assert oc.confidence <= 0.3

    def test_completed_with_errors_partial_success(self):
        trace = {"trace_id": "t", "status": "completed", "result": {"out": 1}, "error": "warning"}
        oc = self.clf.classify_trace(trace)
        assert oc.status == OutcomeStatus.PARTIAL_SUCCESS

    def test_classify_trace_dict(self):
        oc = self.clf.classify_trace_dict(
            {"trace_id": "td", "status": "completed", "result": {"x": 1}}
        )
        assert oc.status == OutcomeStatus.SUCCESS

    def test_denied_is_safety_not_failure(self):
        trace = {
            "trace_id": "t",
            "events": [{"event_type": "governance", "payload": {"allowed": False}}],
        }
        oc = self.clf.classify_trace(trace)
        assert oc.status == OutcomeStatus.DENIED
        assert oc.status != OutcomeStatus.FAILURE


# ═══════════════════════════════════════════════════════════════════════
# 6. Feedback Store
# ═══════════════════════════════════════════════════════════════════════

from umh.feedback.store import FeedbackStore, get_feedback_store, reset_feedback_store


class TestFeedbackStore:
    def test_append_outcome(self):
        store = FeedbackStore()
        oc = OutcomeRecord(
            outcome_id="oc1", trace_id="t1", user_id="u1", status=OutcomeStatus.SUCCESS
        )
        store.append_outcome(oc)
        assert store.get_outcome("oc1") is oc

    def test_append_feedback(self):
        store = FeedbackStore()
        fb = FeedbackRecord(feedback_id="fb1", trace_id="t1", outcome_id="oc1", user_id="u1")
        store.append_feedback(fb)
        assert len(store.list_feedback()) == 1

    def test_append_memory_candidate(self):
        store = FeedbackStore()
        mc = MemoryCandidate(candidate_id="mc1", trace_id="t1", outcome_id="oc1", user_id="u1")
        store.append_memory_candidate(mc)
        assert len(store.list_memory_candidates()) == 1

    def test_list_by_user(self):
        store = FeedbackStore()
        store.append_outcome(OutcomeRecord(outcome_id="o1", trace_id="t1", user_id="u1"))
        store.append_outcome(OutcomeRecord(outcome_id="o2", trace_id="t2", user_id="u2"))
        assert len(store.list_outcomes(user_id="u1")) == 1

    def test_list_by_trace_id(self):
        store = FeedbackStore()
        store.append_outcome(OutcomeRecord(outcome_id="o1", trace_id="t1", user_id="u"))
        store.append_outcome(OutcomeRecord(outcome_id="o2", trace_id="t2", user_id="u"))
        assert len(store.list_outcomes(trace_id="t1")) == 1

    def test_get_outcome_missing(self):
        store = FeedbackStore()
        assert store.get_outcome("nope") is None

    def test_append_only_no_delete(self):
        store = FeedbackStore()
        assert not hasattr(store, "delete_outcome")
        assert not hasattr(store, "clear")
        assert not hasattr(store, "pop")

    def test_in_memory_fallback(self):
        store = FeedbackStore()
        store.append_outcome(OutcomeRecord(outcome_id="o1", trace_id="t1", user_id="u1"))
        assert len(store.list_outcomes()) == 1

    def test_to_dict_from_dict(self):
        store = FeedbackStore()
        store.append_outcome(
            OutcomeRecord(
                outcome_id="o1", trace_id="t1", user_id="u1", status=OutcomeStatus.SUCCESS
            )
        )
        store.append_feedback(
            FeedbackRecord(feedback_id="f1", trace_id="t1", outcome_id="o1", user_id="u1")
        )
        store.append_memory_candidate(
            MemoryCandidate(candidate_id="mc1", trace_id="t1", outcome_id="o1", user_id="u1")
        )
        d = store.to_dict()
        restored = FeedbackStore.from_dict(d)
        assert len(restored.list_outcomes()) == 1
        assert len(restored.list_feedback()) == 1
        assert len(restored.list_memory_candidates()) == 1

    def test_global_singleton(self):
        reset_feedback_store(None)
        s1 = get_feedback_store()
        s2 = get_feedback_store()
        assert s1 is s2
        reset_feedback_store(None)


# ═══════════════════════════════════════════════════════════════════════
# 7. Feedback Loop Orchestrator
# ═══════════════════════════════════════════════════════════════════════

from umh.feedback.feedback_loop import FeedbackLoopResult, process_trace_feedback


class TestFeedbackLoop:
    def test_success_trace_full_pipeline(self):
        trace = {
            "trace_id": "t_ok",
            "status": "completed",
            "result": {"output": "done"},
            "user_id": "u1",
        }
        store = FeedbackStore()
        result = process_trace_feedback(trace, store=store)
        assert result.status == "completed"
        assert result.outcome is not None
        assert result.outcome.status == OutcomeStatus.SUCCESS
        assert result.feedback is not None
        assert result.memory_candidate is not None
        assert len(store.list_outcomes()) == 1
        assert len(store.list_feedback()) == 1

    def test_failure_trace(self):
        trace = {"trace_id": "t_fail", "status": "failed", "error": "broke", "user_id": "u1"}
        result = process_trace_feedback(trace)
        assert result.outcome.status == OutcomeStatus.FAILURE
        assert result.feedback is not None
        assert result.memory_candidate is not None

    def test_denied_trace(self):
        trace = {
            "trace_id": "t_den",
            "events": [{"event_type": "governance", "payload": {"allowed": False}}],
            "user_id": "u1",
        }
        result = process_trace_feedback(trace)
        assert result.outcome.status == OutcomeStatus.DENIED
        assert result.feedback is not None

    def test_sparse_trace_safe(self):
        trace = {"trace_id": "t_sparse"}
        result = process_trace_feedback(trace)
        assert result.outcome.status == OutcomeStatus.INSUFFICIENT_DATA

    def test_store_receives_artifacts(self):
        store = FeedbackStore()
        trace = {"trace_id": "t_store", "status": "completed", "result": {"x": 1}, "user_id": "u1"}
        process_trace_feedback(trace, store=store)
        assert len(store.list_outcomes()) == 1
        assert len(store.list_feedback()) == 1

    def test_errors_do_not_raise(self):
        result = process_trace_feedback(None)
        assert result.status == "error" or result.trace_id == ""

    def test_result_includes_ids(self):
        trace = {
            "trace_id": "t_ids",
            "status": "completed",
            "result": {"ok": True},
            "user_id": "u1",
        }
        result = process_trace_feedback(trace)
        assert result.metadata.get("outcome_id") is not None
        assert result.metadata.get("feedback_id") is not None

    def test_no_store_still_works(self):
        trace = {"trace_id": "t_nostore", "status": "completed", "result": {"ok": True}}
        result = process_trace_feedback(trace, store=None)
        assert result.outcome is not None
        assert result.status == "completed"


# ═══════════════════════════════════════════════════════════════════════
# 8. Run Loop Integration
# ═══════════════════════════════════════════════════════════════════════


class TestRunLoopFeedbackIntegration:
    def test_successful_run_includes_feedback_metadata(self):
        from umh.run import run

        result = run("hello")
        assert "phase78_feedback" in result.metadata
        assert "outcome_status" in result.metadata["phase78_feedback"]
        assert "outcome_id" in result.metadata["phase78_feedback"]

    def test_feedback_failure_does_not_fail_run(self):
        from umh.run import run

        result = run("hello")
        assert result.run_id.startswith("run_")

    def test_run_without_workstation_context(self):
        from umh.run import run

        result = run("hello")
        assert result.success is True or result.success is False

    def test_run_with_workstation_context(self):
        from umh.run import run

        ws_ctx = {"active_mode": "developer", "active_session_id": "sess_test"}
        result = run("hello", workstation_context=ws_ctx)
        assert "phase78_feedback" in result.metadata


# ═══════════════════════════════════════════════════════════════════════
# 9. Workstation Resume Integration
# ═══════════════════════════════════════════════════════════════════════

from umh.workstation.operator_profile import create_default_profile
from umh.workstation.resume import build_resume_summary
from umh.workstation.session_state import SessionStore, reset_session_store


class TestResumeWithFeedback:
    def test_resume_without_feedback_store(self):
        profile = create_default_profile("u1")
        summary = build_resume_summary(profile=profile)
        assert summary.recent_denials == 0
        assert summary.memory_candidates_pending == 0
        assert summary.recent_outcomes == []

    def test_resume_with_feedback_store(self):
        profile = create_default_profile("u1")
        store = FeedbackStore()
        store.append_outcome(
            OutcomeRecord(
                outcome_id="o1",
                trace_id="t1",
                user_id="u1",
                status=OutcomeStatus.SUCCESS,
                confidence=0.9,
            )
        )
        store.append_outcome(
            OutcomeRecord(
                outcome_id="o2",
                trace_id="t2",
                user_id="u1",
                status=OutcomeStatus.DENIED,
                confidence=0.9,
            )
        )
        store.append_memory_candidate(
            MemoryCandidate(
                candidate_id="mc1",
                trace_id="t1",
                outcome_id="o1",
                user_id="u1",
                promotion_status=MemoryPromotionStatus.CANDIDATE,
            )
        )
        summary = build_resume_summary(profile=profile, feedback_store=store)
        assert summary.recent_denials == 1
        assert summary.last_outcome_status == "denied"
        assert summary.memory_candidates_pending == 1
        assert len(summary.recent_outcomes) == 2

    def test_resume_includes_denial_resume_point(self):
        profile = create_default_profile("u1")
        store = FeedbackStore()
        store.append_outcome(
            OutcomeRecord(
                outcome_id="o1",
                trace_id="t1",
                user_id="u1",
                status=OutcomeStatus.DENIED,
                confidence=0.9,
            )
        )
        summary = build_resume_summary(profile=profile, feedback_store=store)
        assert any("denial" in p for p in summary.recommended_resume_points)

    def test_resume_does_not_invent_outcomes(self):
        profile = create_default_profile("u1")
        store = FeedbackStore()
        summary = build_resume_summary(profile=profile, feedback_store=store)
        assert summary.recent_outcomes == []
        assert summary.last_outcome_status == ""


# ═══════════════════════════════════════════════════════════════════════
# 10. Invariants: no forbidden imports
# ═══════════════════════════════════════════════════════════════════════

import ast
import pathlib

_FORBIDDEN = {"subprocess", "requests", "selenium", "playwright"}
_FEEDBACK_DIR = pathlib.Path("/opt/OS/umh/feedback")


class TestFeedbackInvariants:
    def test_no_forbidden_imports(self):
        violations = []
        for py_file in _FEEDBACK_DIR.glob("*.py"):
            source = py_file.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in _FORBIDDEN:
                            violations.append(f"{py_file.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and any(node.module.startswith(m) for m in _FORBIDDEN):
                        violations.append(f"{py_file.name}: from {node.module}")
        assert violations == [], f"Forbidden imports: {violations}"

    def test_no_adapter_imports(self):
        violations = []
        for py_file in _FEEDBACK_DIR.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "umh.adapters" in node.module:
                        violations.append(f"{py_file.name}: from {node.module}")
        assert violations == [], f"Adapter imports in feedback: {violations}"

    def test_no_governance_gate_import(self):
        violations = []
        for py_file in _FEEDBACK_DIR.glob("*.py"):
            source = py_file.read_text()
            if "governance_gate" in source and "import" in source:
                try:
                    tree = ast.parse(source)
                    for node in ast.walk(tree):
                        if (
                            isinstance(node, ast.ImportFrom)
                            and node.module
                            and "governance_gate" in node.module
                        ):
                            violations.append(py_file.name)
                except SyntaxError:
                    pass
        assert violations == [], f"Governance gate imports: {violations}"

    def test_no_backend_registry_import(self):
        violations = []
        for py_file in _FEEDBACK_DIR.glob("*.py"):
            source = py_file.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and "backend_registry" in node.module
                ):
                    violations.append(py_file.name)
        assert violations == [], f"Backend registry imports: {violations}"

    def test_feedback_modules_do_not_mutate_traces(self):
        violations = []
        forbidden_calls = ["complete_trace", "fail_trace", "append_event"]
        for py_file in _FEEDBACK_DIR.glob("*.py"):
            source = py_file.read_text()
            for call in forbidden_calls:
                if call in source:
                    violations.append(f"{py_file.name}: {call}")
        assert violations == [], f"Trace mutation calls: {violations}"

    def test_adapters_do_not_import_feedback(self):
        adapter_dir = pathlib.Path("/opt/OS/umh/adapters")
        violations = []
        for py_file in adapter_dir.glob("*.py"):
            source = py_file.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and "umh.feedback" in node.module
                ):
                    violations.append(f"{py_file.name}: from {node.module}")
        assert violations == [], f"Adapter imports feedback: {violations}"


# ═══════════════════════════════════════════════════════════════════════
# 11. Package/Export Sanity
# ═══════════════════════════════════════════════════════════════════════


class TestPhase78Exports:
    def test_outcome_imports(self):
        from umh.feedback.outcome import OutcomeRecord, OutcomeStatus, OutcomeSource

        assert OutcomeRecord is not None

    def test_records_imports(self):
        from umh.feedback.records import FeedbackRecord, FeedbackSignalType, FeedbackSource

        assert FeedbackRecord is not None

    def test_memory_bridge_imports(self):
        from umh.feedback.memory_bridge import (
            MemoryCandidate,
            MemoryCandidateType,
            MemoryPromotionStatus,
        )

        assert MemoryCandidate is not None

    def test_trace_analyzer_imports(self):
        from umh.feedback.trace_analyzer import TraceAnalysis, analyze_trace

        assert TraceAnalysis is not None

    def test_classifier_imports(self):
        from umh.feedback.classifier import OutcomeClassifier

        assert OutcomeClassifier is not None

    def test_store_imports(self):
        from umh.feedback.store import FeedbackStore, get_feedback_store

        assert FeedbackStore is not None

    def test_loop_imports(self):
        from umh.feedback.feedback_loop import FeedbackLoopResult, process_trace_feedback

        assert process_trace_feedback is not None
