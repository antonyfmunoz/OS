#!/usr/bin/env python3
"""
Promote durable knowledge from summaries into 10_Wiki/.

Reads wiki_candidates from summary frontmatter, creates wiki pages
following WIKI_RULES.md, updates index.md and log.md.
Template-based — no LLM call required.

Usage:
    python3 scripts/promote_to_wiki.py                    # scan all summaries
    python3 scripts/promote_to_wiki.py --summary <path>   # promote from one summary
    python3 scripts/promote_to_wiki.py --dry-run           # preview only
"""

import sys
import os
import re
import glob
import argparse
import logging

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

WIKI_DIR = f"{_ROOT}/10_Wiki"
SUMMARIES_DIR = f"{_ROOT}/vault/memory/summaries"
WIKI_INDEX = os.path.join(WIKI_DIR, "index.md")
WIKI_LOG = os.path.join(WIKI_DIR, "log.md")

# page_type → subdirectory name
TYPE_DIRS = {
    "concept": "concepts",
    "entity": "entities",
    "decision": "decisions",
    "synthesis": "synthesis",
    "source": "sources",
}

# page_type → index section header
TYPE_SECTIONS = {
    "concept": "## Concepts",
    "entity": "## Entities",
    "decision": "## Decisions",
    "synthesis": "## Synthesis",
    "source": "## Sources",
}


