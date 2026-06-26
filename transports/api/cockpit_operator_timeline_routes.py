"""Cockpit operator timeline routes — unified chronological activity view.

Merges IntentReceipts, EventSpine events, governance decisions, work packet
statuses, and memory writes into a single chronological timeline.

Mounted under /api/umh/ via include_router in cockpit.py.

Phase 18. UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, Query, Request

logger = logging.getLogger(__name__)

operator_timeline_router: APIRouter = APIRouter()

_configured: bool = False


def configure(require_operator_dep: Any) -> None:
    global _configured, operator_timeline_router
    _configured = True
    operator_timeline_router = _build_router(require_operator_dep)


def _build_router(require_operator_dep: Any) -> APIRouter:
    r = APIRouter()
    auth = [Depends(require_operator_dep)]

    r.add_api_route(
        "/operator/timeline", _timeline, methods=["GET"], dependencies=auth,
    )
    r.add_api_route(
        "/operator/timeline/receipt/{receipt_id}",
        _receipt_detail,
        methods=["GET"],
        dependencies=auth,
    )

    return r


def _build_timeline_entry(
    entry_id: str,
    entry_type: str,
    timestamp: float,
    summary: str,
    details: dict[str, Any],
    intent_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    return {
        "entry_id": entry_id,
        "entry_type": entry_type,
        "timestamp": timestamp,
        "summary": summary,
        "details": details,
        "intent_id": intent_id,
        "correlation_id": correlation_id,
    }


def _timeline(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    since: float | None = Query(default=None),
    route_type: str | None = Query(default=None),
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []

    try:
        from substrate.operator.intent_receipt import IntentReceiptStore
        store = IntentReceiptStore()
        receipts = store.query_recent(limit=limit)

        if route_type:
            receipts = [r for r in receipts if r.route_type == route_type]
        if since:
            receipts = [r for r in receipts if r.created_at >= since]

        for r in receipts:
            entries.append(_build_timeline_entry(
                entry_id=r.intent_id,
                entry_type="intent_receipt",
                timestamp=r.created_at,
                summary=f"[{r.route_type}] {r.raw_input[:120]}",
                details=r.to_dict(),
                intent_id=r.intent_id,
                correlation_id=r.intent_id,
            ))

            if r.work_packet_id:
                try:
                    from substrate.organism.universal_work_queue import UniversalWorkQueue
                    q = UniversalWorkQueue()
                    packets = [p for p in q.rank_packets() if p.packet_id == r.work_packet_id]
                    if packets:
                        pkt = packets[0]
                        entries.append(_build_timeline_entry(
                            entry_id=f"wp-{pkt.packet_id}",
                            entry_type="work_packet",
                            timestamp=pkt.updated_at or pkt.created_at,
                            summary=f"WorkPacket: {pkt.title or pkt.user_intent[:80]} [{pkt.status.value}]",
                            details=pkt.to_safe_dict() if hasattr(pkt, "to_safe_dict") else {"packet_id": pkt.packet_id, "status": pkt.status.value},
                            intent_id=r.intent_id,
                            correlation_id=r.intent_id,
                        ))
                except Exception:
                    pass
    except Exception as exc:
        logger.debug("Timeline: receipt load failed: %s", exc)

    try:
        from substrate.organism.event_spine import EventDomain, EventSpine
        spine = EventSpine()
        if since is not None:
            events = spine.replay(domains={EventDomain.OPERATOR}, since=since)
        else:
            events = spine.recent(limit=limit)
            events = [e for e in events if e.domain == EventDomain.OPERATOR]

        for ev in events[-limit:]:
            entries.append(_build_timeline_entry(
                entry_id=ev.event_id,
                entry_type="event",
                timestamp=ev.timestamp,
                summary=f"Event: {ev.event_type}",
                details=ev.to_dict(),
                intent_id=ev.correlation_id,
                correlation_id=ev.correlation_id,
            ))
    except Exception as exc:
        logger.debug("Timeline: event load failed: %s", exc)

    entries.sort(key=lambda e: e["timestamp"], reverse=True)
    entries = entries[:limit]

    return {"timeline": entries, "total": len(entries)}


def _receipt_detail(
    request: Request,
    receipt_id: str,
) -> dict[str, Any]:
    try:
        from substrate.operator.intent_receipt import IntentReceiptStore
        store = IntentReceiptStore()
        receipt = store.get(receipt_id)
        if receipt:
            return {"receipt": receipt.to_dict(), "found": True}
    except Exception as exc:
        logger.debug("Receipt detail failed: %s", exc)

    return {"receipt": None, "found": False}
