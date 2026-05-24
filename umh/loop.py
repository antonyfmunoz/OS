"""Interaction loop — text + voice input with concurrent processing.

Sprint 1: text-only stdin loop.
Sprint 2: voice input via AmbientMic/PushToTalkMic racing against stdin.
Sprint 4: perception integration (webcam, workspace, metrics).
Sprint 6: personality command, sensing adapter display.
Sprint 8: continuity tracking, awakening command, transport status.
Sprint 9: approval queue, signal emission, scheduler, triggers.
Sprint 10: outcome display, capability routing, operator state sync, inference suggestions.

When voice is enabled, stdin runs in a background thread and the main loop
polls both the mic transcript queue and the stdin queue. When voice is
disabled, falls back to the simple blocking input() loop from Sprint 1.

Perception router is polled each cycle to check auto-AWAY timeout.
Continuity bridge tracks every execution and mode transition.
Signal socket emits SignalEnvelopes for text/voice inputs.
"""

from __future__ import annotations

import logging
import os
import queue
import sys
import threading
import time
from typing import Any

from umh.modes import CommandResult, ModeState, parse_command
from umh.signals import emit_text_input, emit_voice_transcription
from umh.voice import VoiceOutput

logger = logging.getLogger(__name__)

sys.path.insert(0, os.environ.get("UMH_ROOT", "/opt/OS"))


def _try_gateway(text: str) -> str | None:
    try:
        from substrate.control_plane.runtime.gateway import get_gateway

        gw = get_gateway()
        result = gw.handle({"type": "agent_task", "prompt": text})
        if result.get("status") == "ok":
            return result.get("response") or result.get("result") or str(result)
        if result.get("status") == "error":
            return f"Error: {result.get('message', 'unknown')}"
        return str(result)
    except ImportError:
        logger.debug("Gateway not available")
        return None
    except Exception as exc:
        logger.debug("Gateway call failed: %s", exc)
        return None


def _try_voice_route(text: str, voice: VoiceOutput) -> str | None:
    try:
        return voice.route_query(text)
    except Exception as exc:
        logger.debug("Voice routing failed: %s", exc)
        return None


def _record_transcript(node_id: str, text: str, source: str = "manual") -> None:
    try:
        from substrate.execution.bridge.audio_loop import record_transcript

        record_transcript(node_id, text, source=source)
    except (ImportError, Exception) as exc:
        logger.debug("Transcript recording failed: %s", exc)


def _update_audio_loop_status(node_id: str, status: str) -> None:
    try:
        from substrate.execution.bridge import audio_loop

        fn = getattr(audio_loop, f"mark_{status}", None)
        if fn is not None:
            fn(node_id)
    except (ImportError, Exception) as exc:
        logger.debug("Audio loop status update failed: %s", exc)


def _sync_operator_exit(node_id: str) -> None:
    """Sync operator state to IDLE on workstation exit."""
    try:
        from umh.operator_sync import sync_exit

        sync_exit(node_id)
    except Exception as exc:
        logger.debug("Operator exit sync failed: %s", exc)


def _emit_input_signal(text: str, source: str) -> None:
    """Emit a signal for text or voice input through the signal socket."""
    try:
        if source == "voice":
            emit_voice_transcription(text)
        else:
            emit_text_input(text, source=source)
    except Exception as exc:
        logger.debug("Signal emission failed: %s", exc)


