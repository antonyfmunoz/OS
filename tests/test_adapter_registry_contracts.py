"""Tests for adapter registry contracts -- Phase 96.8K."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

import unittest
from pathlib import Path

from adapters.adapter_engine.adapter_registry_contracts import (
    AdapterDescriptor,
    AdapterRegistry,
    CapabilityDescriptor,
)
from execution.runtime.worker_runtime_contracts import (
    AuthorityDomain,
    MessageBusType,
)

REGISTRY_FIXTURE = Path(_ROOT) / "data" / "registries" / "local_worker_adapter_registry_v1.json"


class TestCapabilityDescriptor(unittest.TestCase):
    def test_ping_does_not_require_gui(self):
        cap = CapabilityDescriptor(
            capability_id="ping",
            action_type="ping",
            requires_gui=False,
        )
        self.assertFalse(cap.requires_gui)

    def test_open_application_url_requires_gui(self):
        cap = CapabilityDescriptor(
            capability_id="open_application_url",
            action_type="open_application_url",
            requires_gui=True,
            required_authority=AuthorityDomain.LOCAL_GUI,
        )
        self.assertTrue(cap.requires_gui)
        self.assertEqual(cap.required_authority, AuthorityDomain.LOCAL_GUI)


class TestAdapterDescriptor(unittest.TestCase):
    def test_windows_relay_supports_ping_and_chrome(self):
        adapter = AdapterDescriptor(
            adapter_id="windows_interactive_desktop_relay",
            adapter_type="gui_actuator",
            environment_type="local_windows_desktop",
            authority_domain=AuthorityDomain.LOCAL_GUI,
            message_bus=MessageBusType.FILESYSTEM_JSON,
            capabilities=[
                CapabilityDescriptor(
                    capability_id="ping",
                    action_type="ping",
                ),
                CapabilityDescriptor(
                    capability_id="open_application_url",
                    action_type="open_application_url",
                    requires_gui=True,
                    required_authority=AuthorityDomain.LOCAL_GUI,
                ),
            ],
        )
        self.assertTrue(adapter.supports("ping"))
        self.assertTrue(adapter.supports("open_application_url"))
        self.assertFalse(adapter.supports("screenshot"))

    def test_get_capability_returns_correct_cap(self):
        adapter = AdapterDescriptor(
            adapter_id="test",
            adapter_type="test",
            environment_type="test",
            authority_domain=AuthorityDomain.LOCAL_GUI,
            message_bus=MessageBusType.FILESYSTEM_JSON,
            capabilities=[
                CapabilityDescriptor(
                    capability_id="open_application_url",
                    action_type="open_application_url",
                    requires_gui=True,
                    required_authority=AuthorityDomain.LOCAL_GUI,
                ),
            ],
        )
        cap = adapter.get_capability("open_application_url")
        self.assertIsNotNone(cap)
        self.assertTrue(cap.requires_gui)
        self.assertIsNone(adapter.get_capability("nonexistent"))


class TestAdapterRegistry(unittest.TestCase):
    def test_register_and_find(self):
        registry = AdapterRegistry()
        adapter = AdapterDescriptor(
            adapter_id="test_adapter",
            adapter_type="test",
            environment_type="test",
            authority_domain=AuthorityDomain.LOCAL_GUI,
            message_bus=MessageBusType.FILESYSTEM_JSON,
            capabilities=[
                CapabilityDescriptor(
                    capability_id="ping",
                    action_type="ping",
                ),
            ],
        )
        registry.register_adapter(adapter)
        found = registry.find_adapter_for_action("ping")
        self.assertIsNotNone(found)
        self.assertEqual(found.adapter_id, "test_adapter")

    def test_find_returns_none_for_unknown(self):
        registry = AdapterRegistry()
        self.assertIsNone(registry.find_adapter_for_action("unknown"))

    def test_find_gui_adapter(self):
        registry = AdapterRegistry()
        gui = AdapterDescriptor(
            adapter_id="gui_adapter",
            adapter_type="gui_actuator",
            environment_type="local_windows_desktop",
            authority_domain=AuthorityDomain.LOCAL_GUI,
            message_bus=MessageBusType.FILESYSTEM_JSON,
        )
        shell = AdapterDescriptor(
            adapter_id="shell_adapter",
            adapter_type="shell",
            environment_type="local_wsl",
            authority_domain=AuthorityDomain.LOCAL_SHELL,
            message_bus=MessageBusType.FILESYSTEM_JSON,
        )
        registry.register_adapter(gui)
        registry.register_adapter(shell)
        found = registry.find_gui_adapter()
        self.assertIsNotNone(found)
        self.assertEqual(found.adapter_id, "gui_adapter")


class TestRegistryFixtureLoading(unittest.TestCase):
    def test_fixture_file_exists(self):
        self.assertTrue(REGISTRY_FIXTURE.exists())

    def test_fixture_loads_successfully(self):
        registry = AdapterRegistry.from_json_file(REGISTRY_FIXTURE)
        self.assertIn("windows_interactive_desktop_relay", registry.adapters)

    def test_fixture_windows_relay_declares_gui_authority(self):
        registry = AdapterRegistry.from_json_file(REGISTRY_FIXTURE)
        adapter = registry.adapters["windows_interactive_desktop_relay"]
        self.assertEqual(adapter.authority_domain, AuthorityDomain.LOCAL_GUI)

    def test_fixture_wsl_worker_does_not_declare_gui(self):
        registry = AdapterRegistry.from_json_file(REGISTRY_FIXTURE)
        wsl = registry.workers.get("local_wsl_worker", {})
        self.assertFalse(wsl.get("can_own_gui", False))

    def test_fixture_open_application_url_requires_windows_relay(self):
        registry = AdapterRegistry.from_json_file(REGISTRY_FIXTURE)
        adapter = registry.find_adapter_for_action("open_application_url")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.adapter_id, "windows_interactive_desktop_relay")
        cap = adapter.get_capability("open_application_url")
        self.assertTrue(cap.requires_gui)

    def test_fixture_ping_routable_through_filesystem_json(self):
        registry = AdapterRegistry.from_json_file(REGISTRY_FIXTURE)
        adapter = registry.find_adapter_for_action("ping")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.message_bus, MessageBusType.FILESYSTEM_JSON)

    def test_fixture_windows_relay_uses_filesystem_json(self):
        registry = AdapterRegistry.from_json_file(REGISTRY_FIXTURE)
        adapter = registry.adapters["windows_interactive_desktop_relay"]
        self.assertEqual(adapter.message_bus, MessageBusType.FILESYSTEM_JSON)


if __name__ == "__main__":
    unittest.main()
