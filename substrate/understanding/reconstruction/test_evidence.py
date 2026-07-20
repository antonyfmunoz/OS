"""Test-evidence acquisition + ingestion for the reconstruction subsystem (v1.2).

Turns the pytest evidence artifact (written by pytest_evidence_plugin.py) and a
deterministic test-file inventory into evidence-graded records, WITHOUT
collapsing the truth hierarchy:

    test_declared != test_present != test_collected != test_executed !=
    test_passed != component_exercised != behavior_asserted !=
    outcome_verified != general correctness

Non-negotiables implemented here:
  - a test file referencing/importing a module is a CANDIDATE link
    (observation_kind="test_reference", maturity_facet=None,
    relationship_strength="candidate") — NEVER a tested facet;
  - classification comes from REGISTERED markers only ("integration" is the
    only class marker this repository registers; everything else is
    "unknown") — never from filenames or intuition;
  - two outcome dimensions are preserved per execution: semantic_outcome
    (passed/failed/skipped/xfailed/xpassed/error) and session_effect
    (pass/fail/neutral), plus raw setup/call/teardown phase outcomes;
  - a stale or invalid artifact (commit mismatch, dirty tree, plugin_error,
    unsupported schema, missing session fields) is REJECTED: zero execution
    observations, an explicit report_rejected record instead;
  - tested facets derive ONLY through derive_tested_facets(): passing
    execution at the build commit + evidence-backed class + QUALIFYING
    component-exercise mapping (coverage context / explicit target metadata).
    Static imports never qualify. With no coverage tooling installed the real
    path derives ZERO facets and says so (component_mapping_status).

Deterministic, no subprocess — the controlling CLI owns the pytest invocation.

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from substrate.understanding.reconstruction.contracts import (
    ObservationRecord,
    SourceRecord,
    ValidTime,
)
from substrate.understanding.reconstruction.repository_inventory import (
    _excluded_category,
    _is_sensitive,
)

TEST_EVIDENCE_SCHEMA_VERSION = "test-evidence-v1"
PLUGIN_MODULE = "substrate.understanding.reconstruction.pytest_evidence_plugin"

# The ONLY class markers this repository registers (pyproject
# [tool.pytest.ini_options].markers). There is no "unit" marker and no
# documented filename-class convention, so unmarked tests classify "unknown".
REGISTERED_CLASS_MARKERS: dict[str, str] = {"integration": "integration"}

# Mapping bases that QUALIFY a test→component relationship for facet
# derivation. Static references never appear here by design.
QUALIFYING_MAPPING_BASES: frozenset[str] = frozenset(
    {"coverage_context", "explicit_target_metadata"}
)

SEMANTIC_OUTCOMES: frozenset[str] = frozenset(
    {"passed", "failed", "skipped", "xfailed", "xpassed", "error"}
)
SESSION_EFFECTS: frozenset[str] = frozenset({"pass", "fail", "neutral"})

# Top-level packages whose imports count as candidate component references.
_COMPONENT_PACKAGES: frozenset[str] = frozenset(
    {"substrate", "adapters", "transports", "services", "projections", "saas", "nodes"}
)

_MAX_PARSE_BYTES = 2 * 1024 * 1024

# Bounded, evidence-driven selection templates (§9). Files verified to collect
# cleanly at template-definition time; the artifact records the resolved
# manifest so eligibility is always reconstructable. Tests outside a template
# are outside_selection_boundary — never "deselected".
SELECTION_TEMPLATES: dict[str, dict[str, Any]] = {
    "reconstruction-spine-v1": {
        "description": (
            "Reconstruction subsystem + type-divergence gate + canonical "
            "mutation path + world model + approval authority + runtime "
            "convergence (event spine)"
        ),
        "paths": [
            "tests/test_reconstruction_contracts.py",
            "tests/test_reconstruction_provenance.py",
            "tests/test_reconstruction_ledger.py",
            "tests/test_reconstruction_identity.py",
            "tests/test_reconstruction_inventory.py",
            "tests/test_reconstruction_probes.py",
            "tests/test_reconstruction_builder.py",
            "tests/test_reconstruction_evaluation.py",
            "tests/test_reconstruction_import_evidence.py",
            "tests/test_reconstruction_test_evidence.py",
            "tests/test_type_divergence.py",
            "tests/test_c34_mutation_router.py",
            "tests/test_governed_mutation_fail_closed.py",
            "tests/test_governed_execution_runtime.py",
            "tests/test_p1_phase4_world_model.py",
            "tests/test_unified_approval_runtime.py",
            "tests/test_unified_approval_authority.py",
            "tests/test_c40a_runtime_convergence.py",
        ],
    },
}


@dataclass(frozen=True)
class TestEvidenceResult:
    """Result of the test-evidence seam: sources + observations + accounting.

    facet_observations are SEPARATE from observations so the builder (and the
    reader) can always see exactly which records assert component maturity —
    in real v1.2 runs this tuple is empty (no qualifying mapping source).
    """

    sources: tuple[SourceRecord, ...]
    observations: tuple[ObservationRecord, ...]
    facet_observations: tuple[ObservationRecord, ...] = ()
    accounting: dict[str, Any] = field(default_factory=dict)
    qualification: dict[str, Any] = field(default_factory=dict)
    artifact: Optional[dict[str, Any]] = None


def file_bytes_sha256(path: str | os.PathLike[str]) -> str:
    """SHA-256 of a file's raw bytes (no parse/reserialize — amendment G)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def component_mapping_status() -> str:
    """Honest statement of the component-exercise mapping capability.

    Coverage dynamic contexts are the preferred mapping evidence; the tooling
    is not installed in this repository, so the adapter is contract-only.
    """
    if importlib.util.find_spec("coverage") is None:
        return "coverage_tooling_not_installed"
    return "coverage_installed_but_context_ingestion_not_wired"


