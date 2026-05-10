"""
Result query helpers — tiny operator-facing view over the ResultStore.

Not a UI, not an API — just the smallest useful set of lookups so operators
and reporting scripts can answer questions like:

    "What happened on my workstation in the last hour?"
    "Which station actions failed recently?"
    "Did that specific action_id resolve, and what was the detail?"

All helpers are best-effort, never raise, and return plain dicts so they
are trivially JSON-serializable for CLI output.
"""

from __future__ import annotations

from typing import Any, Optional

from eos_ai.transport.result_store import (
    IngestedResult,
    ResultStore,
    get_result_store,
)


def _row(r: IngestedResult) -> dict[str, Any]:
    return {
        "action_id": r.action_id,
        "node_id": r.node_id,
        "status": r.status,
        "detail": r.detail,
        "fallback": r.is_fallback,
        "returned_at": r.returned_at,
        "ingested_at": r.ingested_at,
        "kind": r.kind,
    }


def latest(limit: int = 20, *, store: Optional[ResultStore] = None) -> list[dict]:
    s = store or get_result_store()
    return [_row(r) for r in s.latest(limit=limit)]


def latest_by_node(
    node_id: str,
    limit: int = 20,
    *,
    store: Optional[ResultStore] = None,
) -> list[dict]:
    s = store or get_result_store()
    rows = sorted(s.by_node(node_id), key=lambda r: r.ingested_at or "", reverse=True)
    return [_row(r) for r in rows[: max(0, int(limit))]]


def by_action_id(
    action_id: str,
    *,
    store: Optional[ResultStore] = None,
) -> Optional[dict]:
    s = store or get_result_store()
    ir = s.get(action_id)
    return _row(ir) if ir is not None else None


def latest_failed(
    limit: int = 20,
    *,
    store: Optional[ResultStore] = None,
) -> list[dict]:
    """Recent failures + rejections + any fallback-flagged outcomes."""
    s = store or get_result_store()
    bad: list[IngestedResult] = []
    for r in s.all():
        status = (r.status or "").lower()
        if status in {"failed", "rejected"} or r.is_fallback:
            bad.append(r)
    bad.sort(key=lambda r: r.ingested_at or "", reverse=True)
    return [_row(r) for r in bad[: max(0, int(limit))]]


def stats(*, store: Optional[ResultStore] = None) -> dict[str, Any]:
    s = store or get_result_store()
    base = dict(s.stats())
    # Enrich with kind breakdown — tiny, bounded, only walks the store once.
    by_kind: dict[str, int] = {}
    without_kind = 0
    for r in s.all():
        if r.kind:
            by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
        else:
            without_kind += 1
    base["by_kind"] = by_kind
    base["without_kind"] = without_kind
    return base


def latest_by_kind(
    kind: str,
    limit: int = 20,
    *,
    store: Optional[ResultStore] = None,
) -> list[dict]:
    """Most recent results of a single action kind (e.g. 'speak_text')."""
    s = store or get_result_store()
    needle = (kind or "").strip().lower()
    rows = [r for r in s.all() if (r.kind or "").lower() == needle]
    rows.sort(key=lambda r: r.ingested_at or "", reverse=True)
    return [_row(r) for r in rows[: max(0, int(limit))]]


def node_health_summary(
    node_id: str,
    *,
    store: Optional[ResultStore] = None,
) -> dict[str, Any]:
    """
    Tiny operator-facing health view for a single node: counts by status,
    counts by kind, fallback count, last ingested_at.
    """
    s = store or get_result_store()
    rows = s.by_node(node_id)
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    fallbacks = 0
    last_seen: Optional[str] = None
    for r in rows:
        by_status[(r.status or "unknown").lower()] = (
            by_status.get((r.status or "unknown").lower(), 0) + 1
        )
        if r.kind:
            by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
        if r.is_fallback:
            fallbacks += 1
        if (r.ingested_at or "") > (last_seen or ""):
            last_seen = r.ingested_at
    return {
        "node_id": node_id,
        "total": len(rows),
        "by_status": by_status,
        "by_kind": by_kind,
        "fallbacks": fallbacks,
        "last_ingested_at": last_seen,
    }


