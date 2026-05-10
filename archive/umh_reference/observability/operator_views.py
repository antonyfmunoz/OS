"""Phase 79 operator views — assemble interface-ready read models.

Read-only. Safe if stores unavailable. No execution. No adapter calls.
No memory promotion. No trace mutation.
"""

from __future__ import annotations

from typing import Any

from umh.core.clock import iso_now as _iso_now
from umh.interface.views import (
    AdapterStatusView,
    FeedbackView,
    MemoryCandidateView,
    OperatorDashboardSnapshot,
    OutcomeView,
    WorkstationStatusView,
)
from umh.observability.execution_summary import summarize_executions
from umh.observability.failure_search import (
    FailureSearchQuery,
    outcome_to_failure_record,
    search_failures,
)
from umh.observability.system_status import build_system_status
from umh.observability.trace_query import list_recent_trace_views


def _outcome_to_view(outcome: Any) -> OutcomeView:
    if isinstance(outcome, dict):
        s = outcome.get("status", "")
        return OutcomeView(
            outcome_id=outcome.get("outcome_id", ""),
            trace_id=outcome.get("trace_id", ""),
            user_id=outcome.get("user_id", ""),
            status=s.value if hasattr(s, "value") else str(s),
            success_score=outcome.get("success_score", 0.0),
            confidence=outcome.get("confidence", 0.0),
            summary=outcome.get("summary", "")[:200],
            evidence_count=len(outcome.get("evidence", [])),
            errors_count=len(outcome.get("errors", [])),
            timestamp=outcome.get("completed_at", ""),
        )
    s = getattr(outcome, "status", "")
    return OutcomeView(
        outcome_id=getattr(outcome, "outcome_id", ""),
        trace_id=getattr(outcome, "trace_id", ""),
        user_id=getattr(outcome, "user_id", ""),
        status=s.value if hasattr(s, "value") else str(s),
        success_score=getattr(outcome, "success_score", 0.0),
        confidence=getattr(outcome, "confidence", 0.0),
        summary=getattr(outcome, "summary", "")[:200],
        evidence_count=len(getattr(outcome, "evidence", [])),
        errors_count=len(getattr(outcome, "errors", [])),
        timestamp=getattr(outcome, "completed_at", ""),
    )


def _feedback_to_view(feedback: Any) -> FeedbackView:
    if isinstance(feedback, dict):
        sig = feedback.get("signal_type", "")
        src = feedback.get("source", "")
        return FeedbackView(
            feedback_id=feedback.get("feedback_id", ""),
            trace_id=feedback.get("trace_id", ""),
            outcome_id=feedback.get("outcome_id", ""),
            user_id=feedback.get("user_id", ""),
            signal_type=sig.value if hasattr(sig, "value") else str(sig),
            score=feedback.get("score", 0.0),
            confidence=feedback.get("confidence", 0.0),
            source=src.value if hasattr(src, "value") else str(src),
            notes_preview=(feedback.get("notes", "") or "")[:100],
            timestamp=feedback.get("timestamp", ""),
        )
    sig = getattr(feedback, "signal_type", "")
    src = getattr(feedback, "source", "")
    return FeedbackView(
        feedback_id=getattr(feedback, "feedback_id", ""),
        trace_id=getattr(feedback, "trace_id", ""),
        outcome_id=getattr(feedback, "outcome_id", ""),
        user_id=getattr(feedback, "user_id", ""),
        signal_type=sig.value if hasattr(sig, "value") else str(sig),
        score=getattr(feedback, "score", 0.0),
        confidence=getattr(feedback, "confidence", 0.0),
        source=src.value if hasattr(src, "value") else str(src),
        notes_preview=(getattr(feedback, "notes", "") or "")[:100],
        timestamp=getattr(feedback, "timestamp", ""),
    )


