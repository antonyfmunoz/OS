"""Fire a single browser export via Camoufox anti-detect browser.

Uses Camoufox (humanized Firefox fork) to bypass Cloudflare and other bot
detection. Scripted login with MFA branching — zero manual cookie seeding.

Usage:
    python3 scripts/fire_export.py claude
    python3 scripts/fire_export.py chatgpt
    python3 scripts/fire_export.py instagram

Environment:
    BROWSER_HEADLESS              — "true"/"false" (default: false for inspection)
    CAMOUFOX_PROFILES_DIR         — persistent profile base dir
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

LOGS_DIR = Path(os.environ.get("EOS_EXPORT_LOGS_DIR", str(_REPO / "logs" / "exports")))
LOGS_DIR.mkdir(parents=True, exist_ok=True)

_MAX_RETRIES = 3


async def run_export(service: str) -> None:
    """Launch Camoufox, authenticate, navigate to export page, trigger export."""
    from services.browser_adapter import launch_browser

    headless = os.environ.get("BROWSER_HEADLESS", "false").lower() == "true"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    svc_log_dir = LOGS_DIR / service
    svc_log_dir.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, _MAX_RETRIES + 1):
        print(f"[{service}] Attempt {attempt}/{_MAX_RETRIES}")
        cleanup = None
        try:
            locale = "en-US" if service == "chatgpt" else None
            context, page, cleanup = await launch_browser(
                service=service,
                headless=headless,
                locale=locale,
            )

            # Step 1: Screenshot initial state
            shot_path = str(svc_log_dir / f"{ts}_step1_initial.png")
            await page.screenshot(path=shot_path, full_page=False)
            print(f"[{service}] Screenshot saved: {shot_path}")

            # Step 2: Authenticate via service-specific auth flow
            print(f"[{service}] Running auth flow...")
            auth_module = _load_auth_flow(service)
            if auth_module:
                authenticated = await auth_module.login(page)
                if not authenticated:
                    fail_shot = str(svc_log_dir / f"{ts}_auth_failed.png")
                    await page.screenshot(path=fail_shot, full_page=False)
                    print(f"[{service}] [ERROR] Authentication failed. Screenshot: {fail_shot}")
                    await cleanup()
                    if attempt < _MAX_RETRIES:
                        continue
                    _try_tier_3(service, fail_shot)
                    sys.exit(1)
                print(f"[{service}] Authenticated successfully")
            else:
                print(f"[{service}] No auth flow module — proceeding unauthenticated")

            # Step 3: Navigate to export page
            export_url = _get_export_url(service)
            print(f"[{service}] Navigating to {export_url}")
            await page.goto(export_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            post_nav_shot = str(svc_log_dir / f"{ts}_step3_export_page.png")
            await page.screenshot(path=post_nav_shot, full_page=False)
            print(f"[{service}] Screenshot saved: {post_nav_shot}")
            print(f"[{service}] Current URL: {page.url}")

            # Step 4: Click export button
            print(f"[{service}] Looking for export button...")
            clicked = await _click_export_button(page, service)
            if not clicked:
                print(f"[{service}] [ERROR] Could not find export button")
                await cleanup()
                if attempt < _MAX_RETRIES:
                    continue
                sys.exit(1)

            await page.wait_for_timeout(5000)

            # Step 5: Verify success
            success_shot = str(svc_log_dir / f"{ts}_success.png")
            await page.screenshot(path=success_shot, full_page=False)
            print(f"[{service}] Screenshot saved: {success_shot}")

            body_text = ""
            try:
                body_text = await page.inner_text("body")
            except Exception:
                pass

            success_markers = _get_success_markers(service)
            found_success = any(m.lower() in body_text.lower() for m in success_markers)

            if found_success:
                print(f"[{service}] [OK] Export requested successfully!")
                print(f"[{service}] Success screenshot: {success_shot}")
            else:
                print(f"[{service}] Export button clicked but no success marker in DOM")
                print(f"[{service}] Screenshot: {success_shot}")

            print(f"\n[{service}] Export attempt complete.")
            await cleanup()
            return

        except Exception as exc:
            print(f"[{service}] [ERROR] Attempt {attempt} failed: {exc}")
            traceback.print_exc()
            if cleanup:
                try:
                    await cleanup()
                except Exception:
                    pass
            if attempt < _MAX_RETRIES:
                print(f"[{service}] Retrying in 5s...")
                await asyncio.sleep(5)
                continue
            _try_tier_3(service, None)
            sys.exit(1)


def _load_auth_flow(service: str):
    """Dynamically load the auth flow module for a service."""
    try:
        if service == "claude":
            from services.auth_flows import claude
            return claude
        elif service == "chatgpt":
            from services.auth_flows import chatgpt
            return chatgpt
        elif service == "instagram":
            from services.auth_flows import instagram
            return instagram
    except ImportError as exc:
        print(f"[{service}] Auth flow not implemented: {exc}")
    return None


def _get_export_url(service: str) -> str:
    urls = {
        "claude": "https://claude.ai/settings",
        "chatgpt": "https://chatgpt.com/#settings/DataControls",
        "instagram": "https://www.instagram.com/download/request/",
    }
    return urls.get(service, "")


def _get_success_markers(service: str) -> list[str]:
    markers = {
        "claude": ["export requested", "export data", "request submitted", "we'll email you"],
        "chatgpt": ["export requested", "export data", "data export"],
        "instagram": ["request submitted", "we'll notify you", "download request"],
    }
    return markers.get(service, [])


async def _click_export_button(page, service: str) -> bool:
    """Find and click the export/request button for a given service."""
    selectors = {
        "claude": [
            'button:has-text("Export")',
            'button:has-text("Request")',
            'button:has-text("Export Data")',
            'a:has-text("Export")',
        ],
        "chatgpt": [
            'button[aria-label*="Export" i]',
            'button:has-text("Export")',
            'button:has-text("Export data")',
            'button:has-text("Confirm export")',
            'button[data-testid*="export" i]',
        ],
        "instagram": [
            'button:has-text("Request")',
            'button:has-text("Next")',
            'button:has-text("Submit")',
        ],
    }

    for selector in selectors.get(service, []):
        try:
            btn = page.locator(selector)
            if await btn.count() > 0:
                await btn.first.click()
                print(f"[{service}] Clicked: {selector}")
                return True
        except Exception:
            continue

    return False


def _try_tier_3(service: str, screenshot_path: str | None) -> None:
    """Invoke tier 3 fallback after exhausting retries."""
    try:
        from services.tier_3_fallback import tier_3_fallback
        screenshot_bytes = None
        if screenshot_path and Path(screenshot_path).exists():
            screenshot_bytes = Path(screenshot_path).read_bytes()
        result = tier_3_fallback(service, screenshot_bytes)
        print(f"[{service}] Tier 3 result: {result}")
    except Exception as exc:
        print(f"[{service}] Tier 3 fallback failed: {exc}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/fire_export.py <claude|chatgpt|instagram>")
        sys.exit(1)

    service = sys.argv[1].lower()
    if service not in ("claude", "chatgpt", "instagram"):
        print(f"Unknown service: {service}. Use: claude, chatgpt, instagram")
        sys.exit(1)

    asyncio.run(run_export(service))
