"""
Scene registry — small, code-declared workstation bootstrap recipes.

A Scene is an ordered sequence of MVP-safe SafeAction steps that together
prepare a workstation for a particular mode of work. Scenes are NOT runtime-
definable in this pass: they are hardcoded here so the trust boundary cannot
be widened by proposing an arbitrary "scene" payload.

Each step is a `SceneStep`, a lightweight (kind, payload) pair. When the
daemon handles an OPEN_SCENE action it looks up the scene here and executes
each step in-process through its existing handler table — every step still
goes through MVP allow-list enforcement because the daemon only dispatches
kinds it knows how to handle.

Three seeded scenes:
  operator_mode — minimal: an audible ack + the operator dashboard URL
  builder_mode  — editor + GitHub
  full_station  — both of the above combined

To add a new scene: declare a new `_scene(...)` entry below. Keep them tiny.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eos_ai.substrate.actions import ActionKind


@dataclass(frozen=True)
class SceneStep:
    """A single safe action inside a scene."""

    kind: ActionKind
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Scene:
    name: str
    description: str
    steps: tuple[SceneStep, ...]


def _scene(name: str, description: str, *steps: SceneStep) -> tuple[str, Scene]:
    return name, Scene(name=name, description=description, steps=tuple(steps))


SCENE_REGISTRY: dict[str, Scene] = dict([
    _scene(
        "operator_mode",
        "Lightweight ops dashboard — audible ack + EOS operator URL.",
        SceneStep(ActionKind.SPEAK_TEXT, {"text": "Operator mode engaged."}),
        SceneStep(ActionKind.OPEN_URL, {"url": "https://github.com/antonyfmunoz"}),
    ),
    _scene(
        "builder_mode",
        "Developer loadout — editor plus code host.",
        SceneStep(ActionKind.SPEAK_TEXT, {"text": "Builder mode engaged."}),
        SceneStep(ActionKind.LAUNCH_APP, {"app_id": "vscode"}),
        SceneStep(ActionKind.OPEN_URL, {"url": "https://github.com/antonyfmunoz"}),
    ),
    _scene(
        "full_station",
        "Full workstation bring-up — ops dashboard and builder loadout.",
        SceneStep(ActionKind.SPEAK_TEXT, {"text": "Full station bring-up."}),
        SceneStep(ActionKind.LAUNCH_APP, {"app_id": "vscode"}),
        SceneStep(ActionKind.OPEN_URL, {"url": "https://github.com/antonyfmunoz"}),
        SceneStep(ActionKind.OPEN_URL, {"url": "https://www.notion.so"}),
    ),
])


def get_scene(name: str) -> Scene | None:
    return SCENE_REGISTRY.get(name)


def list_scenes() -> list[str]:
    return list(SCENE_REGISTRY.keys())
