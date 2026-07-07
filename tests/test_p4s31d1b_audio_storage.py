"""P4S-31D1-B lane F — audio artifact storage law tests.

Contract: data/umh/voice/voice_message_contract.json
  - types.AudioArtifactRef (artifact_id, url, content_type, size_bytes, sha256)
  - types.AudioArtifactRef.storage_law (auth-scoped retrieval, no secrets,
    retention with chat history, audio bytes never logged)
  - types.VoiceDiagnostics.logging_law (no transcript/content at INFO+)

Covers:
  1. Upload route auth-gated (static + direct-call).
  2. Audio type + size validation (audio/webm, audio/wav; 25MB cap).
  3. sha256 + size_bytes in the upload response.
  4. Retrieval auth-gated (parent-router Clerk gate, no static-mount bypass).
  5. Logging law — no content/filename logging at INFO+ on the media paths.
  6. No plaintext secrets in the module.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

import pytest

_WORKTREE = str(Path(__file__).resolve().parent.parent)
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

_CHAT_ROUTES_PATH = Path(_WORKTREE) / "transports" / "api" / "cockpit_chat_routes.py"
_COCKPIT_PATH = Path(_WORKTREE) / "transports" / "api" / "cockpit.py"

_SRC = _CHAT_ROUTES_PATH.read_text()
_COCKPIT_SRC = _COCKPIT_PATH.read_text()


# ── Test app plumbing ─────────────────────────────────────────────────────────


def _build_app(authorized: bool):
    """Build a FastAPI app around the chat router with a stub operator dep."""
    from fastapi import FastAPI, HTTPException

    import transports.api.cockpit_chat_routes as chat_mod

    def _stub_operator_dep():
        if not authorized:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return "operator"

    app = FastAPI()
    app.include_router(chat_mod._build_router(_stub_operator_dep))
    return app


@pytest.fixture()
def media_env(tmp_path, monkeypatch):
    """Point UMH_ROOT at a temp dir so uploads never touch real chat_media."""
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture()
def client(media_env):
    from fastapi.testclient import TestClient

    return TestClient(_build_app(authorized=True))


@pytest.fixture()
def anon_client(media_env):
    from fastapi.testclient import TestClient

    return TestClient(_build_app(authorized=False), raise_server_exceptions=False)


_WEBM_BYTES = b"\x1a\x45\xdf\xa3" + os.urandom(2048)  # EBML magic + noise


def _upload(client, content: bytes = _WEBM_BYTES, content_type: str = "audio/webm"):
    return client.post(
        "/chat/upload",
        files={"file": ("recording.webm", content, content_type)},
    )


# ── 1. Upload + delete routes are auth-gated ─────────────────────────────────


def test_upload_route_declares_operator_auth_static():
    """POST /chat/upload carries the route-level operator dependency."""
    m = re.search(r'@r\.post\("/chat/upload",\s*dependencies=auth\)', _SRC)
    assert m, "POST /chat/upload must declare dependencies=auth (operator gate)"


def test_delete_route_declares_operator_auth_static():
    m = re.search(r'@r\.delete\("/chat/media/\{file_id\}",\s*dependencies=auth\)', _SRC)
    assert m, "DELETE /chat/media/{file_id} must declare dependencies=auth"


def test_upload_rejected_without_operator_auth(anon_client):
    resp = _upload(anon_client)
    assert resp.status_code == 401


def test_delete_rejected_without_operator_auth(anon_client):
    resp = anon_client.delete("/chat/media/deadbeef.weba")
    assert resp.status_code == 401


# ── 2. Audio type + size validation ──────────────────────────────────────────


def test_audio_webm_accepted(client):
    resp = _upload(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["media_type"] == "audio"
    assert body["content_type"] == "audio/webm"


def test_audio_wav_accepted(client):
    resp = _upload(client, content_type="audio/wav")
    assert resp.status_code == 200
    assert resp.json()["content_type"] == "audio/wav"


def test_codec_parameter_normalized(client):
    """MediaRecorder emits e.g. audio/webm;codecs=opus — must be accepted."""
    resp = _upload(client, content_type="audio/webm;codecs=opus")
    assert resp.status_code == 200
    assert resp.json()["content_type"] == "audio/webm"


def test_non_contract_audio_type_rejected(client):
    for bad in ("audio/mpeg", "audio/ogg", "application/octet-stream", "text/plain"):
        resp = _upload(client, content_type=bad)
        assert resp.status_code == 400, f"{bad} must be rejected"


def test_audio_size_cap_enforced(client, monkeypatch):
    import transports.api.cockpit_chat_routes as chat_mod

    monkeypatch.setattr(chat_mod, "MAX_AUDIO_UPLOAD_SIZE", 1024)
    resp = _upload(client, content=b"\x00" * 4096)
    assert resp.status_code == 413


def test_audio_cap_is_25mb_and_separate_from_media_cap():
    import transports.api.cockpit_chat_routes as chat_mod

    assert chat_mod.MAX_AUDIO_UPLOAD_SIZE == 25 * 1024 * 1024
    assert chat_mod.MAX_UPLOAD_SIZE == 50 * 1024 * 1024
    assert chat_mod.ALLOWED_AUDIO_TYPES == {"audio/webm", "audio/wav"}


def test_oversize_audio_leaves_no_partial_file(client, media_env, monkeypatch):
    import transports.api.cockpit_chat_routes as chat_mod

    monkeypatch.setattr(chat_mod, "MAX_AUDIO_UPLOAD_SIZE", 1024)
    _upload(client, content=b"\x00" * 4096)
    media_dir = media_env / "data" / "chat_media"
    leftovers = list(media_dir.glob("*")) if media_dir.is_dir() else []
    assert leftovers == [], f"partial upload not cleaned: {leftovers}"


def test_existing_image_upload_still_works(client):
    """Never break the existing image/video seam (regression guard)."""
    resp = client.post(
        "/chat/upload",
        files={"file": ("shot.png", b"\x89PNG\r\n" + os.urandom(256), "image/png")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["media_type"] == "image"
    assert body["sha256"]  # integrity fields are additive for all media


# ── 3. Integrity: sha256 + size_bytes in the response ────────────────────────


def test_upload_response_carries_audioartifactref_fields(client):
    resp = _upload(client)
    body = resp.json()
    assert body["size_bytes"] == len(_WEBM_BYTES)
    assert body["size"] == len(_WEBM_BYTES)  # legacy key preserved
    assert body["sha256"] == hashlib.sha256(_WEBM_BYTES).hexdigest()
    assert body["url"] == f"/api/umh/chat/media/{body['id']}"


def test_audio_artifact_id_non_guessable(client):
    resp = _upload(client)
    file_id = resp.json()["id"]
    stem, ext = file_id.rsplit(".", 1)
    assert ext == "weba"  # server-derived, never the client extension
    assert re.fullmatch(r"[0-9a-f]{32}", stem), "audio id must be 128-bit uuid4 hex"


def test_audio_extension_never_from_client_filename(client):
    """A hostile client filename must not leak into the stored name."""
    resp = client.post(
        "/chat/upload",
        files={"file": ("../../evil.mp4", _WEBM_BYTES, "audio/webm")},
    )
    assert resp.status_code == 200
    assert resp.json()["id"].endswith(".weba")


# ── 4. Retrieval auth-gated ───────────────────────────────────────────────────


def test_parent_router_clerk_gate_static():
    """/api/umh parent router requires Clerk auth; chat router is mounted
    under it — so GET /chat/media inherits the authenticated-session gate."""
    assert re.search(
        r'APIRouter\(prefix="/api/umh",\s*dependencies=\[Depends\(require_clerk_auth\)\]\)',
        _COCKPIT_SRC,
    ), "parent /api/umh router must carry require_clerk_auth"
    assert "router.include_router(cockpit_chat_routes.chat_router)" in _COCKPIT_SRC


def test_no_static_mount_of_chat_media():
    """data/chat_media must never be exposed via an unauthenticated static mount."""
    for path in (Path(_WORKTREE) / "transports" / "api").glob("*.py"):
        src = path.read_text()
        for m in re.finditer(r"StaticFiles\([^)]*\)", src):
            assert "chat_media" not in m.group(0), f"static mount of chat_media in {path}"


def test_retrieval_roundtrip_serves_correct_audio_content_type(client):
    up = _upload(client).json()
    resp = client.get(f"/chat/media/{up['id']}")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/webm")
    assert hashlib.sha256(resp.content).hexdigest() == up["sha256"]


def test_retrieval_rejects_traversal_ids(client):
    for bad in ("../secrets.env", ".hidden.weba", "a/b.weba"):
        resp = client.get(f"/chat/media/{bad}")
        assert resp.status_code in (400, 404), f"traversal id {bad!r} not rejected"


# ── 5. Delete semantics (retention law) ───────────────────────────────────────


def test_delete_removes_audio_artifact(client, media_env):
    up = _upload(client).json()
    stored = media_env / "data" / "chat_media" / up["id"]
    assert stored.is_file()
    resp = client.delete(f"/chat/media/{up['id']}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    assert not stored.exists()
    assert client.get(f"/chat/media/{up['id']}").status_code == 404


def test_delete_refuses_non_audio_media(client):
    up = client.post(
        "/chat/upload",
        files={"file": ("shot.png", b"\x89PNG" + os.urandom(64), "image/png")},
    ).json()
    resp = client.delete(f"/chat/media/{up['id']}")
    assert resp.status_code == 400


def test_delete_rejects_traversal_ids(client):
    for bad in ("..%2Fx.weba", ".hidden.weba"):
        resp = client.delete(f"/chat/media/{bad}")
        assert resp.status_code in (400, 404)


# ── 6. Logging law + no secrets (static scan) ────────────────────────────────


def _media_section() -> str:
    """Source slice covering upload/retrieval/delete handlers."""
    start = _SRC.index("Media upload for multimodal chat")
    return _SRC[start:]


def test_no_info_or_higher_logging_on_media_paths():
    section = _media_section()
    for level in ("info", "warning", "error", "critical", "exception"):
        assert f"logger.{level}(" not in section, (
            f"media path logs at {level} — storage law allows DEBUG only"
        )


def test_no_filename_or_content_in_debug_logs():
    """DEBUG lines on the media paths may carry ids only — never client
    filenames, raw content, or transcript text."""
    for m in re.finditer(r"logger\.debug\(([^)]*)\)", _media_section()):
        args = m.group(1)
        assert "file.filename" not in args
        assert "content" not in args
        assert "transcript" not in args


def test_no_plaintext_secrets_in_module():
    patterns = [
        r"(?i)(api_key|apikey|password|secret|token)\s*=\s*[\"'][A-Za-z0-9_\-]{16,}[\"']",
        r"sk-[A-Za-z0-9]{20,}",
    ]
    for pat in patterns:
        assert not re.search(pat, _SRC), f"plaintext secret pattern {pat} in module"


def test_audio_bytes_never_logged():
    """No logging call on the media paths references the streamed chunk/hash
    input or the destination file object."""
    section = _media_section()
    for m in re.finditer(r"logger\.\w+\(([^)]*)\)", section):
        assert "chunk" not in m.group(1)
        assert "hasher" not in m.group(1)
