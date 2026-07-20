"""Tests for the reconstruction repository-inventory acquisition module."""

import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(os.environ.get("UMH_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(REPO_ROOT))

from substrate.understanding.reconstruction.repository_inventory import (
    InventoryResult,
    inventory_repository,
    resolve_repository_commit,
)


def _build_synthetic_repo(root: Path) -> None:
    """A small tree: real files, an excluded __pycache__, an oversized file,
    and sensitive files that must never be fingerprinted."""
    (root / "substrate").mkdir(parents=True)
    (root / "substrate" / "mod.py").write_text("x = 1\n")
    (root / "substrate" / "helper.py").write_text("y = 2\n")
    (root / "docs").mkdir()
    (root / "docs" / "readme.md").write_text("# hi\n")
    (root / "config.json").write_text('{"a": 1}\n')
    # excluded cache subtree
    (root / "substrate" / "__pycache__").mkdir()
    (root / "substrate" / "__pycache__" / "mod.cpython-311.pyc").write_bytes(b"\x00\x01")
    # excluded vendored dep
    (root / "node_modules").mkdir()
    (root / "node_modules" / "left-pad.js").write_text("module.exports = 1\n")
    # oversized file (> tested threshold)
    (root / "big.bin").write_bytes(b"A" * 4096)
    # sensitive files — presence-only, never fingerprinted
    (root / ".env").write_text("SECRET_TOKEN=supersecretvalue123456789012345\n")
    (root / "server.key").write_text("-----BEGIN PRIVATE KEY-----\nfake\n")
    # code file whose NAME matches a sensitive prefix — must stay inventoried
    (root / "substrate" / "secrets_manager.py").write_text("z = 3\n")
    # the self-model's own output — must NEVER be re-ingested as evidence
    (root / "data" / "world_models" / "self" / "runs" / "old").mkdir(parents=True)
    (root / "data" / "world_models" / "self" / "runs" / "old" / "claims.jsonl").write_text(
        '{"id": "claimentry:prior"}\n'
    )
    # runtime-state boundary (Wave 0): live organism state — excluded as
    # runtime_state, never hashed/parsed/emitted as a SourceRecord
    (root / "data" / "runtime" / "umh" / "organism").mkdir(parents=True)
    (root / "data" / "runtime" / "umh" / "organism" / "events.jsonl").write_text(
        '{"event": "tick", "detail": "operational metadata"}\n'
    )
    # decoy: an ordinary `runtime` package dir must stay inventoried
    (root / "substrate" / "runtime").mkdir()
    (root / "substrate" / "runtime" / "adapter.py").write_text("r = 4\n")


class TestInventoryAccounting:
    def test_returns_inventory_result(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(
                root, run_id="R", activity_id="A", now="2026-07-19T00:00:00Z"
            )
            assert isinstance(res, InventoryResult)

    def test_totals_reconcile(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            acc = res.accounting
            total = acc["total_encountered_files"]
            excluded = sum(acc["excluded_by_category"].values())
            assert total == acc["inventoried"] + excluded
            assert acc["counts_reconcile"] is True

    def test_excludes_pycache_and_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            cats = res.accounting["excluded_by_category"]
            assert cats.get("cache", 0) >= 1
            assert cats.get("vendored_dependency", 0) >= 1
            # no source records for excluded files
            paths = {s.subject_path for s in res.sources}
            assert not any("__pycache__" in p for p in paths)
            assert not any("node_modules" in p for p in paths)

    def test_sensitive_files_presence_only_no_fingerprint(self):
        """.env / *.key are recorded present but carry NO hash, NO size, NO
        mtime — no fingerprint of any kind (V4.1 correction 12)."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            sensitive = [
                s for s in res.sources if s.metadata.get("path_class") == "sensitive_configuration"
            ]
            sensitive_paths = {s.subject_path for s in sensitive}
            assert ".env" in sensitive_paths
            assert "server.key" in sensitive_paths
            for s in sensitive:
                assert s.source_content_hash == ""
                assert s.redaction_status == "redacted"
                assert s.metadata.get("content_recorded") is False
                assert s.metadata.get("hash_recorded") is False
                assert "size_bytes" not in s.metadata
                assert "mtime" not in s.metadata
            assert res.accounting["sensitive_presence_only"] == len(sensitive)

    def test_sensitive_prefix_exempts_code_files(self):
        """secrets_manager.py is source code, not secret material — it must be
        inventoried and hashed normally (review finding 7)."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            sm = [s for s in res.sources if s.subject_path == "substrate/secrets_manager.py"]
            assert len(sm) == 1
            assert sm[0].metadata.get("path_class") != "sensitive_configuration"
            assert len(sm[0].source_content_hash) == 64

    def test_self_model_output_never_reingested(self):
        """data/world_models/ is the self-model's OWN output — re-hashing prior
        runs' artifacts would be a recursive evidence loop (review finding 1)."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            cats = res.accounting["excluded_by_category"]
            assert cats.get("self_model_output", 0) >= 1
            paths = {s.subject_path for s in res.sources}
            assert not any("world_models" in p for p in paths)
            assert res.accounting["counts_reconcile"] is True

    def test_runtime_state_excluded_never_evidence(self):
        """Wave 0 runtime-state boundary: data/runtime/** is live organism
        state — excluded as `runtime_state`, counted in accounting, never
        hashed/parsed/emitted as a repository-backed SourceRecord."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            cats = res.accounting["excluded_by_category"]
            assert cats.get("runtime_state", 0) >= 1
            paths = {s.subject_path for s in res.sources}
            assert not any(p.startswith("data/runtime") for p in paths)
            assert res.accounting["counts_reconcile"] is True

    def test_runtime_state_contents_do_not_alter_evidence_ids(self):
        """Mutating runtime state between runs must not change repository
        evidence: same sources, same hashes, same record identity inputs."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res1 = inventory_repository(root, run_id="R", activity_id="A", now="N")
            journal = root / "data" / "runtime" / "umh" / "organism" / "events.jsonl"
            journal.write_text('{"event": "different-now"}\n' * 50)
            (root / "data" / "runtime" / "umh" / "queue").mkdir(parents=True)
            (root / "data" / "runtime" / "umh" / "queue" / "queue.json").write_text("{}")
            res2 = inventory_repository(root, run_id="R", activity_id="A", now="N")
            ids1 = sorted((s.subject_path, s.source_content_hash) for s in res1.sources)
            ids2 = sorted((s.subject_path, s.source_content_hash) for s in res2.sources)
            assert ids1 == ids2
            assert res2.accounting["counts_reconcile"] is True

    def test_ordinary_runtime_package_dir_still_inventoried(self):
        """The exclusion is positional (data/runtime) — a normal `runtime`
        code package must remain inventoried."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            paths = {s.subject_path for s in res.sources}
            assert "substrate/runtime/adapter.py" in paths

    def test_oversized_file_gets_no_fake_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(
                root, run_id="R", activity_id="A", now="N", max_hash_bytes=1024
            )
            big = [s for s in res.sources if s.subject_path == "big.bin"]
            assert len(big) == 1
            assert big[0].source_content_hash == ""  # never a fabricated hash
            assert big[0].metadata.get("hash_skipped") == "oversized"
            # a small file within the (default) budget IS hashed with real bytes
            small = [s for s in res.sources if s.subject_path.endswith("mod.py")]
            assert small and all(len(s.source_content_hash) == 64 for s in small)

    def test_aggregate_is_derived_not_label_hashed(self):
        """The aggregate source carries extraction/derivation hashes of the
        actual derived payload — never a label hash posing as acquired bytes
        (V4.1 correction 5)."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            agg = [s for s in res.sources if s.source_kind == "derived_artifact"]
            assert len(agg) == 1
            assert agg[0].source_content_hash == ""
            assert len(agg[0].extraction_hash) == 64
            assert agg[0].derivation_activity_id == "A"

    def test_git_unavailable_handled(self):
        # Fresh tempdir is NOT a git repo → git calls fail → tracked=None,
        # git_tracked/untracked both 0, explicit note recorded, no crash.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            acc = res.accounting
            assert acc["git_available"] is False
            assert acc["git_tracked"] == 0
            assert acc["git_untracked"] == 0
            assert any("git_unavailable" in n for n in acc["notes"])
            # git_tracked metadata is None (never guessed) when git is unavailable
            for s in res.sources:
                if s.metadata.get("path_class") == "sensitive_configuration":
                    continue
                if s.source_kind == "derived_artifact":
                    continue
                assert s.metadata.get("git_tracked") is None
            # commit status is explicit, never guessed
            for s in res.sources:
                assert s.repository_commit_status == "unavailable"

    def test_preflight_resolves_unavailable_in_non_repo(self):
        with tempfile.TemporaryDirectory() as d:
            head, status, dirty = resolve_repository_commit(d)
            assert head is None
            assert status == "unavailable"
            assert dirty is None

    def test_determinism_identical_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            r1 = inventory_repository(root, run_id="R", activity_id="A", now="N")
            r2 = inventory_repository(root, run_id="R", activity_id="A", now="N")
            ids1 = [s.id for s in r1.sources]
            ids2 = [s.id for s in r2.sources]
            assert ids1 == ids2  # stable ordering AND stable ids
            oids1 = [o.id for o in r1.observations]
            oids2 = [o.id for o in r2.observations]
            assert oids1 == oids2

    def test_surface_observations_only_for_py_under_surface_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            # per-file source_present observations only for substrate/*.py
            per_file = [o for o in res.observations if o.predicate == "source_present"]
            subjects = {o.subject for o in per_file}
            assert "file:substrate/mod.py" in subjects
            assert "file:substrate/helper.py" in subjects
            # docs/readme.md is NOT python → no per-file source_present obs
            assert not any("readme" in s for s in subjects)
            # aggregate package observation present for substrate
            agg = [o for o in res.observations if o.predicate == "python_files_present"]
            agg_subjects = {o.subject: o.value for o in agg}
            # mod.py, helper.py, secrets_manager.py + runtime/adapter.py decoy
            assert agg_subjects.get("package:substrate") == 4
            assert all(o.observation_kind == "aggregate_count" for o in agg)

    def test_all_observations_are_source_present_never_overasserted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            # inventory NEVER asserts runtime facets — only source_present
            for o in res.observations:
                assert o.maturity_facet == "source_present"

    def test_artifact_freshness_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N")
            fresh = res.accounting["artifact_freshness"]
            # neither artifact exists in the synthetic repo
            assert fresh["codebase_graph"]["present"] is False
            assert fresh["codewiki_manifest"]["present"] is False


class TestInventoryBounding:
    def test_max_paths_cap_bounds_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _build_synthetic_repo(root)
            res = inventory_repository(root, run_id="R", activity_id="A", now="N", max_paths=1)
            assert res.accounting["inventoried"] >= 1
            assert res.accounting["counts_reconcile"] is True
            assert any("path_cap_reached" in n for n in res.accounting["notes"])
