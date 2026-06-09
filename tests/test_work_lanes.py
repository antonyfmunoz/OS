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
