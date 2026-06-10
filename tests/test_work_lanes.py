"""Tests for Beast multi-session work lanes, app resolver, and loop engine.

Covers:
  - Native app resolution (5 tests)
  - Chrome-first browser policy (2 tests)
  - App vs website classification (3 tests)
  - Lane routing (3 tests)
  - Foreground guard (3 tests)
  - Loop engine (3 tests)
  - Search URL generation (1 test)
  - Command router integration (2 tests)
"""

from __future__ import annotations

import sys
import uuid

sys.path.insert(0, "/opt/OS")

import pytest


# ---------------------------------------------------------------------------
# 1. Native App Resolution (5 tests)
# ---------------------------------------------------------------------------


class TestNativeAppResolution:
    def test_spotify_resolves_native(self) -> None:
        from substrate.workstation.app_resolver import resolve_app_target

        t = resolve_app_target("spotify")
        assert t.is_native is True
        assert t.process_name.lower() == "spotify"
        assert t.launch_cmd is not None
        assert t.open_url is None

    def test_discord_resolves_native(self) -> None:
        from substrate.workstation.app_resolver import resolve_app_target

        t = resolve_app_target("discord")
        assert t.is_native is True
        assert t.process_name == "Discord"

    def test_vscode_resolves_native(self) -> None:
        from substrate.workstation.app_resolver import resolve_app_target

        t = resolve_app_target("code")
        assert t.is_native is True
        assert t.process_name == "Code"

    def test_steam_resolves_native(self) -> None:
        from substrate.workstation.app_resolver import resolve_app_target

        t = resolve_app_target("steam")
        assert t.is_native is True

    def test_unknown_app_resolves_as_website(self) -> None:
        from substrate.workstation.app_resolver import resolve_app_target

        t = resolve_app_target("reddit")
        assert t.is_native is False
        assert t.browser == "chrome"


# ---------------------------------------------------------------------------
# 2. Chrome-First Browser Policy (2 tests)
# ---------------------------------------------------------------------------


class TestChromeFirstPolicy:
    def test_chrome_is_default_browser(self) -> None:
        from substrate.workstation.app_resolver import resolve_app_target

        t = resolve_app_target("reddit")
        assert t.browser == "chrome"

    def test_never_edge_or_explorer(self) -> None:
        from substrate.workstation.app_resolver import resolve_app_target

        web_targets = ["reddit", "twitter", "youtube", "gmail", "stackoverflow"]
        for name in web_targets:
            t = resolve_app_target(name)
            assert t.browser == "chrome", f"{name} should use chrome, got {t.browser}"
            assert "edge" not in t.browser.lower()
            assert "explorer" not in t.browser.lower()


# ---------------------------------------------------------------------------
# 3. App vs Website Classification (3 tests)
# ---------------------------------------------------------------------------


class TestAppVsWebsiteClassification:
    def test_classify_open_spotify_native(self) -> None:
        from substrate.workstation.app_resolver import classify_app_vs_website

        assert classify_app_vs_website("open spotify") == "native_app"

    def test_classify_search_website(self) -> None:
        from substrate.workstation.app_resolver import classify_app_vs_website

        assert classify_app_vs_website("search for python docs") == "website"

    def test_classify_open_discord_native(self) -> None:
        from substrate.workstation.app_resolver import classify_app_vs_website

        assert classify_app_vs_website("open discord") == "native_app"


# ---------------------------------------------------------------------------
# 4. Lane Routing (3 tests)
# ---------------------------------------------------------------------------


class TestLaneRouting:
    def test_route_native_app_lane(self) -> None:
        from substrate.workstation.work_lane import LaneType, route_to_lane

        lane = route_to_lane("open spotify", "sess-1")
        assert lane.lane_type == LaneType.native_app

    def test_route_browser_background(self) -> None:
        from substrate.workstation.work_lane import LaneType, route_to_lane

        lane = route_to_lane("search for python tutorials", "sess-1")
        assert lane.lane_type == LaneType.background_browser

    def test_route_screenshot_foreground(self) -> None:
        from substrate.workstation.work_lane import LaneType, route_to_lane

        lane = route_to_lane("take a screenshot", "sess-1")
        assert lane.lane_type == LaneType.foreground


# ---------------------------------------------------------------------------
# 5. Foreground Guard (3 tests)
# ---------------------------------------------------------------------------


