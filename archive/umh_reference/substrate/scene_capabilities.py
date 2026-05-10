"""
Scene → capability requirements — tiny explicit mapping.

Scenes in `scenes.SCENE_REGISTRY` are ordered recipes of SafeActions. Each
action implicitly needs a node capability to execute meaningfully:

    SPEAK_TEXT  → audio_output  (stdout fallback exists but the *intent* is audio)
    PLAY_SOUND  → audio_output
    OPEN_URL    → browser_control
    LAUNCH_APP  → full_computer_control
    OPEN_SCENE  → (recursive; resolved by walking the inner steps)

This module derives the capability requirement set for each scene by walking
its steps at import time and freezing the result. No runtime configuration,
no scoring — just a small lookup table so scene_policy can ask:

    "does this node support every capability this scene requires?"

Design rules:
  - Deterministic. Frozen at import, explainable in one glance.
  - Explicit. Action-kind → capability map lives right here, not hidden in
    the daemon.
  - Conservative. Unknown action kinds degrade to "no requirement" so an
    unmapped step never spuriously blocks scene selection.
  - Backward compatible. Nothing in this module edits scenes, nodes, or
    capability definitions.

Public API:
    requirements_for(scene_name) -> set[str]
    node_supports(node, scene_name) -> tuple[bool, set[str]]
    scene_requirements_inventory() -> dict[str, list[str]]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Optional

from umh.substrate.actions import ActionKind
from umh.substrate.capabilities import Capability
from umh.substrate.scenes import SCENE_REGISTRY, Scene

if TYPE_CHECKING:  # avoid runtime cycle
    from umh.substrate.nodes import Node


# ─── Action kind → required capability (equivalence sets) ──────────────────
#
# Two capability vocabularies coexist in EOS today:
#   1. The canonical `Capability` enum in capabilities.py (browser_control,
#      full_computer_control, audio_output, …).
#   2. The station_daemon's historical slugs (url_open, app_launch,
#      scene_bootstrap, text_to_speech, …).
#
# Rather than break one vocabulary to privilege the other, each action kind
# maps to a *set* of acceptable capability slugs. A node satisfies the
# requirement if it advertises ANY slug from the set. This is deliberately
# generous — future passes can tighten it once the daemon migrates to the
# canonical enum.
_ACTION_REQUIRES: dict[ActionKind, frozenset[str]] = {
    ActionKind.SPEAK_TEXT: frozenset({
        Capability.AUDIO_OUTPUT.value, "text_to_speech",
    }),
    ActionKind.PLAY_SOUND: frozenset({
        Capability.AUDIO_OUTPUT.value,
    }),
    ActionKind.OPEN_URL: frozenset({
        Capability.BROWSER_CONTROL.value, "url_open",
    }),
    ActionKind.LAUNCH_APP: frozenset({
        Capability.FULL_COMPUTER_CONTROL.value, "app_launch",
    }),
    # OPEN_SCENE is recursive — resolved below. No direct requirement.
    ActionKind.OPEN_SCENE: frozenset(),
}


# Each scene maps to a list of frozensets — one per step that carried a
# requirement. When checking a node, EVERY step's requirement must be
# satisfied by at least one of the node's advertised slugs.
def _walk_scene(scene: Scene, _seen: Optional[set[str]] = None) -> list[frozenset[str]]:
    seen = _seen if _seen is not None else set()
    if scene.name in seen:
        return []
    seen.add(scene.name)

    out: list[frozenset[str]] = []
    for step in scene.steps:
        kind = step.kind
        if kind == ActionKind.OPEN_SCENE:
            inner_name = (step.payload or {}).get("scene")
            if isinstance(inner_name, str):
                inner = SCENE_REGISTRY.get(inner_name)
                if inner is not None:
                    out.extend(_walk_scene(inner, seen))
            continue
        req = _ACTION_REQUIRES.get(kind)
        if req:
            out.append(req)
    return out


_SCENE_REQUIREMENTS: dict[str, tuple[frozenset[str], ...]] = {
    name: tuple(_walk_scene(scene))
    for name, scene in SCENE_REGISTRY.items()
}


# ─── Public API ──────────────────────────────────────────────────────────────

def requirements_for(scene_name: str) -> set[str]:
    """
    Flat union of every capability slug this scene mentions, across all
    accepted vocabularies. Useful for display; NOT the check function.
    Unknown scene → empty set.
    """
    reqs = _SCENE_REQUIREMENTS.get(scene_name, tuple())
    out: set[str] = set()
    for req in reqs:
        out |= set(req)
    return out


def node_supports(
    node: "Node",
    scene_name: str,
) -> tuple[bool, set[str]]:
    """
    Check whether `node` can satisfy every step of `scene_name`.

    For each step, the node must advertise AT LEAST ONE of the acceptable
    capability slugs for that step. The daemon and the canonical Capability
    enum use different vocabularies, and this is how we bridge them
    without privileging one.

    Returns (ok, missing). `missing` lists one representative slug per
    unsatisfied step (the canonical enum value when possible), so operator
    reports can show which capabilities were the blocker.

    Tolerates unknown scenes (treats as no requirement → ok). Tolerates
    None node by treating every step as unsatisfied.
    """
    reqs = _SCENE_REQUIREMENTS.get(scene_name, tuple())
    if not reqs:
        return True, set()

    node_caps: Iterable[str] = getattr(node, "capabilities", None) or [] if node else []
    have = {str(c) for c in node_caps}

    missing: set[str] = set()
    for step_req in reqs:
        if not (step_req & have):
            # Pick a stable, human-readable representative — prefer the
            # canonical enum vocabulary when the step lists one.
            canonical = next(
                (s for s in sorted(step_req) if s in Capability.all_slugs()),
                None,
            )
            missing.add(canonical or sorted(step_req)[0])

    return (not missing), missing


def scene_requirements_inventory() -> dict[str, list[str]]:
    """
    Debug helper: {scene_name: sorted list of capability slugs}. Shows the
    flat union across all accepted vocabularies — useful in operator
    reports so it's obvious why a scene was downgraded.
    """
    return {
        name: sorted(requirements_for(name))
        for name in _SCENE_REQUIREMENTS
    }
