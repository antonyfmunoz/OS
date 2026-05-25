"""EOS entity definitions — full entity hierarchy.

Maps ARCHITECTURE.md §3 entity model to Pydantic types from substrate.types.
User → Portfolio → Company → Department → Role, plus Workflows and Dashboards.
"""

from __future__ import annotations

from substrate.types import (
    Company,
    Dashboard,
    DashboardWidget,
    DashboardWidgetType,
    Department,
    OperatorType,
    Portfolio,
    Role,
    User,
    Workflow,
    WorkflowExecutionMode,
    WorkflowStep,
    WorkflowStepType,
    WorkflowTriggerType,
)


def default_departments(org_id: str, venture_id: str = "") -> list[Department]:
    """Return the 10 default EOS departments."""
    return [
        Department(
            name="Executive",
            slug="executive",
            organization_id=org_id,
            venture_id=venture_id,
            agent_name="eos-ceo",
            permission_tier="commit",
            roles=["ceo", "founder"],
            metrics=["revenue", "runway", "customer_count", "north_star_progress"],
            workflows=["morning_brief", "decision_review", "delegation"],
        ),
        Department(
            name="Sales",
            slug="sales",
            organization_id=org_id,
            venture_id=venture_id,
            agent_name="eos-sales",
            permission_tier="execute",
            roles=["sales_lead", "bdr", "account_executive"],
            metrics=["pipeline_value", "conversion_rate", "outreach_volume", "calls_booked"],
            workflows=["outreach", "follow_up", "pipeline_review"],
        ),
        Department(
            name="Marketing",
            slug="marketing",
            organization_id=org_id,
            venture_id=venture_id,
            agent_name="eos-marketing",
            permission_tier="execute",
            roles=["content_creator", "brand_manager", "growth_marketer"],
            metrics=["followers", "engagement_rate", "content_output", "cac"],
            workflows=["content_calendar", "campaign_execution", "brand_audit"],
        ),
        Department(
            name="Finance",
            slug="finance",
            organization_id=org_id,
            venture_id=venture_id,
            agent_name="eos-finance",
            permission_tier="commit",
            roles=["cfo", "bookkeeper", "financial_analyst"],
            metrics=["revenue", "expenses", "burn_rate", "runway_months", "ltv_cac_ratio"],
            workflows=["revenue_tracking", "expense_review", "budget_forecast"],
        ),
        Department(
            name="Customer Success",
            slug="customer_success",
            organization_id=org_id,
            venture_id=venture_id,
            agent_name="eos-customer-success",
            permission_tier="execute",
            roles=["cs_lead", "support_agent", "onboarding_specialist"],
            metrics=["nps", "churn_rate", "ticket_resolution_time", "satisfaction_score"],
            workflows=["ticket_routing", "onboarding", "churn_prevention"],
        ),
        Department(
            name="HR",
            slug="hr",
            organization_id=org_id,
            venture_id=venture_id,
            agent_name="eos-hr",
            permission_tier="execute",
            roles=["hr_lead", "recruiter", "people_ops"],
            metrics=["headcount", "hiring_pipeline", "time_to_hire", "retention_rate"],
            workflows=["hiring", "onboarding", "performance_review"],
        ),
        Department(
            name="Legal",
            slug="legal",
            organization_id=org_id,
            venture_id=venture_id,
            agent_name="eos-legal",
            permission_tier="commit",
            roles=["general_counsel", "compliance_officer"],
            metrics=["open_contracts", "compliance_status", "pending_reviews"],
            workflows=["contract_review", "compliance_check", "entity_management"],
        ),
        Department(
            name="Operations",
            slug="operations",
            organization_id=org_id,
            venture_id=venture_id,
            agent_name="eos-operations",
            permission_tier="execute",
            roles=["ops_lead", "systems_admin", "process_engineer"],
            metrics=["uptime", "automation_coverage", "bottleneck_count", "cycle_time"],
            workflows=["system_monitoring", "process_automation", "incident_response"],
        ),
        Department(
            name="Product",
            slug="product",
            organization_id=org_id,
            venture_id=venture_id,
            agent_name="eos-product",
            permission_tier="draft",
            roles=["product_manager", "ux_researcher", "product_analyst"],
            metrics=["feature_velocity", "user_satisfaction", "roadmap_completion"],
            workflows=["feature_prioritization", "user_research", "release_planning"],
        ),
        Department(
            name="Engineering",
            slug="engineering",
            organization_id=org_id,
            venture_id=venture_id,
            agent_name="eos-engineering",
            permission_tier="execute",
            roles=["tech_lead", "developer", "devops_engineer"],
            metrics=["deploy_frequency", "incident_count", "tech_debt_ratio", "test_coverage"],
            workflows=["code_review", "deployment", "incident_response"],
        ),
    ]


