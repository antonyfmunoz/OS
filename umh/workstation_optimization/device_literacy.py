"""Phase 87C device literacy — plain-language explanations of device areas.

Advisory/planning only. No real scanning. No cleanup. No deletion.
No process killing. No settings changes. No overclocking. No execution.
"""

from __future__ import annotations

from umh.workstation_optimization.contracts import (
    DeviceArea,
    DeviceLiteracyExplanation,
    _ws_id,
)


def build_default_device_literacy_explanations() -> list[DeviceLiteracyExplanation]:
    return [
        _explain_storage(),
        _explain_memory(),
        _explain_cpu_gpu(),
        _explain_startup_processes(),
        _explain_cloud_sync(),
        _explain_developer_bloat(),
        _explain_overclocking(),
        _explain_thermals(),
        _explain_browser(),
        _explain_backups(),
        _explain_power_modes(),
    ]


def explain_device_area(area: DeviceArea) -> DeviceLiteracyExplanation | None:
    mapping = {
        DeviceArea.STORAGE: _explain_storage,
        DeviceArea.MEMORY: _explain_memory,
        DeviceArea.CPU: _explain_cpu_gpu,
        DeviceArea.GPU: _explain_cpu_gpu,
        DeviceArea.STARTUP_ITEMS: _explain_startup_processes,
        DeviceArea.BACKGROUND_PROCESSES: _explain_startup_processes,
        DeviceArea.CLOUD_SYNC: _explain_cloud_sync,
        DeviceArea.DEVELOPMENT_ENVIRONMENT: _explain_developer_bloat,
        DeviceArea.DOCKER_VM: _explain_developer_bloat,
        DeviceArea.PACKAGE_CACHES: _explain_developer_bloat,
        DeviceArea.THERMALS: _explain_thermals,
        DeviceArea.BROWSER_DATA: _explain_browser,
        DeviceArea.BACKUPS: _explain_backups,
        DeviceArea.BATTERY_POWER: _explain_power_modes,
    }
    fn = mapping.get(area)
    return fn() if fn else None


def explain_storage_basics() -> DeviceLiteracyExplanation:
    return _explain_storage()


def explain_memory_basics() -> DeviceLiteracyExplanation:
    return _explain_memory()


def explain_cpu_gpu_basics() -> DeviceLiteracyExplanation:
    return _explain_cpu_gpu()


def explain_startup_processes() -> DeviceLiteracyExplanation:
    return _explain_startup_processes()


def explain_cloud_sync_risks() -> DeviceLiteracyExplanation:
    return _explain_cloud_sync()


def explain_developer_bloat() -> DeviceLiteracyExplanation:
    return _explain_developer_bloat()


def explain_overclocking_risks() -> DeviceLiteracyExplanation:
    return _explain_overclocking()


def _explain_storage() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.STORAGE,
        topic="Storage: SSDs, HDDs, and Disk Space",
        plain_language_summary=(
            "Your computer has one or more drives that store everything — the operating system, apps, files, "
            "and caches. SSDs (Solid State Drives) are fast and have no moving parts. HDDs (Hard Disk Drives) "
            "are slower, cheaper, and use spinning platters. Many modern machines use SSDs for the OS and apps, "
            "with optional HDDs or external drives for bulk storage."
        ),
        why_it_matters=(
            "Running low on disk space causes slowdowns, failed updates, app crashes, and inability to save files. "
            "SSDs also slow down when nearly full because they need free space for wear leveling."
        ),
        what_good_looks_like="At least 15-20% free space on your primary drive. OS and apps on SSD. Media archives on separate/external drive.",
        common_failure_modes=[
            "Boot drive nearly full — system becomes sluggish or unresponsive",
            "Downloads folder accumulates gigabytes of forgotten files",
            "Cloud sync duplicates files across drives without user awareness",
            "Docker images and developer caches consume tens of GB silently",
            "Old backups and Time Machine snapshots fill internal drive",
        ],
        recommended_user_decisions=[
            "Know which drive is your SSD and which is HDD",
            "Check free space monthly",
            "Move large media to external or cloud storage",
            "Clean downloads folder regularly",
            "Monitor developer tool disk usage",
        ],
    )


