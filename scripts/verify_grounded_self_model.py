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

Test evidence (v1.2): --run-tests <template-id> executes the bounded pytest
selection with the evidence plugin (repository state INJECTED via env — the
plugin never shells out to git), qualifies the artifact (missing report /
plugin_error / schema / session-field failures are acquisition failures even
when the tests themselves passed), then builds a run ingesting it.
--test-artifact ingests a pre-produced artifact instead. scripts/ is CPU-gate
exempt (precedent: check_pytest_collection.py).

Usage:
    UMH_ROOT=/opt/OS python3 scripts/verify_grounded_self_model.py --build
    python3 scripts/verify_grounded_self_model.py --run-tests reconstruction-spine-v1
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
    critical = set(vector.get("critical_criteria") or CRITICAL_CRITERIA)
    print("  acceptance vector:")
    for k in sorted(vector.get("criteria", {})):
        v = vector["criteria"][k]
        crit = " *critical*" if k in critical else ""
        print(f"    {k:<34}{v}{crit}")
    print(
        f"    -> passes {vector.get('passes')}/{vector.get('denominator')} "
        f"scored criteria (N/A: {len(vector.get('not_applicable', []))})"
    )


def _do_build(
    repo_root: Path, output: Path, run_id: str, test_artifact: Path | None = None
) -> Path:
    from substrate.understanding.reconstruction.builder import build_self_model

    now = datetime.now(timezone.utc).isoformat()
    result = build_self_model(
        repo_root=repo_root,
        output_root=output,
        run_id=run_id,
        now=now,
        test_artifact_path=test_artifact,
    )
    return Path(result.run_dir)


def _repo_state(repo_root: Path) -> tuple[str, str, str, list[str]]:
    """Bounded preflight: (commit, dirty, fingerprint, tracked_changed_paths).

    ONE git status call (review finding 3: no split dirty-signal source).
    dirty means TRACKED-file modifications — untracked files do not change the
    identity of committed code and never dirty a qualification. The
    fingerprint distinguishes a clean commit from a dirty tree WITHOUT storing
    diff contents: sha256 over commit + dirty flag + changed path NAMES only.
    """
    import hashlib
    import subprocess

    commit = ""
    tracked_changed: list[str] = []
    dirty_str = "unknown"
    try:
        head_proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if head_proc.returncode == 0:
            commit = head_proc.stdout.strip()
        status_proc = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if status_proc.returncode == 0:
            for line in status_proc.stdout.splitlines():
                if not line.strip():
                    continue
                if line[:2] != "??":  # untracked files are not tracked changes
                    tracked_changed.append(line[3:].strip())
            tracked_changed.sort()
            dirty_str = "true" if tracked_changed else "false"
    except Exception as exc:
        print(f"  repo-state preflight degraded ({exc})")
    fingerprint = hashlib.sha256(
        f"{commit}|dirty={dirty_str}|{'|'.join(tracked_changed)}".encode("utf-8")
    ).hexdigest()
    return commit, dirty_str, fingerprint, tracked_changed