def default_roles(org_id: str, venture_id: str = "") -> list[Role]:
    """Return default roles for an EOS organization."""
    roles = []

    role_defs = [
        (
            "CEO",
            "executive",
            "eos-ceo",
            "commit",
            OperatorType.HYBRID,
            ["Strategic direction", "Capital allocation", "Team building", "Vision setting"],
            ["morning_brief", "decision_review"],
            ["revenue", "runway", "north_star"],
        ),
        (
            "Sales Lead",
            "sales",
            "eos-sales",
            "execute",
            OperatorType.HYBRID,
            ["Pipeline management", "Outreach strategy", "Close deals", "CRM hygiene"],
            ["outreach", "follow_up", "pipeline_review"],
            ["pipeline_value", "conversion_rate"],
        ),
        (
            "Content Creator",
            "marketing",
            "eos-marketing",
            "execute",
            OperatorType.AI,
            ["Content production", "Brand voice", "Channel management"],
            ["content_calendar", "content_creation"],
            ["content_output", "engagement_rate"],
        ),
        (
            "Bookkeeper",
            "finance",
            "eos-finance",
            "commit",
            OperatorType.AI,
            ["Expense tracking", "Revenue recording", "Invoice processing"],
            ["revenue_tracking", "expense_review"],
            ["expenses", "revenue"],
        ),
        (
            "Support Agent",
            "customer_success",
            "eos-customer-success",
            "execute",
            OperatorType.AI,
            ["Ticket response", "Customer onboarding", "Feedback collection"],
            ["ticket_routing", "onboarding"],
            ["resolution_time", "satisfaction"],
        ),
        (
            "Recruiter",
            "hr",
            "eos-hr",
            "execute",
            OperatorType.AI,
            ["Candidate sourcing", "Screening", "Interview coordination"],
            ["hiring", "candidate_screening"],
            ["pipeline_count", "time_to_hire"],
        ),
        (
            "Compliance Officer",
            "legal",
            "eos-legal",
            "commit",
            OperatorType.AI,
            ["Compliance monitoring", "Contract review", "Risk assessment"],
            ["compliance_check", "contract_review"],
            ["compliance_status", "open_contracts"],
        ),
        (
            "DevOps Engineer",
            "operations",
            "eos-operations",
            "execute",
            OperatorType.AI,
            ["System monitoring", "Deployment automation", "Incident response"],
            ["system_monitoring", "deployment"],
            ["uptime", "incident_count"],
        ),
        (
            "Product Manager",
            "product",
            "eos-product",
            "draft",
            OperatorType.HYBRID,
            ["Feature prioritization", "User research", "Roadmap management"],
            ["feature_prioritization", "release_planning"],
            ["feature_velocity", "user_satisfaction"],
        ),
        (
            "Developer",
            "engineering",
            "eos-engineering",
            "execute",
            OperatorType.AI,
            ["Code implementation", "Code review", "Architecture"],
            ["code_review", "deployment"],
            ["deploy_frequency", "test_coverage"],
        ),
    ]

    for name, dept, agent, tier, operator, resps, wfs, mets in role_defs:
        roles.append(
            Role(
                name=name,
                department=dept,
                organization_id=org_id,
                venture_id=venture_id,
                agent_name=agent,
                operator=operator,
                permission_tier=tier,
                responsibilities=resps,
                workflows=wfs,
                metrics=mets,
            )
        )

    return roles


