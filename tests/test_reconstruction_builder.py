"""Tests for the Grounded Self-Model builder (DOMAIN_RECONSTRUCTION_SPEC §15).

Covers: maturity-vector derivation; documented-vs-implemented separation (a
compose-configured fake service never gets a running facet); all 10 competency
questions represented with structured answers; canonical_owner claim mining
(narrow declaration rule); identity candidates (remain_separate only with
evidence, else unresolved; deterministic basename mining); run-dir semantics
(output_root/runs/<id> exactly); manifest artifact hashes; builder end-to-end
against a SYNTHETIC tempdir repo with fake inventory/probes/preflight injected
— fast, no real repo scan, no subprocess.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(os.environ.get("UMH_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(REPO_ROOT))

from substrate.understanding.reconstruction.builder import (  # noqa: E402
    _parse_component_status,
    _parse_compose_services,
    build_self_model,
    record_run_outcomes,
)
from substrate.understanding.reconstruction.competency_questions import (  # noqa: E402
    COMPETENCY_IDS,
)
from substrate.understanding.reconstruction.contracts import (  # noqa: E402
    ObservationRecord,
    RUNTIME_FACETS,
    SourceRecord,
)

CLAUDE_MD = """\
# header

## Component status (phase X)
Status taxonomy:
  CONFIRMED_RUNTIME  — imports clean

- substrate/types.py                     — CONFIRMED_RUNTIME (single type system)
- substrate/organism/canonical_runtime.py — CONFIRMED_RUNTIME (WP-P1-001: declares the one canonical operation runtime)
- substrate/foo/dormant.py               — DORMANT (not imported by anything live)

## Current build phase
next section
"""

COMPOSE = """\
networks:
  eos_network:
    driver: bridge

services:
  os-scraper:
    build: .
    container_name: os-scraper
  os-discord:
    build: .
  os-operator:
    build: .
