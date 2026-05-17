"""browser_adapter.py — Camoufox browser wrapper for anti-detect automation.

Wraps Camoufox (humanized Firefox fork) with a Playwright-compatible API surface.
Drop-in replacement for ProfileManager's browser launch — call sites use the same
page.goto(), page.fill(), page.click(), page.screenshot() interface.

Camoufox auto-passes Cloudflare without manual cookie seeding.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_PROFILES_BASE = Path(
    os.getenv("CAMOUFOX_PROFILES_DIR", str(Path.home() / ".camoufox-profiles"))
)


async def launch_browser(
    service: str,
    headless: bool = False,
    geoip: bool = True,
    humanize: bool | float = True,
    **kwargs,
):
    """Launch a Camoufox browser instance with anti-detect fingerprinting.

    Returns a (context, page, cleanup) tuple. `cleanup` is an async callable
    that closes browser + stops playwright.

    The page object has the standard Playwright API: goto(), fill(), click(),
    screenshot(), query_selector(), inner_text(), url, etc.
    """
    from camoufox.async_api import AsyncCamoufox

    profile_dir = _PROFILES_BASE / service
    profile_dir.mkdir(parents=True, exist_ok=True)

    os_targets = kwargs.pop("os_targets", ["windows"])

    logger.info(
        "[BrowserAdapter] Launching Camoufox for %s (headless=%s, geoip=%s, humanize=%s)",
        service, headless, geoip, humanize,
    )

    camoufox = AsyncCamoufox(
        headless=headless,
        humanize=humanize,
        os=os_targets,
        geoip=geoip,
        persistent_context=True,
        user_data_dir=str(profile_dir),
        **kwargs,
    )

    context = await camoufox.__aenter__()
    page = context.pages[0] if context.pages else await context.new_page()

    async def cleanup():
        try:
            await camoufox.__aexit__(None, None, None)
        except Exception as exc:
            logger.warning("[BrowserAdapter] Cleanup error: %s", exc)

    logger.info("[BrowserAdapter] Browser launched for %s", service)
    return context, page, cleanup


# ── Emergency Playwright rollback ──────────────────────────────────────────
# async def launch_browser_playwright(service: str, headless: bool = False, **kwargs):
#     """Fallback: launch via Playwright Chromium with stealth flags."""
#     from playwright.async_api import async_playwright
#     profile_dir = _PROFILES_BASE / service
#     profile_dir.mkdir(parents=True, exist_ok=True)
#     pw = await async_playwright().start()
#     context = await pw.chromium.launch_persistent_context(
#         user_data_dir=str(profile_dir),
#         headless=headless,
#         args=["--disable-blink-features=AutomationControlled"],
#         viewport={"width": 1280, "height": 800},
#     )
#     page = context.pages[0] if context.pages else await context.new_page()
#     async def cleanup():
#         await context.close()
#         await pw.stop()
#     return context, page, cleanup
