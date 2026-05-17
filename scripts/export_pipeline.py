"""export_pipeline.py — Autonomous export-to-ingestion pipeline.

Polls Gmail for export download emails, downloads the archives,
routes to the correct parser, and ingests into canonical memory store.

No human in the loop after initial MFA login + export trigger.

Usage:
    python3 scripts/export_pipeline.py              # poll once
    python3 scripts/export_pipeline.py --watch       # poll every 5 min
    python3 scripts/export_pipeline.py --service claude  # single service

Cron example (every 10 min):
    */10 * * * * cd /opt/OS && python3 scripts/export_pipeline.py >> /opt/OS/logs/export_pipeline.log 2>&1
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, "/opt/OS")

from dotenv import load_dotenv

load_dotenv("/opt/OS/runtime/.env")
load_dotenv("/opt/OS/services/.env", override=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_EXPORT_DIR = Path("/opt/OS/data/runtime/exports")
_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

_PROCESSED_LOG = _EXPORT_DIR / "processed_emails.json"
_MEMORY_STORE = Path("/opt/OS/data/runtime/canonical_memory_store")


def _load_processed() -> set[str]:
    """Load set of already-processed email IDs."""
    if _PROCESSED_LOG.exists():
        try:
            data = json.loads(_PROCESSED_LOG.read_text())
            return set(data)
        except (json.JSONDecodeError, TypeError):
            return set()
    return set()


def _save_processed(processed: set[str]) -> None:
    """Save processed email IDs."""
    _PROCESSED_LOG.write_text(json.dumps(sorted(processed), indent=2))


async def poll_and_process(service: str | None = None) -> dict[str, int]:
    """Poll Gmail for export emails, download, parse, ingest.

    Returns stats: {polled, downloaded, ingested, skipped}
    """
    from adapters.browser_exports.gmail_export_poller import poll_for_export_emails

    services = [service] if service else ["claude", "chatgpt"]
    processed = _load_processed()
    stats = {"polled": 0, "downloaded": 0, "ingested": 0, "skipped": 0, "failed": 0}

    for svc in services:
        logger.info("Polling Gmail for %s export emails...", svc)
        try:
            emails = await poll_for_export_emails(svc)
        except Exception as e:
            logger.error("Poll failed for %s: %s", svc, e)
            stats["failed"] += 1
            continue

        stats["polled"] += len(emails)

        for email_entry in emails:
            email_id = email_entry.get("email_id", "")
            url = email_entry.get("url", "")

            if email_id in processed:
                logger.info("Already processed email %s, skipping", email_id[:8])
                stats["skipped"] += 1
                continue

            if not url:
                logger.warning("No URL in email %s", email_id[:8])
                stats["skipped"] += 1
                continue

            # Download the export archive
            download_path = await _download_export(svc, url, email_id)
            if not download_path:
                stats["failed"] += 1
                continue
            stats["downloaded"] += 1

            # Route to correct parser and ingest
            ingested = await _route_and_ingest(svc, download_path)
            if ingested:
                stats["ingested"] += 1
                processed.add(email_id)
            else:
                stats["failed"] += 1

    _save_processed(processed)
    return stats


async def _download_export(service: str, url: str, email_id: str) -> Path | None:
    """Download export archive from URL.

    Returns path to downloaded file, or None on failure.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:8]
    download_dir = _EXPORT_DIR / service
    download_dir.mkdir(parents=True, exist_ok=True)

    # Determine filename from URL or fallback
    parsed = urlparse(url)
    filename = Path(parsed.path).name if parsed.path else f"export_{url_hash}.zip"
    if not filename.endswith((".zip", ".json", ".tar.gz")):
        filename = f"{service}_export_{ts}_{url_hash}.zip"

    download_path = download_dir / filename

    try:
        import urllib.request

        logger.info("Downloading %s export from %s...", service, url[:60])
        urllib.request.urlretrieve(url, str(download_path))
        size = download_path.stat().st_size
        logger.info("Downloaded %s (%d bytes)", download_path.name, size)
        return download_path
    except Exception as e:
        logger.error("Download failed for %s: %s", service, e)
        return None


async def _route_and_ingest(service: str, archive_path: Path) -> bool:
    """Route downloaded archive to correct parser and ingest results."""
    try:
        # Extract if ZIP
        extract_dir = archive_path.parent / archive_path.stem
        if archive_path.suffix == ".zip":
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(extract_dir)
            logger.info("Extracted %d files to %s", len(list(extract_dir.rglob("*"))), extract_dir)
        elif archive_path.suffix == ".json":
            extract_dir = archive_path.parent
        else:
            logger.warning("Unknown archive format: %s", archive_path.suffix)
            return False

        # Route to parser based on service
        if service == "claude":
            return await _ingest_claude_export(extract_dir)
        elif service == "chatgpt":
            return await _ingest_chatgpt_export(extract_dir)
        elif service == "instagram":
            return await _ingest_instagram_export(extract_dir)
        else:
            logger.warning("No parser for service: %s", service)
            return False

    except Exception as e:
        logger.error("Route/ingest failed for %s: %s", service, e)
        return False


