"""Tests for Layer 3 Phase 1 type system — modality, participant, manifest.

Validates:
- ModalityType enum values and str behavior
- ParticipantType enum values and str behavior
- AdapterMaturityLevel ordering and IntEnum behavior
- AdapterManifest construction, methods, serialization
- AdapterDescriptor backward compat with new optional fields
- AdapterRegistry manifest registration and modality/participant queries
"""

import sys
import os

sys.path.insert(
    0,
    os.environ.get("UMH_ROOT")
    or os.environ.get("OS_ROOT")
    or os.environ.get("EOS_ROOT")
    or "/opt/OS",
)

import unittest

from adapters.adapter_engine.modality import ModalityType
from adapters.adapter_engine.participant import ParticipantType
from adapters.adapter_engine.adapter_manifest import (
    AdapterManifest,
    AdapterMaturityLevel,
)
from adapters.adapter_engine.adapter_registry_contracts import (
    AdapterDescriptor,
    AdapterRegistry,
    CapabilityDescriptor,
)
from execution.runtime.worker_runtime_contracts import (
    AuthorityDomain,
    MessageBusType,
)


class TestModalityType(unittest.TestCase):
    def test_enum_values(self):
        self.assertEqual(ModalityType.API, "api")
        self.assertEqual(ModalityType.COMPUTER_USE, "computer_use")
        self.assertEqual(ModalityType.FILESYSTEM, "filesystem")
        self.assertEqual(ModalityType.DIRECT_DB, "direct_db")

    def test_all_values_present(self):
        self.assertEqual(len(ModalityType), 4)

    def test_str_comparison(self):
        self.assertTrue(ModalityType.API == "api")
        self.assertIsInstance(ModalityType.API, str)

    def test_construction_from_value(self):
        self.assertEqual(ModalityType("api"), ModalityType.API)
        self.assertEqual(ModalityType("filesystem"), ModalityType.FILESYSTEM)


class TestParticipantType(unittest.TestCase):
    def test_enum_values(self):
        self.assertEqual(ParticipantType.ECOSYSTEM, "ecosystem")
        self.assertEqual(ParticipantType.EXTERNAL, "external")

    def test_all_values_present(self):
        self.assertEqual(len(ParticipantType), 2)

    def test_str_comparison(self):
        self.assertTrue(ParticipantType.ECOSYSTEM == "ecosystem")
        self.assertIsInstance(ParticipantType.EXTERNAL, str)

    def test_construction_from_value(self):
        self.assertEqual(ParticipantType("ecosystem"), ParticipantType.ECOSYSTEM)
        self.assertEqual(ParticipantType("external"), ParticipantType.EXTERNAL)


class TestAdapterMaturityLevel(unittest.TestCase):
    def test_level_ordering(self):
        self.assertLess(
            AdapterMaturityLevel.L0_REGISTERED,
            AdapterMaturityLevel.L7_MASTERFUL,
        )
        self.assertLess(
            AdapterMaturityLevel.L3_TESTED,
            AdapterMaturityLevel.L4_EDGE_CASES_MAPPED,
        )

    def test_all_eight_levels(self):
        self.assertEqual(len(AdapterMaturityLevel), 8)

    def test_int_values(self):
        self.assertEqual(int(AdapterMaturityLevel.L0_REGISTERED), 0)
        self.assertEqual(int(AdapterMaturityLevel.L7_MASTERFUL), 7)

    def test_comparison_with_int(self):
        self.assertTrue(AdapterMaturityLevel.L3_TESTED >= 3)
        self.assertTrue(AdapterMaturityLevel.L0_REGISTERED < 1)


