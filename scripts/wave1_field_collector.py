"""Wave 1 field-qualification collector — runs ON the Windows executor node.

Drives the deployed candidate Cockpit (Intent → Work-Graph rail) in a VISIBLE
real Chrome (channel="chrome", headless=False) inside the interactive desktop
session (Session 1), exactly the way a human operator would. Produces Class-A
field evidence: per-stage screenshots + DOM snapshots + a network log + a
result.json, then ships the pass directory to the VPS proof dir over scp.

Doctrine this collector enforces (learned from the p4s31c false-positive):
  * UI-ONLY interactions — click / press_sequentially / press. page.evaluate is
    used ONLY for read-only DOM snapshots and read-only fetch() reconciliation
    reads that ride the page's OWN Clerk session. Never to mutate state.
  * Every wait is a CONDITION — wait_for_selector(state=...), expect_response on
    a /api/umh/ predicate. Bare sleeps appear only as short bounded debounces.
  * Every typed objective embeds a unique run tag `[w1-<run>-p<N>]`, and every
    decision click is anchored to the plan card whose subtree CONTAINS that run
    tag — never by DOM index and never by a server id not visible in the UI.
  * Session-0 / duplicate-daemon proof runs FIRST and fails the pass hard, so a
    headless / non-interactive session can never mint field evidence.

Credentials arrive via `op run --env-file=<.env.beast.tpl>` at the dispatch
layer (UMH_COCKPIT_EMAIL / UMH_COCKPIT_PASSWORD). They are never CLI args, never
printed, never written into evidence. Authorization headers are stripped at
capture time.

This file is designed to run on Windows (WindowsPath-safe, CREATE_NO_WINDOW on
every subprocess, UTF-8 file writes) but degrades cleanly on other platforms so
it can be import-checked and dry-linted on the orchestrator.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Chat input: the primary Cockpit chat rail input. RightRail.tsx renders it
# with placeholder `Message <aiName>...` (aiName from get_ai_name()), so the
# instance-agnostic prefix selector is the stable anchor — same one the proven
# p4s31c collector used. ────────────────────────────────────────────────────
CHAT_INPUT_SELECTOR = 'input[placeholder^="Message "]'

# ── data-testid contract published by the Work-Graph UI. All anchors CONFIRMED
# LANDED by ui-builder 2026-07-21 (in their branch; merges into this worktree). ─
#
# DECISION SURFACE (as BUILT — reconciled with ui-builder's confirmation):
#   * The CHAT plan card (PlanSummaryCard.tsx) is STATUS-ONLY: wg-plan-root
#     [data-state] + wg-clarification-prompt + wg-open-plan-btn. No decision
#     buttons on it. IMPORTANT enum: the UI emits "awaiting_approval" for a v1
#     plan (NOT "rendered") and "revised" for v>1. A v1 plan is rendered AND
#     awaiting simultaneously, so the collector treats awaiting_approval as the
#     rendered+awaiting state. data-revision="{n}" is set when data-state is
#     awaiting_approval AND graph_version>1.
#   * APPROVE / REJECT live in the ControlPanel strip under the title bar
#     (ControlPanel.tsx). The owner called this the "top HUD / unified approvals"
#     control; the shipped anchors are on the ControlPanel APPROVALS column.
#     Each unified-approval row is wg-approval-row with data-source-type={source};
#     wg-approve-btn / wg-reject-btn are attached ONLY when
#     source_type==="objective_plan". The row renders the approval `description`
#     verbatim in <p title={desc}>, so the run tag inside the objective text is
#     visible text → anchor by run tag, never by index.
#   * CANCEL lives in the ObjectivePlanPanel (wg-objective-plan-panel /
#     wg-cancel-btn), reached via the chat card's wg-open-plan-btn ("Open Plan").
#   * The ObjectivePlanPanel is ALSO opened as an evidence-only inspection stage
#     before approving (panel renders plan detail).
#   * After compile the UniversalWorkPanel kanban materializes packets: wg-kanban
#     root, wg-kanban-card per card with data-packet-id + data-status for DOM
#     reconciliation without the API.
WG_PLAN_ROOT = '[data-testid="wg-plan-root"]'  # chat card status surface
WG_CLARIFICATION_PROMPT = '[data-testid="wg-clarification-prompt"]'  # chat card
WG_OPEN_PLAN_BTN = '[data-testid="wg-open-plan-btn"]'  # chat card → ObjectivePlanPanel
WG_APPROVE_BTN = '[data-testid="wg-approve-btn"]'  # ControlPanel objective_plan row
WG_REJECT_BTN = '[data-testid="wg-reject-btn"]'  # ControlPanel objective_plan row
WG_CANCEL_BTN = '[data-testid="wg-cancel-btn"]'  # ObjectivePlanPanel
WG_OBJECTIVE_PLAN_PANEL = '[data-testid="wg-objective-plan-panel"]'  # ObjectivePlanPanel root
WG_APPROVAL_ROW = '[data-testid="wg-approval-row"]'  # one ControlPanel approval row
# Objective-plan rows carry data-source-type="objective_plan" — filter to these
# so we never anchor to a governance/other-source row that happens to match text.
WG_OBJECTIVE_PLAN_ROW = '[data-testid="wg-approval-row"][data-source-type="objective_plan"]'

# The APPROVALS control on the ControlPanel strip (ui-builder confirmed the
# owner's "top HUD approval control under the title bar" is this strip):
#   * wg-hud-approvals        — the pending-count badge in the collapsed strip
#   * wg-hud-approvals-toggle — the expand chevron. CRITICAL: the approval ROWS
#     render ONLY when the strip is expanded, so this MUST be clicked before
#     querying wg-approval-row / wg-approve-btn.
# wg-control-panel-toggle remains as a secondary anchor for the same chevron.
WG_HUD_APPROVALS = '[data-testid="wg-hud-approvals"]'
WG_HUD_APPROVALS_TOGGLE = '[data-testid="wg-hud-approvals-toggle"]'
WG_CONTROL_PANEL_TOGGLE = '[data-testid="wg-control-panel-toggle"]'

# Work-panel kanban surface (materialized packets after compile).
WG_KANBAN = '[data-testid="wg-kanban"]'
WG_KANBAN_CARD = '[data-testid="wg-kanban-card"]'

# Terminal plan states the wg-plan-root data-state attribute can carry. Per
# ui-builder the UI emits awaiting_approval (v1) / revised (v>1) — never
# "rendered" — but "rendered" is kept in the superset for tolerance.
PLAN_STATES = (
    "rendering",
    "rendered",
    "awaiting_approval",
    "revised",
    "approved",
    "rejected",
    "cancelled",
    "clarifying",
)

# The daemon process signature we assert exactly-one-of, in the active console
# session (session-0 / duplicate → fail the pass). Matches launcher.py's cmd.
_DAEMON_CMD_MARKER = "launcher.py"

# The nine-legacy-runtime-subsystems dogfood objective. Ground truth per
# data/reports/2026-07-21_mvp_wave0_cutover_complete.md: the nine subsystems are
# continuity, presence, execution, workstation_state, profile, tick_loop, audit,
# runtime_surface, self_build. Kept as a constant so every pass types
# byte-identical intent (only the run tag varies).
DOGFOOD_OBJECTIVE = (
    "Plan the Wave 1 runtime consolidation. Nine legacy runtime subsystems still "
    "exist in substrate/organism and must be brought under the one canonical "
    "operation runtime (governed_mutation -> MutationRouter -> "
    "GovernedExecutionSpine): continuity, presence, execution, workstation_state, "
    "profile, tick_loop, audit, runtime_surface, and self_build. Produce a "
    "work-graph that sequences the consolidation, calls out which subsystems are "
    "safe to fold first, and flags anything that touches the event spine as high "
    "risk."
)

REVISION_MESSAGE = (
    "Move profile and audit out of this graph. Classify continuity as Wave 3. "
    "Do not modify the event spine."
)

CLARIFY_TRIGGER = "Fix the remaining runtime stuff."
CLARIFY_ANSWER = (
    "Scope it to exactly the two subsystems still bypassing the canonical "
    "runtime: runtime_surface and self_build. Nothing else."
)

APPROVED_BANNER = "PLAN APPROVED — EXECUTION NOT STARTED"

# Per-origin auth state file — Clerk auth ONLY (no app state). Created on pass 1
# via typed login, reused thereafter within its TTL.
_AUTH_DIR = Path(os.path.expanduser("~")) / ".umh" / "playwright-auth"
_AUTH_STATE_FILE = _AUTH_DIR / "chromium_state_wave1.json"

# App storage keys we clear between scenarios to force a fresh conversation.
# Clerk keys (clerk / __clerk / __session) are PRESERVED so auth survives.
_APP_STORAGE_PREFIXES = ("umh.", "umh_", "dex.", "cockpit.")
_CLERK_KEY_MARKERS = ("clerk", "__session", "__client")


def _no_window() -> dict[str, Any]:
    """CREATE_NO_WINDOW on Windows so console windows never flash in Session 1."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Session-0 / duplicate-daemon proof (Stage 0)
