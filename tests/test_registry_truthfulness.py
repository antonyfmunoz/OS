"""WP-P2-001 — negative-control tests for the registry truthfulness audit.

Proves the hardened `verify_registry_truthful()` genuinely FAILS on injected
divergence (not a rubber stamp) and PASSES on the corrected tree. Each test
mutates the in-memory registry, asserts the specific failure, and restores it.
"""

from __future__ import annotations

import copy

import pytest

import scripts.check_type_divergence as gate
import substrate.canonical_types as ct


@pytest.fixture(autouse=True)
def _restore_registry():
    """Snapshot + restore the mutable registry structures around each test."""
    canon = copy.deepcopy(ct.CANONICAL_TYPES)
    meta = copy.deepcopy(ct.LEGACY_DUPLICATES_META)
    yield
    ct.CANONICAL_TYPES.clear()
    ct.CANONICAL_TYPES.update(canon)
    ct.LEGACY_DUPLICATES_META.clear()
    ct.LEGACY_DUPLICATES_META.update(meta)


# ── the corrected tree passes ────────────────────────────────────────────────


def test_audit_passes_on_clean_tree():
    assert gate.verify_registry_truthful() == []


# ── negative controls: each must FAIL ────────────────────────────────────────


def test_fails_on_stale_registry_entry():
    ct.CANONICAL_TYPES["ZZZ_DoesNotExist"] = ["substrate.types"]
    errors = gate.verify_registry_truthful()
    assert any("STALE REGISTRY ENTRY" in e and "ZZZ_DoesNotExist" in e for e in errors)


def test_fails_on_dead_exemption():
    ct.LEGACY_DUPLICATES_META["substrate.types"] = {
        "NoSuchSymbol": {"owner": "x", "sunset": "2099-01-01", "rationale": "y"},
    }
    errors = gate.verify_registry_truthful()
    assert any("DEAD EXEMPTION" in e and "NoSuchSymbol" in e for e in errors)


def test_fails_on_exemption_missing_metadata():
    # Real symbol, but no owner field.
    ct.LEGACY_DUPLICATES_META["substrate.types"] = {
        "RiskClass": {"sunset": "2099-01-01", "rationale": "y"},
    }
    errors = gate.verify_registry_truthful()
    assert any("MISSING METADATA" in e and "owner" in e for e in errors)


def test_fails_on_exemption_past_sunset():
    ct.LEGACY_DUPLICATES_META["substrate.types"] = {
        "RiskClass": {"owner": "x", "sunset": "2020-01-01", "rationale": "y"},
    }
    errors = gate.verify_registry_truthful()
    assert any("PAST SUNSET" in e for e in errors)


def test_fails_on_bad_sunset_format():
    ct.LEGACY_DUPLICATES_META["substrate.types"] = {
        "RiskClass": {"owner": "x", "sunset": "not-a-date", "rationale": "y"},
    }
    errors = gate.verify_registry_truthful()
    assert any("BAD SUNSET" in e for e in errors)


# ── duplicate-key detection reads the SOURCE literal ─────────────────────────


def test_duplicate_key_detector_reads_source():
    # The corrected source has zero duplicate keys.
    assert gate._registry_source_dup_keys() == []


# ── the audit CLI mode returns the right exit code ───────────────────────────


def test_registry_audit_mode_exits_zero_on_clean_tree():
    assert gate._run_registry_audit() == 0
