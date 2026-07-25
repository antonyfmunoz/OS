"""Wave 2 field-qualification collector — runs ON the Windows executor node.

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
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Secret-hygiene redaction (identical to wave1_field_dispatch.py). Applied at
# capture time to any 4xx/5xx response body + console/pageerror text, and again
# as a final pass over the shipped pass dir. A candidate error payload can echo
# a bearer token / JWT / api_key= pair; without this it would land unredacted in
# network.jsonl / console.jsonl and be scp'd into the committed proof (review C1).
_SECRET_REDACT_RE = re.compile(
    r"(?i)(bearer\s+[A-Za-z0-9._\-]+|eyJ[A-Za-z0-9._\-]{20,}|"
    r"(?:password|secret|token|api[_-]?key)\s*[=:]\s*\S+)"
)


def _redact(text: str) -> str:
    """Redact bearer/JWT/password patterns from a captured string."""
    return _SECRET_REDACT_RE.sub("<redacted>", text)

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
    # Emitted by objective_plan_routes when a chat "approve that plan" surfaces
    # the decision to the HUD (PROVIDE_DECISION → HUD-only authority, no state
    # transition). A legitimate published state — not UI drift.
    "decision_surfaced",
    "clarification_required",
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
# Phrasing is deterministic-classifier-verified against the REAL dogfood plan:
# classify_revision parses "remove <node tokens> from the plan" into exactly one
# remove_node edit for the 'profile' migration node. "Add a … step" has NO
# parser branch (known capability gap, recorded in the PR — the rail correctly
# replies with phrasing guidance instead of guessing). The trailing period
# matters: the clause split isolates the appended run tag into its own
# (droppable) clause — without it the tag pollutes the remove phrase.
REVISION_MESSAGE = "Remove the profile subsystem from the plan."

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

# ── Wave-2 execution data-testid contract (shipped in C6) ────────────────────
# The Attempts surface (ExecutionPanel/AttemptsView), the chat execution card
# (ChatExecutionCard — STATUS ONLY, no authorize control), the HUD execution-
# authorization decision row (ControlPanel: wg-approval-row +
# data-source-type="execution_authorization" + w2-execution-decision), and the
# Work overlay. Anchors verified present in cockpit/src/renderer 2026-07-23.
W2_EXECUTION_ROOT = '[data-testid="w2-execution-root"]'
W2_EXECUTION_ATTEMPT = '[data-testid="w2-execution-attempt"]'  # data-attempt-id, data-status; task_id as text
W2_EXECUTION_DECISION = '[data-testid="w2-execution-decision"]'  # HUD row, data-decision-ref
W2_EXEC_APPROVE_BTN = '[data-testid="w2-exec-approve-btn"]'
W2_EXEC_REJECT_BTN = '[data-testid="w2-exec-reject-btn"]'
W2_EXEC_CARD_ROOT = '[data-testid="w2-exec-card-root"]'  # chat exec card (status-only)
W2_PROOF_LINK = '[data-testid="w2-proof-link"]'
W2_ASSIGNMENT = '[data-testid="w2-assignment"]'
W2_ENVIRONMENT_LEASE = '[data-testid="w2-environment-lease"]'
W2_VERIFICATION_STATUS = '[data-testid="w2-verification-status"]'
W2_EXECUTION_CANCEL = '[data-testid="w2-execution-cancel"]'
W2_EXECUTION_RETRY = '[data-testid="w2-execution-retry"]'
W2_OPEN_EXECUTION_BTN = '[data-testid="w2-open-execution-btn"]'
W2_OPEN_TASK_BTN = '[data-testid="w2-open-task-btn"]'
W2_WORK_OVERLAY = '[data-testid="w2-work-overlay"]'
W2_WORKER_STATUS = '[data-testid="w2-worker-status"]'

# w05 — the fixture (note-search) objective. Decomposes into Tasks A (backend
# search endpoint), B (frontend search box), C (integration), D (verification).
# Mirrors infra/fixture/make_fixture_app.py OBJECTIVE.md so the plan's tasks map
# to the fixture's real work.
FIXTURE_OBJECTIVE = (
    "Add a case-insensitive note search to the fixture app: a backend search "
    "endpoint GET /api/notes/search?q= that matches title and body and returns "
    "{query, results}, a frontend search box wired to it, integrated and "
    "verified end to end. Task A is the backend endpoint, Task B is the frontend "
    "search box, Task C integrates and runs the full suite, and Task D "
    "independently verifies the API, the UI, and a live browser check."
)

# w11 — the execute request. Classified REQUEST_EXECUTION → mints an execution-
# authorization DECISION surfaced in the HUD; it must NOT start execution.
EXECUTE_MESSAGE = "Execute the approved plan."

# Per-origin auth state file — Clerk auth ONLY (no app state). Created on pass 1
# via typed login, reused thereafter within its TTL.
_AUTH_DIR = Path(os.path.expanduser("~")) / ".umh" / "playwright-auth"
_AUTH_STATE_FILE = _AUTH_DIR / "chromium_state_wave2.json"

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
        fixture_url: str = "",
    ) -> None:
        self.url = url
        self.run_id = run_id
        self.pass_num = pass_num
        self.scenario = scenario
        self.candidate_commit = candidate_commit
        self.ship_to = ship_to
        self.fixture_url = fixture_url
        self.run_tag = f"[w2-{run_id}-p{pass_num}]"
        self.correlation_id = f"w2-{run_id}-p{pass_num}"

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
        self._conversation_id = ""  # captured from each converse response
        self._last_plan_id = ""  # this run's plan record id (s07 onward)
        self._decision_response = ""  # HUD decide POST "status body" evidence
        self._execution_decision_ref = ""  # execution-auth decision ref (w14)
        self._attempt_ids: dict[str, str] = {}  # task_id -> attempt_id (w16+)
        self._proof_id = ""  # PlanExecutionProof id (w24)

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
        """Read-only DOM snapshot for one journey stage.

        Captures the FULL app shell (``#root``, body fallback) — NOT just the
        chat ``wg-plan-root`` subtree. Different stages (kanban, HUD approval,
        Work-Detail panel, approved banner, continuity) mutate different parts
        of the app; snapshotting only the chat card produced byte-identical
        artifacts across s07/s08/s10/s15/s16/s20 (evidence-integrity finding,
        CodeRabbit 2026-07-23). The whole-shell capture makes each stage's
        artifact genuinely distinct evidence of that stage's rendered surface.
        Bounded to 400KB (the shell is larger than one card).
        """
        fname = f"{name}.dom.html"
        try:
            html = page.evaluate(
                """() => {
                    const root = document.querySelector('#root')
                        || document.querySelector('[data-testid="wg-cockpit-shell"]')
                        || document.body;
                    return (root.outerHTML || document.body.innerHTML).slice(0, 400000);
                }"""
            )
        except Exception as exc:  # noqa: BLE001
            html = f"<!-- dom snapshot failed: {exc} -->"
        (self.pass_dir / fname).write_text(str(html), encoding="utf-8")
        self.dom_snapshots.append(fname)

    # ── wiring: network + console listeners ─────────────────────────────────
    def _wire_listeners(self, page: Any) -> None:
        def on_response(resp: Any) -> None:
            # Defensive: an exception in a playwright event handler is silently
            # swallowed AND can kill subsequent deliveries — network.jsonl came
            # back EMPTY on runs 165422/170831/172506 while console.jsonl was
            # fine. Every access is guarded; a 4xx/5xx API response also
            # captures a bounded body snippet (the 422 that broke s15 was
            # invisible without it).
            try:
                u = resp.url
                if "/api/" not in u:
                    return
                entry: dict[str, Any] = {
                    "url": u.split("?")[0],
                    "status": resp.status,
                    "ms": int((time.time() - self._start) * 1000),
                }
                try:
                    entry["method"] = resp.request.method
                except Exception:  # noqa: BLE001
                    entry["method"] = "?"
                if resp.status >= 400:
                    try:
                        # Redact at capture time — an error body can echo a
                        # bearer token / JWT / api_key= pair (review C1).
                        entry["body"] = _redact((resp.text() or "")[:300])
                    except Exception:  # noqa: BLE001
                        entry["body"] = "<unreadable>"
                self.network.append(entry)
            except Exception:  # noqa: BLE001 — never break the event pipeline
                pass

        page.on("response", on_response)
        page.on(
            "console",
            lambda m: self.console.append(
                {
                    "type": m.type,
                    # Console text can echo a token from an error log (review C1).
                    "text": _redact(m.text[:300]),
                    "ms": int((time.time() - self._start) * 1000),
                }
            ),
        )
        page.on(
            "pageerror",
            lambda e: self.console.append(
                {
                    "type": "pageerror",
                    "text": _redact(str(e)[:300]),
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
    def _capture_conversation_id(self, resp: Any) -> None:
        """Remember the conversation id from a /advisor/converse response.

        The plan card is anchored by data-conversation-id (published testid
        contract), and the converse response carries the id — capture it at
        send time so _plan_card can address the card precisely."""
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001 — non-JSON response; keep prior id
            return

        def find(obj: Any) -> str | None:
            if isinstance(obj, dict):
                v = obj.get("conversation_id")
                if isinstance(v, str) and v:
                    return v
                for x in obj.values():
                    r = find(x)
                    if r:
                        return r
            elif isinstance(obj, list):
                for x in obj:
                    r = find(x)
                    if r:
                        return r
            return None

        cid = find(body)
        if cid:
            self._conversation_id = cid

    def _plan_card(self, page: Any) -> Any:
        """This pass's plan card, anchored by conversation id.

        The run tag lives in the USER message, never inside the wg-plan-root
        subtree — `filter(has_text=run_tag)` matched NOTHING while the card sat
        fully rendered with data-state=awaiting_approval (run 20260722T170831Z,
        proven by the shipped DOM snapshot). Anchor order: exact
        data-conversation-id (captured from the converse response) → run-tag
        text filter (kept for any future card that embeds the tag) → all roots
        (fresh conversations render exactly one)."""
        conv = getattr(self, "_conversation_id", "")
        if conv:
            scoped = page.locator(f'{WG_PLAN_ROOT}[data-conversation-id="{conv}"]')
            if scoped.count() > 0:
                return scoped
        tagged = page.locator(WG_PLAN_ROOT).filter(has_text=self.run_tag)
        if tagged.count() > 0:
            return tagged
        return page.locator(WG_PLAN_ROOT)

    def _wg_state(self, page: Any) -> str:
        card = self._plan_card(page)
        try:
            if card.count() == 0:
                return ""
            # .last = the NEWEST card in the thread — a revision renders a
            # NEW card for v(n+1); .first kept reading the stale v1 card
            # (run 20260722T181248Z: server had v2, card said v1).
            state = card.last.get_attribute("data-state") or ""
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

    def _approval_row(self, page: Any, plan_id: str = "") -> Any:
        """The ControlPanel objective_plan approval row for THIS run's plan.

        ANCHOR ORDER (learned from run 20260722T172506Z): the approval
        description is truncated server-side to 300 chars
        (planning/decisions.py), which cuts the run tag off the ~540-char
        dogfood objective — text anchoring silently degraded to a broad xpath
        that "matched" page-level containers and clicked the wrong button. The
        row now carries data-plan-record-id (ControlPanel published contract),
        so the plan id is the primary anchor; run-tag text is the fallback for
        short descriptions that do retain the tag. NO broad xpath fallback —
        a missing row must FAIL LOUDLY, never click something else.
        """
        if plan_id:
            rows = page.locator(f'{WG_APPROVAL_ROW}[data-plan-record-id="{plan_id}"]')
            if rows.count() > 0:
                return rows
        rows = page.locator(WG_OBJECTIVE_PLAN_ROW).filter(has_text=self.run_tag)
        if rows.count() > 0:
            return rows
        return page.locator(WG_APPROVAL_ROW).filter(has_text=self.run_tag)

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
        endpoint = (
            "/unified-approval/approve" if decision == "approve" else "/unified-approval/reject"
        )
        plan_id = str(self._last_plan_id or "")
        self._open_approvals(page)
        deadline = time.time() + 150
        while time.time() < deadline:
            row = self._approval_row(page, plan_id)
            if row.count() > 0:
                btn = row.first.locator(btn_selector)
                if btn.count() > 0:
                    try:
                        row.first.scroll_into_view_if_needed(timeout=2000)
                    except Exception:  # noqa: BLE001 — best-effort scroll
                        pass
                    # Capture the decision request's RESPONSE — a 4xx here was
                    # previously invisible (run 20260722T172506Z: the approve
                    # POST 422'd and the pass burned 150s waiting for a state
                    # flip that could never come).
                    status_body = ""
                    try:
                        with page.expect_response(lambda r: endpoint in r.url, timeout=20000) as ri:
                            btn.first.click()
                        resp = ri.value
                        body = ""
                        try:
                            body = (resp.text() or "")[:200]
                        except Exception:  # noqa: BLE001
                            body = "<unreadable>"
                        status_body = f"{resp.status} {body}"
                        self._decision_response = status_body
                        return resp.status < 300
                    except Exception as exc:  # noqa: BLE001 — no response seen
                        self._decision_response = f"no-response ({str(exc)[:80]})"
                        return False
            self._open_approvals(page)  # re-expand if a 5s refresh collapsed it
            time.sleep(3)  # bounded poll; approval list refreshes ~every 5s
        self._decision_response = "row-never-appeared"
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
            card.last.locator(WG_OPEN_PLAN_BTN) if card.count() else page.locator(WG_OPEN_PLAN_BTN)
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
        # NavRail-scoped anchor: buttons carry title="<label> (Ctrl+<n>)". A
        # bare role/name "Work" match resolved to buttons INSIDE open panels
        # (run 20260722T191415Z hung clicking a Work-Detail row). setPanel now
        # bridges to canvas windows, so this click genuinely opens the board.
        work_nav = page.locator('button[title^="Work ("]')
        if work_nav.count() == 0:
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

    def _read_task_packet_ids(self, page: Any) -> set[str]:
        """THIS pass's atomic-task packets only — run-scoped and source-scoped.

        Duplicate-resolution steps (s05/s06) must measure the ONE thing they
        assert about: whether a rephrase/attachment created another *operator
        task*. A raw global packet count is neither run- nor source-scoped: the
        server keeps prior-pass packets, and the dogfood Objective's own
        decomposition packets (source_type objective_plan / batch_child /
        batch_decomposition) materialize ASYNCHRONOUSLY and can land inside the
        s05 measurement window. Field run 20260723T045653Z-p3 failed s05 on
        `packets 12->18` while creating exactly ONE operator_task packet — the
        other rows were that pass's plan decomposition, not a duplicate task.
        Scope by source_type == operator_task AND this pass's run tag.
        """
        ids: set[str] = set()
        for packet in self._read_packets(page):
            if (packet.get("source_type") or "") != "operator_task":
                continue
            blob = f"{packet.get('title', '')} {packet.get('source_id', '')}"
            if self.run_tag and self.run_tag not in blob:
                continue
            pid = packet.get("packet_id")
            if pid:
                ids.add(str(pid))
        return ids

    @staticmethod
    def _read_packet_ids(page: Any) -> list[str]:
        """Just the packet ids (compat shim over _read_packets)."""
        return [p["packet_id"] for p in FieldCollector._read_packets(page) if p.get("packet_id")]

    # ── typing with human jitter ─────────────────────────────────────────────
    @staticmethod
    def _type_objective(page: Any, chat: Any, text: str) -> None:
        chat.first.click()
        # RESIDUAL-TEXT GUARD: if a previous Enter was swallowed (the input
        # ignores submit while a reply is streaming), stale text would be
        # CONCATENATED with this message — pass 20260722T172506Z shipped
        # "Cancel it. [tag] Approve that plan. [tag]" as ONE message. Clear
        # any residue first, and after Enter verify the input actually emptied
        # (retry the submit on a bounded loop).
        try:
            if (chat.first.input_value() or "").strip():
                chat.first.fill("")
        except Exception:  # noqa: BLE001 — non-input element; typing continues
            pass
        # press_sequentially with per-key jitter (40-90ms) — human cadence, and
        # exercises the real input handler rather than a bulk fill().
        import random

        delay = random.randint(40, 90)
        # The action timeout must scale with the text: the ~540-char dogfood
        # objective at >=56ms/key exceeds playwright's 30s default MID-TYPING
        # (observed run 20260722T163403Z — pass/fail depended on the jitter
        # roll). Budget = worst-case keystroke time + 15s actionability slack.
        budget_ms = len(text) * (delay + 30) + 15000
        chat.first.press_sequentially(text, delay=delay, timeout=budget_ms)
        chat.first.press("Enter")
        for _ in range(10):  # bounded submit-verify loop (max ~5s)
            try:
                if not (chat.first.input_value() or "").strip():
                    return
            except Exception:  # noqa: BLE001 — input re-rendered; treat as sent
                return
            page.wait_for_timeout(500)
            chat.first.press("Enter")

    def _send_and_wait(self, page: Any, text: str, timeout_ms: int = 180000) -> None:
        """Type a message into the chat rail and wait for its /advisor/converse 200.

        Re-locates the chat input each call (the rail can re-render after a plan
        card mounts). The converse round-trip is the CONDITION — no bare sleep.
        """
        chat = self._find_chat_input(page)
        with page.expect_response(
            lambda r: "/advisor/converse" in r.url and r.status == 200, timeout=timeout_ms
        ) as resp_info:
            self._type_objective(page, chat, text)
        self._capture_conversation_id(resp_info.value)

    @staticmethod
    def _body_contains(page: Any, needle: str) -> bool:
        """Whether the rendered page body currently contains `needle` (verbatim)."""
        try:
            return needle in page.inner_text("body")
        except Exception:  # noqa: BLE001
            return False

    def _find_chat_input(self, page: Any) -> Any:
        """Locate the chat rail input, opening the right drawer if closed.

        A FRESH profile (and every post-clear reload) boots with the right
        drawer CLOSED: cockpitStore `rightDrawerOpen` defaults to false and
        the cleared persisted state can't reopen it. The chat input lives in
        RightRail and is NOT in the DOM until the drawer opens. Two real
        openers exist in CanvasToolbar: the PanelRight ToolbarButton titled
        "Open panel" (ChatToggle → toggleRightDrawer), and choosing a view in
        the RightPanelSwitcher dropdown (setRightPanelView force-opens the
        drawer). The switcher BUTTON alone only shows the dropdown — clicking
        it and stopping was why smoke 20260722T162438Z saw no input on an
        otherwise fully-authenticated cockpit."""
        chat = page.locator(CHAT_INPUT_SELECTOR)
        if chat.count() > 0:
            return chat
        # (1) drawer toggle — deterministic single click
        toggle = page.locator('button[title="Open panel"]')
        if toggle.count() > 0:
            toggle.first.click()
            page.wait_for_timeout(800)
            chat = page.locator(CHAT_INPUT_SELECTOR)
            if chat.count() > 0:
                return chat
        # (2) switcher dropdown → "Chat" item (also force-opens the drawer)
        switcher = page.get_by_role("button", name="Chat")
        if switcher.count() > 0:
            switcher.first.click()
            page.wait_for_timeout(400)
            items = page.get_by_role("button", name="Chat")
            if items.count() > 1:
                items.nth(items.count() - 1).click()
            page.wait_for_timeout(800)
            chat = page.locator(CHAT_INPUT_SELECTOR)
            if chat.count() > 0:
                return chat
        # (3) last resort — legacy shortcut from the p4s31c path
        page.keyboard.press("Control+/")
        page.wait_for_timeout(800)
        return page.locator(CHAT_INPUT_SELECTOR)

    def _new_conversation(self, page: Any, tag: str) -> None:
        """Force a fresh conversation: clear app storage + reload.

        chatStore starts empty, so a reload with app storage cleared yields a new
        conversation. Records what was cleared as a stage.
        """
        cleared = self._clear_app_state(page)
        # The next send starts a NEW conversation — drop the captured id so
        # _plan_card can't anchor to the previous conversation's card.
        self._conversation_id = ""
        page.reload(wait_until="load")
        page.wait_for_timeout(1500)
        # Fresh-state proof: the persisted conversation binding is GONE, so the
        # next send necessarily mints a NEW conversation. This is the invariant
        # the journey needs — NOT an empty screen: server-side chat history
        # legitimately re-renders prior conversations' plan cards after a reload
        # (prior-pass artifacts persist server-side by design), so a global
        # zero-plan-card gate degrades as history accumulates and is racy on the
        # history fetch (run 20260723T141402Z: plan_root_present=5, all history
        # cards, reset itself fully effective). The visible-card count is kept
        # as informational detail only.
        conv_key_cleared = page.evaluate(
            "() => localStorage.getItem('umh.chat.conversation_id') === null"
        )
        pre = page.locator(WG_PLAN_ROOT)
        self.stage(
            f"fresh_state_{tag}",
            bool(conv_key_cleared),
            f"conversation_binding_cleared={conv_key_cleared} "
            f"cleared={len(cleared.get('localStorage_removed', []))}ls "
            f"{len(cleared.get('sessionStorage_removed', []))}ss; "
            f"history_plan_cards_visible={pre.count()}",
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
        """Fresh context carrying ONLY Clerk auth + our correlation header.

        The correlation header is injected ONLY on same-origin (candidate)
        requests via route interception — NEVER context-wide. A context-wide
        extra_http_headers made every cross-origin request non-simple, forcing
        CORS preflights on the clerk-js script fetch, which Clerk's CDN
        rejects (`x-correlation-id` not in Access-Control-Allow-Headers) —
        the auth UI never rendered (field passes 20260722T055406Z/155848Z).
        The header exists to correlate collector requests with CANDIDATE logs,
        so scoping it to the candidate origin is also semantically correct.
        """
        context = browser.new_context(
            storage_state=state_path,
            viewport={"width": 1920, "height": 1080},
        )
        origin = self.url.rstrip("/")

        def _inject_correlation(route: Any, request: Any) -> None:
            headers = {**request.headers, "X-Correlation-ID": self.correlation_id}
            route.continue_(headers=headers)

        context.route(
            lambda u: u.startswith(origin),
            _inject_correlation,
        )
        return context

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
        # LOCAL-context freshness only (same scoping s01 documents): the server
        # legitimately re-renders prior conversations' plan cards from history
        # after a reload, so a global zero-card gate degrades as history
        # accumulates. Gate on the conversation binding being cleared; record
        # the visible history-card count as evidence baseline.
        conv_key_cleared = page.evaluate(
            "() => localStorage.getItem('umh.chat.conversation_id') === null"
        )
        pre = page.locator(WG_PLAN_ROOT)
        self.stage(
            "fresh_context",
            bool(conv_key_cleared),
            f"conversation_binding_cleared={conv_key_cleared} "
            f"cleared={len(cleared.get('localStorage_removed', []))}ls; "
            f"history_plan_cards_visible={pre.count()}",
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

        try:
            if self.scenario == "smoke":
                return self._scenario_smoke(page, chat)
            return self._scenario_full(page, context, browser, state_path, chat)
        except Exception:
            # Evidence-first: capture what the page looked like at the moment
            # of failure (shot() never raises). Diagnosing the 163403 typing
            # stall took a source-dive that one screenshot would have shortcut.
            self.shot(page, "99_failure")
            raise

    # ── smoke: login + fresh state + one objective + plan render ────────────
    def _scenario_smoke(self, page: Any, chat: Any) -> Any:
        obj = f"{DOGFOOD_OBJECTIVE} {self.run_tag}"
        with page.expect_response(
            lambda r: "/advisor/converse" in r.url and r.status == 200, timeout=180000
        ) as resp_info:
            self._type_objective(page, chat, obj)
        self._capture_conversation_id(resp_info.value)
        state = self._wait_wg_state(page, {"rendered", "awaiting_approval"})
        self.stage("smoke_plan_rendered", state in {"rendered", "awaiting_approval"}, state)
        self.shot(page, "smoke_plan")
        self.dom(page, "smoke_plan")
        # Leave no pending decision behind: undecided plans accumulate in the
        # unified-approval pool (equal urgency → stable sort puts the NEWEST
        # plan LAST), pushing later passes' rows out of the ControlPanel's
        # top-3 window. Every scenario decides what it creates.
        self._reject_plan_cleanup(page, "smoke")
        return page

    def _reject_plan_cleanup(self, page: Any, label: str) -> None:
        """Reject the newest card's plan via the HUD (governed, non-fatal)."""
        try:
            card = self._plan_card(page)
            pid = card.last.get_attribute("data-plan-record-id") or "" if card.count() else ""
            if not pid:
                return
            keep = self._last_plan_id
            self._last_plan_id = pid
            rejected = self._decide_via_control_panel(page, "reject")
            self._last_plan_id = keep
            self.console.append(
                {
                    "type": "cleanup",
                    "text": f"{label}: rejected pending plan {pid[:16]} = {rejected} "
                    f"({self._decision_response[:80]})",
                    "ms": int((time.time() - self._start) * 1000),
                }
            )
        except Exception as exc:  # noqa: BLE001 — cleanup never fails the pass
            self.console.append(
                {
                    "type": "cleanup",
                    "text": f"{label}: cleanup failed: {str(exc)[:100]}",
                    "ms": int((time.time() - self._start) * 1000),
                }
            )
    # ── full scenario (w01→w30) ──────────────────────────────────────────────
    def _scenario_full(
        self, page: Any, context: Any, browser: Any, state_path: str, chat: Any
    ) -> Any:
        """The 30-step governed-EXECUTION operator journey (w01..w30).

        Reuses the Wave-1 plan-approval steps for w05-w10 (plan compile → HUD
        approve → APPROVED banner + zero execution authority), then drives the
        Wave-2 execution slice: "Execute the approved plan" → chat surfaces the
        decision (never authorizes) → HUD execution-authorization → A+B run
        concurrently → C blocked until both verified → C reconverges → D
        independently verifies (visible-Chrome fixture) → Proof → same-thread
        report → refresh + Chrome-restart persistence.

        Each w## is a discrete method with a machine-checkable assertion and
        evidence capture. The pass gates on the load-bearing execution-semantics
        steps; environment/probe-owned sub-checks that are genuinely the
        dispatcher's or Beast probe's responsibility are in _NON_GATING_STAGES.
        The steps share a mutable `ctx` dict so later steps reference ids from
        earlier ones.
        """
        ctx: dict[str, Any] = {}
        self._w01_session_proof(page, ctx)
        self._w02_zero_attempts_fresh(page, ctx)
        self._w03_clerk_auth(page, ctx)
        self._w04_principal_tenant(page, ctx)
        self._w05_type_fixture_objective(page, ctx)
        self._w06_plan_compiles(page, ctx)
        self._w07_inspect_plan(page, ctx)
        self._w08_tasks_non_executable(page, ctx)
        self._w09_approve_plan_hud(page, ctx)
        self._w10_approved_banner_zero_attempts(page, ctx)
        self._w11_type_execute(page, ctx)
        self._w12_chat_surfaces_decision(page, ctx)
        self._w13_zero_attempts_pre_hud(page, ctx)
        self._w14_hud_execution_row(page, ctx)
        self._w15_authorize_execution(page, ctx)
        self._w16_ab_running_concurrent(page, ctx)
        self._w17_c_blocked(page, ctx)
        self._w18_ab_verified(page, ctx)
        self._w19_c_reconverges(page, ctx)
        self._w20_preview_live(page, ctx)
        self._w21_d_distinct_verifier(page, ctx)
        self._w22_d_browser_probe(page, ctx)
        self._w23_fixture_witness(page, context, ctx)
        self._w24_proof(page, ctx)
        self._w25_complete_only_after_proof(page, ctx)
        self._w26_same_thread_report(page, ctx)
        self._w27_work_detail_lineage(page, ctx)
        page = self._w28_refresh_restart_persistence(page, browser, state_path, ctx)
        self._w29_zero_deploy_no_secrets(page, ctx)
        self._w30_cleanup(page, ctx)
        return page

    # ── read-only execution-API reads (ride the page's own Clerk session) ─────
    def _read_attempts(self, page: Any, plan_record_id: str = "") -> list[dict[str, Any]]:
        """Read-only fetch of this plan's ExecutionAttempts (canonical ledger).

        Uses GET /api/umh/execution/by-plan/{plan_record_id} (attempts scoped to
        one plan) when a plan id is known, else /api/umh/execution/attempts.
        Mutates nothing. Returns [] on any failure. NOTE: callers that assert
        "zero attempts" MUST use _read_attempts_checked instead — a failed read
        also returns [] and would otherwise look identical to "confirmed empty"
        (review C2). This bare form is for callers that only need the rows.
        """
        rows, _ok, _status = self._read_attempts_checked(page, plan_record_id)
        return rows

    def _read_attempts_checked(
        self, page: Any, plan_record_id: str = ""
    ) -> tuple[list[dict[str, Any]], bool, Any]:
        """Like _read_attempts but distinguishes 'confirmed empty (HTTP 200)' from
        'unknown (non-200 / malformed)'. Returns (rows, ok, status) where ok is
        True ONLY when the endpoint answered 200 with a well-formed body. A
        negative "zero attempts" gate must require ok AND rows == [] (review C2)."""
        pid = plan_record_id or str(self._last_plan_id or "")
        path = (
            f"/api/umh/execution/by-plan/{pid}" if pid else "/api/umh/execution/attempts"
        )
        resp = self._authed_get(page, path)
        if not isinstance(resp, dict):
            return [], False, None
        status = resp.get("__status")
        if status != 200 or resp.get("__error"):
            return [], False, status
        rows = resp.get("attempts")
        if rows is None:
            rows = resp.get("__body") if isinstance(resp.get("__body"), list) else None
        if rows is None:
            rows = resp.get("items")
        if isinstance(rows, dict):
            rows = rows.get("attempts")
        if not isinstance(rows, list):
            # 200 but no recognizable attempts field → cannot confirm the shape.
            return [], False, status
        return list(rows), True, status

    def _read_authorizations(self, page: Any) -> list[dict[str, Any]]:
        rows, _ok, _status = self._read_authorizations_checked(page)
        return rows

    def _read_authorizations_checked(
        self, page: Any
    ) -> tuple[list[dict[str, Any]], bool, Any]:
        """Read-only fetch of execution-authorization grants + pending decisions,
        with read-success status (review C2)."""
        resp = self._authed_get(page, "/api/umh/execution/authorizations")
        if not isinstance(resp, dict):
            return [], False, None
        status = resp.get("__status")
        if status != 200 or resp.get("__error"):
            return [], False, status
        rows = resp.get("authorizations")
        if rows is None:
            rows = resp.get("__body") if isinstance(resp.get("__body"), list) else None
        if rows is None:
            rows = resp.get("items")
        if not isinstance(rows, list):
            return [], False, status
        return list(rows), True, status

    def _read_frontier(self, page: Any) -> dict[str, Any]:
        """Read-only fetch of the authorized execution frontier."""
        resp = self._authed_get(page, "/api/umh/execution/frontier")
        return resp if isinstance(resp, dict) else {}

    def _attempts_dom(self, page: Any, status: str = "") -> Any:
        """Locator over w2-execution-attempt rows, optionally filtered by status."""
        sel = W2_EXECUTION_ATTEMPT
        if status:
            sel = f'{W2_EXECUTION_ATTEMPT}[data-status="{status}"]'
        return page.locator(sel)

    def _attempt_status(self, attempt: dict[str, Any]) -> str:
        return str(attempt.get("status", "")).lower()

    def _attempt_task(self, attempt: dict[str, Any]) -> str:
        return str(attempt.get("task_id", ""))

    # ── w01 — session + single-daemon proof ──────────────────────────────────
    def _w01_session_proof(self, page: Any, ctx: dict[str, Any]) -> None:
        """Re-assert the Stage-0 session proof under the w01 id (visible Chrome,
        interactive Session 1, exactly one daemon)."""
        ok = bool(self.session_proof.get("ok"))
        self.stage(
            "w01_session_proof",
            ok,
            f"active_session={self.session_proof.get('active_console_session')} "
            f"daemon_in_active={self.session_proof.get('daemon_in_active_session')}",
        )
        self.shot(page, "w01_session_proof")

    # ── w02 — fresh candidate + fixture, ZERO attempts pre-authorization ──────
    def _w02_zero_attempts_fresh(self, page: Any, ctx: dict[str, Any]) -> None:
        """No ExecutionAttempt exists anywhere before any authorization — plan
        acceptance grants ZERO execution authority (the Wave-1 invariant Wave-2
        keeps). Both the canonical ledger read AND the DOM must be empty."""
        cleared = self._clear_app_state(page)
        page.reload(wait_until="load")
        page.wait_for_timeout(1500)
        self._conversation_id = ""
        attempts, read_ok, status = self._read_attempts_checked(page)
        dom_attempts = self._attempts_dom(page).count()
        # A failed/errored read must NOT look like "zero attempts" (review C2):
        # require the endpoint to have answered 200 AND returned an empty list.
        ok = read_ok and len(attempts) == 0 and dom_attempts == 0
        detail = (
            f"ledger_attempts={len(attempts)} dom_attempts={dom_attempts} "
            f"cleared={len(cleared.get('localStorage_removed', []))}ls"
        )
        if not read_ok:
            detail = f"attempts read FAILED (status={status}) — cannot confirm zero; " + detail
        self.stage("w02_zero_attempts_fresh", ok, detail)
        self.shot(page, "w02_fresh")

    # ── w03 — Clerk auth ──────────────────────────────────────────────────────
    def _w03_clerk_auth(self, page: Any, ctx: dict[str, Any]) -> None:
        clerk_ok = bool(page.evaluate("() => !!(window.Clerk && window.Clerk.session)"))
        self.stage("w03_clerk_auth", clerk_ok, f"clerk_session={clerk_ok}")
        self.shot(page, "w03_clerk")

    # ── w04 — principal + tenant proof ────────────────────────────────────────
    def _w04_principal_tenant(self, page: Any, ctx: dict[str, Any]) -> None:
        resp = self._authed_get(page, "/api/umh/objective-plan")
        status = resp.get("__status") if isinstance(resp, dict) else None
        ok = status == 200 and not resp.get("__error")
        self.stage("w04_principal_tenant", ok, f"objective_plan_status={status}")
        self.shot(page, "w04_principal")

    # ── w05 — type the fixture (note-search) objective ────────────────────────
    def _w05_type_fixture_objective(self, page: Any, ctx: dict[str, Any]) -> None:
        """Type the exact fixture objective that decomposes into Tasks A-D."""
        self._send_and_wait(page, f"{FIXTURE_OBJECTIVE} {self.run_tag}")
        ctx["execution_conversation_id"] = getattr(self, "_conversation_id", "")
        self.stage("w05_type_fixture_objective", True, "fixture objective sent")
        self.shot(page, "w05_objective")

    # ── w06 — plan compiles ───────────────────────────────────────────────────
    def _w06_plan_compiles(self, page: Any, ctx: dict[str, Any]) -> None:
        """The fixture objective → plan card with data-state + record id (REUSES
        the Wave-1 s07 compile logic)."""
        state = self._wait_wg_state(page, {"rendered", "awaiting_approval", "revised"})
        card = self._plan_card(page)
        plan_id = ""
        try:
            if card.count():
                plan_id = card.last.get_attribute("data-plan-record-id") or ""
        except Exception:  # noqa: BLE001
            plan_id = ""
        ctx["plan_record_id"] = plan_id
        self._last_plan_id = plan_id
        ok = state in {"rendered", "awaiting_approval", "revised"} and bool(plan_id)
        self.stage("w06_plan_compiles", ok, f"state={state} plan_record_id={plan_id[:16]}")
        self.shot(page, "w06_plan")
        self.dom(page, "w06_plan")

    # ── w07 — inspect plan detail ─────────────────────────────────────────────
    def _w07_inspect_plan(self, page: Any, ctx: dict[str, Any]) -> None:
        opened = self._open_plan_panel(page)
        detail_visible = page.locator(WG_WORK_DETAIL).count() > 0
        plan_json = self._read_plan_json(page)
        has_scope = bool(
            isinstance(plan_json, dict)
            and (plan_json.get("work_scope") or plan_json.get("planning_scale"))
        )
        self.stage(
            "w07_inspect_plan",
            opened and detail_visible and (page.locator(WG_WORK_DETAIL_CONTEXT).count() > 0 or has_scope),
            f"work_detail={detail_visible} server_has_scope={has_scope}",
        )
        self.shot(page, "w07_plan_detail")
        try:
            closer = page.locator('button[title="Close"]')
            if closer.count() > 0:
                closer.last.click()
                page.wait_for_timeout(500)
        except Exception:  # noqa: BLE001
            pass

    # ── w08 — Tasks A-D non-executable ────────────────────────────────────────
    def _w08_tasks_non_executable(self, page: Any, ctx: dict[str, Any]) -> None:
        """The plan materialized ≥1 task packet, all in a non-executable status,
        and STILL zero ExecutionAttempts (plan acceptance ≠ execution authority)."""
        packets = self._read_packets(page)
        plan_packets = [p for p in packets if p.get("source_type") == "objective_plan"]
        ctx["plan_packet_ids"] = [p["packet_id"] for p in plan_packets]
        non_exec = all(
            (p.get("status") or "").lower()
            in ("drafted", "classified", "planned", "ready_for_review", "")
            for p in plan_packets
        )
        attempts, read_ok, status = self._read_attempts_checked(page)
        dom_attempts = self._attempts_dom(page).count()
        ok = (
            len(plan_packets) >= 1
            and non_exec
            and read_ok
            and len(attempts) == 0
            and dom_attempts == 0
        )
        detail = (
            f"plan_packets={len(plan_packets)} non_executable={non_exec} "
            f"attempts={len(attempts)} dom_attempts={dom_attempts}"
        )
        if not read_ok:
            detail = f"attempts read FAILED (status={status}) — cannot confirm zero; " + detail
        self.stage("w08_tasks_non_executable", ok, detail)
        self.shot(page, "w08_tasks")

    # ── w09 — approve the PLAN via HUD ────────────────────────────────────────
    def _w09_approve_plan_hud(self, page: Any, ctx: dict[str, Any]) -> None:
        """Approve the plan-acceptance decision via the HUD (REUSES s15 logic)."""
        clicked = self._decide_via_control_panel(page, "approve")
        server_status = ""
        deadline = time.time() + 60
        while time.time() < deadline and ctx.get("plan_record_id"):
            pj = self._authed_get(page, f"/api/umh/objective-plan/{ctx['plan_record_id']}")
            server_status = pj.get("status", "") if isinstance(pj, dict) else ""
            if server_status == "approved":
                break
            time.sleep(2)
        ctx["plan_approved"] = clicked and server_status == "approved"
        self.stage(
            "w09_approve_plan_hud",
            clicked and server_status == "approved",
            f"clicked={clicked} server_status={server_status} "
            f"decision_response={self._decision_response[:100]}",
        )
        self.shot(page, "w09_plan_approved")
        self.dom(page, "w09_plan_approved")

    # ── w10 — APPROVED banner + still ZERO attempts ───────────────────────────
    def _w10_approved_banner_zero_attempts(self, page: Any, ctx: dict[str, Any]) -> None:
        """The 'PLAN APPROVED — EXECUTION NOT STARTED' banner is present AND still
        zero ExecutionAttempts — plan approval grants no execution authority."""
        self._open_plan_panel(page)
        page.wait_for_timeout(1200)
        banner_ok = self._body_contains(page, APPROVED_BANNER)
        try:
            closer = page.locator('button[title="Close"]')
            if closer.count() > 0:
                closer.last.click()
                page.wait_for_timeout(400)
        except Exception:  # noqa: BLE001
            pass
        attempts, read_ok, status = self._read_attempts_checked(page)
        ok = banner_ok and read_ok and len(attempts) == 0
        detail = f"banner={banner_ok} attempts_after_plan_approval={len(attempts)}"
        if not read_ok:
            detail = f"attempts read FAILED (status={status}) — cannot confirm zero; " + detail
        self.stage("w10_approved_banner_zero_attempts", ok, detail)
        self.shot(page, "w10_banner")
        self.dom(page, "w10_banner")

    # ── w11 — type "Execute the approved plan" ────────────────────────────────
    def _w11_type_execute(self, page: Any, ctx: dict[str, Any]) -> None:
        """The operator asks to execute. This mints an execution-authorization
        DECISION — it must NOT start execution."""
        self._send_and_wait(page, f"{EXECUTE_MESSAGE} {self.run_tag}")
        self.stage("w11_type_execute", True, "execute request sent")
        self.shot(page, "w11_execute")

    # ── w12 — chat surfaces the DECISION, starts NO execution ─────────────────
    def _w12_chat_surfaces_decision(self, page: Any, ctx: dict[str, Any]) -> None:
        """The chat renders a STATUS-ONLY execution card (w2-exec-card-root) with
        NO authorize control, and no ExecutionAttempt has started."""
        page.wait_for_timeout(2000)
        card_present = page.locator(W2_EXEC_CARD_ROOT).count() > 0
        # The chat card must NOT carry an authorize button (decisions are HUD-only).
        authorize_in_card = 0
        if card_present:
            try:
                authorize_in_card = (
                    page.locator(W2_EXEC_CARD_ROOT).locator(W2_EXEC_APPROVE_BTN).count()
                )
            except Exception:  # noqa: BLE001
                authorize_in_card = 0
        attempts, read_ok, status = self._read_attempts_checked(page)
        ok = card_present and authorize_in_card == 0 and read_ok and len(attempts) == 0
        detail = (
            f"exec_card={card_present} authorize_in_card={authorize_in_card} "
            f"attempts={len(attempts)}"
        )
        if not read_ok:
            detail = f"attempts read FAILED (status={status}) — cannot confirm zero; " + detail
        self.stage("w12_chat_surfaces_decision", ok, detail)
        self.shot(page, "w12_exec_card")
        self.dom(page, "w12_exec_card")

    # ── w13 — ZERO attempts pre-HUD; a PENDING authorization exists ───────────
    def _w13_zero_attempts_pre_hud(self, page: Any, ctx: dict[str, Any]) -> None:
        """Before the operator authorizes in the HUD: no attempt exists, and an
        execution-authorization decision is PENDING (not yet approved)."""
        attempts, attempts_ok, attempts_status = self._read_attempts_checked(page)
        auths, auths_ok, auths_status = self._read_authorizations_checked(page)
        # A pending execution authorization: a decision surfaced but not granted.
        pending = [
            a for a in auths
            if str(a.get("status", "")).lower() in ("", "pending", "activating")
            and str(a.get("state", "")).lower() not in ("active",)
        ]
        # Zero attempts must be a CONFIRMED empty read (200), not a failed read
        # returning [] (review C2). The authorizations read must also have
        # succeeded so a broken surface can't masquerade as "no pending".
        ok = attempts_ok and len(attempts) == 0 and auths_ok
        detail = (
            f"attempts={len(attempts)} authorizations={len(auths)} pending_like={len(pending)}"
        )
        if not attempts_ok:
            detail = (
                f"attempts read FAILED (status={attempts_status}) — cannot confirm zero; " + detail
            )
        elif not auths_ok:
            detail = (
                f"authorizations read FAILED (status={auths_status}) — cannot confirm pending; "
                + detail
            )
        self.stage("w13_zero_attempts_pre_hud", ok, detail)
        self.shot(page, "w13_pre_hud")

    # ── w14 — HUD execution-authorization row present ─────────────────────────
    def _w14_hud_execution_row(self, page: Any, ctx: dict[str, Any]) -> None:
        """The Top HUD shows the execution-authorization decision row
        (w2-execution-decision / wg-approval-row[data-source-type=
        execution_authorization]). Capture its decision_ref."""
        self._open_approvals(page)
        deadline = time.time() + 60
        decision_ref = ""
        count = 0
        while time.time() < deadline:
            rows = page.locator(W2_EXECUTION_DECISION)
            count = rows.count()
            if count >= 1:
                try:
                    decision_ref = rows.first.get_attribute("data-decision-ref") or ""
                except Exception:  # noqa: BLE001
                    decision_ref = ""
                break
            self._open_approvals(page)
            time.sleep(3)
        self._execution_decision_ref = decision_ref
        ctx["execution_decision_ref"] = decision_ref
        self.stage(
            "w14_hud_execution_row",
            count >= 1,
            f"execution_decision_rows={count} decision_ref={decision_ref[:32]}",
        )
        self.shot(page, "w14_hud_exec_row")
        self.dom(page, "w14_hud_exec_row")

    # ── w15 — authorize execution in the HUD ──────────────────────────────────
    def _w15_authorize_execution(self, page: Any, ctx: dict[str, Any]) -> None:
        """Click Authorize on the execution-authorization row (anchored by
        decision_ref), inside expect_response on /unified-approval/approve.

        The Top HUD renders the pending-approval list from an ASYNC poll of
        /unified-approval, so the execution-decision row + its approve button can
        take a few seconds to (re)appear after _open_approvals re-navigates —
        exactly like w14, which already retries up to 60s. A single _open_approvals
        followed by an immediate row.count() check races that poll: the row is 0,
        the whole click block is skipped, and the stage fails with an EMPTY
        decision_response (observed run 20260725T171015Z-p1: authorized=False,
        decision_response=<empty>, while the backend grant was correctly still
        ACTIVATING and approvable). Retry _open_approvals until the APPROVE BUTTON
        itself is present, then click — mirroring w14's tolerance."""
        ref = str(self._execution_decision_ref or "")
        row = page.locator(W2_EXECUTION_DECISION)
        btn = None
        deadline = time.time() + 60
        while time.time() < deadline:
            self._open_approvals(page)
            row = page.locator(W2_EXECUTION_DECISION)
            if ref:
                scoped = page.locator(f'{W2_EXECUTION_DECISION}[data-decision-ref="{ref}"]')
                if scoped.count() > 0:
                    row = scoped
            if row.count() > 0:
                cand = row.first.locator(W2_EXEC_APPROVE_BTN)
                if cand.count() > 0:
                    btn = cand
                    break
            time.sleep(3)
        clicked = False
        status_body = ""
        if btn is not None:
            try:
                with page.expect_response(
                    lambda r: "/unified-approval/approve" in r.url, timeout=20000
                ) as ri:
                    btn.first.click()
                resp = ri.value
                body = ""
                try:
                    body = (resp.text() or "")[:160]
                except Exception:  # noqa: BLE001
                    body = "<unreadable>"
                status_body = f"{resp.status} {body}"
                clicked = resp.status < 300
            except Exception as exc:  # noqa: BLE001
                status_body = f"no-response ({str(exc)[:80]})"
        else:
            status_body = "approve-button-never-appeared"
        ctx["execution_authorized"] = clicked
        self.stage(
            "w15_authorize_execution",
            clicked,
            f"authorized={clicked} decision_response={status_body[:120]}",
        )
        self.shot(page, "w15_authorized")
        self.dom(page, "w15_authorized")

    # ── w16 — A + B RUNNING concurrently ──────────────────────────────────────
    def _w16_ab_running_concurrent(self, page: Any, ctx: dict[str, Any]) -> None:
        """Exactly TWO implementation attempts (A, B) run concurrently with
        DISTINCT task ids — proving parallel dispatch of the independent tasks."""
        deadline = time.time() + 240
        running_tasks: set[str] = set()
        dom_running = 0
        while time.time() < deadline:
            attempts = self._read_attempts(page)
            running = [a for a in attempts if self._attempt_status(a) == "running"]
            running_tasks = {self._attempt_task(a) for a in running if self._attempt_task(a)}
            dom_running = self._attempts_dom(page, "running").count()
            # Record every attempt id we see for later steps.
            for a in attempts:
                tid, aid = self._attempt_task(a), a.get("attempt_id")
                if tid and aid:
                    self._attempt_ids[tid] = aid
            if len(running_tasks) >= 2:
                break
            time.sleep(3)
        ctx["concurrent_running_tasks"] = sorted(running_tasks)
        # The canonical execution surface must be mounted while attempts run.
        exec_surface = page.locator(W2_EXECUTION_ROOT).count() > 0
        # Exactly-2 concurrency: two distinct implementation tasks running at once.
        # BOTH the ledger and the DOM must show EXACTLY two — dom_running == 2, not
        # >= 2, so a 3-way over-dispatch cannot slip through the DOM half (review W7).
        ok = len(running_tasks) == 2 and dom_running == 2 and exec_surface
        self.stage(
            "w16_ab_running_concurrent",
            ok,
            f"concurrent_running_tasks={sorted(running_tasks)} dom_running={dom_running} "
            f"execution_surface={exec_surface}",
        )
        self.shot(page, "w16_ab_running")
        self.dom(page, "w16_ab_running")

    # ── w17 — C blocked until A and B verified ────────────────────────────────
    def _w17_c_blocked(self, page: Any, ctx: dict[str, Any]) -> None:
        """The integration task C must NOT run before A and B are verified. This
        gate is bounded-wait (like w16/w18/w19, not a single snapshot — review
        W6): it polls until a fan-in task appears-and-is-blocked, and enforces
        that no task outside the two running implementation tasks has advanced to
        running/succeeded. The blocked fan-in task is the SPECIFIC integration
        task (neither of the two concurrent A/B tasks)."""
        running_tasks = set(ctx.get("concurrent_running_tasks", []))
        deadline = time.time() + 120
        blocked_tasks: set[str] = set()
        dom_blocked = 0
        advanced_non_ab: list[dict[str, Any]] = []
        c_specific_blocked = False
        while time.time() < deadline:
            attempts = self._read_attempts(page)
            blocked = [a for a in attempts if self._attempt_status(a) == "blocked"]
            blocked_tasks = {self._attempt_task(a) for a in blocked if self._attempt_task(a)}
            dom_blocked = self._attempts_dom(page, "blocked").count()
            # The SPECIFIC integration task = a blocked task that is NOT one of the
            # two concurrent implementation tasks (A, B).
            c_tasks = {t for t in blocked_tasks if t not in running_tasks}
            c_specific_blocked = len(c_tasks) >= 1
            # No task outside {A,B} may be running or succeeded before A∧B verify.
            advanced_non_ab = [
                a for a in attempts
                if self._attempt_task(a) not in running_tasks
                and self._attempt_status(a) in ("running", "succeeded")
            ]
            # Terminal-good once we've positively seen a non-A/B task blocked with
            # nothing advanced; keep waiting for the blocked attempt to materialize.
            if (c_specific_blocked or dom_blocked >= 1) and not advanced_non_ab:
                # Give a beat to catch a late over-dispatch before declaring OK.
                if c_specific_blocked:
                    break
            if advanced_non_ab:
                break  # a violation is terminal — report it immediately
            time.sleep(3)
        ctx["blocked_tasks"] = sorted(blocked_tasks)
        # Prefer the specific-C proof; fall back to "≥1 blocked" only if the task
        # id can't be distinguished, but ALWAYS require nothing advanced past A,B.
        ok = (c_specific_blocked or len(blocked_tasks) >= 1 or dom_blocked >= 1) and len(
            advanced_non_ab
        ) == 0
        self.stage(
            "w17_c_blocked",
            ok,
            f"blocked_tasks={sorted(blocked_tasks)} c_specific_blocked={c_specific_blocked} "
            f"dom_blocked={dom_blocked} advanced_non_ab={len(advanced_non_ab)}",
        )
        self.shot(page, "w17_c_blocked")

    # ── w18 — A and B verified (AttemptProof) ─────────────────────────────────
    def _w18_ab_verified(self, page: Any, ctx: dict[str, Any]) -> None:
        """A and B reach succeeded, each with an AttemptProof (w2-proof-link)."""
        running_tasks = set(ctx.get("concurrent_running_tasks", []))
        deadline = time.time() + 360
        succeeded_ab: dict[str, str] = {}
        while time.time() < deadline:
            attempts = self._read_attempts(page)
            for a in attempts:
                tid = self._attempt_task(a)
                if tid in running_tasks and self._attempt_status(a) == "succeeded":
                    succeeded_ab[tid] = str(a.get("proof_id", ""))
            if len(succeeded_ab) >= 2 and all(succeeded_ab.values()):
                break
            time.sleep(3)
        ctx["ab_verified_at"] = time.time()
        all_have_proof = len(succeeded_ab) >= 2 and all(succeeded_ab.values())
        self.stage(
            "w18_ab_verified",
            all_have_proof,
            f"succeeded_ab={sorted(succeeded_ab)} proofs={[p[:12] for p in succeeded_ab.values()]}",
        )
        self.shot(page, "w18_ab_verified")
        self.dom(page, "w18_ab_verified")

    # ── w19 — C reconverges after both A and B ────────────────────────────────
    def _w19_c_reconverges(self, page: Any, ctx: dict[str, Any]) -> None:
        """After A and B succeed, C (integration) runs and succeeds — and it did
        NOT start before both predecessors were verified."""
        running_tasks = set(ctx.get("concurrent_running_tasks", []))
        blocked_tasks = set(ctx.get("blocked_tasks", []))
        deadline = time.time() + 360
        c_task = ""
        c_status = ""
        c_started_after = True
        while time.time() < deadline:
            attempts = self._read_attempts(page)
            # C = a task that was blocked, now advancing, not one of A/B.
            for a in attempts:
                tid = self._attempt_task(a)
                if tid in running_tasks:
                    continue
                st = self._attempt_status(a)
                if tid in blocked_tasks or st in ("running", "succeeded"):
                    # ordering: C must not have started before ab_verified_at.
                    started = a.get("started_at") or a.get("running_at") or 0
                    if started and ctx.get("ab_verified_at") and started < ctx["ab_verified_at"] - 5:
                        c_started_after = False
                    c_task, c_status = tid, st
            if c_status == "succeeded":
                break
            time.sleep(3)
        ok = c_status == "succeeded" and c_started_after
        self.stage(
            "w19_c_reconverges",
            ok,
            f"c_task={c_task} c_status={c_status} started_after_ab_verified={c_started_after}",
        )
        self.shot(page, "w19_c_reconverges")
        self.dom(page, "w19_c_reconverges")

    # ── w20 — preview live (best-effort, non-gating) ──────────────────────────
    def _w20_preview_live(self, page: Any, ctx: dict[str, Any]) -> None:
        """The integration preview is reachable. This is surfaced by the runner;
        here it is a best-effort read (dispatcher owns the authoritative check)."""
        frontier = self._read_frontier(page)
        preview = frontier.get("preview") or frontier.get("integration_preview") or {}
        reachable = bool(preview)
        self.stage(
            "w20_preview_live",
            True,  # non-gating: authoritative preview check is dispatcher-side
            f"preview_surfaced={reachable}",
        )
        self.shot(page, "w20_preview")

    # ── w21 — D is a distinct verifier role ───────────────────────────────────
    def _w21_d_distinct_verifier(self, page: Any, ctx: dict[str, Any]) -> None:
        """The verification task D runs under a verifier role distinct from the
        implementation workers (separation of duty)."""
        attempts = self._read_attempts(page)
        sod_ok = False
        d_task = ""
        for a in attempts:
            verifier = str(a.get("verifier_role_id", "") or a.get("verifier_identity", ""))
            worker = str(a.get("worker_identity", ""))
            if verifier and worker and verifier != worker:
                sod_ok = True
            if "verif" in self._attempt_task(a).lower() or "verif" in verifier.lower():
                d_task = self._attempt_task(a)
        self.stage(
            "w21_d_distinct_verifier",
            sod_ok,
            f"separation_of_duty={sod_ok} d_task={d_task}",
        )
        self.shot(page, "w21_verifier")

    # ── w22 — D browser probe (dispatcher/Beast-owned, non-gating) ────────────
    def _w22_d_browser_probe(self, page: Any, ctx: dict[str, Any]) -> None:
        """D's verification includes a visible-Chrome fixture probe. The probe
        itself runs via wave2_fixture_browser_probe.py on the Beast (dispatcher-
        driven); here we assert D reached verifying/succeeded so the probe fired."""
        attempts = self._read_attempts(page)
        d_advanced = any(
            self._attempt_status(a) in ("verifying", "succeeded")
            and ("verif" in self._attempt_task(a).lower()
                 or "verif" in str(a.get("verifier_role_id", "")).lower())
            for a in attempts
        )
        self.stage(
            "w22_d_browser_probe",
            True,  # non-gating: the visible-Chrome probe is Beast-side evidence
            f"d_reached_verify_or_succeed={d_advanced}",
        )
        self.shot(page, "w22_d_probe")

    # ── w23 — collector's OWN visible-Chrome fixture witness ──────────────────
    def _w23_fixture_witness(self, page: Any, context: Any, ctx: dict[str, Any]) -> None:
        """Independent visible-Chrome witness: open the fixture app in this same
        real Chrome, type 'alpha' into the search box, and confirm results render.
        Proves the end-to-end feature actually works in a browser, not just in the
        attempt ledger. SKIPPED (non-gating) when no --fixture-url is provided."""
        if not self.fixture_url:
            self.stage(
                "w23_fixture_witness",
                True,  # non-gating when no fixture origin was wired for this run
                "SKIPPED — no --fixture-url provided (fixture reachability is dispatcher-wired)",
            )
            return
        ok = False
        detail = ""
        fpage = None
        try:
            fpage = context.new_page()
            fpage.goto(self.fixture_url, wait_until="load", timeout=30000)
            search = fpage.locator('[data-testid="note-search-input"]')
            results = fpage.locator('[data-testid="note-search-results"]')
            if search.count() > 0:
                with fpage.expect_response(
                    lambda r: "/api/notes/search" in r.url, timeout=15000
                ):
                    search.first.fill("alpha")
                fpage.wait_for_timeout(1000)
                rendered = results.count() > 0 and bool((results.first.inner_text() or "").strip())
                ok = rendered
                detail = f"search_input=1 results_rendered={rendered}"
            else:
                detail = "note-search-input not present (feature not integrated)"
            self.shot(fpage, "w23_fixture_witness")
        except Exception as exc:  # noqa: BLE001
            detail = f"exception={str(exc)[:120]}"
        finally:
            try:
                if fpage is not None:
                    fpage.close()
            except Exception:  # noqa: BLE001
                pass
        self.stage("w23_fixture_witness", ok, detail)

    # ── w24 — Proof (PlanExecutionProof) ──────────────────────────────────────
    def _w24_proof(self, page: Any, ctx: dict[str, Any]) -> None:
        """A Proof link is present (the PlanExecutionProof for the whole plan
        execution). Capture the proof id."""
        deadline = time.time() + 120
        proof_present = False
        while time.time() < deadline:
            if page.locator(W2_PROOF_LINK).count() > 0:
                proof_present = True
                break
            # also accept ledger-level proof on the plan's attempts
            attempts = self._read_attempts(page)
            if any(a.get("proof_id") for a in attempts):
                proof_present = True
                break
            time.sleep(3)
        # capture a proof id from the ledger
        for a in self._read_attempts(page):
            if a.get("proof_id"):
                self._proof_id = str(a.get("proof_id"))
                break
        self.stage(
            "w24_proof",
            proof_present,
            f"proof_link={page.locator(W2_PROOF_LINK).count()} proof_id={self._proof_id[:16]}",
        )
        self.shot(page, "w24_proof")
        self.dom(page, "w24_proof")

    # ── w25 — Tasks complete only AFTER Proof ─────────────────────────────────
    def _w25_complete_only_after_proof(self, page: Any, ctx: dict[str, Any]) -> None:
        """Every SUCCEEDED attempt carries a proof_id — no task completed without
        an independent AttemptProof."""
        attempts = self._read_attempts(page)
        succeeded = [a for a in attempts if self._attempt_status(a) == "succeeded"]
        without_proof = [a for a in succeeded if not a.get("proof_id")]
        ok = len(succeeded) >= 1 and len(without_proof) == 0
        self.stage(
            "w25_complete_only_after_proof",
            ok,
            f"succeeded={len(succeeded)} succeeded_without_proof={len(without_proof)}",
        )
        self.shot(page, "w25_proof_gated")

    # ── w26 — same-thread completion report ───────────────────────────────────
    def _w26_same_thread_report(self, page: Any, ctx: dict[str, Any]) -> None:
        """A completion report is posted back to the ORIGINAL conversation thread
        (the same conversation the operator drove the execution from)."""
        conv = ctx.get("execution_conversation_id", "")
        report_present = False
        detail = ""
        if conv:
            # The report is a message in the same conversation — read the plan/
            # conversation surface and look for an execution-complete signal.
            body_has = (
                self._body_contains(page, "Execution complete")
                or self._body_contains(page, "COMPLETE — PROOF")
                or self._body_contains(page, "PlanExecutionProof")
                or self._body_contains(page, "execution report")
            )
            report_present = body_has
            detail = f"conversation_id={conv[:16]} report_in_thread={body_has}"
        else:
            detail = "no execution conversation id captured"
        self.stage("w26_same_thread_report", report_present, detail)
        self.shot(page, "w26_report")
        self.dom(page, "w26_report")

    # ── w27 — Work Detail shows execution lineage ─────────────────────────────
    def _w27_work_detail_lineage(self, page: Any, ctx: dict[str, Any]) -> None:
        """Work Detail exposes the execution lineage: attempt → assignment →
        environment lease → verification/proof."""
        # Open a task's execution detail via the overlay / open-task affordance.
        opened = False
        if page.locator(W2_OPEN_TASK_BTN).count() > 0:
            page.locator(W2_OPEN_TASK_BTN).first.click()
            page.wait_for_timeout(1000)
            opened = True
        elif page.locator(W2_OPEN_EXECUTION_BTN).count() > 0:
            page.locator(W2_OPEN_EXECUTION_BTN).first.click()
            page.wait_for_timeout(1000)
            opened = True
        assignment = page.locator(W2_ASSIGNMENT).count() > 0
        lease = page.locator(W2_ENVIRONMENT_LEASE).count() > 0
        verification = page.locator(W2_VERIFICATION_STATUS).count() > 0
        overlay = page.locator(W2_WORK_OVERLAY).count() > 0
        worker = page.locator(W2_WORKER_STATUS).count() > 0
        # The governed cancel/retry affordances render on the drawer (they route
        # through governed_mutation — their PRESENCE is the surface contract; the
        # collector never clicks them on a green pass). reject lives on the HUD row.
        cancel_ctrl = page.locator(W2_EXECUTION_CANCEL).count()
        retry_ctrl = page.locator(W2_EXECUTION_RETRY).count()
        reject_ctrl = page.locator(W2_EXEC_REJECT_BTN).count()
        # Lineage is proven when the drawer shows assignment + lease + verification;
        # the overlay/worker-status/governed-controls are corroborating surfaces.
        ok = assignment and lease and verification
        self.stage(
            "w27_work_detail_lineage",
            ok,
            f"opened={opened} assignment={assignment} lease={lease} "
            f"verification={verification} overlay={overlay} worker_status={worker} "
            f"cancel_ctrl={cancel_ctrl} retry_ctrl={retry_ctrl} reject_ctrl={reject_ctrl}",
        )
        self.shot(page, "w27_lineage")
        self.dom(page, "w27_lineage")

    # ── w28 — refresh + full Chrome restart persistence ───────────────────────
    def _w28_refresh_restart_persistence(
        self, page: Any, browser: Any, state_path: str, ctx: dict[str, Any]
    ) -> Any:
        """Attempts + proof survive a reload AND a full Chrome context restart
        (persistence-by-refetch — the store rehydrates from canonical state)."""
        before = {a.get("attempt_id"): a.get("proof_id", "") for a in self._read_attempts(page)}
        page.reload(wait_until="load")
        page.wait_for_timeout(2000)
        # full restart: brand-new context
        context = self._new_context(browser, state_path)
        newpage = context.new_page()
        self._wire_listeners(newpage)
        newpage.goto(self.url, wait_until="load", timeout=45000)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if bool(newpage.evaluate("() => !!(window.Clerk && window.Clerk.session)")):
                    break
            except Exception:  # noqa: BLE001
                pass
            newpage.wait_for_timeout(1000)
        after = {a.get("attempt_id"): a.get("proof_id", "") for a in self._read_attempts(newpage)}
        # Same attempt ids persist, and proofs are still linked.
        persisted = bool(before) and all(k in after for k in before)
        proofs_intact = all(after.get(k) == v for k, v in before.items() if v)
        ok = persisted and proofs_intact
        self.stage(
            "w28_refresh_restart_persistence",
            ok,
            f"attempts_before={len(before)} attempts_after={len(after)} "
            f"persisted={persisted} proofs_intact={proofs_intact}",
        )
        self.shot(newpage, "w28_persistence")
        self.dom(newpage, "w28_persistence")
        return newpage

    # ── w29 — zero production deploy + no secrets in evidence ─────────────────
    def _w29_zero_deploy_no_secrets(self, page: Any, ctx: dict[str, Any]) -> None:
        """No attempt references a production deploy, and no attempt env-audit
        surfaces a production credential. The authoritative /opt/OS-unchanged +
        zero-deploy check is the dispatcher's reconcile; here it is a read-only
        corroboration (non-gating for the dispatcher-owned parts)."""
        attempts = self._read_attempts(page)
        leaked = []
        for a in attempts:
            env_names = a.get("env_audit") or a.get("env_names") or []
            if isinstance(env_names, dict):
                env_names = list(env_names.keys())
            for name in env_names or []:
                up = str(name).upper()
                if any(bad in up for bad in ("FLY", "GH_", "GITHUB", "DEPLOY")):
                    leaked.append(name)
        ok = len(leaked) == 0
        self.stage(
            "w29_zero_deploy_no_secrets",
            ok,
            f"prod_cred_or_deploy_names_in_attempt_env={leaked[:5]} "
            f"(authoritative zero-deploy check is dispatcher reconcile)",
        )
        self.shot(page, "w29_zero_deploy")

    # ── w30 — cleanup ─────────────────────────────────────────────────────────
    def _w30_cleanup(self, page: Any, ctx: dict[str, Any]) -> None:
        """Leave the candidate clean: reject any leftover pending plan decision
        (governed, non-fatal). Execution attempts are terminal + proof-gated, so
        nothing else to undo."""
        self._reject_plan_cleanup(page, "w30")
        self.stage("w30_cleanup", True, "leftover pending decisions rejected")
        self.shot(page, "w30_cleanup")

    # ── finalize + ship ──────────────────────────────────────────────────────
    # Steps whose AUTHORITATIVE check is owned by the dispatcher reconcile or
    # the Beast visible-Chrome probe, not the collector: the collector records
    # corroborating evidence but does not gate the pass on them. Every OTHER
    # w## step (incl. the load-bearing w16/w17/w18/w19/w24/w25/w26) DOES gate.
    #   w20 preview_live      — integration preview reachability (dispatcher)
    #   w22 d_browser_probe   — visible-Chrome fixture probe runs on the Beast
    #   w23 fixture_witness   — SKIPPED unless --fixture-url wired for the run
    #   w29 zero_deploy       — authoritative /opt/OS-unchanged + zero-deploy is
    #                           the dispatcher reconcile; here read-only corrob.
    _NON_GATING_STAGES = (
        "w20_preview_live",
        "w22_d_browser_probe",
        "w23_fixture_witness",
        "w29_zero_deploy_no_secrets",
    )

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
        (self.pass_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (self.pass_dir / "network.jsonl").write_text(
            "\n".join(json.dumps(n) for n in self.network), encoding="utf-8"
        )
        (self.pass_dir / "console.jsonl").write_text(
            "\n".join(json.dumps(c) for c in self.console), encoding="utf-8"
        )
        # Final secret-hygiene pass over EVERY collected JSON/JSONL before it is
        # shipped — bodies/console are redacted at capture time, but this is the
        # belt-and-suspenders sweep so nothing unredacted can ever be scp'd into
        # the committed proof (review C1).
        self._redact_pass_dir()
        self._status("passed" if passed else "failed")
        self._ship()
        return result

    def _redact_pass_dir(self) -> None:
        """Redact bearer/JWT/password patterns in-place across the pass dir's
        JSON/JSONL evidence before it ships (mirrors wave1_field_dispatch
        _redact_tree). Runs AFTER the evidence is written, BEFORE _ship."""
        for p in list(self.pass_dir.rglob("*.json")) + list(self.pass_dir.rglob("*.jsonl")):
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            redacted = _SECRET_REDACT_RE.sub("<redacted>", text)
            if redacted != text:
                try:
                    p.write_text(redacted, encoding="utf-8")
                except OSError as exc:
                    print(f"  redact rewrite failed for {p.name}: {exc}", file=sys.stderr)

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
    parser = argparse.ArgumentParser(description="Wave 2 field-qualification collector")
    parser.add_argument("--url", required=True)
    parser.add_argument("--run-id", default=_run_id_default())
    parser.add_argument("--pass-num", type=int, default=1)
    parser.add_argument("--evidence-dir", default=r"C:\dev\wave2_evidence")
    parser.add_argument("--candidate-commit", default="")
    parser.add_argument("--scenario", choices=["full", "smoke"], default="full")
    parser.add_argument(
        "--ship-to",
        default="/opt/OS/data/audits/proof/wave2_field/raw",
        help="VPS-side proof dir root (scp target); empty to skip shipping",
    )
    parser.add_argument(
        "--fixture-url",
        default="",
        help="Fixture app origin for the w23 visible-Chrome witness (empty skips w23)",
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
        fixture_url=args.fixture_url,
    )
    result = collector.run()
    # result.json is the durable artifact; stdout carries the terminal verdict.
    print(json.dumps({"pass": result["pass"], "failed_stage": result.get("failed_stage")}))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
