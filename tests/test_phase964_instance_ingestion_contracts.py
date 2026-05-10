"""Tests for Phase 96.4 instance ingestion contracts."""

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest

from eos_ai.substrate.instance_ingestion_contracts import (
    InstanceSourceContext,
    build_w0_001_instance_context,
)
from eos_ai.substrate.memory_scope_contracts import MemoryScope


class TestInstanceSourceContext(unittest.TestCase):
    """Tests for InstanceSourceContext serialization."""

    def test_serializes_correctly(self) -> None:
        ctx = InstanceSourceContext(
            instance_id="test_inst",
            account="test@example.com",
            source_system="TestSystem",
            source_owner="Test Owner",
        )
        d = ctx.to_dict()
        self.assertEqual(d["instance_id"], "test_inst")
        self.assertEqual(d["account"], "test@example.com")
        self.assertEqual(d["source_system"], "TestSystem")
        self.assertEqual(d["source_owner"], "Test Owner")
        self.assertIn("default_memory_scope", d)
        self.assertIn("allowed_memory_scopes", d)
        self.assertIn("global_canon_allowed_by_default", d)


class TestW0001InstanceContext(unittest.TestCase):
    """Tests for the W0-001 instance context builder."""

    def setUp(self) -> None:
        self.ctx = build_w0_001_instance_context()

    def test_instance_id(self) -> None:
        self.assertEqual(self.ctx.instance_id, "antony_empyrean")

    def test_account(self) -> None:
        self.assertEqual(self.ctx.account, "antonyfm@empyreanstudios.co")

    def test_default_memory_scope_is_instance(self) -> None:
        self.assertEqual(self.ctx.default_memory_scope, MemoryScope.INSTANCE_MEMORY)

    def test_global_canon_not_allowed(self) -> None:
        self.assertFalse(self.ctx.global_canon_allowed_by_default)

    def test_source_system(self) -> None:
        self.assertEqual(self.ctx.source_system, "Google Drive / Google Docs")

    def test_source_owner(self) -> None:
        self.assertEqual(self.ctx.source_owner, "Antony F. Munoz")


if __name__ == "__main__":
    unittest.main()
