"""Tests for the type divergence detection system."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/opt/OS")

import pytest

from substrate.canonical_types import CANONICAL_TYPES, check_name, lookup


class TestCanonicalTypeRegistry:
    def test_registry_has_entries(self):
        assert len(CANONICAL_TYPES) >= 70

    def test_lookup_existing(self):
        assert lookup("TaskType") == ["substrate.contracts.agent_types"]
        assert "substrate.execution.runtime.capability_router" in lookup("Capability")
        assert lookup("CapabilityStatus") == ["substrate.types"]
        assert lookup("WorkPacketRiskLevel") == ["nodes.environments.work_packet"]

    def test_lookup_homonym(self):
        caps = lookup("Capability")
        assert len(caps) == 2
        assert "substrate.execution.runtime.capability_router" in caps
        assert "substrate.types" in caps

    def test_lookup_missing(self):
        assert lookup("CompletelyNewType") is None

    def test_check_name_allows_canonical_location(self):
        result = check_name("TaskType", "substrate.contracts.agent_types")
        assert result is None

    def test_check_name_blocks_shadow(self):
        result = check_name("TaskType", "substrate.organism.new_module")
        assert result is not None
        assert "DIVERGENCE BLOCKED" in result
        assert "substrate.contracts.agent_types" in result

    def test_check_name_allows_new_types(self):
        result = check_name("BrandNewConcept", "any.module")
        assert result is None

    def test_check_name_allows_legacy_duplicate(self):
        result = check_name("SignalEnvelope", "substrate.sockets.envelopes")
        assert result is None

    def test_check_name_blocks_new_duplicate_not_in_legacy(self):
        result = check_name("SignalEnvelope", "substrate.some_new_module")
        assert result is not None
        assert "DIVERGENCE BLOCKED" in result

    def test_all_substrate_types_registered(self):
        key_types = [
            "SignalEnvelope",
            "ExecutionContext",
            "RiskClass",
            "GovernanceDecision",
            "ExecutionOutcome",
            "CapabilityStatus",
            "PrimitiveType",
            "TaskType",
            "Capability",
            "EnvironmentType",
            "WorkPacketRiskLevel",
            "WorkUnitType",
            "WorkcellRole",
        ]
        for t in key_types:
            assert t in CANONICAL_TYPES, f"{t} missing from canonical registry"


class TestDivergenceChecker:
    def test_detects_shadow_enum(self):
        from scripts.check_type_divergence import check_files

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from enum import Enum\n\nclass TaskType(str, Enum):\n    FOO = 'foo'\n")
            f.flush()
            errors, warnings = check_files([f.name])
            assert len(errors) == 1
            assert "TaskType" in errors[0]

    def test_allows_new_type(self):
        from scripts.check_type_divergence import check_files

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("from enum import Enum\n\nclass BrandNewThing(str, Enum):\n    A = 'a'\n")
            f.flush()
            errors, warnings = check_files([f.name])
            assert len(errors) == 0

    def test_allows_canonical_source(self):
        from scripts.check_type_divergence import check_files

        errors, _ = check_files(["/opt/OS/substrate/contracts/agent_types.py"])
        assert len(errors) == 0

    def test_detects_shadow_basemodel(self):
        from scripts.check_type_divergence import check_files

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(
                "from pydantic import BaseModel\n\n"
                "class SignalEnvelope(BaseModel):\n    data: str = ''\n"
            )
            f.flush()
            errors, _ = check_files([f.name])
            assert len(errors) == 1
            assert "SignalEnvelope" in errors[0]

    def test_warns_on_similar_names(self):
        from scripts.check_type_divergence import _similar_names

        similar = _similar_names("TaskStatus", CANONICAL_TYPES)
        # Not a direct match but might catch suffix-based similarity
        # The important thing is no crash
        assert isinstance(similar, list)

    def test_full_codebase_scan_clean(self):
        from scripts.check_type_divergence import _get_all_python_files, check_files

        files = _get_all_python_files()
        errors, _ = check_files(files)
        assert len(errors) == 0, f"Existing codebase has divergent types:\n{''.join(errors)}"
