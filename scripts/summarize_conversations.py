#!/usr/bin/env python3
"""
Summarize conversation files into structured knowledge summaries.

Reads raw conversation logs from vault/memory/conversations/,
calls an LLM to extract structured knowledge, and writes
summary files to vault/memory/summaries/.

Usage:
    python3 scripts/summarize_conversations.py                    # process all unsummarized
    python3 scripts/summarize_conversations.py --session <id>     # process one session
    python3 scripts/summarize_conversations.py --dry-run          # show what would be processed
"""

import sys
import os
import re
import glob
import argparse
import logging

sys.path.insert(0, "/opt/OS")

from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

CONVERSATIONS_DIR = "/opt/OS/vault/memory/conversations"
SUMMARIES_DIR = "/opt/OS/vault/memory/summaries"
MEMORY_INDEX = "/opt/OS/vault/memory/index.md"

# Skip conversations with less content than this (after stripping frontmatter)
MIN_CONTENT_CHARS = 100


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


# ─── Idempotency ────────────────────────────────────────────────────────────


def get_processed_sessions() -> set[str]:
    """Return set of session IDs that already have summaries."""
    processed = set()
    for path in glob.glob(os.path.join(SUMMARIES_DIR, "*.md")):
        try:
            with open(path) as f:
                fm, _ = _parse_frontmatter(f.read())
            sid = fm.get("source_session", "")
            if sid:
                processed.add(sid)
        except Exception:
            continue
    return processed


# ─── Content extraction ─────────────────────────────────────────────────────


def _extract_body(filepath: str) -> tuple[dict, str]:
    """Read a conversation file and return (frontmatter, body_text)."""
    with open(filepath) as f:
        content = f.read()
    return _parse_frontmatter(content)


def _is_trivial(body: str) -> bool:
    """Return True if conversation body is too short to summarize."""
    # Strip markdown headers and whitespace
    cleaned = re.sub(r"^#+\s.*$", "", body, flags=re.MULTILINE).strip()
    cleaned = re.sub(r"^-+\s*$", "", cleaned, flags=re.MULTILINE).strip()
    return len(cleaned) < MIN_CONTENT_CHARS


# ─── LLM summarization ──────────────────────────────────────────────────────

SUMMARIZE_SYSTEM = (
    "You are a knowledge extraction assistant. "
    "Extract structured information from conversation logs. "
    "Respond in YAML format only. No markdown fences. No explanation."
)

SUMMARIZE_PROMPT = """Given this conversation log from a Claude Code session, extract:

1. title: A concise title (5-10 words) describing the main topic
2. topics: List of 2-5 topic tags (lowercase, hyphenated)
3. decisions: List of decisions made (empty list if none)
4. constraints: List of constraints or rules established (empty list if none)
5. entities: List of named things mentioned (tools, files, products, concepts)
6. open_loops: List of unresolved items or future work mentioned (empty list if none)
7. wiki_candidates: List of items durable enough to become wiki pages, each with:
   - name: lowercase-hyphenated-slug
   - page_type: one of concept, entity, decision, synthesis
   - description: one sentence explaining what the page would cover

Only include wiki_candidates for genuinely durable knowledge, not ephemeral session details.
If nothing is wiki-worthy, return an empty list.

Respond in YAML only. No markdown fences.

---
CONVERSATION:
{conversation}"""


def _call_llm(conversation_text: str) -> str | None:
    """Call the LLM for summarization. Returns raw output or None on failure."""
    try:
        from eos_ai.model_router import call_with_fallback

        prompt = SUMMARIZE_PROMPT.format(conversation=conversation_text[:4000])
        result = call_with_fallback(
            prompt=prompt,
            system=SUMMARIZE_SYSTEM,
            task_type="summarize",
            trigger_source="memory_pipeline",
        )
        if not result.output or "[EOS]" in result.output:
            logger.warning("LLM returned empty or error sentinel")
            return None
        return result.output, result.model, result.provider
    except Exception as e:
        logger.warning("LLM call failed: %s", e)
        return None


