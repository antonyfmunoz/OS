"""Phase 87C workstation optimization contracts — typed enums and dataclasses.

Device areas, audit modes, action types, risk levels, approval requirements,
reversibility, file classifications, performance tuning categories.

All enums have UNKNOWN fallback. All normalizers degrade gracefully.
All dataclasses support to_dict()/from_dict() round-trips.

Advisory/planning only. No real scanning. No cleanup. No deletion.
No process killing. No settings changes. No overclocking. No execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any


def _ws_id(prefix: str) -> str:
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


# ─── Enums (8) ───────────────────────────────────────────���──────────


@unique
class DeviceArea(str, Enum):
    STORAGE = "storage"
    MEMORY = "memory"
    CPU = "cpu"
    GPU = "gpu"
    BATTERY_POWER = "battery_power"
    THERMALS = "thermals"
    STARTUP_ITEMS = "startup_items"
    BACKGROUND_PROCESSES = "background_processes"
    INSTALLED_APPS = "installed_apps"
    BROWSER_DATA = "browser_data"
    CLOUD_SYNC = "cloud_sync"
    BACKUPS = "backups"
    LOCAL_FILES = "local_files"
    MEDIA_FOLDERS = "media_folders"
    DEVELOPMENT_ENVIRONMENT = "development_environment"
    DOCKER_VM = "docker_vm"
    PACKAGE_CACHES = "package_caches"
    SYSTEM_SETTINGS = "system_settings"
    DRIVERS = "drivers"
    BIOS_UEFI = "bios_uefi"
    NETWORK = "network"
    SECURITY = "security"
    CREDENTIALS = "credentials"
    UNKNOWN = "unknown"


@unique
class WorkstationAuditMode(str, Enum):
    PLANNING_ONLY = "planning_only"
    AUDIT_ONLY = "audit_only"
    RECOMMENDATION_ONLY = "recommendation_only"
    APPROVAL_REQUIRED = "approval_required"
    GOVERNED_EXECUTION_FUTURE = "governed_execution_future"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@unique
class OptimizationActionType(str, Enum):
    EXPLAIN = "explain"
    RECOMMEND = "recommend"
    ARCHIVE = "archive"
    DELETE = "delete"
    UNINSTALL = "uninstall"
    DISABLE_STARTUP = "disable_startup"
    KILL_PROCESS = "kill_process"
    CLEAR_CACHE = "clear_cache"
    MOVE_FILES = "move_files"
    CHANGE_SETTING = "change_setting"
    UPDATE_DRIVER = "update_driver"
    CHANGE_POWER_PROFILE = "change_power_profile"
    OVERCLOCK = "overclock"
    UNDERVOLT = "undervolt"
    FAN_CURVE_CHANGE = "fan_curve_change"
    BACKUP = "backup"
    RESTORE = "restore"
    DEFER = "defer"
    PRESERVE = "preserve"
    UNKNOWN = "unknown"


@unique
class OptimizationRiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@unique
class OptimizationApprovalRequirement(str, Enum):
    NONE = "none"
    REVIEW_RECOMMENDED = "review_recommended"
    EXPLICIT_APPROVAL = "explicit_approval"
    BATCH_APPROVAL_ALLOWED = "batch_approval_allowed"
    ONE_BY_ONE_APPROVAL = "one_by_one_approval"
    EXPERT_REVIEW_REQUIRED = "expert_review_required"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@unique
class OptimizationReversibility(str, Enum):
    FULLY_REVERSIBLE = "fully_reversible"
    MOSTLY_REVERSIBLE = "mostly_reversible"
    PARTIALLY_REVERSIBLE = "partially_reversible"
    HARD_TO_REVERSE = "hard_to_reverse"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"


@unique
class FileClassification(str, Enum):
    SYSTEM_CRITICAL = "system_critical"
    USER_CREATED = "user_created"
    GENERATED_CACHE = "generated_cache"
    TEMPORARY = "temporary"
    DUPLICATE_CANDIDATE = "duplicate_candidate"
    LARGE_FILE_CANDIDATE = "large_file_candidate"
    MEDIA_ARCHIVE = "media_archive"
    DEVELOPER_ARTIFACT = "developer_artifact"
    CREDENTIAL_OR_SECRET = "credential_or_secret"
    BUSINESS_CRITICAL = "business_critical"
    LEGAL_FINANCIAL = "legal_financial"
    CLOUD_SYNCED = "cloud_synced"
    UNKNOWN = "unknown"


@unique
class PerformanceTuningCategory(str, Enum):
    POWER_PROFILE = "power_profile"
    THERMAL_MANAGEMENT = "thermal_management"
    DRIVER_UPDATE = "driver_update"
    OVERCLOCKING = "overclocking"
    UNDERVOLTING = "undervolting"
    FAN_CURVE = "fan_curve"
    RAM_XMP_EXPO = "ram_xmp_expo"
    GPU_PROFILE = "gpu_profile"
    STORAGE_UPGRADE = "storage_upgrade"
    RAM_UPGRADE = "ram_upgrade"
    CLEANING_COOLING = "cleaning_cooling"
    UNKNOWN = "unknown"


# ─── Normalizers ────────────────────────────────────────────────────


def normalize_device_area(v: str | DeviceArea) -> DeviceArea:
    return _normalize(DeviceArea, v)  # type: ignore[return-value]


def normalize_audit_mode(v: str | WorkstationAuditMode) -> WorkstationAuditMode:
    return _normalize(WorkstationAuditMode, v)  # type: ignore[return-value]


def normalize_action_type(v: str | OptimizationActionType) -> OptimizationActionType:
    return _normalize(OptimizationActionType, v)  # type: ignore[return-value]


def normalize_risk_level(v: str | OptimizationRiskLevel) -> OptimizationRiskLevel:
    return _normalize(OptimizationRiskLevel, v)  # type: ignore[return-value]


def normalize_approval(v: str | OptimizationApprovalRequirement) -> OptimizationApprovalRequirement:
    return _normalize(OptimizationApprovalRequirement, v)  # type: ignore[return-value]


def normalize_reversibility(v: str | OptimizationReversibility) -> OptimizationReversibility:
    return _normalize(OptimizationReversibility, v)  # type: ignore[return-value]


def normalize_file_classification(v: str | FileClassification) -> FileClassification:
    return _normalize(FileClassification, v)  # type: ignore[return-value]


def normalize_tuning_category(v: str | PerformanceTuningCategory) -> PerformanceTuningCategory:
    return _normalize(PerformanceTuningCategory, v)  # type: ignore[return-value]


# ─── Dataclasses ──────────────────────────────────────────────���─────


@dataclass
class DeviceBaselineCategory:
    category_id: str = ""
    area: DeviceArea = DeviceArea.UNKNOWN
    name: str = ""
    description: str = ""
    audit_mode: WorkstationAuditMode = WorkstationAuditMode.PLANNING_ONLY
    default_risk: OptimizationRiskLevel = OptimizationRiskLevel.UNKNOWN
    default_approval: OptimizationApprovalRequirement = OptimizationApprovalRequirement.UNKNOWN
    explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category_id": self.category_id,
            "area": self.area.value,
            "name": self.name,
            "description": self.description,
            "audit_mode": self.audit_mode.value,
            "default_risk": self.default_risk.value,
            "default_approval": self.default_approval.value,
            "explanation": self.explanation,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DeviceBaselineCategory:
        return cls(
            category_id=d.get("category_id", ""),
            area=normalize_device_area(d.get("area", "unknown")),
            name=d.get("name", ""),
            description=d.get("description", ""),
            audit_mode=normalize_audit_mode(d.get("audit_mode", "unknown")),
            default_risk=normalize_risk_level(d.get("default_risk", "unknown")),
            default_approval=normalize_approval(d.get("default_approval", "unknown")),
            explanation=d.get("explanation", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass
class WorkstationBaselinePlan:
    plan_id: str = ""
    node_id: str = ""
    audit_mode: WorkstationAuditMode = WorkstationAuditMode.PLANNING_ONLY
    categories: list[DeviceBaselineCategory] = field(default_factory=list)
    safe_observations: list[str] = field(default_factory=list)
    blocked_observations: list[str] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "node_id": self.node_id,
            "audit_mode": self.audit_mode.value,
            "categories": [c.to_dict() for c in self.categories],
            "safe_observations": self.safe_observations,
            "blocked_observations": self.blocked_observations,
            "required_permissions": self.required_permissions,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkstationBaselinePlan:
        return cls(
            plan_id=d.get("plan_id", ""),
            node_id=d.get("node_id", ""),
            audit_mode=normalize_audit_mode(d.get("audit_mode", "unknown")),
            categories=[DeviceBaselineCategory.from_dict(c) for c in d.get("categories", [])],
            safe_observations=d.get("safe_observations", []),
            blocked_observations=d.get("blocked_observations", []),
            required_permissions=d.get("required_permissions", []),
            warnings=d.get("warnings", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class OptimizationCandidate:
    candidate_id: str = ""
    area: DeviceArea = DeviceArea.UNKNOWN
    action_type: OptimizationActionType = OptimizationActionType.UNKNOWN
    title: str = ""
    description: str = ""
    target: str = ""
    reason: str = ""
    estimated_benefit: str = ""
    risk_level: OptimizationRiskLevel = OptimizationRiskLevel.UNKNOWN
    approval_required: OptimizationApprovalRequirement = OptimizationApprovalRequirement.UNKNOWN
    reversibility: OptimizationReversibility = OptimizationReversibility.UNKNOWN
    rollback_plan_required: bool = False
    post_action_verification_required: bool = False
    non_actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "area": self.area.value,
            "action_type": self.action_type.value,
            "title": self.title,
            "description": self.description,
            "target": self.target,
            "reason": self.reason,
            "estimated_benefit": self.estimated_benefit,
            "risk_level": self.risk_level.value,
            "approval_required": self.approval_required.value,
            "reversibility": self.reversibility.value,
            "rollback_plan_required": self.rollback_plan_required,
            "post_action_verification_required": self.post_action_verification_required,
            "non_actions": self.non_actions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> OptimizationCandidate:
        return cls(
            candidate_id=d.get("candidate_id", ""),
            area=normalize_device_area(d.get("area", "unknown")),
            action_type=normalize_action_type(d.get("action_type", "unknown")),
            title=d.get("title", ""),
            description=d.get("description", ""),
            target=d.get("target", ""),
            reason=d.get("reason", ""),
            estimated_benefit=d.get("estimated_benefit", ""),
            risk_level=normalize_risk_level(d.get("risk_level", "unknown")),
            approval_required=normalize_approval(d.get("approval_required", "unknown")),
            reversibility=normalize_reversibility(d.get("reversibility", "unknown")),
            rollback_plan_required=d.get("rollback_plan_required", False),
            post_action_verification_required=d.get("post_action_verification_required", False),
            non_actions=d.get("non_actions", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class DeviceLiteracyExplanation:
    explanation_id: str = ""
    area: DeviceArea = DeviceArea.UNKNOWN
    topic: str = ""
    plain_language_summary: str = ""
    why_it_matters: str = ""
    what_good_looks_like: str = ""
    common_failure_modes: list[str] = field(default_factory=list)
    recommended_user_decisions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "explanation_id": self.explanation_id,
            "area": self.area.value,
            "topic": self.topic,
            "plain_language_summary": self.plain_language_summary,
            "why_it_matters": self.why_it_matters,
            "what_good_looks_like": self.what_good_looks_like,
            "common_failure_modes": self.common_failure_modes,
            "recommended_user_decisions": self.recommended_user_decisions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DeviceLiteracyExplanation:
        return cls(
            explanation_id=d.get("explanation_id", ""),
            area=normalize_device_area(d.get("area", "unknown")),
            topic=d.get("topic", ""),
            plain_language_summary=d.get("plain_language_summary", ""),
            why_it_matters=d.get("why_it_matters", ""),
            what_good_looks_like=d.get("what_good_looks_like", ""),
            common_failure_modes=d.get("common_failure_modes", []),
            recommended_user_decisions=d.get("recommended_user_decisions", []),
            metadata=d.get("metadata", {}),
        )


@dataclass
class PerformanceTuningAdvisory:
    advisory_id: str = ""
    category: PerformanceTuningCategory = PerformanceTuningCategory.UNKNOWN
    summary: str = ""
    compatibility_required: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    approval_required: OptimizationApprovalRequirement = (
        OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED
    )
    rollback_plan: str = ""
    stability_testing_required: bool = True
    recommendation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "advisory_id": self.advisory_id,
            "category": self.category.value,
            "summary": self.summary,
            "compatibility_required": self.compatibility_required,
            "risks": self.risks,
            "prerequisites": self.prerequisites,
            "approval_required": self.approval_required.value,
            "rollback_plan": self.rollback_plan,
            "stability_testing_required": self.stability_testing_required,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PerformanceTuningAdvisory:
        return cls(
            advisory_id=d.get("advisory_id", ""),
            category=normalize_tuning_category(d.get("category", "unknown")),
            summary=d.get("summary", ""),
            compatibility_required=d.get("compatibility_required", []),
            risks=d.get("risks", []),
            prerequisites=d.get("prerequisites", []),
            approval_required=normalize_approval(d.get("approval_required", "unknown")),
            rollback_plan=d.get("rollback_plan", ""),
            stability_testing_required=d.get("stability_testing_required", True),
            recommendation=d.get("recommendation", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass
class WorkstationOptimizationReport:
    report_id: str = ""
    node_id: str = ""
    baseline_plan: WorkstationBaselinePlan | None = None
    device_literacy_items: list[DeviceLiteracyExplanation] = field(default_factory=list)
    optimization_candidates: list[OptimizationCandidate] = field(default_factory=list)
    high_risk_items: list[str] = field(default_factory=list)
    preserved_items: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "node_id": self.node_id,
            "baseline_plan": self.baseline_plan.to_dict() if self.baseline_plan else None,
            "device_literacy_items": [e.to_dict() for e in self.device_literacy_items],
            "optimization_candidates": [c.to_dict() for c in self.optimization_candidates],
            "high_risk_items": self.high_risk_items,
            "preserved_items": self.preserved_items,
            "warnings": self.warnings,
            "next_steps": self.next_steps,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> WorkstationOptimizationReport:
        bp = d.get("baseline_plan")
        return cls(
            report_id=d.get("report_id", ""),
            node_id=d.get("node_id", ""),
            baseline_plan=WorkstationBaselinePlan.from_dict(bp) if bp else None,
            device_literacy_items=[
                DeviceLiteracyExplanation.from_dict(e) for e in d.get("device_literacy_items", [])
            ],
            optimization_candidates=[
                OptimizationCandidate.from_dict(c) for c in d.get("optimization_candidates", [])
            ],
            high_risk_items=d.get("high_risk_items", []),
            preserved_items=d.get("preserved_items", []),
            warnings=d.get("warnings", []),
            next_steps=d.get("next_steps", []),
            metadata=d.get("metadata", {}),
        )
