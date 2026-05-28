"""Tests for substrate.self_model — the system's self-awareness foundation.

Verifies that the self-model can:
  1. Know what it is (canonical structure)
  2. Know who it is (instance identity)
  3. Classify canonical vs instance values
  4. Determine architectural layers
  5. Query connected subsystems
  6. Produce a unified self-snapshot
  7. Detect instance values at runtime
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate.self_model import (
    CANONICAL,
    CanonicalSelf,
    ContextKind,
    InstanceSelf,
    Layer,
    SelfModel,
)


class TestCanonicalSelf:
    def test_frozen(self):
        with pytest.raises(Exception):
            CANONICAL.system_name = "something else"

    def test_universal_values(self):
        assert CANONICAL.system_name == "UMH"
        assert CANONICAL.system_full_name == "Universal Mastery Hierarchy"
        assert len(CANONICAL.architecture_layers) == 4
        assert len(CANONICAL.core_principles) == 4

    def test_to_dict(self):
        d = CANONICAL.to_dict()
        assert d["system_name"] == "UMH"
        assert "layers" in d
        assert "principles" in d


class TestInstanceSelf:
    def test_default_empty(self):
        inst = InstanceSelf()
        assert inst.ai_name == ""
        assert inst.loaded is False

    def test_mutable(self):
        inst = InstanceSelf()
        inst.ai_name = "TestAI"
        assert inst.ai_name == "TestAI"

    def test_to_dict(self):
        inst = InstanceSelf(ai_name="TestAI", org_id="org-1")
        d = inst.to_dict()
        assert d["ai_name"] == "TestAI"
        assert d["org_id"] == "org-1"


class TestClassification:
    def test_instance_signals(self):
        sm = SelfModel()
        assert sm.classify("founder name") == ContextKind.INSTANCE
        assert sm.classify("company IP address") == ContextKind.INSTANCE
        assert sm.classify("user account id") == ContextKind.INSTANCE
        assert sm.classify("venture product") == ContextKind.INSTANCE
        assert sm.classify("node_id value") == ContextKind.INSTANCE

    def test_canonical_signals(self):
        sm = SelfModel()
        assert sm.classify("governance engine") == ContextKind.CANONICAL
        assert sm.classify("type system") == ContextKind.CANONICAL
        assert sm.classify("execution spine") == ContextKind.CANONICAL


class TestLayerDetection:
    def test_substrate(self):
        sm = SelfModel()
        assert sm.which_layer("substrate.types") == Layer.SUBSTRATE
        assert sm.which_layer("substrate.organism.coordinator") == Layer.SUBSTRATE

    def test_adapter(self):
        sm = SelfModel()
        assert sm.which_layer("adapters.models.model_router") == Layer.ADAPTER

    def test_transport(self):
        sm = SelfModel()
        assert sm.which_layer("transports.discord.signal_factory") == Layer.TRANSPORT

    def test_projection(self):
        sm = SelfModel()
        assert sm.which_layer("projections.eos.agents") == Layer.PROJECTION

    def test_unknown_is_instance(self):
        sm = SelfModel()
        assert sm.which_layer("some_unknown_module") == Layer.INSTANCE


class TestInstanceValueDetection:
    def test_no_detection_before_load(self):
        sm = SelfModel()
        assert sm.is_instance_value("anything") is False

    def test_detects_loaded_values(self):
        sm = SelfModel()
        sm.instance.loaded = True
        sm.instance.ai_name = "TestBot"
        sm.instance.org_id = "org-test-123"
        assert sm.is_instance_value("TestBot") is True
        assert sm.is_instance_value("org-test-123") is True
        assert sm.is_instance_value("unknown") is False

    def test_detects_venture_values(self):
        sm = SelfModel()
        sm.instance.loaded = True
        sm.instance.ventures = [{"name": "TestVenture", "id": "v-1"}]
        assert sm.is_instance_value("TestVenture") is True
        assert sm.is_instance_value("v-1") is True

    def test_ignores_empty_values(self):
        sm = SelfModel()
        sm.instance.loaded = True
        sm.instance.ai_name = ""
        assert sm.is_instance_value("") is False


class _MockRegistry:
    def count(self):
        return 3


class _MockTraceRecorder:
    def count(self):
        return 42


class _MockRuntimeGraph:
    @property
    def node_count(self):
        return 5

    @property
    def available_count(self):
        return 4


class _MockObserver:
    class _Snap:
        def to_dict(self):
            return {"objectives": 2, "work_units": 7}

    def snapshot(self):
        return self._Snap()


class TestOperationalAwareness:
    def test_no_subsystems(self):
        sm = SelfModel()
        assert sm.capabilities() == {"available": False, "components": 0}
        assert sm.runtimes() == {"available": False, "total": 0, "active": 0}
        assert sm.traces() == {"available": False, "count": 0}

    def test_with_registry(self):
        sm = SelfModel()
        sm.register_subsystems(registry=_MockRegistry())
        cap = sm.capabilities()
        assert cap["available"] is True
        assert cap["components"] == 3

    def test_with_trace_recorder(self):
        sm = SelfModel()
        sm.register_subsystems(trace_recorder=_MockTraceRecorder())
        tr = sm.traces()
        assert tr["available"] is True
        assert tr["count"] == 42

    def test_with_runtime_graph(self):
        sm = SelfModel()
        sm.register_subsystems(runtime_graph=_MockRuntimeGraph())
        rt = sm.runtimes()
        assert rt["available"] is True
        assert rt["total"] == 5
        assert rt["active"] == 4

    def test_with_organism_observer(self):
        sm = SelfModel()
        sm.register_subsystems(organism_observer=_MockObserver())
        org = sm.organism()
        assert org["available"] is True
        assert org["snapshot"]["objectives"] == 2

    def test_laws_available(self):
        sm = SelfModel()
        law_info = sm.laws()
        assert law_info["available"] is True
        assert law_info["count"] == 14


class TestWhoAmI:
    def test_full_snapshot_structure(self):
        sm = SelfModel()
        sm.instance.loaded = True
        sm.instance.ai_name = "TestAI"
        sm.register_subsystems(
            registry=_MockRegistry(),
            trace_recorder=_MockTraceRecorder(),
            runtime_graph=_MockRuntimeGraph(),
        )
        result = sm.who_am_i()
        assert "canonical" in result
        assert "instance" in result
        assert "operational" in result
        assert "identity_summary" in result
        assert result["canonical"]["system_name"] == "UMH"
        assert result["instance"]["ai_name"] == "TestAI"
        assert result["operational"]["capabilities"]["components"] == 3
        assert result["operational"]["runtimes"]["active"] == 4
        assert result["operational"]["traces"]["count"] == 42
        assert "subsystems_connected" in result["operational"]

    def test_identity_summary(self):
        sm = SelfModel()
        sm.instance.loaded = True
        sm.instance.ai_name = "TestAI"
        sm.instance.business_stage = "pre_revenue"
        sm.register_subsystems(runtime_graph=_MockRuntimeGraph())
        result = sm.who_am_i()
        summary = result["identity_summary"]
        assert "UMH" in summary
        assert "TestAI" in summary
        assert "pre_revenue" in summary
        assert "4/5 runtimes" in summary

    def test_subsystems_connected_tracks_registrations(self):
        sm = SelfModel()
        sm.register_subsystems(registry=_MockRegistry(), trace_recorder=_MockTraceRecorder())
        result = sm.who_am_i()
        connected = result["operational"]["subsystems_connected"]
        assert "registry" in connected
        assert "trace_recorder" in connected


class TestConfigFileLoading:
    def test_loads_from_config_file(self, tmp_path):
        config = tmp_path / "data" / "umh" / "instance.json"
        config.parent.mkdir(parents=True)
        config.write_text('{"ai_name": "ARIA", "org_name": "TestOrg"}')
        sm = SelfModel()
        os.environ["UMH_ROOT"] = str(tmp_path)
        try:
            sm.load_instance()
        finally:
            del os.environ["UMH_ROOT"]
        assert sm.instance.ai_name == "ARIA"
        assert sm.instance.org_name == "TestOrg"

    def test_env_vars_take_priority_over_config(self, tmp_path):
        config = tmp_path / "data" / "umh" / "instance.json"
        config.parent.mkdir(parents=True)
        config.write_text('{"ai_name": "FromConfig"}')
        sm = SelfModel()
        os.environ["UMH_ROOT"] = str(tmp_path)
        os.environ["AI_NAME"] = "FromEnv"
        try:
            sm.load_instance()
        finally:
            del os.environ["UMH_ROOT"]
            del os.environ["AI_NAME"]
        assert sm.instance.ai_name == "FromEnv"

    def test_missing_config_file_is_fine(self, tmp_path):
        sm = SelfModel()
        os.environ["UMH_ROOT"] = str(tmp_path)
        try:
            sm.load_instance()
        finally:
            del os.environ["UMH_ROOT"]
        assert sm.instance.loaded is True
        assert sm.instance.ai_name == ""


class TestInstanceLoaderRegistration:
    def test_registered_loader_populates_instance(self):
        sm = SelfModel()
        def my_loader(inst):
            inst.ai_name = inst.ai_name or "LoaderAI"
            inst.org_name = "LoaderOrg"
        sm.register_instance_loader(my_loader)
        sm.load_instance()
        assert sm.instance.ai_name == "LoaderAI"
        assert sm.instance.org_name == "LoaderOrg"

    def test_env_vars_take_priority_over_loader(self):
        sm = SelfModel()
        def my_loader(inst):
            inst.ai_name = inst.ai_name or "LoaderAI"
        sm.register_instance_loader(my_loader)
        os.environ["AI_NAME"] = "EnvAI"
        try:
            sm.load_instance()
        finally:
            del os.environ["AI_NAME"]
        assert sm.instance.ai_name == "EnvAI"

    def test_loader_failure_doesnt_crash(self):
        sm = SelfModel()
        def bad_loader(inst):
            raise RuntimeError("boom")
        sm.register_instance_loader(bad_loader)
        sm.load_instance()
        assert sm.instance.loaded is True

    def test_multiple_loaders_run_in_order(self):
        sm = SelfModel()
        calls = []
        def loader_a(inst):
            calls.append("a")
            inst.org_name = "A"
        def loader_b(inst):
            calls.append("b")
            inst.org_name = inst.org_name or "B"
        sm.register_instance_loader(loader_a)
        sm.register_instance_loader(loader_b)
        sm.load_instance()
        assert calls == ["a", "b"]
        assert sm.instance.org_name == "A"


class TestSingleton:
    def test_module_singleton_exists(self):
        from substrate.self_model import self_model
        assert isinstance(self_model, SelfModel)
        assert self_model.canonical is CANONICAL

    def test_self_model_has_no_projection_imports(self):
        """The self-model must never import projection-specific code."""
        import importlib
        from pathlib import Path
        mod = importlib.import_module("substrate.self_model")
        source = Path(mod.__file__).read_text()
        assert "business_instance" not in source
        assert "from projections" not in source
        assert "from services" not in source
        assert "from transports" not in source
