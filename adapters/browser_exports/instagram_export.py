"""Instagram saved posts export — scrapes saved collection via Playwright."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / "runtime" / ".env")
load_dotenv(_REPO_ROOT / "services" / ".env", override=True)

from adapters.browser_exports.contract import ExportRequest, ExportResult
from adapters.browser_exports.profile_manager import ProfileManager

logger = logging.getLogger(__name__)

_LOGS_DIR = _REPO_ROOT / "logs"
_LOGS_DIR.mkdir(parents=True, exist_ok=True)


async def trigger_instagram_export(request: ExportRequest) -> ExportResult:
    """Export saved posts from Instagram by scrolling through the saved collection.

    Navigates to the user's saved posts page, scrolls through to collect
    post URLs and metadata, then saves as JSON.

    Args:
        request: ExportRequest with service="instagram"

    Returns:
        ExportResult with exported_files pointing to the saved JSON
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    username = os.getenv("INSTAGRAM_USERNAME", "")

    if not username:
        error = "INSTAGRAM_USERNAME not set in environment"
        logger.error(f"[instagram_export] {error}")
        return ExportResult(
            service="instagram",
            status="failed",
            timestamp=timestamp,
            error=error,
        )

    saved_url = f"https://www.instagram.com/{username}/saved/"
    pm = ProfileManager(service="instagram", headless=True)

    try:
        await pm.start()
        logger.info(f"[instagram_export] Navigating to saved posts: {saved_url}")
        await pm.navigate(saved_url)

        # Wait for page to load
        page_loaded = await pm.wait_for("body", timeout=15000)
        if not page_loaded:
            error = "Instagram page did not load within 15s"
            logger.error(f"[instagram_export] {error}")
            await _screenshot(pm, "instagram_export_page_load_fail")
            return ExportResult(
                service="instagram",
                status="failed",
                timestamp=timestamp,
                error=error,
            )

        # Check if login is required
        current_url = pm._page.url if pm._page else ""
        if "login" in current_url or "accounts/login" in current_url:
            logger.info("[instagram_export] Login page detected, handling MFA")
            mfa_result = await pm.handle_mfa(request.mfa_handler)
            if not mfa_result and request.mfa_handler:
                error = f"MFA handling failed (type={request.mfa_handler})"
                await _screenshot(pm, "instagram_export_mfa_fail")
                return ExportResult(
                    service="instagram",
                    status="failed",
                    timestamp=timestamp,
                    error=error,
                )
            # Re-navigate after login
            await pm.navigate(saved_url)

        # Wait for the posts grid to appear
        grid_loaded = await pm.wait_for("article, main [role='main']", timeout=10000)
        if not grid_loaded:
            error = "Saved posts grid did not load"
            logger.warning(f"[instagram_export] {error}")
            await _screenshot(pm, "instagram_export_no_grid")

        # Scroll and collect post links
        posts = await _scroll_and_collect_posts(pm)
        logger.info(f"[instagram_export] Collected {len(posts)} saved posts")

        # Save results to JSON
        output_dir = Path(request.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "saved_posts.json"

        export_data = {
            "username": username,
            "exported_at": timestamp,
            "post_count": len(posts),
            "posts": posts,
        }

        output_path.write_text(json.dumps(export_data, indent=2))
        logger.info(f"[instagram_export] Saved to {output_path}")

        await _screenshot(pm, "instagram_export_success")

        return ExportResult(
            service="instagram",
            status="export_downloaded",
            exported_files=[output_path],
            timestamp=timestamp,
            metadata={"post_count": len(posts), "username": username},
        )

    except Exception as e:
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        error_msg = str(e)
        if isinstance(e, PlaywrightTimeout):
            error_msg = f"Playwright timeout: {e}"
        logger.error(f"[instagram_export] Failed: {error_msg}")
        await _screenshot(pm, "instagram_export_error")
        return ExportResult(
            service="instagram",
            status="failed",
            timestamp=timestamp,
            error=error_msg,
        )

    finally:
        await pm.stop()


async def _scroll_and_collect_posts(pm: ProfileManager, max_scrolls: int = 20) -> list[dict]:
    """Scroll through saved posts grid and extract post URLs and metadata.

    Args:
        pm: ProfileManager with active page
        max_scrolls: Maximum number of scroll iterations

    Returns:
        List of post dicts with url, shortcode, and thumbnail info
    """
    collected_posts: list[dict] = []
    seen_urls: set[str] = set()
    no_new_count = 0

    for scroll_i in range(max_scrolls):
        # Extract post links from current viewport
        new_posts = await pm._page.evaluate("""() => {
            const links = [...document.querySelectorAll('a[href*="/p/"]')];
            return links.map(a => {
                const img = a.querySelector('img');
                return {
                    url: a.href,
                    shortcode: a.href.match(/\\/p\\/([^/]+)/)?.[1] || '',
                    thumbnail: img ? img.src : '',
                    alt_text: img ? (img.alt || '') : '',
                };
            });
        }""")

        added = 0
        for post in new_posts:
            url = post.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                collected_posts.append(post)
                added += 1

        if added == 0:
            no_new_count += 1
            if no_new_count >= 3:
                # No new posts after 3 scrolls — we've reached the end
                logger.info(f"[instagram_export] Reached end of saved posts at scroll {scroll_i}")
                break
        else:
            no_new_count = 0

        # Scroll down
        await pm._page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        # Wait for new content to load
        await pm._page.wait_for_timeout(1500)

    return collected_posts


async def _screenshot(pm: ProfileManager, name: str) -> None:
    """Take a screenshot for debugging, saving to /opt/OS/logs/."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = str(_LOGS_DIR / f"{name}_{ts}.png")
    try:
        await pm.screenshot(path)
        logger.info(f"[instagram_export] Screenshot saved: {path}")
    except Exception as e:
        logger.warning(f"[instagram_export] Screenshot failed: {e}")