def default_company(org_id: str, venture_id: str = "", name: str = "Primary") -> Company:
    """Return a default EOS company instance."""
    depts = default_departments(org_id, venture_id)
    return Company(
        name=name,
        organization_id=org_id,
        venture_id=venture_id,
        stage=1,
        stage_name="validation",
        departments=[d.slug for d in depts],
        north_star="$10K/month net profit",
    )


def default_portfolio(user_id: str, org_id: str = "") -> Portfolio:
    """Return a default portfolio for a founder."""
    return Portfolio(
        user_id=user_id,
        companies=[org_id] if org_id else [],
    )


def default_user(email: str, display_name: str = "") -> User:
    """Return a default founder user."""
    return User(
        email=email,
        display_name=display_name or email.split("@")[0],
        role_scope="founder",
    )


def default_workflows(org_id: str, venture_id: str = "") -> list[Workflow]:
    """Return default EOS workflows across departments."""
    return [
        Workflow(
            name="Morning Brief",
            slug="morning_brief",
            department="executive",
            organization_id=org_id,
            trigger_type=WorkflowTriggerType.SCHEDULED,
            trigger_config={"cron": "0 7 * * *"},
            steps=[
                WorkflowStep(
                    name="Gather KPIs",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="analyze",
                ),
                WorkflowStep(
                    name="Check calendar",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="read",
                ),
                WorkflowStep(
                    name="Draft brief",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="draft_brief",
                ),
                WorkflowStep(
                    name="Deliver to founder",
                    step_type=WorkflowStepType.NOTIFICATION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="report",
                ),
            ],
            output_artifacts=["morning_brief_report"],
        ),
        Workflow(
            name="Outreach Sequence",
            slug="outreach",
            department="sales",
            organization_id=org_id,
            trigger_type=WorkflowTriggerType.MANUAL,
            steps=[
                WorkflowStep(
                    name="Research prospect",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="research_prospect",
                ),
                WorkflowStep(
                    name="Draft message",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="draft_message",
                ),
                WorkflowStep(
                    name="Review gate",
                    step_type=WorkflowStepType.APPROVAL_GATE,
                    approval_required=True,
                    execution_mode=WorkflowExecutionMode.HUMAN,
                ),
                WorkflowStep(
                    name="Send message",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="send_dm",
                ),
                WorkflowStep(
                    name="Schedule follow-up",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="create_task",
                ),
            ],
            output_artifacts=["outreach_message", "follow_up_task"],
            permission_tier="execute",
        ),
        Workflow(
            name="Content Calendar",
            slug="content_calendar",
            department="marketing",
            organization_id=org_id,
            trigger_type=WorkflowTriggerType.SCHEDULED,
            trigger_config={"cron": "0 9 * * 1"},
            steps=[
                WorkflowStep(
                    name="Audit content pipeline",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="analyze",
                ),
                WorkflowStep(
                    name="Generate content ideas",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="draft_content",
                ),
                WorkflowStep(
                    name="Schedule posts",
                    step_type=WorkflowStepType.APPROVAL_GATE,
                    approval_required=True,
                    execution_mode=WorkflowExecutionMode.HUMAN,
                ),
                WorkflowStep(
                    name="Publish",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="post_content",
                ),
            ],
            output_artifacts=["content_plan", "scheduled_posts"],
        ),
        Workflow(
            name="Expense Review",
            slug="expense_review",
            department="finance",
            organization_id=org_id,
            trigger_type=WorkflowTriggerType.SCHEDULED,
            trigger_config={"cron": "0 18 * * 5"},
            steps=[
                WorkflowStep(
                    name="Pull transactions",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="read",
                ),
                WorkflowStep(
                    name="Categorize expenses",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="classify",
                ),
                WorkflowStep(
                    name="Flag anomalies",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="analyze",
                ),
                WorkflowStep(
                    name="Generate report",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="report",
                ),
                WorkflowStep(
                    name="Founder review",
                    step_type=WorkflowStepType.APPROVAL_GATE,
                    approval_required=True,
                    execution_mode=WorkflowExecutionMode.HUMAN,
                ),
            ],
            output_artifacts=["expense_report"],
            permission_tier="commit",
        ),
        Workflow(
            name="Ticket Routing",
            slug="ticket_routing",
            department="customer_success",
            organization_id=org_id,
            trigger_type=WorkflowTriggerType.EVENT,
            trigger_config={"event": "new_support_ticket"},
            steps=[
                WorkflowStep(
                    name="Classify ticket",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="classify",
                ),
                WorkflowStep(
                    name="Route to agent",
                    step_type=WorkflowStepType.DECISION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    branch_conditions={"urgent": "escalate", "normal": "auto_respond"},
                ),
                WorkflowStep(
                    name="Draft response",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="draft_message",
                ),
                WorkflowStep(
                    name="Send response",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="send_dm",
                ),
            ],
            output_artifacts=["ticket_response"],
        ),
        Workflow(
            name="Hiring Pipeline",
            slug="hiring",
            department="hr",
            organization_id=org_id,
            trigger_type=WorkflowTriggerType.MANUAL,
            steps=[
                WorkflowStep(
                    name="Draft job description",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="create_document",
                ),
                WorkflowStep(
                    name="Source candidates",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="browser_research",
                ),
                WorkflowStep(
                    name="Screen applications",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="score",
                ),
                WorkflowStep(
                    name="Schedule interviews",
                    step_type=WorkflowStepType.APPROVAL_GATE,
                    approval_required=True,
                    execution_mode=WorkflowExecutionMode.HUMAN,
                ),
            ],
            output_artifacts=["job_posting", "candidate_shortlist"],
        ),
        Workflow(
            name="Contract Review",
            slug="contract_review",
            department="legal",
            organization_id=org_id,
            trigger_type=WorkflowTriggerType.MANUAL,
            steps=[
                WorkflowStep(
                    name="Extract key terms",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="analyze",
                ),
                WorkflowStep(
                    name="Flag risk clauses",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="classify",
                ),
                WorkflowStep(
                    name="Generate summary",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="report",
                ),
                WorkflowStep(
                    name="Human review",
                    step_type=WorkflowStepType.APPROVAL_GATE,
                    approval_required=True,
                    execution_mode=WorkflowExecutionMode.HUMAN,
                ),
            ],
            output_artifacts=["contract_summary", "risk_assessment"],
            permission_tier="commit",
        ),
        Workflow(
            name="Incident Response",
            slug="incident_response",
            department="operations",
            organization_id=org_id,
            trigger_type=WorkflowTriggerType.EVENT,
            trigger_config={"event": "system_alert"},
            steps=[
                WorkflowStep(
                    name="Assess severity",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="classify",
                ),
                WorkflowStep(
                    name="Notify stakeholders",
                    step_type=WorkflowStepType.NOTIFICATION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="report",
                ),
                WorkflowStep(
                    name="Execute runbook",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.HYBRID,
                    action_type="execute_workflow",
                ),
                WorkflowStep(
                    name="Post-mortem",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="create_document",
                ),
            ],
            output_artifacts=["incident_report", "post_mortem"],
        ),
        Workflow(
            name="Feature Prioritization",
            slug="feature_prioritization",
            department="product",
            organization_id=org_id,
            trigger_type=WorkflowTriggerType.SCHEDULED,
            trigger_config={"cron": "0 10 * * 1"},
            steps=[
                WorkflowStep(
                    name="Collect feedback",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="read",
                ),
                WorkflowStep(
                    name="ICE score features",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="score",
                ),
                WorkflowStep(
                    name="Update roadmap",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="create_document",
                ),
                WorkflowStep(
                    name="Review gate",
                    step_type=WorkflowStepType.APPROVAL_GATE,
                    approval_required=True,
                    execution_mode=WorkflowExecutionMode.HUMAN,
                ),
            ],
            output_artifacts=["prioritized_backlog"],
            permission_tier="draft",
        ),
        Workflow(
            name="Code Review & Deploy",
            slug="code_review_deploy",
            department="engineering",
            organization_id=org_id,
            trigger_type=WorkflowTriggerType.EVENT,
            trigger_config={"event": "pull_request_opened"},
            steps=[
                WorkflowStep(
                    name="Static analysis",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="analyze",
                ),
                WorkflowStep(
                    name="AI code review",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AI,
                    action_type="review_code",
                ),
                WorkflowStep(
                    name="Human approval",
                    step_type=WorkflowStepType.APPROVAL_GATE,
                    approval_required=True,
                    execution_mode=WorkflowExecutionMode.HUMAN,
                ),
                WorkflowStep(
                    name="Deploy",
                    step_type=WorkflowStepType.ACTION,
                    execution_mode=WorkflowExecutionMode.AUTOMATED,
                    action_type="production_deployment",
                ),
            ],
            output_artifacts=["review_report", "deployment_log"],
            permission_tier="execute",
        ),
    ]


