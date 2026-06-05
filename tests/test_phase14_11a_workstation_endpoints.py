"""Phase 14.11A — workstation endpoint and mode resolver tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")


class TestModeResolver:
    def test_resolve_returns_all_four_modes(self) -> None:
        from substrate.workstation.mode_resolver import resolve_composite_mode
        result = resolve_composite_mode()
        assert "operator_day_mode" in result
        assert "operational_mode" in result
        assert "station_presence_mode" in result
        assert "operator_mode" in result
        assert "effective_posture" in result

    def test_each_mode_has_mode_key(self) -> None:
        from substrate.workstation.mode_resolver import resolve_composite_mode
        result = resolve_composite_mode()
        for key in ("operator_day_mode", "operational_mode", "station_presence_mode", "operator_mode"):
            assert "mode" in result[key], f"{key} missing 'mode' field"
            assert "source" in result[key], f"{key} missing 'source' field"

    def test_effective_posture_is_string(self) -> None:
        from substrate.workstation.mode_resolver import resolve_composite_mode
        result = resolve_composite_mode()
        assert isinstance(result["effective_posture"], str)
        assert result["effective_posture"] in (
            "overnight_autonomous", "deep_work", "inactive", "remote", "active",
        )


class TestPostureDerivation:
    def test_overnight_posture(self) -> None:
        from substrate.workstation.mode_resolver import _derive_posture
        modes = {"operator_day_mode": {"mode": "overnight"}}
        assert _derive_posture(modes) == "overnight_autonomous"

    def test_deep_work_posture(self) -> None:
        from substrate.workstation.mode_resolver import _derive_posture
        modes = {"operator_day_mode": {"mode": "deep_work"}}
        assert _derive_posture(modes) == "deep_work"

    def test_inactive_posture(self) -> None:
        from substrate.workstation.mode_resolver import _derive_posture
        modes = {"operator_day_mode": {"mode": "inactive"}}
        assert _derive_posture(modes) == "inactive"

    def test_remote_posture(self) -> None:
        from substrate.workstation.mode_resolver import _derive_posture
        modes = {"operator_day_mode": {"mode": "remote_active"}}
        assert _derive_posture(modes) == "remote"

    def test_local_active_posture(self) -> None:
        from substrate.workstation.mode_resolver import _derive_posture
        modes = {"operator_day_mode": {"mode": "local_active"}}
        assert _derive_posture(modes) == "active"

    def test_unknown_falls_to_active(self) -> None:
        from substrate.workstation.mode_resolver import _derive_posture
        modes = {"operator_day_mode": {"mode": "unknown"}}
        assert _derive_posture(modes) == "active"


class TestMeshSnapshotReader:
    def test_missing_file_returns_empty(self) -> None:
        import os
        original = os.environ.get("UMH_ROOT")
        os.environ["UMH_ROOT"] = "/tmp/nonexistent_umh_root_test"
        try:
            from transports.api.cockpit_workstation_control_routes import _read_mesh_snapshot
            result = _read_mesh_snapshot()
            assert result == []
        finally:
            if original:
                os.environ["UMH_ROOT"] = original
            else:
                os.environ.pop("UMH_ROOT", None)


class TestVpsNodeReader:
    def test_vps_node_has_required_fields(self) -> None:
        from transports.api.cockpit_workstation_control_routes import _read_vps_node
        node = _read_vps_node()
        assert "id" in node
        assert "name" in node
        assert "os" in node
        assert "status" in node
        assert node["status"] == "connected"
        assert node["role"] == "orchestrator"


class TestTmuxAdapter:
    def test_tmux_adapter_import(self) -> None:
        from adapters.tool_adapters.tmux import TmuxAdapter
        adapter = TmuxAdapter()
        assert adapter.name == "tmux"


class TestRouteFileImport:
    def test_routes_module_imports(self) -> None:
        import transports.api.cockpit_workstation_control_routes as mod
        assert hasattr(mod, "configure")
        assert hasattr(mod, "workstation_control_router")
