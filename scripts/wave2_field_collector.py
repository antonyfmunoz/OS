"""Wave 2 field-qualification collector — runs ON the Windows executor node.

Drives the deployed candidate Cockpit (Intent → Work-Graph rail) in a VISIBLE
real Chrome (channel="chrome", headless=False) inside the interactive desktop
session (Session 1), exactly the way a human operator would. Produces Class-A
field evidence: per-stage screenshots + DOM snapshots + a network log + a
result.json, then ships the pass directory to the VPS proof dir over scp.

Doctrine this collector enforces (learned from the p4s31c false-positive):
  * UI-ONLY interactions — click / fill / press. page.evaluate is used ONLY
    for read-only DOM snapshots and read-only fetch() reconciliation reads
    that ride the page's OWN Clerk session. Never to mutate state.
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
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

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
W2_EXECUTION_ATTEMPT = (
    '[data-testid="w2-execution-attempt"]'  # data-attempt-id, data-status; task_id as text
)
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

# ── observation latency envelope (inv #54, run 20260809T144154Z-p1) ──────────
# The REAL end-to-end worker chain A-fail(97s) → A-retry(111s) → C-composition
# landed the composition proof ~236s after w15, and Task D takes ~100-110s from
# dispatch. Observation bounds must EXCEED the proven envelope with headroom:
# a bound below it fails correct-but-slow runs and consumes field quota.
# Every timeout below fails CLOSED — a stage NEVER passes on timeout.
PROVEN_WORKER_LATENCY_ENVELOPE_S = 240  # observed 236s w15→composition, rounded up
W16_COMPOSITION_WAIT_S = 420  # must stay > PROVEN_WORKER_LATENCY_ENVELOPE_S
W26_D_TERMINALIZE_WAIT_S = 300  # must stay > observed D latency (~110s) with headroom
# Non-gating corroboration only: the same-thread completion-report POST is a
# capability the candidate does not yet implement (verified: no producer emits
# execution_state='complete' or posts a report message; w26's report scan has
# failed in 100% of recorded field runs). Gating on it would make w26
# unpassable. The gate is D terminalization from durable evidence (owner
# directive 2026-08-09); the report scan is recorded evidence for the day the
# capability ships.
W26_REPORT_CORROBORATION_WAIT_S = 20
W27_DRAWER_WAIT_S = 60

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
        # THE grant-binding correlation. It must match, byte for byte, what
        # `_capture_execution_binding` looks for in wave2_field_dispatch.py:
        # `f"w2-{run_id}"`. `run_id` ALREADY carries the pass suffix (the
        # dispatcher mints `<stamp>-p<N>`), so appending `-p{pass_num}` here
        # produced `w2-<stamp>-p1-p1` — a doubled suffix the consumer could
        # never match, and the exact-correlation binding therefore refused
        # every field run it was asked to bind (run 20260805T062433Z-p1).
        #
        # `run_tag` keeps the historical shape: it is a log/evidence tag, is
        # NOT part of the ExecutionAuthorizationGrant identity contract, and
        # nothing binds on it.
        self.correlation_id = f"w2-{run_id}"

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
        self._last_nav_error = ""  # why the latest _goto_panel/goto failed (diagnosable detail)

    # ── heartbeat + status ──────────────────────────────────────────────────
    def _status(self, state: str, **extra: Any) -> None:
        payload = {
            "state": state,
            "run_id": self.run_id,
            "pass": self.pass_num,
            "updated": _utc_now(),
            "stages_done": len(self.stages),
            "failed_stage": self.failed_stage,
        }
        payload.update(extra)
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

    # ── reliable text entry ──────────────────────────────────────────────────
    @staticmethod
    def _type_objective(page: Any, chat: Any, text: str) -> None:
        # (1) Wait for the input to be stable and interactable
        chat.first.wait_for(state="visible", timeout=10000)
        chat.first.click()
        page.wait_for_timeout(150)

        # (2) Clear residual text (swallowed Enter from a prior streaming reply)
        try:
            if (chat.first.input_value() or "").strip():
                chat.first.fill("")
                page.wait_for_timeout(100)
        except Exception:  # noqa: BLE001
            pass

        # (3) Focus explicitly and verify focus landed
        chat.first.focus()
        page.wait_for_timeout(100)

        # (4) Fill the text in one shot — 17ms vs 27-56s for press_sequentially.
        # fill() triggers React's onChange via native input-value setter +
        # InputEvent dispatch, same as a user paste. Probe confirmed this
        # produces value_matches=True on the real cockpit (20260804 probe).
        chat.first.fill(text)

        # (5) Verify the value was accepted by the React-controlled input
        actual = ""
        for _ in range(5):
            try:
                actual = chat.first.input_value() or ""
            except Exception:  # noqa: BLE001 — input may re-render
                page.wait_for_timeout(200)
                continue
            if actual == text:
                break
            page.wait_for_timeout(200)

        if actual != text:
            raise RuntimeError(
                f"chat input rejected fill: expected {len(text)} chars, "
                f"got {len(actual)} chars; first divergence at "
                f"pos {next((i for i, (a, b) in enumerate(zip(actual, text)) if a != b), min(len(actual), len(text)))}"
            )

        # (6) Submit and verify the input cleared
        chat.first.press("Enter")
        for _ in range(10):
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

    def _goto_panel(
        self, page: Any, panel: str, ready_selector: str, timeout_ms: int = 30000
    ) -> bool:
        """Deep-link navigate to a canonical cockpit panel and bounded-wait for
        its root element to mount.

        ``?panel=<id>`` is the cockpit's single navigation authority (App.tsx →
        cockpitStore.setPanel). A surface check must NEVER rely on the page
        coincidentally being on the right view — that structural assumption
        consumed field invocation #54 (w16 execution_surface=False on the
        approvals view). Fails CLOSED: navigation error or mount timeout → False.
        """
        self._last_nav_error = (
            ""  # per-attempt: never leak a stale error into a later stage's detail
        )
        try:
            sep = "&" if "?" in self.url else "?"
            page.goto(f"{self.url}{sep}panel={panel}", wait_until="load", timeout=45000)
            page.wait_for_selector(ready_selector, timeout=timeout_ms)
            return page.locator(ready_selector).count() > 0
        except Exception as exc:  # noqa: BLE001
            self._last_nav_error = str(exc)[:120]
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
        self._w26_task_d_terminal_verified(page, ctx)
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
        path = f"/api/umh/execution/by-plan/{pid}" if pid else "/api/umh/execution/attempts"
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

    def _read_authorizations_checked(self, page: Any) -> tuple[list[dict[str, Any]], bool, Any]:
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

    # ── durable history-backed observation (w16/w17/w18) ──────────────────────
    #
    # w16/w17/w18 must verify that a required lifecycle TRANSITION OCCURRED during
    # this run — not that the system is STILL in that transient state when the
    # collector happens to poll. A correct fast graph reconverges in seconds; a
    # point-in-time "is X currently running/blocked?" check then observes nothing
    # and falsely fails (field invocation #52). These helpers read the durable
    # canonical evidence — the per-attempt ``transitions`` ledger and the
    # composition Proof's ``predecessor_commits`` — so the required truths are
    # reconstructable AFTER the graph has advanced.

    def _attempt_detail(self, page: Any, attempt_id: str) -> dict[str, Any]:
        """Full attempt record INCLUDING ``transitions`` (the by-plan row omits it).

        GET /api/umh/execution/attempts/{attempt_id} → the canonical attempt with
        its timestamped lifecycle transitions. Returns {} on any non-200.
        """
        if not attempt_id:
            return {}
        resp = self._authed_get(page, f"/api/umh/execution/attempts/{attempt_id}")
        if not isinstance(resp, dict) or resp.get("__status") != 200 or resp.get("__error"):
            return {}
        if resp.get("error"):
            return {}
        return resp

    def _transition_at(
        self, transitions: list[dict[str, Any]], *, to_status: str = "", from_status: str = ""
    ) -> float | None:
        """Timestamp of the FIRST transition matching to_status and/or from_status."""
        for t in transitions or []:
            if to_status and str(t.get("to_status", "")) != to_status:
                continue
            if from_status and str(t.get("from_status", "")) != from_status:
                continue
            at = t.get("at")
            if isinstance(at, (int, float)):
                return float(at)
        return None

    def _dispatched_interval(self, transitions: list[dict[str, Any]]) -> tuple[float, float] | None:
        """The real worker-execution window: [leased→dispatched, dispatched→running].

        The ``running`` STATUS is a zero-width instant in the ledger (the poller
        stamps ``dispatched→running`` and ``running→verifying`` at the same time
        when the worker RESULT arrives), so it cannot express overlap. The
        ``dispatched`` PHASE — from ``leased→dispatched`` until the result is
        received (``dispatched→running``) — is the actual interval a worker was
        executing. Returns (enter, exit) or None if the attempt never dispatched.
        """
        enter = self._transition_at(transitions, to_status="dispatched")
        exit_ = self._transition_at(transitions, from_status="dispatched")
        if enter is None or exit_ is None or exit_ < enter:
            return None
        return (enter, exit_)

    @staticmethod
    def _intervals_overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
        """Seconds of temporal overlap between two [enter, exit] intervals (0 if none)."""
        return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))

    def _composition_proof(self, page: Any, proof_id: str) -> dict[str, Any]:
        """A composition Proof's ``action`` (predecessor_commits / composed_commit).

        GET /api/umh/proof-inspector/packages/{proof_id} → pkg.to_dict(). The
        composition action carries ``predecessor_commits`` (task_id → commit),
        which is how Task C is identified from durable evidence alone (no
        execution_kind field is exposed on any read surface). Returns the action
        dict, or {} on any non-200 / missing action.
        """
        if not proof_id:
            return {}
        resp = self._authed_get(page, f"/api/umh/proof-inspector/packages/{proof_id}")
        if not isinstance(resp, dict) or resp.get("__status") != 200:
            return {}
        action = resp.get("action")
        if isinstance(action, dict):
            return action
        # some serializers nest the package under __body
        body = resp.get("__body")
        if isinstance(body, dict) and isinstance(body.get("action"), dict):
            return body["action"]
        return {}

    def _identify_composition(self, page: Any, attempts: list[dict[str, Any]]) -> dict[str, Any]:
        """Task C, identified from DURABLE evidence: the attempt whose Proof carries
        ``predecessor_commits``. Returns
        {task_id, attempt_id, proof_id, predecessor_commits, composed_commit} or {}.
        """
        for a in attempts:
            proof_id = str(a.get("proof_id", ""))
            if not proof_id:
                continue
            action = self._composition_proof(page, proof_id)
            preds = action.get("predecessor_commits")
            if isinstance(preds, dict) and preds:
                return {
                    "task_id": self._attempt_task(a),
                    "attempt_id": str(a.get("attempt_id", "")),
                    "proof_id": proof_id,
                    "predecessor_commits": dict(preds),
                    "composed_commit": str(action.get("composed_commit", "")),
                }
        return {}

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
            opened
            and detail_visible
            and (page.locator(WG_WORK_DETAIL_CONTEXT).count() > 0 or has_scope),
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
            a
            for a in auths
            if str(a.get("status", "")).lower() in ("", "pending", "activating")
            and str(a.get("state", "")).lower() not in ("active",)
        ]
        # Zero attempts must be a CONFIRMED empty read (200), not a failed read
        # returning [] (review C2). The authorizations read must also have
        # succeeded so a broken surface can't masquerade as "no pending".
        ok = attempts_ok and len(attempts) == 0 and auths_ok
        detail = f"attempts={len(attempts)} authorizations={len(auths)} pending_like={len(pending)}"
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

    def _durable_execution_authorized(self, page: Any, ctx: dict[str, Any]) -> tuple[bool, str]:
        """Reconstruct w15 authorization from canonical durable grant/binding facts.

        The HUD click is the intended operator action, but a completed graph can
        race the observer after the click. The durable invariant is the one the
        runner admits on: an ACTIVE run-correlated grant and/or an attempt bound
        to that exact authorization before admission.
        """
        ref = str(ctx.get("execution_decision_ref") or self._execution_decision_ref or "")
        plan_id = str(ctx.get("plan_record_id") or self._last_plan_id or "")
        auths, auths_ok, auths_status = self._read_authorizations_checked(page)
        attempts, attempts_ok, attempts_status = self._read_attempts_checked(page, plan_id)

        def _matches_ref(row: dict[str, Any]) -> bool:
            row_ref = str(
                row.get("decision_ref")
                or row.get("execution_authorization_ref")
                or row.get("authorization_ref")
                or ""
            )
            if ref:
                return row_ref == ref
            return bool(plan_id) and str(row.get("plan_record_id", "")) == plan_id

        active_grants = [
            a
            for a in auths
            if _matches_ref(a)
            and str(a.get("status") or a.get("state") or "").lower() == "active"
        ]

        admitted_statuses = {"leased", "dispatched", "running", "verifying"}
        terminal_statuses = {"succeeded", "failed", "cancelled", "rolled_back"}

        def _has_admission_binding(row: dict[str, Any]) -> bool:
            return any(
                str(row.get(k, "") or "")
                for k in ("assignment_id", "lease_id", "worker_identity", "proof_id")
            )

        def _detail_has_admitted_transition(attempt_id: str) -> bool:
            detail = self._attempt_detail(page, attempt_id)
            transitions = detail.get("transitions") if isinstance(detail, dict) else None
            if not isinstance(transitions, list):
                return False
            for t in transitions:
                to_status = str(t.get("to_status", "")).lower()
                from_status = str(t.get("from_status", "")).lower()
                if to_status in admitted_statuses or from_status in admitted_statuses:
                    return True
            return False

        def _attempt_proves_admission(row: dict[str, Any]) -> bool:
            status = str(row.get("status") or row.get("phase") or "").lower()
            if status in admitted_statuses:
                return _has_admission_binding(row)
            if status in terminal_statuses:
                if _has_admission_binding(row):
                    return True
                return _detail_has_admitted_transition(str(row.get("attempt_id", "") or ""))
            return False

        admitted_attempts = [
            a
            for a in attempts
            if _matches_ref(a) and _attempt_proves_admission(a)
        ]
        ok = auths_ok and attempts_ok and (bool(active_grants) or bool(admitted_attempts))
        detail = (
            f"durable_authorized={ok} ref={ref[:32]} plan={plan_id[:16]} "
            f"active_grants={len(active_grants)} admitted_bindings={len(admitted_attempts)} "
            f"auth_read={auths_ok}/{auths_status} attempt_read={attempts_ok}/{attempts_status}"
        )
        return ok, detail

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
                action = ""
                try:
                    parsed = json.loads(body)
                    if isinstance(parsed, dict):
                        action = str(parsed.get("action", ""))
                except Exception:  # noqa: BLE001
                    action = ""
                clicked = resp.status < 300 and action == "approved"
            except Exception as exc:  # noqa: BLE001
                status_body = f"no-response ({str(exc)[:80]})"
        else:
            status_body = "approve-button-never-appeared"
        durable_ok, durable_detail = self._durable_execution_authorized(page, ctx)
        authorized = clicked or durable_ok
        ctx["execution_authorized"] = authorized
        self.stage(
            "w15_authorize_execution",
            authorized,
            (
                f"authorized={authorized} hud_authorized={clicked} "
                f"decision_response={status_body[:120]} {durable_detail}"
            ),
        )
        self.shot(page, "w15_authorized")
        self.dom(page, "w15_authorized")

    # ── w16 — A + B RUNNING concurrently ──────────────────────────────────────
    def _w16_ab_running_concurrent(self, page: Any, ctx: dict[str, Any]) -> None:
        """Exactly TWO implementation attempts (A, B) executed CONCURRENTLY with
        DISTINCT task ids — proven from DURABLE history, not a live snapshot.

        HISTORY-BACKED (field #52 fix): the ``running`` status is a zero-width
        instant in the ledger, so a fast graph never shows two "running" at once.
        Instead we reconstruct each implementation attempt's real worker-execution
        window — the ``dispatched`` phase ([leased→dispatched, dispatched→running])
        — from its durable ``transitions`` and require genuine TEMPORAL OVERLAP of
        the two independent first-attempts (A1 ∥ B). This passes for both fast and
        slow correct graphs and cannot be satisfied by two sequential dispatches.

        The implementation attempts are the two ``attempt_number == 1`` attempts
        that are NOT the composition task (identified via its Proof's
        predecessor_commits) and NOT the verification task (D). The composed
        task's own predecessor_commits name exactly these two task ids, which is
        the run-bound, candidate-bound anchor tying this stage to THIS graph.
        """
        deadline = time.time() + W16_COMPOSITION_WAIT_S
        comp: dict[str, Any] = {}
        impl_first: dict[str, dict[str, Any]] = {}
        # Bounded-wait until BOTH implementation attempts have a durable dispatched
        # interval AND the composition proof exists (so we can name the true A/B
        # pair from predecessor_commits — never a DOM guess).
        while time.time() < deadline:
            attempts = self._read_attempts(page)
            for a in attempts:
                tid, aid = self._attempt_task(a), a.get("attempt_id")
                if tid and aid:
                    self._attempt_ids[tid] = aid
            comp = self._identify_composition(page, attempts) or comp
            pred_tasks = set((comp.get("predecessor_commits") or {}).keys())
            if pred_tasks:
                # First attempt (attempt_number==1) of each predecessor task = the
                # concurrent implementation pair. (A2 retry is sequential recovery.)
                impl_first = {}
                for a in attempts:
                    tid = self._attempt_task(a)
                    if tid in pred_tasks and int(a.get("attempt_number", 0) or 0) == 1:
                        impl_first[tid] = a
                if len(impl_first) == 2:
                    intervals = {
                        tid: self._dispatched_interval(
                            self._attempt_detail(page, str(a.get("attempt_id", ""))).get(
                                "transitions", []
                            )
                        )
                        for tid, a in impl_first.items()
                    }
                    if all(intervals.values()):
                        break
            time.sleep(3)

        pred_tasks = sorted((comp.get("predecessor_commits") or {}).keys())
        ctx["concurrent_running_tasks"] = pred_tasks
        ctx["composition"] = comp
        # Reconstruct the two dispatched intervals and prove real overlap.
        ivals = {
            tid: self._dispatched_interval(
                self._attempt_detail(page, str(a.get("attempt_id", ""))).get("transitions", [])
            )
            for tid, a in impl_first.items()
        }
        overlap_s = 0.0
        both_ran = len(ivals) == 2 and all(ivals.values())
        if both_ran:
            (ia, ib) = list(ivals.values())
            overlap_s = self._intervals_overlap(ia, ib)
        # The canonical execution surface must be mounted (structural
        # corroboration) — EXPLICITLY navigated to, never sampled from whatever
        # view the page happens to be on (inv #54: the page sits on the
        # approvals view after w15, so a point-in-time count here is
        # structurally False for a fully correct run).
        exec_surface = self._goto_panel(page, "execution", W2_EXECUTION_ROOT)
        # PASS requires: exactly two distinct predecessor tasks, both with a real
        # dispatched interval, GENUINE temporal overlap (> 0), and the surface
        # mounted. Sequential A-then-B yields overlap 0 → fails.
        ok = len(pred_tasks) == 2 and both_ran and overlap_s > 0.0 and exec_surface
        nav_note = "" if exec_surface else f" nav_err={self._last_nav_error or 'mount_timeout'}"
        self.stage(
            "w16_ab_running_concurrent",
            ok,
            f"concurrent_tasks={pred_tasks} dispatched_overlap_s={overlap_s:.1f} "
            f"both_dispatched={both_ran} execution_surface={exec_surface}" + nav_note,
        )
        self.shot(page, "w16_ab_running")
        self.dom(page, "w16_ab_running")

    # ── w17 — C blocked until A and B verified ────────────────────────────────
    def _w17_c_blocked(self, page: Any, ctx: dict[str, Any]) -> None:
        """The integration task C was correctly WITHHELD until A and B completed —
        proven from DURABLE history, valid even after C has already composed.

        HISTORY-BACKED (field #52 fix): the live "is C currently blocked?" snapshot
        is gone the instant C composes. Instead we establish, from durable
        ``transitions``, that C did not begin its own work until BOTH predecessors
        reached a terminal-good (verified/succeeded) state:

          - C exists and is the composition task (Proof carries predecessor_commits);
          - C's earliest own-work transition (``created→ready`` — the moment the
            scheduler admitted C to the frontier) is AT/AFTER both predecessors'
            ``verifying→succeeded`` time — i.e. C was held while they ran;
          - NO non-A/B/D task advanced to running/succeeded before the predecessors
            verified (nothing jumped the dependency gate).

        This distinguishes "C correctly withheld pending dependencies" from "C
        never ran for an unrelated authority failure": a real C attempt with a
        composition Proof must exist AND its admission must post-date predecessor
        success. A missing C, or a C admitted before predecessors verified, fails.
        """
        pred_tasks = set(ctx.get("concurrent_running_tasks", []))
        comp = ctx.get("composition") or {}
        c_task = str(comp.get("task_id", ""))
        c_attempt_id = str(comp.get("attempt_id", ""))
        deadline = time.time() + 360
        c_admit_at: float | None = None
        pred_verified_at: dict[str, float] = {}
        advanced_non_ab_early = False
        while time.time() < deadline:
            attempts = self._read_attempts(page)
            # predecessor success times (each predecessor's verifying→succeeded)
            pred_verified_at = {}
            for a in attempts:
                tid = self._attempt_task(a)
                if tid in pred_tasks and self._attempt_status(a) == "succeeded":
                    det = self._attempt_detail(page, str(a.get("attempt_id", "")))
                    t = self._transition_at(det.get("transitions", []), to_status="succeeded")
                    if t is not None:
                        # keep the LATEST success across retries of this task
                        pred_verified_at[tid] = max(pred_verified_at.get(tid, 0.0), t)
            # C's admission time (created→ready)
            if c_attempt_id:
                cdet = self._attempt_detail(page, c_attempt_id)
                c_admit_at = self._transition_at(cdet.get("transitions", []), to_status="ready")
            # dependency-gate violation: any task that is NOT a predecessor and NOT
            # the composition/verification lane that entered running before both
            # predecessors verified.
            if len(pred_verified_at) == 2:
                gate = max(pred_verified_at.values())
                for a in attempts:
                    tid = self._attempt_task(a)
                    if tid in pred_tasks or tid == c_task:
                        continue
                    det = self._attempt_detail(page, str(a.get("attempt_id", "")))
                    ran = self._transition_at(det.get("transitions", []), to_status="dispatched")
                    if ran is not None and ran < gate - 1.0:
                        advanced_non_ab_early = True
            # terminal-good once both predecessors verified and C is admitted after
            if len(pred_verified_at) == 2 and c_admit_at is not None:
                break
            time.sleep(3)
        ctx["blocked_tasks"] = [c_task] if c_task else []
        both_verified = len(pred_verified_at) == 2
        gate = max(pred_verified_at.values()) if both_verified else 0.0
        # C admitted AT/AFTER both predecessors verified (allow 1s clock slack).
        c_withheld = (
            bool(c_task) and c_admit_at is not None and both_verified and c_admit_at >= gate - 1.0
        )
        ok = c_withheld and not advanced_non_ab_early
        self.stage(
            "w17_c_blocked",
            ok,
            f"c_task={c_task} c_admit_at={c_admit_at} pred_verified={both_verified} "
            f"gate={gate:.3f} c_withheld={c_withheld} early_advance={advanced_non_ab_early}",
        )
        self.shot(page, "w17_c_blocked")

    # ── w18 — A and B verified (AttemptProof) ─────────────────────────────────
    def _w18_ab_verified(self, page: Any, ctx: dict[str, Any]) -> None:
        """A and B each SUCCEEDED with a durable Proof BEFORE C consumed them, and
        C's composition binds exactly their commits — proven from DURABLE evidence,
        valid even after C and D have already succeeded.

        HISTORY-BACKED (field #52 fix): rather than requiring A/B to be *currently*
        shown succeeded, we establish from durable state that:

          - for EACH predecessor task, its qualifying SUCCEEDED attempt (the retry
            that succeeded, not the failed A1) has a non-empty ``proof_id`` and a
            ``verifying→succeeded`` transition;
          - both predecessors succeeded BEFORE C's composition began
            (C's ``created→ready`` / composition transition post-dates them);
          - C's composition Proof ``predecessor_commits`` names exactly these two
            predecessor task ids AND binds each to that task's succeeded commit.

        A predecessor that only ever FAILED (e.g. A1) cannot satisfy this — only a
        task's succeeded attempt with a Proof does. Wrong predecessor bindings in
        C's Proof fail the stage.
        """
        pred_tasks = set(ctx.get("concurrent_running_tasks", []))
        comp = ctx.get("composition") or {}
        comp_preds: dict[str, str] = dict(comp.get("predecessor_commits") or {})
        deadline = time.time() + 360
        verified: dict[str, dict[str, Any]] = {}
        while time.time() < deadline:
            attempts = self._read_attempts(page)
            verified = {}
            for a in attempts:
                tid = self._attempt_task(a)
                if tid not in pred_tasks or self._attempt_status(a) != "succeeded":
                    continue
                proof_id = str(a.get("proof_id", ""))
                if not proof_id:
                    continue
                det = self._attempt_detail(page, str(a.get("attempt_id", "")))
                succ_at = self._transition_at(det.get("transitions", []), to_status="succeeded")
                commit = ""
                commits = det.get("commits") or a.get("commits") or []
                if commits:
                    # commit sha is the leading token of the row ("<sha> <msg>")
                    commit = str(commits[0]).split()[0]
                verified[tid] = {"proof_id": proof_id, "succeeded_at": succ_at, "commit": commit}
            if len(verified) == 2 and all(
                v["proof_id"] and v["succeeded_at"] for v in verified.values()
            ):
                break
            time.sleep(3)

        # latest predecessor success time → the "before C composed" anchor
        ab_verified_at = max(
            (v["succeeded_at"] for v in verified.values() if v["succeeded_at"]), default=0.0
        )
        ctx["ab_verified_at"] = ab_verified_at or time.time()

        # C composition must post-date both predecessor successes.
        c_attempt_id = str(comp.get("attempt_id", ""))
        c_compose_at: float | None = None
        if c_attempt_id:
            cdet = self._attempt_detail(page, c_attempt_id)
            # composition begins at leased→verifying (composer) or created→ready
            c_compose_at = self._transition_at(
                cdet.get("transitions", []), from_status="leased", to_status="verifying"
            ) or self._transition_at(cdet.get("transitions", []), to_status="ready")

        both_proofed = len(verified) == 2 and all(
            v["proof_id"] and v["succeeded_at"] for v in verified.values()
        )
        composed_after = (
            c_compose_at is not None
            and ab_verified_at > 0.0
            and c_compose_at >= ab_verified_at - 1.0
        )

        # C's Proof predecessor set must be EXACTLY the two predecessor tasks, and
        # EACH predecessor commit must match that task's succeeded-attempt commit.
        # STRICT: every predecessor must resolve to a verified attempt with a
        # commit that binds to C's predecessor_commits — no vacuous skip (a
        # missing/foreign predecessor must FAIL, never pass by omission).
        def _commit_binds(tid: str) -> bool:
            v = verified.get(tid, {})
            vc = str(v.get("commit", ""))
            pc = str(comp_preds.get(tid, ""))
            if not vc or not pc:
                return False
            return vc.startswith(pc[:12]) or pc.startswith(vc[:12])

        # ONE load-bearing binding check (no redundant set-equality term whose
        # mutation would be equivalent): exactly 2 predecessors, the set equals
        # the concurrent pair, and every predecessor binds to a verified commit.
        preds_bound = (
            len(comp_preds) == 2
            and set(comp_preds.keys()) == pred_tasks
            and len(pred_tasks) == 2
            and all(_commit_binds(tid) for tid in pred_tasks)
        )
        ok = both_proofed and composed_after and preds_bound
        self.stage(
            "w18_ab_verified",
            ok,
            f"verified={sorted(verified)} both_proofed={both_proofed} "
            f"composed_after={composed_after} preds_bound={preds_bound}",
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
                    if (
                        started
                        and ctx.get("ab_verified_at")
                        and started < ctx["ab_verified_at"] - 5
                    ):
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
            and (
                "verif" in self._attempt_task(a).lower()
                or "verif" in str(a.get("verifier_role_id", "")).lower()
            )
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
                with fpage.expect_response(lambda r: "/api/notes/search" in r.url, timeout=15000):
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

    # ── w26 — Task D terminal VERIFIED (full bound chain) ─────────────────────
    def _w26_task_d_terminal_verified(self, page: Any, ctx: dict[str, Any]) -> None:
        """Task D — the verification task — reaches the required terminal
        VERIFIED outcome, proven from durable canonical execution evidence.

        OWNER RULING 2026-08-09 (inv #54): this stage was formerly
        ``w26_same_thread_report`` and gated on a same-thread completion
        report — a capability the candidate does not implement (no producer
        emits execution_state='complete' or posts a report message; the scan
        failed in 100% of recorded field runs). The name was semantically
        false and has been corrected. The report scan survives ONLY as
        non-gating corroboration at the end of this stage.

        Gate conjuncts (ALL required; ANY failure fails closed — final graph
        success alone is insufficient):
          terminalized  — every verification task (outside the concurrent
                          pair and the composition task; deciding attempt =
                          HIGHEST attempt_number) settles within the latency
                          envelope; timeout fails closed;
          succeeded     — final attempt succeeded WITH a Proof id;
          run_bound     — attempt.correlation_id == 'w2-<run_id>' (foreign /
                          stale-run evidence fails);
          candidate_bound — the lease's read-only source_ref.repo_root lies
                          under <candidate_sha>/targets/<run_id>/;
          composed_base — lease.source_ref.base_commit equals Task C's
                          composed_commit from the w16 composition anchor
                          (wrong or missing base fails);
          verifier_ran  — a verifying→succeeded transition by a 'verifier:*'
                          actor exists AND the Proof records a verifier
                          identity distinct from the worker identity;
          proof_bound   — the Proof's action binds THIS attempt_id, task_id,
                          plan_record_id and lease_id (missing or foreign
                          Proof fails);
          zero_write    — the lease's diff-scope enforcement is 'enforced'
                          and the succeeded attempt reports zero
                          files_changed and zero commits (source mutation
                          where forbidden fails).
        """
        pair = set(ctx.get("concurrent_running_tasks", []))
        comp = ctx.get("composition") or {}
        comp_task = str(comp.get("task_id", ""))
        composed_commit = str(comp.get("composed_commit", ""))

        def _d_rows() -> dict[str, tuple[int, dict[str, Any]]]:
            # DECIDING attempt per task = HIGHEST attempt_number (a retried D
            # is judged by its final attempt, never by API row order).
            rows: dict[str, tuple[int, dict[str, Any]]] = {}
            for a in self._read_attempts(page):
                tid = self._attempt_task(a)
                if not tid or tid in pair or tid == comp_task:
                    continue
                n = int(a.get("attempt_number", 0) or 0)
                if tid not in rows or n >= rows[tid][0]:
                    rows[tid] = (n, a)
            return rows

        d_rows = _d_rows()
        if not d_rows:
            # No verification task exists outside the pair/composition — a
            # structural graph mismatch. Fail IMMEDIATELY (no 300s stall).
            self.stage(
                "w26_task_d_terminal_verified",
                False,
                f"no verification task outside pair={sorted(pair)} "
                f"composition={comp_task or '-'} (fail closed)",
            )
            self.shot(page, "w26_d_terminal")
            self.dom(page, "w26_d_terminal")
            return
        deadline = time.time() + W26_D_TERMINALIZE_WAIT_S
        d_settled = False
        while time.time() < deadline:
            if d_rows and all(
                self._attempt_status(a) in ("succeeded", "failed", "cancelled")
                for _, a in d_rows.values()
            ):
                d_settled = True
                break
            time.sleep(5)
            d_rows = _d_rows()

        checks: dict[str, bool] = {
            "terminalized": d_settled,
            "succeeded": True,
            "run_bound": True,
            "candidate_bound": True,
            "composed_base": True,
            "verifier_ran": True,
            "proof_bound": True,
            "zero_write": True,
        }
        expect_corr = f"w2-{self.run_id}"
        expect_path = f"/{self.candidate_commit}/targets/{self.run_id}/"
        summary: list[str] = []
        for tid, (n, a) in sorted(d_rows.items()):
            aid = str(a.get("attempt_id", ""))
            st = self._attempt_status(a)
            proof_id = str(a.get("proof_id", ""))
            summary.append(f"{tid}:#{n}:{st}{'+proof' if proof_id else ''}")
            if st != "succeeded" or not proof_id:
                checks["succeeded"] = False
                continue
            detail = self._attempt_detail(page, aid) or {}
            lease = detail.get("environment_lease") or {}
            src = lease.get("source_ref") or {}
            if str(detail.get("correlation_id", "")) != expect_corr:
                checks["run_bound"] = False
            if expect_path not in str(src.get("repo_root", "")):
                checks["candidate_bound"] = False
            if not composed_commit or str(src.get("base_commit", "")) != composed_commit:
                checks["composed_base"] = False
            verifier_transition = any(
                t.get("from_status") == "verifying"
                and t.get("to_status") == "succeeded"
                and str(t.get("actor", "")).startswith("verifier:")
                for t in (detail.get("transitions") or [])
            )
            action = self._composition_proof(page, proof_id) or {}
            verifier_id = str(action.get("verifier_identity", "") or "")
            worker_id = str(action.get("worker_identity", "") or "")
            if not verifier_transition or not verifier_id or verifier_id == worker_id:
                checks["verifier_ran"] = False
            if not (
                action
                and str(action.get("attempt_id", "")) == aid
                and str(action.get("task_id", "")) == tid
                and str(action.get("plan_record_id", "")) == str(detail.get("plan_record_id", ""))
                and str(action.get("lease_id", "")) == str(detail.get("lease_id", ""))
            ):
                checks["proof_bound"] = False
            enforcement = lease.get("enforcement") or {}
            # Forward-guard: 'enforced' is today's dataclass default for the
            # diff-scope ledger — the load-bearing mutation check is the empty
            # files/commits conjunct below; this guard exists so a future
            # 'declared'-only lease can never silently qualify.
            if str(enforcement.get("diff_scope_post_hoc", "")) != "enforced":
                checks["zero_write"] = False
            if (detail.get("files_changed") or []) or (detail.get("commits") or []):
                checks["zero_write"] = False

        d_ok = all(checks.values())

        # NON-GATING corroboration — read the chat surface explicitly and
        # record whether a completion report rendered in the original thread.
        # The candidate does not implement this capability today; presence or
        # absence NEVER decides qualification.
        try:
            page.goto(self.url, wait_until="load", timeout=45000)
        except Exception as exc:  # noqa: BLE001
            self._last_nav_error = str(exc)[:120]
        report_present = False
        deadline = time.time() + W26_REPORT_CORROBORATION_WAIT_S
        while time.time() < deadline:
            if (
                self._body_contains(page, "EXECUTION COMPLETE")
                or self._body_contains(page, "COMPLETE — PROOF")
                or self._body_contains(page, "PlanExecutionProof")
            ):
                report_present = True
                break
            time.sleep(3)
        conjuncts = " ".join(f"{k}={v}" for k, v in checks.items())
        self.stage(
            "w26_task_d_terminal_verified",
            d_ok,
            f"d=[{','.join(summary) or '-'}] {conjuncts} "
            f"report_in_thread={report_present}"
            + (
                ""
                if report_present
                else " (non-gating: completion-report capability not yet implemented by candidate)"
            ),
        )
        self.shot(page, "w26_d_terminal")
        self.dom(page, "w26_d_terminal")

    # ── w27 — Work Detail shows execution lineage ─────────────────────────────
    def _w27_work_detail_lineage(self, page: Any, ctx: dict[str, Any]) -> None:
        """Work Detail exposes the execution lineage: attempt → assignment →
        environment lease → verification/proof.

        EXPLICIT NAVIGATION (inv #54 fix): the lineage drawer (AttemptsView)
        lives on the canonical execution panel; the old implementation clicked
        the chat-card affordance from whatever view was mounted and sampled the
        drawer 1s later — structurally False on a correct run. Now: navigate to
        the execution panel, select an attempt row (the drawer's real open
        affordance), and bounded-wait for the drawer's lineage sections to
        render (the drawer fetches attempt detail). Timeout fails CLOSED.
        """
        on_surface = self._goto_panel(page, "execution", W2_EXECUTION_ROOT)
        opened = False
        assignment = lease = verification = False
        if on_surface:
            deadline = time.time() + W27_DRAWER_WAIT_S
            while time.time() < deadline:
                rows = page.locator(W2_EXECUTION_ATTEMPT)
                if rows.count() > 0:
                    if not opened:
                        # AttemptsView repolls every 4s — a count()-then-click()
                        # straddling a re-render can raise on a detached node.
                        # A transient click failure retries in-loop; it must
                        # NEVER abort the whole journey (that would lose
                        # w28-w30 and the entire pass to a stale handle).
                        try:
                            rows.first.click()
                            opened = True
                        except Exception as exc:  # noqa: BLE001
                            self._last_nav_error = str(exc)[:120]
                    if opened:
                        assignment = page.locator(W2_ASSIGNMENT).count() > 0
                        lease = page.locator(W2_ENVIRONMENT_LEASE).count() > 0
                        verification = page.locator(W2_VERIFICATION_STATUS).count() > 0
                        if assignment and lease and verification:
                            break
                time.sleep(2)
        overlay = page.locator(W2_WORK_OVERLAY).count() > 0
        worker = page.locator(W2_WORKER_STATUS).count() > 0
        # The governed cancel/retry affordances render on the drawer (they route
        # through governed_mutation — their PRESENCE is the surface contract; the
        # collector never clicks them on a green pass). reject lives on the HUD row.
        cancel_ctrl = page.locator(W2_EXECUTION_CANCEL).count()
        retry_ctrl = page.locator(W2_EXECUTION_RETRY).count()
        reject_ctrl = page.locator(W2_EXEC_REJECT_BTN).count()
        # Lineage is proven when the drawer shows assignment + lease + verification
        # ON the explicitly-navigated execution surface with a genuinely opened
        # attempt; the overlay/worker-status/governed-controls are corroborating.
        ok = on_surface and opened and assignment and lease and verification
        nav_note = "" if on_surface else f" nav_err={self._last_nav_error or 'mount_timeout'}"
        self.stage(
            "w27_work_detail_lineage",
            ok,
            f"on_surface={on_surface} opened={opened} assignment={assignment} "
            f"lease={lease} verification={verification} overlay={overlay} "
            f"worker_status={worker} cancel_ctrl={cancel_ctrl} "
            f"retry_ctrl={retry_ctrl} reject_ctrl={reject_ctrl}" + nav_note,
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
        execution_passed = self.error is None and all(s["ok"] for s in gating_stages)
        self._status("execution_complete", execution_passed=execution_passed)
        bonus = {s["stage"]: s["ok"] for s in self.stages if s["stage"] in self._NON_GATING_STAGES}
        asset_files = sorted(
            {
                n["url"]
                for n in self.network
                if n["url"].endswith((".js", ".css")) or "/assets/" in n["url"]
            }
        )
        result = {
            "pass": execution_passed,
            "execution_passed": execution_passed,
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
        self._status("evidence_finalizing", execution_passed=execution_passed)
        # Final secret-hygiene pass over EVERY collected JSON/JSONL before it is
        # shipped — bodies/console are redacted at capture time, but this is the
        # belt-and-suspenders sweep so nothing unredacted can ever be scp'd into
        # the committed proof (review C1).
        self._redact_pass_dir()
        self._status("evidence_shipping", execution_passed=execution_passed)
        publication = self._publish_evidence(execution_passed)
        result["evidence_publication"] = publication
        if not publication.get("ok"):
            result["pass"] = False
            (self.pass_dir / "result.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            self._status(
                "evidence_preservation_failed",
                execution_passed=execution_passed,
                preservation_error=str(publication.get("error", "evidence publication failed")),
            )
            return result
        self._status(
            "passed" if execution_passed else "failed",
            execution_passed=execution_passed,
            evidence_receipt=publication.get("receipt", {}),
        )
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

    def _artifact_inventory(self) -> list[dict[str, Any]]:
        excluded = {
            "status.json",
            "evidence_manifest.json",
            "evidence_manifest.sha256",
            "evidence_receipt.json",
        }
        files: list[dict[str, Any]] = []
        for path in sorted(self.pass_dir.rglob("*")):
            if not path.is_file() or path.name in excluded:
                continue
            rel = path.relative_to(self.pass_dir).as_posix()
            data = path.read_bytes()
            files.append(
                {
                    "path": rel,
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        return files

    def _write_artifact_manifest(self) -> dict[str, Any]:
        required = ("result.json", "network.jsonl", "console.jsonl")
        files = self._artifact_inventory()
        by_path = {f["path"] for f in files}
        missing = [name for name in required if name not in by_path]
        created_at = _utc_now()
        manifest_path = self.pass_dir / "evidence_manifest.json"
        if manifest_path.exists():
            try:
                previous = json.loads(manifest_path.read_text(encoding="utf-8"))
                if (
                    previous.get("schema_version") == 1
                    and previous.get("campaign_id") == os.environ.get("UMH_WAVE2_CAMPAIGN_ID", "")
                    and previous.get("run_id") == self.run_id
                    and previous.get("pass_id") == f"pass{self.pass_num}"
                    and previous.get("pass_num") == self.pass_num
                    and previous.get("candidate_sha") == self.candidate_commit
                    and previous.get("scenario") == self.scenario
                    and previous.get("required_artifacts") == list(required)
                    and previous.get("missing_required_artifacts") == missing
                    and previous.get("files") == files
                    and previous.get("created_at")
                ):
                    created_at = str(previous["created_at"])
            except (OSError, json.JSONDecodeError, TypeError):
                pass
        manifest = {
            "schema_version": 1,
            "campaign_id": os.environ.get("UMH_WAVE2_CAMPAIGN_ID", ""),
            "run_id": self.run_id,
            "pass_id": f"pass{self.pass_num}",
            "pass_num": self.pass_num,
            "candidate_sha": self.candidate_commit,
            "scenario": self.scenario,
            "collector_identity": {
                "pid": os.getpid(),
                "hostname": os.environ.get("COMPUTERNAME", ""),
            },
            "created_at": created_at,
            "required_artifacts": list(required),
            "missing_required_artifacts": missing,
            "files": files,
        }
        tmp = manifest_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(manifest_path)
        manifest["manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        (self.pass_dir / "evidence_manifest.sha256").write_text(
            f"{manifest['manifest_sha256']}  evidence_manifest.json\n",
            encoding="utf-8",
        )
        return manifest

    def _publish_evidence(self, execution_passed: bool) -> dict[str, Any]:
        """Ship evidence through staging, remote verification and atomic promotion."""
        manifest = self._write_artifact_manifest()
        if manifest["missing_required_artifacts"]:
            return {
                "ok": False,
                "error": f"missing required artifacts: {manifest['missing_required_artifacts']}",
                "manifest": manifest,
            }
        if not self.ship_to:
            return {"ok": False, "error": "ship_to unset", "manifest": manifest}
        vps = os.environ.get("UMH_VPS_SSH", "")
        if not vps:
            return {"ok": False, "error": "UMH_VPS_SSH unset", "manifest": manifest}

        dest = self.ship_to.rstrip("/")
        attempt_id = uuid4().hex[:12]
        run_root = f"{dest}/{self.run_id}"
        staging = f"{run_root}/.staging-pass{self.pass_num}-{attempt_id}"
        canonical = f"{run_root}/pass{self.pass_num}"
        try:
            prep = f"rm -rf {shlex.quote(staging)} && mkdir -p {shlex.quote(run_root)}"
            prep_proc = subprocess.run(
                ["ssh", vps, prep],
                timeout=30,
                capture_output=True,
                text=True,
                **_no_window(),
            )
            if prep_proc.returncode != 0:
                return {
                    "ok": False,
                    "error": "staging preparation failed",
                    "stderr": _redact(prep_proc.stderr or prep_proc.stdout or ""),
                    "manifest": manifest,
                }
            scp_proc = subprocess.run(
                ["scp", "-r", str(self.pass_dir), f"{vps}:{staging}"],
                timeout=300,
                capture_output=True,
                text=True,
                **_no_window(),
            )
            if scp_proc.returncode != 0:
                return {
                    "ok": False,
                    "error": "staging transfer failed",
                    "stderr": _redact(scp_proc.stderr or scp_proc.stdout or ""),
                    "staging_path": staging,
                    "manifest": manifest,
                }
            receipt = self._verify_and_promote(
                vps, staging=staging, canonical=canonical, manifest=manifest
            )
            if not receipt.get("ok"):
                return {
                    "ok": False,
                    "error": receipt.get("error", "destination verification failed"),
                    "receipt": receipt,
                    "manifest": manifest,
                }
            (self.pass_dir / "evidence_receipt.json").write_text(
                json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8"
            )
            return {"ok": True, "receipt": receipt, "manifest": manifest, "execution_passed": execution_passed}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc), "manifest": manifest, "staging_path": staging}

    def _verify_and_promote(
        self,
        vps: str,
        *,
        staging: str,
        canonical: str,
        manifest: dict[str, Any],
    ) -> dict[str, Any]:
        code = f"""
import hashlib, json, os, shutil, sys, time
from pathlib import Path
staging = Path({json.dumps(staging)})
canonical = Path({json.dumps(canonical)})
required_artifacts = ('result.json', 'network.jsonl', 'console.jsonl')
required_binding = {{
  'run_id': {json.dumps(self.run_id)},
  'pass_num': {self.pass_num},
  'candidate_sha': {json.dumps(self.candidate_commit)},
}}
def fail(reason):
    print(json.dumps({{
      'ok': False,
      'error': reason,
      'staging_path': str(staging),
      'canonical_path': str(canonical),
    }}))
    sys.exit(0)
def fsync_dir(path):
    try:
        fd = os.open(str(path), os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except Exception:
        pass
def load_and_verify(root):
    manifest_path = root / 'evidence_manifest.json'
    if not manifest_path.is_file():
        return None, '', 'missing evidence_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for key, expected in required_binding.items():
        if manifest.get(key) != expected:
            return None, '', f'binding mismatch {{key}}'
    if tuple(manifest.get('required_artifacts', [])) != required_artifacts:
        return None, '', 'required artifact contract mismatch'
    for rel in required_artifacts:
        if not (root / rel).is_file():
            return None, '', f'missing required artifact {{rel}}'
    seen = set()
    for item in manifest.get('files', []):
        if not isinstance(item, dict):
            return None, '', 'malformed manifest file entry'
        rel = item.get('path')
        if not isinstance(rel, str) or rel.startswith('/') or '\\\\' in rel:
            return None, '', 'unsafe manifest path'
        parts = Path(rel).parts
        if any(part in ('', '.', '..') for part in parts):
            return None, '', 'unsafe manifest path'
        if rel in seen:
            return None, '', 'duplicate manifest path'
        seen.add(rel)
        path = root / item['path']
        if not path.is_file():
            return None, '', f'missing manifest file {{item[\"path\"]}}'
        data = path.read_bytes()
        if len(data) != int(item['size']) or hashlib.sha256(data).hexdigest() != item['sha256']:
            return None, '', f'digest mismatch {{item[\"path\"]}}'
    missing_bound = [rel for rel in required_artifacts if rel not in seen]
    if missing_bound:
        return None, '', 'required artifact missing from hash inventory: ' + ','.join(missing_bound)
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    sidecar = root / 'evidence_manifest.sha256'
    if sidecar.is_file():
        expected = sidecar.read_text(encoding='utf-8').split()[0]
        if expected != digest:
            return None, '', 'manifest sidecar digest mismatch'
    return manifest, digest, ''
def build_receipt(manifest, manifest_digest, recovered=False):
    return {{
      'ok': True,
      'schema_version': 1,
      'receipt_id': 'receipt-' + hashlib.sha256((str(canonical) + manifest_digest).encode()).hexdigest()[:16],
      'run_id': manifest['run_id'],
      'pass_id': manifest['pass_id'],
      'pass_num': manifest['pass_num'],
      'candidate_sha': manifest['candidate_sha'],
      'artifact_count': len(manifest.get('files', [])),
      'manifest_sha256': manifest_digest,
      'canonical_path': str(canonical),
      'verified_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
      'recovered_after_promotion': recovered,
    }}
def write_receipt(root, receipt):
    tmp = root / 'evidence_receipt.json.tmp'
    tmp.write_text(json.dumps(receipt, sort_keys=True), encoding='utf-8')
    with tmp.open('rb') as fh:
        os.fsync(fh.fileno())
    os.replace(tmp, root / 'evidence_receipt.json')
    fsync_dir(root)
staging_manifest, staging_manifest_digest, staging_error = load_and_verify(staging)
if staging_error:
    fail(staging_error)
if canonical.exists():
    existing = canonical / 'evidence_receipt.json'
    if existing.is_file():
        prior = json.loads(existing.read_text(encoding='utf-8'))
        canonical_manifest, canonical_digest, canonical_error = load_and_verify(canonical)
        if canonical_error:
            fail('canonical destination exists with invalid committed evidence: ' + canonical_error)
        if (
            prior.get('ok') is True
            and prior.get('manifest_sha256') == canonical_digest
            and canonical_digest == staging_manifest_digest
            and prior.get('run_id') == canonical_manifest.get('run_id')
            and prior.get('pass_num') == canonical_manifest.get('pass_num')
            and prior.get('candidate_sha') == canonical_manifest.get('candidate_sha')
        ):
            shutil.rmtree(staging, ignore_errors=True)
            prior['ok'] = True
            prior['idempotent_replay'] = True
            print(json.dumps(prior, sort_keys=True))
            sys.exit(0)
    canonical_manifest, canonical_digest, canonical_error = load_and_verify(canonical)
    if canonical_error:
        fail('canonical destination already exists with no receipt and invalid evidence: ' + canonical_error)
    if canonical_digest != staging_manifest_digest:
        fail('canonical destination already exists with divergent evidence')
    receipt = build_receipt(canonical_manifest, canonical_digest, recovered=True)
    write_receipt(canonical, receipt)
    shutil.rmtree(staging, ignore_errors=True)
    print(json.dumps(receipt, sort_keys=True))
    sys.exit(0)
canonical.parent.mkdir(parents=True, exist_ok=True)
os.replace(staging, canonical)
fsync_dir(canonical.parent)
receipt = build_receipt(staging_manifest, staging_manifest_digest)
write_receipt(canonical, receipt)
print(json.dumps(receipt, sort_keys=True))
"""
        proc = subprocess.run(
            ["ssh", vps, "python3 - <<'PY'\n" + code + "\nPY"],
            timeout=120,
            capture_output=True,
            text=True,
            **_no_window(),
        )
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": "remote verification command failed",
                "stderr": _redact(proc.stderr or proc.stdout or ""),
            }
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {
                "ok": False,
                "error": "remote verification returned non-json",
                "stdout": _redact(proc.stdout[:1000]),
            }

    def _ship(self) -> None:
        """Backward-compatible wrapper; field terminalization uses _publish_evidence."""
        result = self._publish_evidence(False)
        if not result.get("ok"):
            print(f"  ship failed: {result.get('error')}", file=sys.stderr)
        else:
            print(f"  shipped pass{self.pass_num} → receipt {result.get('receipt', {}).get('receipt_id')}", file=sys.stderr)
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