def unresolved_rituals(limit: int = 20) -> list[dict]:
    """
    Recent rituals whose body_actions include at least one action_id that
    has no matching result yet. Bounded, read-only, never raises.
    """
    try:
        from eos_ai.transport.rituals import RitualRegistry
    except Exception:
        return []
    s = get_result_store()
    try:
        history = list(RitualRegistry.default().history())[-max(1, int(limit)) :]
    except Exception:
        return []
    out: list[dict] = []
    for ritual in reversed(history):
        body = (ritual.outputs or {}).get("body_actions") or []
        if not isinstance(body, list):
            continue
        pending: list[str] = []
        total_with_id = 0
        for entry in body:
            if not isinstance(entry, dict):
                continue
            aid = entry.get("action_id")
            if not aid:
                continue
            total_with_id += 1
            if s.get(aid) is None:
                pending.append(aid)
        if pending:
            out.append(
                {
                    "ritual_id": ritual.ritual_id,
                    "ritual_type": getattr(ritual, "ritual_type", None),
                    "total_with_action_id": total_with_id,
                    "pending_action_ids": pending,
                }
            )
    return out


def station_readiness_report(node_id: str) -> dict[str, Any]:
    """
    Operator-facing readiness snapshot for a single node, paired with the
    scene the policy layer would currently recommend AND the scene that
    ritual inference would propose if no explicit hint were supplied.

    Bounded, JSON-friendly, never raises. Safe to embed in operator reports.
    """
    try:
        from eos_ai.transport.scene_policy import select_scene
        from eos_ai.transport.station_readiness import station_readiness
    except Exception as e:
        return {
            "node_id": node_id,
            "classification": "UNKNOWN",
            "reasons": [f"readiness import failed: {e}"],
            "recommended_scene": None,
            "inferred_mode": None,
        }
    try:
        readiness = station_readiness(node_id)
    except Exception as e:
        return {
            "node_id": node_id,
            "classification": "UNKNOWN",
            "reasons": [f"readiness compute failed: {e}"],
            "recommended_scene": None,
            "inferred_mode": None,
        }

    # Inference trace (what WOULD the ritual layer pick if no hint?)
    inferred_payload: Optional[dict] = None
    try:
        from eos_ai.transport.ritual_inference import infer_open_scene_hint

        inferred_payload = infer_open_scene_hint(node_id).to_dict()
    except Exception as e:
        inferred_payload = {
            "scene": None,
            "reason": f"inference failed: {e}",
            "source": "none",
        }

    # Scene policy decision, fed by the inferred hint (mirrors what a no-hint
    # open_day would actually do). Falls back to a no-hint call if inference
    # returned nothing.
    try:
        hint = (inferred_payload or {}).get("scene")
        decision = select_scene(
            node_id=node_id, readiness=readiness, requested_mode=hint
        )
        rec = decision.to_dict()
    except Exception as e:
        rec = {
            "scene": None,
            "reason": f"policy failed: {e}",
            "classification": readiness.classification,
        }

    # Scene capability requirements inventory — small, static, helps the
    # operator understand WHY a scene was downgraded.
    try:
        from eos_ai.transport.scene_capabilities import scene_requirements_inventory

        scene_reqs = scene_requirements_inventory()
    except Exception:
        scene_reqs = {}

    out = readiness.to_dict()
    out["recommended_scene"] = rec
    out["inferred_mode"] = inferred_payload
    out["scene_requirements"] = scene_reqs
    return out


def recent_open_close_summaries(limit: int = 5) -> list[dict]:
    """
    Filter the most recent rituals to open_day / close_day only and surface
    the operator-relevant outputs (readiness snapshot + close_day_summary +
    body_action_count). JSON-friendly, bounded.
    """
    try:
        from eos_ai.transport.rituals import RitualKind, RitualRegistry
    except Exception:
        return []
    try:
        history = list(RitualRegistry.default().history())
    except Exception:
        return []

    out: list[dict] = []
    wanted_kinds = {RitualKind.OPEN_DAY, RitualKind.CLOSE_DAY}
    for ritual in reversed(history):
        kind = getattr(ritual, "kind", None)
        if kind not in wanted_kinds:
            continue
        outputs = getattr(ritual, "outputs", {}) or {}
        body = outputs.get("body_actions") or []
        out.append(
            {
                "ritual_id": getattr(ritual, "ritual_id", None),
                "kind": kind.value if hasattr(kind, "value") else str(kind),
                "started_at": getattr(ritual, "started_at", None),
                "body_action_count": len(body) if isinstance(body, list) else 0,
                "readiness": outputs.get("readiness"),
                "close_day_summary": outputs.get("close_day_summary"),
                "result_summary": outputs.get("result_summary"),
                "inferred_scene_hint": outputs.get("inferred_scene_hint"),
                "scene_decision": outputs.get("scene_decision"),
            }
        )
        if len(out) >= max(1, int(limit)):
            break
    return out