class TestAdapterManifest(unittest.TestCase):
    def _make_manifest(self, **overrides):
        defaults = {
            "adapter_id": "test_adapter",
            "adapter_type": "test",
            "modalities": [ModalityType.API],
            "participant_type": ParticipantType.EXTERNAL,
        }
        defaults.update(overrides)
        return AdapterManifest(**defaults)

    def test_basic_construction(self):
        m = self._make_manifest()
        self.assertEqual(m.adapter_id, "test_adapter")
        self.assertEqual(m.adapter_type, "test")
        self.assertEqual(m.modalities, [ModalityType.API])
        self.assertEqual(m.participant_type, ParticipantType.EXTERNAL)
        self.assertEqual(m.maturity, AdapterMaturityLevel.L0_REGISTERED)
        self.assertEqual(m.version, "v1")
        self.assertEqual(m.capabilities, [])
        self.assertEqual(m.notes, [])

    def test_multi_modality(self):
        m = self._make_manifest(
            modalities=[ModalityType.API, ModalityType.FILESYSTEM],
        )
        self.assertEqual(len(m.modalities), 2)
        self.assertTrue(m.uses_modality(ModalityType.API))
        self.assertTrue(m.uses_modality(ModalityType.FILESYSTEM))
        self.assertFalse(m.uses_modality(ModalityType.DIRECT_DB))

    def test_ecosystem_property(self):
        eco = self._make_manifest(participant_type=ParticipantType.ECOSYSTEM)
        ext = self._make_manifest(participant_type=ParticipantType.EXTERNAL)
        self.assertTrue(eco.is_ecosystem)
        self.assertFalse(ext.is_ecosystem)

    def test_supports_action(self):
        cap = CapabilityDescriptor(
            capability_id="read_doc",
            action_type="read_document",
        )
        m = self._make_manifest(capabilities=[cap])
        self.assertTrue(m.supports("read_document"))
        self.assertFalse(m.supports("write_document"))

    def test_get_capability(self):
        cap = CapabilityDescriptor(
            capability_id="read_doc",
            action_type="read_document",
        )
        m = self._make_manifest(capabilities=[cap])
        found = m.get_capability("read_document")
        self.assertIsNotNone(found)
        self.assertEqual(found.capability_id, "read_doc")
        self.assertIsNone(m.get_capability("nonexistent"))

    def test_maturity_override(self):
        m = self._make_manifest(maturity=AdapterMaturityLevel.L3_TESTED)
        self.assertEqual(m.maturity, AdapterMaturityLevel.L3_TESTED)

    def test_to_dict_serialization(self):
        cap = CapabilityDescriptor(
            capability_id="ping",
            action_type="ping",
        )
        m = self._make_manifest(
            modalities=[ModalityType.API, ModalityType.FILESYSTEM],
            capabilities=[cap],
            maturity=AdapterMaturityLevel.L2_CAPABILITIES_KNOWN,
        )
        d = m.to_dict()
        self.assertEqual(d["adapter_id"], "test_adapter")
        self.assertEqual(d["modalities"], ["api", "filesystem"])
        self.assertEqual(d["participant_type"], "external")
        self.assertEqual(d["maturity"], 2)
        self.assertEqual(d["maturity_label"], "L2_CAPABILITIES_KNOWN")
        self.assertEqual(len(d["capabilities"]), 1)
        self.assertEqual(d["capabilities"][0]["action_type"], "ping")


class TestAdapterDescriptorBackwardCompat(unittest.TestCase):
    def test_old_construction_still_works(self):
        adapter = AdapterDescriptor(
            adapter_id="legacy",
            adapter_type="gui_actuator",
            environment_type="local_windows_desktop",
            authority_domain=AuthorityDomain.LOCAL_GUI,
            message_bus=MessageBusType.FILESYSTEM_JSON,
        )
        self.assertIsNone(adapter.modalities)
        self.assertIsNone(adapter.participant_type)
        self.assertTrue(adapter.supports("") is False)

    def test_new_fields_populated(self):
        adapter = AdapterDescriptor(
            adapter_id="notion",
            adapter_type="notion_adapter",
            environment_type="cloud",
            authority_domain=AuthorityDomain.LOCAL_SHELL,
            message_bus=MessageBusType.DIRECT_CALL,
            modalities=[ModalityType.API],
            participant_type=ParticipantType.EXTERNAL,
        )
        self.assertEqual(adapter.modalities, [ModalityType.API])
        self.assertEqual(adapter.participant_type, ParticipantType.EXTERNAL)


