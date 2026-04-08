"""Safe metadata handoff for the Tool Mastery Research Agent.

The only thing this module is allowed to mutate is existing SKILL.md
frontmatter fields that can be derived unambiguously from the research
run:

    - source_url        (from the top-priority successful fetch)
    - last_researched   (today's UTC date)

It will NEVER:
    - create a SKILL.md (scaffolding is the Manager's job)
    - touch references/best_practices.md
    - invent sdk_version / api_version values
    - write narrative prose

If the skill file does not exist, handoff is a no-op with an
explanatory note. This keeps the "no fabricated mastery" invariant
intact.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .models import FetchedSource, FetchStatus, ResearchArtifact
from .paths import SKILLS_TOOLS_DIR


def _top_source_url(artifact: ResearchArtifact) -> str | None:
    """Pick the first successfully fetched source. Preserves plan order,
    which already encodes our tier preference."""

    for s in artifact.sources:
        if s.status is FetchStatus.OK:
            return s.ref.url
    return None


def _update_frontmatter_field(text: str, key: str, value: str) -> tuple[str, bool]:
    """Update ``key: value`` inside a leading ``---`` frontmatter block.

    Returns (new_text, changed). If the key does not exist inside the
    frontmatter, the text is returned unchanged — we never invent new
    fields in this safe-update path.
    """

    if not text.startswith("---"):
        return text, False

    # locate end of frontmatter
    end = text.find("\n---", 3)
    if end == -1:
        return text, False
    head = text[: end + 1]
    tail = text[end + 1 :]

    lines = head.split("\n")
    changed = False
    for i, line in enumerate(lines):
        # match "key:" possibly followed by value (quoted or not)
        stripped = line.lstrip()
        if stripped.startswith(f"{key}:"):
            indent = line[: len(line) - len(stripped)]
            lines[i] = f'{indent}{key}: "{value}"'
            changed = True
            break
    if not changed:
        return text, False
    return "\n".join(lines) + tail, True


def apply_safe_metadata(
    tool_slug: str,
    artifact: ResearchArtifact,
) -> dict[str, object]:
    """Apply source_url + last_researched to an existing SKILL.md.

    Returns a small report describing what (if anything) changed.
    """

    report: dict[str, object] = {
        "tool_slug": tool_slug,
        "skill_md_exists": False,
        "updated_fields": [],
        "skipped_reason": None,
    }

    skill_path = SKILLS_TOOLS_DIR / tool_slug / "SKILL.md"
    if not skill_path.is_file():
        report["skipped_reason"] = f"no SKILL.md at {skill_path}"
        return report
    report["skill_md_exists"] = True

    source_url = _top_source_url(artifact)
    if not source_url:
        report["skipped_reason"] = "no successful fetches — nothing to write"
        return report

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    original = skill_path.read_text(encoding="utf-8")
    text = original
    updated: list[str] = []

    text, changed = _update_frontmatter_field(text, "source_url", source_url)
    if changed:
        updated.append("source_url")

    text, changed = _update_frontmatter_field(text, "last_researched", today)
    if changed:
        updated.append("last_researched")

    if text != original:
        skill_path.write_text(text, encoding="utf-8")

    report["updated_fields"] = updated
    if not updated:
        report["skipped_reason"] = (
            "frontmatter did not contain source_url or last_researched keys — "
            "no new fields invented"
        )
    return report
