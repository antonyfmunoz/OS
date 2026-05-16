"""Claude data export trigger — deterministic Playwright script."""

import sys

sys.path.insert(0, "/opt/OS")

import logging
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv("/opt/OS/runtime/.env")
load_dotenv("/opt/OS/services/.env", override=True)

from adapters.browser_exports.contract import ExportRequest, ExportResult
from adapters.browser_exports.profile_manager import ProfileManager

logger = logging.getLogger(__name__)

_LOGS_DIR = Path("/opt/OS/logs")
_LOGS_DIR.mkdir(parents=True, exist_ok=True)

_SETTINGS_URL = "https://claude.ai/settings"


async def trigger_claude_export(request: ExportRequest) -> ExportResult:
    """Trigger a data export from Claude AI settings page.

    Navigates to claude.ai/settings, finds the data export section,
    and clicks the export/request button.

    Args:
        request: ExportRequest with service="claude"

    Returns:
        ExportResult with status "export_requested" or "failed"
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    pm = ProfileManager(service="claude", headless=True)

    try:
        await pm.start()
        logger.info("[claude_export] Navigating to Claude settings")
        await pm.navigate(_SETTINGS_URL)

        # Wait for the settings page to load
        page_loaded = await pm.wait_for("body", timeout=15000)
        if not page_loaded:
            error = "Settings page did not load within 15s"
            logger.error(f"[claude_export] {error}")
            await _screenshot(pm, "claude_export_page_load_fail")
            return ExportResult(
                service="claude",
                status="failed",
                timestamp=timestamp,
                error=error,
            )

        # Check if we need to handle MFA/login
        current_url = pm._page.url if pm._page else ""
        if "login" in current_url or "signin" in current_url:
            logger.info("[claude_export] Login page detected, handling MFA")
            mfa_result = await pm.handle_mfa(request.mfa_handler)
            if not mfa_result and request.mfa_handler:
                error = f"MFA handling failed (type={request.mfa_handler})"
                await _screenshot(pm, "claude_export_mfa_fail")
                return ExportResult(
                    service="claude",
                    status="failed",
                    timestamp=timestamp,
                    error=error,
                )

        # Look for export/download section using priority selectors:
        # 1. data-testid attributes
        # 2. aria-label
        # 3. CSS text content matching
        export_selectors = [
            '[data-testid="export-data-button"]',
            '[data-testid="download-data-button"]',
            'button[aria-label*="export" i]',
            'button[aria-label*="download" i]',
            'a[aria-label*="export" i]',
            'a[aria-label*="download" i]',
        ]

        clicked = False
        for selector in export_selectors:
            clicked = await pm.click(selector, timeout=3000)
            if clicked:
                logger.info(f"[claude_export] Clicked export button: {selector}")
                break

        if not clicked:
            # Fallback: search for text-based buttons
            try:
                clicked = await pm._page.evaluate("""() => {
                    const buttons = [...document.querySelectorAll('button, a')];
                    const target = buttons.find(b => {
                        const text = b.innerText.toLowerCase();
                        return text.includes('export') || text.includes('download my data')
                            || text.includes('request data');
                    });
                    if (target) { target.click(); return true; }
                    return false;
                }""")
            except Exception as e:
                logger.warning(f"[claude_export] JS fallback click failed: {e}")
                clicked = False

        if not clicked:
            error = "Could not find export/download button on settings page"
            logger.error(f"[claude_export] {error}")
            await _screenshot(pm, "claude_export_no_button")
            return ExportResult(
                service="claude",
                status="failed",
                timestamp=timestamp,
                error=error,
            )

        # Wait briefly for confirmation dialog or toast
        await pm.wait_for('[role="dialog"], [role="alert"], .toast', timeout=5000)

        # Check for confirmation button in dialog
        confirm_selectors = [
            '[data-testid="confirm-export"]',
            'button[aria-label*="confirm" i]',
        ]
        for selector in confirm_selectors:
            confirm_clicked = await pm.click(selector, timeout=3000)
            if confirm_clicked:
                logger.info(f"[claude_export] Confirmed export dialog: {selector}")
                break

        # Fallback confirm via text match
        if not confirm_clicked:
            try:
                await pm._page.evaluate("""() => {
                    const buttons = [...document.querySelectorAll('button')];
                    const confirm = buttons.find(b => {
                        const text = b.innerText.toLowerCase();
                        return text.includes('confirm') || text.includes('yes')
                            || text.includes('request');
                    });
                    if (confirm) confirm.click();
                }""")
            except Exception:
                pass

        # Success screenshot
        await _screenshot(pm, "claude_export_success")
        logger.info("[claude_export] Export request submitted successfully")

        return ExportResult(
            service="claude",
            status="export_requested",
            timestamp=timestamp,
            metadata={"settings_url": _SETTINGS_URL},
        )

    except Exception as e:
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        error_msg = str(e)
        if isinstance(e, PlaywrightTimeout):
            error_msg = f"Playwright timeout: {e}"
        logger.error(f"[claude_export] Failed: {error_msg}")
        await _screenshot(pm, "claude_export_error")
        return ExportResult(
            service="claude",
            status="failed",
            timestamp=timestamp,
            error=error_msg,
        )

    finally:
        await pm.stop()


async def _screenshot(pm: ProfileManager, name: str) -> None:
    """Take a screenshot for debugging, saving to /opt/OS/logs/."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = str(_LOGS_DIR / f"{name}_{ts}.png")
    try:
        await pm.screenshot(path)
        logger.info(f"[claude_export] Screenshot saved: {path}")
    except Exception as e:
        logger.warning(f"[claude_export] Screenshot failed: {e}")
