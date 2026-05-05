"""Phase 87B source class taxonomy — maps source classes to platforms and modalities.

Apps are not the primitive. Source classes are.
Gmail, Outlook, Apple Mail are all implementations of "email."

Advisory/planning only. No scraping. No API calls. No account connections.
No file reading. No memory promotion. No execution.
"""

from __future__ import annotations

from umh.ingestion.contracts import (
    AccessMethod,
    IngestionPriority,
    OnboardingTier,
    PlatformType,
    PermissionScope,
    RefreshCadence,
    SourceClass,
    SourceModality,
    SourceSensitivity,
)


_SOURCE_CLASS_PLATFORMS: dict[SourceClass, list[PlatformType]] = {
    SourceClass.EMAIL: [
        PlatformType.GMAIL,
        PlatformType.OUTLOOK,
        PlatformType.APPLE_MAIL,
        PlatformType.PROTONMAIL,
    ],
    SourceClass.CALENDAR: [
        PlatformType.GOOGLE_CALENDAR,
        PlatformType.APPLE_CALENDAR,
        PlatformType.OUTLOOK_CALENDAR,
    ],
    SourceClass.TASK_MANAGEMENT: [
        PlatformType.TODOIST,
        PlatformType.ASANA,
        PlatformType.LINEAR,
        PlatformType.JIRA,
        PlatformType.NOTION,
    ],
    SourceClass.NOTE_TAKING: [
        PlatformType.NOTION,
        PlatformType.OBSIDIAN,
        PlatformType.APPLE_NOTES,
        PlatformType.ROAM,
    ],
    SourceClass.DOCUMENT_EDITING: [
        PlatformType.GOOGLE_DOCS,
        PlatformType.MICROSOFT_WORD,
        PlatformType.NOTION,
    ],
    SourceClass.SPREADSHEET: [
        PlatformType.GOOGLE_SHEETS,
        PlatformType.EXCEL,
    ],
    SourceClass.CLOUD_STORAGE: [
        PlatformType.GOOGLE_DRIVE,
        PlatformType.DROPBOX,
        PlatformType.ICLOUD,
        PlatformType.ONEDRIVE,
    ],
    SourceClass.CODE_REPOSITORY: [
        PlatformType.GITHUB,
        PlatformType.GITLAB,
        PlatformType.BITBUCKET,
    ],
    SourceClass.CI_CD: [
        PlatformType.GITHUB_ACTIONS,
    ],
    SourceClass.CONTAINER_RUNTIME: [
        PlatformType.DOCKER,
    ],
    SourceClass.SOCIAL_MEDIA: [
        PlatformType.INSTAGRAM,
        PlatformType.TIKTOK,
        PlatformType.TWITTER,
        PlatformType.LINKEDIN,
        PlatformType.YOUTUBE,
    ],
    SourceClass.MESSAGING: [
        PlatformType.DISCORD,
        PlatformType.TELEGRAM,
        PlatformType.SLACK,
        PlatformType.WHATSAPP,
        PlatformType.IMESSAGE,
    ],
    SourceClass.VIDEO_PLATFORM: [
        PlatformType.YOUTUBE,
    ],
    SourceClass.AUDIO_PLATFORM: [],
    SourceClass.CRM: [
        PlatformType.NOTION,
    ],
    SourceClass.PAYMENT_PROCESSING: [
        PlatformType.STRIPE,
        PlatformType.PAYPAL,
        PlatformType.SQUARE,
    ],
    SourceClass.ACCOUNTING: [
        PlatformType.QUICKBOOKS,
    ],
    SourceClass.ANALYTICS: [
        PlatformType.GOOGLE_ANALYTICS,
    ],
    SourceClass.ADVERTISING: [],
    SourceClass.AI_ASSISTANT: [
        PlatformType.CHATGPT,
        PlatformType.CLAUDE,
    ],
    SourceClass.BROWSER_HISTORY: [],
    SourceClass.VOICE_MEMO: [],
    SourceClass.CAMERA_CAPTURE: [],
    SourceClass.SCREEN_CAPTURE: [],
    SourceClass.EBOOK_READER: [],
    SourceClass.PODCAST_PLAYER: [],
    SourceClass.DESIGN_TOOL: [],
    SourceClass.THREE_D_MODELING: [],
}

