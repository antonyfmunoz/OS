"""gws_scanner_cron.py — Thin cron wrapper for GWSDocumentScanner.

Runs an incremental scan of Google Workspace documents and ingests
new/modified docs into EOS knowledge layers.

Usage:
    python3 scripts/gws_scanner_cron.py                # incremental (default)
    python3 scripts/gws_scanner_cron.py --full         # full rescan
    python3 scripts/gws_scanner_cron.py --limit 50     # cap at 50 docs

Cron example (every 6 hours):
    0 */6 * * * cd /opt/OS && python3 scripts/gws_scanner_cron.py >> /opt/OS/logs/gws_scanner.log 2>&1
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from dotenv import load_dotenv

load_dotenv("/opt/OS/runtime/.env")
load_dotenv("/opt/OS/services/.env", override=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run GWS scanner with cron-friendly defaults."""
    parser = argparse.ArgumentParser(description="GWS Document Scanner (cron mode)")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full rescan (ignore deduplication). Default is incremental.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of docs to list from Drive (default: 200)",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Scan only — do not ingest into EOS",
    )
    parser.add_argument(
        "--skip-profile",
        action="store_true",
        help="Skip founder profile generation",
    )
    args = parser.parse_args()

    start_time = datetime.now(timezone.utc)
    logger.info("GWS Scanner starting at %s", start_time.isoformat())
    logger.info("Mode: %s | Limit: %d", "full" if args.full else "incremental", args.limit)

    try:
        from substrate.state.context.context import load_context_from_env
        from adapters.google_workspace.gws_scanner import GWSDocumentScanner

        ctx = load_context_from_env()
        scanner = GWSDocumentScanner(ctx)

        # Scan
        docs = scanner.scan_all(limit=args.limit, incremental=not args.full)

        if not docs:
            logger.info("No new/modified documents to process")
            return

        # Ingest
        if not args.skip_ingest:
            ingested = scanner.ingest_to_eos(docs)
            logger.info("Ingested %d documents", ingested)
        else:
            logger.info("Skipping ingestion (--skip-ingest)")

        # Save context summary (always — cheap operation)
        scanner.save_context_summary(docs)

        # Generate founder profile on full scans only (expensive)
        if args.full and not args.skip_profile:
            logger.info("Generating founder profile...")
            scanner.generate_founder_profile(docs)

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info("GWS Scanner complete in %.1fs — %d docs processed", elapsed, len(docs))

    except Exception as e:
        logger.error("GWS Scanner failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
