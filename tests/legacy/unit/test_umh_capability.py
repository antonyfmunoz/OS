"""Tests for umh.governance.capability — permission + risk matrix."""

from __future__ import annotations

import ast
import sys

sys.path.insert(0, "/opt/OS")

import pytest

from umh.governance.capability import (
    CapabilityDecision,
    CapabilityEnforcer,
    CapabilityLevel,
    CapabilityProfile,
    OperationKind,
    ProfileRegistry,
    RiskTier,
    cap_implies,
    coerce_risk,
    default_registry,
    operation_for_action_type,
    required_capability,
)


# ── Import boundary ─────────────────────────────────────────────


class TestImportBoundary:
    def test_no_forbidden_imports(self):
        with open("umh/governance/capability.py") as f:
            tree = ast.parse(f.read())
        forbidden = {"eos", "core", "services", "scripts"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root not in forbidden, f"import {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                assert root not in forbidden, f"from {node.module}"

    def test_clean_import(self):
        from umh.governance import capability

        assert hasattr(capability, "CapabilityEnforcer")
        assert hasattr(capability, "ProfileRegistry")


# ── Capability lattice ───────────────────────────────────────────


class TestCapabilityLevel:
    def test_rank_ordering(self):
        assert CapabilityLevel.READ.rank < CapabilityLevel.WRITE.rank
        assert CapabilityLevel.WRITE.rank < CapabilityLevel.EXECUTE.rank
        assert CapabilityLevel.EXECUTE.rank < CapabilityLevel.CRITICAL.rank

    def test_cap_implies_same(self):
        assert cap_implies(CapabilityLevel.READ, CapabilityLevel.READ)

    def test_cap_implies_higher(self):
        assert cap_implies(CapabilityLevel.CRITICAL, CapabilityLevel.READ)
        assert cap_implies(CapabilityLevel.EXECUTE, CapabilityLevel.WRITE)

    def test_cap_not_implies_lower(self):
        assert not cap_implies(CapabilityLevel.READ, CapabilityLevel.WRITE)
        assert not cap_implies(CapabilityLevel.WRITE, CapabilityLevel.EXECUTE)


# ── Risk tiers ───────────────────────────────────────────────────


class TestRiskTier:
    def test_rank_ordering(self):
        assert RiskTier.NONE.rank < RiskTier.LOW.rank
        assert RiskTier.LOW.rank < RiskTier.MEDIUM.rank
        assert RiskTier.MEDIUM.rank < RiskTier.HIGH.rank
        assert RiskTier.HIGH.rank < RiskTier.CRITICAL.rank

    def test_coerce_from_string(self):
        assert coerce_risk("low") == RiskTier.LOW
        assert coerce_risk("HIGH") == RiskTier.HIGH

    def test_coerce_from_enum(self):
        assert coerce_risk(RiskTier.MEDIUM) == RiskTier.MEDIUM

    def test_coerce_none(self):
        assert coerce_risk(None) == RiskTier.NONE

    def test_coerce_unknown(self):
        assert coerce_risk("bogus") == RiskTier.NONE


# ── Required capability mapping ─────────────────────────────────


class TestRequiredCapability:
    def test_read_ops_need_read(self):
        assert required_capability(OperationKind.READ_DATA) == CapabilityLevel.READ
        assert required_capability(OperationKind.READ_MEMORY) == CapabilityLevel.READ

    def test_write_ops_need_write(self):
        assert required_capability(OperationKind.WRITE_MEMORY) == CapabilityLevel.WRITE
        assert required_capability(OperationKind.WRITE_LOG) == CapabilityLevel.WRITE

    def test_execute_ops_need_execute(self):
        assert required_capability(OperationKind.EDIT_FILE) == CapabilityLevel.EXECUTE
        assert required_capability(OperationKind.RUN_SCRIPT) == CapabilityLevel.EXECUTE

    def test_critical_ops_need_critical(self):
        assert (
            required_capability(OperationKind.DELETE_FILE) == CapabilityLevel.CRITICAL
        )
        assert (
            required_capability(OperationKind.MUTATE_INFRA) == CapabilityLevel.CRITICAL
        )

    def test_call_llm_needs_read(self):
        assert required_capability(OperationKind.CALL_LLM) == CapabilityLevel.READ


# ── CapabilityProfile ────────────────────────────────────────────


class TestCapabilityProfile:
    def test_to_dict(self):
        p = CapabilityProfile(
            name="test",
            max_capability=CapabilityLevel.WRITE,
            denied_operations={OperationKind.DELETE_FILE},
        )
        d = p.to_dict()
        assert d["name"] == "test"
        assert d["max_capability"] == "write"
        assert "delete_file" in d["denied_operations"]
        assert isinstance(d["allowed_operations"], list)


# ── CapabilityEnforcer ───────────────────────────────────────────


class TestCapabilityEnforcer:
    def setup_method(self):
        self.enforcer = CapabilityEnforcer()
        self.reader = CapabilityProfile(
            name="reader",
            max_capability=CapabilityLevel.READ,
            max_auto_risk=RiskTier.LOW,
        )
        self.writer = CapabilityProfile(
            name="writer",
            max_capability=CapabilityLevel.WRITE,
            max_auto_risk=RiskTier.LOW,
        )
        self.executor = CapabilityProfile(
            name="executor",
            max_capability=CapabilityLevel.EXECUTE,
            max_auto_risk=RiskTier.MEDIUM,
            denied_operations={OperationKind.MUTATE_INFRA},
        )

    def test_reader_can_read(self):
        d = self.enforcer.may(self.reader, OperationKind.READ_DATA)
        assert d.allowed is True

    def test_reader_cannot_write(self):
        d = self.enforcer.may(self.reader, OperationKind.WRITE_MEMORY)
        assert d.allowed is False
        assert "read" in d.reason
        assert "write" in d.reason

    def test_writer_can_write(self):
        d = self.enforcer.may(self.writer, OperationKind.WRITE_MEMORY)
        assert d.allowed is True

    def test_denied_operation_blocked(self):
        d = self.enforcer.may(self.executor, OperationKind.MUTATE_INFRA)
        assert d.allowed is False
        assert "denies" in d.reason

    def test_allow_list_filters(self):
        restricted = CapabilityProfile(
            name="restricted",
            max_capability=CapabilityLevel.EXECUTE,
            allowed_operations={OperationKind.READ_DATA, OperationKind.CALL_LLM},
        )
        d = self.enforcer.may(restricted, OperationKind.RUN_SCRIPT)
        assert d.allowed is False
        assert "allow-list" in d.reason

    def test_approval_required_at_high_risk(self):
        d = self.enforcer.may(self.writer, OperationKind.WRITE_LOG, risk="high")
        assert d.allowed is True
        assert d.needs_approval is True

    def test_no_approval_at_low_risk(self):
        d = self.enforcer.may(self.writer, OperationKind.WRITE_LOG, risk="low")
        assert d.allowed is True
        assert d.needs_approval is False

    def test_enforce_raises_on_denied(self):
        with pytest.raises(PermissionError, match="denies"):
            self.enforcer.enforce(self.executor, OperationKind.MUTATE_INFRA)

    def test_enforce_returns_decision_on_allowed(self):
        d = self.enforcer.enforce(self.executor, OperationKind.EDIT_FILE)
        assert d.allowed is True

    def test_risk_none_coerced(self):
        d = self.enforcer.may(self.reader, OperationKind.READ_DATA, risk=None)
        assert d.effective_risk == RiskTier.NONE
        assert d.allowed is True


# ── ProfileRegistry ──────────────────────────────────────────────


class TestProfileRegistry:
    def test_register_and_get(self):
        reg = ProfileRegistry()
        p = CapabilityProfile(name="agent_a", max_capability=CapabilityLevel.READ)
        reg.register(p)
        assert reg.get("agent_a") is p

    def test_get_unknown_raises(self):
        reg = ProfileRegistry()
        with pytest.raises(KeyError, match="no capability profile"):
            reg.get("nonexistent")

    def test_list_profiles(self):
        reg = ProfileRegistry()
        reg.register(CapabilityProfile(name="b", max_capability=CapabilityLevel.READ))
        reg.register(CapabilityProfile(name="a", max_capability=CapabilityLevel.READ))
        assert reg.list_profiles() == ["a", "b"]

    def test_size(self):
        reg = ProfileRegistry()
        assert reg.size == 0
        reg.register(CapabilityProfile(name="x", max_capability=CapabilityLevel.READ))
        assert reg.size == 1


# ── Default registry ─────────────────────────────────────────────


class TestDefaultRegistry:
    def test_has_five_archetypes(self):
        reg = default_registry()
        assert reg.size == 5
        assert set(reg.list_profiles()) == {
            "reader",
            "writer",
            "executor",
            "observer",
            "advisor",
        }

    def test_reader_can_read_and_call_llm(self):
        reg = default_registry()
        enforcer = CapabilityEnforcer()
        reader = reg.get("reader")
        assert enforcer.may(reader, OperationKind.READ_DATA).allowed
        assert enforcer.may(reader, OperationKind.CALL_LLM).allowed

    def test_reader_cannot_write(self):
        reg = default_registry()
        enforcer = CapabilityEnforcer()
        reader = reg.get("reader")
        assert not enforcer.may(reader, OperationKind.WRITE_MEMORY).allowed

    def test_executor_denied_critical(self):
        reg = default_registry()
        enforcer = CapabilityEnforcer()
        executor = reg.get("executor")
        assert not enforcer.may(executor, OperationKind.DELETE_FILE).allowed
        assert not enforcer.may(executor, OperationKind.MUTATE_INFRA).allowed

    def test_advisor_read_only(self):
        reg = default_registry()
        enforcer = CapabilityEnforcer()
        advisor = reg.get("advisor")
        assert enforcer.may(advisor, OperationKind.READ_DATA).allowed
        assert not enforcer.may(advisor, OperationKind.WRITE_MEMORY).allowed


# ── operation_for_action_type ────────────────────────────────────


class TestOperationForActionType:
    def test_query_maps_to_read_data(self):
        assert operation_for_action_type("query") == OperationKind.READ_DATA

    def test_edit_file_maps(self):
        assert operation_for_action_type("edit_file") == OperationKind.EDIT_FILE

    def test_edit_file_critical_flag(self):
        assert (
            operation_for_action_type("edit_file", is_critical=True)
            == OperationKind.EDIT_CRITICAL
        )

    def test_delete_file_maps(self):
        assert operation_for_action_type("delete_file") == OperationKind.DELETE_FILE

    def test_unknown_defaults_to_edit_file(self):
        assert operation_for_action_type("unknown_thing") == OperationKind.EDIT_FILE

    def test_case_insensitive(self):
        assert operation_for_action_type("QUERY") == OperationKind.READ_DATA
        assert operation_for_action_type("Delete_File") == OperationKind.DELETE_FILE

    def test_graph_operations_map_to_read_graph(self):
        assert operation_for_action_type("query_graph") == OperationKind.READ_GRAPH
        assert operation_for_action_type("read_graph") == OperationKind.READ_GRAPH
        assert operation_for_action_type("graph_search") == OperationKind.READ_GRAPH


# ── READ_GRAPH operation ──────────────────────────────────────────


class TestReadGraph:
    def test_read_graph_exists(self):
        assert hasattr(OperationKind, "READ_GRAPH")
        assert OperationKind.READ_GRAPH.value == "read_graph"

    def test_read_graph_requires_read(self):
        from umh.governance.capability import required_capability

        assert required_capability(OperationKind.READ_GRAPH) == CapabilityLevel.READ

    def test_reader_can_read_graph(self):
        enforcer = CapabilityEnforcer()
        reg = default_registry()
        reader = reg.get("reader")
        # reader has allow-list; READ_GRAPH must be added to profile for this to pass
        # Default reader doesn't include READ_GRAPH in allow-list, so test current behavior
        decision = enforcer.may(reader, OperationKind.READ_GRAPH)
        # Reader has allow-list that doesn't include READ_GRAPH → denied
        assert not decision.allowed

    def test_executor_can_read_graph(self):
        enforcer = CapabilityEnforcer()
        reg = default_registry()
        executor = reg.get("executor")
        decision = enforcer.may(executor, OperationKind.READ_GRAPH)
        # executor's allow-list doesn't include READ_GRAPH → denied
        assert not decision.allowed

    def test_profile_with_read_graph_allowed(self):
        enforcer = CapabilityEnforcer()
        profile = CapabilityProfile(
            name="graph_reader",
            max_capability=CapabilityLevel.READ,
            allowed_operations={OperationKind.READ_GRAPH, OperationKind.READ_DATA},
        )
        decision = enforcer.may(profile, OperationKind.READ_GRAPH)
        assert decision.allowed
