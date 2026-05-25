"""EOS entity definitions — departments, roles, and portfolio structure.

Maps ARCHITECTURE.md §3 entity model to Pydantic types from substrate.types.
"""

from __future__ import annotations

from substrate.types import Department, OperatorType, Role


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
