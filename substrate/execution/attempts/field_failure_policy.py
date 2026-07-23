"""Wave 2 field failure-injection policy (qualification harness only).

The failure-qualification pass must inject a GENUINE worker failure — not a
poisoned fixture — so that the graph provably FAILS the right way: task A's
first attempt runs with Edit/Write revoked, the real worker cannot commit,
verification refuses (no false Proof), C stays blocked, and a retry (A2, without
revocation) lets the graph continue.

The dispatcher's ``inject-failure`` subcommand writes a ``.inject_failure``
marker (containing the variant name) into the run's targets dir. This module is
the SINGLE reader of that marker: the field-run dispatch path calls
``disallowed_tools_for(...)`` when it builds each dispatch envelope, so the
revocation is applied at DISPATCH time (as a real tool policy on the envelope),
exactly where ``DispatchEnvelope.disallowed_tools`` is consumed by the worker.

Without this reader the marker would be a dead write and the failure pass would
silently run clean — a false green (review W1). A unit test pins that the marker
actually changes the computed policy.

Scope: qualification only. The variant is a bounded, named policy; there is no
general "inject failure" capability in the runtime.
"""

from __future__ import annotations

import os
from pathlib import Path

# The exact revocation for the tools-revoked-a variant: A's implementation
# worker loses every file-mutation tool, so it genuinely cannot produce a commit.
_TOOLS_REVOKED = ["Edit", "Write", "MultiEdit", "NotebookEdit"]

_MARKER_NAME = ".inject_failure"


def read_variant(targets_dir: str | os.PathLike[str]) -> str:
    """Return the armed failure variant for a run ('' if none/clean)."""
    marker = Path(targets_dir) / _MARKER_NAME
    try:
        variant = marker.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""
    return variant if variant and variant != "clean" else ""


def disallowed_tools_for(
    *, targets_dir: str | os.PathLike[str], task_id: str, attempt_number: int,
) -> list[str]:
    """Tool revocations to apply to THIS dispatch, honoring the armed variant.

    ``tools-revoked-a`` revokes file-mutation tools for task A's FIRST attempt
    only (``attempt_number == 1``). The retry (attempt 2+) runs unrevoked so the
    graph can recover — this is what proves retry-as-new-attempt works. Any other
    task, later attempt, or the clean variant → no revocation.
    """
    variant = read_variant(targets_dir)
    if variant != "tools-revoked-a":
        return []
    # Task A is the backend implementation task. Match by the canonical task id
    # the fixture/plan uses for A (the field harness names it so it is
    # identifiable — a leading 'A'/'wp-a'/'…-a' segment). Be permissive on form
    # but strict on "is this task A's first attempt".
    tid = (task_id or "").lower()
    is_task_a = tid == "a" or tid.endswith("-a") or tid == "wp-a" or tid.startswith("a-")
    if is_task_a and attempt_number == 1:
        return list(_TOOLS_REVOKED)
    return []


__all__ = ["read_variant", "disallowed_tools_for"]
