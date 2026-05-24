"""Boot orchestrator — routes to first-boot or daily-boot, starts mic + discovery."""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from umh.daily import run_daily_boot
from umh.loop import run_interaction_loop
from umh.profile import ProfileManager

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


def _start_mic(text_only: bool, voice_mode: str = "ambient") -> Any:
    """Start the appropriate mic based on capabilities and preferences."""
    if text_only:
        return None

    try:
        from umh.capabilities import WorkstationCapabilities
        from umh.diagnostics import get_capabilities

        report = get_capabilities()
        caps = WorkstationCapabilities.from_report(report)
        if not caps.can_voice_input:
            logger.info("Voice input unavailable (missing mic, STT, or VAD)")
            return None
    except Exception as exc:
        logger.debug("Capability check failed, skipping mic: %s", exc)
        return None

    try:
        if voice_mode == "push_to_talk":
            from umh.mic import PushToTalkMic

            mic = PushToTalkMic()
        else:
            from umh.mic import AmbientMic

            mic = AmbientMic()

        if mic.start():
            print(f"[mic] {voice_mode.replace('_', '-')} mode active")
            return mic
        logger.info("Mic failed to start, falling back to text-only")
        return None
    except (ImportError, Exception) as exc:
        logger.info("Mic not available: %s", exc)
        return None


def _start_discovery() -> Any:
    """Start background environment discovery scan."""
    try:
        from umh.discovery import DiscoveryScanner

        scanner = DiscoveryScanner()
        if scanner.start_background_scan():
            print("[discovery] Background environment scan started.")
            return scanner
        return None
    except Exception as exc:
        logger.debug("Discovery scan failed to start: %s", exc)
        return None


def run_boot(text_only: bool = False, voice_mode: str = "ambient") -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    from umh.installer import ensure_directories

    ensure_directories()

    pm = ProfileManager()
    if not pm.has_snapshot():
        return run_first_boot(text_only=text_only, voice_mode=voice_mode)

    mode_state, session_id = run_daily_boot(text_only=text_only)
    mic = _start_mic(text_only, voice_mode)
    _start_discovery()

    return run_interaction_loop(
        mode_state=mode_state,
        session_id=session_id,
        text_only=text_only,
        mic=mic,
    )


def run_first_boot(text_only: bool = False, voice_mode: str = "ambient") -> int:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    from umh.installer import ensure_directories

    ensure_directories()

    print()
    print("=" * 50)
    print("  UMH Workstation — First Boot")
    print("=" * 50)
    print()

    # Phase 0: Diagnostics
    from umh.diagnostics import run_diagnostics

    diag_result = run_diagnostics()
    if diag_result != 0:
        print("Fix diagnostic failures before continuing.")
        return diag_result

    # Phases 1-2 + 4: Onboarding (naming + setup method + business context)
    from umh.onboarding_adapter import run_onboarding_cli

    result = run_onboarding_cli(text_only=text_only)
    if result is None:
        print("Onboarding cancelled. Run `umh setup` to try again.")
        return 1

    # Start background discovery (Phase 6 beginning)
    _start_discovery()

    # Continue to daily boot + interaction loop
    mode_state, session_id = run_daily_boot(text_only=text_only)
    mic = _start_mic(text_only, voice_mode)

    return run_interaction_loop(
        mode_state=mode_state,
        session_id=session_id,
        text_only=text_only,
        mic=mic,
    )
