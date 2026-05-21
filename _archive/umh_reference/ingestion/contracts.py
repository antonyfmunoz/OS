"""Phase 87B onboarding context ingestion contracts — typed enums and dataclasses.

Source-class abstractions, tool-stack discovery, onboarding tiers,
permission/sensitivity/review policy, memory candidate policy.

All enums have UNKNOWN fallback. All normalizers degrade gracefully.
All dataclasses support to_dict()/from_dict() round-trips.

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any


def _ingest_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _normalize(enum_cls: type[Enum], value: str | Enum) -> Enum:
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        upper = value.upper().replace(" ", "_").replace("-", "_")
        for member in enum_cls:
            if member.value == value or member.name == upper:
                return member
    return enum_cls.UNKNOWN  # type: ignore[attr-defined]


# ─── Enums (12) ──────────────────────────────────────────────────────


@unique
class SourceClass(str, Enum):
    EMAIL = "email"
    CALENDAR = "calendar"
    TASK_MANAGEMENT = "task_management"
    NOTE_TAKING = "note_taking"
    DOCUMENT_EDITING = "document_editing"
    SPREADSHEET = "spreadsheet"
    CLOUD_STORAGE = "cloud_storage"
    CODE_REPOSITORY = "code_repository"
    CI_CD = "ci_cd"
    CONTAINER_RUNTIME = "container_runtime"
    SOCIAL_MEDIA = "social_media"
    MESSAGING = "messaging"
    VIDEO_PLATFORM = "video_platform"
    AUDIO_PLATFORM = "audio_platform"
    CRM = "crm"
    PAYMENT_PROCESSING = "payment_processing"
    ACCOUNTING = "accounting"
    ANALYTICS = "analytics"
    ADVERTISING = "advertising"
    AI_ASSISTANT = "ai_assistant"
    BROWSER_HISTORY = "browser_history"
    VOICE_MEMO = "voice_memo"
    CAMERA_CAPTURE = "camera_capture"
    SCREEN_CAPTURE = "screen_capture"
    EBOOK_READER = "ebook_reader"
    PODCAST_PLAYER = "podcast_player"
    DESIGN_TOOL = "design_tool"
    THREE_D_MODELING = "3d_modeling"
    UNKNOWN = "unknown"


@unique
class PlatformType(str, Enum):
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    APPLE_MAIL = "apple_mail"
    PROTONMAIL = "protonmail"
    GOOGLE_CALENDAR = "google_calendar"
    APPLE_CALENDAR = "apple_calendar"
    OUTLOOK_CALENDAR = "outlook_calendar"
    TODOIST = "todoist"
    ASANA = "asana"
    LINEAR = "linear"
    JIRA = "jira"
    NOTION = "notion"
    OBSIDIAN = "obsidian"
    APPLE_NOTES = "apple_notes"
    ROAM = "roam"
    GOOGLE_DOCS = "google_docs"
    MICROSOFT_WORD = "microsoft_word"
    GOOGLE_SHEETS = "google_sheets"
    EXCEL = "excel"
    GOOGLE_DRIVE = "google_drive"
    DROPBOX = "dropbox"
    ICLOUD = "icloud"
    ONEDRIVE = "onedrive"
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    GITHUB_ACTIONS = "github_actions"
    DOCKER = "docker"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    IMESSAGE = "imessage"
    STRIPE = "stripe"
    PAYPAL = "paypal"
    SQUARE = "square"
    QUICKBOOKS = "quickbooks"
    GOOGLE_ANALYTICS = "google_analytics"
    CALENDLY = "calendly"
    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    UNKNOWN = "unknown"


@unique
class SourceModality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    STRUCTURED_DATA = "structured_data"
    CODE = "code"
    PDF = "pdf"
    RICH_TEXT = "rich_text"
    CONVERSATION = "conversation"
    FEED = "feed"
    TRANSACTION = "transaction"
    UNKNOWN = "unknown"


@unique
class AccessMethod(str, Enum):
    OFFICIAL_API = "official_api"
    OAUTH = "oauth"
    API_KEY = "api_key"
    EXPORT_FILE = "export_file"
    BROWSER_EXTENSION = "browser_extension"
    BROWSER_SESSION = "browser_session"
    LOCAL_FILESYSTEM = "local_filesystem"
    SCREEN_CAPTURE = "screen_capture"
    MANUAL_ENTRY = "manual_entry"
    WEBHOOK = "webhook"
    RSS = "rss"
    UNKNOWN = "unknown"


@unique
class PermissionScope(str, Enum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    READ_METADATA = "read_metadata"
    READ_CONTENT = "read_content"
    READ_ANALYTICS = "read_analytics"
    READ_CONTACTS = "read_contacts"
    READ_TRANSACTIONS = "read_transactions"
    EXPORT_ONLY = "export_only"
    SEARCH_ONLY = "search_only"
    NONE = "none"
    UNKNOWN = "unknown"


@unique
class OnboardingTier(str, Enum):
    TIER_0_MANUAL_CORE = "tier_0_manual_core"
    TIER_1_LOCAL_ARCHIVES = "tier_1_local_archives"
    TIER_2_WORKSPACE = "tier_2_workspace"
    TIER_3_SOCIAL_ALGORITHM = "tier_3_social_algorithm"
    TIER_4_COMPUTER_USE = "tier_4_computer_use"
    TIER_5_CONTINUOUS = "tier_5_continuous"
    DEFERRED = "deferred"
    UNKNOWN = "unknown"


@unique
class IngestionPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BACKGROUND = "background"
    DEFERRED = "deferred"
    UNKNOWN = "unknown"


@unique
class SourceSensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    FINANCIAL = "financial"
    CREDENTIAL = "credential"
    UNKNOWN = "unknown"


@unique
class ReviewRequirement(str, Enum):
    NONE = "none"
    SPOT_CHECK = "spot_check"
    SAMPLE_REVIEW = "sample_review"
    FULL_REVIEW = "full_review"
    APPROVAL_REQUIRED = "approval_required"
    LEGAL_REVIEW = "legal_review"
    UNKNOWN = "unknown"


@unique
class MemoryPromotionPolicy(str, Enum):
    AUTO_PROMOTE = "auto_promote"
    CONFIDENCE_THRESHOLD = "confidence_threshold"
    HUMAN_REVIEW = "human_review"
    BATCH_REVIEW = "batch_review"
    NEVER_PROMOTE = "never_promote"
    SUPERSESSION_CHECK = "supersession_check"
    CONFLICT_RESOLUTION = "conflict_resolution"
    UNKNOWN = "unknown"


@unique
class SourceStatus(str, Enum):
    DISCOVERED = "discovered"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    CONNECTED = "connected"
    INGESTING = "ingesting"
    PAUSED = "paused"
    FAILED = "failed"
    DISCONNECTED = "disconnected"
    DEPRECATED = "deprecated"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@unique
class RefreshCadence(str, Enum):
    REAL_TIME = "real_time"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    ON_DEMAND = "on_demand"
    ONE_TIME = "one_time"
    CONTINUOUS = "continuous"
    UNKNOWN = "unknown"


# ─── Normalizers (12) ────────────────────────────────────────────────


def normalize_source_class(v: str | SourceClass) -> SourceClass:
    return _normalize(SourceClass, v)  # type: ignore[return-value]


def normalize_platform_type(v: str | PlatformType) -> PlatformType:
    return _normalize(PlatformType, v)  # type: ignore[return-value]


def normalize_source_modality(v: str | SourceModality) -> SourceModality:
    return _normalize(SourceModality, v)  # type: ignore[return-value]


def normalize_access_method(v: str | AccessMethod) -> AccessMethod:
    return _normalize(AccessMethod, v)  # type: ignore[return-value]


def normalize_permission_scope(v: str | PermissionScope) -> PermissionScope:
    return _normalize(PermissionScope, v)  # type: ignore[return-value]


def normalize_onboarding_tier(v: str | OnboardingTier) -> OnboardingTier:
    return _normalize(OnboardingTier, v)  # type: ignore[return-value]


def normalize_ingestion_priority(v: str | IngestionPriority) -> IngestionPriority:
    return _normalize(IngestionPriority, v)  # type: ignore[return-value]


def normalize_source_sensitivity(v: str | SourceSensitivity) -> SourceSensitivity:
    return _normalize(SourceSensitivity, v)  # type: ignore[return-value]


def normalize_review_requirement(v: str | ReviewRequirement) -> ReviewRequirement:
    return _normalize(ReviewRequirement, v)  # type: ignore[return-value]


def normalize_memory_promotion_policy(v: str | MemoryPromotionPolicy) -> MemoryPromotionPolicy:
    return _normalize(MemoryPromotionPolicy, v)  # type: ignore[return-value]


def normalize_source_status(v: str | SourceStatus) -> SourceStatus:
    return _normalize(SourceStatus, v)  # type: ignore[return-value]


def normalize_refresh_cadence(v: str | RefreshCadence) -> RefreshCadence:
    return _normalize(RefreshCadence, v)  # type: ignore[return-value]


# ─── Dataclasses (5) ─────────────────────────────────────────────────


@dataclass
class IngestionSource:
    source_id: str
    source_class: SourceClass = SourceClass.UNKNOWN
    platform: PlatformType = PlatformType.UNKNOWN
    name: str = ""
    description: str = ""
    modalities: list[SourceModality] = field(default_factory=list)
    access_methods: list[AccessMethod] = field(default_factory=list)
    permission_scopes: list[PermissionScope] = field(default_factory=list)
    onboarding_tier: OnboardingTier = OnboardingTier.UNKNOWN
    priority: IngestionPriority = IngestionPriority.MEDIUM
    sensitivity: SourceSensitivity = SourceSensitivity.INTERNAL
    review_requirement: ReviewRequirement = ReviewRequirement.SAMPLE_REVIEW
    promotion_policy: MemoryPromotionPolicy = MemoryPromotionPolicy.HUMAN_REVIEW
    status: SourceStatus = SourceStatus.DISCOVERED
    refresh_cadence: RefreshCadence = RefreshCadence.ON_DEMAND
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_class": self.source_class.value,
            "platform": self.platform.value,
            "name": self.name,
            "description": self.description,
            "modalities": [m.value for m in self.modalities],
            "access_methods": [a.value for a in self.access_methods],
            "permission_scopes": [p.value for p in self.permission_scopes],
            "onboarding_tier": self.onboarding_tier.value,
            "priority": self.priority.value,
            "sensitivity": self.sensitivity.value,
            "review_requirement": self.review_requirement.value,
            "promotion_policy": self.promotion_policy.value,
            "status": self.status.value,
            "refresh_cadence": self.refresh_cadence.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IngestionSource:
        return cls(
            source_id=d["source_id"],
            source_class=normalize_source_class(d.get("source_class", "unknown")),
            platform=normalize_platform_type(d.get("platform", "unknown")),
            name=d.get("name", ""),
            description=d.get("description", ""),
            modalities=[normalize_source_modality(m) for m in d.get("modalities", [])],
            access_methods=[normalize_access_method(a) for a in d.get("access_methods", [])],
            permission_scopes=[
                normalize_permission_scope(p) for p in d.get("permission_scopes", [])
            ],
            onboarding_tier=normalize_onboarding_tier(d.get("onboarding_tier", "unknown")),
            priority=normalize_ingestion_priority(d.get("priority", "medium")),
            sensitivity=normalize_source_sensitivity(d.get("sensitivity", "internal")),
            review_requirement=normalize_review_requirement(
                d.get("review_requirement", "sample_review")
            ),
            promotion_policy=normalize_memory_promotion_policy(
                d.get("promotion_policy", "human_review")
            ),
            status=normalize_source_status(d.get("status", "discovered")),
            refresh_cadence=normalize_refresh_cadence(d.get("refresh_cadence", "on_demand")),
            metadata=d.get("metadata", {}),
        )


@dataclass
class ToolStackProfile:
    profile_id: str
    user_label: str = ""
    discovered_platforms: list[PlatformType] = field(default_factory=list)
    confirmed_platforms: list[PlatformType] = field(default_factory=list)
    rejected_platforms: list[PlatformType] = field(default_factory=list)
    source_class_coverage: dict[str, list[str]] = field(default_factory=dict)
    gaps: list[str] = field(default_factory=list)
    notes: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "user_label": self.user_label,
            "discovered_platforms": [p.value for p in self.discovered_platforms],
            "confirmed_platforms": [p.value for p in self.confirmed_platforms],
            "rejected_platforms": [p.value for p in self.rejected_platforms],
            "source_class_coverage": self.source_class_coverage,
            "gaps": self.gaps,
            "notes": self.notes,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ToolStackProfile:
        return cls(
            profile_id=d["profile_id"],
            user_label=d.get("user_label", ""),
            discovered_platforms=[
                normalize_platform_type(p) for p in d.get("discovered_platforms", [])
            ],
            confirmed_platforms=[
                normalize_platform_type(p) for p in d.get("confirmed_platforms", [])
            ],
            rejected_platforms=[
                normalize_platform_type(p) for p in d.get("rejected_platforms", [])
            ],
            source_class_coverage=d.get("source_class_coverage", {}),
            gaps=d.get("gaps", []),
            notes=d.get("notes", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass
class OnboardingIngestionPlan:
    plan_id: str
    tier: OnboardingTier = OnboardingTier.UNKNOWN
    name: str = ""
    description: str = ""
    sources: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    estimated_effort: str = ""
    user_actions_required: list[str] = field(default_factory=list)
    automated_steps: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "tier": self.tier.value,
            "name": self.name,
            "description": self.description,
            "sources": self.sources,
            "prerequisites": self.prerequisites,
            "estimated_effort": self.estimated_effort,
            "user_actions_required": self.user_actions_required,
            "automated_steps": self.automated_steps,
            "success_criteria": self.success_criteria,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OnboardingIngestionPlan:
        return cls(
            plan_id=d["plan_id"],
            tier=normalize_onboarding_tier(d.get("tier", "unknown")),
            name=d.get("name", ""),
            description=d.get("description", ""),
            sources=d.get("sources", []),
            prerequisites=d.get("prerequisites", []),
            estimated_effort=d.get("estimated_effort", ""),
            user_actions_required=d.get("user_actions_required", []),
            automated_steps=d.get("automated_steps", []),
            success_criteria=d.get("success_criteria", []),
            warnings=d.get("warnings", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class SourceIngestionRoute:
    route_id: str
    source_id: str = ""
    source_class: SourceClass = SourceClass.UNKNOWN
    platform: PlatformType = PlatformType.UNKNOWN
    recommended_node_type: str = ""
    source_affinity: str = ""
    required_capabilities: list[str] = field(default_factory=list)
    access_method: AccessMethod = AccessMethod.UNKNOWN
    permission_scope: PermissionScope = PermissionScope.UNKNOWN
    sensitivity: SourceSensitivity = SourceSensitivity.INTERNAL
    review_requirement: ReviewRequirement = ReviewRequirement.SAMPLE_REVIEW
    reason: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "source_id": self.source_id,
            "source_class": self.source_class.value,
            "platform": self.platform.value,
            "recommended_node_type": self.recommended_node_type,
            "source_affinity": self.source_affinity,
            "required_capabilities": self.required_capabilities,
            "access_method": self.access_method.value,
            "permission_scope": self.permission_scope.value,
            "sensitivity": self.sensitivity.value,
            "review_requirement": self.review_requirement.value,
            "reason": self.reason,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceIngestionRoute:
        return cls(
            route_id=d["route_id"],
            source_id=d.get("source_id", ""),
            source_class=normalize_source_class(d.get("source_class", "unknown")),
            platform=normalize_platform_type(d.get("platform", "unknown")),
            recommended_node_type=d.get("recommended_node_type", ""),
            source_affinity=d.get("source_affinity", ""),
            required_capabilities=d.get("required_capabilities", []),
            access_method=normalize_access_method(d.get("access_method", "unknown")),
            permission_scope=normalize_permission_scope(d.get("permission_scope", "unknown")),
            sensitivity=normalize_source_sensitivity(d.get("sensitivity", "internal")),
            review_requirement=normalize_review_requirement(
                d.get("review_requirement", "sample_review")
            ),
            reason=d.get("reason", ""),
            warnings=d.get("warnings", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class IngestionReviewPolicy:
    policy_id: str
    name: str = ""
    source_class: SourceClass = SourceClass.UNKNOWN
    sensitivity: SourceSensitivity = SourceSensitivity.INTERNAL
    review_requirement: ReviewRequirement = ReviewRequirement.SAMPLE_REVIEW
    promotion_policy: MemoryPromotionPolicy = MemoryPromotionPolicy.HUMAN_REVIEW
    confidence_threshold: float = 0.8
    requires_supersession_check: bool = True
    requires_conflict_check: bool = True
    max_auto_promote_per_batch: int = 0
    human_reviewers: list[str] = field(default_factory=list)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "source_class": self.source_class.value,
            "sensitivity": self.sensitivity.value,
            "review_requirement": self.review_requirement.value,
            "promotion_policy": self.promotion_policy.value,
            "confidence_threshold": round(self.confidence_threshold, 4),
            "requires_supersession_check": self.requires_supersession_check,
            "requires_conflict_check": self.requires_conflict_check,
            "max_auto_promote_per_batch": self.max_auto_promote_per_batch,
            "human_reviewers": self.human_reviewers,
            "description": self.description,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> IngestionReviewPolicy:
        return cls(
            policy_id=d["policy_id"],
            name=d.get("name", ""),
            source_class=normalize_source_class(d.get("source_class", "unknown")),
            sensitivity=normalize_source_sensitivity(d.get("sensitivity", "internal")),
            review_requirement=normalize_review_requirement(
                d.get("review_requirement", "sample_review")
            ),
            promotion_policy=normalize_memory_promotion_policy(
                d.get("promotion_policy", "human_review")
            ),
            confidence_threshold=d.get("confidence_threshold", 0.8),
            requires_supersession_check=d.get("requires_supersession_check", True),
            requires_conflict_check=d.get("requires_conflict_check", True),
            max_auto_promote_per_batch=d.get("max_auto_promote_per_batch", 0),
            human_reviewers=d.get("human_reviewers", []),
            description=d.get("description", ""),
            metadata=d.get("metadata", {}),
        )
