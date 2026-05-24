"""Installer — Phase 0 system setup + substrate registration.

Wraps diagnostics with fix-it guidance and creates required data
directories. Registers the workstation transport with the substrate
via IntegrationManifest (four-socket connection).
"""

from __future__ import annotations

import logging
import os

from umh import UMH_ROOT

logger = logging.getLogger(__name__)

REQUIRED_DIRS = [
    os.path.join(UMH_ROOT, "data", "onboarding"),
    os.path.join(UMH_ROOT, "data", "voice"),
    os.path.join(UMH_ROOT, "data", "permissions"),
    os.path.join(UMH_ROOT, "data", "sessions"),
    os.path.join(UMH_ROOT, "data", "environment_maps"),
    os.path.join(UMH_ROOT, "data", "audio"),
    os.path.join(UMH_ROOT, "data", "diagnostic_scans"),
    os.path.join(UMH_ROOT, "data", "runtime", "workstation_continuity"),
]

FIX_INSTRUCTIONS: dict[str, str] = {
    "faster-whisper (STT)": "pip install faster-whisper",
    "Silero VAD": "pip install torch torchaudio",
    "Coqui TTS (persona voice)": "pip install TTS",
    "XTTS v2 (voice clone)": "pip install TTS",
    "Audio output": "apt install alsa-utils  (or pulseaudio)",
    "Microphone (sounddevice)": "pip install sounddevice",
    "Webcam (OpenCV)": "pip install opencv-python-headless",
    "Ollama": "curl -fsSL https://ollama.ai/install.sh | sh",
}


def run_install() -> int:
    """Run Phase 0 installation: diagnostics + directory setup + registration."""
    print()
    print("=" * 50)
    print("  UMH Workstation — Installation")
    print("=" * 50)
    print()

    # Step 1: Create required directories
    print("[1/3] Creating data directories...")
    for d in REQUIRED_DIRS:
        os.makedirs(d, exist_ok=True)
    print(f"      {len(REQUIRED_DIRS)} directories ready.")
    print()

    # Step 2: Run diagnostics
    print("[2/3] Running system diagnostics...")
    from umh.diagnostics import Status, get_capabilities

    report = get_capabilities()
    report.print_report()

    # Show fix instructions for warnings/failures
    fixable = [
        c
        for c in report.checks
        if c.status in (Status.WARN, Status.FAIL) and c.name in FIX_INSTRUCTIONS
    ]
    if fixable:
        print("  To fix missing components:")
        for c in fixable:
            print(f"    {c.name}: {FIX_INSTRUCTIONS[c.name]}")
        print()

    # Step 3: Register with substrate
    print("[3/3] Registering workstation transport...")
    registered = _register_transport()
    if registered:
        print("      Registered with substrate (four-socket connection).")
    else:
        print("      Substrate not available — standalone mode.")
    print()

    if report.has_failures:
        print("Fix FAIL items before running `umh`.")
        return 1

    print("Installation complete. Run `umh setup` to begin onboarding.")
    print()
    return 0


def _register_transport() -> bool:
    """Register workstation as a transport with the substrate."""
    try:
        from substrate.sockets.registry import IntegrationManifest, IntegrationRegistry

        manifest = IntegrationManifest(
            integration_id="workstation_local",
            signal_emitter=None,
            capability_handler=None,
            outcome_receiver=None,
            view_subscriber=None,
        )

        registry = IntegrationRegistry.get_instance()
        registry.register(manifest)
        logger.info("Workstation transport registered with substrate")
        return True
    except (ImportError, Exception) as exc:
        logger.debug("Substrate registration failed: %s", exc)
        return False


def ensure_directories() -> None:
    """Create required data directories if missing."""
    for d in REQUIRED_DIRS:
        os.makedirs(d, exist_ok=True)
