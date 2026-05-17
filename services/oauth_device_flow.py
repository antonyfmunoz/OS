"""oauth_device_flow.py — Headless OAuth re-auth via Tailscale-routed callback.

Google doesn't support RFC 8628 device flow for Desktop/Installed OAuth clients.
Instead, this module runs a one-shot HTTP listener on the VPS (Tailscale-accessible)
and surfaces the consent URL to Discord. User taps link on phone, Google redirects
to http://VPS_TAILSCALE_IP:PORT/oauth/callback, we catch the auth code and exchange.

Generalized for any future scope grant (Calendar, Drive write, etc.).

Usage:
    python3 services/oauth_device_flow.py --scopes gmail.readonly drive.readonly
    python3 services/oauth_device_flow.py --scopes gmail.readonly --notify-discord
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import urllib.parse
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("oauth_flow")

_CLIENT_SECRET_PATH = Path("/root/.config/gws/client_secret.json")
_CREDENTIALS_PATH = Path("/root/.config/gws/gmail_credentials.json")
_CALLBACK_PORT = int(os.getenv("OAUTH_CALLBACK_PORT", "8090"))
_TAILSCALE_IP = os.getenv("TAILSCALE_VPS_IP", "100.77.233.50")
_USE_LOCALHOST_REDIRECT = True  # Google enforces localhost-only for Installed App clients

_SCOPE_ALIASES: dict[str, str] = {
    "gmail.readonly": "https://www.googleapis.com/auth/gmail.readonly",
    "gmail.send": "https://www.googleapis.com/auth/gmail.send",
    "drive.readonly": "https://www.googleapis.com/auth/drive.readonly",
    "drive": "https://www.googleapis.com/auth/drive",
    "calendar.readonly": "https://www.googleapis.com/auth/calendar.readonly",
    "calendar": "https://www.googleapis.com/auth/calendar",
    "profile": "https://www.googleapis.com/auth/userinfo.profile",
    "email": "https://www.googleapis.com/auth/userinfo.email",
    "openid": "openid",
}

_BASE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _resolve_scopes(scope_args: list[str]) -> list[str]:
    """Resolve scope aliases to full URLs, merge with base scopes."""
    resolved = set(_BASE_SCOPES)
    for s in scope_args:
        resolved.add(_SCOPE_ALIASES.get(s, s))
    return sorted(resolved)


def _load_client_config() -> dict:
    data = json.loads(_CLIENT_SECRET_PATH.read_text())
    return data.get("installed", data.get("web", {}))


def _get_redirect_uri() -> str:
    if _USE_LOCALHOST_REDIRECT:
        return f"http://localhost:{_CALLBACK_PORT}/oauth/callback"
    return f"http://{_TAILSCALE_IP}:{_CALLBACK_PORT}/oauth/callback"


def _build_auth_url(client_id: str, scopes: list[str], state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": _get_redirect_uri(),
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)


async def _exchange_code(client_config: dict, code: str) -> dict:
    """Exchange auth code for tokens."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_config["client_id"],
                "client_secret": client_config["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _get_redirect_uri(),
            },
        ) as resp:
            return await resp.json()


async def _notify_discord(message: str) -> None:
    """Post message to Discord via VPS webhook receiver."""
    import aiohttp

    webhook_port = os.getenv("CC_WEBHOOK_PORT", "8765")
    session_name = os.getenv("EOS_DISCORD_BUILDER_SESSION", "dex_builder_main")

    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"http://127.0.0.1:{webhook_port}/cc-reply",
                json={"session_name": session_name, "text": message},
                timeout=aiohttp.ClientTimeout(total=5),
            )
    except Exception as exc:
        logger.warning("[OAuth] Discord notify failed: %s", exc)


def _save_credentials(token_data: dict, scopes: list[str], account_email: str | None = None) -> Path:
    """Save credentials in a format the magic_link_handler can read.

    If account_email is provided, saves to gmail_credentials_{domain}.json.
    Also always updates the default gmail_credentials.json for backwards compat.
    """
    client_cfg = _load_client_config()
    creds = {
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_cfg["client_id"],
        "client_secret": client_cfg["client_secret"],
        "scopes": scopes,
        "expiry": token_data.get("expires_in"),
        "issued_at": time.time(),
    }
    if account_email:
        creds["account_email"] = account_email

    _CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(creds, indent=2)

    save_path = _CREDENTIALS_PATH
    if account_email and "@" in account_email:
        domain = account_email.split("@")[-1]
        save_path = _CREDENTIALS_PATH.parent / f"gmail_credentials_{domain}.json"
        save_path.write_text(content)
        logger.info("[OAuth] Per-domain credentials saved to %s", save_path)

    _CREDENTIALS_PATH.write_text(content)
    logger.info("[OAuth] Default credentials saved to %s", _CREDENTIALS_PATH)
    return save_path


