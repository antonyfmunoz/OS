"""P4S-31C — deployed Cockpit Chat intent-loop browser proof.

Runs ON an executor node (real Chrome, interactive desktop session) via the
governed mesh dispatch path — never on the orchestrator (Browser Verification
Law). Clerk credentials arrive via `op run` env injection
(UMH_COCKPIT_EMAIL / UMH_COCKPIT_PASSWORD) — never CLI args, never printed,
never included in evidence output.

The flow drives ONLY the canonical intent rail (Cockpit Chat doctrine):

  Clerk login (adapters.browser_auth.clerk_auth)
    -> type intent into the Cockpit Chat input -> Enter
    -> in-thread reply "Intent captured — loop `<id>` is HELD ..."
    -> click the suggested action "Open Intent Loop" (panel = downstream
       control surface, opened FROM the thread — never a parallel intent form)
    -> click Approve for that loop (governed decision)
    -> panel shows proof_recorded; thread carries the proof-status turn

Evidence: per-stage screenshots + network log of /advisor/converse and
/intent-loop responses + extracted loop/proof ids, emitted as JSON on stdout.
Screenshots are copied to the orchestrator proof dir when UMH_VPS_SSH is set.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Any

CHAT_INPUT_SELECTOR = 'input[placeholder^="Message "]'
INTENT_CAPTURED_RE = re.compile(r"loop_[0-9a-f]{12}")
PROOF_DIR_NAME = "p4s31c_browser_proof"


def _proof_dir() -> str:
    base = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "proof", PROOF_DIR_NAME
    )
    os.makedirs(base, exist_ok=True)
    return base


def run_proof(url: str, email: str, password: str) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from adapters.browser_auth.clerk_auth import ensure_clerk_auth

    evidence: dict[str, Any] = {
        "flow": "cockpit_chat_intent_rail",
        "target_url": url,
        "stages": [],
        "network": [],
        "screenshots": [],
        "loop_id": None,
        "proof_confirmed": False,
        "error": None,
    }
    shots = _proof_dir()

    def stage(name: str, ok: bool, detail: str = "") -> None:
        evidence["stages"].append({"stage": name, "ok": ok, "detail": detail[:300]})
        print(f"  [{'OK' if ok else 'FAIL'}] {name} {detail[:120]}", file=sys.stderr)

    def shot(page: Any, name: str) -> None:
        path = os.path.join(shots, f"{name}.png")
        page.screenshot(path=path, full_page=False)
        evidence["screenshots"].append(path)

    with sync_playwright() as pw:
        state_path = ensure_clerk_auth(pw, browser_type="chromium", url=url, channel="chrome")
        stage("clerk_auth", bool(state_path), "auth state ready")

        browser = pw.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}, storage_state=state_path
        )
        page = context.new_page()

        live_reply: dict[str, Any] = {}

        def on_response(resp: Any) -> None:
            u = resp.url
            if "/api/" in u:
                evidence["network"].append(
                    {"url": u.split("?")[0], "status": resp.status, "method": resp.request.method}
                )
                # The loop id comes from OUR OWN converse response — immune to
                # history turns rendering asynchronously in the thread.
                if (
                    "/advisor/converse" in u
                    and resp.request.method == "POST"
                    and resp.status == 200
                ):
                    try:
                        body = resp.json()
                        m = INTENT_CAPTURED_RE.search(str(body.get("text", "")))
                        if m and body.get("intent") == "intent_loop_submit":
                            live_reply["loop_id"] = m.group(0)
                    except Exception:  # noqa: BLE001 — non-JSON responses are fine
                        pass

        page.on("response", on_response)
        console_errors: list[str] = []
        page.on(
            "console",
            lambda msg: console_errors.append(msg.text[:200]) if msg.type == "error" else None,
        )
        page.on("pageerror", lambda exc: console_errors.append(f"pageerror: {exc}"[:200]))
        evidence["console_errors"] = console_errors

        try:
            page.goto(url, wait_until="load", timeout=45000)
            time.sleep(6)
            shot(page, "01_cockpit_loaded")

            chat = page.locator(CHAT_INPUT_SELECTOR)
            if chat.count() == 0:
                # Canvas layout boots with the chat rail closed. The toolbar
                # "Chat" control is a dropdown (Chat / Context / Execution) —
                # open it, then click the "Chat" menu item. Ctrl+/ as fallback.
                toggle = page.get_by_role("button", name="Chat")
                if toggle.count() > 0:
                    toggle.first.click()
                    time.sleep(1)
                    menu_item = page.get_by_text("Chat", exact=True)
                    if menu_item.count() > 1:
                        menu_item.last.click()
                    elif menu_item.count() == 1:
                        menu_item.first.click()
                else:
                    page.keyboard.press("Control+/")
                time.sleep(3)
                shot(page, "01b_chat_rail_opened")
                chat = page.locator(CHAT_INPUT_SELECTOR)
                if chat.count() == 0:
                    page.keyboard.press("Control+/")
                    time.sleep(3)
                    shot(page, "01c_chat_shortcut")
                    chat = page.locator(CHAT_INPUT_SELECTOR)
            if chat.count() == 0:
                raise RuntimeError("Cockpit chat input not found — not authenticated or UI changed")
            stage("chat_input_found", True)

            # Unique per-run text: panel cards render raw_text (not loop_id),
            # so this is the ONLY reliable row anchor for the Approve click.
            run_tag = f"run-{int(time.time())}"
            intent_text = f"Fix this stale probe path {run_tag}"
            chat.first.click()
            chat.first.fill(intent_text)
            chat.first.press("Enter")
            stage("chat_submit", True, intent_text)

            # The loop id is taken from OUR converse response via the network
            # listener — the DOM also renders history turns with other ids.
            deadline = time.time() + 120  # converse degrades with runtime age
            while time.time() < deadline and "loop_id" not in live_reply:
                time.sleep(3)
            shot(page, "02_intent_captured_held")
            loop_id = live_reply.get("loop_id")
            if not loop_id:
                raise RuntimeError("No intent_loop_submit converse response within 120s")
            evidence["loop_id"] = loop_id
            body_text = page.inner_text("body")
            held = loop_id in body_text and (
                "HELD" in body_text or "awaiting_approval" in body_text
            )
            stage("gate_held_in_thread", held, loop_id)

            # Panel = downstream control surface, opened FROM the thread's
            # suggested action. In canvas layout panels open as canvas windows
            # via the palette, so follow the button with the palette path.
            open_btn = page.get_by_role("button", name="Open Intent Loop")
            if open_btn.count() > 0:
                open_btn.first.click()
                stage("panel_opened_from_thread", True, "suggested action clicked")
                time.sleep(2)
            # Panel cards render raw_text, NOT loop_id — the unique run_tag in
            # the message is the only reliable row anchor.
            row_card = page.locator("div.bg-surface-raised").filter(has_text=run_tag)
            if row_card.count() == 0:
                palette_toggle = page.locator('button[title="Show palette"]')
                if palette_toggle.count() > 0:
                    palette_toggle.first.click()
                    time.sleep(2)
                # Panel routes live under the palette's Instruments submenu.
                instruments = page.get_by_text("Instruments", exact=True)
                if instruments.count() > 0:
                    instruments.first.click()
                    time.sleep(1)
                palette_item = page.get_by_text("Intent Loop", exact=True)
                if palette_item.count() > 0:
                    palette_item.first.click()
                    stage("panel_window_added_from_palette", True)
                    time.sleep(3)
            # Wait PASSIVELY for our row (clicking Refresh abandons the
            # in-flight request); the panel polls every 5-15s.
            row_deadline = time.time() + 150
            while time.time() < row_deadline:
                if page.locator("div.bg-surface-raised").filter(has_text=run_tag).count() > 0:
                    break
                time.sleep(5)
            shot(page, "03_intent_loop_panel")

            # In-page probe: does the route work from THIS origin+session? This
            # distinguishes a route/auth failure from a client-plumbing hang.
            try:
                probe = page.evaluate(
                    """async () => {
                        const hasClerk = !!(window.Clerk && window.Clerk.session);
                        let token = null, tokenMs = -1;
                        if (hasClerk) {
                            const t0 = performance.now();
                            try { token = await Promise.race([
                                window.Clerk.session.getToken(),
                                new Promise((_, rej) => setTimeout(() => rej(new Error('token timeout 10s')), 10000)),
                            ]); } catch (e) { token = 'ERR:' + e.message; }
                            tokenMs = Math.round(performance.now() - t0);
                        }
                        let status = null, fetchMs = -1;
                        if (token && !String(token).startsWith('ERR:')) {
                            const t1 = performance.now();
                            try {
                                const r = await fetch('/api/umh/intent-loop', { headers: { Authorization: 'Bearer ' + token } });
                                status = r.status;
                            } catch (e) { status = 'ERR:' + e.message; }
                            fetchMs = Math.round(performance.now() - t1);
                        }
                        return { hasClerk, tokenState: String(token).startsWith('ERR:') ? String(token) : (token ? 'ok' : 'null'), tokenMs, status, fetchMs };
                    }"""
                )
                evidence["inpage_probe"] = probe
            except Exception as probe_exc:  # noqa: BLE001
                evidence["inpage_probe"] = f"probe failed: {probe_exc}"[:200]

            # Diagnostics: what the panel window actually shows.
            panel_hdr = page.get_by_text("Cockpit Chat intent rail")
            if panel_hdr.count() > 0:
                try:
                    evidence["panel_text"] = panel_hdr.first.locator(
                        "xpath=ancestor::div[contains(@class,'flex-col')][1]"
                    ).inner_text()[:600]
                except Exception as diag_exc:  # noqa: BLE001
                    evidence["panel_text"] = f"unavailable: {diag_exc}"

            # Approve THIS run's row card — anchored on the unique run_tag.
            row_card = page.locator("div.bg-surface-raised").filter(has_text=run_tag)
            if row_card.count() == 0:
                raise RuntimeError(f"Row card for {run_tag} ({loop_id}) not found in panel")
            row_approve = row_card.first.get_by_role("button", name="Approve")
            if row_approve.count() == 0:
                raise RuntimeError(f"Approve control missing in {run_tag} row card")
            row_approve.first.click()
            stage("governed_approve_clicked", True, f"{run_tag} -> {loop_id}")

            # NO fake completion: confirm via SERVER TRUTH fetched from the
            # browser origin — OUR loop must reach proof_recorded.
            proof_fields: dict[str, Any] = {}
            confirm_deadline = time.time() + 90
            while time.time() < confirm_deadline:
                try:
                    state = page.evaluate(
                        """async (loopId) => {
                            const token = await window.Clerk.session.getToken();
                            const r = await fetch('/api/umh/intent-loop', { headers: { Authorization: 'Bearer ' + token } });
                            const d = await r.json();
                            const l = (d.loops || []).find(x => x.loop_id === loopId);
                            return l ? { stage: l.stage, proof: l.proof } : null;
                        }""",
                        loop_id,
                    )
                    if state and state.get("stage") == "proof_recorded":
                        proof_fields = state.get("proof") or {}
                        break
                except Exception as poll_exc:  # noqa: BLE001
                    print(f"  server-truth poll retry: {poll_exc}", file=sys.stderr)
                time.sleep(6)
            evidence["proof"] = proof_fields
            proof_ok = (
                bool(proof_fields.get("proof_id")) and proof_fields.get("decision") == "approve"
            )
            stage(
                "proof_recorded_server_truth",
                proof_ok,
                f"proof_id={proof_fields.get('proof_id')} envelope={proof_fields.get('envelope_id')} decided_by={proof_fields.get('decided_by')}",
            )
            time.sleep(4)
            shot(page, "04_proof_recorded")

            page_text = page.inner_text("body")
            row_badge = page.locator("div.bg-surface-raised").filter(has_text=run_tag)
            badge_ok = row_badge.count() > 0 and "proof_recorded" in (row_badge.first.inner_text())
            stage("proof_badge_on_own_row", badge_ok)
            thread_status = loop_id in page_text
            stage("status_visible_in_cockpit", thread_status, "loop id present in thread/panel")

            evidence["proof_confirmed"] = proof_ok and thread_status
        except Exception as exc:  # noqa: BLE001 — evidence must report, never raise
            evidence["error"] = str(exc)[:300]
            try:
                shot(page, "99_failure_state")
            except Exception as shot_exc:  # noqa: BLE001
                print(f"  failure screenshot unavailable: {shot_exc}", file=sys.stderr)
        finally:
            browser.close()

    _ship_screenshots(evidence)
    return evidence


def _ship_screenshots(evidence: dict[str, Any]) -> None:
    """Copy screenshots to the orchestrator proof dir (best effort)."""
    vps = os.environ.get("UMH_VPS_SSH", "")
    if not vps or not evidence["screenshots"]:
        return
    dest = "/opt/OS/data/audits/proof/2026-07-06_p4s31c_browser/"
    try:
        subprocess.run(["ssh", vps, f"mkdir -p {dest}"], timeout=30, check=False)
        for path in evidence["screenshots"]:
            subprocess.run(["scp", path, f"{vps}:{dest}"], timeout=60, check=False)
        evidence["screenshots_shipped_to"] = dest
    except Exception as exc:  # noqa: BLE001
        evidence["screenshots_shipped_to"] = f"ship failed: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="P4S-31C Cockpit Chat intent-loop browser proof")
    parser.add_argument("--url", default="https://universalmetaharness.tech")
    args = parser.parse_args()

    email = os.environ.get("UMH_COCKPIT_EMAIL", "")
    password = os.environ.get("UMH_COCKPIT_PASSWORD", "")
    if not (email and password):
        print(
            json.dumps(
                {"error": "credentials not injected (op run env missing)", "proof_confirmed": False}
            )
        )
        return 1

    evidence = run_proof(args.url, email, password)
    print(json.dumps(evidence))
    return 0 if evidence["proof_confirmed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
