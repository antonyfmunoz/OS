"""Tests for organism world model — system self-model."""

from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))

import pytest

from substrate.organism.world_model import (
    EntityCategory,
    EntityStatus,
    EvidenceType,
    GapSeverity,
    WorldCapability,
    WorldEntity,
    WorldEvidence,
    WorldGap,
    WorldModel,
    WorldUncertainty,
    extract_world_model,
    persist_world_model,
)


class TestWorldEvidence:
    def test_creation(self):
        ev = WorldEvidence(
            evidence_type=EvidenceType.FILE_EXISTS,
            source="substrate/organism/daemon.py",
            detail="File exists",
        )
        assert ev.evidence_type == EvidenceType.FILE_EXISTS
        assert ev.source == "substrate/organism/daemon.py"
        assert ev.observed_at > 0

    def test_to_dict(self):
        ev = WorldEvidence(
            evidence_type=EvidenceType.IMPORT_SUCCEEDS,
            source="substrate.organism.daemon",
            detail="Import succeeds",
        )
        d = ev.to_dict()
        assert d["type"] == "import_succeeds"
        assert "source" in d
        assert "observed_at" in d


class TestWorldEntity:
    def test_creation(self):
        entity = WorldEntity(
            id="test_entity",
            name="TestEntity",
            category=EntityCategory.SUBSYSTEM,
            status=EntityStatus.OPERATIONAL,
            description="A test subsystem",
        )
        assert entity.id == "test_entity"
        assert entity.category == EntityCategory.SUBSYSTEM
        assert entity.status == EntityStatus.OPERATIONAL

    def test_evidence_attachment(self):
        entity = WorldEntity(
            id="ev_test", name="EvTest",
            category=EntityCategory.SUBSYSTEM,
        )
        ev = WorldEvidence(
            evidence_type=EvidenceType.FILE_EXISTS,
            source="path.py", detail="exists",
        )
        entity.evidence.append(ev)
        assert len(entity.evidence) == 1
        assert entity.evidence[0].evidence_type == EvidenceType.FILE_EXISTS

    def test_capability_attachment(self):
        entity = WorldEntity(
            id="cap_test", name="CapTest",
            category=EntityCategory.SUBSYSTEM,
        )
        cap = WorldCapability(
            name="event_transport",
            provided_by="cap_test",
            status=EntityStatus.OPERATIONAL,
        )
        entity.capabilities.append(cap)
        assert len(entity.capabilities) == 1
        d = entity.to_dict()
        assert len(d["capabilities"]) == 1
        assert d["capabilities"][0]["name"] == "event_transport"

    def test_to_dict(self):
        entity = WorldEntity(
            id="dict_test", name="DictTest",
            category=EntityCategory.GOVERNANCE,
            status=EntityStatus.DEGRADED,
            description="test desc",
            depends_on=["other_entity"],
        )
        d = entity.to_dict()
        assert d["id"] == "dict_test"
        assert d["category"] == "governance"
        assert d["status"] == "degraded"
        assert d["depends_on"] == ["other_entity"]


class TestWorldGap:
    def test_creation(self):
        gap = WorldGap(
            description="Missing API route",
            severity=GapSeverity.HIGH,
            entity_id="test_entity",
            recommendation="Add GET /api/test endpoint",
        )
        assert gap.severity == GapSeverity.HIGH
        assert gap.entity_id == "test_entity"
        assert gap.id  # auto-generated

    def test_to_dict(self):
        gap = WorldGap(
            description="Test gap",
            severity=GapSeverity.CRITICAL,
        )
        d = gap.to_dict()
        assert d["severity"] == "critical"
        assert "id" in d


class TestWorldUncertainty:
    def test_creation(self):
        u = WorldUncertainty(
            description="Unclear if daemon runs in production",
            entity_id="organism_daemon",
            reason="No container status check available",
            confidence=0.4,
        )
        assert u.confidence == 0.4
        assert u.entity_id == "organism_daemon"

    def test_to_dict(self):
        u = WorldUncertainty(
            description="Test uncertainty",
            confidence=0.7,
        )
        d = u.to_dict()
        assert d["confidence"] == 0.7


