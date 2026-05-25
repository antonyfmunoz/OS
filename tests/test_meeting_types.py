"""Tests for substrate.execution.bridge.meeting_types."""

import sys

sys.path.insert(0, "/opt/OS/.claude/worktrees/close-all-gaps-v2")

import pytest

from substrate.execution.bridge.meeting_types import (
    MEETING_CONFIGS,
    MeetingConfig,
    MeetingType,
    get_meeting_config,
    get_post_actions,
    get_pre_brief,
)


class TestMeetingTypeEnum:
    """Verify the enum has exactly 11 members with correct values."""

    def test_exactly_11_types(self):
        assert len(MeetingType) == 11

    def test_all_values_are_strings(self):
        for mt in MeetingType:
            assert isinstance(mt.value, str)
            assert mt.value  # non-empty

    def test_expected_members_present(self):
        expected = {
            "SALES_CALL",
            "INVESTOR_PITCH",
            "TEAM_STANDUP",
            "ONE_ON_ONE",
            "CLIENT_ONBOARDING",
            "PERFORMANCE_REVIEW",
            "BOARD_MEETING",
            "STRATEGY_SESSION",
            "PRODUCT_DEMO",
            "INTERVIEW",
            "PARTNERSHIP",
        }
        actual = {mt.name for mt in MeetingType}
        assert actual == expected

    def test_str_enum_behavior(self):
        """MeetingType members compare equal to their string value."""
        assert MeetingType.SALES_CALL == "sales_call"
        assert str(MeetingType.INTERVIEW.value) == "interview"


class TestMeetingConfigs:
    """Verify MEETING_CONFIGS dict completeness and structure."""

    def test_all_11_types_have_configs(self):
        for mt in MeetingType:
            assert mt in MEETING_CONFIGS, f"Missing config for {mt.name}"

    def test_no_extra_configs(self):
        """No config for a key that isn't in the enum."""
        for key in MEETING_CONFIGS:
            assert isinstance(key, MeetingType)

    def test_every_config_has_10_shortcuts(self):
        for mt, cfg in MEETING_CONFIGS.items():
            assert len(cfg.during_shortcuts) == 10, (
                f"{mt.name} has {len(cfg.during_shortcuts)} shortcuts, expected 10"
            )

    def test_every_config_has_3_to_5_post_actions(self):
        for mt, cfg in MEETING_CONFIGS.items():
            count = len(cfg.post_actions)
            assert 3 <= count <= 5, (
                f"{mt.name} has {count} post_actions, expected 3-5"
            )

    def test_every_config_has_kpi_tracking(self):
        for mt, cfg in MEETING_CONFIGS.items():
            assert len(cfg.kpi_tracking) >= 1, (
                f"{mt.name} has no kpi_tracking entries"
            )

    def test_config_meeting_type_matches_key(self):
        """Each config's meeting_type field matches its dict key."""
        for mt, cfg in MEETING_CONFIGS.items():
            assert cfg.meeting_type == mt

    def test_pre_brief_template_is_nonempty(self):
        for mt, cfg in MEETING_CONFIGS.items():
            assert cfg.pre_brief_template.strip(), (
                f"{mt.name} has empty pre_brief_template"
            )

    def test_shortcuts_are_unique_per_type(self):
        """No duplicate shortcuts within a single meeting type."""
        for mt, cfg in MEETING_CONFIGS.items():
            assert len(cfg.during_shortcuts) == len(set(cfg.during_shortcuts)), (
                f"{mt.name} has duplicate shortcuts"
            )

    def test_post_actions_are_unique_per_type(self):
        for mt, cfg in MEETING_CONFIGS.items():
            assert len(cfg.post_actions) == len(set(cfg.post_actions)), (
                f"{mt.name} has duplicate post_actions"
            )


