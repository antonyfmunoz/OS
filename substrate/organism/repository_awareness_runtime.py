"""Repository Awareness Runtime — file-level depth for repositories.

WorkspaceAwarenessRuntime detects the ACTIVE workspace (device, repo, branch).
RepositoryAwarenessRuntime adds file-level depth: directory structure,
file categories, important files, file-to-entity mapping.

Read-only observation pattern. Instance-agnostic.

Campaign 6.1. UMH substrate layer.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"

_IGNORE_DIRS = frozenset({
    ".git", "__pycache__", "node_modules", ".mypy_cache",
    ".ruff_cache", ".pytest_cache", ".claude",
    ".venv", "venv", ".tox", "dist", "build",
    ".next", ".nuxt", ".turbo",
})

_IMPORTANT_PATTERNS = [
    "CLAUDE.md", "README*", "package.json", "requirements.txt",
    "Dockerfile", "docker-compose*", "pyproject.toml", "tsconfig.json",
    ".env.example", ".env.tpl", "ARCHITECTURE.md", "Makefile",
    "PROTOCOLS.md", "PHILOSOPHY.md", "compose.yml", "compose.yaml",
]

_EXT_TO_CATEGORY: dict[str, str] = {
    ".py": "source_code", ".ts": "source_code", ".tsx": "source_code",
    ".js": "source_code", ".jsx": "source_code", ".go": "source_code",
    ".rs": "source_code", ".java": "source_code", ".rb": "source_code",
    ".c": "source_code", ".cpp": "source_code", ".h": "source_code",
    ".swift": "source_code", ".kt": "source_code", ".cs": "source_code",
    ".json": "configuration", ".yaml": "configuration", ".yml": "configuration",
    ".toml": "configuration", ".ini": "configuration", ".cfg": "configuration",
    ".md": "documentation", ".txt": "documentation", ".rst": "documentation",
    ".adoc": "documentation",
    ".csv": "data", ".jsonl": "data", ".sql": "data", ".db": "data",
    ".parquet": "data",
    ".tf": "infrastructure", ".hcl": "infrastructure",
    ".sh": "build", ".bash": "build",
}


# ── Types ─────────────────────────────────────────────────────────────────


class FileCategory(str, Enum):
    SOURCE_CODE = "source_code"
    TEST = "test"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    BUILD = "build"
    DATA = "data"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


@dataclass
class FileEntry:
    path: str
    category: str
    size_bytes: int
    last_modified: float
    entity_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepositorySnapshot:
    repository_id: str
    name: str
    root_path: str
    branch: str
    file_count: int
    files_by_category: dict[str, int] = field(default_factory=dict)
    important_files: list[FileEntry] = field(default_factory=list)
    recent_changes: list[dict[str, Any]] = field(default_factory=list)
    detected_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "name": self.name,
            "root_path": self.root_path,
            "branch": self.branch,
            "file_count": self.file_count,
            "files_by_category": self.files_by_category,
            "important_files": [f.to_dict() for f in self.important_files],
            "recent_changes": self.recent_changes,
            "detected_at": self.detected_at,
        }


# ── Repository Awareness Runtime ─────────────────────────────────────────


class RepositoryAwarenessRuntime:
    """File-level awareness for repositories.

    Composes WorkspaceAwarenessRuntime (active context) with filesystem
    scanning to provide file categories, important files, and entity mapping.
    """

    def __init__(
        self,
        workspace_awareness: Any = None,
        artifact_registry: Any = None,
        reality_graph: Any = None,
    ) -> None:
        self._workspace = workspace_awareness
        self._artifacts = artifact_registry
        self._graph = reality_graph
        self._last_scan: RepositorySnapshot | None = None

    def scan_repository(self, repo_path: str) -> RepositorySnapshot:
        """Deterministic filesystem scan of a repository."""
        now = time.time()
        repo_name = os.path.basename(os.path.abspath(repo_path))
        branch = self._detect_branch(repo_path)

        files_by_category: dict[str, int] = {}
        file_count = 0

        for dirpath, dirnames, filenames in os.walk(repo_path):
            dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, repo_path)
                cat = self.categorize_file(rel_path)
                files_by_category[cat] = files_by_category.get(cat, 0) + 1
                file_count += 1

        important = self.detect_important_files(repo_path)
        recent = self.get_recent_changes(repo_path)

        snap = RepositorySnapshot(
            repository_id=f"repo-{repo_name}",
            name=repo_name,
            root_path=repo_path,
            branch=branch,
            file_count=file_count,
            files_by_category=files_by_category,
            important_files=important,
            recent_changes=recent,
            detected_at=now,
        )
        self._last_scan = snap
        return snap

    def detect_important_files(self, repo_path: str) -> list[FileEntry]:
        """Pattern-matched detection of important repository files."""
        import fnmatch

        result: list[FileEntry] = []
        seen: set[str] = set()

        try:
            entries = os.listdir(repo_path)
        except OSError:
            return result

        for pattern in _IMPORTANT_PATTERNS:
            for entry_name in entries:
                if fnmatch.fnmatch(entry_name, pattern):
                    full = os.path.join(repo_path, entry_name)
                    if os.path.isfile(full) and entry_name not in seen:
                        seen.add(entry_name)
                        try:
                            stat = os.stat(full)
                            result.append(FileEntry(
                                path=entry_name,
                                category=self.categorize_file(entry_name),
                                size_bytes=stat.st_size,
                                last_modified=stat.st_mtime,
                            ))
                        except OSError:
                            pass
        return result

    def categorize_file(self, path: str) -> str:
        """Classify a file by extension and path patterns."""
        basename = os.path.basename(path)
        lower_basename = basename.lower()
        lower_path = path.lower()

        if "/tests/" in lower_path or "/test/" in lower_path or "\\tests\\" in lower_path:
            return FileCategory.TEST.value
        if lower_path.startswith("tests/") or lower_path.startswith("test/"):
            return FileCategory.TEST.value
        if lower_basename.startswith("test_") or "_test." in lower_basename:
            return FileCategory.TEST.value
        if ".test." in lower_basename or ".spec." in lower_basename:
            return FileCategory.TEST.value

        if lower_basename.startswith("dockerfile"):
            return FileCategory.BUILD.value
        if lower_basename == "makefile":
            return FileCategory.BUILD.value

        if lower_basename.startswith(".env"):
            return FileCategory.CONFIGURATION.value

        _, ext = os.path.splitext(lower_basename)
        cat = _EXT_TO_CATEGORY.get(ext)
        if cat:
            return cat

        return FileCategory.UNKNOWN.value

    def find_files_for_entity(self, entity_id: str) -> list[FileEntry]:
        """Find scanned files related to a RealityGraph entity."""
        if self._graph is None or self._last_scan is None:
            return []

        entity = self._graph.get(entity_id)
        if entity is None:
            return []

        name_lower = entity.name.lower()
        result: list[FileEntry] = []
        for imp in self._last_scan.important_files:
            if name_lower in imp.path.lower():
                result.append(imp)
        return result

    def get_recent_changes(
        self,
        repo_path: str,
        count: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent git commits. Deterministic, no LLM."""
        try:
            from substrate.execution.cpu_gate import gated_subprocess_run
            proc = gated_subprocess_run(
                ["git", "log", f"--format=%H|%s|%an|%at", f"-n{count}"],
                caller="repository_awareness.get_recent_changes",
                capture_output=True, text=True, timeout=10,
                cwd=repo_path,
            )
            if proc is None or proc.returncode != 0:
                return []
        except (FileNotFoundError, OSError):
            return []

        commits: list[dict[str, Any]] = []
        for line in proc.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 3)
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0][:8],
                    "message": parts[1],
                    "author": parts[2],
                    "timestamp": int(parts[3]) if parts[3].isdigit() else 0,
                })
        return commits

    def snapshot(self) -> dict[str, Any]:
        """Return last scan as dict, or scan active workspace."""
        if self._last_scan is not None:
            return self._last_scan.to_dict()

        if self._workspace is not None:
            ws_snap = None
            if hasattr(self._workspace, "detect"):
                ws_snap = self._workspace.detect()
            elif hasattr(self._workspace, "snapshot"):
                ws_snap = self._workspace.snapshot()

            if ws_snap is not None:
                repo_path = getattr(ws_snap, "directory", "") or getattr(ws_snap, "root_path", "")
                if repo_path and os.path.isdir(repo_path):
                    return self.scan_repository(repo_path).to_dict()

        return {}

    @staticmethod
    def _detect_branch(repo_path: str) -> str:
        try:
            from substrate.execution.cpu_gate import gated_subprocess_run
            proc = gated_subprocess_run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                caller="repository_awareness._detect_branch",
                capture_output=True, text=True, timeout=5,
                cwd=repo_path,
            )
            if proc is not None and proc.returncode == 0:
                return proc.stdout.strip()
        except (FileNotFoundError, OSError):
            pass
        return "unknown"
