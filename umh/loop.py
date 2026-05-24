"""Interaction loop — text + voice input with concurrent processing.

Sprint 1: text-only stdin loop.
Sprint 2: voice input via AmbientMic/PushToTalkMic racing against stdin.
Sprint 4: perception integration (webcam, workspace, metrics).
Sprint 6: personality command, sensing adapter display.

When voice is enabled, stdin runs in a background thread and the main loop
polls both the mic transcript queue and the stdin queue. When voice is
disabled, falls back to the simple blocking input() loop from Sprint 1.

Perception router is polled each cycle to check auto-AWAY timeout.
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

    if cmd.command in ("pending", "approve", "reject"):
        return "Approval system not yet wired"

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

    return f"Unknown command: {cmd.command}"


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
) -> bool:
    """Process a single input line. Returns True to continue, False to exit."""
    if not user_input:
        return True

    _record_transcript(node_id, user_input, source=source)
    _update_audio_loop_status(node_id, "listening")

    cmd = parse_command(user_input, mode_state)
    if cmd.handled:
        response = _handle_system_command(cmd, mode_state, voice, perception=perception)
        if response == "__EXIT__":
            _update_audio_loop_status(node_id, "inactive")
            if perception is not None:
                perception.stop_all()
            voice.speak_and_print("State saved. Goodbye.")
            return False
        if response:
            _update_audio_loop_status(node_id, "responding")
            voice.speak_and_print(response)
            _update_audio_loop_status(node_id, "cooling_down")
        _record_transcript(node_id, response or "(no response)", source="system")
        return True

    _update_audio_loop_status(node_id, "responding")

    response = _try_gateway(user_input)
    if response is None:
        response = _try_voice_route(user_input, voice)
    if response is None:
        response = "No LLM provider available. Run `umh diag` to check."

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
        return _text_only_loop(mode_state, voice, persona_name, prompt, node_id, perception)

    return _voice_text_loop(mode_state, voice, persona_name, prompt, node_id, mic, perception)


def _text_only_loop(
    mode_state: ModeState,
    voice: VoiceOutput,
    persona_name: str,
    prompt: str,
    node_id: str,
    perception: Any = None,
) -> int:
    while True:
        try:
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not _process_input(
            user_input, "manual", mode_state, voice, node_id, persona_name, perception
        ):
            break

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
) -> int:
    """Concurrent voice + text loop.

    Stdin runs in a daemon thread. Main thread polls both stdin queue
    and mic transcript queue at ~50ms intervals. Voice input gets a
    "[voice]" prefix in the transcript for debugging.

    Perception router is polled each cycle for auto-AWAY timeout.
    """
    text_queue: queue.Queue[str | None] = queue.Queue()
    stop_event = threading.Event()
    _start_stdin_thread(text_queue, stop_event, prompt)

    _update_audio_loop_status(node_id, "primed")

    try:
        while not stop_event.is_set():
            if perception is not None:
                perception.check_away_timeout()

            text_input: str | None = None
            try:
                text_input = text_queue.get_nowait()
            except queue.Empty:
                pass

            if text_input is not None:
                if not _process_input(
                    text_input, "manual", mode_state, voice, node_id, persona_name, perception
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
                    voice_input, "voice", mode_state, voice, node_id, persona_name, perception
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
        if perception is not None:
            perception.stop_all()

    return 0
