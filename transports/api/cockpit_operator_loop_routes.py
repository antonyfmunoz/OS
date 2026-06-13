"""Cockpit operator loop routes — intent to plan to implementation to audit.

The Operator Loop lifecycle (Phase 1+2+3):
  1. Operator submits intent (full contract or natural language)
  2. Empire Router classifies domain, decomposes to WorkPackets
  3. Risk classified → approval gate enforced
  4. Plan generated → reviewable in cockpit
  5. Approved packets → sandbox created → agent executes
  6. Validation runs → proof captured
  7. Outcomes recorded in reality model
  8. Audit trail preserved
  9. Next best actions surfaced

Execution modes:
  VALIDATE_ONLY        — run validation commands (default)
  IMPLEMENT            — invoke coding agent
  IMPLEMENT_AND_VALIDATE — agent implements, then validate

Phase 3 additions:
  - /empire/route — full intent routing with domain/agent/proof assignment
  - /empire/domains — domain registry listing
  - /empire/agents — agent registry listing
  - /empire/reality — reality model snapshot
  - /empire/packets-by-domain — domain-filtered packet view
  - /empire/next-actions — computed next best actions

Mounted under /api/umh/ via include_router in cockpit.py.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

operator_loop_router: APIRouter = APIRouter()

_configured: bool = False

_REPO_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")

_VALID_MODES = ("validate_only", "implement", "implement_and_validate")

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _safe_artifact_path(kind: str, ident: str) -> str | None:
    """Build a safe filesystem path for execution artifacts. Returns None on traversal attempt."""
    if not _ID_RE.match(ident):
        return None
    base = os.path.realpath(os.path.join(_REPO_ROOT, "data", "umh", "execution", kind))
    path = os.path.realpath(os.path.join(base, f"{ident}.json"))
    if not path.startswith(base + os.sep):
        return None
    return path


def configure(require_operator_dep: Any) -> None:
    global _configured, operator_loop_router
    _configured = True
    operator_loop_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/operator-loop/submit-intent", _submit_intent, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/approve", _approve_packet, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/reject", _reject_packet, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/execute", _execute_packet, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/complete", _complete_packet, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/status", _loop_status, methods=["GET"], dependencies=auth)
    r.add_api_route("/operator-loop/packet/{packet_id}", _packet_detail, methods=["GET"], dependencies=auth)
    r.add_api_route("/operator-loop/pending-approvals", _pending_approvals, methods=["GET"], dependencies=auth)
    r.add_api_route("/operator-loop/active-packets", _active_packets, methods=["GET"], dependencies=auth)
    r.add_api_route("/operator-loop/audit-trail", _audit_trail, methods=["GET"], dependencies=auth)
    r.add_api_route("/operator-loop/record-outcome", _record_outcome, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/health", _loop_health, methods=["GET"])
    r.add_api_route("/operator-loop/generate-plan", _generate_plan, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/plan/{plan_id}", _get_plan, methods=["GET"], dependencies=auth)
    r.add_api_route("/operator-loop/approve-plan", _approve_plan, methods=["POST"], dependencies=auth)
    r.add_api_route("/operator-loop/execution-record/{record_id}", _get_execution_record, methods=["GET"], dependencies=auth)
    r.add_api_route("/operator-loop/packet/{packet_id}/records", _packet_records, methods=["GET"], dependencies=auth)
    r.add_api_route("/operator-loop/packet/{packet_id}/failure", _packet_failure, methods=["GET"], dependencies=auth)

    # ── Phase 3: Empire WorkPacket Engine routes ────────────────
    r.add_api_route("/empire/route", _empire_route, methods=["POST"], dependencies=auth)
    r.add_api_route("/empire/domains", _empire_domains, methods=["GET"], dependencies=auth)
    r.add_api_route("/empire/agents", _empire_agents, methods=["GET"], dependencies=auth)
    r.add_api_route("/empire/reality", _empire_reality, methods=["GET"], dependencies=auth)
    r.add_api_route("/empire/packets-by-domain", _empire_packets_by_domain, methods=["GET"], dependencies=auth)
    r.add_api_route("/empire/next-actions", _empire_next_actions, methods=["GET"], dependencies=auth)

    # ── Phase 4: Strategic Gap Engine routes ───────────────────
    r.add_api_route("/strategy/analyze", _strategy_analyze, methods=["POST"], dependencies=auth)
    r.add_api_route("/strategy/goals", _strategy_goals, methods=["GET"], dependencies=auth)
    r.add_api_route("/strategy/goals/add", _strategy_add_goal, methods=["POST"], dependencies=auth)
    r.add_api_route("/strategy/goals/{goal_id}", _strategy_goal_detail, methods=["GET"], dependencies=auth)
    r.add_api_route("/strategy/goals/{goal_id}", _strategy_update_goal, methods=["PUT"], dependencies=auth)
    r.add_api_route("/strategy/goals/{goal_id}", _strategy_delete_goal, methods=["DELETE"], dependencies=auth)
    r.add_api_route("/strategy/gaps", _strategy_gaps, methods=["GET"], dependencies=auth)
    r.add_api_route("/strategy/recommendations", _strategy_recommendations, methods=["GET"], dependencies=auth)
    r.add_api_route("/strategy/recommendations/{rec_id}/approve", _strategy_approve_rec, methods=["POST"], dependencies=auth)
    r.add_api_route("/strategy/recommendations/{rec_id}/reject", _strategy_reject_rec, methods=["POST"], dependencies=auth)
    r.add_api_route("/strategy/decisions", _strategy_decisions, methods=["GET"], dependencies=auth)
    r.add_api_route("/strategy/decisions/{decision_id}/outcome", _strategy_record_outcome, methods=["POST"], dependencies=auth)

    # ── Phase 5: Strategic Tick Loop routes ────────────────────
    r.add_api_route("/tick/status", _tick_status, methods=["GET"], dependencies=auth)
    r.add_api_route("/tick/state", _tick_strategic_state, methods=["GET"], dependencies=auth)
    r.add_api_route("/tick/execute", _tick_execute, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/start", _tick_start, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/stop", _tick_stop, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/pause", _tick_pause, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/resume", _tick_resume, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/frequency", _tick_set_frequency, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/profiles", _tick_set_profiles, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/candidates", _tick_candidates, methods=["GET"], dependencies=auth)
    r.add_api_route("/tick/candidates/{candidate_id}/accept", _tick_accept_candidate, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/candidates/{candidate_id}/reject", _tick_reject_candidate, methods=["POST"], dependencies=auth)
    r.add_api_route("/tick/drift", _tick_drift_warnings, methods=["GET"], dependencies=auth)
    r.add_api_route("/tick/history", _tick_history, methods=["GET"], dependencies=auth)

    return r


def _get_queue():
    from substrate.organism.universal_work_queue import UniversalWorkQueue
    return UniversalWorkQueue()


def _get_runner():
    from substrate.organism.agent_execution_runner import AgentExecutionRunner
    return AgentExecutionRunner()


def _get_sandbox_manager():
    from substrate.organism.worktree_sandbox import SandboxManager
    return SandboxManager()


def _audit_log(event_type: str, data: dict[str, Any]) -> None:
    """Append to JSONL audit trail."""
    audit_path = os.path.join(_REPO_ROOT, "data", "umh", "audit", "operator_loop_audit.jsonl")
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    entry = {
        "id": str(uuid4()),
        "event_type": event_type,
        "timestamp": time.time(),
        "data": data,
    }
    try:
        with open(audit_path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.debug("audit log write failed: %s", e)


def _record_outcome_internal(
    packet_id: str,
    outcome_text: str,
    domain: str = "execution",
    confidence: float = 0.7,
) -> str | None:
    """Write outcome to reality model."""
    try:
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        org_id = os.environ.get("UMH_ORG_ID", os.environ.get("EOS_ORG_ID", "default"))
        user_id = os.environ.get("UMH_USER_ID", os.environ.get("EOS_USER_ID", "default"))
        instance = InstanceRealityModel(user_id=user_id, org_id=org_id)
        obs = InstanceObservation(
            content=outcome_text[:2000],
            domain=domain,
            confidence=confidence,
            tags=["execution_outcome", "operator_loop"],
            metadata={"packet_id": packet_id} if packet_id else {},
        )
        obs_id = instance.record(obs)

        if packet_id:
            try:
                queue = _get_queue()
                pkt = queue.get_packet(packet_id)
                if pkt:
                    pkt.outcome_observation_id = str(obs_id)
                    pkt.outcome_ids = list(set(pkt.outcome_ids + [str(obs_id)]))
                    queue._save()
            except Exception:
                pass

        return str(obs_id)
    except Exception as e:
        logger.debug("record_outcome failed: %s", e)
        return None


# ── Intent Submission ─────────────────────────────────────────


async def _submit_intent(request: Request):
    """Submit high-level intent with full contract."""
    body = await request.json()
    user_intent = body.get("user_intent", "") or body.get("intent", "")
    if not user_intent:
        return {"success": False, "error": "user_intent is required"}

    desired_end_state = body.get("desired_end_state", "")
    constraints = body.get("constraints", [])
    non_goals = body.get("non_goals", [])
    acceptance_criteria = body.get("acceptance_criteria", [])
    quality_bar = body.get("quality_bar", "")
    approval_policy = body.get("approval_policy", "")
    risk_tolerance = body.get("risk_tolerance", "")
    proof_required = body.get("proof_required", [])
    execution_mode = body.get("execution_mode", "validate_only")

    if execution_mode not in _VALID_MODES:
        execution_mode = "validate_only"

    queue = _get_queue()
    packet = queue.ingest_user_intent(
        user_intent=user_intent,
        desired_end_state=desired_end_state,
        constraints=constraints,
    )

    if non_goals:
        packet.failure_criteria = non_goals if isinstance(non_goals, list) else [non_goals]
    if acceptance_criteria:
        packet.success_criteria = acceptance_criteria if isinstance(acceptance_criteria, list) else [acceptance_criteria]
    if quality_bar:
        packet.validation_plan = f"Quality bar: {quality_bar}. {packet.validation_plan or ''}"
    if approval_policy == "auto":
        packet.approval_gates = []
    elif approval_policy == "always":
        packet.approval_gates = ["operator_approval_required"]
    if risk_tolerance and risk_tolerance in ("low", "medium", "high", "critical"):
        packet.risk_class = risk_tolerance
        if risk_tolerance in ("high", "critical"):
            packet.approval_gates = list(set(packet.approval_gates + ["operator_approval_required"]))
    if proof_required:
        proofs = proof_required if isinstance(proof_required, list) else [proof_required]
        existing = packet.validation_plan or ""
        packet.validation_plan = existing + " Proof required: " + ", ".join(proofs)

    if not hasattr(packet, "execution_mode"):
        packet.constraints = list(set(packet.constraints + [f"mode:{execution_mode}"]))

    queue._save()

    needs_approval = bool(packet.approval_gates)

    _audit_log("intent_submitted", {
        "packet_id": packet.packet_id,
        "user_intent": user_intent[:500],
        "risk_class": packet.risk_class,
        "needs_approval": needs_approval,
        "execution_mode": execution_mode,
    })

    return {
        "success": True,
        "packet": packet.to_safe_dict(),
        "needs_approval": needs_approval,
        "risk_class": packet.risk_class,
        "execution_mode": execution_mode,
        "next_action": "approve" if needs_approval else "generate-plan",
    }


# ── Plan Generation ──────────────────────────────────────────


async def _generate_plan(request: Request):
    """Generate an execution plan for a work packet."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"success": False, "error": "packet_id is required"}

    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"success": False, "error": f"Packet {packet_id} not found"}

    runner = _get_runner()
    plan = runner.generate_plan(pkt)

    _audit_log("plan_generated", {
        "packet_id": packet_id,
        "plan_id": plan.plan_id,
        "objectives": plan.objectives[:5],
    })

    return {
        "success": True,
        "plan": plan.to_dict(),
        "next_action": "approve-plan",
    }