_SOURCE_CLASS_MODALITIES: dict[SourceClass, list[SourceModality]] = {
    SourceClass.EMAIL: [SourceModality.TEXT, SourceModality.RICH_TEXT],
    SourceClass.CALENDAR: [SourceModality.STRUCTURED_DATA],
    SourceClass.TASK_MANAGEMENT: [SourceModality.STRUCTURED_DATA, SourceModality.TEXT],
    SourceClass.NOTE_TAKING: [SourceModality.TEXT, SourceModality.RICH_TEXT, SourceModality.IMAGE],
    SourceClass.DOCUMENT_EDITING: [SourceModality.RICH_TEXT, SourceModality.TEXT],
    SourceClass.SPREADSHEET: [SourceModality.STRUCTURED_DATA],
    SourceClass.CLOUD_STORAGE: [SourceModality.TEXT, SourceModality.IMAGE, SourceModality.PDF],
    SourceClass.CODE_REPOSITORY: [SourceModality.CODE, SourceModality.TEXT],
    SourceClass.CI_CD: [SourceModality.STRUCTURED_DATA, SourceModality.TEXT],
    SourceClass.CONTAINER_RUNTIME: [SourceModality.TEXT, SourceModality.STRUCTURED_DATA],
    SourceClass.SOCIAL_MEDIA: [
        SourceModality.TEXT,
        SourceModality.IMAGE,
        SourceModality.VIDEO,
        SourceModality.FEED,
    ],
    SourceClass.MESSAGING: [SourceModality.CONVERSATION, SourceModality.TEXT, SourceModality.IMAGE],
    SourceClass.VIDEO_PLATFORM: [SourceModality.VIDEO, SourceModality.TEXT],
    SourceClass.AUDIO_PLATFORM: [SourceModality.AUDIO],
    SourceClass.CRM: [SourceModality.STRUCTURED_DATA, SourceModality.TEXT],
    SourceClass.PAYMENT_PROCESSING: [SourceModality.TRANSACTION, SourceModality.STRUCTURED_DATA],
    SourceClass.ACCOUNTING: [SourceModality.TRANSACTION, SourceModality.STRUCTURED_DATA],
    SourceClass.ANALYTICS: [SourceModality.STRUCTURED_DATA],
    SourceClass.ADVERTISING: [SourceModality.STRUCTURED_DATA, SourceModality.TEXT],
    SourceClass.AI_ASSISTANT: [
        SourceModality.CONVERSATION,
        SourceModality.TEXT,
        SourceModality.CODE,
    ],
    SourceClass.BROWSER_HISTORY: [SourceModality.STRUCTURED_DATA, SourceModality.TEXT],
    SourceClass.VOICE_MEMO: [SourceModality.AUDIO],
    SourceClass.CAMERA_CAPTURE: [SourceModality.IMAGE, SourceModality.VIDEO],
    SourceClass.SCREEN_CAPTURE: [SourceModality.IMAGE],
    SourceClass.EBOOK_READER: [SourceModality.TEXT, SourceModality.PDF],
    SourceClass.PODCAST_PLAYER: [SourceModality.AUDIO],
    SourceClass.DESIGN_TOOL: [SourceModality.IMAGE],
    SourceClass.THREE_D_MODELING: [SourceModality.STRUCTURED_DATA],
}

