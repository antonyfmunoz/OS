"""Sprint 4 — Data/Log Hygiene verification.

Validates:
  - Runtime JSONL logs are gitignored
  - data/runtime/ is gitignored
  - JSONL rotation utility works correctly
  - Rotation is wired into TraceStore and MemoryCandidateGenerator
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT") or "/opt/OS")

REPO = Path(__file__).resolve().parents[1]


class TestGitignoreCoversRuntimeData:
    SHOULD_BE_IGNORED = [
        "data/orchestrator_log.jsonl",
        "data/control_plane_log.jsonl",
        "data/persistent_agents_log.jsonl",
        "data/workflow_log.jsonl",
        "data/harness_log.jsonl",
        "data/optimizer_proposals.jsonl",
        "data/advisor_log.jsonl",
        "data/improvement_log.jsonl",
        "data/umh/traces/traces.jsonl",
        "data/umh/memory_candidates/candidates.jsonl",
        "data/runtime/canonical_memory_store/memories.jsonl",
        "data/runtime/actuator_maturity_proofs/some_proof.json",
    ]

    @pytest.mark.parametrize("path", SHOULD_BE_IGNORED)
    def test_file_is_gitignored(self, path: str):
        result = subprocess.run(
            ["git", "check-ignore", "-q", path],
            cwd=str(REPO),
            capture_output=True,
        )
        assert result.returncode == 0, f"{path} is NOT gitignored"

    def test_config_jsonl_not_ignored(self):
        result = subprocess.run(
            ["git", "check-ignore", "-q", "data/config/loop_definitions.jsonl"],
            cwd=str(REPO),
            capture_output=True,
        )
        assert result.returncode != 0, "config JSONL should NOT be gitignored"


class TestJsonlRotation:
    def test_no_rotation_under_threshold(self, tmp_path: Path):
        from substrate.observability.jsonl_rotation import rotate_if_needed

        f = tmp_path / "test.jsonl"
        for i in range(100):
            f.open("a").write(json.dumps({"i": i}) + "\n")

        result = rotate_if_needed(f, max_lines=5000)
        assert result is None
        assert f.exists()

    def test_rotation_over_threshold(self, tmp_path: Path):
        from substrate.observability.jsonl_rotation import rotate_if_needed

        f = tmp_path / "test.jsonl"
        for i in range(200):
            f.open("a").write(json.dumps({"i": i}) + "\n")

        result = rotate_if_needed(f, max_lines=100)
        assert result is not None
        assert result.exists()
        assert "archive" in str(result.parent)
        assert f.exists()
        assert f.stat().st_size == 0

    def test_rotation_nonexistent_file(self, tmp_path: Path):
        from substrate.observability.jsonl_rotation import rotate_if_needed

        result = rotate_if_needed(tmp_path / "nope.jsonl")
        assert result is None

    def test_rotation_preserves_content(self, tmp_path: Path):
        from substrate.observability.jsonl_rotation import rotate_if_needed

        f = tmp_path / "test.jsonl"
        lines = [json.dumps({"i": i}) + "\n" for i in range(50)]
        f.write_text("".join(lines))

        archive = rotate_if_needed(f, max_lines=10)
        assert archive is not None
        archived_lines = archive.read_text().strip().split("\n")
        assert len(archived_lines) == 50


class TestRotationWiredIn:
    def test_trace_store_imports_rotation(self):
        import substrate.observability.trace_store as ts
        assert hasattr(ts, "rotate_if_needed")

    def test_candidate_generator_imports_rotation(self):
        import substrate.memory.candidate_generator as cg
        assert hasattr(cg, "rotate_if_needed")

    def test_error_recorder_imports_rotation(self):
        import substrate.observability.error_recorder as er
        assert hasattr(er, "rotate_if_needed")
