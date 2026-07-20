#!/usr/bin/env python3
"""Gate 15 — Runtime-State Boundary (Wave 0).

Enforces the runtime/source separation established by the MVP campaign's
Wave 0 packet:

1. TRACKED-PATH CHECK (primary, over `git ls-files` — never raw filesystem
   presence): no tracked file may live under `data/runtime/` or under any
   RETIRED legacy runtime-state path (the subsystems migrated to
   substrate/state/runtime_paths.py).
2. LITERAL CHECK: no NEW source literal may point at a migrated legacy path.
   Remaining references are frozen in the shrink-only LEGACY_STATE_PATH_REFS
   ledger — it may only shrink, never grow, and it must not hide a
   reader/writer of a migrated path (the frozen files are legacy verification
   scripts, not live services).

Scope: Python, shell, TS/TSX, YAML and compose files across substrate/,
adapters/, transports/, services/, scripts/, nodes/, projections/, saas/,
cockpit/src/ — not only substrate/. Markdown and comment-only lines are
skipped (documentation examples are not runtime writers). Worktrees are
excluded by REPOSITORY-RELATIVE path (the absolute-parts bug class from the
gate-worktree-exclude incident).

Self-test: `--self-test` builds a synthetic tree containing one violation of
each class and asserts the gate catches them.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess  # scripts/ is CPU-gate exempt
import sys
import tempfile
from pathlib import Path


def _default_repo() -> Path:
    """The repository the commit is happening in (worktree-aware), not the
    UMH_ROOT deployment checkout — pre-commit must gate the tree being
    committed."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout.strip()
        if out:
            return Path(out)
    except Exception:
        pass
    return Path(os.environ.get("UMH_ROOT", "/opt/OS"))


REPO = _default_repo()

# Tracked files must never appear under these prefixes (dir-level retirements).
RETIRED_TRACKED_PREFIXES = (
    "data/runtime/",
    "data/umh/organism/",
    "data/umh/c35/",
    "data/umh/qualification/",
    "data/umh/fleet/",
    "data/umh/execution_coordinator/",
    "data/umh/reality_model/",
    "data/umh/work_portfolio/",
    "data/umh/operator/intent_loop/",
    "data/umh/workcell_daemon/",
)

# File-level retirements inside dirs that still hold static tracked evidence.
RETIRED_TRACKED_REGEXES = (
    re.compile(r"^data/umh/projections/registrations\.jsonl$"),
    re.compile(r"^data/umh/universal_work/[^/]+\.jsonl$"),
    re.compile(r"^data/umh/operator_experience/[^/]+\.jsonl$"),
)

# Source literals that may no longer be introduced (migrated legacy homes).
# Both path-literal styles are matched: "data/umh/organism" and
# `"data", "umh", "organism"` join-style.
_LITERAL_SUBSYSTEMS = (
    "organism",
    "c35",
    "qualification",
    "fleet",
    "execution_coordinator",
    "reality_model",
    "work_portfolio",
    "workcell_daemon",
)
LITERAL_PATTERNS = [
    re.compile(r"data/umh/(?:%s)\b" % "|".join(_LITERAL_SUBSYSTEMS)),
    re.compile(r'"data",\s*"umh",\s*"(?:%s)"' % "|".join(_LITERAL_SUBSYSTEMS)),
    # pathlib `/`-operator style: ... / "data" / "umh" / "organism"
    re.compile(r'"data"\s*/\s*"umh"\s*/\s*"(?:%s)"' % "|".join(_LITERAL_SUBSYSTEMS)),
    re.compile(r"data/umh/operator/intent_loop"),
    re.compile(r'"data"\s*/\s*"umh"\s*/\s*"operator"\s*/\s*"intent_loop"'),
    re.compile(r"data/umh/projections/registrations\.jsonl"),
    re.compile(
        r"data/umh/universal_work/(?:work_packets|workcells|role_contracts|knowledge_models)\.jsonl"
    ),
    re.compile(
        r'"data",\s*"umh",\s*"universal_work",\s*"(?:work_packets|workcells|role_contracts|knowledge_models)\.jsonl"'
    ),
    re.compile(
        r'"data"\s*/\s*"umh"\s*/\s*"universal_work"\s*/\s*"(?:work_packets|workcells|role_contracts|knowledge_models)\.jsonl"'
    ),
    re.compile(r"data/umh/operator_experience/\w+\.jsonl"),
    re.compile(r'"data"\s*/\s*"umh"\s*/\s*"operator_experience"'),
    re.compile(r'"data",\s*"umh",\s*"operator_experience"'),
]

SCAN_ROOTS = (
    "substrate",
    "adapters",
    "transports",
    "services",
    "scripts",
    "nodes",
    "projections",
    "saas",
    "cockpit/src",
    "docker-compose.yml",
)
SCAN_SUFFIXES = {".py", ".sh", ".ts", ".tsx", ".yml", ".yaml"}

# Files that legitimately encode legacy paths (the migration/gate machinery
# itself) — they DESCRIBE the old homes, they do not read or write them at
# runtime.
MACHINERY_ALLOWLIST = {
    "scripts/migrate_runtime_state.py",
    "scripts/check_runtime_state_boundary.py",
}

