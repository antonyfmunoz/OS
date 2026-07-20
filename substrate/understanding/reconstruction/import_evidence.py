"""Formal-dependency import evidence for the reconstruction subsystem (v1.1).

Collects deterministic, AST/text-based software-dependency evidence for a set
of candidate modules — the evidence layer behind evidence-backed identity
verdicts. ZERO subprocess; one bounded walk over the repository's .py surface
(same exclusion + sensitive rules as repository_inventory), plus bounded scans
of the canonical registries, packaging files, and governing documents.

Evidence categories (per candidate module):
  1.  static imports          — ``import a.b.c`` (exact / submodule prefix)
  2.  relative imports        — ``from . import x`` resolved against the
                                importer's package before matching
  3.  __init__.py re-exports  — importer is a package __init__ (flagged)
  4.  symbol usage            — ``from cand import Foo`` → symbol references
  5.  qualified textual refs  — dotted-name occurrences in files that did NOT
                                import it (textual, a declared limitation)
  6.  __all__ exports         — the candidate's own declared export surface
  7.  registry registration   — dotted name in substrate/canonical_types.py or
                                data/umh/projection_registry.json
  8.  entry-point registration— pyproject.toml / setup.cfg textual scan
  9.  literal dynamic imports — importlib.import_module("<literal>") /
                                __import__("<literal>"); NON-literal calls are
                                counted repo-wide as opaque (absence of dynamic
                                evidence is NEVER provable while that count>0)
  10. test references         — importers under tests/ are references ONLY,
                                never proof of correctness
  11. documentation references— bounded governing-doc set, textual containment

Every import observation carries direct source locations ({lineno} sites,
first N per importer with an explicit total — truncation is recorded, never
silent). Observations carry observation_kind (import_reference /
symbol_reference / registry_registration / ...) with maturity_facet=None:
dependency evidence describes relationships, not implementation maturity.

Per candidate with >=1 static importer a CausalSupportRecord(basis="formal")
is emitted — the one causal class software reconstruction attains directly
(DOMAIN_RECONSTRUCTION_SPEC §4.9) — with limitations naming what static
scanning cannot see (string/dynamic imports, runtime paths).

UMH substrate subsystem. Instance-agnostic.
"""

from __future__ import annotations

import ast
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from substrate.understanding.reconstruction.contracts import (
    CausalSupportRecord,
    ObservationRecord,
    SourceRecord,
    ValidTime,
)
from substrate.understanding.reconstruction.provenance import content_hash
from substrate.understanding.reconstruction.repository_inventory import (
    _excluded_category,
    _is_sensitive,
)

logger = logging.getLogger(__name__)

# Files larger than this are not parsed (matches inventory hashing bound).
MAX_PARSE_BYTES = 2 * 1024 * 1024
# Line sites recorded per importer before explicit truncation.
MAX_SITES_PER_IMPORTER = 5

# Bounded governing-document set for reference category 11.
GOVERNING_DOCS: tuple[str, ...] = (
    "ARCHITECTURE.md",
    "PLATFORM_SPEC.md",
    "EPISTEMOLOGY.md",
    "DOMAIN_RECONSTRUCTION_SPEC.md",
    ".claude/CLAUDE.md",
)
GOVERNING_DOC_GLOBS: tuple[str, ...] = (".claude/rules",)

# Registry surfaces for category 7.
CANONICAL_TYPES_PATH = "substrate/canonical_types.py"
PROJECTION_REGISTRY_PATH = "data/umh/projection_registry.json"
# Packaging surfaces for category 8.
PACKAGING_PATHS: tuple[str, ...] = ("pyproject.toml", "setup.cfg")


def module_dotted_name(rel_path: str) -> str:
    """``substrate/organism/world_model.py`` → ``substrate.organism.world_model``.

    A package ``__init__.py`` maps to the package's dotted name.
    """
    p = rel_path[:-3] if rel_path.endswith(".py") else rel_path
    parts = [seg for seg in p.split("/") if seg]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


@dataclass
class _CandidateEvidence:
    """Accumulator for one candidate module's evidence."""

    path: str
    dotted: str
    importers: dict[str, dict[str, Any]] = field(default_factory=dict)
    symbols: dict[str, list[str]] = field(default_factory=dict)
    dynamic_importers: list[str] = field(default_factory=list)
    qualified_refs: list[str] = field(default_factory=list)
    registries: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    all_exports: list[str] = field(default_factory=list)
    doc_references: list[str] = field(default_factory=list)

    def importer_entry(self, importer: str) -> dict[str, Any]:
        e = self.importers.get(importer)
        if e is None:
            e = {
                "path": importer,
                "re_export": importer.endswith("/__init__.py"),
                "reference_class": (
                    "test_reference"
                    if importer.split("/", 1)[0] == "tests" or "/tests/" in importer
                    else "code"
                ),
                "line_sites": [],
                "site_count": 0,
            }
            self.importers[importer] = e
        return e

    def add_site(self, importer: str, lineno: int) -> None:
        e = self.importer_entry(importer)
        e["site_count"] += 1
        if len(e["line_sites"]) < MAX_SITES_PER_IMPORTER:
            e["line_sites"].append(lineno)


