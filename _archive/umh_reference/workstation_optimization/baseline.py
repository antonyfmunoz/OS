"""Phase 87C workstation baseline — default categories and onboarding plans.

Advisory/planning only. No real scanning. No cleanup. No deletion.
No process killing. No settings changes. No overclocking. No execution.
"""

from __future__ import annotations

from umh.workstation_optimization.contracts import (
    DeviceArea,
    DeviceBaselineCategory,
    OptimizationApprovalRequirement,
    OptimizationRiskLevel,
    WorkstationAuditMode,
    WorkstationBaselinePlan,
    _ws_id,
)


_DEFAULT_CATEGORIES: list[
    tuple[DeviceArea, str, str, OptimizationRiskLevel, OptimizationApprovalRequirement]
] = [
    (
        DeviceArea.STORAGE,
        "Storage / Drives",
        "Internal and external drives, free space, partition layout",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
    ),
    (
        DeviceArea.MEMORY,
        "RAM / Memory Pressure",
        "Installed RAM, usage patterns, swap/page file",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.NONE,
    ),
    (
        DeviceArea.CPU,
        "CPU Usage",
        "Processor load, core utilization, thermal throttling indicators",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.NONE,
    ),
    (
        DeviceArea.GPU,
        "GPU Usage",
        "Graphics processor load, VRAM, driver version",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.NONE,
    ),
    (
        DeviceArea.STARTUP_ITEMS,
        "Startup Apps",
        "Applications that launch at boot",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
    ),
    (
        DeviceArea.BACKGROUND_PROCESSES,
        "Background Processes",
        "Running services and processes consuming resources",
        OptimizationRiskLevel.MEDIUM,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
    ),
    (
        DeviceArea.INSTALLED_APPS,
        "Installed Applications",
        "All installed software including rarely used apps",
        OptimizationRiskLevel.MEDIUM,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
    ),
    (
        DeviceArea.BROWSER_DATA,
        "Browser Data",
        "Browser cache, extensions, saved sessions, cookies",
        OptimizationRiskLevel.MEDIUM,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
    ),
    (
        DeviceArea.CLOUD_SYNC,
        "Cloud Sync Folders",
        "Dropbox, iCloud, Google Drive, OneDrive sync paths and duplication",
        OptimizationRiskLevel.MEDIUM,
        OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
    ),
    (
        DeviceArea.BACKUPS,
        "Backups",
        "Local and cloud backup status, coverage, freshness",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
    ),
    (
        DeviceArea.LOCAL_FILES,
        "Downloads / Large Files",
        "Downloads folder, large files, duplicate candidates",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
    ),
    (
        DeviceArea.MEDIA_FOLDERS,
        "Media Folders",
        "Photos, videos, music, and media archives",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
    ),
    (
        DeviceArea.DEVELOPMENT_ENVIRONMENT,
        "Developer Environments",
        "IDEs, SDKs, language runtimes, project folders",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
    ),
    (
        DeviceArea.DOCKER_VM,
        "Docker / VM Storage",
        "Docker images, containers, volumes, VM disk images",
        OptimizationRiskLevel.MEDIUM,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
    ),
    (
        DeviceArea.PACKAGE_CACHES,
        "Package Caches",
        "node_modules, pip cache, npm cache, cargo cache, brew cache",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.BATCH_APPROVAL_ALLOWED,
    ),
    (
        DeviceArea.SYSTEM_SETTINGS,
        "System Settings",
        "OS configuration, power settings, display, notifications",
        OptimizationRiskLevel.MEDIUM,
        OptimizationApprovalRequirement.EXPLICIT_APPROVAL,
    ),
    (
        DeviceArea.DRIVERS,
        "Drivers",
        "Hardware driver versions, update status, compatibility",
        OptimizationRiskLevel.HIGH,
        OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED,
    ),
    (
        DeviceArea.BATTERY_POWER,
        "Power / Battery",
        "Power profile, battery health, charging behavior",
        OptimizationRiskLevel.LOW,
        OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
    ),
    (
        DeviceArea.THERMALS,
        "Thermals / Cooling",
        "CPU/GPU temperatures, fan behavior, thermal throttling",
        OptimizationRiskLevel.MEDIUM,
        OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
    ),
    (
        DeviceArea.BIOS_UEFI,
        "BIOS / UEFI",
        "Firmware settings, boot order, XMP/EXPO, secure boot",
        OptimizationRiskLevel.CRITICAL,
        OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED,
    ),
    (
        DeviceArea.NETWORK,
        "Network",
        "Wi-Fi, Ethernet, VPN, DNS, firewall configuration",
        OptimizationRiskLevel.MEDIUM,
        OptimizationApprovalRequirement.REVIEW_RECOMMENDED,
    ),
    (
        DeviceArea.SECURITY,
        "Security Tools",
        "Antivirus, firewall, encryption status, secure boot",
        OptimizationRiskLevel.HIGH,
        OptimizationApprovalRequirement.EXPERT_REVIEW_REQUIRED,
    ),
    (
        DeviceArea.CREDENTIALS,
        "Credentials / Secrets",
        "Password managers, SSH keys, API keys, tokens",
        OptimizationRiskLevel.CRITICAL,
        OptimizationApprovalRequirement.DISABLED,
    ),
]


