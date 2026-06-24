"""C28 Panel Audit — runs ON Beast with real Playwright display.

Navigates every cockpit panel, captures evidence, rates each.
Called by c28_certification.py on VPS via SSH, or directly on Beast.

Usage (on Beast):
  python tests/certification/c28_panel_audit.py --url https://universalmetaharness.tech
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

AUTH_STATE_DIR = os.path.join(os.path.expanduser("~"), ".umh", "playwright-auth")

# (route_id, label) — must match cockpit/src/renderer/types/routes.ts
# Only primary+system visibility panels shown in LeftRail
PANELS = [
    ("commandcenter", "Command Center"),
    ("work", "Work"),
    ("agents", "Agents"),
    ("approvals", "Approvals"),
    ("activity", "Activity"),
    ("editor", "Meta IDE"),
    ("execution", "Execution"),
    ("organismmap", "Organism Map"),
    ("rooms", "Conference Rooms"),
    ("vision", "Vision"),
    ("broadcast", "Broadcast"),
    ("knowledge", "Knowledge"),
    ("settings", "Settings"),
    ("unifiedexecution", "Unified Execution"),
    ("buildloop", "Build Loop"),
    ("projectionintegration", "Projection Integration"),
    ("orchestratorawareness", "Orchestrator"),
    ("operatingloopview", "Operating Loop"),
    ("sessionresume", "Session Resume"),
    ("delegation", "Delegation"),
    ("operations", "Operations"),
]


@dataclass
class PanelEvidence:
    panel_id: str = ""
    panel_label: str = ""
    navigated: bool = False
    rendered: bool = False
    console_errors: int = 0
    network_errors: int = 0
    interactive_elements: int = 0
    clickable_tested: int = 0
    screenshot_path: str = ""
    notes: str = ""
    console_messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "panel_label": self.panel_label,
            "navigated": self.navigated,
            "rendered": self.rendered,
            "console_errors": self.console_errors,
            "network_errors": self.network_errors,
            "interactive_elements": self.interactive_elements,
            "clickable_tested": self.clickable_tested,
            "screenshot_path": self.screenshot_path,
            "notes": self.notes,
            "console_messages": self.console_messages[:20],
        }


def _get_auth_state(browser_type: str = "chromium") -> str:
    return os.path.join(AUTH_STATE_DIR, f"{browser_type}_state.json")


def audit_panels(
    url: str,
    screenshot_dir: str = "",
    panels: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Run panel audit with Playwright. Returns structured evidence dict."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "playwright not installed", "panel_audit": {}}

    if panels is None:
        panels = PANELS

    if not screenshot_dir:
        screenshot_dir = os.path.join(
            os.environ.get("UMH_ROOT", r"C:\dev\dev\OS"),
            "data", "certification", "c28", "screenshots",
        )
    os.makedirs(screenshot_dir, exist_ok=True)

    results: dict[str, Any] = {}

    with sync_playwright() as pw:
        auth_state = _get_auth_state()
        has_auth = os.path.exists(auth_state)

        browser = pw.chromium.launch(channel="chrome", headless=False)

        if has_auth:
            context = browser.new_context(
                storage_state=auth_state,
                viewport={"width": 1920, "height": 1080},
            )
        else:
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
            )

        page = context.new_page()

        console_errors: list[str] = []
        network_errors: list[str] = []

        def on_console(msg):
            if msg.type == "error":
                console_errors.append(msg.text[:200])

        def on_response(resp):
            if resp.status >= 400 and not resp.url.endswith((".ico", ".png", ".svg")):
                network_errors.append(f"{resp.status} {resp.url[:100]}")

        page.on("console", on_console)
        page.on("response", on_response)

        page.goto(url, wait_until="load", timeout=30000)
        time.sleep(5)

        if not has_auth:
            print("WARNING: No auth state — panels may not render behind Clerk", file=sys.stderr)

        for panel_id, panel_label in panels:
            console_errors.clear()
            network_errors.clear()

            evidence = PanelEvidence(
                panel_id=panel_id,
                panel_label=panel_label,
            )

            try:
                # Strategy 1: Click nav button by title attribute (collapsed LeftRail)
                nav_btn = page.locator(f'button[title="{panel_label}"]')
                if nav_btn.count() > 0:
                    nav_btn.first.click()
                    time.sleep(2)
                    evidence.navigated = True
                else:
                    # Strategy 2: Click by visible text (expanded LeftRail)
                    text_btn = page.locator(f'button:has-text("{panel_label}")')
                    if text_btn.count() > 0:
                        text_btn.first.click()
                        time.sleep(2)
                        evidence.navigated = True
                    else:
                        # Strategy 3: Use keyboard shortcut if available
                        # Strategy 4: Use page.evaluate to call store directly
                        navigated = page.evaluate(f"""() => {{
                            // Find the Zustand store via React internals
                            const root = document.getElementById('root');
                            if (!root || !root._reactRootContainer && !root.__reactFiber) {{
                                // Try direct store manipulation via module scope
                                const buttons = document.querySelectorAll('nav button');
                                for (const b of buttons) {{
                                    if (b.title === '{panel_label}' ||
                                        b.textContent?.trim().toUpperCase() === '{panel_label}'.toUpperCase()) {{
                                        b.click();
                                        return true;
                                    }}
                                }}
                                return false;
                            }}
                            return false;
                        }}""")
                        evidence.navigated = bool(navigated)
                        if evidence.navigated:
                            time.sleep(2)
                        else:
                            evidence.notes = f"Panel '{panel_label}' not reachable via nav buttons"

                if evidence.navigated:
                    # Check if content rendered
                    main_content = page.locator('main, [role="main"], .panel-content, [class*="panel"]')
                    evidence.rendered = main_content.count() > 0

                    # Count interactive elements
                    buttons = page.locator('button:visible')
                    inputs = page.locator('input:visible, select:visible, textarea:visible')
                    evidence.interactive_elements = buttons.count() + inputs.count()

                    # Screenshot
                    ss_path = os.path.join(screenshot_dir, f"{panel_id}.png")
                    page.screenshot(path=ss_path, full_page=False)
                    evidence.screenshot_path = ss_path

            except Exception as exc:
                evidence.notes = f"Error: {str(exc)[:200]}"

            evidence.console_errors = len(console_errors)
            evidence.network_errors = len(network_errors)
            evidence.console_messages = list(console_errors)

            results[panel_id] = evidence.to_dict()
            status = "PASS" if evidence.navigated and evidence.rendered else "FAIL"
            print(f"  [{status}] {panel_label}: navigated={evidence.navigated} "
                  f"rendered={evidence.rendered} "
                  f"errors={evidence.console_errors} "
                  f"interactive={evidence.interactive_elements}",
                  file=sys.stderr)

        browser.close()

    return {"panel_audit": results}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="C28 Panel Audit (runs on Beast)")
    parser.add_argument("--url", default="https://universalmetaharness.tech")
    parser.add_argument("--screenshot-dir", default="")
    parser.add_argument("--panels", default="", help="Comma-separated panel IDs")
    parser.add_argument("--output-json", action="store_true")
    args = parser.parse_args()

    panels = None
    if args.panels:
        panel_ids = [p.strip() for p in args.panels.split(",")]
        panel_map = {pid: plabel for pid, plabel in PANELS}
        panels = [(pid, panel_map.get(pid, pid)) for pid in panel_ids]

    result = audit_panels(
        url=args.url,
        screenshot_dir=args.screenshot_dir,
        panels=panels,
    )

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        audit = result.get("panel_audit", {})
        nav_count = sum(1 for d in audit.values() if d.get("navigated"))
        render_count = sum(1 for d in audit.values() if d.get("rendered"))
        error_count = sum(d.get("console_errors", 0) for d in audit.values())
        print(f"\n{'='*50}")
        print(f"Panel Audit Summary: {nav_count}/{len(audit)} navigated, "
              f"{render_count}/{len(audit)} rendered, {error_count} total console errors")
        for pid, data in audit.items():
            status = "PASS" if data.get("rendered") and data.get("console_errors", 0) == 0 else "FAIL"
            print(f"  [{status}] {data.get('panel_label', pid)}: "
                  f"nav={data.get('navigated')} render={data.get('rendered')} "
                  f"errors={data.get('console_errors', 0)} "
                  f"interactive={data.get('interactive_elements', 0)}")


if __name__ == "__main__":
    main()
