"""Phase 87B progressive onboarding — tier-based ingestion plan generation.

Tier 0: Manual core (user tells EOS identity, goals, companies)
Tier 1: Local/AI archives (notes, voice memos, AI chat exports, ebooks)
Tier 2: Workspace (email, calendar, tasks, docs, code, messaging, CRM)
Tier 3: Social/algorithm (social media, video, audio, advertising)
Tier 4: Computer-use read-only (browser history, screen capture)
Tier 5: Continuous assimilation (real-time feeds, webhooks, always-on)

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution.
"""

from __future__ import annotations

from umh.ingestion.contracts import (
    OnboardingIngestionPlan,
    OnboardingTier,
    SourceClass,
    _ingest_id,
)
from umh.ingestion.source_classes import get_default_tier, list_source_classes


_TIER_DESCRIPTIONS: dict[OnboardingTier, str] = {
    OnboardingTier.TIER_0_MANUAL_CORE: (
        "User tells EOS who they are: identity, goals, companies, ventures, "
        "key relationships, strategic context. No automation — pure declaration."
    ),
    OnboardingTier.TIER_1_LOCAL_ARCHIVES: (
        "Import existing local archives: notes, voice memos, AI chat exports, "
        "ebooks, documents. User provides files — EOS parses and candidates."
    ),
    OnboardingTier.TIER_2_WORKSPACE: (
        "Connect workspace tools: email, calendar, tasks, docs, code repos, "
        "messaging, CRM, cloud storage. OAuth or API key — user approves each."
    ),
    OnboardingTier.TIER_3_SOCIAL_ALGORITHM: (
        "Connect social and algorithm sources: social media feeds, saved videos, "
        "liked content, advertising platforms, video/audio platforms."
    ),
    OnboardingTier.TIER_4_COMPUTER_USE: (
        "Read-only computer observation: browser history, screen captures, "
        "active window tracking. Requires explicit opt-in and local agent."
    ),
    OnboardingTier.TIER_5_CONTINUOUS: (
        "Always-on assimilation: real-time webhooks, continuous feed monitoring, "
        "live event streams. Requires running services and governance."
    ),
}

_TIER_PREREQUISITES: dict[OnboardingTier, list[str]] = {
    OnboardingTier.TIER_0_MANUAL_CORE: [],
    OnboardingTier.TIER_1_LOCAL_ARCHIVES: ["Tier 0 completed (identity declared)"],
    OnboardingTier.TIER_2_WORKSPACE: [
        "Tier 0 completed (identity declared)",
        "At least one Tier 1 source ingested",
    ],
    OnboardingTier.TIER_3_SOCIAL_ALGORITHM: [
        "Tier 2 partially connected (email + calendar minimum)",
        "Local embodiment node available (browser + local accounts)",
    ],
    OnboardingTier.TIER_4_COMPUTER_USE: [
        "Tier 2 workspace connected",
        "Local agent installed and running",
        "Explicit user opt-in for observation",
    ],
    OnboardingTier.TIER_5_CONTINUOUS: [
        "Tier 2 workspace connected",
        "VPS always-on services running",
        "Governance layer active",
        "Review pipeline operational",
    ],
}

_TIER_USER_ACTIONS: dict[OnboardingTier, list[str]] = {
    OnboardingTier.TIER_0_MANUAL_CORE: [
        "Declare identity, goals, and company structure",
        "Confirm strategic context and current focus",
        "Set initial preferences and constraints",
    ],
    OnboardingTier.TIER_1_LOCAL_ARCHIVES: [
        "Export AI chat archives (ChatGPT, Claude) as files",
        "Point EOS to local notes directory",
        "Transfer voice memos to accessible location",
    ],
    OnboardingTier.TIER_2_WORKSPACE: [
        "Authorize OAuth for each workspace tool",
        "Provide API keys where OAuth unavailable",
        "Review and approve permission scopes per source",
    ],
    OnboardingTier.TIER_3_SOCIAL_ALGORITHM: [
        "Log into social accounts on local browser",
        "Approve browser-session access for each platform",
        "Set content export preferences",
    ],
    OnboardingTier.TIER_4_COMPUTER_USE: [
        "Install local observation agent",
        "Opt in to specific observation modes",
        "Set exclusion zones (apps, URLs, time windows)",
    ],
    OnboardingTier.TIER_5_CONTINUOUS: [
        "Configure webhook endpoints",
        "Set monitoring schedules",
        "Review governance rules for continuous ingestion",
    ],
}

_TIER_SUCCESS_CRITERIA: dict[OnboardingTier, list[str]] = {
    OnboardingTier.TIER_0_MANUAL_CORE: [
        "Identity profile created in EOS",
        "At least one company/venture defined",
        "Current north star documented",
    ],
    OnboardingTier.TIER_1_LOCAL_ARCHIVES: [
        "At least one archive parsed into candidates",
        "Candidate review pipeline populated",
        "No raw artifacts lost or corrupted",
    ],
    OnboardingTier.TIER_2_WORKSPACE: [
        "Email and calendar connected",
        "At least one note/doc source connected",
        "Source status shows CONNECTED for approved sources",
    ],
    OnboardingTier.TIER_3_SOCIAL_ALGORITHM: [
        "At least one social feed ingesting",
        "Saved/liked content accessible",
        "Algorithmic profile sketch generated",
    ],
    OnboardingTier.TIER_4_COMPUTER_USE: [
        "Browser history accessible read-only",
        "Screen capture pipeline working",
        "Exclusion zones respected",
    ],
    OnboardingTier.TIER_5_CONTINUOUS: [
        "At least one real-time webhook active",
        "Governance checks passing for continuous sources",
        "Review queue not backing up",
    ],
}