_BLOCKED_OBSERVATIONS: list[str] = [
    "Credential contents (passwords, API keys, tokens)",
    "Password manager database contents",
    "Private key file contents",
    "System-protected files (OS internals)",
    "Unknown hidden system directories",
    "Destructive mutation of any kind",
    "BIOS/UEFI mutation",
    "Overclocking/undervolting execution",
    "Process killing",
    "File deletion",
    "App uninstallation",
    "Settings changes",
]


def build_default_baseline_categories() -> list[DeviceBaselineCategory]:
    return [
        DeviceBaselineCategory(
            category_id=_ws_id("bcat"),
            area=area,
            name=name,
            description=desc,
            audit_mode=WorkstationAuditMode.PLANNING_ONLY,
            default_risk=risk,
            default_approval=approval,
        )
        for area, name, desc, risk, approval in _DEFAULT_CATEGORIES
    ]


def create_workstation_baseline_plan(
    node_id: str = "local_pc",
    audit_mode: WorkstationAuditMode = WorkstationAuditMode.PLANNING_ONLY,
) -> WorkstationBaselinePlan:
    categories = build_default_baseline_categories()
    for cat in categories:
        cat.audit_mode = audit_mode

    safe_observations = [
        "Disk space usage per drive/partition",
        "RAM total and available",
        "CPU core count and current load",
        "GPU model and VRAM",
        "List of startup items (names only)",
        "List of running processes (names, resource usage)",
        "List of installed applications (names, sizes)",
        "Browser extension list (names only)",
        "Cloud sync folder paths and sizes",
        "Backup status and last backup date",
        "Downloads folder size",
        "Developer environment paths and sizes",
        "Docker image/container/volume sizes",
        "Package cache sizes",
        "Power profile name",
        "CPU/GPU temperature readings",
        "Driver version numbers",
    ]

    return WorkstationBaselinePlan(
        plan_id=_ws_id("bplan"),
        node_id=node_id,
        audit_mode=audit_mode,
        categories=categories,
        safe_observations=safe_observations,
        blocked_observations=list(_BLOCKED_OBSERVATIONS),
        required_permissions=[
            "Read-only file system access",
            "Process list read",
            "System info read",
        ],
        warnings=[
            "Planning-only mode — no changes will be made",
            "Real audit requires future phase implementation",
        ],
    )


def build_onboarding_workstation_baseline_plan(
    node_id: str = "local_pc",
) -> WorkstationBaselinePlan:
    return create_workstation_baseline_plan(
        node_id=node_id,
        audit_mode=WorkstationAuditMode.PLANNING_ONLY,
    )
