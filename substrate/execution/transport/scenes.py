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
from typing import Any, Optional

from substrate.execution.transport.actions import ActionKind


@dataclass(frozen=True)
class SceneStep:
    """A single safe action inside a scene."""

    kind: ActionKind
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Scene:
    """A workstation bootstrap recipe with optional preference hints.

    Preference fields (all Optional) suggest what the station should
    configure when this scene is activated.  None means "don't change."

    Behavioral fields control daemon posture during this scene:
    - action_constraints: set of ActionKind values allowed; None = all
    - wake_behavior: "enabled" | "disabled" | None (don't change)
    """

    name: str
    description: str
    steps: tuple[SceneStep, ...]
    preferred_control_mode: Optional[str] = None
    preferred_tts_enabled: Optional[bool] = None
    preferred_wake_enabled: Optional[bool] = None
    preferred_workspace: Optional[str] = None
    action_constraints: Optional[frozenset[str]] = None
    wake_behavior: Optional[str] = None


def _scene(
    name: str,
    description: str,
    *steps: SceneStep,
    preferred_control_mode: Optional[str] = None,
    preferred_tts_enabled: Optional[bool] = None,
    preferred_wake_enabled: Optional[bool] = None,
    preferred_workspace: Optional[str] = None,
    action_constraints: Optional[frozenset[str]] = None,
    wake_behavior: Optional[str] = None,
) -> tuple[str, Scene]:
    return name, Scene(
        name=name,
        description=description,
        steps=tuple(steps),
        preferred_control_mode=preferred_control_mode,
        preferred_tts_enabled=preferred_tts_enabled,
        preferred_wake_enabled=preferred_wake_enabled,
        preferred_workspace=preferred_workspace,
        action_constraints=action_constraints,
        wake_behavior=wake_behavior,
    )


SCENE_REGISTRY: dict[str, Scene] = dict(
    [
        _scene(
            "operator_mode",
            "Lightweight ops dashboard — audible ack + EOS operator URL.",
            SceneStep(ActionKind.SPEAK_TEXT, {"text": "Operator mode engaged."}),
            SceneStep(ActionKind.OPEN_URL, {"url": "https://github.com/antonyfmunoz"}),
            preferred_control_mode="assisted",
            preferred_workspace="product",
        ),
        _scene(
            "builder_mode",
            "Developer loadout — editor plus code host.",
            SceneStep(ActionKind.SPEAK_TEXT, {"text": "Builder mode engaged."}),
            SceneStep(ActionKind.LAUNCH_APP, {"app_id": "vscode"}),
            SceneStep(ActionKind.OPEN_URL, {"url": "https://github.com/antonyfmunoz"}),
            preferred_control_mode="assisted",
            preferred_workspace="builder",
        ),
        _scene(
            "full_station",
            "Full workstation bring-up — ops dashboard and builder loadout.",
            SceneStep(ActionKind.SPEAK_TEXT, {"text": "Full station bring-up."}),
            SceneStep(ActionKind.LAUNCH_APP, {"app_id": "vscode"}),
            SceneStep(ActionKind.OPEN_URL, {"url": "https://github.com/antonyfmunoz"}),
            SceneStep(ActionKind.OPEN_URL, {"url": "https://www.notion.so"}),
            preferred_control_mode="assisted",
            preferred_tts_enabled=True,
            preferred_wake_enabled=True,
            preferred_workspace="builder",
        ),
        _scene(
            "founder_mode",
            "Founder strategic mode — CRM, analytics, and full voice.",
            SceneStep(ActionKind.SPEAK_TEXT, {"text": "Founder mode engaged."}),
            SceneStep(ActionKind.OPEN_URL, {"url": "https://www.notion.so"}),
            preferred_control_mode="full",
            preferred_tts_enabled=True,
            preferred_wake_enabled=True,
            preferred_workspace="product",
            wake_behavior="enabled",
        ),
        _scene(
            "deep_work",
            "Focus block — suppress non-critical, disable wake.",
            SceneStep(
                ActionKind.SPEAK_TEXT, {"text": "Deep work. Notifications suppressed."}
            ),
            preferred_control_mode="assisted",
            preferred_tts_enabled=False,
            preferred_wake_enabled=False,
            preferred_workspace="builder",
            wake_behavior="disabled",
        ),
        _scene(
            "voice_session",
            "Voice-first interaction — TTS and wake enabled, minimal UI.",
            SceneStep(ActionKind.SPEAK_TEXT, {"text": "Voice session active."}),
            preferred_control_mode="full",
            preferred_tts_enabled=True,
            preferred_wake_enabled=True,
            wake_behavior="enabled",
        ),
        _scene(
            "idle",
            "Idle station — no apps launched, passive monitoring only.",
            # No steps — pure posture change
            preferred_control_mode="passive",
            preferred_tts_enabled=False,
            preferred_wake_enabled=False,
            wake_behavior="disabled",
        ),
        _scene(
            "overnight",
            "Overnight mode — autonomous execution, no operator interaction.",
            # No steps — pure posture change
            preferred_control_mode="passive",
            preferred_tts_enabled=False,
            preferred_wake_enabled=False,
            wake_behavior="disabled",
        ),
    ]
)


def get_scene(name: str) -> Scene | None:
    return SCENE_REGISTRY.get(name)


def list_scenes() -> list[str]:
    return list(SCENE_REGISTRY.keys())
