"""
Scene policy — deterministic mapping from (node, readiness, hint) → scene.

NOT a rules engine. NOT runtime-configurable. A small pure function with a
fixed table so the substrate stays inspectable: any operator can read this
file and know exactly which scene a ritual will pick.

Inputs:
    node_id          — required, used only for logging/recordkeeping
    readiness        — StationReadiness | str | None
    requested_mode   — optional hint: "operator", "builder", "full", or
                       any registered scene name

Output:
    SceneDecision(scene, reason) where scene may be None when no scene
    should run (e.g. station unavailable, or hint not recognized and no
    sensible default).

Rules (read top-to-bottom; first match wins):

  1. UNAVAILABLE       → no scene (skip safely)
  2. requested_mode set + valid scene name → that scene
  3. DEGRADED          → operator_mode (smallest, safest scene) when no hint,
                         or honor a hint that maps to operator_mode only
  4. READY + "builder" → builder_mode
  5. READY + "full"    → full_station
  6. READY (no hint)   → operator_mode (default safe bring-up)
  7. anything else     → no scene
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Union

from execution.transport.scene_capabilities import node_supports, requirements_for
from execution.transport.scenes import get_scene
from execution.transport.station_readiness import (
    DEGRADED,
    READY,
    UNAVAILABLE,
    StationReadiness,
)


def _lookup_node(node_id: str):
    """Best-effort node fetch for capability checks. Never raises."""
    try:
        from execution.transport.nodes import NodeRegistry
        return NodeRegistry.default().get(node_id)
    except Exception:
        return None


def _capability_guarded(
    node_id: str,
    scene: str,
    base_reason: str,
    classification: str,
) -> "SceneDecision":
    """
    Enforce scene→capability requirements against the target node.

    If `scene` is not in the registry, the caller already handles that
    elsewhere — we just return the base decision untouched.

    If every required capability is present on the node, honor the scene.
    If any are missing, try to downgrade to 'operator_mode' when THAT
    scene's requirements are satisfied. Otherwise return no scene with
    an explanation listing the missing capabilities.
    """
    node = _lookup_node(node_id)
    ok, missing = node_supports(node, scene)
    if ok:
        return SceneDecision(
            scene=scene, reason=base_reason, classification=classification
        )

    miss_str = ", ".join(sorted(missing)) if missing else "unknown"
    # Attempt downgrade to operator_mode if (a) it's not the same scene and
    # (b) the node supports it.
    if scene != "operator_mode":
        ok2, _ = node_supports(node, "operator_mode")
        if ok2:
            return SceneDecision(
                scene="operator_mode",
                reason=(
                    f"{base_reason}; downgraded from {scene!r} "
                    f"(missing: {miss_str})"
                ),
                classification=classification,
            )

    return SceneDecision(
        scene=None,
        reason=(
            f"{base_reason}; scene {scene!r} unsupported by {node_id!r} "
            f"(missing: {miss_str})"
        ),
        classification=classification,
    )


# Hint aliases. Keep tiny.
_HINT_ALIASES = {
    "operator": "operator_mode",
    "operator_mode": "operator_mode",
    "ops": "operator_mode",
    "builder": "builder_mode",
    "builder_mode": "builder_mode",
    "dev": "builder_mode",
    "code": "builder_mode",
    "full": "full_station",
    "full_station": "full_station",
    "all": "full_station",
}

# Scenes considered "safe under degradation" — minimal side effects.
_DEGRADED_SAFE_SCENES = frozenset({"operator_mode"})


@dataclass
class SceneDecision:
    """The result of select_scene(). scene=None means 'do not open a scene'."""

    scene: Optional[str]
    reason: str
    classification: str  # READY | DEGRADED | UNAVAILABLE | UNKNOWN

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene": self.scene,
            "reason": self.reason,
            "classification": self.classification,
        }


def _resolve_classification(
    readiness: Union[StationReadiness, str, None],
) -> str:
    if readiness is None:
        return "UNKNOWN"
    if isinstance(readiness, StationReadiness):
        return readiness.classification
    s = str(readiness).strip().upper()
    if s in {READY, DEGRADED, UNAVAILABLE}:
        return s
    return "UNKNOWN"


def _normalize_hint(requested_mode: Optional[str]) -> Optional[str]:
    if not requested_mode:
        return None
    key = str(requested_mode).strip().lower()
    if not key:
        return None
    # Direct alias hit.
    if key in _HINT_ALIASES:
        return _HINT_ALIASES[key]
    # Direct registry hit (allows future-added scenes without alias edits).
    if get_scene(key) is not None:
        return key
    return None


def select_scene(
    node_id: str,
    readiness: Union[StationReadiness, str, None] = None,
    requested_mode: Optional[str] = None,
) -> SceneDecision:
    """
    Deterministic scene selection. Never raises.

    `node_id` is accepted for parity with future per-node policy refinement;
    it is currently used only for traceability in the reason string.
    """
    classification = _resolve_classification(readiness)
    hint = _normalize_hint(requested_mode)

    # 1. UNAVAILABLE → never open a scene.
    if classification == UNAVAILABLE:
        return SceneDecision(
            scene=None,
            reason=f"node {node_id!r} UNAVAILABLE — no scene",
            classification=classification,
        )

    # 2. UNKNOWN readiness — treat as too risky to bring a scene up.
    if classification == "UNKNOWN":
        if hint is not None:
            # Operator explicitly asked → honor only if scene exists.
            if get_scene(hint) is not None:
                return SceneDecision(
                    scene=hint,
                    reason=f"explicit hint {hint!r} despite unknown readiness",
                    classification=classification,
                )
        return SceneDecision(
            scene=None,
            reason="readiness unknown — declining to auto-open a scene",
            classification=classification,
        )

    # 3. DEGRADED → restrict to safe scenes, capability-gated.
    if classification == DEGRADED:
        if hint is not None and hint in _DEGRADED_SAFE_SCENES:
            return _capability_guarded(
                node_id, hint,
                f"degraded — honoring safe hint {hint!r}",
                classification,
            )
        if hint is not None:
            return _capability_guarded(
                node_id, "operator_mode",
                f"degraded — downgraded hint {hint!r} to operator_mode",
                classification,
            )
        return _capability_guarded(
            node_id, "operator_mode",
            "degraded — defaulting to operator_mode",
            classification,
        )

    # 4. READY → honor hint if any, else default to operator_mode.
    if classification == READY:
        if hint is not None:
            return _capability_guarded(
                node_id, hint,
                f"ready — honoring hint {hint!r}",
                classification,
            )
        return _capability_guarded(
            node_id, "operator_mode",
            "ready — default operator_mode",
            classification,
        )

    # Catch-all: no scene.
    return SceneDecision(
        scene=None,
        reason=f"no rule matched (classification={classification!r})",
        classification=classification,
    )
