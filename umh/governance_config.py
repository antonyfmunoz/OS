"""User-facing governance preferences for UMH workstation.

Wraps substrate/control_plane/governance.py with a configurable
behavioral layer. The substrate handles the LOCKED tier (encryption,
audit, auth, human supremacy) — always on, non-configurable. This
module handles the CONFIGURABLE tier — per-domain autonomy, notification
frequency, proactivity, data retention, approval thresholds.

Two tiers, one system:
  LOCKED (substrate):      security, audit, encryption, human supremacy
  CONFIGURABLE (this file): autonomy level, notifications, proactivity
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
GOVERNANCE_FILE = os.path.join(UMH_ROOT, "data", "sessions", "governance.json")


class AutonomyLevel(StrEnum):
    """How much the AI can do without asking."""

    NONE = "none"
    READ_ONLY = "read_only"
    SUGGEST = "suggest"
    ACT_WITH_APPROVAL = "act_with_approval"
    ACT_FREELY = "act_freely"


class NotificationFrequency(StrEnum):
    """How often the AI surfaces information."""

    SILENT = "silent"
    MINIMAL = "minimal"
    NORMAL = "normal"
    VERBOSE = "verbose"


class DataRetention(StrEnum):
    """How long observed data is kept."""

    SESSION_ONLY = "session_only"
    SEVEN_DAYS = "7_days"
    THIRTY_DAYS = "30_days"
    INDEFINITE = "indefinite"


GOVERNANCE_DOMAINS = [
    "communication",
    "code_execution",
    "file_operations",
    "browser_control",
    "desktop_automation",
    "outreach",
    "scheduling",
    "financial",
    "content_publishing",
    "system_administration",
]


@dataclass
class DomainGovernance:
    """Governance settings for a single domain."""

    domain: str
    autonomy: AutonomyLevel = AutonomyLevel.SUGGEST
    requires_approval_above: str = "medium"
    notes: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "domain": self.domain,
            "autonomy": self.autonomy.value,
            "requires_approval_above": self.requires_approval_above,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DomainGovernance:
        return cls(
            domain=d.get("domain", "unknown"),
            autonomy=AutonomyLevel(d.get("autonomy", "suggest")),
            requires_approval_above=d.get("requires_approval_above", "medium"),
            notes=d.get("notes", ""),
        )


_DEFAULT_DOMAIN_AUTONOMY: dict[str, AutonomyLevel] = {
    "communication": AutonomyLevel.ACT_WITH_APPROVAL,
    "code_execution": AutonomyLevel.ACT_WITH_APPROVAL,
    "file_operations": AutonomyLevel.ACT_WITH_APPROVAL,
    "browser_control": AutonomyLevel.SUGGEST,
    "desktop_automation": AutonomyLevel.SUGGEST,
    "outreach": AutonomyLevel.ACT_WITH_APPROVAL,
    "scheduling": AutonomyLevel.SUGGEST,
    "financial": AutonomyLevel.READ_ONLY,
    "content_publishing": AutonomyLevel.ACT_WITH_APPROVAL,
    "system_administration": AutonomyLevel.SUGGEST,
}


@dataclass
class GovernancePreferences:
    """Full configurable governance preferences."""

    global_autonomy: AutonomyLevel = AutonomyLevel.SUGGEST
    notification_frequency: NotificationFrequency = NotificationFrequency.NORMAL
    data_retention: DataRetention = DataRetention.THIRTY_DAYS
    domain_overrides: dict[str, DomainGovernance] = field(default_factory=dict)

    def autonomy_for(self, domain: str) -> AutonomyLevel:
        """Get autonomy level for a domain, falling back to global."""
        override = self.domain_overrides.get(domain)
        if override:
            return override.autonomy
        return _DEFAULT_DOMAIN_AUTONOMY.get(domain, self.global_autonomy)

    def set_domain_autonomy(self, domain: str, level: AutonomyLevel) -> None:
        if domain not in self.domain_overrides:
            self.domain_overrides[domain] = DomainGovernance(domain=domain)
        self.domain_overrides[domain].autonomy = level

    def clear_domain_override(self, domain: str) -> None:
        self.domain_overrides.pop(domain, None)

    def to_dict(self) -> dict:
        return {
            "global_autonomy": self.global_autonomy.value,
            "notification_frequency": self.notification_frequency.value,
            "data_retention": self.data_retention.value,
            "domain_overrides": {k: v.to_dict() for k, v in self.domain_overrides.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> GovernancePreferences:
        overrides = {}
        for k, v in d.get("domain_overrides", {}).items():
            overrides[k] = DomainGovernance.from_dict(v)
        return cls(
            global_autonomy=AutonomyLevel(d.get("global_autonomy", "suggest")),
            notification_frequency=NotificationFrequency(d.get("notification_frequency", "normal")),
            data_retention=DataRetention(d.get("data_retention", "30_days")),
            domain_overrides=overrides,
        )


def load_governance() -> GovernancePreferences:
    """Load governance preferences from disk, or return defaults."""
    if os.path.exists(GOVERNANCE_FILE):
        try:
            with open(GOVERNANCE_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return GovernancePreferences.from_dict(data)
        except Exception as exc:
            logger.debug("Failed to load governance: %s", exc)
    return GovernancePreferences()


def save_governance(prefs: GovernancePreferences) -> None:
    """Save governance preferences to disk."""
    os.makedirs(os.path.dirname(GOVERNANCE_FILE), exist_ok=True)
    try:
        with open(GOVERNANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs.to_dict(), f, indent=2)
    except Exception as exc:
        logger.debug("Failed to save governance: %s", exc)


def show_governance() -> int:
    """Display current governance configuration."""
    prefs = load_governance()
    print()
    print("=" * 50)
    print("  UMH Governance Configuration")
    print("=" * 50)
    print()
    print("  LOCKED (always on, non-configurable):")
    print("    Encryption:     AES-256 at rest, TLS 1.3+ in transit")
    print("    Authentication: OAuth + SSH keys")
    print("    Audit logging:  immutable, cannot be disabled")
    print("    Human supremacy: instant revocation, always in control")
    print()
    print("  CONFIGURABLE (your preferences):")
    print(f"    Global autonomy:  {prefs.global_autonomy.value}")
    print(f"    Notifications:    {prefs.notification_frequency.value}")
    print(f"    Data retention:   {prefs.data_retention.value}")
    print()
    print("  Per-domain autonomy:")
    for domain in GOVERNANCE_DOMAINS:
        level = prefs.autonomy_for(domain)
        override = " *" if domain in prefs.domain_overrides else ""
        print(f"    {domain:<25s} {level.value}{override}")
    if prefs.domain_overrides:
        print()
        print("  (* = custom override, rest = defaults)")
    print("=" * 50)
    print()
    return 0
