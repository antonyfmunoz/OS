"""P4S-31D lane G — voice_server hardening acceptance tests.

Covers:
  1. HTTP /health on the WS port (process_request hook, unit-tested directly)
  2. systemd watchdog integration (raw sd_notify, no pip dependency)
  3. Graceful shutdown (SIGTERM handler resolves the stop future)
  4. Bounded logs — no transcript content at INFO+ (AST static scan)
  5. No transcript leakage — no file-write of transcript content (AST static scan)
  6. No consent-file access — the server is a pure STT/TTS bridge (static scan)
  7. Unit file invariants — Type=notify, WatchdogSec, Restart, CPUQuota, MemoryMax
  8. WS protocol message shapes unchanged (cockpit client depends on them)
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import json
import os
import signal
import socket
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SERVER_PATH = _REPO_ROOT / "umh" / "voice_server.py"
_UNIT_PATH = _REPO_ROOT / "infra" / "systemd" / "umh-voice-server.service"


def _load_server_module():
    spec = importlib.util.spec_from_file_location("voice_server_under_test", _SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def vs():
    return _load_server_module()


@pytest.fixture(scope="module")
def source() -> str:
    return _SERVER_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def tree(source) -> ast.Module:
    return ast.parse(source)


class _FakeRequest:
    def __init__(self, path: str):
        self.path = path


# ── 1. Health endpoint ─────────────────────────────────────────────────────────


def test_process_request_exists_and_is_wired(vs, source):
    assert callable(vs.process_request)
    assert "process_request=process_request" in source, (
        "process_request must be passed to websockets.serve"
    )


def test_health_returns_200_json_with_required_keys(vs):
    resp = vs.process_request(None, _FakeRequest("/health"))
    assert resp is not None
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/json"
    payload = json.loads(resp.body.decode("utf-8"))
    assert set(payload) == {
        "status",
        "uptime_s",
        "stt_engine",
        "tts_provider",
        "active_sessions",
    }
    assert payload["status"] == "ok"
    assert isinstance(payload["uptime_s"], (int, float)) and payload["uptime_s"] >= 0
    assert payload["stt_engine"] in ("groq", "faster-whisper")
    assert payload["tts_provider"] in ("kokoro", "espeak")
    assert isinstance(payload["active_sessions"], int)


def test_health_handles_query_string(vs):
    resp = vs.process_request(None, _FakeRequest("/health?probe=1"))
    assert resp is not None and resp.status_code == 200


def test_ws_upgrade_path_untouched(vs):
    # Returning None lets the normal WebSocket handshake proceed.
    assert vs.process_request(None, _FakeRequest("/voice")) is None
    assert vs.process_request(None, _FakeRequest("/")) is None
    assert vs.process_request(None, _FakeRequest("/healthz")) is None


def test_health_payload_counts_active_sessions(vs):
    vs.ACTIVE_SESSIONS.clear()
    assert vs.build_health_payload()["active_sessions"] == 0
    sentinel = object()
    vs.ACTIVE_SESSIONS.add(sentinel)
    try:
        assert vs.build_health_payload()["active_sessions"] == 1
    finally:
        vs.ACTIVE_SESSIONS.discard(sentinel)


# ── 2. systemd watchdog (raw sd_notify, no pip dependency) ────────────────────


def test_sd_notify_noop_without_notify_socket(vs, monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    assert vs.sd_notify("READY=1") is False


def test_sd_notify_sends_datagram(vs, monkeypatch, tmp_path):
    sock_path = str(tmp_path / "notify.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        server.bind(sock_path)
        server.settimeout(2)
        monkeypatch.setenv("NOTIFY_SOCKET", sock_path)
        assert vs.sd_notify("READY=1") is True
        assert server.recv(64) == b"READY=1"
        assert vs.sd_notify("WATCHDOG=1") is True
        assert server.recv(64) == b"WATCHDOG=1"
    finally:
        server.close()


def test_watchdog_keepalive_exits_when_not_under_systemd(vs, monkeypatch):
    monkeypatch.delenv("WATCHDOG_USEC", raising=False)
    asyncio.run(asyncio.wait_for(vs.watchdog_keepalive(), timeout=2))


def test_watchdog_keepalive_pings_at_half_interval(vs, monkeypatch, tmp_path):
    sock_path = str(tmp_path / "notify.sock")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        server.bind(sock_path)
        server.settimeout(3)
        monkeypatch.setenv("NOTIFY_SOCKET", sock_path)
        monkeypatch.setenv("WATCHDOG_USEC", "2000000")  # 2s -> keepalive every 1s
        monkeypatch.setenv("WATCHDOG_PID", str(os.getpid()))

        async def run_briefly():
            task = asyncio.ensure_future(vs.watchdog_keepalive())
            await asyncio.sleep(1.3)
            task.cancel()

        asyncio.run(run_briefly())
        assert server.recv(64) == b"WATCHDOG=1"
    finally:
        server.close()


# ── 3. Graceful shutdown ───────────────────────────────────────────────────────


def test_sigterm_handler_registered_and_resolves_stop(vs):
    async def scenario():
        loop = asyncio.get_running_loop()
        stop = loop.create_future()
        vs.install_signal_handlers(loop, stop)
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                assert signal.getsignal(sig) not in (signal.SIG_DFL, signal.SIG_IGN), (
                    "%s handler must be registered" % sig.name
                )
            os.kill(os.getpid(), signal.SIGTERM)
            await asyncio.wait_for(stop, timeout=5)
        finally:
            loop.remove_signal_handler(signal.SIGTERM)
            loop.remove_signal_handler(signal.SIGINT)

    asyncio.run(scenario())


def test_shutdown_closes_sessions_with_going_away(source):
    assert "code=1001" in source, "graceful shutdown must close WS sessions with 1001 (going away)"
    assert "STOPPING=1" in source


# ── 4 + 5. Bounded logs / no transcript leakage (AST static scans) ────────────

_CONTENT_NAMES = {"text", "spoken"}
_INFO_PLUS = {"info", "warning", "error", "exception", "critical"}


def _refs_content(node: ast.AST) -> bool:
    """True if the subtree references transcript content (text/spoken).

    len(text) is pruned — a character count is metadata, not content.
    """
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
        return False
    if isinstance(node, ast.Name) and node.id in _CONTENT_NAMES:
        return True
    return any(_refs_content(child) for child in ast.iter_child_nodes(node))


def _log_calls(tree: ast.Module):
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "log"
        ):
            yield node.func.attr, node


def test_no_transcript_content_logged_at_info_or_above(tree):
    violations = []
    for level, call in _log_calls(tree):
        if level in _INFO_PLUS:
            for arg in call.args:
                if _refs_content(arg):
                    violations.append(
                        "line %d: log.%s references transcript content" % (call.lineno, level)
                    )
    assert not violations, "\n".join(violations)


def test_debug_previews_are_truncated_to_40_chars(vs, source):
    assert vs.TRANSCRIPT_PREVIEW_CHARS <= 40
    # Every DEBUG preview of content must go through the bounded slice.
    for line in source.splitlines():
        if "log.debug" in line and ("text[" in line or "spoken[" in line):
            assert "TRANSCRIPT_PREVIEW_CHARS" in line, (
                "DEBUG preview must use the bounded TRANSCRIPT_PREVIEW_CHARS slice: %s"
                % line.strip()
            )


def test_no_file_write_of_transcript_content(tree):
    """No .write()/.writelines()/json.dump() call may receive transcript text."""
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_write_method = isinstance(func, ast.Attribute) and func.attr in (
            "write",
            "writelines",
            "writeframes",
            "dump",
        )
        if is_write_method and any(_refs_content(a) for a in node.args):
            violations.append("line %d: file-write of transcript content" % node.lineno)
    assert not violations, "\n".join(violations)


def _code_string_constants(tree: ast.Module):
    """All string constants in the module, EXCLUDING docstrings.

    Docstrings legitimately document the privacy boundary (they may name
    consent files or DEX endpoints while stating the server never touches
    them); only string constants in executable code are enforcement targets.
    """
    docstring_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstring_ids.add(id(node.body[0].value))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            yield node


def test_transcript_only_sent_to_requesting_ws_client(source, tree):
    # The only outbound surfaces are: the requesting WS client (send_json /
    # ws.send), the STT provider (audio, not transcript), and the TTS
    # provider (client-requested tts_request text). No HTTP POST of
    # transcript text to any other endpoint may exist.
    assert "requests.post" not in source
    assert "httpx" not in source
    for node in _code_string_constants(tree):
        assert "/dex/converse" not in node.value, (
            "line %d: DEX routing belongs to the browser client, never the "
            "voice server" % node.lineno
        )


def test_no_transcript_in_process_argv(source):
    # espeak must read text from stdin, never argv (visible in `ps`).
    assert "--stdin" in source
    assert "path, text[" not in source, "espeak must not receive text as an argv element"


# ── 6. No consent-file access (pure STT/TTS bridge) ───────────────────────────


def test_no_consent_file_reference_in_voice_server(tree):
    # No consent-store path, grant type, or consent-named string may appear
    # in any EXECUTABLE code path (docstrings documenting the boundary are
    # exempt — see _code_string_constants). The server must never read or
    # write data/umh/voice/consent_grants.json; consent is enforced
    # client+API side and this process is a pure STT/TTS bridge.
    for node in _code_string_constants(tree):
        value = node.value.lower()
        for token in ("consent", "data/umh/voice"):
            assert token not in value, (
                "line %d: consent-store reference %r in voice_server code — "
                "consent is enforced client+API side" % (node.lineno, token)
            )
    # No identifier may reference consent either (e.g. load_consent_grants).
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert "consent" not in node.id.lower(), (
                "line %d: consent-named identifier in voice_server" % node.lineno
            )
        if isinstance(node, ast.Attribute):
            assert "consent" not in node.attr.lower(), (
                "line %d: consent-named attribute in voice_server" % node.lineno
            )


# ── 7. Unit file invariants ────────────────────────────────────────────────────


def test_unit_file_hardening_invariants():
    assert _UNIT_PATH.exists()
    unit = _UNIT_PATH.read_text(encoding="utf-8")
    assert "Type=notify" in unit
    assert "WatchdogSec=" in unit
    assert "Restart=on-failure" in unit
    assert "RestartSec=" in unit
    assert "StartLimitIntervalSec=" in unit
    assert "StartLimitBurst=" in unit
    # CPU Gate Law bounds (do not raise without re-measuring):
    assert "CPUQuota=150%" in unit
    assert "MemoryMax=1G" in unit
    assert "/health" in unit, "unit must document the health check"


def test_no_raw_subprocess_in_voice_server(source):
    assert "subprocess.run(" not in source
    assert "subprocess.Popen(" not in source
    assert "subprocess.check_call(" not in source
    assert "gated_subprocess_run" in source, "espeak fallback must go through the CPU gate"


# ── 8. WS protocol shapes unchanged (cockpit client contract) ─────────────────


def test_ws_protocol_message_types_unchanged(source):
    for msg_type in (
        '"type": "connected"',
        '"type": "transcript"',
        '"type": "tts_status"',
        '"type": "tts_error"',
        '"type": "vad_status"',
        '"type": "audio_level"',
        '"type": "error"',
    ):
        assert msg_type in source, "protocol message shape missing: %s" % msg_type
    for inbound in ("mic_start", "mic_stop", "tts_request", "tts_cancel"):
        assert '"%s"' % inbound in source


def test_server_module_compiles():
    compile(_SERVER_PATH.read_text(encoding="utf-8"), str(_SERVER_PATH), "exec")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
