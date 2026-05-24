"""Claude Bridge — syncs Claude Code memory files to substrate memory candidates.

Watches ~/.claude/projects/-opt-OS/memory/ for memory files with YAML
frontmatter. Each file becomes a substrate memory candidate, which flows
through the standard promotion → reconciliation → canonical pipeline.

Can be run as a one-shot sync or as a continuous watcher.

UMH substrate subsystem.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from substrate.memory.candidate_generator import MemoryCandidateGenerator
from substrate.memory.promoter import MemoryPromoter
from substrate.memory.auto_reconciler import AutoReconciler

logger = logging.getLogger(__name__)

CLAUDE_MEMORY_DIR = Path.home() / ".claude" / "projects" / "-opt-OS" / "memory"

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


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a memory file. Returns (meta, body)."""
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    yaml_block = match.group(1)
    body = match.group(2).strip()

    meta: dict[str, str] = {}
    for line in yaml_block.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key in ("name", "description", "type"):
                meta[key] = value
            elif key == "metadata":
                continue
            elif "type" in key:
                continue

    # Handle nested type under metadata
    if "type" not in meta:
        for line in yaml_block.split("\n"):
            stripped = line.strip()
            if stripped.startswith("type:"):
                meta["type"] = stripped.split(":", 1)[1].strip().strip("'\"")

    return meta, body


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


class ClaudeMemoryBridge:
    """Syncs Claude Code memory files to substrate memory candidates."""

    def __init__(
        self,
        memory_dir: Path | None = None,
        candidate_gen: MemoryCandidateGenerator | None = None,
        promoter: MemoryPromoter | None = None,
        reconciler: AutoReconciler | None = None,
    ) -> None:
        self._dir = memory_dir or CLAUDE_MEMORY_DIR
        self._gen = candidate_gen or MemoryCandidateGenerator()
        self._promoter = promoter or MemoryPromoter()
        self._reconciler = reconciler or AutoReconciler()
        self._synced_hashes: set[str] = set()
        self._hash_file = Path("data/umh/claude_memory_sync_hashes.json")
        self._load_synced()

    def _load_synced(self) -> None:
        if self._hash_file.exists():
            import json
            try:
                self._synced_hashes = set(json.loads(self._hash_file.read_text()))
            except (json.JSONDecodeError, OSError):
                self._synced_hashes = set()

    def _save_synced(self) -> None:
        import json
        self._hash_file.parent.mkdir(parents=True, exist_ok=True)
        self._hash_file.write_text(json.dumps(sorted(self._synced_hashes)))

    def sync(self) -> dict[str, Any]:
        """One-shot sync of all Claude memory files to substrate.

        Returns summary: new, skipped, errors.
        """
        if not self._dir.exists():
            return {"new": 0, "skipped": 0, "errors": 0, "detail": "dir not found"}

        results = {"new": 0, "skipped": 0, "errors": 0, "details": []}

        for path in sorted(self._dir.glob("*.md")):
            if path.name == "MEMORY.md":
                continue

            file_hash = _file_hash(path)
            if file_hash in self._synced_hashes:
                results["skipped"] += 1
                continue

            try:
                text = path.read_text(encoding="utf-8")
                meta, body = _parse_frontmatter(text)

                if not body or not meta.get("name"):
                    results["skipped"] += 1
                    continue

                mem_type = meta.get("type", "project")
                confidence = TYPE_TO_CONFIDENCE.get(mem_type, 0.75)
                scope = TYPE_TO_SCOPE.get(mem_type, "project")

                content = f"{meta.get('description', meta['name'])}: {body[:500]}"

                candidate = self._gen.generate_candidate(
                    source_trace_id=f"claude-memory-{meta['name']}",
                    content=content,
                    reason=f"synced from Claude Code memory: {path.name}",
                    confidence=confidence,
                    scope=scope,
                    tags=["claude-memory", mem_type, meta["name"]],
                )

                promotion = self._promoter.evaluate(candidate)
                if promotion.get("promoted"):
                    recon = self._reconciler.reconcile_promoted(candidate, promotion)
                    results["details"].append({
                        "file": path.name,
                        "action": recon.get("action", "unknown"),
                    })
                    results["new"] += 1
                else:
                    results["details"].append({
                        "file": path.name,
                        "action": "promotion_skipped",
                        "reason": promotion.get("reason", ""),
                    })
                    results["skipped"] += 1

                self._synced_hashes.add(file_hash)

            except Exception as e:
                logger.error("Failed to sync %s: %s", path.name, e)
                results["errors"] += 1

        self._save_synced()
        logger.info(
            "Claude memory sync: %d new, %d skipped, %d errors",
            results["new"], results["skipped"], results["errors"],
        )
        return results


def sync_claude_memories() -> dict[str, Any]:
    """Convenience function for scripts and cron."""
    bridge = ClaudeMemoryBridge()
    return bridge.sync()