@dataclass(frozen=True)
class ImportEvidenceResult:
    """Result of a formal-dependency evidence pass over candidate modules."""

    sources: tuple[SourceRecord, ...]
    observations: tuple[ObservationRecord, ...]
    causal_records: tuple[CausalSupportRecord, ...]
    evidence_by_path: dict[str, dict[str, Any]] = field(default_factory=dict)
    accounting: dict[str, Any] = field(default_factory=dict)


def _resolve_import_from(importer_pkg_parts: list[str], node: ast.ImportFrom) -> Optional[str]:
    """Resolve an ImportFrom to an absolute dotted module (None if unresolvable)."""
    if node.level == 0:
        return node.module
    # level=1 → current package; each extra level ascends one package.
    keep = len(importer_pkg_parts) - (node.level - 1)
    if keep < 0:
        return None
    base = importer_pkg_parts[:keep]
    if node.module:
        base = base + node.module.split(".")
    return ".".join(base) if base else None


def _match_candidate(abs_module: str, names: list[str], cand_dotted: str) -> tuple[bool, list[str]]:
    """Does an import of abs_module (with symbol names) reference cand_dotted?

    Returns (matched, imported_symbols). Symbols are non-empty only for a
    direct ``from cand import X`` form.
    """
    if abs_module == cand_dotted:
        return True, [n for n in names if n != "*"]
    if abs_module.startswith(cand_dotted + "."):
        return True, []
    # from <parent> import <basename>
    parent, _, base = cand_dotted.rpartition(".")
    if parent and abs_module == parent and base in names:
        return True, []
    return False, []


def _scan_python_file(
    rel_path: str,
    text: str,
    candidates: dict[str, _CandidateEvidence],
    accounting: dict[str, Any],
) -> None:
    """Collect import/symbol/dynamic evidence from one parsed .py file."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as exc:
        accounting["parse_errors"] = accounting.get("parse_errors", 0) + 1
        logger.debug("import scan could not parse %s: %s", rel_path, exc)
        return

    # importer package parts (for relative-import resolution)
    parts = rel_path[:-3].split("/")
    pkg_parts = parts[:-1] if parts[-1] != "__init__" else parts[:-1]

    imported_any: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for cand in candidates.values():
                    if alias.name == cand.dotted or alias.name.startswith(cand.dotted + "."):
                        cand.add_site(rel_path, node.lineno)
                        imported_any.add(cand.dotted)
        elif isinstance(node, ast.ImportFrom):
            abs_module = _resolve_import_from(pkg_parts, node)
            if not abs_module:
                continue
            names = [a.name for a in node.names]
            for cand in candidates.values():
                matched, symbols = _match_candidate(abs_module, names, cand.dotted)
                if matched:
                    cand.add_site(rel_path, node.lineno)
                    imported_any.add(cand.dotted)
                    for sym in symbols:
                        cand.symbols.setdefault(sym, [])
                        if rel_path not in cand.symbols[sym]:
                            cand.symbols[sym].append(rel_path)
        elif isinstance(node, ast.Call):
            func = node.func
            is_dynamic = (
                isinstance(func, ast.Attribute)
                and func.attr == "import_module"
                and isinstance(func.value, ast.Name)
                and func.value.id == "importlib"
            ) or (isinstance(func, ast.Name) and func.id == "__import__")
            if not is_dynamic:
                continue
            if (
                node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                target = node.args[0].value
                for cand in candidates.values():
                    if target == cand.dotted or target.startswith(cand.dotted + "."):
                        if rel_path not in cand.dynamic_importers:
                            cand.dynamic_importers.append(rel_path)
            else:
                # Opaque dynamic import — absence of dynamic evidence is never
                # provable while this count is > 0.
                accounting["opaque_dynamic_import_count"] = (
                    accounting.get("opaque_dynamic_import_count", 0) + 1
                )

    # qualified textual references: dotted name present without an import
    for cand in candidates.values():
        if rel_path == cand.path or cand.dotted in imported_any:
            continue
        if cand.dotted in text:
            cand.qualified_refs.append(rel_path)


def _scan_candidate_own_file(root: Path, cand: _CandidateEvidence) -> None:
    """Parse the candidate's own module for its declared __all__ surface."""
    fpath = root / cand.path
    if not fpath.is_file():
        return
    try:
        tree = ast.parse(fpath.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, ValueError, OSError) as exc:
        logger.debug("could not parse candidate %s: %s", cand.path, exc)
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        cand.all_exports = [
                            e.value
                            for e in node.value.elts
                            if isinstance(e, ast.Constant) and isinstance(e.value, str)
                        ]