def _handle_system_command(
    cmd: CommandResult, mode_state: ModeState, voice: VoiceOutput, perception: Any = None
) -> str:
    if cmd.command == "status":
        return mode_state.display()

    if cmd.command == "mode_switch":
        return cmd.response

    if cmd.command == "help":
        return _help_text(mode_state)

    if cmd.command == "mode_info":
        profiles = ", ".join(p.value for p in mode_state.profiles)
        return f"System: {mode_state.system.value}\nProfiles: {profiles}"

    if cmd.command == "exit":
        return "__EXIT__"

    if cmd.command == "settings":
        from umh.profile import show_settings

        show_settings()
        return ""

    if cmd.command == "voice_setup":
        from umh.voice import run_voice_setup

        run_voice_setup()
        return ""

    if cmd.command == "push_to_talk":
        return "Voice mode: push-to-talk (toggle with 'always on')"

    if cmd.command == "always_on":
        return "Voice mode: ambient (toggle with 'push to talk')"

    if cmd.command == "pending":
        from umh.approvals import show_pending

        return show_pending()

    if cmd.command == "approve":
        from umh.approvals import approve_item

        item_id = cmd.response or ""
        if not item_id:
            return "Usage: approve <id>"
        return approve_item(item_id)

    if cmd.command == "reject":
        from umh.approvals import reject_item

        item_id = cmd.response or ""
        if not item_id:
            return "Usage: reject <id>"
        return reject_item(item_id)

    if cmd.command == "webcam_on":
        if perception is not None:
            return perception.enable_webcam()
        return "Perception not initialized — restart with webcam support"

    if cmd.command == "webcam_off":
        if perception is not None:
            return perception.disable_webcam()
        return "Perception not initialized"

    if cmd.command == "mesh_status":
        try:
            from umh.mesh import format_mesh_status

            return format_mesh_status()
        except Exception as exc:
            return f"Mesh status unavailable: {exc}"

    if cmd.command == "personality":
        from umh.personality import show_personality

        show_personality()
        return ""

    if cmd.command == "governance":
        from umh.governance_config import show_governance

        show_governance()
        return ""

    if cmd.command == "review":
        from umh.review import show_review

        show_review()
        return ""

    if cmd.command == "profile_inference":
        from umh.profile_inference import show_inference

        show_inference()
        return ""

    if cmd.command == "awakening":
        from umh.awakening import show_awakening

        show_awakening()
        return ""

    if cmd.command == "continuity":
        from umh.continuity import show_continuity

        show_continuity()
        return ""

    if cmd.command == "transport":
        return _show_transport_status()

    if cmd.command == "triggers":
        from umh.triggers import show_triggers

        show_triggers()
        return ""

    if cmd.command == "scheduler":
        from umh.scheduler import show_scheduler_status

        show_scheduler_status()
        return ""

    if cmd.command == "approvals":
        from umh.approvals import show_approvals

        show_approvals()
        return ""

    if cmd.command == "outcomes":
        from umh.outcomes import show_outcomes

        show_outcomes()
        return ""

    if cmd.command == "operator":
        from umh.operator_sync import show_operator_state

        show_operator_state()
        return ""

    if cmd.command == "local_capabilities":
        from umh.capability_router import show_capabilities

        show_capabilities()
        return ""

    return f"Unknown command: {cmd.command}"


def _show_transport_status() -> str:
    """Show the workstation transport registration status."""
    try:
        from umh.transport import INTEGRATION_ID

        lines = [f"Transport: {INTEGRATION_ID}", "Sockets: signal, capability, outcome, view"]
        return "\n".join(lines)
    except Exception as exc:
        return f"Transport status unavailable: {exc}"


def _help_text(mode_state: ModeState) -> str:
    return """Available commands:
  status              — show workstation status
  help                — this help text
  mode info           — current mode details
  settings            — view preferences
  voice setup         — configure voice
  developer mode      — switch to developer mode
  research mode       — switch to research mode
  command center      — switch to command center
  stack <mode>        — add a profile mode
  unstack <mode>      — remove a profile mode
  emergency           — lock down (read-only)
  push to talk        — switch to push-to-talk voice mode
  always on           — switch to ambient voice mode
  webcam on           — enable webcam perception
  webcam off          — disable webcam perception
  personality         — show personality configuration
  governance          — show governance configuration
  review              — full instance review dashboard
  profile inference   — show inferred profile modes
  awakening           — run The Awakening reality brief
  continuity          — show session continuity state
  transport           — show transport registration status
  show pending        — list pending approvals
  approve <id>        — approve a pending item
  reject <id>         — reject a pending item
  triggers            — show trigger history
  scheduler           — show scheduler status
  outcomes            — show pipeline outcomes
  operator            — show operator state
  capabilities        — show local capabilities
  open <url>          — open URL in browser
  system info         — show system metrics
  run <command>       — execute shell command
  exit / bye          — save state and exit"""


