"""Platform audio I/O — play sounds, detect audio capabilities."""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess

logger = logging.getLogger(__name__)

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
BOOT_CLAP_PATH = os.path.join(UMH_ROOT, "data", "audio", "boot_clap.wav")


def _find_player() -> str | None:
    if platform.system() == "Darwin" and shutil.which("afplay"):
        return "afplay"
    if shutil.which("aplay"):
        return "aplay"
    if shutil.which("paplay"):
        return "paplay"
    return None


def play_sound(path: str) -> bool:
    if not os.path.exists(path):
        logger.debug("Audio file not found: %s", path)
        return False

    player = _find_player()
    if not player:
        logger.debug("No audio player available")
        return False

    try:
        subprocess.run([player, path], capture_output=True, timeout=10)
        return True
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("Audio playback failed: %s", exc)
        return False


def play_boot_clap() -> bool:
    return play_sound(BOOT_CLAP_PATH)


def can_play_audio() -> bool:
    return _find_player() is not None
