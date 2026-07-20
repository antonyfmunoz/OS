"""Tests for the formal-dependency import-evidence scan (v1.1).

Covers the council's evidence categories: absolute/from/relative/parent-from
static imports with line sites; __init__ re-export flagging; symbol usage;
__all__ exports; literal importlib matches; opaque importlib counted (never
classified as absence); registry + packaging + documentation references; test
importers as references only; determinism; parse-error tolerance; exclusion
and sensitive-path respect. Verdict rules are tested in the builder suite —
this module produces evidence only, never identity decisions.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(os.environ.get("UMH_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(REPO_ROOT))

from substrate.understanding.reconstruction.import_evidence import (
    ImportEvidenceResult,
    module_dotted_name,
    scan_import_evidence,
)

CANDIDATE_A = "pkg/target.py"
CANDIDATE_B = "other/lonely.py"


def _build_tree(root: Path) -> None:
    (root / "pkg" / "sub").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("from pkg.target import Foo\n")
    (root / "pkg" / "target.py").write_text(
        '__all__ = ["Foo", "Bar"]\n\nclass Foo:\n    pass\n\nclass Bar:\n    pass\n'
    )
    (root / "pkg" / "user_abs.py").write_text("import pkg.target\n\nimport pkg.target\n")
    (root / "pkg" / "user_from.py").write_text("from pkg import target\n")
    (root / "pkg" / "sub" / "__init__.py").write_text("")
    (root / "pkg" / "sub" / "user_rel.py").write_text("from ..target import Bar\n")
    (root / "pkg" / "dyn.py").write_text(
        "import importlib\n"
        'mod = importlib.import_module("pkg.target")\n'
        "name = 'x'\n"
        "other = importlib.import_module(name)\n"
    )
    (root / "pkg" / "qual.py").write_text('REF = "pkg.target"  # no import here\n')
    (root / "pkg" / "broken.py").write_text("def broken(:\n")  # parse error
    (root / "other").mkdir()
    (root / "other" / "lonely.py").write_text("x = 1\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_target.py").write_text("import pkg.target\n")
    # registry + docs surfaces
    (root / "substrate").mkdir()
    (root / "substrate" / "canonical_types.py").write_text(
        'CANONICAL_TYPES = {\n    "Foo": ["pkg.target"],\n}\n'
    )
    (root / "ARCHITECTURE.md").write_text("The core module is pkg/target.py.\n")
    # excluded + sensitive files must never be scanned
    (root / "node_modules").mkdir()
    (root / "node_modules" / "evil.py").write_text("import pkg.target\n")
    (root / ".env").write_text("SECRET=import pkg.target\n")


def _scan(root: Path) -> ImportEvidenceResult:
    return scan_import_evidence(
        root, [CANDIDATE_A, CANDIDATE_B], run_id="R", activity_id="A", now="N"
    )


class TestDottedNames:
    def test_module_and_package_forms(self):
        assert module_dotted_name("pkg/target.py") == "pkg.target"
        assert module_dotted_name("pkg/__init__.py") == "pkg"


class TestStaticImportDetection:
    def test_all_import_forms_detected_with_sites(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            ev = res.evidence_by_path[CANDIDATE_A]
            importers = set(ev["static_importers"])
            assert "pkg/user_abs.py" in importers  # absolute import
            assert "pkg/user_from.py" in importers  # from-parent import
            assert "pkg/sub/user_rel.py" in importers  # relative import
            assert "pkg/__init__.py" in importers  # re-export
            assert "tests/test_target.py" in importers  # test reference
            # excluded/sensitive importers never appear
            assert not any("node_modules" in p for p in importers)
            # line sites are recorded with an explicit total
            imported_by = next(
                o
                for o in res.observations
                if o.subject == f"file:{CANDIDATE_A}" and o.predicate == "imported_by"
            )
            abs_entry = next(
                e for e in imported_by.value["importers"] if e["path"] == "pkg/user_abs.py"
            )
            assert abs_entry["site_count"] == 2 and abs_entry["line_sites"] == [1, 3]

    def test_reexport_and_test_classification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            imported_by = next(
                o
                for o in res.observations
                if o.subject == f"file:{CANDIDATE_A}" and o.predicate == "imported_by"
            )
            entries = {e["path"]: e for e in imported_by.value["importers"]}
            assert entries["pkg/__init__.py"]["re_export"] is True
            assert entries["tests/test_target.py"]["reference_class"] == "test_reference"
            assert entries["pkg/user_abs.py"]["reference_class"] == "code"
            ev = res.evidence_by_path[CANDIDATE_A]
            assert ev["test_reference_count"] == 1


class TestSymbolAndExports:
    def test_symbol_usage_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            sym = next(
                o
                for o in res.observations
                if o.subject == f"file:{CANDIDATE_A}" and o.predicate == "symbol_referenced_by"
            )
            assert "pkg/__init__.py" in sym.value["symbols"]["Foo"]
            assert "pkg/sub/user_rel.py" in sym.value["symbols"]["Bar"]

    def test_all_exports_declared(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            exp = next(
                o
                for o in res.observations
                if o.subject == f"file:{CANDIDATE_A}" and o.predicate == "declares_all_exports"
            )
            assert exp.value["names"] == ["Foo", "Bar"]


class TestDynamicAndQualified:
    def test_literal_dynamic_import_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            ev = res.evidence_by_path[CANDIDATE_A]
            assert ev["dynamic_import_count"] == 1

    def test_opaque_dynamic_import_counted_never_classified(self):
        """A non-literal import_module call makes dynamic absence unprovable —
        counted repo-wide, never treated as evidence of separation."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            assert res.accounting["opaque_dynamic_import_count"] == 1

    def test_qualified_textual_reference(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            ev = res.evidence_by_path[CANDIDATE_A]
            assert ev["qualified_reference_count"] >= 1
            qual = next(
                o
                for o in res.observations
                if o.subject == f"file:{CANDIDATE_A}" and o.predicate == "qualified_referenced_by"
            )
            assert "pkg/qual.py" in qual.value["files"]


class TestRegistriesAndDocs:
    def test_registry_and_doc_references(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            ev = res.evidence_by_path[CANDIDATE_A]
            assert "substrate.canonical_types" in ev["registries"]
            assert "ARCHITECTURE.md" in ev["doc_references"]

    def test_unreferenced_candidate_has_empty_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            ev = res.evidence_by_path[CANDIDATE_B]
            assert ev["static_importers"] == []
            assert ev["registries"] == []
            assert ev["dynamic_import_count"] == 0
            assert ev["doc_references"] == []
            assert ev["qualified_reference_count"] == 0
            assert ev["test_reference_count"] == 0


class TestRecordsAndIntegrity:
    def test_causal_record_only_for_imported_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            scopes = {c.scope for c in res.causal_records}
            assert f"file:{CANDIDATE_A}" in scopes
            assert f"file:{CANDIDATE_B}" not in scopes
            for c in res.causal_records:
                assert c.basis == "formal"
                assert c.method == "ast_static_import_scan"
                assert c.limitations  # never presented as unlimited proof

    def test_every_observation_resolves_to_the_scan_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            assert len(res.sources) == 1
            src_id = res.sources[0].id
            assert all(o.source_id == src_id for o in res.observations)
            assert res.sources[0].extraction_hash  # real derived payload hash
            assert res.sources[0].source_content_hash == ""

    def test_no_maturity_facet_on_relationship_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            assert all(o.maturity_facet is None for o in res.observations)

    def test_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            r1, r2 = _scan(root), _scan(root)
            assert [o.id for o in r1.observations] == [o.id for o in r2.observations]
            assert r1.sources[0].id == r2.sources[0].id

    def test_parse_error_tolerated_and_counted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_tree(root)
            res = _scan(root)
            assert res.accounting["parse_errors"] == 1  # pkg/broken.py