class TestWorldModel:
    def test_add_entity(self):
        model = WorldModel()
        entity = WorldEntity(
            id="test", name="Test",
            category=EntityCategory.SUBSYSTEM,
        )
        model.add_entity(entity)
        assert "test" in model.entities
        assert model.get_entity("test") is entity

    def test_add_gap(self):
        model = WorldModel()
        gap = WorldGap(description="A gap", severity=GapSeverity.LOW)
        model.add_gap(gap)
        assert len(model.gaps) == 1

    def test_add_uncertainty(self):
        model = WorldModel()
        u = WorldUncertainty(description="An uncertainty")
        model.add_uncertainty(u)
        assert len(model.uncertainties) == 1

    def test_get_by_category(self):
        model = WorldModel()
        model.add_entity(WorldEntity(id="a", name="A", category=EntityCategory.SUBSYSTEM))
        model.add_entity(WorldEntity(id="b", name="B", category=EntityCategory.INTERFACE))
        model.add_entity(WorldEntity(id="c", name="C", category=EntityCategory.SUBSYSTEM))
        subs = model.get_entities_by_category(EntityCategory.SUBSYSTEM)
        assert len(subs) == 2

    def test_get_by_status(self):
        model = WorldModel()
        model.add_entity(WorldEntity(id="a", name="A", category=EntityCategory.SUBSYSTEM, status=EntityStatus.OPERATIONAL))
        model.add_entity(WorldEntity(id="b", name="B", category=EntityCategory.SUBSYSTEM, status=EntityStatus.MISSING))
        model.add_entity(WorldEntity(id="c", name="C", category=EntityCategory.SUBSYSTEM, status=EntityStatus.OPERATIONAL))
        ops = model.get_entities_by_status(EntityStatus.OPERATIONAL)
        assert len(ops) == 2

    def test_get_gaps_by_severity(self):
        model = WorldModel()
        model.add_gap(WorldGap(description="crit", severity=GapSeverity.CRITICAL))
        model.add_gap(WorldGap(description="low", severity=GapSeverity.LOW))
        model.add_gap(WorldGap(description="crit2", severity=GapSeverity.CRITICAL))
        crits = model.get_gaps_by_severity(GapSeverity.CRITICAL)
        assert len(crits) == 2

    def test_summary(self):
        model = WorldModel()
        model.add_entity(WorldEntity(id="a", name="A", category=EntityCategory.SUBSYSTEM, status=EntityStatus.OPERATIONAL))
        model.add_gap(WorldGap(description="g", severity=GapSeverity.HIGH))
        model.add_uncertainty(WorldUncertainty(description="u"))
        s = model.summary()
        assert s["total_entities"] == 1
        assert s["total_gaps"] == 1
        assert s["total_uncertainties"] == 1
        assert s["by_status"]["operational"] == 1

    def test_to_dict_serialization(self):
        model = WorldModel()
        entity = WorldEntity(
            id="ser", name="Ser",
            category=EntityCategory.SUBSYSTEM,
            status=EntityStatus.OPERATIONAL,
        )
        entity.evidence.append(WorldEvidence(
            evidence_type=EvidenceType.FILE_EXISTS,
            source="test.py", detail="exists",
        ))
        model.add_entity(entity)
        model.add_gap(WorldGap(description="gap", severity=GapSeverity.LOW))
        d = model.to_dict()
        serialized = json.dumps(d, default=str)
        parsed = json.loads(serialized)
        assert "summary" in parsed
        assert "entities" in parsed
        assert "gaps" in parsed
        assert "uncertainties" in parsed


class TestExtraction:
    def test_extract_world_model_runs(self):
        model = extract_world_model()
        assert len(model.entities) > 0
        assert model.extracted_at > 0

    def test_extract_finds_organism_subsystems(self):
        model = extract_world_model()
        entity = model.get_entity("event_spine")
        assert entity is not None
        assert entity.category == EntityCategory.SUBSYSTEM

    def test_extract_finds_data_stores(self):
        model = extract_world_model()
        stores = model.get_entities_by_category(EntityCategory.DATA_STORE)
        assert len(stores) > 0


class TestPersistence:
    def test_persist_world_model(self):
        model = WorldModel()
        model.add_entity(WorldEntity(
            id="p", name="P", category=EntityCategory.SUBSYSTEM,
        ))
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            result = persist_world_model(model, path=path)
            assert os.path.isfile(result)
            with open(result) as f:
                line = f.readline()
            data = json.loads(line)
            assert "entities" in data
            assert "p" in data["entities"]
        finally:
            os.unlink(path)


class TestDaemonIntegration:
    def test_world_model_importable_from_organism(self):
        from substrate.organism import world_model
        assert hasattr(world_model, "extract_world_model")
        assert hasattr(world_model, "WorldModel")
        assert hasattr(world_model, "WorldEntity")
