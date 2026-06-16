"""Phase 26 — Governed Action Bridge tests.

Tests the action catalog, action bridge, voice contract, routes,
type registration, and integration flows.
"""

from __future__ import annotations

import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Action Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestActionTypes:
    def test_risk_level_values(self):
        from substrate.organism.action_catalog import ActionRiskLevel

        assert ActionRiskLevel.SAFE.value == "safe"
        assert ActionRiskLevel.LOW.value == "low"
        assert ActionRiskLevel.MEDIUM.value == "medium"
        assert ActionRiskLevel.HIGH.value == "high"
        assert ActionRiskLevel.CRITICAL.value == "critical"

    def test_category_values(self):
        from substrate.organism.action_catalog import ActionCategory

        assert len(ActionCategory) == 6
        assert ActionCategory.CONTAINER.value == "container"
        assert ActionCategory.OBSERVATION.value == "observation"
        assert ActionCategory.TEST.value == "test"

    def test_status_values(self):
        from substrate.organism.action_catalog import ActionStatus

        assert len(ActionStatus) == 7
        assert ActionStatus.AWAITING_APPROVAL.value == "awaiting_approval"
        assert ActionStatus.BLOCKED.value == "blocked"

    def test_risk_level_is_string_enum(self):
        from substrate.organism.action_catalog import ActionRiskLevel

        assert isinstance(ActionRiskLevel.SAFE, str)
        assert ActionRiskLevel.SAFE == "safe"

    def test_all_enums_have_string_values(self):
        from substrate.organism.action_catalog import (
            ActionCategory,
            ActionRiskLevel,
            ActionStatus,
        )

        for e in [ActionRiskLevel, ActionCategory, ActionStatus]:
            for member in e:
                assert isinstance(member.value, str)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Action Definition
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestActionDefinition:
    def test_construction(self):
        from substrate.organism.action_catalog import ActionDefinition

        ad = ActionDefinition(
            action_id="test_action",
            name="Test",
            description="A test",
            category="test",
            risk_level="safe",
        )
        assert ad.action_id == "test_action"
        assert ad.enabled is True
        assert ad.executor_type == "workstation"
        assert ad.operation == "run_command"

    def test_to_dict(self):
        from substrate.organism.action_catalog import ActionDefinition

        ad = ActionDefinition(
            action_id="test",
            name="Test",
            description="desc",
            category="test",
            risk_level="low",
            tags=["a", "b"],
        )
        d = ad.to_dict()
        assert d["action_id"] == "test"
        assert d["tags"] == ["a", "b"]
        assert isinstance(d["parameters"], list)

    def test_from_dict(self):
        from substrate.organism.action_catalog import ActionDefinition

        data = {
            "action_id": "test",
            "name": "Test",
            "description": "desc",
            "category": "test",
            "risk_level": "low",
        }
        ad = ActionDefinition.from_dict(data)
        assert ad.action_id == "test"
        assert ad.enabled is True

    def test_roundtrip(self):
        from substrate.organism.action_catalog import (
            ActionDefinition,
            ActionParameter,
            ActionPrecondition,
        )

        ad = ActionDefinition(
            action_id="test",
            name="Test",
            description="desc",
            category="test",
            risk_level="medium",
            parameters=[ActionParameter(name="x", description="param x")],
            preconditions=[ActionPrecondition(check_type="container_running")],
        )
        d = ad.to_dict()
        restored = ActionDefinition.from_dict(d)
        assert restored.action_id == ad.action_id
        assert len(restored.parameters) == 1
        assert restored.parameters[0].name == "x"
        assert len(restored.preconditions) == 1

    def test_from_dict_ignores_unknown_fields(self):
        from substrate.organism.action_catalog import ActionDefinition

        data = {
            "action_id": "test",
            "name": "Test",
            "description": "desc",
            "category": "test",
            "risk_level": "low",
            "unknown_field": "ignored",
        }
        ad = ActionDefinition.from_dict(data)
        assert ad.action_id == "test"

    def test_parameter_to_dict(self):
        from substrate.organism.action_catalog import ActionParameter

        p = ActionParameter(name="x", param_type="integer", choices=["1", "2"])
        d = p.to_dict()
        assert d["name"] == "x"
        assert d["choices"] == ["1", "2"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Action Catalog
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestActionCatalog:
    def test_seed_defaults_count(self):
        from substrate.organism.action_catalog import ActionCatalog

        catalog = ActionCatalog()
        actions = catalog.list_actions()
        assert len(actions) == 7

    def test_resolve_by_id(self):
        from substrate.organism.action_catalog import ActionCatalog

        catalog = ActionCatalog()
        action = catalog.resolve_by_id("list_containers")
        assert action is not None
        assert action.action_id == "list_containers"
        assert action.risk_level == "safe"

    def test_resolve_by_id_missing(self):
        from substrate.organism.action_catalog import ActionCatalog

        catalog = ActionCatalog()
        assert catalog.resolve_by_id("nonexistent") is None

    def test_resolve_from_text(self):
        from substrate.organism.action_catalog import ActionCatalog

        catalog = ActionCatalog()
        action = catalog.resolve("show me docker containers")
        assert action is not None
        assert action.action_id == "list_containers"

    def test_resolve_from_text_no_match(self):
        from substrate.organism.action_catalog import ActionCatalog

        catalog = ActionCatalog()
        assert catalog.resolve("fly me to the moon") is None

    def test_list_by_category(self):
        from substrate.organism.action_catalog import ActionCatalog

        catalog = ActionCatalog()
        obs = catalog.list_actions(category="observation")
        assert len(obs) >= 3
        assert all(a.category == "observation" for a in obs)

    def test_register_custom(self):
        from substrate.organism.action_catalog import ActionCatalog, ActionDefinition

        catalog = ActionCatalog()
        custom = ActionDefinition(
            action_id="custom_action",
            name="Custom",
            description="Custom action",
            category="build",
            risk_level="low",
        )
        catalog.register(custom)
        assert catalog.resolve_by_id("custom_action") is not None

    def test_disabled_not_resolved(self):
        from substrate.organism.action_catalog import ActionCatalog, ActionDefinition

        catalog = ActionCatalog()
        disabled = ActionDefinition(
            action_id="disabled_one",
            name="Disabled",
            description="Should not resolve",
            category="test",
            risk_level="safe",
            enabled=False,
        )
        catalog.register(disabled)
        assert catalog.resolve_by_id("disabled_one") is None

    def test_restart_container_is_medium(self):
        from substrate.organism.action_catalog import ActionCatalog

        catalog = ActionCatalog()
        action = catalog.resolve_by_id("restart_container")
        assert action is not None
        assert action.risk_level == "medium"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Action Bridge
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestActionBridge:
    def _make_bridge(self, coordinator=None):
        from substrate.organism.action_bridge import ActionBridge
        from substrate.organism.action_catalog import ActionCatalog

        return ActionBridge(catalog=ActionCatalog(), coordinator=coordinator)

    def _mock_coordinator(self, auto_approve=True):
        coord = MagicMock()
        plan = MagicMock()
        plan.execution_plan_id = "plan-123"
        plan.approval_state = "approved" if auto_approve else "pending"
        coord.create_plan.return_value = plan
        coord.enqueue_plan.return_value = plan
        coord.dispatch_next.return_value = plan
        coord.approve_plan.return_value = plan
        return coord

    def test_execute_unknown_action_fails(self):
        from substrate.organism.action_bridge import ActionBridge, ActionRequest

        bridge = self._make_bridge(coordinator=self._mock_coordinator())
        req = ActionRequest(action_id="nonexistent")
        result = bridge.execute_action(req)
        assert result.status == "failed"
        assert "Unknown action" in result.error

    def test_execute_safe_action_auto_approves(self):
        from substrate.organism.action_bridge import ActionRequest

        coord = self._mock_coordinator(auto_approve=True)
        bridge = self._make_bridge(coordinator=coord)
        req = ActionRequest(action_id="list_containers")
        result = bridge.execute_action(req)
        assert result.status == "completed"
        assert result.execution_plan_id == "plan-123"
        coord.create_plan.assert_called_once()
        coord.enqueue_plan.assert_called_once()

    def test_execute_medium_risk_awaits_approval(self):
        from substrate.organism.action_bridge import ActionRequest

        coord = self._mock_coordinator(auto_approve=False)
        bridge = self._make_bridge(coordinator=coord)
        req = ActionRequest(
            action_id="restart_container",
            parameters={"container_name": "os-webhook"},
        )
        result = bridge.execute_action(req)
        assert result.status == "awaiting_approval"
        assert result.execution_plan_id == "plan-123"
        coord.enqueue_plan.assert_not_called()

    def test_missing_required_param_fails(self):
        from substrate.organism.action_bridge import ActionRequest

        coord = self._mock_coordinator()
        bridge = self._make_bridge(coordinator=coord)
        req = ActionRequest(
            action_id="container_logs",
            parameters={},
        )
        result = bridge.execute_action(req)
        assert result.status == "failed"
        assert "Missing required" in result.error

    def test_build_command_substitution(self):
        from substrate.organism.action_catalog import ActionDefinition, ActionParameter

        bridge = self._make_bridge()
        action = ActionDefinition(
            action_id="test",
            name="Test",
            description="test",
            category="test",
            risk_level="safe",
            command_template="echo {message}",
            parameters=[ActionParameter(name="message")],
        )
        cmd = bridge._build_command(action, {"message": "hello"})
        assert cmd == "echo hello"

    def test_build_command_rejects_shell_injection(self):
        from substrate.organism.action_catalog import ActionDefinition, ActionParameter

        bridge = self._make_bridge()
        action = ActionDefinition(
            action_id="test",
            name="Test",
            description="test",
            category="test",
            risk_level="safe",
            command_template="echo {message}",
            parameters=[ActionParameter(name="message")],
        )
        cmd = bridge._build_command(action, {"message": "hello; rm -rf /"})
        assert cmd is None

    def test_build_command_rejects_leading_dash(self):
        from substrate.organism.action_catalog import ActionDefinition, ActionParameter

        bridge = self._make_bridge()
        action = ActionDefinition(
            action_id="test",
            name="Test",
            description="test",
            category="test",
            risk_level="safe",
            command_template="docker restart {container_name}",
            parameters=[ActionParameter(name="container_name")],
        )
        cmd = bridge._build_command(action, {"container_name": "--rm"})
        assert cmd is None

    def test_build_command_rejects_path_traversal(self):
        from substrate.organism.action_catalog import ActionDefinition, ActionParameter

        bridge = self._make_bridge()
        action = ActionDefinition(
            action_id="test",
            name="Test",
            description="test",
            category="test",
            risk_level="safe",
            command_template="git -C {repo_path} status",
            parameters=[ActionParameter(name="repo_path", param_type="path")],
        )
        cmd = bridge._build_command(action, {"repo_path": "/etc/passwd"})
        assert cmd is None

    def test_build_command_rejects_spaces(self):
        from substrate.organism.action_catalog import ActionDefinition, ActionParameter

        bridge = self._make_bridge()
        action = ActionDefinition(
            action_id="test",
            name="Test",
            description="test",
            category="test",
            risk_level="safe",
            command_template="docker restart {container_name}",
            parameters=[ActionParameter(name="container_name")],
        )
        cmd = bridge._build_command(action, {"container_name": "os-webhook --rm"})
        assert cmd is None

    def test_validate_parameters_choice(self):
        from substrate.organism.action_catalog import ActionDefinition, ActionParameter

        bridge = self._make_bridge()
        action = ActionDefinition(
            action_id="test",
            name="Test",
            description="test",
            category="test",
            risk_level="safe",
            parameters=[
                ActionParameter(name="env", choices=["dev", "staging"]),
            ],
        )
        ok, _ = bridge._validate_parameters(action, {"env": "dev"})
        assert ok
        ok2, reason = bridge._validate_parameters(action, {"env": "prod"})
        assert not ok2
        assert "Invalid value" in reason

    def test_precondition_container_running_pass(self):
        from substrate.organism.action_catalog import ActionDefinition, ActionPrecondition

        bridge = self._make_bridge()
        action = ActionDefinition(
            action_id="test",
            name="Test",
            description="test",
            category="test",
            risk_level="safe",
            preconditions=[ActionPrecondition(check_type="container_running")],
        )
        mock_snapshot = {
            "containers": [{"container_name": "os-webhook", "status": "Up 2 hours"}],
        }
        with patch.object(bridge, "_get_workspace_snapshot", return_value=mock_snapshot):
            results = bridge.check_preconditions(action, {"container_name": "os-webhook"})
        assert len(results) == 1
        assert results[0]["passed"] is True

    def test_precondition_container_running_fail(self):
        from substrate.organism.action_catalog import ActionDefinition, ActionPrecondition

        bridge = self._make_bridge()
        action = ActionDefinition(
            action_id="test",
            name="Test",
            description="test",
            category="test",
            risk_level="safe",
            preconditions=[ActionPrecondition(check_type="container_running")],
        )
        mock_snapshot = {
            "containers": [{"container_name": "os-webhook", "status": "Exited (1)"}],
        }
        with patch.object(bridge, "_get_workspace_snapshot", return_value=mock_snapshot):
            results = bridge.check_preconditions(action, {"container_name": "os-webhook"})
        assert len(results) == 1
        assert results[0]["passed"] is False

    def test_precondition_no_observation_assumes_met(self):
        from substrate.organism.action_catalog import ActionDefinition, ActionPrecondition

        bridge = self._make_bridge()
        action = ActionDefinition(
            action_id="test",
            name="Test",
            description="test",
            category="test",
            risk_level="safe",
            preconditions=[ActionPrecondition(check_type="container_running")],
        )
        with patch.object(bridge, "_get_workspace_snapshot", return_value=None):
            results = bridge.check_preconditions(action, {"container_name": "os-webhook"})
        assert results[0]["passed"] is True

    def test_action_history(self):
        from substrate.organism.action_bridge import ActionRequest

        coord = self._mock_coordinator(auto_approve=True)
        bridge = self._make_bridge(coordinator=coord)
        bridge.execute_action(ActionRequest(action_id="list_containers"))
        bridge.execute_action(ActionRequest(action_id="git_status"))
        history = bridge.history(limit=10)
        assert len(history) == 2

    def test_get_action_status(self):
        from substrate.organism.action_bridge import ActionRequest

        coord = self._mock_coordinator(auto_approve=True)
        bridge = self._make_bridge(coordinator=coord)
        req = ActionRequest(action_id="list_containers")
        result = bridge.execute_action(req)
        found = bridge.get_action_status(result.request_id)
        assert found is not None
        assert found.action_id == "list_containers"

    def test_result_carries_requested_by(self):
        from substrate.organism.action_bridge import ActionRequest

        coord = self._mock_coordinator(auto_approve=True)
        bridge = self._make_bridge(coordinator=coord)
        req = ActionRequest(action_id="list_containers", requested_by="user_abc123")
        result = bridge.execute_action(req)
        assert result.requested_by == "user_abc123"

    def test_history_filtered_by_operator(self):
        from substrate.organism.action_bridge import ActionRequest

        coord = self._mock_coordinator(auto_approve=True)
        bridge = self._make_bridge(coordinator=coord)
        bridge.execute_action(ActionRequest(action_id="list_containers", requested_by="alice"))
        bridge.execute_action(ActionRequest(action_id="git_status", requested_by="bob"))
        alice_history = bridge.history(limit=10, operator_id="alice")
        assert len(alice_history) == 1
        assert alice_history[0]["action_id"] == "list_containers"
        bob_history = bridge.history(limit=10, operator_id="bob")
        assert len(bob_history) == 1
        assert bob_history[0]["action_id"] == "git_status"

    def test_status_filtered_by_operator(self):
        from substrate.organism.action_bridge import ActionRequest

        coord = self._mock_coordinator(auto_approve=True)
        bridge = self._make_bridge(coordinator=coord)
        req = ActionRequest(action_id="list_containers", requested_by="alice")
        result = bridge.execute_action(req)
        assert bridge.get_action_status(result.request_id, operator_id="alice") is not None
        assert bridge.get_action_status(result.request_id, operator_id="bob") is None

    def test_list_available_enriches(self):
        bridge = self._make_bridge()
        with patch.object(bridge, "_get_workspace_snapshot", return_value=None):
            available = bridge.list_available_actions()
        assert len(available) == 7
        for entry in available:
            assert "precondition_state" in entry


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Intent Action Contract
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntentContract:
    def test_translate_with_action_id(self):
        from substrate.organism.action_catalog import ActionCatalog
        from substrate.organism.action_voice_contract import (
            IntentActionContract,
            IntentActionRequest,
        )

        contract = IntentActionContract(catalog=ActionCatalog())
        intent = IntentActionRequest(
            raw_text="",
            intent_source="cockpit_button",
            action_id="list_containers",
        )
        result = contract.translate(intent)
        assert result is not None
        assert result.action_id == "list_containers"
        assert result.source == "cockpit_button"

    def test_translate_with_text(self):
        from substrate.organism.action_catalog import ActionCatalog
        from substrate.organism.action_voice_contract import (
            IntentActionContract,
            IntentActionRequest,
        )

        contract = IntentActionContract(catalog=ActionCatalog())
        intent = IntentActionRequest(
            raw_text="show me docker containers",
            intent_source="voice",
        )
        result = contract.translate(intent)
        assert result is not None
        assert result.action_id == "list_containers"

    def test_translate_no_match(self):
        from substrate.organism.action_catalog import ActionCatalog
        from substrate.organism.action_voice_contract import (
            IntentActionContract,
            IntentActionRequest,
        )

        contract = IntentActionContract(catalog=ActionCatalog())
        intent = IntentActionRequest(raw_text="fly to mars")
        result = contract.translate(intent)
        assert result is None

    def test_translate_preserves_parameters(self):
        from substrate.organism.action_catalog import ActionCatalog
        from substrate.organism.action_voice_contract import (
            IntentActionContract,
            IntentActionRequest,
        )

        contract = IntentActionContract(catalog=ActionCatalog())
        intent = IntentActionRequest(
            raw_text="",
            action_id="container_logs",
            parameters={"container_name": "os-webhook", "lines": "100"},
        )
        result = contract.translate(intent)
        assert result is not None
        assert result.parameters["container_name"] == "os-webhook"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cockpit Routes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestCockpitRoutes:
    def test_import_works(self):
        from transports.api.cockpit_action_bridge_routes import action_bridge_router

        assert action_bridge_router is not None

    def test_configure_sets_flag(self):
        import transports.api.cockpit_action_bridge_routes as mod

        mod._configured = False
        mod.configure(require_operator_dep=lambda: "test")
        assert mod._configured is True

    def test_router_has_routes(self):
        from transports.api.cockpit_action_bridge_routes import action_bridge_router

        route_paths = [r.path for r in action_bridge_router.routes]
        assert any("/catalog" in p for p in route_paths)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Type Registration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestTypeRegistration:
    def test_canonical_types_has_action_entries(self):
        from substrate.canonical_types import CANONICAL_TYPES

        expected = [
            "ActionRiskLevel",
            "ActionCategory",
            "ActionStatus",
            "ActionDefinition",
            "ActionParameter",
            "ActionPrecondition",
            "ActionRequest",
            "ActionResult",
            "IntentActionRequest",
        ]
        for name in expected:
            assert name in CANONICAL_TYPES, f"Missing: {name}"

    def test_action_types_import_from_canonical_location(self):
        from substrate.organism.action_catalog import (
            ActionCategory,
            ActionDefinition,
            ActionParameter,
            ActionPrecondition,
            ActionRiskLevel,
            ActionStatus,
        )

        assert ActionRiskLevel.SAFE.value == "safe"
        assert ActionDefinition.__dataclass_fields__ is not None

    def test_bridge_types_import(self):
        from substrate.organism.action_bridge import ActionRequest, ActionResult

        req = ActionRequest(action_id="test")
        assert req.source == "cockpit"
        result = ActionResult(action_id="test")
        assert result.status == "pending"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Integration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class TestIntegration:
    def _mock_coordinator(self, auto_approve=True):
        coord = MagicMock()
        plan = MagicMock()
        plan.execution_plan_id = f"plan-{time.time_ns()}"
        plan.approval_state = "approved" if auto_approve else "pending"
        coord.create_plan.return_value = plan
        coord.enqueue_plan.return_value = plan
        coord.dispatch_next.return_value = plan
        return coord

    def test_full_lifecycle_safe(self):
        from substrate.organism.action_bridge import ActionBridge, ActionRequest
        from substrate.organism.action_catalog import ActionCatalog

        coord = self._mock_coordinator(auto_approve=True)
        bridge = ActionBridge(catalog=ActionCatalog(), coordinator=coord)
        req = ActionRequest(action_id="git_status")
        result = bridge.execute_action(req)
        assert result.status == "completed"
        assert result.execution_plan_id != ""
        coord.create_plan.assert_called_once()
        call_kwargs = coord.create_plan.call_args
        assert call_kwargs.kwargs["risk_class"] == "safe"

    def test_full_lifecycle_approval(self):
        from substrate.organism.action_bridge import ActionBridge, ActionRequest
        from substrate.organism.action_catalog import ActionCatalog

        coord = self._mock_coordinator(auto_approve=False)
        bridge = ActionBridge(catalog=ActionCatalog(), coordinator=coord)
        req = ActionRequest(
            action_id="restart_container",
            parameters={"container_name": "os-webhook"},
        )
        result = bridge.execute_action(req)
        assert result.status == "awaiting_approval"
        call_kwargs = coord.create_plan.call_args
        assert call_kwargs.kwargs["risk_class"] == "medium"

    def test_catalog_to_bridge_chain(self):
        from substrate.organism.action_bridge import ActionBridge, ActionRequest
        from substrate.organism.action_catalog import ActionCatalog

        catalog = ActionCatalog()
        action = catalog.resolve("run pytest")
        assert action is not None
        assert action.action_id == "run_tests"

        coord = self._mock_coordinator(auto_approve=True)
        bridge = ActionBridge(catalog=catalog, coordinator=coord)
        req = ActionRequest(action_id=action.action_id)
        result = bridge.execute_action(req)
        assert result.status == "completed"

    def test_precondition_blocks_execution(self):
        from substrate.organism.action_bridge import ActionBridge, ActionRequest
        from substrate.organism.action_catalog import ActionCatalog

        coord = self._mock_coordinator(auto_approve=False)
        bridge = ActionBridge(catalog=ActionCatalog(), coordinator=coord)

        mock_snapshot = {
            "containers": [
                {"container_name": "os-webhook", "status": "Exited (1)"},
            ],
        }
        with patch.object(bridge, "_get_workspace_snapshot", return_value=mock_snapshot):
            req = ActionRequest(
                action_id="restart_container",
                parameters={"container_name": "os-webhook"},
            )
            result = bridge.execute_action(req)
        assert result.status == "blocked"
        coord.create_plan.assert_not_called()

    def test_voice_contract_to_bridge(self):
        from substrate.organism.action_bridge import ActionBridge
        from substrate.organism.action_catalog import ActionCatalog
        from substrate.organism.action_voice_contract import (
            IntentActionContract,
            IntentActionRequest,
        )

        catalog = ActionCatalog()
        contract = IntentActionContract(catalog=catalog)

        intent = IntentActionRequest(
            raw_text="show git status of the repo",
            intent_source="voice",
        )
        action_req = contract.translate(intent)
        assert action_req is not None
        assert action_req.action_id == "git_status"

        coord = self._mock_coordinator(auto_approve=True)
        bridge = ActionBridge(catalog=catalog, coordinator=coord)
        result = bridge.execute_action(action_req)
        assert result.status == "completed"
