#!/usr/bin/env python3
"""Batch ingest conversation exports into UMH canonical memory store.

Scans data/exports/<service>/ for conversation export files,
parses with the appropriate parser, wraps in ConversationSource,
and feeds each to GenericIngestionOrchestrator.

Usage:
    python3 scripts/ingest_conversations.py --service claude
    python3 scripts/ingest_conversations.py --service chatgpt
    python3 scripts/ingest_conversations.py --service all
    python3 scripts/ingest_conversations.py --service claude --path /custom/export.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from adapters.data_source_adapters.conversation_source import ConversationSource
from adapters.data_source_adapters.parsers.chatgpt_parser import parse_chatgpt_export
from adapters.data_source_adapters.parsers.claude_parser import parse_claude_export

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest_conversations")

BASE_DIR = Path("/opt/OS")
EXPORT_DIR = BASE_DIR / "data" / "exports"
LOG_DIR = BASE_DIR / "data" / "runtime" / "ingestion_logs"


def _get_orchestrator():  # type: ignore[no-untyped-def]
    """Import and return the orchestrator (deferred to avoid import at module level)."""
    try:
        from substrate.understanding.perception.orchestrator import GenericIngestionOrchestrator

        return GenericIngestionOrchestrator()
    except ImportError as e:
        logger.error("Cannot import GenericIngestionOrchestrator: %s", e)
        return None


def _scan_export_dir(service: str) -> list[Path]:
    """Find export files for a given service."""
    service_dir = EXPORT_DIR / service
    if not service_dir.is_dir():
        logger.warning("Export directory does not exist: %s", service_dir)
        return []

    files: list[Path] = []
    # JSON files
    files.extend(sorted(service_dir.glob("*.json")))
    # ZIP files (ChatGPT)
    if service == "chatgpt":
        files.extend(sorted(service_dir.glob("*.zip")))
    # Subdirectories (Claude multi-file export)
    for sub in sorted(service_dir.iterdir()):
        if sub.is_dir():
            files.append(sub)

    return files


def ingest_service(
    service: str,
    path_override: Path | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Ingest conversations from a single service.

    Returns:
        Dict with counts: {parsed, ingested, failed}
    """
    stats = {"parsed": 0, "ingested": 0, "failed": 0}

    # Determine parser
    if service == "claude":
        parser = parse_claude_export
    elif service == "chatgpt":
        parser = parse_chatgpt_export
    else:
        logger.error("Unknown service: %s", service)
        return stats

    # Find files
    if path_override:
        files = [path_override]
    else:
        files = _scan_export_dir(service)

    if not files:
        logger.info("No export files found for %s", service)
        return stats

    # Parse all files
    all_conversations = []
    for file_path in files:
        logger.info("Parsing %s ...", file_path)
        try:
            conversations = parser(file_path)
            all_conversations.extend(conversations)
            logger.info("  -> %d conversations", len(conversations))
        except Exception as e:
            logger.error("  -> FAILED: %s", e)
            stats["failed"] += 1

    stats["parsed"] = len(all_conversations)
    logger.info("Ingesting %d conversations from %s...", len(all_conversations), service)

    if dry_run:
        logger.info("DRY RUN — skipping actual ingestion")
        return stats

    # Ingest
    orchestrator = _get_orchestrator()
    for conv in all_conversations:
        source = ConversationSource(conv)
        try:
            if orchestrator:
                orchestrator.ingest(source)
            stats["ingested"] += 1
        except Exception as e:
            logger.error(
                "Failed to ingest conversation %s: %s",
                conv.conversation_id,
                e,
            )
            stats["failed"] += 1

    return stats


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Batch ingest conversation exports into UMH memory store."
    )
    parser.add_argument(
        "--service",
        choices=["claude", "chatgpt", "all"],
        required=True,
        help="Service to ingest from",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Override: specific file or directory to parse",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse only, don't ingest into memory store",
    )
    args = parser.parse_args()

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"conversations_{timestamp}.jsonl"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    services = ["claude", "chatgpt"] if args.service == "all" else [args.service]
    all_stats: dict[str, dict[str, int]] = {}

    for svc in services:
        logger.info("=== Ingesting %s ===", svc)
        stats = ingest_service(svc, path_override=args.path, dry_run=args.dry_run)
        all_stats[svc] = stats
        logger.info(
            "%s: parsed=%d ingested=%d failed=%d",
            svc,
            stats["parsed"],
            stats["ingested"],
            stats["failed"],
        )

    # Write log entry
    log_entry = {
        "timestamp": timestamp,
        "services": all_stats,
        "dry_run": args.dry_run,
    }
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        logger.info("Log written to %s", log_path)
    except OSError as e:
        logger.error("Failed to write log: %s", e)

    # Summary
    total_parsed = sum(s["parsed"] for s in all_stats.values())
    total_ingested = sum(s["ingested"] for s in all_stats.values())
    total_failed = sum(s["failed"] for s in all_stats.values())
    logger.info(
        "DONE — total: parsed=%d ingested=%d failed=%d",
        total_parsed,
        total_ingested,
        total_failed,
    )


if __name__ == "__main__":
    main()
