"""Scripted login for claude.ai — email magic-link flow.

Claude.ai uses Google OAuth, Apple OAuth, or email magic-link.
This module implements the magic-link path:
  1. Navigate to login page
  2. Click "Continue with email"
  3. Fill email, submit
  4. Wait for magic-link email via bridge Gmail poller
  5. Navigate directly to the magic-link URL
  6. Confirm authenticated state
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

_LOGIN_URL = "https://claude.ai/login"
_MAGIC_LINK_TIMEOUT = 120


async def login(page) -> bool:
    """Drive claude.ai magic-link login. Returns True if authenticated.

    Reads CLAUDE_EMAIL from .env.secrets.
    If already authenticated (persistent profile has session), returns immediately.
    """
    email = os.getenv("CLAUDE_EMAIL")
    if not email:
        logger.error("[claude:auth] CLAUDE_EMAIL not set in .env.secrets")
        return False

    if await _already_authenticated(page):
        return True

    logger.info("[claude:auth] Not authenticated — starting magic-link flow")
    await page.goto(_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    if not await _click_continue_with_email(page):
        logger.error("[claude:auth] Could not find 'Continue with email' button")
        return False

    await page.wait_for_timeout(2000)

    if not await _fill_email(page, email):
        logger.error("[claude:auth] Could not fill email input")
        return False

    await page.wait_for_timeout(3000)

    if not _detect_check_email_page(await _get_body_text(page)):
        logger.warning("[claude:auth] Did not detect 'check your email' confirmation")

    logger.info("[claude:auth] Email submitted — requesting magic link from bridge")
    magic_url = await _wait_for_magic_link(email)
    if not magic_url:
        logger.error("[claude:auth] Magic link not received within %ds", _MAGIC_LINK_TIMEOUT)
        print("AUTH_BLOCKED type=MAGIC_LINK_TIMEOUT service=claude")
        return False

    logger.info("[claude:auth] Magic link received — navigating to URL")
    await page.goto(magic_url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(5000)

    if await _confirm_authenticated(page):
        logger.info("[claude:auth] Magic-link login succeeded")
        return True

    logger.warning("[claude:auth] Navigation to magic link did not result in auth")
    return False


async def _already_authenticated(page) -> bool:
    """Check if session is already valid by navigating to claude.ai."""
    try:
        await page.goto("https://claude.ai", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        url = page.url
        if "login" not in url.lower() and "auth" not in url.lower():
            body = await _get_body_text(page)
            auth_markers = ["new chat", "start a new", "claude", "conversation"]
            if any(m in body.lower() for m in auth_markers):
                logger.info("[claude:auth] Already authenticated (session cookie valid)")
                return True
    except Exception as exc:
        logger.warning("[claude:auth] Session check failed: %s", exc)
    return False


async def _click_continue_with_email(page) -> bool:
    """Find and click the 'Continue with email' button."""
    selectors = [
        'button:has-text("Continue with email")',
        'button:has-text("continue with email")',
        'a:has-text("Continue with email")',
        'button:has-text("Email")',
        '[data-testid="email-login"]',
    ]
    for selector in selectors:
        try:
            btn = page.locator(selector)
            if await btn.count() > 0:
                await btn.first.click()
                logger.info("[claude:auth] Clicked: %s", selector)
                return True
        except Exception:
            continue
    return False


async def _fill_email(page, email: str) -> bool:
    """Fill the email input and submit."""
    try:
        email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]')
        if await email_input.count() > 0:
            await email_input.first.fill(email)
            await page.wait_for_timeout(500)

            submit = page.locator(
                'button[type="submit"], '
                'button:has-text("Continue"), '
                'button:has-text("Send"), '
                'button:has-text("Sign in"), '
                'button:has-text("Send login link")'
            )
            if await submit.count() > 0:
                await submit.first.click()
                logger.info("[claude:auth] Email submitted: %s", email)
                return True
            else:
                await email_input.first.press("Enter")
                logger.info("[claude:auth] Email submitted via Enter key")
                return True
    except Exception as exc:
        logger.warning("[claude:auth] Email fill failed: %s", exc)
    return False


def _detect_check_email_page(body_text: str) -> bool:
    """Detect the 'check your email' confirmation page."""
    markers = ["check your email", "magic link", "login link", "sent you", "check your inbox"]
    return any(m in body_text.lower() for m in markers)


async def _wait_for_magic_link(email: str) -> str | None:
    """Request magic link URL from the VPS Gmail poller.

    The VPS has Gmail API access (GWS CLI with gmail.readonly scope).
    Windows calls the VPS webhook receiver which runs the Gmail poller.
    Falls back to local bridge if VPS is unreachable.
    """
    import aiohttp

    vps_url = os.getenv("EOS_MAGIC_LINK_URL", "http://100.77.233.50:8769")
    bridge_port = os.getenv("EOS_LOCAL_BRIDGE_PORT", "8767")
    local_url = f"http://localhost:{bridge_port}"

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
                        "service": "claude",
                        "email": email,
                        "timeout": _MAGIC_LINK_TIMEOUT,
                    },
                    timeout=aiohttp.ClientTimeout(total=_MAGIC_LINK_TIMEOUT + 10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        url = data.get("magic_link_url")
                        if url:
                            logger.info("[claude:auth] %s returned magic link", label)
                            return url
                        logger.warning("[claude:auth] %s returned 200 but no URL: %s", label, data)
                    elif resp.status == 408:
                        logger.warning("[claude:auth] %s timed out waiting for magic link", label)
                    else:
                        body = await resp.text()
                        logger.warning("[claude:auth] %s returned %d: %s", label, resp.status, body[:200])
        except Exception as exc:
            logger.warning("[claude:auth] %s unreachable: %s — trying next", label, exc)
            continue

    return None


async def _confirm_authenticated(page) -> bool:
    """Verify we landed on an authenticated page after magic-link navigation."""
    url = page.url
    if "login" in url.lower() or "auth" in url.lower():
        return False

    body = await _get_body_text(page)
    auth_markers = ["new chat", "start a new", "conversation", "settings", "claude"]
    return any(m in body.lower() for m in auth_markers)


async def _get_body_text(page) -> str:
    """Safely extract body text."""
    try:
        return await page.inner_text("body")
    except Exception:
        return ""
