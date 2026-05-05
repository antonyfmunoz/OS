"""Tool Mastery Engine / Manager integration for the Control Plane.

Two concerns live here:

    1. Advisory skill search (legacy) — `query_relevant_skills` shells
       out to scripts/query_skills.py so the Control Plane's pre-execute
       hook can attach a "is there a relevant skill for this?" hint to
       every action result. This is the advisory path that has existed
       since Phase 1. It never fails loudly — TME is advisory.

    2. Active mastery assurance (new) — `ensure_tool_mastery` calls into
       `core.tool_mastery_manager.ensure_mastery`, which evaluates
       coverage, scaffolds missing skills, and queues research / refresh
       / repair work through the Control Plane itself. This replaces
       the old stub behaviour where TME integration was purely advisory.

Both entry points stay tolerant of failure. The Control Plane imports
`query_relevant_skills` at module load time, so an exception here would
break every action in the system — `ensure_tool_mastery` catches
everything and returns a structured failure dict instead of raising.
"""

from __future__ import annotations

import subprocess
from typing import Any

QUERY_SKILLS_CLI = "/opt/OS/scripts/query_skills.py"


def query_relevant_skills(term: str, *, timeout: int = 10) -> dict:
    """Run `query_skills.py search <term>` and return a dict with the raw output.

    Never raises — TME is advisory, not load-bearing for Control Plane v1.
    """
    try:
        proc = subprocess.run(
            ["python3", QUERY_SKILLS_CLI, "search", term],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except FileNotFoundError:
        return {"ok": False, "error": f"{QUERY_SKILLS_CLI} not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"query_skills timed out after {timeout}s"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def ensure_tool_mastery(tool: str, *, dry_run: bool = False) -> dict[str, Any]:
    """Active mastery assurance for a tool.

    Delegates to `core.tool_mastery_manager.ensure_mastery`. Import is
    deferred to call time so module-load remains side-effect-free and
    circular imports are impossible (the Manager itself depends on
    `control_plane.run_action`).

    Returns the EnsureResult as a dict, or `{"ok": False, "error": ...}`
    on any failure. Never raises — TME integration stays advisory from
    the Control Plane's point of view even when it now has teeth.
    """
    try:
        from core.tool_mastery_manager.ensure import ensure_mastery

        result = ensure_mastery(tool, dry_run=dry_run)
        payload = result.to_dict()
        payload["ok"] = True
        return payload
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def ensure_mastery_before_tool_execution(
    tool_name: str,
    *,
    pack_exists: bool = False,
    pack_text: str = "",
    last_researched: str | None = None,
    speed_category: str = "medium",
    tier: str = "standard",
    founder_waiver: bool = False,
) -> dict[str, Any]:
    """Mastery Assurance Gate — blocks tool execution without a fresh pack.

    Combines the existing ensure_tool_mastery flow with the new
    mastery_assurance contract. Returns the MasteryAssuranceDecision
    as a dict, or ``{"ok": False, "error": ...}`` on failure.
    Never raises.
    """
    try:
        from core.tool_mastery_manager.mastery_assurance import (
            ensure_mastery_before_execution,
        )

        decision = ensure_mastery_before_execution(
            tool_name=tool_name,
            pack_exists=pack_exists,
            pack_text=pack_text,
            last_researched=last_researched,
            speed_category=speed_category,
            tier=tier,
            founder_waiver=founder_waiver,
        )
        payload = decision.to_dict()
        payload["ok"] = True
        return payload
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def resolve_mastery_for_user_intent(
    text: str,
) -> dict[str, Any]:
    """Natural language tool/capability/runtime detection.

    Wraps resolve_mastery_for_task for Control Plane callers.
    Never raises.
    """
    try:
        from core.tool_mastery_manager.tool_mastery_resolver import (
            resolve_mastery_for_task,
        )

        resolution = resolve_mastery_for_task(text)
        payload = resolution.to_dict()
        payload["ok"] = True
        return payload
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