def _explain_memory() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.MEMORY,
        topic="RAM: Memory vs. Storage",
        plain_language_summary=(
            "RAM (Random Access Memory) is fast, temporary workspace your computer uses while running apps. "
            "It is NOT the same as storage/disk space. When you open Chrome, Photoshop, or VS Code, they load "
            "into RAM. When RAM fills up, the OS uses swap (disk as overflow), which is much slower."
        ),
        why_it_matters=(
            "Insufficient RAM causes freezing, slow app switching, and system stuttering. Browsers with many tabs, "
            "Docker, IDEs, and media editing are heavy RAM consumers."
        ),
        what_good_looks_like="8 GB minimum for basic use. 16 GB for development. 32 GB+ for heavy multitasking, VMs, or media production.",
        common_failure_modes=[
            "Too many browser tabs consuming several GB",
            "Docker containers consuming available RAM",
            "IDE + multiple dev servers running simultaneously",
            "Memory leaks in long-running applications",
            "Swap thrashing causing system freeze",
        ],
        recommended_user_decisions=[
            "Know how much RAM your machine has",
            "Close unused apps and tabs",
            "Monitor which apps use the most memory",
            "Consider upgrading RAM if consistently maxed out",
        ],
    )


def _explain_cpu_gpu() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.CPU,
        topic="CPU and GPU: Processing Power",
        plain_language_summary=(
            "The CPU (Central Processing Unit) handles general computation — running apps, compiling code, "
            "managing the OS. The GPU (Graphics Processing Unit) handles visual rendering, video editing, "
            "3D work, and increasingly AI/ML workloads. Some machines have integrated graphics (GPU built into CPU) "
            "and some have discrete GPUs (separate chip with dedicated VRAM)."
        ),
        why_it_matters=(
            "High CPU usage causes slowdowns across all apps. High GPU usage affects rendering, video playback, "
            "and display responsiveness. Sustained high load causes thermal throttling — the system reduces speed "
            "to prevent overheating."
        ),
        what_good_looks_like="CPU usage under 80% during normal work. GPU temps under 85C. No thermal throttling during standard tasks.",
        common_failure_modes=[
            "Background processes consuming CPU silently",
            "Browser extensions running expensive scripts",
            "Indexing services (Spotlight, Windows Search) running during work",
            "Thermal throttling due to dust buildup or poor ventilation",
            "GPU driver issues causing crashes or artifacts",
        ],
        recommended_user_decisions=[
            "Learn to check CPU/GPU usage in task manager or activity monitor",
            "Identify processes using high CPU",
            "Keep laptop vents unblocked",
            "Update GPU drivers through official channels",
        ],
    )


def _explain_startup_processes() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.STARTUP_ITEMS,
        topic="Startup Apps and Background Processes",
        plain_language_summary=(
            "Many apps register themselves to start automatically when your computer boots. Each startup app "
            "adds to boot time and consumes RAM/CPU in the background. Some are essential (antivirus, drivers). "
            "Many are not (updaters, chat apps, cloud sync agents)."
        ),
        why_it_matters=(
            "Too many startup items slow boot time, consume RAM before you even open anything, and keep your "
            "CPU busy with background tasks. Some background processes also send data, check for updates, or "
            "sync files continuously."
        ),
        what_good_looks_like="Only essential items at startup. Non-essential apps launched manually when needed. Boot time under 30 seconds on SSD.",
        common_failure_modes=[
            "20+ apps launching at boot — 3-5 minute startup",
            "Multiple cloud sync agents running simultaneously",
            "Old software updaters for apps no longer used",
            "Chat apps (Discord, Slack, Teams) all launching at boot",
            "Unknown background processes from bundled software",
        ],
        recommended_user_decisions=[
            "Review startup items in task manager / system preferences",
            "Disable non-essential startup apps",
            "Keep security tools and critical drivers enabled",
            "Research unknown startup items before disabling",
        ],
    )


