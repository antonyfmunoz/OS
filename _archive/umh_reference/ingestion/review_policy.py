"""Phase 87B review policy — memory candidate review and promotion policies.

Defines default review policies per source class and sensitivity level.
Raw artifacts → parsed candidates → review → confidence/conflict/supersession
checks → promotion. No raw-to-memory shortcut.

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution.
"""

from __future__ import annotations

from umh.ingestion.contracts import (
    IngestionReviewPolicy,
    IngestionSource,
    MemoryPromotionPolicy,
    ReviewRequirement,
    SourceClass,
    SourceSensitivity,
    _ingest_id,
)


def build_default_review_policies() -> list[IngestionReviewPolicy]:
    return [
        IngestionReviewPolicy(
            policy_id=_ingest_id("rpol"),
            name="Public Content",
            source_class=SourceClass.SOCIAL_MEDIA,
            sensitivity=SourceSensitivity.PUBLIC,
            review_requirement=ReviewRequirement.SAMPLE_REVIEW,
            promotion_policy=MemoryPromotionPolicy.BATCH_REVIEW,
            confidence_threshold=0.7,
            requires_supersession_check=True,
            requires_conflict_check=True,
            max_auto_promote_per_batch=0,
            description="Public social content — batch review, no auto-promote",
        ),
        IngestionReviewPolicy(
            policy_id=_ingest_id("rpol"),
            name="Workspace Documents",
            source_class=SourceClass.DOCUMENT_EDITING,
            sensitivity=SourceSensitivity.INTERNAL,
            review_requirement=ReviewRequirement.SAMPLE_REVIEW,
            promotion_policy=MemoryPromotionPolicy.CONFIDENCE_THRESHOLD,
            confidence_threshold=0.8,
            requires_supersession_check=True,
            requires_conflict_check=True,
            max_auto_promote_per_batch=10,
            description="Workspace docs — promote above confidence threshold with checks",
        ),
        IngestionReviewPolicy(
            policy_id=_ingest_id("rpol"),
            name="Messaging / Conversations",
            source_class=SourceClass.MESSAGING,
            sensitivity=SourceSensitivity.CONFIDENTIAL,
            review_requirement=ReviewRequirement.SAMPLE_REVIEW,
            promotion_policy=MemoryPromotionPolicy.HUMAN_REVIEW,
            confidence_threshold=0.85,
            requires_supersession_check=True,
            requires_conflict_check=True,
            max_auto_promote_per_batch=0,
            description="Confidential conversations — human review required",
        ),
        IngestionReviewPolicy(
            policy_id=_ingest_id("rpol"),
            name="Financial Data",
            source_class=SourceClass.PAYMENT_PROCESSING,
            sensitivity=SourceSensitivity.FINANCIAL,
            review_requirement=ReviewRequirement.FULL_REVIEW,
            promotion_policy=MemoryPromotionPolicy.HUMAN_REVIEW,
            confidence_threshold=0.95,
            requires_supersession_check=True,
            requires_conflict_check=True,
            max_auto_promote_per_batch=0,
            description="Financial data — full human review, never auto-promote",
        ),
        IngestionReviewPolicy(
            policy_id=_ingest_id("rpol"),
            name="AI Chat Archives",
            source_class=SourceClass.AI_ASSISTANT,
            sensitivity=SourceSensitivity.CONFIDENTIAL,
            review_requirement=ReviewRequirement.SAMPLE_REVIEW,
            promotion_policy=MemoryPromotionPolicy.SUPERSESSION_CHECK,
            confidence_threshold=0.8,
            requires_supersession_check=True,
            requires_conflict_check=True,
            max_auto_promote_per_batch=5,
            description="AI chat exports — supersession check mandatory, newer corrections win",
        ),
        IngestionReviewPolicy(
            policy_id=_ingest_id("rpol"),
            name="Calendar / Scheduling",
            source_class=SourceClass.CALENDAR,
            sensitivity=SourceSensitivity.INTERNAL,
            review_requirement=ReviewRequirement.SPOT_CHECK,
            promotion_policy=MemoryPromotionPolicy.AUTO_PROMOTE,
            confidence_threshold=0.6,
            requires_supersession_check=False,
            requires_conflict_check=False,
            max_auto_promote_per_batch=50,
            description="Calendar events — structured data, low risk, auto-promote",
        ),
        IngestionReviewPolicy(
            policy_id=_ingest_id("rpol"),
            name="Code Repositories",
            source_class=SourceClass.CODE_REPOSITORY,
            sensitivity=SourceSensitivity.INTERNAL,
            review_requirement=ReviewRequirement.SPOT_CHECK,
            promotion_policy=MemoryPromotionPolicy.AUTO_PROMOTE,
            confidence_threshold=0.7,
            requires_supersession_check=False,
            requires_conflict_check=False,
            max_auto_promote_per_batch=20,
            description="Code repos — structured, version-controlled, auto-promote metadata",
        ),
        IngestionReviewPolicy(
            policy_id=_ingest_id("rpol"),
            name="Email",
            source_class=SourceClass.EMAIL,
            sensitivity=SourceSensitivity.CONFIDENTIAL,
            review_requirement=ReviewRequirement.SAMPLE_REVIEW,
            promotion_policy=MemoryPromotionPolicy.CONFIDENCE_THRESHOLD,
            confidence_threshold=0.8,
            requires_supersession_check=True,
            requires_conflict_check=True,
            max_auto_promote_per_batch=5,
            description="Email — confidential, promote above threshold with conflict check",
        ),
    ]