async def _get_plan(plan_id: str):
    """Retrieve a generated plan."""
    plan_path = _safe_artifact_path("plans", plan_id)
    if not plan_path or not os.path.exists(plan_path):
        return {"error": "Plan not found", "plan_id": plan_id}
    try:
        with open(plan_path) as f:
            return json.load(f)
    except Exception:
        return {"error": "Failed to read plan"}


async def _approve_plan(request: Request):
    """Approve a generated plan for execution."""
    body = await request.json()
    plan_id = body.get("plan_id", "")
    if not plan_id:
        return {"success": False, "error": "plan_id is required"}

    plan_path = _safe_artifact_path("plans", plan_id)
    if not plan_path or not os.path.exists(plan_path):
        return {"success": False, "error": "Plan not found"}

    try:
        with open(plan_path) as f:
            plan_data = json.load(f)
        plan_data["approved"] = True
        with open(plan_path, "w") as f:
            json.dump(plan_data, f, indent=2, default=str)
    except Exception as e:
        return {"success": False, "error": str(e)}

    _audit_log("plan_approved", {"plan_id": plan_id, "packet_id": plan_data.get("packet_id", "")})

    return {
        "success": True,
        "plan_id": plan_id,
        "next_action": "execute",
    }


# ── Approval ─────────────────────────────────────────────────


