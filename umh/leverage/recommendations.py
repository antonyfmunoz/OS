"""Phase 87 leverage recommendations — action recommendation logic.

Deterministic rules map opportunity characteristics to recommended actions.
The Initiate Arena first workflow gets specific leverage recommendations
based on the 16-stage revenue loop.

No execution. No mutation. No adapter calls. No LLM calls.
"""

from __future__ import annotations

from typing import Any

from umh.leverage.contracts import (
    LeverageAction,
    LeverageAssessment,
    LeverageConfidence,
    LeverageOpportunity,
    LeverageRecommendation,
    LeverageRiskLevel,
    LeverageTimeHorizon,
    LeverageType,
    _lev_id,
)
from umh.leverage.scoring import LeverageScorecard, build_leverage_scorecard


def recommend_leverage_action(
    opp: LeverageOpportunity,
    context: str | None = None,
) -> LeverageAction:
    ctx = (context or "").lower()
    title = opp.title.lower()
    desc = opp.description.lower()
    combined = f"{title} {desc} {ctx}"

    if opp.confidence in (LeverageConfidence.VERY_LOW, LeverageConfidence.LOW):
        return LeverageAction.RESEARCH

    if opp.risk_level in (LeverageRiskLevel.HIGH, LeverageRiskLevel.CRITICAL):
        if "real-world" in combined or "financial" in combined or "legal" in combined:
            return LeverageAction.APPROVE_AND_EXECUTE_LATER
        if opp.confidence == LeverageConfidence.MEDIUM:
            return LeverageAction.SIMULATE

    if any(
        kw in combined
        for kw in [
            "personal brand",
            "sales call",
            "close",
            "high-trust",
            "judgment",
            "creative direction",
            "vision",
            "strategy",
            "relationship",
            "dm conversation",
            "qualify",
        ]
    ):
        return LeverageAction.DO_SELF

    if any(kw in combined for kw in ["low value", "no strategic", "busywork", "vanity"]):
        return LeverageAction.ELIMINATE

    if any(
        kw in combined
        for kw in [
            "repeated",
            "rule-based",
            "low-risk",
            "automated",
            "scheduling",
            "posting",
            "notification",
            "tracking",
        ]
    ):
        return LeverageAction.AUTOMATE

    if any(
        kw in combined
        for kw in [
            "template",
            "sop",
            "checklist",
            "reusable",
            "standardize",
        ]
    ):
        return LeverageAction.TEMPLATE

    if any(
        kw in combined
        for kw in [
            "systemize",
            "workflow",
            "process",
            "pipeline",
        ]
    ):
        return LeverageAction.SYSTEMIZE

    if any(
        kw in combined
        for kw in [
            "bottleneck",
            "bandwidth",
            "delegate",
            "assign",
        ]
    ):
        if "ongoing" in combined or "permanent" in combined:
            return LeverageAction.HIRE
        return LeverageAction.DELEGATE

    if any(kw in combined for kw in ["buy", "purchase", "subscribe", "tool"]):
        return LeverageAction.BUY

    if any(kw in combined for kw in ["partner", "joint", "collab"]):
        return LeverageAction.PARTNER

    if any(kw in combined for kw in ["outsource", "external", "freelance"]):
        return LeverageAction.OUTSOURCE

    if any(kw in combined for kw in ["defer", "wait", "not ready", "dependency"]):
        return LeverageAction.DEFER

    return LeverageAction.DO_SELF


