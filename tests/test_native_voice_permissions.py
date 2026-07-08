"""P4S31 Voice Convergence — native mic permissions + runtime-derived identity (Commit 6).

Proves the packaged native shells declare mic permission (so the WebView
getUserMedia prompt fires) and that the capture surface label / device id are
derived at runtime, not hardcoded to 'desktop_browser'.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROOT = Path(__file__).resolve().parent.parent


def test_ios_declares_microphone_usage() -> None:
    plist = (_ROOT / "cockpit" / "ios" / "App" / "App" / "Info.plist").read_text(encoding="utf-8")
    assert "NSMicrophoneUsageDescription" in plist


def test_android_declares_record_audio() -> None:
    manifest = (
        _ROOT / "cockpit" / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    ).read_text(encoding="utf-8")
    assert "android.permission.RECORD_AUDIO" in manifest


def test_source_label_uses_capacitor_platform() -> None:
    adapter = (
        _ROOT / "cockpit" / "src" / "renderer" / "api" / "platform-voice-adapter.ts"
    ).read_text(encoding="utf-8")
    # Capacitor native platform is consulted for the source label.
    assert "getPlatform" in adapter
    assert "isNativePlatform" in adapter


def test_no_hardcoded_desktop_browser_device_id() -> None:
    adapter = (
        _ROOT / "cockpit" / "src" / "renderer" / "api" / "platform-voice-adapter.ts"
    ).read_text(encoding="utf-8")
    # The device-id fallback must NOT be the bare 'desktop_browser' string — it is
    # runtime-derived now. (The adapter's own `platform: 'desktop_browser'`
    # identity const is a different thing and is allowed.)
    assert "return 'desktop_browser'" not in adapter
    assert "_device`" in adapter  # runtime-derived fallback id


def test_electron_scaffold_points_at_governed_ws() -> None:
    src = (_ROOT / "cockpit" / "src" / "main" / "desktop-voice-adapter.ts").read_text(
        encoding="utf-8"
    )
    # the scaffold's target is the governed WS, not the retired standalone server
    assert "8096" not in src
    assert "/api/umh/voice/ws" in src
