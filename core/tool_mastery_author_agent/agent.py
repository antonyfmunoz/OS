"""Author Agent orchestrator.

Loader → mapping → drafting → reconcile → verify → final state.

Public entry: ``author(request) -> AuthorResult``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .draft import build_drafts, render_best_practices, render_skill_body
from .loader import load_artifact
from .mapping import map_sections
from .models import (
    AuthoredProvenance,
    AuthorRequest,
    AuthorResult,
    AuthorStatus,
)
from .reconcile import (
    plan_reconciliation,
    replace_body_preserving_frontmatter,
    run_scaffold,
)
from .verify import verify_skill


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _display_name(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.split("_"))


def author(request: AuthorRequest) -> AuthorResult:
    """Execute a single authoring run end-to-end."""

    result = AuthorResult(request=request, status=AuthorStatus.BLOCKED_NO_SOURCES)

    # 1. Load research artifact + raw captures.
    artifact_path = Path(request.artifact_path)
    try:
        loaded = load_artifact(artifact_path)
    except FileNotFoundError as e:
        result.notes.append(f"load failed: {e}")
        result.status = AuthorStatus.VERIFY_FAILED
        return result

    if loaded.load_errors:
        result.notes.extend(f"load warning: {e}" for e in loaded.load_errors)

    if not loaded.has_any_source:
        result.notes.append(
            "research artifact has no successfully fetched sources — nothing to author"
        )
        result.status = AuthorStatus.BLOCKED_NO_SOURCES
        _write_provenance(result, loaded.run_dir, loaded.tool_slug, [], [])
        return result

    # 2. Map sections to evidence. Keyword-based. No LLM.
    evidence = map_sections(loaded)
    drafts = build_drafts(evidence)
    sourced_count = sum(1 for d in drafts if d.sourced)
    placeholder_count = sum(1 for d in drafts if not d.sourced)

    # 3. Reconcile against on-disk state.
    plan = plan_reconciliation(
        request.tool_slug, force_rewrite=request.force_rewrite
    )

    preserved: list[str] = []
    preserve_mode = (
        plan.skill_exists
        and not plan.will_write_skill_md
        and not plan.will_write_bp_md
    )
    if preserve_mode:
        # Existing human skill — preserve everything. This is the
        # "refresh against a strong skill" path. We don't touch files;
        # the counters reflect reality (nothing authored, nothing
        # placeheld), not the hypothetical drafts we declined to use.
        result.notes.append(plan.preserved_reason)
        preserved = [d.section for d in drafts]
        result.sections_preserved = len(preserved)
        result.sections_sourced = 0
        result.sections_placeholder = 0
        result.skill_path = str(plan.skill_md) if plan.skill_exists else None
        result.best_practices_path = (
            str(plan.bp_md) if plan.bp_md.is_file() else None
        )
    else:
        # 4. Maybe scaffold, then write.
        if plan.will_scaffold and request.allow_scaffold:
            ok, msg = run_scaffold(request.tool_slug)
            result.notes.append(f"scaffold: {msg}")
            if not ok:
                result.status = AuthorStatus.VERIFY_FAILED
                _write_provenance(
                    result, loaded.run_dir, loaded.tool_slug, drafts, preserved
                )
                return result
        elif plan.will_scaffold and not request.allow_scaffold:
            result.notes.append(
                "skill missing and allow_scaffold=False — cannot proceed"
            )
            result.status = AuthorStatus.VERIFY_FAILED
            _write_provenance(
                result, loaded.run_dir, loaded.tool_slug, drafts, preserved
            )
            return result

        display = _display_name(request.tool_slug)
        generated_at = _iso_now()

        if plan.will_write_bp_md:
            bp_body = render_best_practices(
                request.tool_slug, display, drafts, generated_at
            )
            plan.bp_md.parent.mkdir(parents=True, exist_ok=True)
            plan.bp_md.write_text(bp_body, encoding="utf-8")
            result.best_practices_path = str(plan.bp_md)
            result.notes.append(f"wrote {plan.bp_md}")

        if plan.will_write_skill_md:
            skill_body = render_skill_body(request.tool_slug, display, drafts)
            replace_body_preserving_frontmatter(plan.skill_md, skill_body)
            result.skill_path = str(plan.skill_md)
            result.notes.append(f"updated body of {plan.skill_md}")
        elif plan.skill_exists:
            result.skill_path = str(plan.skill_md)

        result.sections_sourced = sourced_count
        result.sections_placeholder = placeholder_count

    # 5. Verify against the canonical verifier.
    report = verify_skill(request.tool_slug)
    result.verifier_passed = report.passed
    result.verifier_failures = list(report.failures)
    if report.error:
        result.notes.append(f"verifier error: {report.error}")

    # 6. Decide final status.
    #
    # Preserve-mode (existing human skill, untouched) + verifier pass
    # is AUTHORED_READY — the tool IS ready, the agent simply had
    # nothing to improve. The "partial" state is reserved for runs
    # where we actually wrote placeholder sections to disk.
    if not report.passed:
        result.status = AuthorStatus.VERIFY_FAILED
    elif preserve_mode:
        result.status = AuthorStatus.AUTHORED_READY
    elif placeholder_count > 0:
        result.status = AuthorStatus.AUTHORED_PARTIAL
    else:
        result.status = AuthorStatus.AUTHORED_READY

    _write_provenance(
        result, loaded.run_dir, loaded.tool_slug, drafts, preserved
    )
    return result


def _write_provenance(
    result: AuthorResult,
    run_dir: Path,
    tool_slug: str,
    drafts: list,
    preserved: list[str],
) -> None:
    """Write the authored_provenance.json sidecar next to the research artifact."""
    prov = AuthoredProvenance(
        tool_slug=tool_slug,
        authored_at=_iso_now(),
        run_dir=str(run_dir),
        drafts=list(drafts),
        preserved_sections=list(preserved),
        notes=list(result.notes),
    )
    try:
        path = run_dir / "authored_provenance.json"
        path.write_text(json.dumps(prov.to_dict(), indent=2), encoding="utf-8")
        result.provenance_path = str(path)
    except OSError as e:
        result.notes.append(f"provenance write failed: {e}")
