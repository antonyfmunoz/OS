"""Tests for leverage_assimilation — external framework ingestion and scoring."""

import json
import tempfile
from pathlib import Path

import pytest

from substrate.organism.leverage_assimilation import (
    ArtifactType,
    AssimilationArtifact,
    AssimilationStatus,
    ExtractedPrimitive,
    LeverageAssimilator,
    LeverageScore,
    PrimitiveType,
)


class TestLeverageScore:
    def test_default_score(self):
        score = LeverageScore()
        assert score.composite == pytest.approx(0.35, abs=0.01)

    def test_high_score(self):
        score = LeverageScore(
            uniqueness=1.0,
            applicability=1.0,
            implementation_cost=0.0,
            risk=0.0,
        )
        assert score.composite == pytest.approx(1.0, abs=0.01)

    def test_to_dict(self):
        score = LeverageScore(uniqueness=0.8, applicability=0.6)
        d = score.to_dict()
        assert "uniqueness" in d
        assert "composite" in d
        assert d["uniqueness"] == 0.8


class TestExtractedPrimitive:
    def test_auto_id(self):
        prim = ExtractedPrimitive(name="test")
        assert prim.id.startswith("prim-")

    def test_to_dict(self):
        prim = ExtractedPrimitive(
            name="test_pattern",
            primitive_type=PrimitiveType.PATTERN,
            description="A test pattern",
            source_artifact="art-123",
        )
        d = prim.to_dict()
        assert d["name"] == "test_pattern"
        assert d["primitive_type"] == "pattern"
        assert d["source_artifact"] == "art-123"


class TestAssimilationArtifact:
    def test_auto_id(self):
        art = AssimilationArtifact(name="test")
        assert art.id.startswith("art-")

    def test_leverage_summary_empty(self):
        art = AssimilationArtifact(name="test")
        summary = art.leverage_summary
        assert summary["count"] == 0

    def test_leverage_summary_with_primitives(self):
        art = AssimilationArtifact(name="test")
        art.primitives = [
            ExtractedPrimitive(
                name="p1",
                leverage=LeverageScore(uniqueness=0.8, applicability=0.6),
            ),
            ExtractedPrimitive(
                name="p2",
                leverage=LeverageScore(uniqueness=0.4, applicability=0.3),
            ),
        ]
        summary = art.leverage_summary
        assert summary["count"] == 2
        assert summary["avg_score"] > 0
        assert summary["max_score"] >= summary["avg_score"]


