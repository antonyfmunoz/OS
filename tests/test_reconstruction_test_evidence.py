"""Tests for v1.2 execution-backed test evidence (plugin + ingestion + facets).

Covers the amendment's fixture matrix: two-dimension outcome normalization
(incl. strict/non-strict XPASS, setup/teardown errors), registered-marker-only
classification, facet derivation gates (§6 — static imports never qualify,
stale commits inert, unknown class never facets), artifact rejection (schema /
plugin_error / dirty / stale / malformed), builder integration (run copy +
manifest hashes + structured CQ5 PARTIALLY_ANSWERED), acceptance integrity
(dynamic-critical test_evidence_integrity, backward compatibility for
pre-v1.2 runs, tamper rejection), and a pytester black-box pass over the real
plugin loaded by its production dotted path in a SUBPROCESS (no in-process
pytest.main reuse — module caching would contaminate repeated runs).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(os.environ.get("UMH_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(REPO_ROOT))

from substrate.understanding.reconstruction import test_evidence as TE  # noqa: E402
from substrate.understanding.reconstruction.builder import build_self_model  # noqa: E402
from substrate.understanding.reconstruction.evaluation import (  # noqa: E402
    acceptance_vector,
    check_test_evidence,
    final_status,
)
from tests.test_reconstruction_builder import (  # noqa: E402
    _fake_import_evidence,
    _fake_inventory,
    _fake_preflight,
    _fake_probes_empty,
    _fake_world_model,
    _synthetic_repo,
)

pytest_plugins = ["pytester"]

BUILD_COMMIT = "abc123def456"  # matches _fake_preflight


def _phase(outcome, **extra):
    return {"outcome": outcome, "duration": 0.001, **extra}


def _make_artifact(
    *,
    commit: str = BUILD_COMMIT,
    dirty: str = "false",
    executions: dict | None = None,
    collected: list | None = None,
    **overrides,
):
    executions = executions or {
        "tests/test_x.py::test_ok": {
            "phases": {
                "setup": _phase("passed"),
                "call": _phase("passed"),
                "teardown": _phase("passed"),
            }
        }
    }
    if collected is None:
        collected = [
            {"nodeid": n, "path": "tests/test_x.py", "markers": [], "parametrized": False}
            for n in executions
        ]
    artifact = {
        "schema_version": "test-evidence-v1",
        "plugin_version": "umh-pytest-evidence-v1",
        "session": {
            "pytest_version": "9.0.2",
            "python_version": "3.12.3",
            "started_at": "2026-07-20T00:00:00Z",
            "finished_at": "2026-07-20T00:00:05Z",
            "exit_status": 0,
            "injected": {
                "repository_commit": commit,
                "repository_dirty": dirty,
                "repository_fingerprint": "fp",
                "selection_template_id": "reconstruction-spine-v1",
                "expected_schema_version": "test-evidence-v1",
            },
            "selection_manifest": {"template_id": "reconstruction-spine-v1", "args": []},
        },
        "collected": collected,
        "deselected_after_collection": [],
        "collection_errors": [],
        "executions": executions,
        "plugin_error": None,
    }
    artifact.update(overrides)
    return artifact


def _write_artifact(artifact: dict) -> Path:
    d = Path(tempfile.mkdtemp(prefix="adl-te-"))
    p = d / "artifact.json"
    p.write_text(json.dumps(artifact, sort_keys=True), encoding="utf-8")
    return p


# ── outcome normalization (two dimensions, phases preserved) ────────────────


class TestNormalization:
    def test_ordinary_pass(self):
        n = TE.normalize_execution(
            {"setup": _phase("passed"), "call": _phase("passed"), "teardown": _phase("passed")}
        )
        assert n["semantic_outcome"] == "passed" and n["session_effect"] == "pass"

    def test_call_failure(self):
        n = TE.normalize_execution(
            {"setup": _phase("passed"), "call": _phase("failed"), "teardown": _phase("passed")}
        )
        assert n["semantic_outcome"] == "failed" and n["session_effect"] == "fail"

    def test_skip_at_setup(self):
        n = TE.normalize_execution({"setup": _phase("skipped"), "teardown": _phase("passed")})
        assert n["semantic_outcome"] == "skipped" and n["session_effect"] == "neutral"
        assert n["phase_outcomes"]["call"] == "not_run"

    def test_expected_xfail_is_neutral(self):
        n = TE.normalize_execution(
            {
                "setup": _phase("passed"),
                "call": _phase("skipped", wasxfail=True, wasxfail_reason="known bug"),
                "teardown": _phase("passed"),
            }
        )
        assert n["semantic_outcome"] == "xfailed" and n["session_effect"] == "neutral"
        assert n["wasxfail_reason"] == "known bug"

    def test_nonstrict_xpass_passes_session(self):
        n = TE.normalize_execution(
            {
                "setup": _phase("passed"),
                "call": _phase("passed", wasxfail=True),
                "teardown": _phase("passed"),
            }
        )
        assert n["semantic_outcome"] == "xpassed" and n["session_effect"] == "pass"
        assert n["strict_xfail_effect"] == "false"

    def test_strict_xpass_fails_session(self):
        n = TE.normalize_execution(
            {
                "setup": _phase("passed"),
                "call": _phase("failed", detail="[XPASS(strict)] should fail"),
                "teardown": _phase("passed"),
            }
        )
        assert n["semantic_outcome"] == "xpassed" and n["session_effect"] == "fail"
        assert n["strict_xfail_effect"] == "true"

    def test_setup_error(self):
        n = TE.normalize_execution({"setup": _phase("failed"), "teardown": _phase("passed")})
        assert n["semantic_outcome"] == "error" and n["session_effect"] == "fail"
        assert n["phase_outcomes"]["call"] == "not_run"

    def test_teardown_failure_after_pass_is_error_with_phases_intact(self):
        n = TE.normalize_execution(
            {"setup": _phase("passed"), "call": _phase("passed"), "teardown": _phase("failed")}
        )
        assert n["semantic_outcome"] == "error" and n["session_effect"] == "fail"
        assert n["phase_outcomes"] == {"setup": "passed", "call": "passed", "teardown": "failed"}

    def test_teardown_failure_after_fail_stays_failed(self):
        n = TE.normalize_execution(
            {"setup": _phase("passed"), "call": _phase("failed"), "teardown": _phase("failed")}
        )
        assert n["semantic_outcome"] == "failed" and n["session_effect"] == "fail"


# ── classification (registered markers only) ────────────────────────────────


class TestClassification:
    def test_integration_marker(self):
        assert TE.classify_test(["integration"]) == (
            "integration",
            "registered_marker:integration",
        )

    def test_unmarked_is_unknown(self):
        assert TE.classify_test([]) == ("unknown", "no_registered_class_marker")

    def test_smoke_is_not_a_class_marker(self):
        cls, _ = TE.classify_test(["smoke", "asyncio"])
        assert cls == "unknown"


# ── facet derivation gates ──────────────────────────────────────────────────


def _exec(
    nodeid="tests/test_x.py::test_ok",
    semantic="passed",
    effect="pass",
    cls="integration",
    basis="registered_marker:integration",
    commit=BUILD_COMMIT,
):
    return {
        "nodeid": nodeid,
        "semantic_outcome": semantic,
        "session_effect": effect,
        "classification": cls,
        "classification_basis": basis,
        "commit": commit,
    }


def _derive(executions, exercise_map, commit=BUILD_COMMIT):
    return TE.derive_tested_facets(
        executions, exercise_map, build_commit=commit, run_id="R", source_id="source:x", now="N"
    )


class TestFacetDerivation:
    MAP = {
        "tests/test_x.py::test_ok": {
            "components": ["substrate/types.py"],
            "basis": "coverage_context",
        }
    }

    def test_qualifying_integration_pass_derives_facet(self):
        out = _derive([_exec()], self.MAP)
        assert len(out["facets"]) == 1
        f = out["facets"][0]
        assert f.maturity_facet == "integration_tested"
        assert f.support["mapping_basis"] == "coverage_context"
        assert "never general correctness" in f.value["proof_scope"]

    def test_unknown_class_never_facets(self):
        out = _derive([_exec(cls="unknown", basis="no_registered_class_marker")], self.MAP)
        assert out["facets"] == []
        assert any("class_not_evidence_backed" in r["reason"] for r in out["rejections"])

    def test_static_import_basis_never_qualifies(self):
        static_map = {
            "tests/test_x.py::test_ok": {
                "components": ["substrate/types.py"],
                "basis": "static_import",
            }
        }
        out = _derive([_exec()], static_map)
        assert out["facets"] == []
        assert any("mapping_basis_not_qualifying" in r["reason"] for r in out["rejections"])

    def test_failed_execution_never_facets(self):
        out = _derive([_exec(semantic="failed", effect="fail")], self.MAP)
        assert out["facets"] == []

    def test_xpassed_never_facets(self):
        out = _derive([_exec(semantic="xpassed", effect="pass")], self.MAP)
        assert out["facets"] == []

    def test_skipped_never_facets(self):
        out = _derive([_exec(semantic="skipped", effect="neutral")], self.MAP)
        assert out["facets"] == []

    def test_stale_commit_inert(self):
        out = _derive([_exec(commit="feedface0000")], self.MAP)
        assert out["facets"] == []
        assert any(r["reason"] == "stale_or_unresolved_commit" for r in out["rejections"])

    def test_no_mapping_no_facet_with_named_gap(self):
        out = _derive([_exec()], None)
        assert out["facets"] == []
        assert out["component_mapping_status"] == TE.component_mapping_status()
        assert any(r["reason"] == "no_qualifying_component_mapping" for r in out["rejections"])

    def test_unit_class_supported_by_pure_function(self):
        # The derivation is general: a repo that REGISTERS a unit marker gets
        # unit_tested — this repo does not, so real runs can never reach it.
        out = _derive([_exec(cls="unit", basis="registered_marker:unit")], self.MAP)
        assert out["facets"] and out["facets"][0].maturity_facet == "unit_tested"


# ── artifact ingestion ──────────────────────────────────────────────────────


class TestIngestion:
    def _ingest(self, artifact_path, commit=BUILD_COMMIT):
        return TE.ingest_test_report(artifact_path, "R", "A", build_commit=commit, now="N")

    def test_valid_artifact_ingests_executions(self):
        p = _write_artifact(_make_artifact())
        out = self._ingest(p)
        assert out["qualification"]["valid"] is True
        kinds = {o.observation_kind for o in out["observations"]}
        assert kinds == {"test_execution", "test_collection"}
        ex = next(o for o in out["observations"] if o.observation_kind == "test_execution")
        assert ex.maturity_facet is None  # execution evidence != maturity
        assert ex.value["semantic_outcome"] == "passed"

    def test_failed_tests_are_valid_counterevidence(self):
        art = _make_artifact(
            executions={
                "tests/test_x.py::test_bad": {
                    "phases": {"setup": _phase("passed"), "call": _phase("failed")}
                }
            }
        )
        art["session"]["exit_status"] = 1
        out = self._ingest(_write_artifact(art))
        assert out["qualification"]["valid"] is True  # qualification != test outcome
        ex = next(o for o in out["observations"] if o.observation_kind == "test_execution")
        assert ex.value["semantic_outcome"] == "failed"

    def test_malformed_report_rejected(self):
        d = Path(tempfile.mkdtemp())
        p = d / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        out = self._ingest(p)
        assert out["qualification"]["valid"] is False
        assert "malformed_report" in out["qualification"]["reasons"]
        assert out["executions"] == []

    def test_unsupported_schema_rejected(self):
        out = self._ingest(_write_artifact(_make_artifact(schema_version="test-evidence-v99")))
        assert not out["qualification"]["valid"]
        assert any("unsupported_schema" in r for r in out["qualification"]["reasons"])

    def test_plugin_error_rejected(self):
        out = self._ingest(
            _write_artifact(_make_artifact(plugin_error={"stage": "x", "message": "boom"}))
        )
        assert not out["qualification"]["valid"]
        assert "plugin_error_present" in out["qualification"]["reasons"]

    def test_stale_commit_rejected(self):
        out = self._ingest(_write_artifact(_make_artifact(commit="feedface0000")))
        assert not out["qualification"]["valid"]
        assert "stale_commit" in out["qualification"]["reasons"]
        # rejection is explicit, not silent
        assert any(o.predicate == "report_rejected" for o in out["observations"])
        assert not any(o.observation_kind == "test_execution" for o in out["observations"])

    def test_dirty_tree_rejected(self):
        out = self._ingest(_write_artifact(_make_artifact(dirty="true")))
        assert not out["qualification"]["valid"]
        assert any(r.startswith("repository_dirty") for r in out["qualification"]["reasons"])

    def test_unknown_dirty_state_rejected(self):
        out = self._ingest(_write_artifact(_make_artifact(dirty="unknown")))
        assert not out["qualification"]["valid"]

    def test_missing_report(self):
        out = self._ingest(Path(tempfile.mkdtemp()) / "nope.json")
        assert out["qualification"]["reasons"] == ["report_missing"]
        assert out["source"] is None

    def test_missing_session_fields_rejected(self):
        art = _make_artifact()
        del art["session"]["started_at"]
        out = self._ingest(_write_artifact(art))
        assert any("missing_session_field" in r for r in out["qualification"]["reasons"])


# ── inventory (candidate links only) ────────────────────────────────────────


class TestInventory:
    def _repo_with_tests(self):
        d = Path(tempfile.mkdtemp(prefix="adl-inv-"))
        (d / "tests").mkdir()
        (d / "tests" / "test_a.py").write_text(
            "import substrate.types\nfrom adapters.models import model_router\n"
        )
        (d / "tests" / "test_broken.py").write_text("def broken(:\n")
        (d / "tests" / "helper.py").write_text("import substrate.types\n")  # not a test file
        return d

    def test_candidate_links_are_never_facets(self):
        d = self._repo_with_tests()
        sources, obs, acc = TE.scan_test_inventory(d, "R", "A", now="N")
        assert acc["inventory_discovered"] == 2  # helper.py excluded
        assert acc["inventory_parse_errors"] == 1
        links = [o for o in obs if o.observation_kind == "test_reference"]
        assert len(links) == 1
        link = links[0]
        assert link.maturity_facet is None
        assert link.value["relationship_strength"] == "candidate"
        assert "substrate.types" in link.value["targets"]
        # real bytes hash on the source record
        src = next(s for s in sources if s.subject_path == "tests/test_a.py")
        assert len(src.source_content_hash) == 64


# ── builder integration ─────────────────────────────────────────────────────


def _build(test_artifact_path=None, run_id="run-te-1", test_evidence_fn=None):
    repo = _synthetic_repo()
    out = Path(tempfile.mkdtemp(prefix="adl-te-out-")) / "self"
    kwargs = {}
    if test_evidence_fn is not None:
        kwargs["test_evidence_fn"] = test_evidence_fn
    result = build_self_model(
        repo_root=repo,
        output_root=out,
        run_id=run_id,
        now="2026-07-20T00:00:00Z",
        inventory_fn=_fake_inventory,
        probes_fn=_fake_probes_empty,
        preflight_fn=_fake_preflight,
        world_model_fn=_fake_world_model,
        import_evidence_fn=_fake_import_evidence,
        test_artifact_path=test_artifact_path,
        **kwargs,
    )
    return result, Path(result.run_dir)


class TestBuilderIntegration:
    def test_run_copy_and_manifest_block(self):
        artifact = _write_artifact(_make_artifact())
        result, run_dir = _build(artifact)
        copy = run_dir / "test_report.json"
        assert copy.is_file()
        assert copy.read_bytes() == artifact.read_bytes()  # byte-identical copy
        manifest = json.loads((run_dir / "manifest.json").read_text())
        te = manifest["test_evidence"]
        assert te["valid"] is True
        assert te["original_plugin_artifact_sha256"] == te["run_copy_sha256"]
        assert len(te["run_copy_sha256"]) == 64
        assert te["artifact_commit"] == BUILD_COMMIT
        assert te["parsed_semantic_record_hash"]
        # run copy participates in artifact hashing
        assert "test_report.json" in manifest["artifact_hashes"]
        assert result.counts["test_executions"] == 1
        assert result.counts["tested_facets"] == 0  # no qualifying mapping source

    def test_cq5_partially_answered_with_council_language(self):
        artifact = _write_artifact(_make_artifact())
        _, run_dir = _build(artifact)
        model = json.loads((run_dir / "model.json").read_text())
        cq5 = next(q for q in model["competency_questions"] if q["question_id"] == "CQ5")
        assert cq5["answer_status"] == "PARTIALLY_ANSWERED"
        assert cq5["partial_reason"] == (
            "Test execution and outcome evidence are available. No component "
            "receives a unit_tested or integration_tested facet because no "
            "qualifying component-exercise mapping source is installed or "
            "canonically declared."
        )
        assert cq5["items"] and cq5["cited_record_ids"]
        assert cq5["summary"]["component_mapping_status"] == TE.component_mapping_status()

    def test_acceptance_integrity_pass_and_dynamically_critical(self):
        artifact = _write_artifact(_make_artifact())
        _, run_dir = _build(artifact)
        vector = acceptance_vector(run_dir)
        assert vector["criteria"]["test_evidence_integrity"] == "PASS"
        assert "test_evidence_integrity" in vector["critical_criteria"]
        assert final_status(vector) != "FAILED"

    def test_rejected_artifact_recorded_not_ingested(self):
        artifact = _write_artifact(_make_artifact(commit="feedface0000"))
        result, run_dir = _build(artifact, run_id="run-te-stale")
        manifest = json.loads((run_dir / "manifest.json").read_text())
        te = manifest["test_evidence"]
        assert te["valid"] is False and "stale_commit" in te["rejection_reasons"]
        assert result.counts["test_executions"] == 0
        # rejection does not FAIL the run — it is honest thin evidence
        vector = acceptance_vector(run_dir)
        assert vector["criteria"]["test_evidence_integrity"] == "PASS"

    def test_no_artifact_backward_compatible(self):
        _, run_dir = _build(None, run_id="run-te-none")
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert "test_evidence" not in manifest
        vector = acceptance_vector(run_dir)
        assert vector["criteria"]["test_evidence_integrity"] == "N_A"
        assert "test_evidence_integrity" not in vector["critical_criteria"]


# ── acceptance integrity: tamper + inflation + backward compat ──────────────


class TestAcceptanceIntegrity:
    def test_tampered_run_copy_fails(self):
        artifact = _write_artifact(_make_artifact())
        _, run_dir = _build(artifact, run_id="run-te-tamper")
        copy = run_dir / "test_report.json"
        data = json.loads(copy.read_text())
        data["executions"]["tests/test_x.py::test_forged"] = {"phases": {"call": _phase("passed")}}
        copy.write_text(json.dumps(data, sort_keys=True))
        vector = acceptance_vector(run_dir)
        assert vector["criteria"]["test_evidence_integrity"] == "FAIL"
        assert final_status(vector) == "FAILED"

    def test_declared_but_missing_report_fails(self):
        artifact = _write_artifact(_make_artifact())
        _, run_dir = _build(artifact, run_id="run-te-missing")
        (run_dir / "test_report.json").unlink()
        vector = acceptance_vector(run_dir)
        assert vector["criteria"]["test_evidence_integrity"] == "FAIL"
        assert final_status(vector) == "FAILED"

    def test_execution_obs_without_declaration_fails(self):
        run = {
            "run_dir": Path(tempfile.mkdtemp()),
            "manifest": {"repository_commit": BUILD_COMMIT},
            "observations": [
                {
                    "id": "obs:" + "0" * 64,
                    "observation_kind": "test_execution",
                    "predicate": "test_execution",
                    "value": {
                        "nodeid": "t::x",
                        "semantic_outcome": "passed",
                        "session_effect": "pass",
                        "phase_outcomes": {
                            "setup": "passed",
                            "call": "passed",
                            "teardown": "passed",
                        },
                        "commit": BUILD_COMMIT,
                    },
                    "source_id": "source:" + "0" * 64,
                }
            ],
        }
        res = check_test_evidence(run)
        assert res["applicable"] and not res["passed"]
        assert any("no manifest test_evidence block" in f for f in res["findings"])

    def test_facet_without_qualifying_basis_fails(self):
        # Inject a forged tested facet via a fake seam that launders a static
        # reference into integration_tested — acceptance must kill it.
        from substrate.understanding.reconstruction.contracts import (
            ObservationRecord,
            SourceRecord,
        )

        def forging_seam(repo_root, run_id, activity_id, artifact_path, commit, status, now):
            src = SourceRecord(
                subject_path="run:test_report.json",
                source_kind="derived_artifact",
                modality="derived",
                activity_id=activity_id,
                run_id=run_id,
                source_content_hash="f" * 64,
            )
            forged = ObservationRecord(
                subject="file:substrate/types.py",
                predicate="tested_by",
                value={"nodeid": "t::x"},
                observation_kind="tested_facet",
                maturity_facet="integration_tested",
                source_id=src.id,
                run_id=run_id,
                support={
                    "derived_from_execution": "t::x",
                    "mapping_basis": "static_import",  # NOT qualifying
                    "classification": "integration",
                    "classification_basis": "registered_marker:integration",
                },
            )

            class R:
                sources = (src,)
                observations = ()
                facet_observations = (forged,)
                accounting = {"component_mapping_status": "synthetic_fixture"}
                qualification = {"valid": True, "reasons": [], "artifact_commit": commit}
                artifact = {"schema_version": "test-evidence-v1"}

            return R()

        _, run_dir = _build(None, run_id="run-te-forge", test_evidence_fn=forging_seam)
        vector = acceptance_vector(run_dir)
        assert vector["criteria"]["test_evidence_integrity"] == "FAIL"
        assert final_status(vector) == "FAILED"

    def test_pre_v12_run_shape_is_na(self):
        # Authentic pre-v1.2 run shape: no test_evidence manifest block, no
        # test-evidence observation kinds (regression fixture, amendment H).
        run = {
            "run_dir": Path(tempfile.mkdtemp()),
            "manifest": {"run_id": "run-old", "repository_commit": "x" * 12},
            "observations": [
                {
                    "id": "obs:" + "1" * 64,
                    "observation_kind": "maturity",
                    "maturity_facet": "source_present",
                    "predicate": "source_present",
                    "value": True,
                    "source_id": "source:" + "1" * 64,
                }
            ],
        }
        res = check_test_evidence(run)
        assert res["applicable"] is False


# ── plugin black-box (pytester, subprocess — production dotted path) ────────


class TestPluginBlackBox:
    def _env(self, monkeypatch, out_path, commit=BUILD_COMMIT, dirty="false"):
        monkeypatch.setenv("UMH_TEST_EVIDENCE_OUT", str(out_path))
        monkeypatch.setenv("UMH_TEST_EVIDENCE_COMMIT", commit)
        monkeypatch.setenv("UMH_TEST_EVIDENCE_DIRTY", dirty)
        monkeypatch.setenv("UMH_TEST_EVIDENCE_FINGERPRINT", "fp-test")
        monkeypatch.setenv("UMH_TEST_EVIDENCE_TEMPLATE", "blackbox")
        monkeypatch.setenv("UMH_TEST_EVIDENCE_SCHEMA", "test-evidence-v1")
        monkeypatch.setenv("PYTHONPATH", str(REPO_ROOT))

    def test_full_lifecycle_semantics(self, pytester, monkeypatch):
        pytester.makepyfile(
            test_mini="""
            import pytest

            def test_ok():
                assert True

            def test_bad():
                assert False

            @pytest.mark.skip(reason="TOKEN=abcdefghijklmnopqrstuvwxyz012345")
            def test_skipped():
                pass

            @pytest.mark.xfail(reason="known")
            def test_xfail():
                assert False

            @pytest.mark.xfail(reason="surprise")
            def test_xpass_nonstrict():
                assert True

            @pytest.mark.xfail(strict=True, reason="must fail")
            def test_xpass_strict():
                assert True

            @pytest.mark.parametrize("v", [1, 2])
            def test_param(v):
                assert v > 0

            @pytest.fixture
            def broken_setup():
                raise RuntimeError("setup boom")

            def test_setup_error(broken_setup):
                pass

            @pytest.fixture
            def broken_teardown():
                yield 1
                raise RuntimeError("teardown boom")

            def test_teardown_error(broken_teardown):
                assert broken_teardown == 1

            @pytest.mark.integration
            def test_marked_integration():
                assert True
            """
        )
        pytester.makeini("[pytest]\nmarkers =\n    integration: x\n")
        out = pytester.path / "evidence.json"
        self._env(monkeypatch, out)
        result = pytester.runpytest_subprocess(
            "-p", TE.PLUGIN_MODULE, "-q", "-p", "no:cacheprovider"
        )
        assert out.is_file(), result.stderr.str()
        artifact = json.loads(out.read_text())
        assert artifact["schema_version"] == "test-evidence-v1"
        assert artifact["plugin_error"] is None
        assert artifact["session"]["injected"]["repository_commit"] == BUILD_COMMIT
        assert artifact["session"]["started_at"] and artifact["session"]["finished_at"]

        execs = artifact["executions"]

        def norm(name):
            nodeid = f"test_mini.py::{name}"
            return TE.normalize_execution(execs[nodeid]["phases"])

        assert norm("test_ok")["semantic_outcome"] == "passed"
        assert norm("test_bad")["semantic_outcome"] == "failed"
        assert norm("test_skipped")["semantic_outcome"] == "skipped"
        assert norm("test_xfail")["semantic_outcome"] == "xfailed"
        assert norm("test_xfail")["session_effect"] == "neutral"
        xp = norm("test_xpass_nonstrict")
        assert xp["semantic_outcome"] == "xpassed" and xp["session_effect"] == "pass"
        xps = norm("test_xpass_strict")
        assert xps["semantic_outcome"] == "xpassed" and xps["session_effect"] == "fail"
        se = norm("test_setup_error")
        assert se["semantic_outcome"] == "error" and se["phase_outcomes"]["call"] == "not_run"
        te_err = norm("test_teardown_error")
        assert te_err["semantic_outcome"] == "error"
        assert te_err["phase_outcomes"]["call"] == "passed"
        assert "test_mini.py::test_param[1]" in execs  # parametrized nodeids
        # redaction: the skip-reason token never lands in the artifact
        raw = out.read_text()
        assert "abcdefghijklmnopqrstuvwxyz012345" not in raw
        # collected markers captured for classification downstream
        collected = {c["nodeid"]: c for c in artifact["collected"]}
        assert "integration" in collected["test_mini.py::test_marked_integration"]["markers"]

    def test_noop_when_env_unset(self, pytester, monkeypatch):
        for var in (
            "UMH_TEST_EVIDENCE_OUT",
            "UMH_TEST_EVIDENCE_COMMIT",
            "UMH_TEST_EVIDENCE_DIRTY",
        ):
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("PYTHONPATH", str(REPO_ROOT))
        pytester.makepyfile(test_one="def test_ok():\n    assert True\n")
        result = pytester.runpytest_subprocess(
            "-p", TE.PLUGIN_MODULE, "-q", "-p", "no:cacheprovider"
        )
        result.assert_outcomes(passed=1)
        assert not list(pytester.path.glob("*.json"))

    def test_deselection_recorded(self, pytester, monkeypatch):
        pytester.makepyfile(test_sel="def test_keep():\n    pass\n\ndef test_drop():\n    pass\n")
        out = pytester.path / "evidence.json"
        self._env(monkeypatch, out)
        pytester.runpytest_subprocess(
            "-p", TE.PLUGIN_MODULE, "-q", "-p", "no:cacheprovider", "-k", "keep"
        )
        artifact = json.loads(out.read_text())
        assert artifact["deselected_after_collection"] == ["test_sel.py::test_drop"]
        assert "test_sel.py::test_keep" in artifact["executions"]
        assert "test_sel.py::test_drop" not in artifact["executions"]

    def test_collection_error_recorded(self, pytester, monkeypatch):
        pytester.makepyfile(test_broken="import nonexistent_module_xyz\n")
        out = pytester.path / "evidence.json"
        self._env(monkeypatch, out)
        pytester.runpytest_subprocess("-p", TE.PLUGIN_MODULE, "-q", "-p", "no:cacheprovider")
        artifact = json.loads(out.read_text())
        assert artifact["collection_errors"]
        assert artifact["executions"] == {}

    def test_repeated_invocations_isolated(self, pytester, monkeypatch):
        pytester.makepyfile(test_r1="def test_a():\n    pass\n")
        out1 = pytester.path / "e1.json"
        out2 = pytester.path / "e2.json"
        self._env(monkeypatch, out1)
        pytester.runpytest_subprocess("-p", TE.PLUGIN_MODULE, "-q", "-p", "no:cacheprovider")
        monkeypatch.setenv("UMH_TEST_EVIDENCE_OUT", str(out2))
        pytester.runpytest_subprocess("-p", TE.PLUGIN_MODULE, "-q", "-p", "no:cacheprovider")
        a1, a2 = json.loads(out1.read_text()), json.loads(out2.read_text())
        # each artifact reflects exactly one session — no accumulation
        assert len(a1["executions"]) == len(a2["executions"]) == 1
