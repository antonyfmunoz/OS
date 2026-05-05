# Phase 79: Observability + Operator Interface Backend v1

**Status**: Complete
**Date**: 2026-05-03
**Tests**: 128 passed, 0 failed
**Regression**: 370 prior tests (75B + 76 + 77 + 78) pass

## Executive Summary

Phase 79 makes UMH inspectable and operable without executing actions. Every trace, outcome, feedback record, memory candidate, governance decision, adapter status, and workstation state is now queryable through typed view models, read-only operator views, and a dashboard snapshot.

## Why Observability Before Deeper Intelligence

The MVP harness now executes governed operations, produces outcomes, records feedback, and creates memory candidates. Before building active learning, policy adaptation, or autonomous behavior, the system must be inspectable:
- Operators need to see what happened
- Failures need to be findable without digging through raw stores
- Decisions need explanations derived from evidence, not hallucinated
- System health needs to be assessable without calling adapters

This phase creates the read layer that Command Center, FAB, and voice surfaces will consume.

## Files Created (10)

| File | Purpose |
|------|---------|
| `umh/interface/__init__.py` | Interface package |
| `umh/interface/contracts.py` | InterfaceType (11), InterfaceActionType (16), InterfaceRequest, InterfaceResponse |
| `umh/interface/views.py` | 8 view models: TraceView, OutcomeView, FeedbackView, MemoryCandidateView, GovernanceDecisionView, AdapterStatusView, WorkstationStatusView, OperatorDashboardSnapshot |
| `umh/observability/__init__.py` | Observability package |
| `umh/observability/trace_query.py` | TraceQuery, TraceQueryResult, trace_to_view(), query_traces(), get_trace_view() |
| `umh/observability/timeline.py` | TimelineEventType (12), TimelineEvent, ExecutionTimeline, build_timeline() |
| `umh/observability/execution_summary.py` | ExecutionSummary with 9 status counters, summarize_executions(), by_capability/environment/adapter |
| `umh/observability/failure_search.py` | FailureCategory (7), FailureRecord, FailureSearchQuery, search_failures() |
| `umh/observability/decision_explainer.py` | DecisionExplanation, explain_trace(), explain_governance(), explain_adapter_selection() |
| `umh/observability/system_status.py` | SystemHealth (5), SystemStatus, ComponentStatus, build_system_status() |
| `umh/observability/operator_views.py` | build_operator_dashboard_snapshot(), view builders for all data types |

## Files Modified (3)

| File | Change |
|------|--------|
| `umh/control/api.py` | 8 read-only observability endpoints under `/observability/` |
| `umh/control/cli.py` | 8 observe commands + `_print` helper |
| `umh/workstation/resume.py` | Added `execution_health` field to TraceResumeSummary |

## API Endpoints Added

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/observability/status` | System health |
| GET | `/observability/dashboard` | Operator dashboard snapshot |
| GET | `/observability/timeline` | Execution timeline |
| GET | `/observability/traces` | Query traces with filters |
| GET | `/observability/traces/{trace_id}` | Single trace detail |
| GET | `/observability/traces/{trace_id}/explain` | Decision explanation |
| GET | `/observability/failures` | Failure search |
| GET | `/observability/executions/summary` | Execution summary |

## CLI Commands Added

| Command | Purpose |
|---------|---------|
| `observe-status` | System health |
| `observe-dashboard` | Operator dashboard snapshot |
| `observe-timeline` | Execution timeline |
| `observe-traces` | List recent traces |
| `observe-trace --trace-id` | Single trace |
| `observe-explain --trace-id` | Decision explanation |
| `observe-failures` | Failure search |
| `observe-summary` | Execution summary |

## Design Decisions

1. **Read-only by design**: All observability modules are stateless readers. No mutations, no executions, no adapter calls.
2. **Typed view models**: 8 view types ensure UI surfaces get stable, serializable shapes with no secrets.
3. **Sparse-safe**: Missing stores return empty results with warnings, not crashes. UNKNOWN health when checks missing.
4. **No causal attribution**: Failure search and decision explainer report evidence, not root causes.
5. **Observer pattern**: `system_status` imports `check_governance` to verify module availability, not to evaluate governance.
6. **Dashboard snapshot**: Single function assembles all views. Safe to call with zero stores, degrades to empty lists.
7. **Interface contracts prepared for UI**: InterfaceType covers CLI, API, Desktop CC, overlay, minimized wave, mobile, widget, live activity, voice, messaging. No frontend implemented.

## Invariants Honored

All 25 Phase 79 invariants (441-465) verified:
- 441-452: Read-only, no execution/mutation/bypass
- 453: Typed and deterministic responses
- 454-455: Graceful degradation, sparse safety
- 456: UNKNOWN distinguished from HEALTHY
- 457-458: No causal attribution, evidence-derived explanations
- 459: Identity-scoped dashboard
- 460-461: No secrets in views
- 462: Endpoints safe to call repeatedly
- 463: Query limits enforced (max 100)
- 464: Backward compatible
- 465: Prepared for UI/FAB/voice without implementing

## Test Coverage (128 tests)

| Class | Tests | Coverage |
|-------|-------|----------|
| TestInterfaceType | 4 | Normalization, all types |
| TestInterfaceActionType | 2 | Normalization |
| TestInterfaceRequest | 3 | Serialization, from_dict, degradation |
| TestInterfaceResponse | 3 | Serialization, display_payload, from_dict |
| TestViewModels | 9 | All 8 views serialize + raw omission |
| TestTraceQuery | 11 | Empty/null store, limits, filters, sparse, raw |
| TestTimeline | 8 | Empty, trace/outcome/feedback events, sort, serialize |
| TestExecutionSummary | 10 | All 9 status counts + capabilities + attention |
| TestFailureSearch | 12 | All categories, limits, filters, determinism, no causal |
| TestDecisionExplainer | 9 | Sparse, denied, success, failure, confidence, deterministic |
| TestSystemStatus | 9 | Missing/available stores, health levels, serialize |
| TestOperatorDashboard | 17 | No stores, all fields, limits, identity, sub-builders |
| TestControlAPIFunctions | 9 | All functions callable, no mutation |
| TestCLICommands | 4 | Parser accepts observe commands |
| TestLayeringInvariants | 11 | Forbidden imports across 9 modules |
| TestResumeIntegration | 2 | execution_health field |
| TestPhase78Compatibility | 5 | All Phase 78 exports intact |

## Known Limitations

- No frontend UI yet
- No floating overlay/FAB yet
- No voice surface yet
- No live streaming observability
- No causal root-cause analysis
- No world-model state dashboard
- No advanced metrics database
- Dashboard snapshot is backend/read-model only
- Interface contracts prepared for UI surfaces but do not implement them

## Is Phase 80 Safe?

Yes. Phase 79 is purely additive:
- 10 new files, 3 modified files
- All observability modules are read-only
- No execution/governance/routing behavior changes
- No adapter calls from new modules
- No trace/outcome/feedback mutation
- All 498 tests pass (128 + 370 regression)
- The system is now inspectable without being more dangerous
