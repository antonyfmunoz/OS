"""One-shot OAuth grant for Gmail scope — run on Windows (needs browser).

Opens browser to Google consent, catches the callback on localhost:8090,
exchanges for tokens, saves to .config/gws/gmail_credentials.json.

After running, scp the credentials to VPS:
  The script prints the exact command at the end.

Usage:
    python scripts/oauth_grant_gmail.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import urllib.parse
import webbrowser
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CALLBACK_PORT = 8090
_CLIENT_SECRET_PATH = Path.home() / ".config" / "gws" / "client_secret.json"
_CREDENTIALS_PATH = Path.home() / ".config" / "gws" / "gmail_credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _load_client_config() -> dict:
    if not _CLIENT_SECRET_PATH.exists():
        print(f"ERROR: {_CLIENT_SECRET_PATH} not found")
        print("Copy from VPS: scp root@100.77.233.50:/root/.config/gws/client_secret.json ~/.config/gws/")
        sys.exit(1)
    data = json.loads(_CLIENT_SECRET_PATH.read_text())
    return data.get("installed", data.get("web", {}))


async def main():
    from aiohttp import web
    import aiohttp

    client = _load_client_config()
    state = f"eos-{int(time.time())}"
    redirect_uri = f"http://localhost:{_CALLBACK_PORT}/oauth/callback"

    auth_url = "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode({
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })

    code_future: asyncio.Future = asyncio.get_event_loop().create_future()

    async def handle_callback(request: web.Request) -> web.Response:
        if request.query.get("state") != state:
            return web.Response(text="State mismatch", status=400)
        error = request.query.get("error")
        if error:
            code_future.set_exception(Exception(f"Denied: {error}"))
            return web.Response(text=f"Denied: {error}", content_type="text/html")
        code = request.query.get("code", "")
        code_future.set_result(code)
        return web.Response(
            text="<h2>Success! Close this tab.</h2>",
            content_type="text/html",
        )

    app = web.Application()
    app.router.add_get("/oauth/callback", handle_callback)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", _CALLBACK_PORT)
    await site.start()

    print(f"[OAuth] Listener on http://localhost:{_CALLBACK_PORT}/oauth/callback")
    print(f"[OAuth] Opening browser...")
    webbrowser.open(auth_url)
    print(f"[OAuth] Waiting for consent (600s timeout)...")
    print(f"[OAuth] Sign in as antonyfm@empyreanstudios.co and approve Gmail access")

    try:
        code = await asyncio.wait_for(code_future, timeout=600)
    except asyncio.TimeoutError:
        print("[OAuth] TIMEOUT — no consent received in 600s")
        await runner.cleanup()
        sys.exit(1)

    await runner.cleanup()
    print(f"[OAuth] Code received — exchanging for tokens...")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client["client_id"],
                "client_secret": client["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        ) as resp:
            token_data = await resp.json()

    if "error" in token_data:
        print(f"[OAuth] TOKEN EXCHANGE FAILED: {token_data}")
        sys.exit(1)

    creds = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client["client_id"],
        "client_secret": client["client_secret"],
        "scopes": SCOPES,
        "expiry": token_data.get("expires_in"),
        "issued_at": time.time(),
    }

    _CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CREDENTIALS_PATH.write_text(json.dumps(creds, indent=2))
    print(f"\n[OAuth] SUCCESS — credentials saved to: {_CREDENTIALS_PATH}")
    print(f"[OAuth] Scopes granted: {SCOPES}")

    if token_data.get("refresh_token"):
        print("[OAuth] Refresh token: PRESENT (long-lived)")
    else:
        print("[OAuth] WARNING: No refresh token — may need to re-auth later")

    print(f"\n[OAuth] Now copy to VPS:")
    creds_path_str = str(_CREDENTIALS_PATH).replace("\\", "/")
    print(f'  Type in VPS terminal:')
    print(f'  ssh -l "antonys beast pc" 100.74.199.102 "type \\"{_CREDENTIALS_PATH}\\"" > /root/.config/gws/gmail_credentials.json')
    print(f"\n  Or from this machine:")
    print(f'  scp "{_CREDENTIALS_PATH}" root@100.77.233.50:/root/.config/gws/gmail_credentials.json')


if __name__ == "__main__":
    asyncio.run(main())
