"""Fire a single browser export — runs headless, screenshots every step.

Usage:
    python3 scripts/fire_export.py claude
    python3 scripts/fire_export.py chatgpt
    python3 scripts/fire_export.py instagram

Environment:
    BROWSER_HEADLESS              — "true"/"false" (default: true)
    PLAYWRIGHT_USER_DATA_DIR_SERVICE — override profile dir for this service
    EOS_EXPORT_MFA_CALLBACK_URL   — if set, bridge-mediated MFA (no stdin wait)
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.browser_exports.contract import ExportRequest
from adapters.browser_exports.profile_manager import ProfileManager

_REPO = Path(__file__).resolve().parent.parent
EXPORT_DIR = Path(os.environ.get("EOS_EXPORT_DIR", str(_REPO / "data" / "runtime" / "exports")))
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

LOGS_DIR = Path(os.environ.get("EOS_EXPORT_LOGS_DIR", str(_REPO / "logs" / "exports")))
LOGS_DIR.mkdir(parents=True, exist_ok=True)


async def _wait_for_bridge_mfa(pm: ProfileManager, service: str, mfa_type: str, timeout: int = 300) -> bool:
    """Wait for MFA code delivered via bridge HTTP callback.

    The bridge handler (export_bridge_handler.py) monitors our stdout for
    MFA_CHALLENGE, notifies VPS, and delivers the user's response to
    /mfa-response on the local bridge. Meanwhile, we poll for page navigation
    (push/approve case) or wait for the code to appear in a local file
    that the bridge writes.

    For PUSH type: just poll page URL until it navigates away from challenge.
    For TOTP/SMS/EMAIL: bridge injects code via Playwright form fill.
    """
    elapsed = 0
    interval = 5

    while elapsed < timeout:
        await asyncio.sleep(interval)
        elapsed += interval

        if pm._page:
            url = pm._page.url
            mfa_indicators = ["login", "signin", "verify", "challenge",
                              "accounts/login", "auth", "two-factor", "mfa", "otp"]
            still_on_mfa = any(ind in url.lower() for ind in mfa_indicators)

            if not still_on_mfa:
                print(f"[{service}] Page navigated away from MFA — resolved!")
                return True

        if elapsed % 30 == 0:
            print(f"[{service}] Still waiting for MFA resolution... ({elapsed}s)")

    return False


async def run_export(service: str) -> None:
    """Fire export for a single service, pausing on MFA for manual action."""
    print(f"[{service}] Starting export attempt...")

    headless = os.environ.get("BROWSER_HEADLESS", "true").lower() != "false"
    pm = ProfileManager(service=service, headless=headless)
    await pm.start()

    urls = {
        "claude": "https://claude.ai/settings",
        "chatgpt": "https://chatgpt.com/#settings/DataControls",
        "instagram": "https://www.instagram.com/download/request/",
    }

    url = urls[service]
    print(f"[{service}] Navigating to {url}")
    await pm.navigate(url)

    # Screenshot: initial page state
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shot_path = str(LOGS_DIR / f"{service}_step1_initial_{ts}.png")
    await pm.screenshot(shot_path)
    print(f"[{service}] Screenshot saved: {shot_path}")

    # Check current URL for login/MFA redirects
    current_url = pm._page.url if pm._page else ""
    print(f"[{service}] Current URL: {current_url}")

    mfa_indicators = ["login", "signin", "verify", "challenge", "accounts/login",
                      "auth", "two-factor", "mfa", "otp"]
    hit_mfa = any(ind in current_url.lower() for ind in mfa_indicators)

    if not hit_mfa:
        # Also check page content for login forms
        try:
            page_text = await pm._page.inner_text("body")
            login_keywords = ["sign in", "log in", "enter your email",
                              "enter your password", "verification code",
                              "two-factor", "confirm your identity"]
            hit_mfa = any(kw in page_text.lower() for kw in login_keywords)
        except Exception:
            pass

    if hit_mfa:
        # Screenshot the MFA/login page
        mfa_shot = str(LOGS_DIR / f"{service}_MFA_CHALLENGE_{ts}.png")
        await pm.screenshot(mfa_shot)
        print(f"\n{'='*60}")
        print(f"  MFA CHALLENGE DETECTED — {service.upper()}")
        print(f"  URL: {current_url}")
        print(f"  Screenshot: {mfa_shot}")
        print(f"  ACTION NEEDED: Complete login/MFA manually or confirm type")
        print(f"{'='*60}\n")

        # Detect MFA type from page content
        try:
            body = await pm._page.inner_text("body")
            body_lower = body.lower()

            if "authenticator" in body_lower or "totp" in body_lower or "6-digit code" in body_lower:
                mfa_type = "TOTP"
            elif "text message" in body_lower or "sms" in body_lower or "phone number" in body_lower:
                mfa_type = "SMS"
            elif "push" in body_lower or "approve" in body_lower or "notification" in body_lower:
                mfa_type = "PUSH"
            elif "email" in body_lower and ("code" in body_lower or "verify" in body_lower):
                mfa_type = "EMAIL_2FA"
            elif "password" in body_lower and "login" in current_url.lower():
                mfa_type = "PASSWORD_FIRST (no MFA yet)"
            else:
                mfa_type = "UNKNOWN — check screenshot"

            print(f"  Observed MFA type: {mfa_type}")
        except Exception as e:
            mfa_type = f"DETECTION_FAILED: {e}"
            print(f"  MFA type detection failed: {e}")

        # Write MFA observation to file for future autonomous runs
        mfa_log = LOGS_DIR / f"{service}_mfa_observed.txt"
        mfa_log.write_text(
            f"service: {service}\n"
            f"observed: {datetime.now(timezone.utc).isoformat()}\n"
            f"url: {current_url}\n"
            f"mfa_type: {mfa_type}\n"
        )

        # Bridge-mediated MFA: wait for code via HTTP callback
        mfa_callback_url = os.environ.get("EOS_EXPORT_MFA_CALLBACK_URL")
        if mfa_callback_url:
            print(f"[{service}] Bridge MFA mode — waiting for code via callback (300s timeout)...")
            mfa_resolved = await _wait_for_bridge_mfa(pm, service, mfa_type, timeout=300)
        else:
            # Standalone mode: wait for manual page navigation
            print(f"[{service}] Waiting up to 120s for manual MFA completion...")
            mfa_resolved = await pm.handle_mfa("manual", timeout=120)

        if mfa_resolved:
            print(f"[{service}] MFA resolved! Continuing...")
            post_mfa_shot = str(LOGS_DIR / f"{service}_post_mfa_{ts}.png")
            await pm.screenshot(post_mfa_shot)
            print(f"[{service}] Post-MFA screenshot: {post_mfa_shot}")
        else:
            print(f"[{service}] MFA NOT resolved within timeout. Profile NOT seeded.")
            await pm.stop()
            return
    else:
        print(f"[{service}] No MFA detected — session appears authenticated!")

    # If we're past login, trigger the actual export
    print(f"[{service}] Attempting export action...")

    if service == "claude":
        from adapters.browser_exports.claude_export import trigger_claude_export
        req = ExportRequest(
            service="claude",
            credentials_ref="claude_profile",
            output_dir=EXPORT_DIR,
            mfa_handler=None,
        )
        # We already have an authenticated page; reuse the profile
        await pm.stop()
        result = await trigger_claude_export(req)
        print(f"[claude] Export result: {result.status}")
        if result.error:
            print(f"[claude] Error: {result.error}")

    elif service == "chatgpt":
        from adapters.browser_exports.chatgpt_export import trigger_chatgpt_export
        req = ExportRequest(
            service="chatgpt",
            credentials_ref="chatgpt_profile",
            output_dir=EXPORT_DIR,
            mfa_handler=None,
        )
        await pm.stop()
        result = await trigger_chatgpt_export(req)
        print(f"[chatgpt] Export result: {result.status}")
        if result.error:
            print(f"[chatgpt] Error: {result.error}")

    elif service == "instagram":
        from adapters.browser_exports.instagram_export import trigger_instagram_export
        req = ExportRequest(
            service="instagram",
            credentials_ref="instagram_profile",
            output_dir=EXPORT_DIR,
            mfa_handler=None,
        )
        await pm.stop()
        result = await trigger_instagram_export(req)
        print(f"[instagram] Export result: {result.status}")
        if result.error:
            print(f"[instagram] Error: {result.error}")

    print(f"\n[{service}] Export attempt complete.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/fire_export.py <claude|chatgpt|instagram>")
        sys.exit(1)

    service = sys.argv[1].lower()
    if service not in ("claude", "chatgpt", "instagram"):
        print(f"Unknown service: {service}. Use: claude, chatgpt, instagram")
        sys.exit(1)

    asyncio.run(run_export(service))