class TestForegroundGuard:
    def test_native_app_approved(self) -> None:
        from substrate.workstation.work_lane import (
            ForegroundGuard,
            LaneType,
            route_to_lane,
        )

        lane = route_to_lane("open spotify", "sess-1")
        result = ForegroundGuard().check("open spotify", lane)
        assert result.approved is True

    def test_foreground_click_needs_approval(self) -> None:
        from substrate.workstation.work_lane import (
            ForegroundGuard,
            LaneType,
            route_to_lane,
        )

        lane = route_to_lane("click the button", "sess-1")
        result = ForegroundGuard().check("click the button", lane)
        assert result.requires_approval is True

    def test_screenshot_approved(self) -> None:
        from substrate.workstation.work_lane import (
            ForegroundGuard,
            LaneType,
            route_to_lane,
        )

        lane = route_to_lane("take a screenshot", "sess-1")
        result = ForegroundGuard().check("take a screenshot", lane)
        assert result.approved is True


# ---------------------------------------------------------------------------
# 6. Loop Engine (3 tests)
# ---------------------------------------------------------------------------


class TestLoopEngine:
    def test_loop_verifies_on_evidence(self) -> None:
        from substrate.workstation.loop_engine import (
            LoopContract,
            LoopStatus,
            advance_loop,
        )

        contract = LoopContract(
            task_description="open spotify",
            end_state_description="spotify is running",
        )
        evidence = {"process_running": True, "process_name": "Spotify"}
        updated, result = advance_loop(contract, evidence)
        assert result.verified is True
        assert updated.status == LoopStatus.verified

    def test_loop_fails_after_max_iterations(self) -> None:
        from substrate.workstation.loop_engine import (
            LoopContract,
            LoopStatus,
            advance_loop,
        )

        contract = LoopContract(
            task_description="open spotify",
            end_state_description="spotify is running",
            max_iterations=3,
        )
        for _ in range(3):
            contract, result = advance_loop(contract, {})
        assert contract.status == LoopStatus.failed

    def test_loop_report_generation(self) -> None:
        from substrate.workstation.loop_engine import (
            LoopContract,
            LoopProgressReport,
            create_loop_report,
        )

        contract = LoopContract(
            task_description="open spotify",
            end_state_description="spotify is running",
        )
        report = create_loop_report(contract, "lane-123")
        assert isinstance(report, LoopProgressReport)
        assert report.lane_id == "lane-123"
        assert report.contract_id == contract.contract_id


# ---------------------------------------------------------------------------
# 7. Search URL Generation (1 test)
# ---------------------------------------------------------------------------


class TestSearchUrl:
    def test_search_url_generation(self) -> None:
        from substrate.workstation.app_resolver import resolve_search_url

        url = resolve_search_url("search for python tutorials")
        assert url is not None
        assert "google.com/search" in url
        assert "python+tutorials" in url or "python%20tutorials" in url


# ---------------------------------------------------------------------------
# 8. Command Router Integration (2 tests)
# ---------------------------------------------------------------------------


class TestCommandRouterIntegration:
    def test_resolve_workstation_spotify_native(self) -> None:
        from substrate.workstation.command_router import resolve_workstation_target

        result = resolve_workstation_target("open spotify")
        assert result.get("is_native") is True
        assert result.get("lane_type") == "native_app"
        # Native apps should not have a target_url
        assert not result.get("target_url")

    def test_resolve_workstation_search_chrome(self) -> None:
        from substrate.workstation.command_router import resolve_workstation_target

        result = resolve_workstation_target("search for react docs")
        assert result.get("browser") == "chrome"
        assert "google.com/search" in result.get("target_url", "")


# ---------------------------------------------------------------------------
# 9. Field Trial Regression Tests (4 tests)
# ---------------------------------------------------------------------------


class TestFieldTrialRegressions:
    """Bugs found during Phase 14.13X Beast field trial."""

    def test_open_instagram_routes_to_background_browser(self) -> None:
        """Instagram is not in PLATFORM_PROCESS_MAP but 'open instagram'
        should resolve as a website via app_resolver fallback."""
        from substrate.workstation.work_lane import LaneType, route_to_lane

        lane = route_to_lane("open instagram", "sess-1")
        assert lane.lane_type == LaneType.background_browser

    def test_click_on_browser_tab_routes_to_foreground(self) -> None:
        """GUI interaction patterns must be checked before browser patterns
        so 'click on the browser tab' doesn't route to background_browser."""
        from substrate.workstation.work_lane import LaneType, route_to_lane

        lane = route_to_lane("click on the browser tab", "sess-1")
        assert lane.lane_type == LaneType.foreground

    def test_click_foreground_requires_approval(self) -> None:
        """GUI click actions should require approval when routed to foreground."""
        from substrate.workstation.work_lane import ForegroundGuard, route_to_lane

        lane = route_to_lane("click on the browser tab", "sess-1")
        result = ForegroundGuard().check("click on the browser tab", lane)
        assert result.requires_approval is True
        assert result.approved is False

    def test_open_reddit_routes_to_background_browser(self) -> None:
        """Unknown web apps with 'open' prefix should route to background_browser."""
        from substrate.workstation.work_lane import LaneType, route_to_lane

        lane = route_to_lane("open reddit", "sess-1")
        assert lane.lane_type == LaneType.background_browser


