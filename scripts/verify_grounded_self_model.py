#!/usr/bin/env python3
"""Grounded Self-Model verifier / builder CLI (DOMAIN_RECONSTRUCTION_SPEC §16).

Builds and/or verifies a run-scoped grounded self-model of the UMH codebase. It
calls builder/evaluation functions only — it spawns no heavy work itself (the
inventory/probe seams own any gated process access, and scripts/ is CPU-gate
exempt).

Prints: run id; repo commit; evidence counts by facet; claim counts by status;
unknown count; competency disposition; integrity results; acceptance vector;
final status.

Gate/test outcomes are recorded ONLY through --record-gates / --record-tests
(the supported record_run_outcomes mechanism) — never by editing run artifacts
by hand.

Exit codes:
  0  — built/verified; a PARTIAL / INSUFFICIENT_EVIDENCE outcome is exit 0
       (missing runtime evidence is reported, not an error).
  1  — critical integrity/safety failure (final status FAILED).
  2  — setup error (no run to verify, bad paths).

Usage:
    UMH_ROOT=/opt/OS python3 scripts/verify_grounded_self_model.py --build
    python3 scripts/verify_grounded_self_model.py --verify
    python3 scripts/verify_grounded_self_model.py --record-gates true --record-tests true
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

from substrate.understanding.reconstruction.contracts import (  # noqa: E402
    DECLARATION_FACETS,
    RUNTIME_FACETS,
)
from substrate.understanding.reconstruction.evaluation import (  # noqa: E402
    CRITICAL_CRITERIA,
    acceptance_vector,
    final_status,
    load_run,
)


def _default_repo_root() -> Path:
    return Path(os.environ.get("UMH_ROOT", "/opt/OS"))


def _default_output(repo_root: Path) -> Path:
    return repo_root / "data" / "world_models" / "self"


def _resolve_run_dir(output: Path, run_id: str | None) -> Path | None:
    if run_id:
        cand = output / "runs" / run_id
        return cand if cand.is_dir() else None
    latest = output / "latest.json"
    if latest.is_file():
        info = json.loads(latest.read_text(encoding="utf-8"))
        rd = Path(info.get("run_dir", ""))
        if rd.is_dir():
            return rd
    return None


def _parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in ("true", "1", "yes", "pass"):
        return True
    if lowered in ("false", "0", "no", "fail"):
        return False
    raise argparse.ArgumentTypeError(f"expected true/false, got {value!r}")


def _print_facet_counts(observations: list[dict]) -> None:
    counts: dict[str, int] = {}
    kindless = 0
    for o in observations:
        facet = o.get("maturity_facet")
        if facet:
            counts[facet] = counts.get(facet, 0) + 1
        else:
            kindless += 1
    print("  evidence counts by maturity facet:")
    for f in sorted(counts):
        tag = ""
        if f in DECLARATION_FACETS:
            tag = " (declaration)"
        elif f in RUNTIME_FACETS:
            tag = " (runtime)"
        print(f"    {f:<26}{counts[f]:>6}{tag}")
    if kindless:
        print(f"    (no-facet observations: {kindless} — probe/repository-state kinds)")
    if not any(o.get("maturity_facet") in RUNTIME_FACETS for o in observations):
        print("    (no runtime-facet observations — runtime coverage is thin)")


def _print_claim_statuses(claims: list[dict]) -> None:
    counts: dict[str, int] = {}
    for c in claims:
        counts[c.get("status", "?")] = counts.get(c.get("status", "?"), 0) + 1
    print("  claim counts by status:")
    for s in sorted(counts):
        print(f"    {s:<14}{counts[s]:>6}")


def _print_competency(model: dict) -> None:
    qs = model.get("competency_questions", [])
    unknown = sum(1 for q in qs if q.get("answer_status") == "UNKNOWN")
    print(f"  competency questions: {len(qs)} total, {unknown} unknown")
    for q in qs:
        mark = "?" if q.get("answer_status") == "UNKNOWN" else "="
        summary = q.get("summary", {})
        detail = (
            q.get("unknown_reason", "")[:70]
            if q.get("answer_status") == "UNKNOWN"
            else json.dumps(summary, sort_keys=True)[:70]
        )
        print(f"    [{mark}] {q.get('question_id')}: {detail}")


def _print_acceptance(vector: dict) -> None:
    print("  acceptance vector:")
    for k in sorted(vector.get("criteria", {})):
        v = vector["criteria"][k]
        crit = " *critical*" if k in CRITICAL_CRITERIA else ""
        print(f"    {k:<34}{v}{crit}")
    print(
        f"    -> passes {vector.get('passes')}/{vector.get('denominator')} "
        f"scored criteria (N/A: {len(vector.get('not_applicable', []))})"
    )


def _do_build(repo_root: Path, output: Path, run_id: str) -> Path:
    from substrate.understanding.reconstruction.builder import build_self_model

    now = datetime.now(timezone.utc).isoformat()
    result = build_self_model(repo_root=repo_root, output_root=output, run_id=run_id, now=now)
    return Path(result.run_dir)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build", action="store_true", help="build a new run")
    ap.add_argument("--verify", action="store_true", help="verify a run")
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="self-model root (default <repo>/data/world_models/self)",
    )
    ap.add_argument("--repo-root", type=Path, default=None, help="repo root")
    ap.add_argument("--run-id", type=str, default=None, help="run id to verify/build")
    ap.add_argument(
        "--record-gates",
        type=_parse_bool,
        default=None,
        metavar="true|false",
        help="record the gate outcome in the run manifest (supported mechanism)",
    )
    ap.add_argument(
        "--record-tests",
        type=_parse_bool,
        default=None,
        metavar="true|false",
        help="record the targeted-test outcome in the run manifest",
    )
    args = ap.parse_args()

    repo_root = args.repo_root or _default_repo_root()
    output = args.output or _default_output(repo_root)

    if not args.build and not args.verify:
        args.verify = True  # default action

    run_dir: Path | None = None
    if args.build:
        run_id = args.run_id or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
        print(f"[build] repo_root={repo_root} output={output} run_id={run_id}")
        try:
            run_dir = _do_build(repo_root, output, run_id)
        except Exception as exc:  # setup / environment failure
            print(f"  setup error: {exc}")
            return 2
        print(f"  built run at {run_dir}")

    if run_dir is None:
        run_dir = _resolve_run_dir(output, args.run_id)
    if run_dir is None or not run_dir.is_dir():
        print(f"no run to verify under {output} (build first with --build)")
        return 2

    if args.record_gates is not None or args.record_tests is not None:
        from substrate.understanding.reconstruction.builder import record_run_outcomes

        record_run_outcomes(
            run_dir,
            gates_clean=args.record_gates,
            targeted_tests_passed=args.record_tests,
        )
        print(
            f"  recorded outcomes: gates_clean={args.record_gates} "
            f"targeted_tests_passed={args.record_tests}"
        )

    run = load_run(run_dir)
    manifest = run["manifest"]
    print("\n[verify] Grounded Self-Model")
    print(f"  run id:       {manifest.get('run_id', run_dir.name)}")
    print(
        f"  repo commit:  {manifest.get('repository_commit') or 'unknown'} "
        f"({manifest.get('repository_commit_status', '?')})"
    )
    print(f"  code version: {manifest.get('code_version', '?')}")
    print()
    _print_facet_counts(run["observations"])
    print()
    _print_claim_statuses(run["claims"])
    unknown = sum(
        1
        for q in run["model"].get("competency_questions", [])
        if q.get("answer_status") == "UNKNOWN"
    )
    print(f"\n  unknown competency answers: {unknown}")
    _print_competency(run["model"])
    print()

    vector = acceptance_vector(run_dir)
    status = final_status(vector)
    no_design = vector["detail"]["no_design_as_implementation"]
    citations = vector["detail"]["convergence_citations"]
    print("  integrity results:")
    print(
        f"    no_design_as_implementation: "
        f"{'PASS' if no_design['passed'] else 'FAIL'} "
        f"(violations: {no_design['violations']})"
    )
    print(f"    convergence citations: {citations['resolved']}/{citations['cited']} resolved")
    print(f"    structural: {'PASS' if vector['detail']['structural']['passed'] else 'FAIL'}")
    print(f"    temporal:   {'PASS' if vector['detail']['temporal']['passed'] else 'FAIL'}")
    hashes = vector["detail"]["artifact_hashes"]
    print(
        f"    artifact hashes: "
        f"{'PASS' if hashes.get('passed') else ('not-verifiable' if not hashes.get('verifiable') else 'FAIL')}"
        f" ({hashes.get('checked', 0)} checked)"
    )
    print()
    _print_acceptance(vector)
    print()
    print(f"  FINAL STATUS: {status}")

    return 1 if status == "FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())
