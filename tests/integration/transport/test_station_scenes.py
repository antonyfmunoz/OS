"""Smoke tests for enhanced eos_ai.substrate.scenes.

Validates:
  1.  test_scene_registry          — all 3 scenes exist
  2.  test_scene_preferences       — scenes have preference fields
  3.  test_list_scenes             — list_scenes returns correct names
  4.  test_builder_mode_scene      — builder_mode has expected content
  5.  test_get_scene_not_found     — unknown scene returns None

Run directly:
    python3 tests/substrate/test_station_scenes.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate.scenes import (  # noqa: E402
    SCENE_REGISTRY,
    Scene,
    get_scene,
    list_scenes,
)

_PASS = 0
_FAIL = 0


def _report(name: str, passed: bool, detail: str = "") -> None:
    global _PASS, _FAIL  # noqa: PLW0603
    tag = "PASS" if passed else "FAIL"
    if not passed:
        _FAIL += 1
    else:
        _PASS += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


def test_scene_registry() -> None:
    print("\n── Test: scene registry ──")
    _report("operator_mode exists", get_scene("operator_mode") is not None)
    _report("builder_mode exists", get_scene("builder_mode") is not None)
    _report("full_station exists", get_scene("full_station") is not None)


def test_scene_preferences() -> None:
    print("\n── Test: scene preferences ──")
    builder = get_scene("builder_mode")
    assert builder is not None
    _report("has preferred_control_mode", hasattr(builder, "preferred_control_mode"))
    _report("has preferred_tts_enabled", hasattr(builder, "preferred_tts_enabled"))
    _report("has preferred_wake_enabled", hasattr(builder, "preferred_wake_enabled"))
    _report("has preferred_workspace", hasattr(builder, "preferred_workspace"))

    _report(
        "builder control_mode is assisted",
        builder.preferred_control_mode == "assisted",
    )
    _report(
        "builder workspace is builder",
        builder.preferred_workspace == "builder",
    )

    full = get_scene("full_station")
    assert full is not None
    _report("full_station control_mode", full.preferred_control_mode == "assisted")
    _report("full_station tts", full.preferred_tts_enabled is True)
    _report("full_station wake", full.preferred_wake_enabled is True)

    operator = get_scene("operator_mode")
    assert operator is not None
    _report(
        "operator workspace is product",
        operator.preferred_workspace == "product",
    )


def test_list_scenes() -> None:
    print("\n── Test: list_scenes ──")
    names = list_scenes()
    _report("has 3 scenes", len(names) == 3)
    _report("operator_mode in list", "operator_mode" in names)
    _report("builder_mode in list", "builder_mode" in names)
    _report("full_station in list", "full_station" in names)


def test_builder_mode_scene() -> None:
    print("\n── Test: builder_mode scene content ──")
    builder = get_scene("builder_mode")
    assert builder is not None
    _report("has steps", len(builder.steps) > 0)
    _report(
        "preferred_workspace is builder",
        builder.preferred_workspace == "builder",
    )


def test_get_scene_not_found() -> None:
    print("\n── Test: unknown scene returns None ──")
    _report("not_found is None", get_scene("nonexistent_scene") is None)


if __name__ == "__main__":
    print("=" * 60)
    print("station_scenes smoke tests")
    print("=" * 60)
    test_scene_registry()
    test_scene_preferences()
    test_list_scenes()
    test_builder_mode_scene()
    test_get_scene_not_found()
    print(f"\n{'=' * 60}")
    print(f"Results: {_PASS} passed, {_FAIL} failed")
    print("=" * 60)
    raise SystemExit(1 if _FAIL else 0)
