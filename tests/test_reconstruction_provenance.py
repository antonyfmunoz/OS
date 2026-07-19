"""Tests for reconstruction provenance & persistence primitives."""

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(os.environ.get("UMH_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(REPO_ROOT))

from substrate.understanding.reconstruction import provenance as P


class TestProvenance:
    def test_canonical_json_sorted_compact(self):
        assert P.canonical_json({"b": 1, "a": [3, 1]}) == '{"a":[3,1],"b":1}'

    def test_content_hash_bytes_and_str_agree(self):
        assert P.content_hash("hi") == P.content_hash(b"hi") == hashlib.sha256(b"hi").hexdigest()

    def test_file_sha256_matches_content_hash(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "f.bin")
            with open(p, "wb") as fh:
                fh.write(b"payload")
            assert P.file_sha256(p) == P.content_hash(b"payload")

    def test_activity_id_deterministic(self):
        a = P.ActivityRecord("extraction", "script:x", "r")
        b = P.ActivityRecord("extraction", "script:x", "r")
        assert a.id == b.id and a.id.startswith("activity:")

    def test_activity_id_stable_when_lineage_added(self):
        """The completed record (lineage populated) keeps the id that in-flight
        records already referenced (V4.1 correction 17)."""
        proto = P.ActivityRecord("acquisition", "script:x", "r", started_at="t0")
        done = P.ActivityRecord(
            "acquisition",
            "script:x",
            "r",
            started_at="t0",
            ended_at="t1",
            used_source_ids=("source:aaa",),
            generated_record_ids=("obs:bbb",),
        )
        assert proto.id == done.id
        d = done.to_dict()
        assert d["used_source_ids"] == ["source:aaa"]
        assert d["generated_record_ids"] == ["obs:bbb"]

    def test_jsonl_append_only_across_appenders(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "s.jsonl")
            P.JsonlAppender(p).append({"n": 1})
            P.JsonlAppender(p).append({"n": 2})
            assert [r["n"] for r in P.JsonlAppender(p).read_all()] == [1, 2]

    def test_atomic_write_replaces(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "m.json")
            P.atomic_write_json(p, {"v": 1})
            P.atomic_write_json(p, {"v": 2})
            with open(p) as fh:
                assert json.load(fh)["v"] == 2
            assert not any(n.startswith(".m.json.tmp") for n in os.listdir(td))

    def test_runlayout_lands_exactly_at_self_model_root(self):
        """RunLayout(run_id, self_model_root=X) → run dir X/runs/<id> — no path
        segments appended to X (V4.1 correction 1)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "data" / "world_models" / "self"
            rl = P.RunLayout("run0", self_model_root=root)
            assert rl.run_dir == root / "runs" / "run0"
            assert "data/world_models/self/data" not in rl.run_dir.as_posix()

    def test_runlayout_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "self"
            rl = P.RunLayout("run1", self_model_root=root).create()
            rl.appender("observations.jsonl").append({"x": 1})
            try:
                P.RunLayout("run1", self_model_root=root).create()
                assert False, "expected FileExistsError"
            except FileExistsError:
                pass
            P.RunLayout("run1", self_model_root=root).create(resume=True)

    def test_runlayout_artifact_paths(self):
        with tempfile.TemporaryDirectory() as td:
            rl = P.RunLayout("run2", self_model_root=Path(td) / "self")
            assert rl.path("manifest.json").name == "manifest.json"
            for a in P.RUN_ARTIFACTS:
                assert rl.path(a).parent == rl.run_dir
            try:
                rl.path("bogus.json")
                assert False
            except KeyError:
                pass

    def test_latest_pointer_atomic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "self"
            rl = P.RunLayout("run3", self_model_root=root).create()
            rl.update_latest_pointer()
            with open(root / "latest.json") as fh:
                latest = json.load(fh)
            assert latest["run_id"] == "run3"
            assert Path(latest["run_dir"]) == rl.run_dir

    def test_invalid_run_id_rejected(self):
        for bad in ("", "a/b", "..", "."):
            try:
                P.RunLayout(bad, self_model_root="/tmp/x")
                assert False, bad
            except ValueError:
                pass

    def test_appender_requires_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            rl = P.RunLayout("run4", self_model_root=Path(td) / "self").create()
            try:
                rl.appender("manifest.json")
                assert False
            except ValueError:
                pass
