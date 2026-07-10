"""WP-P0-004 — CC webhook receiver auth + loopback-bind regression tests.

Drives the REAL `start_webhook_server` aiohttp app (real routes, real
`_auth_middleware`) through an in-process TestServer — not a mock substitute.
A fake bot/channel records every `channel.send(...)` so each test can assert
that unauthenticated / mis-authenticated requests produce ZERO side effect
(no Discord send, no tmux/session control) before auth passes.

Covers the exact live routes: /cc-reply, /cc-prompt, /mfa-challenge, /health.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer

from services import cc_webhook_receiver as rcv

TOKEN = "test-cc-webhook-token-abc123"
TEST_SESSION = "test_builder_main"
BUILDER_CHANNEL = 111111111111111111


class _FakeChannel:
    def __init__(self) -> None:
        self.sends: list = []

    async def send(self, *args, **kwargs):
        # Records any delivery. If this is ever called for an unauthenticated
        # request, the side-effect-free assertion fails.
        self.sends.append((args, kwargs))
        return None


class _FakeBot:
    def __init__(self, channel: _FakeChannel) -> None:
        self._channel = channel

    def get_channel(self, channel_id: int):
        return self._channel


@pytest.fixture
def fake_channel() -> _FakeChannel:
    return _FakeChannel()


@pytest.fixture(autouse=True)
def _env(monkeypatch, fake_channel):
    """Configure a session→channel mapping and a known token by default."""
    monkeypatch.setenv("EOS_DISCORD_BUILDER_SESSION", TEST_SESSION)
    monkeypatch.setenv("EOS_DISCORD_BUILDER_CHANNELS", str(BUILDER_CHANNEL))
    monkeypatch.setenv("EOS_DISCORD_GENERAL_CHANNEL", str(BUILDER_CHANNEL))
    monkeypatch.setenv("CC_WEBHOOK_TOKEN", TOKEN)
    monkeypatch.delenv("CC_WEBHOOK_BIND_HOST", raising=False)
    yield


@pytest_asyncio.fixture
async def client(fake_channel) -> TestClient:
    bot = _FakeBot(fake_channel)
    runner = await rcv.start_webhook_server(bot, ai_name="TestAI", port=0)
    # start_webhook_server already started a TCPSite; for testing we instead
    # build a TestServer around the same app object it constructed. Re-create
    # the app via the app factory path: the runner exposes the app.
    app = runner.app
    await runner.cleanup()  # stop the real TCPSite; TestServer will serve the app
    server = TestServer(app)
    test_client = TestClient(server)
    await test_client.start_server()
    yield test_client
    await test_client.close()


# ── Auth: unauthenticated rejected, zero side effect ─────────────────────────


@pytest.mark.asyncio
async def test_unauthenticated_cc_reply_rejected_no_side_effect(client, fake_channel):
    resp = await client.post("/cc-reply", json={"session_name": TEST_SESSION, "text": "hi"})
    assert resp.status == 401
    assert fake_channel.sends == [], "unauthenticated request must not send"


@pytest.mark.asyncio
async def test_unauthenticated_cc_prompt_rejected_before_tmux(client, fake_channel):
    """/cc-prompt drives tmux/session control on button callbacks — it must be
    rejected before the handler (and therefore any session control) runs."""
    resp = await client.post(
        "/cc-prompt",
        json={"session_name": TEST_SESSION, "text": "approve?", "prompt_type": "permission"},
    )
    assert resp.status == 401
    assert fake_channel.sends == [], "unauth /cc-prompt must not reach the session bridge"


@pytest.mark.asyncio
async def test_unauthenticated_mfa_challenge_rejected(client, fake_channel):
    resp = await client.post(
        "/mfa-challenge", json={"service": "google", "mfa_type": "TOTP", "url": "x"}
    )
    assert resp.status == 401
    assert fake_channel.sends == [], "unauth MFA relay must not surface a code"


# ── Fail closed when the token is not configured ─────────────────────────────


@pytest.mark.asyncio
async def test_missing_token_fails_closed(client, fake_channel, monkeypatch):
    monkeypatch.delenv("CC_WEBHOOK_TOKEN", raising=False)
    resp = await client.post(
        "/cc-reply",
        json={"session_name": TEST_SESSION, "text": "hi"},
        headers={"Authorization": "Bearer anything"},
    )
    assert resp.status == 503, "no configured token must fail closed (503)"
    assert fake_channel.sends == []


# ── Valid token passes (only for the intended endpoint) ──────────────────────


@pytest.mark.asyncio
async def test_valid_token_cc_reply_passes(client, fake_channel):
    resp = await client.post(
        "/cc-reply",
        json={"session_name": TEST_SESSION, "text": "hello world"},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status == 200
    assert len(fake_channel.sends) == 1, "valid token should deliver exactly once"


# ── Token in URL is NOT accepted (header transport only) ─────────────────────


@pytest.mark.asyncio
async def test_token_in_url_not_accepted(client, fake_channel):
    resp = await client.post(
        f"/cc-reply?token={TOKEN}&access_token={TOKEN}",
        json={"session_name": TEST_SESSION, "text": "hi"},
    )
    assert resp.status == 401, "URL/query token must not authenticate"
    assert fake_channel.sends == []


# ── Invalid / expired token → zero side effect ───────────────────────────────


@pytest.mark.asyncio
async def test_invalid_token_zero_side_effect(client, fake_channel):
    resp = await client.post(
        "/cc-prompt",
        json={"session_name": TEST_SESSION, "text": "approve?"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status == 401
    assert fake_channel.sends == [], "invalid token must cause no session control"


# ── /health stays open (liveness, no side effect, no auth) ───────────────────


@pytest.mark.asyncio
async def test_health_open_no_auth(client):
    resp = await client.get("/health")
    assert resp.status == 200


# ── Bind host defaults to loopback ───────────────────────────────────────────


def test_bind_host_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("CC_WEBHOOK_BIND_HOST", raising=False)
    import importlib

    importlib.reload(rcv)
    assert rcv.CC_WEBHOOK_BIND_HOST == "127.0.0.1"


def test_bind_host_override_is_explicit(monkeypatch):
    monkeypatch.setenv("CC_WEBHOOK_BIND_HOST", "100.77.233.50")
    import importlib

    importlib.reload(rcv)
    assert rcv.CC_WEBHOOK_BIND_HOST == "100.77.233.50"
    # restore default for other tests
    monkeypatch.delenv("CC_WEBHOOK_BIND_HOST", raising=False)
    importlib.reload(rcv)


# ── The middleware never reads a URL token (unit-level guard) ─────────────────


def test_extract_bearer_ignores_url_and_reads_header_only():
    class _Req:
        def __init__(self, headers):
            self.headers = headers

    assert rcv._extract_bearer(_Req({"Authorization": f"Bearer {TOKEN}"})) == TOKEN
    assert rcv._extract_bearer(_Req({"Authorization": "Basic xyz"})) == ""
    assert rcv._extract_bearer(_Req({})) == ""


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
