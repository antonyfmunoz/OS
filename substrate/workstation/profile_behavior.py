"""Profile behavior configs — per-profile policies for voice, camera, notifications, apps.

Each ProfileMode maps to a ProfileBehavior that governs how the workstation
operates when that profile is active. Behaviors compose with lifecycle modes:
lifecycle mode sets the risk ceiling, profile mode sets the work context.

Substrate layer. Instance-agnostic.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class VoiceBehavior(str, Enum):
    FULL = "full"
    MINIMAL_INTERRUPTIONS = "minimal_interruptions"
    CRITICAL_ONLY = "critical_only"
    MUTED = "muted"


class NotificationPolicy(str, Enum):
    ALL = "all"
    IMPORTANT_ONLY = "important_only"
    CRITICAL_ONLY = "critical_only"
    SILENT = "silent"


class CameraPolicy(str, Enum):
    LIVE = "live"
    PREVIEW_ONLY = "preview_only"
    OFF = "off"


class ExecutionMode(str, Enum):
    MANUAL = "manual"
    GUIDED = "guided"
    AUTONOMOUS = "autonomous"
    AUTONOMOUS_WITH_APPROVAL = "autonomous_with_approval"


class ReportingCadence(str, Enum):
    HIGH_TOUCH = "high_touch"
    CHECKPOINT_INTERVAL = "checkpoint_interval"
    BLOCKER_OR_COMPLETION = "blocker_or_completion"
    COMPLETION_ONLY = "completion_only"
    SILENT_BACKGROUND = "silent_background"


@dataclass
class ProfileBehavior:
    """Behavior config for a single profile mode."""

    profile_mode: str
    voice_behavior: str = VoiceBehavior.FULL.value
    notification_policy: str = NotificationPolicy.ALL.value
    camera_policy: str = CameraPolicy.OFF.value
    music_policy: str = "allowed"
    default_panels: list[str] = field(default_factory=list)
    agent_policy: str = "continue_approved_loops"
    approval_policy: str = "immediate"
    reporting_cadence: str = ReportingCadence.BLOCKER_OR_COMPLETION.value
    default_execution_mode: str = ExecutionMode.GUIDED.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileBehavior:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


DEFAULT_BEHAVIORS: dict[str, ProfileBehavior] = {
    "developer": ProfileBehavior(
        profile_mode="developer",
        voice_behavior=VoiceBehavior.MINIMAL_INTERRUPTIONS.value,
        notification_policy=NotificationPolicy.IMPORTANT_ONLY.value,
        camera_policy=CameraPolicy.OFF.value,
        music_policy="allowed",
        default_panels=["commandcenter", "editor", "advisor"],
        agent_policy="continue_approved_loops",
        approval_policy="batch_noncritical",
        reporting_cadence=ReportingCadence.BLOCKER_OR_COMPLETION.value,
        default_execution_mode=ExecutionMode.AUTONOMOUS_WITH_APPROVAL.value,
    ),
    "research": ProfileBehavior(
        profile_mode="research",
        voice_behavior=VoiceBehavior.MINIMAL_INTERRUPTIONS.value,
        notification_policy=NotificationPolicy.IMPORTANT_ONLY.value,
        camera_policy=CameraPolicy.OFF.value,
        music_policy="allowed",
        default_panels=["commandcenter", "knowledge", "advisor"],
        agent_policy="continue_approved_loops",
        approval_policy="immediate",
        reporting_cadence=ReportingCadence.CHECKPOINT_INTERVAL.value,
        default_execution_mode=ExecutionMode.GUIDED.value,
    ),
    "music": ProfileBehavior(
        profile_mode="music",
        voice_behavior=VoiceBehavior.MUTED.value,
        notification_policy=NotificationPolicy.SILENT.value,
        camera_policy=CameraPolicy.OFF.value,
        music_policy="active_production",
        default_panels=["advisor"],
        agent_policy="pause_nonessential",
        approval_policy="batch_noncritical",
        reporting_cadence=ReportingCadence.COMPLETION_ONLY.value,
        default_execution_mode=ExecutionMode.MANUAL.value,
    ),
    "design": ProfileBehavior(
        profile_mode="design",
        voice_behavior=VoiceBehavior.MINIMAL_INTERRUPTIONS.value,
        notification_policy=NotificationPolicy.IMPORTANT_ONLY.value,
        camera_policy=CameraPolicy.PREVIEW_ONLY.value,
        music_policy="allowed",
        default_panels=["advisor"],
        agent_policy="continue_approved_loops",
        approval_policy="immediate",
        reporting_cadence=ReportingCadence.HIGH_TOUCH.value,
        default_execution_mode=ExecutionMode.GUIDED.value,
    ),
    "content": ProfileBehavior(
        profile_mode="content",
        voice_behavior=VoiceBehavior.FULL.value,
        notification_policy=NotificationPolicy.IMPORTANT_ONLY.value,
        camera_policy=CameraPolicy.PREVIEW_ONLY.value,
        music_policy="allowed",
        default_panels=["advisor"],
        agent_policy="continue_approved_loops",
        approval_policy="immediate",
        reporting_cadence=ReportingCadence.HIGH_TOUCH.value,
        default_execution_mode=ExecutionMode.GUIDED.value,
    ),
    "command_center": ProfileBehavior(
        profile_mode="command_center",
        voice_behavior=VoiceBehavior.FULL.value,
        notification_policy=NotificationPolicy.ALL.value,
        camera_policy=CameraPolicy.OFF.value,
        music_policy="allowed",
        default_panels=["commandcenter", "approvals", "agents"],
        agent_policy="continue_approved_loops",
        approval_policy="immediate",
        reporting_cadence=ReportingCadence.CHECKPOINT_INTERVAL.value,
        default_execution_mode=ExecutionMode.AUTONOMOUS_WITH_APPROVAL.value,
    ),
    "finance": ProfileBehavior(
        profile_mode="finance",
        voice_behavior=VoiceBehavior.CRITICAL_ONLY.value,
        notification_policy=NotificationPolicy.CRITICAL_ONLY.value,
        camera_policy=CameraPolicy.OFF.value,
        music_policy="allowed",
        default_panels=["commandcenter", "analytics"],
        agent_policy="pause_nonessential",
        approval_policy="immediate",
        reporting_cadence=ReportingCadence.BLOCKER_OR_COMPLETION.value,
        default_execution_mode=ExecutionMode.MANUAL.value,
    ),
    "learning": ProfileBehavior(
        profile_mode="learning",
        voice_behavior=VoiceBehavior.FULL.value,
        notification_policy=NotificationPolicy.SILENT.value,
        camera_policy=CameraPolicy.OFF.value,
        music_policy="allowed",
        default_panels=["knowledge", "advisor"],
        agent_policy="pause_nonessential",
        approval_policy="batch_noncritical",
        reporting_cadence=ReportingCadence.COMPLETION_ONLY.value,
        default_execution_mode=ExecutionMode.MANUAL.value,
    ),
}


def get_behavior(profile_mode: str) -> ProfileBehavior:
    """Get the behavior config for a profile mode, with fallback."""
    return DEFAULT_BEHAVIORS.get(
        profile_mode,
        ProfileBehavior(profile_mode=profile_mode),
    )


def get_notification_policy_for_lifecycle(lifecycle_mode: str) -> str:
    """Override notification policy based on lifecycle mode.

    Lifecycle mode can further restrict notifications beyond what
    the profile allows. Returns the most restrictive policy.
    """
    lifecycle_overrides: dict[str, str] = {
        "night_cycle": NotificationPolicy.CRITICAL_ONLY.value,
        "overnight": NotificationPolicy.SILENT.value,
        "away": NotificationPolicy.CRITICAL_ONLY.value,
        "end_of_workday": NotificationPolicy.IMPORTANT_ONLY.value,
        "emergency": NotificationPolicy.ALL.value,
    }
    return lifecycle_overrides.get(lifecycle_mode, "")


_POLICY_RANK = {
    NotificationPolicy.SILENT.value: 0,
    NotificationPolicy.CRITICAL_ONLY.value: 1,
    NotificationPolicy.IMPORTANT_ONLY.value: 2,
    NotificationPolicy.ALL.value: 3,
}


def resolve_effective_notification_policy(
    profile_mode: str,
    lifecycle_mode: str,
) -> str:
    """Resolve the effective notification policy by composing profile + lifecycle.

    Returns the more restrictive of the two policies.
    """
    behavior = get_behavior(profile_mode)
    profile_policy = behavior.notification_policy
    lifecycle_policy = get_notification_policy_for_lifecycle(lifecycle_mode)

    if not lifecycle_policy:
        return profile_policy

    profile_rank = _POLICY_RANK.get(profile_policy, 3)
    lifecycle_rank = _POLICY_RANK.get(lifecycle_policy, 3)
    return profile_policy if profile_rank <= lifecycle_rank else lifecycle_policy
