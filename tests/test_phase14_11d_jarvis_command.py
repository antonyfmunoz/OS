"""Phase 14.11D — Command routing + governance tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/OS")

import pytest


class TestClassifyIntent:
    def test_status_query(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what is happening?") == CommandIntent.STATUS_QUERY

    def test_status_whats_going_on(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what's going on?") == CommandIntent.STATUS_QUERY

    def test_sitrep(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("sitrep") == CommandIntent.STATUS_QUERY

    def test_resume_query(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what happened while i was gone?") == CommandIntent.RESUME_QUERY

    def test_resume_catch_me_up(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("catch me up") == CommandIntent.RESUME_QUERY

    def test_resume_im_back(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("I'm back") == CommandIntent.RESUME_QUERY

    def test_resume_good_morning(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("good morning") == CommandIntent.RESUME_QUERY

    def test_approval_query(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what needs approval?") == CommandIntent.APPROVAL_QUERY

    def test_approval_pending(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("anything pending approval?") == CommandIntent.APPROVAL_QUERY

    def test_mode_switch_developer(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("switch to developer mode") == CommandIntent.MODE_SWITCH

    def test_continuity_night(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("start night cycle") == CommandIntent.CONTINUITY_TRANSITION

    def test_continuity_away(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("stepping away") == CommandIntent.CONTINUITY_TRANSITION

    def test_mode_switch_review(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("switch to review mode") == CommandIntent.MODE_SWITCH

    def test_work_packet_draft(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("prepare the next safe step") == CommandIntent.WORK_PACKET_DRAFT

    def test_whats_next_is_explain_view(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what's next?") == CommandIntent.EXPLAIN_CURRENT_VIEW

    def test_navigation_show(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        # "show agents" now resolves to AGENT_QUERY (14.11E) — more specific than navigation
        assert classify_intent("show agents") == CommandIntent.AGENT_QUERY
        # "show dashboard" remains navigation
        assert classify_intent("show dashboard") == CommandIntent.COCKPIT_NAVIGATION

    def test_navigation_go_to(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("go to workspace") == CommandIntent.COCKPIT_NAVIGATION

    def test_navigation_open(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("open dashboard") == CommandIntent.COCKPIT_NAVIGATION

    def test_unknown(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("xyzzy foobar") == CommandIntent.UNKNOWN

    def test_case_insensitive(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("WHAT IS HAPPENING?") == CommandIntent.STATUS_QUERY

    # ── EXPLAIN_CURRENT_VIEW routing ─────────────────────────────────

    def test_explain_view_what_am_i_looking_at(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what am I looking at") == CommandIntent.EXPLAIN_CURRENT_VIEW

    def test_explain_view_what_should_i_do_next(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what should I do next") == CommandIntent.EXPLAIN_CURRENT_VIEW

    def test_explain_view_what_should_we_do_next(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what should we do next") == CommandIntent.EXPLAIN_CURRENT_VIEW

    def test_explain_view_what_is_this(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what is this") == CommandIntent.EXPLAIN_CURRENT_VIEW

    def test_explain_view_with_context(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what am I looking at, and what should I do next?") == CommandIntent.EXPLAIN_CURRENT_VIEW

    # ── Explicit work packet commands ────────────────────────────────

    def test_work_packet_explicit_draft(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("draft a work packet") == CommandIntent.WORK_PACKET_DRAFT

    def test_work_packet_create_for_this(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("create a work packet for this") == CommandIntent.WORK_PACKET_DRAFT

    def test_work_packet_create_task(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("create a task to fix auth") == CommandIntent.WORK_PACKET_DRAFT

    def test_work_packet_start_this_task(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("start this task") == CommandIntent.WORK_PACKET_DRAFT

    # ── Decompose stays decompose ────────────────────────────────────

    def test_decompose_turn_into_packets(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("turn this into work packets") == CommandIntent.DECOMPOSE_INTENT

    # ── Resume distinction ───────────────────────────────────────────

    def test_resume_what_should_resume(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("what happened while i was gone?") == CommandIntent.RESUME_QUERY

    # ── Council only on explicit command ──────────────────────────────

    def test_council_explicit(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("run council review") == CommandIntent.COUNCIL_REVIEW

    def test_is_this_good_enough_is_conversational(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("is this good enough") == CommandIntent.UNKNOWN

    # ── Advisory phrases stay conversational ─────────────────────────

    def test_start_thinking_is_conversational(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("start thinking through this") == CommandIntent.UNKNOWN

    def test_help_me_understand_is_conversational(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("help me understand this") == CommandIntent.UNKNOWN

    def test_lets_think_through_is_conversational(self) -> None:
        from substrate.workstation.command_router import CommandIntent, classify_intent
        assert classify_intent("let's think through this") == CommandIntent.UNKNOWN


class TestResolveNavigationTarget:
    def test_show_workspace(self) -> None:
        from substrate.workstation.command_router import resolve_navigation_target
        assert resolve_navigation_target("show workspace") == "workspace"

    def test_go_to_agents(self) -> None:
        from substrate.workstation.command_router import resolve_navigation_target
        assert resolve_navigation_target("go to agents") == "agents"

    def test_open_dashboard(self) -> None:
        from substrate.workstation.command_router import resolve_navigation_target
        assert resolve_navigation_target("open dashboard") == "dashboard"

    def test_command_center(self) -> None:
        from substrate.workstation.command_router import resolve_navigation_target
        assert resolve_navigation_target("show command center") == "commandcenter"

    def test_ide(self) -> None:
        from substrate.workstation.command_router import resolve_navigation_target
        assert resolve_navigation_target("show ide") == "editor"

    def test_unknown_panel(self) -> None:
        from substrate.workstation.command_router import resolve_navigation_target
        assert resolve_navigation_target("show foobar") == ""


class TestResolveModeTarget:
    def test_developer(self) -> None:
        from substrate.workstation.command_router import resolve_mode_target
        assert resolve_mode_target("switch to developer mode") == "developer"

    def test_night(self) -> None:
        from substrate.workstation.command_router import resolve_mode_target
        assert resolve_mode_target("start night cycle") == "night_sleeping"

    def test_away(self) -> None:
        from substrate.workstation.command_router import resolve_mode_target
        assert resolve_mode_target("stepping away") == "away"

    def test_returning(self) -> None:
        from substrate.workstation.command_router import resolve_mode_target
        assert resolve_mode_target("i'm back") == "returning"

    def test_review_mode(self) -> None:
        from substrate.workstation.command_router import resolve_mode_target
        assert resolve_mode_target("switch to review") == "REVIEW"

    def test_execute_mode(self) -> None:
        from substrate.workstation.command_router import resolve_mode_target
        assert resolve_mode_target("execute mode") == "EXECUTE"

    def test_plan_mode(self) -> None:
        from substrate.workstation.command_router import resolve_mode_target
        assert resolve_mode_target("plan mode") == "PLAN"


class TestGovernanceRequirement:
    def test_status_informational(self) -> None:
        from substrate.workstation.command_router import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.STATUS_QUERY) == GovernanceRequirement.INFORMATIONAL

    def test_resume_informational(self) -> None:
        from substrate.workstation.command_router import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.RESUME_QUERY) == GovernanceRequirement.INFORMATIONAL

    def test_approval_informational(self) -> None:
        from substrate.workstation.command_router import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.APPROVAL_QUERY) == GovernanceRequirement.INFORMATIONAL

    def test_navigation_informational(self) -> None:
        from substrate.workstation.command_router import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.COCKPIT_NAVIGATION) == GovernanceRequirement.INFORMATIONAL

    def test_mode_switch_informational(self) -> None:
        from substrate.workstation.command_router import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.MODE_SWITCH) == GovernanceRequirement.INFORMATIONAL

    def test_work_packet_requires_governance(self) -> None:
        from substrate.workstation.command_router import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.WORK_PACKET_DRAFT) == GovernanceRequirement.REQUIRES_GOVERNANCE

    def test_explain_view_informational(self) -> None:
        from substrate.workstation.command_router import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        assert governance_requirement(CommandIntent.EXPLAIN_CURRENT_VIEW) == GovernanceRequirement.INFORMATIONAL

    def test_informational_does_not_require_approval(self) -> None:
        from substrate.workstation.command_router import (
            CommandIntent, GovernanceRequirement, governance_requirement,
        )
        for intent in [
            CommandIntent.STATUS_QUERY,
            CommandIntent.RESUME_QUERY,
            CommandIntent.APPROVAL_QUERY,
            CommandIntent.COCKPIT_NAVIGATION,
            CommandIntent.EXPLAIN_CURRENT_VIEW,
        ]:
            gov = governance_requirement(intent)
            assert gov != GovernanceRequirement.REQUIRES_GOVERNANCE, f"{intent} should not require governance"


class TestCommandResult:
    def test_auto_id(self) -> None:
        from substrate.workstation.command_router import CommandResult
        r = CommandResult(intent="status_query", raw_text="sitrep")
        assert r.command_id.startswith("jcmd_")

    def test_auto_timestamp(self) -> None:
        from substrate.workstation.command_router import CommandResult
        r = CommandResult(intent="status_query", raw_text="sitrep")
        assert r.timestamp != ""

    def test_to_dict(self) -> None:
        from substrate.workstation.command_router import CommandResult
        r = CommandResult(
            intent="cockpit_navigation",
            raw_text="show agents",
            panel_target="agents",
        )
        d = r.to_dict()
        assert d["intent"] == "cockpit_navigation"
        assert d["panel_target"] == "agents"
