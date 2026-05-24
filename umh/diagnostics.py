"""System diagnostics — Phase 0 of UMH instance instantiation."""

from __future__ import annotations

import importlib
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class Status(Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str = ""


@dataclass
class DiagnosticReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(c.status == Status.FAIL for c in self.checks)

    def print_report(self) -> None:
        max_name = max((len(c.name) for c in self.checks), default=20)
        print()
        print("╔" + "═" * (max_name + 18) + "╗")
        print(f"║  UMH System Diagnostics{' ' * (max_name - 6)}║")
        print("╠" + "═" * (max_name + 18) + "╣")
        for c in self.checks:
            marker = {"OK": "✓", "WARN": "⚠", "FAIL": "✗"}[c.status.value]
            pad = " " * (max_name - len(c.name))
            detail = f"  {c.detail}" if c.detail else ""
            print(
                f"║  [{marker}] {c.name}{pad} {c.status.value:4s}{detail:>{max_name - len(detail) + 6 if False else 0}s}  ║"
            )
        print("╚" + "═" * (max_name + 18) + "╝")

        ok = sum(1 for c in self.checks if c.status == Status.OK)
        warn = sum(1 for c in self.checks if c.status == Status.WARN)
        fail = sum(1 for c in self.checks if c.status == Status.FAIL)
        print(f"\n  {ok} passed, {warn} warnings, {fail} failures")
        if self.has_failures:
            print("  Fix FAIL items before running `umh`.")
        print()


def _check_python_version() -> CheckResult:
    v = sys.version_info
    if v >= (3, 11):
        return CheckResult("Python >= 3.11", Status.OK, f"{v.major}.{v.minor}.{v.micro}")
    return CheckResult("Python >= 3.11", Status.FAIL, f"found {v.major}.{v.minor}")


def _check_import(name: str, package: str | None = None) -> CheckResult:
    label = package or name
    try:
        importlib.import_module(name)
        return CheckResult(label, Status.OK)
    except ImportError:
        return CheckResult(label, Status.WARN, "not installed")


def _check_faster_whisper() -> CheckResult:
    return _check_import("faster_whisper", "faster-whisper (STT)")


def _check_silero_vad() -> CheckResult:
    try:
        import torch  # noqa: F401

        return CheckResult("Silero VAD", Status.OK)
    except ImportError:
        return CheckResult("Silero VAD", Status.WARN, "torch not installed")


def _check_coqui_tts() -> CheckResult:
    return _check_import("TTS", "Coqui TTS (persona voice)")


def _check_xtts_v2() -> CheckResult:
    try:
        from TTS.api import TTS  # noqa: F401

        return CheckResult("XTTS v2 (voice clone)", Status.OK)
    except ImportError:
        return CheckResult("XTTS v2 (voice clone)", Status.WARN, "TTS package not installed")


def _check_audio_output() -> CheckResult:
    if platform.system() == "Darwin":
        if shutil.which("afplay"):
            return CheckResult("Audio output", Status.OK, "afplay")
    if shutil.which("aplay"):
        return CheckResult("Audio output", Status.OK, "aplay")
    if shutil.which("paplay"):
        return CheckResult("Audio output", Status.OK, "paplay")
    return CheckResult("Audio output", Status.WARN, "no audio player found")


def _check_microphone() -> CheckResult:
    try:
        import sounddevice  # noqa: F401

        return CheckResult("Microphone (sounddevice)", Status.OK)
    except ImportError:
        return CheckResult("Microphone (sounddevice)", Status.WARN, "not installed")
    except Exception as exc:
        return CheckResult("Microphone (sounddevice)", Status.WARN, str(exc)[:60])


def _check_ollama() -> CheckResult:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            model_count = max(0, len(lines) - 1)
            return CheckResult("Ollama", Status.OK, f"{model_count} models")
        return CheckResult("Ollama", Status.WARN, "not responding")
    except FileNotFoundError:
        return CheckResult("Ollama", Status.WARN, "not installed")
    except subprocess.TimeoutExpired:
        return CheckResult("Ollama", Status.WARN, "timeout")


def _check_webcam() -> CheckResult:
    try:
        import cv2

        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            cap.release()
            return CheckResult("Webcam (OpenCV)", Status.OK)
        cap.release()
        return CheckResult("Webcam (OpenCV)", Status.WARN, "no device found")
    except ImportError:
        return CheckResult("Webcam (OpenCV)", Status.WARN, "opencv not installed")


def _check_network() -> CheckResult:
    try:
        import socket

        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return CheckResult("Network", Status.OK)
    except OSError:
        return CheckResult("Network", Status.WARN, "no internet")


def _check_disk_space() -> CheckResult:
    umh_root = os.environ.get("UMH_ROOT", "/opt/OS")
    usage = shutil.disk_usage(umh_root)
    free_gb = usage.free / (1024**3)
    if free_gb >= 5.0:
        return CheckResult("Disk space", Status.OK, f"{free_gb:.1f} GB free")
    if free_gb >= 2.0:
        return CheckResult("Disk space", Status.WARN, f"{free_gb:.1f} GB free")
    return CheckResult("Disk space", Status.FAIL, f"{free_gb:.1f} GB free (<2 GB)")


ALL_CHECKS: list[Callable[[], CheckResult]] = [
    _check_python_version,
    _check_faster_whisper,
    _check_silero_vad,
    _check_coqui_tts,
    _check_xtts_v2,
    _check_audio_output,
    _check_microphone,
    _check_ollama,
    _check_webcam,
    _check_network,
    _check_disk_space,
]


def run_diagnostics() -> int:
    report = DiagnosticReport()
    for check_fn in ALL_CHECKS:
        try:
            report.checks.append(check_fn())
        except Exception as exc:
            report.checks.append(
                CheckResult(check_fn.__name__.replace("_check_", ""), Status.FAIL, str(exc)[:60])
            )
    report.print_report()
    return 1 if report.has_failures else 0


def get_capabilities() -> DiagnosticReport:
    report = DiagnosticReport()
    for check_fn in ALL_CHECKS:
        try:
            report.checks.append(check_fn())
        except Exception as exc:
            report.checks.append(
                CheckResult(check_fn.__name__.replace("_check_", ""), Status.FAIL, str(exc)[:60])
            )
    return report
