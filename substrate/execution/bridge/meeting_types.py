"""
Meeting types — bounded configuration for 11 voice-meeting archetypes.

Purpose
-------
ARCHITECTURE.md specifies "11 meeting types with pre-meeting brief,
during-meeting real-time assist (10 shortcuts), and post-meeting action
routing."  This module defines those types as a deterministic config layer
that the voice session runtime can query.  No LLM calls — pure data +
template expansion.

Design rules
------------
- Additive only.  Does not import from hot path.
- Deterministic.  Config is static; `get_pre_brief` does string formatting.
- Bounded.  Exactly 11 types.  Adding a 12th requires editing this file.
- Reversible.  Removing this file leaves everything else intact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─── Enum ────────────────────────────────────────────────────────────────────


class MeetingType(str, Enum):
    """The 11 canonical meeting archetypes supported by the voice interface."""

    SALES_CALL = "sales_call"
    INVESTOR_PITCH = "investor_pitch"
    TEAM_STANDUP = "team_standup"
    ONE_ON_ONE = "one_on_one"
    CLIENT_ONBOARDING = "client_onboarding"
    PERFORMANCE_REVIEW = "performance_review"
    BOARD_MEETING = "board_meeting"
    STRATEGY_SESSION = "strategy_session"
    PRODUCT_DEMO = "product_demo"
    INTERVIEW = "interview"
    PARTNERSHIP = "partnership"


# ─── Config dataclass ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MeetingConfig:
    """Static configuration for a single meeting type.

    Attributes
    ----------
    meeting_type : MeetingType
        Which archetype this config describes.
    pre_brief_template : str
        Template string for the pre-meeting brief.  Supports {key} placeholders
        filled by the context dict passed to ``get_pre_brief``.
    during_shortcuts : list[str]
        Exactly 10 quick-actions available during the meeting.
    post_actions : list[str]
        3-5 follow-up actions routed after the meeting ends.
    kpi_tracking : list[str]
        Metrics tracked for this meeting type.
    """

    meeting_type: MeetingType
    pre_brief_template: str
    during_shortcuts: list[str] = field(default_factory=list)
    post_actions: list[str] = field(default_factory=list)
    kpi_tracking: list[str] = field(default_factory=list)


# ─── Configs ─────────────────────────────────────────────────────────────────

MEETING_CONFIGS: dict[MeetingType, MeetingConfig] = {
    # ── SALES_CALL ───────────────────────────────────────────────────
    MeetingType.SALES_CALL: MeetingConfig(
        meeting_type=MeetingType.SALES_CALL,
        pre_brief_template=(
            "Preparing sales call brief.\n"
            "Prospect: {prospect_name}\n"
            "Company: {company}\n"
            "Deal stage: {deal_stage}\n"
            "Previous interactions: {interaction_count}\n"
            "Key pain points: {pain_points}\n"
            "Proposed solution: {proposed_solution}\n"
            "Pricing tier: {pricing_tier}\n"
            "Decision maker: {decision_maker}\n"
            "Competitive landscape: {competitors}\n"
            "Objective: close or advance to next stage."
        ),
        during_shortcuts=[
            "surface_objection_handler",
            "pull_pricing_sheet",
            "show_competitor_comparison",
            "display_case_study",
            "calculate_roi",
            "log_objection",
            "schedule_follow_up",
            "share_proposal_link",
            "flag_buying_signal",
            "request_decision_timeline",
        ],
        post_actions=[
            "send_follow_up_email_with_summary",
            "update_crm_deal_stage",
            "create_proposal_if_advanced",
            "schedule_next_touchpoint",
        ],
        kpi_tracking=[
            "conversion_rate",
            "average_deal_cycle_days",
            "objections_raised",
            "next_step_secured",
        ],
    ),
    # ── INVESTOR_PITCH ───────────────────────────────────────────────
    MeetingType.INVESTOR_PITCH: MeetingConfig(
        meeting_type=MeetingType.INVESTOR_PITCH,
        pre_brief_template=(
            "Preparing investor pitch brief.\n"
            "Investor: {investor_name}\n"
            "Fund: {fund_name}\n"
            "Thesis alignment: {thesis_alignment}\n"
            "Ask amount: {ask_amount}\n"
            "Current traction: {traction_summary}\n"
            "Burn rate: {burn_rate}\n"
            "Runway: {runway_months} months\n"
            "Previous round: {previous_round}\n"
            "Portfolio overlap: {portfolio_overlap}\n"
            "Objective: secure term sheet or next meeting."
        ),
        during_shortcuts=[
            "show_traction_metrics",
            "display_financial_model",
            "pull_market_size_data",
            "show_competitive_moat",
            "surface_team_bios",
            "display_product_roadmap",
            "show_unit_economics",
            "log_investor_question",
            "display_cap_table",
            "show_use_of_funds",
        ],
        post_actions=[
            "send_deck_and_data_room_link",
            "log_investor_feedback",
            "update_fundraising_pipeline",
            "schedule_partner_meeting_if_positive",
            "draft_follow_up_with_answers",
        ],
        kpi_tracking=[
            "meetings_to_term_sheet",
            "investor_response_rate",
            "questions_asked",
            "follow_up_secured",
        ],
    ),
    # ── TEAM_STANDUP ─────────────────────────────────────────────────
    MeetingType.TEAM_STANDUP: MeetingConfig(
        meeting_type=MeetingType.TEAM_STANDUP,
        pre_brief_template=(
            "Preparing standup brief.\n"
            "Team: {team_name}\n"
            "Sprint: {sprint_name}\n"
            "Days remaining: {days_remaining}\n"
            "Blockers from yesterday: {blockers}\n"
            "Velocity trend: {velocity_trend}\n"
            "Open PRs: {open_prs}\n"
            "Objective: surface blockers, align on today's priorities."
        ),
        during_shortcuts=[
            "show_sprint_board",
            "log_blocker",
            "assign_action_item",
            "show_burn_down",
            "flag_at_risk_item",
            "pull_yesterday_commits",
            "display_team_capacity",
            "escalate_blocker",
            "mark_item_done",
            "timebox_warning",
        ],
        post_actions=[
            "update_sprint_board_with_blockers",
            "notify_absent_members",
            "distribute_standup_summary",
        ],
        kpi_tracking=[
            "standup_duration_minutes",
            "blockers_raised",
            "blockers_resolved_same_day",
            "attendance_rate",
        ],
    ),
    # ── ONE_ON_ONE ───────────────────────────────────────────────────
    MeetingType.ONE_ON_ONE: MeetingConfig(
        meeting_type=MeetingType.ONE_ON_ONE,
        pre_brief_template=(
            "Preparing 1:1 brief.\n"
            "Participant: {participant_name}\n"
            "Role: {participant_role}\n"
            "Last 1:1: {last_meeting_date}\n"
            "Open action items: {open_items}\n"
            "Recent wins: {recent_wins}\n"
            "Growth areas: {growth_areas}\n"
            "Mood trend: {mood_trend}\n"
            "Objective: coach, unblock, and strengthen relationship."
        ),
        during_shortcuts=[
            "show_previous_notes",
            "log_action_item",
            "surface_goal_progress",
            "record_feedback_given",
            "record_feedback_received",
            "flag_career_topic",
            "show_performance_data",
            "schedule_follow_up_task",
            "mark_item_resolved",
            "capture_personal_note",
        ],
        post_actions=[
            "send_action_items_summary",
            "update_1on1_history",
            "schedule_next_1on1",
            "create_tasks_from_action_items",
        ],
        kpi_tracking=[
            "meeting_cadence_adherence",
            "action_items_completed",
            "feedback_exchanged_count",
            "topics_covered",
        ],
    ),
    # ── CLIENT_ONBOARDING ────────────────────────────────────────────
    MeetingType.CLIENT_ONBOARDING: MeetingConfig(
        meeting_type=MeetingType.CLIENT_ONBOARDING,
        pre_brief_template=(
            "Preparing client onboarding brief.\n"
            "Client: {client_name}\n"
            "Plan: {plan_tier}\n"
            "Signed date: {signed_date}\n"
            "Primary contact: {primary_contact}\n"
            "Implementation scope: {scope}\n"
            "Integration requirements: {integrations}\n"
            "Success criteria: {success_criteria}\n"
            "Objective: align on milestones and set client up for first win."
        ),
        during_shortcuts=[
            "show_onboarding_checklist",
            "share_setup_guide",
            "log_integration_requirement",
            "assign_onboarding_task",
            "display_timeline",
            "capture_custom_requirement",
            "show_knowledge_base_link",
            "set_milestone_date",
            "flag_risk",
            "confirm_access_granted",
        ],
        post_actions=[
            "send_onboarding_plan_document",
            "create_project_in_tracker",
            "schedule_first_check_in",
            "provision_client_accounts",
        ],
        kpi_tracking=[
            "time_to_first_value_days",
            "onboarding_completion_rate",
            "client_satisfaction_score",
            "setup_tasks_completed",
        ],
    ),
    # ── PERFORMANCE_REVIEW ───────────────────────────────────────────
    MeetingType.PERFORMANCE_REVIEW: MeetingConfig(
        meeting_type=MeetingType.PERFORMANCE_REVIEW,
        pre_brief_template=(
            "Preparing performance review brief.\n"
            "Employee: {employee_name}\n"
            "Role: {employee_role}\n"
            "Review period: {review_period}\n"
            "Goals set: {goals_count}\n"
            "Goals met: {goals_met}\n"
            "Peer feedback summary: {peer_summary}\n"
            "Self-assessment highlights: {self_assessment}\n"
            "Compensation band: {comp_band}\n"
            "Objective: deliver clear, actionable feedback and set next-period goals."
        ),
        during_shortcuts=[
            "show_goal_scorecard",
            "display_peer_feedback",
            "show_self_assessment",
            "log_strength",
            "log_growth_area",
            "set_next_period_goal",
            "show_compensation_data",
            "record_rating",
            "capture_development_plan_item",
            "summarize_discussion",
        ],
        post_actions=[
            "finalize_review_document",
            "submit_ratings_to_hr",
            "create_development_plan",
            "schedule_mid_period_check_in",
        ],
        kpi_tracking=[
            "goals_completion_rate",
            "review_timeliness",
            "development_actions_created",
            "rating_distribution",
        ],
    ),
    # ── BOARD_MEETING ────────────────────────────────────────────────
    MeetingType.BOARD_MEETING: MeetingConfig(
        meeting_type=MeetingType.BOARD_MEETING,
        pre_brief_template=(
            "Preparing board meeting brief.\n"
            "Meeting date: {meeting_date}\n"
            "Attendees: {attendees}\n"
            "Agenda: {agenda}\n"
            "Previous action items: {prev_actions}\n"
            "Financial summary: {financial_summary}\n"
            "Key risks: {key_risks}\n"
            "Strategic decisions needed: {decisions_needed}\n"
            "Objective: present progress, secure approvals, align on strategy."
        ),
        during_shortcuts=[
            "show_financial_dashboard",
            "display_kpi_summary",
            "pull_agenda_item",
            "log_board_resolution",
            "surface_risk_register",
            "show_competitive_update",
            "record_action_item",
            "display_org_chart",
            "show_fundraising_status",
            "call_vote",
        ],
        post_actions=[
            "distribute_board_minutes",
            "file_resolutions",
            "update_action_items_tracker",
            "send_follow_up_materials",
            "schedule_next_board_meeting",
        ],
        kpi_tracking=[
            "resolutions_passed",
            "action_items_assigned",
            "meeting_duration_minutes",
            "attendance_rate",
        ],
    ),
    # ── STRATEGY_SESSION ─────────────────────────────────────────────
    MeetingType.STRATEGY_SESSION: MeetingConfig(
        meeting_type=MeetingType.STRATEGY_SESSION,
        pre_brief_template=(
            "Preparing strategy session brief.\n"
            "Topic: {topic}\n"
            "Participants: {participants}\n"
            "Time horizon: {time_horizon}\n"
            "Current position: {current_position}\n"
            "Market context: {market_context}\n"
            "Constraints: {constraints}\n"
            "Options under consideration: {options}\n"
            "Objective: decide on strategic direction and assign execution owners."
        ),
        during_shortcuts=[
            "show_swot_analysis",
            "display_market_data",
            "log_decision",
            "capture_option",
            "score_option",
            "assign_owner",
            "show_resource_availability",
            "set_deadline",
            "flag_dependency",
            "summarize_consensus",
        ],
        post_actions=[
            "distribute_strategy_memo",
            "create_execution_plan_from_decisions",
            "assign_workstreams",
            "schedule_progress_review",
        ],
        kpi_tracking=[
            "decisions_made",
            "options_evaluated",
            "execution_owners_assigned",
            "follow_up_scheduled",
        ],
    ),
    # ── PRODUCT_DEMO ─────────────────────────────────────────────────
    MeetingType.PRODUCT_DEMO: MeetingConfig(
        meeting_type=MeetingType.PRODUCT_DEMO,
        pre_brief_template=(
            "Preparing product demo brief.\n"
            "Audience: {audience}\n"
            "Company: {company}\n"
            "Use case: {use_case}\n"
            "Features to highlight: {features}\n"
            "Known pain points: {pain_points}\n"
            "Demo environment: {demo_env}\n"
            "Competitor currently using: {current_solution}\n"
            "Objective: demonstrate value and move toward trial or purchase."
        ),
        during_shortcuts=[
            "switch_demo_scenario",
            "show_feature_highlight",
            "pull_pricing_info",
            "log_audience_question",
            "display_integration_options",
            "show_testimonial",
            "capture_feature_request",
            "share_screen_annotation",
            "show_comparison_chart",
            "offer_trial_signup",
        ],
        post_actions=[
            "send_demo_recording",
            "create_trial_account_if_requested",
            "send_tailored_proposal",
            "schedule_technical_deep_dive",
        ],
        kpi_tracking=[
            "demo_to_trial_rate",
            "questions_asked",
            "features_requested",
            "follow_up_meeting_secured",
        ],
    ),
    # ── INTERVIEW ────────────────────────────────────────────────────
    MeetingType.INTERVIEW: MeetingConfig(
        meeting_type=MeetingType.INTERVIEW,
        pre_brief_template=(
            "Preparing interview brief.\n"
            "Candidate: {candidate_name}\n"
            "Role: {target_role}\n"
            "Stage: {interview_stage}\n"
            "Resume highlights: {resume_highlights}\n"
            "Must-have skills: {must_have_skills}\n"
            "Nice-to-have skills: {nice_to_have_skills}\n"
            "Culture fit criteria: {culture_criteria}\n"
            "Previous round feedback: {prev_feedback}\n"
            "Objective: assess fit and provide great candidate experience."
        ),
        during_shortcuts=[
            "show_resume",
            "pull_interview_question",
            "log_answer_rating",
            "show_scoring_rubric",
            "flag_concern",
            "flag_strength",
            "display_role_requirements",
            "capture_candidate_question",
            "check_time_remaining",
            "advance_to_next_section",
        ],
        post_actions=[
            "submit_interview_scorecard",
            "send_candidate_thank_you",
            "update_hiring_pipeline",
            "schedule_next_round_if_pass",
        ],
        kpi_tracking=[
            "scorecard_completion_rate",
            "time_to_decision_hours",
            "candidate_nps",
            "offer_acceptance_rate",
        ],
    ),
    # ── PARTNERSHIP ───────────────────────────────────────────────────
    MeetingType.PARTNERSHIP: MeetingConfig(
        meeting_type=MeetingType.PARTNERSHIP,
        pre_brief_template=(
            "Preparing partnership brief.\n"
            "Partner: {partner_name}\n"
            "Partner company: {partner_company}\n"
            "Partnership type: {partnership_type}\n"
            "Mutual value: {mutual_value}\n"
            "Revenue model: {revenue_model}\n"
            "Integration points: {integration_points}\n"
            "Legal considerations: {legal_notes}\n"
            "Objective: align on terms and define joint execution plan."
        ),
        during_shortcuts=[
            "show_partnership_framework",
            "display_mutual_benefits",
            "log_term_agreed",
            "flag_open_question",
            "show_integration_architecture",
            "pull_legal_template",
            "calculate_revenue_share",
            "assign_joint_action",
            "set_milestone",
            "summarize_agreements",
        ],
        post_actions=[
            "send_partnership_summary",
            "draft_mou_or_agreement",
            "create_joint_project_plan",
            "schedule_kickoff_meeting",
        ],
        kpi_tracking=[
            "terms_agreed",
            "time_to_signed_agreement_days",
            "joint_revenue_generated",
            "integration_milestones_hit",
        ],
    ),
}


# ─── Public API ──────────────────────────────────────────────────────────────


def get_meeting_config(meeting_type: MeetingType) -> MeetingConfig:
    """Return the static config for a meeting type.

    Raises
    ------
    KeyError
        If the meeting type has no config (should never happen for valid enum
        members since all 11 are populated above).
    """
    try:
        return MEETING_CONFIGS[meeting_type]
    except KeyError:
        raise KeyError(f"No config for meeting type {meeting_type!r}") from None


def get_pre_brief(meeting_type: MeetingType, context: Optional[dict] = None) -> str:
    """Generate a pre-meeting brief by expanding the template with context.

    Missing keys in *context* are replaced with ``"N/A"`` so the brief is
    always complete even when the caller provides partial data.

    Parameters
    ----------
    meeting_type : MeetingType
        The archetype to generate a brief for.
    context : dict, optional
        Key-value pairs to fill template placeholders.

    Returns
    -------
    str
        The formatted pre-meeting brief text.
    """
    config = get_meeting_config(meeting_type)
    ctx = context or {}

    class _DefaultDict(dict):
        """Dict that returns 'N/A' for missing keys during str.format_map."""

        def __missing__(self, key: str) -> str:
            return "N/A"

    safe_ctx = _DefaultDict(ctx)
    return config.pre_brief_template.format_map(safe_ctx)


def get_post_actions(meeting_type: MeetingType, notes: str = "") -> list[str]:
    """Return post-meeting action items, optionally annotated with notes.

    Parameters
    ----------
    meeting_type : MeetingType
        The archetype whose post-actions to return.
    notes : str, optional
        Free-text meeting notes.  When provided, appended as context
        to each action item so downstream routing knows what happened.

    Returns
    -------
    list[str]
        Post-meeting actions.  If *notes* is non-empty, each action has
        the notes reference appended.
    """
    config = get_meeting_config(meeting_type)
    actions = list(config.post_actions)
    if notes and notes.strip():
        actions = [f"{a} [notes: {notes.strip()}]" for a in actions]
    return actions