async def _ingest_claude_export(extract_dir: Path) -> bool:
    """Parse and ingest Claude conversation export."""
    conversations_file = None
    for candidate in ["conversations.json", "data.json"]:
        path = extract_dir / candidate
        if path.exists():
            conversations_file = path
            break

    if not conversations_file:
        # Search recursively
        json_files = list(extract_dir.rglob("*.json"))
        if json_files:
            conversations_file = max(json_files, key=lambda f: f.stat().st_size)

    if not conversations_file:
        logger.error("No conversation data found in Claude export at %s", extract_dir)
        return False

    from adapters.data_source_adapters.local_file_source import LocalFileSource
    from governance.policy.authority_tier import T2_PRIMARY
    from understanding.perception.orchestrator import GenericIngestionOrchestrator

    orchestrator = GenericIngestionOrchestrator(
        memory_store_path=_MEMORY_STORE,
        proof_dir=_MEMORY_STORE / "proofs" / "claude_export",
    )

    source = LocalFileSource(conversations_file, authority_tier=T2_PRIMARY)
    result = orchestrator.ingest(source)
    logger.info("Claude export ingestion: %s", result.verdict)
    return result.verdict == "COMPLETE_CYCLE"


async def _ingest_chatgpt_export(extract_dir: Path) -> bool:
    """Parse and ingest ChatGPT conversation export."""
    conversations_file = extract_dir / "conversations.json"
    if not conversations_file.exists():
        json_files = list(extract_dir.rglob("conversations.json"))
        if json_files:
            conversations_file = json_files[0]
        else:
            logger.error("No conversations.json found in ChatGPT export at %s", extract_dir)
            return False

    from adapters.data_source_adapters.local_file_source import LocalFileSource
    from governance.policy.authority_tier import T2_PRIMARY
    from understanding.perception.orchestrator import GenericIngestionOrchestrator

    orchestrator = GenericIngestionOrchestrator(
        memory_store_path=_MEMORY_STORE,
        proof_dir=_MEMORY_STORE / "proofs" / "chatgpt_export",
    )

    source = LocalFileSource(conversations_file, authority_tier=T2_PRIMARY)
    result = orchestrator.ingest(source)
    logger.info("ChatGPT export ingestion: %s", result.verdict)
    return result.verdict == "COMPLETE_CYCLE"


async def _ingest_instagram_export(extract_dir: Path) -> bool:
    """Parse Instagram export and run curation analyst."""
    saved_posts = None
    for candidate in ["saved_posts.json", "your_saved_posts.json"]:
        path = extract_dir / candidate
        if path.exists():
            saved_posts = path
            break

    if not saved_posts:
        json_files = list(extract_dir.rglob("*saved*.json"))
        if json_files:
            saved_posts = json_files[0]

    if not saved_posts:
        logger.warning("No saved_posts.json in Instagram export — ingesting as generic")
        # Fall through to generic ingestion of all JSON files
        from adapters.data_source_adapters.local_file_source import LocalFileSource
        from governance.policy.authority_tier import T4_SUPPORTING
        from understanding.perception.orchestrator import GenericIngestionOrchestrator

        orchestrator = GenericIngestionOrchestrator(
            memory_store_path=_MEMORY_STORE,
            proof_dir=_MEMORY_STORE / "proofs" / "instagram_export",
        )

        ingested = 0
        for json_file in extract_dir.rglob("*.json"):
            source = LocalFileSource(json_file, authority_tier=T4_SUPPORTING)
            result = orchestrator.ingest(source)
            if result.verdict == "COMPLETE_CYCLE":
                ingested += 1

        logger.info("Instagram generic ingestion: %d files", ingested)
        return ingested > 0

    from adapters.browser_exports.instagram_export_parser import parse_instagram_saves

    report = parse_instagram_saves(saved_posts)

    # Save report
    import dataclasses

    report_path = _EXPORT_DIR / "instagram" / f"curation_report_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(dataclasses.asdict(report), indent=2, default=str))
    logger.info("Instagram curation report saved to %s", report_path)
    logger.info("Harness candidates flagged for review (NOT auto-swapped)")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Export-to-ingestion pipeline")
    parser.add_argument("--service", choices=["claude", "chatgpt", "instagram"])
    parser.add_argument("--watch", action="store_true", help="Poll every 5 min")
    args = parser.parse_args()

    if args.watch:
        logger.info("Watch mode: polling every 5 minutes")
        while True:
            stats = asyncio.run(poll_and_process(args.service))
            logger.info("Poll stats: %s", stats)
            time.sleep(300)
    else:
        stats = asyncio.run(poll_and_process(args.service))
        logger.info("Pipeline stats: %s", stats)


if __name__ == "__main__":
    main()
