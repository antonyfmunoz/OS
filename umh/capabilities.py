"""Workstation capabilities — detected from diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from umh.diagnostics import DiagnosticReport, Status


@dataclass
class WorkstationCapabilities:
    has_mic: bool = False
    has_webcam: bool = False
    has_ollama: bool = False
    has_stt: bool = False
    has_vad: bool = False
    has_tts: bool = False
    has_xtts: bool = False
    has_audio_output: bool = False
    has_network: bool = False
    ollama_models: int = 0

    @classmethod
    def from_report(cls, report: DiagnosticReport) -> WorkstationCapabilities:
        lookup = {c.name: c for c in report.checks}

        def _ok(name: str) -> bool:
            r = lookup.get(name)
            return r is not None and r.status == Status.OK

        caps = cls(
            has_mic=_ok("Microphone (sounddevice)"),
            has_webcam=_ok("Webcam (OpenCV)"),
            has_ollama=_ok("Ollama"),
            has_stt=_ok("faster-whisper (STT)"),
            has_vad=_ok("Silero VAD"),
            has_tts=_ok("Coqui TTS (persona voice)"),
            has_xtts=_ok("XTTS v2 (voice clone)"),
            has_audio_output=_ok("Audio output"),
            has_network=_ok("Network"),
        )

        ollama_check = lookup.get("Ollama")
        if ollama_check and ollama_check.status == Status.OK and "models" in ollama_check.detail:
            try:
                caps.ollama_models = int(ollama_check.detail.split()[0])
            except (ValueError, IndexError):
                pass

        return caps

    @property
    def can_voice_input(self) -> bool:
        return self.has_mic and self.has_stt and self.has_vad

    @property
    def can_voice_output(self) -> bool:
        return self.has_tts and self.has_audio_output

    @property
    def can_voice_clone(self) -> bool:
        return self.has_xtts and self.has_audio_output

    @property
    def voice_mode_available(self) -> bool:
        return self.can_voice_input and self.can_voice_output