def _explain_cloud_sync() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.CLOUD_SYNC,
        topic="Cloud Sync: Duplication and Storage Impact",
        plain_language_summary=(
            "Cloud sync services (Dropbox, iCloud, Google Drive, OneDrive) keep local copies of your cloud files. "
            "If you have multiple sync services or sync large folders, you may be storing the same files 2-3 times: "
            "once locally, once in the cloud, and once in another sync service."
        ),
        why_it_matters=(
            "Cloud sync duplication can consume tens or hundreds of GB on your local drive without you realizing it. "
            "Sync conflicts can corrupt or duplicate files. Background sync uses bandwidth and CPU."
        ),
        what_good_looks_like="One primary sync service. Large files set to online-only. Known sync folder locations.",
        common_failure_modes=[
            "Multiple sync services syncing overlapping folders",
            "Full local copies of large cloud archives consuming SSD space",
            "Sync conflicts creating duplicate files",
            "Sync running during bandwidth-sensitive tasks",
            "Accidentally deleting synced files, losing cloud copy",
        ],
        recommended_user_decisions=[
            "Know which sync services are active and what folders they cover",
            "Use online-only / on-demand mode for large archives",
            "Consolidate to fewer sync services if possible",
            "Check sync folder sizes periodically",
        ],
    )


def _explain_developer_bloat() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.DEVELOPMENT_ENVIRONMENT,
        topic="Developer Environment Bloat",
        plain_language_summary=(
            "Development tools create large amounts of cached and generated files: node_modules folders (often "
            "200-500 MB each), Python virtual environments, Docker images (1-10 GB each), package manager caches, "
            "build artifacts, and log files. A developer with 10 projects can easily have 20-50 GB of generated files."
        ),
        why_it_matters=(
            "Developer artifacts are the single largest source of recoverable disk space for most technical users. "
            "Old node_modules, unused Docker images, and stale venvs are safe to remove and will be regenerated "
            "when needed."
        ),
        what_good_looks_like="Regular cleanup of unused project dependencies. Docker image pruning. Package cache clearing quarterly.",
        common_failure_modes=[
            "50+ node_modules folders from abandoned projects",
            "Dozens of Docker images never pruned",
            "Python venvs for projects no longer worked on",
            "npm/pip/cargo caches growing to multi-GB",
            "Build artifacts and log files accumulating over months",
        ],
        recommended_user_decisions=[
            "Run 'docker system prune' periodically to clear unused images",
            "Delete node_modules in projects you are not actively working on",
            "Clear package manager caches quarterly",
            "Review virtual environments and remove unused ones",
            "Identify largest folders with disk usage tools",
        ],
    )


def _explain_overclocking() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.BIOS_UEFI,
        topic="Overclocking and Undervolting Risks",
        plain_language_summary=(
            "Overclocking increases CPU/GPU/RAM clock speeds beyond factory defaults for more performance. "
            "Undervolting reduces voltage to lower temperatures and power consumption. Both modify hardware "
            "behavior at a fundamental level and carry real risks."
        ),
        why_it_matters=(
            "Incorrect overclocking can cause system instability, crashes, data corruption, and hardware damage. "
            "Incorrect undervolting can cause random crashes and data loss. Both require knowledge of your specific "
            "hardware, cooling capacity, and power delivery."
        ),
        what_good_looks_like="Only attempted by informed users. Stability tested. Temperatures monitored. Rollback plan ready.",
        common_failure_modes=[
            "System crashes under load after overclock",
            "Data corruption from unstable memory overclock",
            "Reduced hardware lifespan from excessive voltage",
            "Random blue screens from aggressive undervolt",
            "Thermal throttling negating overclock gains",
            "Voided warranty from unsupported modifications",
        ],
        recommended_user_decisions=[
            "Do not overclock unless you understand the risks",
            "Start with safe first steps (cleanup, cooling, power profile) before hardware tuning",
            "If overclocking: research your specific hardware, use conservative settings, stress test thoroughly",
            "Always have a way to reset to defaults (CMOS clear, BIOS reset)",
            "Monitor temperatures during and after changes",
        ],
    )


