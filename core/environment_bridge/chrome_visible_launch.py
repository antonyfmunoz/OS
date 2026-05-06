"""Chrome visible launch gate for the Environment Bridge.

Evaluates whether Chrome was launched through the direct executable
path AND has a visible window (MainWindowHandle != 0 or MainWindowTitle
nonblank). Process existence alone is NOT sufficient proof.

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


class ChromeVisibleLaunchStatus(str, Enum):
    VISIBLE_CHROME_LAUNCH = "visible_chrome_launch"
    VISIBLE_CHROME_LAUNCH_UNVERIFIED = "visible_chrome_launch_unverified"
    CHROME_BACKGROUND_PROCESS_ONLY = "chrome_background_process_only"
    CHROME_NOT_FOUND = "chrome_not_found"
    LAUNCH_METHOD_DISALLOWED = "launch_method_disallowed"
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
    visible_window_detected: bool = False
    founder_visual_confirmation_required: bool = False
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
            "visible_window_detected": self.visible_window_detected,
            "founder_visual_confirmation_required": self.founder_visual_confirmation_required,
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


def visible_chrome_window_detected(
    processes: list[ChromeProcessSnapshot],
) -> bool:
    for proc in processes:
        if proc.main_window_handle != 0:
            return True
        if proc.main_window_title.strip():
            return True
    return False


def evaluate_visible_chrome_launch(
    launch_method: ChromeLaunchMethod,
    executable_path: str,
    requested_url: str,
    processes: list[ChromeProcessSnapshot],
) -> ChromeVisibleLaunchProof:
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
        proof.notes.append(
            f"Launch method {launch_method.value} with path {executable_path} is not allowed"
        )
        return proof

    if not processes:
        proof.status = ChromeVisibleLaunchStatus.CHROME_NOT_FOUND
        proof.notes.append("No Chrome processes found after launch attempt")
        return proof

    if visible_chrome_window_detected(processes):
        proof.visible_window_detected = True
        proof.status = ChromeVisibleLaunchStatus.VISIBLE_CHROME_LAUNCH
        proof.notes.append("Visible Chrome window detected")
        return proof

    proof.status = ChromeVisibleLaunchStatus.CHROME_BACKGROUND_PROCESS_ONLY
    proof.founder_visual_confirmation_required = True
    proof.notes.append(
        "Chrome processes exist but MainWindowHandle=0 and MainWindowTitle blank. "
        "Founder visual confirmation required."
    )
    return proof


def visible_launch_proof_allows_next_gate(proof: ChromeVisibleLaunchProof) -> bool:
    return proof.status == ChromeVisibleLaunchStatus.VISIBLE_CHROME_LAUNCH
