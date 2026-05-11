"""
Interface projection contracts for Phase 94D.3.

Additive-only module. Defines the contract for interface projections —
UI/channel-specific representations of the central advisor session.

Does not import from or modify any existing substrate module.
Does not implement any interface adapter — only contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class InterfaceType(str, Enum):
    CLI = "cli"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    MOBILE_APP = "mobile_app"
    WORKSTATION_UI = "workstation_ui"
    VOICE = "voice"
    BROWSER_OVERLAY = "browser_overlay"
    WEB_DASHBOARD = "web_dashboard"


class ApprovalMode(str, Enum):
    TEXT_PROMPT = "text_prompt"
    BUTTON = "button"
    INLINE_KEYBOARD = "inline_keyboard"
    MODAL = "modal"
    VOICE_CONFIRM = "voice_confirm"
    NONE = "none"


class InterfaceCapability(str, Enum):
    TEXT_INPUT = "text_input"
    TEXT_OUTPUT = "text_output"
    COMMAND_INPUT = "command_input"
    BUTTON_INPUT = "button_input"
    TAP_INPUT = "tap_input"
    VOICE_INPUT = "voice_input"
    HOTKEY_INPUT = "hotkey_input"
    GESTURE_INPUT = "gesture_input"
    FORM_INPUT = "form_input"
    EMBED_OUTPUT = "embed_output"
    NOTIFICATION_OUTPUT = "notification_output"
    AUDIO_OUTPUT = "audio_output"
    PANEL_OUTPUT = "panel_output"
    OVERLAY_OUTPUT = "overlay_output"
    CHART_OUTPUT = "chart_output"
    TABLE_OUTPUT = "table_output"
    VIDEO_FEED_OUTPUT = "video_feed_output"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    LOG_STREAMING = "log_streaming"
    LIVE_STATE = "live_state"
    COMPUTER_USE_OBSERVATION = "computer_use_observation"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class InterfaceProjection:
    interface_id: str
    interface_type: InterfaceType
    capabilities: set[InterfaceCapability]
    limitations: list[str]
    input_modalities: list[str]
    output_modalities: list[str]
    authentication: str
    supported_message_types: set[str]
    approval_mode: ApprovalMode
    file_support: bool
    evidence_support: bool
    realtime_support: bool
    fallback_behavior: str
    connected: bool = False
    last_activity: str = field(default_factory=_now_iso)

    def can_handle_approval(self) -> bool:
        return self.approval_mode != ApprovalMode.NONE

    def can_handle_files(self) -> bool:
        return self.file_support

    def can_observe_computer_use(self) -> bool:
        return InterfaceCapability.COMPUTER_USE_OBSERVATION in self.capabilities

    def to_dict(self) -> dict[str, Any]:
        return {
            "interface_id": self.interface_id,
            "interface_type": self.interface_type.value,
            "capabilities": sorted(c.value for c in self.capabilities),
            "limitations": self.limitations,
            "input_modalities": self.input_modalities,
            "output_modalities": self.output_modalities,
            "authentication": self.authentication,
            "supported_message_types": sorted(self.supported_message_types),
            "approval_mode": self.approval_mode.value,
            "file_support": self.file_support,
            "evidence_support": self.evidence_support,
            "realtime_support": self.realtime_support,
            "fallback_behavior": self.fallback_behavior,
            "connected": self.connected,
            "last_activity": self.last_activity,
        }


# Pre-built declarations for known interfaces

CLI_VPS = InterfaceProjection(
    interface_id="cli_vps_main",
    interface_type=InterfaceType.CLI,
    capabilities={
        InterfaceCapability.TEXT_INPUT,
        InterfaceCapability.TEXT_OUTPUT,
        InterfaceCapability.COMMAND_INPUT,
        InterfaceCapability.LOG_STREAMING,
    },
    limitations=["no buttons", "no rich media inline", "no push notifications"],
    input_modalities=["text", "command"],
    output_modalities=["text"],
    authentication="ssh_key",
    supported_message_types=set(),  # all types supported via text rendering
    approval_mode=ApprovalMode.TEXT_PROMPT,
    file_support=True,
    evidence_support=False,
    realtime_support=True,
    fallback_behavior="render as plain text",
)

DISCORD_CHANNEL = InterfaceProjection(
    interface_id="discord_eos_channel",
    interface_type=InterfaceType.DISCORD,
    capabilities={
        InterfaceCapability.TEXT_INPUT,
        InterfaceCapability.TEXT_OUTPUT,
        InterfaceCapability.BUTTON_INPUT,
        InterfaceCapability.EMBED_OUTPUT,
        InterfaceCapability.FILE_UPLOAD,
        InterfaceCapability.FILE_DOWNLOAD,
    },
    limitations=["2000 char message limit", "no terminal streaming", "async delivery"],
    input_modalities=["text", "button", "reaction"],
    output_modalities=["text", "embed", "button", "file"],
    authentication="discord_user_id",
    supported_message_types=set(),
    approval_mode=ApprovalMode.BUTTON,
    file_support=True,
    evidence_support=True,
    realtime_support=True,
    fallback_behavior="queue and deliver on next interaction",
)

WORKSTATION_JARVIS = InterfaceProjection(
    interface_id="workstation_jarvis",
    interface_type=InterfaceType.WORKSTATION_UI,
    capabilities={
        InterfaceCapability.TEXT_INPUT,
        InterfaceCapability.TEXT_OUTPUT,
        InterfaceCapability.VOICE_INPUT,
        InterfaceCapability.AUDIO_OUTPUT,
        InterfaceCapability.PANEL_OUTPUT,
        InterfaceCapability.LIVE_STATE,
        InterfaceCapability.COMPUTER_USE_OBSERVATION,
        InterfaceCapability.HOTKEY_INPUT,
        InterfaceCapability.VIDEO_FEED_OUTPUT,
    },
    limitations=["local PC only", "requires desktop application running"],
    input_modalities=["text", "hotkey", "voice", "gesture"],
    output_modalities=["text", "panel", "audio", "video_feed", "overlay"],
    authentication="tailscale_identity",
    supported_message_types=set(),
    approval_mode=ApprovalMode.MODAL,
    file_support=True,
    evidence_support=True,
    realtime_support=True,
    fallback_behavior="spoken summary if panels unavailable",
)