SKILL_ALLOCATION: dict[str, list[str]] = {
    "executive": [
        "meta/ceo_framework",
        "meta/portfolio_framework",
        "Ops/weekly_ceo_report",
        "Ops/prepare_war_room_agenda",
    ],
    "sales": [
        "Sales/analyze_conversation",
        "Sales/analyze_dm_conversation",
        "Sales/analyze_dm_conversation_titled",
        "Sales/binding_constraint_diagnosis",
        "Sales/call_booking_confirmation",
        "Sales/call_to_close",
        "Sales/crm_stage_update",
        "Sales/extract_icp_insight",
        "Sales/follow_up_sequence",
        "Sales/generate_follow_up_message",
        "Sales/generate_outreach_from_intel",
        "Sales/lead_nurture",
        "Sales/lead_personalization_from_profile",
        "Sales/objection_handling",
        "Sales/opener_batch_audit",
        "Sales/pre_call_research_brief",
        "Sales/proof_promise_plan_close",
        "Sales/qualify_lead",
        "Sales/stage_transition_assessment",
        "Sales/summarize_sales_call",
        "Outreach/dm_opener",
        "Outreach/reply_handler",
        "Research/analyze_icp_signal",
        "Research/detect_icp_patterns",
        "Research/generate_market_report",
        "Research/icp_signal_detection",
        "Research/person_recognition_lookup",
        "Research/process_signal_queue",
    ],
    "marketing": [
        "Marketing/Content/draft_arena_content_post",
        "Marketing/Content/generate_content_from_intel",
        "Marketing/campaign_diagnosis",
        "Marketing/content_calendar",
        "Content/content_video_brief",
        "Content/hook_performance_analysis",
        "content/analyze_content_performance",
        "content/discover_content_angles",
        "content/generate_content_script",
    ],
    "finance": [],
    "customer_success": [
        "CustomerSuccess/churn_prevention",
        "CustomerSuccess/onboarding_sequence",
    ],
    "hr": [],
    "legal": [],
    "operations": [
        "Ops/communication_templates",
        "Ops/playbook_client_issue",
        "Ops/playbook_deal_closed",
        "Ops/playbook_investor_inquiry",
        "Ops/playbook_job_inquiry",
        "Ops/playbook_new_inbound_lead",
        "Ops/playbook_no_show_recovery",
        "Ops/playbook_partnership_proposal",
        "Ops/playbook_speaking_podcast_request",
        "Ops/playbook_vendor_contract",
        "Ops/schedule_event",
    ],
    "product": [],
    "engineering": [
        "developer/adversarial_review",
    ],
}


