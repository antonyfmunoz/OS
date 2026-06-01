"""Phase 13.4M tests — multi-runtime operator acceptance correction.

Validates:
- Device role registry
- Runtime fleet model
- Workload placement policy
- Operator readiness gate (corrected)
- Operator acceptance mode (corrected)
- API bridge handlers
- Safety invariants
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time

import pytest

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, _REPO)

# ── Device Role Registry ──────────────────────────────────────────


class TestDeviceRoleRegistry:
    def test_seed_known_nodes(self):
        from substrate.organism.device_role_registry import (
            DeviceRole,
            seed_known_nodes,
        )
        nodes = seed_known_nodes()
        assert len(nodes) == 3
        roles = {n.role for n in nodes}
        assert DeviceRole.CONTROL_PLANE in roles
        assert DeviceRole.HEAVY_WORKSTATION in roles
        assert DeviceRole.COCKPIT_UI in roles

    def test_vps_is_control_plane(self):
        from substrate.organism.device_role_registry import (
            DeviceCapability,
            DeviceRole,
            seed_known_nodes,
        )
        nodes = seed_known_nodes()
        vps = [n for n in nodes if n.role == DeviceRole.CONTROL_PLANE][0]
        assert DeviceCapability.CANONICAL_STATE in vps.capabilities
        assert DeviceCapability.CPU_LIGHT in vps.capabilities
        assert "heavy_computation" in vps.blocked_workloads
        assert vps.max_risk_class == "low"

    def test_beast_is_heavy_workstation(self):
        from substrate.organism.device_role_registry import (
            DeviceCapability,
            DeviceRole,
            seed_known_nodes,
        )
        nodes = seed_known_nodes()
        beast = [n for n in nodes if n.role == DeviceRole.HEAVY_WORKSTATION][0]
        assert DeviceCapability.CPU_HEAVY in beast.capabilities
        assert DeviceCapability.GPU_AVAILABLE in beast.capabilities
        assert "heavy_execution" in beast.allowed_workloads
        assert beast.max_risk_class == "medium"

    def test_cockpit_no_execution(self):
        from substrate.organism.device_role_registry import (
            DeviceRole,
            seed_known_nodes,
        )
        nodes = seed_known_nodes()
        cockpit = [n for n in nodes if n.role == DeviceRole.COCKPIT_UI][0]
        assert "heavy_execution" in cockpit.blocked_workloads
        assert "runtime_execution" in cockpit.blocked_workloads

    def test_serialization_roundtrip(self):
        from substrate.organism.device_role_registry import (
            node_from_dict,
            seed_known_nodes,
        )
        nodes = seed_known_nodes()
        for node in nodes:
            d = node.to_dict()
            restored = node_from_dict(d)
            assert restored.node_id == node.node_id
            assert restored.role == node.role
            assert restored.device_name == node.device_name

    def test_persist_and_load(self):
        from substrate.organism.device_role_registry import (
            load_registry,
            persist_registry,
            seed_known_nodes,
        )
        with tempfile.TemporaryDirectory() as td:
            nodes = seed_known_nodes()
            persist_registry(nodes, td)
            loaded = load_registry(td)
            assert len(loaded) == len(nodes)

    def test_get_nodes_by_role(self):
        from substrate.organism.device_role_registry import (
            DeviceRole,
            get_nodes_by_role,
            persist_registry,
            seed_known_nodes,
        )
        with tempfile.TemporaryDirectory() as td:
            persist_registry(seed_known_nodes(), td)
            ctrl = get_nodes_by_role(DeviceRole.CONTROL_PLANE, td)
            assert len(ctrl) == 1


# ── Runtime Fleet Model ──────────────────────────────────────────


class TestRuntimeFleetModel:
    def test_provider_enum_count(self):
        from substrate.organism.runtime_fleet import RuntimeProvider
        assert len(RuntimeProvider) == 11

    def test_create_fleet_member(self):
        from substrate.organism.runtime_fleet import (
            RuntimeProvider,
            RuntimeReadiness,
            create_fleet_member,
        )
        m = create_fleet_member(
            provider=RuntimeProvider.CLAUDE_CODE,
            device_node_id="dn-vps",
            status=RuntimeReadiness.READY,
        )
        assert m.runtime_id.startswith("rfm-")
        assert m.provider == RuntimeProvider.CLAUDE_CODE

    def test_create_selection(self):
        from substrate.organism.runtime_fleet import create_selection
        s = create_selection(
            work_packet_id="wp-test",
            workcell_id="wc-test",
            selected_runtime="rfm-123",
            selected_device="dn-vps",
            reason="Claude Code available via subscription",
        )
        assert s.selection_id.startswith("rts-")
        assert s.work_packet_id == "wp-test"

    def test_serialization_roundtrip(self):
        from substrate.organism.runtime_fleet import (
            RuntimeProvider,
            RuntimeReadiness,
            create_fleet_member,
            member_from_dict,
        )
        m = create_fleet_member(
            provider=RuntimeProvider.CODEX,
            device_node_id="dn-vps",
            status=RuntimeReadiness.AVAILABLE_NOT_TESTED,
        )
        d = m.to_dict()
        restored = member_from_dict(d)
        assert restored.provider == m.provider
        assert restored.status == m.status

    def test_get_capable_runtimes(self):
        from substrate.organism.runtime_fleet import (
            RuntimeProvider,
            RuntimeReadiness,
            create_fleet_member,
            get_capable_runtimes,
            has_capable_runtime,
        )
        members = [
            create_fleet_member(RuntimeProvider.CLAUDE_CODE, "dn-vps", RuntimeReadiness.READY),
            create_fleet_member(RuntimeProvider.SHELL, "dn-vps", RuntimeReadiness.READY),
            create_fleet_member(RuntimeProvider.CLOUD_API, "dn-vps", RuntimeReadiness.ERROR),
        ]
        capable = get_capable_runtimes(members)
        assert len(capable) == 2
        assert has_capable_runtime(members)

    def test_no_capable_runtimes(self):
        from substrate.organism.runtime_fleet import (
            RuntimeProvider,
            RuntimeReadiness,
            create_fleet_member,
            has_capable_runtime,
        )
        members = [
            create_fleet_member(RuntimeProvider.CLOUD_API, "dn-vps", RuntimeReadiness.ERROR),
        ]
        assert not has_capable_runtime(members)

    def test_persist_and_load_fleet(self):
        from substrate.organism.runtime_fleet import (
            RuntimeProvider,
            RuntimeReadiness,
            create_fleet_member,
            load_fleet,
            persist_fleet,
        )
        with tempfile.TemporaryDirectory() as td:
            members = [
                create_fleet_member(RuntimeProvider.CLAUDE_CODE, "dn-vps", RuntimeReadiness.READY),
            ]
            persist_fleet(members, td)
            loaded = load_fleet(td)
            assert len(loaded) == 1


# ── Workload Placement Policy ────────────────────────────────────


class TestWorkloadPlacementPolicy:
    def test_vps_selected_for_governance(self):
        from substrate.organism.workload_placement_policy import (
            WorkloadType,
            select_placement,
        )
        d = select_placement(
            "wp-1", WorkloadType.GOVERNANCE,
            available_devices=["vps", "windows_beast"],
            available_runtimes=["shell", "claude_code"],
        )
        assert d.selected_device == "vps"
        assert d.selected_runtime == "shell"
        assert not d.approval_required

    def test_beast_selected_for_heavy_execution(self):
        from substrate.organism.workload_placement_policy import (
            WorkloadType,
            select_placement,
        )
        d = select_placement(
            "wp-2", WorkloadType.HEAVY_CODE_EXECUTION,
            available_devices=["vps", "windows_beast"],
            available_runtimes=["claude_code", "shell"],
        )
        assert d.selected_device == "windows_beast"
        assert d.selected_runtime == "claude_code"

    def test_claude_code_prioritized_for_coding(self):
        from substrate.organism.workload_placement_policy import (
            WorkloadType,
            select_placement,
        )
        d = select_placement(
            "wp-3", WorkloadType.LONG_RUNNING_CODING,
            available_devices=["vps"],
            available_runtimes=["claude_code", "codex", "shell"],
        )
        assert d.selected_runtime == "claude_code"

    def test_codex_opencode_hermes_accepted(self):
        from substrate.organism.workload_placement_policy import (
            WorkloadType,
            select_placement,
        )
        for rt in ("codex", "opencode", "hermes"):
            d = select_placement(
                "wp-4", WorkloadType.AI_REASONING,
                available_devices=["vps"],
                available_runtimes=[rt],
            )
            assert d.selected_runtime == rt

    def test_medium_risk_requires_approval(self):
        from substrate.organism.workload_placement_policy import (
            WorkloadType,
            select_placement,
        )
        d = select_placement(
            "wp-5", WorkloadType.SANDBOX_RUNTIME, "medium",
            available_devices=["vps"],
            available_runtimes=["shell"],
        )
        assert d.approval_required

    def test_degraded_mode_when_no_preferred(self):
        from substrate.organism.workload_placement_policy import (
            WorkloadType,
            select_placement,
        )
        d = select_placement(
            "wp-6", WorkloadType.BROWSER_AUTOMATION,
            available_devices=["vps"],
            available_runtimes=["shell"],
        )
        assert d.degraded_mode

    def test_serialization_roundtrip(self):
        from substrate.organism.workload_placement_policy import (
            WorkloadType,
            decision_from_dict,
            select_placement,
        )
        d = select_placement("wp-7", WorkloadType.GOVERNANCE)
        data = d.to_dict()
        restored = decision_from_dict(data)
        assert restored.decision_id == d.decision_id
        assert restored.workload_type == d.workload_type


# ── Operator Readiness Gate (corrected) ──────────────────────────


class TestOperatorReadinessGate:
    def test_standard_ready_with_subscription_runtime(self):
        from substrate.organism.operator_readiness_gate import assess_readiness
        r = assess_readiness(repo_root=_REPO)
        assert len(r.capable_runtimes) > 0
        assert "claude_code" in r.capable_runtimes

    def test_cloud_api_exhaustion_is_warning_not_blocker(self):
        from substrate.organism.operator_readiness_gate import assess_readiness
        r = assess_readiness(repo_root=_REPO)
        for issue in r.blocking_issues:
            assert "cloud api" not in issue.lower()
        cloud_warning = any("cloud api" in w.lower() for w in r.warnings)
        assert cloud_warning or r.evidence.get("llm_cloud_available", False)

    def test_report_has_fleet_evidence(self):
        from substrate.organism.operator_readiness_gate import assess_readiness
        r = assess_readiness(repo_root=_REPO)
        assert "runtime_fleet" in r.evidence
        assert "capable_runtime_count" in r.evidence
        assert "capable_runtime_providers" in r.evidence

    def test_report_serialization(self):
        from substrate.organism.operator_readiness_gate import assess_readiness
        r = assess_readiness(repo_root=_REPO)
        d = r.to_dict()
        assert "standard_ready" in d
        assert "deterministic_only_ready" in d
        assert "capable_runtimes" in d


# ── Operator Acceptance Mode (corrected) ─────────────────────────


class TestOperatorAcceptanceMode:
    def test_standard_multi_runtime_mode_exists(self):
        from substrate.organism.operator_acceptance_mode import OperatorAcceptanceMode
        assert OperatorAcceptanceMode.STANDARD_MULTI_RUNTIME.value == "standard_multi_runtime"

    def test_create_standard_decision(self):
        from substrate.organism.operator_acceptance_mode import (
            OperatorAcceptanceMode,
            create_standard_mode_decision,
        )
        d = create_standard_mode_decision("rpt-1", "claude_code", "vps")
        assert d.mode == OperatorAcceptanceMode.STANDARD_MULTI_RUNTIME
        assert d.capable_runtime_path_exists is True
        assert d.degraded is False
        assert d.selected_runtime == "claude_code"

    def test_create_deterministic_decision(self):
        from substrate.organism.operator_acceptance_mode import (
            OperatorAcceptanceMode,
            create_deterministic_mode_decision,
        )
        d = create_deterministic_mode_decision("rpt-2")
        assert d.mode == OperatorAcceptanceMode.DETERMINISTIC_ONLY
        assert d.capable_runtime_path_exists is False
        assert d.degraded is True

    def test_select_standard_when_capable_runtime(self):
        from substrate.organism.operator_acceptance_mode import (
            OperatorAcceptanceMode,
            select_acceptance_mode,
        )
        d = select_acceptance_mode(
            capable_runtime_exists=True,
            selected_runtime="claude_code",
            selected_device="vps",
            llm_cloud_available=False,
            readiness_report_id="rpt-3",
        )
        assert d.mode == OperatorAcceptanceMode.STANDARD_MULTI_RUNTIME

    def test_select_blocked_when_no_runtime_no_acceptance(self):
        from substrate.organism.operator_acceptance_mode import (
            OperatorAcceptanceMode,
            select_acceptance_mode,
        )
        d = select_acceptance_mode(
            capable_runtime_exists=False,
            selected_runtime="",
            selected_device="",
            llm_cloud_available=False,
            readiness_report_id="rpt-4",
            operator_accepts_degraded=False,
        )
        assert d.mode == OperatorAcceptanceMode.BLOCKED

    def test_select_deterministic_when_operator_accepts(self):
        from substrate.organism.operator_acceptance_mode import (
            OperatorAcceptanceMode,
            select_acceptance_mode,
        )
        d = select_acceptance_mode(
            capable_runtime_exists=False,
            selected_runtime="",
            selected_device="",
            llm_cloud_available=False,
            readiness_report_id="rpt-5",
            operator_accepts_degraded=True,
        )
        assert d.mode == OperatorAcceptanceMode.DETERMINISTIC_ONLY

    def test_cloud_exhaustion_not_blocker(self):
        from substrate.organism.operator_acceptance_mode import (
            OperatorAcceptanceMode,
            select_acceptance_mode,
        )
        d = select_acceptance_mode(
            capable_runtime_exists=True,
            selected_runtime="claude_code",
            selected_device="vps",
            llm_cloud_available=False,
            readiness_report_id="rpt-6",
        )
        assert d.mode == OperatorAcceptanceMode.STANDARD_MULTI_RUNTIME
        assert d.degraded is False

    def test_serialization_roundtrip(self):
        from substrate.organism.operator_acceptance_mode import (
            create_standard_mode_decision,
            from_dict,
        )
        d = create_standard_mode_decision("rpt-7", "codex", "windows_beast")
        data = d.to_dict()
        restored = from_dict(data)
        assert restored.mode == d.mode
        assert restored.selected_runtime == "codex"
        assert restored.capable_runtime_path_exists is True

    def test_persist_and_load(self):
        from substrate.organism.operator_acceptance_mode import (
            create_standard_mode_decision,
            load_mode_decisions,
            persist_mode_decision,
        )
        with tempfile.TemporaryDirectory() as td:
            d = create_standard_mode_decision("rpt-8", "claude_code", "vps")
            persist_mode_decision(d, td)
            loaded = load_mode_decisions(td)
            assert len(loaded) == 1
            assert loaded[0].selected_runtime == "claude_code"


# ── Safety Invariants ────────────────────────────────────────────


class TestSafetyInvariants:
    def test_medium_risk_always_requires_approval(self):
        from substrate.organism.workload_placement_policy import (
            WorkloadType,
            select_placement,
        )
        for wt in (WorkloadType.HEAVY_CODE_EXECUTION, WorkloadType.SANDBOX_RUNTIME):
            d = select_placement("wp-safe", wt, "medium")
            assert d.approval_required

    def test_no_secret_values_in_fleet_audit(self):
        path = os.path.join(
            _REPO,
            "data", "umh", "operator_acceptance", "phase13_4m_runtime_fleet_audit.json",
        )
        if os.path.exists(path):
            content = open(path).read()
            for secret_value in ("sk-ant-", "gsk_", "AIza"):
                assert secret_value not in content, f"Secret value pattern {secret_value} found in fleet audit"

    def test_no_secrets_in_mode_decision(self):
        path = os.path.join(
            _REPO,
            "data", "umh", "operator_acceptance", "phase13_4m_mode_selection_decision.json",
        )
        if os.path.exists(path):
            content = open(path).read()
            for secret_pattern in ("sk-ant-", "gsk_", "API_KEY="):
                assert secret_pattern not in content

    def test_deterministic_only_requires_explicit_acceptance(self):
        from substrate.organism.operator_acceptance_mode import (
            OperatorAcceptanceMode,
            select_acceptance_mode,
        )
        d = select_acceptance_mode(
            capable_runtime_exists=False,
            selected_runtime="",
            selected_device="",
            llm_cloud_available=False,
            readiness_report_id="safety-test",
            operator_accepts_degraded=False,
        )
        assert d.mode == OperatorAcceptanceMode.BLOCKED
        assert d.accepted_by_operator is False


# ── API Bridge Handlers ──────────────────────────────────────────


class TestAPIBridgeHandlers:
    def test_runtime_fleet_handler_exists(self):
        content = open(
            os.path.join(_REPO,
                         "transports", "api", "organism_bridge.py")
        ).read()
        assert "organism.operational_truth.runtime_fleet" in content
        assert "_operational_truth_runtime_fleet" in content

    def test_device_roles_handler_exists(self):
        content = open(
            os.path.join(_REPO,
                         "transports", "api", "organism_bridge.py")
        ).read()
        assert "organism.operational_truth.device_roles" in content

    def test_workload_placement_handler_exists(self):
        content = open(
            os.path.join(_REPO,
                         "transports", "api", "organism_bridge.py")
        ).read()
        assert "organism.operational_truth.workload_placement" in content

    def test_runtime_readiness_handler_exists(self):
        content = open(
            os.path.join(_REPO,
                         "transports", "api", "organism_bridge.py")
        ).read()
        assert "organism.operational_truth.runtime_readiness" in content

    def test_all_handlers_have_auth(self):
        content = open(
            os.path.join(_REPO,
                         "transports", "api", "http", "routes", "organism.ts")
        ).read()
        for route in ("runtime-fleet", "device-roles", "workload-placement", "runtime-readiness"):
            route_line_idx = content.find(f"'/operational-truth/{route}'")
            assert route_line_idx > -1, f"Route {route} not found"
            line_start = content.rfind("\n", 0, route_line_idx)
            line_end = content.find("\n", route_line_idx)
            line_text = content[max(0, line_start):line_end]
            assert "operatorGuard" in line_text, f"Route {route} missing operatorGuard"


# ── Readiness Gate vs Runtime Fleet ──────────────────────────────


class TestReadinessGateUsesFleet:
    def test_gate_detects_claude_code(self):
        from substrate.organism.operator_readiness_gate import _detect_runtime_fleet
        from pathlib import Path
        fleet = _detect_runtime_fleet(Path(_REPO))
        cc = [r for r in fleet if r["provider"] == "claude_code"]
        assert len(cc) == 1
        assert cc[0]["installed"] is True

    def test_gate_detects_shell(self):
        from substrate.organism.operator_readiness_gate import _detect_runtime_fleet
        from pathlib import Path
        fleet = _detect_runtime_fleet(Path(_REPO))
        shell = [r for r in fleet if r["provider"] == "shell"]
        assert len(shell) == 1
        assert shell[0]["capable"] is True

    def test_mode_decision_uses_fleet(self):
        from substrate.organism.operator_acceptance_mode import (
            OperatorAcceptanceMode,
            select_acceptance_mode,
        )
        from substrate.organism.operator_readiness_gate import assess_readiness
        r = assess_readiness(repo_root=_REPO)
        d = select_acceptance_mode(
            capable_runtime_exists=r.standard_ready,
            selected_runtime=r.capable_runtimes[0] if r.capable_runtimes else "",
            selected_device="vps",
            llm_cloud_available=r.evidence.get("llm_cloud_available", False),
            readiness_report_id="test",
        )
        if r.standard_ready:
            assert d.mode == OperatorAcceptanceMode.STANDARD_MULTI_RUNTIME


# ── No Fake Data ─────────────────────────────────────────────────


class TestNoFakeData:
    def test_fleet_audit_is_real(self):
        path = os.path.join(
            _REPO,
            "data", "umh", "operator_acceptance", "phase13_4m_runtime_fleet_audit.json",
        )
        if os.path.exists(path):
            data = json.load(open(path))
            for rt in data.get("runtimes", []):
                if rt.get("readiness_status") == "ready":
                    assert rt.get("evidence"), f"Runtime {rt['runtime_id']} claims ready with no evidence"

    def test_mode_decision_matches_fleet(self):
        path = os.path.join(
            _REPO,
            "data", "umh", "operator_acceptance", "phase13_4m_mode_selection_decision.json",
        )
        if os.path.exists(path):
            data = json.load(open(path))
            decision = data.get("decision", {})
            if decision.get("mode") == "standard_multi_runtime":
                assert decision.get("capable_runtime_path_exists") is True
                assert decision.get("selected_runtime") != ""
