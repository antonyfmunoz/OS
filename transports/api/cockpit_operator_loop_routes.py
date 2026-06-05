"""Cockpit operator loop routes — intent to execution to audit.

The core Stage 1 organism loop:
  1. Operator gives intent (text)
  2. Intent classified → work packet created
  3. Risk classified → approval gate enforced
  4. Approved packets routed to agents/tools
  5. Execution state tracked
  6. Outcomes recorded in reality model
  7. Audit trail preserved

Mounted under /api/umh/ via include_router in cockpit.py.

Phase 14.7A WP-2.1/2.2/2.4. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

operator_loop_router: APIRouter = APIRouter()

_configured: bool = False


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
    r.add_api_route("/operator-loop/status", _loop_status, methods=["GET"])
    r.add_api_route("/operator-loop/packet/{packet_id}", _packet_detail, methods=["GET"])
    r.add_api_route("/operator-loop/pending-approvals", _pending_approvals, methods=["GET"])
    r.add_api_route("/operator-loop/active-packets", _active_packets, methods=["GET"])
    r.add_api_route("/operator-loop/audit-trail", _audit_trail, methods=["GET"])
    r.add_api_route("/operator-loop/record-outcome", _record_outcome, methods=["POST"], dependencies=auth)

    return r


def _get_engine():
    from substrate.organism.work_packet_engine import WorkPacketEngine
    return WorkPacketEngine()


def _get_queue():
    from substrate.organism.universal_work_queue import UniversalWorkQueue
    return UniversalWorkQueue()


def _get_classifier():
    from substrate.organism.intent_classifier import IntentClassifier
    return IntentClassifier()


def _audit_log(event_type: str, data: dict[str, Any]) -> None:
    """Append to JSONL audit trail."""
    audit_path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "audit", "operator_loop_audit.jsonl",
    )
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


async def _submit_intent(request: Request):
    """Step 1: Operator submits high-level intent. Creates a work packet."""
    body = await request.json()
    user_intent = body.get("user_intent", "")
    if not user_intent:
        return {"success": False, "error": "user_intent is required"}

    desired_end_state = body.get("desired_end_state", "")
    constraints = body.get("constraints", [])

    queue = _get_queue()
    packet = queue.ingest_user_intent(
        user_intent=user_intent,
        desired_end_state=desired_end_state,
        constraints=constraints,
    )

    needs_approval = bool(packet.approval_gates)
    risk_class = packet.risk_class

    _audit_log("intent_submitted", {
        "packet_id": packet.packet_id,
        "user_intent": user_intent[:500],
        "risk_class": risk_class,
        "needs_approval": needs_approval,
        "domain": packet.domain,
    })

    return {
        "success": True,
        "packet": packet.to_safe_dict(),
        "needs_approval": needs_approval,
        "risk_class": risk_class,
        "next_action": "approve" if needs_approval else "execute",
    }


async def _approve_packet(request: Request):
    """Step 2a: Operator approves a work packet for execution."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"success": False, "error": "packet_id is required"}

    from substrate.organism.work_packet import PacketLifecycleStatus

    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"success": False, "error": f"Packet {packet_id} not found"}

    target_status = PacketLifecycleStatus.APPROVED
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
        return {
            "success": False,
            "error": f"Cannot approve from status '{current.value}'",
        }

    for next_status in transitions_needed:
        ok = queue.update_packet_status(packet_id, next_status, f"operator approved (advancing to {next_status.value})")
        if not ok:
            return {"success": False, "error": f"Transition to {next_status.value} failed"}

    _audit_log("packet_approved", {"packet_id": packet_id})

    return {
        "success": True,
        "packet_id": packet_id,
        "status": "approved",
        "next_action": "execute",
    }


async def _reject_packet(request: Request):
    """Step 2b: Operator rejects a work packet."""
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


