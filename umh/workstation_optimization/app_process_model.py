"""Phase 87C app/process model — classification and policy for apps and processes.

Advisory/planning only. No real process listing. No killing. No uninstalling.
"""

from __future__ import annotations

from typing import Any

from umh.workstation_optimization.contracts import (
    OptimizationActionType,
    OptimizationApprovalRequirement,
    OptimizationRiskLevel,
)


_SECURITY_KEYWORDS = frozenset(
    {
        "antivirus",
        "firewall",
        "defender",
        "malwarebytes",
        "norton",
        "mcafee",
        "bitdefender",
        "kaspersky",
        "1password",
        "bitwarden",
        "lastpass",
        "keepass",
        "keychain",
        "credential",
        "authenticator",
        "yubikey",
        "gpg",
        "ssh-agent",
        "vault",
    }
)

_SYSTEM_KEYWORDS = frozenset(
    {
        "kernel",
        "systemd",
        "init",
        "launchd",
        "svchost",
        "csrss",
        "winlogon",
        "explorer",
        "finder",
        "windowserver",
        "loginwindow",
        "dbus",
        "udev",
        "cron",
        "atd",
        "networkmanager",
        "resolved",
        "journald",
    }
)

_STARTUP_BLOAT_KEYWORDS = frozenset(
    {
        "updater",
        "helper",
        "agent",
        "sync",
        "tray",
        "notifier",
        "launcher",
        "spotify",
        "discord",
        "slack",
        "teams",
        "zoom",
        "skype",
        "telegram",
        "steam",
        "epic",
        "onedrive",
        "dropbox",
        "creative cloud",
    }
)


def classify_app_candidate(
    name: str | None = None,
    purpose: str | None = None,
    context: str | None = None,
) -> str:
    hints = " ".join(filter(None, [name, purpose, context])).lower()
    if not hints:
        return "unknown"
    if any(k in hints for k in _SECURITY_KEYWORDS):
        return "security_tool"
    if any(k in hints for k in _SYSTEM_KEYWORDS):
        return "system_process"
    if any(k in hints for k in _STARTUP_BLOAT_KEYWORDS):
        return "startup_bloat_candidate"
    return "unknown"


def classify_process_candidate(
    name: str | None = None,
    purpose: str | None = None,
    context: str | None = None,
) -> str:
    hints = " ".join(filter(None, [name, purpose, context])).lower()
    if not hints:
        return "unknown"
    if any(k in hints for k in _SECURITY_KEYWORDS):
        return "security_tool"
    if any(k in hints for k in _SYSTEM_KEYWORDS):
        return "system_process"
    if "high" in hints and ("cpu" in hints or "memory" in hints or "resource" in hints):
        return "high_resource_unknown"
    return "unknown"


def recommend_app_action(
    classification: str,
    usage_confidence: float | None = None,
) -> dict[str, Any]:
    if classification in ("security_tool", "system_process"):
        return _action(
            "preserve", "disabled", "critical", "Security and system tools must be preserved"
        )
    if classification == "startup_bloat_candidate":
        if usage_confidence is not None and usage_confidence < 0.3:
            return _action(
                "uninstall",
                "explicit_approval",
                "medium",
                "Rarely used app — uninstall candidate with approval",
            )
        return _action(
            "recommend", "explicit_approval", "low", "Review usage and decide whether to keep"
        )
    return _action("preserve", "disabled", "medium", "Unknown app — preserve until identified")


def recommend_process_action(
    classification: str,
    usage_confidence: float | None = None,
) -> dict[str, Any]:
    if classification in ("security_tool", "system_process"):
        return _action(
            "preserve", "disabled", "critical", "Security and system processes must not be killed"
        )
    if classification == "high_resource_unknown":
        return _action(
            "recommend",
            "explicit_approval",
            "high",
            "High-resource unknown process — investigate, do not kill blindly",
        )
    return _action("preserve", "disabled", "medium", "Unknown process — preserve until identified")


def build_startup_item_policy() -> dict[str, Any]:
    return {
        "policy_name": "Startup Item Review Policy",
        "rules": [
            {
                "classification": "security_tool",
                "action": "preserve",
                "reason": "Security tools must start at boot",
            },
            {
                "classification": "system_process",
                "action": "preserve",
                "reason": "System processes required for OS function",
            },
            {
                "classification": "startup_bloat_candidate",
                "action": "disable_startup",
                "approval": "explicit_approval",
                "reason": "Non-essential startup items slow boot and consume resources",
            },
            {
                "classification": "unknown",
                "action": "preserve",
                "reason": "Unknown items preserved until identified",
            },
        ],
        "core_rule": "Never disable security or system startup items. Research unknown items before disabling. Explicit approval required for all disable actions.",
    }


def build_process_policy() -> dict[str, Any]:
    return {
        "policy_name": "Process Management Policy",
        "rules": [
            {
                "classification": "security_tool",
                "action": "preserve",
                "reason": "Never kill security processes",
            },
            {
                "classification": "system_process",
                "action": "preserve",
                "reason": "Never kill system processes",
            },
            {
                "classification": "high_resource_unknown",
                "action": "investigate",
                "approval": "explicit_approval",
                "reason": "Investigate before killing — may be critical",
            },
            {
                "classification": "unknown",
                "action": "preserve",
                "reason": "Unknown processes preserved until identified",
            },
        ],
        "core_rule": "Killing any process requires explicit approval. Unknown processes are not killed — they are investigated first.",
    }


def _action(action: str, approval: str, risk: str, reason: str) -> dict[str, Any]:
    return {
        "recommended_action": action,
        "approval_required": approval,
        "risk_level": risk,
        "reason": reason,
    }
