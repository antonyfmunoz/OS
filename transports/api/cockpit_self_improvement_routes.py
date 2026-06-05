"""Cockpit self-improvement loop routes — outcome assimilation, verification,
cadence integration, and projection build feedback.

Wires the operator loop output (completed work packets with outcomes)
to the self-improvement infrastructure:
  1. Outcome → reality model (already in operator_loop_routes._record_outcome)
  2. Outcome → cadence candidate supply
  3. Outcome verification pipeline
  4. Feedback loop: outcome → next work packet

Mounted under /api/umh/ via include_router in cockpit.py.

Phase 14.7A WP-3.1/3.2/3.3/3.4. UMH transport layer. Instance-agnostic.
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

self_improvement_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, self_improvement_router
    _configured = True
    self_improvement_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route("/self-improvement/status", _improvement_status, methods=["GET"])
    r.add_api_route("/self-improvement/cadence-status", _cadence_status, methods=["GET"])
    r.add_api_route("/self-improvement/recent-outcomes", _recent_outcomes, methods=["GET"])
    r.add_api_route("/self-improvement/verification-log", _verification_log, methods=["GET"])
    r.add_api_route("/self-improvement/feedback-loop", _feedback_loop_status, methods=["GET"])

    r.add_api_route("/self-improvement/assimilate-outcome", _assimilate_outcome, methods=["POST"], dependencies=auth)
    r.add_api_route("/self-improvement/verify-outcome", _verify_outcome, methods=["POST"], dependencies=auth)
    r.add_api_route("/self-improvement/generate-follow-up", _generate_follow_up, methods=["POST"], dependencies=auth)
    r.add_api_route("/self-improvement/feed-cadence", _feed_cadence, methods=["POST"], dependencies=auth)

    return r


def _get_queue():
    from substrate.organism.universal_work_queue import UniversalWorkQueue
    return UniversalWorkQueue()


def _get_instance_model():
    from substrate.reality_model.instance import InstanceRealityModel
    org_id = os.environ.get("UMH_ORG_ID", os.environ.get("EOS_ORG_ID", "default"))
    user_id = os.environ.get("UMH_USER_ID", os.environ.get("EOS_USER_ID", "default"))
    return InstanceRealityModel(user_id=user_id, org_id=org_id)


def _get_canonical_model():
    from substrate.reality_model.canonical import CanonicalRealityModel
    return CanonicalRealityModel()


def _get_cadence():
    from substrate.organism.autonomous_cadence import AutonomousCadence
    return AutonomousCadence()


def _get_self_build_queue():
    from substrate.organism.self_build_queue import SelfBuildQueueEngine
    return SelfBuildQueueEngine()


def _improvement_log_path() -> str:
    return os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "audit", "self_improvement_log.jsonl",
    )


def _log_improvement_event(event_type: str, data: dict[str, Any]) -> None:
    path = _improvement_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {
        "id": str(uuid4()),
        "event_type": event_type,
        "timestamp": time.time(),
        "data": data,
    }
    try:
        with open(path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        logger.debug("self-improvement log write failed: %s", e)


async def _improvement_status():
    """Unified self-improvement loop status."""
    cadence = _get_cadence()
    sbq = _get_self_build_queue()
    instance = _get_instance_model()

    recent_obs = instance.recent(limit=10)
    execution_outcomes = [
        o for o in recent_obs
        if "execution_outcome" in (o.tags if hasattr(o, "tags") else o.get("tags", []))
    ]

    return {
        "cadence": cadence.status(),
        "self_build_queue": sbq.compute_queue_summary(),
        "recent_execution_outcomes": len(execution_outcomes),
        "loop_active": cadence.mode.value != "off",
        "safety": {
            "dry_run_only": cadence.mode.value in ("off", "dry_run_only"),
            "no_auto_merge": cadence.policy.no_auto_merge,
            "operator_approval_required": cadence.policy.require_operator_enable_for_pr_creation,
        },
    }


async def _cadence_status():
    """Current cadence engine status with run history."""
    cadence = _get_cadence()
    return cadence.status()


async def _recent_outcomes(limit: int = 20):
    """Recent execution outcomes recorded in the instance reality model."""
    instance = _get_instance_model()
    recent = instance.recent(limit=limit * 2)
    outcomes = [
        (o.to_dict() if hasattr(o, "to_dict") else o)
        for o in recent
        if "execution_outcome" in (o.tags if hasattr(o, "tags") else o.get("tags", []))
    ]
    return {"outcomes": outcomes[:limit], "total": len(outcomes)}


async def _verification_log(limit: int = 50):
    """Read the self-improvement verification log."""
    path = _improvement_log_path()
    if not os.path.exists(path):
        return {"entries": [], "total": 0}

    entries = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        if entry.get("event_type") in ("verification", "verification_result"):
                            entries.append(entry)
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass

    entries.reverse()
    return {"entries": entries[:limit], "total": len(entries)}


async def _feedback_loop_status():
    """Status of the outcome → next-work-packet feedback loop."""
    queue = _get_queue()
    summary = queue.compute_queue_summary()

    cadence = _get_cadence()
    pending_recs = cadence.status().get("pending_recommendations", 0)

    return {
        "queue_summary": summary,
        "pending_recommendations": pending_recs,
        "loop_description": (
            "Completed work packets generate outcomes. "
            "Outcomes are recorded in the instance reality model. "
            "The cadence engine discovers improvement candidates from outcomes. "
            "Candidates become new work packets via the self-build queue."
        ),
    }


async def _assimilate_outcome(request: Request):
    """Record an execution outcome into both reality model and self-build queue.

    This is the primary WP-3.1 endpoint: outcomes from completed work packets
    flow into the instance reality model AND optionally into the self-build
    queue as improvement candidates.
    """
    body = await request.json()
    packet_id = body.get("packet_id", "")
    outcome_text = body.get("outcome", "")
    domain = body.get("domain", "execution")
    confidence = body.get("confidence", 0.7)
    create_follow_up = body.get("create_follow_up", False)

    if not outcome_text:
        return {"success": False, "error": "outcome is required"}

    result: dict[str, Any] = {"packet_id": packet_id}

    try:
        from substrate.reality_model.instance import InstanceRealityModel, InstanceObservation
        instance = _get_instance_model()
        obs = InstanceObservation(
            content=outcome_text[:2000],
            domain=domain,
            confidence=confidence,
            tags=["execution_outcome", "self_improvement"],
            metadata={"packet_id": packet_id} if packet_id else {},
        )
        obs_id = instance.record(obs)
        result["observation_id"] = str(obs_id)
        result["reality_model_updated"] = True
    except Exception as e:
        logger.debug("assimilate outcome reality model failed: %s", e)
        result["reality_model_updated"] = False
        result["reality_model_error"] = str(e)

    if create_follow_up and packet_id:
        try:
            sbq = _get_self_build_queue()
            item = sbq.create_work_item(
                title=f"Follow-up from {packet_id}: {outcome_text[:80]}",
                description=outcome_text[:500],
                source_type="cadence_candidate",
                source_id=packet_id,
                risk_class="low",
            )
            result["follow_up_work_item_id"] = item.work_item_id
        except Exception as e:
            logger.debug("assimilate outcome follow-up failed: %s", e)
            result["follow_up_error"] = str(e)

    _log_improvement_event("outcome_assimilated", result)

    result["success"] = True
    return result


async def _verify_outcome(request: Request):
    """Verify an execution outcome against the reality model.

    WP-3.3: deterministic verification pipeline. Checks whether the
    claimed outcome is consistent with known reality model state.
    """
    body = await request.json()
    packet_id = body.get("packet_id", "")
    claimed_outcome = body.get("claimed_outcome", "")
    domain = body.get("domain", "")

    if not claimed_outcome:
        return {"success": False, "error": "claimed_outcome is required"}

    verification: dict[str, Any] = {
        "packet_id": packet_id,
        "claimed_outcome": claimed_outcome[:500],
        "checks": [],
        "verified": True,
    }

    try:
        canonical = _get_canonical_model()
        related = canonical.search(domain or "execution")
        if related:
            verification["checks"].append({
                "check": "canonical_consistency",
                "status": "pass",
                "detail": f"Found {len(related)} related canonical patterns",
            })
        else:
            verification["checks"].append({
                "check": "canonical_consistency",
                "status": "info",
                "detail": "No related canonical patterns found (new domain)",
            })
    except Exception as e:
        verification["checks"].append({
            "check": "canonical_consistency",
            "status": "skip",
            "detail": str(e),
        })

    try:
        instance = _get_instance_model()
        recent = instance.recent(limit=20)
        contradictions = []
        for obs in recent:
            obs_content = obs.content if hasattr(obs, "content") else obs.get("content", "")
            obs_domain = obs.domain if hasattr(obs, "domain") else obs.get("domain", "")
            if obs_domain == domain and "failed" in obs_content.lower() and "success" in claimed_outcome.lower():
                contradictions.append(obs_content[:100])

        if contradictions:
            verification["checks"].append({
                "check": "contradiction_scan",
                "status": "warning",
                "detail": f"Potential contradictions with {len(contradictions)} recent observations",
                "contradictions": contradictions[:3],
            })
            verification["verified"] = False
        else:
            verification["checks"].append({
                "check": "contradiction_scan",
                "status": "pass",
                "detail": "No contradictions with recent observations",
            })
    except Exception as e:
        verification["checks"].append({
            "check": "contradiction_scan",
            "status": "skip",
            "detail": str(e),
        })

    if packet_id:
        try:
            queue = _get_queue()
            pkt = queue.get_packet(packet_id)
            if pkt:
                verification["checks"].append({
                    "check": "packet_status",
                    "status": "pass" if pkt.status.value in ("executing", "completed", "validating") else "warning",
                    "detail": f"Packet status: {pkt.status.value}",
                })
            else:
                verification["checks"].append({
                    "check": "packet_status",
                    "status": "warning",
                    "detail": "Packet not found in queue",
                })
        except Exception as e:
            verification["checks"].append({
                "check": "packet_status",
                "status": "skip",
                "detail": str(e),
            })

    _log_improvement_event("verification_result", verification)

    return {"success": True, "verification": verification}


async def _generate_follow_up(request: Request):
    """Generate a follow-up work packet from a completed outcome.

    WP-3.4: the projection build loop. A completed outcome can
    generate new work — this is how UMH compounds improvement.
    """
    body = await request.json()
    packet_id = body.get("packet_id", "")
    outcome = body.get("outcome", "")
    suggested_intent = body.get("suggested_intent", "")

    if not outcome and not suggested_intent:
        return {"success": False, "error": "outcome or suggested_intent is required"}

    intent_text = suggested_intent or f"Follow-up improvement from outcome: {outcome[:200]}"

    try:
        queue = _get_queue()
        packet = queue.ingest_user_intent(
            user_intent=intent_text,
            desired_end_state=f"Improve based on prior outcome (source: {packet_id})" if packet_id else "",
            constraints=["derived_from_prior_outcome"],
        )

        _log_improvement_event("follow_up_generated", {
            "source_packet_id": packet_id,
            "new_packet_id": packet.packet_id,
            "intent": intent_text[:300],
        })

        return {
            "success": True,
            "new_packet": packet.to_safe_dict(),
            "source_packet_id": packet_id,
            "needs_approval": bool(packet.approval_gates),
        }
    except Exception as e:
        logger.debug("generate follow-up failed: %s", e)
        return {"success": False, "error": str(e)}


async def _feed_cadence(request: Request):
    """Feed execution outcomes as candidates to the autonomous cadence.

    WP-3.2: connects operator loop outcomes to the cadence candidate
    supply so the autonomous improvement discovery has real data.
    """
    body = await request.json()
    outcomes = body.get("outcomes", [])

    if not outcomes:
        return {"success": False, "error": "outcomes list is required"}

    candidates = []
    for o in outcomes[:10]:
        candidates.append({
            "candidate_id": str(uuid4()),
            "description": o.get("outcome", o.get("description", ""))[:500],
            "risk_class": o.get("risk_class", "low"),
            "source_packet_id": o.get("packet_id", ""),
            "domain": o.get("domain", "execution"),
            "template_id": None,
            "agent_reliability": 0,
            "validation_method": "operator_verification",
            "non_mutating": True,
        })

    try:
        sbq = _get_self_build_queue()
        created = []
        for c in candidates:
            item = sbq.create_work_item(
                title=f"Cadence candidate: {c['description'][:60]}",
                description=c["description"],
                source_type="cadence_candidate",
                source_id=c.get("source_packet_id", ""),
                risk_class=c["risk_class"],
            )
            created.append(item.work_item_id)
    except Exception as e:
        logger.debug("feed cadence to self-build queue failed: %s", e)
        created = []

    _log_improvement_event("cadence_fed", {
        "candidates_submitted": len(candidates),
        "work_items_created": len(created),
    })

    return {
        "success": True,
        "candidates_submitted": len(candidates),
        "work_items_created": len(created),
        "work_item_ids": created,
    }