_SOURCE_CLASS_DEFAULT_ACCESS: dict[SourceClass, list[AccessMethod]] = {
    SourceClass.EMAIL: [AccessMethod.OFFICIAL_API, AccessMethod.OAUTH],
    SourceClass.CALENDAR: [AccessMethod.OFFICIAL_API, AccessMethod.OAUTH],
    SourceClass.TASK_MANAGEMENT: [AccessMethod.OFFICIAL_API, AccessMethod.API_KEY],
    SourceClass.NOTE_TAKING: [
        AccessMethod.LOCAL_FILESYSTEM,
        AccessMethod.EXPORT_FILE,
        AccessMethod.OFFICIAL_API,
    ],
    SourceClass.DOCUMENT_EDITING: [AccessMethod.OFFICIAL_API, AccessMethod.OAUTH],
    SourceClass.SPREADSHEET: [AccessMethod.OFFICIAL_API, AccessMethod.EXPORT_FILE],
    SourceClass.CLOUD_STORAGE: [AccessMethod.OFFICIAL_API, AccessMethod.OAUTH],
    SourceClass.CODE_REPOSITORY: [AccessMethod.OFFICIAL_API, AccessMethod.API_KEY],
    SourceClass.CI_CD: [AccessMethod.OFFICIAL_API, AccessMethod.WEBHOOK],
    SourceClass.CONTAINER_RUNTIME: [AccessMethod.LOCAL_FILESYSTEM],
    SourceClass.SOCIAL_MEDIA: [
        AccessMethod.BROWSER_SESSION,
        AccessMethod.OFFICIAL_API,
        AccessMethod.EXPORT_FILE,
    ],
    SourceClass.MESSAGING: [
        AccessMethod.OFFICIAL_API,
        AccessMethod.WEBHOOK,
        AccessMethod.EXPORT_FILE,
    ],
    SourceClass.VIDEO_PLATFORM: [AccessMethod.OFFICIAL_API, AccessMethod.RSS],
    SourceClass.AUDIO_PLATFORM: [AccessMethod.LOCAL_FILESYSTEM, AccessMethod.RSS],
    SourceClass.CRM: [AccessMethod.OFFICIAL_API],
    SourceClass.PAYMENT_PROCESSING: [AccessMethod.OFFICIAL_API, AccessMethod.API_KEY],
    SourceClass.ACCOUNTING: [AccessMethod.OFFICIAL_API, AccessMethod.OAUTH],
    SourceClass.ANALYTICS: [AccessMethod.OFFICIAL_API, AccessMethod.OAUTH],
    SourceClass.ADVERTISING: [AccessMethod.OFFICIAL_API, AccessMethod.OAUTH],
    SourceClass.AI_ASSISTANT: [AccessMethod.EXPORT_FILE, AccessMethod.OFFICIAL_API],
    SourceClass.BROWSER_HISTORY: [AccessMethod.LOCAL_FILESYSTEM, AccessMethod.BROWSER_EXTENSION],
    SourceClass.VOICE_MEMO: [AccessMethod.LOCAL_FILESYSTEM],
    SourceClass.CAMERA_CAPTURE: [AccessMethod.LOCAL_FILESYSTEM],
    SourceClass.SCREEN_CAPTURE: [AccessMethod.LOCAL_FILESYSTEM],
    SourceClass.EBOOK_READER: [AccessMethod.LOCAL_FILESYSTEM, AccessMethod.EXPORT_FILE],
    SourceClass.PODCAST_PLAYER: [AccessMethod.RSS, AccessMethod.LOCAL_FILESYSTEM],
    SourceClass.DESIGN_TOOL: [AccessMethod.LOCAL_FILESYSTEM, AccessMethod.EXPORT_FILE],
    SourceClass.THREE_D_MODELING: [AccessMethod.LOCAL_FILESYSTEM],
}

_SOURCE_CLASS_DEFAULT_TIER: dict[SourceClass, OnboardingTier] = {
    SourceClass.EMAIL: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.CALENDAR: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.TASK_MANAGEMENT: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.NOTE_TAKING: OnboardingTier.TIER_1_LOCAL_ARCHIVES,
    SourceClass.DOCUMENT_EDITING: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.SPREADSHEET: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.CLOUD_STORAGE: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.CODE_REPOSITORY: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.CI_CD: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.CONTAINER_RUNTIME: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.SOCIAL_MEDIA: OnboardingTier.TIER_3_SOCIAL_ALGORITHM,
    SourceClass.MESSAGING: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.VIDEO_PLATFORM: OnboardingTier.TIER_3_SOCIAL_ALGORITHM,
    SourceClass.AUDIO_PLATFORM: OnboardingTier.TIER_3_SOCIAL_ALGORITHM,
    SourceClass.CRM: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.PAYMENT_PROCESSING: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.ACCOUNTING: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.ANALYTICS: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.ADVERTISING: OnboardingTier.TIER_3_SOCIAL_ALGORITHM,
    SourceClass.AI_ASSISTANT: OnboardingTier.TIER_1_LOCAL_ARCHIVES,
    SourceClass.BROWSER_HISTORY: OnboardingTier.TIER_4_COMPUTER_USE,
    SourceClass.VOICE_MEMO: OnboardingTier.TIER_1_LOCAL_ARCHIVES,
    SourceClass.CAMERA_CAPTURE: OnboardingTier.TIER_1_LOCAL_ARCHIVES,
    SourceClass.SCREEN_CAPTURE: OnboardingTier.TIER_4_COMPUTER_USE,
    SourceClass.EBOOK_READER: OnboardingTier.TIER_1_LOCAL_ARCHIVES,
    SourceClass.PODCAST_PLAYER: OnboardingTier.TIER_3_SOCIAL_ALGORITHM,
    SourceClass.DESIGN_TOOL: OnboardingTier.TIER_2_WORKSPACE,
    SourceClass.THREE_D_MODELING: OnboardingTier.TIER_2_WORKSPACE,
}

