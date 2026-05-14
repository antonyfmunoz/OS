"""Tests for Phase 96.8BQ — Controlled Browser and GUI Embodiment.

Tests cover:
  - Browser/GUI contracts (8 shapes)
  - Browser operational modes (4 modes, navigation scope)
  - Governed browser adapter (URL blocks, action blocks, navigation scope)
  - Visible GUI adapter (governance gating)
  - Browser observability pipeline (telemetry recording)
  - Browser continuity bridge (session lineage)
  - Browser replay validator (determinism verification)
  - Browser execution orchestrator (pipeline coordination)
  - Browser/GUI embodiment engine (command dispatch)
  - Blocked navigation (login, payment, account mutation)
  - Blocked mutation attempts
  - Operational mode enforcement
  - Screenshot lineage preservation
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import pytest

# --- Contracts ---
from execution.workers.workstation.browser_gui_contracts_v1 import (
    BrowserActionType,
    BrowserActionVerdict,
    BrowserExecutionOutcome,
    BrowserExecutionRequest,
    BrowserExecutionResult,
    BrowserOperationalMode,
    BrowserOperationalSnapshot,
    BrowserSession,
    BrowserState,
    BrowserCapabilityRequest,
    GUIState,
    GUIWindowState,
    NavigationScope,
    VisibleActuationEvent,
    _content_hash,
    _deterministic_id,
    _new_id,
    _now_iso,
)

# --- Modes ---
from execution.workers.workstation.browser_operational_modes_v1 import (
    INSPECTION_MODE,
    INTERNAL_NAVIGATION_MODE,
    RESEARCH_MODE,
    RESTRICTED_EXECUTION_MODE,
    BrowserModeDefinition,
    get_all_browser_modes,
    get_browser_mode_definition,
)

# --- Browser Adapter ---
from execution.workers.workstation.governed_browser_adapter_v1 import (
    BLOCKED_DOMAINS,
    BLOCKED_URL_PATTERNS,
    BrowserGovernanceDecision,
    GovernedBrowserAdapter,
)

# --- GUI Adapter ---
from execution.workers.workstation.visible_gui_adapter_v1 import (
    BLOCKED_GUI_ACTIONS,
    GUIGovernanceDecision,
    VisibleGUIAdapter,
)

# --- Observability ---
from execution.workers.workstation.browser_observability_pipeline_v1 import (
    BrowserObservabilityPipeline,
)

# --- Continuity ---
from execution.workers.workstation.browser_continuity_bridge_v1 import BrowserContinuityBridge

# --- Replay ---
from execution.workers.workstation.browser_replay_validator_v1 import (
    BrowserReplayCheck,
    BrowserReplayResult,
    BrowserReplaySessionResult,
    BrowserReplayValidator,
)

# --- Orchestrator ---
from execution.workers.workstation.browser_execution_orchestrator_v1 import (
    BrowserExecutionOrchestrator,
)

# --- Engine ---
from execution.workers.workstation.browser_gui_embodiment_engine_v1 import (
    BROWSER_COMMANDS,
    BrowserGUIEmbodimentEngine,
)


# =========================================================================
# 1. Contracts
# =========================================================================


class TestContracts:
    def test_browser_state_serializes(self) -> None:
        state = BrowserState(browser_type="chrome", is_running=True, active_tabs=3)
        d = state.to_dict()
        assert d["browser_type"] == "chrome"
        assert d["is_running"] is True
        assert d["active_tabs"] == 3
        assert d["state_id"].startswith("bstate-")
        assert "content_hash" in d

    def test_browser_session_deterministic_id(self) -> None:
        s1 = BrowserSession(tab_index=0, url="http://localhost:3000")
        s2 = BrowserSession(tab_index=0, url="http://localhost:3000")
        assert s1.session_id == s2.session_id

    def test_browser_session_different_urls_different_ids(self) -> None:
        s1 = BrowserSession(tab_index=0, url="http://localhost:3000")
        s2 = BrowserSession(tab_index=0, url="http://localhost:8080")
        assert s1.session_id != s2.session_id

    def test_capability_request_serializes(self) -> None:
        req = BrowserCapabilityRequest(action_type=BrowserActionType.INSPECT_TABS)
        d = req.to_dict()
        assert d["action_type"] == "inspect_tabs"
        assert d["request_id"].startswith("bcapreq-")

    def test_execution_request_serializes(self) -> None:
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000",
        )
        d = req.to_dict()
        assert d["action_type"] == "navigate"
        assert d["target_url"] == "http://localhost:3000"
        assert "content_hash" in d

    def test_execution_result_succeeded(self) -> None:
        r = BrowserExecutionResult(outcome=BrowserExecutionOutcome.SUCCESS)
        assert r.succeeded is True

    def test_execution_result_failed(self) -> None:
        r = BrowserExecutionResult(outcome=BrowserExecutionOutcome.DENIED)
        assert r.succeeded is False

    def test_gui_state_serializes(self) -> None:
        g = GUIState(desktop_session_active=True, display_available=True)
        d = g.to_dict()
        assert d["desktop_session_active"] is True
        assert d["state_id"].startswith("guistate-")

    def test_visible_actuation_event_serializes(self) -> None:
        e = VisibleActuationEvent(
            action_type=BrowserActionType.SCREENSHOT,
            visibility_confirmed=True,
        )
        d = e.to_dict()
        assert d["action_type"] == "screenshot"
        assert d["visibility_confirmed"] is True

    def test_operational_snapshot_serializes(self) -> None:
        s = BrowserOperationalSnapshot(phase="96.8BQ", total_actions=5)
        d = s.to_dict()
        assert d["phase"] == "96.8BQ"
        assert d["total_actions"] == 5
        assert "content_hash" in d

    def test_content_hash_deterministic(self) -> None:
        d = {"a": 1, "b": 2}
        assert _content_hash(d) == _content_hash(d)

    def test_deterministic_id_stable(self) -> None:
        a = _deterministic_id("ns", "x")
        b = _deterministic_id("ns", "x")
        assert a == b


# =========================================================================
# 2. Browser Operational Modes
# =========================================================================


class TestBrowserModes:
    def test_inspection_allows_inspect_tabs(self) -> None:
        assert INSPECTION_MODE.allows_action(BrowserActionType.INSPECT_TABS)

    def test_inspection_denies_navigate(self) -> None:
        assert not INSPECTION_MODE.allows_action(BrowserActionType.NAVIGATE)

    def test_inspection_denies_all_navigation(self) -> None:
        assert not INSPECTION_MODE.allows_navigation_to("http://localhost:3000")

    def test_research_allows_inspect(self) -> None:
        assert RESEARCH_MODE.allows_action(BrowserActionType.INSPECT_TABS)
        assert RESEARCH_MODE.allows_action(BrowserActionType.DOCUMENT_INSPECT)

    def test_research_denies_navigate(self) -> None:
        assert not RESEARCH_MODE.allows_action(BrowserActionType.NAVIGATE)

    def test_research_allows_approved_domain(self) -> None:
        assert RESEARCH_MODE.allows_navigation_to("https://github.com/repo")
        assert RESEARCH_MODE.allows_navigation_to("https://docs.python.org/3/")

    def test_research_denies_unapproved_domain(self) -> None:
        assert not RESEARCH_MODE.allows_navigation_to("https://facebook.com")

    def test_internal_nav_allows_navigation(self) -> None:
        assert INTERNAL_NAVIGATION_MODE.allows_action(BrowserActionType.NAVIGATE)

    def test_internal_nav_allows_local(self) -> None:
        assert INTERNAL_NAVIGATION_MODE.allows_navigation_to("http://localhost:3000")
        assert INTERNAL_NAVIGATION_MODE.allows_navigation_to("http://127.0.0.1:8080")

    def test_internal_nav_allows_tailscale(self) -> None:
        assert INTERNAL_NAVIGATION_MODE.allows_navigation_to("http://100.77.233.50:3000")

    def test_internal_nav_denies_external(self) -> None:
        assert not INTERNAL_NAVIGATION_MODE.allows_navigation_to("https://google.com")

    def test_restricted_execution_requires_screenshot(self) -> None:
        assert RESTRICTED_EXECUTION_MODE.require_screenshot is True
        assert RESTRICTED_EXECUTION_MODE.require_visibility_confirmation is True

    def test_get_all_modes_returns_four(self) -> None:
        modes = get_all_browser_modes()
        assert len(modes) == 4

    def test_mode_serialization(self) -> None:
        d = INSPECTION_MODE.to_dict()
        assert d["mode"] == "inspection_mode"
        assert "allowed_actions" in d


# =========================================================================
# 3. Governed Browser Adapter — Governance Enforcement
# =========================================================================


class TestGovernedBrowserAdapter:
    def test_inspect_tabs_approved(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INSPECTION)
        req = BrowserExecutionRequest(action_type=BrowserActionType.INSPECT_TABS)
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.APPROVED

    def test_navigate_denied_in_inspection(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INSPECTION)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED

    def test_login_url_blocked(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INTERNAL_NAVIGATION)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000/login",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED
        assert "BLOCKED_URL_PATTERN" in decision.rules_applied

    def test_payment_url_blocked(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INTERNAL_NAVIGATION)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000/checkout",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED

    def test_account_settings_blocked(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INTERNAL_NAVIGATION)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000/settings",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED

    def test_oauth_url_blocked(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INTERNAL_NAVIGATION)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000/oauth/callback",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED

    def test_blocked_domain_denied(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.RESEARCH)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="https://accounts.google.com/signin",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED
        assert "BLOCKED_DOMAIN" in decision.rules_applied

    def test_paypal_blocked(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.RESEARCH)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="https://www.paypal.com/pay",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED

    def test_stripe_blocked(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.RESEARCH)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="https://stripe.com/dashboard",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED

    def test_local_navigation_approved_in_internal_mode(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INTERNAL_NAVIGATION)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000/dashboard",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.APPROVED

    def test_external_navigation_denied_in_internal_mode(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INTERNAL_NAVIGATION)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="https://google.com",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED
        assert "NAVIGATION_SCOPE_DENIED" in decision.rules_applied

    def test_navigate_without_url_denied(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INTERNAL_NAVIGATION)
        req = BrowserExecutionRequest(action_type=BrowserActionType.NAVIGATE)
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED
        assert "NAVIGATE_NO_URL" in decision.rules_applied

    def test_screenshot_approved(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INSPECTION)
        req = BrowserExecutionRequest(action_type=BrowserActionType.SCREENSHOT)
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.APPROVED

    def test_execute_approved_action(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INSPECTION)
        req = BrowserExecutionRequest(action_type=BrowserActionType.INSPECT_TABS)
        result = adapter.execute(req)
        assert result.succeeded is True
        assert result.adapter_used == "governed_browser"

    def test_execute_denied_action(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INSPECTION)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000",
        )
        result = adapter.execute(req)
        assert result.outcome == BrowserExecutionOutcome.DENIED

    def test_stats_tracking(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INSPECTION)
        req1 = BrowserExecutionRequest(action_type=BrowserActionType.INSPECT_TABS)
        req2 = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://evil.com",
        )
        adapter.evaluate_action(req1)
        adapter.evaluate_action(req2)
        stats = adapter.get_stats()
        assert stats["total_decisions"] == 2
        assert stats["approved"] == 1
        assert stats["denied"] == 1

    def test_upload_url_blocked(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INTERNAL_NAVIGATION)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000/upload",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED

    def test_admin_url_blocked(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INTERNAL_NAVIGATION)
        req = BrowserExecutionRequest(
            action_type=BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000/admin",
        )
        decision = adapter.evaluate_action(req)
        assert decision.verdict == BrowserActionVerdict.DENIED

    def test_risk_classification(self) -> None:
        adapter = GovernedBrowserAdapter(BrowserOperationalMode.INSPECTION)
        req = BrowserExecutionRequest(action_type=BrowserActionType.INSPECT_TABS)
        decision = adapter.evaluate_action(req)
        assert decision.risk_class == "safe"


# =========================================================================
# 4. Visible GUI Adapter
# =========================================================================


class TestVisibleGUIAdapter:
    def test_inspect_windows_in_inspection(self) -> None:
        gui = VisibleGUIAdapter(BrowserOperationalMode.INSPECTION)
        result = gui.inspect_windows()
        assert result.outcome == BrowserExecutionOutcome.SUCCESS

    def test_screenshot_in_inspection(self) -> None:
        gui = VisibleGUIAdapter(BrowserOperationalMode.INSPECTION)
        result = gui.capture_screenshot("/tmp/test.png")
        assert result.outcome == BrowserExecutionOutcome.SUCCESS

    def test_ui_state_inspect(self) -> None:
        gui = VisibleGUIAdapter(BrowserOperationalMode.INSPECTION)
        result = gui.inspect_ui_state()
        assert result.outcome == BrowserExecutionOutcome.SUCCESS

    def test_blocked_gui_actions(self) -> None:
        gui = VisibleGUIAdapter()
        assert gui.is_action_blocked("close_window") is True
        assert gui.is_action_blocked("kill_process") is True
        assert gui.is_action_blocked("clipboard_write") is True
        assert gui.is_action_blocked("keystroke_inject") is True
        assert gui.is_action_blocked("mouse_click") is True
        assert gui.is_action_blocked("logout") is True

    def test_capture_gui_state(self) -> None:
        gui = VisibleGUIAdapter()
        state = gui.capture_gui_state()
        assert state.state_id.startswith("guistate-")

    def test_stats(self) -> None:
        gui = VisibleGUIAdapter(BrowserOperationalMode.INSPECTION)
        gui.inspect_windows()
        stats = gui.get_stats()
        assert stats["total_decisions"] == 1
        assert stats["approved"] == 1

    def test_focus_window(self) -> None:
        gui = VisibleGUIAdapter(BrowserOperationalMode.INTERNAL_NAVIGATION)
        result = gui.focus_window("test-window")
        assert result.outcome == BrowserExecutionOutcome.SUCCESS


# =========================================================================
# 5. Browser Observability Pipeline
# =========================================================================


class TestBrowserObservability:
    def test_record_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = BrowserObservabilityPipeline(observability_dir=td)
            req = BrowserExecutionRequest(action_type=BrowserActionType.INSPECT_TABS)
            result = BrowserExecutionResult(outcome=BrowserExecutionOutcome.SUCCESS)
            record = obs.record_execution(req, result)
            assert record["action_type"] == "inspect_tabs"
            assert record["outcome"] == "success"

    def test_denial_tracking(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = BrowserObservabilityPipeline(observability_dir=td)
            req = BrowserExecutionRequest(action_type=BrowserActionType.NAVIGATE)
            result = BrowserExecutionResult(outcome=BrowserExecutionOutcome.DENIED)
            obs.record_execution(req, result)
            denials = obs.get_denial_records()
            assert len(denials) == 1

    def test_stats(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = BrowserObservabilityPipeline(observability_dir=td)
            req = BrowserExecutionRequest(action_type=BrowserActionType.INSPECT_TABS)
            success = BrowserExecutionResult(outcome=BrowserExecutionOutcome.SUCCESS)
            denied = BrowserExecutionResult(outcome=BrowserExecutionOutcome.DENIED)
            obs.record_execution(req, success)
            obs.record_execution(req, denied)
            stats = obs.get_stats()
            assert stats["total_recorded"] == 2
            assert stats["total_successes"] == 1
            assert stats["total_denials"] == 1

    def test_actuation_log(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = BrowserObservabilityPipeline(observability_dir=td)
            event = VisibleActuationEvent(
                action_type=BrowserActionType.SCREENSHOT,
                visibility_confirmed=True,
            )
            obs.record_actuation_event(event)
            log = obs.get_actuation_log()
            assert len(log) == 1


# =========================================================================
# 6. Browser Continuity Bridge
# =========================================================================


class TestBrowserContinuityBridge:
    def test_start_session(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = BrowserContinuityBridge(continuity_dir=td)
            sid = bridge.start_session("test-session")
            assert sid == "test-session"

    def test_bridge_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = BrowserContinuityBridge(continuity_dir=td)
            bridge.start_session()
            result = BrowserExecutionResult(
                outcome=BrowserExecutionOutcome.SUCCESS,
                url_after="http://localhost:3000",
            )
            lineage = bridge.bridge_execution(result)
            assert lineage["outcome"] == "success"

    def test_bridge_governance_decision(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = BrowserContinuityBridge(continuity_dir=td)
            bridge.start_session()
            event = bridge.bridge_governance_decision(
                action_type="navigate",
                target_url="http://localhost/login",
                verdict="denied",
                rules_applied=["BLOCKED_URL_PATTERN"],
            )
            assert event["verdict"] == "denied"

    def test_bridge_mode_transition(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = BrowserContinuityBridge(continuity_dir=td)
            bridge.start_session()
            event = bridge.bridge_mode_transition(
                BrowserOperationalMode.INSPECTION,
                BrowserOperationalMode.RESEARCH,
            )
            assert event["old_mode"] == "inspection_mode"
            assert event["new_mode"] == "research_mode"

    def test_take_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = BrowserContinuityBridge(continuity_dir=td)
            bridge.start_session()
            result = BrowserExecutionResult(outcome=BrowserExecutionOutcome.SUCCESS)
            bridge.bridge_execution(result)
            snapshot = bridge.take_snapshot()
            assert snapshot["executions_tracked"] == 1

    def test_stats(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = BrowserContinuityBridge(continuity_dir=td)
            bridge.start_session()
            result = BrowserExecutionResult(outcome=BrowserExecutionOutcome.SUCCESS)
            bridge.bridge_execution(result)
            stats = bridge.get_stats()
            assert stats["events_bridged"] >= 1
            assert stats["executions_tracked"] == 1

    def test_bridge_browser_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = BrowserContinuityBridge(continuity_dir=td)
            bridge.start_session()
            state = BrowserState(browser_type="chrome", is_running=True)
            event = bridge.bridge_browser_state(state)
            assert event["browser_type"] == "chrome"

    def test_bridge_gui_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bridge = BrowserContinuityBridge(continuity_dir=td)
            bridge.start_session()
            state = GUIState(desktop_session_active=True)
            event = bridge.bridge_gui_state(state)
            assert event["desktop_session_active"] is True


# =========================================================================
# 7. Browser Replay Validator
# =========================================================================


class TestBrowserReplayValidator:
    def test_replay_approved_action(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = BrowserReplayValidator(BrowserOperationalMode.INSPECTION, proof_dir=td)
            record = {
                "action_type": "inspect_tabs",
                "target_url": "",
                "governance_verdict": "approved",
                "risk_class": "safe",
                "adapter_used": "governed_browser",
                "operational_mode": "inspection_mode",
            }
            result = replay.replay_record(record)
            assert result.all_passed is True

    def test_replay_denied_action(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = BrowserReplayValidator(BrowserOperationalMode.INSPECTION, proof_dir=td)
            record = {
                "action_type": "navigate",
                "target_url": "http://localhost:3000",
                "governance_verdict": "denied",
                "risk_class": "medium",
                "adapter_used": "denied",
                "operational_mode": "inspection_mode",
            }
            result = replay.replay_record(record)
            gov_check = next(c for c in result.checks if c.check_name == "governance_verdict")
            assert gov_check.passed is True

    def test_replay_detects_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = BrowserReplayValidator(BrowserOperationalMode.INSPECTION, proof_dir=td)
            record = {
                "action_type": "inspect_tabs",
                "governance_verdict": "denied",
                "risk_class": "safe",
                "adapter_used": "governed_browser",
                "operational_mode": "inspection_mode",
            }
            result = replay.replay_record(record)
            gov_check = next(c for c in result.checks if c.check_name == "governance_verdict")
            assert gov_check.passed is False

    def test_replay_session_with_proof(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = BrowserReplayValidator(BrowserOperationalMode.INSPECTION, proof_dir=td)
            records = [
                {
                    "action_type": "inspect_tabs",
                    "governance_verdict": "approved",
                    "risk_class": "safe",
                    "adapter_used": "governed_browser",
                    "operational_mode": "inspection_mode",
                },
                {
                    "action_type": "screenshot",
                    "governance_verdict": "approved",
                    "risk_class": "safe",
                    "adapter_used": "governed_browser",
                    "operational_mode": "inspection_mode",
                },
            ]
            session = replay.replay_session(records, session_id="test-browser")
            assert session.total_records == 2
            assert session.all_passed is True
            proof_path = Path(td) / "browser_replay_proof_test-browser.json"
            assert proof_path.exists()

    def test_replay_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = BrowserReplayValidator(BrowserOperationalMode.INSPECTION, proof_dir=td)
            result = replay.replay_from_file("/nonexistent/path.jsonl")
            assert result.total_records == 0

    def test_stats(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            replay = BrowserReplayValidator(BrowserOperationalMode.INSPECTION, proof_dir=td)
            record = {
                "action_type": "inspect_tabs",
                "governance_verdict": "approved",
                "risk_class": "safe",
                "adapter_used": "governed_browser",
                "operational_mode": "inspection_mode",
            }
            replay.replay_record(record)
            stats = replay.get_stats()
            assert stats["total_replays"] == 1


# =========================================================================
# 8. Browser Execution Orchestrator
# =========================================================================


class TestBrowserExecutionOrchestrator:
    def test_execute_approved_action(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = BrowserObservabilityPipeline(observability_dir=f"{td}/obs")
            cont = BrowserContinuityBridge(continuity_dir=f"{td}/cont")
            orch = BrowserExecutionOrchestrator(observability=obs, continuity=cont)
            result = orch.execute_browser(BrowserActionType.INSPECT_TABS)
            assert result.succeeded is True

    def test_execute_denied_action(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = BrowserObservabilityPipeline(observability_dir=f"{td}/obs")
            cont = BrowserContinuityBridge(continuity_dir=f"{td}/cont")
            orch = BrowserExecutionOrchestrator(observability=obs, continuity=cont)
            result = orch.execute_browser(
                BrowserActionType.NAVIGATE,
                target_url="http://localhost:3000",
            )
            assert result.outcome == BrowserExecutionOutcome.DENIED

    def test_mode_change_propagates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = BrowserObservabilityPipeline(observability_dir=f"{td}/obs")
            cont = BrowserContinuityBridge(continuity_dir=f"{td}/cont")
            orch = BrowserExecutionOrchestrator(observability=obs, continuity=cont)
            orch.set_mode(BrowserOperationalMode.INTERNAL_NAVIGATION)
            result = orch.execute_browser(
                BrowserActionType.NAVIGATE,
                target_url="http://localhost:3000/dashboard",
            )
            assert result.succeeded is True

    def test_stats(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = BrowserObservabilityPipeline(observability_dir=f"{td}/obs")
            cont = BrowserContinuityBridge(continuity_dir=f"{td}/cont")
            orch = BrowserExecutionOrchestrator(observability=obs, continuity=cont)
            orch.execute_browser(BrowserActionType.INSPECT_TABS)
            orch.execute_browser(BrowserActionType.NAVIGATE, target_url="http://evil.com")
            stats = orch.get_stats()
            assert stats["total_executions"] == 2
            assert stats["total_successes"] == 1
            assert stats["total_denials"] == 1

    def test_gui_action_routing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            obs = BrowserObservabilityPipeline(observability_dir=f"{td}/obs")
            cont = BrowserContinuityBridge(continuity_dir=f"{td}/cont")
            orch = BrowserExecutionOrchestrator(observability=obs, continuity=cont)
            result = orch.execute_gui(BrowserActionType.WINDOW_INSPECT)
            assert result.succeeded is True
            assert result.adapter_used == "visible_gui"


# =========================================================================
# 9. Browser/GUI Embodiment Engine
# =========================================================================


class TestBrowserGUIEmbodimentEngine:
    def test_initialization(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        info = engine.initialize()
        assert "session_id" in info
        assert info["operational_mode"] == "inspection_mode"

    def test_mode_change(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        result = engine.set_mode(BrowserOperationalMode.RESEARCH)
        assert result["old_mode"] == "inspection_mode"
        assert result["new_mode"] == "research_mode"

    def test_dispatch_browser_status(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("browser-status")
        assert result["command"] == "browser-status"
        assert "browser_state" in result

    def test_dispatch_browser_tabs(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("browser-tabs")
        assert result["command"] == "browser-tabs"

    def test_dispatch_browser_inspect(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("browser-inspect")
        assert result["command"] == "browser-inspect"

    def test_dispatch_browser_summary(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("browser-summary")
        assert result["command"] == "browser-summary"

    def test_dispatch_gui_state(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("gui-state")
        assert result["command"] == "gui-state"
        assert "gui_state" in result

    def test_dispatch_actuation_log(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        result = engine.dispatch_command("visible-actuation-log")
        assert result["command"] == "visible-actuation-log"

    def test_dispatch_unknown_command(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        result = engine.dispatch_command("nonexistent")
        assert "error" in result

    def test_execute_through_engine(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        result = engine.execute_browser(BrowserActionType.INSPECT_TABS)
        assert result.succeeded is True

    def test_denied_through_engine(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        result = engine.execute_browser(BrowserActionType.NAVIGATE, target_url="https://paypal.com")
        assert result.outcome == BrowserExecutionOutcome.DENIED

    def test_take_snapshot(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        snapshot = engine.take_snapshot()
        assert snapshot.phase == "96.8BQ"

    def test_stats(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        stats = engine.get_stats()
        assert stats["initialized"] is True
        assert stats["operational_mode"] == "inspection_mode"

    def test_browser_commands_defined(self) -> None:
        assert len(BROWSER_COMMANDS) >= 6
        assert "browser-status" in BROWSER_COMMANDS
        assert "gui-state" in BROWSER_COMMANDS
        assert "visible-actuation-log" in BROWSER_COMMANDS

    def test_login_blocked_through_engine(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        engine.set_mode(BrowserOperationalMode.INTERNAL_NAVIGATION)
        result = engine.execute_browser(
            BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000/login",
        )
        assert result.outcome == BrowserExecutionOutcome.DENIED

    def test_safe_local_navigation(self) -> None:
        engine = BrowserGUIEmbodimentEngine()
        engine.initialize()
        engine.set_mode(BrowserOperationalMode.INTERNAL_NAVIGATION)
        result = engine.execute_browser(
            BrowserActionType.NAVIGATE,
            target_url="http://localhost:3000/dashboard",
        )
        assert result.succeeded is True


# ── §14.1 Adapter Contract Tests ─────────────────────────────────────────────


class TestBrowserAdapterContract:
    """§14.1 contract methods on GovernedBrowserAdapter."""

    def test_translate_request_returns_input(self) -> None:
        from execution.workers.workstation.governed_browser_adapter_v1 import GovernedBrowserAdapter
        from execution.workers.workstation.browser_gui_contracts_v1 import BrowserExecutionRequest, BrowserActionType
        adapter = GovernedBrowserAdapter()
        req = BrowserExecutionRequest(action_type=BrowserActionType.INSPECT_TABS, target_url="")
        assert adapter.translate_request(req) is req

    def test_validate_operation_approved(self) -> None:
        from execution.workers.workstation.governed_browser_adapter_v1 import GovernedBrowserAdapter
        from execution.workers.workstation.browser_gui_contracts_v1 import BrowserExecutionRequest, BrowserActionType
        adapter = GovernedBrowserAdapter()
        req = BrowserExecutionRequest(action_type=BrowserActionType.INSPECT_TABS, target_url="")
        decision = adapter.validate_operation(req)
        assert decision.verdict.value == "approved"

    def test_validate_operation_denied(self) -> None:
        from execution.workers.workstation.governed_browser_adapter_v1 import GovernedBrowserAdapter
        from execution.workers.workstation.browser_gui_contracts_v1 import BrowserExecutionRequest, BrowserActionType
        adapter = GovernedBrowserAdapter()
        req = BrowserExecutionRequest(action_type=BrowserActionType.NAVIGATE, target_url="https://accounts.google.com/login")
        decision = adapter.validate_operation(req)
        assert decision.verdict.value == "denied"

    def test_normalize_result_attaches_timing(self) -> None:
        from execution.workers.workstation.governed_browser_adapter_v1 import GovernedBrowserAdapter
        from execution.workers.workstation.browser_gui_contracts_v1 import (
            BrowserExecutionRequest, BrowserExecutionResult, BrowserActionType,
            BrowserExecutionOutcome,
        )
        adapter = GovernedBrowserAdapter()
        req = BrowserExecutionRequest(action_type=BrowserActionType.INSPECT_TABS, target_url="")
        decision = adapter.validate_operation(req)
        raw = BrowserExecutionResult(
            request_id=req.request_id,
            action_type=req.action_type,
            outcome=BrowserExecutionOutcome.SUCCESS,
            adapter_used="governed_browser",
            correlation_id=req.correlation_id,
        )
        result = adapter.normalize_result(raw, decision, 55.0)
        assert result.duration_ms == 55.0
        assert result.governance_verdict == "approved"

    def test_observe_state(self) -> None:
        from execution.workers.workstation.governed_browser_adapter_v1 import GovernedBrowserAdapter
        adapter = GovernedBrowserAdapter()
        state = adapter.observe_state()
        assert state["adapter_id"] == "governed_browser"
        assert state["healthy"] is True
        assert "operational_mode" in state
        assert "total_decisions" in state


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
