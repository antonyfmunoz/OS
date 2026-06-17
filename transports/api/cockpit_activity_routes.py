"""Cockpit Activity Routes — canonical activity/timeline capability surface.

Composes activity subsystems into a unified API for the Activity capability:
  - EventSpine (organism event stream)
  - IntentReceiptStore (operator interaction audit trail)
  - ContinuityEngine (continuity timeline)
  - RealityIntelligenceEngine (reality mutations timeline)

This is the canonical activity surface. Subsystem-specific timeline endpoints
in other route files remain mounted for backward compat.

Gate 4 — Workstation Convergence. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Query

logger = logging.getLogger(__name__)

activity_router: APIRouter = APIRouter()
_configured = False


def configure(*, require_operator_dep: Any) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    _router = _build_router(require_operator_dep)
    activity_router.include_router(_router)


def _get_event_spine() -> Any:
    if not hasattr(_get_event_spine, "_instance"):
        try:
            from substrate.organism.event_spine import EventSpine
            _get_event_spine._instance = EventSpine()
        except Exception:
            logger.debug("EventSpine unavailable")
            _get_event_spine._instance = None
    return _get_event_spine._instance


def _get_receipt_store() -> Any:
    if not hasattr(_get_receipt_store, "_instance"):
        try:
            from substrate.operator.intent_receipt import IntentReceiptStore
            _get_receipt_store._instance = IntentReceiptStore()
        except Exception:
            logger.debug("IntentReceiptStore unavailable")
            _get_receipt_store._instance = None
    return _get_receipt_store._instance


def _get_continuity_engine() -> Any:
    if not hasattr(_get_continuity_engine, "_instance"):
        try:
            from substrate.operator.continuity_runtime import ContinuityRuntime
            _get_continuity_engine._instance = ContinuityRuntime()
        except Exception:
            logger.debug("ContinuityRuntime unavailable")
            _get_continuity_engine._instance = None
    return _get_continuity_engine._instance


def _get_reality_engine() -> Any:
    if not hasattr(_get_reality_engine, "_instance"):
        try:
            from substrate.operator.reality_intelligence_engine import RealityIntelligenceEngine
            _get_reality_engine._instance = RealityIntelligenceEngine()
        except Exception:
            logger.debug("RealityIntelligenceEngine unavailable")
            _get_reality_engine._instance = None
    return _get_reality_engine._instance


def _safe_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {"value": str(obj)}


def _safe_list(items: Any) -> list[dict[str, Any]]:
    if not items:
        return []
    if not isinstance(items, (list, tuple)):
        return []
    return [_safe_dict(item) for item in items]


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    @r.get("/activity/feed", dependencies=auth)
    async def activity_feed(
        limit: int = Query(50, description="Max events"),
        since: float = Query(0, description="Unix timestamp filter"),
    ) -> dict[str, Any]:
        """Unified activity feed — organism events + receipts merged by time."""
        entries: list[dict[str, Any]] = []

        es = _get_event_spine()
        if es is not None:
            try:
                events = es.recent(limit=limit)
                for ev in events:
                    d = _safe_dict(ev)
                    d["source"] = "organism"
                    ts = d.get("timestamp", 0)
                    if isinstance(ts, (int, float)) and (since <= 0 or ts >= since):
                        entries.append(d)
            except Exception:
                logger.debug("EventSpine.recent failed")

        rs = _get_receipt_store()
        if rs is not None:
            try:
                receipts = rs.recent(limit=limit) if hasattr(rs, "recent") else []
                for rc in receipts:
                    d = _safe_dict(rc)
                    d["source"] = "operator"
                    ts = d.get("timestamp", 0)
                    if isinstance(ts, (int, float)) and (since <= 0 or ts >= since):
                        entries.append(d)
            except Exception:
                logger.debug("IntentReceiptStore.recent failed")

        entries.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        entries = entries[:limit]

        return {
            "success": True,
            "entries": entries,
            "count": len(entries),
        }

    @r.get("/activity/organism-events", dependencies=auth)
    async def organism_events(
        limit: int = Query(50, description="Max events"),
        since: float = Query(0, description="Unix timestamp filter"),
    ) -> dict[str, Any]:
        """Organism event stream from EventSpine."""
        es = _get_event_spine()
        if es is None:
            return {"success": True, "events": [], "count": 0}
        try:
            events = es.recent(limit=limit)
            result = _safe_list(events)
            if since > 0:
                result = [e for e in result if e.get("timestamp", 0) >= since]
            return {"success": True, "events": result, "count": len(result)}
        except Exception:
            logger.debug("EventSpine.recent failed")
            return {"success": True, "events": [], "count": 0}

    @r.get("/activity/receipts", dependencies=auth)
    async def operator_receipts(
        limit: int = Query(50, description="Max receipts"),
    ) -> dict[str, Any]:
        """Operator interaction audit trail from IntentReceiptStore."""
        rs = _get_receipt_store()
        if rs is None:
            return {"success": True, "receipts": [], "count": 0}
        try:
            receipts = rs.recent(limit=limit) if hasattr(rs, "recent") else []
            result = _safe_list(receipts)
            return {"success": True, "receipts": result, "count": len(result)}
        except Exception:
            logger.debug("IntentReceiptStore.recent failed")
            return {"success": True, "receipts": [], "count": 0}

    @r.get("/activity/continuity", dependencies=auth)
    async def continuity_timeline(
        limit: int = Query(20, description="Max entries"),
    ) -> dict[str, Any]:
        """Continuity checkpoints — session transitions, state saves."""
        ce = _get_continuity_engine()
        if ce is None:
            return {"success": True, "checkpoints": [], "count": 0}
        try:
            if hasattr(ce, "checkpoints"):
                checkpoints = ce.checkpoints(limit=limit)
            elif hasattr(ce, "recent_checkpoints"):
                checkpoints = ce.recent_checkpoints(limit=limit)
            else:
                checkpoints = []
            result = _safe_list(checkpoints)
            return {"success": True, "checkpoints": result, "count": len(result)}
        except Exception:
            logger.debug("ContinuityRuntime checkpoints failed")
            return {"success": True, "checkpoints": [], "count": 0}

    @r.get("/activity/reality-changes", dependencies=auth)
    async def reality_changes(
        limit: int = Query(20, description="Max changes"),
        since: float = Query(0, description="Unix timestamp filter"),
    ) -> dict[str, Any]:
        """Reality model mutations — what changed in the world model."""
        re = _get_reality_engine()
        if re is None:
            return {"success": True, "changes": [], "count": 0}
        try:
            if hasattr(re, "recent_mutations"):
                changes = re.recent_mutations(limit=limit)
            elif hasattr(re, "query"):
                changes = re.query("recent_changes", limit=limit)
            else:
                changes = []
            result = _safe_list(changes)
            if since > 0:
                result = [c for c in result if c.get("timestamp", 0) >= since]
            return {"success": True, "changes": result, "count": len(result)}
        except Exception:
            logger.debug("RealityIntelligenceEngine changes failed")
            return {"success": True, "changes": [], "count": 0}

    return r
