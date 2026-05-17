"""Scripted login for claude.ai — email + password + MFA branching."""

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
_SETTINGS_URL = "https://claude.ai/settings"


async def login(page) -> bool:
    """Drive claude.ai login flow. Returns True if authenticated.

    Reads CLAUDE_EMAIL, CLAUDE_PASSWORD, CLAUDE_TOTP_SECRET from .env.secrets.
    If already authenticated (persistent profile has session), returns immediately.
    """
    email = os.getenv("CLAUDE_EMAIL")
    password = os.getenv("CLAUDE_PASSWORD")
    if not email or not password:
        logger.error("[claude:auth] CLAUDE_EMAIL or CLAUDE_PASSWORD not set in .env.secrets")
        return False

    await page.goto(_SETTINGS_URL, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    url = page.url
    if "login" not in url.lower() and "verify" not in url.lower():
        logger.info("[claude:auth] Already authenticated (session cookie valid)")
        return True

    logger.info("[claude:auth] Not authenticated — starting login flow")
    await page.goto(_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(3000)

    try:
        email_input = page.locator('input[type="email"], input[name="email"]')
        if await email_input.count() > 0:
            await email_input.first.fill(email)
            await page.wait_for_timeout(500)

            submit = page.locator('button[type="submit"], button:has-text("Continue"), button:has-text("Sign in")')
            if await submit.count() > 0:
                await submit.first.click()
                await page.wait_for_timeout(3000)
    except Exception as exc:
        logger.warning("[claude:auth] Email step failed: %s", exc)

    try:
        pw_input = page.locator('input[type="password"]')
        if await pw_input.count() > 0:
            await pw_input.first.fill(password)
            await page.wait_for_timeout(500)

            submit = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Log in")')
            if await submit.count() > 0:
                await submit.first.click()
                await page.wait_for_timeout(5000)
    except Exception as exc:
        logger.warning("[claude:auth] Password step failed: %s", exc)

    return await _handle_mfa(page)


async def _handle_mfa(page) -> bool:
    """Detect and handle MFA challenge after password submission."""
    url = page.url
    body_text = ""
    try:
        body_text = (await page.inner_text("body")).lower()
    except Exception:
        pass

    mfa_indicators = ["verify", "two-factor", "mfa", "authenticator", "code", "otp"]
    is_mfa = any(ind in url.lower() or ind in body_text for ind in mfa_indicators)

    if not is_mfa:
        if "login" not in url.lower():
            logger.info("[claude:auth] Login succeeded — no MFA required")
            return True
        logger.warning("[claude:auth] Still on login page after password — check screenshot")
        return False

    logger.info("[claude:auth] MFA challenge detected")

    if "authenticator" in body_text or "totp" in body_text or "6-digit" in body_text:
        return await _handle_totp(page)
    elif "email" in body_text and ("code" in body_text or "verify" in body_text):
        return await _handle_email_code(page)
    else:
        return await _handle_push_sms(page)


async def _handle_totp(page) -> bool:
    """Fill TOTP code from CLAUDE_TOTP_SECRET."""
    secret = os.getenv("CLAUDE_TOTP_SECRET")
    if not secret:
        logger.error("[claude:auth] CLAUDE_TOTP_SECRET not set — cannot complete TOTP MFA")
        print("MFA_CHALLENGE type=TOTP service=claude")
        return False

    try:
        import pyotp
        code = pyotp.TOTP(secret).now()
        logger.info("[claude:auth] Generated TOTP code")

        code_input = page.locator('input[type="text"], input[type="number"], input[name*="code"], input[name*="otp"]')
        if await code_input.count() > 0:
            await code_input.first.fill(code)
            await page.wait_for_timeout(500)

            submit = page.locator('button[type="submit"], button:has-text("Verify"), button:has-text("Continue")')
            if await submit.count() > 0:
                await submit.first.click()
                await page.wait_for_timeout(5000)

            if "login" not in page.url.lower() and "verify" not in page.url.lower():
                logger.info("[claude:auth] TOTP MFA succeeded")
                return True

        logger.warning("[claude:auth] TOTP submission did not resolve MFA")
        return False

    except ImportError:
        logger.error("[claude:auth] pyotp not installed")
        return False
    except Exception as exc:
        logger.error("[claude:auth] TOTP failed: %s", exc)
        return False


async def _handle_email_code(page) -> bool:
    """Wait for email verification code via Gmail poller."""
    print("MFA_CHALLENGE type=EMAIL_2FA service=claude")
    logger.info("[claude:auth] Email MFA detected — requesting code via bridge")

    try:
        import aiohttp
        bridge_url = os.getenv("EOS_VPS_WEBHOOK_URL", "http://100.77.233.50:8765")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{bridge_url}/mfa-challenge",
                json={"type": "mfa_challenge", "service": "claude", "mfa_type": "EMAIL_2FA"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                logger.info("[claude:auth] MFA challenge surfaced to VPS (status=%d)", resp.status)
    except Exception as exc:
        logger.warning("[claude:auth] Could not surface MFA to VPS: %s", exc)

    import asyncio
    for attempt in range(12):
        await asyncio.sleep(10)
        try:
            import aiohttp
            bridge_port = os.getenv("EOS_LOCAL_BRIDGE_PORT", "8767")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:{bridge_port}/mfa-code/claude",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        code = data.get("code")
                        if code:
                            code_input = page.locator('input[type="text"], input[name*="code"]')
                            if await code_input.count() > 0:
                                await code_input.first.fill(code)
                                submit = page.locator('button[type="submit"]')
                                if await submit.count() > 0:
                                    await submit.first.click()
                                    await page.wait_for_timeout(5000)
                                if "login" not in page.url.lower():
                                    logger.info("[claude:auth] Email MFA succeeded")
                                    return True
        except Exception:
            pass

    logger.warning("[claude:auth] Email MFA timed out (120s)")
    return False


async def _handle_push_sms(page) -> bool:
    """Fallback: surface to Discord and wait 300s for manual resolution."""
    print("MFA_CHALLENGE type=PUSH_SMS service=claude")
    logger.info("[claude:auth] Push/SMS MFA — surfacing to Discord, waiting 300s")

    try:
        import aiohttp
        bridge_url = os.getenv("EOS_VPS_WEBHOOK_URL", "http://100.77.233.50:8765")
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{bridge_url}/mfa-challenge",
                json={"type": "mfa_challenge", "service": "claude", "mfa_type": "PUSH_SMS"},
                timeout=aiohttp.ClientTimeout(total=10),
            )
    except Exception:
        pass

    import asyncio
    for _ in range(60):
        await asyncio.sleep(5)
        url = page.url
        if "login" not in url.lower() and "verify" not in url.lower() and "mfa" not in url.lower():
            logger.info("[claude:auth] Push/SMS MFA resolved (page navigated)")
            return True

    logger.warning("[claude:auth] Push/SMS MFA timed out (300s)")
    return False