def _parse_llm_response(raw: str) -> dict | None:
    """Parse YAML response from LLM. Falls back to regex extraction."""
    import yaml

    # Strip markdown fences if model added them despite instructions
    cleaned = re.sub(r"^```ya?ml\s*\n?", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        parsed = yaml.safe_load(cleaned)
        if isinstance(parsed, dict) and "title" in parsed:
            return parsed
    except Exception:
        pass

    # Regex fallback for weak models
    result = {}
    title_match = re.search(r"title:\s*[\"']?(.+?)[\"']?\s*$", raw, re.MULTILINE)
    if title_match:
        result["title"] = title_match.group(1).strip()

    topics_match = re.search(r"topics:\s*\n((?:\s*-\s*.+\n?)+)", raw, re.MULTILINE)
    if topics_match:
        result["topics"] = [
            line.strip().lstrip("- ").strip()
            for line in topics_match.group(1).strip().splitlines()
        ]

    if "title" in result:
        # Fill defaults for missing fields
        result.setdefault("topics", [])
        result.setdefault("decisions", [])
        result.setdefault("constraints", [])
        result.setdefault("entities", [])
        result.setdefault("open_loops", [])
        result.setdefault("wiki_candidates", [])
        return result

    logger.warning("Could not parse LLM response")
    return None


# ─── File writing ────────────────────────────────────────────────────────────


def _slugify(text: str) -> str:
    """Convert text to a filename-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:50]


def write_summary(
    session_id: str,
    parsed: dict,
    source_path: str,
    date_str: str,
) -> str:
    """Write summary file. Returns output filepath."""
    title = parsed.get("title", "untitled")
    slug = _slugify(title)
    filename = f"summary_{session_id[:8]}_{date_str}_{slug}.md"
    filepath = os.path.join(SUMMARIES_DIR, filename)

    # Compute per-session salience
    from scripts.salience import score_summary, score_cross_session

    salience = score_summary(parsed, body_text=str(parsed))

    # Compute cross-session salience (repeated themes across summaries)
    cross = score_cross_session(
        parsed,
        body_text=str(parsed),
        summaries_dir=SUMMARIES_DIR,
        exclude_session=session_id,
    )

    # Build frontmatter
    fm = {
        "type": "summary",
        "source_session": session_id,
        "source_path": f"vault/memory/conversations/{session_id}.md",
        "created": date_str,
        "title": title,
        "topics": parsed.get("topics", []),
        "salience_score": salience.score,
        "salience_label": salience.label,
        "salience_reasons": salience.reasons,
        "recommended_action": salience.consolidation_recommendation,
        "promotion_recommendation": salience.promotion_recommendation,
        "cross_session_salience_score": cross.score,
        "cross_session_salience_reasons": cross.reasons,
        "compounded_recommendation": cross.compounded_recommendation,
    }
    if cross.repeated_entities:
        fm["repeated_entities"] = cross.repeated_entities
    if cross.repeated_topics:
        fm["repeated_topics"] = cross.repeated_topics
    if cross.repeated_open_loops:
        fm["repeated_open_loops"] = cross.repeated_open_loops
    wiki_candidates = parsed.get("wiki_candidates", [])
    if wiki_candidates:
        fm["wiki_candidates"] = wiki_candidates

    # Build body
    sections = [f"# {title}\n"]
    sections.append(f"## Source\n- Session: {session_id[:8]}\n- Date: {date_str}\n")

    for field, heading in [
        ("decisions", "Decisions"),
        ("constraints", "Constraints"),
        ("entities", "Entities"),
        ("open_loops", "Open Loops"),
    ]:
        items = parsed.get(field, [])
        if items:
            lines = [f"## {heading}"]
            for item in items:
                if isinstance(item, str):
                    lines.append(f"- {item}")
                elif isinstance(item, dict):
                    lines.append(f"- {item}")
            sections.append("\n".join(lines) + "\n")

    if wiki_candidates:
        lines = ["## Wiki Promotion Candidates"]
        for c in wiki_candidates:
            if isinstance(c, dict):
                name = c.get("name", "unknown")
                ptype = c.get("page_type", "concept")
                desc = c.get("description", "")
                lines.append(f"- **{name}** ({ptype}) — {desc}")
            elif isinstance(c, str):
                lines.append(f"- {c}")
        sections.append("\n".join(lines) + "\n")

    # Salience section
    sections.append(
        f"## Salience\n- Score: {salience.score}\n- Label: {salience.label}"
    )
    sections.append(f"- Promotion: {salience.promotion_recommendation}")
    sections.append(f"- Consolidation: {salience.consolidation_recommendation}")
    if salience.reasons:
        sections.append("- Reasons:")
        for reason in salience.reasons:
            sections.append(f"  - {reason}")
    sections.append("")

    # Cross-session salience section
    if cross.score > 0:
        sections.append(
            f"## Cross-Session Salience\n- Score: {cross.score}"
        )
        sections.append(f"- Recommendation: {cross.compounded_recommendation}")
        if cross.reasons:
            sections.append("- Reasons:")
            for reason in cross.reasons:
                sections.append(f"  - {reason}")
        if cross.repeated_entities:
            sections.append("- Recurring entities:")
            for e in cross.repeated_entities:
                sections.append(f"  - {e}")
        if cross.repeated_open_loops:
            sections.append("- Persistent open loops:")
            for loop in cross.repeated_open_loops:
                sections.append(f"  - {loop}")
        sections.append("")

    body = "\n".join(sections)
    content = _dump_frontmatter(fm, body)

    os.makedirs(SUMMARIES_DIR, exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)

    logger.info("  Wrote: %s", filepath)
    return filepath


# ─── Index update ────────────────────────────────────────────────────────────


def update_memory_index(summary_relpath: str, title: str, session_id: str) -> None:
    """Add entry to vault/memory/index.md under the Summaries section."""
    if not os.path.exists(MEMORY_INDEX):
        return

    with open(MEMORY_INDEX) as f:
        content = f.read()

    # Build the new entry
    summary_name = os.path.splitext(os.path.basename(summary_relpath))[0]
    entry = f"- [[summaries/{summary_name}]] — {title} (session {session_id[:8]})"

    # Check if already listed
    if summary_name in content:
        return

    # Find Summaries section and insert
    placeholder = (
        "(none yet — create summaries in `summaries/` after productive sessions)"
    )
    if placeholder in content:
        content = content.replace(placeholder, entry)
    elif "## Summaries" in content:
        # Append after the section header
        idx = content.index("## Summaries")
        # Find end of section description (next blank line or next ##)
        lines = content[idx:].split("\n")
        insert_after = 1
        for i, line in enumerate(lines[1:], 1):
            if line.startswith("- ") or line.startswith("##") or line.strip() == "":
                if line.startswith("##"):
                    insert_after = i
                    break
                if line.startswith("- "):
                    insert_after = i + 1
                    continue
                if line.strip() == "" and i > 2:
                    insert_after = i
                    break
                insert_after = i + 1
        lines.insert(insert_after, entry)
        content = content[:idx] + "\n".join(lines)
    else:
        # No Summaries section — append one
        content += f"\n## Summaries\n\n{entry}\n"

    with open(MEMORY_INDEX, "w") as f:
        f.write(content)
    logger.info("  Updated: %s", MEMORY_INDEX)


# ─── Main pipeline ──────────────────────────────────────────────────────────


def process_session(filepath: str, dry_run: bool = False) -> bool:
    """Process a single conversation file. Returns True if summary created."""
    fm, body = _extract_body(filepath)
    session_id = fm.get("session_id", os.path.splitext(os.path.basename(filepath))[0])

    if _is_trivial(body):
        logger.info("  SKIP (trivial): %s", session_id[:8])
        return False

    if dry_run:
        logger.info("  WOULD SUMMARIZE: %s (%d chars)", session_id[:8], len(body))
        return False

    logger.info("  Summarizing: %s ...", session_id[:8])

    llm_result = _call_llm(body)
    if llm_result is None:
        logger.warning("  SKIP (LLM failed): %s", session_id[:8])
        return False

    raw_output, model_used, provider = llm_result
    parsed = _parse_llm_response(raw_output)
    if parsed is None:
        logger.warning("  SKIP (parse failed): %s", session_id[:8])
        return False

    # Determine date from frontmatter or filename
    started = fm.get("started_at", "")
    if started:
        try:
            date_str = datetime.fromisoformat(str(started)).strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    summary_path = write_summary(session_id, parsed, filepath, date_str)

    # Update vault/memory/index.md
    update_memory_index(
        summary_path,
        parsed.get("title", "untitled"),
        session_id,
    )

    # Record to Neon (non-blocking enhancement)
    # Recompute salience here since write_summary scopes it locally
    try:
        from scripts.salience import score_summary as _score_summary
        from scripts.memory_neon import record_summary_created

        _sal = _score_summary(parsed, body_text=str(parsed))
        record_summary_created(
            session_id=session_id,
            summary_path=summary_path,
            title=parsed.get("title", "untitled"),
            topics=parsed.get("topics", []),
            model_used=model_used,
            provider=provider,
            salience_score=_sal.score,
            salience_label=_sal.label,
            salience_reasons=_sal.reasons,
        )
    except Exception as e:
        logger.warning("  Neon recording skipped: %s", e)

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize conversation files")
    parser.add_argument("--session", help="Process a specific session ID")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be processed"
    )
    args = parser.parse_args()

    logger.info("=== Conversation Summarizer ===\n")

    # Get already-processed sessions
    processed = get_processed_sessions()
    logger.info("Already summarized: %d sessions", len(processed))

    # Find conversation files to process
    conv_files = sorted(glob.glob(os.path.join(CONVERSATIONS_DIR, "*.md")))
    if not conv_files:
        logger.info("No conversation files found in %s", CONVERSATIONS_DIR)
        return

    if args.session:
        # Filter to specific session
        conv_files = [f for f in conv_files if args.session in os.path.basename(f)]
        if not conv_files:
            logger.info("No conversation file found for session: %s", args.session)
            return

    created = 0
    skipped = 0

    for filepath in conv_files:
        session_id = os.path.splitext(os.path.basename(filepath))[0]

        if session_id in processed:
            logger.info("  SKIP (already summarized): %s", session_id[:8])
            skipped += 1
            continue

        if process_session(filepath, dry_run=args.dry_run):
            created += 1
        else:
            skipped += 1

    logger.info("\nDone. Created: %d, Skipped: %d", created, skipped)


if __name__ == "__main__":
    main()