_SOURCE_CLASS_DEFAULT_SENSITIVITY: dict[SourceClass, SourceSensitivity] = {
    SourceClass.EMAIL: SourceSensitivity.CONFIDENTIAL,
    SourceClass.CALENDAR: SourceSensitivity.INTERNAL,
    SourceClass.TASK_MANAGEMENT: SourceSensitivity.INTERNAL,
    SourceClass.NOTE_TAKING: SourceSensitivity.INTERNAL,
    SourceClass.DOCUMENT_EDITING: SourceSensitivity.INTERNAL,
    SourceClass.SPREADSHEET: SourceSensitivity.INTERNAL,
    SourceClass.CLOUD_STORAGE: SourceSensitivity.INTERNAL,
    SourceClass.CODE_REPOSITORY: SourceSensitivity.INTERNAL,
    SourceClass.CI_CD: SourceSensitivity.INTERNAL,
    SourceClass.CONTAINER_RUNTIME: SourceSensitivity.INTERNAL,
    SourceClass.SOCIAL_MEDIA: SourceSensitivity.PUBLIC,
    SourceClass.MESSAGING: SourceSensitivity.CONFIDENTIAL,
    SourceClass.VIDEO_PLATFORM: SourceSensitivity.PUBLIC,
    SourceClass.AUDIO_PLATFORM: SourceSensitivity.PUBLIC,
    SourceClass.CRM: SourceSensitivity.CONFIDENTIAL,
    SourceClass.PAYMENT_PROCESSING: SourceSensitivity.FINANCIAL,
    SourceClass.ACCOUNTING: SourceSensitivity.FINANCIAL,
    SourceClass.ANALYTICS: SourceSensitivity.INTERNAL,
    SourceClass.ADVERTISING: SourceSensitivity.INTERNAL,
    SourceClass.AI_ASSISTANT: SourceSensitivity.CONFIDENTIAL,
    SourceClass.BROWSER_HISTORY: SourceSensitivity.CONFIDENTIAL,
    SourceClass.VOICE_MEMO: SourceSensitivity.INTERNAL,
    SourceClass.CAMERA_CAPTURE: SourceSensitivity.INTERNAL,
    SourceClass.SCREEN_CAPTURE: SourceSensitivity.INTERNAL,
    SourceClass.EBOOK_READER: SourceSensitivity.PUBLIC,
    SourceClass.PODCAST_PLAYER: SourceSensitivity.PUBLIC,
    SourceClass.DESIGN_TOOL: SourceSensitivity.INTERNAL,
    SourceClass.THREE_D_MODELING: SourceSensitivity.INTERNAL,
}