# ---------------------------------------------------------------------------
# 10. SSH Transport Guard (4 tests)
# ---------------------------------------------------------------------------


class TestSSHTransportGuard:
    """Phase 14.13Y: GUI actions must not route through SSH (Session 0)."""

    def test_gui_capability_blocked_via_ssh(self) -> None:
        from substrate.workstation.work_lane import check_transport_allowed

        result = check_transport_allowed("desktop.screenshot", "", "ssh")
        assert result.allowed is False
        assert "Session 0" in result.reason

    def test_gui_shell_command_blocked_via_ssh(self) -> None:
        from substrate.workstation.work_lane import check_transport_allowed

        result = check_transport_allowed("shell", "start Spotify", "ssh")
        assert result.allowed is False
        assert "mesh relay" in result.reason

    def test_non_gui_allowed_via_ssh(self) -> None:
        from substrate.workstation.work_lane import check_transport_allowed

        result = check_transport_allowed("shell", "tasklist /FI \"IMAGENAME eq python*\"", "ssh")
        assert result.allowed is True

    def test_mesh_relay_always_allowed(self) -> None:
        from substrate.workstation.work_lane import check_transport_allowed

        result = check_transport_allowed("desktop.screenshot", "", "mesh_relay")
        assert result.allowed is True


# ---------------------------------------------------------------------------
# 11. Background Browser Profile Lane (4 tests)
# ---------------------------------------------------------------------------


class TestBackgroundBrowserProfile:
    """Phase 14.13Y: Chrome worker profile background lane."""

    def test_worker_profile_lane_type(self) -> None:
        from substrate.workstation.work_lane import (
            IsolationLevel,
            LaneType,
            WorkLane,
        )

        lane = WorkLane(
            lane_type=LaneType.background_browser_profile,
            session_id="sess-1",
            chrome_profile="UMH_Worker_01",
        )
        assert lane.isolation_level == IsolationLevel.profile_isolated.value
        assert lane.is_operator_foreground is False

    def test_worker_profile_foreground_guard_approved(self) -> None:
        from substrate.workstation.work_lane import (
            ForegroundGuard,
            LaneType,
            WorkLane,
        )

        lane = WorkLane(
            lane_type=LaneType.background_browser_profile,
            session_id="sess-1",
        )
        result = ForegroundGuard().check("research TTS options", lane)
        assert result.approved is True
        assert result.requires_approval is False

    def test_worker_profile_hud_metadata(self) -> None:
        from substrate.workstation.work_lane import (
            LaneType,
            WorkLane,
            lane_hud_metadata,
        )

        lane = WorkLane(
            lane_type=LaneType.background_browser_profile,
            session_id="sess-1",
            chrome_profile="UMH_Worker_01",
        )
        hud = lane_hud_metadata(lane)
        assert hud["is_background"] is True
        assert hud["disruption_risk"] == "low"
        assert hud["isolation_level"] == "profile_isolated"
        assert hud["chrome_profile"] == "UMH_Worker_01"

    def test_worker_chrome_launch_cmd(self) -> None:
        from substrate.workstation.work_lane import build_worker_chrome_launch_cmd

        cmd = build_worker_chrome_launch_cmd("https://example.com")
        assert "--user-data-dir=" in cmd
        assert "--profile-directory=Default" in cmd
        assert '"https://example.com"' in cmd

    def test_worker_chrome_rejects_shell_injection(self) -> None:
        from substrate.workstation.work_lane import build_worker_chrome_launch_cmd

        with pytest.raises(ValueError, match="shell-unsafe"):
            build_worker_chrome_launch_cmd("https://example.com&calc.exe")
        with pytest.raises(ValueError, match="shell-unsafe"):
            build_worker_chrome_launch_cmd("https://x --disable-web-security")
        with pytest.raises(ValueError, match="shell-unsafe"):
            build_worker_chrome_launch_cmd("https://x(calc)")
        with pytest.raises(ValueError, match="shell-unsafe"):
            build_worker_chrome_launch_cmd("https://x!var")
        with pytest.raises(ValueError, match="http"):
            build_worker_chrome_launch_cmd("file:///etc/passwd")


