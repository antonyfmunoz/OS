"""Layer 3 Phase 2 Slice E — vertical thin slice on GoogleDriveAdapterV1.

Proves the full Phase 2 pipeline end-to-end on a real adapter:
manifest construction → register_from_manifest() → execution tracking
→ maturity computation → to_dict() serialization → JSON round-trip.
"""

from __future__ import annotations

import json
import os
import sys
import unittest

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(
    0,
    os.environ.get("UMH_ROOT")
    or os.environ.get("OS_ROOT")
    or os.environ.get("EOS_ROOT")
    or _REPO_ROOT,
)

from adapters.adapter_engine.adapter_manifest import AdapterManifest, AdapterMaturityLevel
from adapters.adapter_engine.adapter_lifecycle_manager_v1 import (
    AdapterLifecycleManager,
    AdapterHealthRecord,
)
from adapters.adapter_engine.google_drive_adapter_v1 import GoogleDriveAdapterV1
from adapters.adapter_engine.modality import ModalityType
from adapters.adapter_engine.participant import ParticipantType


class TestGoogleDriveManifest(unittest.TestCase):
    def test_manifest_fields_valid(self) -> None:
        m = GoogleDriveAdapterV1.MANIFEST
        self.assertEqual(m.adapter_id, "google-drive-adapter-v1")
        self.assertEqual(m.adapter_type, "google_drive")
        self.assertEqual(m.modalities, [ModalityType.API])
        self.assertEqual(m.participant_type, ParticipantType.EXTERNAL)
        self.assertEqual(len(m.capabilities), 1)
        self.assertEqual(m.capabilities[0].action_type, "GOOGLE_DRIVE_SAFE_OPEN")
        self.assertEqual(m.maturity, AdapterMaturityLevel.L0_REGISTERED)
        self.assertEqual(m.version, "v1")

    def test_manifest_adapter_id_matches_class_constant(self) -> None:
        self.assertEqual(
            GoogleDriveAdapterV1.MANIFEST.adapter_id,
            GoogleDriveAdapterV1.ADAPTER_ID,
        )


class TestRegisterFromManifest(unittest.TestCase):
    def test_register_from_manifest_creates_health_record(self) -> None:
        mgr = AdapterLifecycleManager()
        record = mgr.register_from_manifest(GoogleDriveAdapterV1.MANIFEST)
        self.assertIsInstance(record, AdapterHealthRecord)
        self.assertEqual(record.adapter_id, "google-drive-adapter-v1")
        self.assertEqual(record.adapter_type, "google_drive")
        self.assertEqual(record.maturity, AdapterMaturityLevel.L0_REGISTERED)
        self.assertEqual(record.capabilities, ["GOOGLE_DRIVE_SAFE_OPEN"])

    def test_register_from_manifest_delegates_to_register_adapter(self) -> None:
        mgr = AdapterLifecycleManager()
        from_manifest = mgr.register_from_manifest(GoogleDriveAdapterV1.MANIFEST)

        mgr2 = AdapterLifecycleManager()
        from_manual = mgr2.register_adapter(
            adapter_id="google-drive-adapter-v1",
            adapter_type="google_drive",
            capabilities=["GOOGLE_DRIVE_SAFE_OPEN"],
        )

        self.assertEqual(from_manifest.adapter_id, from_manual.adapter_id)
        self.assertEqual(from_manifest.adapter_type, from_manual.adapter_type)
        self.assertEqual(from_manifest.capabilities, from_manual.capabilities)
        self.assertEqual(from_manifest.maturity, from_manual.maturity)
        self.assertEqual(from_manifest.state, from_manual.state)


class TestFullPipeline(unittest.TestCase):
    def test_execution_advances_maturity_through_pipeline(self) -> None:
        mgr = AdapterLifecycleManager()
        mgr.register_from_manifest(GoogleDriveAdapterV1.MANIFEST)
        adapter_id = GoogleDriveAdapterV1.MANIFEST.adapter_id

        record = mgr.get_adapter(adapter_id)
        self.assertEqual(record.maturity, AdapterMaturityLevel.L0_REGISTERED)

        mgr.record_execution_success(adapter_id)
        record = mgr.get_adapter(adapter_id)
        # L1_CONNECTED is skipped: L2 subsumes L1 when capabilities are non-empty.
        # _build_evidence() sets auth_verified=True and capability_count=1,
        # satisfying both L1 (auth_verified) and L2 (auth_verified + capability_count>0).
        # Walk-down-from-top returns L2 as the highest level where all predicates pass.
        self.assertEqual(record.maturity, AdapterMaturityLevel.L2_CAPABILITIES_KNOWN)

        for _ in range(10):
            mgr.record_execution_success(adapter_id)
        record = mgr.get_adapter(adapter_id)
        self.assertEqual(record.total_executions, 11)
        self.assertEqual(record.maturity, AdapterMaturityLevel.L3_TESTED)

    def test_to_dict_serialization_includes_maturity(self) -> None:
        mgr = AdapterLifecycleManager()
        mgr.register_from_manifest(GoogleDriveAdapterV1.MANIFEST)
        adapter_id = GoogleDriveAdapterV1.MANIFEST.adapter_id

        for _ in range(11):
            mgr.record_execution_success(adapter_id)

        record = mgr.get_adapter(adapter_id)
        d = record.to_dict()
        self.assertIn("maturity", d)
        self.assertIn("maturity_label", d)
        self.assertEqual(d["maturity"], AdapterMaturityLevel.L3_TESTED.value)
        self.assertEqual(d["maturity_label"], "L3_TESTED")

    def test_serialization_round_trip(self) -> None:
        mgr = AdapterLifecycleManager()
        mgr.register_from_manifest(GoogleDriveAdapterV1.MANIFEST)
        adapter_id = GoogleDriveAdapterV1.MANIFEST.adapter_id

        for _ in range(11):
            mgr.record_execution_success(adapter_id)

        record = mgr.get_adapter(adapter_id)
        serialized = json.dumps(record.to_dict())
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["maturity_label"], "L3_TESTED")
        self.assertEqual(deserialized["adapter_id"], "google-drive-adapter-v1")


if __name__ == "__main__":
    unittest.main()
