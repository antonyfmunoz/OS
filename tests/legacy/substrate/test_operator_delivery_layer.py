"""Comprehensive tests for the operator delivery layer.

Validates:
  1. Formatter — success/failure/approval summaries, missing fields, markdown reports
  2. Artifacts — filename determinism, bytes, UTF-8, temp write, validation
  3. Approvals — correlation, dedup, expiry, reject/approve, resolution responses
  4. Runtime session — start/touch/end, mode persistence, no-session fallback
  5. Mode system — ACTIVE/PASSIVE/AUTONOMOUS gating, delivery classification
  6. Integration — full trace → summary + artifact pipeline

Run directly:
    python3 tests/substrate/test_operator_delivery_layer.py
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    tag = "PASS" if passed else "FAIL"
    if not passed:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def _section(name: str) -> None:
    print(f"\n── {name} ──")


# ═══════════════════════════════════════════════════════════════════════════
# Test fixtures
# ═══════════════════════════════════════════════════════════════════════════

from umh.substrate.operator_trace import OperatorTrace  # noqa: E402
from umh.substrate.runtime_mode import (  # noqa: E402
    RuntimeMode,
    DeliveryClass,
    should_deliver,
    classify_delivery,
    resolve_mode,
    mode_to_dict,
    DEFAULT_MODE,
)
from umh.substrate.operator_delivery import (  # noqa: E402
    format_completion_summary,
    format_failure_summary,
    format_approval_summary,
    build_full_report_markdown,
    build_report_filename,
    build_operator_response,
)
from umh.substrate.operator_artifacts import (  # noqa: E402
    ReportArtifact,
    build_operator_report_artifact,
    build_approval_context_artifact,
    build_text_artifact,
    cleanup_artifact,
    validate_artifact,
)
from umh.substrate.operator_approvals import (  # noqa: E402
    ApprovalStatus,
    ApprovalRequest,
    ApprovalStore,
    build_approval_request,
    approve,
    reject,
    expire,
    cancel,
    format_resolution_response,
    reset_for_tests as reset_approvals,
)
from umh.substrate.runtime_session import (  # noqa: E402
    RuntimeSessionState,
    RuntimeSessionStore,
    start_runtime_session,
    touch_runtime_session,
    end_runtime_session,
    record_summary_sent,
)


def _make_trace(
    *,
    intent_type: str = "morning_brief",
    terminal_status: str = "completed",
    terminal_reason: str = "Brief delivered",
    steps_total: int = 3,
    steps_executed: int = 3,
    events_processed: int = 7,
    mutations_applied: int = 4,
    ingress_source: str = "discord",
    ingress_transport: str = "text",
    ingress_text: str = "run morning brief",
    intent_id: str = "int_abc123",
    plan_id: str = "plan_001",
    variant_id: str = "var_001",
) -> OperatorTrace:
    return OperatorTrace(
        intent_type=intent_type,
        terminal_status=terminal_status,
        terminal_reason=terminal_reason,
        steps_total=steps_total,
        steps_executed=steps_executed,
        events_processed=events_processed,
        mutations_applied=mutations_applied,
        ingress_source=ingress_source,
        ingress_transport=ingress_transport,
        ingress_text=ingress_text,
        intent_id=intent_id,
        plan_id=plan_id,
        variant_id=variant_id,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. Formatter tests
# ═══════════════════════════════════════════════════════════════════════════


def test_formatter_success_summary() -> None:
    _section("Formatter: success summary")
    trace = _make_trace()
    summary = format_completion_summary(
        trace,
        title="Morning Brief",
        result_text="Daily brief generated and delivered",
        started_at="2026-04-17T08:00:00+00:00",
        completed_at="2026-04-17T08:00:05+00:00",
    )
    _report("contains ✅", "✅" in summary)
    _report("contains title", "Morning Brief" in summary)
    _report("contains result", "Daily brief generated" in summary)
    _report("contains steps", "3/3" in summary)
    _report("contains time", "5.0s" in summary)
    _report("contains mode", "active" in summary)
    _report("contains attachment note", "Full report attached" in summary)
    lines = summary.strip().split("\n")
    _report("max 7 lines", len(lines) <= 7, f"got {len(lines)} lines")


def test_formatter_failure_summary() -> None:
    _section("Formatter: failure summary")
    trace = _make_trace(
        terminal_status="failed",
        terminal_reason="API rate limit exceeded",
        steps_executed=1,
    )
    summary = format_failure_summary(
        trace,
        title="Email Send",
        cause="API rate limit exceeded",
        next_step="Retry in 60 seconds",
    )
    _report("contains ❌", "❌" in summary)
    _report("contains title", "Email Send" in summary)
    _report("contains cause", "API rate limit" in summary)
    _report("contains next step", "Retry in 60" in summary)
    _report("contains mode", "active" in summary)
    _report("contains attachment note", "Full report attached" in summary)
    lines = summary.strip().split("\n")
    _report("max 7 lines", len(lines) <= 7, f"got {len(lines)} lines")


def test_formatter_approval_summary() -> None:
    _section("Formatter: approval summary")
    summary = format_approval_summary(
        title="Deploy to Production",
        reason="This will push to main branch",
        approval_id="appr_abc123def4",
    )
    _report("contains ⚠️", "⚠️" in summary)
    _report("contains title", "Deploy to Production" in summary)
    _report("contains reason", "push to main" in summary)
    _report("contains approve/reject", "approve / reject" in summary)
    _report("contains ref", "appr_abc123d" in summary)
    _report("contains attachment note", "Context attached" in summary)
    lines = summary.strip().split("\n")
    _report("max 6 lines", len(lines) <= 6, f"got {len(lines)} lines")


def test_formatter_missing_fields() -> None:
    _section("Formatter: missing fields handled safely")
    empty_trace = OperatorTrace()

    # Should not raise
    summary = format_completion_summary(empty_trace)
    _report("success with empty trace", "✅" in summary)
    _report("defaults to 'Task'", "Task" in summary)

    fail_summary = format_failure_summary(empty_trace)
    _report("failure with empty trace", "❌" in fail_summary)

    approval = format_approval_summary()
    _report("approval with no args", "⚠️" in approval)


def test_formatter_full_report_markdown() -> None:
    _section("Formatter: full report markdown")
    trace = _make_trace()
    report = build_full_report_markdown(
        trace,
        title="Morning Brief",
        extra_sections={"Notes": "Everything went well."},
    )
    _report("starts with heading", report.startswith("# Morning Brief"))
    _report("has outcome section", "## Outcome" in report)
    _report("has ingress section", "## Ingress" in report)
    _report("has intent section", "## Intent" in report)
    _report("has plan section", "## Plan Selection" in report)
    _report("has scheduler section", "## Scheduler Stats" in report)
    _report("has extra section", "## Notes" in report)
    _report("has extra content", "Everything went well" in report)
    _report("has timestamp", "Generated:" in report)


def test_formatter_report_filename() -> None:
    _section("Formatter: report filename")
    trace = _make_trace()
    filename = build_report_filename(trace)
    _report("ends with .md", filename.endswith(".md"))
    _report("contains intent type slug", "morning_brief" in filename)
    _report("starts with report_", filename.startswith("report_"))


def test_formatter_build_operator_response() -> None:
    _section("Formatter: build_operator_response convenience")
    trace = _make_trace()
    payload = build_operator_response(trace, title="Test")
    _report("has summary key", "summary" in payload)
    _report("has full_report key", "full_report" in payload)
    _report("has filename key", "filename" in payload)
    _report("is_failure is False", payload["is_failure"] is False)
    _report("is_approval is False", payload["is_approval"] is False)

    # Failure case
    fail_trace = _make_trace(terminal_status="failed")
    fail_payload = build_operator_response(fail_trace)
    _report("failure payload is_failure True", fail_payload["is_failure"] is True)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Artifact tests
# ═══════════════════════════════════════════════════════════════════════════


def test_artifact_from_trace() -> None:
    _section("Artifact: build from trace")
    trace = _make_trace()
    artifact = build_operator_report_artifact(trace, title="Brief Report")

    _report("has artifact_id", artifact.artifact_id.startswith("art_"))
    _report("has filename", artifact.filename.endswith(".md"))
    _report("has content_type", artifact.content_type == "text/markdown")
    _report("body_text non-empty", len(artifact.body_text) > 0)
    _report("file_size > 0", artifact.file_size_bytes > 0)

    # File actually exists
    from pathlib import Path

    _report("file exists on disk", Path(artifact.file_path).exists())

    # Read back and check UTF-8
    content = Path(artifact.file_path).read_text(encoding="utf-8")
    _report("content matches body_text", content == artifact.body_text)

    # Cleanup
    cleanup_artifact(artifact)
    _report("cleanup removes file", not Path(artifact.file_path).exists())


def test_artifact_text() -> None:
    _section("Artifact: build from raw text")
    body = "# Test Report\n\nThis is a test.\n\n日本語テスト\n"
    artifact = build_text_artifact(body, prefix="test")

    _report("filename starts with test_", artifact.filename.startswith("test_"))
    _report("body matches", artifact.body_text == body)

    from pathlib import Path

    content = Path(artifact.file_path).read_text(encoding="utf-8")
    _report("UTF-8 content intact", "日本語テスト" in content)

    cleanup_artifact(artifact)


def test_artifact_approval_context() -> None:
    _section("Artifact: approval context")
    artifact = build_approval_context_artifact(
        approval_id="appr_test123",
        title="Deploy Check",
        context_text="Deploying version 2.0 to production.",
        metadata={"environment": "production", "version": "2.0"},
    )
    _report("contains approval ID", "appr_test123" in artifact.body_text)
    _report("contains context text", "Deploying version 2.0" in artifact.body_text)
    _report("contains metadata", "environment" in artifact.body_text)
    cleanup_artifact(artifact)


def test_artifact_validation() -> None:
    _section("Artifact: validation")
    trace = _make_trace()
    artifact = build_operator_report_artifact(trace)
    result = validate_artifact(artifact)
    _report("valid artifact passes", result["valid"] is True)
    _report("size_bytes > 0", result["size_bytes"] > 0)

    # Cleanup file then validate again
    cleanup_artifact(artifact)
    result2 = validate_artifact(artifact)
    _report("missing file fails validation", result2["valid"] is False)
    _report(
        "error is artifact_file_missing", result2["error"] == "artifact_file_missing"
    )


def test_artifact_filename_deterministic() -> None:
    _section("Artifact: filename determinism")
    trace = _make_trace()
    fn1 = build_report_filename(trace, prefix="report")
    # Same trace, same prefix → same structural pattern
    _report("filename has intent slug", "morning_brief" in fn1)
    _report("filename has prefix", fn1.startswith("report_"))
    _report("filename has .md", fn1.endswith(".md"))


# ═══════════════════════════════════════════════════════════════════════════
# 3. Approval tests
# ═══════════════════════════════════════════════════════════════════════════


def test_approval_create_and_resolve() -> None:
    _section("Approval: create and resolve")
    store = ApprovalStore()

    req = build_approval_request(
        correlation_id="corr_001",
        title="Deploy",
        reason="Pushing to prod",
    )
    submitted = store.submit(req)
    _report("submitted successfully", submitted is not None)
    _report("status is pending", req.status == ApprovalStatus.PENDING)
    _report("has approval_id", req.approval_id.startswith("appr_"))

    # Approve
    resolved = store.resolve(req.approval_id, action="approve")
    _report("resolve returns request", resolved is not None)
    _report("status is approved", resolved.status == ApprovalStatus.APPROVED)
    _report("resolved_by is operator", resolved.resolved_by == "operator")
    _report("resolved_at set", resolved.resolved_at is not None)


def test_approval_duplicate_suppression() -> None:
    _section("Approval: duplicate suppression")
    store = ApprovalStore()

    req1 = build_approval_request(
        correlation_id="corr_dup",
        title="Deploy",
        reason="First request",
    )
    req2 = build_approval_request(
        correlation_id="corr_dup",
        title="Deploy",
        reason="Second request",
    )

    result1 = store.submit(req1)
    result2 = store.submit(req2)

    _report("first accepted", result1 is not None)
    _report("second suppressed", result2 is None)


def test_approval_duplicate_after_terminal() -> None:
    _section("Approval: new request allowed after terminal")
    store = ApprovalStore()

    req1 = build_approval_request(
        correlation_id="corr_terminal",
        title="Deploy",
        reason="First",
    )
    store.submit(req1)
    store.resolve(req1.approval_id, action="reject")

    req2 = build_approval_request(
        correlation_id="corr_terminal",
        title="Deploy",
        reason="Second try",
    )
    result = store.submit(req2)
    _report("new request after reject accepted", result is not None)


def test_approval_expiry() -> None:
    _section("Approval: expiry")
    store = ApprovalStore()

    req = build_approval_request(
        correlation_id="corr_expire",
        title="Quick Action",
        reason="Time sensitive",
        timeout_s=1,  # 1 second timeout
    )
    store.submit(req)

    # Wait for expiry
    time.sleep(1.1)

    retrieved = store.get(req.approval_id)
    _report("expired after timeout", retrieved.status == ApprovalStatus.EXPIRED)

    # Resolution after expiry is clean
    response = format_resolution_response(retrieved)
    _report("expiry response has ⏰", "⏰" in response)
    _report("expiry response mentions timeout", "No response received" in response)


def test_approval_reject_path() -> None:
    _section("Approval: reject path")
    store = ApprovalStore()

    req = build_approval_request(
        correlation_id="corr_reject",
        title="Delete Database",
        reason="Dropping staging tables",
    )
    store.submit(req)
    store.resolve(req.approval_id, action="reject", detail="Too risky")

    _report("status is rejected", req.status == ApprovalStatus.REJECTED)
    response = format_resolution_response(req)
    _report("reject response has 🚫", "🚫" in response)


def test_approval_cancel() -> None:
    _section("Approval: cancel")
    req = build_approval_request(
        correlation_id="corr_cancel",
        title="Cancelled Task",
        reason="No longer needed",
    )
    cancel(req, detail="Task superseded")
    _report("status is cancelled", req.status == ApprovalStatus.CANCELLED)
    _report("detail recorded", req.resolution_detail == "Task superseded")


def test_approval_idempotent_resolution() -> None:
    _section("Approval: idempotent resolution (no double-approve)")
    req = build_approval_request(
        correlation_id="corr_idempotent",
        title="Test",
        reason="Test",
    )
    approve(req, resolved_by="operator1")
    original_resolved_at = req.resolved_at

    # Try to reject after already approved — should be ignored
    reject(req, resolved_by="operator2")
    _report("status stays approved", req.status == ApprovalStatus.APPROVED)
    _report("resolved_by unchanged", req.resolved_by == "operator1")
    _report("resolved_at unchanged", req.resolved_at == original_resolved_at)


def test_approval_store_stats() -> None:
    _section("Approval: store stats")
    store = ApprovalStore()

    for i in range(5):
        req = build_approval_request(
            correlation_id=f"corr_stats_{i}",
            title=f"Task {i}",
            reason="Test",
        )
        store.submit(req)
        if i < 2:
            store.resolve(req.approval_id, action="approve")

    stats = store.stats()
    _report("total is 5", stats.get("total") == 5)
    _report("approved is 2", stats.get("approved") == 2)
    _report("pending is 3", stats.get("pending") == 3)


def test_approval_get_by_correlation() -> None:
    _section("Approval: get by correlation")
    store = ApprovalStore()

    req = build_approval_request(
        correlation_id="corr_lookup",
        title="Lookup Test",
        reason="Testing correlation lookup",
    )
    store.submit(req)

    found = store.get_by_correlation("corr_lookup")
    _report("found by correlation", found is not None)
    _report("correct approval_id", found.approval_id == req.approval_id)

    not_found = store.get_by_correlation("corr_nonexistent")
    _report("not found returns None", not_found is None)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Runtime session tests
# ═══════════════════════════════════════════════════════════════════════════


def test_session_start() -> None:
    _section("Session: start")
    session = start_runtime_session(mode=RuntimeMode.ACTIVE, transport="discord")
    _report("has session_id", session.session_id.startswith("rs_"))
    _report("started_at set", session.started_at is not None)
    _report("is_active", session.is_active is True)
    _report("mode is ACTIVE", session.active_mode == RuntimeMode.ACTIVE)
    _report("transport is discord", session.active_operator_transport == "discord")
    _report("open_task_count is 0", session.open_task_count == 0)


def test_session_touch() -> None:
    _section("Session: touch")
    session = start_runtime_session()
    original_time = session.last_active_at

    time.sleep(0.05)
    touch_runtime_session(session, open_task_count=5)

    _report("last_active_at updated", session.last_active_at > original_time)
    _report("open_task_count set", session.open_task_count == 5)


def test_session_end() -> None:
    _section("Session: end")
    session = start_runtime_session()
    _report("is_active before end", session.is_active is True)

    end_runtime_session(session)
    _report("is_active after end", session.is_active is False)
    _report("ended_at set", session.ended_at is not None)


def test_session_record_summary() -> None:
    _section("Session: record summary sent")
    session = start_runtime_session()
    _report("last_summary_at initially None", session.last_summary_at is None)

    record_summary_sent(session)
    _report("last_summary_at set", session.last_summary_at is not None)


def test_session_mode_persistence() -> None:
    _section("Session: mode persistence via serialization")
    session = start_runtime_session(mode=RuntimeMode.PASSIVE)
    d = session.to_dict()
    _report("mode serializes to passive", d["active_mode"] == "passive")

    restored = RuntimeSessionState.from_dict(d)
    _report("mode restores to PASSIVE", restored.active_mode == RuntimeMode.PASSIVE)


def test_session_no_session_fallback() -> None:
    _section("Session: no-session fallback")
    RuntimeSessionStore.reset_for_tests()
    store = RuntimeSessionStore(autoload=False)

    result = store.get()
    _report("get returns None when empty", result is None)

    touch_result = store.touch()
    _report("touch returns None when empty", touch_result is None)

    end_result = store.end()
    _report("end returns None when empty", end_result is None)


def test_session_store_lifecycle() -> None:
    _section("Session: store lifecycle")
    store = RuntimeSessionStore(autoload=False)

    session = store.start(mode=RuntimeMode.AUTONOMOUS, transport="voice")
    _report("start returns session", session is not None)
    _report("mode is AUTONOMOUS", session.active_mode == RuntimeMode.AUTONOMOUS)

    stored = store.get()
    _report("get returns same session", stored.session_id == session.session_id)

    touched = store.touch(open_task_count=3)
    _report("touch returns session", touched is not None)
    _report("task count updated", touched.open_task_count == 3)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Mode tests
# ═══════════════════════════════════════════════════════════════════════════


def test_mode_enum_values() -> None:
    _section("Mode: enum values")
    _report("ACTIVE value", RuntimeMode.ACTIVE.value == "active")
    _report("PASSIVE value", RuntimeMode.PASSIVE.value == "passive")
    _report("AUTONOMOUS value", RuntimeMode.AUTONOMOUS.value == "autonomous")
    _report("exactly 3 members", len(RuntimeMode) == 3)


def test_mode_resolve() -> None:
    _section("Mode: resolve from string")
    _report("resolve 'active'", resolve_mode("active") == RuntimeMode.ACTIVE)
    _report("resolve 'PASSIVE'", resolve_mode("PASSIVE") == RuntimeMode.PASSIVE)
    _report("resolve None", resolve_mode(None) == DEFAULT_MODE)
    _report("resolve ''", resolve_mode("") == DEFAULT_MODE)
    _report("resolve 'invalid'", resolve_mode("invalid") == DEFAULT_MODE)


def test_mode_active_delivers_all() -> None:
    _section("Mode: ACTIVE delivers all classes")
    for dc in DeliveryClass:
        result = should_deliver(RuntimeMode.ACTIVE, dc)
        _report(f"ACTIVE delivers {dc.value}", result is True)


def test_mode_passive_filters() -> None:
    _section("Mode: PASSIVE filters status/verbose")
    _report(
        "PASSIVE delivers CRITICAL",
        should_deliver(RuntimeMode.PASSIVE, DeliveryClass.CRITICAL) is True,
    )
    _report(
        "PASSIVE delivers COMPLETION",
        should_deliver(RuntimeMode.PASSIVE, DeliveryClass.COMPLETION) is True,
    )
    _report(
        "PASSIVE blocks STATUS",
        should_deliver(RuntimeMode.PASSIVE, DeliveryClass.STATUS) is False,
    )
    _report(
        "PASSIVE blocks VERBOSE",
        should_deliver(RuntimeMode.PASSIVE, DeliveryClass.VERBOSE) is False,
    )


def test_mode_autonomous_minimal() -> None:
    _section("Mode: AUTONOMOUS delivers only critical")
    _report(
        "AUTONOMOUS delivers CRITICAL",
        should_deliver(RuntimeMode.AUTONOMOUS, DeliveryClass.CRITICAL) is True,
    )
    _report(
        "AUTONOMOUS blocks COMPLETION",
        should_deliver(RuntimeMode.AUTONOMOUS, DeliveryClass.COMPLETION) is False,
    )
    _report(
        "AUTONOMOUS blocks STATUS",
        should_deliver(RuntimeMode.AUTONOMOUS, DeliveryClass.STATUS) is False,
    )
    _report(
        "AUTONOMOUS blocks VERBOSE",
        should_deliver(RuntimeMode.AUTONOMOUS, DeliveryClass.VERBOSE) is False,
    )


def test_mode_classify_delivery() -> None:
    _section("Mode: classify_delivery")
    _report(
        "failure → CRITICAL",
        classify_delivery(is_failure=True) == DeliveryClass.CRITICAL,
    )
    _report(
        "approval → CRITICAL",
        classify_delivery(is_approval=True) == DeliveryClass.CRITICAL,
    )
    _report(
        "completion → COMPLETION",
        classify_delivery(is_completion=True) == DeliveryClass.COMPLETION,
    )
    _report(
        "status → STATUS",
        classify_delivery(is_status=True) == DeliveryClass.STATUS,
    )
    _report(
        "nothing → VERBOSE",
        classify_delivery() == DeliveryClass.VERBOSE,
    )
    # Priority: failure overrides completion
    _report(
        "failure+completion → CRITICAL",
        classify_delivery(is_failure=True, is_completion=True)
        == DeliveryClass.CRITICAL,
    )


def test_mode_to_dict() -> None:
    _section("Mode: mode_to_dict")
    d = mode_to_dict(RuntimeMode.ACTIVE)
    _report("mode key present", d["mode"] == "active")
    _report("allowed_classes is list", isinstance(d["allowed_classes"], list))
    _report("is_default for ACTIVE", d["is_default"] is True)

    d2 = mode_to_dict(RuntimeMode.PASSIVE)
    _report("not default for PASSIVE", d2["is_default"] is False)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Integration tests
# ═══════════════════════════════════════════════════════════════════════════


def test_integration_trace_to_delivery() -> None:
    _section("Integration: trace → summary + artifact")
    trace = _make_trace()

    # Build delivery payload
    payload = build_operator_response(
        trace,
        title="Morning Brief",
        result_text="Brief delivered to #general",
        started_at="2026-04-17T08:00:00+00:00",
        completed_at="2026-04-17T08:00:12+00:00",
    )

    summary = payload["summary"]
    _report("summary has ✅", "✅" in summary)
    _report("summary has title", "Morning Brief" in summary)
    _report("summary under 500 chars", len(summary) < 500, f"got {len(summary)}")

    # Build artifact from same trace
    artifact = build_operator_report_artifact(trace, title="Morning Brief")
    _report("artifact file exists", artifact.file_size_bytes > 0)
    _report("artifact body has heading", "# Morning Brief" in artifact.body_text)

    # Validate artifact
    validation = validate_artifact(artifact)
    _report("artifact validates", validation["valid"] is True)

    # Cleanup
    cleanup_artifact(artifact)


def test_integration_failure_trace_to_delivery() -> None:
    _section("Integration: failure trace → summary + artifact")
    trace = _make_trace(
        terminal_status="failed",
        terminal_reason="Gemini API 429",
        steps_executed=1,
        steps_total=4,
    )

    payload = build_operator_response(
        trace,
        title="Email Campaign",
        cause="Gemini API rate limited",
        next_step="Retry after cooldown",
    )

    _report("is_failure True", payload["is_failure"] is True)
    _report("summary has ❌", "❌" in payload["summary"])
    _report("full_report has outcome", "## Outcome" in payload["full_report"])


def test_integration_approval_flow() -> None:
    _section("Integration: approval request → response → artifact")
    store = ApprovalStore()

    # Build and submit
    req = build_approval_request(
        correlation_id="corr_integ",
        title="Deploy v2.0",
        reason="Production deployment requires approval",
        context={"version": "2.0", "target": "production"},
    )
    store.submit(req)

    # Format summary
    summary = format_approval_summary(
        title=req.title,
        reason=req.reason,
        approval_id=req.approval_id,
    )
    _report("approval summary has ⚠️", "⚠️" in summary)

    # Build context artifact
    artifact = build_approval_context_artifact(
        approval_id=req.approval_id,
        title=req.title,
        context_text="Deploying version 2.0 to production environment.",
        metadata=req.context,
    )
    _report(
        "artifact has approval context", "Deploying version 2.0" in artifact.body_text
    )

    # Approve
    store.resolve(req.approval_id, action="approve")
    response = format_resolution_response(req)
    _report("resolution response has ✅", "✅" in response)

    cleanup_artifact(artifact)


def test_integration_mode_gated_delivery() -> None:
    _section("Integration: mode-gated delivery decision")

    # In ACTIVE mode, everything delivers
    dc = classify_delivery(is_status=True)
    _report("status classified", dc == DeliveryClass.STATUS)
    _report("ACTIVE allows status", should_deliver(RuntimeMode.ACTIVE, dc) is True)
    _report("PASSIVE blocks status", should_deliver(RuntimeMode.PASSIVE, dc) is False)
    _report(
        "AUTONOMOUS blocks status", should_deliver(RuntimeMode.AUTONOMOUS, dc) is False
    )

    # Failures always deliver
    dc_fail = classify_delivery(is_failure=True)
    _report("failure classified as CRITICAL", dc_fail == DeliveryClass.CRITICAL)
    for mode in RuntimeMode:
        _report(
            f"{mode.value} delivers failure",
            should_deliver(mode, dc_fail) is True,
        )


def test_integration_session_with_mode() -> None:
    _section("Integration: session tracks mode across lifecycle")
    session = start_runtime_session(mode=RuntimeMode.PASSIVE)
    _report("session starts PASSIVE", session.active_mode == RuntimeMode.PASSIVE)

    # Mode gating works with session's mode
    _report(
        "session mode gates status",
        should_deliver(session.active_mode, DeliveryClass.STATUS) is False,
    )
    _report(
        "session mode allows critical",
        should_deliver(session.active_mode, DeliveryClass.CRITICAL) is True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    print("Operator Delivery Layer — Comprehensive Tests")
    print("=" * 65)

    # 1. Formatter
    test_formatter_success_summary()
    test_formatter_failure_summary()
    test_formatter_approval_summary()
    test_formatter_missing_fields()
    test_formatter_full_report_markdown()
    test_formatter_report_filename()
    test_formatter_build_operator_response()

    # 2. Artifacts
    test_artifact_from_trace()
    test_artifact_text()
    test_artifact_approval_context()
    test_artifact_validation()
    test_artifact_filename_deterministic()

    # 3. Approvals
    test_approval_create_and_resolve()
    test_approval_duplicate_suppression()
    test_approval_duplicate_after_terminal()
    test_approval_expiry()
    test_approval_reject_path()
    test_approval_cancel()
    test_approval_idempotent_resolution()
    test_approval_store_stats()
    test_approval_get_by_correlation()

    # 4. Runtime session
    test_session_start()
    test_session_touch()
    test_session_end()
    test_session_record_summary()
    test_session_mode_persistence()
    test_session_no_session_fallback()
    test_session_store_lifecycle()

    # 5. Mode
    test_mode_enum_values()
    test_mode_resolve()
    test_mode_active_delivers_all()
    test_mode_passive_filters()
    test_mode_autonomous_minimal()
    test_mode_classify_delivery()
    test_mode_to_dict()

    # 6. Integration
    test_integration_trace_to_delivery()
    test_integration_failure_trace_to_delivery()
    test_integration_approval_flow()
    test_integration_mode_gated_delivery()
    test_integration_session_with_mode()

    print("\n" + "=" * 65)
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    if _FAIL:
        sys.exit(1)
    else:
        print("All tests passed.")
