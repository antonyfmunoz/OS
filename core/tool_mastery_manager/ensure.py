"""ensure_mastery — the primary entry point of the Tool Mastery Manager.

For a given tool slug this function:

    1. Evaluates current coverage via the composed TME utilities.
    2. If READY → returns immediately (no side effects).
    3. If MISSING → optionally scaffolds a skeleton via scaffold_tool_skill.py
                    so there is a real file artifact, then queues a
                    `research` action through the Control Plane.
    4. If STALE → queues a `refresh` action.
    5. If INVALID → queues a `repair` action.
    6. If PARTIAL → queues a `repair` action (soft gaps are still work).

All queued actions go through `core.action_system.control_plane.run_action`
with `risk_level="medium"`. Medium-risk without `explicit_approval=True`
is the Control Plane's standard path for "persist to the deferred queue
and notify" — which IS the Manager's backlog. Nothing about the Control
Plane's invariants is bypassed.

Idempotency: the key is `tool_mastery:{work_type}:{slug}`. If a prior
call for the same tool/work is already in-flight or deferred, the
Control Plane returns a synthetic `skipped_duplicate` action and the
Manager treats it as already-queued.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from core.action_system.control_plane import run_action  # noqa: E402

from .coverage import evaluate_coverage
from .models import CoverageStatus, EnsureResult, ManagerPlan
from .paths import RESEARCH_DISPATCHER, SCAFFOLD_SCRIPT, SKILLS_TOOLS_DIR

SOURCE_AGENT = "tool_mastery_manager"


def _scaffold(slug: str) -> tuple[bool, str]:
    """Run scaffold_tool_skill.py for a missing tool.

    Returns (ok, message). We shell out rather than import so the
    scaffold script stays the single source of truth for the template
    layout, and so a scaffold failure does not raise into the Manager.
    """
    if (SKILLS_TOOLS_DIR / slug / "SKILL.md").is_file():
        return True, "skill already exists, skipping scaffold"
    if not SCAFFOLD_SCRIPT.is_file():
        return False, f"scaffold script not found at {SCAFFOLD_SCRIPT}"
    try:
        proc = subprocess.run(
            ["python3", str(SCAFFOLD_SCRIPT), slug],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return False, f"scaffold exited {proc.returncode}: {proc.stderr.strip()}"
        return True, proc.stdout.strip() or "scaffolded"
    except subprocess.TimeoutExpired:
        return False, "scaffold timed out"
    except Exception as e:
        return False, f"scaffold error: {type(e).__name__}: {e}"


def _plan_for(status: CoverageStatus, slug: str, reason: str) -> ManagerPlan | None:
    """Map a coverage status to a ManagerPlan (or None for READY)."""
    if status is CoverageStatus.READY:
        return None
    if status is CoverageStatus.MISSING:
        work_type = "research"
    elif status is CoverageStatus.STALE:
        work_type = "refresh"
    else:  # INVALID or PARTIAL
        work_type = "repair"
    return ManagerPlan(
        work_type=work_type,
        tool_slug=slug,
        reason=reason,
        script_path=str(RESEARCH_DISPATCHER),
        script_args=["--work-type", work_type, "--tool", slug],
    )


def _queue(plan: ManagerPlan, *, source_agent: str = SOURCE_AGENT) -> tuple[str | None, str | None]:
    """Push the plan through the Control Plane.

    Returns (action_id, action_status). Medium-risk actions without
    explicit_approval are auto-deferred — that is the intended
    behaviour: the Manager is writing to the existing deferred queue.
    """
    action = run_action(
        type="run_script",
        description=(
            f"tool_mastery:{plan.work_type}:{plan.tool_slug} — "
            f"{plan.reason}"
        ),
        inputs={
            "path": plan.script_path,
            "args": plan.script_args,
            # Semantic payload — picked up by resume_action / future dispatchers.
            "work_type": plan.work_type,
            "tool": plan.tool_slug,
        },
        expected_output=f"Research/refresh/repair plan for {plan.tool_slug}",
        risk_level="medium",
        source_agent=source_agent,
        idempotency_key=f"tool_mastery:{plan.work_type}:{plan.tool_slug}",
        idempotency_ttl_seconds=7 * 24 * 3600,
    )
    return action.id, action.status


def ensure_mastery(
    slug: str,
    *,
    auto_scaffold: bool = True,
    dry_run: bool = False,
    source_agent: str = SOURCE_AGENT,
) -> EnsureResult:
    """Ensure mastery coverage for `slug`. See module docstring."""
    initial = evaluate_coverage(slug)
    result = EnsureResult(
        slug=slug,
        initial_status=initial.status,
        final_status=initial.status,
    )

    if initial.status is CoverageStatus.READY:
        result.notes.append("already READY — no action")
        return result

    # --- MISSING: scaffold first so there is a file artifact ---
    if initial.status is CoverageStatus.MISSING and auto_scaffold and not dry_run:
        ok, msg = _scaffold(slug)
        result.scaffolded = ok
        result.notes.append(f"scaffold: {msg}")
        # Re-evaluate: a successful scaffold flips the tool from MISSING
        # to INVALID (the template intentionally fails the verifier
        # until best_practices is filled).
        post = evaluate_coverage(slug)
        result.final_status = post.status
        # ...but the *semantic* work is still "research a new tool", so
        # we use MISSING's plan (work_type=research) even after scaffold.
        plan = _plan_for(CoverageStatus.MISSING, slug, "scaffolded — needs initial research")
    else:
        reason = "; ".join(initial.reasons) or initial.status.value
        plan = _plan_for(initial.status, slug, reason)

    result.plan = plan

    if dry_run:
        result.notes.append("dry_run=True — no Control Plane action queued")
        return result

    if plan is None:  # defensive — should not happen if status != READY
        return result

    action_id, action_status = _queue(plan, source_agent=source_agent)
    result.action_id = action_id
    result.action_status = action_status

    # Re-evaluate once more so final_status reflects any post-scaffold
    # reality. Do NOT downgrade final_status below READY just because an
    # action was queued — queueing is additive.
    final = evaluate_coverage(slug)
    result.final_status = final.status
    return result
