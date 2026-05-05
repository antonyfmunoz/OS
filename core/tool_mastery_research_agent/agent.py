"""Research Agent orchestrator.

Glues discovery → fetch → artifact → handoff into a single run, and
writes a run manifest so every execution is auditable.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .artifact import build_artifact, write_artifact
from .fetcher import fetch_plan
from .handoff import apply_safe_metadata
from .models import (
    FetchStatus,
    ResearchRequest,
    ResearchResult,
    ResearchStatus,
)
from .paths import RESEARCH_LOG_DIR
from .source_discovery import discover_sources


def _run_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _derive_status(fetched_count: int, ok_count: int) -> ResearchStatus:
    if fetched_count == 0:
        return ResearchStatus.NO_SOURCES
    if ok_count == 0:
        return ResearchStatus.FETCH_FAILED
    if ok_count < fetched_count:
        return ResearchStatus.PARTIAL
    return ResearchStatus.OK


AUTHOR_DISPATCHER_SCRIPT = "/opt/OS/scripts/tool_mastery_author.py"


def _queue_author_action(*, tool_slug: str, artifact_path: str) -> dict[str, object]:
    """Queue a tool_mastery.author action through the Control Plane.

    The Control Plane is the only allowed transport between the Research
    Agent and the Author Agent. We never import the Author Agent here.

    Returns a small status dict that gets embedded in the run manifest.
    Failures are captured (never raised) so a Control Plane outage cannot
    break a research run.
    """
    try:
        # Imported lazily so a CP failure cannot break module load.
        from core.action_system.control_plane import run_action

        action = run_action(
            type="run_script",
            description=(
                f"tool_mastery:author:{tool_slug} — Author skill from research artifact"
            ),
            inputs={
                "path": AUTHOR_DISPATCHER_SCRIPT,
                "args": [
                    "--tool",
                    tool_slug,
                    "--artifact",
                    artifact_path,
                ],
                # Semantic payload — read by the dispatcher's
                # --execute-author drainer when it consumes the
                # deferred queue.
                "work_type": "author",
                "tool": tool_slug,
                "artifact_path": artifact_path,
            },
            expected_output=f"Authored skill for {tool_slug}",
            risk_level="medium",
            source_agent="tool_mastery_research_agent",
            idempotency_key=f"tool_mastery:author:{tool_slug}",
            idempotency_ttl_seconds=24 * 3600,
        )
        return {
            "queued": True,
            "action_id": action.id,
            "action_status": action.status,
        }
    except Exception as e:  # pragma: no cover - defensive
        return {
            "queued": False,
            "error": f"{type(e).__name__}: {e}",
        }


def run(request: ResearchRequest) -> ResearchResult:
    """Execute a single research run end-to-end."""

    stamp = _run_stamp()
    run_dir = RESEARCH_LOG_DIR / request.tool_slug / stamp
    raw_dir = run_dir / "raw"
    run_dir.mkdir(parents=True, exist_ok=True)

    plan = discover_sources(
        request.tool_slug,
        source_hints=request.source_hints,
        official_url=request.official_url,
    )
    (run_dir / "source_plan.json").write_text(
        json.dumps(plan.to_dict(), indent=2), encoding="utf-8"
    )

    fetched = fetch_plan(plan.sources, raw_dir=raw_dir) if plan.sources else []

    artifact = build_artifact(
        tool_slug=request.tool_slug,
        mode=request.mode,
        plan=plan,
        fetched=fetched,
        run_dir=run_dir,
    )
    # Use post-filter status counts so downstream accounting reflects
    # what the Author Agent will actually see (low-signal sources
    # demoted to SKIPPED don't count as OK).
    ok_count = sum(1 for s in artifact.sources if s.status is FetchStatus.OK)
    paths = write_artifact(run_dir, artifact, plan)

    handoff_report = apply_safe_metadata(request.tool_slug, artifact)
    (run_dir / "handoff.json").write_text(
        json.dumps(handoff_report, indent=2), encoding="utf-8"
    )

    status = _derive_status(len(artifact.sources), ok_count)

    next_steps: list[str] = []
    if status is ResearchStatus.NO_SOURCES:
        next_steps.append(
            "Add a tool_doc_registry.md entry or re-run with --official-url"
        )
    elif status is ResearchStatus.FETCH_FAILED:
        next_steps.append("Inspect sources.md for per-source errors and retry")
    else:
        next_steps.extend(
            [
                f"Read raw captures under {raw_dir}",
                (
                    "Follow TME decision tree at "
                    "skills/meta/tool_mastery_engine/SKILL.md to author "
                    f"skills/tools/{request.tool_slug}/"
                ),
                (
                    f"Run: python3 scripts/verify_tool_skill.py "
                    f"--skill {request.tool_slug} (after authoring)"
                ),
            ]
        )

    # Loop closure: when we have at least the *possibility* of authoring
    # (anything other than NO_SOURCES), queue a tool_mastery.author action
    # through the Control Plane. We never invoke the Author Agent directly
    # from here — the Control Plane is the only allowed transport.
    author_handoff: dict[str, object] = {"queued": False}
    if status is not ResearchStatus.NO_SOURCES:
        author_handoff = _queue_author_action(
            tool_slug=request.tool_slug,
            artifact_path=paths["artifact_path"],
        )

    manifest = {
        "schema_version": 1,
        "request": request.to_dict(),
        "status": status.value,
        "run_dir": str(run_dir),
        "generated_at": artifact.generated_at,
        "plan_size": len(plan.sources),
        "fetched": len(fetched),
        "fetched_ok": ok_count,
        "quality": artifact.quality,
        "signal_reports": list(artifact.signal_reports),
        "artifact_path": paths["artifact_path"],
        "summary_path": paths["summary_path"],
        "sources_path": paths["sources_path"],
        "handoff": handoff_report,
        "author_handoff": author_handoff,
        "next_steps": next_steps,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    return ResearchResult(
        request=request,
        status=status,
        run_dir=str(run_dir),
        artifact_path=paths["artifact_path"],
        summary_path=paths["summary_path"],
        sources_path=paths["sources_path"],
        next_steps=next_steps,
    )