# ─── Frontmatter parsing ────────────────────────────────────────────────────


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (frontmatter_dict, body)."""
    import yaml

    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except Exception:
        fm = {}
    return fm, parts[2].strip()


def _dump_frontmatter(fm: dict, body: str) -> str:
    """Reconstruct a markdown file with YAML frontmatter."""
    import yaml

    fm_str = yaml.dump(fm, default_flow_style=False, sort_keys=False).strip()
    return f"---\n{fm_str}\n---\n\n{body}\n"


# ─── Wiki state ──────────────────────────────────────────────────────────────


def get_existing_wiki_pages() -> set[str]:
    """Return set of existing wiki page slugs (filenames without .md)."""
    pages = set()
    for dirpath, _, filenames in os.walk(WIKI_DIR):
        for fname in filenames:
            if fname.endswith(".md") and fname not in (
                "index.md",
                "log.md",
                "WIKI_RULES.md",
            ):
                pages.add(os.path.splitext(fname)[0])
    return pages


def _find_related_pages(candidate_name: str, existing: set[str]) -> list[str]:
    """Find existing wiki pages that might be related to the candidate.

    Used to satisfy the no-orphans rule — every page must link to at least one other.
    Returns list of page slugs to wikilink to.
    """
    # Simple heuristic: check for word overlap
    candidate_words = set(candidate_name.split("-"))
    related = []
    for page in existing:
        page_words = set(page.split("-"))
        if candidate_words & page_words:
            related.append(page)
    # If no overlap found, link to the most recent page or a default
    if not related and existing:
        related.append(sorted(existing)[0])
    return related[:3]


# ─── Wiki page building ─────────────────────────────────────────────────────


def build_wiki_page(
    candidate: dict,
    summary_path: str,
    summary_fm: dict,
) -> str:
    """Build wiki page content with proper frontmatter per WIKI_RULES.md."""
    name = candidate.get("name", "unknown")
    page_type = candidate.get("page_type", "concept")
    description = candidate.get("description", "")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    topics = summary_fm.get("topics", [])

    # Build frontmatter per WIKI_RULES.md page type specs
    if page_type == "decision":
        fm = {"type": "decision", "created": today, "status": "active"}
    elif page_type == "synthesis":
        summary_name = os.path.splitext(os.path.basename(summary_path))[0]
        fm = {
            "type": "synthesis",
            "created": today,
            "sources": [f"vault/memory/summaries/{summary_name}"],
        }
    else:
        fm = {"type": page_type, "created": today, "tags": topics}

    # Build body
    title = name.replace("-", " ").title()
    body_lines = [f"# {title}\n"]

    if description:
        body_lines.append(f"{description}\n")

    # Provenance (includes salience context)
    summary_name = os.path.splitext(os.path.basename(summary_path))[0]
    session_id = summary_fm.get("source_session", "")
    salience_label = summary_fm.get("salience_label", "unknown")
    salience_score = summary_fm.get("salience_score", "?")
    body_lines.append("## Provenance\n")
    body_lines.append(f"- Promoted from [[summaries/{summary_name}]]")
    if session_id:
        body_lines.append(f"- Source session: {session_id[:8]}")
    body_lines.append(f"- Created: {today}")
    body_lines.append(f"- Salience: {salience_label} ({salience_score})\n")

    # Related pages (no orphans rule)
    existing = get_existing_wiki_pages()
    existing.discard(name)  # don't link to self
    related = _find_related_pages(name, existing)
    if related:
        body_lines.append("## Related\n")
        for page in related:
            body_lines.append(f"- [[{page}]]")
        body_lines.append("")

    body = "\n".join(body_lines)
    return _dump_frontmatter(fm, body)


# ─── Index and log updates ───────────────────────────────────────────────────


def update_wiki_index(page_slug: str, page_type: str, description: str) -> None:
    """Add entry to 10_Wiki/index.md under the correct section."""
    with open(WIKI_INDEX) as f:
        content = f.read()

    # Check if already indexed
    if f"[[{page_slug}]]" in content:
        return

    section_header = TYPE_SECTIONS.get(page_type, "## Concepts")
    entry = (
        f"- [[{page_slug}]] — {description}" if description else f"- [[{page_slug}]]"
    )

    if section_header in content:
        # Find the section and insert the entry after existing entries
        lines = content.split("\n")
        new_lines = []
        inserted = False
        in_section = False
        last_entry_idx = -1

        for i, line in enumerate(lines):
            new_lines.append(line)
            if line.strip() == section_header.strip():
                in_section = True
                continue
            if in_section and not inserted:
                if line.strip() == "(none yet)":
                    new_lines[-1] = entry
                    inserted = True
                    in_section = False
                elif line.startswith("- "):
                    last_entry_idx = len(new_lines) - 1
                elif line.startswith("##"):
                    # Hit next section — insert after last entry or section header
                    insert_pos = (
                        last_entry_idx + 1
                        if last_entry_idx >= 0
                        else len(new_lines) - 1
                    )
                    new_lines.insert(insert_pos, entry)
                    inserted = True
                    in_section = False

        if in_section and not inserted:
            insert_pos = last_entry_idx + 1 if last_entry_idx >= 0 else len(new_lines)
            new_lines.insert(insert_pos, entry)

        content = "\n".join(new_lines)
    else:
        content += f"\n{section_header}\n\n{entry}\n"

    with open(WIKI_INDEX, "w") as f:
        f.write(content)
    logger.info("  Updated: %s", WIKI_INDEX)


def append_wiki_log(action: str, page_slug: str, description: str) -> None:
    """Append entry to 10_Wiki/log.md."""
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    entry = f"\n## [{now}] {action} | {page_slug}\n{description}\n"

    with open(WIKI_LOG, "a") as f:
        f.write(entry)
    logger.info("  Appended to: %s", WIKI_LOG)


# ─── Summary frontmatter update ─────────────────────────────────────────────


def mark_summary_promoted(summary_path: str, wiki_slug: str) -> None:
    """Add wiki_slug to the summary's promoted_to list in frontmatter."""
    with open(summary_path) as f:
        content = f.read()
    fm, body = _parse_frontmatter(content)

    promoted = fm.get("promoted_to", [])
    if wiki_slug not in promoted:
        promoted.append(wiki_slug)
        fm["promoted_to"] = promoted
        with open(summary_path, "w") as f:
            f.write(_dump_frontmatter(fm, body))


# ─── Promotion logic ────────────────────────────────────────────────────────


