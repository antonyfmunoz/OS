"""
Station drainer — EOS-side ingestion seam for inbox messages.

Completes two round-trip loops:

    1) EVENTS
       Station Daemon
         → StationBus.daemon_post_event(...)
         → [inbox file]
         → drain_events() (this module)
         → StationContract.record_event(...)
         → EventBus.publish_async("station.<event_type>", ...)

    2) RESULTS
       EOS proposes SafeAction
         → StationBus outbox
         → StationDaemon executes
         → StationBus.daemon_post_result(...)
         → [inbox file]
         → drain_results() (this module)
         → ResultStore.put(IngestedResult)
         → visible to rituals via ritual_reconciler.reconcile_*

`drain_all()` reads the inbox exactly once and routes each message to the
appropriate sink — use it in operator paths so events and results stay in
lockstep and the inbox is never double-read.

Design rules:
  - Tiny, additive, best-effort. Never raises on malformed input.
  - No scheduling, no daemon management. Callers decide cadence.
  - Dedup is implicit: StationBus.drain_inbox() atomically clears on read.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

from runtime.transport.result_store import (
    IngestedResult,
    ResultStore,
    get_result_store,
)
from runtime.transport.station import StationContract, StationEvent
from runtime.transport.station_bus import StationBus, get_station_bus


def _log(msg: str) -> None:
    print(f"[substrate.station_drainer] {msg}", file=sys.stderr)


# ─── Stats dataclasses ───────────────────────────────────────────────────────

@dataclass
class DrainStats:
    """Event drain counters."""
    node_id: str
    drained: int = 0
    skipped: int = 0
    malformed: int = 0
    errors: int = 0
    event_types: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResultDrainStats:
    """Result drain counters, broken down by terminal status."""
    node_id: str
    drained: int = 0                # total results stored
    malformed: int = 0
    errors: int = 0
    succeeded: int = 0
    failed: int = 0
    rejected: int = 0
    other: int = 0                  # any non-terminal status values
    fallbacks: int = 0              # results whose data flagged fallback/dry_run
    by_kind: dict[str, int] = field(default_factory=dict)
    without_kind: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class DrainAllStats:
    node_id: str
    events: DrainStats
    results: ResultDrainStats

    def as_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "events": self.events.as_dict(),
            "results": self.results.as_dict(),
        }


# ─── Validation helpers ──────────────────────────────────────────────────────

_REQUIRED_EVENT_FIELDS = ("node_id", "event_type")
_REQUIRED_RESULT_FIELDS = ("action_id", "status")


def _hydrate_event(payload: dict, expected_node: str) -> Optional[StationEvent]:
    if not isinstance(payload, dict):
        return None
    for k in _REQUIRED_EVENT_FIELDS:
        if not payload.get(k):
            return None
    if payload["node_id"] != expected_node:
        return None
    inner_payload = payload.get("payload") or {}
    if not isinstance(inner_payload, dict):
        return None
    try:
        evt = StationEvent(
            node_id=payload["node_id"],
            event_type=str(payload["event_type"]),
            payload=inner_payload,
        )
        occurred_at = payload.get("occurred_at")
        if occurred_at:
            evt.occurred_at = str(occurred_at)
        return evt
    except Exception:
        return None


def _hydrate_result(payload: dict, node_id: str) -> Optional[IngestedResult]:
    if not isinstance(payload, dict):
        return None
    for k in _REQUIRED_RESULT_FIELDS:
        if not payload.get(k):
            return None
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    # kind is best-effort: daemons that post it stamp either the top-level
    # payload or data["kind"]. Older daemons stamp neither — that's fine.
    kind = payload.get("kind") or data.get("kind")
    try:
        return IngestedResult(
            action_id=str(payload["action_id"]),
            node_id=node_id,
            status=str(payload["status"]),
            detail=payload.get("detail"),
            returned_at=payload.get("returned_at"),
            data=data,
            kind=str(kind) if kind else None,
        )
    except Exception:
        return None


# ─── Public API ──────────────────────────────────────────────────────────────

def drain_node(
    node_id: str,
    *,
    contract: Optional[StationContract] = None,
    bus: Optional[StationBus] = None,
) -> DrainStats:
    """
    EVENT-ONLY drain. Kept for backwards compatibility with the earlier
    drainer pass. Reads the inbox, ingests events, skips results.

    For a full drain (events + results) prefer `drain_all()` — it reads
    the inbox only once and updates both sinks atomically.
    """
    b = bus or get_station_bus()
    try:
        messages = b.drain_inbox(node_id)
    except Exception as e:
        _log(f"{node_id}: drain_inbox failed: {e}")
        return DrainStats(node_id=node_id)
    return _ingest_events(
        node_id,
        [m for m in messages if isinstance(m, dict) and m.get("type") == "event"],
        contract=contract,
        skipped_other=sum(
            1 for m in messages if isinstance(m, dict) and m.get("type") != "event"
        ),
    )


def drain_results(
    node_id: str,
    *,
    store: Optional[ResultStore] = None,
    bus: Optional[StationBus] = None,
) -> ResultDrainStats:
    """
    RESULT-ONLY drain. Reads the inbox, ingests result entries, skips events.

    Prefer `drain_all()` in operator paths so events and results cannot
    race each other across two drain_inbox() calls.
    """
    b = bus or get_station_bus()
    try:
        messages = b.drain_inbox(node_id)
    except Exception as e:
        _log(f"{node_id}: drain_inbox failed: {e}")
        return ResultDrainStats(node_id=node_id)
    return _ingest_results(
        node_id,
        [m for m in messages if isinstance(m, dict) and m.get("type") == "result"],
        store=store,
    )


def drain_all(
    node_id: str,
    *,
    contract: Optional[StationContract] = None,
    store: Optional[ResultStore] = None,
    bus: Optional[StationBus] = None,
) -> DrainAllStats:
    """
    Unified drain: one inbox read, both sinks populated.

    Use this in operator/loop contexts so event and result ingestion stay
    in lockstep. A single drain_inbox() call atomically clears everything,
    so there is no window where events and results can diverge.
    """
    b = bus or get_station_bus()
    try:
        messages = b.drain_inbox(node_id)
    except Exception as e:
        _log(f"{node_id}: drain_inbox failed: {e}")
        return DrainAllStats(
            node_id=node_id,
            events=DrainStats(node_id=node_id),
            results=ResultDrainStats(node_id=node_id),
        )

    event_msgs: list[dict] = []
    result_msgs: list[dict] = []
    other = 0
    for m in messages:
        if not isinstance(m, dict):
            other += 1
            continue
        t = m.get("type")
        if t == "event":
            event_msgs.append(m)
        elif t == "result":
            result_msgs.append(m)
        else:
            other += 1

    ev_stats = _ingest_events(
        node_id, event_msgs, contract=contract, skipped_other=other
    )
    rs_stats = _ingest_results(node_id, result_msgs, store=store)
    return DrainAllStats(node_id=node_id, events=ev_stats, results=rs_stats)


def drain_nodes(node_ids: list[str]) -> list[DrainAllStats]:
    """Drain multiple nodes via `drain_all`. Errors on one never block others."""
    out: list[DrainAllStats] = []
    for nid in node_ids:
        try:
            out.append(drain_all(nid))
        except Exception as e:
            _log(f"{nid}: unexpected drain failure: {e}")
            out.append(
                DrainAllStats(
                    node_id=nid,
                    events=DrainStats(node_id=nid, errors=1),
                    results=ResultDrainStats(node_id=nid, errors=1),
                )
            )
    return out


# ─── Internal ingestion ──────────────────────────────────────────────────────

def _ingest_events(
    node_id: str,
    event_msgs: list[dict],
    *,
    contract: Optional[StationContract],
    skipped_other: int,
) -> DrainStats:
    stats = DrainStats(node_id=node_id, skipped=skipped_other)
    c = contract or StationContract(node_id=node_id)

    for msg in event_msgs:
        evt = _hydrate_event(msg.get("payload") or {}, expected_node=node_id)
        if evt is None:
            stats.malformed += 1
            _log(f"{node_id}: malformed event payload: {msg.get('payload')!r}")
            continue
        try:
            c.record_event(evt)
        except Exception as e:
            stats.errors += 1
            _log(f"{node_id}: record_event raised on {evt.event_type}: {e}")
            continue
        stats.drained += 1
        stats.event_types[evt.event_type] = stats.event_types.get(evt.event_type, 0) + 1
    return stats


def _ingest_results(
    node_id: str,
    result_msgs: list[dict],
    *,
    store: Optional[ResultStore],
) -> ResultDrainStats:
    stats = ResultDrainStats(node_id=node_id)
    s = store or get_result_store()

    for msg in result_msgs:
        ir = _hydrate_result(msg.get("payload") or {}, node_id=node_id)
        if ir is None:
            stats.malformed += 1
            _log(f"{node_id}: malformed result payload: {msg.get('payload')!r}")
            continue
        try:
            s.put(ir)
        except Exception as e:
            stats.errors += 1
            _log(f"{node_id}: result_store.put raised: {e}")
            continue

        stats.drained += 1
        status = (ir.status or "").lower()
        if status == "succeeded":
            stats.succeeded += 1
        elif status == "failed":
            stats.failed += 1
        elif status == "rejected":
            stats.rejected += 1
        else:
            stats.other += 1
        if ir.is_fallback:
            stats.fallbacks += 1
        if ir.kind:
            stats.by_kind[ir.kind] = stats.by_kind.get(ir.kind, 0) + 1
        else:
            stats.without_kind += 1
    return stats
