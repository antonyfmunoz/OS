"""Clerk browser auth adapter — single login flow for all UMH browser automation.

Consolidates 3 duplicate Clerk login implementations:
  - scripts/browser_gate_collector.py (sync, _ensure_auth)
  - scripts/c29_class_b_runner.py (async, _clerk_login)
  - scripts/c29_thesis_runner.py (async, _clerk_login)

Credentials via env vars: UMH_COCKPIT_EMAIL, UMH_COCKPIT_PASSWORD.
Injected by `op run --env-file=<tpl>` at the dispatch layer.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_AUTH_DIR = os.path.join(os.path.expanduser("~"), ".umh", "playwright-auth")
_DEFAULT_MAX_AGE_HOURS = 12.0
_POST_LOGIN_SELECTORS = (
    "[data-testid='left-rail'], nav, .wv-left-rail, .bg-surface, button[title*=\"IDE\"]"
)


def _get_credentials() -> tuple[str, str]:
    email = os.environ.get("UMH_COCKPIT_EMAIL", "")
    password = os.environ.get("UMH_COCKPIT_PASSWORD", "")
    return email, password


def validate_auth_state(state_path: str, max_age_hours: float = _DEFAULT_MAX_AGE_HOURS) -> bool:
    """Check if saved auth state exists and is within TTL."""
    if not os.path.exists(state_path):
        return False
    age_hours = (time.time() - os.path.getmtime(state_path)) / 3600
    return age_hours < max_age_hours


def get_default_state_path(browser_type: str = "chromium") -> str:
    """Return default path for persisted auth state."""
    os.makedirs(_DEFAULT_AUTH_DIR, mode=0o700, exist_ok=True)
    return os.path.join(_DEFAULT_AUTH_DIR, f"{browser_type}_state.json")


def _clerk_login_sync(
    page: Any,
    email: str,
    password: str,
    post_login_selector: str = _POST_LOGIN_SELECTORS,
    timeout_ms: int = 30000,
) -> bool:
    """Synchronous Playwright Clerk login flow."""
    email_input = page.locator('input[name="identifier"], input[type="email"]')
    if email_input.count() == 0:
        logger.debug("No email input found — may already be authenticated")
        return True

    if not email or not password:
        logger.warning("Credentials empty — login will fail. Check op run / env vars.")

    email_input.fill(email)
    continue_btn = page.locator('button:visible:has-text("Continue")')
    if continue_btn.count() > 0:
        continue_btn.first.click()
        time.sleep(2)

    pw_input = page.locator('input[type="password"]')
    if pw_input.count() > 0:
        pw_input.fill(password)
        submit_btn = page.locator(
            'button:visible:has-text("Continue"), button:visible:has-text("Sign in")'
        )
        if submit_btn.count() > 0:
            submit_btn.first.click()
            time.sleep(3)

    page.wait_for_selector(post_login_selector, timeout=timeout_ms)
    time.sleep(2)
    return True


async def _clerk_login_async(
    page: Any,
    email: str,
    password: str,
    post_login_selector: str = _POST_LOGIN_SELECTORS,
    timeout_ms: int = 30000,
) -> bool:
    """Async Playwright Clerk login flow."""
    try:
        await page.wait_for_selector(post_login_selector, timeout=3000)
        logger.info("Already authenticated — post-login selector detected.")
        return True
    except Exception:
        pass

    try:
        email_input = await page.wait_for_selector(
            "input[name='identifier'], input[type='email'], "
            "input[placeholder*='email'], input[placeholder*='Email']",
            timeout=timeout_ms,
        )
        if email_input is None:
            logger.error("Email input not found.")
            return False

        await email_input.fill(email)
        await page.wait_for_timeout(500)

        visible_btn = page.locator(
            "button[type='submit']:visible, "
            "button:visible:has-text('Continue'), "
            "button:visible:has-text('Sign in')"
        ).first
        if await visible_btn.count() > 0:
            await visible_btn.click()
        else:
            await page.keyboard.press("Enter")

        await page.wait_for_timeout(2000)

        password_input = await page.query_selector("input[name='password'], input[type='password']")
        if password_input:
            if not password:
                logger.error("Password input found but UMH_COCKPIT_PASSWORD not set.")
                return False
            await password_input.fill(password)
            await page.wait_for_timeout(500)

            pw_btn = page.locator(
                "button[type='submit']:visible, "
                "button:visible:has-text('Continue'), "
                "button:visible:has-text('Sign in')"
            ).first
            if await pw_btn.count() > 0:
                await pw_btn.click()
            else:
                await page.keyboard.press("Enter")

        await page.wait_for_selector(post_login_selector, timeout=timeout_ms)
        logger.info("Login successful.")
        return True

    except Exception as exc:
        logger.error("Login failed: %s", exc)
        return False


def ensure_clerk_auth(
    pw: Any,
    browser_type: str = "chromium",
    url: str = "",
    state_path: str | None = None,
    max_age_hours: float = _DEFAULT_MAX_AGE_HOURS,
    post_login_selector: str = _POST_LOGIN_SELECTORS,
    channel: str = "chrome",
) -> str:
    """Sync entry point. Ensures valid Clerk auth state. Returns path to state file."""
    if state_path is None:
        state_path = get_default_state_path(browser_type)

    if validate_auth_state(state_path, max_age_hours):
        age_h = (time.time() - os.path.getmtime(state_path)) / 3600
        logger.info("Auth state for %s is %.1fh old — reusing", browser_type, age_h)
        return state_path

    email, password = _get_credentials()
    logger.info("Logging into Clerk via %s...", browser_type)

    launcher = getattr(pw, browser_type)
    browser = launcher.launch(channel=channel, headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto(url, wait_until="load", timeout=30000)
    time.sleep(3)

    _clerk_login_sync(page, email, password, post_login_selector)

    context.storage_state(path=state_path)
    try:
        os.chmod(state_path, 0o600)
    except OSError:
        pass
    logger.info("Auth state saved to %s", state_path)

    browser.close()
    return state_path


async def ensure_clerk_auth_async(
    pw: Any,
    browser_type: str = "chromium",
    url: str = "",
    state_path: str | None = None,
    max_age_hours: float = _DEFAULT_MAX_AGE_HOURS,
    post_login_selector: str = _POST_LOGIN_SELECTORS,
    channel: str = "chrome",
    viewport: dict[str, int] | None = None,
) -> tuple[str, Any]:
    """Async entry point. Returns (state_path, browser_context).

    The caller owns the context and must close the browser when done.
    """
    if state_path is None:
        state_path = get_default_state_path(browser_type)

    email, password = _get_credentials()
    launcher = getattr(pw, browser_type)
    browser = await launcher.launch(channel=channel, headless=False)

    vp = viewport or {"width": 1920, "height": 1080}

    if validate_auth_state(state_path, max_age_hours):
        try:
            context = await browser.new_context(storage_state=state_path, viewport=vp)
            logger.info("Loaded saved auth state from %s", state_path)
            return state_path, context
        except Exception:
            logger.warning("Saved auth state invalid — re-authenticating")

    context = await browser.new_context(viewport=vp)
    page = await context.new_page()
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    success = await _clerk_login_async(page, email, password, post_login_selector)
    if not success:
        logger.error("Clerk login failed")

    state_dir = Path(state_path).parent
    state_dir.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=state_path)
    logger.info("Auth state saved to %s", state_path)

    return state_path, context