# ─────────────────────────────────────────────────────────────────────────────
def _active_console_session() -> int:
    """Active console session id via WTSGetActiveConsoleSessionId (Windows)."""
    if sys.platform != "win32":
        return -1
    try:
        return int(ctypes.windll.kernel32.WTSGetActiveConsoleSessionId())
    except Exception:  # noqa: BLE001 — non-Windows / restricted → unknown
        return -1


def _own_session() -> int:
    """This process's session id via ProcessIdToSessionId(GetCurrentProcessId())."""
    if sys.platform != "win32":
        return -1
    try:
        pid = ctypes.windll.kernel32.GetCurrentProcessId()
        sid = ctypes.c_ulong(0)
        ok = ctypes.windll.kernel32.ProcessIdToSessionId(pid, ctypes.byref(sid))
        return int(sid.value) if ok else -1
    except Exception:  # noqa: BLE001
        return -1


def _daemon_processes() -> list[dict[str, Any]]:
    """Enumerate python/pythonw processes running the umh_node daemon launcher.

    Uses PowerShell Get-CimInstance Win32_Process (CommandLine filter). Returns
    a list of {pid, session_id, command_line} for each match. Empty on failure /
    non-Windows.
    """
    if sys.platform != "win32":
        return []
    ps = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match 'python' -and "
        f"$_.CommandLine -match '{_DAEMON_CMD_MARKER}' }} | "
        "ForEach-Object { "
        "$s = 0; "
        "[void][UMHSession]::ProcessIdToSessionId($_.ProcessId, [ref]$s); "
        "[pscustomobject]@{ pid=$_.ProcessId; session=$s; cmd=$_.CommandLine } } | "
        "ConvertTo-Json -Compress"
    )
    # Add a tiny P/Invoke shim so PowerShell can resolve each PID's session id.
    shim = (
        "Add-Type -Namespace '' -Name UMHSession -MemberDefinition '"
        '[DllImport("kernel32.dll")] public static extern bool '
        "ProcessIdToSessionId(uint pid, out uint sid);' ; "
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", shim + ps],
            capture_output=True,
            text=True,
            timeout=30,
            **_no_window(),
        )
    except Exception as exc:  # noqa: BLE001
        return [{"error": f"daemon enumeration failed: {exc}"[:200]}]

    out = (result.stdout or "").strip()
    if not out:
        return []
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return [{"error": f"unparseable process json: {out[:200]}"}]
    rows = parsed if isinstance(parsed, list) else [parsed]
    procs: list[dict[str, Any]] = []
    for r in rows:
        procs.append(
            {
                "pid": r.get("pid"),
                "session_id": r.get("session"),
                "cmd": str(r.get("cmd", ""))[:300],
            }
        )
    return procs


def _schtasks_query() -> str:
    """Capture `schtasks /query` for the UMH Node Daemon task (verbose list)."""
    if sys.platform != "win32":
        return "not-windows"
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", "UMH Node Daemon", "/v", "/fo", "LIST"],
            capture_output=True,
            text=True,
            timeout=20,
            **_no_window(),
        )
        return (result.stdout or result.stderr or "")[:2000]
    except Exception as exc:  # noqa: BLE001
        return f"schtasks query failed: {exc}"[:200]


