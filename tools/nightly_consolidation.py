#!/usr/bin/env python3
"""
Nightly memory consolidation — the "sleep/dream" layer.

Processes accumulated episodic memory into durable knowledge:
1. Find new/unprocessed conversations
2. Generate summaries with salience scoring
3. Upsert Neon metadata/events
4. Promote high-salience durable knowledge to wiki
5. Update indexes/logs
6. Skip trivial/noisy sessions

Idempotent — safe to re-run. Already-processed sessions are skipped.

Usage:
    python3 scripts/nightly_consolidation.py               # full consolidation
    python3 scripts/nightly_consolidation.py --dry-run      # preview only
    python3 scripts/nightly_consolidation.py --summarize    # summarize only (no promotion)
    python3 scripts/nightly_consolidation.py --promote      # promote only (no summarization)
    python3 scripts/nightly_consolidation.py --rescore      # rescore existing summaries
"""

import sys
import os
import glob
import argparse
import logging

sys.path.insert(0, "/opt/OS")

from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

CONVERSATIONS_DIR = "/opt/OS/data/vault/memory/conversations"
SUMMARIES_DIR = "/opt/OS/data/vault/memory/summaries"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body."""
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
    """Reconstruct markdown with YAML frontmatter."""
    import yaml

    fm_str = yaml.dump(fm, default_flow_style=False, sort_keys=False).strip()
    return f"---\n{fm_str}\n---\n\n{body}\n"


def run_summarization(dry_run: bool = False) -> dict:
    """Run conversation summarization. Returns stats dict."""
    logger.info("─── Phase 1: Summarization ───\n")

    from scripts.summarize_conversations import (
        get_processed_sessions,
        process_session,
    )

    processed = get_processed_sessions()
    conv_files = sorted(glob.glob(os.path.join(CONVERSATIONS_DIR, "*.md")))

    if not conv_files:
        logger.info("No conversation files found.")
        return {"created": 0, "skipped": 0, "total": 0}

    created = 0
    skipped = 0

    for filepath in conv_files:
        session_id = os.path.splitext(os.path.basename(filepath))[0]

        if session_id in processed:
            logger.info("  SKIP (already summarized): %s", session_id[:8])
            skipped += 1
            continue

        if process_session(filepath, dry_run=dry_run):
            created += 1
        else:
            skipped += 1

    logger.info("\nSummarization: created=%d, skipped=%d\n", created, skipped)
    return {"created": created, "skipped": skipped, "total": len(conv_files)}


def run_promotion(dry_run: bool = False) -> dict:
    """Run wiki promotion with salience gating. Returns stats dict."""
    logger.info("─── Phase 2: Wiki Promotion ───\n")

    from scripts.promote_to_wiki import (
        get_existing_wiki_pages,
        should_promote,
        promote_candidate,
    )

    existing_pages = get_existing_wiki_pages()
    summary_files = sorted(glob.glob(os.path.join(SUMMARIES_DIR, "*.md")))

    if not summary_files:
        logger.info("No summary files found.")
        return {"promoted": 0, "skipped": 0, "total": 0}

    promoted = 0
    skipped = 0

    for filepath in summary_files:
        logger.info("Checking: %s", os.path.basename(filepath))

        with open(filepath) as f:
            content = f.read()
        fm, body = _parse_frontmatter(content)

        candidates = fm.get("wiki_candidates", [])
        if not candidates:
            logger.info("  No wiki candidates")
            skipped += 1
            continue

        salience_label = fm.get("salience_label", "low")
        promotion_rec = fm.get("promotion_recommendation", "skip")
        already_promoted = fm.get("promoted_to", [])

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
                candidate, filepath, fm, existing_pages, dry_run=dry_run
            )
            if result:
                promoted += 1
                existing_pages.add(candidate.get("name", ""))
            else:
                skipped += 1

    logger.info("\nPromotion: promoted=%d, skipped=%d\n", promoted, skipped)
    return {"promoted": promoted, "skipped": skipped, "total": len(summary_files)}


def rescore_summaries(dry_run: bool = False) -> dict:
    """Rescore all existing summaries with current salience weights.

    Useful after tuning weights — updates frontmatter in place.
    """
    logger.info("─── Rescoring Summaries ───\n")

    from scripts.salience import score_from_frontmatter, score_cross_session

    summary_files = sorted(glob.glob(os.path.join(SUMMARIES_DIR, "*.md")))
    updated = 0

    for filepath in summary_files:
        with open(filepath) as f:
            content = f.read()
        fm, body = _parse_frontmatter(content)

        result = score_from_frontmatter(fm, body)

        # Cross-session salience (uses other summaries for comparison)
        parsed_for_cross = {
            "entities": [],
            "topics": fm.get("topics", []),
            "decisions": [],
            "open_loops": [],
        }
        # Extract from body sections for cross-session comparison
        import re as _re

        for section, key in [
            ("## Entities", "entities"),
            ("## Decisions", "decisions"),
            ("## Open Loops", "open_loops"),
        ]:
            pattern = _re.escape(section) + r"\s*\n((?:- .+\n?)+)"
            match = _re.search(pattern, body)
            if match:
                parsed_for_cross[key] = [
                    line.strip()[2:].strip()
                    for line in match.group(1).strip().splitlines()
                    if line.strip().startswith("- ")
                ]

        cross = score_cross_session(
            parsed_for_cross,
            body_text=body,
            summaries_dir=SUMMARIES_DIR,
            exclude_session=fm.get("source_session", ""),
        )

        old_score = fm.get("salience_score")
        old_label = fm.get("salience_label")

        fm["salience_score"] = result.score
        fm["salience_label"] = result.label
        fm["salience_reasons"] = result.reasons
        fm["recommended_action"] = result.consolidation_recommendation
        fm["promotion_recommendation"] = result.promotion_recommendation
        fm["cross_session_salience_score"] = cross.score
        fm["cross_session_salience_reasons"] = cross.reasons
        fm["compounded_recommendation"] = cross.compounded_recommendation
        if cross.repeated_entities:
            fm["repeated_entities"] = cross.repeated_entities
        if cross.repeated_topics:
            fm["repeated_topics"] = cross.repeated_topics
        if cross.repeated_open_loops:
            fm["repeated_open_loops"] = cross.repeated_open_loops

        changed = old_score != result.score or old_label != result.label

        if changed:
            logger.info(
                "  %s: %s(%s) → %s(%s)",
                os.path.basename(filepath),
                old_label or "none",
                old_score or "?",
                result.label,
                result.score,
            )
            if not dry_run:
                with open(filepath, "w") as f:
                    f.write(_dump_frontmatter(fm, body))
            updated += 1
        else:
            logger.info(
                "  %s: unchanged (%s/%s)",
                os.path.basename(filepath),
                result.label,
                result.score,
            )

    logger.info("\nRescored: %d updated\n", updated)
    return {"updated": updated, "total": len(summary_files)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Nightly memory consolidation")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing"
    )
    parser.add_argument(
        "--summarize", action="store_true", help="Run summarization only"
    )
    parser.add_argument("--promote", action="store_true", help="Run promotion only")
    parser.add_argument(
        "--rescore", action="store_true", help="Rescore existing summaries"
    )
    args = parser.parse_args()

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    logger.info("═══ Nightly Consolidation ═══")
    logger.info("Started: %s", now)
    if args.dry_run:
        logger.info("MODE: dry-run (no writes)\n")
    else:
        logger.info("")

    if args.rescore:
        rescore_summaries(dry_run=args.dry_run)
        return

    # Default: run both phases unless one is selected
    run_summarize = not args.promote  # run unless --promote-only
    run_promote = not args.summarize  # run unless --summarize-only

    stats = {}

    if run_summarize:
        stats["summarize"] = run_summarization(dry_run=args.dry_run)

    if run_promote:
        stats["promote"] = run_promotion(dry_run=args.dry_run)

    # Report
    logger.info("═══ Consolidation Complete ═══")
    if "summarize" in stats:
        s = stats["summarize"]
        logger.info(
            "Summaries: %d created, %d skipped (of %d conversations)",
            s["created"],
            s["skipped"],
            s["total"],
        )
    if "promote" in stats:
        p = stats["promote"]
        logger.info(
            "Wiki: %d promoted, %d skipped (of %d summaries)",
            p["promoted"],
            p["skipped"],
            p["total"],
        )

    end = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    logger.info("Finished: %s", end)


if __name__ == "__main__":
    main()
