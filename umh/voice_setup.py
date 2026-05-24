"""Voice setup — XTTS v2 reference capture + wake command configuration.

Phase 9 of UMH instance instantiation. Configures:
  1. Persona voice selection (how the AI sounds talking to you)
  2. Voice cloning reference capture (your voice for AI to use externally)
  3. Wake phrase configuration (what triggers the AI)

Voice cloning requires:
  - Coqui TTS with XTTS v2 model (~1.5GB, Apache 2.0)
  - 6-30 second reference WAV of the operator speaking
  - Captures via sounddevice, saves to data/voice/reference.wav
"""

from __future__ import annotations

import importlib.util
import logging
import os
import wave

from umh import UMH_ROOT

logger = logging.getLogger(__name__)
VOICE_DIR = os.path.join(UMH_ROOT, "data", "voice")
REFERENCE_WAV = os.path.join(VOICE_DIR, "reference.wav")

SAMPLE_RATE = 16000
CHANNELS = 1
BYTES_PER_SAMPLE = 2


def run_voice_setup_flow() -> int:
    """Interactive voice setup flow via stdin."""
    print()
    print("=" * 50)
    print("  Voice Setup")
    print("=" * 50)
    print()

    # Step 1: Wake phrase
    wake_phrase = _configure_wake_phrase()

    # Step 2: Voice cloning reference
    _configure_voice_clone()

    # Step 3: Voice mode preference
    voice_mode = _configure_voice_mode()

    # Save preferences
    _save_voice_preferences(wake_phrase, voice_mode)

    print()
    print("Voice setup complete.")
    print()
    return 0


def _configure_wake_phrase() -> str:
    """Configure the wake phrase that activates the AI."""
    print("Wake Phrase Configuration")
    print("-" * 30)
    print()
    print("The wake phrase activates your AI by voice.")
    print("Examples: DEX, JARVIS, HEY UMH, COMPUTER")
    print()

    try:
        phrase = input("  Wake phrase (or press Enter for none): ").strip()
    except (EOFError, KeyboardInterrupt):
        phrase = ""

    if phrase:
        print(f'\n  Wake phrase set to: "{phrase}"')

        # Map to role hint if applicable
        try:
            from substrate.execution.bridge.wake_producer import resolve_role_hint

            hint = resolve_role_hint(phrase)
            if hint:
                print(f"  Role hint: {hint}")
        except (ImportError, Exception) as exc:
            logger.debug("Role hint lookup failed: %s", exc)
    else:
        print("\n  No wake phrase configured. Use text input or push-to-talk.")

    print()
    return phrase


def _configure_voice_clone() -> bool:
    """Offer voice cloning reference capture."""
    try:
        from umh.profile import ProfileManager

        prefs = ProfileManager().get_preferences()
        if prefs.voice_clone_attempted:
            return False
    except Exception as exc:
        logger.debug("Voice clone preference check failed: %s", exc)

    print("Voice Cloning")
    print("-" * 30)
    print()
    print("Voice cloning lets the AI speak AS YOU to other people")
    print("(calls, meetings, outreach). It does NOT change how")
    print("the AI sounds when talking to you.")
    print()

    # Check if XTTS is available
    xtts_available = importlib.util.find_spec("TTS") is not None

    if not xtts_available:
        print("  XTTS v2 not installed. Voice cloning unavailable.")
        print("  Install with: pip install TTS")
        print("  (Requires ~1.5GB for the model)")
        print()
        try:
            from umh.profile import ProfileManager

            pm = ProfileManager()
            prefs = pm.get_preferences()
            prefs.voice_clone_attempted = True
            pm.save_preferences(prefs)
        except Exception as exc:
            logger.debug("Failed to save voice clone preference: %s", exc)
        return False

    # Check if mic is available
    mic_available = importlib.util.find_spec("sounddevice") is not None

    if not mic_available:
        print("  Microphone not available (sounddevice not installed).")
        print("  You can provide a reference WAV file instead.")
        print()

        try:
            wav_path = input(
                "  Path to reference WAV (6-30s of your voice, or Enter to skip): "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            wav_path = ""

        if wav_path and os.path.exists(wav_path):
            return _save_reference_wav(wav_path)
        print("  Skipping voice cloning.")
        print()
        return False

    try:
        choice = input("  Record voice reference now? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        choice = ""

    if choice != "y":
        print("  Skipping voice cloning. Run `umh voice-setup` later.")
        print()
        return False

    return _record_reference()


def _record_reference() -> bool:
    """Record a voice reference via microphone."""
    if importlib.util.find_spec("numpy") is None or importlib.util.find_spec("sounddevice") is None:
        print("  sounddevice/numpy not available.")
        return False
    try:
        import sounddevice as sd
    except ImportError:
        print("  sounddevice failed to load.")
        return False

    duration = 10
    print()
    print(f"  Recording {duration} seconds of your voice...")
    print("  Speak naturally — read something aloud or describe your day.")
    print("  Press Enter to start recording.")

    try:
        input()
    except (EOFError, KeyboardInterrupt):
        return False

    print("  Recording... (speak now)")

    try:
        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
        )
        sd.wait()
    except Exception as exc:
        print(f"  Recording failed: {exc}")
        return False

    # Save to WAV
    os.makedirs(VOICE_DIR, exist_ok=True)
    try:
        with wave.open(REFERENCE_WAV, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(BYTES_PER_SAMPLE)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio.tobytes())
        print(f"  Reference saved to {REFERENCE_WAV}")
        print()
        return True
    except Exception as exc:
        print(f"  Save failed: {exc}")
        return False


def _save_reference_wav(source_path: str) -> bool:
    """Copy a user-provided WAV file as the voice reference."""
    import shutil

    os.makedirs(VOICE_DIR, exist_ok=True)
    try:
        shutil.copy2(source_path, REFERENCE_WAV)
        print(f"  Reference copied to {REFERENCE_WAV}")
        print()
        return True
    except Exception as exc:
        print(f"  Copy failed: {exc}")
        return False


def _configure_voice_mode() -> str:
    """Select default voice input mode."""
    print("Voice Input Mode")
    print("-" * 30)
    print()
    print("  1. Ambient (always-on, VAD-gated)")
    print("  2. Push-to-talk (hotkey-activated)")
    print("  3. Text-only (no microphone)")
    print()

    try:
        choice = input("  Select mode [1/2/3]: ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "3"

    mode_map = {"1": "ambient", "2": "push_to_talk", "3": "text_only"}
    mode = mode_map.get(choice, "text_only")
    print(f"  Voice mode: {mode.replace('_', '-')}")
    print()
    return mode


def _save_voice_preferences(wake_phrase: str, voice_mode: str) -> None:
    """Save voice preferences to profile."""
    try:
        from umh.profile import ProfileManager

        pm = ProfileManager()
        prefs = pm.get_preferences()
        prefs.wake_phrase = wake_phrase
        prefs.voice_mode = voice_mode
        pm.save_preferences(prefs)
        logger.info("Voice preferences saved")
    except Exception as exc:
        logger.debug("Failed to save voice preferences: %s", exc)
        # Fallback: save to env
        if wake_phrase:
            os.environ["UMH_WAKE_PHRASE"] = wake_phrase
        os.environ["UMH_VOICE_MODE"] = voice_mode


def has_voice_reference() -> bool:
    """Check if a voice clone reference WAV exists."""
    return os.path.exists(REFERENCE_WAV)


def get_reference_path() -> str | None:
    """Get the path to the voice reference WAV, if it exists."""
    if os.path.exists(REFERENCE_WAV):
        return REFERENCE_WAV
    return None