def _candidate_to_view(candidate: Any) -> MemoryCandidateView:
    if isinstance(candidate, dict):
        mt = candidate.get("memory_type", "")
        ps = candidate.get("promotion_status", "candidate")
        return MemoryCandidateView(
            candidate_id=candidate.get("candidate_id", ""),
            trace_id=candidate.get("trace_id", ""),
            outcome_id=candidate.get("outcome_id", ""),
            user_id=candidate.get("user_id", ""),
            memory_type=mt.value if hasattr(mt, "value") else str(mt),
            confidence=candidate.get("confidence", 0.0),
            reason=candidate.get("reason", "")[:200],
            promotion_status=ps.value if hasattr(ps, "value") else str(ps),
            content_preview=(candidate.get("content", "") or "")[:100],
            created_at=candidate.get("created_at", ""),
        )
    mt = getattr(candidate, "memory_type", "")
    ps = getattr(candidate, "promotion_status", "candidate")
    return MemoryCandidateView(
        candidate_id=getattr(candidate, "candidate_id", ""),
        trace_id=getattr(candidate, "trace_id", ""),
        outcome_id=getattr(candidate, "outcome_id", ""),
        user_id=getattr(candidate, "user_id", ""),
        memory_type=mt.value if hasattr(mt, "value") else str(mt),
        confidence=getattr(candidate, "confidence", 0.0),
        reason=getattr(candidate, "reason", "")[:200],
        promotion_status=ps.value if hasattr(ps, "value") else str(ps),
        content_preview=(getattr(candidate, "content", "") or "")[:100],
        created_at=getattr(candidate, "created_at", ""),
    )


def build_workstation_status_view(
    profile: Any | None = None,
    session: Any | None = None,
    resume_summary: Any | None = None,
) -> WorkstationStatusView:
    """Build a workstation status view from profile/session/resume."""
    user_id = ""
    workstation_id = ""
    active_mode = ""
    active_session_id = ""
    active_device = ""
    active_environment = ""
    execution_preference: dict[str, Any] = {}
    pending_count = 0
    trace_count = 0
    resume_text = ""

    if profile is not None:
        user_id = getattr(profile, "user_id", "")
        workstation_id = getattr(profile, "workstation_id", "")
        active_mode = getattr(profile, "active_mode", "")
        active_session_id = getattr(profile, "active_session_id", "")
        pending_count = len(getattr(profile, "pending_approvals", []))
        trace_count = len(getattr(profile, "active_traces", []))
        ep = getattr(profile, "execution_preference", None)
        if ep is not None and hasattr(ep, "preferred_environment"):
            execution_preference = {
                "preferred_environment": ep.preferred_environment,
                "preferred_device": ep.preferred_device,
                "allow_simulation_fallback": ep.allow_simulation_fallback,
            }

    if session is not None:
        if not active_session_id:
            active_session_id = getattr(session, "session_id", "")
        if not active_mode:
            active_mode = getattr(session, "active_mode", "")
        active_device = getattr(session, "active_device", "")
        active_environment = getattr(session, "active_environment", "")

    if resume_summary is not None:
        if hasattr(resume_summary, "recommended_resume_points"):
            pts = resume_summary.recommended_resume_points
            resume_text = "; ".join(pts) if pts else ""
        elif isinstance(resume_summary, str):
            resume_text = resume_summary

    return WorkstationStatusView(
        user_id=user_id,
        workstation_id=workstation_id,
        active_mode=active_mode,
        active_session_id=active_session_id,
        active_device=active_device,
        active_environment=active_environment,
        execution_preference=execution_preference,
        pending_approval_count=pending_count,
        recent_trace_count=trace_count,
        resume_summary=resume_text,
    )


def build_adapter_status_views(
    adapter_registry: Any | None = None,
    backend_registry: Any | None = None,
) -> list[AdapterStatusView]:
    """Build adapter status views without calling adapters."""
    views: list[AdapterStatusView] = []

    if adapter_registry is not None and hasattr(adapter_registry, "list_adapters"):
        try:
            adapters = adapter_registry.list_adapters()
            for adp in adapters:
                name = getattr(adp, "name", str(adp))
                caps = list(getattr(adp, "supported_capabilities", []))
                envs = list(getattr(adp, "supported_environments", []))
                views.append(
                    AdapterStatusView(
                        adapter_name=name,
                        capabilities=caps,
                        environments=envs,
                        status="registered",
                    )
                )
        except Exception:
            pass

    if backend_registry is not None and hasattr(backend_registry, "list_environments"):
        try:
            envs = backend_registry.list_environments()
            existing_names = {v.adapter_name for v in views}
            for env in envs:
                if env not in existing_names:
                    views.append(
                        AdapterStatusView(
                            adapter_name=env,
                            environments=[env],
                            status="backend_registered",
                        )
                    )
        except Exception:
            pass

    return views


