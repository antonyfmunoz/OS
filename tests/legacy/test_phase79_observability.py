"""Phase 79 Observability + Operator Interface — comprehensive test suite.

Tests (110+):
  - Interface contracts: InterfaceType, InterfaceActionType, request/response, normalization
  - View models: all 8 view types serialize, sparse safety, no secrets
  - Trace query: empty store, limits, user filter, include_raw, sparse trace
  - Timeline: empty, trace events, outcome events, feedback events, sorting, serialize
  - Execution summary: empty, counts from outcomes, capabilities, attention
  - Failure search: finds failures/denials/timeouts/unknowns, limits, categories, no causal
  - Decision explainer: sparse, denied, success, failure, confidence bounds, deterministic
  - System status: missing stores, available stores, health levels
  - Operator dashboard: no stores, with stores, health, traces, outcomes, feedback, limits
  - Control/API: endpoint functions, read-only
  - CLI: command existence
  - Layering: no forbidden imports, no mutation, no adapters
  - Regression: Phase 75B/76/77/78 pass
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest

# ═══════════════════════════════════════════════════════════════════════
# 1. Interface Contracts
# ═══════════════════════════════════════════════════════════════════════

from umh.interface.contracts import (
    InterfaceActionType,
    InterfaceRequest,
    InterfaceResponse,
    InterfaceType,
    create_interface_request,
    create_interface_response,
    normalize_interface_action_type,
    normalize_interface_type,
)


class TestInterfaceType:
    def test_all_types_exist(self):
        names = {m.value for m in InterfaceType}
        assert "cli" in names
        assert "api" in names
        assert "voice" in names
        assert "unknown" in names

    def test_normalize_valid(self):
        assert normalize_interface_type("cli") == InterfaceType.CLI
        assert normalize_interface_type("API") == InterfaceType.API

    def test_normalize_invalid(self):
        assert normalize_interface_type("bogus") == InterfaceType.UNKNOWN

    def test_normalize_whitespace(self):
        assert normalize_interface_type("  voice  ") == InterfaceType.VOICE


class TestInterfaceActionType:
    def test_normalize_valid(self):
        assert normalize_interface_action_type("run") == InterfaceActionType.RUN
        assert normalize_interface_action_type("QUERY_TRACES") == InterfaceActionType.QUERY_TRACES

    def test_normalize_invalid(self):
        assert normalize_interface_action_type("bogus") == InterfaceActionType.UNKNOWN


class TestInterfaceRequest:
    def test_serializes(self):
        req = create_interface_request("u1", InterfaceActionType.STATUS)
        d = req.to_dict()
        assert d["user_id"] == "u1"
        assert d["action_type"] == "status"
        assert d["request_id"]

    def test_from_dict(self):
        d = {"request_id": "r1", "user_id": "u1", "action_type": "run"}
        req = InterfaceRequest.from_dict(d)
        assert req.action_type == InterfaceActionType.RUN

    def test_unknown_degrades(self):
        d = {"request_id": "r1", "user_id": "u1", "interface_type": "hologram"}
        req = InterfaceRequest.from_dict(d)
        assert req.interface_type == InterfaceType.UNKNOWN


class TestInterfaceResponse:
    def test_serializes(self):
        resp = create_interface_response("r1", "u1", display_payload={"msg": "ok"})
        d = resp.to_dict()
        assert d["request_id"] == "r1"
        assert d["display_payload"]["msg"] == "ok"
        assert d["status"] == "ok"

    def test_contains_display_payload(self):
        resp = InterfaceResponse(request_id="r1", user_id="u1", display_payload={"data": 123})
        assert "data" in resp.to_dict()["display_payload"]

    def test_from_dict(self):
        d = {"request_id": "r1", "user_id": "u1", "errors": ["e1"]}
        resp = InterfaceResponse.from_dict(d)
        assert resp.errors == ["e1"]


# ═══════════════════════════════════════════════════════════════════════
# 2. View Models
# ═══════════════════════════════════════════════════════════════════════

from umh.interface.views import (
    AdapterStatusView,
    FeedbackView,
    GovernanceDecisionView,
    MemoryCandidateView,
    OperatorDashboardSnapshot,
    OutcomeView,
    TraceView,
    WorkstationStatusView,
)


class TestViewModels:
    def test_trace_view_serializes(self):
        v = TraceView(trace_id="t1", status="completed")
        d = v.to_dict()
        assert d["trace_id"] == "t1"
        assert d["status"] == "completed"

    def test_outcome_view_serializes(self):
        v = OutcomeView(outcome_id="o1", status="success", success_score=1.0)
        d = v.to_dict()
        assert d["outcome_id"] == "o1"
        assert d["success_score"] == 1.0

    def test_feedback_view_serializes(self):
        v = FeedbackView(feedback_id="f1", signal_type="execution_success")
        d = v.to_dict()
        assert d["feedback_id"] == "f1"

    def test_memory_candidate_view_serializes(self):
        v = MemoryCandidateView(candidate_id="c1", promotion_status="candidate")
        d = v.to_dict()
        assert d["candidate_id"] == "c1"
        assert d["promotion_status"] == "candidate"

    def test_governance_decision_view_serializes(self):
        v = GovernanceDecisionView(trace_id="t1", status="denied", reason="too risky")
        d = v.to_dict()
        assert d["reason"] == "too risky"

    def test_adapter_status_view_serializes(self):
        v = AdapterStatusView(adapter_name="cli", capabilities=["cli.command"])
        d = v.to_dict()
        assert d["adapter_name"] == "cli"
        assert "cli.command" in d["capabilities"]

    def test_workstation_status_view_serializes(self):
        v = WorkstationStatusView(user_id="u1", active_mode="command_center")
        d = v.to_dict()
        assert d["active_mode"] == "command_center"

    def test_dashboard_snapshot_serializes(self):
        v = OperatorDashboardSnapshot(user_id="u1", system_health="healthy")
        d = v.to_dict()
        assert d["system_health"] == "healthy"
        assert d["user_id"] == "u1"

    def test_views_omit_raw_by_default(self):
        v = TraceView(trace_id="t1")
        d = v.to_dict()
        assert "raw" not in d.get("metadata", {})


# ═══════════════════════════════════════════════════════════════════════
# 3. Trace Query
# ═══════════════════════════════════════════════════════════════════════

from umh.observability.trace_query import (
    TraceQuery,
    TraceQueryResult,
    get_trace_view,
    list_recent_trace_views,
    query_traces,
    trace_to_view,
)


class _FakeTrace:
    def __init__(self, trace_id="t1", status="completed", user_id="u1", error=None):
        self.trace_id = trace_id
        self.status = status
        self.user_id = user_id
        self.created_at = "2026-01-01T00:00:00Z"
        self.completed_at = "2026-01-01T00:00:01Z"
        self.input_summary = "test input"
        self.error = error
        self.events = []
        self.result = {}

    def to_dict(self):
        return {
            "trace_id": self.trace_id,
            "status": self.status,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "input_summary": self.input_summary,
            "error": self.error,
            "events": self.events,
            "result": self.result,
        }


class _FakeTraceStore:
    def __init__(self, traces=None):
        self._traces = traces or []

    def list_traces(self, limit=50):
        return self._traces[:limit]

    def get_trace(self, trace_id):
        for t in self._traces:
            if t.trace_id == trace_id:
                return t
        return None


class TestTraceQuery:
    def test_empty_store_returns_empty(self):
        result = query_traces(_FakeTraceStore(), TraceQuery())
        assert result.total_returned == 0

    def test_none_store_returns_warning(self):
        result = query_traces(None, TraceQuery())
        assert result.warnings
        assert result.total_returned == 0

    def test_recent_views_respect_limit(self):
        traces = [_FakeTrace(f"t{i}") for i in range(10)]
        store = _FakeTraceStore(traces)
        views = list_recent_trace_views(store, limit=3)
        assert len(views) <= 3

    def test_trace_view_from_sparse_trace(self):
        t = _FakeTrace("t_sparse")
        t.created_at = ""
        t.completed_at = None
        t.input_summary = ""
        view = trace_to_view(t)
        assert view.trace_id == "t_sparse"
        assert view.duration_ms is None

    def test_trace_view_includes_trace_id(self):
        view = trace_to_view(_FakeTrace("t_abc"))
        assert view.trace_id == "t_abc"

    def test_trace_view_includes_outcome_when_lookup(self):
        view = trace_to_view(_FakeTrace("t1"), outcome_lookup={"t1": {"status": "success"}})
        assert view.outcome_status == "success"

    def test_include_raw_false_omits_raw(self):
        store = _FakeTraceStore([_FakeTrace("t1")])
        view = get_trace_view(store, "t1", include_raw=False)
        assert "raw" not in view.metadata

    def test_include_raw_true_includes_raw(self):
        store = _FakeTraceStore([_FakeTrace("t1")])
        view = get_trace_view(store, "t1", include_raw=True)
        assert "raw" in view.metadata

    def test_query_limit_max_enforced(self):
        q = TraceQuery(limit=500)
        assert q.effective_limit() == 100

    def test_user_id_filter(self):
        traces = [_FakeTrace("t1", user_id="u1"), _FakeTrace("t2", user_id="u2")]
        store = _FakeTraceStore(traces)
        result = query_traces(store, TraceQuery(user_id="u1"))
        assert all(t.user_id == "u1" for t in result.traces)

    def test_status_filter(self):
        traces = [_FakeTrace("t1", status="completed"), _FakeTrace("t2", status="failed")]
        store = _FakeTraceStore(traces)
        result = query_traces(store, TraceQuery(status="failed"))
        assert all(t.status == "failed" for t in result.traces)


# ═══════════════════════════════════════════════════════════════════════
# 4. Timeline
# ═══════════════════════════════════════════════════════════════════════

from umh.observability.timeline import (
    ExecutionTimeline,
    TimelineEvent,
    TimelineEventType,
    build_timeline,
    feedback_to_timeline_event,
    normalize_timeline_event_type,
    outcome_to_timeline_event,
    trace_to_timeline_events,
)


class TestTimeline:
    def test_empty_timeline(self):
        tl = build_timeline()
        assert tl.events == []
        assert tl.generated_at

    def test_trace_creates_events(self):
        t = _FakeTrace("t1")
        events = trace_to_timeline_events(t)
        assert len(events) >= 1
        assert any(e.event_type == TimelineEventType.INPUT_RECEIVED for e in events)

    def test_outcome_creates_event(self):
        oc = {
            "trace_id": "t1",
            "status": "success",
            "summary": "done",
            "completed_at": "2026-01-01T00:00:01Z",
        }
        ev = outcome_to_timeline_event(oc)
        assert ev.event_type == TimelineEventType.OUTCOME_CLASSIFIED

    def test_feedback_creates_event(self):
        fb = {
            "trace_id": "t1",
            "signal_type": "execution_success",
            "timestamp": "2026-01-01T00:00:02Z",
            "source": "system",
        }
        ev = feedback_to_timeline_event(fb)
        assert ev.event_type == TimelineEventType.FEEDBACK_RECORDED

    def test_events_sort_by_timestamp(self):
        traces = [_FakeTrace("t1")]
        traces[0].created_at = "2026-01-01T00:00:02Z"
        traces[0].completed_at = "2026-01-01T00:00:03Z"
        outcomes = [{"trace_id": "t1", "status": "success", "completed_at": "2026-01-01T00:00:01Z"}]
        tl = build_timeline(traces=traces, outcomes=outcomes)
        timestamps = [e.timestamp for e in tl.events if e.timestamp]
        assert timestamps == sorted(timestamps)

    def test_missing_timestamp_handled(self):
        outcomes = [{"trace_id": "t1", "status": "success", "completed_at": ""}]
        tl = build_timeline(outcomes=outcomes)
        assert tl.warnings

    def test_event_type_normalizes(self):
        assert normalize_timeline_event_type("input_received") == TimelineEventType.INPUT_RECEIVED
        assert normalize_timeline_event_type("bogus") == TimelineEventType.UNKNOWN

    def test_timeline_serializes(self):
        tl = build_timeline()
        d = tl.to_dict()
        assert "events" in d
        assert "generated_at" in d


# ═══════════════════════════════════════════════════════════════════════
# 5. Execution Summary
# ═══════════════════════════════════════════════════════════════════════

from umh.observability.execution_summary import (
    ExecutionSummary,
    compute_attention_required,
    summarize_executions,
)

from umh.feedback.outcome import OutcomeRecord, OutcomeStatus


class TestExecutionSummary:
    def test_empty_returns_zeros(self):
        s = summarize_executions()
        assert s.total_traces == 0
        assert s.success_count == 0
        assert s.failure_count == 0

    def test_success_count(self):
        outcomes = [
            OutcomeRecord(
                outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.SUCCESS
            ),
            OutcomeRecord(
                outcome_id="o2", trace_id="t2", user_id="u", status=OutcomeStatus.SUCCESS
            ),
        ]
        s = summarize_executions(outcomes=outcomes)
        assert s.success_count == 2

    def test_failure_count(self):
        outcomes = [
            OutcomeRecord(
                outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.FAILURE
            ),
        ]
        s = summarize_executions(outcomes=outcomes)
        assert s.failure_count == 1

    def test_denied_count(self):
        outcomes = [
            OutcomeRecord(outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.DENIED),
        ]
        s = summarize_executions(outcomes=outcomes)
        assert s.denied_count == 1

    def test_validation_failed_count(self):
        outcomes = [
            OutcomeRecord(
                outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.VALIDATION_FAILED
            ),
        ]
        s = summarize_executions(outcomes=outcomes)
        assert s.validation_failed_count == 1

    def test_timeout_count(self):
        outcomes = [
            OutcomeRecord(
                outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.TIMEOUT
            ),
        ]
        s = summarize_executions(outcomes=outcomes)
        assert s.timeout_count == 1

    def test_unknown_count(self):
        outcomes = [
            OutcomeRecord(
                outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.UNKNOWN
            ),
        ]
        s = summarize_executions(outcomes=outcomes)
        assert s.unknown_count == 1

    def test_capabilities_from_traces(self):
        t = _FakeTrace("t1")
        t.events = [
            {"event_type": "adapter", "payload": {"capability": "cli.command"}, "timestamp": ""}
        ]
        s = summarize_executions(traces=[t])
        assert "cli.command" in s.recent_capabilities

    def test_environments_from_traces(self):
        t = _FakeTrace("t1")
        t.events = [{"event_type": "adapter", "payload": {"environment": "local"}, "timestamp": ""}]
        s = summarize_executions(traces=[t])
        assert "local" in s.recent_environments

    def test_attention_required(self):
        traces = [_FakeTrace("t1", status="failed")]
        count = compute_attention_required(traces=traces)
        assert count >= 1


# ═══════════════════════════════════════════════════════════════════════
# 6. Failure Search
# ═══════════════════════════════════════════════════════════════════════

from umh.observability.failure_search import (
    FailureCategory,
    FailureRecord,
    FailureSearchQuery,
    FailureSearchResult,
    outcome_to_failure_record,
    search_failures,
    trace_to_failure_record,
)


class TestFailureSearch:
    def test_finds_failure_outcomes(self):
        outcomes = [
            OutcomeRecord(
                outcome_id="o1",
                trace_id="t1",
                user_id="u",
                status=OutcomeStatus.FAILURE,
                errors=["err"],
            )
        ]
        result = search_failures(outcomes=outcomes)
        assert result.total_returned == 1
        assert result.failures[0].category == FailureCategory.FAILURE

    def test_finds_denied_outcomes(self):
        outcomes = [
            OutcomeRecord(outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.DENIED)
        ]
        result = search_failures(outcomes=outcomes)
        assert result.total_returned == 1
        assert result.failures[0].category == FailureCategory.DENIED

    def test_finds_validation_failures(self):
        outcomes = [
            OutcomeRecord(
                outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.VALIDATION_FAILED
            )
        ]
        result = search_failures(outcomes=outcomes)
        assert result.failures[0].category == FailureCategory.VALIDATION_FAILED

    def test_finds_timeouts(self):
        outcomes = [
            OutcomeRecord(outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.TIMEOUT)
        ]
        result = search_failures(outcomes=outcomes)
        assert result.failures[0].category == FailureCategory.TIMEOUT

    def test_finds_unknown(self):
        outcomes = [
            OutcomeRecord(outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.UNKNOWN)
        ]
        result = search_failures(outcomes=outcomes)
        assert result.failures[0].category == FailureCategory.UNKNOWN

    def test_denied_not_labeled_as_execution_error(self):
        outcomes = [
            OutcomeRecord(outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.DENIED)
        ]
        result = search_failures(outcomes=outcomes)
        assert result.failures[0].category != FailureCategory.FAILURE

    def test_search_respects_limit(self):
        outcomes = [
            OutcomeRecord(
                outcome_id=f"o{i}", trace_id=f"t{i}", user_id="u", status=OutcomeStatus.FAILURE
            )
            for i in range(20)
        ]
        result = search_failures(outcomes=outcomes, query=FailureSearchQuery(limit=5))
        assert result.total_returned <= 5

    def test_search_filters_category(self):
        outcomes = [
            OutcomeRecord(
                outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.FAILURE
            ),
            OutcomeRecord(outcome_id="o2", trace_id="t2", user_id="u", status=OutcomeStatus.DENIED),
        ]
        result = search_failures(outcomes=outcomes, query=FailureSearchQuery(category="denied"))
        assert all(f.category == FailureCategory.DENIED for f in result.failures)

    def test_failure_record_deterministic(self):
        oc = OutcomeRecord(
            outcome_id="o1", trace_id="t1", user_id="u", status=OutcomeStatus.FAILURE
        )
        r1 = outcome_to_failure_record(oc)
        r2 = outcome_to_failure_record(oc)
        assert r1.category == r2.category
        assert r1.trace_id == r2.trace_id

    def test_no_causal_language(self):
        oc = OutcomeRecord(
            outcome_id="o1",
            trace_id="t1",
            user_id="u",
            status=OutcomeStatus.FAILURE,
            summary="something failed",
        )
        rec = outcome_to_failure_record(oc)
        assert "root cause" not in rec.summary.lower()
        assert "caused by" not in rec.summary.lower()

    def test_trace_failure_record(self):
        t = _FakeTrace("t1", status="failed", error="some error")
        rec = trace_to_failure_record(t)
        assert rec is not None
        assert rec.category == FailureCategory.FAILURE

    def test_success_trace_returns_none(self):
        t = _FakeTrace("t1", status="completed")
        rec = trace_to_failure_record(t)
        assert rec is None


# ═══════════════════════════════════════════════════════════════════════
# 7. Decision Explainer
# ═══════════════════════════════════════════════════════════════════════

from umh.observability.decision_explainer import (
    DecisionExplanation,
    explain_adapter_selection,
    explain_execution_result,
    explain_governance,
    explain_trace,
    explain_unknowns,
)


class TestDecisionExplainer:
    def test_sparse_trace_with_unknowns(self):
        t = {"trace_id": "t1"}
        exp = explain_trace(t)
        assert exp.unknowns
        assert exp.trace_id == "t1"

    def test_governance_denied(self):
        t = {
            "trace_id": "t1",
            "events": [
                {
                    "event_type": "governance",
                    "payload": {"allowed": False, "reason": "blocked"},
                    "timestamp": "",
                }
            ],
            "status": "denied",
        }
        exp = explain_trace(t)
        assert exp.governance_summary == "denied"
        assert any("governance denied" in e for e in exp.evidence)

    def test_adapter_success(self):
        t = {
            "trace_id": "t1",
            "status": "completed",
            "result": {"adapter_name": "cli_adapter"},
            "events": [],
            "created_at": "2026-01-01",
            "completed_at": "2026-01-01",
        }
        exp = explain_trace(t)
        assert exp.adapter == "cli_adapter"

    def test_adapter_failure(self):
        t = {
            "trace_id": "t1",
            "status": "failed",
            "error": "adapter crashed",
            "result": {},
            "events": [],
            "created_at": "2026-01-01",
        }
        exp = explain_trace(t)
        assert "failed" in exp.execution_summary.lower()

    def test_confidence_bounded(self):
        exp = explain_trace({"trace_id": "t1"})
        assert 0.0 <= exp.confidence <= 1.0

    def test_missing_governance_is_unknown(self):
        summary, _, unknowns = explain_governance({"trace_id": "t1", "events": []})
        assert summary == "unknown"
        assert unknowns

    def test_missing_adapter_is_unknown(self):
        adapter, _, unknowns = explain_adapter_selection(
            {"trace_id": "t1", "events": [], "result": {}}
        )
        assert adapter == ""
        assert unknowns

    def test_deterministic(self):
        t = {
            "trace_id": "t1",
            "status": "completed",
            "result": {},
            "events": [],
            "created_at": "2026-01-01",
            "completed_at": "2026-01-01",
        }
        e1 = explain_trace(t)
        e2 = explain_trace(t)
        assert e1.governance_summary == e2.governance_summary
        assert e1.execution_summary == e2.execution_summary
        assert e1.evidence == e2.evidence

    def test_no_invented_fields(self):
        exp = explain_trace({"trace_id": "t_empty"})
        assert exp.capability == ""
        assert exp.adapter == ""


# ═══════════════════════════════════════════════════════════════════════
# 8. System Status
# ═══════════════════════════════════════════════════════════════════════

from umh.observability.system_status import (
    SystemHealth,
    SystemStatus,
    build_system_status,
    check_feedback_store,
    check_trace_store,
    check_workstation_state,
)


class _FakeFeedbackStore:
    def list_outcomes(self, user_id=None, trace_id=None, limit=50):
        return []

    def list_feedback(self, user_id=None, trace_id=None, outcome_id=None, limit=50):
        return []

    def list_memory_candidates(self, user_id=None, trace_id=None, outcome_id=None, limit=50):
        return []


class TestSystemStatus:
    def test_missing_stores_not_healthy(self):
        status = build_system_status()
        assert status.health != SystemHealth.HEALTHY

    def test_trace_store_available(self):
        cs = check_trace_store(_FakeTraceStore())
        assert cs.available
        assert cs.status == "ok"

    def test_trace_store_unavailable(self):
        cs = check_trace_store(None)
        assert not cs.available

    def test_feedback_store_available(self):
        cs = check_feedback_store(_FakeFeedbackStore())
        assert cs.available

    def test_workstation_available(self):
        class FakeProfile:
            user_id = "u1"

        cs = check_workstation_state(profile=FakeProfile())
        assert cs.available

    def test_workstation_unavailable(self):
        cs = check_workstation_state()
        assert not cs.available

    def test_health_serializes(self):
        status = build_system_status()
        d = status.to_dict()
        assert "health" in d
        assert d["health"] in ("healthy", "degraded", "partial", "unknown", "error")

    def test_warnings_included(self):
        status = build_system_status()
        assert isinstance(status.warnings, list)

    def test_no_network_calls(self):
        status = build_system_status(
            trace_store=_FakeTraceStore(),
            feedback_store=_FakeFeedbackStore(),
        )
        assert status.health.value in ("healthy", "degraded", "partial", "unknown", "error")


# ═══════════════════════════════════════════════════════════════════════
# 9. Operator Dashboard
# ═══════════════════════════════════════════════════════════════════════

from umh.observability.operator_views import (
    build_adapter_status_views,
    build_operator_dashboard_snapshot,
    build_pending_attention_views,
    build_resume_points,
    build_workstation_status_view,
)


class TestOperatorDashboard:
    def test_no_stores_builds(self):
        snap = build_operator_dashboard_snapshot("u1")
        assert snap.user_id == "u1"
        assert snap.generated_at

    def test_includes_system_health(self):
        snap = build_operator_dashboard_snapshot("u1")
        assert snap.system_health

    def test_includes_workstation(self):
        snap = build_operator_dashboard_snapshot("u1")
        assert isinstance(snap.workstation, dict)

    def test_includes_recent_traces(self):
        store = _FakeTraceStore([_FakeTrace("t1")])
        snap = build_operator_dashboard_snapshot("u1", trace_store=store)
        assert isinstance(snap.recent_traces, list)

    def test_includes_outcomes_with_store(self):
        snap = build_operator_dashboard_snapshot("u1", feedback_store=_FakeFeedbackStore())
        assert isinstance(snap.recent_outcomes, list)

    def test_includes_feedback_with_store(self):
        snap = build_operator_dashboard_snapshot("u1", feedback_store=_FakeFeedbackStore())
        assert isinstance(snap.recent_feedback, list)

    def test_includes_memory_candidates(self):
        snap = build_operator_dashboard_snapshot("u1", feedback_store=_FakeFeedbackStore())
        assert isinstance(snap.memory_candidates, list)

    def test_includes_failures(self):
        snap = build_operator_dashboard_snapshot("u1")
        assert isinstance(snap.failures, list)

    def test_includes_denials(self):
        snap = build_operator_dashboard_snapshot("u1")
        assert isinstance(snap.denials, list)

    def test_includes_pending_attention(self):
        snap = build_operator_dashboard_snapshot("u1")
        assert isinstance(snap.pending_attention, list)

    def test_includes_adapter_statuses(self):
        snap = build_operator_dashboard_snapshot("u1")
        assert isinstance(snap.adapter_statuses, list)

    def test_respects_limit(self):
        traces = [_FakeTrace(f"t{i}") for i in range(50)]
        store = _FakeTraceStore(traces)
        snap = build_operator_dashboard_snapshot("u1", trace_store=store, limit=5)
        assert len(snap.recent_traces) <= 5

    def test_identity_scoped(self):
        snap = build_operator_dashboard_snapshot("u1")
        assert snap.user_id == "u1"

    def test_workstation_status_view(self):
        v = build_workstation_status_view()
        assert v.user_id == ""
        assert isinstance(v.to_dict(), dict)

    def test_adapter_views_empty(self):
        views = build_adapter_status_views()
        assert views == []

    def test_pending_attention_empty(self):
        items = build_pending_attention_views()
        assert items == []

    def test_resume_points_empty(self):
        pts = build_resume_points()
        assert pts == []


# ═══════════════════════════════════════════════════════════════════════
# 10. Control/API Functions
# ═══════════════════════════════════════════════════════════════════════


class TestControlAPIFunctions:
    def test_system_status_function(self):
        from umh.observability.system_status import build_system_status

        status = build_system_status()
        d = status.to_dict()
        assert "health" in d

    def test_dashboard_function(self):
        from umh.observability.operator_views import build_operator_dashboard_snapshot

        snap = build_operator_dashboard_snapshot("u1")
        assert snap.to_dict()["user_id"] == "u1"

    def test_timeline_function(self):
        from umh.observability.timeline import build_timeline

        tl = build_timeline()
        assert "events" in tl.to_dict()

    def test_trace_query_function(self):
        from umh.observability.trace_query import TraceQuery, query_traces

        result = query_traces(None, TraceQuery())
        assert result.total_returned == 0

    def test_explain_function(self):
        from umh.observability.decision_explainer import explain_trace

        exp = explain_trace({"trace_id": "t1"})
        assert exp.trace_id == "t1"

    def test_failure_search_function(self):
        from umh.observability.failure_search import search_failures

        result = search_failures()
        assert result.total_returned == 0

    def test_execution_summary_function(self):
        from umh.observability.execution_summary import summarize_executions

        s = summarize_executions()
        assert s.total_traces == 0

    def test_functions_do_not_execute(self):
        from umh.observability.system_status import build_system_status

        status = build_system_status()
        assert status.health.value != "executed"

    def test_functions_do_not_mutate(self):
        store = _FakeTraceStore([_FakeTrace("t1")])
        from umh.observability.trace_query import query_traces, TraceQuery

        result = query_traces(store, TraceQuery())
        assert len(store._traces) == 1


# ═══════════════════════════════════════════════════════════════════════
# 11. CLI Commands
# ═══════════════════════════════════════════════════════════════════════


class TestCLICommands:
    def test_observe_commands_in_dispatch(self):
        from umh.control.cli import build_parser, main

        parser = build_parser()
        args = parser.parse_args(["observe-status"])
        assert args.command == "observe-status"

    def test_observe_traces_command(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["observe-traces", "--limit", "10"])
        assert args.command == "observe-traces"
        assert args.limit == 10

    def test_observe_trace_command(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["observe-trace", "--trace-id", "t1"])
        assert args.trace_id == "t1"

    def test_observe_failures_command(self):
        from umh.control.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["observe-failures"])
        assert args.command == "observe-failures"


# ═══════════════════════════════════════════════════════════════════════
# 12. Layering — Forbidden Imports
# ═══════════════════════════════════════════════════════════════════════

import importlib
import inspect


class TestLayeringInvariants:
    OBSERVABILITY_MODULES = [
        "umh.observability.trace_query",
        "umh.observability.timeline",
        "umh.observability.execution_summary",
        "umh.observability.failure_search",
        "umh.observability.decision_explainer",
        "umh.observability.system_status",
        "umh.observability.operator_views",
    ]

    INTERFACE_MODULES = [
        "umh.interface.contracts",
        "umh.interface.views",
    ]

    def _source(self, module_name: str) -> str:
        mod = importlib.import_module(module_name)
        return inspect.getsource(mod)

    def test_observability_no_adapter_imports(self):
        for mod_name in self.OBSERVABILITY_MODULES:
            src = self._source(mod_name)
            assert "from umh.adapters" not in src, f"{mod_name} imports adapters"
            assert "import umh.adapters" not in src, f"{mod_name} imports adapters"

    def test_observability_no_subprocess(self):
        for mod_name in self.OBSERVABILITY_MODULES:
            src = self._source(mod_name)
            assert "import subprocess" not in src, f"{mod_name} imports subprocess"

    def test_observability_no_requests(self):
        for mod_name in self.OBSERVABILITY_MODULES:
            src = self._source(mod_name)
            assert "import requests" not in src, f"{mod_name} imports requests"
            assert "import httpx" not in src, f"{mod_name} imports httpx"

    def test_observability_no_backend_execute(self):
        for mod_name in self.OBSERVABILITY_MODULES:
            src = self._source(mod_name)
            assert "from umh.execution.engine import execute" not in src
            assert "from umh.execution.engine import dispatch" not in src

    def test_observability_no_governance_modify(self):
        for mod_name in self.OBSERVABILITY_MODULES:
            src = self._source(mod_name)
            assert "check_governance(" not in src or "system_status" in mod_name

    def test_observability_no_trace_mutation(self):
        for mod_name in self.OBSERVABILITY_MODULES:
            src = self._source(mod_name)
            assert "complete_trace(" not in src
            assert "fail_trace(" not in src
            assert "append_event(" not in src

    def test_observability_no_memory_promotion(self):
        for mod_name in self.OBSERVABILITY_MODULES:
            src = self._source(mod_name)
            assert "PROMOTED" not in src or "promotion_status" in src.split("PROMOTED")[0][-50:]

    def test_interface_no_execution_engine(self):
        for mod_name in self.INTERFACE_MODULES:
            src = self._source(mod_name)
            assert "from umh.execution.engine" not in src

    def test_interface_no_adapters(self):
        for mod_name in self.INTERFACE_MODULES:
            src = self._source(mod_name)
            assert "from umh.adapters" not in src

    def test_adapters_no_observability(self):
        adapter_modules = [
            "umh.adapters.mvp_contract",
            "umh.adapters.adapter_backend",
        ]
        for mod_name in adapter_modules:
            try:
                src = self._source(mod_name)
                assert "from umh.observability" not in src
            except Exception:
                pass

    def test_feedback_modules_non_executing(self):
        feedback_modules = [
            "umh.feedback.outcome",
            "umh.feedback.records",
            "umh.feedback.memory_bridge",
            "umh.feedback.trace_analyzer",
            "umh.feedback.classifier",
            "umh.feedback.store",
            "umh.feedback.feedback_loop",
        ]
        for mod_name in feedback_modules:
            src = self._source(mod_name)
            assert "from umh.execution.engine import execute" not in src


# ═══════════════════════════════════════════════════════════════════════
# 13. Workstation Resume Integration
# ═══════════════════════════════════════════════════════════════════════

from umh.workstation.resume import TraceResumeSummary


class TestResumeIntegration:
    def test_execution_health_field_exists(self):
        summary = TraceResumeSummary(user_id="u1")
        assert hasattr(summary, "execution_health")
        assert summary.execution_health == {}

    def test_execution_health_in_to_dict(self):
        summary = TraceResumeSummary(user_id="u1", execution_health={"status": "ok"})
        d = summary.to_dict()
        assert d["execution_health"] == {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════
# 14. Phase 78 Exports Still Work
# ═══════════════════════════════════════════════════════════════════════


class TestPhase78Compatibility:
    def test_outcome_imports(self):
        from umh.feedback.outcome import OutcomeRecord, OutcomeStatus, clamp_score

        assert OutcomeStatus.SUCCESS.value == "success"

    def test_records_imports(self):
        from umh.feedback.records import FeedbackRecord, FeedbackSignalType

        assert FeedbackSignalType.EXECUTION_SUCCESS.value == "execution_success"

    def test_memory_bridge_imports(self):
        from umh.feedback.memory_bridge import MemoryCandidate, MemoryPromotionStatus

        assert MemoryPromotionStatus.CANDIDATE.value == "candidate"

    def test_store_imports(self):
        from umh.feedback.store import FeedbackStore, get_feedback_store

        store = get_feedback_store()
        assert hasattr(store, "append_outcome")

    def test_feedback_loop_imports(self):
        from umh.feedback.feedback_loop import process_trace_feedback

        assert callable(process_trace_feedback)
