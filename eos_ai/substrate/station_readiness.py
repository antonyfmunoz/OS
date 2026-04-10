"""
Station readiness — derived view of whether a node is fit for ritual work.

Pure derivation. No new state. No persistence. Reads:
  - NodeRegistry  (last_seen, declared status)
  - ResultStore   (recent outcomes, fallbacks, kinds)
  - RitualRegistry (unresolved body actions, optional)

Output is a tiny JSON-ready dict and a three-state classification:

    READY        — heartbeat fresh, recent results healthy
    DEGRADED     — heartbeat present but failure/fallback rate high,
                   OR declared NodeStatus.DEGRADED, OR stale heartbeat
    UNAVAILABLE  — node unknown, no recent heartbeat, OR declared OFFLINE

Design rules (mirror substrate philosophy):
  - Best-effort. Never raises. Missing data degrades classification, not crash.
  - Bounded. Walks at most the per-node result slice (already capped at 500).
  - Backward compatible. Adds nothing to Node, ResultStore, or storage.
  - Hot-path-free. Imports only substrate siblings.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from eos_ai.substrate.nodes import NodeRegistry, NodeStatus
from eos_ai.substrate.result_query import node_health_summary
from eos_ai.substrate.result_store import ResultStore, get_result_store


# ─── Tunables (deliberately conservative) ────────────────────────────────────

# Heartbeat freshness windows (seconds).
HEARTBEAT_FRESH_S = 5 * 60        # ≤ 5 min   → fresh
HEARTBEAT_STALE_S = 30 * 60       # ≤ 30 min  → stale (degraded)
                                  # > 30 min  → offline (unavailable)

# Failure-rate thresholds over the recent window of results for the node.
RECENT_WINDOW = 25                # how many recent results to weigh
DEGRADED_FAIL_RATIO = 0.30        # ≥ 30% failed/rejected → degraded
DEGRADED_FALLBACK_RATIO = 0.50    # ≥ 50% fallbacks       → degraded
UNRESOLVED_DEGRADED_THRESHOLD = 5  # ≥ 5 unresolved actions → degraded

READY = "READY"
DEGRADED = "DEGRADED"
UNAVAILABLE = "UNAVAILABLE"


@dataclass
class StationReadiness:
    """Tiny JSON-ready readiness snapshot for a node."""

    node_id: str
    classification: str  # READY | DEGRADED | UNAVAILABLE
    reasons: list[str] = field(default_factory=list)
    last_heartbeat: Optional[str] = None        # ISO from Node.last_seen
    last_result_at: Optional[str] = None        # ISO from ResultStore
    heartbeat_age_s: Optional[float] = None
    declared_status: Optional[str] = None       # NodeStatus.value or "unknown"
    recent_total: int = 0
    recent_failed: int = 0
    recent_rejected: int = 0
    recent_fallbacks: int = 0
    fail_ratio: float = 0.0
    fallback_ratio: float = 0.0
    unresolved_actions: int = 0
    by_kind: dict[str, int] = field(default_factory=dict)
    # Capability-awareness (additive; omitted from legacy consumers that
    # iterate keys they know — dataclasses.asdict includes them harmlessly).
    capability_mismatch: bool = False
    missing_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # tolerate "...Z" suffix
        v = value.replace("Z", "+00:00") if value.endswith("Z") else value
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _age_seconds(value: Optional[str]) -> Optional[float]:
    dt = _parse_iso(value)
    if dt is None:
        return None
    return max(0.0, (_utcnow() - dt).total_seconds())


def _count_unresolved_for_node(node_id: str, store: ResultStore) -> int:
    """Best-effort scan of recent rituals for unresolved actions on this node."""
    try:
        from eos_ai.substrate.rituals import RitualRegistry
    except Exception:
        return 0
    try:
        history = list(RitualRegistry.default().history())[-50:]
    except Exception:
        return 0

    pending = 0
    for ritual in history:
        body = (getattr(ritual, "outputs", {}) or {}).get("body_actions") or []
        if not isinstance(body, list):
            continue
        for entry in body:
            if not isinstance(entry, dict):
                continue
            aid = entry.get("action_id")
            if not aid:
                continue
            ir = store.get(aid)
            if ir is None:
                pending += 1
                continue
            if ir.node_id != node_id:
                continue
            # Resolved on this node — not pending.
    return pending


# ─── Public API ──────────────────────────────────────────────────────────────

def station_readiness(
    node_id: str,
    *,
    store: Optional[ResultStore] = None,
    registry: Optional[NodeRegistry] = None,
) -> StationReadiness:
    """
    Compute readiness for a node. Always returns a StationReadiness object;
    never raises. UNAVAILABLE is the safe default when data is missing.
    """
    s = store or get_result_store()
    reg = registry or NodeRegistry.default()

    reasons: list[str] = []
    declared_status: Optional[str] = None
    last_heartbeat: Optional[str] = None

    # 1. Look up the node — missing node is UNAVAILABLE.
    try:
        node = reg.get(node_id)
    except Exception as e:
        node = None
        reasons.append(f"node lookup failed: {e}")

    if node is None:
        return StationReadiness(
            node_id=node_id,
            classification=UNAVAILABLE,
            reasons=["node not registered"] + reasons,
            declared_status="unknown",
        )

    declared_status = (
        node.status.value if isinstance(node.status, NodeStatus) else str(node.status)
    )
    last_heartbeat = node.last_seen

    # 2. Pull node health summary (counts by status / kind / fallbacks).
    try:
        health = node_health_summary(node_id, store=s)
    except Exception as e:
        health = {
            "total": 0, "by_status": {}, "by_kind": {},
            "fallbacks": 0, "last_ingested_at": None,
        }
        reasons.append(f"health summary failed: {e}")

    by_status = health.get("by_status", {}) or {}
    by_kind = health.get("by_kind", {}) or {}
    last_result_at = health.get("last_ingested_at")
    fallbacks = int(health.get("fallbacks", 0) or 0)

    # 3. Recent-window slice — most recent N results for this node.
    try:
        node_results = sorted(
            s.by_node(node_id),
            key=lambda r: r.ingested_at or "",
            reverse=True,
        )[:RECENT_WINDOW]
    except Exception:
        node_results = []

    recent_total = len(node_results)
    recent_failed = sum(1 for r in node_results if (r.status or "").lower() == "failed")
    recent_rejected = sum(1 for r in node_results if (r.status or "").lower() == "rejected")
    recent_fallbacks = sum(1 for r in node_results if r.is_fallback)

    fail_ratio = (
        (recent_failed + recent_rejected) / recent_total if recent_total else 0.0
    )
    fallback_ratio = (recent_fallbacks / recent_total) if recent_total else 0.0

    # 4. Unresolved actions — bounded ritual scan.
    try:
        unresolved = _count_unresolved_for_node(node_id, s)
    except Exception:
        unresolved = 0

    heartbeat_age = _age_seconds(last_heartbeat)

    # 4b. Capability snapshot — does this node support even the smallest
    # default scene? Used as a DEGRADED hint, not a hard UNAVAILABLE, so an
    # offline-but-capable node still reports stale-heartbeat as primary.
    capability_mismatch = False
    missing_capabilities: list[str] = []
    try:
        from eos_ai.substrate.scene_capabilities import node_supports
        ok_default, missing_default = node_supports(node, "operator_mode")
        if not ok_default:
            capability_mismatch = True
            missing_capabilities = sorted(missing_default)
    except Exception:
        # Never fail readiness on capability lookup errors.
        pass

    # 5. Classify.
    classification = READY

    # Hard UNAVAILABLE conditions.
    if declared_status == NodeStatus.OFFLINE.value:
        classification = UNAVAILABLE
        reasons.append("node declared OFFLINE")
    elif heartbeat_age is None and last_heartbeat is None:
        classification = UNAVAILABLE
        reasons.append("no heartbeat ever recorded")
    elif heartbeat_age is not None and heartbeat_age > HEARTBEAT_STALE_S:
        classification = UNAVAILABLE
        reasons.append(f"heartbeat stale ({int(heartbeat_age)}s old)")

    # Degradation conditions (only if not already UNAVAILABLE).
    if classification != UNAVAILABLE:
        if declared_status == NodeStatus.DEGRADED.value:
            classification = DEGRADED
            reasons.append("node declared DEGRADED")
        if heartbeat_age is not None and heartbeat_age > HEARTBEAT_FRESH_S:
            classification = DEGRADED
            reasons.append(f"heartbeat aging ({int(heartbeat_age)}s old)")
        if recent_total >= 5 and fail_ratio >= DEGRADED_FAIL_RATIO:
            classification = DEGRADED
            reasons.append(
                f"failure ratio {fail_ratio:.0%} over last {recent_total}"
            )
        if recent_total >= 5 and fallback_ratio >= DEGRADED_FALLBACK_RATIO:
            classification = DEGRADED
            reasons.append(
                f"fallback ratio {fallback_ratio:.0%} over last {recent_total}"
            )
        if unresolved >= UNRESOLVED_DEGRADED_THRESHOLD:
            classification = DEGRADED
            reasons.append(f"{unresolved} unresolved ritual actions")
        if capability_mismatch:
            classification = DEGRADED
            reasons.append(
                "capability_mismatch: node lacks "
                f"{', '.join(missing_capabilities) or 'required caps'} "
                "for operator_mode"
            )

    if classification == READY:
        reasons.append("recent results healthy")

    return StationReadiness(
        node_id=node_id,
        classification=classification,
        reasons=reasons,
        last_heartbeat=last_heartbeat,
        last_result_at=last_result_at,
        heartbeat_age_s=heartbeat_age,
        declared_status=declared_status,
        recent_total=recent_total,
        recent_failed=recent_failed,
        recent_rejected=recent_rejected,
        recent_fallbacks=recent_fallbacks,
        fail_ratio=round(fail_ratio, 3),
        fallback_ratio=round(fallback_ratio, 3),
        unresolved_actions=unresolved,
        by_kind=dict(by_kind),
        capability_mismatch=capability_mismatch,
        missing_capabilities=missing_capabilities,
    )


def is_ready(node_id: str, **kwargs) -> bool:
    """Convenience predicate."""
    return station_readiness(node_id, **kwargs).classification == READY
