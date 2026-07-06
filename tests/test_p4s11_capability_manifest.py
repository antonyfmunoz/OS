"""P4S-11 — capability registry manifest tests.

Verifies the manifest (data/umh/capabilities/capability_manifest.json) unifies
the 28 substrate job capabilities with the projection governed action types,
each pointing to exactly one canonical home.

Packet tests (from p4_sync_workgraph.json::P4S-11):
  - manifest resolves every declared capability
  - no duplicate capability keys

Plus the P4S-11 stop-condition guard: no capability defined in two homes.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from substrate.execution.runtime.capability_router import (  # noqa: E402
    Capability,
    audit_capability_registry,
    load_capability_manifest,
)


def test_manifest_loads() -> None:
    m = load_capability_manifest()
    assert isinstance(m, dict)
    assert m.get("packet") == "P4S-11"
    assert "substrate_capabilities" in m
    assert "projection_action_types" in m


def test_manifest_resolves_every_declared_capability() -> None:
    """Every substrate capability key resolves to a real Capability enum member."""
    m = load_capability_manifest()
    report = audit_capability_registry(m)
    assert report["resolved_all"] is True, report["violations"]
    enum_by_value = {c.value: c for c in Capability}
    for row in m["substrate_capabilities"]:
        member = enum_by_value.get(row["key"])
        assert member is not None, f"unresolved capability key: {row['key']}"
        assert row["enum_member"] == member.name


def test_manifest_matches_enum_exactly() -> None:
    """Manifest substrate set equals the Capability enum (count + keys)."""
    m = load_capability_manifest()
    enum_keys = {c.value for c in Capability}
    manifest_keys = {row["key"] for row in m["substrate_capabilities"]}
    assert manifest_keys == enum_keys
    assert len(m["substrate_capabilities"]) == len(list(Capability)) == 28


def test_no_duplicate_capability_keys() -> None:
    m = load_capability_manifest()
    sub_keys = [row["key"] for row in m["substrate_capabilities"]]
    assert len(sub_keys) == len(set(sub_keys)), "duplicate substrate capability keys"
    proj_pairs = [(row.get("projection"), row["key"]) for row in m["projection_action_types"]]
    assert len(proj_pairs) == len(set(proj_pairs)), "duplicate projection action-type keys"


def test_no_capability_defined_in_two_homes() -> None:
    """P4S-11 stop condition: substrate and projection namespaces are disjoint."""
    m = load_capability_manifest()
    report = audit_capability_registry(m)
    assert report["namespaces_disjoint"] is True, report["violations"]
    sub_keys = {row["key"] for row in m["substrate_capabilities"]}
    proj_keys = {row["key"] for row in m["projection_action_types"]}
    assert sub_keys.isdisjoint(proj_keys)


def test_registry_audit_truthful() -> None:
    """The full audit passes with zero violations (the packet proof)."""
    report = audit_capability_registry()
    assert report["ok"] is True, report["violations"]
    assert report["violations"] == []
    assert report["substrate_capability_count"] == 28
    assert report["enum_capability_count"] == 28