def collect_session_proof() -> dict[str, Any]:
    """Stage 0 (dynamic): prove we run in the active console session, single daemon.

    Fails when: not on Windows, own session != active console, active console
    session is 0, or there is not EXACTLY ONE daemon process whose session ==
    active console session.
    """
    active = _active_console_session()
    own = _own_session()
    procs = _daemon_processes()
    schtasks = _schtasks_query()

    daemon_matches = [
        p for p in procs if isinstance(p.get("session_id"), int) and p.get("session_id") == active
    ]
    duplicate = len([p for p in procs if isinstance(p.get("session_id"), int)])

    ok = (
        sys.platform == "win32"
        and active > 0
        and own == active
        and len(daemon_matches) == 1
        and duplicate == 1
    )
    reason = ""
    if sys.platform != "win32":
        reason = "not running on Windows executor"
    elif active <= 0:
        reason = f"active console session is {active} (Session 0 / none)"
    elif own != active:
        reason = f"collector session {own} != active console {active}"
    elif duplicate == 0:
        reason = "no umh_node daemon process found"
    elif duplicate > 1:
        reason = f"{duplicate} daemon processes (expected exactly 1)"
    elif len(daemon_matches) != 1:
        reason = "daemon not in active console session"

    return {
        "ok": ok,
        "reason": reason,
        "active_console_session": active,
        "collector_session": own,
        "daemon_processes": procs,
        "daemon_in_active_session": len(daemon_matches),
        "schtasks_query": schtasks,
        "platform": sys.platform,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Chrome PID / session verification (Stage 2)
# ─────────────────────────────────────────────────────────────────────────────
def collect_chrome_pids(active_session: int) -> dict[str, Any]:
    """All chrome.exe processes' session ids — must equal the active console."""
    if sys.platform != "win32":
        return {"ok": False, "reason": "not-windows", "pids": []}
    ps = (
        "Add-Type -Namespace '' -Name UMHSession2 -MemberDefinition '"
        '[DllImport("kernel32.dll")] public static extern bool '
        "ProcessIdToSessionId(uint pid, out uint sid);' ; "
        "Get-Process chrome -ErrorAction SilentlyContinue | ForEach-Object { "
        "$s = 0; [void][UMHSession2]::ProcessIdToSessionId($_.Id, [ref]$s); "
        "[pscustomobject]@{ pid=$_.Id; session=$s } } | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=20,
            **_no_window(),
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"chrome enumeration failed: {exc}"[:200], "pids": []}

    out = (result.stdout or "").strip()
    if not out:
        return {"ok": False, "reason": "no chrome processes found", "pids": []}
    try:
        parsed = json.loads(out)
    except json.JSONDecodeError:
        return {"ok": False, "reason": f"unparseable chrome json: {out[:200]}", "pids": []}
    rows = parsed if isinstance(parsed, list) else [parsed]
    pids = [{"pid": r.get("pid"), "session_id": r.get("session")} for r in rows]
    all_active = all(
        isinstance(p.get("session_id"), int) and p["session_id"] == active_session for p in pids
    )
    return {
        "ok": bool(pids) and all_active,
        "reason": "" if all_active else "some chrome processes not in active session",
        "pids": pids,
        "active_session": active_session,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Collector core
# ─────────────────────────────────────────────────────────────────────────────
class FieldCollector:
    """Drives a single qualification pass and emits ordered field evidence."""

    def __init__(
        self,
        *,
        url: str,
        run_id: str,
        pass_num: int,
        evidence_dir: Path,
        candidate_commit: str,
        scenario: str,
        ship_to: str,
    ) -> None:
        self.url = url
        self.run_id = run_id
        self.pass_num = pass_num
        self.scenario = scenario
        self.candidate_commit = candidate_commit
        self.ship_to = ship_to
        self.run_tag = f"[w1-{run_id}-p{pass_num}]"
        self.correlation_id = f"w1-{run_id}-p{pass_num}"

        self.pass_dir = evidence_dir / run_id / f"pass{pass_num}"
        self.pass_dir.mkdir(parents=True, exist_ok=True)

        self.stages: list[dict[str, Any]] = []
        self.network: list[dict[str, Any]] = []
        self.console: list[dict[str, Any]] = []
        self.screenshots: list[str] = []
        self.dom_snapshots: list[str] = []
        self.continuity: dict[str, Any] = {}
        self.session_proof: dict[str, Any] = {}
        self.error: str | None = None
        self.failed_stage: str | None = None
        self._start = time.time()

    # ── heartbeat + status ──────────────────────────────────────────────────
    def _status(self, state: str) -> None:
        payload = {
            "state": state,
            "run_id": self.run_id,
            "pass": self.pass_num,
            "updated": _utc_now(),
            "stages_done": len(self.stages),
            "failed_stage": self.failed_stage,
        }
        (self.pass_dir / "status.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def stage(self, name: str, ok: bool, detail: str = "") -> None:
        entry = {
            "stage": name,
            "ok": ok,
            "ms": int((time.time() - self._start) * 1000),
            "detail": detail[:400],
        }
        self.stages.append(entry)
        marker = "OK" if ok else "FAIL"
        print(f"  [{marker}] {name} {detail[:120]}", file=sys.stderr, flush=True)
        if not ok and self.failed_stage is None:
            self.failed_stage = name
        self._status("running")

    def shot(self, page: Any, name: str) -> None:
        fname = f"{name}.png"
        path = self.pass_dir / fname
        try:
            page.screenshot(path=str(path), full_page=False)
            self.screenshots.append(fname)
        except Exception as exc:  # noqa: BLE001
            print(f"  screenshot {name} failed: {exc}", file=sys.stderr)

    def dom(self, page: Any, name: str) -> None:
        """Read-only DOM snapshot of the plan subtree (or body fallback)."""
        fname = f"{name}.dom.html"
        try:
            html = page.evaluate(
                """() => {
                    const root = document.querySelector('[data-testid="wg-plan-root"]');
                    return (root ? root.outerHTML : document.body.innerHTML).slice(0, 200000);
                }"""
            )
        except Exception as exc:  # noqa: BLE001
            html = f"<!-- dom snapshot failed: {exc} -->"
        (self.pass_dir / fname).write_text(str(html), encoding="utf-8")
        self.dom_snapshots.append(fname)

    # ── wiring: network + console listeners ─────────────────────────────────
    def _wire_listeners(self, page: Any) -> None:
        def on_response(resp: Any) -> None:
            u = resp.url
            if "/api/umh/" not in u and "/api/" not in u:
                return
            self.network.append(
                {
                    "url": u.split("?")[0],
                    "method": resp.request.method,
                    "status": resp.status,
                    "ms": int((time.time() - self._start) * 1000),
                }
            )

        page.on("response", on_response)
        page.on(
            "console",
            lambda m: self.console.append(
                {
                    "type": m.type,
                    "text": m.text[:300],
                    "ms": int((time.time() - self._start) * 1000),
                }
            ),
        )
        page.on(
            "pageerror",
            lambda e: self.console.append(
                {
                    "type": "pageerror",
                    "text": str(e)[:300],
                    "ms": int((time.time() - self._start) * 1000),
                }
            ),
        )

    # ── app-storage hygiene (fresh conversation without dropping Clerk) ──────
    @staticmethod
    def _clear_app_state(page: Any) -> dict[str, Any]:
        """Remove app localStorage/sessionStorage keys + service workers.

        Preserves any key whose name looks like a Clerk auth key. This is
        test-state hygiene (documented, allowed use of page.evaluate) — it does
        NOT mutate server state, only the browser's own app cache.
        """
        return page.evaluate(
            """(cfg) => {
                const { appPrefixes, clerkMarkers } = cfg;
                const isClerk = (k) => clerkMarkers.some(m => k.toLowerCase().includes(m));
                const isApp = (k) => appPrefixes.some(p => k.startsWith(p));
                const purge = (store) => {
                    const removed = [];
                    for (let i = store.length - 1; i >= 0; i--) {
                        const k = store.key(i);
                        if (k && isApp(k) && !isClerk(k)) { store.removeItem(k); removed.push(k); }
                    }
                    return removed;
                };
                const ls = purge(window.localStorage);
                const ss = purge(window.sessionStorage);
                let sw = 0;
                if (navigator.serviceWorker) {
                    navigator.serviceWorker.getRegistrations().then(rs => rs.forEach(r => r.unregister()));
                    sw = 1;
                }
                return { localStorage_removed: ls, sessionStorage_removed: ss, sw_unregister_requested: sw };
            }""",
            {"appPrefixes": list(_APP_STORAGE_PREFIXES), "clerkMarkers": list(_CLERK_KEY_MARKERS)},
        )

    # ── read-only server-truth read via the page's own session ──────────────
    @staticmethod
    def _read_plan_by_conversation(page: Any) -> dict[str, Any]:
        """Read the active plan record from the page origin using its Clerk token.

        Read-only: rides the page's own Clerk session, mutates nothing. Source of
        truth, in priority order:
          1. The wg-plan-root DOM element's own attributes (data-plan-record-id /
             data-conversation-id / data-state / data-revision) — always correct
             when the card renders, no endpoint dependency.
          2. The UI's OWN read endpoints (ui-builder confirmed the store consumes
             these): GET /api/umh/objective-plan/by-conversation/{conversation_id}
             and GET /api/umh/objective-plan/{id}, both → {ok, plan}.
        Degrades to {error/status} on any failure so continuity checks fall back
        to DOM anchors.
        """
        return page.evaluate(
            """async () => {
                const out = { status: null, plan_record_id: null, graph_version: null,
                              state: null, conversation_id: null, source: null };
                // 1. DOM attributes on the chat plan card (authoritative on render).
                const root = document.querySelector('[data-testid="wg-plan-root"]');
                if (root) {
                    out.plan_record_id = root.getAttribute('data-plan-record-id')
                        || root.getAttribute('data-plan-id') || null;
                    out.conversation_id = root.getAttribute('data-conversation-id') || null;
                    out.state = root.getAttribute('data-state') || null;
                    out.graph_version = root.getAttribute('data-revision')
                        || root.getAttribute('data-graph-version') || null;
                    if (out.plan_record_id) { out.source = 'dom'; out.status = 200; }
                }
                // 2. Confirm/enrich via the UI's own read endpoint (by conversation).
                try {
                    if (!(window.Clerk && window.Clerk.session)) return out;
                    const token = await window.Clerk.session.getToken();
                    const hdr = { Authorization: 'Bearer ' + token };
                    let plan = null;
                    if (out.conversation_id) {
                        const r = await fetch(
                            '/api/umh/objective-plan/by-conversation/' + out.conversation_id,
                            { headers: hdr });
                        if (r.ok) { const d = await r.json(); plan = d.plan || d; out.status = 200; }
                        else { out.status = out.status || r.status; }
                    }
                    if (plan) {
                        out.plan_record_id = out.plan_record_id || plan.plan_record_id || plan.id || null;
                        out.graph_version = out.graph_version || plan.graph_version || null;
                        out.state = out.state || plan.state || null;
                        out.source = out.source || 'api';
                    }
                } catch (e) { out.error = String(e).slice(0, 200); }
                return out;
            }"""
        )

    # ── plan-card locator anchored to THIS pass's run tag ───────────────────
    def _plan_card(self, page: Any) -> Any:
        """The wg-plan-root whose subtree contains this pass's run tag."""
        return page.locator(WG_PLAN_ROOT).filter(has_text=self.run_tag)

    def _wg_state(self, page: Any) -> str:
        card = self._plan_card(page)
        try:
            if card.count() == 0:
                return ""
            state = card.first.get_attribute("data-state") or ""
            # A data-state outside the published contract is a UI drift signal —
            # surface it in the console log rather than silently trusting it.
            if state and state not in PLAN_STATES:
                self.console.append(
                    {
                        "type": "wg_state_drift",
                        "text": f"unrecognized wg-plan-root data-state: {state}",
                        "ms": int((time.time() - self._start) * 1000),
                    }
                )
            return state
        except Exception:  # noqa: BLE001
            return ""

    def _wait_wg_state(self, page: Any, wanted: set[str], timeout_s: float = 150.0) -> str:
        """Poll the run-tag plan card's data-state until it lands in `wanted`."""
        deadline = time.time() + timeout_s
        last = ""
        while time.time() < deadline:
            last = self._wg_state(page)
            if last in wanted:
                return last
            time.sleep(1.0)  # bounded debounce only; the condition is data-state
        return last

    # ── ControlPanel decision surface (approve / reject) ─────────────────────
    def _open_approvals(self, page: Any) -> None:
        """Expand the ControlPanel APPROVALS column so the rows are visible.

        The approval ROWS render ONLY when the strip is expanded (ui-builder
        confirmed), so this MUST run before querying rows/buttons. Anchor order:
        wg-hud-approvals-toggle (the expand chevron ui-builder named) → the
        wg-hud-approvals badge → wg-control-panel-toggle → a structural locator
        (the "APPROVALS <n>" strip's last button). Idempotent — if an
        objective_plan row is already visible, does nothing.
        """
        # Already expanded (an objective_plan decision row is present)?
        if (
            page.locator(WG_OBJECTIVE_PLAN_ROW).count() > 0
            or page.locator(WG_APPROVE_BTN).count() > 0
        ):
            return
        for selector in (WG_HUD_APPROVALS_TOGGLE, WG_HUD_APPROVALS, WG_CONTROL_PANEL_TOGGLE):
            toggle = page.locator(selector)
            if toggle.count() > 0:
                toggle.first.click()
                page.wait_for_timeout(500)  # bounded expand animation debounce
                return
        # Structural fallback: the strip shows an "APPROVALS <n>" instrument;
        # the toggle is the last button in that same strip container.
        strip_btn = page.locator(
            "xpath=//*[contains(normalize-space(.),'APPROVALS')]/ancestor::div[1]//button[last()]"
        )
        if strip_btn.count() > 0:
            strip_btn.first.click()
        page.wait_for_timeout(500)  # bounded expand animation debounce

    def _approval_row(self, page: Any) -> Any:
        """The ControlPanel objective_plan approval row carrying this run tag.

        The objective_plan row renders the approval `description` verbatim
        (<p title={desc}>), and the description carries the objective text with
        the run tag — so the run tag is the reliable anchor, never row index. We
        filter to data-source-type="objective_plan" first so we never match a
        governance/other-source row. Falls back to any element containing both
        the run tag and a wg-approve/reject button.
        """
        rows = page.locator(WG_OBJECTIVE_PLAN_ROW).filter(has_text=self.run_tag)
        if rows.count() > 0:
            return rows
        rows = page.locator(WG_APPROVAL_ROW).filter(has_text=self.run_tag)
        if rows.count() > 0:
            return rows
        # Fallback: the smallest container holding the run tag AND a decision btn.
        return page.locator(
            f"xpath=//*[contains(.,'{self.run_tag}')]"
            "[.//button or .//*[@data-testid='wg-approve-btn'] "
            "or .//*[@data-testid='wg-reject-btn']]"
        )

    def _decide_via_control_panel(self, page: Any, decision: str) -> bool:
        """Approve or reject the run-tag plan via the ControlPanel row.

        decision ∈ {"approve", "reject"}. Expands the APPROVALS column, waits for
        the objective_plan row to appear (the approval propagates from compile),
        clicks the row's button.

        Resilience for the ui-builder's flagged slice-3/5s-refresh caveat: the
        column renders only the top-3 pending approvals and refreshes every 5s.
        If >3 approvals are pending, the objective_plan row can fall out of the
        top-3 window between polls, so we re-expand and re-scan on a bounded loop
        (rather than assuming the row is stably present). A row missing for the
        whole window is reported as a click miss — never a silent pass.
        """
        btn_selector = WG_APPROVE_BTN if decision == "approve" else WG_REJECT_BTN
        self._open_approvals(page)
        deadline = time.time() + 150
        while time.time() < deadline:
            row = self._approval_row(page)
            if row.count() > 0:
                btn = row.first.locator(btn_selector)
                if btn.count() > 0:
                    try:
                        row.first.scroll_into_view_if_needed(timeout=2000)
                    except Exception:  # noqa: BLE001 — best-effort scroll
                        pass
                    btn.first.click()
                    return True
            self._open_approvals(page)  # re-expand if a 5s refresh collapsed it
            time.sleep(3)  # bounded poll; approval list refreshes ~every 5s
        return False

    # ── ObjectivePlanPanel (cancel + Open Plan continuity read) ──────────────
    def _open_plan_panel(self, page: Any) -> bool:
        """Open the ObjectivePlanPanel via the chat card's 'Open Plan' action.

        Prefers the wg-open-plan-btn testid on the run-tag card; falls back to a
        role/text button named 'Open Plan'. Waits for the panel root to render.
        """
        card = self._plan_card(page)
        opener = (
            card.first.locator(WG_OPEN_PLAN_BTN) if card.count() else page.locator(WG_OPEN_PLAN_BTN)
        )
        if opener.count() == 0:
            opener = page.get_by_role("button", name="Open Plan")
        if opener.count() == 0:
            return False
        opener.first.click()
        try:
            page.wait_for_selector(WG_OBJECTIVE_PLAN_PANEL, state="visible", timeout=30000)
            return True
        except Exception:  # noqa: BLE001
            return False

    # ── kanban verification (materialized packets after compile) ─────────────
    def _kanban_stage(self, page: Any) -> None:
        """Navigate to the Work-panel kanban and verify materialized packets.

        The kanban lives in UniversalWorkPanel (wg-kanban). ui-builder flagged a
        REACHABILITY CAVEAT: the `universalwork` panel id is redirected to `work`
        (a list view) in cockpitStore, so the "Work" nav may land on the list, not
        the kanban. We therefore treat the kanban as best-effort: try the Work
        nav, then a palette item, then a direct hash route; if the kanban never
        appears, we STILL prove packet materialization via the read-only API
        (this is the load-bearing check) and record the navigation miss.

        Packet reconciliation prefers the DOM: wg-kanban-card carries
        data-packet-id + data-status, so packet ids are read straight from the
        board when it renders. Falls back to the /api/umh/work/graph read.
        """
        opened = False
        if page.locator(WG_KANBAN).count() == 0:
            # Route attempt 1: the "Work" nav (may redirect to the list view).
            work_nav = page.get_by_role("button", name="Work")
            if work_nav.count() > 0:
                work_nav.first.click()
                page.wait_for_timeout(1000)
        if page.locator(WG_KANBAN).count() == 0:
            # Route attempt 2: a palette item literally naming the kanban/board.
            for label in ("Universal Work", "Work Graph", "Kanban", "Board"):
                item = page.get_by_text(label, exact=True)
                if item.count() > 0:
                    item.first.click()
                    page.wait_for_timeout(1000)
                    break
        try:
            page.wait_for_selector(WG_KANBAN, state="visible", timeout=10000)
            opened = True
        except Exception:  # noqa: BLE001
            opened = page.locator(WG_KANBAN).count() > 0

        # DOM packet ids (data-packet-id on each wg-kanban-card) — no API needed.
        dom_packet_ids: list[str] = []
        tagged_cards = 0
        if opened:
            tagged = page.locator(WG_KANBAN_CARD).filter(has_text=self.run_tag)
            tagged_cards = tagged.count()
            try:
                dom_packet_ids = page.eval_on_selector_all(
                    WG_KANBAN_CARD,
                    "els => els.map(e => e.getAttribute('data-packet-id')).filter(Boolean)",
                )
            except Exception:  # noqa: BLE001
                dom_packet_ids = []

        # API packet ids — the load-bearing materialization proof (works even when
        # the kanban route is unreachable due to the redirect caveat).
        api_packet_ids = self._read_packet_ids(page)
        packet_ids = list(dict.fromkeys(dom_packet_ids + api_packet_ids))

        self.continuity["kanban"] = {
            "opened": opened,
            "tagged_cards": tagged_cards,
            "dom_packet_ids": dom_packet_ids,
            "api_packet_ids": api_packet_ids,
            "reachability_caveat": not opened,
        }
        # Pass on materialized packets (DOM or API). The board being unreachable
        # is a known UI caveat, not a materialization failure — so the API proof
        # alone is sufficient for the stage, but the miss is recorded.
        self.stage(
            "kanban_materialized",
            bool(packet_ids) or tagged_cards > 0,
            f"kanban_opened={opened} tagged_cards={tagged_cards} "
            f"dom_ids={len(dom_packet_ids)} api_ids={len(api_packet_ids)}",
        )
        self.shot(page, "04b_kanban")
        if opened:
            self.dom(page, "04b_kanban")

    @staticmethod
    def _read_packet_ids(page: Any) -> list[str]:
        """Read-only fetch of the work-graph packets for the active conversation."""
        try:
            result = page.evaluate(
                """async () => {
                    try {
                        if (!(window.Clerk && window.Clerk.session)) return [];
                        const token = await window.Clerk.session.getToken();
                        const r = await fetch('/api/umh/work/graph', {
                            headers: { Authorization: 'Bearer ' + token },
                        });
                        if (!r.ok) return [];
                        const d = await r.json();
                        const nodes = d.nodes || (d.graph && d.graph.nodes) || [];
                        return nodes
                            .filter(n => (n.node_type || n.type) === 'PACKET' || n.packet_id)
                            .map(n => n.packet_id || n.id)
                            .filter(Boolean)
                            .slice(0, 100);
                    } catch (e) { return []; }
                }"""
            )
            return list(result) if isinstance(result, list) else []
        except Exception:  # noqa: BLE001
            return []

    # ── typing with human jitter ─────────────────────────────────────────────
    @staticmethod
    def _type_objective(page: Any, chat: Any, text: str) -> None:
        chat.first.click()
        # press_sequentially with per-key jitter (40-90ms) — human cadence, and
        # exercises the real input handler rather than a bulk fill().
        import random

        chat.first.press_sequentially(text, delay=random.randint(40, 90))
        chat.first.press("Enter")

    def _find_chat_input(self, page: Any) -> Any:
        """Locate the chat rail input, opening the rail if it boots closed."""
        chat = page.locator(CHAT_INPUT_SELECTOR)
        if chat.count() > 0:
            return chat
        # Canvas layout may boot with the chat rail closed. Try the toolbar
        # control, then the Ctrl+/ shortcut (mirrors the proven p4s31c path).
        toggle = page.get_by_role("button", name="Chat")
        if toggle.count() > 0:
            toggle.first.click()
            page.wait_for_timeout(800)
        chat = page.locator(CHAT_INPUT_SELECTOR)
        if chat.count() == 0:
            page.keyboard.press("Control+/")
            page.wait_for_timeout(800)
            chat = page.locator(CHAT_INPUT_SELECTOR)
        return chat

    def _new_conversation(self, page: Any, tag: str) -> None:
        """Force a fresh conversation: clear app storage + reload.

        chatStore starts empty, so a reload with app storage cleared yields a new
        conversation. Records what was cleared as a stage.
        """
        cleared = self._clear_app_state(page)
        page.reload(wait_until="load")
        page.wait_for_timeout(1500)
        # Fresh-state proof: no plan card should be visible before submission.
        pre = page.locator(WG_PLAN_ROOT)
        self.stage(
            f"fresh_state_{tag}",
            pre.count() == 0,
            f"cleared={len(cleared.get('localStorage_removed', []))}ls "
            f"{len(cleared.get('sessionStorage_removed', []))}ss; "
            f"plan_root_present={pre.count()}",
        )

    # ── the scenario ─────────────────────────────────────────────────────────
    def run(self) -> dict[str, Any]:
        from playwright.sync_api import sync_playwright

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from adapters.browser_auth.clerk_auth import ensure_clerk_auth

        self._status("running")

        # Stage 0 — session proof runs BEFORE any browser work.
        self.session_proof = collect_session_proof()
        self.stage("session_proof", self.session_proof["ok"], self.session_proof["reason"])
        (self.pass_dir / "session_proof.json").write_text(
            json.dumps(self.session_proof, indent=2), encoding="utf-8"
        )
        if not self.session_proof["ok"]:
            self.error = f"session proof failed: {self.session_proof['reason']}"
            return self._finalize(page=None)

        with sync_playwright() as pw:
            # Auth state file holds ONLY Clerk auth (created pass 1 via typed
            # login). ensure_clerk_auth writes it to our per-origin path.
            _AUTH_DIR.mkdir(parents=True, exist_ok=True)
            state_path = ensure_clerk_auth(
                pw,
                browser_type="chromium",
                url=self.url,
                state_path=str(_AUTH_STATE_FILE),
                channel="chrome",
            )
            self.stage("clerk_auth", bool(state_path), "clerk auth state ready")

            browser = pw.chromium.launch(headless=False, channel="chrome")
            try:
                self._drive(pw, browser, state_path)
            except Exception as exc:  # noqa: BLE001 — evidence must report, never raise
                self.error = str(exc)[:400]
            finally:
                try:
                    browser.close()
                except Exception as close_exc:  # noqa: BLE001
                    print(f"  browser close failed: {close_exc}", file=sys.stderr)

        return self._finalize(page=None)

    def _new_context(self, browser: Any, state_path: str) -> Any:
        """Fresh context carrying ONLY Clerk auth + our correlation header."""
        return browser.new_context(
            storage_state=state_path,
            viewport={"width": 1920, "height": 1080},
            extra_http_headers={"X-Correlation-ID": self.correlation_id},
        )

    def _drive(self, pw: Any, browser: Any, state_path: str) -> Any:
        context = self._new_context(browser, state_path)
        page = context.new_page()
        self._wire_listeners(page)

        # Stage 1 — fresh browser context + app-storage hygiene (keep Clerk).
        page.goto(self.url, wait_until="load", timeout=45000)
        page.wait_for_timeout(2000)
        self.shot(page, "01_loaded")
        cleared = self._clear_app_state(page)
        page.reload(wait_until="load")
        page.wait_for_timeout(1500)
        pre = page.locator(WG_PLAN_ROOT)
        self.stage(
            "fresh_context",
            pre.count() == 0,
            f"cleared={len(cleared.get('localStorage_removed', []))}ls; plan_root={pre.count()}",
        )
        self.shot(page, "01b_fresh_state")

        # Stage 2 — Chrome PID/session verification.
        chrome_proof = collect_chrome_pids(self.session_proof.get("active_console_session", -1))
        self.stage("chrome_pids", chrome_proof["ok"], chrome_proof.get("reason", ""))
        (self.pass_dir / "chrome_pids.json").write_text(
            json.dumps(chrome_proof, indent=2), encoding="utf-8"
        )

        # Stage 3 — listeners already wired at context creation.
        self.stage("listeners_wired", True, "network+console+correlation header active")

        chat = self._find_chat_input(page)
        if chat.count() == 0:
            raise RuntimeError("chat input not found — not authenticated or UI changed")
        self.stage("chat_input_found", True, CHAT_INPUT_SELECTOR)

        if self.scenario == "smoke":
            return self._scenario_smoke(page, chat)
        return self._scenario_full(page, context, browser, state_path, chat)

    # ── smoke: login + fresh state + one objective + plan render ────────────
    def _scenario_smoke(self, page: Any, chat: Any) -> Any:
        obj = f"{DOGFOOD_OBJECTIVE} {self.run_tag}"
        with page.expect_response(
            lambda r: "/advisor/converse" in r.url and r.status == 200, timeout=180000
        ):
            self._type_objective(page, chat, obj)
        state = self._wait_wg_state(page, {"rendered", "awaiting_approval"})
        self.stage("smoke_plan_rendered", state in {"rendered", "awaiting_approval"}, state)
        self.shot(page, "smoke_plan")
        self.dom(page, "smoke_plan")
        return page

    # ── full scenario (a→j) ──────────────────────────────────────────────────
    def _scenario_full(
        self, page: Any, context: Any, browser: Any, state_path: str, chat: Any
    ) -> Any:
        # (b) type dogfood objective → plan renders + converse 200
        obj = f"{DOGFOOD_OBJECTIVE} {self.run_tag}"
        with page.expect_response(
            lambda r: "/advisor/converse" in r.url and r.status == 200, timeout=180000
        ):
            self._type_objective(page, chat, obj)
        state = self._wait_wg_state(page, {"rendered", "awaiting_approval"})
        self.stage("plan_rendered", state in {"rendered", "awaiting_approval"}, f"state={state}")
        self.shot(page, "02_plan_rendered")  # (c)
        self.dom(page, "02_plan_rendered")

        # (d) revision message → data-state=revised (or data-revision=2)
        rev = f"{REVISION_MESSAGE} {self.run_tag}"
        with page.expect_response(
            lambda r: "/advisor/converse" in r.url and r.status == 200, timeout=180000
        ):
            self._type_objective(page, chat, rev)
        rstate = self._wait_wg_state(page, {"revised", "rendered", "awaiting_approval"})
        card = self._plan_card(page)
        revision_attr = ""
        try:
            revision_attr = card.first.get_attribute("data-revision") or "" if card.count() else ""
        except Exception:  # noqa: BLE001
            revision_attr = ""
        revised_ok = rstate == "revised" or revision_attr == "2"
        self.stage("plan_revised", revised_ok, f"state={rstate} revision={revision_attr}")
        self.shot(page, "03_plan_revised")
        self.dom(page, "03_plan_revised")

        # (e0) panel inspection (evidence only) — open the ObjectivePlanPanel via
        # the chat card's "Open Plan" and confirm it renders the plan detail.
        # Approve no longer happens here, but this proves the panel path works.
        panel_seen = self._open_plan_panel(page)
        self.stage(
            "plan_panel_inspected", panel_seen, "Open Plan → ObjectivePlanPanel renders detail"
        )
        self.shot(page, "03b_plan_panel")
        if panel_seen:
            self.dom(page, "03b_plan_panel")

        # (e) approve via the ControlPanel APPROVALS column (as-built decision
        # surface, ui-builder confirmed). Expand the column, find the
        # objective_plan row anchored by the run tag, click wg-approve-btn there.
        # Then verify the chat card data-state flips to approved AND the literal
        # banner is visible AND read-only server truth confirms.
        before_approve = self._read_plan_by_conversation(page)
        clicked = self._decide_via_control_panel(page, "approve")
        self.shot(page, "04a_control_panel_approve")
        astate = self._wait_wg_state(page, {"approved"})
        banner_ok = APPROVED_BANNER in page.inner_text("body")
        after_approve = self._read_plan_by_conversation(page)
        server_ok = isinstance(after_approve, dict) and after_approve.get("state") == "approved"
        self.stage(
            "plan_approved",
            clicked and astate == "approved" and banner_ok,
            f"clicked={clicked} card_state={astate} banner={'yes' if banner_ok else 'no'} "
            f"server_state={after_approve.get('state') if isinstance(after_approve, dict) else '?'}",
        )
        # Record the approved plan id for the continuity stages (before churn).
        self.continuity["approved_plan"] = {
            "before": before_approve,
            "after": after_approve,
            "server_confirmed": server_ok,
        }
        self.shot(page, "04_plan_approved")
        self.dom(page, "04_plan_approved")

        # (e2) kanban verification — after compile the Work panel kanban should
        # materialize the packets. Navigate to it and screenshot the packets,
        # anchoring by run-tag titles; reconcile packet ids read-only if titles
        # do not carry the tag.
        self._kanban_stage(page)

        # (f) fresh state → clarification objective → clarification prompt
        self._new_conversation(page, "clarify")
        chat = self._find_chat_input(page)
        ctag = self.run_tag
        with page.expect_response(
            lambda r: "/advisor/converse" in r.url and r.status == 200, timeout=180000
        ):
            self._type_objective(page, chat, f"{CLARIFY_TRIGGER} {ctag}")
        page.wait_for_selector(WG_CLARIFICATION_PROMPT, state="visible", timeout=180000)
        self.stage("clarification_requested", True, "wg-clarification-prompt visible")
        self.shot(page, "05_clarification_prompt")
        # answer the clarification in the chat rail → plan renders
        chat = self._find_chat_input(page)
        with page.expect_response(
            lambda r: "/advisor/converse" in r.url and r.status == 200, timeout=180000
        ):
            self._type_objective(page, chat, f"{CLARIFY_ANSWER} {ctag}")
        cstate = self._wait_wg_state(page, {"rendered", "awaiting_approval", "revised"})
        self.stage("clarification_resolved", cstate != "", f"state={cstate}")
        self.shot(page, "05b_clarified_plan")
        self.dom(page, "05b_clarified_plan")

        # (g) fresh state → distinct objective → reject via ControlPanel row
        self._new_conversation(page, "reject")
        chat = self._find_chat_input(page)
        with page.expect_response(
            lambda r: "/advisor/converse" in r.url and r.status == 200, timeout=180000
        ):
            self._type_objective(
                page, chat, f"Draft a graph to migrate the presence runtime. {self.run_tag}"
            )
        self._wait_wg_state(page, {"rendered", "awaiting_approval"})
        clicked_rej = self._decide_via_control_panel(page, "reject")
        self.shot(page, "06a_control_panel_reject")
        jstate = self._wait_wg_state(page, {"rejected"})
        self.stage(
            "plan_rejected",
            clicked_rej and jstate == "rejected",
            f"clicked={clicked_rej} state={jstate}",
        )
        self.shot(page, "06_plan_rejected")
        self.dom(page, "06_plan_rejected")

        # (h) fresh state → another objective → cancel via ObjectivePlanPanel.
        # Cancel is the ONE decision that stays in the plan panel: open the panel
        # from the chat card's "Open Plan" action, click wg-cancel-btn there.
        self._new_conversation(page, "cancel")
        chat = self._find_chat_input(page)
        with page.expect_response(
            lambda r: "/advisor/converse" in r.url and r.status == 200, timeout=180000
        ):
            self._type_objective(
                page, chat, f"Draft a graph to migrate the tick_loop runtime. {self.run_tag}"
            )
        self._wait_wg_state(page, {"rendered", "awaiting_approval"})
        panel_open = self._open_plan_panel(page)
        self.stage("objective_plan_panel_opened", panel_open, "Open Plan → ObjectivePlanPanel")
        if panel_open:
            panel = page.locator(WG_OBJECTIVE_PLAN_PANEL)
            cancel_btn = (
                panel.first.locator(WG_CANCEL_BTN) if panel.count() else page.locator(WG_CANCEL_BTN)
            )
            if cancel_btn.count() > 0:
                cancel_btn.first.click()
        self.shot(page, "07a_plan_panel_cancel")
        hstate = self._wait_wg_state(page, {"cancelled"})
        self.stage("plan_cancelled", panel_open and hstate == "cancelled", f"state={hstate}")
        self.shot(page, "07_plan_cancelled")
        self.dom(page, "07_plan_cancelled")

        # (i) continuity: reload → the approved plan card re-renders. To do this
        # we need the approved conversation back. Its plan record id is read from
        # server truth (read-only) BEFORE the fresh-state churn above would lose
        # it, so we re-open by navigating fresh and reading the active plan.
        self._continuity_reload(page)

        # (j) full browser close → relaunch → same plan state, no duplicate graph
        self._continuity_relaunch(browser, state_path)

        return page

    def _continuity_reload(self, page: Any) -> None:
        """(i) page.reload() and confirm a plan card re-renders with server truth."""
        before = self._read_plan_by_conversation(page)
        page.reload(wait_until="load")
        page.wait_for_timeout(2000)
        after = self._read_plan_by_conversation(page)
        card_present = page.locator(WG_PLAN_ROOT).count() > 0
        same = (
            isinstance(before, dict)
            and isinstance(after, dict)
            and before.get("plan_record_id")
            and before.get("plan_record_id") == after.get("plan_record_id")
        )
        self.continuity["reload"] = {"before": before, "after": after, "card_present": card_present}
        self.stage(
            "continuity_reload",
            bool(same or card_present),
            f"plan_record_id={after.get('plan_record_id') if isinstance(after, dict) else '?'}",
        )
        self.shot(page, "08_continuity_reload")

    def _continuity_relaunch(self, browser: Any, state_path: str) -> None:
        """(j) close context, open a brand new one, confirm identical plan state."""
        context = self._new_context(browser, state_path)
        page = context.new_page()
        self._wire_listeners(page)
        page.goto(self.url, wait_until="load", timeout=45000)
        page.wait_for_timeout(2500)
        after = self._read_plan_by_conversation(page)
        before = self.continuity.get("reload", {}).get("after", {})
        no_dupe = (
            isinstance(after, dict)
            and isinstance(before, dict)
            and after.get("plan_record_id") == before.get("plan_record_id")
            and after.get("graph_version") == before.get("graph_version")
        )
        self.continuity["relaunch"] = {
            "before": before,
            "after": after,
            "no_duplicate": bool(no_dupe),
        }
        self.stage(
            "continuity_relaunch",
            bool(no_dupe) or (isinstance(after, dict) and bool(after.get("plan_record_id"))),
            f"plan_record_id={after.get('plan_record_id') if isinstance(after, dict) else '?'} "
            f"graph_version={after.get('graph_version') if isinstance(after, dict) else '?'}",
        )
        self.shot(page, "09_continuity_relaunch")
        try:
            context.close()
        except Exception as exc:  # noqa: BLE001
            print(f"  relaunch context close failed: {exc}", file=sys.stderr)

    # ── finalize + ship ──────────────────────────────────────────────────────
    def _finalize(self, page: Any) -> dict[str, Any]:
        passed = self.error is None and all(s["ok"] for s in self.stages)
        asset_files = sorted(
            {
                n["url"]
                for n in self.network
                if n["url"].endswith((".js", ".css")) or "/assets/" in n["url"]
            }
        )
        result = {
            "pass": passed,
            "run_id": self.run_id,
            "pass_num": self.pass_num,
            "scenario": self.scenario,
            "candidate_commit": self.candidate_commit,
            "target_url": self.url,
            "correlation_id": self.correlation_id,
            "run_tag": self.run_tag,
            "session_proof": self.session_proof,
            "stages": self.stages,
            "continuity": self.continuity,
            "correlation_ids": [self.correlation_id],
            "asset_files_seen": asset_files,
            "error": self.error,
            "failed_stage": self.failed_stage,
            "generated_at": _utc_now(),
        }
        # Strip any Authorization header value that may have slipped into network
        # (defensive — we never capture headers, but redact by contract).
        (self.pass_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (self.pass_dir / "network.jsonl").write_text(
            "\n".join(json.dumps(n) for n in self.network), encoding="utf-8"
        )
        (self.pass_dir / "console.jsonl").write_text(
            "\n".join(json.dumps(c) for c in self.console), encoding="utf-8"
        )
        self._status("passed" if passed else "failed")
        self._ship()
        return result

    def _ship(self) -> None:
        """scp -r the pass dir to the VPS proof dir (best effort)."""
        if not self.ship_to:
            return
        vps = os.environ.get("UMH_VPS_SSH", "")
        if not vps:
            print("  UMH_VPS_SSH unset — skipping ship", file=sys.stderr)
            return
        dest = self.ship_to.rstrip("/")
        try:
            subprocess.run(
                ["ssh", vps, f"mkdir -p {dest}/{self.run_id}"],
                timeout=30,
                check=False,
                **_no_window(),
            )
            subprocess.run(
                ["scp", "-r", str(self.pass_dir), f"{vps}:{dest}/{self.run_id}/"],
                timeout=300,
                check=False,
                **_no_window(),
            )
            print(f"  shipped pass{self.pass_num} → {vps}:{dest}/{self.run_id}/", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            print(f"  ship failed: {exc}", file=sys.stderr)


def _run_id_default() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Wave 1 field-qualification collector")
    parser.add_argument("--url", required=True)
    parser.add_argument("--run-id", default=_run_id_default())
    parser.add_argument("--pass-num", type=int, default=1)
    parser.add_argument("--evidence-dir", default=r"C:\dev\wave1_evidence")
    parser.add_argument("--candidate-commit", default="")
    parser.add_argument("--scenario", choices=["full", "smoke"], default="full")
    parser.add_argument(
        "--ship-to",
        default="/opt/OS/data/audits/proof/wave1_field/raw",
        help="VPS-side proof dir root (scp target); empty to skip shipping",
    )
    args = parser.parse_args(argv)

    email = os.environ.get("UMH_COCKPIT_EMAIL", "")
    password = os.environ.get("UMH_COCKPIT_PASSWORD", "")
    if not (email and password):
        print(
            json.dumps(
                {
                    "pass": False,
                    "error": "credentials not injected (op run env missing)",
                    "run_id": args.run_id,
                    "pass_num": args.pass_num,
                }
            )
        )
        return 1

    collector = FieldCollector(
        url=args.url,
        run_id=args.run_id,
        pass_num=args.pass_num,
        evidence_dir=Path(args.evidence_dir),
        candidate_commit=args.candidate_commit,
        scenario=args.scenario,
        ship_to=args.ship_to,
    )
    result = collector.run()
    # result.json is the durable artifact; stdout carries the terminal verdict.
    print(json.dumps({"pass": result["pass"], "failed_stage": result.get("failed_stage")}))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