def _run_test_selection(repo_root: Path, output: Path, template_id: str) -> Path | None:
    """Run the bounded pytest selection with the evidence plugin.

    Returns the artifact path, or None when EVIDENCE ACQUISITION failed
    (missing/unqualifiable report). Test failures are NOT acquisition
    failures — a valid artifact recording failed tests is valid evidence.
    """
    import subprocess

    from substrate.understanding.reconstruction.pytest_evidence_plugin import (
        ENV_COMMIT,
        ENV_DIRTY,
        ENV_FINGERPRINT,
        ENV_OUT,
        ENV_SCHEMA,
        ENV_TEMPLATE,
        TEST_EVIDENCE_SCHEMA_VERSION,
    )
    from substrate.understanding.reconstruction.test_evidence import (
        PLUGIN_MODULE,
        SELECTION_TEMPLATES,
    )

    template = SELECTION_TEMPLATES.get(template_id)
    if template is None:
        print(f"unknown selection template {template_id!r}; known: {sorted(SELECTION_TEMPLATES)}")
        return None

    commit, dirty, fingerprint, pre_changed = _repo_state(repo_root)
    artifacts_dir = output / "test_artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = artifacts_dir / f"{template_id}-{stamp}.json"

    env = os.environ.copy()
    env[ENV_OUT] = str(artifact_path)
    env[ENV_COMMIT] = commit
    env[ENV_DIRTY] = dirty
    env[ENV_FINGERPRINT] = fingerprint
    env[ENV_TEMPLATE] = template_id
    env[ENV_SCHEMA] = TEST_EVIDENCE_SCHEMA_VERSION
    env.setdefault("UMH_ROOT", str(repo_root))

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *template["paths"],
        "-p",
        PLUGIN_MODULE,
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    print(
        f"[run-tests] template={template_id} files={len(template['paths'])} commit={commit[:12]} dirty={dirty}"
    )
    proc = subprocess.run(cmd, cwd=repo_root, env=env, capture_output=True, text=True, timeout=2400)
    tail = "\n".join((proc.stdout or "").splitlines()[-6:])
    print(f"  pytest exit={proc.returncode}\n{tail}")

    # Evidence QUALIFICATION (separate from test outcomes — amendment F).
    if not artifact_path.is_file():
        print("  evidence acquisition FAILED: report missing")
        return None
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        print(f"  evidence acquisition FAILED: report unparseable ({exc})")
        return None
    problems: list[str] = []
    if artifact.get("schema_version") != TEST_EVIDENCE_SCHEMA_VERSION:
        problems.append(f"schema {artifact.get('schema_version')!r}")
    if artifact.get("plugin_error"):
        problems.append(f"plugin_error {artifact['plugin_error']}")
    session = artifact.get("session") or {}
    for field_name in ("started_at", "finished_at", "exit_status", "injected"):
        if session.get(field_name) in (None, ""):
            problems.append(f"missing session field {field_name}")
    if problems:
        print(f"  evidence acquisition FAILED: {'; '.join(problems)}")
        return None

    # Post-run repository drift (review finding 1): some selection tests
    # exercise the REAL canonical mutation path and append to tracked
    # data/umh/** runtime journals. Classify the drift:
    #   - drift outside data/  → implementation changed during the evidence
    #     run → acquisition FAILED (the artifact no longer describes HEAD);
    #   - drift limited to data/ (runtime journals) → test side effects, not
    #     code change; when the preflight was CLEAN, restore exactly those
    #     paths so the subsequent build sees the same clean state the
    #     artifact was stamped with.
    post_commit, _post_dirty, _post_fp, post_changed = _repo_state(repo_root)
    if post_commit != commit:
        print("  evidence acquisition FAILED: HEAD changed during the evidence run")
        return None
    drift = sorted(set(post_changed) - set(pre_changed))
    non_data_drift = [p for p in drift if not p.startswith("data/")]
    if non_data_drift:
        print(
            "  evidence acquisition FAILED: tracked non-data files changed during "
            f"the evidence run: {non_data_drift[:10]}"
        )
        return None
    if drift:
        if dirty == "false":
            restore = subprocess.run(
                ["git", "-C", str(repo_root), "restore", "--", *drift],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if restore.returncode == 0:
                print(
                    f"  restored {len(drift)} tracked data/ runtime-journal paths "
                    "mutated by the selection tests (side effects, not code change)"
                )
            else:
                print(
                    f"  WARNING: could not restore {len(drift)} test-side-effect "
                    f"paths: {restore.stderr.strip()[:200]}"
                )
        else:
            print(
                f"  note: {len(drift)} tracked data/ paths mutated by the selection "
                "tests (tree was already dirty — dev mode, artifact self-rejects)"
            )
    print(f"  evidence artifact qualified: {artifact_path}")
    return artifact_path


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
    ap.add_argument(
        "--test-artifact",
        type=Path,
        default=None,
        help="pytest evidence artifact to ingest into the build (v1.2)",
    )
    ap.add_argument(
        "--run-tests",
        type=str,
        default=None,
        metavar="TEMPLATE_ID",
        help="run a bounded pytest selection with the evidence plugin, then build",
    )
    args = ap.parse_args()

    repo_root = args.repo_root or _default_repo_root()
    output = args.output or _default_output(repo_root)

    test_artifact: Path | None = args.test_artifact
    if args.run_tests:
        test_artifact = _run_test_selection(repo_root, output, args.run_tests)
        if test_artifact is None:
            return 2  # evidence acquisition failed (independent of test outcomes)
        args.build = True  # a fresh evidence artifact implies a fresh build

    if not args.build and not args.verify:
        args.verify = True  # default action

    run_dir: Path | None = None
    if args.build:
        run_id = args.run_id or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
        print(f"[build] repo_root={repo_root} output={output} run_id={run_id}")
        try:
            run_dir = _do_build(repo_root, output, run_id, test_artifact=test_artifact)
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

    te = manifest.get("test_evidence")
    if te:
        acc = te.get("accounting", {})
        print("\n  test evidence (v1.2):")
        print(
            f"    valid={te.get('valid')} template={te.get('selection_template_id') or '-'} "
            f"artifact_commit={str(te.get('artifact_commit'))[:12] or '-'}"
        )
        print(f"    by semantic outcome: {acc.get('executions_by_semantic_outcome', {})}")
        print(f"    by classification:   {acc.get('executions_by_classification', {})}")
        print(
            f"    tested facets derived: {acc.get('facets_derived', 0)} "
            f"| component mapping: {acc.get('component_mapping_status', '?')}"
        )
        if te.get("rejection_reasons"):
            print(f"    rejection reasons: {te['rejection_reasons']}")
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
