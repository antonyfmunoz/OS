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

PANELS = [
    ("command-center", "Command Center"),
    ("meta-ide", "Meta IDE"),
    ("execution", "Execution"),
    ("unified-execution", "Unified Execution"),
    ("work", "Work"),
    ("planning", "Planning"),
    ("organism-map", "Organism Map"),
    ("governance", "Governance"),
    ("settings", "Settings"),
    ("deliverables", "Deliverables"),
    ("actions", "Actions"),
    ("distributed-runtime", "Distributed Runtime"),
    ("operator-continuity", "Operator Continuity"),
    ("operator-home", "Operator Home"),
    ("screen-awareness", "Screen Awareness"),
    ("service-graph", "Service Graph"),
    ("state-authority", "State Authority"),
    ("umh-nodes", "UMH Nodes"),
    ("workspace-topology", "Workspace Topology"),
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
    """Get Clerk auth state path."""
    return os.path.join(AUTH_STATE_DIR, f"{browser_type}_state.json")


def audit_panels(
    url: str,
    screenshot_dir: str = "",
    panels: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Run panel audit with Playwright.

    Returns structured evidence dict.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"error": "playwright not installed", "panel_audit": {}}

    if panels is None:
        panels = PANELS

    if not screenshot_dir:
        screenshot_dir = os.path.join(
            os.environ.get("UMH_ROOT", "C:\\dev\\dev\\OS"),
            "data", "certification", "c28", "screenshots",
        )
    os.makedirs(screenshot_dir, exist_ok=True)

    results: dict[str, Any] = {}

    with sync_playwright() as pw:
        auth_state = _get_auth_state()
        has_auth = os.path.exists(auth_state)

        browser = pw.chromium.launch(headless=False)

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
        time.sleep(3)

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
                nav_item = page.locator(f'[data-panel="{panel_id}"], a[href*="{panel_id}"]')
                if nav_item.count() > 0:
                    nav_item.first.click()
                    time.sleep(2)
                    evidence.navigated = True
                else:
                    js_nav = f"""
                        const store = window.__cockpitStore || window.__zustand_stores?.cockpit;
                        if (store) {{
                            store.getState().setActivePanel('{panel_id}');
                            true;
                        }} else {{
                            false;
                        }}
                    """
                    try:
                        navigated = page.evaluate(js_nav)
                        evidence.navigated = bool(navigated)
                        if evidence.navigated:
                            time.sleep(2)
                    except Exception:
                        evidence.navigated = False
                        evidence.notes = "Panel not reachable via nav or store"

                if evidence.navigated:
                    main_content = page.locator('main, [role="main"], .panel-content, [class*="panel"]')
                    evidence.rendered = main_content.count() > 0

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
            print(f"  {panel_label}: navigated={evidence.navigated} "
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
        panels = [(pid, pid) for pid in panel_ids]

    result = audit_panels(
        url=args.url,
        screenshot_dir=args.screenshot_dir,
        panels=panels,
    )

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        audit = result.get("panel_audit", {})
        for pid, data in audit.items():
            status = "PASS" if data.get("rendered") and data.get("console_errors", 0) == 0 else "FAIL"
            print(f"[{status}] {data.get('panel_label', pid)}: "
                  f"nav={data.get('navigated')} render={data.get('rendered')} "
                  f"errors={data.get('console_errors', 0)}")


if __name__ == "__main__":
    main()
