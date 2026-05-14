"""Tests for Phase 95.0 — Local GUI Control Contracts."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from runtime.substrate.local_gui_control_contracts import (
    ALLOWED_OBSERVATION_TARGETS,
    BLOCKED_OBSERVATION_TARGETS,
    GUIControlStatus,
    GUIInventoryItem,
    GUIObservationMethod,
    GUIObservationPolicy,
    GUIObservationResult,
    build_gui_backend_missing_report,
    classify_gui_control_availability,
    is_observation_target_allowed,
    is_observation_target_blocked,
)


class TestGUIObservationPolicy:
    def test_serializes(self) -> None:
        policy = GUIObservationPolicy()
        d = policy.to_dict()
        assert "allowed_targets" in d
        assert "blocked_targets" in d
        assert isinstance(d["allowed_targets"], list)
        assert isinstance(d["blocked_targets"], list)

    def test_temporary_observation_does_not_imply_persistent_storage(self) -> None:
        policy = GUIObservationPolicy()
        assert policy.temporary_observation_allowed is True
        assert policy.persistent_screenshot_allowed is False

    def test_credential_fields_blocked(self) -> None:
        policy = GUIObservationPolicy()
        assert policy.is_target_allowed("credential_field") is False
        assert policy.is_target_allowed("password_field") is False
        assert policy.is_target_allowed("login_form") is False

    def test_document_opening_blocked(self) -> None:
        policy = GUIObservationPolicy()
        assert policy.document_opening_blocked is True
        assert policy.is_target_allowed("document_body") is False
        assert policy.is_target_allowed("document_content") is False

    def test_wrong_account_pauses(self) -> None:
        policy = GUIObservationPolicy()
        assert policy.wrong_account_pauses is True

    def test_drive_file_list_allowed(self) -> None:
        policy = GUIObservationPolicy()
        assert policy.is_target_allowed("drive_file_list") is True
        assert policy.is_target_allowed("drive_file_name") is True
        assert policy.is_target_allowed("drive_modified_date") is True


class TestClassifyAvailability:
    def test_ui_automation_available(self) -> None:
        status, method = classify_gui_control_availability(has_ui_automation=True)
        assert status == GUIControlStatus.AVAILABLE
        assert method == GUIObservationMethod.WINDOWS_UI_AUTOMATION

    def test_accessibility_available(self) -> None:
        status, method = classify_gui_control_availability(has_accessibility=True)
        assert status == GUIControlStatus.AVAILABLE
        assert method == GUIObservationMethod.ACCESSIBILITY_TREE

    def test_screen_capture_partial(self) -> None:
        status, method = classify_gui_control_availability(has_screen_capture=True)
        assert status == GUIControlStatus.PARTIAL
        assert method == GUIObservationMethod.TEMPORARY_SCREEN_OBSERVATION

    def test_nothing_available(self) -> None:
        status, method = classify_gui_control_availability()
        assert status == GUIControlStatus.MISSING
        assert method is None


class TestBlockedTargets:
    def test_gmail_blocked(self) -> None:
        assert is_observation_target_blocked("gmail_inbox")

    def test_cookie_store_blocked(self) -> None:
        assert is_observation_target_blocked("cookie_store")

    def test_drive_list_not_blocked(self) -> None:
        assert not is_observation_target_blocked("drive_file_list")


class TestGUIBackendMissingReport:
    def test_includes_options(self) -> None:
        report = build_gui_backend_missing_report(["ui_automation", "accessibility"])
        assert report["status"] == "GUI_OBSERVATION_BACKEND_MISSING"
        assert len(report["options"]) == 4
        assert any(o["option"] == "A" for o in report["options"])


class TestGUIInventoryItem:
    def test_serializes(self) -> None:
        item = GUIInventoryItem(
            name="UMH",
            item_type="application/vnd.google-apps.document",
            modified_date="May 4, 2026",
            row_index=0,
        )
        d = item.to_dict()
        assert d["name"] == "UMH"
        assert d["item_type"] == "application/vnd.google-apps.document"
        assert d["modified_date"] == "May 4, 2026"
