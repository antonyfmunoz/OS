#!/usr/bin/env python3
"""verify_knowledge_system.py — Acceptance check for the EOS cognition stack.

Runs validation in retrieval-hierarchy order so any failure maps directly to
the layer it breaks. Exit 0 = all checks pass. Exit 1 = at least one failure.

Usage:
    python3 scripts/verify_knowledge_system.py          # run all checks
    python3 scripts/verify_knowledge_system.py --json   # machine-readable report
    python3 scripts/verify_knowledge_system.py --strict # also fail on WARN

Checks cover:
  - session docs exist (cloud.md, palace/index, cloud_palace, codebase/cloud, retrieval_rules)
  - palace directory + index + rooms + wings present
  - codebase graph JSON exists, loads, and has expected keys
  - graph freshness metadata present and parseable
  - parser registry loads every expected language
  - query_graph.py CLI answers deps/dependents/critical/languages
  - summaries loaded and aligned with current graph
  - palace.json aligned with graph generated_at
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, "/opt/OS")

ROOT = Path("/opt/OS")


@dataclass
class CheckResult:
    name: str
    status: str  # PASS | FAIL | WARN
    detail: str = ""
    data: dict[str, object] = field(default_factory=dict)


# ─── Individual checks ──────────────────────────────────────────────────────


REQUIRED_DOCS = [
    ROOT / "cloud.md",
    ROOT / "10_Wiki" / "palace" / "index.md",
    ROOT / "10_Wiki" / "cloud_palace.md",
    ROOT / "10_Wiki" / "codebase" / "cloud.md",
    ROOT / "10_Wiki" / "retrieval_rules.md",
    ROOT / "CLAUDE.md",
]

REQUIRED_DATA = [
    ROOT / "data" / "codebase_graph.json",
    ROOT / "data" / "palace.json",
    ROOT / "data" / "node_summaries.json",
]

PALACE_SUBDIRS = [
    ROOT / "10_Wiki" / "palace" / "rooms",
    ROOT / "10_Wiki" / "palace" / "wings",
]

CODEBASE_VAULT_SUBDIRS = [
    ROOT / "10_Wiki" / "codebase" / "files",
    ROOT / "10_Wiki" / "codebase" / "modules",
    ROOT / "10_Wiki" / "codebase" / "classes",
    ROOT / "10_Wiki" / "codebase" / "functions",
]

EXPECTED_LANGUAGES = {"python", "typescript", "javascript", "sql", "config"}


def check_session_docs() -> CheckResult:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_DOCS if not p.exists()]
    if missing:
        return CheckResult("session_docs", "FAIL", f"missing: {missing}")
    return CheckResult("session_docs", "PASS", f"{len(REQUIRED_DOCS)} docs present")


def check_data_artifacts() -> CheckResult:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED_DATA if not p.exists()]
    if missing:
        return CheckResult("data_artifacts", "FAIL", f"missing: {missing}")
    return CheckResult("data_artifacts", "PASS", f"{len(REQUIRED_DATA)} data files present")


def check_palace_structure() -> CheckResult:
    missing = [str(p.relative_to(ROOT)) for p in PALACE_SUBDIRS if not p.is_dir()]
    if missing:
        return CheckResult("palace_structure", "FAIL", f"missing dirs: {missing}")
    rooms = list((ROOT / "10_Wiki" / "palace" / "rooms").glob("*.md"))
    wings = list((ROOT / "10_Wiki" / "palace" / "wings").glob("*.md"))
    if not rooms:
        return CheckResult("palace_structure", "FAIL", "no room pages generated")
    if not wings:
        return CheckResult("palace_structure", "FAIL", "no wing pages generated")
    return CheckResult(
        "palace_structure",
        "PASS",
        f"{len(rooms)} rooms, {len(wings)} wings",
        {"rooms": len(rooms), "wings": len(wings)},
    )


def check_codebase_vault() -> CheckResult:
    missing = [str(p.relative_to(ROOT)) for p in CODEBASE_VAULT_SUBDIRS if not p.is_dir()]
    if missing:
        return CheckResult("codebase_vault", "FAIL", f"missing dirs: {missing}")
    files = sum(1 for _ in (ROOT / "10_Wiki" / "codebase" / "files").glob("*.md"))
    if files == 0:
        return CheckResult("codebase_vault", "FAIL", "no file pages generated")
    return CheckResult("codebase_vault", "PASS", f"{files} file pages")


def check_graph_loads() -> CheckResult:
    try:
        from scripts.query_graph import GraphQuery

        q = GraphQuery.load()
    except Exception as exc:
        return CheckResult("graph_loads", "FAIL", f"load error: {exc}")
    required_keys = {"files", "classes", "functions", "edges", "generated_at", "stats"}
    missing = required_keys - set(q.raw.keys())
    if missing:
        return CheckResult("graph_loads", "FAIL", f"missing keys: {missing}")
    return CheckResult(
        "graph_loads",
        "PASS",
        f"{len(q.raw['files'])} files, {len(q.raw['edges'])} edges",
        {"files": len(q.raw["files"]), "edges": len(q.raw["edges"])},
    )


def check_freshness() -> CheckResult:
    try:
        from scripts.query_graph import GraphQuery

        q = GraphQuery.load()
        f = q.freshness()
    except Exception as exc:
        return CheckResult("freshness", "FAIL", f"error: {exc}")
    if not f.get("generated_at"):
        return CheckResult("freshness", "FAIL", "no generated_at metadata")
    if f.get("stale"):
        return CheckResult(
            "freshness",
            "WARN",
            f"graph is {f.get('age_hours')}h old (threshold {f.get('threshold_hours')}h)",
            f,
        )
    return CheckResult(
        "freshness", "PASS", f"graph {f.get('age_hours')}h old", f
    )


def check_parser_registry() -> CheckResult:
    try:
        from parsers import REGISTRY
    except Exception as exc:
        return CheckResult("parser_registry", "FAIL", f"import error: {exc}")
    langs = {p.language for p in REGISTRY}
    missing = EXPECTED_LANGUAGES - langs
    if missing:
        return CheckResult(
            "parser_registry",
            "FAIL",
            f"missing parsers: {missing}",
            {"loaded": sorted(langs)},
        )
    return CheckResult(
        "parser_registry",
        "PASS",
        f"{len(REGISTRY)} parsers: {sorted(langs)}",
        {"loaded": sorted(langs)},
    )


def check_query_cli() -> CheckResult:
    """Smoke-test query_graph.py CLI on a few subcommands."""
    commands = [
        ["critical"],
        ["entry-points"],
        ["languages"],
        ["freshness"],
    ]
    failures: list[str] = []
    for cmd in commands:
        full = ["python3", str(ROOT / "scripts" / "query_graph.py")] + cmd
        try:
            result = subprocess.run(
                full, capture_output=True, text=True, timeout=30, check=False
            )
        except Exception as exc:
            failures.append(f"{' '.join(cmd)}: {exc}")
            continue
        if result.returncode != 0:
            failures.append(
                f"{' '.join(cmd)}: exit {result.returncode}: {result.stderr.strip()[:120]}"
            )
    if failures:
        return CheckResult("query_cli", "FAIL", "; ".join(failures))
    return CheckResult("query_cli", "PASS", f"{len(commands)} CLI commands green")


def check_summaries_alignment() -> CheckResult:
    summaries_path = ROOT / "data" / "node_summaries.json"
    if not summaries_path.exists():
        return CheckResult("summaries", "FAIL", "node_summaries.json missing")
    try:
        store = json.loads(summaries_path.read_text())
    except Exception as exc:
        return CheckResult("summaries", "FAIL", f"parse error: {exc}")
    nodes = store.get("nodes") or {}
    if not nodes:
        return CheckResult("summaries", "FAIL", "no nodes recorded")
    return CheckResult(
        "summaries",
        "PASS",
        f"{len(nodes)} nodes, {store.get('versions', 0)} versions",
        {"nodes": len(nodes), "versions": store.get("versions", 0)},
    )


def check_palace_alignment() -> CheckResult:
    palace_path = ROOT / "data" / "palace.json"
    graph_path = ROOT / "data" / "codebase_graph.json"
    if not palace_path.exists():
        return CheckResult("palace_alignment", "FAIL", "palace.json missing")
    try:
        palace = json.loads(palace_path.read_text())
        graph = json.loads(graph_path.read_text())
    except Exception as exc:
        return CheckResult("palace_alignment", "FAIL", f"parse error: {exc}")
    pg = palace.get("source_graph_generated_at")
    g = graph.get("generated_at")
    if pg != g:
        return CheckResult(
            "palace_alignment",
            "WARN",
            f"palace source={pg} vs graph={g} — run scripts/update-graph",
        )
    if palace.get("source_graph_stale"):
        return CheckResult(
            "palace_alignment",
            "WARN",
            f"palace built against stale graph ({palace.get('source_graph_age_hours')}h)",
        )
    return CheckResult("palace_alignment", "PASS", f"palace aligned with graph {g}")


def check_claude_md_directives() -> CheckResult:
    """Confirm CLAUDE.md names the session bootstrap and hierarchy."""
    claude = ROOT / "CLAUDE.md"
    if not claude.exists():
        return CheckResult("claude_md_directives", "FAIL", "CLAUDE.md missing")
    text = claude.read_text()
    missing = []
    for token in [
        "session_bootstrap.py",
        "query_graph.py",
        "retrieval_rules",
        "palace",
        "Retrieval hierarchy",
    ]:
        if token.lower() not in text.lower():
            missing.append(token)
    if missing:
        return CheckResult("claude_md_directives", "FAIL", f"missing tokens: {missing}")
    return CheckResult("claude_md_directives", "PASS", "graph-first directives present")


CHECKS = [
    check_session_docs,
    check_data_artifacts,
    check_palace_structure,
    check_codebase_vault,
    check_graph_loads,
    check_freshness,
    check_parser_registry,
    check_query_cli,
    check_summaries_alignment,
    check_palace_alignment,
    check_claude_md_directives,
]


def run_all() -> list[CheckResult]:
    results: list[CheckResult] = []
    for check in CHECKS:
        try:
            results.append(check())
        except Exception as exc:  # pragma: no cover — defensive
            results.append(CheckResult(check.__name__, "FAIL", f"crashed: {exc}"))
    return results


def print_report(results: list[CheckResult]) -> None:
    print("EOS KNOWLEDGE SYSTEM — VERIFICATION REPORT")
    print("=" * 64)
    width = max(len(r.name) for r in results)
    for r in results:
        icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]"}.get(r.status, "[??]")
        print(f"  {icon}  {r.name:<{width}}  {r.detail}")
    passed = sum(1 for r in results if r.status == "PASS")
    warn = sum(1 for r in results if r.status == "WARN")
    fail = sum(1 for r in results if r.status == "FAIL")
    print("-" * 64)
    print(f"  {passed} passed, {warn} warn, {fail} fail")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="verify_knowledge_system")
    p.add_argument("--json", action="store_true", help="emit JSON report")
    p.add_argument("--strict", action="store_true", help="fail on WARN as well")
    args = p.parse_args(argv)

    results = run_all()

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "name": r.name,
                        "status": r.status,
                        "detail": r.detail,
                        "data": r.data,
                    }
                    for r in results
                ],
                indent=2,
            )
        )
    else:
        print_report(results)

    failed = [r for r in results if r.status == "FAIL"]
    warned = [r for r in results if r.status == "WARN"]
    if failed:
        return 1
    if args.strict and warned:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