async def _execute_packet(request: Request):
    """Step 3: Execute an approved work packet through the governed spine."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    if not packet_id:
        return {"success": False, "error": "packet_id is required"}

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
            "approval_gates": pkt.approval_gates,
        }

    if pkt.status == PacketLifecycleStatus.APPROVED:
        queue.update_packet_status(packet_id, PacketLifecycleStatus.DELEGATED, "delegated for execution")

    pkt = queue.get_packet(packet_id)
    if pkt.status == PacketLifecycleStatus.DELEGATED:
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.EXECUTING, "execution started by operator")
    elif pkt.status == PacketLifecycleStatus.CLASSIFIED and not pkt.approval_gates:
        queue.update_packet_status(packet_id, PacketLifecycleStatus.PLANNED, "auto-planned")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.READY_FOR_REVIEW, "auto-reviewed")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.APPROVAL_PENDING, "auto-pending")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.APPROVED, "auto-approved (no approval gates)")
        queue.update_packet_status(packet_id, PacketLifecycleStatus.DELEGATED, "auto-delegated")
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.EXECUTING, "execution started")
    else:
        return {
            "success": False,
            "error": f"Cannot execute from status '{pkt.status.value}'",
        }

    _audit_log("packet_executing", {
        "packet_id": packet_id,
        "risk_class": pkt.risk_class,
        "domain": pkt.domain,
    })

    return {
        "success": True,
        "packet_id": packet_id,
        "status": "executing",
        "risk_class": pkt.risk_class,
    }


async def _complete_packet(request: Request):
    """Step 4: Mark an executing packet as completed with outcome."""
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
        queue.update_packet_status(packet_id, PacketLifecycleStatus.VALIDATING, "validating outcome")
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.COMPLETED, outcome or "completed")
    else:
        ok = queue.update_packet_status(packet_id, PacketLifecycleStatus.FAILED, outcome or "failed")

    _audit_log("packet_completed", {
        "packet_id": packet_id,
        "success": success,
        "outcome": outcome[:500] if outcome else "",
    })

    return {"success": ok, "packet_id": packet_id, "status": "completed" if success else "failed"}


async def _loop_status():
    """Current operator loop status — packets, approvals, execution."""
    queue = _get_queue()
    summary = queue.compute_queue_summary()

    pending_approval = queue.get_packets_requiring_approval()
    blocked = queue.get_blocked_packets()
    human_required = queue.get_packets_requiring_human()

    return {
        "queue_summary": summary,
        "pending_approval_count": len(pending_approval),
        "blocked_count": len(blocked),
        "human_required_count": len(human_required),
        "next_best": queue.get_next_best_packet().to_safe_dict() if queue.get_next_best_packet() else None,
    }


async def _packet_detail(packet_id: str):
    """Full work packet detail with audit trail."""
    queue = _get_queue()
    pkt = queue.get_packet(packet_id)
    if not pkt:
        return {"error": "Not found", "packet_id": packet_id}

    audit_entries = _get_audit_entries_for_packet(packet_id)

    result = pkt.to_dict()
    result["audit_trail"] = audit_entries
    return result


async def _pending_approvals():
    """List all packets needing operator approval."""
    queue = _get_queue()
    pending = queue.get_packets_requiring_approval()
    return [p.to_safe_dict() for p in pending]


async def _active_packets():
    """List all packets currently executing or recently completed."""
    queue = _get_queue()
    all_packets = queue.all_packets()
    active = [p for p in all_packets if p.status.value in (
        "executing", "delegated", "reconverging", "validating",
    )]
    return [p.to_safe_dict() for p in active]


async def _audit_trail(packet_id: str | None = None, limit: int = 50):
    """Read audit trail, optionally filtered by packet."""
    if packet_id:
        return _get_audit_entries_for_packet(packet_id)

    audit_path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "audit", "operator_loop_audit.jsonl",
    )
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
    """Record an execution outcome in the reality model."""
    body = await request.json()
    packet_id = body.get("packet_id", "")
    outcome_text = body.get("outcome", "")
    domain = body.get("domain", "execution")
    confidence = body.get("confidence", 0.7)

    if not outcome_text:
        return {"success": False, "error": "outcome is required"}

    try:
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        org_id = os.environ.get("UMH_ORG_ID", os.environ.get("EOS_ORG_ID", "default"))
        user_id = os.environ.get("UMH_USER_ID", os.environ.get("EOS_USER_ID", "default"))
        instance = InstanceRealityModel(user_id=user_id, org_id=org_id)
        obs = InstanceObservation(
            content=outcome_text[:2000],
            domain=domain,
            confidence=confidence,
            tags=["execution_outcome"],
            metadata={"packet_id": packet_id} if packet_id else {},
        )
        obs_id = instance.record(obs)

        _audit_log("outcome_recorded", {
            "packet_id": packet_id,
            "observation_id": str(obs_id),
            "domain": domain,
        })

        return {"success": True, "observation_id": str(obs_id)}
    except Exception as e:
        logger.debug("record_outcome failed: %s", e)
        return {"success": False, "error": str(e)}


def _get_audit_entries_for_packet(packet_id: str) -> list[dict]:
    """Read audit entries for a specific packet."""
    audit_path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "audit", "operator_loop_audit.jsonl",
    )
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
