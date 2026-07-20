"""Tests for the Grounded Self-Model evaluation (DOMAIN_RECONSTRUCTION_SPEC §15).

Covers: the §4.3 invariant check FAILS a planted declaration-only "supported"
claim; all 10 competency questions represented with valid answer_status;
tampered-artifact rejection (corrupt a source_id / delete an answer / plant a
laundered claim / leak a secret / break a convergence citation → criterion
FAIL and terminal FAILED where integrity is violated); acceptance-state
calculation (all-critical-pass → OPERATIONAL; one critical FAIL → not
OPERATIONAL; N/A never counted as a pass); mechanism-safety (basis-free /
experimental-without-method); convergence citations RESOLVED, not
pattern-matched; DQ3 rewards the ability to distinguish configured from
running, not the presence of a defect.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(os.environ.get("UMH_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(REPO_ROOT))

from substrate.understanding.reconstruction.builder import build_self_model  # noqa: E402
from substrate.understanding.reconstruction.competency_questions import (  # noqa: E402
    COMPETENCY_IDS,
)
from substrate.understanding.reconstruction.evaluation import (  # noqa: E402
    CRITICAL_CRITERIA,
    acceptance_vector,
    check_convergence_citations,
    check_decision_usefulness,
    check_mechanism_safety,
    check_no_design_as_implementation,
    check_structural,
    final_status,
    load_run,
)

# Reuse the builder test fixtures for a real, valid run.
from tests.test_reconstruction_builder import (  # noqa: E402
    _fake_inventory,
    _fake_preflight,
    _fake_probes_empty,
    _fake_import_evidence,
    _fake_probes_running,
    _fake_world_model,
    _synthetic_repo,
)


def _built_run(probes_fn=_fake_probes_running) -> Path:
    repo = _synthetic_repo()
    out = Path(tempfile.mkdtemp(prefix="adl-eval-")) / "self"
    result = build_self_model(
        repo_root=repo,
        output_root=out,
        run_id="run-eval-1",
        now="2026-07-19T00:00:00Z",
        inventory_fn=_fake_inventory,
        probes_fn=probes_fn,
        preflight_fn=_fake_preflight,
        world_model_fn=_fake_world_model,
        import_evidence_fn=_fake_import_evidence,
    )
    return Path(result.run_dir)


class TestInvariant43:
    def test_declaration_only_supported_claim_fails(self):
        """A 'supported' claim backed only by a declaration facet is a violation."""
        run = {
            "observations": [
                {
                    "id": "obs:1",
                    "maturity_facet": "declared",
                    "subject": "x",
                    "source_id": "s",
                },
            ],
            "claims": [
                {
                    "id": "c:1",
                    "status": "supported",
                    "supporting_observation_ids": ["obs:1"],
                }
            ],
        }
        res = check_no_design_as_implementation(run)
        assert not res["passed"]
        assert "c:1" in res["violations"]

    def test_supported_with_runtime_obs_passes(self):
        run = {
            "observations": [
                {
                    "id": "obs:1",
                    "maturity_facet": "running",
                    "subject": "x",
                    "source_id": "s",
                },
            ],
            "claims": [
                {
                    "id": "c:1",
                    "status": "supported",
                    "supporting_observation_ids": ["obs:1"],
                }
            ],
        }
        assert check_no_design_as_implementation(run)["passed"]


class TestMechanismSafety:
    def test_basis_free_causal_fails(self):
        run = {"model": {"causal": [{"id": "cs:1", "basis": ""}]}}
        assert not check_mechanism_safety(run)["passed"]

    def test_experimental_without_method_fails(self):
        run = {"model": {"causal": [{"id": "cs:1", "basis": "experimental", "method": ""}]}}
        assert not check_mechanism_safety(run)["passed"]

    def test_reported_basis_ok(self):
        run = {"model": {"causal": [{"id": "cs:1", "basis": "reported"}]}}
        assert check_mechanism_safety(run)["passed"]

    def test_no_causal_is_vacuously_safe(self):
        run = {"model": {}}
        assert check_mechanism_safety(run)["passed"]


class TestStructuralAndCompetency:
    def test_valid_run_structural_passes(self):
        run = load_run(_built_run())
        res = check_structural(run)
        assert res["passed"], res["findings"]

    def test_all_ten_questions_in_model_with_status(self):
        run = load_run(_built_run())
        qs = run["model"]["competency_questions"]
        qids = {q["question_id"] for q in qs}
        assert qids == set(COMPETENCY_IDS)
        assert all(q["answer_status"] in ("ANSWERED", "UNKNOWN") for q in qs)

    def test_missing_competency_question_fails_structural(self):
        rd = _built_run()
        model = json.loads((rd / "model.json").read_text())
        model["competency_questions"] = model["competency_questions"][:-1]  # drop one
        (rd / "model.json").write_text(json.dumps(model))
        run = load_run(rd)
        assert not check_structural(run)["passed"]

    def test_unknown_without_reason_fails_structural(self):
        rd = _built_run()
        model = json.loads((rd / "model.json").read_text())
        model["competency_questions"][0]["answer_status"] = "UNKNOWN"
        model["competency_questions"][0]["unknown_reason"] = ""
        (rd / "model.json").write_text(json.dumps(model))
        run = load_run(rd)
        assert not check_structural(run)["passed"]


class TestConvergenceCitations:
    def test_fresh_run_citations_resolve(self):
        run = load_run(_built_run())
        res = check_convergence_citations(run)
        assert res["passed"], res["unresolved"][:3]
        assert res["cited"] > 0

    def test_heading_alone_never_passes(self):
        """A 'Record ids' heading with zero resolvable tokens is a FAIL —
        the syntactic false positive the council flagged (V4.1 correction 7)."""
        rd = _built_run()
        (rd / "convergence.md").write_text(
            "# conv\n\n## Record ids\n- source ids: 5\n\nPROPOSAL: something\n"
        )
        run = load_run(rd)
        assert not check_convergence_citations(run)["passed"]

    def test_pure_intent_citations_never_pass(self):
        """Resolution alone is not enough: a convergence that cites only
        declaration-facet records is a pure-intent model (review finding 6)."""
        rd = _built_run()
        run = load_run(rd)
        declared_obs = next(o for o in run["observations"] if o.get("maturity_facet") == "declared")
        (rd / "convergence.md").write_text(f"# conv\n\n- finding [{declared_obs['id']}]\n")
        res = check_convergence_citations(load_run(rd))
        assert res["resolved"] == res["cited"] == 1  # it RESOLVES...
        assert res["grounded"] == 0  # ...but nothing is grounded
        assert not res["passed"]

    def test_unresolvable_citation_fails(self):
        rd = _built_run()
        text = (rd / "convergence.md").read_text()
        text += "\n- bogus finding [claimentry:" + "0" * 64 + "]\n"
        (rd / "convergence.md").write_text(text)
        run = load_run(rd)
        res = check_convergence_citations(run)
        assert not res["passed"]
        assert res["unresolved"]


class TestDecisionUsefulness:
    def test_dq4_seeds_alone_never_pass(self):
        """Seed fixtures are always emitted — DQ4 must require a mined or
        evidence-backed finding (review finding 2)."""
        run = load_run(_built_run(_fake_probes_running))
        seeds_only = [
            r
            for r in run["identities"]
            if r.get("candidate_basis") == "seed_fixture" and not r.get("supporting_evidence_ids")
        ]
        assert seeds_only, "fixture sanity: evidence-less seeds exist"
        stripped = dict(run)
        stripped["identities"] = seeds_only
        res = check_decision_usefulness(stripped)
        assert any("DQ4" in f for f in res["findings"])

    def test_dq3_requires_real_comparison_inputs(self):
        """A model with ZERO configured subjects cannot claim it distinguished
        configured from running (review finding 2)."""
        run = load_run(_built_run(_fake_probes_running))
        stripped = dict(run)
        stripped["divergence"] = {
            "divergences": [],
            "checks_performed": [
                {
                    "check": "deployment_configured_vs_running",
                    "status": "performed",
                    "compared_subjects": 0,
                }
            ],
        }
        res = check_decision_usefulness(stripped)
        assert any("DQ3" in f for f in res["findings"])

    def test_dq3_rewards_distinction_not_defect(self):
        """DQ3 passes because the configured-vs-running CHECK was performed —
        whether or not a mismatch exists (V4.1 correction 15)."""
        run = load_run(_built_run(_fake_probes_running))
        res = check_decision_usefulness(run)
        assert not any("DQ3" in f for f in res["findings"]), res["findings"]

    def test_all_five_answered_on_fresh_run(self):
        run = load_run(_built_run(_fake_probes_running))
        res = check_decision_usefulness(run)
        assert res["answered"] == res["total"], res["findings"]


class TestAcceptanceStates:
    def test_valid_run_is_not_failed(self):
        rd = _built_run(_fake_probes_running)
        vector = acceptance_vector(rd)
        status = final_status(vector)
        # No integrity/safety FAIL on a clean run.
        for name in (
            "no_design_as_implementation",
            "provenance_integrity",
            "evidence_refs_resolve",
            "append_preserving",
            "no_basis_free_causal",
            "no_secrets_emitted",
            "convergence_cites_ids",
        ):
            assert vector["criteria"][name] == "PASS", (name, vector["criteria"][name])
        assert status in (
            "OPERATIONAL",
            "PARTIALLY_OPERATIONAL",
            "INSUFFICIENT_EVIDENCE",
        )
        assert status != "FAILED"

    def test_na_not_counted_as_pass(self):
        rd = _built_run(_fake_probes_empty)
        vector = acceptance_vector(rd)
        # gates_clean_flag / targeted_tests_flag absent from manifest → N_A
        assert vector["criteria"]["gates_clean_flag"] == "N_A"
        assert "gates_clean_flag" in vector["not_applicable"]
        # N_A criteria excluded from the denominator
        assert vector["denominator"] == sum(1 for v in vector["criteria"].values() if v != "N_A")

    def test_operational_requires_all_critical_pass(self):
        criteria = {name: "PASS" for name in CRITICAL_CRITERIA}
        criteria["retrieval"] = "PASS"
        criteria["structural"] = "PASS"
        criteria["decision_usefulness"] = "PASS"
        vector = {
            "criteria": criteria,
            "detail": {"decision_usefulness": {"answered": 5, "total": 5}},
        }
        assert final_status(vector) == "OPERATIONAL"

    def test_one_critical_fail_is_not_operational(self):
        criteria = {name: "PASS" for name in CRITICAL_CRITERIA}
        criteria["convergence_cites_ids"] = "FAIL"  # critical
        vector = {
            "criteria": criteria,
            "detail": {"decision_usefulness": {"answered": 5, "total": 5}},
        }
        status = final_status(vector)
        assert status != "OPERATIONAL"

    def test_critical_na_blocks_operational(self):
        criteria = {name: "PASS" for name in CRITICAL_CRITERIA}
        criteria["gates_clean_flag"] = "N_A"  # N/A never counts as a pass
        vector = {
            "criteria": criteria,
            "detail": {"decision_usefulness": {"answered": 5, "total": 5}},
        }
        assert final_status(vector) != "OPERATIONAL"

    def test_integrity_fail_is_failed(self):
        criteria = {name: "PASS" for name in CRITICAL_CRITERIA}
        criteria["no_design_as_implementation"] = "FAIL"  # integrity/safety
        vector = {"criteria": criteria, "detail": {}}
        assert final_status(vector) == "FAILED"


class TestTamperedArtifacts:
    def test_corrupt_source_id_fails_acceptance(self):
        rd = _built_run()
        # Corrupt an observation's source_id so referential integrity breaks.
        obs_path = rd / "observations.jsonl"
        lines = [line for line in obs_path.read_text().splitlines() if line.strip()]
        first = json.loads(lines[0])
        first["source_id"] = "source:TAMPERED"
        lines[0] = json.dumps(first)
        obs_path.write_text("\n".join(lines) + "\n")
        vector = acceptance_vector(rd)
        assert (
            vector["criteria"]["evidence_refs_resolve"] == "FAIL"
            or vector["criteria"]["structural"] == "FAIL"
        )
        assert final_status(vector) == "FAILED"

    def test_tamper_detected_by_artifact_hashes(self):
        rd = _built_run()
        obs_path = rd / "observations.jsonl"
        obs_path.write_text(obs_path.read_text() + "\n")
        vector = acceptance_vector(rd)
        assert vector["criteria"]["artifact_hashes"] == "FAIL"

    def test_deleted_competency_answer_fails(self):
        rd = _built_run()
        model = json.loads((rd / "model.json").read_text())
        model["competency_questions"] = model["competency_questions"][:-2]
        (rd / "model.json").write_text(json.dumps(model))
        vector = acceptance_vector(rd)
        assert vector["criteria"]["ten_questions_answered_or_unknown"] == "FAIL"

    def test_planted_declaration_only_supported_claim_fails_acceptance(self):
        rd = _built_run()
        # Append a claim that laundered a declaration into 'supported'.
        obs_lines = [
            line for line in (rd / "observations.jsonl").read_text().splitlines() if line.strip()
        ]
        declared = next(
            json.loads(line)
            for line in obs_lines
            if json.loads(line).get("maturity_facet") == "declared"
        )
        claims_path = rd / "claims.jsonl"
        planted = {
            "id": "claimentry:PLANTED",
            "proposition": "x is operational",
            "claim_type": "component_status",
            "scope": "x",
            "status": "supported",
            "run_id": "run-eval-1",
            "supporting_observation_ids": [declared["id"]],
            "contradicting_observation_ids": [],
        }
        with open(claims_path, "a") as fh:
            fh.write(json.dumps(planted) + "\n")
        vector = acceptance_vector(rd)
        assert vector["criteria"]["no_design_as_implementation"] == "FAIL"
        assert final_status(vector) == "FAILED"

    def test_secret_leak_in_artifact_fails(self):
        rd = _built_run()
        (rd / "report.md").write_text("leak: api_key = 'sk-abcdefghijklmnopqrstuvwxyz'\n")
        vector = acceptance_vector(rd)
        assert vector["criteria"]["no_secrets_emitted"] == "FAIL"
        assert final_status(vector) == "FAILED"
