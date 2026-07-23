#!/usr/bin/env python3
"""Operator-language gate — Layer-2 vocabulary must not leak into Layer-1 surfaces.

docs/LEXICON.md defines the two-layer language standard: operators read
Layer-1 words (Goal, Objective, Plan, Task, Decision, ...); canonical internal
type names (WorkPacket, IntentSpec, ApprovalRequest, ...) are Layer 2 and must
never appear as operator-facing labels on TOUCHED surfaces.

Scope (deliberately narrow, §13 of the Wave 1 plan):
  - scans ONLY the string literals of the touched surface files listed in
    TOUCHED_SURFACES (committed UI strings — not user text, not model output,
    not logs, not payload data, not identifiers/testids/imports);
  - shrink-only baseline: violations may only decrease. The baseline lives at
    data/audits/operator_language_baseline.json and is updated ONLY via
    --update-baseline after a genuine reduction.

Exit codes: 0 = pass, 1 = new leakage (or self-test failure), 2 = usage error.

Usage:
  python3 scripts/check_operator_language.py            # gate (vs baseline)
  python3 scripts/check_operator_language.py --update-baseline
  python3 scripts/check_operator_language.py --self-test
"""

from __future__ import annotations

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_PATH = os.path.join(REPO_ROOT, "data", "audits", "operator_language_baseline.json")

# Touched operator surfaces (repo-RELATIVE paths — never absolute, so the gate
# behaves identically in worktrees; see feedback_gate_worktree_exclude_bug).
TOUCHED_SURFACES: tuple[str, ...] = (
    "cockpit/src/renderer/components/cards/PlanSummaryCard.tsx",
    "cockpit/src/renderer/panels/ObjectivePlanPanel.tsx",
    "cockpit/src/renderer/panels/WorkDetailPanel.tsx",
    "cockpit/src/renderer/panels/UniversalWorkPanel.tsx",
    "cockpit/src/renderer/components/ControlPanel.tsx",
)

# Layer-2 terms banned inside operator-facing string literals. Word-bounded;
# case as written (type names are case-sensitive, prose synonyms insensitive).
BANNED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("WorkPacket (Layer 2 — say Task)", re.compile(r"\bWork ?Packets?\b")),
    ("work packet (Layer 2 — say Task)", re.compile(r"\bwork packets?\b")),
    ("IntentSpec (Layer 2)", re.compile(r"\bIntentSpec\b")),
    ("IntentLoop (Layer 2)", re.compile(r"\bIntent ?Loop\b")),
    ("ApprovalRequest (Layer 2 — say Decision)", re.compile(r"\bApprovalRequest\b")),
    ("ObjectivePlanRecord (Layer 2 — say Plan)", re.compile(r"\bObjectivePlanRecord\b")),
    (
        "mutation spine (Layer 2)",
        re.compile(r"\b(?:governed[_ ]mutation|MutationRouter|ExecutionSpine)\b"),
    ),
    ("ticket/todo for Task", re.compile(r"\b(?:tickets?|todos?)\b", re.IGNORECASE)),
)

