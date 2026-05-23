"""Actuator Backend Registry v1.

Tracks available actuator backends and selects the best one for a
given actuation request. The registry does not execute — it selects.
Execution is delegated to the backend itself.

UMH substrate subsystem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BackendCapability(str, Enum):
    CHROME_LAUNCH = "chrome_launch"
    WINDOW_FOCUS = "window_focus"
    HWND_OBSERVATION = "hwnd_observation"
    SCREENSHOT_CAPTURE = "screenshot_capture"
    BROWSER_NAVIGATION = "browser_navigation"
    FOREGROUND_DETECTION = "foreground_detection"
    PROCESS_DETECTION = "process_detection"


class BackendEnvironment(str, Enum):
    NATIVE_WINDOWS = "native_windows"
    WSL = "wsl"
    VPS_LINUX = "vps_linux"


@dataclass(frozen=True)
class ActuatorBackendEntry:
    """A registered actuator backend."""

    backend_id: str
    display_name: str
    technology: str
    environments: frozenset[BackendEnvironment]
    capabilities: frozenset[BackendCapability]
    install_difficulty: str
    integration_hours: float
    security_risk: str
    requires_display_session: bool
    python_support: bool
    recommended_use: str
    notes: str = ""

    def supports(self, cap: BackendCapability) -> bool:
        return cap in self.capabilities

    def runs_in(self, env: BackendEnvironment) -> bool:
        return env in self.environments

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id,
            "display_name": self.display_name,
            "technology": self.technology,
            "environments": sorted(e.value for e in self.environments),
            "capabilities": sorted(c.value for c in self.capabilities),
            "install_difficulty": self.install_difficulty,
            "integration_hours": self.integration_hours,
            "security_risk": self.security_risk,
            "requires_display_session": self.requires_display_session,
            "python_support": self.python_support,
            "recommended_use": self.recommended_use,
            "notes": self.notes,
        }


REGISTERED_BACKENDS: tuple[ActuatorBackendEntry, ...] = (
    ActuatorBackendEntry(
        backend_id="windows_interactive_desktop_relay",
        display_name="Windows Interactive Desktop Relay (PowerShell)",
        technology="Win32 P/Invoke via PowerShell + System.Drawing",
        environments=frozenset({BackendEnvironment.NATIVE_WINDOWS}),
        capabilities=frozenset(
            {
                BackendCapability.CHROME_LAUNCH,
                BackendCapability.WINDOW_FOCUS,
                BackendCapability.HWND_OBSERVATION,
                BackendCapability.SCREENSHOT_CAPTURE,
                BackendCapability.BROWSER_NAVIGATION,
                BackendCapability.FOREGROUND_DETECTION,
                BackendCapability.PROCESS_DETECTION,
            }
        ),
        install_difficulty="zero — already deployed",
        integration_hours=0,
        security_risk="low",
        requires_display_session=True,
        python_support=False,
        recommended_use="Primary actuator backend. Already proven in production.",
        notes="Uses Start-Process for Chrome, Get-Process for HWND, "
        "GetForegroundWindow for focus, System.Drawing for screenshots.",
    ),
    ActuatorBackendEntry(
        backend_id="playwright_cdp",
        display_name="Playwright (CDP browser automation)",
        technology="Chromium DevTools Protocol",
        environments=frozenset({BackendEnvironment.NATIVE_WINDOWS, BackendEnvironment.WSL}),
        capabilities=frozenset(
            {
                BackendCapability.BROWSER_NAVIGATION,
                BackendCapability.SCREENSHOT_CAPTURE,
            }
        ),
        install_difficulty="low — pip install playwright",
        integration_hours=2,
        security_risk="low",
        requires_display_session=False,
        python_support=True,
        recommended_use="Browser-internal automation when HWND not needed. "
        "Cannot observe window focus or desktop state.",
        notes="Browser-only. No HWND, no desktop screenshot, no focus detection.",
    ),
    ActuatorBackendEntry(
        backend_id="pyautogui",
        display_name="PyAutoGUI",
        technology="Cross-platform mouse/keyboard/screenshot",
        environments=frozenset({BackendEnvironment.NATIVE_WINDOWS}),
        capabilities=frozenset(
            {
                BackendCapability.SCREENSHOT_CAPTURE,
                BackendCapability.PROCESS_DETECTION,
            }
        ),
        install_difficulty="low — pip install pyautogui",
        integration_hours=2,
        security_risk="medium",
        requires_display_session=True,
        python_support=True,
        recommended_use="Desktop screenshot fallback. Cannot reliably navigate Chrome.",
        notes="Fragile for browser navigation (address bar focus race). "
        "No HWND support. No foreground detection.",
    ),
    ActuatorBackendEntry(
        backend_id="win32_api",
        display_name="Win32 APIs (pywin32/ctypes)",
        technology="Windows API via Python bindings",
        environments=frozenset({BackendEnvironment.NATIVE_WINDOWS}),
        capabilities=frozenset(
            {
                BackendCapability.CHROME_LAUNCH,
                BackendCapability.WINDOW_FOCUS,
                BackendCapability.HWND_OBSERVATION,
                BackendCapability.FOREGROUND_DETECTION,
                BackendCapability.PROCESS_DETECTION,
            }
        ),
        install_difficulty="low — pip install pywin32",
        integration_hours=3,
        security_risk="low",
        requires_display_session=True,
        python_support=True,
        recommended_use="Window management when Python is preferred over PowerShell.",
        notes="No browser navigation. No screenshot without additional libs.",
    ),
    ActuatorBackendEntry(
        backend_id="ui_automation",
        display_name="Windows UI Automation",
        technology="Microsoft accessibility framework",
        environments=frozenset({BackendEnvironment.NATIVE_WINDOWS}),
        capabilities=frozenset(
            {
                BackendCapability.HWND_OBSERVATION,
                BackendCapability.FOREGROUND_DETECTION,
                BackendCapability.PROCESS_DETECTION,
            }
        ),
        install_difficulty="medium — pip install uiautomation",
        integration_hours=4,
        security_risk="low",
        requires_display_session=True,
        python_support=True,
        recommended_use="UI element inspection for non-browser desktop apps.",
        notes="No screenshot. No browser navigation. Overkill for Chrome proof.",
    ),
    ActuatorBackendEntry(
        backend_id="ui_tars_desktop",
        display_name="UI-TARS Desktop (ByteDance)",
        technology="Vision-model agent with Electron wrapper",
        environments=frozenset({BackendEnvironment.NATIVE_WINDOWS}),
        capabilities=frozenset(
            {
                BackendCapability.CHROME_LAUNCH,
                BackendCapability.BROWSER_NAVIGATION,
                BackendCapability.SCREENSHOT_CAPTURE,
            }
        ),
        install_difficulty="high — model download 7GB+, Node, Electron",
        integration_hours=12,
        security_risk="high",
        requires_display_session=True,
        python_support=False,
        recommended_use="Not recommended for deterministic proof. Non-deterministic vision agent.",
        notes="Research-grade. No stable CLI. Non-deterministic actions.",
    ),
)


class ActuatorBackendRegistry:
    """Registry of available actuator backends."""

    def __init__(
        self,
        entries: tuple[ActuatorBackendEntry, ...] = REGISTERED_BACKENDS,
    ) -> None:
        self._entries = {e.backend_id: e for e in entries}

    def get(self, backend_id: str) -> ActuatorBackendEntry | None:
        return self._entries.get(backend_id)

    def select_for_proof(
        self,
        required_capabilities: set[BackendCapability] | None = None,
        environment: BackendEnvironment = BackendEnvironment.NATIVE_WINDOWS,
    ) -> ActuatorBackendEntry | None:
        """Select the best backend for producing a real actuation proof."""
        if required_capabilities is None:
            required_capabilities = {
                BackendCapability.CHROME_LAUNCH,
                BackendCapability.HWND_OBSERVATION,
                BackendCapability.SCREENSHOT_CAPTURE,
                BackendCapability.FOREGROUND_DETECTION,
            }

        candidates = [
            e
            for e in self._entries.values()
            if e.runs_in(environment) and all(e.supports(c) for c in required_capabilities)
        ]

        if not candidates:
            return None

        candidates.sort(key=lambda e: e.integration_hours)
        return candidates[0]

    @property
    def available_backends(self) -> list[str]:
        return sorted(self._entries.keys())

    def to_dict(self) -> dict[str, Any]:
        return {bid: e.to_dict() for bid, e in sorted(self._entries.items())}


_GLOBAL_BACKEND_REGISTRY: ActuatorBackendRegistry | None = None


def get_backend_registry() -> ActuatorBackendRegistry:
    """Get the singleton backend registry."""
    global _GLOBAL_BACKEND_REGISTRY
    if _GLOBAL_BACKEND_REGISTRY is None:
        _GLOBAL_BACKEND_REGISTRY = ActuatorBackendRegistry()
    return _GLOBAL_BACKEND_REGISTRY