# ---------------------------------------------------------------------------
# 12. Lane Inventory (3 tests)
# ---------------------------------------------------------------------------


class TestLaneInventory:
    """Phase 14.13Y: Truthful lane inventory — no fake sessions."""

    def test_base_inventory_has_two_lanes(self) -> None:
        from substrate.workstation.work_lane import get_lane_inventory

        lanes = get_lane_inventory()
        assert len(lanes) == 2
        assert lanes[0]["lane_id"] == "beast_service_session_0"
        assert lanes[1]["lane_id"] == "beast_operator_foreground"

    def test_worker_profile_adds_third_lane(self) -> None:
        from substrate.workstation.work_lane import get_lane_inventory

        lanes = get_lane_inventory(has_worker_profile=True)
        assert len(lanes) == 3
        worker = lanes[2]
        assert worker["lane_id"] == "beast_background_browser_01"
        assert worker["isolation_level"] == "profile_isolated"
        assert worker["chrome_profile"] == "UMH_Worker_01"

    def test_headless_adds_lane(self) -> None:
        from substrate.workstation.work_lane import get_lane_inventory

        lanes = get_lane_inventory(has_headless=True)
        assert len(lanes) == 3
        headless = lanes[2]
        assert headless["lane_id"] == "beast_headless_browser_01"
        assert headless["visible_to_operator"] is False


# ---------------------------------------------------------------------------
# 13. Headless Browser Lane (2 tests)
# ---------------------------------------------------------------------------


class TestHeadlessBrowserLane:
    """Phase 14.13Y: Headless browser for zero-disruption research."""

    def test_headless_lane_isolation(self) -> None:
        from substrate.workstation.work_lane import (
            IsolationLevel,
            LaneType,
            WorkLane,
        )

        lane = WorkLane(lane_type=LaneType.headless_browser, session_id="sess-1")
        assert lane.isolation_level == IsolationLevel.headless.value
        assert lane.is_operator_foreground is False

    def test_headless_hud_metadata(self) -> None:
        from substrate.workstation.work_lane import (
            LaneType,
            WorkLane,
            lane_hud_metadata,
        )

        lane = WorkLane(lane_type=LaneType.headless_browser, session_id="sess-1")
        hud = lane_hud_metadata(lane)
        assert hud["is_background"] is True
        assert hud["disruption_risk"] == "none"
        assert hud["isolation_level"] == "headless"


# ---------------------------------------------------------------------------
# 14. Node Qualifier Stripping (4 tests) — Phase 14.14A daily-driver fixes
# ---------------------------------------------------------------------------


class TestNodeQualifierStripping:
    """Phase 14.14A: 'Open Spotify on Beast' must resolve correctly."""

    def test_open_spotify_on_beast(self) -> None:
        from substrate.workstation.command_router import resolve_workstation_target

        result = resolve_workstation_target("Open Spotify on Beast")
        assert result.get("is_native") is True
        assert result.get("target_app") == "spotify"
        assert result.get("process_name") == "Spotify"

    def test_open_instagram_in_chrome_on_beast(self) -> None:
        from substrate.workstation.command_router import resolve_workstation_target

        result = resolve_workstation_target("Open Instagram in Chrome on Beast")
        assert result.get("target_app") == "instagram"
        assert "instagram.com" in result.get("target_url", "")

    def test_launch_discord_on_the_beast(self) -> None:
        from substrate.workstation.command_router import resolve_workstation_target

        result = resolve_workstation_target("launch discord on the beast")
        assert result.get("is_native") is True
        assert result.get("target_app") == "discord"

    def test_no_qualifier_still_works(self) -> None:
        from substrate.workstation.command_router import resolve_workstation_target

        result = resolve_workstation_target("Open Spotify")
        assert result.get("is_native") is True
        assert result.get("target_app") == "spotify"


# ---------------------------------------------------------------------------
# 15. VPS Classification Expansion (2 tests) — Phase 14.14A daily-driver fixes
# ---------------------------------------------------------------------------


class TestVPSClassificationExpansion:
    """Phase 14.14A: Natural VPS queries must classify correctly."""

    def test_docker_container_status_on_vps(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent

        assert classify_intent("Show me the Docker container status on VPS") == CommandIntent.VPS_CONTROL

    def test_docker_status(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent

        assert classify_intent("what is the docker status") == CommandIntent.VPS_CONTROL
