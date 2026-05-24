"""Memory Watcher — substrate-level filesystem watcher for agent memory directories.

Monitors any number of directories for .md files with YAML frontmatter.
When a file is created or modified, it's immediately synced to the
substrate canonical memory store.

Agent-agnostic: works for Claude Code, Codex, Hermes, or any future
agent that writes structured memory files to a watched directory.

Runs as a substrate daemon thread. Start with MemoryWatcher.start().

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from pathlib import Path
from typing import Any

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from substrate.memory.candidate_generator import MemoryCandidateGenerator
from substrate.memory.promoter import MemoryPromoter
from substrate.memory.auto_reconciler import AutoReconciler

logger = logging.getLogger(__name__)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.+?)\n---\s*\n(.*)$", re.DOTALL)

TYPE_TO_CONFIDENCE = {
    "feedback": 0.9,
    "user": 0.85,
    "project": 0.8,
    "reference": 0.85,
}

TYPE_TO_SCOPE = {
    "feedback": "global",
    "user": "global",
    "project": "project",
    "reference": "project",
}

HASH_STORE = Path("data/umh/memory_watcher_hashes.json")

DEFAULT_WATCH_DIRS = [
    Path.home() / ".claude" / "projects" / "-opt-OS" / "memory",
]


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    yaml_block, body = match.group(1), match.group(2).strip()
    meta: dict[str, str] = {}
    for line in yaml_block.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip().strip("'\"")
            if key in ("name", "description", "type"):
                meta[key] = value
    if "type" not in meta:
        for line in yaml_block.split("\n"):
            s = line.strip()
            if s.startswith("type:"):
                meta["type"] = s.split(":", 1)[1].strip().strip("'\"")
    return meta, body


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


class _SyncedHashes:
    """Thread-safe hash tracking for deduplication."""

    def __init__(self, path: Path = HASH_STORE) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._hashes: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._hashes = set(json.loads(self._path.read_text()))
            except (json.JSONDecodeError, OSError):
                self._hashes = set()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(sorted(self._hashes)))

    def seen(self, h: str) -> bool:
        with self._lock:
            return h in self._hashes

    def add(self, h: str) -> None:
        with self._lock:
            self._hashes.add(h)
            self._save()


class _MemoryFileHandler(FileSystemEventHandler):
    """Handles file creation/modification events in watched directories."""

    def __init__(
        self,
        agent_name: str,
        gen: MemoryCandidateGenerator,
        promoter: MemoryPromoter,
        reconciler: AutoReconciler,
        hashes: _SyncedHashes,
    ) -> None:
        self._agent = agent_name
        self._gen = gen
        self._promoter = promoter
        self._reconciler = reconciler
        self._hashes = hashes
        self._debounce: dict[str, float] = {}

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle(event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle(event.src_path)

    def _handle(self, filepath: str) -> None:
        path = Path(filepath)

        if not path.name.endswith(".md"):
            return
        if path.name == "MEMORY.md":
            return

        now = time.monotonic()
        last = self._debounce.get(filepath, 0)
        if now - last < 1.0:
            return
        self._debounce[filepath] = now

        try:
            self._sync_file(path)
        except Exception as e:
            logger.error("Memory watcher sync error for %s: %s", path.name, e)

    def _sync_file(self, path: Path) -> None:
        if not path.exists():
            return

        fh = _file_hash(path)
        if self._hashes.seen(fh):
            return

        text = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)

        if not body or not meta.get("name"):
            return

        mem_type = meta.get("type", "project")
        confidence = TYPE_TO_CONFIDENCE.get(mem_type, 0.75)
        scope = TYPE_TO_SCOPE.get(mem_type, "project")
        content = f"{meta.get('description', meta['name'])}: {body[:500]}"

        candidate = self._gen.generate_candidate(
            source_trace_id=f"{self._agent}-memory-{meta['name']}",
            content=content,
            reason=f"watcher sync from {self._agent}: {path.name}",
            confidence=confidence,
            scope=scope,
            tags=["agent-memory", self._agent, mem_type, meta["name"]],
        )

        promotion = self._promoter.evaluate(candidate)
        if promotion.get("promoted"):
            recon = self._reconciler.reconcile_promoted(candidate, promotion)
            logger.info(
                "[MemoryWatcher] %s → canonical (%s, %s, conf=%.2f)",
                path.name, self._agent, recon.get("action", "?"), confidence,
            )

        self._hashes.add(fh)


class MemoryWatcher:
    """Watches directories for agent memory files and auto-syncs to substrate.

    Usage:
        watcher = MemoryWatcher()
        watcher.add_directory("/path/to/agent/memory", agent_name="codex")
        watcher.start()  # non-blocking, runs in daemon thread
        ...
        watcher.stop()
    """

    def __init__(self) -> None:
        self._observer = Observer()
        self._observer.daemon = True
        self._gen = MemoryCandidateGenerator()
        self._promoter = MemoryPromoter()
        self._reconciler = AutoReconciler()
        self._hashes = _SyncedHashes()
        self._watches: list[str] = []
        self._started = False

    def add_directory(self, path: str | Path, agent_name: str = "unknown") -> None:
        """Register a directory to watch for memory files."""
        dirpath = Path(path)
        if not dirpath.exists():
            dirpath.mkdir(parents=True, exist_ok=True)

        handler = _MemoryFileHandler(
            agent_name=agent_name,
            gen=self._gen,
            promoter=self._promoter,
            reconciler=self._reconciler,
            hashes=self._hashes,
        )
        self._observer.schedule(handler, str(dirpath), recursive=False)
        self._watches.append(f"{agent_name}:{dirpath}")
        logger.info("[MemoryWatcher] Watching %s for agent '%s'", dirpath, agent_name)

    def add_defaults(self) -> None:
        """Add default watch directories for known agents."""
        home = Path.home()

        claude_mem = home / ".claude" / "projects" / "-opt-OS" / "memory"
        if claude_mem.exists():
            self.add_directory(claude_mem, agent_name="claude-code")

        codex_mem = home / ".codex" / "memory"
        self.add_directory(codex_mem, agent_name="codex")

        hermes_mem = Path("/opt/OS/data/agent_memory/hermes")
        self.add_directory(hermes_mem, agent_name="hermes")

        shared_mem = Path("/opt/OS/data/agent_memory/shared")
        self.add_directory(shared_mem, agent_name="shared")

    def start(self) -> None:
        """Start watching (non-blocking daemon thread)."""
        if self._started:
            return
        self._observer.start()
        self._started = True
        logger.info("[MemoryWatcher] Started with %d watches", len(self._watches))

    def stop(self) -> None:
        """Stop watching."""
        if self._started:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._started = False

    def initial_sync(self) -> dict[str, int]:
        """One-shot sync of all existing files in watched directories."""
        synced = 0
        skipped = 0

        for watch in self._watches:
            agent_name, dirpath_str = watch.split(":", 1)
            dirpath = Path(dirpath_str)
            if not dirpath.exists():
                continue

            handler = _MemoryFileHandler(
                agent_name=agent_name,
                gen=self._gen,
                promoter=self._promoter,
                reconciler=self._reconciler,
                hashes=self._hashes,
            )

            for md_file in sorted(dirpath.glob("*.md")):
                if md_file.name == "MEMORY.md":
                    continue
                fh = _file_hash(md_file)
                if self._hashes.seen(fh):
                    skipped += 1
                    continue
                try:
                    handler._sync_file(md_file)
                    synced += 1
                except Exception as e:
                    logger.error("Initial sync error %s: %s", md_file.name, e)

        return {"synced": synced, "skipped": skipped}

    @property
    def watches(self) -> list[str]:
        return list(self._watches)


def start_memory_watcher() -> MemoryWatcher:
    """Convenience: create watcher with defaults, initial sync, and start."""
    watcher = MemoryWatcher()
    watcher.add_defaults()
    result = watcher.initial_sync()
    logger.info(
        "[MemoryWatcher] Initial sync: %d new, %d already synced",
        result["synced"], result["skipped"],
    )
    watcher.start()
    return watcher
