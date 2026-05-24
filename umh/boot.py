"""Boot orchestrator — routes to first-boot or daily-boot, starts mic + discovery + perception.

Sprint 8: registers workstation as four-socket substrate transport,
starts continuity tracking, wires resume state into daily greeting.
Sprint 9: starts scheduler, wires signal socket, emits boot signal.
Sprint 10: outcome callbacks, operator state sync, inference checker, capability routing.
Sprint 12: retains transport manifest for view subscriber access at runtime.
"""

from __future__ import annotations

import logging
from typing import Any

from umh.daily import run_daily_boot
from umh.loop import run_interaction_loop
from umh.profile import ProfileManager

logger = logging.getLogger(__name__)


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


def _register_transport() -> Any:
    """Register the workstation as a four-socket substrate transport."""
    try:
        from umh.transport import build_workstation_manifest, set_active_manifest

        manifest = build_workstation_manifest()
        set_active_manifest(manifest)

        try:
            from substrate.sockets.capability_socket import CapabilitySocket
            from substrate.sockets.outcome_socket import OutcomeSocket
            from substrate.sockets.registry import IntegrationRegistry
            from substrate.sockets.signal_socket import SignalSocket
            from substrate.sockets.view_socket import ViewSocket

            signal_socket = SignalSocket()
            registry = IntegrationRegistry(
                signal_socket=signal_socket,
                capability_socket=CapabilitySocket(),
                outcome_socket=OutcomeSocket(),
                view_socket=ViewSocket(),
            )
            registry.register(manifest)

            from umh.signals import set_signal_socket

            set_signal_socket(signal_socket)

            print(f"[transport] Registered: {manifest.integration_id} (4 sockets)")
            return registry
        except ImportError:
            logger.info("Substrate sockets not available — transport registered locally only")
            print(f"[transport] Manifest built: {manifest.integration_id} (offline)")
            return manifest
    except Exception as exc:
        logger.debug("Transport registration failed: %s", exc)
        return None


def _start_continuity(session_id: str) -> Any:
    """Start continuity tracking for this session."""
    try:
        from umh.continuity import SessionContinuity

        continuity = SessionContinuity()
        sid = continuity.start(session_id)
        print(f"[continuity] Session: {sid[:16]}...")
        return continuity
    except Exception as exc:
        logger.debug("Continuity start failed: %s", exc)
        return None


def _start_scheduler() -> Any:
    """Start the background scheduled trigger producer."""
    try:
        from umh.scheduler import create_scheduler_from_preferences

        scheduler = create_scheduler_from_preferences()
        if scheduler.start():
            print("[scheduler] Background trigger producer active")
            return scheduler
        return None
    except Exception as exc:
        logger.debug("Scheduler start failed: %s", exc)
        return None


def _emit_boot_signal(session_id: str, boot_type: str = "daily") -> None:
    """Emit a boot signal through the signal socket."""
    try:
        from umh.signals import emit_boot_event

        emit_boot_event(boot_type=boot_type, session_id=session_id)
    except Exception as exc:
        logger.debug("Boot signal emission failed: %s", exc)


def _sync_operator_boot(node_id: str = "workstation_local") -> None:
    """Sync operator state to ACTIVE on workstation boot."""
    try:
        from umh.operator_sync import sync_boot

        result = sync_boot(node_id)
        if result.get("status") == "synced":
            print(f"[operator] State: {result.get('mode', '?')}")
    except Exception as exc:
        logger.debug("Operator boot sync failed: %s", exc)


def _setup_outcome_callback() -> None:
    """Register outcome callback to print/speak pipeline results."""
    try:
        from umh.outcomes import format_outcome, set_outcome_callback

        def _on_outcome(envelope):
            text = format_outcome(envelope)
            if text:
                print(f"  [outcome] {text}")

        set_outcome_callback(_on_outcome)
    except Exception as exc:
        logger.debug("Outcome callback setup failed: %s", exc)


def _create_inference_checker() -> Any:
    """Create the runtime inference checker."""
    try:
        from umh.inference_loop import create_inference_checker

        return create_inference_checker()
    except Exception as exc:
        logger.debug("Inference checker creation failed: %s", exc)
        return None


def _start_perception(mode_state: Any) -> Any:
    """Start all perception sources (webcam, workspace, metrics)."""
    try:
        from umh.perception.router import PerceptionRouter

        router = PerceptionRouter(mode_state=mode_state)
        results = router.start_all()
        started = [k for k, v in results.items() if v]
        if started:
            print(f"[perception] Active: {', '.join(started)}")
        return router
    except Exception as exc:
        logger.debug("Perception start failed: %s", exc)
        return None


def _run_personality_selection() -> None:
    """Phase 3: Quick personality preset selection during first boot."""
    try:
        from umh.personality import (
            PRESET_TRAITS,
            PersonalityConfig,
            PersonalityPreset,
            save_personality,
        )

        print()
        print("Choose your AI personality:")
        print()
        for i, preset in enumerate(PersonalityPreset, 1):
            traits = PRESET_TRAITS[preset]
            print(
                f"  {i}. {preset.value.capitalize():<12s} — {traits.tone}, {traits.style}, {traits.governance.value} autonomy"
            )
        print()

        try:
            choice = input("  Pick a number (default: 1 Operator): ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = ""

        presets = list(PersonalityPreset)
        try:
            idx = int(choice) - 1
            selected = presets[idx] if 0 <= idx < len(presets) else PersonalityPreset.OPERATOR
        except (ValueError, IndexError):
            selected = PersonalityPreset.OPERATOR

        config = PersonalityConfig(preset=selected)
        save_personality(config)
        print(f"\n  Personality set: {selected.value.capitalize()}\n")

    except Exception as exc:
        logger.debug("Personality selection failed: %s", exc)


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
    _register_transport()
    _setup_outcome_callback()
    _sync_operator_boot()
    continuity = _start_continuity(session_id)
    scheduler = _start_scheduler()
    inference_checker = _create_inference_checker()
    _emit_boot_signal(session_id, boot_type="daily")
    mic = _start_mic(text_only, voice_mode)
    _start_discovery()
    perception = _start_perception(mode_state)

    return run_interaction_loop(
        mode_state=mode_state,
        session_id=session_id,
        text_only=text_only,
        mic=mic,
        perception=perception,
        continuity=continuity,
        scheduler=scheduler,
        inference_checker=inference_checker,
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

    # Phase 3: Personality selection
    _run_personality_selection()

    # Start background discovery (Phase 6 beginning)
    _start_discovery()

    # Continue to daily boot + interaction loop
    mode_state, session_id = run_daily_boot(text_only=text_only)
    _register_transport()
    _setup_outcome_callback()
    _sync_operator_boot()
    continuity = _start_continuity(session_id)
    scheduler = _start_scheduler()
    inference_checker = _create_inference_checker()
    _emit_boot_signal(session_id, boot_type="first_boot")
    mic = _start_mic(text_only, voice_mode)
    perception = _start_perception(mode_state)

    return run_interaction_loop(
        mode_state=mode_state,
        session_id=session_id,
        text_only=text_only,
        mic=mic,
        perception=perception,
        continuity=continuity,
        scheduler=scheduler,
        inference_checker=inference_checker,
    )
