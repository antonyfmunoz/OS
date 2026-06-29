"""Cockpit execution and loop routes — persistent loops + execution substrate.

Extracted from cockpit_core_routes.py to bring it under the 3,000-line
quality gate. UMH transport layer.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request

from transports.api.cockpit_audit import emit_mutation_audit
from transports.api.governed import governed_mutation

logger = logging.getLogger(__name__)

execution_loop_router: APIRouter = APIRouter()

_get_organism_fn: Callable[[], Any] = lambda: None
_configured: bool = False


def configure(
    get_organism_fn: Callable[[], Any],
    require_operator_dep: Any,
) -> None:
    """Wire shared cockpit utilities and operator auth into the execution loop router."""
    global _get_organism_fn, _configured, execution_loop_router

    _get_organism_fn = get_organism_fn
    _configured = True

    execution_loop_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    """Construct the execution/loop router with operator auth on privileged routes."""
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    # ─── Persistent Loops ────────────────────────────────────────────────────

    def _get_loop_registry():
        from substrate.execution.loop import get_registry

        registry = get_registry()
        if not registry.list_loops():
            registry.load_definitions()
        return registry

    @r.get("/loops")
    def loop_status():
        """Status of all persistent loops."""
        try:
            return _get_loop_registry().status()
        except Exception as e:
            return {"error": str(e)}

    @r.get("/loops/stages")
    def loop_stages():
        """List available pipeline stages."""
        try:
            from substrate.execution.loop import STAGE_REGISTRY

            return {
                name: (func.__doc__ or "").strip().split("\n")[0]
                for name, func in sorted(STAGE_REGISTRY.items())
            }
        except Exception as e:
            return {"error": str(e)}

    @r.post("/loops/{loop_name}/start", dependencies=auth)
    def loop_start(loop_name: str):
        """Start a persistent loop."""
        def _do_start():
            try:
                ok = _get_loop_registry().start(loop_name)
                if ok:
                    emit_mutation_audit("loops", "start", loop_name)
                    from transports.api.cockpit_core_routes import push_mutation_event
                    if push_mutation_event is not None:
                        push_mutation_event("loops", "started", {"name": loop_name})
                return f"loop {loop_name} started={ok}", ok
            except Exception as e:
                return str(e), False

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"start loop {loop_name}",
            execute_fn=_do_start,
            source="cockpit",
            metadata={"loop_name": loop_name},
        )
        return resp.to_http_dict()

    @r.post("/loops/{loop_name}/stop", dependencies=auth)
    def loop_stop(loop_name: str):
        """Stop a persistent loop."""
        def _do_stop():
            try:
                ok = _get_loop_registry().stop(loop_name)
                if ok:
                    emit_mutation_audit("loops", "stop", loop_name)
                    from transports.api.cockpit_core_routes import push_mutation_event
                    if push_mutation_event is not None:
                        push_mutation_event("loops", "stopped", {"name": loop_name})
                return f"loop {loop_name} stopped={ok}", ok
            except Exception as e:
                return str(e), False

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"stop loop {loop_name}",
            execute_fn=_do_stop,
            source="cockpit",
            metadata={"loop_name": loop_name},
        )
        return resp.to_http_dict()

    @r.post("/loops/{loop_name}/run-once", dependencies=auth)
    def loop_run_once(loop_name: str):
        """Run a single cycle of a loop synchronously."""
        def _do_run_once():
            try:
                registry = _get_loop_registry()
                loop = registry.get(loop_name)
                if not loop:
                    return f"unknown loop: {loop_name}", False
                loop.run_once()
                return f"loop {loop_name} ran one cycle", True
            except Exception as e:
                return str(e), False

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"run loop {loop_name} once",
            execute_fn=_do_run_once,
            source="cockpit",
            metadata={"loop_name": loop_name},
        )
        return resp.to_http_dict()

    @r.post("/loops/create", dependencies=auth)
    def loop_create(payload: dict):
        """Create a new loop definition at runtime."""
        from substrate.execution.loop import STAGE_REGISTRY

        stages = payload.get("stages", [])
        unknown = [s for s in stages if s not in STAGE_REGISTRY]
        if unknown:
            return {
                "error": f"unknown stages: {unknown}",
                "available": sorted(STAGE_REGISTRY.keys()),
            }

        def _do_create():
            try:
                from substrate.execution.loop.persistent_loop import LoopDefinition
                registry = _get_loop_registry()
                defn = LoopDefinition(
                    name=payload["name"],
                    domain=payload.get("domain", "general"),
                    interval_seconds=payload.get("interval_seconds", 300),
                    stages=stages,
                    description=payload.get("description", ""),
                )
                registry.register_definition(defn)
                registry.save_definitions()
                emit_mutation_audit("loops", "create", defn.name, new_value=defn.to_dict())
                from transports.api.cockpit_core_routes import push_mutation_event
                if push_mutation_event is not None:
                    push_mutation_event("loops", "created", {"name": defn.name})
                return f"loop {defn.name} created", True
            except Exception as e:
                return str(e), False

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"create loop {payload.get('name', '')}",
            execute_fn=_do_create,
            source="cockpit",
            metadata={"loop_name": payload.get("name", "")},
        )
        return resp.to_http_dict()

    @r.delete("/loops/{loop_name}", dependencies=auth)
    def loop_delete(loop_name: str):
        """Remove a loop definition."""
        def _do_delete():
            try:
                registry = _get_loop_registry()
                ok = registry.remove(loop_name)
                if ok:
                    registry.save_definitions()
                    emit_mutation_audit("loops", "delete", loop_name)
                    from transports.api.cockpit_core_routes import push_mutation_event
                    if push_mutation_event is not None:
                        push_mutation_event("loops", "deleted", {"name": loop_name})
                return f"loop {loop_name} removed={ok}", ok
            except Exception as e:
                return str(e), False

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"delete loop {loop_name}",
            execute_fn=_do_delete,
            source="cockpit",
            metadata={"loop_name": loop_name},
        )
        return resp.to_http_dict()

    # ── Execution Substrate endpoints ────────────────────────────────────────

    @r.get("/execution/status")
    def execution_status():
        """Execution status from live organism spine and work packet engine."""
        try:
            organism = _get_organism_fn()
            spine_status = {}
            pending_count = 0
            active_count = 0
            completed_count = 0

            if organism:
                spine = getattr(organism, "spine", None)
                if spine:
                    spine_status = {
                        "mode": getattr(spine, "mode", "unknown"),
                        "guard_mode": getattr(spine, "guard_mode", "unknown"),
                    }
                pending = getattr(organism, "get_pending_envelopes", lambda: [])()
                active = getattr(organism, "get_active_envelopes", lambda: [])()
                completed_list = getattr(organism, "get_completed_envelopes", lambda: [])()
                pending_count = len(pending) if pending else 0
                active_count = len(active) if active else 0
                completed_count = len(completed_list) if completed_list else 0

            from substrate.organism.work_packet_engine import WorkPacketEngine

            wpe = WorkPacketEngine()
            packets = wpe.all_packets()
            packet_summary = {}
            for pkt in packets:
                status_val = pkt.status.value if hasattr(pkt.status, "value") else str(pkt.status)
                packet_summary[status_val] = packet_summary.get(status_val, 0) + 1

            return {
                "spine": spine_status,
                "envelopes": {
                    "pending": pending_count,
                    "active": active_count,
                    "completed": completed_count,
                },
                "work_packets": {
                    "total": len(packets),
                    "by_status": packet_summary,
                },
            }
        except Exception as e:
            logger.debug("execution_status: %s", e)
            return {
                "spine": {},
                "envelopes": {"pending": 0, "active": 0, "completed": 0},
                "work_packets": {"total": 0, "by_status": {}},
                "error": str(e),
            }

    @r.get("/execution/log")
    def execution_log(limit: int = 20):
        """Recent execution journal entries from spine."""
        try:
            organism = _get_organism_fn()
            if not organism:
                return {"log": [], "count": 0}
            journal = getattr(organism, "journal", None)
            if not journal:
                return {"log": [], "count": 0}
            recent = getattr(journal, "recent", lambda n: [])(limit)
            entries = []
            for entry in recent:
                entries.append(
                    {
                        "id": str(getattr(entry, "id", "")),
                        "event_type": str(getattr(entry, "event_type", "")),
                        "timestamp": str(getattr(entry, "timestamp", "")),
                        "envelope_id": str(getattr(entry, "envelope_id", "")),
                        "summary": str(getattr(entry, "summary", ""))[:200],
                    }
                )
            return {"log": entries, "count": len(entries)}
        except Exception as e:
            logger.debug("execution_log: %s", e)
            return {"log": [], "count": 0, "error": str(e)}

    @r.get("/execution/authority")
    def execution_authority(layer: str = "native"):
        """Authority preview using live governance engine."""
        try:
            from substrate.governance.policy_engine import PolicyEngine

            engine = PolicyEngine()
            return {
                "layer": layer,
                "authority_class": "operator",
                "safe_roots": engine.safe_roots,
                "risk_class": "LOW",
                "approval_requirement": "none"
                if layer in ("native", "container")
                else "operator_review",
            }
        except Exception as e:
            logger.debug("execution_authority: %s", e)
            return {
                "layer": layer,
                "authority_class": "operator",
                "risk_class": "LOW",
                "approval_requirement": "none",
            }

    @r.post("/execution/start", dependencies=auth)
    async def execution_start(request: Request):
        """Start execution of a work packet through the governed spine."""
        body = await request.json()
        packet_id = body.get("packet_id", "")
        if not packet_id:
            return {"ok": False, "error": "packet_id is required"}

        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.work_packet import PacketLifecycleStatus

        wpe = WorkPacketEngine()
        pkt = wpe.get_packet(packet_id)
        if not pkt:
            return {"ok": False, "error": f"Work packet {packet_id} not found"}

        if pkt.approval_gates and pkt.status != PacketLifecycleStatus.APPROVED:
            return {
                "ok": False,
                "error": "Work packet requires approval before execution",
                "status": pkt.status.value,
                "approval_gates": pkt.approval_gates,
            }

        if pkt.status not in (PacketLifecycleStatus.APPROVED, PacketLifecycleStatus.DELEGATED):
            return {
                "ok": False,
                "error": f"Cannot start execution from status '{pkt.status.value}'",
                "valid_start_statuses": ["approved", "delegated"],
            }

        def _do_start():
            nonlocal pkt
            if pkt.status == PacketLifecycleStatus.APPROVED:
                ok = wpe.update_packet_status(
                    packet_id, PacketLifecycleStatus.DELEGATED, "delegated for execution"
                )
                if ok:
                    ok = wpe.update_packet_status(
                        packet_id, PacketLifecycleStatus.EXECUTING, "execution started"
                    )
            else:
                ok = wpe.update_packet_status(
                    packet_id, PacketLifecycleStatus.EXECUTING, "execution started"
                )

            from substrate.execution.runtime.capability_router import (
                detect_capability,
                route_capability,
            )

            cap = detect_capability(pkt.user_intent or pkt.title)
            routing_result: dict[str, Any] = {
                "capability": cap.value,
                "routed": False,
                "provider": None,
                "error": None,
            }
            try:
                result = route_capability(pkt.user_intent or pkt.title)
                if result is not None:
                    routing_result["routed"] = True
                    routing_result["provider"] = result.provider_id
                else:
                    from adapters.models.model_router import call_with_fallback
                    llm_result = call_with_fallback(
                        prompt=pkt.user_intent or pkt.title,
                        system="Execute this work packet concisely.",
                        task_type="command",
                    )
                    routing_result["routed"] = bool(llm_result)
                    routing_result["provider"] = "llm_fallback" if llm_result else None
                    if not llm_result:
                        routing_result["error"] = "UNAVAILABLE"
            except Exception as exc:
                logger.debug("execution routing failed: %s", exc)
                routing_result["error"] = f"UNAVAILABLE: {exc}"

            if ok:
                emit_mutation_audit("execution", "start", packet_id, new_value=routing_result)
            return f"execution started for {packet_id}", ok

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"start execution of packet {packet_id}",
            execute_fn=_do_start,
            source="cockpit",
            metadata={"packet_id": packet_id},
        )
        return resp.to_http_dict()

    @r.post("/execution/stop", dependencies=auth, deprecated=True)
    async def execution_stop(request: Request):
        """DEPRECATED — use POST /workstation/execution/stop instead."""
        body = await request.json()
        packet_id = body.get("packet_id", "")
        if not packet_id:
            return {"ok": False, "error": "packet_id is required"}

        def _do_stop():
            from substrate.organism.work_packet_engine import WorkPacketEngine
            from substrate.organism.work_packet import PacketLifecycleStatus
            wpe = WorkPacketEngine()
            ok = wpe.update_packet_status(
                packet_id, PacketLifecycleStatus.BLOCKED, "stopped by operator"
            )
            if ok:
                emit_mutation_audit("execution", "stop", packet_id)
            return f"execution stopped for {packet_id}", ok

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"stop execution of packet {packet_id}",
            execute_fn=_do_stop,
            source="cockpit",
            metadata={"packet_id": packet_id},
        )
        return resp.to_http_dict()

    @r.post("/execution/pause", dependencies=auth, deprecated=True)
    async def execution_pause(request: Request):
        """DEPRECATED — use POST /workstation/execution/pause instead."""
        body = await request.json()
        packet_id = body.get("packet_id", "")
        if not packet_id:
            return {"ok": False, "error": "packet_id is required"}

        def _do_pause():
            from substrate.organism.work_packet_engine import WorkPacketEngine
            from substrate.organism.work_packet import PacketLifecycleStatus
            wpe = WorkPacketEngine()
            ok = wpe.update_packet_status(
                packet_id, PacketLifecycleStatus.BLOCKED, "paused by operator"
            )
            return f"execution paused for {packet_id}", ok

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"pause execution of packet {packet_id}",
            execute_fn=_do_pause,
            source="cockpit",
            metadata={"packet_id": packet_id},
        )
        return resp.to_http_dict()

    @r.post("/execution/complete", dependencies=auth)
    async def execution_complete(request: Request):
        """Mark a work packet as completed, triggering outcome recording and verification."""
        body = await request.json()
        packet_id = body.get("packet_id", "")
        if not packet_id:
            return {"ok": False, "error": "packet_id is required"}
        reason = body.get("reason", "completed by operator")

        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.work_packet import PacketLifecycleStatus

        wpe = WorkPacketEngine()
        pkt = wpe.get_packet(packet_id)
        if not pkt:
            return {"ok": False, "error": f"Work packet {packet_id} not found"}

        if pkt.status not in (PacketLifecycleStatus.EXECUTING, PacketLifecycleStatus.VALIDATING):
            return {
                "ok": False,
                "error": f"Cannot complete from status '{pkt.status.value}'",
                "valid_statuses": ["executing", "validating"],
            }

        def _do_complete():
            if pkt.status == PacketLifecycleStatus.EXECUTING:
                ok = wpe.update_packet_status(
                    packet_id, PacketLifecycleStatus.VALIDATING, "validating before completion"
                )
                if ok:
                    wpe.run_verification(packet_id)
                    refreshed = wpe.get_packet(packet_id)
                    if refreshed and refreshed.verification_passed is False:
                        wpe.update_packet_status(
                            packet_id, PacketLifecycleStatus.FAILED, "verification failed"
                        )
                        return "verification failed", False
                    ok = wpe.update_packet_status(
                        packet_id, PacketLifecycleStatus.COMPLETED, reason
                    )
            else:
                ok = wpe.update_packet_status(
                    packet_id, PacketLifecycleStatus.COMPLETED, reason
                )
            return f"packet {packet_id} completed", ok

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"complete execution of packet {packet_id}",
            execute_fn=_do_complete,
            source="cockpit",
            metadata={"packet_id": packet_id},
        )
        return resp.to_http_dict()

    @r.post("/execution/fail", dependencies=auth)
    async def execution_fail(request: Request):
        """Mark a work packet as failed, triggering failure outcome recording."""
        body = await request.json()
        packet_id = body.get("packet_id", "")
        if not packet_id:
            return {"ok": False, "error": "packet_id is required"}
        reason = body.get("reason", "failed")

        from substrate.organism.work_packet_engine import WorkPacketEngine
        from substrate.organism.work_packet import PacketLifecycleStatus

        wpe = WorkPacketEngine()
        pkt = wpe.get_packet(packet_id)
        if not pkt:
            return {"ok": False, "error": f"Work packet {packet_id} not found"}

        if pkt.status not in (
            PacketLifecycleStatus.EXECUTING,
            PacketLifecycleStatus.VALIDATING,
            PacketLifecycleStatus.DELEGATED,
        ):
            return {
                "ok": False,
                "error": f"Cannot fail from status '{pkt.status.value}'",
                "valid_statuses": ["executing", "validating", "delegated"],
            }

        def _do_fail():
            ok = wpe.update_packet_status(packet_id, PacketLifecycleStatus.FAILED, reason)
            return f"packet {packet_id} marked failed", ok

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"fail execution of packet {packet_id}: {reason[:80]}",
            execute_fn=_do_fail,
            source="cockpit",
            metadata={"packet_id": packet_id, "reason": reason},
        )
        return resp.to_http_dict()

    @r.post("/execution/resume", dependencies=auth, deprecated=True)
    async def execution_resume(request: Request):
        """DEPRECATED — use POST /workstation/execution/resume instead."""
        body = await request.json()
        packet_id = body.get("packet_id", "")
        if not packet_id:
            return {"ok": False, "error": "packet_id is required"}

        def _do_resume():
            from substrate.organism.work_packet_engine import WorkPacketEngine
            from substrate.organism.work_packet import PacketLifecycleStatus
            wpe = WorkPacketEngine()
            ok = wpe.update_packet_status(
                packet_id, PacketLifecycleStatus.CLASSIFIED, "resumed by operator"
            )
            return f"execution resumed for {packet_id}", ok

        resp = governed_mutation(
            mutation_name="state_mutate",
            intent=f"resume execution of packet {packet_id}",
            execute_fn=_do_resume,
            source="cockpit",
            metadata={"packet_id": packet_id},
        )
        return resp.to_http_dict()

    return r
