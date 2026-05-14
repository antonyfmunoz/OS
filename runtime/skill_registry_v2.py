"""
SkillRegistryV2 — first-class skill objects with trust scoring,
versioning, performance metrics, and execution tracking.

Extends the file-based SkillRegistry (V1) with:
  - Trust levels that gate what the skill can do autonomously
  - Version history stored in Neon
  - Execution + success tracking per skill
  - Semantic search via embeddings (delegates to V1)
  - Core skill seeding for Stage 1

All writes go to the skills table (existing schema).
Performance data is derived from the interactions table.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class SkillDomain(Enum):
    SALES       = 'sales'
    MARKETING   = 'marketing'
    RESEARCH    = 'research'
    OPERATIONS  = 'operations'
    FINANCE     = 'finance'
    PRODUCT     = 'product'
    ENGINEERING = 'engineering'
    LEGAL       = 'legal'
    EXECUTIVE   = 'executive'


class TrustLevel(Enum):
    OBSERVE    = 'observe'     # watch and log only
    RECOMMEND  = 'recommend'   # surface suggestions, human decides
    ASSIST     = 'assist'      # draft output, human approves before send
    EXECUTE    = 'execute'     # run and commit, log for review
    AUTONOMOUS = 'autonomous'  # run, commit, no approval required


# ─── Dataclass ────────────────────────────────────────────────────────────────

@dataclass
class SkillV2:
    id: str
    name: str
    domain: SkillDomain
    purpose: str
    when_to_use: str
    inputs: list[str]
    outputs: list[str]
    process: str
    trust_level: TrustLevel
    version: int = 1
    tools_required: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_markdown(self) -> str:
        """Serialize to 8-component markdown for storage in skills table."""
        inputs_str  = '\n'.join(f'- {i}' for i in self.inputs)
        outputs_str = '\n'.join(f'- {o}' for o in self.outputs)
        tools_str   = ', '.join(self.tools_required) or 'model_router'
        return (
            f"# Skill: {self.name}\n\n"
            f"## Purpose\n{self.purpose}\n\n"
            f"## When to Use\n{self.when_to_use}\n\n"
            f"## Inputs\n{inputs_str}\n\n"
            f"## Outputs\n{outputs_str}\n\n"
            f"## Process\n{self.process}\n\n"
            f"## Trust Level\n{self.trust_level.value}\n\n"
            f"## Domain\n{self.domain.value}\n\n"
            f"## Tools Required\n{tools_str}\n"
        )


# ─── Registry ─────────────────────────────────────────────────────────────────

class SkillRegistryV2:

    def __init__(self, ctx) -> None:
        self.ctx = ctx

    # ─── Write ────────────────────────────────────────────────────────────────

    def register(self, skill: SkillV2) -> bool:
        """
        Upsert a SkillV2 into the Neon skills table.
        Uses the existing skills schema: (id, org_id, name, content, version).
        """
        try:
            from state.stores.skill_store import SkillStore
            content = skill.to_markdown()
            SkillStore().upsert_skill(
                org_id=self.ctx.org_id,
                name=skill.id,
                content=content,
                version=skill.version,
            )
            print(f'[SkillV2] Registered: {skill.name}')
            return True
        except Exception as e:
            print(f'[SkillV2] Register failed ({skill.name}): {e}')
            return False

    # ─── Performance ──────────────────────────────────────────────────────────

    def get_skill_stats(self, skill_id: str) -> dict:
        """
        Derive performance stats from the interactions table.
        Returns total executions, successes, and success_rate.
        """
        try:
            from state.storage.db import get_conn
            with get_conn(self.ctx.org_id) as cur:
                # Total executions where this skill was used
                cur.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM interactions i
                    JOIN skills s ON s.id = i.skill_id
                    WHERE i.org_id = %s AND s.name = %s
                    """,
                    (self.ctx.org_id, skill_id),
                )
                total = (cur.fetchone() or {}).get('total', 0) or 0

                # Successes = interactions that led to a positive outcome
                cur.execute(
                    """
                    SELECT COUNT(*) AS successes
                    FROM interactions i
                    JOIN skills s ON s.id = i.skill_id
                    JOIN outcomes o ON o.interaction_id = i.id
                    WHERE i.org_id = %s AND s.name = %s
                      AND o.outcome_label IN ('booked', 'closed', 'reply')
                    """,
                    (self.ctx.org_id, skill_id),
                )
                successes = (cur.fetchone() or {}).get('successes', 0) or 0

            return {
                'skill_id':    skill_id,
                'total':       int(total),
                'successes':   int(successes),
                'success_rate': round(successes / total, 3) if total > 0 else 0.0,
            }
        except Exception as e:
            print(f'[SkillV2] Stats failed ({skill_id}): {e}')
            return {'skill_id': skill_id, 'total': 0, 'successes': 0, 'success_rate': 0.0}

    def get_all_stats(self) -> list[dict]:
        """Return performance stats for every registered V2 skill."""
        skill_ids = [s.id for s in _CORE_SKILLS]
        return [self.get_skill_stats(sid) for sid in skill_ids]

    # ─── Seed ─────────────────────────────────────────────────────────────────

    def seed_core_skills(self) -> int:
        """
        Register Stage 1 core skills as first-class Neon objects.
        Returns count of skills successfully registered.
        """
        count = sum(1 for s in _CORE_SKILLS if self.register(s))
        print(f'[SkillV2] Seeded {count}/{len(_CORE_SKILLS)} core skills')
        return count


