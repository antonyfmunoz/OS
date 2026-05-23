"""
Ritual body — tiny executable layer for open_day / close_day.

Rituals have historically been pure lifecycle markers (PENDING → … → COMPLETED)
with no side effects beyond state transitions. This module adds the smallest
useful executable layer: a declarative `RitualPolicy` that maps a ritual
lifecycle event to a bounded set of *already-safe* station actions.

Design rules:
  - Declarative, not imperative. No branching logic, no template engine.
  - Uses ONLY actions that are already in the MVP allow-list:
      SPEAK_TEXT, PLAY_SOUND, OPEN_URL, LAUNCH_APP, OPEN_SCENE
  - Best-effort. If the target node is missing or offline the ritual still
    succeeds — the body just logs and skips. A station being unavailable is
    never a ritual failure.
  - Audit trail. Every proposed action is captured in
    `ritual.outputs["body_actions"]` so the operator can see what ran.
  - Reversible. Disabling the body anywhere in the call chain drops the
    system back to lifecycle-marker behavior exactly.

Non-goals:
  - Ritual workflow engine / DAG execution.
  - User-defined rituals at runtime.
  - Any action kind not already cleared by StationContract.MVP_ALLOWED_ACTIONS.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Optional

from substrate.execution.bridge.actions import SafeAction
from substrate.execution.bridge.nodes import NodeRegistry, NodeStatus
from substrate.execution.bridge.result_query import node_health_summary
from substrate.execution.bridge.ritual_inference import InferredHint, infer_open_scene_hint
from substrate.execution.bridge.rituals import Ritual, RitualKind, RitualRegistry
from substrate.execution.bridge.scene_policy import select_scene
from substrate.execution.bridge.scenes import get_scene
from substrate.execution.bridge.station_helpers import (
    propose_open_scene,
    propose_play_sound,
    propose_speak_text,
)
from substrate.execution.bridge.station_readiness import (
    DEGRADED,
    READY,
    UNAVAILABLE,
    StationReadiness,
    station_readiness,
)


def _log(msg: str) -> None:
    print(f"[substrate.ritual_body] {msg}", file=sys.stderr)


# ─── Policy ───────────────────────────────────────────────────────────────────

@dataclass
class RitualPolicy:
    """
    Declarative body for a ritual.

    Every field is optional. A policy with nothing set produces a no-op body
    (ritual stays a pure lifecycle marker). Setting a field opts into one
    specific safe action.

    Fields:
        station_node_id — target local station for any station action. If
                          unset, no station actions run at all.
        open_scene      — scene name proposed to the station on open_day.
                          Must be in scenes.SCENE_REGISTRY.
        open_speak      — SPEAK_TEXT text proposed on open_day.
        close_speak     — SPEAK_TEXT text proposed on close_day.
        close_sound     — PLAY_SOUND path proposed on close_day.
        require_online  — if True, skip station actions when the node is not
                          ONLINE. If False, still propose (outbox queues for
                          whenever the daemon next polls).
    """

    station_node_id: Optional[str] = None
    open_scene: Optional[str] = None
    open_speak: Optional[str] = None
    close_speak: Optional[str] = None
    close_sound: Optional[str] = None
    require_online: bool = False


# ─── Runner ───────────────────────────────────────────────────────────────────

def _resolve_station(policy: RitualPolicy) -> tuple[Optional[str], Optional[str]]:
    """
    Return (node_id, skip_reason). skip_reason is None when the station is
    usable; otherwise it's a short human-readable explanation of why the
    ritual body is skipping station actions.
    """
    if not policy.station_node_id:
        return None, "no station_node_id in policy"

    try:
        registry = NodeRegistry.default()
        node = registry.get(policy.station_node_id)
    except Exception as e:
        return None, f"node lookup failed: {e}"

    if node is None:
        return None, f"node {policy.station_node_id!r} not registered"

    if policy.require_online and node.status != NodeStatus.ONLINE:
        return None, f"node {policy.station_node_id!r} status={node.status.value}"

    return policy.station_node_id, None


def _record(body_actions: list[dict], kind: str, detail: str, action: Optional[SafeAction]) -> None:
    entry = {"kind": kind, "detail": detail}
    if action is not None:
        entry["action_id"] = action.action_id
        entry["status"] = action.status.value
    body_actions.append(entry)
    _log(f"{kind}: {detail}")


def run_open_day_body(ritual_id: str, policy: RitualPolicy) -> list[dict]:
    """
    Execute the open_day body for an existing ritual. Returns the list of
    body action records, which is also written into `ritual.outputs["body_actions"]`.

    Never raises on station/transport problems — the ritual remains valid
    even when no workstation is reachable.
    """
    reg = RitualRegistry.default()
    ritual = reg.get(ritual_id)
    if ritual is None:
        _log(f"open_day body: unknown ritual_id {ritual_id!r}")
        return []
    if ritual.kind != RitualKind.OPEN_DAY:
        _log(f"open_day body: ritual_id {ritual_id!r} is not open_day")
        return []

    body_actions: list[dict] = []
    node_id, skip_reason = _resolve_station(policy)

    # Compute readiness up-front so the body can record *why* it acted or
    # skipped. Best-effort — failure here downgrades to UNKNOWN, never raises.
    readiness: Optional[StationReadiness] = None
    if policy.station_node_id:
        try:
            readiness = station_readiness(policy.station_node_id)
        except Exception as e:
            _log(f"readiness check failed: {e}")
            readiness = None

    # Only record readiness in body_actions when we actually have a usable
    # station — otherwise we'd duplicate the 'skipped' signal and break the
    # legacy contract that "no station = exactly one body action: skipped".
    # The full readiness snapshot is always persisted in ritual.outputs below.
    if readiness is not None and node_id is not None:
        _record(
            body_actions,
            "readiness",
            f"{readiness.classification}: {'; '.join(readiness.reasons[:3])}",
            None,
        )

    if node_id is None:
        _record(body_actions, "skipped", skip_reason or "no station", None)
    elif readiness is not None and readiness.classification == UNAVAILABLE:
        _record(
            body_actions,
            "skipped",
            f"readiness UNAVAILABLE: {'; '.join(readiness.reasons[:2])}",
            None,
        )
    else:
        if policy.open_speak:
            try:
                action = propose_speak_text(
                    node_id, policy.open_speak, issued_by="ritual:open_day"
                )
                _record(body_actions, "speak_text", policy.open_speak, action)
            except Exception as e:
                _record(body_actions, "speak_text_error", str(e), None)

        # Scene selection: explicit hint wins; otherwise infer deterministically
        # from recent ritual history + node metadata. Inference NEVER overrides
        # an explicit policy.open_scene.
        requested_mode = policy.open_scene
        inferred: Optional[InferredHint] = None  # noqa: F841 — read by locals() below
        if not requested_mode:
            try:
                inferred = infer_open_scene_hint(node_id)
            except Exception as e:
                _log(f"inference failed: {e}")
                inferred = None
            if inferred is not None and inferred.scene:
                requested_mode = inferred.scene
                _record(
                    body_actions,
                    "scene_inference",
                    f"{inferred.scene} — {inferred.reason} [source={inferred.source}]",
                    None,
                )

        decision = select_scene(
            node_id=node_id,
            readiness=readiness,
            requested_mode=requested_mode,
        )
        _record(
            body_actions,
            "scene_decision",
            f"{decision.scene or 'none'} — {decision.reason}",
            None,
        )

        if decision.scene is not None:
            if get_scene(decision.scene) is None:
                _record(
                    body_actions,
                    "open_scene_rejected",
                    f"scene {decision.scene!r} not in registry",
                    None,
                )
            else:
                try:
                    action = propose_open_scene(
                        node_id, decision.scene, issued_by="ritual:open_day"
                    )
                    _record(body_actions, "open_scene", decision.scene, action)
                except Exception as e:
                    _record(body_actions, "open_scene_error", str(e), None)

    # Persist the body actions into ritual outputs for audit.
    ritual.outputs["body_actions"] = body_actions
    if readiness is not None:
        ritual.outputs["readiness"] = readiness.to_dict()
    # Stash the final scene decision (always when we actually ran selection)
    # and any inferred hint so the reporter can trace the decision path.
    try:
        if node_id is not None and "decision" in locals():
            ritual.outputs["scene_decision"] = decision.to_dict()  # type: ignore[name-defined]
        if "inferred" in locals() and inferred is not None:  # type: ignore[name-defined]
            ritual.outputs["inferred_scene_hint"] = inferred.to_dict()  # type: ignore[name-defined]
    except Exception:
        pass
    try:
        reg._flush()  # noqa: SLF001 — reuse existing persistence path
    except Exception as e:
        _log(f"flush failed: {e}")
    return body_actions


def run_close_day_body(ritual_id: str, policy: RitualPolicy) -> list[dict]:
    """
    Execute the close_day body. Same semantics as run_open_day_body:
    best-effort, never raises, writes to ritual.outputs["body_actions"].
    """
    reg = RitualRegistry.default()
    ritual = reg.get(ritual_id)
    if ritual is None:
        _log(f"close_day body: unknown ritual_id {ritual_id!r}")
        return []
    if ritual.kind != RitualKind.CLOSE_DAY:
        _log(f"close_day body: ritual_id {ritual_id!r} is not close_day")
        return []

    body_actions: list[dict] = []
    node_id, skip_reason = _resolve_station(policy)

    # Best-effort readiness snapshot — used for the close summary so the
    # operator can see how the workstation actually behaved during the day.
    readiness: Optional[StationReadiness] = None
    if policy.station_node_id:
        try:
            readiness = station_readiness(policy.station_node_id)
        except Exception as e:
            _log(f"readiness check failed: {e}")
            readiness = None

    # Same backward-compat rule as open_day: only emit a readiness body
    # action when we have a usable station, so the legacy "exactly one
    # skipped entry on missing station" contract is preserved.
    if readiness is not None and node_id is not None:
        _record(
            body_actions,
            "readiness",
            f"{readiness.classification}: {'; '.join(readiness.reasons[:3])}",
            None,
        )

    if node_id is None:
        _record(body_actions, "skipped", skip_reason or "no station", None)
    elif readiness is not None and readiness.classification == UNAVAILABLE:
        _record(
            body_actions,
            "skipped",
            f"readiness UNAVAILABLE: {'; '.join(readiness.reasons[:2])}",
            None,
        )
    else:
        if policy.close_speak:
            try:
                action = propose_speak_text(
                    node_id, policy.close_speak, issued_by="ritual:close_day"
                )
                _record(body_actions, "speak_text", policy.close_speak, action)
            except Exception as e:
                _record(body_actions, "speak_text_error", str(e), None)

        if policy.close_sound:
            try:
                action = propose_play_sound(
                    node_id, path=policy.close_sound, issued_by="ritual:close_day"
                )
                _record(body_actions, "play_sound", policy.close_sound, action)
            except Exception as e:
                _record(body_actions, "play_sound_error", str(e), None)

    # Build a tiny close-day workstation summary the operator can read at a
    # glance — counts the body actions by kind so failures are visible.
    summary_by_kind: dict[str, int] = {}
    for entry in body_actions:
        k = entry.get("kind", "unknown")
        summary_by_kind[k] = summary_by_kind.get(k, 0) + 1

    ritual.outputs["body_actions"] = body_actions
    ritual.outputs["close_day_summary"] = {
        "node_id": policy.station_node_id,
        "readiness": readiness.classification if readiness else "UNKNOWN",
        "body_action_count": len(body_actions),
        "by_kind": summary_by_kind,
    }
    if readiness is not None:
        ritual.outputs["readiness"] = readiness.to_dict()
    try:
        reg._flush()  # noqa: SLF001
    except Exception as e:
        _log(f"flush failed: {e}")
    return body_actions