"""


def _synthetic_repo() -> Path:
    d = Path(tempfile.mkdtemp(prefix="adl-repo-"))
    (d / ".claude").mkdir()
    (d / ".claude" / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")
    (d / "docker-compose.yml").write_text(COMPOSE, encoding="utf-8")
    return d


def _fake_preflight(repo_root):
    return "abc123def456", "resolved", False


class _FakeCap:
    provided_by = "file:substrate/types.py"
    name = "type_system"


class _FakeEntity:
    module_path = "file:substrate/types.py"
    name = "types"
    category = "module"
    status = "active"
    capabilities = [_FakeCap()]


class _FakeWorldModel:
    entities = {"e1": _FakeEntity()}
    gaps = []


def _fake_world_model(repo_root):
    """Deterministic world-model fake (review finding 4: the extractor is now
    an injectable seam, so tests never touch the live extractor)."""
    return _FakeWorldModel()


def _fake_inventory(repo_root, run_id, activity_id):
    class InventoryResult:
        pass

    src = SourceRecord(
        subject_path="substrate/types.py",
        source_kind="repository_file",
        modality="code",
        source_content_hash="deadbeef",
        activity_id=activity_id,
        run_id=run_id,
    )
    obs = ObservationRecord(
        subject="file:substrate/types.py",
        predicate="source_present",
        value=True,
        observation_kind="maturity",
        maturity_facet="source_present",
        source_id=src.id,
        run_id=run_id,
    )
    # a mined-duplicate candidate pair for the identity step
    dup_a = SourceRecord(
        subject_path="substrate/organism/gateway.py",
        source_kind="repository_file",
        modality="code",
        source_content_hash="cafe01",
        activity_id=activity_id,
        run_id=run_id,
    )
    dup_b = SourceRecord(
        subject_path="substrate/understanding/gateway.py",
        source_kind="repository_file",
        modality="code",
        source_content_hash="cafe02",
        activity_id=activity_id,
        run_id=run_id,
    )
    r = InventoryResult()
    r.sources = (src, dup_a, dup_b)
    r.observations = (obs,)
    r.accounting = {
        "total_encountered_files": 5,
        "inventoried": 3,
        "excluded_by_category": {},
        "by_language": {"python": 3},
        "git_tracked": 3,
        "git_untracked": 0,
    }
    return r


def _fake_probes_empty(run_id, activity_id, repo_root="/opt/OS"):
    """No runtime evidence available — thin runtime coverage, never fabricated."""

    class ProbeCollection:
        pass

    r = ProbeCollection()
    r.sources = ()
    r.observations = ()
    r.probe_results = (
        {
            "name": "docker_services",
            "available": False,
            "exit_status": None,
            "observed_at": None,
            "error": "docker not available",
            "redaction_applied": False,
        },
    )
    return r


def _fake_probes_running(run_id, activity_id, repo_root="/opt/OS"):
    """One genuine runtime observation of a running process."""

    class ProbeCollection:
        pass

    src = SourceRecord(
        subject_path="probe:docker_services",
        source_kind="runtime_probe",
        modality="runtime_probe",
        source_content_hash="livehash",
        activity_id=activity_id,
        run_id=run_id,
        probe_name="docker_services",
    )
    obs = ObservationRecord(
        subject="service:os-discord",
        predicate="container_status",
        value="Up 3 hours",
        observation_kind="maturity",
        maturity_facet="running",
        source_id=src.id,
        run_id=run_id,
    )
    r = ProbeCollection()
    r.sources = (src,)
    r.observations = (obs,)
    r.probe_results = (
        {
            "name": "docker_services",
            "available": True,
            "exit_status": 0,
            "observed_at": "t",
            "error": None,
            "redaction_applied": False,
        },
    )
    return r


class TestParsers:
    def test_component_status_parse(self):
        rows = _parse_component_status(CLAUDE_MD)
        assert len(rows) == 3
        paths = [r["path"] for r in rows]
        assert "substrate/types.py" in paths
        assert rows[-1]["status"] == "DORMANT"

    def test_compose_services_parse(self):
        svcs = _parse_compose_services(COMPOSE)
        assert svcs == ["os-scraper", "os-discord", "os-operator"]
        # network keys must NOT leak in as services
        assert "eos_network" not in svcs


class TestBuildEndToEnd:
    def _build(self, probes_fn, run_id="run-test-1"):
        repo = _synthetic_repo()
        out = Path(tempfile.mkdtemp(prefix="adl-out-")) / "self"
        result = build_self_model(
            repo_root=repo,
            output_root=out,
            run_id=run_id,
            now="2026-07-19T00:00:00Z",
            inventory_fn=_fake_inventory,
            probes_fn=probes_fn,
            preflight_fn=_fake_preflight,
            world_model_fn=_fake_world_model,
        )
        return result, Path(result.run_dir), out

    def test_run_dir_is_exactly_output_root_runs_id(self):
        """V4.1 correction 1: run lands at <output_root>/runs/<run_id>."""
        result, run_dir, out = self._build(_fake_probes_empty)
        assert run_dir == out / "runs" / "run-test-1"
        assert "self/data/world_models" not in run_dir.as_posix()

    def test_build_produces_all_artifacts(self):
        result, run_dir, _ = self._build(_fake_probes_empty)
        for name in (
            "manifest.json",
            "sources.jsonl",
            "observations.jsonl",
            "claims.jsonl",
            "activities.jsonl",
            "identity_resolutions.jsonl",
            "model.json",
            "coverage.json",
            "divergence.json",
            "acceptance.json",
            "convergence.md",
            "report.md",
        ):
            assert (run_dir / name).exists(), f"missing artifact {name}"

    def test_preflight_commit_on_every_repo_source(self):
        """V4.1 correction 4: HEAD resolved before any record; every
        repository-backed source carries it."""
        _, run_dir, _ = self._build(_fake_probes_empty)
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["repository_commit"] == "abc123def456"
        assert manifest["repository_commit_status"] == "resolved"
        sources = [
            json.loads(line)
            for line in (run_dir / "sources.jsonl").read_text().splitlines()
            if line.strip()
        ]
        declared = [
            s for s in sources if s["subject_path"] in (".claude/CLAUDE.md", "docker-compose.yml")
        ]
        assert declared
        for s in declared:
            assert s["repository_commit"] == "abc123def456"
            assert s["repository_commit_status"] == "resolved"

    def test_manifest_has_artifact_hashes(self):
        """V4.1 correction 18: finalized manifest carries per-artifact hashes."""
        _, run_dir, _ = self._build(_fake_probes_empty)
        manifest = json.loads((run_dir / "manifest.json").read_text())
        hashes = manifest.get("artifact_hashes", {})
        assert "claims.jsonl" in hashes and "convergence.md" in hashes
        # acceptance.json is the evaluation OF the artifacts — excluded from
        # the hash set so the stored vector can verify the hashes (finding 3)
        assert "acceptance.json" not in hashes
        assert "manifest.json" not in hashes
        assert "previous_run_manifest_hash" in manifest

    def test_acceptance_contains_final_status(self):
        """V4.1 correction 21."""
        result, run_dir, _ = self._build(_fake_probes_empty)
        acceptance = json.loads((run_dir / "acceptance.json").read_text())
        assert acceptance.get("final_status") == result.status
        # finding 3: hashes are finalized BEFORE acceptance, so the STORED
        # vector verifies them — never a permanent N_A disagreement
        assert acceptance["criteria"]["artifact_hashes"] == "PASS"
        assert result.status in (
            "OPERATIONAL",
            "PARTIALLY_OPERATIONAL",
            "INSUFFICIENT_EVIDENCE",
            "FAILED",
        )

    def test_fresh_build_never_failed_on_integrity(self):
        """A genuinely fresh build must not FAIL its own integrity checks
        (the candidate payload's ordering defect made this impossible)."""
        result, run_dir, _ = self._build(_fake_probes_empty)
        assert result.status != "FAILED", result.acceptance["criteria"]
        crit = result.acceptance["criteria"]
        assert crit["evidence_refs_resolve"] == "PASS"
        assert crit["provenance_integrity"] == "PASS"
        assert crit["no_design_as_implementation"] == "PASS"
        assert crit["convergence_cites_ids"] == "PASS"

    def test_all_ten_competency_questions_structured(self):
        """V4.1 correction 6: structured answers with answer_status + items."""
        _, run_dir, _ = self._build(_fake_probes_empty)
        model = json.loads((run_dir / "model.json").read_text())
        qs = model["competency_questions"]
        qids = {q["question_id"] for q in qs}
        assert qids == set(COMPETENCY_IDS)
        for q in qs:
            assert q["answer_status"] in ("ANSWERED", "UNKNOWN")
            if q["answer_status"] == "UNKNOWN":
                assert q["unknown_reason"]
        # CQ1 items carry subjects + record ids, not counts
        cq1 = next(q for q in qs if q["question_id"] == "CQ1")
        assert cq1["answer_status"] == "ANSWERED"
        assert any(
            i["subject"] == "file:substrate/types.py" and i["claim_id"] for i in cq1["items"]
        )
        # CQ5 (tested) is an explicit evidence gap in v1
        cq5 = next(q for q in qs if q["question_id"] == "CQ5")
        assert cq5["answer_status"] == "UNKNOWN"
        assert "contract-only" in cq5["unknown_reason"]

    def test_canonical_owner_claim_mined_narrowly(self):
        """V4.1 correction 16: canonical ownership is an explicit claim type,
        emitted only for a literal 'declares the one canonical X runtime'."""
        _, run_dir, _ = self._build(_fake_probes_empty)
        claims = [
            json.loads(line)
            for line in (run_dir / "claims.jsonl").read_text().splitlines()
            if line.strip()
        ]
        owners = [c for c in claims if c["claim_type"] == "canonical_owner"]
        assert len(owners) == 1
        assert owners[0]["object_ref"] == "substrate/organism/canonical_runtime.py"
        assert owners[0]["scope"] == "operation_runtime"
        assert owners[0]["status"] == "proposed"  # declaration-only evidence
        # CQ6 answers from these claims
        model = json.loads((run_dir / "model.json").read_text())
        cq6 = next(q for q in model["competency_questions"] if q["question_id"] == "CQ6")
        assert cq6["answer_status"] == "ANSWERED"
        assert cq6["items"][0]["declared_owner"] == owners[0]["object_ref"]

    def test_model_json_indexes_not_full_ledger(self):
        """V4.1 correction 20: claims.jsonl is authoritative; model.json holds
        indexes + the ledger artifact hash."""
        _, run_dir, _ = self._build(_fake_probes_empty)
        model = json.loads((run_dir / "model.json").read_text())
        assert "claims" not in model  # no full-record duplication
        assert model["claim_index"]
        assert model["ledger_artifact"]["path"] == "claims.jsonl"
        assert len(model["ledger_artifact"]["sha256"]) == 64

    def test_configured_service_never_running_without_probe(self):
        """A compose-configured service gets deployment_configured but not running."""
        _, run_dir, _ = self._build(_fake_probes_empty)
        obs = [
            json.loads(line)
            for line in (run_dir / "observations.jsonl").read_text().splitlines()
            if line.strip()
        ]
        discord = [o for o in obs if o["subject"] == "service:os-discord"]
        assert discord, "expected a service:os-discord observation"
        facets = {o["maturity_facet"] for o in discord}
        assert "deployment_configured" in facets
        assert not (facets & RUNTIME_FACETS), "config must never yield a runtime facet"

    def test_maturity_vector_separates_documented_from_running(self):
        """With a live probe, os-discord gains 'running'; types.py stays source-only."""
        _, run_dir, _ = self._build(_fake_probes_running)
        obs = [
            json.loads(line)
            for line in (run_dir / "observations.jsonl").read_text().splitlines()
            if line.strip()
        ]
        discord_facets = {o["maturity_facet"] for o in obs if o["subject"] == "service:os-discord"}
        types_facets = {
            o["maturity_facet"] for o in obs if o["subject"] == "file:substrate/types.py"
        }
        assert "running" in discord_facets  # observed running
        assert "deployment_configured" in discord_facets  # still configured
        # types.py is declared + present in source, but never observed at runtime.
        assert "source_present" in types_facets
        assert "declared" in types_facets
        assert not (types_facets & RUNTIME_FACETS)

    def test_declared_component_claim_is_not_supported(self):
        """A component_status claim rests on a declaration facet → 'proposed'."""
        _, run_dir, _ = self._build(_fake_probes_empty)
        claims = [
            json.loads(line)
            for line in (run_dir / "claims.jsonl").read_text().splitlines()
            if line.strip()
        ]
        comp = [c for c in claims if c["claim_type"] == "component_status"]
        assert comp, "expected component_status claims"
        assert all(c["status"] == "proposed" for c in comp)

    def test_identity_seeds_and_mining(self):
        """Seeds carry evidence-or-unresolved; mined candidates are unresolved
        with candidate_basis mined:duplicate_basename (V4.1 correction 10)."""
        _, run_dir, _ = self._build(_fake_probes_empty)
        idents = [
            json.loads(line)
            for line in (run_dir / "identity_resolutions.jsonl").read_text().splitlines()
            if line.strip()
        ]
        by_pair = {tuple(r["candidate_entity_ids"]): r for r in idents}
        # council pair: no documented evidence → unresolved, no evidence ids
        council = tuple(
            sorted(
                {
                    "substrate/organism/council.py",
                    "substrate/understanding/deliberation/council.py",
                }
            )
        )
        assert by_pair[council]["verdict"] == "unresolved"
        assert by_pair[council]["supporting_evidence_ids"] == []
        assert by_pair[council]["candidate_basis"] == "seed_fixture"
        # mined pair from the fake inventory (gateway.py duplicated)
        mined = tuple(
            sorted(
                {
                    "substrate/organism/gateway.py",
                    "substrate/understanding/gateway.py",
                }
            )
        )
        assert by_pair[mined]["verdict"] == "unresolved"
        assert by_pair[mined]["candidate_basis"] == "mined:duplicate_basename"
        # synthetic repo has no rule files → seeds with missing rule downgrade
        wm = tuple(
            sorted(
                {
                    "substrate/organism/world_model.py",
                    "substrate/understanding/world_model/world_model.py",
                }
            )
        )
        assert by_pair[wm]["verdict"] == "unresolved"
        assert "not found at build time" in by_pair[wm]["rationale"]

    def test_thin_runtime_coverage_reported_not_fabricated(self):
        _, run_dir, _ = self._build(_fake_probes_empty)
        coverage = json.loads((run_dir / "coverage.json").read_text())
        assert coverage["thin_areas"], "empty probes must mark runtime coverage thin"
        per_facet = coverage["per_facet_observation_counts"]
        assert not (set(per_facet) & RUNTIME_FACETS), "no runtime facets fabricated"
        assert coverage["contract_only_regions"]

    def test_deterministic_repeat_same_ids(self):
        """Same repo + same fakes → identical record ids (content-hashed)."""
        repo = _synthetic_repo()
        out1 = Path(tempfile.mkdtemp(prefix="adl-det1-")) / "self"
        out2 = Path(tempfile.mkdtemp(prefix="adl-det2-")) / "self"
        kwargs = dict(
            run_id="run-det",
            now="2026-07-19T00:00:00Z",
            inventory_fn=_fake_inventory,
            probes_fn=_fake_probes_empty,
            preflight_fn=_fake_preflight,
            world_model_fn=_fake_world_model,
        )
        r1 = build_self_model(repo_root=repo, output_root=out1, **kwargs)
        r2 = build_self_model(repo_root=repo, output_root=out2, **kwargs)
        obs1 = sorted(
            line
            for line in (Path(r1.run_dir) / "observations.jsonl").read_text().splitlines()
            if line.strip()
        )
        obs2 = sorted(
            line
            for line in (Path(r2.run_dir) / "observations.jsonl").read_text().splitlines()
            if line.strip()
        )
        assert obs1 == obs2

    def test_divergence_flags_configured_not_running_and_check_recorded(self):
        _, run_dir, _ = self._build(_fake_probes_empty)
        div = json.loads((run_dir / "divergence.json").read_text())
        classes = {d["class"] for d in div["divergences"]}
        assert "deployment_configured_but_not_observed_running" in classes
        # each divergence names its closing evidence + cites record ids
        for d in div["divergences"]:
            assert d["closing_evidence"]
            assert d.get("claim_ids") or d.get("observation_ids") or d.get("subject")
        # DQ3 evidence: the configured-vs-running CHECK is recorded as performed
        checks = {c["check"]: c["status"] for c in div["checks_performed"]}
        assert checks.get("deployment_configured_vs_running") == "performed"
        # not-computable regions are explicit, not silent
        assert any(str(v).startswith("not_computable") for v in checks.values())

    def test_activities_carry_lineage(self):
        """V4.1 correction 17: completed activities carry generated lineage."""
        _, run_dir, _ = self._build(_fake_probes_empty)
        acts = [
            json.loads(line)
            for line in (run_dir / "activities.jsonl").read_text().splitlines()
            if line.strip()
        ]
        assert acts
        assert any(a["generated_record_ids"] for a in acts)
        # every source's activity_id resolves to a recorded activity
        act_ids = {a["id"] for a in acts}
        sources = [
            json.loads(line)
            for line in (run_dir / "sources.jsonl").read_text().splitlines()
            if line.strip()
        ]
        for s in sources:
            assert s["activity_id"] in act_ids

    def test_record_run_outcomes_mechanism(self):
        """V4.1 correction 22: outcomes recorded via the supported mechanism,
        never manual artifact editing; acceptance + hashes recomputed."""
        result, run_dir, _ = self._build(_fake_probes_empty)
        vector = record_run_outcomes(run_dir, gates_clean=True, targeted_tests_passed=True)
        manifest = json.loads((run_dir / "manifest.json").read_text())
        assert manifest["gates_clean"] is True
        assert manifest["targeted_tests_passed"] is True
        assert vector["criteria"]["gates_clean_flag"] == "PASS"
        assert vector["criteria"]["targeted_tests_flag"] == "PASS"
        acceptance = json.loads((run_dir / "acceptance.json").read_text())
        assert acceptance["criteria"]["gates_clean_flag"] == "PASS"
        assert "final_status" in acceptance
