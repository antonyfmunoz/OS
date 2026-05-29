#!/usr/bin/env python3
"""session_bootstrap.py — Mandatory context load at session start.

Prints, in order:
    1. cloud.md (root system context)
    2. knowledge/palace/index.md (palace index)
    3. data/codebase_pages/cloud.md (graph rules)
    4. knowledge/retrieval_rules.md (enforced hierarchy)
    5. Graph freshness + stale warning

This is the ONLY bootstrap that guarantees context. Any session-start
hook (CLAUDE.md rule, shell alias, Claude Code hook) must invoke this.

Usage:
    python3 scripts/session_bootstrap.py              # full load
    python3 scripts/session_bootstrap.py --compact    # header only
    python3 scripts/session_bootstrap.py --check      # exit 1 if stale
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from scripts.query_graph import GraphQuery

ROOT = Path(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
LOAD_ORDER = [
    ROOT / "cloud.md",
    ROOT / "knowledge" / "palace" / "index.md",
    ROOT / "knowledge" / "cloud_palace.md",
    ROOT / "data" / "codebase_pages" / "cloud.md",
    ROOT / "knowledge" / "retrieval_rules.md",
]

DATA_ARTIFACTS = {
    "graph": ROOT / "data" / "codebase_graph.json",
    "palace": ROOT / "data" / "palace.json",
    "summaries": ROOT / "data" / "node_summaries.json",
}

BANNER = """
================================================================
  UMH KNOWLEDGE SYSTEM — SESSION BOOTSTRAP
  AI MUST read graph before opening raw files.
  Retrieval order: Palace -> Graph -> Summaries -> Raw -> Logs
================================================================
"""


def _read(path: Path) -> str:
    if not path.exists():
        return f"\n[missing: {path}]\n"
    return path.read_text()


def print_full() -> None:
    print(BANNER)
    for p in LOAD_ORDER:
        print(f"\n\n===== {p.relative_to(ROOT)} =====\n")
        print(_read(p))


def print_compact() -> None:
    print(BANNER.strip())
    print("\nDocs:")
    for p in LOAD_ORDER:
        marker = "ok" if p.exists() else "MISSING"
        print(f"  [{marker}] {p.relative_to(ROOT)}")

    print("\nData artifacts:")
    for name, p in DATA_ARTIFACTS.items():
        if p.exists():
            size = p.stat().st_size
            print(f"  [ok]      {name:<10s}  {p.relative_to(ROOT)}  ({size:,} bytes)")
        else:
            print(f"  [MISSING] {name:<10s}  {p.relative_to(ROOT)}")

    # Graph + palace summary lines
    try:
        q = GraphQuery.load()
        stats = q.raw.get("stats", {}) or {}
        langs = q.languages()
        print(
            f"\nGraph:   {stats.get('files', '?')} py files, "
            f"{stats.get('non_python_files', 0)} non-py, "
            f"{stats.get('classes', '?')} classes, "
            f"{stats.get('functions', '?')} functions, "
            f"{stats.get('edges', '?')} edges"
        )
        print(
            "Langs:   "
            + ", ".join(f"{k}={v}" for k, v in sorted(langs.items(), key=lambda r: -r[1]))
        )
    except Exception as exc:  # pragma: no cover — tolerate missing graph
        print(f"\nGraph:   ERROR loading — {exc}")

    if DATA_ARTIFACTS["palace"].exists():
        try:
            p_state = json.loads(DATA_ARTIFACTS["palace"].read_text())
            loci = sum(len(r.get("loci", [])) for r in p_state.get("rooms", []))
            rooms = len(p_state.get("rooms", []))
            stale = p_state.get("source_graph_stale", False)
            print(f"Palace:  {loci} loci across {rooms} rooms  (graph stale={stale})")
        except Exception as exc:  # pragma: no cover
            print(f"Palace:  ERROR — {exc}")

    if DATA_ARTIFACTS["summaries"].exists():
        try:
            s_state = json.loads(DATA_ARTIFACTS["summaries"].read_text())
            print(
                f"Summaries: {len(s_state.get('nodes', {}))} nodes, "
                f"{s_state.get('versions', 0)} versions"
            )
        except Exception as exc:  # pragma: no cover
            print(f"Summaries: ERROR — {exc}")


def check_freshness() -> int:
    try:
        q = GraphQuery.load()
    except FileNotFoundError as e:
        print(f"GRAPH MISSING: {e}", file=sys.stderr)
        return 2
    f = q.freshness()
    if f["stale"]:
        print(
            f"!! GRAPH STALE — generated {f['age_hours']}h ago (>{f['threshold_hours']}h). "
            f"Run scripts/update-graph before making structural decisions.",
            file=sys.stderr,
        )
        return 1
    print(f"graph fresh ({f['age_hours']}h old)")
    return 0


def register_organism_session(harness: str = "claude_code", intent: str = "") -> None:
    """Register this coding session with the organism."""
    try:
        from substrate.organism.development_session_bridge import DevelopmentSessionBridge

        session_id = os.environ.get("CLAUDE_SESSION_ID", "")
        bridge = DevelopmentSessionBridge(
            session_id=session_id or None,
            harness=harness,
        )
        bridge.register_session(intent=intent)
        print(f"\nOrganism: session {bridge.session_id} registered (harness={harness})")
    except Exception as exc:
        print(f"\nOrganism: session registration failed — {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="session_bootstrap")
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--register", action="store_true",
                        help="Register session with organism")
    parser.add_argument("--harness", default="claude_code",
                        help="Harness name (claude_code, codex, etc.)")
    parser.add_argument("--intent", default="",
                        help="Session intent description")
    args = parser.parse_args(argv)

    if args.check:
        return check_freshness()
    if args.compact:
        print_compact()
        check_freshness()
        if args.register:
            register_organism_session(args.harness, args.intent)
        return 0

    print_full()
    check_freshness()
    if args.register:
        register_organism_session(args.harness, args.intent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
