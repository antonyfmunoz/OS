"""Interaction loop — text-mode (Sprint 1). Voice input added in Sprint 2."""

from __future__ import annotations

import logging
import os
import sys

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


def _handle_system_command(cmd: CommandResult, mode_state: ModeState, voice: VoiceOutput) -> str:
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

    if cmd.command in ("pending", "approve", "reject"):
        return "Approval system not yet wired (Sprint 3+)"

    if cmd.command in ("push_to_talk", "always_on", "webcam_on", "webcam_off", "mesh_status"):
        return f"{cmd.command} not yet implemented"

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
  exit / bye          — save state and exit"""


def run_interaction_loop(
    mode_state: ModeState,
    session_id: str,
    text_only: bool = False,
    node_id: str = "workstation_local",
) -> int:
    voice = VoiceOutput(text_only=text_only)
    persona_name = os.environ.get("UMH_PERSONA_NAME", "UMH")

    print(f"[{persona_name}] Ready. Type 'help' for commands, 'exit' to quit.\n")

    while True:
        try:
            user_input = input(f"{'you'} > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not user_input:
            continue

        _record_transcript(node_id, user_input, source="manual")

        cmd = parse_command(user_input, mode_state)
        if cmd.handled:
            response = _handle_system_command(cmd, mode_state, voice)
            if response == "__EXIT__":
                voice.speak_and_print("State saved. Goodbye.")
                break
            if response:
                voice.speak_and_print(response)
            _record_transcript(node_id, response or "(no response)", source="system")
            continue

        response = _try_gateway(user_input)
        if response is None:
            response = _try_voice_route(user_input, voice)
        if response is None:
            response = "No LLM provider available. Run `umh diag` to check."

        print(f"\n{persona_name} > {response}\n")
        voice.speak(response)
        _record_transcript(node_id, response, source="assistant")

    return 0
