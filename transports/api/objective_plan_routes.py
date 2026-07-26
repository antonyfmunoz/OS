"""Objective-plan transport — thin adapter over the canonical intent protocol.

Wave 1. This module DEFINES NO intent semantics (plan §5): it invokes
``substrate.execution.intent.protocol.OperatorIntentProtocol`` (the semantic
owner) and projects planning records to the Cockpit.

Surfaces:
  - GET  /objective-plan                          read: surface list
  - GET  /objective-plan/{id}                     read: full detail
  - GET  /objective-plan/by-conversation/{conv}   read: latest for a thread
  - GET  /objective-plan/{id}/versions            read: version history (asc)
  - POST /objective-plan/{id}/decision            decision (same authority the
        HUD unified-approval route uses — ONE apply_plan_decision path)
  - try_chat_planning_rail(...)                   the Cockpit chat seam

Legacy cutover (§23.5): the chat seam routes work-bearing messages through
the protocol ONLY — new Cockpit submissions never write IntentLoopRecords.
Read surfaces never raise 500 (projection read-surface discipline).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_protocol_singleton: Any | None = None


def _declared_workspace_scope(_scope: Any) -> list[str] | None:
    """The target workspace's DECLARED writable-path authority, or None.

    Substrate is instance-agnostic, so the concrete workspace's least-privilege
    mutation authority is declared by the RUNTIME that owns the workspace and
    injected here (``UMH_WORKSPACE_WRITABLE_PATHS``: a comma-separated list of
    worktree-relative paths). Returning None means the workspace declared no
    authority and Task materialization fails CLOSED — an undeclared scope is
    never whole-repository permission (field run 20260725T230726Z persisted a
    Task with ``scope_declared=False``, making every legitimate worker diff
    unverifiable).

    This resolver NEVER infers a scope: no title matching, no packet-id shapes,
    no evidence, no post-hoc diff. It reads one declaration.
    """
    raw = os.environ.get("UMH_WORKSPACE_WRITABLE_PATHS", "").strip()
    if not raw:
        return None
    paths = [p.strip() for p in raw.split(",") if p.strip()]
    return paths or None


def _declared_lanes(_scope: Any, _objective_text: str) -> list[Any] | None:
    """The DECLARED lane decomposition for this objective, or None.

    Read from ``UMH_WORKSPACE_LANES``: a JSON array of lane objects, each
    ``{"lane_key", "title", "writable_path_scope", "depends_on", "semantic_label"}``.
    A multi-lane objective materializes one Task PER LANE, each with its own
    least-privilege authority and resolved dependencies, instead of a single
    umbrella Task (field run 20260726T025143Z-p1 compiled one combined Task, so
    a graph asserting two concurrent implementation Tasks was unsatisfiable by
    construction).

    Like ``_declared_workspace_scope`` this NEVER infers: no title matching, no
    packet-id shapes, no evidence, no post-hoc diff. It reads one declaration.
    Unset → None → the objective compiles to one umbrella Task exactly as
    before. Malformed → None, and any lane the runtime meant to declare is then
    absent, which the pre-dispatch graph-shape gate refuses BEFORE quota rather
    than discovering after a worker has run.
    """
    raw = os.environ.get("UMH_WORKSPACE_LANES", "").strip()
    if not raw:
        return None
    try:
        declared = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("UMH_WORKSPACE_LANES is not valid JSON — no lanes declared")
        return None
    if not isinstance(declared, list) or not declared:
        logger.warning("UMH_WORKSPACE_LANES is not a non-empty JSON array — no lanes declared")
        return None

    from substrate.execution.planning.records import ObjectiveLane

    lanes: list[Any] = []
    for entry in declared:
        if not isinstance(entry, dict):
            logger.warning("UMH_WORKSPACE_LANES entry is not an object — no lanes declared")
            return None
        lanes.append(ObjectiveLane.from_dict(entry))
    return lanes


def _protocol() -> Any:
    global _protocol_singleton
    if _protocol_singleton is None:
        from substrate.execution.intent.protocol import OperatorIntentProtocol

        _protocol_singleton = OperatorIntentProtocol(
            workspace_scope_resolver=_declared_workspace_scope,
        )
    return _protocol_singleton


def _store() -> Any:
    from substrate.execution.planning.store import PlanningStore

    return PlanningStore()


def _plan_surface_row(plan: Any) -> dict[str, Any]:
    return {
        "plan_record_id": plan.plan_record_id,
        "objective_id": plan.objective_id,
        "objective_text": plan.objective_text,
        "status": plan.status,
        "graph_version": plan.graph_version,
        "conversation_id": plan.conversation_id,
        "planning_scale": plan.planning_scale,
        "packet_count": len(plan.workpacket_ids),
        "workpacket_ids": list(plan.workpacket_ids),
        "readiness": (plan.readiness_assessment or {}).get("state", ""),
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
    }


def _plan_detail(plan: Any) -> dict[str, Any]:
    detail = plan.to_dict()
    detail["linkage"] = plan.linkage()
    return detail


def _latest_approved_plan_for_conversation(store: Any, conversation_id: str) -> Any:
    """The newest APPROVED, non-superseded plan for a conversation (or None).

    Used by the execution-request rail to resolve exactly which accepted plan the
    operator means when they say "execute the approved plan"."""
    try:
        plans = store.load_plans()
    except Exception as exc:  # read-only resolve; never raise into the rail
        logger.debug("approved-plan lookup failed: %s", exc)
        return None
    candidates = [
        p
        for p in plans
        if getattr(p, "conversation_id", "") == conversation_id
        and getattr(p, "status", "") == "approved"
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: getattr(p, "graph_version", 0))


# ── Chat planning rail (the ONE conversational work seam) ────────────────────


def try_chat_planning_rail(
    content: str,
    conversation_id: str = "",
    client_message_id: str = "",
    user_id: str = "",
    _depth: int = 0,
) -> dict | None:
    """Route one Cockpit chat/voice message through the canonical protocol.

    Returns a ChatResponse-shaped dict when the message is work-bearing or
    decision-bearing; ``None`` for pure communication (the normal
    conversation path proceeds). Never raises. Chat NEVER commits a
    decision — PROVIDE_DECISION only surfaces/focuses the HUD item.
    """
    try:
        from substrate.contracts.principal_resolution import resolve_principal_context
        from substrate.contracts.work_context import WorkScope
        from substrate.execution.intent.context_frame import build_context_frame
        from substrate.execution.intent.protocol import IntentClass

        protocol = _protocol()
        principal = resolve_principal_context(
            user_id=user_id or "cockpit_chat_operator", authenticated_by="cockpit"
        )
        conv_id = conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
        scope = WorkScope(
            tenant_id=principal.tenant_id,
            conversation_id=conv_id,
            target_kind="umh_substrate",
            legacy_org_id=principal.compatibility_origin.removeprefix("org:"),
            migration_status="legacy_derived",
        )
        frame = build_context_frame(
            principal.tenant_id,
            principal.principal_id,
            conv_id,
            membership_id=principal.membership_id,
            planning_store=protocol._store,
        )
        resolution = protocol.resolve(
            content, principal, scope, frame, client_message_id=client_message_id
        )
    except Exception as exc:
        logger.error("planning rail resolution failed: %s", exc)
        return None

    intent_class = resolution.intent_class
    timestamp = datetime.now(timezone.utc).isoformat()

    if intent_class in (IntentClass.COMMUNICATE.value, IntentClass.QUERY_STATE.value):
        return None  # conversation path answers; zero artifacts (test A)

    metadata: dict[str, Any] = {
        "surface": "objective_plan",
        "intent_class": intent_class,
        "intent_id": resolution.intent_id,
        "conversation_id": conv_id,
    }

    def _respond(text: str, actions: list[dict] | None = None) -> dict:
        _persist_rail_turn(content, text, metadata, conv_id)
        return {
            "message_id": f"planning-rail-{uuid.uuid4().hex[:8]}",
            "text": text,
            "response": text,
            "conversation_id": conv_id,
            "intent": intent_class,
            "suggested_actions": actions or [],
            "metadata": metadata,
            "timestamp": timestamp,
        }

    try:
        if intent_class == IntentClass.CLARIFICATION_RESPONSE.value and _depth == 0:
            # Resume the held session: fold the answer into the objective and
            # re-enter the rail once with the merged text (§5).
            session = protocol._store.find_active_session(conv_id)
            if session is not None and session.stage == "awaiting_clarification":
                merged = protocol.resume_clarification(session, content)
                return try_chat_planning_rail(
                    merged,
                    conv_id,
                    client_message_id=client_message_id or session.client_message_id,
                    user_id=user_id,
                    _depth=1,
                )
            return None  # nothing held — let the conversation answer

        if resolution.clarification_required:
            question = (
                resolution.clarification_questions[0]["question"]
                if resolution.clarification_questions
                else "Can you narrow that down?"
            )
            # Persist the held session so the NEXT message resumes it.
            protocol.record_clarification(
                resolution,
                content,
                conv_id,
                client_message_id=client_message_id,
                question=question,
            )
            metadata["state"] = "clarification_required"
            metadata["clarification_question"] = question
            return _respond(f"One thing before I plan this: {question}")

        if intent_class == IntentClass.PROVIDE_DECISION.value:
            # HUD-only authority: surface + focus; NO state transition here.
            selected = resolution.reference_resolution.get("selected", {})
            plan_id = selected.get("plan_record_id", "")
            metadata["state"] = "decision_surfaced"
            metadata["plan_record_id"] = plan_id
            return _respond(
                "Decisions are made in the control panel at the top — I've "
                "surfaced this plan's decision there. Nothing changes until "
                "you act on it in the HUD.",
                actions=[
                    {
                        "label": "Open Decisions",
                        "action": "navigate",
                        "payload": {"panel": "approvals"},
                    }
                ],
            )

        if intent_class == IntentClass.CREATE_TASK.value:
            # NB: a rephrase of an EXISTING task resolves upstream as
            # restatement_of_existing and the protocol downgrades it to
            # QUERY_STATE (handled above) — so it never reaches here and no
            # duplicate packet is created (field-journey s05). This branch only
            # runs for genuinely new atomic tasks.
            packet = protocol.capture_task(
                resolution, content, conv_id, client_message_id=client_message_id
            )
            metadata["state"] = "task_captured"
            metadata["packet_id"] = packet.packet_id
            return _respond(
                f"Task captured on the Work board: {packet.title!r}. It is not "
                "scheduled to run — execution needs a separate decision.",
                actions=[
                    {"label": "Open Work", "action": "navigate", "payload": {"panel": "work"}}
                ],
            )

        if intent_class in (IntentClass.CREATE_OBJECTIVE.value,):
            existing = resolution.existing_work_resolution
            if existing.get("relationship") == "restatement_of_existing":
                metadata["state"] = "resolved_existing"
                metadata["plan_record_id"] = existing.get("matched_plan_record_id", "")
                return _respond(
                    "That objective already has a live plan — I linked you to "
                    "it instead of creating a duplicate.",
                )
            session, plan = protocol.plan_objective(
                resolution, content, conv_id, client_message_id=client_message_id
            )
            metadata["state"] = plan.status
            metadata["plan_record_id"] = plan.plan_record_id
            metadata["objective_id"] = plan.objective_id
            metadata["graph_version"] = plan.graph_version
            metadata["packet_count"] = len(plan.workpacket_ids)
            return _respond(
                f"Plan v{plan.graph_version} compiled for this objective — "
                f"{len(plan.workpacket_ids)} task(s) on the Work board, decision "
                "waiting in the control panel. Approving accepts the plan only; "
                "nothing executes.",
                actions=[
                    {
                        "label": "Open Plan",
                        "action": "navigate",
                        "payload": {"panel": "workdetail", "plan_record_id": plan.plan_record_id},
                    }
                ],
            )

        if intent_class == IntentClass.MODIFY_PLAN.value:
            from substrate.execution.planning.compiler import compile_revision
            from substrate.execution.planning.objective_classifier import classify_revision

            plan_id = resolution.existing_work_resolution.get("matched_plan_record_id", "")
            store = protocol._store
            plan = store.get_plan(plan_id) if plan_id else None
            if plan is None:
                metadata["state"] = "revision_target_missing"
                return _respond("I couldn't resolve which plan to revise — which one do you mean?")
            edit_set = classify_revision(content, plan)
            if edit_set is None or not edit_set.edits:
                metadata["state"] = "revision_unparsed"
                return _respond(
                    "I couldn't turn that into concrete plan edits — say e.g. "
                    "'add a step to …' or 'remove the … step'."
                )
            new_plan = compile_revision(plan, edit_set, store, protocol._runner())
            metadata["state"] = new_plan.status
            metadata["plan_record_id"] = new_plan.plan_record_id
            metadata["objective_id"] = new_plan.objective_id
            metadata["graph_version"] = new_plan.graph_version
            return _respond(
                f"Plan revised to v{new_plan.graph_version}; v{plan.graph_version} "
                "is preserved in the version history.",
                actions=[
                    {
                        "label": "Open Plan",
                        "action": "navigate",
                        "payload": {
                            "panel": "workdetail",
                            "plan_record_id": new_plan.plan_record_id,
                        },
                    }
                ],
            )

        if intent_class == IntentClass.REQUEST_EXECUTION.value:
            # Wave 2: chat NEVER authorizes execution. It resolves the accepted
            # plan, runs a readiness pre-pass, and surfaces ONE bounded
            # execution-authorization Decision to the HUD (the sole authorization
            # surface). Nothing runs until the operator authorizes it there.
            from substrate.execution.attempts.decisions import (
                ExecutionDecisionConflict,
                request_execution_authorization,
            )
            from substrate.execution.attempts.store import ExecutionAttemptStore

            # Resolve the plan: an explicitly matched plan, else the latest
            # APPROVED plan for this conversation's objective.
            plan_id = resolution.existing_work_resolution.get("matched_plan_record_id", "")
            plan = protocol._store.get_plan(plan_id) if plan_id else None
            if plan is None:
                plan = _latest_approved_plan_for_conversation(protocol._store, conv_id)
            if plan is None:
                metadata["state"] = "execution_no_accepted_plan"
                return _respond(
                    "There's no accepted plan to execute yet. Accept a plan in "
                    "the control panel first, then ask me to execute it.",
                    actions=[{"type": "focus_panel", "payload": {"panel": "work"}}],
                )
            if plan.status != "approved":
                metadata["state"] = "execution_plan_not_accepted"
                return _respond(
                    f"That plan (v{plan.graph_version}) isn't accepted yet — "
                    "accept it in the control panel first.",
                    actions=[{"type": "focus_panel", "payload": {"panel": "approvals"}}],
                )

            frontier = [pid for pid in plan.workpacket_ids if pid]
            try:
                _grant, _approval = request_execution_authorization(
                    ExecutionAttemptStore(),
                    plan=plan,
                    task_frontier=frontier,
                    tenant_id=scope.tenant_id,
                    principal_id=principal.principal_id,
                    membership_id=principal.membership_id,
                    conversation_id=conv_id,
                    correlation_id=resolution.intent_id,
                    requested_by=user_id or "cockpit_chat_operator",
                    mutation_runner=protocol._runner(),
                )
            except ExecutionDecisionConflict as exc:
                metadata["state"] = "execution_request_conflict"
                return _respond(f"Cannot request execution: {exc}")

            metadata["state"] = "execution_authorization_pending"
            metadata["plan_record_id"] = plan.plan_record_id
            metadata["decision_ref"] = _grant.decision_ref
            metadata["surface"] = "execution_status"
            return _respond(
                f"I've surfaced an execution decision for plan v{plan.graph_version} "
                f"({len(frontier)} task(s)) in the control panel. Nothing runs "
                "until you authorize it there.",
                actions=[{"type": "focus_panel", "payload": {"panel": "approvals"}}],
            )

        if intent_class == IntentClass.CANCEL_WORK.value:
            from substrate.execution.planning.decisions import apply_plan_decision

            plan_id = resolution.existing_work_resolution.get(
                "matched_plan_record_id", ""
            ) or resolution.reference_resolution.get("selected", {}).get("plan_record_id", "")
            if not plan_id:
                metadata["state"] = "cancel_target_missing"
                return _respond("Which plan should I cancel?")
            plan = apply_plan_decision(
                protocol._store,
                plan_id,
                "cancel",
                decided_by=user_id or "cockpit_chat_operator",
                mutation_runner=protocol._runner(),
            )
            metadata["state"] = plan.status
            metadata["plan_record_id"] = plan.plan_record_id
            return _respond(f"Plan cancelled (v{plan.graph_version} preserved in history).")

        # Remaining lifecycle classes: acknowledged, not yet operable in Wave 1.
        metadata["state"] = "not_operable_wave1"
        return _respond(
            "I understood that as a work-lifecycle request that Wave 1 does "
            "not operate yet — no state was changed."
        )
    except Exception as exc:
        logger.error("planning rail action failed: %s", exc)
        metadata["state"] = "failed"
        return _respond(f"Planning failed safely — nothing was partially created twice: {exc}")


def _persist_rail_turn(
    content: str, response_text: str, metadata: dict[str, Any], conv_id: str
) -> None:
    """Persist the exchange (with plan metadata) as server truth. Non-fatal."""
    try:
        from transports.api.governed import governed_mutation

        def _persist() -> tuple[str, bool]:
            from substrate.organism.store import OrganismStore

            OrganismStore().save_conversation_turn(
                content=content,
                response=response_text,
                origin_channel="cockpit",
                responder="assistant",
                metadata=dict(metadata),
                thread_conversation_id=conv_id,
            )
            return ("planning rail turn saved", True)

        governed_mutation(
            mutation_name="conversation_send",
            intent=f"planning rail status: {content[:60]}",
            execute_fn=_persist,
            source="cockpit",
        )
    except Exception as exc:
        logger.debug("planning rail turn persistence failed (non-fatal): %s", exc)


# ── Read + decision routes ───────────────────────────────────────────────────


class DecisionRequest(BaseModel):
    # MODULE scope: with PEP 563 string annotations FastAPI resolves body-param
    # models against module globals — nested inside _build_router() this model
    # was invisible and the /decision body param degraded to a required QUERY
    # param (422 loc ["query","req"]; same defect family as the
    # unified-approval routes, Wave-1 field run 20260722T185410Z).
    decision: str
    decided_by: str = "operator"
    reason: str = ""
    # Optimistic-concurrency token: the graph_version the CLIENT saw.
    # When provided, a decision against a stale view is rejected.
    expected_current_version: int | None = None


def _build_router() -> Any:
    from fastapi import APIRouter

    router = APIRouter(prefix="/objective-plan", tags=["objective-plan"])

    def _caller_tenant_id() -> str:
        """The server-resolved tenant of the calling deployment (single-tenant
        Wave 1). Read surfaces filter to it — defense-in-depth so a future
        second tenant on the same instance can never read foreign plans."""
        try:
            from substrate.contracts.principal_resolution import resolve_principal_context

            return resolve_principal_context().tenant_id
        except Exception as exc:
            logger.debug("caller tenant resolution failed: %s", exc)
            return ""

    def _tenant_visible(plan: Any, tenant_id: str) -> bool:
        plan_tenant = (plan.work_scope or {}).get("tenant_id", "")
        # Empty plan tenant = pre-tenancy record; empty caller = single-tenant
        # env without org config (fail open for reads only, writes fail closed).
        return not tenant_id or not plan_tenant or plan_tenant == tenant_id

    @router.get("")
    def surface_list() -> list[dict[str, Any]]:
        try:
            tenant_id = _caller_tenant_id()
            plans = [
                p for p in _store().query_recent_plans(limit=50) if _tenant_visible(p, tenant_id)
            ]
            return [_plan_surface_row(p) for p in plans]
        except Exception as exc:
            logger.error("objective-plan surface failed: %s", exc)
            return []

    @router.get("/by-conversation/{conversation_id}")
    def by_conversation(conversation_id: str) -> dict[str, Any] | None:
        try:
            store = _store()
            plans = [
                p
                for p in store.load_plans()
                if p.conversation_id == conversation_id
                and p.status not in ("superseded",)
                and _tenant_visible(p, _caller_tenant_id())
            ]
            if not plans:
                return None
            plans.sort(key=lambda p: (p.graph_version, p.created_at))
            return _plan_detail(plans[-1])
        except Exception as exc:
            logger.error("objective-plan by-conversation failed: %s", exc)
            return None

    @router.get("/{plan_record_id}/versions")
    def versions(plan_record_id: str) -> list[dict[str, Any]]:
        try:
            store = _store()
            plan = store.get_plan(plan_record_id)
            if plan is None or not _tenant_visible(plan, _caller_tenant_id()):
                return []
            rows = store.versions_of(plan.objective_id)
            rows.sort(key=lambda p: p.graph_version)
            return [_plan_surface_row(p) for p in rows]
        except Exception as exc:
            logger.error("objective-plan versions failed: %s", exc)
            return []

    @router.get("/{plan_record_id}")
    def detail(plan_record_id: str) -> dict[str, Any]:
        try:
            plan = _store().get_plan(plan_record_id)
            if plan is not None and not _tenant_visible(plan, _caller_tenant_id()):
                plan = None
            if plan is None:
                return {"error": "not_found", "plan_record_id": plan_record_id}
            return _plan_detail(plan)
        except Exception as exc:
            logger.error("objective-plan detail failed: %s", exc)
            return {"error": "unavailable", "plan_record_id": plan_record_id}

    @router.post("/{plan_record_id}/decision")
    def decide(plan_record_id: str, req: DecisionRequest) -> dict[str, Any]:
        """The SAME apply_plan_decision authority the HUD unified-approval
        route uses — one decision path, never a second implementation."""
        try:
            from substrate.execution.planning.decisions import apply_plan_decision
            from transports.api.governed import governed_mutation

            plan = apply_plan_decision(
                _store(),
                plan_record_id,
                req.decision,
                decided_by=req.decided_by,
                reason=req.reason,
                mutation_runner=governed_mutation,
                expected_version=req.expected_current_version,
            )
            return {"ok": True, "plan": _plan_detail(plan)}
        except Exception as exc:
            logger.error("objective-plan decision failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    return router


def mount(app_router: Any) -> None:
    app_router.include_router(_build_router())


__all__ = ["mount", "try_chat_planning_rail"]
