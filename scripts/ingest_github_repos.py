#!/usr/bin/env python3
"""Batch ingest GitHub repos into UMH canonical memory store.

Usage:
    python3 scripts/ingest_github_repos.py                      # all repos
    python3 scripts/ingest_github_repos.py --category trinity   # one category
    python3 scripts/ingest_github_repos.py --repo owner/name    # specific repo
    python3 scripts/ingest_github_repos.py --full               # force full re-ingest
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from adapters.data_source_adapters.github_source import GitHubRepoWalker
from substrate.understanding.perception.orchestrator import GenericIngestionOrchestrator

# Paths
CONFIG_PATH = Path("/opt/OS/data/config/github_repos.json")
SYNC_STATE_PATH = Path("/opt/OS/data/runtime/github_sync_state.json")
LOG_DIR = Path("/opt/OS/data/runtime/ingestion_logs")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest_github_repos")


def load_config() -> dict[str, list[str]]:
    """Load the github_repos.json config."""
    if not CONFIG_PATH.exists():
        logger.error("Config not found: %s", CONFIG_PATH)
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text())


def load_sync_state() -> dict[str, dict]:
    """Load sync state (last commit per repo)."""
    if not SYNC_STATE_PATH.exists():
        return {}
    text = SYNC_STATE_PATH.read_text().strip()
    if not text:
        return {}
    return json.loads(text)


def save_sync_state(state: dict[str, dict]) -> None:
    """Persist sync state to disk."""
    SYNC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SYNC_STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def get_repos(config: dict[str, list[str]], category: str | None, repo: str | None) -> list[str]:
    """Resolve which repos to ingest."""
    if repo:
        return [repo]
    if category and category != "all":
        repos = config.get(category, [])
        if not repos:
            logger.warning("No repos in category %r", category)
        return repos
    # All categories
    all_repos: list[str] = []
    for cat_repos in config.values():
        all_repos.extend(cat_repos)
    return all_repos


def ingest_repo(
    repo: str,
    orchestrator: GenericIngestionOrchestrator,
    sync_state: dict[str, dict],
    *,
    full: bool = False,
    log_file: Path | None = None,
) -> dict[str, int]:
    """Ingest a single repo. Returns stats dict."""
    stats = {"files_walked": 0, "files_ingested": 0, "files_skipped": 0, "errors": 0}

    walker = GitHubRepoWalker(repo)

    try:
        commit_sha = walker.clone_or_pull()
    except RuntimeError as e:
        logger.error("Failed to clone/pull %s: %s", repo, e)
        stats["errors"] += 1
        return stats

    last_state = sync_state.get(repo, {})
    last_commit = last_state.get("last_commit") if not full else None

    # Decide: incremental or full walk
    if last_commit and last_commit != commit_sha:
        logger.info("Incremental ingest for %s (since %s)", repo, last_commit[:8])
        sources = walker.changed_since(last_commit)
    elif last_commit == commit_sha and not full:
        logger.info("No changes for %s (still at %s), skipping", repo, commit_sha[:8])
        return stats
    else:
        logger.info("Full ingest for %s", repo)
        sources = walker.walk()

    for source in sources:
        stats["files_walked"] += 1
        try:
            result = orchestrator.ingest(source)
            stats["files_ingested"] += 1
            if log_file:
                _append_log(
                    log_file,
                    {
                        "repo": repo,
                        "source_id": source.source_id,
                        "status": "ingested",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
            logger.debug("Ingested: %s", source.source_id)
        except Exception as e:
            stats["errors"] += 1
            logger.error("Failed to ingest %s: %s", source.source_id, e)
            if log_file:
                _append_log(
                    log_file,
                    {
                        "repo": repo,
                        "source_id": source.source_id,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

    # Update sync state
    sync_state[repo] = {
        "last_commit": commit_sha,
        "last_ingested": datetime.now(timezone.utc).isoformat(),
        "files_ingested": stats["files_ingested"],
    }
    save_sync_state(sync_state)

    return stats


def _append_log(log_file: Path, entry: dict) -> None:
    """Append a JSON line to the log file."""
    with log_file.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Batch ingest GitHub repos into UMH.")
    parser.add_argument("--repo", type=str, help="Specific repo to ingest (owner/name)")
    parser.add_argument(
        "--category",
        type=str,
        choices=["trinity", "oss_watchlist", "personal", "all"],
        default="all",
        help="Category of repos to ingest",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Force full re-ingest (ignore sync state)",
    )
    args = parser.parse_args()

    config = load_config()
    repos = get_repos(config, args.category, args.repo)

    if not repos:
        logger.info("No repos to ingest.")
        return

    sync_state = load_sync_state()
    orchestrator = GenericIngestionOrchestrator()

    # Prepare log file
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_file = LOG_DIR / f"github_{timestamp}.jsonl"

    total_stats = {"files_walked": 0, "files_ingested": 0, "files_skipped": 0, "errors": 0}

    logger.info("Starting GitHub ingestion for %d repos", len(repos))
    start = time.monotonic()

    for repo in repos:
        logger.info("--- Processing: %s ---", repo)
        repo_stats = ingest_repo(repo, orchestrator, sync_state, full=args.full, log_file=log_file)
        for k in total_stats:
            total_stats[k] += repo_stats[k]

    elapsed = time.monotonic() - start
    logger.info(
        "Done. %d repos processed in %.1fs. Files walked: %d, ingested: %d, errors: %d",
        len(repos),
        elapsed,
        total_stats["files_walked"],
        total_stats["files_ingested"],
        total_stats["errors"],
    )
    logger.info("Log: %s", log_file)


if __name__ == "__main__":
    main()
