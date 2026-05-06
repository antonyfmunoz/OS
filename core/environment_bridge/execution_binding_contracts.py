"""Execution Binding Contracts for the Environment Bridge.

Typed contracts that explicitly model and validate the 6-layer
execution stack:

  1. Environment      — where execution happens (Windows desktop)
  2. Execution Surface — what runs commands (PowerShell, WSL, tmux)
  3. Application       — what program is used (Chrome)
  4. Target Service    — what service is accessed (Google Drive/Docs)
  5. Capability        — what action is performed (open URL, read inventory)
  6. Proof             — what evidence is required (founder confirmation)

UMH must bind all layers explicitly before execution. Collapsing
layers into a single "backend" is architecturally invalid.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enums ────────────────────────────────────────────────────────────────────


class EnvironmentType(str, Enum):
    WINDOWS_DESKTOP = "windows_desktop"
    LINUX_SERVER = "linux_server"
    MACOS_DESKTOP = "macos_desktop"
    WSL = "wsl"


class ExecutionSurfaceType(str, Enum):
    POWERSHELL = "powershell"
    WSL = "wsl"
    TMUX = "tmux"
    CMD = "cmd"
    BASH = "bash"


class ExecutionSurfaceRole(str, Enum):
    RELAY = "relay"
    ORCHESTRATOR = "orchestrator"
    GUI_ACTUATOR = "gui_actuator"


class ApplicationLaunchMethod(str, Enum):
    DIRECT_EXECUTABLE = "direct_executable"
    EXPLORER_URL = "explorer_url"
    DEFAULT_BROWSER = "default_browser"
    SHELL_URL_OPEN = "shell_url_open"
    GENERIC_START_URL = "generic_start_url"
    UNKNOWN_BROWSER = "unknown_browser"


class TargetServiceFamily(str, Enum):
    GOOGLE_WORKSPACE = "google_workspace"
    MICROSOFT_365 = "microsoft_365"
    LOCAL_FILESYSTEM = "local_filesystem"
    CUSTOM_WEB_APP = "custom_web_app"


class CapabilityMutability(str, Enum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    DESTRUCTIVE = "destructive"


class ProofLevel(str, Enum):
    NONE = "none"
    AUTOMATED = "automated"
    FOUNDER_VISUAL_CONFIRMATION = "founder_visual_confirmation"
    TRUSTED_DESKTOP_ADAPTER = "trusted_desktop_adapter"


class EvidenceType(str, Enum):
    PROCESS_EXISTS_ONLY = "process_exists_only"
    WINDOW_METADATA_ONLY = "window_metadata_only"
    FOUNDER_VISUAL_CONFIRMATION = "founder_visual_confirmation"
    DESKTOP_ADAPTER_FOREGROUND_CHECK = "desktop_adapter_foreground_check"
    API_RESPONSE = "api_response"


DISALLOWED_CHROME_LAUNCH_METHODS = frozenset(
    {
        ApplicationLaunchMethod.EXPLORER_URL,
        ApplicationLaunchMethod.DEFAULT_BROWSER,
        ApplicationLaunchMethod.SHELL_URL_OPEN,
        ApplicationLaunchMethod.GENERIC_START_URL,
        ApplicationLaunchMethod.UNKNOWN_BROWSER,
    }
)

WSL_TMUX_SURFACE_TYPES = frozenset(
    {
        ExecutionSurfaceType.WSL,
        ExecutionSurfaceType.TMUX,
    }
)

GUI_ACTUATOR_SURFACE_TYPES = frozenset(
    {
        ExecutionSurfaceType.POWERSHELL,
    }
)


# ── Binding Dataclasses ──────────────────────────────────────────────────────


@dataclass
class EnvironmentBinding:
    environment_id: str = ""
    environment_type: str = ""
    environment_authority: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            "environment_type": self.environment_type,
            "environment_authority": self.environment_authority,
        }


@dataclass
class ExecutionSurfaceBinding:
    execution_surface_id: str = ""
    execution_surface_type: str = ""
    execution_surface_role: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_surface_id": self.execution_surface_id,
            "execution_surface_type": self.execution_surface_type,
            "execution_surface_role": self.execution_surface_role,
        }


@dataclass
class ApplicationBinding:
    application_id: str = ""
    application_name: str = ""
    executable_path: str = ""
    wsl_executable_path: str = ""
    launch_method: str = ""
    disallowed_launch_methods: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "application_name": self.application_name,
            "executable_path": self.executable_path,
            "wsl_executable_path": self.wsl_executable_path,
            "launch_method": self.launch_method,
            "disallowed_launch_methods": self.disallowed_launch_methods,
        }


@dataclass
class TargetServiceBinding:
    target_service_id: str = ""
    target_service_family: str = ""
    service_url: str = ""
    service_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_service_id": self.target_service_id,
            "target_service_family": self.target_service_family,
            "service_url": self.service_url,
            "service_capabilities": self.service_capabilities,
        }


@dataclass
class CapabilityBinding:
    capability_id: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    authority_required: str = ""
    mutability: str = CapabilityMutability.READ_ONLY.value
    proof_required: bool = True
    adapter_package_required: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "authority_required": self.authority_required,
            "mutability": self.mutability,
            "proof_required": self.proof_required,
            "adapter_package_required": self.adapter_package_required,
        }


@dataclass
class ProofBinding:
    proof_level_required: str = ""
    proof_source: str = ""
    founder_confirmation_required: bool = False
    allowed_evidence: list[str] = field(default_factory=list)
    blocked_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proof_level_required": self.proof_level_required,
            "proof_source": self.proof_source,
            "founder_confirmation_required": self.founder_confirmation_required,
            "allowed_evidence": self.allowed_evidence,
            "blocked_evidence": self.blocked_evidence,
        }


@dataclass
class ExecutionBinding:
    environment: EnvironmentBinding = field(default_factory=EnvironmentBinding)
    execution_surfaces: list[ExecutionSurfaceBinding] = field(default_factory=list)
    application: ApplicationBinding = field(default_factory=ApplicationBinding)
    target_services: list[TargetServiceBinding] = field(default_factory=list)
    capabilities: list[CapabilityBinding] = field(default_factory=list)
    proof: ProofBinding = field(default_factory=ProofBinding)

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment.to_dict(),
            "execution_surfaces": [s.to_dict() for s in self.execution_surfaces],
            "application": self.application.to_dict(),
            "target_services": [s.to_dict() for s in self.target_services],
            "capabilities": [c.to_dict() for c in self.capabilities],
            "proof": self.proof.to_dict(),
        }


# ── Preset: W0 Chrome Google Workspace Binding ──────────────────────────────


def build_w0_chrome_gws_binding() -> ExecutionBinding:
    """Build the standard W0 execution binding for Chrome + Google Workspace."""
    return ExecutionBinding(
        environment=EnvironmentBinding(
            environment_id="local_windows_desktop",
            environment_type=EnvironmentType.WINDOWS_DESKTOP.value,
            environment_authority="interactive_user_session_required",
        ),
        execution_surfaces=[
            ExecutionSurfaceBinding(
                execution_surface_id="wsl_tmux_worker",
                execution_surface_type=ExecutionSurfaceType.TMUX.value,
                execution_surface_role=ExecutionSurfaceRole.ORCHESTRATOR.value,
            ),
            ExecutionSurfaceBinding(
                execution_surface_id="windows_powershell_relay",
                execution_surface_type=ExecutionSurfaceType.POWERSHELL.value,
                execution_surface_role=ExecutionSurfaceRole.GUI_ACTUATOR.value,
            ),
        ],
        application=ApplicationBinding(
            application_id="google_chrome_windows",
            application_name="Google Chrome",
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            wsl_executable_path="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
            launch_method=ApplicationLaunchMethod.DIRECT_EXECUTABLE.value,
            disallowed_launch_methods=[m.value for m in DISALLOWED_CHROME_LAUNCH_METHODS],
        ),
        target_services=[
            TargetServiceBinding(
                target_service_id="google_drive",
                target_service_family=TargetServiceFamily.GOOGLE_WORKSPACE.value,
                service_url="https://drive.google.com/drive/my-drive",
                service_capabilities=[
                    "drive_open_my_drive",
                    "drive_read_file_inventory",
                ],
            ),
            TargetServiceBinding(
                target_service_id="google_docs",
                target_service_family=TargetServiceFamily.GOOGLE_WORKSPACE.value,
                service_url="",
                service_capabilities=[
                    "docs_open_document",
                    "docs_detect_tabs",
                    "docs_extract_tab_content",
                ],
            ),
        ],
        capabilities=[
            CapabilityBinding(
                capability_id="browser.open_url_in_application",
                inputs=["url", "application_id"],
                outputs=["browser_window_visible"],
                authority_required="interactive_user_session_required",
                mutability=CapabilityMutability.READ_ONLY.value,
                proof_required=True,
                adapter_package_required="W-GWS-CORE-001",
            ),
            CapabilityBinding(
                capability_id="google_drive.read_file_inventory",
                inputs=["drive_url", "account_id"],
                outputs=["drive_inventory_result"],
                authority_required="interactive_user_session_required",
                mutability=CapabilityMutability.READ_ONLY.value,
                proof_required=True,
                adapter_package_required="W-GDRIVE-CU-001",
            ),
            CapabilityBinding(
                capability_id="google_docs.extract_tabs",
                inputs=["docs_url", "account_id"],
                outputs=["docs_tab_detection_result", "docs_content_extraction_result"],
                authority_required="interactive_user_session_required",
                mutability=CapabilityMutability.READ_ONLY.value,
                proof_required=True,
                adapter_package_required="W-GDOCS-CU-001",
            ),
        ],
        proof=ProofBinding(
            proof_level_required=ProofLevel.FOUNDER_VISUAL_CONFIRMATION.value,
            proof_source="founder",
            founder_confirmation_required=True,
            allowed_evidence=[
                EvidenceType.FOUNDER_VISUAL_CONFIRMATION.value,
                EvidenceType.DESKTOP_ADAPTER_FOREGROUND_CHECK.value,
            ],
            blocked_evidence=[
                EvidenceType.PROCESS_EXISTS_ONLY.value,
                EvidenceType.WINDOW_METADATA_ONLY.value,
            ],
        ),
    )
