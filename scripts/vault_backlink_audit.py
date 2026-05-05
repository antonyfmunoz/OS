#!/usr/bin/env python3
"""
Vault Backlink Health + Retrieval Signal Report

Surfaces backlinking opportunities and retrieval-quality signals
across 10_Wiki/ and vault/.

Reports:
1. Wiki knowledge pages with zero incoming links (true orphans)
2. Summaries that promoted wiki pages but don't link to them
3. Dead-end wiki pages (inbound links but no useful outbound navigation)
4. Graph nodes with known wiki pages but no inbound wiki references
5. Quick stats on link density + retrieval coverage

This is a diagnostic tool, not an enforcer.
Linking should be intelligent and navigational, not mechanical.

Usage:
    python3 scripts/vault_backlink_audit.py
    python3 scripts/vault_backlink_audit.py --retrieval   # include retrieval signals
"""

import argparse
import json
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, "/opt/OS")

VAULT_ROOT = Path("/opt/OS")
WIKI_DIR = VAULT_ROOT / "10_Wiki"
VAULT_DIR = VAULT_ROOT / "vault"

# Directories to skip
SKIP_DIRS = {
    "10_Wiki/codebase",
    "10_Wiki/palace",
    "vault/memory/conversations",
}

# Meta files that don't need incoming links
META_FILES = {
    "index.md",
    "log.md",
    "WIKI_RULES.md",
    "cloud_palace.md",
    "retrieval_rules.md",
    "cloud.md",
}


def extract_wikilinks(content: str) -> set[str]:
    """Extract [[target]] slugs from content."""
    return {m.strip() for m in re.findall(r"\[\[([^\]|#]+)", content)}


def find_scannable_files() -> list[Path]:
    """All .md files excluding machine-generated dirs."""
    files = []
    for scan_dir in (WIKI_DIR, VAULT_DIR):
        if not scan_dir.exists():
            continue
        for md in scan_dir.rglob("*.md"):
            rel_str = str(md.relative_to(VAULT_ROOT))
            if any(rel_str.startswith(skip) for skip in SKIP_DIRS):
                continue
            files.append(md)
    return sorted(files)


def run_health_check(show_retrieval: bool = False) -> None:
    all_files = find_scannable_files()

    # Build link graph: slug -> set of slugs that link to it
    incoming: dict[str, set[str]] = {}
    outgoing: dict[str, set[str]] = {}
    wiki_slugs: set[str] = set()

    # Index wiki knowledge pages (concepts, entities, decisions, synthesis)
    for md in WIKI_DIR.rglob("*.md"):
        rel_str = str(md.relative_to(VAULT_ROOT))
        if any(rel_str.startswith(skip) for skip in SKIP_DIRS):
            continue
        if md.name in META_FILES:
            continue
        slug = md.stem
        wiki_slugs.add(slug)
        incoming.setdefault(slug, set())

    # Build incoming link map from all files
    for f in all_files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        source_slug = f.stem
        links = extract_wikilinks(content)
        outgoing[source_slug] = links
        for link in links:
            # Normalize: [[summaries/summary_xxx]] -> take final component too
            targets = [link]
            if "/" in link:
                targets.append(link.rsplit("/", 1)[-1])
            for t in targets:
                if t in incoming:
                    incoming[t].add(source_slug)

    # Report
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"\n  Vault Backlink Health — {now}\n")

    # 1. Orphan wiki pages (knowledge pages with zero incoming)
    orphans = [s for s in sorted(wiki_slugs) if not incoming.get(s)]
    if orphans:
        print(f"  Wiki pages with no incoming links ({len(orphans)}):")
        for s in orphans:
            print(f"    - {s}")
    else:
        print("  All wiki knowledge pages have incoming links.")

    # 2. Summaries missing links to promoted pages
    print()
    summaries_dir = VAULT_DIR / "memory" / "summaries"
    promo_gaps = []
    if summaries_dir.exists():
        for md in summaries_dir.glob("*.md"):
            try:
                content = md.read_text(encoding="utf-8")
            except Exception:
                continue
            # Parse promoted_to from frontmatter
            fm = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if not fm:
                continue
            promoted: list[str] = []
            in_promoted = False
            for line in fm.group(1).split("\n"):
                if line.startswith("promoted_to:"):
                    in_promoted = True
                    continue
                if in_promoted:
                    if line.startswith("- "):
                        promoted.append(line[2:].strip())
                    else:
                        in_promoted = False
            if not promoted:
                continue
            existing = extract_wikilinks(content)
            missing = [p for p in promoted if p not in existing]
            if missing:
                promo_gaps.append((md.name, missing))

    if promo_gaps:
        print(f"  Summaries missing links to promoted pages ({len(promo_gaps)}):")
        for name, missing in promo_gaps:
            print(f"    - {name}: {', '.join(missing)}")
    else:
        print("  All summaries link to their promoted pages.")

    # 3. Stats
    total_links = sum(len(v) for v in outgoing.values())
    files_with_links = sum(1 for v in outgoing.values() if v)
    print(f"\n  Stats:")
    print(f"    Files scanned:       {len(all_files)}")
    print(f"    Wiki knowledge pages: {len(wiki_slugs)}")
    print(f"    Files with links:    {files_with_links}")
    print(f"    Total wikilinks:     {total_links}")
    print()

    if show_retrieval:
        run_retrieval_signals(wiki_slugs, incoming, outgoing)