class TestRegistryManifestIntegration(unittest.TestCase):
    def test_register_manifest(self):
        registry = AdapterRegistry()
        manifest = AdapterManifest(
            adapter_id="drive_adapter",
            adapter_type="google_drive",
            modalities=[ModalityType.API, ModalityType.FILESYSTEM],
            participant_type=ParticipantType.EXTERNAL,
            capabilities=[
                CapabilityDescriptor(
                    capability_id="list_files",
                    action_type="list_files",
                ),
            ],
        )
        registry.register_manifest(manifest)
        self.assertIn("drive_adapter", registry.adapters)
        found = registry.find_adapter_for_action("list_files")
        self.assertIsNotNone(found)
        self.assertEqual(found.adapter_id, "drive_adapter")
        self.assertEqual(found.modalities, [ModalityType.API, ModalityType.FILESYSTEM])
        self.assertEqual(found.participant_type, ParticipantType.EXTERNAL)

    def test_find_by_modality(self):
        registry = AdapterRegistry()
        api_adapter = AdapterDescriptor(
            adapter_id="api_only",
            adapter_type="test",
            environment_type="cloud",
            authority_domain=AuthorityDomain.LOCAL_SHELL,
            message_bus=MessageBusType.DIRECT_CALL,
            modalities=[ModalityType.API],
        )
        fs_adapter = AdapterDescriptor(
            adapter_id="fs_only",
            adapter_type="test",
            environment_type="local",
            authority_domain=AuthorityDomain.LOCAL_SHELL,
            message_bus=MessageBusType.DIRECT_CALL,
            modalities=[ModalityType.FILESYSTEM],
        )
        legacy_adapter = AdapterDescriptor(
            adapter_id="legacy",
            adapter_type="test",
            environment_type="local",
            authority_domain=AuthorityDomain.LOCAL_SHELL,
            message_bus=MessageBusType.DIRECT_CALL,
        )
        registry.register_adapter(api_adapter)
        registry.register_adapter(fs_adapter)
        registry.register_adapter(legacy_adapter)

        api_results = registry.find_by_modality(ModalityType.API)
        self.assertEqual(len(api_results), 1)
        self.assertEqual(api_results[0].adapter_id, "api_only")

        fs_results = registry.find_by_modality(ModalityType.FILESYSTEM)
        self.assertEqual(len(fs_results), 1)
        self.assertEqual(fs_results[0].adapter_id, "fs_only")

        db_results = registry.find_by_modality(ModalityType.DIRECT_DB)
        self.assertEqual(len(db_results), 0)

    def test_find_by_participant_type(self):
        registry = AdapterRegistry()
        eco = AdapterDescriptor(
            adapter_id="eos",
            adapter_type="eos_adapter",
            environment_type="local",
            authority_domain=AuthorityDomain.LOCAL_SHELL,
            message_bus=MessageBusType.DIRECT_CALL,
            participant_type=ParticipantType.ECOSYSTEM,
        )
        ext = AdapterDescriptor(
            adapter_id="notion",
            adapter_type="notion_adapter",
            environment_type="cloud",
            authority_domain=AuthorityDomain.LOCAL_SHELL,
            message_bus=MessageBusType.DIRECT_CALL,
            participant_type=ParticipantType.EXTERNAL,
        )
        legacy = AdapterDescriptor(
            adapter_id="legacy",
            adapter_type="test",
            environment_type="local",
            authority_domain=AuthorityDomain.LOCAL_SHELL,
            message_bus=MessageBusType.DIRECT_CALL,
        )
        registry.register_adapter(eco)
        registry.register_adapter(ext)
        registry.register_adapter(legacy)

        eco_results = registry.find_by_participant_type(ParticipantType.ECOSYSTEM)
        self.assertEqual(len(eco_results), 1)
        self.assertEqual(eco_results[0].adapter_id, "eos")

        ext_results = registry.find_by_participant_type(ParticipantType.EXTERNAL)
        self.assertEqual(len(ext_results), 1)
        self.assertEqual(ext_results[0].adapter_id, "notion")

    def test_legacy_adapters_excluded_from_modality_search(self):
        registry = AdapterRegistry()
        legacy = AdapterDescriptor(
            adapter_id="legacy",
            adapter_type="test",
            environment_type="local",
            authority_domain=AuthorityDomain.LOCAL_SHELL,
            message_bus=MessageBusType.DIRECT_CALL,
        )
        registry.register_adapter(legacy)
        self.assertEqual(registry.find_by_modality(ModalityType.API), [])


class TestArchitectureCatalogAnnotations(unittest.TestCase):
    """Verify the adapter catalog from Architecture doc §2.4 is representable."""

    def test_eos_ecosystem_direct_db(self):
        m = AdapterManifest(
            adapter_id="eos",
            adapter_type="eos",
            modalities=[ModalityType.DIRECT_DB],
            participant_type=ParticipantType.ECOSYSTEM,
        )
        self.assertTrue(m.is_ecosystem)
        self.assertTrue(m.uses_modality(ModalityType.DIRECT_DB))

    def test_notion_external_api(self):
        m = AdapterManifest(
            adapter_id="notion",
            adapter_type="notion",
            modalities=[ModalityType.API],
            participant_type=ParticipantType.EXTERNAL,
        )
        self.assertFalse(m.is_ecosystem)
        self.assertTrue(m.uses_modality(ModalityType.API))

    def test_github_external_multi_modality(self):
        m = AdapterManifest(
            adapter_id="github",
            adapter_type="github",
            modalities=[ModalityType.API, ModalityType.FILESYSTEM],
            participant_type=ParticipantType.EXTERNAL,
        )
        self.assertTrue(m.uses_modality(ModalityType.API))
        self.assertTrue(m.uses_modality(ModalityType.FILESYSTEM))
        self.assertFalse(m.uses_modality(ModalityType.COMPUTER_USE))

    def test_windows_dev_external_fs_cu(self):
        m = AdapterManifest(
            adapter_id="windows_dev",
            adapter_type="windows_dev",
            modalities=[ModalityType.FILESYSTEM, ModalityType.COMPUTER_USE],
            participant_type=ParticipantType.EXTERNAL,
        )
        self.assertTrue(m.uses_modality(ModalityType.FILESYSTEM))
        self.assertTrue(m.uses_modality(ModalityType.COMPUTER_USE))


if __name__ == "__main__":
    unittest.main()
