#!/usr/bin/env python3
"""Instant memory sync hook — fires on PostToolUse for Write/Edit.

Checks if the written file is a Claude Code memory file. If so,
immediately syncs that single file to substrate canonical store.

Runs in <100ms. Never blocks the session.
"""

import os
import sys

file_path = os.environ.get("CLAUDE_TOOL_INPUT_FILE_PATH", "")

if not file_path or "/.claude/" not in file_path or "/memory/" not in file_path:
    sys.exit(0)

if file_path.endswith("MEMORY.md"):
    sys.exit(0)

if not file_path.endswith(".md"):
    sys.exit(0)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import hashlib
import json
import re
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.+?)\n---\s*\n(.*)$", re.DOTALL)
TYPE_TO_CONFIDENCE = {"feedback": 0.9, "user": 0.85, "project": 0.8, "reference": 0.85}
TYPE_TO_SCOPE = {"feedback": "global", "user": "global", "project": "project", "reference": "project"}
HASH_FILE = Path("data/umh/claude_memory_sync_hashes.json")


def parse_frontmatter(text):
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    yaml_block, body = match.group(1), match.group(2).strip()
    meta = {}
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


try:
    path = Path(file_path)
    if not path.exists():
        sys.exit(0)

    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    if not body or not meta.get("name"):
        sys.exit(0)

    file_hash = hashlib.sha256(path.read_bytes()).hexdigest()[:16]

    synced = set()
    if HASH_FILE.exists():
        try:
            synced = set(json.loads(HASH_FILE.read_text()))
        except (json.JSONDecodeError, OSError):
            pass

    if file_hash in synced:
        sys.exit(0)

    from substrate.memory.candidate_generator import MemoryCandidateGenerator
    from substrate.memory.promoter import MemoryPromoter
    from substrate.memory.auto_reconciler import AutoReconciler

    mem_type = meta.get("type", "project")
    confidence = TYPE_TO_CONFIDENCE.get(mem_type, 0.75)
    scope = TYPE_TO_SCOPE.get(mem_type, "project")
    content = f"{meta.get('description', meta['name'])}: {body[:500]}"

    gen = MemoryCandidateGenerator()
    candidate = gen.generate_candidate(
        source_trace_id=f"claude-memory-{meta['name']}",
        content=content,
        reason=f"instant sync: {path.name}",
        confidence=confidence,
        scope=scope,
        tags=["claude-memory", mem_type, meta["name"]],
    )

    promoter = MemoryPromoter()
    promotion = promoter.evaluate(candidate)

    if promotion.get("promoted"):
        reconciler = AutoReconciler()
        reconciler.reconcile_promoted(candidate, promotion)

    synced.add(file_hash)
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    HASH_FILE.write_text(json.dumps(sorted(synced)))

    print(f"[Memory] Synced {path.name} → canonical ({mem_type}, conf={confidence})")

except Exception as e:
    print(f"[Memory] Sync error: {e}", file=sys.stderr)
    sys.exit(0)
