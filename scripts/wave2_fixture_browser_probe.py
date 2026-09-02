"""Wave 2 fixture browser probe — runs ON the Windows executor node (Beast).

Independent, visible-Chrome witness that the deployed fixture app's note-search
actually works end to end in a REAL browser (Browser Verification Law): opens the
fixture origin in Session-1 visible Chrome, types "alpha" into the search box,
waits on the live ``/api/notes/search`` response, and asserts results render.
Writes a small signed evidence JSON (screenshot + DOM + network) — NO tokens,
NO PII.

This is the D-task browser check driven by the host runner via governed mesh
dispatch (the collector's own w23 witness is a second, independent visible-Chrome
observation from the operator's session). SSH dispatch is prohibited (Session 0
has no display); this file runs only in the interactive desktop session.

Contract asserted (from infra/fixture OBJECTIVE.md Task B/D):
  * search input  : data-testid="note-search-input"
  * results list  : data-testid="note-search-results"
  * search API    : GET /api/notes/search?q=alpha → 200, results non-empty

Session-0 / non-interactive → the probe fails hard, so headless/SSH can never
mint fixture evidence. Windows-targeted (CREATE_NO_WINDOW, UTF-8 writes) but
import-checks cleanly on other platforms.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_id_default() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _active_console_session() -> int:
    """Windows active console (interactive) session id; -1 off Windows."""
    if sys.platform != "win32":
        return -1
    try:
        return int(ctypes.windll.kernel32.WTSGetActiveConsoleSessionId())
    except Exception:  # noqa: BLE001
        return -1


def _own_session() -> int:
    if sys.platform != "win32":
        return -1
    try:
        pid = ctypes.windll.kernel32.GetCurrentProcessId()
        sid = ctypes.c_ulong()
        ctypes.windll.kernel32.ProcessIdToSessionId(pid, ctypes.byref(sid))
        return int(sid.value)
    except Exception:  # noqa: BLE001
        return -1


def collect_session_proof() -> dict[str, Any]:
    """Fail hard unless in the interactive console session (Session 1) on Windows."""
    active = _active_console_session()
    own = _own_session()
    reasons: list[str] = []
    if sys.platform != "win32":
        reasons.append(f"not win32 (platform={sys.platform})")
    if active <= 0:
        reasons.append(f"no active console session (WTSGetActiveConsoleSessionId={active})")
    if own != active:
        reasons.append(f"probe session {own} != active console session {active}")
    ok = not reasons
    return {
        "ok": ok,
        "reason": "interactive console session" if ok else "; ".join(reasons),
        "active_console_session": active,
        "own_session": own,
    }


def _chrome_pids_in_session(active_session: int) -> dict[str, Any]:
    """Prove the visible Chrome we drive is in the active console session."""
    if sys.platform != "win32":
        return {"ok": False, "reason": "not win32", "pids": []}
    ps = (
        "Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object { "
        "$sid=0; "
        "[void][PInvoke.Native]::ProcessIdToSessionId($_.Id,[ref]$sid); "
        "[pscustomobject]@{pid=$_.Id;session=$sid} } | ConvertTo-Json -Compress"
    )
    add_type = (
        "Add-Type -Namespace PInvoke -Name Native -MemberDefinition '"
        "[System.Runtime.InteropServices.DllImport(\"kernel32.dll\")]"
        "public static extern bool ProcessIdToSessionId(uint pid, ref uint sid);'"
    )
    try:
        import subprocess

        flags = 0x08000000  # CREATE_NO_WINDOW
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"{add_type}; {ps}"],
            capture_output=True, text=True, timeout=30, creationflags=flags,
        )
        raw = (out.stdout or "").strip()
        data = json.loads(raw) if raw else []
        if isinstance(data, dict):
            data = [data]
        in_session = [d for d in data if int(d.get("session", -1)) == active_session]
        return {"ok": bool(in_session), "pids": in_session,
                "reason": "chrome in active session" if in_session
                else "no chrome in active console session"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"chrome pid probe failed: {exc}", "pids": []}


class FixtureBrowserProbe:
    def __init__(self, *, url: str, run_id: str, evidence_dir: str, query: str = "alpha") -> None:
        self.url = url.rstrip("/")
        self.run_id = run_id
        self.query = query
        self.pass_dir = Path(evidence_dir) / run_id / "fixture_probe"
        self.pass_dir.mkdir(parents=True, exist_ok=True)
        self.network: list[dict[str, Any]] = []
        self.stages: list[dict[str, Any]] = []
        self.error = ""
        self._start = time.time()

    def _stage(self, name: str, ok: bool, detail: str = "") -> None:
        self.stages.append({"stage": name, "ok": ok, "detail": detail[:300],
                            "ms": int((time.time() - self._start) * 1000)})
        print(f"[{'OK' if ok else 'FAIL'}] {name} {detail}", file=sys.stderr, flush=True)

    def run(self) -> dict[str, Any]:
        session_proof = collect_session_proof()
        self._stage("session_proof", session_proof["ok"], session_proof["reason"])
        if not session_proof["ok"]:
            self.error = f"session proof failed: {session_proof['reason']}"
            return self._finalize(session_proof)

        chrome_proof: dict[str, Any] = {"ok": None, "reason": "not yet probed", "pids": []}
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # noqa: BLE001
            self.error = f"playwright import failed: {exc}"
            return self._finalize(session_proof, chrome_proof)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False, channel="chrome")
            try:
                context = browser.new_context(viewport={"width": 1440, "height": 900})
                page = context.new_page()
                page.on("response", self._on_response)
                page.goto(self.url, wait_until="load", timeout=45000)
                self._stage("fixture_loaded", True, self.url)

                # Prove the visible Chrome is in the interactive session.
                chrome_proof = _chrome_pids_in_session(session_proof["active_console_session"])
                self._stage("chrome_in_session", bool(chrome_proof.get("ok")),
                            chrome_proof.get("reason", ""))

                # The search box + results list must be present (Task B contract).
                search = page.locator('[data-testid="note-search-input"]')
                results = page.locator('[data-testid="note-search-results"]')
                self._stage("search_input_present", search.count() > 0,
                            'data-testid="note-search-input"')

                # Type the query and wait on the LIVE search API response.
                with page.expect_response(
                    lambda r: "/api/notes/search" in r.url and r.status == 200,
                    timeout=30000,
                ) as resp_info:
                    search.fill(self.query)
                    search.press("Enter")
                resp = resp_info.value
                body = {}
                try:
                    body = resp.json()
                except Exception:  # noqa: BLE001
                    body = {}
                api_ok = isinstance(body, dict) and bool(body.get("results"))
                self._stage("search_api_returns_results", api_ok,
                            f"results={len(body.get('results', []))} query={self.query!r}")

                # The rendered results list must be non-empty in the DOM.
                page.wait_for_timeout(600)
                rendered = 0
                if results.count() > 0:
                    rendered = results.locator("li, [data-testid='note-search-result']").count()
                self._stage("results_render_in_dom", rendered > 0, f"rendered_items={rendered}")

                self._shot(page, "fixture_search")
                self._dom(page, "fixture_search")
            except Exception as exc:  # noqa: BLE001 — evidence must report, never raise
                self.error = str(exc)[:400]
                try:
                    self._shot(page, "99_failure")  # type: ignore[has-type]
                except Exception:  # noqa: BLE001
                    pass
            finally:
                try:
                    browser.close()
                except Exception:  # noqa: BLE001
                    pass

        return self._finalize(session_proof, chrome_proof)

    def _on_response(self, resp: Any) -> None:
        try:
            url = resp.url.split("?")[0]
            if "/api/" in url:
                self.network.append({"url": url, "status": resp.status})
        except Exception:  # noqa: BLE001
            pass

    def _shot(self, page: Any, name: str) -> None:
        try:
            page.screenshot(path=str(self.pass_dir / f"{name}.png"), full_page=False)
        except Exception:  # noqa: BLE001
            pass

    def _dom(self, page: Any, name: str) -> None:
        try:
            html = page.evaluate("() => document.body ? document.body.outerHTML.slice(0,200000) : ''")
            (self.pass_dir / f"{name}.dom.html").write_text(html, encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    def _finalize(self, session_proof: dict[str, Any],
                  chrome_proof: dict[str, Any] | None = None) -> dict[str, Any]:
        passed = self.error == "" and all(s["ok"] for s in self.stages)
        result = {
            "pass": passed,
            "run_id": self.run_id,
            "target_url": self.url,
            "query": self.query,
            "session_proof": session_proof,
            "chrome_proof": chrome_proof or {},
            "stages": self.stages,
            "network": self.network,
            "error": self.error,
            "generated_at": _utc_now(),
        }
        (self.pass_dir / "fixture_probe_result.json").write_text(
            json.dumps(result, indent=2), encoding="utf-8"
        )
        (self.pass_dir / "status.json").write_text(
            json.dumps({"state": "passed" if passed else "failed",
                        "run_id": self.run_id, "updated": _utc_now()}, indent=2),
            encoding="utf-8",
        )
        return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Wave 2 fixture browser probe (executor, visible Chrome)")
    ap.add_argument("--url", required=True, help="fixture origin (e.g. https://<tailnet>:10000)")
    ap.add_argument("--run-id", default=_run_id_default())
    ap.add_argument("--evidence-dir", default=r"C:\dev\wave2_evidence")
    ap.add_argument("--query", default="alpha")
    args = ap.parse_args(argv)

    probe = FixtureBrowserProbe(
        url=args.url, run_id=args.run_id, evidence_dir=args.evidence_dir, query=args.query,
    )
    result = probe.run()
    print(json.dumps({"pass": result["pass"], "error": result["error"]}))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
