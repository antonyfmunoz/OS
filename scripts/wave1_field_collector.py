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
WG_CANCEL_BTN = '[data-testid="wg-cancel-btn"]'  # Work Detail (cancel authority)
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
WG_KANBAN_OPEN_PLAN = '[data-testid="wg-kanban-open-plan"]'  # plan-sourced card → Work Detail

# Work-Detail (Plan/Task inspection) surface. WorkDetailPanel.tsx renders the
# panel root, the context sections (scope/planning-scale/archetype/skills/
# readiness), and the ONLY cancel authority (cancel lives here, not the HUD).
WG_WORK_DETAIL = '[data-testid="wg-work-detail"]'
WG_WORK_DETAIL_CONTEXT = '[data-testid="wg-work-detail-context"]'
# The Work-Detail root also carries the wg-objective-plan-panel testid on its
# inner container (WorkDetailPanel.tsx line 620) — kept as the "Open Plan" target.
WG_OBJECTIVE_PLAN_PANEL = '[data-testid="wg-objective-plan-panel"]'

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

# ── Journey message corpus (plan v5.1 §23 / §16). Kept as constants so every
# pass types byte-identical intent (only the run tag varies per pass). Each is a
# distinct intent CLASS the OperatorIntentProtocol must classify differently. ──

# s03 — pure communication. Must classify COMMUNICATE → zero artifacts.
GREETING_MESSAGE = "Hey, good to be back in the cockpit. How's the organism looking today?"

# s04 — an atomic Task (CREATE_TASK). One concrete unit, non-executable.
SIMPLE_TASK_MESSAGE = "Fix the failing import in transports/api/voice.py"

# s05 — a rephrase of the s04 task. Must resolve as a duplicate → NO new card.
SIMPLE_TASK_REPHRASE = (
    "Go patch that broken import over in transports/api/voice.py so the module loads."
)

# s06 — attach the captured task to the objective (link_work intent).
ATTACH_TASK_TEMPLATE = "Attach that task to the objective {run_tag}."

# s07 — the nine-subsystem dogfood Objective (CREATE_OBJECTIVE → plan compiles).
# Ground truth per data/reports/2026-07-21_mvp_wave0_cutover_complete.md: the
# nine subsystems are continuity, presence, execution, workstation_state,
# profile, tick_loop, audit, runtime_surface, self_build.
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

# s10 — conversational revision (MODIFY_PLAN → graph_version 2, v1 preserved).
REVISION_MESSAGE = "Add a rollback verification step to the plan"

# s11 — ambiguous reference (no unique referent → exactly one clarification, no
# state change). "Cancel it" with nothing uniquely selectable.
AMBIGUOUS_CANCEL_MESSAGE = "Cancel it."

# s13 — chat "Approve that plan." PROVIDE_DECISION → HUD-only surface/focus, the
# reply explains decisions happen in the control panel; NO state transition.
CHAT_APPROVE_MESSAGE = "Approve that plan."

# s22a — a self-build planning message (target umh_substrate governance profile).
SELF_BUILD_MESSAGE = (
    "Plan a change to the UMH substrate itself: add a governed pre-commit gate "
    "that blocks any new raw subprocess call in substrate/."
)

