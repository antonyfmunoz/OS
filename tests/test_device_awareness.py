"""Tests for Device Awareness Runtime — Campaign 5.3."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.organism.device_awareness import DeviceAwarenessRuntime, DeviceRecord


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def registry_path(tmp_path):
    data = [
        {
            "id": "vps",
            "tailscale_name": "srv1500858",
            "device_type": "vps",
            "display_name": "srv1500858 (VPS)",
            "os": "linux",
            "role": "orchestrator",
            "tailscale_ip": "100.77.233.50",
            "always_online": True,
            "compute": True,
        },
        {
            "id": "beast",
            "tailscale_name": "desktop-lvguiq9",
            "device_type": "pc",
            "display_name": "desktop-lvguiq9 (PC)",
            "os": "windows",
            "role": "executor",
            "tailscale_ip": "100.74.199.102",
            "compute": True,
            "gpu": "NVIDIA GeForce GTX 1080 Ti",
        },
        {
            "id": "ipad",
            "tailscale_name": "ipad-pro-12-9-gen-5",
            "device_type": "tablet",
            "display_name": "ipad-pro-12-9-gen-5 (Tablet)",
            "os": "ios",
            "role": "controller",
        },
        {
            "id": "iphone",
            "tailscale_name": "iphone-15-pro-max",
            "device_type": "mobile",
            "display_name": "iphone-15-pro-max (Mobile)",
            "os": "ios",
            "role": "controller",
        },
    ]
    path = tmp_path / "device_registry.json"
    path.write_text(json.dumps(data))
    return str(path)


@pytest.fixture
def runtime(registry_path):
    return DeviceAwarenessRuntime(device_registry_path=registry_path)


# ── DeviceRecord Tests ────────────────────────────────────────────────────


class TestDeviceRecord:
    def test_to_dict(self):
        rec = DeviceRecord(
            device_id="vps",
            display_name="srv1500858 (VPS)",
            role="orchestrator",
            compute=True,
        )
        d = rec.to_dict()
        assert d["id"] == "vps"
        assert d["role"] == "orchestrator"
        assert d["compute"] is True

    def test_defaults(self):
        rec = DeviceRecord(device_id="test", display_name="Test")
        assert rec.tailscale_name == ""
        assert rec.gpu == ""
        assert rec.compute is False


# ── Detection Tests ───────────────────────────────────────────────────────


class TestDetectActiveDevice:
    def test_detect_from_env_var(self, runtime, monkeypatch):
        monkeypatch.setenv("UMH_DEVICE_ID", "beast")
        assert runtime.detect_active_device() == "beast"

    def test_detect_from_env_var_unknown_id(self, runtime, monkeypatch):
        monkeypatch.setenv("UMH_DEVICE_ID", "nonexistent")
        # Falls through to hostname check
        result = runtime.detect_active_device()
        assert result != "nonexistent"

    def test_detect_from_hostname_exact(self, runtime, monkeypatch):
        monkeypatch.delenv("UMH_DEVICE_ID", raising=False)
        monkeypatch.setenv("HOSTNAME", "srv1500858")
        assert runtime.detect_active_device() == "vps"

    def test_detect_from_hostname_beast(self, runtime, monkeypatch):
        monkeypatch.delenv("UMH_DEVICE_ID", raising=False)
        monkeypatch.setenv("HOSTNAME", "desktop-lvguiq9")
        assert runtime.detect_active_device() == "beast"

    def test_detect_from_socket_hostname(self, runtime, monkeypatch):
        monkeypatch.delenv("UMH_DEVICE_ID", raising=False)
        monkeypatch.delenv("HOSTNAME", raising=False)
        monkeypatch.setattr("socket.gethostname", lambda: "srv1500858")
        assert runtime.detect_active_device() == "vps"

    def test_detect_fallback_unknown(self, runtime, monkeypatch):
        monkeypatch.delenv("UMH_DEVICE_ID", raising=False)
        monkeypatch.delenv("HOSTNAME", raising=False)
        monkeypatch.setattr("socket.gethostname", lambda: "random-hostname-xyz")
        assert runtime.detect_active_device() == "unknown"

    def test_detect_hostname_substring_match(self, runtime, monkeypatch):
        monkeypatch.delenv("UMH_DEVICE_ID", raising=False)
        monkeypatch.setenv("HOSTNAME", "some-prefix-srv1500858-suffix")
        assert runtime.detect_active_device() == "vps"

    def test_env_takes_priority_over_hostname(self, runtime, monkeypatch):
        monkeypatch.setenv("UMH_DEVICE_ID", "vps")
        monkeypatch.setenv("HOSTNAME", "desktop-lvguiq9")
        assert runtime.detect_active_device() == "vps"


# ── Capability Tests ──────────────────────────────────────────────────────


class TestDeviceCapabilities:
    def test_vps_capabilities(self, runtime):
        caps = runtime.device_capabilities("vps")
        assert caps["role"] == "orchestrator"
        assert caps["compute"] is True
        assert caps["always_online"] is True

    def test_beast_capabilities(self, runtime):
        caps = runtime.device_capabilities("beast")
        assert caps["role"] == "executor"
        assert caps["gpu"] == "NVIDIA GeForce GTX 1080 Ti"

    def test_unknown_device_returns_empty(self, runtime):
        caps = runtime.device_capabilities("nonexistent")
        assert caps == {}

    def test_with_reality_graph(self, registry_path):
        from substrate.organism.reality_graph import (
            RealityEntity,
            RealityEntityStatus,
            RealityEntityType,
            RealityGraph,
        )

        graph = RealityGraph()
        graph._add_entity(RealityEntity(
            entity_id="dev-vps",
            entity_type=RealityEntityType.DEVICE,
            name="VPS",
            status=RealityEntityStatus.ACTIVE,
            properties={"extra_info": "from_graph"},
            last_observed=1000.0,
        ))
        rt = DeviceAwarenessRuntime(
            reality_graph=graph,
            device_registry_path=registry_path,
        )
        caps = rt.device_capabilities("vps")
        assert caps.get("graph_properties", {}).get("extra_info") == "from_graph"
        assert caps["graph_status"] == "active"


# ── Best Device Routing ──────────────────────────────────────────────────


class TestBestDeviceFor:
    def test_gpu_routes_to_beast(self, runtime):
        assert runtime.best_device_for("gpu") == "beast"

    def test_gpu_available_routes_to_beast(self, runtime):
        assert runtime.best_device_for("gpu_available") == "beast"

    def test_orchestration_routes_to_vps(self, runtime):
        assert runtime.best_device_for("orchestration") == "vps"

    def test_execution_routes_to_executor(self, runtime):
        result = runtime.best_device_for("execution")
        assert result in ("beast", "vps")

    def test_always_on_routes_to_vps(self, runtime):
        assert runtime.best_device_for("always_on") == "vps"

    def test_heavy_compute_routes_to_beast(self, runtime):
        assert runtime.best_device_for("heavy_compute") == "beast"

    def test_unknown_capability_returns_unknown(self, runtime):
        assert runtime.best_device_for("teleportation") == "unknown"


# ── Available Devices ────────────────────────────────────────────────────


class TestAvailableDevices:
    def test_lists_all_devices(self, runtime):
        devices = runtime.available_devices()
        assert len(devices) == 4

    def test_device_structure(self, runtime):
        devices = runtime.available_devices()
        for dev in devices:
            assert "id" in dev
            assert "name" in dev
            assert "role" in dev

    def test_contains_all_ids(self, runtime):
        ids = {d["id"] for d in runtime.available_devices()}
        assert ids == {"vps", "beast", "ipad", "iphone"}


# ── Context Population ───────────────────────────────────────────────────


class TestPopulateContext:
    def test_populates_active_device(self, runtime, monkeypatch):
        monkeypatch.setenv("UMH_DEVICE_ID", "vps")
        from substrate.organism.orchestrator_awareness_runtime import OrchestratorContext
        ctx = OrchestratorContext()
        runtime.populate_context(ctx)
        assert ctx.active_device == "vps"

    def test_populates_compute_nodes(self, runtime, monkeypatch):
        monkeypatch.setenv("UMH_DEVICE_ID", "vps")
        from substrate.organism.orchestrator_awareness_runtime import OrchestratorContext
        ctx = OrchestratorContext()
        runtime.populate_context(ctx)
        assert len(ctx.active_compute_nodes) == 2
        compute_ids = {n["id"] for n in ctx.active_compute_nodes}
        assert "vps" in compute_ids
        assert "beast" in compute_ids

    def test_populates_preferred_execution(self, runtime, monkeypatch):
        monkeypatch.setenv("UMH_DEVICE_ID", "vps")
        from substrate.organism.orchestrator_awareness_runtime import OrchestratorContext
        ctx = OrchestratorContext()
        runtime.populate_context(ctx)
        assert ctx.preferred_execution_device == "beast"

    def test_populates_available_execution(self, runtime, monkeypatch):
        monkeypatch.setenv("UMH_DEVICE_ID", "vps")
        from substrate.organism.orchestrator_awareness_runtime import OrchestratorContext
        ctx = OrchestratorContext()
        runtime.populate_context(ctx)
        assert "vps" in ctx.available_execution_devices
        assert "beast" in ctx.available_execution_devices
        assert "ipad" not in ctx.available_execution_devices


# ── Snapshot Tests ────────────────────────────────────────────────────────


class TestSnapshot:
    def test_snapshot_structure(self, runtime, monkeypatch):
        monkeypatch.setenv("UMH_DEVICE_ID", "vps")
        snap = runtime.snapshot()
        assert "active_device" in snap
        assert "active_device_capabilities" in snap
        assert "preferred_execution_device" in snap
        assert "available_devices" in snap
        assert "device_count" in snap

    def test_snapshot_device_count(self, runtime, monkeypatch):
        monkeypatch.setenv("UMH_DEVICE_ID", "vps")
        snap = runtime.snapshot()
        assert snap["device_count"] == 4
        assert snap["active_device"] == "vps"


# ── Edge Cases ────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_missing_registry_file(self, tmp_path):
        rt = DeviceAwarenessRuntime(
            device_registry_path=str(tmp_path / "nope.json"),
        )
        assert rt.available_devices() == []
        assert rt.detect_active_device() == "unknown"

    def test_empty_registry(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("[]")
        rt = DeviceAwarenessRuntime(device_registry_path=str(path))
        assert rt.available_devices() == []

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{invalid")
        rt = DeviceAwarenessRuntime(device_registry_path=str(path))
        assert rt.available_devices() == []

    def test_device_without_id_skipped(self, tmp_path):
        data = [{"display_name": "No ID device", "role": "test"}]
        path = tmp_path / "reg.json"
        path.write_text(json.dumps(data))
        rt = DeviceAwarenessRuntime(device_registry_path=str(path))
        assert rt.available_devices() == []
