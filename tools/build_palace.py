#!/usr/bin/env python3
"""build_palace.py — Generates the EOS memory palace from the graph.

Structure:
    Palace     -> 10_Wiki/palace/index.md
    Wing       -> 10_Wiki/palace/wings/<wing>.md          (top-level module)
    Room       -> 10_Wiki/palace/rooms/<room>.md          (functional cluster)
    Locus      -> entry inside a room page, wikilinked to 10_Wiki/codebase/

A locus is a high-value file promoted into the palace by score:
    score = inbound_centrality * 2
          + outbound_centrality
          + 10 if critical
          + 3  if entry_point

Usage:
    python3 scripts/build_palace.py
    python3 scripts/build_palace.py --stats
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, "/opt/OS")

from scripts.query_graph import GraphQuery

STALE_GRAPH_HOURS = 24

ROOT = Path("/opt/OS")
PALACE_DIR = ROOT / "10_Wiki" / "palace"
WINGS_DIR = PALACE_DIR / "wings"
ROOMS_DIR = PALACE_DIR / "rooms"
CANDIDATES_DIR = PALACE_DIR / "candidates"
PALACE_JSON = ROOT / "data" / "palace.json"
OVERLAY_JSON = ROOT / "data" / "graphify_overlay.json"

# Overlay clusters with fewer than this many members are not promoted to
# candidate rooms — singletons and tiny groups add noise.
MIN_CANDIDATE_CLUSTER_SIZE = 5

# Functional rooms — each room owns a set of path prefixes.
# Modify to reshape the palace; build_palace.py re-promotes nodes every run.
ROOM_DEFS: list[dict[str, Any]] = [
    {
        "id": "intelligence_core",
        "name": "Intelligence Core",
        "wing": "eos",
        "purpose": "Cognition loop, routing, identity, primitives — the mind of EOS.",
        "prefixes": [
            "eos/cognitive_loop.py",
            "eos/ai_identity.py",
            "eos/agent_runtime.py",
            "eos/agent_hierarchy.py",
            "eos/model_router.py",
            "eos/model_preferences.py",
            "eos/primitives.py",
            "eos/intent_router.py",
            "eos/gateway.py",
        ],
    },
    {
        "id": "memory_persistence",
        "name": "Memory & Persistence",
        "wing": "eos",
        "purpose": "Neon-backed memory, session state, authority, context.",
        "prefixes": [
            "eos/memory.py",
            "eos/db.py",
            "eos/session_state.py",
            "eos/context.py",
            "eos/system_context.py",
            "eos/authority_engine.py",
            "eos/knowledge_integrator.py",
        ],
    },
    {
        "id": "substrate",
        "name": "Substrate Layer",
        "wing": "eos",
        "purpose": "Voice/meeting/operator pipeline — station daemon + transports.",
        "prefixes": ["eos/substrate/"],
    },
    {
        "id": "strategy_orchestration",
        "name": "Strategy & Orchestration",
        "wing": "eos",
        "purpose": "Orchestrator, strategy engine, portfolio advisor, reality engine.",
        "prefixes": [
            "eos/orchestrator.py",
            "eos/strategy_engine.py",
            "eos/portfolio_advisor.py",
            "eos/reality_engine.py",
            "eos/accountability.py",
            "eos/research_engine.py",
        ],
    },
    {
        "id": "transports",
        "name": "Transports",
        "wing": "services",
        "purpose": "Discord, Telegram, webhooks — how EOS reaches the founder.",
        "prefixes": ["services/"],
    },
    {
        "id": "tooling",
        "name": "Tooling & Scripts",
        "wing": "scripts",
        "purpose": "Automation, graph updates, build/verify scripts.",
        "prefixes": ["scripts/"],
    },
    {
        "id": "core_agents",
        "name": "Core Agents",
        "wing": "core",
        "purpose": "Tool mastery author/research agents, execution contract.",
        "prefixes": ["core/"],
    },
]

MAX_LOCI_PER_ROOM = 15
MIN_LOCI_PER_ROOM = 5


def _wikilink_for_file(path: str) -> str:
    """Translate a file path into the Obsidian wikilink used by codebase vault."""
    slug = path.replace("/", "-").replace(".", "-")
    return f"[[{slug}]]"


def score_file(q: GraphQuery, path: str) -> int:
    f = q.raw["files"].get(path, {})
    inbound = len(q.file_imported_by.get(path, ()))
    outbound = len(q.file_imports.get(path, ()))
    score = inbound * 2 + outbound
    if f.get("is_critical"):
        score += 10
    if f.get("is_entry_point"):
        score += 3
    return score


def select_loci(q: GraphQuery, room: dict[str, Any]) -> list[dict[str, Any]]:
    """Pick the highest-scoring files matching any room prefix."""
    candidates: list[tuple[int, str]] = []
    for path in q.raw.get("files", {}):
        if not any(path.startswith(p) or path == p for p in room["prefixes"]):
            continue
        candidates.append((score_file(q, path), path))
    candidates.sort(key=lambda r: r[0], reverse=True)

    keep = candidates[:MAX_LOCI_PER_ROOM]
    if len(keep) < MIN_LOCI_PER_ROOM:
        keep = candidates[: max(MIN_LOCI_PER_ROOM, len(keep))]

    return [
        {
            "path": path,
            "score": score,
            "module": q.raw["files"][path]["module_name"],
            "critical": q.raw["files"][path].get("is_critical", False),
            "entry_point": q.raw["files"][path].get("is_entry_point", False),
            "docstring": (q.raw["files"][path].get("docstring") or "").splitlines()[0]
            if q.raw["files"][path].get("docstring")
            else "",
        }
        for score, path in keep
    ]


def render_room(room: dict[str, Any], loci: list[dict[str, Any]]) -> str:
    lines: list[str] = [
        "---",
        f"type: palace-room",
        f"room_id: {room['id']}",
        f"wing: {room['wing']}",
        f"generated: {datetime.now(timezone.utc).date().isoformat()}",
        "---",
        "",
        f"# Room — {room['name']}",
        "",
        f"**Wing:** [[{room['wing']}-wing|{room['wing']}]]  ",
        f"**Palace:** [[../index|EOS Memory Palace]]",
        "",
        "## Purpose",
        "",
        room["purpose"],
        "",
        "## Core Loci",
        "",
        "Top-ranked files by dependency centrality, criticality, and entry status.",
        "These are the files you most often need; open them before grepping.",
        "",
        "| # | Locus | Score | Flags | One-liner |",
        "|---|-------|-------|-------|-----------|",
    ]
    for i, loc in enumerate(loci, start=1):
        flags = []
        if loc["critical"]:
            flags.append("`critical`")
        if loc["entry_point"]:
            flags.append("`entry`")
        flag_str = " ".join(flags) or "—"
        doc = (loc["docstring"] or "").replace("|", "\\|")[:80]
        lines.append(
            f"| {i} | {_wikilink_for_file(loc['path'])} | {loc['score']} | {flag_str} | {doc} |"
        )
    lines += [
        "",
        "## Traversal",
        "",
        f"- Back to wing → [[{room['wing']}-wing|{room['wing']} wing]]",
        "- Up to palace → [[../index|Memory Palace index]]",
        "- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]",
        "",
        "## Raw Paths",
        "",
        "```",
    ]
    lines += [f"  {loc['path']}" for loc in loci]
    lines += ["```", ""]
    return "\n".join(lines)


def render_wing(wing: str, rooms: list[dict[str, Any]]) -> str:
    lines = [
        "---",
        "type: palace-wing",
        f"wing: {wing}",
        f"generated: {datetime.now(timezone.utc).date().isoformat()}",
        "---",
        "",
        f"# Wing — {wing}",
        "",
        "## Rooms",
        "",
    ]
    for room in rooms:
        lines.append(f"- [[rooms/{room['id']}|{room['name']}]] — {room['purpose']}")
    lines += [
        "",
        "## Traversal",
        "",
        "- Up → [[index|Memory Palace]]",
        "",
    ]
    return "\n".join(lines)


def render_index(rooms_by_wing: dict[str, list[dict[str, Any]]], stats: dict[str, Any]) -> str:
    stale_banner = ""
    if stats.get("graph_stale"):
        stale_banner = (
            f"> **WARNING** — source graph is {stats['graph_age_hours']} h old "
            f"(threshold {STALE_GRAPH_HOURS} h). Palace was rebuilt against a stale graph. "
            f"Run `scripts/update-graph` to refresh both.\n\n"
        )
    lines = [
        "---",
        "type: palace-index",
        f"generated: {datetime.now(timezone.utc).isoformat()}",
        f"source_graph_generated: {stats['source_generated_at']}",
        f"graph_stale: {bool(stats.get('graph_stale'))}",
        "---",
        "",
        "# EOS Memory Palace",
        "",
        stale_banner,
        "A navigable map of the codebase organized as rooms you already know.",
        "Use this BEFORE scanning the file tree — it tells you where to stand.",
        "",
        f"**Loci promoted:** {stats['loci']}  ",
        f"**Rooms:** {stats['rooms']}  ",
        f"**Wings:** {stats['wings']}  ",
        f"**Source graph generated:** {stats['source_generated_at']}  ",
        f"**Graph age:** {stats.get('graph_age_hours', '?')} h  ",
        f"**Palace generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Usage",
        "",
        "1. Decide which **wing** your question belongs to.",
        "2. Drill into the **room** that owns the concern.",
        "3. Open loci inside the room — they are the highest-value files.",
        "4. Only escape to raw files if no locus answers your question.",
        "",
        "See [[../retrieval_rules|retrieval_rules.md]] for the enforced hierarchy.",
        "",
        "## Wings",
        "",
    ]
    for wing, rooms in rooms_by_wing.items():
        lines.append(f"### {wing}")
        lines.append("")
        for room in rooms:
            lines.append(f"- [[rooms/{room['id']}|{room['name']}]] — {room['purpose']}")
        lines.append("")
    lines += [
        "## Cloud Files",
        "",
        "- [[../cloud_palace|cloud_palace.md]] — palace usage rules",
        "- [[../codebase/cloud|codebase/cloud.md]] — codebase graph rules",
        "- [[../retrieval_rules|retrieval_rules.md]] — retrieval hierarchy",
        "",
    ]
    return "\n".join(lines)


def _graph_freshness(q: GraphQuery) -> tuple[bool, float]:
    """Return (stale, age_hours) for the source graph this build is reading."""
    ts_str = q.raw.get("generated_at") or ""
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        return True, float("inf")
    age = datetime.now(timezone.utc) - ts
    hours = round(age.total_seconds() / 3600, 2)
    return age > timedelta(hours=STALE_GRAPH_HOURS), hours


def _render_candidate_room(cluster: dict[str, Any]) -> str:
    """Render a Graphify-derived cluster as an UNCURATED candidate room.

    Candidate rooms live in 10_Wiki/palace/candidates/ and are explicitly
    *not* wired into the wing index — they surface for human review only.
    This preserves the curated palace as source of truth while letting
    overlay signal become visible when present.
    """
    lines: list[str] = [
        "---",
        "type: palace-candidate",
        f"cluster_id: {cluster.get('id', 'unknown')}",
        f"source: graphify",
        f"generated: {datetime.now(timezone.utc).date().isoformat()}",
        "---",
        "",
        f"# Candidate Cluster — {cluster.get('label', cluster.get('id'))}",
        "",
        "> **UNCURATED.** This cluster was auto-detected by Graphify overlay.",
        "> It is NOT part of the curated palace. Promote to a real room by",
        "> editing `scripts/build_palace.py` ROOM_DEFS if the grouping is useful.",
        "",
        f"**Size:** {cluster.get('size', len(cluster.get('members', [])))} files  ",
        f"**Seed label:** `{cluster.get('label', '?')}`",
        "",
        "## Members",
        "",
    ]
    for m in cluster.get("members", []):
        lines.append(f"- `{m}`")
    lines += [
        "",
        "## Traversal",
        "",
        "- Up to palace → [[../index|Memory Palace index]]",
        "- Curator notes → edit ROOM_DEFS in scripts/build_palace.py",
        "",
    ]
    return "\n".join(lines)


def _load_overlay_clusters() -> list[dict[str, Any]]:
    if not OVERLAY_JSON.exists():
        return []
    try:
        overlay = json.loads(OVERLAY_JSON.read_text())
    except json.JSONDecodeError:
        return []
    return [
        c
        for c in overlay.get("clusters", [])
        if c.get("size", len(c.get("members", []))) >= MIN_CANDIDATE_CLUSTER_SIZE
    ]


def build(verbose: bool = True, with_overlay: bool = False) -> dict[str, Any]:
    q = GraphQuery.load()
    PALACE_DIR.mkdir(parents=True, exist_ok=True)
    WINGS_DIR.mkdir(parents=True, exist_ok=True)
    ROOMS_DIR.mkdir(parents=True, exist_ok=True)

    graph_stale, graph_age_hours = _graph_freshness(q)

    palace_state: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_graph_generated_at": q.raw.get("generated_at"),
        "source_graph_stale": graph_stale,
        "source_graph_age_hours": graph_age_hours,
        "stale_threshold_hours": STALE_GRAPH_HOURS,
        "rooms": [],
    }

    rooms_by_wing: dict[str, list[dict[str, Any]]] = {}
    loci_total = 0

    for room in ROOM_DEFS:
        loci = select_loci(q, room)
        loci_total += len(loci)
        (ROOMS_DIR / f"{room['id']}.md").write_text(render_room(room, loci))
        palace_state["rooms"].append({**room, "loci": loci})
        rooms_by_wing.setdefault(room["wing"], []).append(room)

    for wing, rooms in rooms_by_wing.items():
        (WINGS_DIR / f"{wing}-wing.md").write_text(render_wing(wing, rooms))

    stats = {
        "loci": loci_total,
        "rooms": len(ROOM_DEFS),
        "wings": len(rooms_by_wing),
        "source_generated_at": q.raw.get("generated_at", "unknown"),
        "graph_stale": graph_stale,
        "graph_age_hours": graph_age_hours,
    }
    (PALACE_DIR / "index.md").write_text(render_index(rooms_by_wing, stats))

    # ── Optional overlay enrichment (candidate rooms, never injected) ────
    if with_overlay:
        CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
        clusters = _load_overlay_clusters()
        written = 0
        for cluster in clusters:
            path = CANDIDATES_DIR / f"{cluster.get('id', 'unknown')}.md"
            path.write_text(_render_candidate_room(cluster))
            written += 1
        palace_state["candidates"] = [
            {
                "id": c.get("id"),
                "label": c.get("label"),
                "size": c.get("size", len(c.get("members", []))),
                "path": f"10_Wiki/palace/candidates/{c.get('id')}.md",
            }
            for c in clusters
        ]
        stats["candidates"] = written
        if verbose:
            print(f"  overlay: {written} candidate rooms from graphify_overlay.json")
    else:
        palace_state["candidates"] = []

    PALACE_JSON.write_text(json.dumps(palace_state, indent=2))

    if verbose:
        print(f"palace built: {loci_total} loci across {len(ROOM_DEFS)} rooms")
        if graph_stale:
            print(
                f"  !! source graph is {graph_age_hours}h old — "
                f"run scripts/update-graph to refresh"
            )
        else:
            print(f"  source graph: {graph_age_hours}h old (fresh)")
        print(f"  index:  {PALACE_DIR / 'index.md'}")
        print(f"  wings:  {WINGS_DIR}")
        print(f"  rooms:  {ROOMS_DIR}")
        print(f"  state:  {PALACE_JSON}")
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build_palace")
    parser.add_argument("--stats", action="store_true", help="print stats only")
    parser.add_argument(
        "--with-overlay",
        action="store_true",
        help="also emit candidate rooms from data/graphify_overlay.json",
    )
    args = parser.parse_args(argv)
    if args.stats:
        if not PALACE_JSON.exists():
            print("palace not built yet")
            return 1
        print(json.dumps(json.loads(PALACE_JSON.read_text())["rooms"][0], indent=2))
        return 0
    build(with_overlay=args.with_overlay)
    return 0


if __name__ == "__main__":
    sys.exit(main())