# ── classification ──────────────────────────────────────────────────────────


def classify_test(markers: list[str] | tuple[str, ...]) -> tuple[str, str]:
    """Evidence-backed test classification: (class, basis).

    Only registered class markers classify; everything else is ("unknown",
    "no_registered_class_marker"). Filenames NEVER classify (no repository law
    defines a filename convention).
    """
    for m in markers:
        cls = REGISTERED_CLASS_MARKERS.get(m)
        if cls:
            return cls, f"registered_marker:{m}"
    return "unknown", "no_registered_class_marker"


# ── outcome normalization (two dimensions, phases preserved) ────────────────


def normalize_execution(phases: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw per-phase pytest outcomes into the two-dimension model.

    Input: {"setup": {...}|None, "call": {...}|None, "teardown": {...}|None}
    where each phase dict carries at least {"outcome"} and optionally
    {"wasxfail", "wasxfail_reason", "detail", "duration"}.

    Returns semantic_outcome, session_effect, phase_outcomes (raw, preserved),
    strict_xfail_effect, wasxfail_reason, duration_total. Aggregation NEVER
    erases phase reports — callers must store phase_outcomes alongside.
    """
    setup = phases.get("setup")
    call = phases.get("call")
    teardown = phases.get("teardown")

    def oc(p: Optional[dict[str, Any]]) -> str:
        return str(p.get("outcome")) if p else "not_run"

    phase_outcomes = {"setup": oc(setup), "call": oc(call), "teardown": oc(teardown)}
    wasxfail = any(bool(p and p.get("wasxfail")) for p in (setup, call, teardown))
    wasxfail_reason = ""
    for p in (call, setup, teardown):
        if p and p.get("wasxfail"):
            wasxfail_reason = str(p.get("wasxfail_reason", ""))
            break
    duration_total = round(
        sum(float(p.get("duration", 0.0)) for p in (setup, call, teardown) if p), 6
    )

    strict_xfail_effect = "unknown"
    if oc(setup) == "failed":
        semantic, effect = "error", "fail"
    elif oc(setup) == "skipped" and oc(call) == "not_run":
        semantic, effect = ("xfailed", "neutral") if wasxfail else ("skipped", "neutral")
    elif oc(call) == "failed":
        detail = str((call or {}).get("detail", ""))
        if "XPASS(strict)" in detail:
            # Strict unexpected pass: semantically XPASS, fails the session.
            semantic, effect = "xpassed", "fail"
            strict_xfail_effect = "true"
        else:
            semantic, effect = "failed", "fail"
    elif oc(call) == "skipped":
        semantic, effect = ("xfailed", "neutral") if wasxfail else ("skipped", "neutral")
    elif oc(call) == "passed":
        if (call or {}).get("wasxfail"):
            # Non-strict unexpected pass: reported, does not fail the session.
            semantic, effect = "xpassed", "pass"
            strict_xfail_effect = "false"
        else:
            semantic, effect = "passed", "pass"
    else:
        # setup passed but call never ran (interrupted/internal) — an error.
        semantic, effect = "error", "fail"

    if oc(teardown) == "failed":
        # Teardown failure always fails the session; a genuine call failure
        # keeps its semantics, everything else becomes an error. Phases stay.
        effect = "fail"
        if semantic != "failed":
            semantic = "error"

    return {
        "semantic_outcome": semantic,
        "session_effect": effect,
        "phase_outcomes": phase_outcomes,
        "wasxfail": wasxfail,
        "wasxfail_reason": wasxfail_reason,
        "strict_xfail_effect": strict_xfail_effect,
        "duration_total": duration_total,
    }


# ── test-file inventory (candidate links ONLY) ──────────────────────────────


def scan_test_inventory(
    repo_root: str | os.PathLike[str],
    run_id: str,
    activity_id: str,
    *,
    repo_commit: Optional[str] = None,
    repo_commit_status: str = "unavailable",
    now: Optional[str] = None,
    test_dir: str = "tests",
) -> tuple[list[SourceRecord], list[ObservationRecord], dict[str, Any]]:
    """Inventory test files: real source hashes + static-import CANDIDATE links.

    Emits per test file one SourceRecord (real bytes hash) and, when the file
    imports component packages, one candidate-link observation
    (observation_kind="test_reference", maturity_facet=None,
    relationship_strength="candidate"). Discovery evidence only — never proof
    that any component is tested.
    """
    root = Path(repo_root).resolve()
    tdir = root / test_dir
    sources: list[SourceRecord] = []
    observations: list[ObservationRecord] = []
    discovered = 0
    parse_errors = 0
    link_files = 0

    if tdir.is_dir():
        for path in sorted(tdir.rglob("*.py")):
            rel = path.relative_to(root)
            if _excluded_category(rel.parts) is not None:
                continue
            if _is_sensitive(rel.parts, path.name):
                continue
            if not path.name.startswith("test_") and path.name != "conftest.py":
                continue
            discovered += 1
            rel_str = rel.as_posix()
            try:
                body = path.read_bytes()
            except OSError:
                parse_errors += 1
                continue
            src = SourceRecord(
                subject_path=rel_str,
                source_kind="repository_file",
                modality="code",
                activity_id=activity_id,
                run_id=run_id,
                source_content_hash=hashlib.sha256(body).hexdigest(),
                repository_commit=repo_commit,
                repository_commit_status=repo_commit_status,  # type: ignore[arg-type]
                acquisition_context="test_inventory",
                acquired_at=now,
                recorded_at=now,
                metadata={"size_bytes": len(body), "category": "test"},
            )
            sources.append(src)

            targets: list[str] = []
            if len(body) <= _MAX_PARSE_BYTES:
                try:
                    tree = ast.parse(body.decode("utf-8", errors="replace"))
                except SyntaxError:
                    parse_errors += 1
                    tree = None
                if tree is not None:
                    seen: set[str] = set()
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                seen.add(alias.name)
                        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                            seen.add(node.module)
                    targets = sorted(d for d in seen if d.split(".", 1)[0] in _COMPONENT_PACKAGES)
            if targets:
                link_files += 1
                observations.append(
                    ObservationRecord(
                        subject=f"test_file:{rel_str}",
                        predicate="references_components",
                        value={
                            "targets": targets,
                            "relationship_strength": "candidate",
                            "note": (
                                "static import reference — discovery evidence, "
                                "never component-tested evidence"
                            ),
                        },
                        observation_kind="test_reference",
                        source_id=src.id,
                        run_id=run_id,
                        maturity_facet=None,
                        scope="tests",
                        valid_time=ValidTime(qualifier="unknown"),
                        recorded_at=now,
                        support={"target_count": len(targets)},
                    )
                )

    accounting = {
        "inventory_discovered": discovered,
        "inventory_parse_errors": parse_errors,
        "candidate_link_files": link_files,
    }
    return sources, observations, accounting


# ── artifact ingestion ──────────────────────────────────────────────────────

_REQUIRED_SESSION_FIELDS = ("started_at", "finished_at", "exit_status", "injected")


def _validate_artifact(
    artifact: Any, build_commit: Optional[str]
) -> tuple[bool, list[str], dict[str, Any]]:
    """Return (valid, rejection_reasons, extracted_session_info)."""
    reasons: list[str] = []
    info: dict[str, Any] = {}
    if not isinstance(artifact, dict):
        return False, ["malformed_report"], info
    if artifact.get("schema_version") != TEST_EVIDENCE_SCHEMA_VERSION:
        reasons.append(f"unsupported_schema:{artifact.get('schema_version')!r}")
    if artifact.get("plugin_error"):
        reasons.append("plugin_error_present")
    session = artifact.get("session")
    if not isinstance(session, dict):
        reasons.append("missing_session_record")
        return False, reasons, info
    for field_name in _REQUIRED_SESSION_FIELDS:
        if session.get(field_name) in (None, ""):
            reasons.append(f"missing_session_field:{field_name}")
    injected = session.get("injected") or {}
    artifact_commit = str(injected.get("repository_commit", "") or "")
    dirty = str(injected.get("repository_dirty", "unknown"))
    info = {
        "artifact_commit": artifact_commit,
        "repository_dirty": dirty,
        "repository_fingerprint": injected.get("repository_fingerprint", ""),
        "selection_template_id": injected.get("selection_template_id", ""),
        "exit_status": session.get("exit_status"),
        "plugin_version": artifact.get("plugin_version", ""),
    }
    if not artifact_commit:
        reasons.append("missing_repository_commit")
    elif build_commit and artifact_commit != build_commit:
        reasons.append("stale_commit")
    elif not build_commit:
        reasons.append("builder_commit_unresolved")
    if dirty != "false":
        reasons.append(f"repository_dirty:{dirty}")
    return not reasons, reasons, info


def ingest_test_report(
    artifact_path: str | os.PathLike[str],
    run_id: str,
    activity_id: str,
    *,
    build_commit: Optional[str],
    build_commit_status: str = "unavailable",
    now: Optional[str] = None,
) -> dict[str, Any]:
    """Ingest a plugin artifact into evidence records.

    Returns {"source", "observations", "qualification", "artifact",
    "artifact_sha256", "executions"}. A stale/invalid artifact is REJECTED:
    zero execution observations; one report_rejected observation carries the
    reasons. Test-run failure and evidence qualification are separate outcomes
    — failed tests in a VALID artifact are ingested as counterevidence.
    """
    p = Path(artifact_path)
    observations: list[ObservationRecord] = []
    executions: list[dict[str, Any]] = []
    qualification: dict[str, Any] = {"valid": False, "reasons": [], "artifact_sha256": ""}

    if not p.is_file():
        qualification["reasons"] = ["report_missing"]
        return {
            "source": None,
            "observations": [],
            "qualification": qualification,
            "artifact": None,
            "artifact_sha256": "",
            "executions": [],
        }

    artifact_sha = file_bytes_sha256(p)
    qualification["artifact_sha256"] = artifact_sha
    try:
        artifact = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        artifact = None

    if artifact is None:
        valid, reasons, info = False, ["malformed_report"], {}
    else:
        valid, reasons, info = _validate_artifact(artifact, build_commit)
    qualification.update({"valid": valid, "reasons": reasons, **info})

    src = SourceRecord(
        subject_path="run:test_report.json",
        source_kind="derived_artifact",
        modality="derived",
        activity_id=activity_id,
        run_id=run_id,
        source_content_hash=artifact_sha,
        repository_commit=(info.get("artifact_commit") or None) if artifact else None,
        repository_commit_status=(
            "resolved" if artifact and info.get("artifact_commit") else "unavailable"
        ),
        acquisition_context="pytest_evidence_plugin artifact (run copy)",
        redaction_status="partial",  # plugin redacts reasons/details at source
        acquired_at=now,
        recorded_at=now,
        metadata={
            "plugin_version": info.get("plugin_version", "") if artifact else "",
            "valid": valid,
        },
    )

    if not valid:
        observations.append(
            ObservationRecord(
                subject="test_report",
                predicate="report_rejected",
                value={"reasons": reasons},
                observation_kind="test_report_status",
                source_id=src.id,
                run_id=run_id,
                maturity_facet=None,
                scope="tests",
                valid_time=ValidTime(qualifier="instant"),
                recorded_at=now,
                support={"artifact_sha256": artifact_sha},
            )
        )
        return {
            "source": src,
            "observations": observations,
            "qualification": qualification,
            "artifact": artifact,
            "artifact_sha256": artifact_sha,
            "executions": [],
        }

    session = artifact["session"]
    collected = artifact.get("collected", [])
    markers_by_nodeid = {c.get("nodeid"): c.get("markers", []) for c in collected}
    raw_execs = artifact.get("executions", {})
    deselected = artifact.get("deselected_after_collection", [])
    collection_errors = artifact.get("collection_errors", [])
    artifact_commit = info["artifact_commit"]

    for nodeid in sorted(raw_execs):
        norm = normalize_execution(raw_execs[nodeid].get("phases", {}))
        markers = list(markers_by_nodeid.get(nodeid, []))
        cls, cls_basis = classify_test(markers)
        record = {
            "nodeid": nodeid,
            **norm,
            "classification": cls,
            "classification_basis": cls_basis,
            "markers": markers,
            "commit": artifact_commit,
        }
        executions.append(record)
        observations.append(
            ObservationRecord(
                subject=f"test:{nodeid}",
                predicate="test_execution",
                value=record,
                observation_kind="test_execution",
                source_id=src.id,
                run_id=run_id,
                maturity_facet=None,  # execution evidence, not component maturity
                scope="tests",
                valid_time=ValidTime(qualifier="instant"),
                recorded_at=now,
                support={"commit": artifact_commit, "session_exit_status": info["exit_status"]},
            )
        )

    executed_ids = set(raw_execs)
    collected_ids = {c.get("nodeid") for c in collected}
    observations.append(
        ObservationRecord(
            subject="test_session",
            predicate="collection_summary",
            value={
                "collected": len(collected),
                "deselected_after_collection": len(deselected),
                "collection_errors": len(collection_errors),
                "executed": len(executed_ids),
                "not_executed_after_collection": len(collected_ids - executed_ids),
                "selection_template_id": info["selection_template_id"],
                "exit_status": info["exit_status"],
                "boundary_note": (
                    "tests outside the selection template are "
                    "outside_selection_boundary — never counted as deselected"
                ),
            },
            observation_kind="test_collection",
            source_id=src.id,
            run_id=run_id,
            maturity_facet=None,
            scope="tests",
            valid_time=ValidTime(qualifier="instant"),
            recorded_at=now,
            support={"started_at": session.get("started_at")},
        )
    )

    return {
        "source": src,
        "observations": observations,
        "qualification": qualification,
        "artifact": artifact,
        "artifact_sha256": artifact_sha,
        "executions": executions,
    }


# ── facet derivation (pure — the ONLY path to a tested facet) ───────────────


def derive_tested_facets(
    executions: list[dict[str, Any]],
    exercise_map: Optional[dict[str, dict[str, Any]]],
    *,
    build_commit: Optional[str],
    run_id: str,
    source_id: str,
    now: Optional[str] = None,
) -> dict[str, Any]:
    """Derive component tested-facet observations from qualified evidence.

    A facet is emitted ONLY when ALL hold for an execution:
      1. semantic_outcome == "passed" AND session_effect == "pass"
         (xpassed/skipped/xfailed/failed/error NEVER qualify);
      2. execution commit == build_commit (both resolved) — stale is inert;
      3. classification is evidence-backed unit/integration
         (basis startswith "registered_marker:");
      4. a QUALIFYING component-exercise mapping exists for the nodeid
         (basis in QUALIFYING_MAPPING_BASES — static references never qualify).

    The derivation is repo-agnostic: it supports any registered class marker.
    In THIS repository no "unit" marker is registered, so unit_tested is
    structurally unreachable in real runs — integration_tested is the only
    derivable facet, and only once a qualifying mapping source exists.

    exercise_map: {nodeid: {"components": [paths], "basis": str}} or None.
    Returns {"facets": [ObservationRecord], "rejections": [...],
    "component_mapping_status": str}.
    """
    facets: list[ObservationRecord] = []
    rejections: list[dict[str, str]] = []

    for ex in executions:
        nodeid = ex.get("nodeid", "")
        if ex.get("semantic_outcome") != "passed" or ex.get("session_effect") != "pass":
            rejections.append(
                {"nodeid": nodeid, "reason": f"not_a_pass:{ex.get('semantic_outcome')}"}
            )
            continue
        if not build_commit or ex.get("commit") != build_commit:
            rejections.append({"nodeid": nodeid, "reason": "stale_or_unresolved_commit"})
            continue
        cls = ex.get("classification", "unknown")
        basis = str(ex.get("classification_basis", ""))
        if cls not in ("unit", "integration") or not basis.startswith("registered_marker:"):
            rejections.append({"nodeid": nodeid, "reason": f"class_not_evidence_backed:{cls}"})
            continue
        mapping = (exercise_map or {}).get(nodeid)
        if not mapping or mapping.get("basis") not in QUALIFYING_MAPPING_BASES:
            rejections.append(
                {
                    "nodeid": nodeid,
                    "reason": (
                        "no_qualifying_component_mapping"
                        if not mapping
                        else f"mapping_basis_not_qualifying:{mapping.get('basis')}"
                    ),
                }
            )
            continue
        facet = f"{cls}_tested"
        for component in sorted(mapping.get("components", [])):
            facets.append(
                ObservationRecord(
                    subject=f"file:{component}",
                    predicate="tested_by",
                    value={
                        "nodeid": nodeid,
                        "semantic_outcome": "passed",
                        "classification": cls,
                        "mapping_basis": mapping["basis"],
                        "commit": build_commit,
                        "proof_scope": (
                            "test passed and exercised this component under the "
                            "recorded mapping; exact behavioral proof scope not "
                            "machine-derived — never general correctness"
                        ),
                    },
                    observation_kind="tested_facet",
                    source_id=source_id,
                    run_id=run_id,
                    maturity_facet=facet,  # type: ignore[arg-type]
                    scope="tests",
                    valid_time=ValidTime(qualifier="instant"),
                    recorded_at=now,
                    support={
                        "derived_from_execution": nodeid,
                        "mapping_basis": mapping["basis"],
                        "classification": cls,
                        "classification_basis": basis,
                    },
                )
            )

    return {
        "facets": facets,
        "rejections": rejections,
        "component_mapping_status": (
            "synthetic_fixture" if exercise_map is not None else component_mapping_status()
        ),
    }


# ── the seam ────────────────────────────────────────────────────────────────


def collect_test_evidence(
    repo_root: str | os.PathLike[str],
    run_id: str,
    activity_id: str,
    *,
    artifact_path: Optional[str | os.PathLike[str]] = None,
    build_commit: Optional[str] = None,
    build_commit_status: str = "unavailable",
    now: Optional[str] = None,
) -> TestEvidenceResult:
    """FIXED SEAM: inventory + optional artifact ingestion + facet derivation.

    Without an artifact_path the result carries inventory evidence only. The
    real path passes exercise_map=None into derive_tested_facets, so ZERO
    facets derive until a qualifying component-exercise mapping source exists
    (component_mapping_status names the gap).
    """
    inv_sources, inv_obs, accounting = scan_test_inventory(
        repo_root,
        run_id,
        activity_id,
        repo_commit=build_commit,
        repo_commit_status=build_commit_status,
        now=now,
    )
    sources = list(inv_sources)
    observations = list(inv_obs)
    facet_observations: list[ObservationRecord] = []
    qualification: dict[str, Any] = {}
    artifact: Optional[dict[str, Any]] = None

    if artifact_path is not None:
        ingest = ingest_test_report(
            artifact_path,
            run_id,
            activity_id,
            build_commit=build_commit,
            build_commit_status=build_commit_status,
            now=now,
        )
        if ingest["source"] is not None:
            sources.append(ingest["source"])
        observations.extend(ingest["observations"])
        qualification = ingest["qualification"]
        artifact = ingest["artifact"]
        if qualification.get("valid"):
            derived = derive_tested_facets(
                ingest["executions"],
                None,  # no qualifying mapping source installed — zero facets
                build_commit=build_commit,
                run_id=run_id,
                source_id=ingest["source"].id,
                now=now,
            )
            facet_observations.extend(derived["facets"])
            accounting["facet_rejection_count"] = len(derived["rejections"])
            accounting["component_mapping_status"] = derived["component_mapping_status"]
            by_semantic: dict[str, int] = {}
            by_class: dict[str, int] = {}
            for ex in ingest["executions"]:
                by_semantic[ex["semantic_outcome"]] = by_semantic.get(ex["semantic_outcome"], 0) + 1
                by_class[ex["classification"]] = by_class.get(ex["classification"], 0) + 1
            accounting["executions_by_semantic_outcome"] = dict(sorted(by_semantic.items()))
            accounting["executions_by_classification"] = dict(sorted(by_class.items()))
        else:
            accounting["component_mapping_status"] = component_mapping_status()
        accounting["executions_ingested"] = len(ingest["executions"])
        accounting["artifact_sha256"] = ingest["artifact_sha256"]
    else:
        accounting["component_mapping_status"] = component_mapping_status()
        accounting["executions_ingested"] = 0

    accounting["facets_derived"] = len(facet_observations)
    return TestEvidenceResult(
        sources=tuple(sources),
        observations=tuple(observations),
        facet_observations=tuple(facet_observations),
        accounting=accounting,
        qualification=qualification,
        artifact=artifact,
    )