def _start_stdin_thread(
    text_queue: queue.Queue[str | None],
    stop_event: threading.Event,
    prompt: str,
) -> threading.Thread:
    def _reader() -> None:
        while not stop_event.is_set():
            try:
                line = input(prompt)
                text_queue.put(line.strip())
            except (EOFError, KeyboardInterrupt):
                text_queue.put(None)
                return
            except Exception:
                text_queue.put(None)
                return

    t = threading.Thread(target=_reader, daemon=True, name="umh-stdin")
    t.start()
    return t


def _process_input(
    user_input: str,
    source: str,
    mode_state: ModeState,
    voice: VoiceOutput,
    node_id: str,
    persona_name: str,
    perception: Any = None,
    continuity: Any = None,
) -> bool:
    """Process a single input line. Returns True to continue, False to exit."""
    if not user_input:
        return True

    _record_transcript(node_id, user_input, source=source)
    _update_audio_loop_status(node_id, "listening")

    _emit_input_signal(user_input, source)

    cmd = parse_command(user_input, mode_state)
    if cmd.handled:
        response = _handle_system_command(cmd, mode_state, voice, perception=perception)
        if response == "__EXIT__":
            _update_audio_loop_status(node_id, "inactive")
            if perception is not None:
                perception.stop_all()
            if continuity is not None:
                continuity.save_on_exit()
            voice.speak_and_print("State saved. Goodbye.")
            return False
        if response:
            _update_audio_loop_status(node_id, "responding")
            voice.speak_and_print(response)
            _update_audio_loop_status(node_id, "cooling_down")
        if continuity is not None:
            continuity.track_execution(
                command=user_input,
                outcome="success",
                adapter_used="system_command",
            )
        _record_transcript(node_id, response or "(no response)", source="system")
        return True

    from umh.capability_router import invoke_capability

    cap_response = invoke_capability(user_input)
    if cap_response is not None:
        _update_audio_loop_status(node_id, "responding")
        voice.speak_and_print(cap_response)
        _update_audio_loop_status(node_id, "cooling_down")
        if continuity is not None:
            continuity.track_execution(
                command=user_input,
                outcome="success",
                adapter_used="capability",
            )
        _record_transcript(node_id, cap_response, source="system")
        return True

    _update_audio_loop_status(node_id, "responding")

    t0 = time.time()
    response = _try_gateway(user_input)
    adapter = "gateway"
    if response is None:
        response = _try_voice_route(user_input, voice)
        adapter = "voice_route"
    if response is None:
        response = "No LLM provider available. Run `umh diag` to check."
        adapter = "none"
    elapsed_ms = (time.time() - t0) * 1000

    if continuity is not None:
        continuity.track_execution(
            command=user_input,
            outcome="success" if adapter != "none" else "failure",
            adapter_used=adapter,
            duration_ms=elapsed_ms,
        )

    print(f"\n{persona_name} > {response}\n")
    voice.speak_streaming(response)
    _record_transcript(node_id, response, source="assistant")
    _update_audio_loop_status(node_id, "cooling_down")

    return True