def get_review_policy_for_source(
    source: IngestionSource,
    policies: list[IngestionReviewPolicy] | None = None,
) -> IngestionReviewPolicy | None:
    if policies is None:
        policies = build_default_review_policies()

    for p in policies:
        if p.source_class == source.source_class and p.sensitivity == source.sensitivity:
            return p
    for p in policies:
        if p.source_class == source.source_class:
            return p
    return None


def should_auto_promote(
    policy: IngestionReviewPolicy,
    confidence: float,
    batch_promoted_count: int,
) -> bool:
    if policy.promotion_policy == MemoryPromotionPolicy.NEVER_PROMOTE:
        return False
    if policy.promotion_policy == MemoryPromotionPolicy.HUMAN_REVIEW:
        return False
    if policy.promotion_policy == MemoryPromotionPolicy.AUTO_PROMOTE:
        if (
            policy.max_auto_promote_per_batch > 0
            and batch_promoted_count >= policy.max_auto_promote_per_batch
        ):
            return False
        return confidence >= policy.confidence_threshold
    if policy.promotion_policy == MemoryPromotionPolicy.CONFIDENCE_THRESHOLD:
        if (
            policy.max_auto_promote_per_batch > 0
            and batch_promoted_count >= policy.max_auto_promote_per_batch
        ):
            return False
        return confidence >= policy.confidence_threshold
    return False


def requires_human_review(policy: IngestionReviewPolicy) -> bool:
    return policy.promotion_policy in (
        MemoryPromotionPolicy.HUMAN_REVIEW,
        MemoryPromotionPolicy.BATCH_REVIEW,
    )


def requires_supersession_check(policy: IngestionReviewPolicy) -> bool:
    return (
        policy.requires_supersession_check
        or policy.promotion_policy == MemoryPromotionPolicy.SUPERSESSION_CHECK
    )


def classify_review_urgency(
    source: IngestionSource,
    policy: IngestionReviewPolicy | None = None,
) -> str:
    if policy is None:
        policy = get_review_policy_for_source(source)
    if policy is None:
        return "medium"

    if policy.review_requirement == ReviewRequirement.APPROVAL_REQUIRED:
        return "critical"
    if policy.review_requirement == ReviewRequirement.LEGAL_REVIEW:
        return "critical"
    if policy.review_requirement == ReviewRequirement.FULL_REVIEW:
        return "high"
    if source.sensitivity == SourceSensitivity.FINANCIAL:
        return "high"
    if policy.review_requirement == ReviewRequirement.SAMPLE_REVIEW:
        return "medium"
    if policy.review_requirement in (ReviewRequirement.SPOT_CHECK, ReviewRequirement.NONE):
        return "low"
    return "medium"