class TestAssimilatorIngest:
    def test_ingest_creates_artifact(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("cortextOS", source_url="https://github.com/example/cortextos")
        assert art.name == "cortextOS"
        assert art.status == AssimilationStatus.STAGED
        assert art.id in [a["id"] for a in assimilator.list_artifacts()]

    def test_ingest_with_content(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("test", content="hello world content")
        staging_file = tmp_path / "assim" / "staging" / f"{art.id}.txt"
        assert staging_file.exists()
        assert staging_file.read_text() == "hello world content"


class TestAssimilatorClassify:
    def test_classify_agent_system(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("cortextOS multi-agent orchestration")
        result = assimilator.classify(art.id)
        assert result == ArtifactType.AGENT_SYSTEM

    def test_classify_pattern_library(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("claude.md best practices pattern library")
        result = assimilator.classify(art.id)
        assert result == ArtifactType.PATTERN_LIBRARY

    def test_classify_runtime_system(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("codex runtime system")
        result = assimilator.classify(art.id)
        assert result == ArtifactType.RUNTIME_SYSTEM

    def test_classify_unknown(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("completely abstract concept xyz")
        result = assimilator.classify(art.id)
        assert result == ArtifactType.UNKNOWN

    def test_classify_nonexistent(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        result = assimilator.classify("nonexistent")
        assert result == ArtifactType.UNKNOWN


class TestAssimilatorExtract:
    def test_extract_with_provided_primitives(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("test")
        assimilator.classify(art.id)

        primitives = [
            {"name": "lifecycle_mgmt", "type": "protocol", "description": "Agent lifecycle"},
            {"name": "task_queue", "type": "pattern", "description": "Task queue pattern"},
        ]
        result = assimilator.extract_primitives(art.id, primitives=primitives)
        assert len(result) == 2
        assert result[0].name == "lifecycle_mgmt"
        assert result[0].primitive_type == PrimitiveType.PROTOCOL

    def test_extract_heuristic_agent_system(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("multi-agent orchestration")
        assimilator.classify(art.id)
        result = assimilator.extract_primitives(art.id)
        assert len(result) == 3
        assert any("lifecycle" in p.name for p in result)

    def test_extract_heuristic_runtime_system(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("codex runtime system")
        assimilator.classify(art.id)
        result = assimilator.extract_primitives(art.id)
        assert len(result) == 2

    def test_extract_nonexistent(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        result = assimilator.extract_primitives("nonexistent")
        assert result == []


class TestAssimilatorRedundancy:
    def test_detect_novel_primitives(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("test")
        assimilator.classify(art.id)
        assimilator.extract_primitives(art.id, primitives=[
            {"name": "completely_novel_xyz", "type": "pattern", "description": "Something brand new"},
        ])
        report = assimilator.detect_redundancy(art.id)
        assert len(report["novel"]) >= 1

    def test_detect_redundant_primitives(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("test")
        assimilator.classify(art.id)
        assimilator.extract_primitives(art.id, primitives=[
            {"name": "heartbeat_monitoring", "type": "pattern", "description": "heartbeat monitoring pattern"},
        ])
        report = assimilator.detect_redundancy(art.id)
        assert len(report["redundant"]) >= 1 or len(report["partial_overlap"]) >= 1

    def test_detect_redundancy_nonexistent(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        result = assimilator.detect_redundancy("nonexistent")
        assert "error" in result


class TestAssimilatorScoring:
    def test_score_leverage(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("test")
        assimilator.classify(art.id)
        assimilator.extract_primitives(art.id, primitives=[
            {"name": "novel_pattern", "type": "pattern", "description": "Something new"},
            {"name": "novel_protocol", "type": "protocol", "description": "New protocol"},
        ])
        assimilator.detect_redundancy(art.id)
        scored = assimilator.score_leverage(art.id)
        assert len(scored) == 2
        assert scored[0]["leverage"]["composite"] >= scored[1]["leverage"]["composite"]

    def test_score_nonexistent(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        assert assimilator.score_leverage("nonexistent") == []


class TestAssimilatorMapping:
    def test_map_to_umh(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("test")
        assimilator.classify(art.id)
        assimilator.extract_primitives(art.id, primitives=[
            {"name": "adapter_impl", "type": "adapter", "description": "Adapter pattern"},
            {"name": "workflow_step", "type": "workflow", "description": "Workflow step"},
        ])
        mapping = assimilator.map_to_umh(art.id)
        assert len(mapping) == 2
        adapter_prim = art.primitives[0]
        assert mapping[adapter_prim.id] == "substrate/organism/runtime_adapters.py"


class TestFullPipeline:
    def test_full_pipeline(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        result = assimilator.full_pipeline(
            "cortextOS agent orchestration",
            source_url="https://github.com/example/cortextos",
            content="Multi-agent system with lifecycle management",
        )
        assert "artifact" in result
        assert result["artifact"]["artifact_type"] == "agent_system"
        assert "redundancy" in result
        assert "scored_primitives" in result
        assert len(result["scored_primitives"]) > 0
        assert "umh_mapping" in result

    def test_full_pipeline_with_explicit_primitives(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        result = assimilator.full_pipeline(
            "karpathy claude.md patterns",
            primitives=[
                {"name": "system_prompt_structure", "type": "config", "description": "How to structure system prompts"},
                {"name": "tool_mastery", "type": "technique", "description": "Tool mastery workflow"},
            ],
        )
        assert len(result["scored_primitives"]) == 2


class TestAssimilatorState:
    def test_list_artifacts(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        assimilator.ingest("art1")
        assimilator.ingest("art2")
        assert len(assimilator.list_artifacts()) == 2

    def test_get_artifact(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        art = assimilator.ingest("test")
        found = assimilator.get_artifact(art.id)
        assert found is not None
        assert found.name == "test"

    def test_to_dict(self, tmp_path):
        assimilator = LeverageAssimilator(state_dir=tmp_path / "assim")
        assimilator.ingest("test")
        d = assimilator.to_dict()
        assert d["total_artifacts"] == 1
        assert "by_status" in d
        assert d["umh_capabilities_tracked"] > 0
