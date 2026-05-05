"""
Operator Interface Layer v1.

A deterministic, bounded, read-first query + command surface over
linkage_snapshot(). This layer turns "structured intelligence exposed"
into "human operator can query, filter, and act on it".

Design rules (non-negotiable):
    * No hot-path edits. No background loops. No external I/O.
    * All queries are pure transforms over linkage_snapshot().
    * All commands are explicit, bounded, and operate only on the
      in-memory MeetingSummaryStore that already backs linkage_snapshot.
    * Never raises. Always returns JSON-friendly data.

Hot-path files (gateway, cognitive_loop, model_router, agent_runtime,
primitives) are not touched.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Iterable, Optional

from eos_ai.substrate import meeting_intelligence as mi

LAYER_NAME = "operator_interface"
LAYER_VERSION = "v1"

_PRIO_RANK = {"low": 0, "medium": 1, "high": 2}

_VALID_READINESS = {
    "ready",
    "blocked_missing_owner",
    "blocked_ambiguous",
    "blocked_low_context",
}
_VALID_PRIORITIES = {"low", "medium", "high"}


# ─── Internal helpers ────────────────────────────────────────────────────────


def _safe_snapshot(
    node_id: str, meeting_id: Optional[str]
) -> dict[str, Any]:
    """linkage_snapshot is already safe-degrading, but guard again anyway."""
    try:
        return mi.linkage_snapshot(node_id or "", meeting_id)
    except Exception:  # noqa: BLE001
        return mi._empty_linkage_snapshot(node_id or "", meeting_id)


def _items(snap: dict[str, Any]) -> list[dict[str, Any]]:
    actionable = snap.get("actionable") or {}
    items = actionable.get("items") or []
    return [dict(it) for it in items if isinstance(it, dict)]


def _match(item: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if expected is None:
            continue
        if key == "execution_ready":
            if bool(item.get("execution_ready", False)) != bool(expected):
                return False
        elif key == "readiness_state":
            if str(item.get("readiness_state") or "") != str(expected):
                return False
        elif key == "owner":
            if (item.get("owner") or "") != expected:
                return False
        elif key == "priority":
            if str(item.get("priority") or "low") != str(expected):
                return False
        else:
            if item.get(key) != expected:
                return False
    return True


# ─── Query layer (pure, read-only) ───────────────────────────────────────────


def get_actionable_items(
    node_id: str,
    meeting_id: Optional[str] = None,
    *,
    filters: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Return actionable items for (node_id, meeting_id), optionally filtered.

    Supported filter keys:
        readiness_state : str in _VALID_READINESS
        owner           : str  (exact match)
        priority        : str in _VALID_PRIORITIES
        execution_ready : bool
    """
    snap = _safe_snapshot(node_id, meeting_id)
    items = _items(snap)
    if not filters:
        return items
    return [it for it in items if _match(it, filters)]


def get_top_actionable(
    node_id: str, meeting_id: Optional[str] = None
) -> Optional[dict[str, Any]]:
    """
    Return highest-priority actionable. Ties broken by readiness
    (ready > blocked) then by original snapshot order (stable).
    """
    snap = _safe_snapshot(node_id, meeting_id)
    items = _items(snap)
    if not items:
        # fall back to snapshot's own pick (may be None)
        return (snap.get("actionable") or {}).get("highest_priority_actionable")

    def _key(it: dict[str, Any]) -> tuple[int, int]:
        prio = _PRIO_RANK.get(str(it.get("priority") or "low"), 0)
        ready_bonus = 1 if it.get("execution_ready") else 0
        return (prio, ready_bonus)

    return max(items, key=_key)