# String-literal extractor for TS/TSX: '...', "...", `...` (no nesting needed
# for label scanning) plus JSX text runs between > and <.
_STRING_RE = re.compile(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\]|\\.)*`")
_JSX_TEXT_RE = re.compile(r">([^<>]+)<")
# Attribute strings that are identifiers, not operator-visible labels.
_IDENTIFIER_ATTR_RE = re.compile(
    r"(?:data-testid|data-[a-z-]+|className|class|id|key|href|src|import|from|type|name)\s*[:=]\s*$"
)


_TEMPLATE_INTERP_RE = re.compile(r"\$\{[^}]*\}")
_JSX_INTERP_RE = re.compile(r"\{[^{}]*\}")


def _extract_label_strings(source: str) -> list[tuple[int, str]]:
    """Return (line, text) for operator-visible string content.

    Interpolations are replaced with a neutral placeholder INSIDE captured
    text (never on the raw source, where braces delimit code blocks) so a
    banned term adjacent to an interpolation is still caught.
    """
    results: list[tuple[int, str]] = []
    for m in _STRING_RE.finditer(source):
        prefix = source[max(0, m.start() - 40) : m.start()]
        if _IDENTIFIER_ATTR_RE.search(prefix):
            continue
        line = source.count("\n", 0, m.start()) + 1
        text = _TEMPLATE_INTERP_RE.sub(" _ ", m.group(0)[1:-1])
        results.append((line, text))
    for m in _JSX_TEXT_RE.finditer(source):
        text = _JSX_INTERP_RE.sub(" _ ", m.group(1)).strip()
        if text and text != "_":
            line = source.count("\n", 0, m.start()) + 1
            results.append((line, text))
    return results


def scan_file(rel_path: str) -> list[str]:
    """Return violation descriptions for one surface file."""
    abs_path = os.path.join(REPO_ROOT, rel_path)
    if not os.path.exists(abs_path):
        return []  # not-yet-created surfaces (e.g. WorkDetailPanel pre-C4) pass
    with open(abs_path, encoding="utf-8") as f:
        source = f.read()
    violations: list[str] = []
    for line, text in _extract_label_strings(source):
        for label, pattern in BANNED_PATTERNS:
            if pattern.search(text):
                violations.append(f"{rel_path}:{line}: {label}: {text[:80]!r}")
    return violations


def scan_all() -> dict[str, list[str]]:
    return {rel: scan_file(rel) for rel in TOUCHED_SURFACES}


def load_baseline() -> dict[str, int]:
    if not os.path.exists(BASELINE_PATH):
        return {}
    with open(BASELINE_PATH, encoding="utf-8") as f:
        return json.load(f).get("violations_per_file", {})


def write_baseline(results: dict[str, list[str]]) -> None:
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    payload = {
        "description": "Shrink-only operator-language baseline (docs/LEXICON.md). "
        "Counts may only decrease.",
        "violations_per_file": {rel: len(v) for rel, v in results.items()},
    }
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def run_gate() -> int:
    results = scan_all()
    baseline = load_baseline()
    failed = False
    for rel, violations in results.items():
        allowed = baseline.get(rel, 0)
        if len(violations) > allowed:
            failed = True
            print(f"FAIL {rel}: {len(violations)} Layer-2 label leak(s), baseline {allowed}")
            for v in violations:
                print(f"  {v}")
        elif len(violations) < allowed:
            print(
                f"SHRUNK {rel}: {len(violations)} < baseline {allowed} — "
                f"run --update-baseline to lock in"
            )
    if failed:
        print("\nOperator-language gate FAILED — see docs/LEXICON.md")
        return 1
    total = sum(len(v) for v in results.values())
    print(
        f"Operator-language gate OK ({total} baselined violation(s) across "
        f"{len(TOUCHED_SURFACES)} surfaces)"
    )
    return 0


def run_self_test() -> int:
    """Inject a violation into a synthetic source and prove the scanner sees it."""
    sample = (
        "export function X() {\n"
        "  const label = 'Approve this WorkPacket now'\n"
        '  return <div data-testid="work-packet-row">Review the work packet</div>\n'
        "}\n"
    )
    hits = []
    for line, text in _extract_label_strings(sample):
        for label, pattern in BANNED_PATTERNS:
            if pattern.search(text):
                hits.append((line, label))
    ok = (
        any("WorkPacket" in label for _, label in hits)
        and any("work packet" in label for _, label in hits)
        and all("work-packet-row" not in str(h) for h in hits)
    )
    print(f"self-test hits: {hits}")
    print("self-test:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return run_self_test()
    if "--update-baseline" in argv:
        results = scan_all()
        baseline = load_baseline()
        for rel, violations in results.items():
            if len(violations) > baseline.get(rel, 0) and baseline:
                print(
                    f"REFUSED: {rel} grew ({len(violations)} > {baseline.get(rel, 0)}); "
                    f"baseline may only shrink"
                )
                return 1
        write_baseline(results)
        print(f"baseline written: {BASELINE_PATH}")
        return 0
    if any(a.startswith("-") for a in argv):
        print(__doc__)
        return 2
    return run_gate()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