def build_leverage_recommendation(
    opp: LeverageOpportunity,
    scorecard: LeverageScorecard | None = None,
    context: str | None = None,
) -> LeverageRecommendation:
    if scorecard is None:
        scorecard = build_leverage_scorecard(opp)

    action = recommend_leverage_action(opp, context)

    _ACTION_RATIONALE: dict[LeverageAction, str] = {
        LeverageAction.DO_SELF: "Requires unique user judgment, brand presence, or high-trust interaction",
        LeverageAction.DELEGATE: "Human skill/time bottleneck exists and task is not core user leverage",
        LeverageAction.AUTOMATE: "Process is repeated, rule-based, and low-risk",
        LeverageAction.TEMPLATE: "Process repeats but still needs human/context customization",
        LeverageAction.HIRE: "Ongoing need exceeds ad hoc delegation capacity",
        LeverageAction.BUY: "External tool/product is cheaper than building and not strategically critical",
        LeverageAction.PARTNER: "Network/distribution/complementary capability matters",
        LeverageAction.OUTSOURCE: "Execution is needed but not strategic",
        LeverageAction.SYSTEMIZE: "Workflow is repeated and currently chaotic",
        LeverageAction.ELIMINATE: "Task has low leverage and no strategic value",
        LeverageAction.DEFER: "Dependencies missing or risk too high right now",
        LeverageAction.RESEARCH: "Evidence is insufficient — gather data before committing",
        LeverageAction.SIMULATE: "Outcome uncertainty is high — model before executing",
        LeverageAction.APPROVE_AND_EXECUTE_LATER: "Real-world action requires governance approval",
        LeverageAction.UNKNOWN: "Insufficient information to recommend an action",
    }

    _DEFAULT_GUARDRAILS: dict[LeverageAction, list[str]] = {
        LeverageAction.DO_SELF: ["Time-box the effort", "Capture process for future templating"],
        LeverageAction.DELEGATE: ["Write clear brief", "Define done criteria", "Review output"],
        LeverageAction.AUTOMATE: [
            "Test before deploying",
            "Monitor for failures",
            "Keep manual fallback",
        ],
        LeverageAction.TEMPLATE: ["Version the template", "Review after 3 uses", "Keep it simple"],
        LeverageAction.HIRE: ["Start with trial period", "Define role clearly", "Set KPIs"],
        LeverageAction.BUY: ["Evaluate alternatives", "Check exit cost", "Monitor usage"],
        LeverageAction.PARTNER: ["Define terms upfront", "Set review date", "Protect IP"],
        LeverageAction.OUTSOURCE: ["Write SOW", "Set milestones", "Retain ownership"],
        LeverageAction.SYSTEMIZE: ["Map current state first", "Start simple", "Iterate"],
        LeverageAction.ELIMINATE: ["Confirm no hidden dependencies", "Document why eliminated"],
        LeverageAction.DEFER: ["Set trigger condition for revisit", "Don't forget it"],
        LeverageAction.RESEARCH: ["Set time limit", "Define what evidence you need", "Decide then"],
        LeverageAction.SIMULATE: ["Define success criteria", "Keep scope small", "Measure"],
        LeverageAction.APPROVE_AND_EXECUTE_LATER: [
            "Document the action",
            "Get explicit approval",
            "Set execution date",
        ],
    }

    _DEFAULT_NON_ACTIONS: dict[LeverageAction, list[str]] = {
        LeverageAction.DO_SELF: ["Do not delegate core judgment", "Do not skip this"],
        LeverageAction.AUTOMATE: ["Do not over-engineer", "Do not automate unvalidated process"],
        LeverageAction.ELIMINATE: ["Do not confuse low-leverage with zero-leverage"],
        LeverageAction.RESEARCH: ["Do not execute while evidence is insufficient"],
    }

    return LeverageRecommendation(
        recommendation_id=_lev_id("rec"),
        action=action,
        summary=f"{action.value.upper()}: {opp.title}",
        rationale=_ACTION_RATIONALE.get(action, ""),
        leverage_type=opp.leverage_type,
        expected_multiplier=opp.expected_multiplier,
        required_resources=opp.required_resources,
        required_tools=opp.applicable_tools,
        first_step=f"Start with: {opp.title}"
        if action == LeverageAction.DO_SELF
        else f"Prepare: {opp.title}",
        guardrails=_DEFAULT_GUARDRAILS.get(action, []),
        non_actions=_DEFAULT_NON_ACTIONS.get(action, []),
        risk_level=opp.risk_level,
        confidence=opp.confidence,
        time_horizon=LeverageTimeHorizon(opp.time_to_impact)
        if opp.time_to_impact in [e.value for e in LeverageTimeHorizon]
        else LeverageTimeHorizon.UNKNOWN,
    )


def assess_leverage_for_goal(
    goal: str,
    context: str | None = None,
    resources: list[Any] | None = None,
    tools: list[Any] | None = None,
    constraints: list[str] | None = None,
) -> LeverageAssessment:
    return LeverageAssessment(
        assessment_id=_lev_id("assess"),
        context=context or "",
        goal=goal,
        constraints=constraints or [],
        resources=resources or [],
        tools=tools or [],
        opportunities=[],
        bottlenecks=[],
        warnings=[
            "Assessment requires opportunities to be populated — use build_initiate_arena_leverage_recommendations() for defaults"
        ],
    )


