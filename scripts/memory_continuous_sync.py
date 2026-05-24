#!/usr/bin/env python3
"""Continuous memory synchronization.

Runs as a cron job or one-shot. Three operations:
1. Sweep promoted_memories.json → canonical store (catches pipeline gaps)
2. Sync Claude Code memory files → substrate candidates → canonical
3. Report stats

Usage:
    python3 scripts/memory_continuous_sync.py          # one-shot
    python3 scripts/memory_continuous_sync.py --stats   # stats only
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/opt/OS")

from substrate.memory.promoter import MemoryPromoter
from substrate.memory.auto_reconciler import AutoReconciler
from substrate.memory.candidate_generator import MemoryCandidate
from substrate.memory.claude_bridge import sync_claude_memories
from substrate.state.memory.contracts.canonical_memory_store_v1 import (
    CanonicalMemoryStore,
)


def sweep_promoted_to_canonical() -> dict:
    """Move any promoted memories that aren't in canonical store yet."""
    promoted_path = Path("data/umh/promoted_memories.json")
    if not promoted_path.exists():
        return {"swept": 0, "skipped": 0}

    promoted = json.loads(promoted_path.read_text())
    store = CanonicalMemoryStore()
    reconciler = AutoReconciler(store=store)

    swept = 0
    skipped = 0

    for mem in promoted:
        existing = store.query_by_id(mem.get("memory_id", ""))
        if existing:
            skipped += 1
            continue

        candidate = MemoryCandidate(
            candidate_id=mem["candidate_id"],
            source_trace_id=mem.get("trace_id", ""),
            content=mem["content"],
            reason="sweep from promoted_memories.json",
            confidence=mem["confidence"],
            scope=mem.get("scope", "session"),
            tags=mem.get("tags", []),
        )
        promotion = {"promoted": True, "memory_id": mem["memory_id"]}
        try:
            recon = reconciler.reconcile_promoted(candidate, promotion)
            if recon.get("action") == "promoted_to_canonical":
                swept += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  Error sweeping {mem['memory_id']}: {e}")

    return {"swept": swept, "skipped": skipped}


def print_stats():
    """Print memory system statistics."""
    store = CanonicalMemoryStore()
    stats = store.get_stats()

    promoted_path = Path("data/umh/promoted_memories.json")
    promoted_count = 0
    if promoted_path.exists():
        promoted_count = len(json.loads(promoted_path.read_text()))

    candidates_path = Path("data/umh/memory_candidates/candidates.jsonl")
    candidate_count = 0
    if candidates_path.exists():
        with open(candidates_path) as f:
            candidate_count = sum(1 for _ in f)

    claude_dir = Path.home() / ".claude" / "projects" / "-opt-OS" / "memory"
    claude_count = len(list(claude_dir.glob("*.md"))) - 1 if claude_dir.exists() else 0

    sync_hashes = Path("data/umh/claude_memory_sync_hashes.json")
    synced_count = 0
    if sync_hashes.exists():
        synced_count = len(json.loads(sync_hashes.read_text()))

    print("=== UMH Memory System Stats ===")
    print(f"  Candidates staged:     {candidate_count}")
    print(f"  Promoted (staging):    {promoted_count}")
    print(f"  Canonical store:       {stats.get('total', 0)}")
    print(f"    Canonical type:      {stats.get('canonical', 0)}")
    print(f"    Instance type:       {stats.get('instance', 0)}")
    print(f"  Claude Code memories:  {claude_count}")
    print(f"  Claude synced:         {synced_count}")
    print(f"  Unsynced Claude:       {claude_count - synced_count}")


def main():
    if "--stats" in sys.argv:
        print_stats()
        return

    start = time.time()
    print("=== Memory Continuous Sync ===")

    print("\n1. Sweeping promoted → canonical...")
    sweep = sweep_promoted_to_canonical()
    print(f"   Swept: {sweep['swept']}, Already in canonical: {sweep['skipped']}")

    print("\n2. Syncing Claude Code memories → substrate...")
    claude = sync_claude_memories()
    print(f"   New: {claude['new']}, Skipped: {claude['skipped']}, Errors: {claude['errors']}")
    for d in claude.get("details", []):
        print(f"     {d.get('file', '?')}: {d.get('action', '?')}")

    print(f"\n3. Stats:")
    print_stats()

    print(f"\nDone in {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
