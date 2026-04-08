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
    ok_count = sum(1 for s in fetched if s.status is FetchStatus.OK)

    artifact = build_artifact(
        tool_slug=request.tool_slug,
        mode=request.mode,
        plan=plan,
        fetched=fetched,
    )
    paths = write_artifact(run_dir, artifact, plan)

    handoff_report = apply_safe_metadata(request.tool_slug, artifact)
    (run_dir / "handoff.json").write_text(
        json.dumps(handoff_report, indent=2), encoding="utf-8"
    )

    status = _derive_status(len(fetched), ok_count)

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

    manifest = {
        "schema_version": 1,
        "request": request.to_dict(),
        "status": status.value,
        "run_dir": str(run_dir),
        "generated_at": artifact.generated_at,
        "plan_size": len(plan.sources),
        "fetched": len(fetched),
        "fetched_ok": ok_count,
        "artifact_path": paths["artifact_path"],
        "summary_path": paths["summary_path"],
        "sources_path": paths["sources_path"],
        "handoff": handoff_report,
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