def run_interaction_loop(
    mode_state: ModeState,
    session_id: str,
    text_only: bool = False,
    node_id: str = "workstation_local",
    mic: Any = None,
    perception: Any = None,
    continuity: Any = None,
    scheduler: Any = None,
    inference_checker: Any = None,
) -> int:
    """Main interaction loop — races voice and text input.

    When mic is provided:
      stdin runs in a background thread, voice runs via mic.get_transcript().
      Main loop polls both at 50ms intervals.

    When mic is None (text-only):
      Simple blocking input() loop — same behavior as Sprint 1.

    When perception is provided:
      Auto-AWAY timeout is checked each poll cycle.
      Welcome-back message is spoken when operator returns.

    When continuity is provided:
      Every execution and mode transition is tracked for session resume.
    """
    voice = VoiceOutput(text_only=text_only)
    persona_name = os.environ.get("UMH_PERSONA_NAME", "UMH")
    prompt = "you > "

    if perception is not None:
        perception.set_welcome_back_callback(
            lambda: voice.speak_and_print(f"Welcome back. {mode_state.display()}")
        )

    if mic is not None and mic.is_listening:
        print(f"[{persona_name}] Ready. Voice + text input active. Type 'help' for commands.\n")
    else:
        print(f"[{persona_name}] Ready. Type 'help' for commands, 'exit' to quit.\n")

    if mic is None or not mic.is_listening:
        return _text_only_loop(
            mode_state,
            voice,
            persona_name,
            prompt,
            node_id,
            perception,
            continuity,
            scheduler,
            inference_checker,
        )

    return _voice_text_loop(
        mode_state,
        voice,
        persona_name,
        prompt,
        node_id,
        mic,
        perception,
        continuity,
        scheduler,
        inference_checker,
    )


def _text_only_loop(
    mode_state: ModeState,
    voice: VoiceOutput,
    persona_name: str,
    prompt: str,
    node_id: str,
    perception: Any = None,
    continuity: Any = None,
    scheduler: Any = None,
    inference_checker: Any = None,
) -> int:
    while True:
        if inference_checker is not None:
            suggestion = inference_checker.check(mode_state.primary_profile.value)
            if suggestion:
                print(f"  [inference] {suggestion}")

        try:
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not _process_input(
            user_input,
            "manual",
            mode_state,
            voice,
            node_id,
            persona_name,
            perception,
            continuity,
        ):
            break

    _sync_operator_exit(node_id)
    if scheduler is not None:
        scheduler.stop()
    if continuity is not None:
        continuity.save_on_exit()
    if perception is not None:
        perception.stop_all()
    return 0


def _voice_text_loop(
    mode_state: ModeState,
    voice: VoiceOutput,
    persona_name: str,
    prompt: str,
    node_id: str,
    mic: Any,
    perception: Any = None,
    continuity: Any = None,
    scheduler: Any = None,
    inference_checker: Any = None,
) -> int:
    """Concurrent voice + text loop.

    Stdin runs in a daemon thread. Main thread polls both stdin queue
    and mic transcript queue at ~50ms intervals. Voice input gets a
    "[voice]" prefix in the transcript for debugging.

    Perception router is polled each cycle for auto-AWAY timeout.
    Continuity bridge tracks every execution for session resume.
    """
    text_queue: queue.Queue[str | None] = queue.Queue()
    stop_event = threading.Event()
    _start_stdin_thread(text_queue, stop_event, prompt)

    _update_audio_loop_status(node_id, "primed")

    try:
        while not stop_event.is_set():
            if perception is not None:
                perception.check_away_timeout()

            if inference_checker is not None:
                suggestion = inference_checker.check(mode_state.primary_profile.value)
                if suggestion:
                    print(f"  [inference] {suggestion}")

            text_input: str | None = None
            try:
                text_input = text_queue.get_nowait()
            except queue.Empty:
                pass

            if text_input is not None:
                if not _process_input(
                    text_input,
                    "manual",
                    mode_state,
                    voice,
                    node_id,
                    persona_name,
                    perception,
                    continuity,
                ):
                    break
                sys.stdout.write(prompt)
                sys.stdout.flush()
                continue

            voice_input = mic.get_transcript()
            if voice_input is not None:
                if voice.is_speaking:
                    voice.interrupt()
                    print("  [interrupted]")
                print(f"  [voice] {voice_input}")
                if not _process_input(
                    voice_input,
                    "voice",
                    mode_state,
                    voice,
                    node_id,
                    persona_name,
                    perception,
                    continuity,
                ):
                    break
                sys.stdout.write(prompt)
                sys.stdout.flush()
                continue

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        stop_event.set()
        _update_audio_loop_status(node_id, "inactive")
        mic.stop()
        _sync_operator_exit(node_id)
        if scheduler is not None:
            scheduler.stop()
        if continuity is not None:
            continuity.save_on_exit()
        if perception is not None:
            perception.stop_all()

    return 0