# ─── Core skill definitions ───────────────────────────────────────────────────

_CORE_SKILLS: list[SkillV2] = [
    SkillV2(
        id='icp_qualify',
        name='ICP Qualification',
        domain=SkillDomain.SALES,
        purpose='Score a prospect against Ideal Customer Profile criteria.',
        when_to_use='When evaluating whether a prospect fits the target profile.',
        inputs=['prospect_profile', 'icp_criteria'],
        outputs=['score', 'fit_analysis', 'recommendation'],
        process=(
            'Analyze prospect profile against ICP criteria. '
            'Score 1-10. Return fit analysis and recommended next step.'
        ),
        trust_level=TrustLevel.EXECUTE,
        tools_required=['model_router'],
    ),
    SkillV2(
        id='outreach_draft',
        name='Outreach Message Draft',
        domain=SkillDomain.SALES,
        purpose='Draft personalized outreach message for a prospect.',
        when_to_use='When preparing to contact a qualified prospect.',
        inputs=['prospect_profile', 'channel', 'context'],
        outputs=['draft_message', 'subject_line'],
        process=(
            'Use prospect profile to craft personalized opener. '
            'Mirror their language and pain points. Keep under 150 words.'
        ),
        trust_level=TrustLevel.ASSIST,
        tools_required=['model_router'],
    ),
    SkillV2(
        id='objection_handle',
        name='Objection Handling',
        domain=SkillDomain.SALES,
        purpose='Generate response to a sales objection.',
        when_to_use='When a prospect raises an objection in conversation.',
        inputs=['objection', 'context', 'offer_details'],
        outputs=['response', 'next_step'],
        process=(
            'Identify objection type. '
            'Acknowledge, reframe, provide evidence. '
            'Guide toward next step.'
        ),
        trust_level=TrustLevel.ASSIST,
        tools_required=['model_router'],
    ),
    SkillV2(
        id='competitor_research',
        name='Competitor Research',
        domain=SkillDomain.RESEARCH,
        purpose='Research a competitor and compile intelligence report.',
        when_to_use=(
            'When analyzing competitive landscape '
            'or preparing for sales conversations.'
        ),
        inputs=['competitor_name', 'focus_areas'],
        outputs=['report', 'key_insights', 'differentiators'],
        process=(
            'Search for competitor info. '
            'Analyze offer, pricing, messaging, positioning. '
            'Identify gaps and opportunities.'
        ),
        trust_level=TrustLevel.EXECUTE,
        tools_required=['model_router', 'web_search'],
    ),
    SkillV2(
        id='morning_brief',
        name='Morning Brief Generation',
        domain=SkillDomain.EXECUTIVE,
        purpose='Generate comprehensive daily morning briefing.',
        when_to_use='Daily at 6am via orchestrator cron.',
        inputs=['date', 'ventures', 'pipeline', 'calendar'],
        outputs=['brief', 'priorities', 'action_items'],
        process=(
            'Pull pipeline data. '
            'Check calendar. '
            'Identify binding constraint. '
            'Surface one clear action.'
        ),
        trust_level=TrustLevel.AUTONOMOUS,
        tools_required=['model_router', 'neon_db', 'gws_connector'],
    ),
    SkillV2(
        id='follow_up_sequence',
        name='Follow-Up Sequence',
        domain=SkillDomain.SALES,
        purpose='Generate next follow-up message for a warm prospect.',
        when_to_use='When a lead has not responded after initial outreach.',
        inputs=['lead_profile', 'previous_messages', 'days_since_contact'],
        outputs=['follow_up_message', 'send_timing'],
        process=(
            'Review previous touchpoints. '
            'Identify most relevant new angle. '
            'Draft message that adds value without pressure.'
        ),
        trust_level=TrustLevel.ASSIST,
        tools_required=['model_router'],
    ),
    SkillV2(
        id='call_prep',
        name='Sales Call Preparation',
        domain=SkillDomain.SALES,
        purpose='Prepare briefing for an upcoming sales call.',
        when_to_use='Before a discovery or closing call.',
        inputs=['lead_profile', 'interaction_history', 'offer_details'],
        outputs=['call_brief', 'likely_objections', 'key_questions'],
        process=(
            'Synthesize lead history. '
            'Identify where they are in the decision process. '
            'Prepare objection responses and open questions.'
        ),
        trust_level=TrustLevel.EXECUTE,
        tools_required=['model_router'],
    ),
    SkillV2(
        id='playbook_new_inbound_lead',
        name='Playbook: New Inbound Lead',
        domain=SkillDomain.OPERATIONS,
        purpose='Handle every new inbound lead from any channel with a consistent, world-class response that qualifies, captures, and advances the relationship.',
        when_to_use='Any time a new person expresses interest in any Munoz Conglomerate venture for the first time.',
        inputs=['person_name', 'email', 'source', 'venture', 'message_content'],
        outputs=['lead_file_created', 'draft_response_queued', 'followup_task_created', 'notion_pipeline_updated'],
        process=(
            'Run person recognition. '
            'If known → ANTONY folder, stop. '
            'If new → create lead file, research sender, classify intent, '
            'draft venture-appropriate response, queue for approval, '
            'create 48h follow-up task, log to Neon, update Notion pipeline.'
        ),
        trust_level=TrustLevel.ASSIST,
        tools_required=['model_router', 'person_recognition', 'email_gps', 'neon_db'],
    ),
    SkillV2(
        id='playbook_investor_inquiry',
        name='Playbook: Investor Inquiry',
        domain=SkillDomain.EXECUTIVE,
        purpose='Handle inbound investor interest or outreach with appropriate gravity — never auto-respond, always escalate to Antony.',
        when_to_use='Any message signaling investor intent: fund, portfolio, term sheet, cap table, due diligence, interested in investing.',
        inputs=['sender_name', 'sender_company', 'message_content', 'source'],
        outputs=['antony_folder_routed', 'discord_alert_sent', 'research_brief', 'holding_response_queued'],
        process=(
            'Run person recognition. '
            'Route to ANTONY folder regardless of status. '
            'Alert Discord with full context. '
            'Research sender and fund. '
            'Draft holding response. '
            'Do NOT send without explicit approval. '
            'Log as high-priority event in Neon.'
        ),
        trust_level=TrustLevel.OBSERVE,
        tools_required=['model_router', 'person_recognition', 'email_gps', 'discord_utils', 'neon_db'],
    ),
    SkillV2(
        id='playbook_partnership_proposal',
        name='Playbook: Partnership Proposal',
        domain=SkillDomain.OPERATIONS,
        purpose='Handle inbound partnership proposals consistently — qualify before escalating, never commit without approval.',
        when_to_use='Any message proposing collaboration, JV, affiliate, co-marketing, referral, white-label, or integration.',
        inputs=['sender_name', 'sender_company', 'proposal_type', 'message_content'],
        outputs=['qualifying_response_queued_or_spam_filed', 'discord_flag', 'lead_file_if_qualified'],
        process=(
            'Run person recognition. '
            'Research sender. '
            'Classify proposal type. '
            'Apply quick filter: ICP alignment, clear value exchange, sender credibility. '
            'If spam → NEWSLETTERS, no response. '
            'If relevant → draft qualifying response, queue, Discord flag. '
            'If high-signal → ANTONY folder with research brief.'
        ),
        trust_level=TrustLevel.ASSIST,
        tools_required=['model_router', 'person_recognition', 'email_gps', 'discord_utils'],
    ),
    SkillV2(
        id='playbook_client_issue',
        name='Playbook: Client Issue or Complaint',
        domain=SkillDomain.OPERATIONS,
        purpose='Handle client complaints or issues with urgency, empathy, and professionalism — protect the relationship while keeping Antony informed.',
        when_to_use='Any message from an existing client expressing dissatisfaction, reporting a problem, requesting a refund, or threatening to leave.',
        inputs=['sender_name', 'client_status', 'issue_type', 'message_content'],
        outputs=['antony_folder_routed', 'discord_urgent_alert', 'context_brief', 'response_drafted_on_instruction'],
        process=(
            'Run person recognition. '
            'If not confirmed client → standard flow. '
            'If confirmed client → ANTONY folder immediately, '
            'Discord urgent alert, do not draft yet, '
            'research purchase history and prior issues, '
            'prepare context brief. '
            'Draft response only when Antony instructs.'
        ),
        trust_level=TrustLevel.OBSERVE,
        tools_required=['model_router', 'person_recognition', 'email_gps', 'discord_utils', 'neon_db'],
    ),
    SkillV2(
        id='playbook_speaking_podcast_request',
        name='Playbook: Speaking or Podcast Request',
        domain=SkillDomain.OPERATIONS,
        purpose='Handle inbound speaking or podcast requests — qualify the opportunity before escalating.',
        when_to_use='Any invitation to speak at an event, appear on a podcast, join a panel, contribute to a publication, or be interviewed.',
        inputs=['sender_name', 'show_or_event_name', 'estimated_audience_size', 'topic', 'format', 'is_paid'],
        outputs=['qualification_assessment', 'discord_flag_if_qualified', 'holding_response_or_decline_queued'],
        process=(
            'Research show/event and host. '
            'Estimate audience size and alignment. '
            'Apply qualification criteria: audience >10K, brand alignment, known host, or paid. '
            'If qualified → flag to Antony with research brief, draft holding response. '
            'If not → draft polite decline, queue for approval.'
        ),
        trust_level=TrustLevel.ASSIST,
        tools_required=['model_router', 'email_gps'],
    ),
    SkillV2(
        id='playbook_no_show_recovery',
        name='Playbook: No-Show Recovery',
        domain=SkillDomain.OPERATIONS,
        purpose='Recover no-show meetings professionally and re-engage the prospect without burning the relationship.',
        when_to_use='When a Calendly or calendar meeting is marked no-show or post-meeting capture detects no activity at meeting time.',
        inputs=['person_name', 'person_email', 'meeting_title', 'scheduled_time', 'no_show_count', 'calendly_link'],
        outputs=['notion_meeting_status_updated', 'recovery_email_queued', 'followup_task_created'],
        process=(
            'Wait 30 minutes past scheduled start. '
            'Update Notion meeting → Status: No-show. '
            'Draft recovery email with reschedule link. '
            'Queue for approval. '
            'Create 48h follow-up task. '
            'If second no-show → flag to Antony, do not auto-reschedule.'
        ),
        trust_level=TrustLevel.ASSIST,
        tools_required=['model_router', 'email_gps', 'meetings'],
    ),
    SkillV2(
        id='playbook_deal_closed',
        name='Playbook: Deal Closed',
        domain=SkillDomain.OPERATIONS,
        purpose='Execute the full deal-closed workflow — celebrate, onboard, document, and set the relationship up for success.',
        when_to_use='When a lead confirms they are in, payment is received, or Antony marks a deal closed in Discord or Notion.',
        inputs=['client_name', 'client_email', 'venture', 'amount', 'payment_confirmed', 'onboarding_steps'],
        outputs=['notion_pipeline_updated', 'wins_discord_post', 'welcome_email_queued', 'onboarding_tasks_created', 'revenue_event_logged'],
        process=(
            'Update Notion pipeline → Closed Won. '
            'Update lead file → Client. '
            'Post to #wins channel in Discord immediately. '
            'Draft welcome email (warm, personal, next steps). '
            'Queue welcome email for approval. '
            'Create onboarding tasks. '
            'Schedule kickoff call if applicable. '
            'Log revenue event to Neon.'
        ),
        trust_level=TrustLevel.EXECUTE,
        tools_required=['model_router', 'discord_utils', 'email_gps', 'neon_db'],
    ),
    SkillV2(
        id='playbook_job_inquiry',
        name='Playbook: Job Inquiry',
        domain=SkillDomain.OPERATIONS,
        purpose='Handle inbound job applications or hiring inquiries appropriately — not dismissively, but efficiently.',
        when_to_use='Any email or message about working for, joining, or collaborating with any Munoz Conglomerate venture.',
        inputs=['sender_name', 'sender_background', 'inquiry_type', 'message_content'],
        outputs=['routed_appropriately', 'discord_flag_if_interesting', 'holding_response_queued_if_relevant'],
        process=(
            'Classify: active candidate vs speculative inquiry. '
            'Research sender background quickly. '
            'If unqualified or spam → file, no response. '
            'If potentially interesting → flag to Antony with sender brief, draft holding response. '
            'If Antony proceeds → schedule intro call.'
        ),
        trust_level=TrustLevel.ASSIST,
        tools_required=['model_router', 'person_recognition', 'email_gps', 'discord_utils'],
    ),
    SkillV2(
        id='playbook_vendor_contract',
        name='Playbook: Vendor or Contract Received',
        domain=SkillDomain.LEGAL,
        purpose='Handle inbound contracts, NDAs, service agreements, and vendor documents with appropriate caution.',
        when_to_use='Any email containing an attached contract, NDA, service agreement, invoice, or legal document.',
        inputs=['sender_name', 'sender_company', 'document_type', 'attachment', 'deadline'],
        outputs=['antony_folder_routed', 'discord_alert_with_summary', 'attachment_saved_to_drive'],
        process=(
            'Identify document type. '
            'Route to ANTONY folder immediately. '
            'Alert Discord with document type, sender, key terms, and deadline. '
            'Save attachment to Drive: /Legal/Pending_Review/. '
            'Extract key terms: parties, obligations, financial terms, termination, deadlines. '
            'NEVER sign, agree, or acknowledge without explicit instruction.'
        ),
        trust_level=TrustLevel.OBSERVE,
        tools_required=['model_router', 'email_gps', 'discord_utils', 'gws_connector'],
    ),
    SkillV2(
        id='communication_templates',
        name='Communication Templates Library',
        domain=SkillDomain.OPERATIONS,
        purpose='Pre-approved, voice-matched response templates for every common communication scenario.',
        when_to_use='Any time DEX needs to draft a response and a standard scenario applies.',
        inputs=['scenario', 'recipient_name', 'context_fields'],
        outputs=['personalized_draft_ready_for_approval'],
        process=(
            'Identify scenario from template library. '
            'Select matching template. '
            'Personalize all bracketed fields. '
            'Review for Antony voice: direct, warm, no corporate speak, clear next step. '
            'Queue for approval.'
        ),
        trust_level=TrustLevel.ASSIST,
        tools_required=['model_router'],
    ),
]