def _explain_thermals() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.THERMALS,
        topic="Thermal Management and Cooling",
        plain_language_summary=(
            "Your CPU and GPU generate heat proportional to their workload. Cooling systems (fans, heatsinks, "
            "liquid cooling) remove this heat. When components get too hot, they automatically reduce speed "
            "(thermal throttling) to prevent damage."
        ),
        why_it_matters=(
            "Poor cooling causes throttling, which reduces performance. Sustained high temperatures can shorten "
            "hardware lifespan. Dust buildup is the most common cause of overheating."
        ),
        what_good_looks_like="CPU under 80C during sustained work. GPU under 85C during rendering. No thermal throttling under normal use.",
        common_failure_modes=[
            "Dust-clogged vents and fans — reduced airflow",
            "Laptop on soft surface blocking intake vents",
            "Dried thermal paste (3-5 year machines)",
            "Fan failure causing rapid overheating",
            "Ambient room temperature too high for adequate cooling",
        ],
        recommended_user_decisions=[
            "Clean dust from vents and fans annually",
            "Use laptop on hard, flat surface",
            "Monitor temperatures if performance seems to degrade over time",
            "Consider repasting if machine is 3+ years old and running hot",
        ],
    )


def _explain_browser() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.BROWSER_DATA,
        topic="Browser Memory and Cache",
        plain_language_summary=(
            "Web browsers (Chrome, Firefox, Edge, Safari) use significant RAM — each tab is a separate process. "
            "30 tabs can easily use 4-8 GB of RAM. Browsers also store caches, cookies, extensions, and session "
            "data that accumulate over time."
        ),
        why_it_matters="Browsers are often the single largest RAM consumer on a machine. Heavy browser usage affects all other apps.",
        what_good_looks_like="Tab count under 20 for regular use. Extensions limited to essentials. Cache cleared periodically.",
        common_failure_modes=[
            "100+ tabs open consuming all available RAM",
            "Extensions running scripts on every page load",
            "Multi-GB browser cache on machines with limited storage",
            "Saved passwords and sessions creating security risk if machine is compromised",
        ],
        recommended_user_decisions=[
            "Use a tab manager or bookmark tabs you plan to read later",
            "Review and remove unused extensions",
            "Clear cache periodically if storage is limited",
            "Use separate browser profiles for personal vs work",
        ],
    )


def _explain_backups() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.BACKUPS,
        topic="Backups: Your Safety Net",
        plain_language_summary=(
            "Backups are copies of your files stored separately from your main drive. They protect against "
            "hardware failure, accidental deletion, ransomware, and data corruption. Types include local backups "
            "(external drive), cloud backups (Backblaze, iCloud, Google), and versioned backups (Time Machine, "
            "File History)."
        ),
        why_it_matters="Without backups, a single drive failure or mistake can destroy irreplaceable files. Most optimization actions are safer when a backup exists.",
        what_good_looks_like="At least one backup method active. Backup verified within last 30 days. Critical files in 2+ locations.",
        common_failure_modes=[
            "No backup at all — single point of failure",
            "Backup drive disconnected for months",
            "Cloud sync mistaken for backup (sync propagates deletions)",
            "Backup not verified — may be corrupted or incomplete",
        ],
        recommended_user_decisions=[
            "Set up at least one backup method",
            "Verify backup works by restoring a test file",
            "Understand that cloud sync is not the same as backup",
            "Keep critical files in at least two separate locations",
        ],
    )


def _explain_power_modes() -> DeviceLiteracyExplanation:
    return DeviceLiteracyExplanation(
        explanation_id=_ws_id("lit"),
        area=DeviceArea.BATTERY_POWER,
        topic="Power Profiles and Battery Management",
        plain_language_summary=(
            "Operating systems offer power profiles (Balanced, High Performance, Power Saver) that control "
            "CPU speed, screen brightness, sleep behavior, and background activity. Laptops also manage "
            "battery charging behavior and health."
        ),
        why_it_matters="Wrong power profile can cause either poor performance or unnecessary battery wear. Many users never check their power settings.",
        what_good_looks_like="Balanced profile for daily use. High Performance only when needed. Battery charge limited to 80% for longevity if supported.",
        common_failure_modes=[
            "Power Saver mode active during demanding work",
            "High Performance mode draining battery unnecessarily on laptop",
            "Battery always charged to 100% — accelerates degradation",
            "Sleep settings preventing machine from sleeping properly",
        ],
        recommended_user_decisions=[
            "Check which power profile is active",
            "Use Balanced for general use",
            "Enable battery health features if available",
            "Only use High Performance for specific demanding tasks",
        ],
    )


def literacy_explanation_to_dict(exp: DeviceLiteracyExplanation) -> dict:
    return exp.to_dict()
