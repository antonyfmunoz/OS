"""ChatGPT data export trigger — deterministic Playwright script."""

import logging
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

_CHATGPT_SETTINGS_URL = "https://chat.openai.com/#settings/DataControls"


async def trigger_chatgpt_export(request: ExportRequest) -> ExportResult:
    """Trigger a data export from ChatGPT settings page.

    Navigates to ChatGPT Settings > Data Controls > Export,
    clicks the export button, and confirms.

    Args:
        request: ExportRequest with service="chatgpt"

    Returns:
        ExportResult with status "export_requested" or "failed"
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    pm = ProfileManager(service="chatgpt", headless=True)

    try:
        await pm.start()
        logger.info("[chatgpt_export] Navigating to ChatGPT settings")
        await pm.navigate(_CHATGPT_SETTINGS_URL)

        # Wait for page load
        page_loaded = await pm.wait_for("body", timeout=15000)
        if not page_loaded:
            error = "ChatGPT page did not load within 15s"
            logger.error(f"[chatgpt_export] {error}")
            await _screenshot(pm, "chatgpt_export_page_load_fail")
            return ExportResult(
                service="chatgpt",
                status="failed",
                timestamp=timestamp,
                error=error,
            )

        # Check if login is required
        current_url = pm._page.url if pm._page else ""
        if "auth" in current_url or "login" in current_url:
            logger.info("[chatgpt_export] Login page detected, handling MFA")
            mfa_result = await pm.handle_mfa(request.mfa_handler)
            if not mfa_result and request.mfa_handler:
                error = f"MFA handling failed (type={request.mfa_handler})"
                await _screenshot(pm, "chatgpt_export_mfa_fail")
                return ExportResult(
                    service="chatgpt",
                    status="failed",
                    timestamp=timestamp,
                    error=error,
                )

        # Navigate settings path: Settings > Data Controls
        # Try clicking settings gear if not already on settings page
        if "settings" not in (pm._page.url if pm._page else "").lower():
            settings_selectors = [
                '[data-testid="settings-button"]',
                'button[aria-label*="Settings" i]',
                'nav a[href*="settings"]',
            ]
            for selector in settings_selectors:
                if await pm.click(selector, timeout=3000):
                    logger.info(f"[chatgpt_export] Opened settings via: {selector}")
                    break

        # Click Data Controls tab
        data_controls_selectors = [
            '[data-testid="data-controls-tab"]',
            'button:has-text("Data controls")',
            'a:has-text("Data controls")',
        ]
        for selector in data_controls_selectors:
            if await pm.click(selector, timeout=3000):
                logger.info(f"[chatgpt_export] Clicked Data Controls: {selector}")
                break

        # Look for export button
        export_selectors = [
            '[data-testid="export-data-button"]',
            'button[aria-label*="export" i]',
            'button:has-text("Export")',
            'button:has-text("Export data")',
        ]

        clicked = False
        for selector in export_selectors:
            clicked = await pm.click(selector, timeout=3000)
            if clicked:
                logger.info(f"[chatgpt_export] Clicked export button: {selector}")
                break

        if not clicked:
            # Fallback: JS text search
            try:
                clicked = await pm._page.evaluate("""() => {
                    const buttons = [...document.querySelectorAll('button, a')];
                    const target = buttons.find(b => {
                        const text = b.innerText.toLowerCase();
                        return text.includes('export') && !text.includes('import');
                    });
                    if (target) { target.click(); return true; }
                    return false;
                }""")
            except Exception as e:
                logger.warning(f"[chatgpt_export] JS fallback click failed: {e}")
                clicked = False

        if not clicked:
            error = "Could not find export button on ChatGPT Data Controls page"
            logger.error(f"[chatgpt_export] {error}")
            await _screenshot(pm, "chatgpt_export_no_button")
            return ExportResult(
                service="chatgpt",
                status="failed",
                timestamp=timestamp,
                error=error,
            )

        # Handle confirmation dialog
        await pm.wait_for('[role="dialog"], [data-state="open"]', timeout=5000)

        confirm_selectors = [
            '[data-testid="confirm-export"]',
            'button:has-text("Confirm export")',
            'button:has-text("Confirm")',
            'button:has-text("Yes")',
        ]
        for selector in confirm_selectors:
            if await pm.click(selector, timeout=3000):
                logger.info(f"[chatgpt_export] Confirmed export: {selector}")
                break

        # Success
        await _screenshot(pm, "chatgpt_export_success")
        logger.info("[chatgpt_export] Export request submitted successfully")

        return ExportResult(
            service="chatgpt",
            status="export_requested",
            timestamp=timestamp,
            metadata={"settings_url": _CHATGPT_SETTINGS_URL},
        )

    except Exception as e:
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        error_msg = str(e)
        if isinstance(e, PlaywrightTimeout):
            error_msg = f"Playwright timeout: {e}"
        logger.error(f"[chatgpt_export] Failed: {error_msg}")
        await _screenshot(pm, "chatgpt_export_error")
        return ExportResult(
            service="chatgpt",
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
        logger.info(f"[chatgpt_export] Screenshot saved: {path}")
    except Exception as e:
        logger.warning(f"[chatgpt_export] Screenshot failed: {e}")