class TestGetMeetingConfig:
    """Verify the get_meeting_config lookup function."""

    def test_returns_config_for_valid_type(self):
        cfg = get_meeting_config(MeetingType.SALES_CALL)
        assert isinstance(cfg, MeetingConfig)
        assert cfg.meeting_type == MeetingType.SALES_CALL

    def test_returns_config_for_all_types(self):
        for mt in MeetingType:
            cfg = get_meeting_config(mt)
            assert cfg.meeting_type == mt


class TestGetPreBrief:
    """Verify pre-brief template expansion."""

    def test_full_context_fills_template(self):
        brief = get_pre_brief(
            MeetingType.SALES_CALL,
            {
                "prospect_name": "Jane Doe",
                "company": "Acme Corp",
                "deal_stage": "Qualification",
                "interaction_count": "3",
                "pain_points": "slow onboarding",
                "proposed_solution": "Initiate Arena",
                "pricing_tier": "Growth",
                "decision_maker": "VP Sales",
                "competitors": "None identified",
            },
        )
        assert "Jane Doe" in brief
        assert "Acme Corp" in brief
        assert "{prospect_name}" not in brief

    def test_missing_keys_replaced_with_na(self):
        brief = get_pre_brief(MeetingType.INVESTOR_PITCH, {})
        assert "N/A" in brief
        # Template structure should still be present
        assert "Investor:" in brief

    def test_none_context_treated_as_empty(self):
        brief = get_pre_brief(MeetingType.TEAM_STANDUP, None)
        assert "N/A" in brief
        assert "Team:" in brief

    def test_partial_context(self):
        brief = get_pre_brief(
            MeetingType.ONE_ON_ONE,
            {"participant_name": "Carlos"},
        )
        assert "Carlos" in brief
        assert "N/A" in brief  # other fields missing

    def test_every_type_produces_brief(self):
        for mt in MeetingType:
            brief = get_pre_brief(mt, {})
            assert isinstance(brief, str)
            assert len(brief) > 20  # non-trivial output


class TestGetPostActions:
    """Verify post-meeting action retrieval."""

    def test_returns_list_without_notes(self):
        actions = get_post_actions(MeetingType.SALES_CALL)
        assert isinstance(actions, list)
        assert len(actions) >= 3
        # No notes annotation
        for a in actions:
            assert "[notes:" not in a

    def test_returns_list_with_notes(self):
        actions = get_post_actions(
            MeetingType.INVESTOR_PITCH,
            notes="Investor liked traction, wants data room access",
        )
        assert isinstance(actions, list)
        for a in actions:
            assert "[notes:" in a
            assert "Investor liked traction" in a

    def test_empty_notes_treated_as_no_notes(self):
        actions = get_post_actions(MeetingType.INTERVIEW, notes="")
        for a in actions:
            assert "[notes:" not in a

    def test_whitespace_only_notes_treated_as_no_notes(self):
        actions = get_post_actions(MeetingType.PARTNERSHIP, notes="   ")
        for a in actions:
            assert "[notes:" not in a

    def test_notes_are_stripped(self):
        actions = get_post_actions(
            MeetingType.PRODUCT_DEMO,
            notes="  needs follow-up  ",
        )
        for a in actions:
            assert "  needs follow-up  " not in a
            assert "needs follow-up" in a

    def test_every_type_returns_actions(self):
        for mt in MeetingType:
            actions = get_post_actions(mt)
            assert len(actions) >= 3


class TestMeetingConfigFrozen:
    """MeetingConfig is frozen — mutation should fail."""

    def test_cannot_mutate_meeting_type(self):
        cfg = get_meeting_config(MeetingType.BOARD_MEETING)
        with pytest.raises(AttributeError):
            cfg.meeting_type = MeetingType.INTERVIEW  # type: ignore[misc]

    def test_cannot_mutate_template(self):
        cfg = get_meeting_config(MeetingType.STRATEGY_SESSION)
        with pytest.raises(AttributeError):
            cfg.pre_brief_template = "hacked"  # type: ignore[misc]