async def _approve_packet(request: Request):
    """Approve a work packet for execution."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"success": False, "error": "packet_id is required"}

    from substrate.organism.work_packet import PacketLifecycleStatus

    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"success": False, "error": f"Packet {packet_id} not found"}

    current = pkt.status
    transitions_needed = []

    if current == PacketLifecycleStatus.CLASSIFIED:
        transitions_needed = [
            PacketLifecycleStatus.PLANNED,
            PacketLifecycleStatus.READY_FOR_REVIEW,
            PacketLifecycleStatus.APPROVAL_PENDING,
            PacketLifecycleStatus.APPROVED,
        ]
    elif current == PacketLifecycleStatus.PLANNED:
        transitions_needed = [
            PacketLifecycleStatus.READY_FOR_REVIEW,
            PacketLifecycleStatus.APPROVAL_PENDING,
            PacketLifecycleStatus.APPROVED,
        ]
    elif current == PacketLifecycleStatus.READY_FOR_REVIEW:
        transitions_needed = [
            PacketLifecycleStatus.APPROVAL_PENDING,
            PacketLifecycleStatus.APPROVED,
        ]
    elif current == PacketLifecycleStatus.APPROVAL_PENDING:
        transitions_needed = [PacketLifecycleStatus.APPROVED]
    elif current == PacketLifecycleStatus.APPROVED:
        return {"success": True, "packet_id": packet_id, "status": "already_approved"}
    else:
        return {"success": False, "error": f"Cannot approve from status '{current.value}'"}

    for next_status in transitions_needed:
        ok = queue.update_packet_status(packet_id, next_status, f"operator approved → {next_status.value}")
        if not ok:
            return {"success": False, "error": f"Transition to {next_status.value} failed"}

    _audit_log("packet_approved", {"packet_id": packet_id})
    return {"success": True, "packet_id": packet_id, "status": "approved", "next_action": "execute"}


async def _reject_packet(request: Request):
    """Reject a work packet."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    reason = body.get("reason", "operator rejected")
    if not packet_id:
        return {"success": False, "error": "packet_id is required"}

    from substrate.organism.work_packet import PacketLifecycleStatus

    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"success": False, "error": f"Packet {packet_id} not found"}

    if pkt.status == PacketLifecycleStatus.APPROVAL_PENDING:
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.REJECTED, reason)
    else:
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.BLOCKED, reason)

    _audit_log("packet_rejected", {"packet_id": packet_id, "reason": reason})
    return {"success": ok, "packet_id": packet_id, "status": "rejected"}


# ── Execution ────────────────────────────────────────────────