def _scan_registries_and_docs(
    root: Path, candidates: dict[str, _CandidateEvidence], accounting: dict[str, Any]
) -> None:
    """Categories 7, 8, 11 — bounded textual scans of known surfaces."""

    def read(rel: str) -> str:
        p = root / rel
        try:
            return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
        except OSError as exc:
            logger.debug("could not read %s: %s", rel, exc)
            return ""

    canonical_text = read(CANONICAL_TYPES_PATH)
    projection_text = read(PROJECTION_REGISTRY_PATH)
    packaging_texts = {p: read(p) for p in PACKAGING_PATHS}

    doc_paths: list[str] = [d for d in GOVERNING_DOCS if (root / d).is_file()]
    for g in GOVERNING_DOC_GLOBS:
        gdir = root / g
        if gdir.is_dir():
            doc_paths.extend(sorted(f"{g}/{p.name}" for p in gdir.glob("*.md") if p.is_file()))
    doc_texts = {d: read(d) for d in doc_paths}
    accounting["docs_scanned"] = doc_paths
    accounting["registries_scanned"] = [CANONICAL_TYPES_PATH, PROJECTION_REGISTRY_PATH]
    accounting["packaging_scanned"] = list(PACKAGING_PATHS)

    for cand in candidates.values():
        if f'"{cand.dotted}"' in canonical_text:
            cand.registries.append("substrate.canonical_types")
        if cand.dotted in projection_text or cand.path in projection_text:
            cand.registries.append("data/umh/projection_registry.json")
        for ppath, ptext in packaging_texts.items():
            if ptext and cand.dotted in ptext:
                cand.entry_points.append(ppath)
        for dpath, dtext in doc_texts.items():
            if cand.path in dtext or cand.dotted in dtext:
                cand.doc_references.append(dpath)


