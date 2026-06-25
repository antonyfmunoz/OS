"""SSO chain auth adapter — follows OAuth redirects through GitHub/Google.

Used by Tailscale admin console login which requires SSO via GitHub → Google.
When an email verification code is needed, calls push_chat_fn to ask the
operator via the cockpit chat channel.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)

_SSO_PATTERNS = {
    "github": re.compile(r"github\.com/(login|oauth)", re.IGNORECASE),
    "google": re.compile(r"accounts\.google\.com", re.IGNORECASE),
}


def detect_sso_provider(url: str) -> str | None:
    """Detect SSO provider from an OAuth redirect URL."""
    for provider, pattern in _SSO_PATTERNS.items():
        if pattern.search(url):
            return provider
    return None


async def sso_chain_auth(
    page: Any,
    target_url: str,
    email: str,
    push_chat_fn: Callable[[str], Any] | None = None,
    timeout_ms: int = 60000,
) -> bool:
    """Follow SSO redirect chain, filling credentials at each step.

    Args:
        page: Async Playwright page already navigated to the SSO entry point.
        target_url: The final URL we expect to land on after SSO completes.
        email: Email to fill at Google step.
        push_chat_fn: Async callable to push a message to operator for email code.
            Called with a message string. If None, code entry is skipped.
        timeout_ms: Max wait time for each step.

    Returns:
        True if SSO chain completed and we landed on target_url.
    """
    try:
        current_url = page.url

        provider = detect_sso_provider(current_url)
        if provider == "github":
            logger.info("SSO: GitHub OAuth detected")
            await _handle_github_step(page, timeout_ms)

        current_url = page.url
        provider = detect_sso_provider(current_url)
        if provider == "google":
            logger.info("SSO: Google OAuth detected")
            await _handle_google_step(page, email, push_chat_fn, timeout_ms)

        await page.wait_for_url(f"{target_url}**", timeout=timeout_ms)
        logger.info("SSO chain complete — landed on %s", page.url)
        return True

    except Exception as exc:
        logger.error("SSO chain failed: %s (current URL: %s)", exc, page.url)
        return False


async def _handle_github_step(page: Any, timeout_ms: int) -> None:
    """Handle GitHub OAuth — authorize the app if prompted."""
    authorize_btn = page.locator('button[name="authorize"], button:has-text("Authorize")')
    try:
        await authorize_btn.wait_for(timeout=5000)
        if await authorize_btn.count() > 0:
            await authorize_btn.first.click()
            await page.wait_for_timeout(3000)
    except Exception:
        logger.debug("No GitHub authorize button — may be pre-authorized")


async def _handle_google_step(
    page: Any,
    email: str,
    push_chat_fn: Callable[[str], Any] | None,
    timeout_ms: int,
) -> None:
    """Handle Google OAuth — fill email, handle verification code if needed."""
    email_input = page.locator('input[type="email"]')
    try:
        await email_input.wait_for(timeout=5000)
        if await email_input.count() > 0:
            await email_input.fill(email)
            next_btn = page.locator('#identifierNext, button:has-text("Next")')
            if await next_btn.count() > 0:
                await next_btn.first.click()
                await page.wait_for_timeout(3000)
    except Exception:
        logger.debug("No Google email input — may be pre-selected")

    code_input = page.locator('input[type="tel"], input[aria-label*="code"]')
    try:
        await code_input.wait_for(timeout=5000)
        if await code_input.count() > 0 and push_chat_fn:
            await push_chat_fn(
                "Google is requesting an email verification code. "
                "Please check your email and reply with the code."
            )
            logger.info("Waiting for operator to provide verification code via chat")
    except Exception:
        logger.debug("No verification code step")
