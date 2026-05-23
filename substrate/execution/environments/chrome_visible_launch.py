"""Chrome visible launch gate for the Environment Bridge.

Evaluates Chrome launch attempts for W0-001 CU execution. Process
existence and window metadata (MainWindowHandle, MainWindowTitle) are
recorded as evidence but are NOT sufficient proof of visible GUI.

WSL/tmux execution can spawn Windows processes without reliable
foreground visibility. Only founder visual confirmation constitutes
proof that Chrome is visibly open.

explorer.exe / default-browser routing is explicitly disallowed for
governed W0-001 CU execution.

UMH substrate subsystem. EOS is one platform consumer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChromeLaunchMethod(str, Enum):
    DIRECT_EXECUTABLE = "direct_executable"
    EXPLORER_DEFAULT = "explorer_default"
    WSL_INTEROP = "wsl_interop"
    POWERSHELL_START = "powershell_start"
    UNKNOWN = "unknown"


class MetadataEvidence(str, Enum):
    """What process/window metadata was observed. Evidence only — not proof."""

    NONE = "none"
    PROCESS_DETECTED_ONLY = "process_detected_only"
    WINDOW_METADATA_DETECTED = "window_metadata_detected"


class ChromeVisibleLaunchStatus(str, Enum):
    PENDING_FOUNDER_VISUAL_CONFIRMATION = "pending_founder_visual_confirmation"
    FOUNDER_CONFIRMED_VISIBLE = "founder_confirmed_visible"
    FOUNDER_DENIED_VISIBLE = "founder_denied_visible"
    CHROME_NOT_FOUND = "chrome_not_found"
    LAUNCH_METHOD_DISALLOWED = "launch_method_disallowed"
    VISIBLE_CHROME_LAUNCH_FAILED = "visible_chrome_launch_failed"
    NOT_ATTEMPTED = "not_attempted"


CHROME_EXECUTABLE_PATHS_WINDOWS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

CHROME_EXECUTABLE_PATHS_WSL = [
    "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
    "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
]

DISALLOWED_LAUNCH_METHODS = frozenset(
    {
        ChromeLaunchMethod.EXPLORER_DEFAULT,
    }
)


@dataclass
class ChromeProcessSnapshot:
    pid: int = 0
    process_name: str = ""
    main_window_handle: int = 0
    main_window_title: str = ""
    executable_path: str = ""


@dataclass
class ChromeVisibleLaunchProof:
    launch_method: str = ""
    executable_path: str = ""
    requested_url: str = ""
    process_ids: list[int] = field(default_factory=list)
    main_window_handle_values: list[int] = field(default_factory=list)
    main_window_titles: list[str] = field(default_factory=list)
    metadata_evidence: str = MetadataEvidence.NONE.value
    founder_visual_confirmation_required: bool = True
    founder_visual_confirmation_received: bool = False
    founder_confirmed: bool = False
    status: ChromeVisibleLaunchStatus = ChromeVisibleLaunchStatus.NOT_ATTEMPTED
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "launch_method": self.launch_method,
            "executable_path": self.executable_path,
            "requested_url": self.requested_url,
            "process_ids": self.process_ids,
            "main_window_handle_values": self.main_window_handle_values,
            "main_window_titles": self.main_window_titles,
            "metadata_evidence": self.metadata_evidence,
            "founder_visual_confirmation_required": self.founder_visual_confirmation_required,
            "founder_visual_confirmation_received": self.founder_visual_confirmation_received,
            "founder_confirmed": self.founder_confirmed,
            "status": self.status.value,
            "notes": self.notes,
        }


def required_chrome_executable_paths() -> list[str]:
    return CHROME_EXECUTABLE_PATHS_WINDOWS + CHROME_EXECUTABLE_PATHS_WSL


def is_allowed_chrome_launch_method(
    method: ChromeLaunchMethod,
    executable_path: str = "",
) -> bool:
    if method in DISALLOWED_LAUNCH_METHODS:
        return False
    if method == ChromeLaunchMethod.DIRECT_EXECUTABLE:
        all_paths = required_chrome_executable_paths()
        normalized = executable_path.replace("\\", "/").lower()
        return any(p.replace("\\", "/").lower() == normalized for p in all_paths)
    if method == ChromeLaunchMethod.WSL_INTEROP:
        normalized = executable_path.replace("\\", "/").lower()
        return any(p.replace("\\", "/").lower() == normalized for p in CHROME_EXECUTABLE_PATHS_WSL)
    return False


def build_chrome_launch_command(
    url: str,
    executable_path: str | None = None,
) -> str:
    if executable_path is None:
        executable_path = CHROME_EXECUTABLE_PATHS_WSL[0]
    return f'"{executable_path}" --new-window "{url}"'


def parse_chrome_process_snapshot(
    snapshot: dict[str, Any],
) -> ChromeProcessSnapshot:
    return ChromeProcessSnapshot(
        pid=snapshot.get("pid", 0),
        process_name=snapshot.get("process_name", ""),
        main_window_handle=snapshot.get("main_window_handle", 0),
        main_window_title=snapshot.get("main_window_title", ""),
        executable_path=snapshot.get("executable_path", ""),
    )


def classify_metadata_evidence(
    processes: list[ChromeProcessSnapshot],
) -> MetadataEvidence:
    """Classify process/window metadata as evidence level. NOT proof."""
    if not processes:
        return MetadataEvidence.NONE
    for proc in processes:
        if proc.main_window_handle != 0 or proc.main_window_title.strip():
            return MetadataEvidence.WINDOW_METADATA_DETECTED
    return MetadataEvidence.PROCESS_DETECTED_ONLY


def evaluate_visible_chrome_launch(
    launch_method: ChromeLaunchMethod,
    executable_path: str,
    requested_url: str,
    processes: list[ChromeProcessSnapshot],
) -> ChromeVisibleLaunchProof:
    """Evaluate Chrome launch attempt. Always requires founder visual confirmation."""
    proof = ChromeVisibleLaunchProof(
        launch_method=launch_method.value,
        executable_path=executable_path,
        requested_url=requested_url,
        process_ids=[p.pid for p in processes],
        main_window_handle_values=[p.main_window_handle for p in processes],
        main_window_titles=[p.main_window_title for p in processes if p.main_window_title],
    )

    if not is_allowed_chrome_launch_method(launch_method, executable_path):
        proof.status = ChromeVisibleLaunchStatus.LAUNCH_METHOD_DISALLOWED
        proof.founder_visual_confirmation_required = False
        proof.notes.append(
            f"Launch method {launch_method.value} with path {executable_path} is not allowed"
        )
        return proof

    if not processes:
        proof.status = ChromeVisibleLaunchStatus.CHROME_NOT_FOUND
        proof.metadata_evidence = MetadataEvidence.NONE.value
        proof.notes.append("No Chrome processes found after launch attempt")
        return proof

    evidence = classify_metadata_evidence(processes)
    proof.metadata_evidence = evidence.value
    proof.status = ChromeVisibleLaunchStatus.PENDING_FOUNDER_VISUAL_CONFIRMATION
    proof.founder_visual_confirmation_required = True

    if evidence == MetadataEvidence.WINDOW_METADATA_DETECTED:
        proof.notes.append(
            "Window metadata detected (MainWindowHandle/Title nonzero). "
            "This is evidence only — NOT proof of visible GUI. "
            "Founder visual confirmation required."
        )
    else:
        proof.notes.append(
            "Chrome processes detected but no window metadata. "
            "Founder visual confirmation required."
        )

    return proof


def apply_founder_visual_confirmation(
    proof: ChromeVisibleLaunchProof,
    confirmed: bool,
    notes: str = "",
) -> ChromeVisibleLaunchProof:
    """Apply founder's visual confirmation to the launch proof."""
    proof.founder_visual_confirmation_received = True
    proof.founder_confirmed = confirmed
    if confirmed:
        proof.status = ChromeVisibleLaunchStatus.FOUNDER_CONFIRMED_VISIBLE
        proof.notes.append("Founder confirmed Chrome is visibly open")
    else:
        proof.status = ChromeVisibleLaunchStatus.FOUNDER_DENIED_VISIBLE
        proof.notes.append("Founder confirmed Chrome is NOT visibly open")
    if notes:
        proof.notes.append(f"Founder notes: {notes}")
    return proof


def parse_founder_visual_confirmation(
    data: dict[str, Any],
) -> tuple[bool, bool, str]:
    """Parse a founder visual confirmation response.

    Returns (is_valid, confirmed, notes).
    """
    if data.get("response_type") != "founder_visual_confirmation":
        return False, False, ""
    if "confirmed" not in data:
        return False, False, ""
    return True, bool(data["confirmed"]), data.get("notes", "")


def visible_launch_proof_allows_next_gate(proof: ChromeVisibleLaunchProof) -> bool:
    """Only founder-confirmed visible launch allows progression."""
    return proof.status == ChromeVisibleLaunchStatus.FOUNDER_CONFIRMED_VISIBLE
