"""P4S31 Voice Convergence — the rival voice runtimes are RETIRED (Commit 4).

Proves the cutover deleted every rival voice path: operator_api's _voice_respond
/_generate_tts/voice_transcript branch, the phantom :8096 proxy + its env, the
standalone voice_server.py, its systemd unit, and the docker-compose upstream env.
The ONE voice ingress is /api/umh/voice/ws behind the API backend.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROOT = Path(__file__).resolve().parent.parent


def test_no_rival_voice_runtime_in_operator_api() -> None:
    src = (_ROOT / "services" / "operator_api.py").read_text(encoding="utf-8")
    assert "async def _voice_respond" not in src
    assert "def _generate_tts" not in src
    assert "/api/voice/tts" not in src
    assert 'msg_type == "voice_transcript"' not in src


def test_no_phantom_8096_proxy() -> None:
    src = (_ROOT / "transports" / "api" / "cockpit_core_routes.py").read_text(encoding="utf-8")
    assert "_VOICE_WS_UPSTREAM" not in src
    assert "voice_ws_proxy" not in src
    # the /voice/ws path is no longer bound here (it would double-bind the
    # governed /api/umh/voice/ws)
    assert '@ws_router.websocket("/voice/ws")' not in src


def test_voice_server_retired() -> None:
    assert not (_ROOT / "umh" / "voice_server.py").exists()
    assert not (_ROOT / "infra" / "systemd" / "umh-voice-server.service").exists()


def test_compose_no_voice_ws_upstream() -> None:
    compose = (_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "VOICE_WS_UPSTREAM" not in compose
    assert "8096" not in compose


def test_nginx_voice_repointed_to_api_backend() -> None:
    nginx = (_ROOT / "cockpit" / "nginx.conf.template").read_text(encoding="utf-8")
    # the voice ws location proxies to the API backend, not :8096
    assert "proxy_pass http://api_backend/api/umh/voice/ws;" in nginx
    assert "8096" not in nginx


def test_start_sh_no_8096_tunnel() -> None:
    start = (_ROOT / "cockpit" / "start.sh").read_text(encoding="utf-8")
    assert "8096" not in start


def test_bridge_is_compat_shim() -> None:
    # bridge/voice_session.py no longer DEFINES the record/store; it re-exports.
    src = (_ROOT / "substrate" / "execution" / "bridge" / "voice_session.py").read_text(
        encoding="utf-8"
    )
    assert "from substrate.execution.voice.store import" in src
    # VoiceSessionRuntime is KEPT (the 10 importers still need it)
    assert "class VoiceSessionRuntime" in src
    # the record dataclass is NOT redefined here (only the runtime remains)
    assert "class VoiceSessionStore" not in src


def test_bridge_aliases_point_to_canonical() -> None:
    from substrate.execution.bridge.voice_session import (
        VoiceSession,
        VoiceSessionStatus,
    )
    from substrate.execution.voice.store import (
        VoiceSessionRecord,
        VoiceSessionRecordStatus,
    )

    assert VoiceSession is VoiceSessionRecord
    assert VoiceSessionStatus is VoiceSessionRecordStatus