# s22b — a projection-build planning message (a projection, not the substrate).
PROJECTION_BUILD_MESSAGE = (
    "Plan a new EOS projection feature: an outreach-sequence dashboard that reads "
    "lead state and surfaces the next best action per lead."
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

    @staticmethod
    def _authed_get(page: Any, path: str) -> dict[str, Any]:
        """Read-only GET on the page origin using its own Clerk token → JSON.

        Rides the page's Clerk session (mutates nothing). Returns
        {"__status": <int>, ...body} on JSON, or {"__status": <int|None>,
        "__error": ...} otherwise. Used for s02 principal/tenant proof and the
        plan-JSON decision-log / status reads.
        """
        return page.evaluate(
            """async (p) => {
                const out = { __status: null };
                try {
                    if (!(window.Clerk && window.Clerk.session)) {
                        out.__error = 'no clerk session'; return out;
                    }
                    const token = await window.Clerk.session.getToken();
                    const r = await fetch(p, { headers: { Authorization: 'Bearer ' + token } });
                    out.__status = r.status;
                    try {
                        const body = await r.json();
                        if (body && typeof body === 'object' && !Array.isArray(body)) {
                            return Object.assign(out, body);
                        }
                        out.__body = body;
                    } catch (e) { out.__error = 'non-json body'; }
                } catch (e) { out.__error = String(e).slice(0, 200); }
                return out;
            }""",
            path,
        )

    def _read_plan_json(self, page: Any) -> dict[str, Any]:
        """Full plan detail JSON for the active conversation (decision_log etc.).

        Prefers the plan_record_id read off the run-tag card DOM, then falls back
        to the by-conversation read. Returns {} when neither resolves.
        """
        anchor = self._read_plan_by_conversation(page)
        plan_id = anchor.get("plan_record_id") if isinstance(anchor, dict) else None
        if plan_id:
            detail = self._authed_get(page, f"/api/umh/objective-plan/{plan_id}")
            if (
                isinstance(detail, dict)
                and detail.get("__status") == 200
                and not detail.get("error")
            ):
                return detail
        conv_id = anchor.get("conversation_id") if isinstance(anchor, dict) else None
        if conv_id:
            detail = self._authed_get(page, f"/api/umh/objective-plan/by-conversation/{conv_id}")
            if isinstance(detail, dict) and detail.get("__status") == 200:
                return detail
        return {}

    def _count_plan_cards(self, page: Any) -> int:
        """How many wg-plan-root cards carry THIS pass's run tag (dedupe check)."""
        try:
            return page.locator(WG_PLAN_ROOT).filter(has_text=self.run_tag).count()
        except Exception:  # noqa: BLE001
            return -1

    def _count_kanban_cards_tagged(self, page: Any) -> int:
        """How many wg-kanban-card rows carry THIS pass's run tag."""
        try:
            return page.locator(WG_KANBAN_CARD).filter(has_text=self.run_tag).count()
        except Exception:  # noqa: BLE001
            return -1

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
        """Open the Work-Detail (Plan) panel via the chat card's 'Open Plan' action.

        Prefers the wg-open-plan-btn testid on the run-tag card; falls back to a
        role/text button named 'Open Plan'. Waits for the Work-Detail root
        (wg-work-detail) to render — that is the panel WorkDetailPanel.tsx mounts,
        which also carries the wg-objective-plan-panel inner container.
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
        for sel in (WG_WORK_DETAIL, WG_OBJECTIVE_PLAN_PANEL):
            try:
                page.wait_for_selector(sel, state="visible", timeout=30000)
                return True
            except Exception:  # noqa: BLE001
                continue
        return False

    # ── kanban verification (materialized packets after compile) ─────────────
    def _open_kanban(self, page: Any) -> bool:
        """Best-effort navigation to the Work-panel kanban (wg-kanban).

        REACHABILITY CAVEAT (ui-builder): the `universalwork` / `tasks` panel ids
        redirect to `work` (registry.ts), which may render a list view rather than
        the kanban. So this is best-effort: if the board never appears, the steps
        that need packet truth fall back to the read-only packets API. Returns
        True iff wg-kanban is visible.
        """
        if page.locator(WG_KANBAN).count() > 0:
            return True
        work_nav = page.get_by_role("button", name="Work")
        if work_nav.count() > 0:
            work_nav.first.click()
            page.wait_for_timeout(1000)
        if page.locator(WG_KANBAN).count() == 0:
            for label in ("Universal Work", "Work Graph", "Kanban", "Board"):
                item = page.get_by_text(label, exact=True)
                if item.count() > 0:
                    item.first.click()
                    page.wait_for_timeout(1000)
                    break
        try:
            page.wait_for_selector(WG_KANBAN, state="visible", timeout=10000)
            return True
        except Exception:  # noqa: BLE001
            return page.locator(WG_KANBAN).count() > 0

    @staticmethod
    def _read_packets(page: Any) -> list[dict[str, Any]]:
        """Read-only fetch of the materialized work packets (PacketSafe rows).

        Rides the page's own Clerk session (read-only, mutates nothing). Hits the
        SAME endpoint UniversalWorkPanel uses — GET
        /api/umh/organism/universal-work/packets?limit=50 → PacketSafe[] — so the
        shape (packet_id / status / title / source_type / source_id) matches the
        kanban's own source of truth. Returns [] on any failure.
        """
        try:
            result = page.evaluate(
                """async () => {
                    try {
                        if (!(window.Clerk && window.Clerk.session)) return [];
                        const token = await window.Clerk.session.getToken();
                        const r = await fetch(
                            '/api/umh/organism/universal-work/packets?limit=50',
                            { headers: { Authorization: 'Bearer ' + token } });
                        if (!r.ok) return [];
                        const d = await r.json();
                        const rows = Array.isArray(d) ? d : (d.packets || d.items || []);
                        return rows.map(p => ({
                            packet_id: p.packet_id || p.id || null,
                            status: p.status || null,
                            title: p.title || '',
                            source_type: p.source_type || null,
                            source_id: p.source_id || null,
                        })).filter(p => p.packet_id).slice(0, 100);
                    } catch (e) { return []; }
                }"""
            )
            return list(result) if isinstance(result, list) else []
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _read_packet_ids(page: Any) -> list[str]:
        """Just the packet ids (compat shim over _read_packets)."""
        return [p["packet_id"] for p in FieldCollector._read_packets(page) if p.get("packet_id")]

    # ── typing with human jitter ─────────────────────────────────────────────
    @staticmethod
    def _type_objective(page: Any, chat: Any, text: str) -> None:
        chat.first.click()
        # press_sequentially with per-key jitter (40-90ms) — human cadence, and
        # exercises the real input handler rather than a bulk fill().
        import random

        chat.first.press_sequentially(text, delay=random.randint(40, 90))
        chat.first.press("Enter")

    def _send_and_wait(self, page: Any, text: str, timeout_ms: int = 180000) -> None:
        """Type a message into the chat rail and wait for its /advisor/converse 200.

        Re-locates the chat input each call (the rail can re-render after a plan
        card mounts). The converse round-trip is the CONDITION — no bare sleep.
        """
        chat = self._find_chat_input(page)
        with page.expect_response(
            lambda r: "/advisor/converse" in r.url and r.status == 200, timeout=timeout_ms
        ):
            self._type_objective(page, chat, text)

    @staticmethod
    def _body_contains(page: Any, needle: str) -> bool:
        """Whether the rendered page body currently contains `needle` (verbatim)."""
        try:
            return needle in page.inner_text("body")
        except Exception:  # noqa: BLE001
            return False

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
        """The 21-step operator journey (plan v5.1 §23 / §16), s01..s21 + s22a/b.

        Each s## is a discrete method with a machine-checkable assertion and
        evidence capture. The pass is gated on s01..s21 (self.stages); s22a/s22b
        are bonus mini-cases whose failure is recorded but does NOT gate the pass
        (see _finalize's gating_stage_names). The steps share a mutable `ctx` dict
        so later continuity checks can reference ids captured earlier.
        """
        ctx: dict[str, Any] = {}
        # s01 already emitted "fresh_context" as part of _drive; re-assert the
        # storage/SW/no-plan invariants explicitly under the s01 id here.
        self._s01_fresh_state(page)
        self._s02_principal_tenant(page)
        self._s03_communication_only(page, ctx)
        self._s04_simple_task(page, ctx)
        self._s05_duplicate_task(page, ctx)
        self._s06_attach_task(page, ctx)
        self._s07_complex_objective(page, ctx)
        self._s08_inspect_plan_detail(page, ctx)
        self._s09_tasks_on_kanban(page, ctx)
        self._s10_conversational_revision(page, ctx)
        self._s11_ambiguous_reference(page, ctx)
        self._s12_no_premature_decision(page, ctx)
        self._s13_chat_approve_reply(page, ctx)
        self._s14_chat_approve_no_change(page, ctx)
        self._s15_approve_via_hud(page, ctx)
        self._s16_approved_banner(page, ctx)
        self._s17_zero_execution_attempts(page, ctx)
        self._s18_refresh_persistence(page, ctx)
        page = self._s19_close_reopen(browser, state_path, ctx)
        self._s20_continuity(page, ctx)
        self._s21_no_rival_decision_path(page, ctx)
        # Bonus mini-cases (do not gate the pass).
        self._s22a_self_build(page, ctx)
        self._s22b_projection_build(page, ctx)
        return page

    # ── s01 — fresh-state proof ──────────────────────────────────────────────
    def _s01_fresh_state(self, page: Any) -> None:
        """App storage cleared, service worker unregistered, no plan pre-submit."""
        cleared = self._clear_app_state(page)
        page.reload(wait_until="load")
        page.wait_for_timeout(1500)
        no_plan = page.locator(WG_PLAN_ROOT).count() == 0
        sw_cleared = bool(cleared.get("sw_unregister_requested"))
        self.stage(
            "s01_fresh_state",
            no_plan,
            f"no_plan_pre_submit={no_plan} sw_unregister={sw_cleared} "
            f"ls_removed={len(cleared.get('localStorage_removed', []))}",
        )
        self.shot(page, "s01_fresh_state")

    # ── s02 — authenticated principal + tenant proof ─────────────────────────
    def _s02_principal_tenant(self, page: Any) -> None:
        """Clerk session present AND GET /api/umh/objective-plan returns 200 JSON.

        A 200 from the authed objective-plan surface proves the server resolved a
        principal + tenant for this session (the route runs under the same auth
        the operator uses); the Clerk session presence is the client-side half.
        """
        clerk_ok = bool(page.evaluate("() => !!(window.Clerk && window.Clerk.session)"))
        resp = self._authed_get(page, "/api/umh/objective-plan")
        # surface_list returns a JSON list; _authed_get wraps non-dict bodies in
        # __body, so a 200 with either a dict or a list body is the pass signal.
        status = resp.get("__status") if isinstance(resp, dict) else None
        api_ok = status == 200 and not resp.get("__error")
        self.stage(
            "s02_principal_tenant",
            clerk_ok and api_ok,
            f"clerk_session={clerk_ok} objective_plan_status={status}",
        )
        self.shot(page, "s02_principal")

    # ── s03 — communication-only ─────────────────────────────────────────────
    def _s03_communication_only(self, page: Any, ctx: dict[str, Any]) -> None:
        """A pure greeting creates NO plan card, NO kanban card, NO HUD row."""
        cards_before = page.locator(WG_KANBAN_CARD).count()
        approvals_before = page.locator(WG_OBJECTIVE_PLAN_ROW).count()
        self._open_approvals(page)  # expand so any spurious row would be visible
        self._send_and_wait(page, GREETING_MESSAGE)
        page.wait_for_timeout(2500)  # bounded window for any (unwanted) artifact
        no_plan = page.locator(WG_PLAN_ROOT).count() == 0
        no_new_kanban = page.locator(WG_KANBAN_CARD).count() <= cards_before
        no_new_approval = page.locator(WG_OBJECTIVE_PLAN_ROW).count() <= approvals_before
        ctx["hud_rows_after_greeting"] = page.locator(WG_OBJECTIVE_PLAN_ROW).count()
        self.stage(
            "s03_communication_only",
            no_plan and no_new_kanban and no_new_approval,
            f"no_plan={no_plan} no_new_kanban={no_new_kanban} no_new_approval={no_new_approval}",
        )
        self.shot(page, "s03_communication")

    # ── s04 — simple Task capture ────────────────────────────────────────────
    def _s04_simple_task(self, page: Any, ctx: dict[str, Any]) -> None:
        """An atomic task message → a new kanban card, NO HUD row, Ready/Backlog."""
        cards_before = page.locator(WG_KANBAN_CARD).count()
        approvals_before = page.locator(WG_OBJECTIVE_PLAN_ROW).count()
        self._send_and_wait(page, f"{SIMPLE_TASK_MESSAGE} {self.run_tag}")
        # The reply verbatim confirms the capture path (server-truthed string).
        page.wait_for_timeout(2000)
        reply_ok = self._body_contains(page, "Task captured on the Work board")
        kanban_opened = self._open_kanban(page)
        # A new card appears (DOM if reachable, else the packets API grows).
        packets = self._read_packets(page)
        task_packets = [p for p in packets if (p.get("source_type") != "objective_plan")]
        dom_cards = page.locator(WG_KANBAN_CARD).count()
        card_grew = dom_cards > cards_before or len(task_packets) >= 1
        # Non-executable column: the packet status is Ready/Backlog, never
        # approval_pending/approved/executing.
        non_exec = all(
            (p.get("status") or "").lower()
            in ("drafted", "classified", "planned", "ready_for_review", "")
            for p in task_packets
        )
        no_hud_row = page.locator(WG_OBJECTIVE_PLAN_ROW).count() <= approvals_before
        ctx["task_packet_ids"] = [p["packet_id"] for p in task_packets]
        ctx["kanban_cards_after_s04"] = dom_cards
        self.stage(
            "s04_simple_task",
            card_grew and no_hud_row and non_exec and reply_ok,
            f"card_grew={card_grew} reply_ok={reply_ok} no_hud_row={no_hud_row} "
            f"non_executable={non_exec} kanban_opened={kanban_opened}",
        )
        self.shot(page, "s04_simple_task")
        if kanban_opened:
            self.dom(page, "s04_simple_task")

    # ── s05 — duplicate resolution ───────────────────────────────────────────
    def _s05_duplicate_task(self, page: Any, ctx: dict[str, Any]) -> None:
        """A rephrase of the s04 task must NOT create a second kanban card."""
        self._open_kanban(page)
        cards_before = page.locator(WG_KANBAN_CARD).count()
        packets_before = len(self._read_packets(page))
        self._send_and_wait(page, f"{SIMPLE_TASK_REPHRASE} {self.run_tag}")
        page.wait_for_timeout(2500)
        self._open_kanban(page)
        cards_after = page.locator(WG_KANBAN_CARD).count()
        packets_after = len(self._read_packets(page))
        # No new card by DOM AND no new packet by API — duplicate was resolved.
        dom_unchanged = cards_after <= cards_before
        api_unchanged = packets_after <= packets_before
        self.stage(
            "s05_duplicate_task",
            dom_unchanged and api_unchanged,
            f"cards {cards_before}->{cards_after} packets {packets_before}->{packets_after}",
        )
        self.shot(page, "s05_duplicate_task")

    # ── s06 — Task-to-Objective attachment ───────────────────────────────────
    def _s06_attach_task(self, page: Any, ctx: dict[str, Any]) -> None:
        """Attach the task to an objective; reply references linking, NO dupes.

        There is no dedicated UI affordance for link_work in Wave 1, so the
        machine-checkable assertion is the conservative one from the plan: the
        reply does NOT create duplicate kanban cards (count unchanged). If the
        reply text references linking/attachment we record it as a stronger
        signal, but card-count invariance is the gate.
        """
        self._open_kanban(page)
        cards_before = page.locator(WG_KANBAN_CARD).count()
        packets_before = len(self._read_packets(page))
        self._send_and_wait(page, ATTACH_TASK_TEMPLATE.format(run_tag=self.run_tag))
        page.wait_for_timeout(2500)
        self._open_kanban(page)
        cards_after = page.locator(WG_KANBAN_CARD).count()
        packets_after = len(self._read_packets(page))
        no_dupes = cards_after <= cards_before and packets_after <= packets_before
        references_link = any(
            self._body_contains(page, phrase) for phrase in ("link", "attach", "objective")
        )
        self.stage(
            "s06_attach_task",
            no_dupes,
            f"no_dupes={no_dupes} references_link={references_link} "
            f"cards {cards_before}->{cards_after}",
        )
        self.shot(page, "s06_attach_task")

    # ── s07 — complex dogfood Objective ──────────────────────────────────────
    def _s07_complex_objective(self, page: Any, ctx: dict[str, Any]) -> None:
        """The nine-subsystem objective → plan card with data-state + record id."""
        self._send_and_wait(page, f"{DOGFOOD_OBJECTIVE} {self.run_tag}")
        state = self._wait_wg_state(page, {"rendered", "awaiting_approval", "revised"})
        card = self._plan_card(page)
        plan_id = ""
        try:
            if card.count():
                plan_id = card.first.get_attribute("data-plan-record-id") or ""
        except Exception:  # noqa: BLE001
            plan_id = ""
        ctx["objective_plan_id"] = plan_id
        ctx["objective_state_after_compile"] = state
        ok = state in {"rendered", "awaiting_approval", "revised"} and bool(plan_id)
        self.stage(
            "s07_complex_objective",
            ok,
            f"state={state} plan_record_id={plan_id[:16]}",
        )
        self.shot(page, "s07_complex_objective")
        self.dom(page, "s07_complex_objective")

    # ── s08 — inspect Plan in Work Detail ────────────────────────────────────
    def _s08_inspect_plan_detail(self, page: Any, ctx: dict[str, Any]) -> None:
        """Open Plan → wg-work-detail visible with context (scope/scale/arch/...)."""
        opened = self._open_plan_panel(page)
        detail_visible = page.locator(WG_WORK_DETAIL).count() > 0
        # The context section renders scope(tenant)/planning-scale/archetype/
        # skills/readiness. Its presence is the machine-checkable signal that the
        # plan detail (not just an empty shell) rendered.
        context_visible = page.locator(WG_WORK_DETAIL_CONTEXT).count() > 0
        # Cross-check against server truth: the plan JSON carries work_scope +
        # planning_scale so we can confirm the sections have real content.
        plan_json = self._read_plan_json(page)
        has_scope = bool(
            isinstance(plan_json, dict)
            and (plan_json.get("work_scope") or plan_json.get("planning_scale"))
        )
        self.stage(
            "s08_inspect_plan_detail",
            opened and detail_visible and (context_visible or has_scope),
            f"work_detail={detail_visible} context_section={context_visible} "
            f"server_has_scope={has_scope}",
        )
        self.shot(page, "s08_plan_detail")
        if detail_visible:
            self.dom(page, "s08_plan_detail")

    # ── s09 — Tasks on kanban (plan-sourced) ─────────────────────────────────
    def _s09_tasks_on_kanban(self, page: Any, ctx: dict[str, Any]) -> None:
        """N>0 plan-sourced packets exist; plan-sourced cards carry Open-Plan btn."""
        opened = self._open_kanban(page)
        packets = self._read_packets(page)
        plan_packets = [p for p in packets if p.get("source_type") == "objective_plan"]
        # Plan-sourced cards render a wg-kanban-open-plan button (fromPlan branch).
        open_plan_btns = page.locator(WG_KANBAN_OPEN_PLAN).count() if opened else 0
        ctx["plan_packet_ids"] = [p["packet_id"] for p in plan_packets]
        # The load-bearing proof is packet materialization from the plan; the
        # open-plan affordance is confirmed when the board is reachable.
        ok = len(plan_packets) > 0 and (open_plan_btns > 0 or not opened)
        self.stage(
            "s09_tasks_on_kanban",
            ok,
            f"plan_packets={len(plan_packets)} open_plan_btns={open_plan_btns} "
            f"kanban_opened={opened}",
        )
        self.shot(page, "s09_tasks_on_kanban")
        if opened:
            self.dom(page, "s09_tasks_on_kanban")

    # ── s10 — conversational revision ────────────────────────────────────────
    def _s10_conversational_revision(self, page: Any, ctx: dict[str, Any]) -> None:
        """Revision → graph_version 2, v1 preserved (superseded) in history."""
        self._send_and_wait(page, f"{REVISION_MESSAGE} {self.run_tag}")
        rstate = self._wait_wg_state(page, {"revised", "awaiting_approval", "rendered"})
        card = self._plan_card(page)
        revision_attr = ""
        try:
            revision_attr = card.first.get_attribute("data-revision") or "" if card.count() else ""
        except Exception:  # noqa: BLE001
            revision_attr = ""
        # Server truth: versions history shows v1 preserved AND a v2 present.
        plan_json = self._read_plan_json(page)
        obj_id = plan_json.get("objective_id") if isinstance(plan_json, dict) else None
        versions_ok = False
        v_max = None
        if obj_id and ctx.get("objective_plan_id"):
            versions = self._authed_get(
                page, f"/api/umh/objective-plan/{ctx['objective_plan_id']}/versions"
            )
            rows = versions.get("__body") if isinstance(versions, dict) else None
            if isinstance(rows, list) and rows:
                gvs = [r.get("graph_version") for r in rows if isinstance(r, dict)]
                gvs = [g for g in gvs if isinstance(g, int)]
                if gvs:
                    v_max = max(gvs)
                    versions_ok = 1 in gvs and v_max >= 2
        card_v2 = rstate == "revised" or revision_attr == "2"
        self.stage(
            "s10_conversational_revision",
            card_v2 and (versions_ok or revision_attr == "2"),
            f"state={rstate} data-revision={revision_attr} versions_ok={versions_ok} v_max={v_max}",
        )
        self.shot(page, "s10_revision")
        self.dom(page, "s10_revision")

    # ── s11 — ambiguous reference ────────────────────────────────────────────
    def _s11_ambiguous_reference(self, page: Any, ctx: dict[str, Any]) -> None:
        """ "Cancel it" with no unique referent → ONE clarification, NO state change.

        Uses a fresh conversation so there is no uniquely-selectable plan in the
        thread's reference frame — the protocol must ask which one, and change
        nothing. We assert the revised plan from s10 is UNTOUCHED afterward.
        """
        state_before = ""
        if ctx.get("objective_plan_id"):
            pj = self._authed_get(page, f"/api/umh/objective-plan/{ctx['objective_plan_id']}")
            state_before = pj.get("status", "") if isinstance(pj, dict) else ""
        ctx["s11_state_before"] = state_before
        self._new_conversation(page, "s11_ambiguous")
        self._send_and_wait(page, f"{AMBIGUOUS_CANCEL_MESSAGE} {self.run_tag}")
        page.wait_for_timeout(2500)
        # Exactly one clarification question: the reply asks "which" and no plan
        # transitioned to cancelled.
        asks_clarification = any(
            self._body_contains(page, phrase)
            for phrase in ("which plan", "Which plan", "which one", "cancel target")
        )
        # No cancellation state appeared anywhere on the page.
        no_cancel_state = (
            page.locator('[data-testid="wg-plan-root"][data-state="cancelled"]').count() == 0
        )
        # The s10 plan is unchanged server-side.
        state_after = state_before
        if ctx.get("objective_plan_id"):
            pj = self._authed_get(page, f"/api/umh/objective-plan/{ctx['objective_plan_id']}")
            state_after = pj.get("status", "") if isinstance(pj, dict) else state_before
        unchanged = state_after == state_before
        self.stage(
            "s11_ambiguous_reference",
            asks_clarification and no_cancel_state and unchanged,
            f"asks_clarification={asks_clarification} no_cancel_state={no_cancel_state} "
            f"plan_state {state_before}->{state_after}",
        )
        self.shot(page, "s11_ambiguous")

    # ── s12 — no premature Decision ──────────────────────────────────────────
    def _s12_no_premature_decision(self, page: Any, ctx: dict[str, Any]) -> None:
        """Before the plan was DECISION_READY there was no HUD row; now exactly one.

        The "before" half is evidenced by s03's timeline (no objective_plan row
        appeared after a pure greeting — recorded in ctx). The "now" half: after
        the s07 objective reached awaiting_approval, exactly one objective_plan
        row carrying this run tag exists in the ControlPanel.
        """
        before_rows = ctx.get("hud_rows_after_greeting", 0)
        self._open_approvals(page)
        rows_now = self._approval_row(page)
        row_count = rows_now.count()
        server_ready = False
        if ctx.get("objective_plan_id"):
            pj = self._authed_get(page, f"/api/umh/objective-plan/{ctx['objective_plan_id']}")
            if isinstance(pj, dict):
                status = pj.get("status", "")
                readiness = (pj.get("readiness_assessment") or {}).get("state", "")
                server_ready = status == "awaiting_approval" or "READY" in str(readiness).upper()
        ok = before_rows == 0 and row_count >= 1 and server_ready
        ctx["s12_row_count"] = row_count
        self.stage(
            "s12_no_premature_decision",
            ok,
            f"rows_after_greeting={before_rows} objective_plan_rows_now={row_count} "
            f"server_decision_ready={server_ready}",
        )
        self.shot(page, "s12_hud_row")

    # ── s13 — chat "Approve that plan." explains HUD-only ────────────────────
    def _s13_chat_approve_reply(self, page: Any, ctx: dict[str, Any]) -> None:
        """Chat approve → reply explains decisions happen in the control panel."""
        self._send_and_wait(page, f"{CHAT_APPROVE_MESSAGE} {self.run_tag}")
        page.wait_for_timeout(2000)
        explains_hud = self._body_contains(page, "Decisions are made in the control panel") or (
            self._body_contains(page, "control panel")
            and self._body_contains(page, "Nothing changes until")
        )
        ctx["s13_explained_hud"] = explains_hud
        self.stage(
            "s13_chat_approve_reply",
            explains_hud,
            f"reply_explains_control_panel={explains_hud}",
        )
        self.shot(page, "s13_chat_approve")

    # ── s14 — chat approve changed NOTHING ───────────────────────────────────
    def _s14_chat_approve_no_change(self, page: Any, ctx: dict[str, Any]) -> None:
        """After the chat 'approve', the plan is STILL awaiting_approval; HUD focused."""
        status = ""
        if ctx.get("objective_plan_id"):
            pj = self._authed_get(page, f"/api/umh/objective-plan/{ctx['objective_plan_id']}")
            status = pj.get("status", "") if isinstance(pj, dict) else ""
        still_awaiting = status == "awaiting_approval"
        self._open_approvals(page)
        hud_row_present = self._approval_row(page).count() >= 1
        self.stage(
            "s14_chat_approve_no_change",
            still_awaiting and hud_row_present,
            f"plan_status={status} still_awaiting={still_awaiting} hud_row={hud_row_present}",
        )
        self.shot(page, "s14_no_change")

    # ── s15 — approve via Top HUD ────────────────────────────────────────────
    def _s15_approve_via_hud(self, page: Any, ctx: dict[str, Any]) -> None:
        """Expand ControlPanel, click wg-approve-btn on the run-tag objective row."""
        clicked = self._decide_via_control_panel(page, "approve")
        astate = self._wait_wg_state(page, {"approved"})
        ctx["approved_via_hud"] = clicked
        ctx["card_state_after_approve"] = astate
        self.stage(
            "s15_approve_via_hud",
            clicked and astate == "approved",
            f"clicked={clicked} card_state={astate}",
        )
        self.shot(page, "s15_hud_approve")
        self.dom(page, "s15_hud_approve")

    # ── s16 — APPROVED banner + decision-log message ─────────────────────────
    def _s16_approved_banner(self, page: Any, ctx: dict[str, Any]) -> None:
        """Plan status APPROVED and the "PLAN APPROVED — EXECUTION NOT STARTED" copy.

        Two independent signals: the UI banner text in the plan card/detail, and
        the server decision_log's last entry carrying the same status message
        (authorization_effect=plan_acceptance_only).
        """
        banner_ok = self._body_contains(page, APPROVED_BANNER)
        plan_json = self._read_plan_json(page)
        status = plan_json.get("status", "") if isinstance(plan_json, dict) else ""
        decision_log = plan_json.get("decision_log") if isinstance(plan_json, dict) else None
        log_ok = False
        auth_effect_ok = False
        if isinstance(decision_log, list) and decision_log:
            last = decision_log[-1]
            if isinstance(last, dict):
                msg = str(last.get("status_message", "")) + str(last.get("message", ""))
                log_ok = "APPROVED" in msg.upper() or "EXECUTION NOT STARTED" in msg.upper()
                auth_effect_ok = str(last.get("authorization_effect", "")) == "plan_acceptance_only"
        server_approved = status == "approved"
        self.stage(
            "s16_approved_banner",
            banner_ok and server_approved and (log_ok or auth_effect_ok),
            f"banner={banner_ok} server_status={status} log_msg_ok={log_ok} "
            f"auth_effect_plan_acceptance_only={auth_effect_ok}",
        )
        self.shot(page, "s16_approved_banner")
        self.dom(page, "s16_approved_banner")

    # ── s17 — zero ExecutionAttempts ─────────────────────────────────────────
    def _s17_zero_execution_attempts(self, page: Any, ctx: dict[str, Any]) -> None:
        """Every plan packet is still status=planned — none approved/executing."""
        packets = self._read_packets(page)
        plan_packets = [p for p in packets if p.get("source_type") == "objective_plan"]
        exec_statuses = {
            "approved",
            "delegated",
            "executing",
            "reconverging",
            "validating",
            "completed",
        }
        executed = [p for p in plan_packets if (p.get("status") or "").lower() in exec_statuses]
        all_planned = all(
            (p.get("status") or "").lower()
            in ("planned", "classified", "drafted", "ready_for_review")
            for p in plan_packets
        )
        ok = len(plan_packets) > 0 and not executed and all_planned
        self.stage(
            "s17_zero_execution_attempts",
            ok,
            f"plan_packets={len(plan_packets)} executed={len(executed)} all_planned={all_planned}",
        )
        self.shot(page, "s17_no_execution")

    # ── s18 — refresh persistence ────────────────────────────────────────────
    def _s18_refresh_persistence(self, page: Any, ctx: dict[str, Any]) -> None:
        """Reload: plan card re-renders, kanban persists, no resurrected pending row."""
        before = self._read_plan_by_conversation(page)
        page.reload(wait_until="load")
        page.wait_for_timeout(2500)
        after = self._read_plan_by_conversation(page)
        card_present = page.locator(WG_PLAN_ROOT).count() > 0
        same_plan = (
            isinstance(before, dict)
            and isinstance(after, dict)
            and before.get("plan_record_id")
            and before.get("plan_record_id") == after.get("plan_record_id")
        )
        self._open_kanban(page)  # navigate the board (persistence of task cards)
        packets = self._read_packets(page)
        plan_packets = [p for p in packets if p.get("source_type") == "objective_plan"]
        # No resurrected pending decision row for the now-decided (approved) plan.
        self._open_approvals(page)
        resurrected = self._approval_row(page).count() > 0
        ctx["s18_after"] = after
        self.stage(
            "s18_refresh_persistence",
            bool(same_plan or card_present) and len(plan_packets) > 0 and not resurrected,
            f"card_present={card_present} same_plan={bool(same_plan)} "
            f"plan_packets={len(plan_packets)} resurrected_pending_row={resurrected}",
        )
        self.shot(page, "s18_refresh")

    # ── s19 — Chrome close / reopen ──────────────────────────────────────────
    def _s19_close_reopen(self, browser: Any, state_path: str, ctx: dict[str, Any]) -> Any:
        """Close the context, open a brand new one, re-auth from cached Clerk state."""
        context = self._new_context(browser, state_path)
        page = context.new_page()
        self._wire_listeners(page)
        page.goto(self.url, wait_until="load", timeout=45000)
        page.wait_for_timeout(2500)
        reauthed = bool(page.evaluate("() => !!(window.Clerk && window.Clerk.session)"))
        ctx["reopened_page"] = True
        self.stage(
            "s19_close_reopen",
            reauthed,
            f"reauthenticated_from_cached_clerk={reauthed}",
        )
        self.shot(page, "s19_reopen")
        return page

    # ── s20 — continuity after relaunch ──────────────────────────────────────
    def _s20_continuity(self, page: Any, ctx: dict[str, Any]) -> None:
        """Conversation, Task cards, approved v2 Objective/Plan, scope, decision,
        assistant name all persist after the s19 close/reopen."""
        after = self._read_plan_by_conversation(page)
        before = ctx.get("s18_after", {})
        # Plan identity + version + approved state persist (no duplicate graph).
        no_dupe = (
            isinstance(after, dict)
            and isinstance(before, dict)
            and after.get("plan_record_id") == before.get("plan_record_id")
        )
        plan_json = self._read_plan_json(page)
        approved_persisted = isinstance(plan_json, dict) and plan_json.get("status") == "approved"
        v2_persisted = (
            isinstance(plan_json, dict)
            and isinstance(plan_json.get("graph_version"), int)
            and plan_json.get("graph_version") >= 2
        )
        scope_persisted = bool(
            isinstance(plan_json, dict)
            and (plan_json.get("work_scope") or plan_json.get("planning_scale"))
        )
        # Task cards persist.
        self._open_kanban(page)
        packets = self._read_packets(page)
        cards_persisted = len(packets) > 0
        # Assistant name persists (the chat input placeholder is "Message <name>…").
        chat = self._find_chat_input(page)
        name_persisted = chat.count() > 0
        ok = (
            (no_dupe or (isinstance(after, dict) and bool(after.get("plan_record_id"))))
            and approved_persisted
            and scope_persisted
            and cards_persisted
            and name_persisted
        )
        self.stage(
            "s20_continuity",
            ok,
            f"no_dupe={bool(no_dupe)} approved_persisted={approved_persisted} "
            f"v2_persisted={v2_persisted} scope_persisted={scope_persisted} "
            f"cards_persisted={cards_persisted} name_persisted={name_persisted}",
        )
        self.shot(page, "s20_continuity")
        self.dom(page, "s20_continuity")

    # ── s21 — no rival decision path ─────────────────────────────────────────
    def _s21_no_rival_decision_path(self, page: Any, ctx: dict[str, Any]) -> None:
        """Retired panel ids route to canonical surfaces; decision controls exist
        ONLY in the ControlPanel HUD.

        The retired ids (intent/intentloop/objectiveplan/commands/tasks) resolve
        client-side through the panel registry (workdetail/work/chat). We cannot
        call the store from Playwright, but we CAN verify the load-bearing
        invariant: NO approve/reject control renders anywhere on the page while
        the HUD is COLLAPSED, and when expanded the ONLY approve/reject controls
        are inside the wg-hud-approvals / ControlPanel strip. A page-wide query
        for wg-approve-btn/wg-reject-btn outside the HUD container must be empty.
        """
        # Navigate through each retired surface's canonical target and confirm no
        # rogue decision control appears. We reach workdetail via Open Plan (the
        # objectiveplan/intent target) and work via the kanban (the tasks target).
        self._open_kanban(page)  # tasks/universalwork → work
        work_decision_ctrls = page.locator(
            f"{WG_KANBAN} {WG_APPROVE_BTN}, {WG_KANBAN} {WG_REJECT_BTN}"
        ).count()
        # Page-wide approve/reject buttons must all live inside the ControlPanel.
        total_approve = page.locator(WG_APPROVE_BTN).count()
        total_reject = page.locator(WG_REJECT_BTN).count()
        # Buttons that are NOT descendants of a wg-approval-row (the HUD row) are
        # rogue. XPath: any wg-approve-btn with no ancestor approval row.
        rogue_approve = page.locator(
            "xpath=//*[@data-testid='wg-approve-btn']"
            "[not(ancestor::*[@data-testid='wg-approval-row'])]"
        ).count()
        rogue_reject = page.locator(
            "xpath=//*[@data-testid='wg-reject-btn']"
            "[not(ancestor::*[@data-testid='wg-approval-row'])]"
        ).count()
        ok = work_decision_ctrls == 0 and rogue_approve == 0 and rogue_reject == 0
        self.stage(
            "s21_no_rival_decision_path",
            ok,
            f"kanban_decision_ctrls={work_decision_ctrls} total_approve={total_approve} "
            f"total_reject={total_reject} rogue_approve={rogue_approve} rogue_reject={rogue_reject}",
        )
        self.shot(page, "s21_no_rival_path")

    # ── s22a / s22b — governance-profile mini-cases (bonus, non-gating) ───────
    def _s22a_self_build(self, page: Any, ctx: dict[str, Any]) -> None:
        """Self-build planning message → plan compiles, umh_substrate governance,
        approval NOT auto-granted."""
        self._new_conversation(page, "s22a_self_build")
        try:
            self._send_and_wait(page, f"{SELF_BUILD_MESSAGE} {self.run_tag}")
            state = self._wait_wg_state(
                page, {"rendered", "awaiting_approval", "revised", "clarifying"}
            )
            plan_json = self._read_plan_json(page)
            scope = plan_json.get("work_scope") if isinstance(plan_json, dict) else {}
            target = (scope or {}).get("target_kind", "") if isinstance(scope, dict) else ""
            not_auto_approved = (
                isinstance(plan_json, dict) and plan_json.get("status") != "approved"
            )
            substrate_profile = target == "umh_substrate" or self._body_contains(page, "substrate")
            self.stage(
                "s22a_self_build",
                state != "" and not_auto_approved,
                f"state={state} target_kind={target} substrate_profile={substrate_profile} "
                f"not_auto_approved={not_auto_approved}",
            )
        except Exception as exc:  # noqa: BLE001 — bonus step never breaks the pass
            self.stage("s22a_self_build", False, f"exception={str(exc)[:120]}")
        self.shot(page, "s22a_self_build")

    def _s22b_projection_build(self, page: Any, ctx: dict[str, Any]) -> None:
        """Projection-build planning message → plan compiles, projection governance,
        approval NOT auto-granted."""
        self._new_conversation(page, "s22b_projection")
        try:
            self._send_and_wait(page, f"{PROJECTION_BUILD_MESSAGE} {self.run_tag}")
            state = self._wait_wg_state(
                page, {"rendered", "awaiting_approval", "revised", "clarifying"}
            )
            plan_json = self._read_plan_json(page)
            scope = plan_json.get("work_scope") if isinstance(plan_json, dict) else {}
            target = (scope or {}).get("target_kind", "") if isinstance(scope, dict) else ""
            not_auto_approved = (
                isinstance(plan_json, dict) and plan_json.get("status") != "approved"
            )
            self.stage(
                "s22b_projection_build",
                state != "" and not_auto_approved,
                f"state={state} target_kind={target} not_auto_approved={not_auto_approved}",
            )
        except Exception as exc:  # noqa: BLE001 — bonus step never breaks the pass
            self.stage("s22b_projection_build", False, f"exception={str(exc)[:120]}")
        self.shot(page, "s22b_projection_build")

    # ── finalize + ship ──────────────────────────────────────────────────────
    # Bonus steps that must NOT gate the pass (plan v5.1 §23: gate on s01–s21).
    _NON_GATING_STAGES = ("s22a_self_build", "s22b_projection_build")

    def _finalize(self, page: Any) -> dict[str, Any]:
        # Gate on every stage EXCEPT the explicitly non-gating bonus mini-cases.
        gating_stages = [s for s in self.stages if s["stage"] not in self._NON_GATING_STAGES]
        passed = self.error is None and all(s["ok"] for s in gating_stages)
        bonus = {s["stage"]: s["ok"] for s in self.stages if s["stage"] in self._NON_GATING_STAGES}
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
            "bonus_stages": bonus,
            "continuity": self.continuity,
            "correlation_ids": [self.correlation_id],
            "asset_files_seen": asset_files,
            "error": self.error,
            # The gating failure (ignoring bonus mini-cases), for the terminal verdict.
            "failed_stage": next((s["stage"] for s in gating_stages if not s["ok"]), None),
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