GRAPH_PATH = Path("/opt/OS/data/codebase_graph.json")


def run_retrieval_signals(
    wiki_slugs: set[str],
    incoming: dict[str, set[str]],
    outgoing: dict[str, set[str]],
) -> None:
    """Report retrieval-quality signals for the wiki-graph bridge.

    Requires the graph to be present. Reports:
    - Dead-end wiki pages (inbound but no useful outbound)
    - Graph nodes with promoted wiki pages but no inbound wiki references
    - Retrieval coverage stats
    """
    print("  Retrieval Signal Report\n")

    # Dead-end wiki pages: have incoming links but no outgoing knowledge links
    knowledge_slugs = wiki_slugs  # concepts, entities, decisions, synthesis
    dead_ends = []
    for slug in sorted(knowledge_slugs):
        has_incoming = bool(incoming.get(slug))
        slug_outgoing = outgoing.get(slug, set())
        # Filter: outgoing links that point to other knowledge pages
        useful_outgoing = slug_outgoing & knowledge_slugs
        if has_incoming and not useful_outgoing:
            dead_ends.append(slug)

    if dead_ends:
        print(
            f"  Dead-end wiki pages — inbound links but no outbound to other knowledge ({len(dead_ends)}):"
        )
        for s in dead_ends:
            in_count = len(incoming.get(s, set()))
            print(f"    - {s}  (incoming: {in_count})")
    else:
        print("  No dead-end wiki pages found.")

    # Graph-wiki coverage: check if WikiIndex can map nodes
    print()
    try:
        from core.wiki_navigation import WikiIndex

        if not GRAPH_PATH.exists():
            print("  [skip] Graph not found — cannot compute retrieval coverage")
            return

        graph = json.loads(GRAPH_PATH.read_text())
        wiki_index = WikiIndex().build(graph)

        mapped_nodes = len(wiki_index.node_to_slug)
        total_files = len(graph.get("files", {}))
        coverage_pct = (mapped_nodes / total_files * 100) if total_files else 0

        print(f"  Graph-wiki mapping:")
        print(f"    Wiki knowledge pages:  {len(wiki_index.slug_to_path)}")
        print(
            f"    Mapped graph nodes:    {mapped_nodes} / {total_files} ({coverage_pct:.1f}%)"
        )
        print(
            f"    Promoted summaries:    {sum(wiki_index.slug_has_promotion.values())}"
        )

        # Wiki pages with promoted summaries but zero incoming wiki links
        promo_no_inbound = []
        for slug, has_promo in wiki_index.slug_has_promotion.items():
            if has_promo and not incoming.get(slug):
                promo_no_inbound.append(slug)

        if promo_no_inbound:
            print(
                f"\n  Promoted pages with no inbound wiki links ({len(promo_no_inbound)}):"
            )
            for s in promo_no_inbound:
                print(f"    - {s}")
        else:
            print("  All promoted pages have inbound wiki links.")

    except ImportError:
        print("  [skip] core.wiki_navigation not available")
    except Exception as e:
        print(f"  [error] Retrieval signal check failed: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vault backlink health + retrieval signals"
    )
    parser.add_argument(
        "--retrieval",
        action="store_true",
        help="Include retrieval signal report (requires graph + wiki_navigation)",
    )
    args = parser.parse_args()
    run_health_check(show_retrieval=args.retrieval)


if __name__ == "__main__":
    main()
