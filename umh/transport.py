"""Workstation transport — four-socket Protocol implementations.

Satisfies SignalEmitter, CapabilityHandler, OutcomeReceiver, and
ViewSubscriber protocols structurally (by shape, no import of Protocol
classes). Follows the node_mesh manifest.py reference pattern.

The workstation is a transport — like Discord or the node mesh — that
translates voice, text, perception, and local actions into signals
and routes them through the substrate spine.

UMH workstation subsystem.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from collections import deque
from typing import Any

from substrate.governance.risk_classes import RiskClass
from substrate.sockets.envelopes import (
    CapabilityRequest,
    CapabilityResponse,
    OutcomeEnvelope,
    ViewFrame,
)
from substrate.sockets.protocols import (
    CapabilityDescriptor,
    CapabilityHealth,
    SignalDescriptor,
)
from substrate.sockets.registry import IntegrationManifest
from substrate.types import CapabilityCategory, SignalUrgency

logger = logging.getLogger(__name__)

INTEGRATION_ID = "workstation_local"


# ---------------------------------------------------------------------------
# SignalEmitter — declares signal types the workstation can emit
# ---------------------------------------------------------------------------


class WorkstationSignalEmitter:
    """Declares signal types the local workstation can push into UMH.

    Voice transcriptions, text input, perception events, mode transitions,
    and system metrics all become signals routed through the substrate spine.
    """

    def __init__(self, integration_id: str = INTEGRATION_ID) -> None:
        self._integration_id = integration_id

    @property
    def integration_id(self) -> str:
        return self._integration_id

    def describe_signals(self) -> list[SignalDescriptor]:
        return [
            SignalDescriptor(
                content_type="workstation.voice.transcription",
                description="Voice input transcribed via STT",
                default_urgency=SignalUrgency.NORMAL,
                default_risk_class=RiskClass.READ_ONLY,
            ),
            SignalDescriptor(
                content_type="workstation.text.input",
                description="Text input from stdin",
                default_urgency=SignalUrgency.NORMAL,
                default_risk_class=RiskClass.READ_ONLY,
            ),
            SignalDescriptor(
                content_type="workstation.perception.presence",
                description="Operator presence detection (webcam face detection)",
                default_urgency=SignalUrgency.LOW,
                default_risk_class=RiskClass.READ_ONLY,
            ),
            SignalDescriptor(
                content_type="workstation.perception.workspace",
                description="Active window / workspace change",
                default_urgency=SignalUrgency.LOW,
                default_risk_class=RiskClass.READ_ONLY,
            ),
            SignalDescriptor(
                content_type="workstation.perception.metrics",
                description="System metrics (CPU, memory, disk)",
                default_urgency=SignalUrgency.BACKGROUND,
                default_risk_class=RiskClass.READ_ONLY,
            ),
            SignalDescriptor(
                content_type="workstation.mode.transition",
                description="Operator mode change (developer, research, etc.)",
                default_urgency=SignalUrgency.NORMAL,
                default_risk_class=RiskClass.READ_ONLY,
            ),
            SignalDescriptor(
                content_type="workstation.boot",
                description="Workstation boot event (first-boot or daily-boot)",
                default_urgency=SignalUrgency.NORMAL,
                default_risk_class=RiskClass.READ_ONLY,
            ),
        ]


# ---------------------------------------------------------------------------
# CapabilityHandler — local actions the workstation can execute
# ---------------------------------------------------------------------------


class WorkstationCapabilityHandler:
    """Handles capability requests that target the local workstation.

    Capabilities: speak text via TTS, execute shell commands, open URLs,
    read/write clipboard, take screenshots. Each goes through the
    existing SafeAction / StationContract governance layer.
    """

    def __init__(self, integration_id: str = INTEGRATION_ID) -> None:
        self._integration_id = integration_id

    @property
    def integration_id(self) -> str:
        return self._integration_id

    def describe_capabilities(self) -> list[CapabilityDescriptor]:
        return [
            CapabilityDescriptor(
                name="speak_text",
                category=CapabilityCategory.COMMUNICATE,
                risk_class=RiskClass.SAFE_WRITE,
                description="Speak text aloud via TTS",
                input_schema={"text": "str", "voice": "str"},
            ),
            CapabilityDescriptor(
                name="shell_execute",
                category=CapabilityCategory.COMPUTE,
                risk_class=RiskClass.REVERSIBLE_WRITE,
                description="Execute a shell command on the local workstation",
                input_schema={"command": "str", "timeout": "int"},
            ),
            CapabilityDescriptor(
                name="open_url",
                category=CapabilityCategory.COMMUNICATE,
                risk_class=RiskClass.SAFE_WRITE,
                description="Open a URL in the default browser",
                input_schema={"url": "str"},
            ),
            CapabilityDescriptor(
                name="clipboard_read",
                category=CapabilityCategory.RETRIEVE,
                risk_class=RiskClass.READ_ONLY,
                description="Read current clipboard contents",
            ),
            CapabilityDescriptor(
                name="clipboard_write",
                category=CapabilityCategory.STORE,
                risk_class=RiskClass.SAFE_WRITE,
                description="Write text to clipboard",
                input_schema={"text": "str"},
            ),
            CapabilityDescriptor(
                name="screenshot",
                category=CapabilityCategory.OBSERVE,
                risk_class=RiskClass.READ_ONLY,
                description="Take a screenshot of the current display",
            ),
            CapabilityDescriptor(
                name="system_info",
                category=CapabilityCategory.RETRIEVE,
                risk_class=RiskClass.READ_ONLY,
                description="Get current system information (OS, CPU, memory)",
            ),
        ]

    def handle_capability(self, request: CapabilityRequest) -> CapabilityResponse:
        """Route capability request to the appropriate local handler."""
        handler_map = {
            "speak_text": self._handle_speak,
            "shell_execute": self._handle_shell,
            "open_url": self._handle_open_url,
            "clipboard_read": self._handle_clipboard_read,
            "clipboard_write": self._handle_clipboard_write,
            "screenshot": self._handle_screenshot,
            "system_info": self._handle_system_info,
        }

        handler = handler_map.get(request.capability_name)
        if handler is None:
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=f"Unknown capability: {request.capability_name}",
            )

        try:
            result = handler(request.params)
            return CapabilityResponse(
                request_id=request.request_id,
                success=True,
                result_data=result,
            )
        except Exception as exc:
            logger.error("Capability %s failed: %s", request.capability_name, exc)
            return CapabilityResponse(
                request_id=request.request_id,
                success=False,
                error=str(exc),
            )

    def health(self) -> CapabilityHealth:
        return CapabilityHealth(
            integration_id=self._integration_id,
            status="healthy",
            detail="local workstation",
        )

    def _handle_speak(self, params: dict[str, Any]) -> dict[str, Any]:
        text = params.get("text", "")
        if not text:
            return {"spoken": False, "reason": "empty text"}
        try:
            from umh.voice import VoiceOutput

            voice = VoiceOutput(text_only=False)
            voice.speak(text)
            return {"spoken": True, "text": text}
        except Exception as exc:
            return {"spoken": False, "reason": str(exc)}

    def _handle_shell(self, params: dict[str, Any]) -> dict[str, Any]:
        command = params.get("command", "")
        timeout = params.get("timeout", 30)
        if not command:
            return {"exit_code": 1, "error": "empty command"}
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.environ.get("UMH_ROOT", "/opt/OS"),
            )
            return {
                "exit_code": result.returncode,
                "stdout": result.stdout[:4096],
                "stderr": result.stderr[:2048],
            }
        except subprocess.TimeoutExpired:
            return {"exit_code": -1, "error": f"timeout after {timeout}s"}

    def _handle_open_url(self, params: dict[str, Any]) -> dict[str, Any]:
        url = params.get("url", "")
        if not url:
            return {"opened": False, "reason": "empty URL"}
        try:
            import webbrowser

            webbrowser.open(url)
            return {"opened": True, "url": url}
        except Exception as exc:
            return {"opened": False, "reason": str(exc)}

    def _handle_clipboard_read(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            result = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return {"content": result.stdout[:4096]}
        except Exception:
            return {"content": "", "error": "clipboard read unavailable"}

    def _handle_clipboard_write(self, params: dict[str, Any]) -> dict[str, Any]:
        text = params.get("text", "")
        try:
            proc = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE,
            )
            proc.communicate(input=text.encode("utf-8"), timeout=5)
            return {"written": True}
        except Exception:
            return {"written": False, "error": "clipboard write unavailable"}

    def _handle_screenshot(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"available": False, "reason": "screenshot not yet implemented"}

    def _handle_system_info(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            import psutil

            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            return {
                "platform": platform.system(),
                "hostname": platform.node(),
                "python": platform.python_version(),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": mem.percent,
                "disk_percent": disk.percent,
            }
        except ImportError:
            return {
                "platform": platform.system(),
                "hostname": platform.node(),
                "python": platform.python_version(),
            }


# ---------------------------------------------------------------------------
# OutcomeReceiver — receives pipeline outcomes for display/voice
# ---------------------------------------------------------------------------


class WorkstationOutcomeReceiver:
    """Receives outcome notifications from the substrate pipeline.

    Outcomes are displayed to the operator (print) and optionally spoken
    via TTS. Recent outcomes are buffered for the status display.
    """

    def __init__(
        self,
        integration_id: str = INTEGRATION_ID,
        max_recent: int = 50,
    ) -> None:
        self._integration_id = integration_id
        self._recent: deque[OutcomeEnvelope] = deque(maxlen=max_recent)

    @property
    def integration_id(self) -> str:
        return self._integration_id

    def on_outcome(self, envelope: OutcomeEnvelope) -> None:
        self._recent.append(envelope)
        logger.info(
            "Outcome [%s]: %s — %s",
            envelope.outcome_type,
            envelope.summary,
            envelope.governance_decision,
        )

    def accepts_outcomes(self) -> list[str]:
        return []

    @property
    def recent_outcomes(self) -> list[OutcomeEnvelope]:
        return list(self._recent)

    @property
    def outcome_count(self) -> int:
        return len(self._recent)


# ---------------------------------------------------------------------------
# ViewSubscriber — receives pipeline state frames for status display
# ---------------------------------------------------------------------------


class WorkstationViewSubscriber:
    """Receives pipeline state frames for the workstation status display.

    Frames are buffered in a ring buffer. The status display reads from
    this buffer to show current pipeline activity.
    """

    def __init__(
        self,
        subscriber_id: str = INTEGRATION_ID,
        max_frames: int = 100,
    ) -> None:
        self._subscriber_id = subscriber_id
        self._frames: deque[ViewFrame] = deque(maxlen=max_frames)

    @property
    def subscriber_id(self) -> str:
        return self._subscriber_id

    def on_frame(self, frame: ViewFrame) -> None:
        self._frames.append(frame)

    def accepts_events(self) -> list[str]:
        return []

    @property
    def recent_frames(self) -> list[ViewFrame]:
        return list(self._frames)

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def last_stage(self) -> int | None:
        if self._frames:
            return self._frames[-1].stage
        return None


# ---------------------------------------------------------------------------
# Manifest builder — the single entry point for boot registration
# ---------------------------------------------------------------------------


def build_workstation_manifest(
    integration_id: str = INTEGRATION_ID,
) -> IntegrationManifest:
    """Build the four-socket IntegrationManifest for the local workstation.

    Called at boot time. The returned manifest is registered with the
    IntegrationRegistry, wiring the workstation into all four substrate
    sockets (signal, capability, outcome, view).
    """
    return IntegrationManifest(
        integration_id=integration_id,
        signal_emitter=WorkstationSignalEmitter(integration_id),
        capability_handler=WorkstationCapabilityHandler(integration_id),
        outcome_receiver=WorkstationOutcomeReceiver(integration_id),
        view_subscriber=WorkstationViewSubscriber(integration_id),
    )
