"""Wave 2 field failure-injection policy (qualification harness only).

The failure-qualification pass must inject a GENUINE worker failure — not a
poisoned fixture — so the graph provably fails the right way: the BACKEND task's
first attempt runs with its file-mutation tools revoked, the real worker cannot
commit, verification refuses (no Proof), C stays blocked, and a retry (A2,
unrevoked) lets the graph continue.

Targeting is by EXACT CANONICAL TASK ID (finding C2)
-----------------------------------------------------
The previous implementation pattern-matched imagined identifiers
(``tid == "a"``, ``tid.endswith("-a")``, …). Real packets are minted as
``wp-<uuid4().hex[:12]>`` by ``WorkPacket``, and a hex12 suffix contains no
``-``, so **0 of 2000 real ids matched** — arming the variant revoked nothing and
the failure pass silently ran clean. That is exactly the false green this module
exists to prevent.

The harness now records a SCENARIO MAP of the actual materialized packet ids at
fixture/plan creation:

    {"backend_task_id": "wp-3f9c1ab77e21",
     "frontend_task_id": "wp-…", "integration_task_id": "wp-…",
     "verification_task_id": "wp-…"}

and the marker names the exact task it targets. Matching is equality against a
recorded id — never a pattern.

Fail closed: if a ``tools-revoked-*`` variant is armed but the scenario map is
missing or does not name the target, ``arming_is_valid()`` reports False and the
run must be treated as INVALID rather than green — an armed failure that never
fired must never be mistaken for a recovered one.

Scope: qualification only. There is no general "inject failure" capability in the
runtime.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# The exact revocation for the tools-revoked-backend variant. Bash is included:
# with only Edit/Write/MultiEdit/NotebookEdit revoked a CLI worker can still
# `bash -c 'cat > file'` and commit, so the "genuine failure" would not be
# genuine (review W9).
_TOOLS_REVOKED = ["Edit", "Write", "MultiEdit", "NotebookEdit", "Bash"]

_MARKER_NAME = ".inject_failure"
_SCENARIO_NAME = "scenario_map.json"

# Variant name. The legacy spelling is accepted so an existing runbook/CLI does
# not silently arm nothing, but it resolves through the scenario map exactly the
# same way — there is no id pattern matching on any path.
_VARIANT_BACKEND = "tools-revoked-backend"
_VARIANT_LEGACY = "tools-revoked-a"
_REVOKING_VARIANTS = frozenset({_VARIANT_BACKEND, _VARIANT_LEGACY})

_SCENARIO_KEYS = (
    "backend_task_id",
    "frontend_task_id",
    "integration_task_id",
    "verification_task_id",
)


def scenario_map_path(targets_dir: str | os.PathLike[str]) -> Path:
    return Path(targets_dir) / _SCENARIO_NAME


def write_scenario_map(targets_dir: str | os.PathLike[str], mapping: dict[str, str]) -> Path:
    """Persist the run's canonical task identities.

    Called once the fixture Plan has materialized its WorkPackets, so the harness
    knows the REAL ``wp-*`` ids it must target.
    """
    path = scenario_map_path(targets_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    recorded = {k: str(mapping.get(k, "") or "") for k in _SCENARIO_KEYS}
    path.write_text(json.dumps(recorded, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_scenario_map(targets_dir: str | os.PathLike[str]) -> dict[str, str]:
    """Return the run's canonical task identities ({} when absent/unreadable)."""
    try:
        data = json.loads(scenario_map_path(targets_dir).read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: str(v) for k, v in data.items() if isinstance(v, str) and v}


def read_variant(targets_dir: str | os.PathLike[str]) -> str:
    """Return the armed failure variant for a run ('' if none/clean)."""
    marker = Path(targets_dir) / _MARKER_NAME
    try:
        variant = marker.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""
    return variant if variant and variant != "clean" else ""


def target_task_id(targets_dir: str | os.PathLike[str]) -> str:
    """The exact canonical task id the armed variant targets ('' if none)."""
    if read_variant(targets_dir) not in _REVOKING_VARIANTS:
        return ""
    return read_scenario_map(targets_dir).get("backend_task_id", "")


def arming_is_valid(targets_dir: str | os.PathLike[str]) -> tuple[bool, str]:
    """Is the armed failure variant actually able to fire? ``(ok, reason)``.

    A revoking variant with no scenario map — or one whose ``backend_task_id`` is
    absent — CANNOT fire. The run must then be reported INVALID, never green:
    that combination is precisely the silent false green of finding C2.
    """
    variant = read_variant(targets_dir)
    if not variant:
        return True, "no failure variant armed (clean run)"
    if variant not in _REVOKING_VARIANTS:
        return False, f"unknown failure variant {variant!r}"
    mapping = read_scenario_map(targets_dir)
    if not mapping:
        return False, (
            f"variant {variant!r} armed but no {_SCENARIO_NAME} exists — the "
            f"injection cannot target a real task and would silently run clean"
        )
    if not mapping.get("backend_task_id"):
        return False, (
            f"variant {variant!r} armed but {_SCENARIO_NAME} has no "
            f"backend_task_id — nothing to revoke"
        )
    return True, f"variant {variant!r} targets {mapping['backend_task_id']}"


def disallowed_tools_for(
    *,
    targets_dir: str | os.PathLike[str],
    task_id: str,
    attempt_number: int,
) -> list[str]:
    """Tool revocations for THIS dispatch, honoring the armed variant.

    Revokes file-mutation tools for the BACKEND task's FIRST attempt only —
    matched by EQUALITY against the recorded canonical id, never by pattern. The
    retry (attempt 2+) runs unrevoked so the graph can recover, which is what
    proves retry-as-new-attempt works.
    """
    target = target_task_id(targets_dir)
    if not target or not task_id:
        return []
    if task_id == target and int(attempt_number) == 1:
        return list(_TOOLS_REVOKED)
    return []


def injection_fired(dispatched_envelopes: list[Any]) -> bool:
    """Did the armed injection actually reach a dispatch?

    ``dispatched_envelopes`` are objects/dicts carrying ``disallowed_tools``. The
    qualification asserts this is True for a failure pass — an armed variant that
    produced no revoked dispatch means the pass proved nothing.
    """
    for env in dispatched_envelopes or []:
        tools = (
            env.get("disallowed_tools")
            if isinstance(env, dict)
            else getattr(env, "disallowed_tools", None)
        )
        if tools:
            return True
    return False


__all__ = [
    "arming_is_valid",
    "disallowed_tools_for",
    "injection_fired",
    "read_scenario_map",
    "read_variant",
    "scenario_map_path",
    "target_task_id",
    "write_scenario_map",
]
