"""Phase 84 interface surface contracts — typed surface taxonomy.

Declarative surface definitions for all future UMH interfaces.
No native UI code. No execution. No external calls.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from umh.core.clock import iso_now as _iso_now


class InterfaceSurfaceType(str, Enum):
    COMMAND_CENTER = "command_center"
    DESKTOP_OVERLAY = "desktop_overlay"
    FLOATING_OPERATOR = "floating_operator"
    MINIMIZED_VOICE_WAVE = "minimized_voice_wave"
    GHOST_MODE = "ghost_mode"
    VOICE_INTERFACE = "voice_interface"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    MOBILE_APP = "mobile_app"
    MOBILE_WIDGET = "mobile_widget"
    LIVE_ACTIVITY = "live_activity"
    SHORTCUT = "shortcut"
    BROWSER_EXTENSION = "browser_extension"
    CLI = "cli"
    API = "api"
    DEVELOPER_CONSOLE = "developer_console"
    UNKNOWN = "unknown"


class InterfacePlatform(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    BROWSER = "browser"
    TERMINAL = "terminal"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    UNKNOWN = "unknown"


class InterfaceSurfaceStatus(str, Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    UNSUPPORTED = "unsupported"
    SIMULATED = "simulated"
    FUTURE = "future"
    UNKNOWN = "unknown"


class InterfaceCapability(str, Enum):
    DISPLAY_STATE = "display_state"
    RECEIVE_TEXT = "receive_text"
    RECEIVE_VOICE = "receive_voice"
    SEND_TEXT = "send_text"
    SEND_VOICE = "send_voice"
    SHOW_APPROVALS = "show_approvals"
    REQUEST_APPROVAL = "request_approval"
    SHOW_NOTIFICATIONS = "show_notifications"
    SHOW_TRACES = "show_traces"
    SHOW_DASHBOARD = "show_dashboard"
    DRAG_POSITION = "drag_position"
    EXPAND = "expand"
    MINIMIZE = "minimize"
    HIDE = "hide"
    GHOST = "ghost"
    ALWAYS_ON_TOP = "always_on_top"
    WAKE_LISTEN = "wake_listen"
    PUSH_TO_TALK = "push_to_talk"
    SHORTCUT_TRIGGER = "shortcut_trigger"
    READ_ONLY_QUERY = "read_only_query"
    EXECUTION_INTENT = "execution_intent"
    UNKNOWN = "unknown"


def normalize_surface_type(value: str) -> InterfaceSurfaceType:
    try:
        return InterfaceSurfaceType(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceSurfaceType.UNKNOWN


def normalize_platform(value: str) -> InterfacePlatform:
    try:
        return InterfacePlatform(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfacePlatform.UNKNOWN


def normalize_surface_status(value: str) -> InterfaceSurfaceStatus:
    try:
        return InterfaceSurfaceStatus(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceSurfaceStatus.UNKNOWN


def normalize_interface_capability(value: str) -> InterfaceCapability:
    try:
        return InterfaceCapability(value.lower().strip())
    except (ValueError, AttributeError):
        return InterfaceCapability.UNKNOWN


def _surface_id(name: str) -> str:
    h = hashlib.sha256(name.encode()).hexdigest()[:10]
    return f"srf_{h}"


@dataclass
class InterfaceSurface:
    surface_id: str
    name: str
    surface_type: InterfaceSurfaceType = InterfaceSurfaceType.UNKNOWN
    platform: InterfacePlatform = InterfacePlatform.UNKNOWN
    status: InterfaceSurfaceStatus = InterfaceSurfaceStatus.UNKNOWN
    capabilities: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    authority_scope: str = "read_only"
    default_mode: str = ""
    supports_global_overlay: bool = False
    supports_voice: bool = False
    supports_background_notifications: bool = False
    supports_system_wide_invocation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_id": self.surface_id,
            "name": self.name,
            "surface_type": self.surface_type.value
            if isinstance(self.surface_type, Enum)
            else self.surface_type,
            "platform": self.platform.value if isinstance(self.platform, Enum) else self.platform,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "capabilities": self.capabilities,
            "limitations": self.limitations,
            "authority_scope": self.authority_scope,
            "default_mode": self.default_mode,
            "supports_global_overlay": self.supports_global_overlay,
            "supports_voice": self.supports_voice,
            "supports_background_notifications": self.supports_background_notifications,
            "supports_system_wide_invocation": self.supports_system_wide_invocation,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterfaceSurface:
        return cls(
            surface_id=data.get("surface_id", ""),
            name=data.get("name", ""),
            surface_type=normalize_surface_type(data.get("surface_type", "unknown")),
            platform=normalize_platform(data.get("platform", "unknown")),
            status=normalize_surface_status(data.get("status", "unknown")),
            capabilities=data.get("capabilities", []),
            limitations=data.get("limitations", []),
            authority_scope=data.get("authority_scope", "read_only"),
            default_mode=data.get("default_mode", ""),
            supports_global_overlay=data.get("supports_global_overlay", False),
            supports_voice=data.get("supports_voice", False),
            supports_background_notifications=data.get("supports_background_notifications", False),
            supports_system_wide_invocation=data.get("supports_system_wide_invocation", False),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SurfaceCapabilityMatrix:
    surface_type: str = ""
    platform: str = ""
    capabilities: list[str] = field(default_factory=list)
    unsupported_capabilities: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_type": self.surface_type,
            "platform": self.platform,
            "capabilities": self.capabilities,
            "unsupported_capabilities": self.unsupported_capabilities,
            "limitations": self.limitations,
            "metadata": self.metadata,
        }


def create_interface_surface(
    name: str,
    surface_type: InterfaceSurfaceType = InterfaceSurfaceType.UNKNOWN,
    platform: InterfacePlatform = InterfacePlatform.UNKNOWN,
    status: InterfaceSurfaceStatus = InterfaceSurfaceStatus.UNKNOWN,
    capabilities: list[str] | None = None,
    limitations: list[str] | None = None,
    authority_scope: str = "read_only",
    default_mode: str = "",
    supports_global_overlay: bool = False,
    supports_voice: bool = False,
    supports_background_notifications: bool = False,
    supports_system_wide_invocation: bool = False,
    metadata: dict[str, Any] | None = None,
) -> InterfaceSurface:
    return InterfaceSurface(
        surface_id=_surface_id(name),
        name=name,
        surface_type=surface_type,
        platform=platform,
        status=status,
        capabilities=capabilities or [],
        limitations=limitations or [],
        authority_scope=authority_scope,
        default_mode=default_mode,
        supports_global_overlay=supports_global_overlay,
        supports_voice=supports_voice,
        supports_background_notifications=supports_background_notifications,
        supports_system_wide_invocation=supports_system_wide_invocation,
        metadata=metadata or {},
    )


def build_surface_capability_matrix(surface: InterfaceSurface) -> SurfaceCapabilityMatrix:
    all_caps = [c.value for c in InterfaceCapability if c != InterfaceCapability.UNKNOWN]
    supported = set(surface.capabilities)
    unsupported = [c for c in all_caps if c not in supported]
    return SurfaceCapabilityMatrix(
        surface_type=surface.surface_type.value
        if isinstance(surface.surface_type, Enum)
        else surface.surface_type,
        platform=surface.platform.value if isinstance(surface.platform, Enum) else surface.platform,
        capabilities=surface.capabilities,
        unsupported_capabilities=unsupported,
        limitations=surface.limitations,
    )


def get_default_interface_surfaces() -> list[InterfaceSurface]:
    return [
        create_interface_surface(
            name="Command Center",
            surface_type=InterfaceSurfaceType.COMMAND_CENTER,
            platform=InterfacePlatform.WEB,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
                InterfaceCapability.RECEIVE_TEXT.value,
                InterfaceCapability.SEND_TEXT.value,
                InterfaceCapability.SHOW_APPROVALS.value,
                InterfaceCapability.REQUEST_APPROVAL.value,
                InterfaceCapability.SHOW_NOTIFICATIONS.value,
                InterfaceCapability.SHOW_TRACES.value,
                InterfaceCapability.SHOW_DASHBOARD.value,
                InterfaceCapability.READ_ONLY_QUERY.value,
                InterfaceCapability.EXECUTION_INTENT.value,
            ],
            default_mode="full_screen",
            supports_background_notifications=True,
        ),
        create_interface_surface(
            name="Desktop Overlay",
            surface_type=InterfaceSurfaceType.DESKTOP_OVERLAY,
            platform=InterfacePlatform.UNKNOWN,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
                InterfaceCapability.ALWAYS_ON_TOP.value,
                InterfaceCapability.DRAG_POSITION.value,
                InterfaceCapability.EXPAND.value,
                InterfaceCapability.MINIMIZE.value,
                InterfaceCapability.HIDE.value,
                InterfaceCapability.GHOST.value,
                InterfaceCapability.SHOW_NOTIFICATIONS.value,
            ],
            limitations=["No implementation yet", "OS-specific overlay support varies"],
            default_mode="expanded_overlay",
            supports_global_overlay=True,
        ),
        create_interface_surface(
            name="Floating Operator",
            surface_type=InterfaceSurfaceType.FLOATING_OPERATOR,
            platform=InterfacePlatform.UNKNOWN,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
                InterfaceCapability.DRAG_POSITION.value,
                InterfaceCapability.EXPAND.value,
                InterfaceCapability.MINIMIZE.value,
                InterfaceCapability.HIDE.value,
                InterfaceCapability.SHOW_NOTIFICATIONS.value,
                InterfaceCapability.SHOW_APPROVALS.value,
            ],
            limitations=["No implementation yet"],
            default_mode="expanded_overlay",
        ),
        create_interface_surface(
            name="Minimized Voice Wave",
            surface_type=InterfaceSurfaceType.MINIMIZED_VOICE_WAVE,
            platform=InterfacePlatform.UNKNOWN,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
                InterfaceCapability.MINIMIZE.value,
                InterfaceCapability.EXPAND.value,
            ],
            limitations=["Representational only in Phase 84", "No animation runtime"],
            default_mode="minimized_wave",
        ),
        create_interface_surface(
            name="Ghost Mode",
            surface_type=InterfaceSurfaceType.GHOST_MODE,
            platform=InterfacePlatform.UNKNOWN,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
                InterfaceCapability.GHOST.value,
            ],
            limitations=["Status indicator only"],
            default_mode="ghost",
        ),
        create_interface_surface(
            name="Voice Interface",
            surface_type=InterfaceSurfaceType.VOICE_INTERFACE,
            platform=InterfacePlatform.UNKNOWN,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.RECEIVE_VOICE.value,
                InterfaceCapability.SEND_VOICE.value,
                InterfaceCapability.WAKE_LISTEN.value,
                InterfaceCapability.PUSH_TO_TALK.value,
            ],
            limitations=["No STT/TTS runtime yet"],
            supports_voice=True,
        ),
        create_interface_surface(
            name="Telegram",
            surface_type=InterfaceSurfaceType.TELEGRAM,
            platform=InterfacePlatform.TELEGRAM,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.RECEIVE_TEXT.value,
                InterfaceCapability.SEND_TEXT.value,
                InterfaceCapability.SHOW_NOTIFICATIONS.value,
            ],
            limitations=["No bot implementation in Phase 84"],
            supports_background_notifications=True,
        ),
        create_interface_surface(
            name="Discord",
            surface_type=InterfaceSurfaceType.DISCORD,
            platform=InterfacePlatform.DISCORD,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.RECEIVE_TEXT.value,
                InterfaceCapability.SEND_TEXT.value,
                InterfaceCapability.SHOW_NOTIFICATIONS.value,
            ],
            limitations=["No bot implementation in Phase 84"],
            supports_background_notifications=True,
        ),
        create_interface_surface(
            name="Mobile App",
            surface_type=InterfaceSurfaceType.MOBILE_APP,
            platform=InterfacePlatform.IOS,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
                InterfaceCapability.RECEIVE_TEXT.value,
                InterfaceCapability.SEND_TEXT.value,
                InterfaceCapability.SHOW_NOTIFICATIONS.value,
                InterfaceCapability.SHOW_APPROVALS.value,
                InterfaceCapability.SHOW_DASHBOARD.value,
            ],
            limitations=[
                "No true global overlay on iOS",
                "No Siri replacement",
                "Supports app/shortcuts/widgets/live activities/notifications as future surfaces",
            ],
            supports_background_notifications=True,
        ),
        create_interface_surface(
            name="Mobile Widget",
            surface_type=InterfaceSurfaceType.MOBILE_WIDGET,
            platform=InterfacePlatform.IOS,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
            ],
            limitations=["No true global overlay on iOS", "Widget refresh limits apply"],
        ),
        create_interface_surface(
            name="Live Activity",
            surface_type=InterfaceSurfaceType.LIVE_ACTIVITY,
            platform=InterfacePlatform.IOS,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
            ],
            limitations=["No true global overlay on iOS", "Time-limited by OS"],
        ),
        create_interface_surface(
            name="Shortcut",
            surface_type=InterfaceSurfaceType.SHORTCUT,
            platform=InterfacePlatform.IOS,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.SHORTCUT_TRIGGER.value,
                InterfaceCapability.EXECUTION_INTENT.value,
            ],
            limitations=["No Siri replacement", "Siri Shortcut integration only"],
        ),
        create_interface_surface(
            name="CLI",
            surface_type=InterfaceSurfaceType.CLI,
            platform=InterfacePlatform.TERMINAL,
            status=InterfaceSurfaceStatus.AVAILABLE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
                InterfaceCapability.RECEIVE_TEXT.value,
                InterfaceCapability.SEND_TEXT.value,
                InterfaceCapability.SHOW_DASHBOARD.value,
                InterfaceCapability.SHOW_TRACES.value,
                InterfaceCapability.READ_ONLY_QUERY.value,
                InterfaceCapability.EXECUTION_INTENT.value,
            ],
            default_mode="terminal",
        ),
        create_interface_surface(
            name="API",
            surface_type=InterfaceSurfaceType.API,
            platform=InterfacePlatform.WEB,
            status=InterfaceSurfaceStatus.AVAILABLE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
                InterfaceCapability.RECEIVE_TEXT.value,
                InterfaceCapability.SEND_TEXT.value,
                InterfaceCapability.SHOW_DASHBOARD.value,
                InterfaceCapability.SHOW_TRACES.value,
                InterfaceCapability.SHOW_APPROVALS.value,
                InterfaceCapability.READ_ONLY_QUERY.value,
                InterfaceCapability.EXECUTION_INTENT.value,
            ],
            default_mode="api",
        ),
        create_interface_surface(
            name="Developer Console",
            surface_type=InterfaceSurfaceType.DEVELOPER_CONSOLE,
            platform=InterfacePlatform.TERMINAL,
            status=InterfaceSurfaceStatus.FUTURE,
            capabilities=[
                InterfaceCapability.DISPLAY_STATE.value,
                InterfaceCapability.RECEIVE_TEXT.value,
                InterfaceCapability.SEND_TEXT.value,
                InterfaceCapability.READ_ONLY_QUERY.value,
                InterfaceCapability.EXECUTION_INTENT.value,
            ],
        ),
    ]