def build_onboarding_plan_for_tier(tier: OnboardingTier) -> OnboardingIngestionPlan:
    source_classes = get_source_classes_for_tier(tier)

    return OnboardingIngestionPlan(
        plan_id=_ingest_id("plan"),
        tier=tier,
        name=f"Onboarding {tier.value}",
        description=_TIER_DESCRIPTIONS.get(tier, ""),
        sources=[sc.value for sc in source_classes],
        prerequisites=_TIER_PREREQUISITES.get(tier, []),
        estimated_effort=_estimate_effort(tier),
        user_actions_required=_TIER_USER_ACTIONS.get(tier, []),
        automated_steps=_get_automated_steps(tier),
        success_criteria=_TIER_SUCCESS_CRITERIA.get(tier, []),
        warnings=_get_tier_warnings(tier),
    )


def build_full_onboarding_sequence() -> list[OnboardingIngestionPlan]:
    tiers = [
        OnboardingTier.TIER_0_MANUAL_CORE,
        OnboardingTier.TIER_1_LOCAL_ARCHIVES,
        OnboardingTier.TIER_2_WORKSPACE,
        OnboardingTier.TIER_3_SOCIAL_ALGORITHM,
        OnboardingTier.TIER_4_COMPUTER_USE,
        OnboardingTier.TIER_5_CONTINUOUS,
    ]
    return [build_onboarding_plan_for_tier(t) for t in tiers]


def get_source_classes_for_tier(tier: OnboardingTier) -> list[SourceClass]:
    result: list[SourceClass] = []
    for sc in list_source_classes():
        if get_default_tier(sc) == tier:
            result.append(sc)
    return result


def get_next_tier(current: OnboardingTier) -> OnboardingTier | None:
    order = [
        OnboardingTier.TIER_0_MANUAL_CORE,
        OnboardingTier.TIER_1_LOCAL_ARCHIVES,
        OnboardingTier.TIER_2_WORKSPACE,
        OnboardingTier.TIER_3_SOCIAL_ALGORITHM,
        OnboardingTier.TIER_4_COMPUTER_USE,
        OnboardingTier.TIER_5_CONTINUOUS,
    ]
    try:
        idx = order.index(current)
        if idx + 1 < len(order):
            return order[idx + 1]
    except ValueError:
        pass
    return None


def _estimate_effort(tier: OnboardingTier) -> str:
    estimates = {
        OnboardingTier.TIER_0_MANUAL_CORE: "15-30 minutes",
        OnboardingTier.TIER_1_LOCAL_ARCHIVES: "30-60 minutes (depends on archive size)",
        OnboardingTier.TIER_2_WORKSPACE: "1-2 hours (OAuth flows + approval)",
        OnboardingTier.TIER_3_SOCIAL_ALGORITHM: "1-3 hours (browser sessions + review)",
        OnboardingTier.TIER_4_COMPUTER_USE: "30-60 minutes (agent install + config)",
        OnboardingTier.TIER_5_CONTINUOUS: "2-4 hours (webhook config + governance)",
    }
    return estimates.get(tier, "unknown")


def _get_automated_steps(tier: OnboardingTier) -> list[str]:
    steps: dict[OnboardingTier, list[str]] = {
        OnboardingTier.TIER_0_MANUAL_CORE: [
            "Parse declared identity into structured profile",
            "Create initial memory candidates from declarations",
        ],
        OnboardingTier.TIER_1_LOCAL_ARCHIVES: [
            "Scan export files for known formats",
            "Parse and extract structured candidates",
            "Run supersession check against existing memory",
            "Queue for review",
        ],
        OnboardingTier.TIER_2_WORKSPACE: [
            "Validate OAuth tokens",
            "Initial sync of recent items (configurable window)",
            "Parse into structured candidates",
            "Run conflict/supersession checks",
            "Queue for review",
        ],
        OnboardingTier.TIER_3_SOCIAL_ALGORITHM: [
            "Navigate to feed/saved content via browser session",
            "Extract visible content within approved scope",
            "Parse into structured candidates",
            "Build algorithmic profile sketch",
            "Queue for review",
        ],
        OnboardingTier.TIER_4_COMPUTER_USE: [
            "Capture approved observation data",
            "Parse into structured candidates",
            "Apply exclusion filters",
            "Queue for review",
        ],
        OnboardingTier.TIER_5_CONTINUOUS: [
            "Process incoming events from webhooks/feeds",
            "Run governance checks per event",
            "Parse and candidate per event type",
            "Auto-promote or queue based on confidence",
        ],
    }
    return steps.get(tier, [])


def _get_tier_warnings(tier: OnboardingTier) -> list[str]:
    warnings: dict[OnboardingTier, list[str]] = {
        OnboardingTier.TIER_0_MANUAL_CORE: [],
        OnboardingTier.TIER_1_LOCAL_ARCHIVES: [
            "Large archives may take significant processing time",
        ],
        OnboardingTier.TIER_2_WORKSPACE: [
            "OAuth tokens expire — renewal flow must be in place",
            "Some APIs have rate limits that affect initial sync speed",
        ],
        OnboardingTier.TIER_3_SOCIAL_ALGORITHM: [
            "Browser sessions require local PC with logged-in accounts",
            "Social platform ToS may restrict automated access",
            "Session cookies expire — re-authentication may be needed",
        ],
        OnboardingTier.TIER_4_COMPUTER_USE: [
            "Observation requires explicit user consent",
            "Screen capture may include sensitive content",
            "Local agent must respect exclusion zones",
        ],
        OnboardingTier.TIER_5_CONTINUOUS: [
            "Continuous ingestion generates high review volume",
            "Governance must be active before enabling",
            "Resource consumption scales with source count",
        ],
    }
    return warnings.get(tier, [])
