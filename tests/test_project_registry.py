"""Tests for Project Registry — Campaign 5.2."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.project_registry import ProjectDefinition, ProjectRegistry


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def seed_data():
    return [
        {
            "project_id": "umh",
            "name": "UMH",
            "description": "Universal Meta Harness",
            "projection": "",
            "repositories": ["umh-os"],
            "documents": ["arch-spec"],
            "infrastructure": ["cockpit-api", "os-discord"],
            "decisions": [{"date": "2026-05-23", "decision": "converge"}],
            "capabilities": ["orchestration", "governance"],
            "owner_device_ids": ["vps", "beast"],
            "status": "active",
        },
        {
            "project_id": "creatoros",
            "name": "CreatorOS",
            "description": "Creator workspace",
            "projection": "creatoros",
            "repositories": ["creatoros-app"],
            "documents": [],
            "infrastructure": [],
            "capabilities": ["desktop-app"],
            "owner_device_ids": ["beast"],
            "status": "active",
        },
        {
            "project_id": "lyfeos",
            "name": "LyfeOS",
            "description": "Life OS",
            "projection": "lyfeos",
            "repositories": ["lyfeos-app"],
            "documents": [],
            "infrastructure": [],
            "capabilities": [],
            "owner_device_ids": ["beast"],
            "status": "inactive",
        },
    ]


@pytest.fixture
def registry_path(tmp_path, seed_data):
    path = tmp_path / "project_registry.json"
    path.write_text(json.dumps(seed_data))
    return str(path)


@pytest.fixture
def registry(registry_path):
    return ProjectRegistry(registry_path=registry_path)


# ── ProjectDefinition Tests ───────────────────────────────────────────────


class TestProjectDefinition:
    def test_create_minimal(self):
        proj = ProjectDefinition(project_id="test", name="Test")
        assert proj.project_id == "test"
        assert proj.name == "Test"

    def test_defaults(self):
        proj = ProjectDefinition(project_id="test", name="Test")
        assert proj.description == ""
        assert proj.projection == ""
        assert proj.repositories == []
        assert proj.documents == []
        assert proj.infrastructure == []
        assert proj.decisions == []
        assert proj.capabilities == []
        assert proj.owner_device_ids == []
        assert proj.status == "active"

    def test_to_dict(self):
        proj = ProjectDefinition(
            project_id="umh",
            name="UMH",
            description="test desc",
            repositories=["umh-os"],
            status="active",
        )
        d = proj.to_dict()
        assert d["project_id"] == "umh"
        assert d["name"] == "UMH"
        assert d["description"] == "test desc"
        assert d["repositories"] == ["umh-os"]
        assert d["status"] == "active"

    def test_to_dict_all_fields(self):
        proj = ProjectDefinition(
            project_id="x",
            name="X",
            description="desc",
            projection="xproj",
            repositories=["r1"],
            documents=["d1"],
            infrastructure=["i1"],
            decisions=[{"d": 1}],
            capabilities=["c1"],
            owner_device_ids=["dev1"],
            status="active",
        )
        d = proj.to_dict()
        assert len(d) == 11
        assert d["projection"] == "xproj"
        assert d["decisions"] == [{"d": 1}]


# ── Registry Load Tests ──────────────────────────────────────────────────


class TestProjectRegistryLoad:
    def test_loads_from_json(self, registry):
        assert registry.project_count == 3

    def test_project_count_property(self, registry):
        assert registry.project_count == 3

    def test_all_project_ids(self, registry):
        ids = registry.all_project_ids()
        assert set(ids) == {"umh", "creatoros", "lyfeos"}


# ── Get Tests ─────────────────────────────────────────────────────────────


class TestProjectRegistryGet:
    def test_get_existing(self, registry):
        proj = registry.get("umh")
        assert proj is not None
        assert proj.name == "UMH"
        assert proj.description == "Universal Meta Harness"

    def test_get_nonexistent(self, registry):
        assert registry.get("nonexistent") is None

    def test_find_by_name_exact(self, registry):
        proj = registry.find_by_name("UMH")
        assert proj is not None
        assert proj.project_id == "umh"

    def test_find_by_name_case_insensitive(self, registry):
        proj = registry.find_by_name("creatoros")
        assert proj is not None
        assert proj.project_id == "creatoros"

    def test_find_by_name_partial(self, registry):
        proj = registry.find_by_name("Creator")
        assert proj is not None
        assert proj.project_id == "creatoros"

    def test_find_by_name_no_match(self, registry):
        assert registry.find_by_name("nonexistent_xyz") is None

    def test_find_by_repo(self, registry):
        proj = registry.find_by_repo("umh-os")
        assert proj is not None
        assert proj.project_id == "umh"

    def test_find_by_repo_creatoros(self, registry):
        proj = registry.find_by_repo("creatoros-app")
        assert proj is not None
        assert proj.project_id == "creatoros"

    def test_find_by_repo_no_match(self, registry):
        assert registry.find_by_repo("nonexistent-repo") is None

    def test_find_by_projection(self, registry):
        proj = registry.find_by_projection("creatoros")
        assert proj is not None
        assert proj.project_id == "creatoros"

    def test_find_by_projection_case_insensitive(self, registry):
        proj = registry.find_by_projection("LyfeOS")
        assert proj is not None
        assert proj.project_id == "lyfeos"

    def test_find_by_projection_no_match(self, registry):
        assert registry.find_by_projection("nonexistent") is None

    def test_find_by_projection_empty(self, registry):
        proj = registry.find_by_projection("")
        assert proj is not None
        assert proj.project_id == "umh"


# ── List Tests ────────────────────────────────────────────────────────────


class TestProjectRegistryList:
    def test_list_all(self, registry):
        projects = registry.list_projects()
        assert len(projects) == 3

    def test_list_active(self, registry):
        projects = registry.list_projects(status="active")
        assert len(projects) == 2
        ids = {p.project_id for p in projects}
        assert "umh" in ids
        assert "creatoros" in ids

    def test_list_inactive(self, registry):
        projects = registry.list_projects(status="inactive")
        assert len(projects) == 1
        assert projects[0].project_id == "lyfeos"

    def test_list_unknown_status(self, registry):
        projects = registry.list_projects(status="archived")
        assert len(projects) == 0


# ── Context Bundle Tests ──────────────────────────────────────────────────


class TestContextForProject:
    def test_context_structure(self, registry):
        ctx = registry.context_for_project("umh")
        assert "project" in ctx
        assert ctx["repo_count"] == 1
        assert ctx["doc_count"] == 1
        assert ctx["infra_count"] == 2
        assert ctx["capability_count"] == 2
        assert ctx["device_count"] == 2
        assert ctx["decision_count"] == 1
        assert ctx["has_projection"] is False

    def test_context_with_projection(self, registry):
        ctx = registry.context_for_project("creatoros")
        assert ctx["has_projection"] is True

    def test_context_project_data(self, registry):
        ctx = registry.context_for_project("umh")
        proj = ctx["project"]
        assert proj["project_id"] == "umh"
        assert proj["name"] == "UMH"

    def test_context_not_found(self, registry):
        ctx = registry.context_for_project("nonexistent")
        assert "error" in ctx


# ── Edge Cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_missing_file(self, tmp_path):
        reg = ProjectRegistry(registry_path=str(tmp_path / "nope.json"))
        assert reg.project_count == 0

    def test_empty_file(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("")
        reg = ProjectRegistry(registry_path=str(path))
        assert reg.project_count == 0

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not valid json")
        reg = ProjectRegistry(registry_path=str(path))
        assert reg.project_count == 0

    def test_not_a_list(self, tmp_path):
        path = tmp_path / "obj.json"
        path.write_text(json.dumps({"project_id": "x", "name": "X"}))
        reg = ProjectRegistry(registry_path=str(path))
        assert reg.project_count == 0

    def test_entries_missing_id(self, tmp_path):
        path = tmp_path / "no_id.json"
        path.write_text(json.dumps([{"name": "No ID"}, {"project_id": "valid", "name": "Valid"}]))
        reg = ProjectRegistry(registry_path=str(path))
        assert reg.project_count == 1
        assert reg.get("valid") is not None

    def test_minimal_entry(self, tmp_path):
        path = tmp_path / "min.json"
        path.write_text(json.dumps([{"project_id": "min"}]))
        reg = ProjectRegistry(registry_path=str(path))
        proj = reg.get("min")
        assert proj is not None
        assert proj.name == "min"
        assert proj.status == "active"
