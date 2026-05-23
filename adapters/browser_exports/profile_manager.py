"""ProfileManager — persistent browser context for authenticated exports."""

import asyncio
import logging
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / "runtime" / ".env")
load_dotenv(_REPO_ROOT / "services" / ".env", override=True)

from substrate.execution.agents.browser_agent import BrowserAgent

logger = logging.getLogger(__name__)

_PROFILES_DIR = Path(
    os.getenv("PLAYWRIGHT_USER_DATA_DIR", str(_REPO_ROOT / "data" / "runtime" / "browser_profiles"))
)


class ProfileManager(BrowserAgent):
    """BrowserAgent subclass that uses persistent browser profiles.

    Maintains login state across runs by storing Chromium user data
    in /opt/OS/data/runtime/browser_profiles/{service}/.
    """

    def __init__(self, service: str, headless: bool = True) -> None:
        super().__init__(headless=headless)
        self.service = service
        # Bridge override: use per-service dir from env if set (Windows path)
        override = os.getenv("PLAYWRIGHT_USER_DATA_DIR_SERVICE")
        self._profile_dir = Path(override) if override else _PROFILES_DIR / service
        self._profile_dir.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        """Launch Chromium with persistent context (preserves cookies/sessions)."""
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._context = await self._pw.chromium.launch_persistent_context(
            user_data_dir=str(self._profile_dir),
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1280, "height": 800},
        )
        # Persistent context has no separate browser handle
        self._browser = None
        self._page = (
            self._context.pages[0] if self._context.pages else await self._context.new_page()
        )

    async def stop(self) -> None:
        """Close the persistent context and Playwright."""
        if self._context:
            await self._context.close()
        if self._pw:
            await self._pw.stop()

    async def handle_mfa(self, mfa_type: str | None, **kwargs) -> str | None:
        """Handle multi-factor authentication challenge.

        Args:
            mfa_type: "totp" | "email_2fa" | "manual" | None

        Returns:
            The MFA code if resolved, None if no MFA needed or manual timeout.
        """
        if mfa_type is None:
            return None

        if mfa_type == "totp":
            return self._handle_totp()
        elif mfa_type == "email_2fa":
            return await self._handle_email_2fa()
        elif mfa_type == "manual":
            return await self._handle_manual(**kwargs)
        else:
            logger.warning(f"[ProfileManager] Unknown MFA type: {mfa_type}")
            return None

    def _handle_totp(self) -> str | None:
        """Generate TOTP code from service-specific secret."""
        secret_var = f"{self.service.upper()}_TOTP_SECRET"
        secret = os.getenv(secret_var)
        if not secret:
            logger.error(f"[ProfileManager] {secret_var} not set in environment")
            return None

        try:
            import pyotp

            totp = pyotp.TOTP(secret)
            code = totp.now()
            logger.info(f"[ProfileManager] Generated TOTP code for {self.service}")
            return code
        except ImportError:
            logger.error("[ProfileManager] pyotp not installed — cannot generate TOTP")
            return None
        except Exception as e:
            logger.error(f"[ProfileManager] TOTP generation failed: {e}")
            return None

    async def _handle_email_2fa(self) -> str | None:
        """Search Gmail for verification code email."""
        try:
            from adapters.google_workspace.gws_connector import GWSConnector

            gws = GWSConnector()
            # Search for recent verification emails from the service
            sender_map = {
                "claude": "noreply@anthropic.com",
                "chatgpt": "noreply@openai.com",
                "instagram": "security@mail.instagram.com",
            }
            sender = sender_map.get(self.service, "")
            if not sender:
                logger.warning(f"[ProfileManager] No known sender for {self.service}")
                return None

            emails = gws.search_emails_from(sender, max_results=3)
            if not emails:
                logger.warning(f"[ProfileManager] No verification emails found from {sender}")
                return None

            # Try to extract code from email snippet/subject
            # TODO: Implement get_email_body in gws_connector for full body parsing
            for email in emails:
                snippet = email.get("snippet", "") + " " + email.get("subject", "")
                # Look for 6-digit codes
                import re

                match = re.search(r"\b(\d{6})\b", snippet)
                if match:
                    code = match.group(1)
                    logger.info(f"[ProfileManager] Found 2FA code in email: {code[:2]}****")
                    return code

            logger.warning("[ProfileManager] Could not extract code from emails")
            return None

        except Exception as e:
            logger.error(f"[ProfileManager] Email 2FA lookup failed: {e}")
            return None

    async def _handle_manual(self, **kwargs) -> str | None:
        """Wait for manual MFA approval (operator must act within 120s).

        Logs a message requesting manual action and polls for page state change.
        """
        timeout = kwargs.get("timeout", 120)
        logger.info(
            f"[ProfileManager] MANUAL MFA REQUIRED for {self.service}. "
            f"Approve the login within {timeout}s."
        )
        # Poll page every 5s to see if MFA was completed externally
        elapsed = 0
        interval = 5
        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval
            # Check if page moved past the MFA challenge
            if self._page:
                url = self._page.url
                # If we've left the MFA/login page, assume success
                if "verify" not in url and "challenge" not in url and "login" not in url:
                    logger.info(
                        "[ProfileManager] Manual MFA appears completed (page navigated away)"
                    )
                    return "manual_approved"
        logger.warning(f"[ProfileManager] Manual MFA timed out after {timeout}s")
        return None