def scan_import_evidence(
    repo_root: str | os.PathLike[str],
    candidate_paths: list[str],
    run_id: str,
    activity_id: str,
    *,
    now: Optional[str] = None,
) -> ImportEvidenceResult:
    """Collect formal-dependency evidence for candidate modules.

    FIXED SEAM: ``scan_import_evidence(repo_root, candidate_paths, run_id,
    activity_id) -> ImportEvidenceResult``. Deterministic given the same tree
    (sorted walk, stable ordering everywhere). Evidence generation is separate
    from verdicts: this module never decides identity — it produces the
    observations verdicts must cite.
    """
    root = Path(repo_root).resolve()
    candidates: dict[str, _CandidateEvidence] = {}
    for path in sorted(set(candidate_paths)):
        candidates[path] = _CandidateEvidence(path=path, dotted=module_dotted_name(path))

    accounting: dict[str, Any] = {
        "candidates": len(candidates),
        "py_files_scanned": 0,
        "parse_errors": 0,
        "opaque_dynamic_import_count": 0,
    }

    # One deterministic walk over the .py surface.
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        filenames.sort()
        dp = Path(dirpath)
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            fpath = dp / fname
            try:
                rel = fpath.relative_to(root)
            except ValueError:
                continue
            rel_parts = rel.parts
            rel_str = rel.as_posix()
            if _excluded_category(rel_parts) is not None:
                continue
            if fpath.is_symlink() or _is_sensitive(rel_parts, fname):
                continue
            try:
                if fpath.stat().st_size > MAX_PARSE_BYTES:
                    continue
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.debug("import scan could not read %s: %s", rel_str, exc)
                continue
            accounting["py_files_scanned"] += 1
            _scan_python_file(rel_str, text, candidates, accounting)

    for cand in candidates.values():
        _scan_candidate_own_file(root, cand)
    _scan_registries_and_docs(root, candidates, accounting)

    # ── Emit records ────────────────────────────────────────────────────────
    evidence_map = {
        p: {
            "importers": sorted(c.importers),
            "symbols": {k: sorted(v) for k, v in sorted(c.symbols.items())},
            "dynamic_importers": sorted(c.dynamic_importers),
            "qualified_refs": sorted(c.qualified_refs),
            "registries": sorted(set(c.registries)),
            "entry_points": sorted(set(c.entry_points)),
            "all_exports": c.all_exports,
            "doc_references": sorted(set(c.doc_references)),
        }
        for p, c in sorted(candidates.items())
    }
    scan_hash = content_hash(evidence_map)
    src = SourceRecord(
        subject_path="derived:import_evidence_scan",
        source_kind="derived_artifact",
        modality="derived",
        source_content_hash="",
        extraction_hash=scan_hash,
        derivation_key=scan_hash,
        derivation_activity_id=activity_id,
        activity_id=activity_id,
        run_id=run_id,
        acquisition_context="formal-dependency import evidence scan",
        recorded_at=now,
        acquired_at=now,
        metadata={
            "content_recorded": False,
            "candidates": len(candidates),
            "py_files_scanned": accounting["py_files_scanned"],
        },
    )

    observations: list[ObservationRecord] = []
    causal_records: list[CausalSupportRecord] = []
    evidence_by_path: dict[str, dict[str, Any]] = {}

    def obs(subject: str, predicate: str, value: Any, kind: str) -> ObservationRecord:
        o = ObservationRecord(
            subject=subject,
            predicate=predicate,
            value=value,
            observation_kind=kind,
            maturity_facet=None,  # relationship evidence, not maturity
            source_id=src.id,
            run_id=run_id,
            scope="import_evidence",
            valid_time=ValidTime(qualifier="unknown"),
            recorded_at=now,
        )
        observations.append(o)
        return o

    for path in sorted(candidates):
        c = candidates[path]
        subject = f"file:{path}"
        summary: dict[str, Any] = {
            "path": path,
            "dotted": c.dotted,
            "observation_ids": {},
        }

        importer_entries = [c.importers[k] for k in sorted(c.importers)]
        code_importers = [e["path"] for e in importer_entries if e["reference_class"] == "code"]
        test_importers = [
            e["path"] for e in importer_entries if e["reference_class"] == "test_reference"
        ]
        o = obs(
            subject,
            "imported_by",
            {"importers": importer_entries, "count": len(importer_entries)},
            "import_reference",
        )
        summary["observation_ids"]["imported_by"] = o.id
        summary["static_importers"] = sorted(c.importers)
        summary["code_importer_count"] = len(code_importers)
        summary["test_reference_count"] = len(test_importers)

        if c.symbols:
            o = obs(
                subject,
                "symbol_referenced_by",
                {
                    "symbols": {k: sorted(v) for k, v in sorted(c.symbols.items())},
                    "count": len(c.symbols),
                },
                "symbol_reference",
            )
            summary["observation_ids"]["symbol_referenced_by"] = o.id
        if c.dynamic_importers:
            o = obs(
                subject,
                "dynamically_imported_by",
                {"importers": sorted(c.dynamic_importers)},
                "dynamic_import_reference",
            )
            summary["observation_ids"]["dynamically_imported_by"] = o.id
        summary["dynamic_import_count"] = len(c.dynamic_importers)
        if c.qualified_refs:
            o = obs(
                subject,
                "qualified_referenced_by",
                {"files": sorted(c.qualified_refs), "count": len(c.qualified_refs)},
                "qualified_reference",
            )
            summary["observation_ids"]["qualified_referenced_by"] = o.id
        summary["qualified_reference_count"] = len(c.qualified_refs)
        if c.registries:
            o = obs(
                subject,
                "registered_in",
                {"registries": sorted(set(c.registries))},
                "registry_registration",
            )
            summary["observation_ids"]["registered_in"] = o.id
        summary["registries"] = sorted(set(c.registries))
        if c.entry_points:
            o = obs(
                subject,
                "entry_point_registered_in",
                {"files": sorted(set(c.entry_points))},
                "entry_point_registration",
            )
            summary["observation_ids"]["entry_point_registered_in"] = o.id
        if c.all_exports:
            o = obs(
                subject,
                "declares_all_exports",
                {"names": c.all_exports},
                "export_declaration",
            )
            summary["observation_ids"]["declares_all_exports"] = o.id
        if c.doc_references:
            o = obs(
                subject,
                "referenced_in_documentation",
                {"documents": sorted(set(c.doc_references))},
                "doc_reference",
            )
            summary["observation_ids"]["referenced_in_documentation"] = o.id
        summary["doc_references"] = sorted(set(c.doc_references))

        if code_importers or test_importers:
            causal_records.append(
                CausalSupportRecord(
                    assertion_id=f"formal_dependency:{path}",
                    basis="formal",
                    run_id=run_id,
                    evidence_ids=(summary["observation_ids"]["imported_by"],),
                    scope=subject,
                    method="ast_static_import_scan",
                    formal_soundness=1.0,
                    limitations=(
                        "string/dynamic imports not statically visible",
                        f"opaque dynamic imports repo-wide: "
                        f"{accounting['opaque_dynamic_import_count']}",
                        "runtime execution paths not assessed in v1.1",
                    ),
                    recorded_at=now,
                )
            )
        evidence_by_path[path] = summary

    return ImportEvidenceResult(
        sources=(src,),
        observations=tuple(observations),
        causal_records=tuple(causal_records),
        evidence_by_path=evidence_by_path,
        accounting=accounting,
    )
