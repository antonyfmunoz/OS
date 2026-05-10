#!/usr/bin/env python3
"""
query_skills.py — Tool Mastery Engine CLI registry.

Practical queries over the tool skill base. Uses the common loader,
the staleness logic, and the dependency graph JSON (if built).

Commands:
    search <substring>        find skills whose slug/title/description match
    show <slug>               print header + description + key metadata
    deps <slug>               what this skill references + is referenced by
    stale [--only stale|near_stale|missing_date]
                              list skills by freshness status
    unverified                list skills failing the verifier
    domain <substring>        search within description only (intent-style)
    list                      list all skill slugs
    count                     totals

Examples:
    python3 scripts/query_skills.py search ads
    python3 scripts/query_skills.py show notion
    python3 scripts/query_skills.py deps notion
    python3 scripts/query_skills.py stale --only near_stale
    python3 scripts/query_skills.py unverified
    python3 scripts/query_skills.py domain "database"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from scripts._tme_common import (  # noqa: E402
    SkillRecord,
    all_skill_slugs,
    load_all_skills,
    load_skill,
)
from scripts.check_skill_staleness import _assess  # noqa: E402

GRAPH_JSON = Path(_ROOT) / "docs" / "system" / "skill_graph.json"


def _matches(rec: SkillRecord, needle: str) -> bool:
    n = needle.lower()
    hay = (rec.slug + " " + rec.title + " " + rec.description).lower()
    return n in hay


def cmd_search(args: argparse.Namespace) -> int:
    skills = load_all_skills()
    hits = [r for r in skills if _matches(r, args.substring)]
    if not hits:
        print(f"No matches for {args.substring!r}")
        return 1
    for r in hits:
        desc = r.description.replace("\n", " ").strip()[:100]
        print(f"  {r.slug:28s} — {desc}")
    print(f"--- {len(hits)} match(es)")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    rec = load_skill(args.slug)
    if not rec.exists:
        print(f"No such skill: {args.slug}", file=sys.stderr)
        return 2
    print(f"slug:            {rec.slug}")
    print(f"title:           {rec.title}")
    print(f"description:     {rec.description[:300]}")
    print(f"last_researched: {rec.frontmatter.get('last_researched', '—')}")
    print(f"speed_category:  {rec.speed_category}")
    print(f"api_version:     {rec.api_version or '—'}")
    print(f"sdk_version:     {rec.sdk_version or '—'}")
    print(f"source_url:      {rec.frontmatter.get('source_url', '—')}")
    print(f"path:            {rec.path}")
    if rec.parse_error:
        print(f"parse_error:     {rec.parse_error}")
    return 0


def _load_graph() -> dict | None:
    if not GRAPH_JSON.is_file():
        return None
    try:
        return json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    except Exception:
        return None


def cmd_deps(args: argparse.Namespace) -> int:
    graph = _load_graph()
    if graph is None:
        print(
            "Graph not built yet — run: python3 scripts/build_skill_graph.py",
            file=sys.stderr,
        )
        return 2
    slug = args.slug
    if slug not in graph["nodes"]:
        print(f"No such skill in graph: {slug}", file=sys.stderr)
        return 2
    out = graph["edges"].get(slug, [])
    inc = graph["reverse_edges"].get(slug, [])
    print(f"# {slug}")
    print(f"references ({len(out)}):   " + (", ".join(out) or "—"))
    print(f"referenced by ({len(inc)}): " + (", ".join(inc) or "—"))
    print(f"centrality: {graph['centrality'].get(slug, 0)}")
    return 0


def cmd_stale(args: argparse.Namespace) -> int:
    today = date.today()
    rows = [_assess(load_skill(s), today) for s in all_skill_slugs()]
    if args.only:
        rows = [r for r in rows if r.status == args.only]
    else:
        rows = [r for r in rows if r.status in ("stale", "near_stale", "missing_date")]
    if not rows:
        print("Nothing to report — all skills fresh.")
        return 0
    for r in sorted(rows, key=lambda x: (x.status, x.slug)):
        age = f"{r.age_days}d" if r.age_days is not None else "—"
        print(
            f"[{r.status:12s}] {r.slug:28s} speed={r.speed:7s} "
            f"age={age:5s} researched={r.last_researched or '—'}"
        )
    print(f"--- {len(rows)} row(s)")
    return 0


def cmd_unverified(_: argparse.Namespace) -> int:
    # Delegate to verify_tool_skill.py --all --json for consistency
    res = subprocess.run(
        [
            sys.executable,
            f"{_ROOT}/scripts/verify_tool_skill.py",
            "--all",
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    try:
        payload = json.loads(res.stdout)
    except json.JSONDecodeError:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        return 2
    failed = [r for r in payload["results"] if not r["passed"]]
    if not failed:
        print("All skills pass verification.")
        return 0
    for r in failed:
        print(f"[FAIL] {r['slug']}")
        for f in r["failures"][:5]:
            print(f"   - {f}")
        if len(r["failures"]) > 5:
            print(f"   - ... +{len(r['failures']) - 5} more")
    print(f"--- {len(failed)} failing skill(s) of {payload['total']}")
    return 1


def cmd_domain(args: argparse.Namespace) -> int:
    n = args.substring.lower()
    skills = load_all_skills()
    hits = [r for r in skills if n in r.description.lower()]
    if not hits:
        print(f"No description matches for {args.substring!r}")
        return 1
    for r in hits:
        print(f"  {r.slug:28s} — {r.description[:100]}")
    print(f"--- {len(hits)} match(es)")
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    for s in all_skill_slugs():
        print(s)
    return 0


def cmd_count(_: argparse.Namespace) -> int:
    slugs = all_skill_slugs()
    print(f"total skills: {len(slugs)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("search"); p.add_argument("substring"); p.set_defaults(fn=cmd_search)
    p = sub.add_parser("show"); p.add_argument("slug"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("deps"); p.add_argument("slug"); p.set_defaults(fn=cmd_deps)
    p = sub.add_parser("stale"); p.add_argument("--only", choices=["fresh", "near_stale", "stale", "missing_date"]); p.set_defaults(fn=cmd_stale)
    p = sub.add_parser("unverified"); p.set_defaults(fn=cmd_unverified)
    p = sub.add_parser("domain"); p.add_argument("substring"); p.set_defaults(fn=cmd_domain)
    p = sub.add_parser("list"); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("count"); p.set_defaults(fn=cmd_count)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