async def _execute_packet(request: Request):
    """Execute a work packet — plan, implement, validate."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    mode = body.get("mode", "validate_only")
    plan_id = body.get("plan_id", "")

    if not packet_id:
        return {"success": False, "error": "packet_id is required"}
    if mode not in _VALID_MODES:
        return {"success": False, "error": f"Invalid mode: {mode}. Must be one of {_VALID_MODES}"}

    from substrate.organism.work_packet import PacketLifecycleStatus

    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"success": False, "error": f"Packet {packet_id} not found"}

    if pkt.approval_gates and pkt.status != PacketLifecycleStatus.APPROVED:
        return {
            "success": False,
            "error": "Packet requires approval before execution",
            "status": pkt.status.value,
        }

    if pkt.status == PacketLifecycleStatus.APPROVED:
        queue.update_packet_status(packet_id, PacketLifecycleStatus.DELEGATED, "delegated")
    elif pkt.status == PacketLifecycleStatus.CLASSIFIED and not pkt.approval_gates:
        queue.update_packet_status(packet_id, PacketLifecycleStatus.PLANNED, "auto-planned")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.READY_FOR_REVIEW, "auto-reviewed")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.APPROVAL_PENDING, "auto-pending")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.APPROVED, "auto-approved")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.DELEGATED, "auto-delegated")
    elif pkt.status == PacketLifecycleStatus.DELEGATED:
        pass
    else:
        return {"success": False, "error": f"Cannot execute from status '{pkt.status.value}'"}

    queue.update_packet_status(packet_id, PacketLifecycleStatus.EXECUTING, "execution started")

    _audit_log("packet_executing", {
        "packet_id": packet_id,
        "mode": mode,
        "risk_class": pkt.risk_class,
    })

    runner = _get_runner()
    pkt = queue.get_packet(packet_id)

    plan = None
    if plan_id:
        plan_data = await _get_plan(plan_id)
        if not isinstance(plan_data, dict) or "error" in plan_data:
            pass
        else:
            from substrate.organism.agent_execution_runner import AgentExecutionPlan
            plan = AgentExecutionPlan(**{k: v for k, v in plan_data.items() if k in AgentExecutionPlan.__dataclass_fields__})
    elif mode in ("implement", "implement_and_validate"):
        plan = runner.generate_plan(pkt)
        _audit_log("plan_auto_generated", {
            "packet_id": packet_id,
            "plan_id": plan.plan_id,
        })

    record = runner.execute(pkt, mode=mode, plan=plan)

    pkt = queue.get_packet(packet_id)
    pkt.verification_results = record.validation_results
    pkt.verification_passed = record.all_validations_passed
    pkt.linked_sandbox_id = record.sandbox_id
    queue._save()

    if record.sandbox_id:
        queue.link_execution_artifacts(packet_id, {"sandbox_id": record.sandbox_id})

    if record.success:
        queue.update_packet_status(packet_id, PacketLifecycleStatus.VALIDATING, "validated")
    else:
        queue.update_packet_status(packet_id, PacketLifecycleStatus.FAILED, record.error or "execution failed")

    _record_outcome_internal(
        packet_id=packet_id,
        outcome_text=(
            f"Execution {mode}: {'passed' if record.success else 'failed'}. "
            f"Files: {len(record.files_changed)}. "
            f"Commits: {len(record.commits)}. "
            f"Duration: {record.duration_seconds}s."
        ),
        domain=pkt.domain or "execution",
        confidence=0.9 if record.success else 0.5,
    )

    _audit_log("execution_complete", {
        "packet_id": packet_id,
        "record_id": record.record_id,
        "mode": mode,
        "success": record.success,
        "files_changed": record.files_changed[:20],
        "duration_seconds": record.duration_seconds,
    })

    return {
        "success": True,
        "packet_id": packet_id,
        "record_id": record.record_id,
        "sandbox_id": record.sandbox_id,
        "mode": mode,
        "execution_success": record.success,
        "files_changed": record.files_changed,
        "diff_summary": record.diff_summary,
        "commits": record.commits,
        "validation_results": record.validation_results,
        "all_passed": record.all_validations_passed,
        "agent_output": record.agent_output[:3000] if record.agent_output else "",
        "duration_seconds": record.duration_seconds,
        "error": record.error,
        "plan": plan.to_dict() if plan else None,
        "failure_report": runner.get_failure(packet_id).to_dict() if runner.get_failure(packet_id) else None,
        "needs_review": pkt.risk_class in ("high", "critical") and record.success,
        "next_action": (
            "review" if pkt.risk_class in ("high", "critical") and record.success
            else "complete" if record.success
            else "retry_or_escalate"
        ),
    }


# ── Completion ───────────────────────────────────────────────


async def _complete_packet(request: Request):
    """Mark a packet as completed with outcome."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    outcome = body.get("outcome", "")
    success = body.get("success", True)
    if not packet_id:
        return {"success": False, "error": "packet_id is required"}

    from substrate.organism.work_packet import PacketLifecycleStatus

    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"success": False, "error": f"Packet {packet_id} not found"}

    if success:
        if pkt.status != PacketLifecycleStatus.VALIDATING:
            queue.update_packet_status(packet_id, PacketLifecycleStatus.VALIDATING, "pre-complete")
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.COMPLETED, outcome or "completed")
    else:
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.FAILED, outcome or "failed")

    pkt = queue.get_packet(packet_id)
    pkt.outcome_summary = outcome[:500] if outcome else ""
    queue._save()

    _record_outcome_internal(
        packet_id=packet_id,
        outcome_text=f"Packet {'completed' if success else 'failed'}: {outcome[:300]}",
        domain=pkt.domain or "execution",
        confidence=0.85 if success else 0.5,
    )

    _audit_log("packet_completed", {"packet_id": packet_id, "success": success, "outcome": outcome[:500]})
    return {"success": ok, "packet_id": packet_id, "status": "completed" if success else "failed"}


# ── Status & Query ───────────────────────────────────────────


async def _loop_status():
    """Current operator loop status."""
    queue = _get_queue()
    summary = queue.compute_queue_summary()
    pending_approval = queue.get_packets_requiring_approval()
    blocked = queue.get_blocked_packets()
    human_required = queue.get_packets_requiring_human()
    next_best = queue.get_next_best_packet()

    return {
        "queue_summary": summary,
        "pending_approval_count": len(pending_approval),
        "blocked_count": len(blocked),
        "human_required_count": len(human_required),
        "next_best": next_best.to_safe_dict() if next_best else None,
    }


