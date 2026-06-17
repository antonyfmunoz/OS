"""Tests for Gate 10 — Projection Consumption Layer.

Verifies:
- Types: ProjectionRegistration, ProjectionPortProtocol
- Drift detection: detect_import_drift, scan_projection_imports
- Registration: register, get, list, unregister, capabilities_for
- Audit: audit_projection, audit_all
- Persistence: JSONL roundtrip
- Backward compat: legacy module-level functions
- Type coherence: canonical_types registration
- Routes: cockpit route mounting
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


class TestTypes(unittest.TestCase):
    def test_registration_creation(self) -> None:
        from substrate.sockets.projection_port import ProjectionRegistration

        r = ProjectionRegistration(name="TestProj")
        assert r.name == "TestProj"
        assert r.projection_id.startswith("proj-")
        assert r.capabilities_consumed == []

    def test_registration_to_dict(self) -> None:
        from substrate.sockets.projection_port import ProjectionRegistration

        r = ProjectionRegistration(name="TestProj")
        d = r.to_dict()
        assert d["name"] == "TestProj"
        assert "projection_id" in d
        assert "registered_at" in d

    def test_registration_from_dict(self) -> None:
        from substrate.sockets.projection_port import ProjectionRegistration

        d = {
            "projection_id": "proj-abc123",
            "name": "EOS",
            "capabilities_consumed": ["deploy", "review"],
            "routes_mounted": ["/eos/dashboard"],
        }
        r = ProjectionRegistration.from_dict(d)
        assert r.projection_id == "proj-abc123"
        assert r.name == "EOS"
        assert len(r.capabilities_consumed) == 2

    def test_protocol_conformance(self) -> None:
        from substrate.sockets.projection_port import (
            ProjectionPort,
            ProjectionPortProtocol,
        )

        assert issubclass(ProjectionPort, ProjectionPortProtocol)

    def test_registration_ignores_unknown_keys(self) -> None:
        from substrate.sockets.projection_port import ProjectionRegistration

        d = {"name": "Test", "unknown_field": "should be ignored"}
        r = ProjectionRegistration.from_dict(d)
        assert r.name == "Test"


class TestDriftDetection(unittest.TestCase):
    def test_clean_imports(self) -> None:
        from substrate.sockets.projection_port import detect_import_drift

        result = detect_import_drift(
            "eos",
            ["substrate.types", "adapters.models.model_router", "transports.api.cockpit"],
        )
        assert result["drifting"] is False
        assert result["violation_count"] == 0
        assert result["clean"] == 3

    def test_drifting_imports(self) -> None:
        from substrate.sockets.projection_port import detect_import_drift

        result = detect_import_drift(
            "eos",
            ["substrate.types", "services.discord_bot", "runtime.legacy"],
        )
        assert result["drifting"] is True
        assert result["violation_count"] == 2
        assert "services.discord_bot" in result["violations"]

    def test_empty_imports(self) -> None:
        from substrate.sockets.projection_port import detect_import_drift

        result = detect_import_drift("empty", [])
        assert result["drifting"] is False
        assert result["total_imports"] == 0

    def test_scan_nonexistent_dir(self) -> None:
        from substrate.sockets.projection_port import scan_projection_imports

        imports = scan_projection_imports("/nonexistent/path")
        assert imports == []

    def test_scan_real_dir(self) -> None:
        from substrate.sockets.projection_port import scan_projection_imports

        tmp = tempfile.mkdtemp()
        with open(os.path.join(tmp, "test.py"), "w") as f:
            f.write("from substrate.types import SignalEnvelope\n")
            f.write("import adapters.models.model_router\n")
        imports = scan_projection_imports(tmp)
        assert "substrate.types" in imports
        assert "adapters.models.model_router" in imports


class TestProjectionPort(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self._path = os.path.join(self._tmp, "registrations.jsonl")

    def _make_port(self) -> "ProjectionPort":
        from substrate.sockets.projection_port import ProjectionPort

        return ProjectionPort(store_path=self._path)

    def test_register_and_get(self) -> None:
        from substrate.sockets.projection_port import ProjectionRegistration

        port = self._make_port()
        reg = ProjectionRegistration(name="EOS", capabilities_consumed=["deploy"])
        port.register(reg)
        result = port.get(reg.projection_id)
        assert result is not None
        assert result.name == "EOS"

    def test_list_registrations(self) -> None:
        from substrate.sockets.projection_port import ProjectionRegistration

        port = self._make_port()
        port.register(ProjectionRegistration(name="EOS"))
        port.register(ProjectionRegistration(name="CreatorOS"))
        assert len(port.list_registrations()) == 2

    def test_unregister(self) -> None:
        from substrate.sockets.projection_port import ProjectionRegistration

        port = self._make_port()
        reg = ProjectionRegistration(name="EOS")
        port.register(reg)
        assert port.unregister(reg.projection_id) is True
        assert port.get(reg.projection_id) is None

    def test_unregister_nonexistent(self) -> None:
        port = self._make_port()
        assert port.unregister("nope") is False

    def test_capabilities_for(self) -> None:
        from substrate.sockets.projection_port import ProjectionRegistration

        port = self._make_port()
        reg = ProjectionRegistration(
            name="EOS",
            capabilities_consumed=["deploy", "review", "governance"],
        )
        port.register(reg)
        caps = port.capabilities_for(reg.projection_id)
        assert len(caps) == 3
        assert "deploy" in caps

    def test_capabilities_for_nonexistent(self) -> None:
        port = self._make_port()
        assert port.capabilities_for("nope") == []

    def test_audit_projection(self) -> None:
        port = self._make_port()
        tmp_proj = tempfile.mkdtemp()
        os.makedirs(os.path.join(tmp_proj, "projections", "test_proj"))
        with open(os.path.join(tmp_proj, "projections", "test_proj", "app.py"), "w") as f:
            f.write("from substrate.types import SignalEnvelope\n")
            f.write("from services.discord_bot import Bot\n")

        os.environ["UMH_ROOT"] = tmp_proj
        try:
            from substrate.sockets import projection_port

            old_root = projection_port._REPO_ROOT
            projection_port._REPO_ROOT = tmp_proj
            result = port.audit_projection("test_proj")
            projection_port._REPO_ROOT = old_root
        finally:
            os.environ["UMH_ROOT"] = "/opt/OS"

        assert result["drifting"] is True
        assert result["violation_count"] == 1

    def test_audit_all_nonexistent_dir(self) -> None:
        from substrate.sockets import projection_port

        port = self._make_port()
        old_root = projection_port._REPO_ROOT
        projection_port._REPO_ROOT = "/nonexistent/path"
        result = port.audit_all()
        projection_port._REPO_ROOT = old_root
        assert result["projections"] == []
        assert result["total_violations"] == 0

    def test_summary(self) -> None:
        from substrate.sockets.projection_port import ProjectionRegistration

        port = self._make_port()
        port.register(ProjectionRegistration(name="EOS", capabilities_consumed=["a", "b"]))
        s = port.summary()
        assert s["total_registrations"] == 1
        assert s["projections"][0]["capabilities_count"] == 2


class TestPersistence(unittest.TestCase):
    def test_jsonl_roundtrip(self) -> None:
        from substrate.sockets.projection_port import (
            ProjectionPort,
            ProjectionRegistration,
        )

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "registrations.jsonl")
        p1 = ProjectionPort(store_path=path)
        p1.register(ProjectionRegistration(name="EOS"))
        p1.register(ProjectionRegistration(name="CreatorOS"))

        p2 = ProjectionPort(store_path=path)
        assert len(p2.list_registrations()) == 2

    def test_malformed_jsonl_skipped(self) -> None:
        from substrate.sockets.projection_port import ProjectionPort

        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "registrations.jsonl")
        with open(path, "w") as f:
            f.write("bad json\n")
            f.write(json.dumps({"projection_id": "proj-ok", "name": "test"}) + "\n")
        p = ProjectionPort(store_path=path)
        assert len(p.list_registrations()) == 1


class TestLegacyCompat(unittest.TestCase):
    def test_module_level_register_and_get(self) -> None:
        from substrate.sockets.projection_port import (
            get_projection,
            register_projection,
        )

        register_projection("test-proj", {"routes": ["/test"]})
        result = get_projection("test-proj")
        assert result is not None
        assert result["routes"] == ["/test"]

    def test_module_level_list(self) -> None:
        from substrate.sockets.projection_port import (
            list_projections,
            register_projection,
        )

        register_projection("legacy-1", {})
        assert "legacy-1" in list_projections()

    def test_module_level_unregister(self) -> None:
        from substrate.sockets.projection_port import (
            register_projection,
            unregister_projection,
        )

        register_projection("to-remove", {})
        assert unregister_projection("to-remove") is True
        assert unregister_projection("to-remove") is False


class TestTypeCoherence(unittest.TestCase):
    def test_canonical_types_registered(self) -> None:
        from substrate.canonical_types import CANONICAL_TYPES

        for name in [
            "ProjectionRegistration",
            "ProjectionPort",
            "ProjectionPortProtocol",
        ]:
            assert name in CANONICAL_TYPES, f"{name} not in canonical_types"
            assert "substrate.sockets.projection_port" in CANONICAL_TYPES[name]


class TestRoutes(unittest.TestCase):
    def test_routes_importable(self) -> None:
        from transports.api.cockpit_projection_routes import projection_router

        assert projection_router is not None

    def test_cockpit_mounts_projection_routes(self) -> None:
        import transports.api.cockpit as c

        route_paths = [r.path for r in c.router.routes]
        assert any("/projections/" in p or p.endswith("/projections") for p in route_paths)
        assert any("/projections/summary" in p for p in route_paths)
        assert any("/projections/audit" in p for p in route_paths)


if __name__ == "__main__":
    unittest.main()
