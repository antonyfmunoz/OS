"""
Ritual hint inference — infer a scene hint when the operator did not
supply one, using only deterministic signals already present in the
ritual history and node registry.

Why this exists
---------------
RitualPolicy.open_scene was the last manual knob in the open_day path.
Operators had to know in advance which scene to select. This module
removes that requirement by deriving a conservative hint from recent
history, without introducing any new runtime state or scoring model.

Signals (checked in order; first match wins):

    1. Last successful scene selected on this node from a recent
       open_day ritual (within the history window). The intuition:
       "yesterday's working setup is probably today's working setup."
    2. Node role metadata hint (e.g. metadata["preferred_scene"])
       if set. Allows operators to pin a default per node without
       touching the policy layer.
    3. Conservative default: "operator_mode". Smallest footprint,
       always compatible with every node that can speak at all.

Rules (non-negotiable):
    - An explicit hint in the policy ALWAYS overrides inference.
      This module is only ever consulted when policy.open_scene is None.
    - Inference is deterministic: same inputs → same output. No
      clocks, no random, no LLMs.
    - Inference never raises. Missing data degrades to the default.
    - Inference never mutates state.
    - Inference is explainable: returns a trace string so the body
      action record can show WHY a hint was chosen.

Public API:
    infer_open_scene_hint(node_id, node=None) -> InferredHint

    where InferredHint is (scene: Optional[str], reason: str, source: str).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from substrate.execution.bridge.nodes import Node, NodeRegistry


# How many recent rituals to scan when looking for "last successful scene".
# Deliberately small — this is a hint, not an analytics query.
_HISTORY_LOOKBACK = 20

# Conservative default when nothing else speaks.
_DEFAULT_HINT = "operator_mode"


@dataclass
class InferredHint:
    """Result of infer_open_scene_hint()."""

    scene: Optional[str]
    reason: str
    source: str  # "history" | "role" | "default" | "none"

    def to_dict(self) -> dict[str, Any]:
        return {"scene": self.scene, "reason": self.reason, "source": self.source}


def _last_successful_scene_for_node(node_id: str) -> Optional[str]:
    """
    Walk recent open_day rituals in reverse chronological order. Return the
    scene name of the most recent one whose body_actions include an
    `open_scene` entry with a non-failed status AND whose readiness
    snapshot (if present) was not UNAVAILABLE.

    Best-effort; never raises; bounded scan.
    """
    try:
        from substrate.execution.bridge.rituals import RitualKind, RitualRegistry
    except Exception:
        return None
    try:
        history = list(RitualRegistry.default().history())
    except Exception:
        return None

    # Most recent first.
    for ritual in reversed(history[-_HISTORY_LOOKBACK:]):
        if getattr(ritual, "kind", None) != RitualKind.OPEN_DAY:
            continue
        outputs = getattr(ritual, "outputs", {}) or {}

        # Only consider rituals that targeted THIS node. We read the
        # close_day_summary style node_id when present, otherwise fall
        # back to scanning body_actions for any action_id tied to node_id.
        # Simplest check: look at readiness snapshot's node_id, which is
        # always the node the open_day ran against.
        readiness_snap = outputs.get("readiness") or {}
        snap_node = readiness_snap.get("node_id") if isinstance(readiness_snap, dict) else None
        if snap_node and snap_node != node_id:
            continue

        # Skip rituals where readiness was clearly UNAVAILABLE — we don't
        # want to resurrect a scene that was selected against a broken node.
        if isinstance(readiness_snap, dict):
            if (readiness_snap.get("classification") or "").upper() == "UNAVAILABLE":
                continue

        body = outputs.get("body_actions") or []
        if not isinstance(body, list):
            continue

        for entry in body:
            if not isinstance(entry, dict):
                continue
            if entry.get("kind") != "open_scene":
                continue
            status = (entry.get("status") or "").lower()
            # "" (no recorded status yet) is acceptable because many rituals
            # record the proposal before the daemon resolves it. "failed"
            # and "rejected" are not acceptable.
            if status in {"failed", "rejected"}:
                continue
            scene = entry.get("detail")
            if isinstance(scene, str) and scene:
                return scene
            # Some records carry scene on a different key; tolerate.
            scene = entry.get("scene")
            if isinstance(scene, str) and scene:
                return scene
    return None


def _role_preferred_scene(node: Optional[Node]) -> Optional[str]:
    """
    If the node carries a preferred scene in metadata, return it.
    Looks at metadata keys: "preferred_scene", "default_scene".
    """
    if node is None:
        return None
    meta = getattr(node, "metadata", {}) or {}
    for key in ("preferred_scene", "default_scene"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def infer_open_scene_hint(
    node_id: str,
    *,
    node: Optional[Node] = None,
) -> InferredHint:
    """
    Infer a scene hint for an open_day ritual on `node_id`. Never raises.

    Order of signals:
        1. Most recent successful open_scene for this node.
        2. Node metadata preferred_scene / default_scene.
        3. Conservative default ("operator_mode").

    The returned InferredHint.source names which signal fired, so the
    body action record can show operators exactly why the hint was chosen.
    """
    # Resolve node lazily only if caller didn't pass one.
    resolved_node = node
    if resolved_node is None:
        try:
            resolved_node = NodeRegistry.default().get(node_id)
        except Exception:
            resolved_node = None

    # 1. History.
    try:
        last = _last_successful_scene_for_node(node_id)
    except Exception:
        last = None
    if last:
        return InferredHint(
            scene=last,
            reason=f"most recent successful open_scene on {node_id!r} was {last!r}",
            source="history",
        )

    # 2. Role metadata.
    role_hint = _role_preferred_scene(resolved_node)
    if role_hint:
        return InferredHint(
            scene=role_hint,
            reason=f"node metadata pinned preferred_scene={role_hint!r}",
            source="role",
        )

    # 3. Default.
    return InferredHint(
        scene=_DEFAULT_HINT,
        reason=f"no history or role preference — defaulting to {_DEFAULT_HINT!r}",
        source="default",
    )
