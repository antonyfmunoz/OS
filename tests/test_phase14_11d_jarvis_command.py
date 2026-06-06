"""Phase 14.11D — Jarvis command routing + governance tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest


class TestClassifyIntent:
    def test_status_query(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("what is happening?") == CommandIntent.STATUS_QUERY

    def test_status_whats_going_on(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("what's going on?") == CommandIntent.STATUS_QUERY

    def test_sitrep(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("sitrep") == CommandIntent.STATUS_QUERY

    def test_resume_query(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("what happened while i was gone?") == CommandIntent.RESUME_QUERY

    def test_resume_catch_me_up(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("catch me up") == CommandIntent.RESUME_QUERY

    def test_resume_im_back(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("I'm back") == CommandIntent.RESUME_QUERY

    def test_resume_good_morning(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("good morning") == CommandIntent.RESUME_QUERY

    def test_approval_query(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("what needs approval?") == CommandIntent.APPROVAL_QUERY

    def test_approval_pending(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("anything pending approval?") == CommandIntent.APPROVAL_QUERY

    def test_mode_switch_developer(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("switch to developer mode") == CommandIntent.MODE_SWITCH

    def test_mode_switch_night(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("start night cycle") == CommandIntent.MODE_SWITCH

    def test_mode_switch_away(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("stepping away") == CommandIntent.MODE_SWITCH

    def test_mode_switch_review(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("switch to review mode") == CommandIntent.MODE_SWITCH

    def test_work_packet_draft(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("prepare the next safe step") == CommandIntent.WORK_PACKET_DRAFT

    def test_work_packet_whats_next(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("what's next?") == CommandIntent.WORK_PACKET_DRAFT

    def test_navigation_show(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("show agents") == CommandIntent.COCKPIT_NAVIGATION

    def test_navigation_go_to(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("go to workspace") == CommandIntent.COCKPIT_NAVIGATION

    def test_navigation_open(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("open dashboard") == CommandIntent.COCKPIT_NAVIGATION

    def test_unknown(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("xyzzy foobar") == CommandIntent.UNKNOWN

    def test_case_insensitive(self) -> None:
        from substrate.workstation.jarvis_command import CommandIntent, classify_intent
        assert classify_intent("WHAT IS HAPPENING?") == CommandIntent.STATUS_QUERY


class TestResolveNavigationTarget:
    def test_show_workspace(self) -> None:
        from substrate.workstation.jarvis_command import resolve_navigation_target
        assert resolve_navigation_target("show workspace") == "workspace"

    def test_go_to_agents(self) -> None:
        from substrate.workstation.jarvis_command import resolve_navigation_target
        assert resolve_navigation_target("go to agents") == "agents"

    def test_open_dashboard(self) -> None:
        from substrate.workstation.jarvis_command import resolve_navigation_target
        assert resolve_navigation_target("open dashboard") == "dashboard"

    def test_command_center(self) -> None:
        from substrate.workstation.jarvis_command import resolve_navigation_target
        assert resolve_navigation_target("show command center") == "dashboard"

    def test_ide(self) -> None:
        from substrate.workstation.jarvis_command import resolve_navigation_target
        assert resolve_navigation_target("show ide") == "editor"

    def test_unknown_panel(self) -> None:
        from substrate.workstation.jarvis_command import resolve_navigation_target
        assert resolve_navigation_target("show foobar") == ""


class TestResolveModeTarget:
    def test_developer(self) -> None:
        from substrate.workstation.jarvis_command import resolve_mode_target
        assert resolve_mode_target("switch to developer mode") == "developer"

    def test_night(self) -> None:
        from substrate.workstation.jarvis_command import resolve_mode_target
        assert resolve_mode_target("start night cycle") == "night_sleeping"

    def test_away(self) -> None:
        from substrate.workstation.jarvis_command import resolve_mode_target
        assert resolve_mode_target("stepping away") == "away"

    def test_returning(self) -> None:
        from substrate.workstation.jarvis_command import resolve_mode_target
        assert resolve_mode_target("i'm back") == "returning"

    def test_review_mode(self) -> None:
        from substrate.workstation.jarvis_command import resolve_mode_target
        assert resolve_mode_target("switch to review") == "REVIEW"

    def test_execute_mode(self) -> None:
        from substrate.workstation.jarvis_command import resolve_mode_target
        assert resolve_mode_target("execute mode") == "EXECUTE"

    def test_plan_mode(self) -> None:
        from substrate.workstation.jarvis_command import resolve_mode_target
        assert resolve_mode_target("plan mode") == "PLAN"


class TestGovernanceRequirement:
    def test_status_informational(self) -> None:
        from substrate.workstation.jarvis_command import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.STATUS_QUERY) == GovernanceRequirement.INFORMATIONAL

    def test_resume_informational(self) -> None:
        from substrate.workstation.jarvis_command import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.RESUME_QUERY) == GovernanceRequirement.INFORMATIONAL

    def test_approval_informational(self) -> None:
        from substrate.workstation.jarvis_command import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.APPROVAL_QUERY) == GovernanceRequirement.INFORMATIONAL

    def test_navigation_informational(self) -> None:
        from substrate.workstation.jarvis_command import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.COCKPIT_NAVIGATION) == GovernanceRequirement.INFORMATIONAL

    def test_mode_switch_informational(self) -> None:
        from substrate.workstation.jarvis_command import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.MODE_SWITCH) == GovernanceRequirement.INFORMATIONAL

    def test_work_packet_requires_governance(self) -> None:
        from substrate.workstation.jarvis_command import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.WORK_PACKET_DRAFT) == GovernanceRequirement.REQUIRES_GOVERNANCE

    def test_informational_does_not_require_approval(self) -> None:
        from substrate.workstation.jarvis_command import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        for intent in [
            CommandIntent.STATUS_QUERY,
            CommandIntent.RESUME_QUERY,
            CommandIntent.APPROVAL_QUERY,
            CommandIntent.COCKPIT_NAVIGATION,
        ]:
            gov = governance_requirement(intent)
            assert gov != GovernanceRequirement.REQUIRES_GOVERNANCE, f"{intent} should not require governance"


class TestJarvisCommandResult:
    def test_auto_id(self) -> None:
        from substrate.workstation.jarvis_command import JarvisCommandResult
        r = JarvisCommandResult(intent="status_query", raw_text="sitrep")
        assert r.command_id.startswith("jcmd_")

    def test_auto_timestamp(self) -> None:
        from substrate.workstation.jarvis_command import JarvisCommandResult
        r = JarvisCommandResult(intent="status_query", raw_text="sitrep")
        assert r.timestamp != ""

    def test_to_dict(self) -> None:
        from substrate.workstation.jarvis_command import JarvisCommandResult
        r = JarvisCommandResult(
            intent="cockpit_navigation",
            raw_text="show agents",
            panel_target="agents",
        )
        d = r.to_dict()
        assert d["intent"] == "cockpit_navigation"
        assert d["panel_target"] == "agents"