def get_blocked_items(
    node_id: str, meeting_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Return actionable items whose readiness_state is not 'ready'."""
    return [
        it
        for it in get_actionable_items(node_id, meeting_id)
        if str(it.get("readiness_state") or "") != "ready"
    ]


def get_ready_items(
    node_id: str, meeting_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """Return actionable items that are execution-ready."""
    return [
        it
        for it in get_actionable_items(node_id, meeting_id)
        if bool(it.get("execution_ready"))
        or str(it.get("readiness_state") or "") == "ready"
    ]


def get_owner_breakdown(
    node_id: str, meeting_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Return ownership distribution across actionable items.

    Shape:
        {
          "counts": {owner: count, ...},
          "unassigned": int,
          "top_owner": str | None,
          "total": int,
        }
    """
    items = get_actionable_items(node_id, meeting_id)
    counts: dict[str, int] = {}
    unassigned = 0
    for it in items:
        owner = it.get("owner")
        if not owner:
            unassigned += 1
            continue
        counts[owner] = counts.get(owner, 0) + 1
    top_owner: Optional[str] = None
    if counts:
        top_owner = max(counts.items(), key=lambda kv: kv[1])[0]
    return {
        "counts": counts,
        "unassigned": unassigned,
        "top_owner": top_owner,
        "total": len(items),
    }


def summarize(
    node_id: str, meeting_id: Optional[str] = None
) -> dict[str, Any]:
    """
    High-level operator summary — a trimmed projection over the snapshot.
    """
    snap = _safe_snapshot(node_id, meeting_id)
    actionable = snap.get("actionable") or {}
    return {
        "schema_version": snap.get("schema_version"),
        "node_id": snap.get("node_id"),
        "meeting_id": snap.get("meeting_id"),
        "generated_at": snap.get("generated_at"),
        "priority_level": (snap.get("summary") or {}).get("priority_level"),
        "commitments_count": (snap.get("execution") or {}).get(
            "commitments_count", 0
        ),
        "unresolved_commitments_count": (snap.get("execution") or {}).get(
            "unresolved_commitments_count", 0
        ),
        "completion_rate": (snap.get("execution") or {}).get(
            "completion_rate", 0.0
        ),
        "actionable_count": actionable.get("count", 0),
        "ready_count": actionable.get("ready_count", 0),
        "blocked_count": actionable.get("blocked_count", 0),
        "readiness_summary": actionable.get("readiness_summary") or {},
        "top_owner": (snap.get("coordination") or {}).get("top_owner"),
        "temporal_health": (snap.get("temporal") or {}).get(
            "temporal_health", "fresh"
        ),
    }


# ─── Action commands (explicit, bounded, no automation) ─────────────────────


def _get_summary(
    node_id: str, meeting_id: str
) -> Optional["mi.MeetingSummary"]:
    try:
        return mi.get_meeting_summary_store().get(node_id, meeting_id)
    except Exception:  # noqa: BLE001
        return None


def mark_resolved(
    node_id: str,
    meeting_id: str,
    *,
    text_contains: Optional[str] = None,
    owner: Optional[str] = None,
) -> dict[str, Any]:
    """
    Operator-triggered resolution of commitments on a meeting summary.

    Two modes:
        1. No selector (text_contains=None, owner=None) — delegate to
           meeting_intelligence.resolve_commitments (phrase-based).
        2. Selector provided — mark matching, still-unresolved commitments
           as resolved in-place (bounded, explicit).

    Returns {"resolved": [ ... ], "count": int}. Never raises.
    """
    out: dict[str, Any] = {"resolved": [], "count": 0}
    if not node_id or not meeting_id:
        return out
    summary = _get_summary(node_id, meeting_id)
    if summary is None:
        return out

    try:
        if text_contains is None and owner is None:
            # Delegate to existing phrase-based resolver. Safe on empty.
            try:
                resolved = mi.resolve_commitments(summary, [])
            except Exception:  # noqa: BLE001
                resolved = []
            out["resolved"] = list(resolved or [])
            out["count"] = len(out["resolved"])
            return out

        needle = (text_contains or "").strip().lower()
        now = time.time()
        commitments = getattr(summary, "commitments", None) or []
        resolved_rows: list[dict[str, Any]] = []
        for c in commitments:
            if not isinstance(c, dict):
                continue
            if c.get("resolved"):
                continue
            if needle and needle not in str(c.get("text") or "").lower():
                continue
            if owner is not None and (c.get("owner") or "") != owner:
                continue
            c["resolved"] = True
            c["resolved_at"] = now
            resolved_rows.append(
                {
                    "text": c.get("text"),
                    "owner": c.get("owner"),
                    "resolved_at": now,
                }
            )
        out["resolved"] = resolved_rows
        out["count"] = len(resolved_rows)
    except Exception:  # noqa: BLE001
        return {"resolved": [], "count": 0}
    return out


def assign_owner(
    node_id: str,
    meeting_id: str,
    *,
    text_contains: str,
    new_owner: str,
    owner_confidence: str = "high",
) -> dict[str, Any]:
    """
    Operator-triggered owner assignment. Updates matching commitment(s)
    in-place on the in-memory summary. No external effects.

    Returns {"updated": [...], "count": int}.
    """
    out: dict[str, Any] = {"updated": [], "count": 0}
    if not node_id or not meeting_id or not text_contains or not new_owner:
        return out
    summary = _get_summary(node_id, meeting_id)
    if summary is None:
        return out
    try:
        needle = text_contains.strip().lower()
        commitments = getattr(summary, "commitments", None) or []
        updated: list[dict[str, Any]] = []
        for c in commitments:
            if not isinstance(c, dict):
                continue
            if needle not in str(c.get("text") or "").lower():
                continue
            prev_owner = c.get("owner")
            c["owner"] = new_owner
            c["owner_confidence"] = owner_confidence
            updated.append(
                {
                    "text": c.get("text"),
                    "previous_owner": prev_owner,
                    "new_owner": new_owner,
                }
            )
        out["updated"] = updated
        out["count"] = len(updated)
    except Exception:  # noqa: BLE001
        return {"updated": [], "count": 0}
    return out


def refresh(
    node_id: str, meeting_id: Optional[str] = None
) -> dict[str, Any]:
    """
    Explicit re-evaluation of the snapshot. Pure: identical to calling
    linkage_snapshot, but exposed as an operator verb for clarity.
    """
    return _safe_snapshot(node_id, meeting_id)
