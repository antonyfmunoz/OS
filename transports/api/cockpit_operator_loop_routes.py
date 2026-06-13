"""Cockpit operator loop routes — intent to plan to implementation to audit.

The Operator Loop lifecycle:
  1. Operator submits intent (full contract)
  2. Intent classified → work packet created
  3. Risk classified → approval gate enforced
  4. Plan generated → reviewable in cockpit
  5. Approved packets → sandbox created → agent executes
  6. Validation runs → proof captured
  7. Outcomes recorded in reality model
  8. Audit trail preserved

Execution modes:
  VALIDATE_ONLY        — run validation commands (default)
  IMPLEMENT            — invoke coding agent
  IMPLEMENT_AND_VALIDATE — agent implements, then validate

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