def get_skills_for_department(slug: str) -> list[str]:
    """Return skill paths allocated to a department."""
    return SKILL_ALLOCATION.get(slug, [])


def get_department_for_skill(skill_path: str) -> str | None:
    """Return which department owns a given skill path, or None."""
    for dept, skills in SKILL_ALLOCATION.items():
        if skill_path in skills:
            return dept
    return None


def default_dashboards(org_id: str) -> list[Dashboard]:
    """Return default role dashboards — one per department with standard widgets."""
    dept_configs = [
        (
            "executive",
            [
                DashboardWidgetType.METRIC_CARD,
                DashboardWidgetType.TASK_BOARD,
                DashboardWidgetType.AI_CHAT,
                DashboardWidgetType.APPROVAL_QUEUE,
                DashboardWidgetType.TIMELINE,
            ],
        ),
        (
            "sales",
            [
                DashboardWidgetType.CRM_TABLE,
                DashboardWidgetType.TASK_BOARD,
                DashboardWidgetType.METRIC_CARD,
                DashboardWidgetType.AI_CHAT,
                DashboardWidgetType.COMMUNICATION,
            ],
        ),
        (
            "marketing",
            [
                DashboardWidgetType.TASK_BOARD,
                DashboardWidgetType.METRIC_CARD,
                DashboardWidgetType.DOCUMENT_LIST,
                DashboardWidgetType.AI_CHAT,
                DashboardWidgetType.TIMELINE,
            ],
        ),
        (
            "finance",
            [
                DashboardWidgetType.METRIC_CARD,
                DashboardWidgetType.APPROVAL_QUEUE,
                DashboardWidgetType.DOCUMENT_LIST,
                DashboardWidgetType.AI_CHAT,
            ],
        ),
        (
            "customer_success",
            [
                DashboardWidgetType.TASK_BOARD,
                DashboardWidgetType.CRM_TABLE,
                DashboardWidgetType.METRIC_CARD,
                DashboardWidgetType.AI_CHAT,
                DashboardWidgetType.COMMUNICATION,
            ],
        ),
        (
            "hr",
            [
                DashboardWidgetType.TASK_BOARD,
                DashboardWidgetType.DOCUMENT_LIST,
                DashboardWidgetType.METRIC_CARD,
                DashboardWidgetType.AI_CHAT,
            ],
        ),
        (
            "legal",
            [
                DashboardWidgetType.DOCUMENT_LIST,
                DashboardWidgetType.APPROVAL_QUEUE,
                DashboardWidgetType.METRIC_CARD,
                DashboardWidgetType.AI_CHAT,
            ],
        ),
        (
            "operations",
            [
                DashboardWidgetType.METRIC_CARD,
                DashboardWidgetType.TASK_BOARD,
                DashboardWidgetType.TIMELINE,
                DashboardWidgetType.AI_CHAT,
                DashboardWidgetType.TOOL_PANEL,
            ],
        ),
        (
            "product",
            [
                DashboardWidgetType.TASK_BOARD,
                DashboardWidgetType.METRIC_CARD,
                DashboardWidgetType.WORKFLOW_LIST,
                DashboardWidgetType.AI_CHAT,
                DashboardWidgetType.DOCUMENT_LIST,
            ],
        ),
        (
            "engineering",
            [
                DashboardWidgetType.TASK_BOARD,
                DashboardWidgetType.METRIC_CARD,
                DashboardWidgetType.TOOL_PANEL,
                DashboardWidgetType.AI_CHAT,
                DashboardWidgetType.TIMELINE,
            ],
        ),
    ]
    dashboards = []
    for dept, widget_types in dept_configs:
        widgets = [
            DashboardWidget(
                widget_type=wt,
                title=wt.value.replace("_", " ").title(),
                position=i,
                width=6
                if wt in (DashboardWidgetType.CRM_TABLE, DashboardWidgetType.TASK_BOARD)
                else 4,
            )
            for i, wt in enumerate(widget_types)
        ]
        dashboards.append(
            Dashboard(
                department=dept,
                organization_id=org_id,
                widgets=widgets,
            )
        )
    return dashboards
