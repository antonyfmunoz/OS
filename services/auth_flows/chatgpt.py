"""Scripted login for chatgpt.com — email-based auth flow.

ChatGPT uses email + password, Google OAuth, Apple OAuth, or Microsoft OAuth.
This module implements the email path with adaptive challenge detection:
  1. Navigate to login page
  2. Enter email, submit
  3. Screenshot the challenge page BEFORE assuming what it is
  4. Handle detected challenge: password, verification code, or magic-link
  5. Confirm authenticated state

IMPORTANT: Forces en-US locale to avoid GeoIP localization breaking selectors.
Uses role/type/aria-label selectors — never button text.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / ".env.secrets")

logger = logging.getLogger(__name__)

_LOGIN_URL = "https://chatgpt.com/auth/login"
_AUTH_TIMEOUT = 120
_SCREENSHOT_DIR = Path(os.getenv("EXPORT_SCREENSHOT_DIR", "/tmp/eos_exports"))


async def login(page) -> bool:
    """Drive ChatGPT login. Returns True if authenticated.

    Reads CHATGPT_EMAIL and optionally CHATGPT_PASSWORD from .env.secrets.
    Screenshots the challenge page for diagnostic before attempting to solve it.
    """
    email = os.getenv("CHATGPT_EMAIL")
    if not email:
        logger.error("[chatgpt:auth] CHATGPT_EMAIL not set in .env.secrets")
        return False

    password = os.getenv("CHATGPT_PASSWORD")

    if await _already_authenticated(page):
        return True

    logger.info("[chatgpt:auth] Not authenticated — starting login flow")
    await page.goto(_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(5000)

    await _screenshot(page, "01_login_page")

    if not await _click_login_button(page):
        logger.warning("[chatgpt:auth] No explicit login button found — may already be on auth page")

    await page.wait_for_timeout(3000)
    await _screenshot(page, "02_after_login_click")

    if not await _fill_email(page, email):
        logger.error("[chatgpt:auth] Could not fill email input")
        return False

    await page.wait_for_timeout(1000)

    if not await _submit_email(page):
        logger.error("[chatgpt:auth] Could not submit email form")
        return False

    await page.wait_for_timeout(5000)
    await _screenshot(page, "03_challenge_page")

    challenge = await _detect_challenge_type(page)
    logger.info("[chatgpt:auth] Detected challenge type: %s", challenge)

    if challenge == "password":
        if not password:
            logger.error("[chatgpt:auth] Password challenge detected but CHATGPT_PASSWORD not set")
            print("AUTH_BLOCKED type=PASSWORD_REQUIRED service=chatgpt")
            return False
        if not await _handle_password_challenge(page, password):
            return False

    elif challenge == "verification_code":
        logger.info("[chatgpt:auth] Verification code challenge — requesting code from Gmail poller")
        code = await _wait_for_verification_code(email)
        if not code:
            logger.error("[chatgpt:auth] Verification code not received within %ds", _AUTH_TIMEOUT)
            print("AUTH_BLOCKED type=VERIFICATION_CODE_TIMEOUT service=chatgpt")
            return False
        if not await _handle_code_challenge(page, code):
            return False

    elif challenge == "magic_link":
        logger.info("[chatgpt:auth] Magic-link challenge — requesting link from Gmail poller")
        magic_url = await _wait_for_magic_link(email)
        if not magic_url:
            logger.error("[chatgpt:auth] Magic link not received within %ds", _AUTH_TIMEOUT)
            print("AUTH_BLOCKED type=MAGIC_LINK_TIMEOUT service=chatgpt")
            return False
        await page.goto(magic_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)

    elif challenge == "already_authenticated":
        logger.info("[chatgpt:auth] Already authenticated after email submission")
        return True

    else:
        logger.error("[chatgpt:auth] Unknown challenge type: %s", challenge)
        await _screenshot(page, "04_unknown_challenge")
        print(f"AUTH_BLOCKED type=UNKNOWN_CHALLENGE service=chatgpt challenge={challenge}")
        return False

    await page.wait_for_timeout(5000)
    await _screenshot(page, "05_post_challenge")

    if await _confirm_authenticated(page):
        logger.info("[chatgpt:auth] Login succeeded")
        return True

    logger.warning("[chatgpt:auth] Post-challenge page did not confirm auth")
    await _screenshot(page, "06_auth_failed")
    return False


async def _already_authenticated(page) -> bool:
    """Check if session is already valid."""
    try:
        await page.goto("https://chatgpt.com", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        url = page.url
        if "login" not in url.lower() and "auth" not in url.lower():
            body = await _get_body_text(page)
            auth_markers = ["new chat", "chatgpt", "send a message", "message chatgpt", "gpt"]
            if any(m in body.lower() for m in auth_markers):
                logger.info("[chatgpt:auth] Already authenticated (session cookie valid)")
                return True
    except Exception as exc:
        logger.warning("[chatgpt:auth] Session check failed: %s", exc)
    return False


async def _click_login_button(page) -> bool:
    """Click the initial 'Log in' button on chatgpt.com landing page."""
    selectors = [
        '[data-testid="login-button"]',
        'button[data-testid="login"]',
        'a[href*="/auth/login"]',
        'button[role="button"][aria-label*="Log in" i]',
        'button[role="button"][aria-label*="Sign in" i]',
        'a[role="button"][aria-label*="Log in" i]',
        'a:text-is("Log in")',
        'button:text-is("Log in")',
    ]
    for selector in selectors:
        try:
            el = page.locator(selector)
            if await el.count() > 0:
                await el.first.click()
                logger.info("[chatgpt:auth] Clicked login button: %s", selector)
                return True
        except Exception:
            continue
    return False


async def _fill_email(page, email: str) -> bool:
    """Fill the email input field."""
    selectors = [
        'input[type="email"]',
        'input[name="email"]',
        'input[name="username"]',
        'input[id="email-input"]',
        'input[id="username"]',
        'input[autocomplete="email"]',
        'input[autocomplete="username"]',
        'input[placeholder*="email" i]',
    ]
    for selector in selectors:
        try:
            el = page.locator(selector)
            if await el.count() > 0:
                await el.first.fill(email)
                logger.info("[chatgpt:auth] Email filled via: %s", selector)
                return True
        except Exception:
            continue
    return False


async def _submit_email(page) -> bool:
    """Submit the email form."""
    selectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button[data-action-button-primary="true"]',
        'button[aria-label*="Continue" i]',
        'button[aria-label*="Submit" i]',
        'button[name="action"][value="default"]',
    ]
    for selector in selectors:
        try:
            el = page.locator(selector)
            if await el.count() > 0:
                await el.first.click()
                logger.info("[chatgpt:auth] Submitted email via: %s", selector)
                return True
        except Exception:
            continue

    try:
        email_input = page.locator('input[type="email"], input[name="email"], input[name="username"]')
        if await email_input.count() > 0:
            await email_input.first.press("Enter")
            logger.info("[chatgpt:auth] Submitted email via Enter key")
            return True
    except Exception:
        pass

    return False


async def _detect_challenge_type(page) -> str:
    """Detect what kind of challenge the login page is presenting."""
    body = await _get_body_text(page)
    body_lower = body.lower()

    password_input = page.locator('input[type="password"]')
    if await password_input.count() > 0:
        return "password"

    code_markers = ["verification code", "enter code", "enter the code", "codice di verifica",
                    "one-time code", "security code", "6-digit"]
    if any(m in body_lower for m in code_markers):
        return "verification_code"

    link_markers = ["check your email", "magic link", "login link", "sent you a link",
                    "check your inbox", "controlla la tua email"]
    if any(m in body_lower for m in link_markers):
        return "magic_link"

    code_input = page.locator('input[type="text"][maxlength="6"], input[type="number"][maxlength="6"], input[autocomplete="one-time-code"]')
    if await code_input.count() > 0:
        return "verification_code"

    auth_markers = ["new chat", "chatgpt", "send a message", "message chatgpt"]
    if any(m in body_lower for m in auth_markers):
        return "already_authenticated"

    return "unknown"


async def _handle_password_challenge(page, password: str) -> bool:
    """Fill password and submit."""
    try:
        pw_input = page.locator('input[type="password"]')
        if await pw_input.count() > 0:
            await pw_input.first.fill(password)
            await page.wait_for_timeout(500)

            submit_selectors = [
                'button[type="submit"]',
                'button[data-action-button-primary="true"]',
                'button[aria-label*="Continue" i]',
                'button[name="action"][value="default"]',
            ]
            for selector in submit_selectors:
                el = page.locator(selector)
                if await el.count() > 0:
                    await el.first.click()
                    logger.info("[chatgpt:auth] Password submitted via: %s", selector)
                    return True

            await pw_input.first.press("Enter")
            logger.info("[chatgpt:auth] Password submitted via Enter key")
            return True
    except Exception as exc:
        logger.error("[chatgpt:auth] Password challenge failed: %s", exc)
    return False


async def _handle_code_challenge(page, code: str) -> bool:
    """Fill verification code and submit."""
    try:
        code_selectors = [
            'input[autocomplete="one-time-code"]',
            'input[type="text"][maxlength="6"]',
            'input[type="number"][maxlength="6"]',
            'input[type="text"][inputmode="numeric"]',
            'input[name="code"]',
            'input[aria-label*="code" i]',
            'input[aria-label*="verification" i]',
        ]
        for selector in code_selectors:
            el = page.locator(selector)
            if await el.count() > 0:
                await el.first.fill(code)
                logger.info("[chatgpt:auth] Code filled via: %s", selector)
                await page.wait_for_timeout(500)

                submit_selectors = [
                    'button[type="submit"]',
                    'button[data-action-button-primary="true"]',
                    'button[aria-label*="Continue" i]',
                    'button[aria-label*="Verify" i]',
                    'button[name="action"][value="default"]',
                ]
                for sub_selector in submit_selectors:
                    sub_el = page.locator(sub_selector)
                    if await sub_el.count() > 0:
                        await sub_el.first.click()
                        logger.info("[chatgpt:auth] Code submitted via: %s", sub_selector)
                        return True

                await el.first.press("Enter")
                logger.info("[chatgpt:auth] Code submitted via Enter key")
                return True
    except Exception as exc:
        logger.error("[chatgpt:auth] Code challenge failed: %s", exc)
    return False


async def _wait_for_verification_code(email: str) -> str | None:
    """Request verification code from the VPS Gmail poller."""
    import aiohttp

    vps_url = os.getenv("EOS_MAGIC_LINK_URL", "http://100.77.233.50:8769")
    bridge_port = os.getenv("EOS_LOCAL_BRIDGE_PORT", "8767")
    local_url = f"http://localhost:{bridge_port}"

    inbox_email = os.getenv("CHATGPT_INBOX_EMAIL", "antonyfm@theempyreancreative.com")

    endpoints = [
        (vps_url, "VPS"),
        (local_url, "local bridge"),
    ]

    for base_url, label in endpoints:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/api/auth/wait-for-magic-link",
                    json={
                        "service": "chatgpt",
                        "email": email,
                        "inbox_email": inbox_email,
                        "timeout": _AUTH_TIMEOUT,
                    },
                    timeout=aiohttp.ClientTimeout(total=_AUTH_TIMEOUT + 10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        code = data.get("verification_code")
                        if code:
                            logger.info("[chatgpt:auth] %s returned verification code", label)
                            return code
                        url = data.get("magic_link_url")
                        if url:
                            logger.info("[chatgpt:auth] %s returned magic link instead of code", label)
                            return None
                        logger.warning("[chatgpt:auth] %s returned 200 but no credential: %s", label, data)
                    elif resp.status == 408:
                        logger.warning("[chatgpt:auth] %s timed out waiting for code", label)
                    else:
                        body = await resp.text()
                        logger.warning("[chatgpt:auth] %s returned %d: %s", label, resp.status, body[:200])
        except Exception as exc:
            logger.warning("[chatgpt:auth] %s unreachable: %s — trying next", label, exc)
            continue

    return None


async def _wait_for_magic_link(email: str) -> str | None:
    """Request magic link URL from the VPS Gmail poller."""
    import aiohttp

    vps_url = os.getenv("EOS_MAGIC_LINK_URL", "http://100.77.233.50:8769")
    bridge_port = os.getenv("EOS_LOCAL_BRIDGE_PORT", "8767")
    local_url = f"http://localhost:{bridge_port}"

    inbox_email = os.getenv("CHATGPT_INBOX_EMAIL", "antonyfm@theempyreancreative.com")

    endpoints = [
        (vps_url, "VPS"),
        (local_url, "local bridge"),
    ]

    for base_url, label in endpoints:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/api/auth/wait-for-magic-link",
                    json={
                        "service": "chatgpt",
                        "email": email,
                        "inbox_email": inbox_email,
                        "timeout": _AUTH_TIMEOUT,
                    },
                    timeout=aiohttp.ClientTimeout(total=_AUTH_TIMEOUT + 10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        url = data.get("magic_link_url")
                        if url:
                            logger.info("[chatgpt:auth] %s returned magic link", label)
                            return url
                        logger.warning("[chatgpt:auth] %s returned 200 but no URL: %s", label, data)
                    elif resp.status == 408:
                        logger.warning("[chatgpt:auth] %s timed out waiting for magic link", label)
                    else:
                        body = await resp.text()
                        logger.warning("[chatgpt:auth] %s returned %d: %s", label, resp.status, body[:200])
        except Exception as exc:
            logger.warning("[chatgpt:auth] %s unreachable: %s — trying next", label, exc)
            continue

    return None


async def _confirm_authenticated(page) -> bool:
    """Verify we landed on an authenticated page."""
    url = page.url
    if "login" in url.lower() or "auth" in url.lower():
        return False

    body = await _get_body_text(page)
    auth_markers = ["new chat", "chatgpt", "send a message", "message chatgpt",
                    "gpt-4", "gpt-3", "settings", "upgrade"]
    return any(m in body.lower() for m in auth_markers)


async def _screenshot(page, step_name: str) -> None:
    """Save diagnostic screenshot."""
    try:
        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        import time
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = _SCREENSHOT_DIR / f"chatgpt_{ts}_{step_name}.png"
        await page.screenshot(path=str(path), full_page=True)
        logger.info("[chatgpt:auth] Screenshot: %s", path)
    except Exception as exc:
        logger.warning("[chatgpt:auth] Screenshot failed: %s", exc)


async def _get_body_text(page) -> str:
    """Safely extract body text."""
    try:
        return await page.inner_text("body")
    except Exception:
        return ""