_SOURCE_CLASS_DEFAULT_PRIORITY: dict[SourceClass, IngestionPriority] = {
    SourceClass.EMAIL: IngestionPriority.HIGH,
    SourceClass.CALENDAR: IngestionPriority.HIGH,
    SourceClass.TASK_MANAGEMENT: IngestionPriority.HIGH,
    SourceClass.NOTE_TAKING: IngestionPriority.HIGH,
    SourceClass.DOCUMENT_EDITING: IngestionPriority.MEDIUM,
    SourceClass.SPREADSHEET: IngestionPriority.MEDIUM,
    SourceClass.CLOUD_STORAGE: IngestionPriority.MEDIUM,
    SourceClass.CODE_REPOSITORY: IngestionPriority.HIGH,
    SourceClass.CI_CD: IngestionPriority.LOW,
    SourceClass.CONTAINER_RUNTIME: IngestionPriority.LOW,
    SourceClass.SOCIAL_MEDIA: IngestionPriority.MEDIUM,
    SourceClass.MESSAGING: IngestionPriority.HIGH,
    SourceClass.VIDEO_PLATFORM: IngestionPriority.LOW,
    SourceClass.AUDIO_PLATFORM: IngestionPriority.LOW,
    SourceClass.CRM: IngestionPriority.HIGH,
    SourceClass.PAYMENT_PROCESSING: IngestionPriority.CRITICAL,
    SourceClass.ACCOUNTING: IngestionPriority.CRITICAL,
    SourceClass.ANALYTICS: IngestionPriority.MEDIUM,
    SourceClass.ADVERTISING: IngestionPriority.MEDIUM,
    SourceClass.AI_ASSISTANT: IngestionPriority.HIGH,
    SourceClass.BROWSER_HISTORY: IngestionPriority.LOW,
    SourceClass.VOICE_MEMO: IngestionPriority.MEDIUM,
    SourceClass.CAMERA_CAPTURE: IngestionPriority.LOW,
    SourceClass.SCREEN_CAPTURE: IngestionPriority.LOW,
    SourceClass.EBOOK_READER: IngestionPriority.BACKGROUND,
    SourceClass.PODCAST_PLAYER: IngestionPriority.BACKGROUND,
    SourceClass.DESIGN_TOOL: IngestionPriority.MEDIUM,
    SourceClass.THREE_D_MODELING: IngestionPriority.LOW,
}

_SOURCE_CLASS_DEFAULT_CADENCE: dict[SourceClass, RefreshCadence] = {
    SourceClass.EMAIL: RefreshCadence.DAILY,
    SourceClass.CALENDAR: RefreshCadence.DAILY,
    SourceClass.TASK_MANAGEMENT: RefreshCadence.DAILY,
    SourceClass.NOTE_TAKING: RefreshCadence.WEEKLY,
    SourceClass.DOCUMENT_EDITING: RefreshCadence.WEEKLY,
    SourceClass.SPREADSHEET: RefreshCadence.WEEKLY,
    SourceClass.CLOUD_STORAGE: RefreshCadence.WEEKLY,
    SourceClass.CODE_REPOSITORY: RefreshCadence.DAILY,
    SourceClass.CI_CD: RefreshCadence.ON_DEMAND,
    SourceClass.CONTAINER_RUNTIME: RefreshCadence.ON_DEMAND,
    SourceClass.SOCIAL_MEDIA: RefreshCadence.DAILY,
    SourceClass.MESSAGING: RefreshCadence.DAILY,
    SourceClass.VIDEO_PLATFORM: RefreshCadence.WEEKLY,
    SourceClass.AUDIO_PLATFORM: RefreshCadence.WEEKLY,
    SourceClass.CRM: RefreshCadence.DAILY,
    SourceClass.PAYMENT_PROCESSING: RefreshCadence.DAILY,
    SourceClass.ACCOUNTING: RefreshCadence.WEEKLY,
    SourceClass.ANALYTICS: RefreshCadence.DAILY,
    SourceClass.ADVERTISING: RefreshCadence.DAILY,
    SourceClass.AI_ASSISTANT: RefreshCadence.ONE_TIME,
    SourceClass.BROWSER_HISTORY: RefreshCadence.WEEKLY,
    SourceClass.VOICE_MEMO: RefreshCadence.ON_DEMAND,
    SourceClass.CAMERA_CAPTURE: RefreshCadence.ON_DEMAND,
    SourceClass.SCREEN_CAPTURE: RefreshCadence.ON_DEMAND,
    SourceClass.EBOOK_READER: RefreshCadence.ONE_TIME,
    SourceClass.PODCAST_PLAYER: RefreshCadence.WEEKLY,
    SourceClass.DESIGN_TOOL: RefreshCadence.ON_DEMAND,
    SourceClass.THREE_D_MODELING: RefreshCadence.ON_DEMAND,
}


def get_platforms_for_class(source_class: SourceClass) -> list[PlatformType]:
    return _SOURCE_CLASS_PLATFORMS.get(source_class, [])


def get_modalities_for_class(source_class: SourceClass) -> list[SourceModality]:
    return _SOURCE_CLASS_MODALITIES.get(source_class, [])


