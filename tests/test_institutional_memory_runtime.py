"""Tests for InstitutionalMemoryRuntime — Campaign 15.2."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest
from substrate.organism.institutional_memory_runtime import (
    InstitutionalKnowledge,
    InstitutionalMemoryDriftWarning,
    InstitutionalMemoryHealth,
    InstitutionalMemoryRuntime,
    InstitutionalMemorySnapshot,
    KnowledgeState,
    MemoryDriftType,
)


# ── Type tests ───────────────────────────────────────────────────────


class TestKnowledgeStateEnum:
    def test_values(self) -> None:
        assert KnowledgeState.PROPOSED.value == "proposed"
        assert KnowledgeState.VALIDATED.value == "validated"
        assert KnowledgeState.CANONICAL.value == "canonical"
        assert KnowledgeState.SUPERSEDED.value == "superseded"
        assert KnowledgeState.RETIRED.value == "retired"

    def test_count(self) -> None:
        assert len(KnowledgeState) == 5


class TestInstitutionalMemoryHealthEnum:
    def test_values(self) -> None:
        assert InstitutionalMemoryHealth.THRIVING.value == "thriving"
        assert InstitutionalMemoryHealth.GROWING.value == "growing"
        assert InstitutionalMemoryHealth.STAGNANT.value == "stagnant"
        assert InstitutionalMemoryHealth.DECAYING.value == "decaying"
        assert InstitutionalMemoryHealth.CRITICAL.value == "critical"

    def test_count(self) -> None:
        assert len(InstitutionalMemoryHealth) == 5


class TestMemoryDriftTypeEnum:
    def test_values(self) -> None:
        assert MemoryDriftType.STALE_CANONICAL.value == "stale_canonical"
        assert MemoryDriftType.CONTRADICTED_MEMORY.value == "contradicted_memory"
        assert MemoryDriftType.UNVALIDATED_BACKLOG.value == "unvalidated_backlog"
        assert MemoryDriftType.LESSON_LOSS.value == "lesson_loss"

    def test_count(self) -> None:
        assert len(MemoryDriftType) == 4


class TestInstitutionalKnowledge:
    def test_defaults(self) -> None:
        k = InstitutionalKnowledge()
        assert k.knowledge_id == ""
        assert k.state == KnowledgeState.PROPOSED.value
        assert k.confidence == 0.5
        assert k.validations == 0

    def test_to_dict(self) -> None:
        k = InstitutionalKnowledge(
            knowledge_id="k-1",
            content="test content",
            source_type="decision",
            source_id="d-1",
        )
        d = k.to_dict()
        assert d["knowledge_id"] == "k-1"
        assert d["content"] == "test content"
        assert d["source_type"] == "decision"
        assert "state" in d
        assert "confidence" in d


class TestInstitutionalMemoryDriftWarning:
    def test_defaults(self) -> None:
        w = InstitutionalMemoryDriftWarning()
        assert w.drift_type == MemoryDriftType.STALE_CANONICAL.value
        assert w.severity == "low"

    def test_to_dict(self) -> None:
        w = InstitutionalMemoryDriftWarning(
            drift_type=MemoryDriftType.LESSON_LOSS.value,
            severity="high",
            description="test",
        )
        d = w.to_dict()
        assert d["drift_type"] == "lesson_loss"
        assert d["severity"] == "high"
        assert "affected_ids" in d


class TestInstitutionalMemorySnapshot:
    def test_defaults(self) -> None:
        s = InstitutionalMemorySnapshot()
        assert s.memory_health == InstitutionalMemoryHealth.GROWING.value
        assert s.total_knowledge == 0

    def test_to_dict(self) -> None:
        s = InstitutionalMemorySnapshot(
            memory_health="thriving",
            total_knowledge=10,
            canonical_count=6,
        )
        d = s.to_dict()
        assert d["memory_health"] == "thriving"
        assert d["total_knowledge"] == 10
        assert "knowledge_by_state" in d
        assert "drift_warnings" in d
        assert "generated_at" in d


# ── Runtime tests ────────────────────────────────────────────────────


class TestNoDeps:
    def test_propose_creates_proposed(self) -> None:
        rt = InstitutionalMemoryRuntime()
        k = rt.propose("test knowledge", "test", "src-1")
        assert k.state == KnowledgeState.PROPOSED.value
        assert k.content == "test knowledge"
        assert k.knowledge_id != ""

    def test_drift_warnings_no_crash(self) -> None:
        rt = InstitutionalMemoryRuntime()
        warnings = rt.drift_warnings()
        assert isinstance(warnings, list)

    def test_health_returns_enum(self) -> None:
        rt = InstitutionalMemoryRuntime()
        h = rt.health()
        assert isinstance(h, InstitutionalMemoryHealth)

    def test_snapshot_returns_snapshot(self) -> None:
        rt = InstitutionalMemoryRuntime()
        s = rt.snapshot()
        assert isinstance(s, InstitutionalMemorySnapshot)
        assert s.generated_at > 0

    def test_summary_has_keys(self) -> None:
        rt = InstitutionalMemoryRuntime()
        s = rt.summary()
        assert "memory_health" in s
        assert "total_knowledge" in s
        assert "canonical_count" in s
        assert "drift_warning_count" in s


class TestKnowledgeLifecycle:
    def test_propose(self) -> None:
        rt = InstitutionalMemoryRuntime()
        k = rt.propose("lesson A", "lesson", "l-1")
        assert k.state == "proposed"
        assert k.validations == 0
        assert k.confidence == 0.3

    def test_validate_increments(self) -> None:
        rt = InstitutionalMemoryRuntime()
        k = rt.propose("lesson B", "lesson", "l-2")
        result = rt.validate(k.knowledge_id)
        assert result is not None
        assert result.validations == 1
        assert result.state == "proposed"

    def test_validate_promotes_to_validated(self) -> None:
        rt = InstitutionalMemoryRuntime()
        k = rt.propose("lesson C", "lesson", "l-3")
        rt.validate(k.knowledge_id)
        result = rt.validate(k.knowledge_id)
        assert result is not None
        assert result.validations == 2
        assert result.state == KnowledgeState.VALIDATED.value

    def test_promote_to_canonical(self) -> None:
        rt = InstitutionalMemoryRuntime()
        k = rt.propose("lesson D", "lesson", "l-4")
        rt.validate(k.knowledge_id)
        rt.validate(k.knowledge_id)
        rt.validate(k.knowledge_id)
        # validations=3 but confidence=0.6 (from validate), need >= 0.7
        # Manually set confidence
        k.confidence = 0.8
        result = rt.promote(k.knowledge_id)
        assert result is not None
        assert result.state == KnowledgeState.CANONICAL.value
        assert result.promoted_at > 0

    def test_promote_fails_without_threshold(self) -> None:
        rt = InstitutionalMemoryRuntime()
        k = rt.propose("lesson E", "lesson", "l-5")
        result = rt.promote(k.knowledge_id)
        assert result is not None
        assert result.state == KnowledgeState.PROPOSED.value

    def test_supersede(self) -> None:
        rt = InstitutionalMemoryRuntime()
        k = rt.propose("old knowledge", "memory", "m-1")
        result = rt.supersede(k.knowledge_id, "replacement-id")
        assert result is not None
        assert result.state == KnowledgeState.SUPERSEDED.value

    def test_retire(self) -> None:
        rt = InstitutionalMemoryRuntime()
        k = rt.propose("retiring knowledge", "memory", "m-2")
        result = rt.retire(k.knowledge_id)
        assert result is not None
        assert result.state == KnowledgeState.RETIRED.value

    def test_validate_nonexistent_returns_none(self) -> None:
        rt = InstitutionalMemoryRuntime()
        result = rt.validate("nonexistent-id")
        assert result is None


class TestFiltering:
    def test_knowledge_by_state_all(self) -> None:
        rt = InstitutionalMemoryRuntime()
        baseline = len(rt.knowledge_by_state())
        rt.propose("a", "test", "1")
        rt.propose("b", "test", "2")
        all_k = rt.knowledge_by_state()
        assert len(all_k) == baseline + 2

    def test_knowledge_by_state_filter(self) -> None:
        rt = InstitutionalMemoryRuntime()
        baseline_proposed = len(rt.knowledge_by_state("proposed"))
        k1 = rt.propose("a", "test", "1")
        k2 = rt.propose("b", "test", "2")
        rt.validate(k1.knowledge_id)
        rt.validate(k1.knowledge_id)
        proposed = rt.knowledge_by_state("proposed")
        validated = rt.knowledge_by_state("validated")
        assert len(proposed) == baseline_proposed + 1
        assert len(validated) == 1

    def test_canonical_knowledge(self) -> None:
        rt = InstitutionalMemoryRuntime()
        k = rt.propose("canonical", "test", "1")
        rt.validate(k.knowledge_id)
        rt.validate(k.knowledge_id)
        rt.validate(k.knowledge_id)
        k.confidence = 0.8
        rt.promote(k.knowledge_id)
        canonical = rt.canonical_knowledge()
        assert len(canonical) == 1
        assert canonical[0].state == "canonical"


class TestHealthClassification:
    def test_critical_when_proposed_only(self) -> None:
        rt = InstitutionalMemoryRuntime()
        rt.propose("a", "test", "1")
        rt.propose("b", "test", "2")
        h = rt.health()
        assert h == InstitutionalMemoryHealth.CRITICAL

    def test_critical_when_empty(self) -> None:
        rt = InstitutionalMemoryRuntime()
        h = rt.health()
        assert h == InstitutionalMemoryHealth.CRITICAL