def build_pending_attention_views(
    outcomes: list[Any] | None = None,
    traces: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Build list of items requiring human attention."""
    items: list[dict[str, Any]] = []

    for oc in outcomes or []:
        s = _extract_status(oc)
        if s in ("failure", "timeout", "validation_failed", "denied"):
            view = _outcome_to_view(oc)
            items.append({"type": "outcome", "status": s, **view.to_dict()})

    for t in traces or []:
        if isinstance(t, dict):
            status = t.get("status", "")
            error = t.get("error")
        else:
            status = getattr(t, "status", "")
            error = getattr(t, "error", None)
        if status == "failed" or error:
            trace_id = t.get("trace_id", "") if isinstance(t, dict) else getattr(t, "trace_id", "")
            items.append(
                {
                    "type": "trace",
                    "status": status,
                    "trace_id": trace_id,
                    "error": str(error)[:120] if error else "",
                }
            )

    return items


def _extract_status(obj: Any) -> str:
    if isinstance(obj, dict):
        s = obj.get("status", "")
        return s.value if hasattr(s, "value") else str(s)
    s = getattr(obj, "status", "")
    return s.value if hasattr(s, "value") else str(s)


def build_resume_points(
    resume_summary: Any | None = None,
    outcomes: list[Any] | None = None,
) -> list[str]:
    """Build next resume points from resume summary and outcomes."""
    points: list[str] = []

    if resume_summary is not None and hasattr(resume_summary, "recommended_resume_points"):
        points.extend(resume_summary.recommended_resume_points)

    failure_count = 0
    denial_count = 0
    for oc in outcomes or []:
        s = _extract_status(oc)
        if s == "failure":
            failure_count += 1
        elif s == "denied":
            denial_count += 1

    if failure_count > 0 and f"{failure_count} recent failures to review" not in points:
        points.append(f"{failure_count} recent failures to review")
    if denial_count > 0 and f"{denial_count} recent denials" not in points:
        points.append(f"{denial_count} recent denials")

    return points


def build_operator_dashboard_snapshot(
    user_id: str,
    trace_store: Any | None = None,
    feedback_store: Any | None = None,
    workstation_profile: Any | None = None,
    session: Any | None = None,
    adapter_registry: Any | None = None,
    backend_registry: Any | None = None,
    storage_gateway: Any | None = None,
    migration_registry: Any | None = None,
    interface_registry: Any | None = None,
    limit: int = 25,
) -> OperatorDashboardSnapshot:
    """Build the complete operator dashboard snapshot. Read-only, safe if stores unavailable."""
    warnings: list[str] = []

    # System health
    sys_status = build_system_status(
        user_id=user_id,
        trace_store=trace_store,
        feedback_store=feedback_store,
        workstation_profile=workstation_profile,
        workstation_session=session,
        adapter_registry=adapter_registry,
        backend_registry=backend_registry,
        storage_gateway=storage_gateway,
        migration_registry=migration_registry,
        interface_registry=interface_registry,
    )

    # Workstation
    ws_view = build_workstation_status_view(workstation_profile, session)

    # Traces
    trace_views = list_recent_trace_views(trace_store, user_id=user_id, limit=limit)

    # Outcomes, feedback, memory candidates from feedback store
    outcomes: list[Any] = []
    feedback_list: list[Any] = []
    candidates: list[Any] = []

    if feedback_store is not None:
        try:
            outcomes = feedback_store.list_outcomes(user_id=user_id, limit=limit)
        except Exception:
            warnings.append("failed to load outcomes")
        try:
            feedback_list = feedback_store.list_feedback(user_id=user_id, limit=limit)
        except Exception:
            warnings.append("failed to load feedback")
        try:
            candidates = feedback_store.list_memory_candidates(user_id=user_id, limit=limit)
        except Exception:
            warnings.append("failed to load memory candidates")

    outcome_views = [_outcome_to_view(o) for o in outcomes]
    feedback_views = [_feedback_to_view(f) for f in feedback_list]
    candidate_views = [_candidate_to_view(c) for c in candidates]

    # Failures and denials from outcomes
    failure_result = search_failures(outcomes=outcomes, query=FailureSearchQuery(limit=limit))
    failure_dicts = [f.to_dict() for f in failure_result.failures if f.category.value != "denied"]
    denial_dicts = [f.to_dict() for f in failure_result.failures if f.category.value == "denied"]

    # Pending attention
    raw_traces: list[Any] = []
    if trace_store is not None:
        try:
            raw_traces = trace_store.list_traces(limit=limit)
        except Exception:
            pass
    pending_attention = build_pending_attention_views(outcomes=outcomes, traces=raw_traces)

    # Adapters
    adapter_views = build_adapter_status_views(adapter_registry, backend_registry)

    # Resume points
    resume_points = build_resume_points(outcomes=outcomes)

    # Ontology kernel summary
    ontology_summary: dict[str, Any] = {}
    try:
        from umh.ontology.correspondence import get_correspondence_maps
        from umh.ontology.domain_projection import get_domain_projections
        from umh.ontology.laws import get_laws
        from umh.ontology.primitives import get_primitives
        from umh.ontology.validation import validate_ontology_kernel
        from umh.ontology.views import build_ontology_kernel_view

        _prims = get_primitives()
        _laws = get_laws()
        _projs = get_domain_projections()
        _corrs = get_correspondence_maps()
        _vr = validate_ontology_kernel(_prims, _laws, _projs)
        onto_view = build_ontology_kernel_view(_prims, _laws, _projs, _corrs, _vr)
        ontology_summary = {
            "primitive_count": onto_view.primitive_count,
            "law_count": onto_view.law_count,
            "domain_projection_count": onto_view.domain_projection_count,
            "correspondence_count": onto_view.correspondence_count,
            "validation_status": onto_view.validation_status,
        }
    except Exception:
        warnings.append("failed to load ontology kernel summary")

    storage_summary: dict[str, Any] = {}
    try:
        from umh.storage.views import build_storage_health_view

        gw_descs = []
        if storage_gateway is not None and hasattr(storage_gateway, "list_descriptors"):
            gw_descs = storage_gateway.list_descriptors(limit=500)
        backend_names = (
            sorted(storage_gateway.backends.keys())
            if storage_gateway is not None and hasattr(storage_gateway, "backends")
            else []
        )
        sh_view = build_storage_health_view(gw_descs, backend_names=backend_names)
        storage_summary = sh_view.to_dict()
    except Exception:
        warnings.append("failed to load storage summary")

    memory_discipline_summary: dict[str, Any] = {}
    try:
        from umh.memory.views import build_memory_discipline_health_view

        md_candidates = candidates if candidates else []
        md_view = build_memory_discipline_health_view(candidates=md_candidates)
        memory_discipline_summary = md_view.to_dict()
    except Exception:
        warnings.append("failed to load memory discipline summary")

    migration_summary: dict[str, Any] = {}
    if migration_registry is not None:
        try:
            from umh.migration.views import build_migration_health_view

            mig_view = build_migration_health_view(migration_registry)
            migration_summary = mig_view.to_dict()
        except Exception:
            warnings.append("failed to load migration summary")

    interface_summary: dict[str, Any] = {}
    if interface_registry is not None:
        try:
            count = getattr(interface_registry, "surface_count", 0)
            interface_summary = {
                "surface_count": count,
                "status": "ok" if count > 0 else "empty",
            }
        except Exception:
            warnings.append("failed to load interface summary")

    warnings.extend(sys_status.warnings)

    return OperatorDashboardSnapshot(
        user_id=user_id,
        generated_at=_iso_now(),
        system_health=sys_status.health.value,
        workstation=ws_view.to_dict(),
        recent_traces=[tv.to_dict() for tv in trace_views],
        recent_outcomes=[ov.to_dict() for ov in outcome_views],
        recent_feedback=[fv.to_dict() for fv in feedback_views],
        memory_candidates=[cv.to_dict() for cv in candidate_views],
        failures=failure_dicts,
        denials=denial_dicts,
        pending_attention=pending_attention,
        adapter_statuses=[av.to_dict() for av in adapter_views],
        ontology_summary=ontology_summary,
        storage_summary=storage_summary,
        memory_discipline_summary=memory_discipline_summary,
        migration_summary=migration_summary,
        interface_summary=interface_summary,
        next_resume_points=resume_points,
        warnings=warnings,
    )