async def run_oauth_flow(
    scopes: list[str],
    notify_discord: bool = True,
    timeout_s: int = 300,
    account_email: str | None = None,
) -> bool:
    """Run the full OAuth flow: start listener, surface URL, wait for callback.

    account_email: which Google account to authorize. Used in Discord notification
    and for per-domain credential storage.
    """
    client_config = _load_client_config()
    state = f"eos-{int(time.time())}"

    login_hint_params = {}
    if account_email:
        login_hint_params["login_hint"] = account_email
    auth_url = _build_auth_url(client_config["client_id"], scopes, state)
    if account_email:
        auth_url += f"&login_hint={urllib.parse.quote(account_email)}"

    code_future: asyncio.Future = asyncio.get_event_loop().create_future()

    async def handle_callback(request: web.Request) -> web.Response:
        received_state = request.query.get("state", "")
        if received_state != state:
            return web.Response(text="State mismatch — rejected.", status=400)

        error = request.query.get("error")
        if error:
            code_future.set_exception(Exception(f"OAuth denied: {error}"))
            return web.Response(
                text=f"Authorization denied: {error}. You can close this tab.",
                content_type="text/html",
            )

        code = request.query.get("code", "")
        if not code:
            return web.Response(text="No code received.", status=400)

        code_future.set_result(code)
        return web.Response(
            text="<h2>Authorization successful.</h2><p>You can close this tab.</p>",
            content_type="text/html",
        )

    app = web.Application()
    app.router.add_get("/oauth/callback", handle_callback)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", _CALLBACK_PORT)
    await site.start()

    logger.info("[OAuth] Callback listener on http://0.0.0.0:%d/oauth/callback", _CALLBACK_PORT)
    logger.info("[OAuth] Auth URL: %s", auth_url)

    display_account = account_email or "antonyfm@empyreanstudios.co"
    if notify_discord:
        scope_names = ", ".join(s.split("/")[-1] if "/" in s else s for s in scopes)
        msg = (
            f"**Google OAuth — scope grant required**\n"
            f"Scopes: `{scope_names}`\n"
            f"Account: `{display_account}`\n\n"
            f"**Tap to authorize:** {auth_url}\n\n"
            f"_Expires in {timeout_s}s. One tap — no code entry needed._"
        )
        await _notify_discord(msg)
        logger.info("[OAuth] Discord notification sent")

    try:
        code = await asyncio.wait_for(code_future, timeout=timeout_s)
    except asyncio.TimeoutError:
        logger.error("[OAuth] Timed out waiting for consent (%ds)", timeout_s)
        if notify_discord:
            await _notify_discord(f"OAuth consent timed out for {display_account}. Re-run when ready.")
        await runner.cleanup()
        return False
    except Exception as exc:
        logger.error("[OAuth] Flow failed: %s", exc)
        if notify_discord:
            await _notify_discord(f"OAuth flow failed: {exc}")
        await runner.cleanup()
        return False

    await runner.cleanup()

    logger.info("[OAuth] Auth code received — exchanging for tokens")
    token_data = await _exchange_code(client_config, code)

    if "error" in token_data:
        logger.error("[OAuth] Token exchange failed: %s", token_data)
        if notify_discord:
            await _notify_discord(f"Token exchange failed: {token_data.get('error_description', token_data.get('error'))}")
        return False

    if not token_data.get("refresh_token"):
        logger.warning("[OAuth] No refresh_token in response — token may be short-lived")

    _save_credentials(token_data, scopes, account_email=account_email)

    if notify_discord:
        await _notify_discord(f"Gmail access granted for {display_account}. Export pipeline ready.")

    logger.info("[OAuth] Flow complete — credentials stored for %s", display_account)
    return True


async def main():
    parser = argparse.ArgumentParser(description="Google OAuth re-auth via Tailscale callback")
    parser.add_argument("--scopes", nargs="+", default=["gmail.readonly"],
                        help="Scope aliases or full URLs to request")
    parser.add_argument("--account", type=str, default=None,
                        help="Google account email (login_hint + per-domain creds storage)")
    parser.add_argument("--no-discord", action="store_true",
                        help="Skip Discord notification (print URL to stdout only)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Seconds to wait for consent (default: 300)")
    args = parser.parse_args()

    scopes = _resolve_scopes(args.scopes)
    logger.info("[OAuth] Requesting scopes: %s (account: %s)", scopes, args.account or "default")

    success = await run_oauth_flow(
        scopes=scopes,
        notify_discord=not args.no_discord,
        timeout_s=args.timeout,
        account_email=args.account,
    )

    if success:
        print("\n[OAuth] SUCCESS — credentials saved to", _CREDENTIALS_PATH)
        sys.exit(0)
    else:
        print("\n[OAuth] FAILED — see logs above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
