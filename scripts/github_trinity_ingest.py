"""github_trinity_ingest.py — Clone and ingest the three core repos via canonical pipeline.

Targets: EntrepreneurOS, CreatorOS, LYFEOS (the "Trinity").
Uses GenericIngestionOrchestrator + LocalFileSource for each relevant file.

Usage:
    python3 scripts/github_trinity_ingest.py
    python3 scripts/github_trinity_ingest.py --repo entrepreneuros
    python3 scripts/github_trinity_ingest.py --dry-run

Cron example (daily at 03:00):
    0 3 * * * cd /opt/OS && python3 scripts/github_trinity_ingest.py >> /opt/OS/logs/trinity_ingest.log 2>&1
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from adapters.data_source_adapters.local_file_source import LocalFileSource
from substrate.governance.policy.authority_tier import T3_REFERENCE
from substrate.understanding.perception.orchestrator import GenericIngestionOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Configuration
_CLONE_BASE = Path("/opt/OS/data/repos")
_MEMORY_STORE = Path("/opt/OS/data/runtime/canonical_memory_store")
_PROOF_DIR = _MEMORY_STORE / "proofs" / "github_trinity"

TRINITY_REPOS: dict[str, str] = {
    "entrepreneuros": "https://github.com/antonyfmunoz/EntrepreneurOS.git",
    "creatoros": "https://github.com/antonyfmunoz/CreatorOS.git",
    "LYFEOS": "https://github.com/antonyfmunoz/LYFEOS.git",
}

# File extensions worth ingesting (source code + docs)
_INGEST_EXTENSIONS: set[str] = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".md", ".txt", ".yaml", ".yml", ".toml",
    ".json", ".sql", ".sh",
}

# Directories to skip
_SKIP_DIRS: set[str] = {
    "node_modules", ".git", "__pycache__", ".next",
    "dist", "build", ".turbo", "coverage", ".venv",
    "venv", ".tox", ".mypy_cache", ".ruff_cache",
}

# Max file size to ingest (skip large generated files)
_MAX_FILE_BYTES: int = 100_000  # 100KB


def clone_or_pull(repo_name: str, repo_url: str) -> Path:
    """Clone the repo if missing, or pull latest if already cloned.

    Returns the local repo path.
    """
    repo_dir = _CLONE_BASE / repo_name
    _CLONE_BASE.mkdir(parents=True, exist_ok=True)

    if repo_dir.exists() and (repo_dir / ".git").exists():
        logger.info("Pulling latest for %s", repo_name)
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.warning("git pull failed for %s: %s", repo_name, result.stderr.strip())
    else:
        logger.info("Cloning %s from %s", repo_name, repo_url)
        result = subprocess.run(
            ["git", "clone", "--depth=1", repo_url, str(repo_dir)],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error("git clone failed for %s: %s", repo_name, result.stderr.strip())
            raise RuntimeError(f"Clone failed: {repo_name}")

    return repo_dir


def collect_files(repo_dir: Path) -> list[Path]:
    """Walk the repo and collect ingestable files."""
    files: list[Path] = []

    for path in repo_dir.rglob("*"):
        if not path.is_file():
            continue

        # Skip excluded directories
        parts = set(path.relative_to(repo_dir).parts)
        if parts & _SKIP_DIRS:
            continue

        # Check extension
        if path.suffix.lower() not in _INGEST_EXTENSIONS:
            continue

        # Check size
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
            if path.stat().st_size == 0:
                continue
        except OSError:
            continue

        files.append(path)

    return sorted(files)


def ingest_repo(repo_name: str, repo_dir: Path, *, dry_run: bool = False) -> dict[str, int]:
    """Ingest all relevant files from a repo via canonical pipeline.

    Returns stats: {total, ingested, skipped, failed}
    """
    files = collect_files(repo_dir)
    logger.info("[%s] Found %d ingestable files", repo_name, len(files))

    if dry_run:
        for f in files[:20]:
            logger.info("  [dry] %s", f.relative_to(repo_dir))
        if len(files) > 20:
            logger.info("  [dry] ... and %d more", len(files) - 20)
        return {"total": len(files), "ingested": 0, "skipped": 0, "failed": 0}

    orchestrator = GenericIngestionOrchestrator(
        memory_store_path=_MEMORY_STORE,
        proof_dir=_PROOF_DIR / repo_name,
    )

    stats = {"total": len(files), "ingested": 0, "skipped": 0, "failed": 0}

    for i, file_path in enumerate(files):
        rel = file_path.relative_to(repo_dir)
        source = LocalFileSource(file_path, authority_tier=T3_REFERENCE)

        try:
            result = orchestrator.ingest(source)
            if result.verdict == "COMPLETE_CYCLE":
                stats["ingested"] += 1
                if (i + 1) % 25 == 0:
                    logger.info(
                        "[%s] Progress: %d/%d ingested", repo_name, stats["ingested"], i + 1
                    )
            else:
                stats["failed"] += 1
                logger.warning("[%s] %s failed: %s", repo_name, rel, result.verdict)
        except Exception as e:
            stats["failed"] += 1
            logger.error("[%s] %s exception: %s", repo_name, rel, e)

    logger.info(
        "[%s] Complete: %d ingested, %d failed out of %d total",
        repo_name,
        stats["ingested"],
        stats["failed"],
        stats["total"],
    )
    return stats


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest GitHub Trinity repos into UMH")
    parser.add_argument(
        "--repo",
        choices=list(TRINITY_REPOS.keys()),
        help="Ingest only this repo (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files without ingesting",
    )
    args = parser.parse_args()

    repos_to_process = (
        {args.repo: TRINITY_REPOS[args.repo]} if args.repo else TRINITY_REPOS
    )

    all_stats: dict[str, dict[str, int]] = {}

    for repo_name, repo_url in repos_to_process.items():
        logger.info("=" * 60)
        logger.info("Processing: %s", repo_name)
        logger.info("=" * 60)

        try:
            repo_dir = clone_or_pull(repo_name, repo_url)
            stats = ingest_repo(repo_name, repo_dir, dry_run=args.dry_run)
            all_stats[repo_name] = stats
        except Exception as e:
            logger.error("Failed to process %s: %s", repo_name, e)
            all_stats[repo_name] = {"total": 0, "ingested": 0, "skipped": 0, "failed": 1}

    # Summary
    logger.info("=" * 60)
    logger.info("TRINITY INGEST SUMMARY")
    logger.info("=" * 60)
    for name, stats in all_stats.items():
        logger.info(
            "  %s: %d ingested / %d total (%d failed)",
            name,
            stats["ingested"],
            stats["total"],
            stats["failed"],
        )


if __name__ == "__main__":
    main()