def should_promote(
    candidate: dict,
    existing_pages: set[str],
    already_promoted: list[str],
    salience_label: str = "low",
    promotion_recommendation: str = "skip",
) -> tuple[bool, str]:
    """Return (should_promote, reason) based on salience and dedup checks."""
    name = candidate.get("name", "")
    page_type = candidate.get("page_type", "")

    if not name or not page_type:
        return False, "missing name or page_type"
    if page_type not in TYPE_DIRS:
        return False, f"unknown page_type: {page_type}"
    if name in existing_pages:
        return False, "page already exists"
    if name in already_promoted:
        return False, "already promoted from this summary"

    # Salience gating — consolidation rules
    if salience_label == "low":
        return False, f"salience too low ({salience_label})"
    if salience_label == "medium":
        # Medium salience: only promote decisions (inherently durable)
        if page_type == "decision":
            return True, "medium salience but decision type is durable"
        return False, f"medium salience, {page_type} not durable enough"
    # high or critical — promote if recommendation allows
    if promotion_recommendation in ("promote", "must_promote"):
        return (
            True,
            f"salience {salience_label}, recommendation: {promotion_recommendation}",
        )
    if promotion_recommendation == "consider":
        return True, f"salience {salience_label}, considering for promotion"
    return False, f"recommendation is {promotion_recommendation}"


def promote_candidate(
    candidate: dict,
    summary_path: str,
    summary_fm: dict,
    existing_pages: set[str],
    dry_run: bool = False,
) -> str | None:
    """Promote a single candidate. Returns wiki page path or None."""
    name = candidate.get("name", "unknown")
    page_type = candidate.get("page_type", "concept")
    description = candidate.get("description", "")

    subdir = TYPE_DIRS.get(page_type, "concepts")
    wiki_path = os.path.join(WIKI_DIR, subdir, f"{name}.md")

    if dry_run:
        logger.info("  WOULD CREATE: %s (%s)", wiki_path, page_type)
        return None

    logger.info("  Creating: %s (%s)", wiki_path, page_type)

    # Build and write the page
    page_content = build_wiki_page(candidate, summary_path, summary_fm)
    os.makedirs(os.path.dirname(wiki_path), exist_ok=True)
    with open(wiki_path, "w") as f:
        f.write(page_content)

    # Update index and log
    update_wiki_index(name, page_type, description)
    append_wiki_log("create", name, f"Promoted from summary. {description}")

    # Mark summary as promoted
    mark_summary_promoted(summary_path, name)

    # Record to Neon
    try:
        from scripts.memory_neon import record_wiki_promoted

        record_wiki_promoted(
            wiki_path=wiki_path,
            wiki_slug=name,
            page_type=page_type,
            source_summary_path=summary_path,
            source_session_id=summary_fm.get("source_session"),
            salience_score=summary_fm.get("salience_score"),
            salience_label=summary_fm.get("salience_label"),
        )
    except Exception as e:
        logger.warning("  Neon recording skipped: %s", e)

    return wiki_path


# ─── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote summaries to wiki")
    parser.add_argument("--summary", help="Process a specific summary file")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview what would be promoted"
    )
    args = parser.parse_args()

    logger.info("=== Wiki Promotion ===\n")

    existing_pages = get_existing_wiki_pages()
    logger.info("Existing wiki pages: %d", len(existing_pages))

    # Find summary files
    if args.summary:
        summary_files = [args.summary]
    else:
        summary_files = sorted(glob.glob(os.path.join(SUMMARIES_DIR, "*.md")))

    if not summary_files:
        logger.info("No summary files found in %s", SUMMARIES_DIR)
        return

    promoted = 0
    skipped = 0

    for filepath in summary_files:
        logger.info("\nProcessing: %s", os.path.basename(filepath))

        with open(filepath) as f:
            content = f.read()
        fm, body = _parse_frontmatter(content)

        candidates = fm.get("wiki_candidates", [])
        if not candidates:
            logger.info("  No wiki candidates")
            skipped += 1
            continue

        already_promoted = fm.get("promoted_to", [])
        salience_label = fm.get("salience_label", "low")
        promotion_rec = fm.get("promotion_recommendation", "skip")

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            ok, reason = should_promote(
                candidate,
                existing_pages,
                already_promoted,
                salience_label=salience_label,
                promotion_recommendation=promotion_rec,
            )
            if not ok:
                name = candidate.get("name", "?")
                logger.info("  SKIP: %s (%s)", name, reason)
                skipped += 1
                continue

            result = promote_candidate(
                candidate, filepath, fm, existing_pages, dry_run=args.dry_run
            )
            if result:
                promoted += 1
                # Add to existing set so next candidate in same file doesn't collide
                existing_pages.add(candidate.get("name", ""))
            else:
                skipped += 1

    logger.info("\nDone. Promoted: %d, Skipped: %d", promoted, skipped)


if __name__ == "__main__":
    main()
