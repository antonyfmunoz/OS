"""Cockpit routes for UnifiedWorkstationRuntime — Campaign 18.0.

Enriched in Phase 10.0 convergence to serve as the single canonical
workstation read path. Individual /workstation/* endpoints remain for
write operations but reads come through here.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter

from transports.api.read_path_isolation import TTLSnapshotCache, cached_isolated_read

logger = logging.getLogger(__name__)

_runtime: Any = None

# ── P4S-31C read-path hardening ─────────────────────────────────────────────
# The composite snapshot composes six sub-reads; one sub-runtime blocks >55 s
# under load (proven in 2026-07-06 sustained-load diagnosis). Bound it: run the
# composition on the dedicated read pool with a hard timeout + short TTL cache,
# so it (a) never holds a shared AnyIO threadpool token and (b) never blocks
# the poller past the budget — it degrades to last-known-good instead. Response
# shape is byte-identical; only freshness degrades under sustained load.
_SNAPSHOT_TTL_SECONDS = 5.0
_SNAPSHOT_TIMEOUT_SECONDS = 8.0
_snapshot_cache = TTLSnapshotCache(ttl_seconds=_SNAPSHOT_TTL_SECONDS)


def _get_runtime() -> Any:
    global _runtime
    if _runtime is None:
        try:
            from substrate.workstation.unified_workstation_runtime import (
                UnifiedWorkstationRuntime,
            )

            _runtime = UnifiedWorkstationRuntime()
        except Exception:
            pass
    return _runtime


def _read_continuity() -> dict[str, Any]:
    """Read continuity state from the same source as /workstation/continuity."""
    try:
        from substrate.workstation.continuity import ContinuityStateMachine

        path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "umh",
            "workstation_state",
            "continuity.json",
        )
        if os.path.exists(path):
            data = json.loads(open(path, encoding="utf-8").read())
            machine = ContinuityStateMachine.from_dict(data)
        else:
            machine = ContinuityStateMachine()
        return {
            "current_state": machine.current_state.value,
            "valid_transitions": [s.value for s in machine.valid_transitions()],
        }
    except Exception:
        logger.debug("continuity read failed", exc_info=True)
        return {"current_state": "ACTIVE", "valid_transitions": []}


def _read_mode_composite() -> dict[str, Any]:
    """Read composite mode from the same source as /workstation/mode-composite."""
    try:
        from substrate.workstation.mode_resolver import resolve_composite_mode

        return resolve_composite_mode()
    except Exception:
        logger.debug("mode composite read failed", exc_info=True)
        return {
            "lifecycle_mode": "day_cycle",
            "risk_ceiling": "HIGH",
            "effective_posture": "",
            "continuity_state": "",
            "active_profile_modes": [],
        }


def _read_overnight() -> dict[str, Any]:
    """Read overnight status from the same source as /workstation/overnight/status."""
    try:
        from substrate.workstation.overnight_queue import OvernightQueue

        queue = OvernightQueue()
        summary = queue.morning_summary()
        return {
            "safe_count": summary.get("safe_count", 0),
            "pending_count": summary.get("pending_count", 0),
            "blocked_count": summary.get("blocked_count", 0),
        }
    except Exception:
        logger.debug("overnight read failed", exc_info=True)
        return {"safe_count": 0, "pending_count": 0, "blocked_count": 0}


def _read_nodes() -> dict[str, Any]:
    """Read node info from the same sources as /workstation/nodes."""
    try:
        from transports.api.cockpit_workstation_control_routes import (
            _read_vps_node,
            _read_mesh_snapshot,
        )

        vps = _read_vps_node()
        mesh = _read_mesh_snapshot()
        all_nodes = [vps] + mesh
        return {"count": len(all_nodes), "nodes": all_nodes}
    except Exception:
        logger.debug("nodes read failed", exc_info=True)
        return {"count": 0, "nodes": []}


def _read_presence_capabilities() -> dict[str, Any]:
    """Read STT/TTS availability."""
    try:
        stt = False
        tts = False
        tts_path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "runtime",
            "presence",
            "tts_status.json",
        )
        stt_path = os.path.join(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "runtime",
            "presence",
            "stt_status.json",
        )
        if os.path.exists(tts_path):
            tts = json.loads(open(tts_path, encoding="utf-8").read()).get("available", False)
        if os.path.exists(stt_path):
            stt = json.loads(open(stt_path, encoding="utf-8").read()).get("available", False)
        return {"stt_available": stt, "tts_available": tts}
    except Exception:
        logger.debug("presence capabilities read failed", exc_info=True)
        return {"stt_available": False, "tts_available": False}


def _compose_snapshot() -> dict[str, Any]:
    """Compose the enriched snapshot (synchronous; the intrinsically slow work).

    Extracted verbatim from the former route body so it can be driven on the
    dedicated read pool under a hard timeout. Produces the exact dict the route
    has always returned — no shape change.
    """
    base: dict[str, Any] = {}
    rt = _get_runtime()
    if rt is not None:
        base = rt.snapshot().to_dict()

    continuity = _read_continuity()
    mode = _read_mode_composite()
    overnight = _read_overnight()
    nodes = _read_nodes()
    presence = _read_presence_capabilities()

    base["continuity_state"] = continuity["current_state"]
    base["valid_transitions"] = continuity["valid_transitions"]
    base["lifecycle_mode"] = mode.get("lifecycle_mode", "day_cycle")
    base["risk_ceiling"] = mode.get("risk_ceiling", "HIGH")
    base["effective_posture"] = mode.get("effective_posture", "")
    base["active_profile_modes"] = mode.get("active_profile_modes", [])
    base["overnight"] = overnight
    base["node_count"] = nodes["count"]
    base["nodes"] = nodes["nodes"]
    base["stt_available"] = presence["stt_available"]
    base["tts_available"] = presence["tts_available"]

    return base


def _empty_snapshot_fallback() -> dict[str, Any]:
    """Stable, shape-complete fallback used ONLY on a cold-cache timeout.

    Every key the composed dict adds (rt is None → base is empty) with each
    sub-read's own documented default. Same key set as ``_compose_snapshot``'s
    ``rt is None`` path, so a cold-start-under-load client still gets the exact
    schema — never a partial or error-shaped body.
    """
    return {
        "continuity_state": "ACTIVE",
        "valid_transitions": [],
        "lifecycle_mode": "day_cycle",
        "risk_ceiling": "HIGH",
        "effective_posture": "",
        "active_profile_modes": [],
        "overnight": {"safe_count": 0, "pending_count": 0, "blocked_count": 0},
        "node_count": 0,
        "nodes": [],
        "stt_available": False,
        "tts_available": False,
    }


def get_router() -> APIRouter:
    router = APIRouter(prefix="/unified-workstation", tags=["unified-workstation"])

    @router.get("/snapshot")
    async def get_snapshot() -> dict[str, Any]:
        """Enriched unified workstation snapshot — single canonical read.

        Composes: UnifiedWorkstationRuntime snapshot + continuity + mode
        + overnight + nodes + presence capabilities.

        P4S-31C: the composition runs on the dedicated read pool under a hard
        timeout with a short TTL cache. It no longer holds a shared AnyIO
        threadpool token, and under sustained load it degrades to
        last-known-good instead of blocking >55 s. Response shape is unchanged.
        """
        return await cached_isolated_read(
            _compose_snapshot,
            cache=_snapshot_cache,
            timeout=_SNAPSHOT_TIMEOUT_SECONDS,
            empty_fallback=_empty_snapshot_fallback(),
            label="unified_workstation_snapshot",
        )

    @router.get("/mode")
    def get_mode() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"state": "unknown"}
        return {"state": rt.mode()}

    @router.get("/attention")
    def get_attention() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"items": []}
        return {"items": rt.attention()}

    @router.get("/risks")
    def get_risks() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"risks": []}
        return {"risks": rt.risks()}

    @router.get("/summary")
    def get_summary() -> dict[str, Any]:
        rt = _get_runtime()
        if rt is None:
            return {"error": "UnifiedWorkstationRuntime unavailable"}
        return rt.summary()

    return router
