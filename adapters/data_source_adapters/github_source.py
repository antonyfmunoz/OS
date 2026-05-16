"""GitHubRepoSource — reads a single file from a cloned GitHub repo as an ingestion source.

GitHubRepoWalker — clones a repo (depth=1) and yields GitHubRepoSource for each
relevant file, filtered by extension and directory exclusions.
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from governance.policy.authority_tier import T4_SUPPORTING, validate_tier
from understanding.perception.source import RawContent, Source

logger = logging.getLogger(__name__)

# Default clone location for repos
_DEFAULT_REPOS_DIR = Path("/opt/OS/data/repos")


class GitHubRepoSource:
    """Wraps a single file from a cloned GitHub repo as a Source."""

    source_type: str = "github_repo_file"

    def __init__(
        self,
        repo: str,
        file_path: Path,
        repo_root: Path,
        *,
        commit_sha: str,
        authority_tier: int = T4_SUPPORTING,
    ) -> None:
        """Initialize a GitHub file source.

        Args:
            repo: Repository in "owner/name" format.
            file_path: Absolute path to the file on disk.
            repo_root: Root directory of the cloned repo.
            commit_sha: HEAD commit SHA at clone/pull time.
            authority_tier: Authority tier for this source (default T4_SUPPORTING).
        """
        self._repo = repo
        self._file_path = Path(file_path).resolve()
        self._repo_root = Path(repo_root).resolve()
        self._commit_sha = commit_sha
        self.authority_tier: int = validate_tier(authority_tier)
        self._cached_content: RawContent | None = None

    @property
    def source_id(self) -> str:
        """Unique identifier: github:{owner/repo}:{relative_path}@{sha}."""
        rel = self._file_path.relative_to(self._repo_root)
        return f"github:{self._repo}:{rel}@{self._commit_sha}"

    def exists(self) -> bool:
        """Check if the file exists on disk."""
        return self._file_path.is_file()

    def read(self) -> RawContent:
        """Read file content, compute sha256, detect content_type."""
        text = self._file_path.read_text(encoding="utf-8")
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        content_type = mimetypes.guess_type(str(self._file_path))[0] or "text/plain"
        self._cached_content = RawContent(
            content=text,
            content_type=content_type,
            size_bytes=len(text.encode("utf-8")),
            sha256=sha,
        )
        return self._cached_content

    def metadata(self) -> dict[str, Any]:
        """Return metadata about this file source."""
        rel = self._file_path.relative_to(self._repo_root)
        stat = self._file_path.stat() if self._file_path.exists() else None
        return {
            "repo": self._repo,
            "path": str(rel),
            "filename": self._file_path.name,
            "extension": self._file_path.suffix,
            "commit_sha": self._commit_sha,
            "size_bytes": stat.st_size if stat else 0,
            "content_type": mimetypes.guess_type(str(self._file_path))[0] or "text/plain",
        }


class GitHubRepoWalker:
    """Clones a repo and yields GitHubRepoSource for each relevant file."""

    INCLUDE_EXTENSIONS: set[str] = {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".md",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".sql",
        ".sh",
    }

    EXCLUDE_DIRS: set[str] = {
        "node_modules",
        ".git",
        "__pycache__",
        ".next",
        "dist",
        "build",
        ".venv",
        "venv",
    }

    def __init__(
        self,
        repo: str,
        *,
        clone_dir: Path | None = None,
        authority_tier: int = T4_SUPPORTING,
    ) -> None:
        """Initialize the walker.

        Args:
            repo: Repository in "owner/name" format.
            clone_dir: Where to clone. Defaults to /opt/OS/data/repos/{owner}/{name}/.
            authority_tier: Authority tier for yielded sources.
        """
        self._repo = repo
        self._authority_tier = validate_tier(authority_tier)

        if clone_dir is not None:
            self._clone_dir = Path(clone_dir)
        else:
            parts = repo.split("/")
            if len(parts) != 2:
                raise ValueError(f"repo must be 'owner/name', got: {repo!r}")
            self._clone_dir = _DEFAULT_REPOS_DIR / parts[0] / parts[1]

        self._commit_sha: str | None = None

    def _git_url(self) -> str:
        """Build the clone URL, using GITHUB_PAT if available."""
        pat = os.environ.get("GITHUB_PAT", "")
        if pat:
            return f"https://{pat}@github.com/{self._repo}.git"
        logger.warning("GITHUB_PAT not set — using unauthenticated access (60 req/hr limit)")
        return f"https://github.com/{self._repo}.git"

    def clone_or_pull(self) -> str:
        """Clone repo (depth=1) or pull if already cloned. Returns HEAD commit SHA."""
        self._clone_dir.mkdir(parents=True, exist_ok=True)

        git_dir = self._clone_dir / ".git"
        if git_dir.is_dir():
            # Pull latest
            logger.info("Pulling latest for %s in %s", self._repo, self._clone_dir)
            result = subprocess.run(
                ["git", "-C", str(self._clone_dir), "pull", "--ff-only"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.error("git pull failed: %s", result.stderr.strip())
                raise RuntimeError(f"git pull failed for {self._repo}: {result.stderr}")
        else:
            # Fresh clone
            logger.info("Cloning %s into %s", self._repo, self._clone_dir)
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth=1",
                    self._git_url(),
                    str(self._clone_dir),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.error("git clone failed: %s", result.stderr.strip())
                raise RuntimeError(f"git clone failed for {self._repo}: {result.stderr}")

        # Get HEAD sha
        sha_result = subprocess.run(
            ["git", "-C", str(self._clone_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if sha_result.returncode != 0:
            raise RuntimeError(f"Cannot read HEAD for {self._repo}")

        self._commit_sha = sha_result.stdout.strip()
        logger.info("HEAD for %s: %s", self._repo, self._commit_sha)
        return self._commit_sha

    def walk(self) -> Iterator[GitHubRepoSource]:
        """Yield a Source for each relevant file in the repo."""
        if self._commit_sha is None:
            raise RuntimeError("Call clone_or_pull() before walk()")

        for path in sorted(self._clone_dir.rglob("*")):
            if not path.is_file():
                continue
            # Check exclusions
            if any(part in self.EXCLUDE_DIRS for part in path.parts):
                continue
            # Check extension
            if path.suffix not in self.INCLUDE_EXTENSIONS:
                continue
            # Skip binary/unreadable
            try:
                path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                logger.debug("Skipping unreadable file: %s", path)
                continue

            yield GitHubRepoSource(
                repo=self._repo,
                file_path=path,
                repo_root=self._clone_dir,
                commit_sha=self._commit_sha,
                authority_tier=self._authority_tier,
            )

    def changed_since(self, last_sha: str) -> Iterator[GitHubRepoSource]:
        """Yield Sources only for files changed since last_sha.

        Requires the repo to NOT be shallow (depth=1 clone may not have last_sha).
        Falls back to full walk if diff fails.
        """
        if self._commit_sha is None:
            raise RuntimeError("Call clone_or_pull() before changed_since()")

        result = subprocess.run(
            [
                "git",
                "-C",
                str(self._clone_dir),
                "diff",
                "--name-only",
                last_sha,
                "HEAD",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.warning(
                "git diff failed (shallow clone?), falling back to full walk: %s",
                result.stderr.strip(),
            )
            yield from self.walk()
            return

        changed_files = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        logger.info(
            "%d files changed since %s in %s",
            len(changed_files),
            last_sha[:8],
            self._repo,
        )

        for rel_path_str in sorted(changed_files):
            abs_path = self._clone_dir / rel_path_str
            if not abs_path.is_file():
                continue
            if any(part in self.EXCLUDE_DIRS for part in abs_path.parts):
                continue
            if abs_path.suffix not in self.INCLUDE_EXTENSIONS:
                continue
            try:
                abs_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            yield GitHubRepoSource(
                repo=self._repo,
                file_path=abs_path,
                repo_root=self._clone_dir,
                commit_sha=self._commit_sha,
                authority_tier=self._authority_tier,
            )


# Protocol conformance check
assert isinstance(GitHubRepoSource, type)
_check: type[Source] = GitHubRepoSource  # type: ignore[assignment]