def recent_voice_sessions(
    limit: int = 5,
    node_id: Optional[str] = None,
) -> list[dict]:
    """
    Most recent voice sessions, newest-first. JSON-friendly. Bounded.

    Read-only view over VoiceSessionStore — exists here so operator scripts
    can pull all "what happened recently" lookups from one module.
    """
    try:
        from eos_ai.transport.voice_session import get_voice_session_store
    except Exception:
        return []
    try:
        store = get_voice_session_store()
        rows = store.latest(limit=limit, node_id=node_id)
    except Exception:
        return []
    return [r.as_dict() for r in rows]


def recent_wake_producer_events(
    limit: int = 20,
    *,
    node_id: Optional[str] = None,
) -> list[dict]:
    """
    Most recent wake producer events (wake word / clap), newest-first.
    JSON-friendly. Bounded. Read-only view over WakeProducerHistory.
    """
    try:
        from eos_ai.transport.wake_producer import get_wake_producer_history
    except Exception:
        return []
    try:
        return get_wake_producer_history().latest(limit=limit, node_id=node_id)
    except Exception:
        return []


def operator_state_snapshot(
    node_id: Optional[str] = None,
) -> dict[str, Any]:
    """Bounded operator state view for a node (or all nodes if node_id is None).

    Read-only. JSON-friendly. Best-effort — returns an empty shape on failure
    so callers don't need to wrap.
    """
    try:
        from eos_ai.transport.operator_state import get_operator_state_store
    except Exception:
        return {"node_id": node_id, "states": [], "stats": {}}
    try:
        store = get_operator_state_store()
    except Exception:
        return {"node_id": node_id, "states": [], "stats": {}}

    try:
        if node_id is not None:
            state = store.get(node_id)
            states = [state.as_dict()] if state is not None else []
        else:
            states = [s.as_dict() for s in store.all()]
        return {
            "node_id": node_id,
            "count": len(states),
            "states": states,
            "stats": store.stats(),
        }
    except Exception:
        return {"node_id": node_id, "states": [], "stats": {}}


def audio_loop_snapshot(
    node_id: Optional[str] = None,
) -> dict[str, Any]:
    """Bounded audio loop view for a node (or all nodes if node_id is None).

    Read-only. JSON-friendly. Best-effort — returns an empty shape on
    failure so callers don't need to wrap. Reports local interaction
    window status, last primed/transcript/response timestamps, last
    spoken presence line, and the node's transcript ring buffer.
    """
    try:
        from eos_ai.transport.audio_loop import snapshot as _audio_snapshot
    except Exception:
        return {"node_id": node_id, "count": 0, "states": [], "stats": {}}
    try:
        return _audio_snapshot(node_id=node_id)
    except Exception:
        return {"node_id": node_id, "count": 0, "states": [], "stats": {}}


def recent_audio_loop_transcripts(
    node_id: str,
    limit: int = 10,
) -> list[dict]:
    """Most recent transcript entries for a node's audio loop, newest-first.

    JSON-friendly. Bounded. Read-only view over the inline transcript ring
    buffer held on AudioLoopState.
    """
    try:
        from eos_ai.transport.audio_loop import get_audio_loop_store
    except Exception:
        return []
    try:
        store = get_audio_loop_store()
        state = store.get(node_id)
        if state is None:
            return []
        entries = list(reversed(state.transcripts))[: max(0, int(limit))]
        return [e.as_dict() for e in entries]
    except Exception:
        return []


def ritual_outcomes_summary(limit: int = 10) -> list[dict]:
    """
    Walk the most recent rituals and emit a bounded summary of their
    station-action outcomes. Reads `ritual.outputs["result_summary"]` which
    is populated by `ritual_reconciler.reconcile_ritual`.

    Useful after a drain+reconcile pass to answer "how did the last few
    open_day / close_day rituals actually land on the workstation?"
    """
    try:
        from eos_ai.transport.rituals import RitualRegistry
    except Exception:
        return []

    try:
        history = list(RitualRegistry.default().history())[-max(1, int(limit)) :]
    except Exception:
        return []

    out: list[dict] = []
    for ritual in reversed(history):
        summary = (ritual.outputs or {}).get("result_summary") or {}
        body = (ritual.outputs or {}).get("body_actions") or []
        out.append(
            {
                "ritual_id": ritual.ritual_id,
                "ritual_type": getattr(ritual, "ritual_type", None),
                "started_at": getattr(ritual, "started_at", None),
                "body_count": len(body) if isinstance(body, list) else 0,
                "summary": summary,
            }
        )
    return out