def get_access_methods_for_class(source_class: SourceClass) -> list[AccessMethod]:
    return _SOURCE_CLASS_DEFAULT_ACCESS.get(source_class, [])


def get_default_tier(source_class: SourceClass) -> OnboardingTier:
    return _SOURCE_CLASS_DEFAULT_TIER.get(source_class, OnboardingTier.UNKNOWN)


def get_default_sensitivity(source_class: SourceClass) -> SourceSensitivity:
    return _SOURCE_CLASS_DEFAULT_SENSITIVITY.get(source_class, SourceSensitivity.UNKNOWN)


def get_default_priority(source_class: SourceClass) -> IngestionPriority:
    return _SOURCE_CLASS_DEFAULT_PRIORITY.get(source_class, IngestionPriority.UNKNOWN)


def get_default_cadence(source_class: SourceClass) -> RefreshCadence:
    return _SOURCE_CLASS_DEFAULT_CADENCE.get(source_class, RefreshCadence.UNKNOWN)


def get_class_for_platform(platform: PlatformType) -> SourceClass:
    for sc, platforms in _SOURCE_CLASS_PLATFORMS.items():
        if platform in platforms:
            return sc
    return SourceClass.UNKNOWN


def classify_source(name: str, description: str | None = None) -> SourceClass:
    key = (name + " " + (description or "")).lower()

    _MAP: list[tuple[list[str], SourceClass]] = [
        (["email", "inbox", "mail"], SourceClass.EMAIL),
        (["calendar", "schedule", "event"], SourceClass.CALENDAR),
        (["task", "todo", "project management"], SourceClass.TASK_MANAGEMENT),
        (["note", "wiki", "knowledge base"], SourceClass.NOTE_TAKING),
        (["document", "doc", "word"], SourceClass.DOCUMENT_EDITING),
        (["spreadsheet", "sheet", "excel"], SourceClass.SPREADSHEET),
        (["drive", "storage", "cloud", "dropbox"], SourceClass.CLOUD_STORAGE),
        (["git", "repo", "code", "github", "gitlab"], SourceClass.CODE_REPOSITORY),
        (["ci", "pipeline", "actions", "build"], SourceClass.CI_CD),
        (["docker", "container", "kubernetes"], SourceClass.CONTAINER_RUNTIME),
        (["instagram", "tiktok", "twitter", "linkedin", "social"], SourceClass.SOCIAL_MEDIA),
        (["discord", "telegram", "slack", "chat", "messenger", "whatsapp"], SourceClass.MESSAGING),
        (["youtube", "video", "stream"], SourceClass.VIDEO_PLATFORM),
        (["podcast", "spotify", "audio"], SourceClass.AUDIO_PLATFORM),
        (["crm", "lead", "pipeline", "sales"], SourceClass.CRM),
        (["stripe", "payment", "paypal", "billing"], SourceClass.PAYMENT_PROCESSING),
        (["quickbooks", "accounting", "invoice", "bookkeeping"], SourceClass.ACCOUNTING),
        (["analytics", "metrics", "tracking"], SourceClass.ANALYTICS),
        (["ads", "advertising", "campaign"], SourceClass.ADVERTISING),
        (["chatgpt", "claude", "ai chat", "ai assistant"], SourceClass.AI_ASSISTANT),
        (["browser history", "browsing"], SourceClass.BROWSER_HISTORY),
        (["voice memo", "voice note", "recording"], SourceClass.VOICE_MEMO),
        (["camera", "photo", "capture"], SourceClass.CAMERA_CAPTURE),
        (["screenshot", "screen capture"], SourceClass.SCREEN_CAPTURE),
        (["ebook", "kindle", "reader"], SourceClass.EBOOK_READER),
        (["podcast", "listen"], SourceClass.PODCAST_PLAYER),
        (["figma", "canva", "design"], SourceClass.DESIGN_TOOL),
        (["3d", "cad", "blender", "model"], SourceClass.THREE_D_MODELING),
    ]

    for keywords, sc in _MAP:
        if any(kw in key for kw in keywords):
            return sc
    return SourceClass.UNKNOWN


def list_source_classes() -> list[SourceClass]:
    return [sc for sc in SourceClass if sc != SourceClass.UNKNOWN]


def list_all_platforms() -> list[PlatformType]:
    return [p for p in PlatformType if p != PlatformType.UNKNOWN]