def assess_leverage_for_eos_tomorrow_plan(
    plan: Any = None,
) -> LeverageAssessment:
    recs = build_initiate_arena_leverage_recommendations(plan)
    opportunities = [
        LeverageOpportunity(
            opportunity_id=_lev_id("opp"),
            title=rec.summary,
            leverage_type=rec.leverage_type,
            description=rec.rationale,
            expected_multiplier=rec.expected_multiplier,
            risk_level=rec.risk_level,
            confidence=rec.confidence,
        )
        for rec in recs
    ]
    return LeverageAssessment(
        assessment_id=_lev_id("assess"),
        context="EOS Tomorrow Operating Loop — Initiate Arena first workflow",
        goal="$10K/month net from Initiate Arena",
        constraints=["pre-revenue", "solo founder", "limited capital"],
        opportunities=opportunities,
        highest_leverage_opportunity=recs[0].summary if recs else "",
        bottlenecks=["founder bandwidth", "unproven offer", "no team"],
    )


def build_initiate_arena_leverage_recommendations(
    plan: Any = None,
) -> list[LeverageRecommendation]:
    recs: list[LeverageRecommendation] = []

    _STAGE_RECS = [
        {
            "title": "Create and publish content daily",
            "action": LeverageAction.DO_SELF,
            "leverage_type": LeverageType.CONTENT_MEDIA,
            "rationale": "Personal brand content is the primary distribution vehicle — requires authentic voice",
            "multiplier": 5.0,
            "risk": LeverageRiskLevel.LOW,
            "confidence": LeverageConfidence.HIGH,
            "horizon": LeverageTimeHorizon.WEEK,
            "first_step": "Batch-produce 7 content pieces for the week",
            "guardrails": ["Track posts/week KPI", "Review engagement weekly"],
            "non_actions": [
                "Do not outsource personal brand voice",
                "Do not post without strategy",
            ],
            "resources": ["user attention", "content assets"],
            "tools": ["Instagram", "TikTok", "YouTube"],
        },
        {
            "title": "Start DM and comment conversations with engaged prospects",
            "action": LeverageAction.DO_SELF,
            "leverage_type": LeverageType.ATTENTION_FOCUS,
            "rationale": "High-trust selling requires personal engagement early — cannot delegate trust-building",
            "multiplier": 8.0,
            "risk": LeverageRiskLevel.LOW,
            "confidence": LeverageConfidence.HIGH,
            "horizon": LeverageTimeHorizon.TODAY,
            "first_step": "Respond to today's comments and open 5 DM conversations",
            "guardrails": ["Track DMs opened per week", "Use templates for openers"],
            "non_actions": ["Do not spam", "Do not use generic messages"],
            "resources": ["user attention", "user time"],
            "tools": ["Instagram", "Discord"],
        },
        {
            "title": "Qualify leads against Initiate Arena avatar",
            "action": LeverageAction.DO_SELF,
            "leverage_type": LeverageType.ATTENTION_FOCUS,
            "rationale": "Qualification requires judgment about fit — core sales skill",
            "multiplier": 6.0,
            "risk": LeverageRiskLevel.LOW,
            "confidence": LeverageConfidence.HIGH,
            "horizon": LeverageTimeHorizon.WEEK,
            "first_step": "Review current leads and score against qualification criteria",
            "guardrails": ["Document qualification criteria", "Track qualified rate"],
            "non_actions": ["Do not skip qualification", "Do not sell to wrong avatar"],
            "resources": ["user attention"],
            "tools": ["CRM / Spreadsheet"],
        },
        {
            "title": "Capture and document objections from every sales conversation",
            "action": LeverageAction.SYSTEMIZE,
            "leverage_type": LeverageType.DATA,
            "rationale": "Objection data improves close rate and informs offer iteration",
            "multiplier": 3.0,
            "risk": LeverageRiskLevel.NONE,
            "confidence": LeverageConfidence.HIGH,
            "horizon": LeverageTimeHorizon.WEEK,
            "first_step": "Create objection tracking template",
            "guardrails": ["Review objections weekly", "Update sales script accordingly"],
            "non_actions": ["Do not ignore objections", "Do not lose objection data"],
            "resources": ["user attention"],
            "tools": ["CRM / Spreadsheet", "Templates and SOPs"],
        },
        {
            "title": "Close or book sales calls with qualified leads",
            "action": LeverageAction.DO_SELF,
            "leverage_type": LeverageType.ATTENTION_FOCUS,
            "rationale": "High-trust closing requires personal presence and judgment",
            "multiplier": 10.0,
            "risk": LeverageRiskLevel.LOW,
            "confidence": LeverageConfidence.MEDIUM,
            "horizon": LeverageTimeHorizon.WEEK,
            "first_step": "Book or conduct next sales call",
            "guardrails": ["Track close rate", "Track show-up rate", "Follow up within 24h"],
            "non_actions": ["Do not close without qualifying first"],
            "resources": ["user attention", "user time"],
            "tools": ["Calendly or equivalent"],
        },
        {
            "title": "Create reusable DM opener and follow-up templates",
            "action": LeverageAction.TEMPLATE,
            "leverage_type": LeverageType.SYSTEMS_PROCESS,
            "rationale": "Templates reduce time-per-DM while maintaining personalization",
            "multiplier": 3.0,
            "risk": LeverageRiskLevel.NONE,
            "confidence": LeverageConfidence.HIGH,
            "horizon": LeverageTimeHorizon.WEEK,
            "first_step": "Write 3 DM opener variants and 2 follow-up sequences",
            "guardrails": ["Personalize each send", "A/B test variants", "Update quarterly"],
            "non_actions": ["Do not send 100% canned messages"],
            "resources": ["content assets"],
            "tools": ["Templates and SOPs"],
        },
        {
            "title": "Track KPIs in EOS Tomorrow Operating Loop",
            "action": LeverageAction.AUTOMATE,
            "leverage_type": LeverageType.CODE_SOFTWARE,
            "rationale": "KPI tracking is repeated, rule-based, and benefits from automation",
            "multiplier": 2.0,
            "risk": LeverageRiskLevel.NONE,
            "confidence": LeverageConfidence.HIGH,
            "horizon": LeverageTimeHorizon.WEEK,
            "first_step": "Use EOS Tomorrow Loop review phase to capture daily metrics",
            "guardrails": ["Review KPIs during end-of-day review", "Weekly trend analysis"],
            "non_actions": ["Do not track vanity metrics"],
            "resources": ["EOS Tomorrow Operating Loop"],
            "tools": ["EntrepreneurOS", "UMH"],
        },
        {
            "title": "End-of-day review using Tomorrow Loop",
            "action": LeverageAction.SYSTEMIZE,
            "leverage_type": LeverageType.SYSTEMS_PROCESS,
            "rationale": "Daily review is a repeated process that compounds learning",
            "multiplier": 2.5,
            "risk": LeverageRiskLevel.NONE,
            "confidence": LeverageConfidence.HIGH,
            "horizon": LeverageTimeHorizon.TODAY,
            "first_step": "Run review phase: what worked, what didn't, blockers, tomorrow top 3",
            "guardrails": ["Never skip review", "Keep it under 15 minutes"],
            "non_actions": ["Do not skip end-of-day review"],
            "resources": ["user attention", "EOS Tomorrow Operating Loop"],
            "tools": ["EntrepreneurOS"],
        },
        {
            "title": "Convert repeated actions into templates and SOPs",
            "action": LeverageAction.TEMPLATE,
            "leverage_type": LeverageType.SYSTEMS_PROCESS,
            "rationale": "Every repeated manual action is a template candidate — compounds over time",
            "multiplier": 4.0,
            "risk": LeverageRiskLevel.NONE,
            "confidence": LeverageConfidence.HIGH,
            "horizon": LeverageTimeHorizon.MONTH,
            "first_step": "Identify top 3 repeated tasks from this week and create SOPs",
            "guardrails": ["Start simple", "Iterate after 3 uses", "Version control"],
            "non_actions": ["Do not template one-time tasks", "Do not over-engineer"],
            "resources": ["user attention", "content assets"],
            "tools": ["Templates and SOPs", "Obsidian"],
        },
    ]

    for sr in _STAGE_RECS:
        recs.append(
            LeverageRecommendation(
                recommendation_id=_lev_id("rec"),
                action=sr["action"],
                summary=sr["title"],
                rationale=sr["rationale"],
                leverage_type=sr["leverage_type"],
                expected_multiplier=sr["multiplier"],
                required_resources=sr["resources"],
                required_tools=sr["tools"],
                first_step=sr["first_step"],
                guardrails=sr["guardrails"],
                non_actions=sr["non_actions"],
                risk_level=sr["risk"],
                confidence=sr["confidence"],
                time_horizon=sr["horizon"],
            )
        )

    return recs


def leverage_recommendation_to_dict(rec: LeverageRecommendation) -> dict[str, Any]:
    return rec.to_dict()