# ── SHRINK-ONLY LEDGER ──────────────────────────────────────────────────────
# Remaining legacy references. Every entry is a retired-era verification
# script (episodic, PR47/campaign vintage) — none is a live service writer;
# the live writers all migrated in the Wave 0 commit. Entries may be REMOVED
# when the file migrates or retires; adding an entry is forbidden.
LEGACY_STATE_PATH_REFS = {
    "scripts/verify_pr47_production.py",
    "scripts/verify_pr47_reliability.py",
    "scripts/verify_pr47_cadence_learning.py",
}


def _tracked_files(repo: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files"],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    ).stdout
    return out.splitlines()


def check_tracked(repo: Path) -> list[str]:
    violations = []
    for rel in _tracked_files(repo):
        if rel.startswith(".claude/worktrees/"):
            continue
        if rel.startswith(RETIRED_TRACKED_PREFIXES):
            violations.append(f"TRACKED under retired runtime path: {rel}")
            continue
        for rx in RETIRED_TRACKED_REGEXES:
            if rx.match(rel):
                violations.append(f"TRACKED under retired runtime path: {rel}")
                break
    return violations


def _iter_scan_files(repo: Path):
    for root in SCAN_ROOTS:
        base = repo / root
        if base.is_file():
            yield base
            continue
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            rel = path.relative_to(repo).as_posix()
            # worktree exclusion by RELATIVE path (never absolute parts)
            if rel.startswith(".claude/worktrees/"):
                continue
            if "/node_modules/" in rel or "/__pycache__/" in rel:
                continue
            yield path


def check_literals(repo: Path) -> list[str]:
    violations = []
    for path in _iter_scan_files(repo):
        rel = path.relative_to(repo).as_posix()
        if rel in MACHINERY_ALLOWLIST or rel in LEGACY_STATE_PATH_REFS:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            # comment-only lines are documentation, not writers
            if stripped.startswith(("#", "//", "*", "--")):
                continue
            for rx in LITERAL_PATTERNS:
                if rx.search(line):
                    violations.append(
                        f"NEW legacy runtime-path literal: {rel}:{lineno}: {stripped[:100]}"
                    )
                    break
    return violations


def check_ledger(repo: Path) -> list[str]:
    """Every ledger entry must still exist (else it must be removed — shrink)."""
    problems = []
    for rel in sorted(LEGACY_STATE_PATH_REFS):
        if not (repo / rel).exists():
            problems.append(
                f"LEDGER STALE: {rel} no longer exists — remove it from LEGACY_STATE_PATH_REFS"
            )
    return problems


def self_test() -> int:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "substrate").mkdir(parents=True)
        # violation class 2: a fresh literal in a scanned source file
        (root / "substrate" / "bad.py").write_text('STORE = "data/umh/organism/events.jsonl"\n')
        # violation class 2b: pathlib `/`-operator style (the C2 blind spot)
        (root / "substrate" / "bad_pathlib.py").write_text(
            'P = ROOT / "data" / "umh" / "organism" / "events.jsonl"\n'
        )
        # violation class 2c: os.path.join comma style
        (root / "substrate" / "bad_join.py").write_text(
            'P = os.path.join(R, "data", "umh", "c35")\n'
        )
        # negative: comment-only line must not flag
        (root / "substrate" / "ok.py").write_text(
            "# example: data/umh/organism/events.jsonl (historical home)\n"
        )
        # negative: worktree copy must be excluded by relative path
        wt = root / ".claude" / "worktrees" / "x" / "substrate"
        wt.mkdir(parents=True)
        (wt / "bad.py").write_text('STORE = "data/umh/organism/events.jsonl"\n')

        lits = check_literals(root)
        assert any("substrate/bad.py" in v for v in lits), "self-test: literal violation missed"
        assert any("bad_pathlib.py" in v for v in lits), "self-test: pathlib style missed"
        assert any("bad_join.py" in v for v in lits), "self-test: join style missed"
        assert not any("ok.py" in v for v in lits), "self-test: comment line falsely flagged"
        assert not any("worktrees" in v for v in lits), "self-test: worktree not excluded"

        # violation class 1: tracked file under a retired path
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True, timeout=60)
        (root / "data" / "runtime" / "umh").mkdir(parents=True)
        (root / "data" / "runtime" / "umh" / "events.jsonl").write_text("{}\n")
        subprocess.run(
            ["git", "-C", str(root), "add", "-f", "data/runtime/umh/events.jsonl"],
            check=True,
            timeout=60,
        )
        tracked = check_tracked(root)
        assert any("data/runtime/umh/events.jsonl" in v for v in tracked), (
            "self-test: tracked violation missed"
        )
    print("[gate15] self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--repo", default=str(REPO))
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    repo = Path(args.repo).resolve()
    violations = check_tracked(repo) + check_literals(repo) + check_ledger(repo)
    if violations:
        print(f"[gate15] Runtime-State Boundary: {len(violations)} violation(s)")
        for v in violations:
            print(f"  {v}")
        return 1
    print("[gate15] Runtime-State Boundary: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