async def _packet_detail(packet_id: str):
    """Full work packet detail with audit trail and execution records."""
    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"error": "Not found", "packet_id": packet_id}

    result = pkt.to_dict()
    result["audit_trail"] = _get_audit_entries_for_packet(packet_id)

    records_dir = os.path.join(_REPO_ROOT, "data", "umh", "execution", "records")
    if os.path.isdir(records_dir):
        records = []
        for fname in os.listdir(records_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(records_dir, fname)) as f:
                        rec = json.load(f)
                    if rec.get("packet_id") == packet_id:
                        records.append(rec)
                except Exception:
                    pass
        result["execution_records"] = sorted(records, key=lambda r: r.get("started_at", 0))

    if pkt.linked_sandbox_id:
        try:
            sandbox_mgr = _get_sandbox_manager()
            sb = sandbox_mgr.get_sandbox(pkt.linked_sandbox_id)
            if sb:
                result["sandbox"] = sb.to_dict()
        except Exception:
            pass

    return result


async def _pending_approvals():
    queue = _get_queue()
    return [p.to_safe_dict() for p in queue.get_packets_requiring_approval()]


async def _active_packets():
    queue = _get_queue()
    active = [p for p in queue.all_packets() if p.status.value in (
        "executing", "delegated", "reconverging", "validating",
    )]
    return [p.to_safe_dict() for p in active]


async def _audit_trail(packet_id: str | None = None, limit: int = 50):
    if packet_id:
        return _get_audit_entries_for_packet(packet_id)

    audit_path = os.path.join(_REPO_ROOT, "data", "umh", "audit", "operator_loop_audit.jsonl")
    if not os.path.exists(audit_path):
        return []

    entries = []
    try:
        with open(audit_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    entries.reverse()
    return entries[:limit]


async def _record_outcome(request: Request):
    body = await request.json()
    outcome_text = body.get("outcome", "")
    if not outcome_text:
        return {"success": False, "error": "outcome is required"}

    obs_id = _record_outcome_internal(
        packet_id=body.get("packet_id", ""),
        outcome_text=outcome_text,
        domain=body.get("domain", "execution"),
        confidence=body.get("confidence", 0.7),
    )
    if obs_id:
        return {"success": True, "observation_id": obs_id}
    return {"success": False, "error": "recording failed"}


async def _loop_health():
    """Health endpoint."""
    queue = _get_queue()
    summary = queue.compute_queue_summary()

    audit_path = os.path.join(_REPO_ROOT, "data", "umh", "audit", "operator_loop_audit.jsonl")
    latest_audit = None
    if os.path.exists(audit_path):
        try:
            with open(audit_path) as f:
                lines = f.readlines()
            if lines:
                last = lines[-1].strip()
                if last:
                    latest_audit = json.loads(last)
        except Exception:
            pass

    sandbox_summary = {}
    try:
        sandbox_mgr = _get_sandbox_manager()
        sandbox_summary = sandbox_mgr.to_dict()
    except Exception:
        sandbox_summary = {"error": "unavailable"}

    records_count = 0
    records_dir = os.path.join(_REPO_ROOT, "data", "umh", "execution", "records")
    if os.path.isdir(records_dir):
        records_count = len([f for f in os.listdir(records_dir) if f.endswith(".json")])

    return {
        "healthy": True,
        "timestamp": time.time(),
        "queue_summary": summary,
        "latest_audit_event": latest_audit,
        "sandbox_summary": {
            "total": sandbox_summary.get("total_sandboxes", 0),
            "active": sandbox_summary.get("active_sandboxes", 0),
        },
        "execution_records": records_count,
    }


# ── Execution Records ────────────────────────────────────────


async def _get_execution_record(record_id: str):
    """Retrieve a single execution record."""
    path = _safe_artifact_path("records", record_id)
    if not path or not os.path.exists(path):
        return {"error": "Not found", "record_id": record_id}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {"error": "Failed to read record"}


async def _packet_records(packet_id: str):
    """All execution records for a packet."""
    records_dir = os.path.join(_REPO_ROOT, "data", "umh", "execution", "records")
    if not os.path.isdir(records_dir):
        return []
    records = []
    for fname in os.listdir(records_dir):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(records_dir, fname)) as f:
                    rec = json.load(f)
                if rec.get("packet_id") == packet_id:
                    records.append(rec)
            except Exception:
                pass
    return sorted(records, key=lambda r: r.get("started_at", 0))


async def _packet_failure(packet_id: str):
    """Get failure report for a packet."""
    fail_dir = os.path.join(_REPO_ROOT, "data", "umh", "execution", "failures")
    if not os.path.isdir(fail_dir):
        return {"error": "No failures recorded"}
    for fname in os.listdir(fail_dir):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(fail_dir, fname)) as f:
                    report = json.load(f)
                if report.get("packet_id") == packet_id:
                    return report
            except Exception:
                pass
    return {"error": "No failure found for this packet"}


# ── Helpers ──────────────────────────────────────────────────


def _get_audit_entries_for_packet(packet_id: str) -> list[dict]:
    audit_path = os.path.join(_REPO_ROOT, "data", "umh", "audit", "operator_loop_audit.jsonl")
    if not os.path.exists(audit_path):
        return []
    entries = []
    try:
        with open(audit_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("data", {}).get("packet_id") == packet_id:
                        entries.append(entry)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return entries


# ── Phase 3: Empire WorkPacket Engine handlers ────────────────────────


async def _empire_route(request: Request) -> dict:
    """Route founder intent through domain classification, decomposition,
    agent assignment, and governance."""
    body = await request.json()
    intent = body.get("intent", "").strip()
    if not intent:
        return {"success": False, "error": "intent is required"}

    desired_end_state = body.get("desired_end_state", "")
    constraints = body.get("constraints", [])
    profile_mode = body.get("profile_mode", "")
    session_mode = body.get("session_mode", "")
    operator_available = body.get("operator_available", True)

    try:
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        result = router.route(
            intent=intent,
            desired_end_state=desired_end_state,
            constraints=constraints,
            profile_mode=profile_mode,
            session_mode=session_mode,
            operator_available=operator_available,
        )

        _audit_log("empire_route", {
            "routing_id": result.routing_id,
            "domain": result.domain,
            "scope": result.scope,
            "packet_count": len(result.work_packets),
            "intent_preview": intent[:100],
        })

        return {
            "success": True,
            "routing": result.to_dict(),
        }
    except Exception as exc:
        logger.error("empire route failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


async def _empire_domains(request: Request) -> list:
    """Return all domain definitions."""
    try:
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        return router.get_domain_summary()
    except Exception as exc:
        logger.error("empire domains failed: %s", exc)
        return []


async def _empire_agents(request: Request) -> list:
    """Return all agent type definitions."""
    try:
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        return router.get_agent_summary()
    except Exception as exc:
        logger.error("empire agents failed: %s", exc)
        return []


async def _empire_reality(request: Request) -> dict:
    """Return current reality model snapshot."""
    try:
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        snapshot = router.get_reality_snapshot()
        return {"success": True, "reality": snapshot.to_dict()}
    except Exception as exc:
        logger.error("empire reality failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _empire_packets_by_domain(request: Request) -> dict:
    """Return work packets grouped by domain."""
    try:
        from substrate.organism.universal_work_queue import UniversalWorkQueue
        from substrate.organism.domain_registry import DomainRegistry

        q = UniversalWorkQueue()
        registry = DomainRegistry()
        by_domain: dict[str, list[dict]] = {}

        for pkt in q.all_packets():
            domain = registry.resolve_id(pkt.domain) if pkt.domain else "unknown"
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(pkt.to_safe_dict())

        return {"success": True, "domains": by_domain}
    except Exception as exc:
        logger.error("empire packets by domain failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _empire_next_actions(request: Request) -> dict:
    """Return computed next best actions."""
    try:
        from substrate.organism.empire_router import EmpireRouter
        router = EmpireRouter()
        snapshot = router.get_reality_snapshot()
        return {
            "success": True,
            "next_actions": snapshot.next_best_actions,
            "open_approvals": snapshot.open_approvals,
            "blocked_count": len(snapshot.blocked_items),
            "active_domains": snapshot.active_domains,
        }
    except Exception as exc:
        logger.error("empire next actions failed: %s", exc)
        return {"success": False, "error": str(exc)}


# ── Phase 4: Strategic Gap Engine handlers ──────────────────────────


def _get_gap_engine():
    from substrate.organism.strategic_gap_engine import StrategicGapEngine
    return StrategicGapEngine()


async def _strategy_analyze(request: Request) -> dict:
    """Run full gap analysis cycle."""
    try:
        engine = _get_gap_engine()
        result = engine.analyze()
        _audit_log("strategy_analyze", {
            "gap_count": result["gap_count"],
            "recommendation_count": result["recommendation_count"],
        })
        return {"success": True, **result}
    except Exception as exc:
        logger.error("strategy analyze failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


async def _strategy_goals(request: Request) -> dict:
    """Return all goals."""
    try:
        engine = _get_gap_engine()
        goals = engine.goal_registry.all_goals()
        return {
            "success": True,
            "goals": [g.to_dict() for g in goals],
            "count": len(goals),
        }
    except Exception as exc:
        logger.error("strategy goals failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _strategy_add_goal(request: Request) -> dict:
    """Add a new goal."""
    try:
        body = await request.json()
        from substrate.organism.strategic_gap_engine import Goal, GoalType, GoalStatus, SuccessCriterion

        criteria = []
        for c in body.get("success_criteria", []):
            criteria.append(SuccessCriterion(
                description=c.get("description", ""),
                measurable=c.get("measurable", True),
                current_value=c.get("current_value", ""),
                target_value=c.get("target_value", ""),
                met=c.get("met", False),
            ))

        goal = Goal(
            title=body.get("title", ""),
            description=body.get("description", ""),
            goal_type=GoalType(body["goal_type"]) if "goal_type" in body else GoalType.GOAL,
            status=GoalStatus(body["status"]) if "status" in body else GoalStatus.ACTIVE,
            domain=body.get("domain", ""),
            parent_goal_id=body.get("parent_goal_id", ""),
            success_criteria=criteria,
            required_capabilities=body.get("required_capabilities", []),
            required_milestones=body.get("required_milestones", []),
            dependencies=body.get("dependencies", []),
            target_date=body.get("target_date", ""),
            priority=body.get("priority", 50),
        )

        engine = _get_gap_engine()
        engine.goal_registry.add(goal)

        _audit_log("strategy_goal_added", {
            "goal_id": goal.goal_id,
            "title": goal.title,
            "domain": goal.domain,
        })

        return {"success": True, "goal": goal.to_dict()}
    except Exception as exc:
        logger.error("strategy add goal failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


async def _strategy_goal_detail(request: Request) -> dict:
    """Return a single goal."""
    goal_id = request.path_params.get("goal_id", "")
    try:
        engine = _get_gap_engine()
        goal = engine.goal_registry.get(goal_id)
        if not goal:
            return {"success": False, "error": f"goal {goal_id} not found"}
        return {"success": True, "goal": goal.to_dict()}
    except Exception as exc:
        logger.error("strategy goal detail failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _strategy_update_goal(request: Request) -> dict:
    """Update a goal."""
    goal_id = request.path_params.get("goal_id", "")
    try:
        body = await request.json()
        engine = _get_gap_engine()
        goal = engine.goal_registry.get(goal_id)
        if not goal:
            return {"success": False, "error": f"goal {goal_id} not found"}

        from substrate.organism.strategic_gap_engine import GoalStatus, GoalType, SuccessCriterion

        if "title" in body:
            goal.title = body["title"]
        if "description" in body:
            goal.description = body["description"]
        if "status" in body:
            goal.status = GoalStatus(body["status"])
        if "goal_type" in body:
            goal.goal_type = GoalType(body["goal_type"])
        if "domain" in body:
            goal.domain = body["domain"]
        if "priority" in body:
            goal.priority = body["priority"]
        if "target_date" in body:
            goal.target_date = body["target_date"]
        if "required_capabilities" in body:
            goal.required_capabilities = body["required_capabilities"]
        if "required_milestones" in body:
            goal.required_milestones = body["required_milestones"]
        if "success_criteria" in body:
            goal.success_criteria = [
                SuccessCriterion.from_dict(c) for c in body["success_criteria"]
            ]

        engine.goal_registry.update(goal)

        _audit_log("strategy_goal_updated", {
            "goal_id": goal.goal_id,
            "title": goal.title,
        })

        return {"success": True, "goal": goal.to_dict()}
    except Exception as exc:
        logger.error("strategy update goal failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


async def _strategy_delete_goal(request: Request) -> dict:
    """Delete a goal."""
    goal_id = request.path_params.get("goal_id", "")
    try:
        engine = _get_gap_engine()
        removed = engine.goal_registry.remove(goal_id)
        if not removed:
            return {"success": False, "error": f"goal {goal_id} not found"}

        _audit_log("strategy_goal_deleted", {"goal_id": goal_id})
        return {"success": True, "goal_id": goal_id}
    except Exception as exc:
        logger.error("strategy delete goal failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _strategy_gaps(request: Request) -> dict:
    """Return detected gaps from last analysis."""
    try:
        engine = _get_gap_engine()
        result = engine.analyze()
        return {
            "success": True,
            "gaps": result["gaps"],
            "count": result["gap_count"],
        }
    except Exception as exc:
        logger.error("strategy gaps failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _strategy_recommendations(request: Request) -> dict:
    """Return top recommendations."""
    try:
        engine = _get_gap_engine()
        recs = engine.get_top_recommendations(limit=10)
        return {
            "success": True,
            "recommendations": [r.to_dict() for r in recs],
            "count": len(recs),
        }
    except Exception as exc:
        logger.error("strategy recommendations failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _strategy_approve_rec(request: Request) -> dict:
    """Approve a recommendation → generates governed WorkPacket."""
    rec_id = request.path_params.get("rec_id", "")
    try:
        body = await request.json()
        reason = body.get("reason", "")
        engine = _get_gap_engine()
        result = engine.approve_recommendation(rec_id, reason)

        if result.get("success"):
            _audit_log("strategy_rec_approved", {
                "recommendation_id": rec_id,
                "packet_id": result.get("packet_id", ""),
            })

        return result
    except Exception as exc:
        logger.error("strategy approve rec failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


async def _strategy_reject_rec(request: Request) -> dict:
    """Reject a recommendation with reason (feeds learning loop)."""
    rec_id = request.path_params.get("rec_id", "")
    try:
        body = await request.json()
        reason = body.get("reason", "")
        engine = _get_gap_engine()
        result = engine.reject_recommendation(rec_id, reason)

        if result.get("success"):
            _audit_log("strategy_rec_rejected", {
                "recommendation_id": rec_id,
                "reason": reason[:200],
            })

        return result
    except Exception as exc:
        logger.error("strategy reject rec failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


async def _strategy_decisions(request: Request) -> dict:
    """Return decision history (learning loop)."""
    try:
        engine = _get_gap_engine()
        decisions = engine.get_decision_history()
        return {
            "success": True,
            "decisions": decisions,
            "count": len(decisions),
        }
    except Exception as exc:
        logger.error("strategy decisions failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _strategy_record_outcome(request: Request) -> dict:
    """Record whether a decision was effective (learning loop)."""
    decision_id = request.path_params.get("decision_id", "")
    try:
        body = await request.json()
        was_effective = body.get("was_effective", False)
        summary = body.get("summary", "")
        engine = _get_gap_engine()
        result = engine.record_outcome(decision_id, was_effective, summary)

        if result.get("success"):
            _audit_log("strategy_outcome_recorded", {
                "decision_id": decision_id,
                "was_effective": was_effective,
            })

        return result
    except Exception as exc:
        logger.error("strategy record outcome failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


# ── Phase 5: Strategic Tick Loop helpers & handlers ────────────────


def _get_tick_loop():
    from substrate.organism.strategic_tick_loop import get_tick_loop
    return get_tick_loop()


async def _tick_status(request: Request) -> dict:
    """Compact tick loop status."""
    try:
        loop = _get_tick_loop()
        return {"success": True, **loop.status()}
    except Exception as exc:
        logger.error("tick status failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_strategic_state(request: Request) -> dict:
    """Full strategic state for cockpit command center."""
    try:
        loop = _get_tick_loop()
        return {"success": True, **loop.get_strategic_state()}
    except Exception as exc:
        logger.error("tick strategic state failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_execute(request: Request) -> dict:
    """Execute one tick cycle manually."""
    try:
        loop = _get_tick_loop()
        record = loop.execute_tick()
        _audit_log("tick_executed", {
            "tick_id": record.tick_id,
            "change_detected": record.change_detected,
            "analysis_ran": record.analysis_ran,
            "gaps_found": record.gaps_found,
        })
        return {"success": True, "tick": record.to_dict()}
    except Exception as exc:
        logger.error("tick execute failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


async def _tick_start(request: Request) -> dict:
    """Start the tick loop."""
    try:
        body = await request.json()
        freq = body.get("frequency", "")
        loop = _get_tick_loop()
        if freq:
            from substrate.organism.strategic_tick_loop import TickFrequency
            loop.frequency = TickFrequency(freq)
        loop.start()
        _audit_log("tick_started", {"frequency": loop.frequency.value})
        return {"success": True, "status": loop.status()}
    except Exception as exc:
        logger.error("tick start failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_stop(request: Request) -> dict:
    """Stop the tick loop."""
    try:
        loop = _get_tick_loop()
        loop.stop()
        _audit_log("tick_stopped", {"cycle_count": loop.cycle_count})
        return {"success": True, "status": loop.status()}
    except Exception as exc:
        logger.error("tick stop failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_pause(request: Request) -> dict:
    """Pause the tick loop (maintains state)."""
    try:
        loop = _get_tick_loop()
        loop.pause()
        _audit_log("tick_paused", {"cycle_count": loop.cycle_count})
        return {"success": True, "status": loop.status()}
    except Exception as exc:
        logger.error("tick pause failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_resume(request: Request) -> dict:
    """Resume the tick loop from paused state."""
    try:
        loop = _get_tick_loop()
        loop.resume()
        _audit_log("tick_resumed", {"cycle_count": loop.cycle_count})
        return {"success": True, "status": loop.status()}
    except Exception as exc:
        logger.error("tick resume failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_set_frequency(request: Request) -> dict:
    """Set tick frequency."""
    try:
        body = await request.json()
        freq = body.get("frequency", "1m")
        from substrate.organism.strategic_tick_loop import TickFrequency
        loop = _get_tick_loop()
        loop.frequency = TickFrequency(freq)
        _audit_log("tick_frequency_changed", {"frequency": freq})
        return {"success": True, "frequency": freq, "status": loop.status()}
    except Exception as exc:
        logger.error("tick set frequency failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_set_profiles(request: Request) -> dict:
    """Set active profile modes for prioritization."""
    try:
        body = await request.json()
        profiles = body.get("profiles", [])
        loop = _get_tick_loop()
        loop.set_active_profiles(profiles)
        _audit_log("tick_profiles_set", {"profiles": profiles})
        return {"success": True, "profiles": profiles}
    except Exception as exc:
        logger.error("tick set profiles failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_candidates(request: Request) -> dict:
    """Return candidate work queue."""
    try:
        loop = _get_tick_loop()
        pending = loop.candidate_queue.pending()
        all_items = loop.candidate_queue.all_items()
        return {
            "success": True,
            "pending": [i.to_dict() for i in pending],
            "pending_count": len(pending),
            "total": len(all_items),
            "all": [i.to_dict() for i in all_items],
        }
    except Exception as exc:
        logger.error("tick candidates failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_accept_candidate(request: Request) -> dict:
    """Accept a candidate → transitions to ACCEPTED lifecycle."""
    candidate_id = request.path_params.get("candidate_id", "")
    try:
        from substrate.organism.strategic_tick_loop import RecommendationLifecycle
        loop = _get_tick_loop()
        success = loop.candidate_queue.update_lifecycle(
            candidate_id, RecommendationLifecycle.ACCEPTED
        )
        if success:
            _audit_log("tick_candidate_accepted", {"candidate_id": candidate_id})
        return {"success": success}
    except Exception as exc:
        logger.error("tick accept candidate failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_reject_candidate(request: Request) -> dict:
    """Reject a candidate → transitions to REJECTED lifecycle."""
    candidate_id = request.path_params.get("candidate_id", "")
    try:
        from substrate.organism.strategic_tick_loop import RecommendationLifecycle
        loop = _get_tick_loop()
        success = loop.candidate_queue.update_lifecycle(
            candidate_id, RecommendationLifecycle.REJECTED
        )
        if success:
            _audit_log("tick_candidate_rejected", {"candidate_id": candidate_id})
        return {"success": success}
    except Exception as exc:
        logger.error("tick reject candidate failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_drift_warnings(request: Request) -> dict:
    """Return current drift warnings."""
    try:
        loop = _get_tick_loop()
        warnings = loop.last_drift_warnings
        return {
            "success": True,
            "warnings": [w.to_dict() for w in warnings],
            "count": len(warnings),
        }
    except Exception as exc:
        logger.error("tick drift warnings failed: %s", exc)
        return {"success": False, "error": str(exc)}


async def _tick_history(request: Request) -> dict:
    """Return recent tick history."""
    try:
        loop = _get_tick_loop()
        history = loop.tick_history
        return {
            "success": True,
            "ticks": [t.to_dict() for t in history[-20:]],
            "count": len(history),
        }
    except Exception as exc:
        logger.error("tick history failed: %s", exc)
        return {"success": False, "error": str(exc)}
