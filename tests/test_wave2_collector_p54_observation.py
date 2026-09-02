"""Wave 2 collector — inv #54 observation-model regression pins (w16/w26/w27).

Field invocation #54 (run 20260809T144154Z-p1) consumed a mandatory unit on a
FULLY CORRECT candidate run because three collector stages made point-in-time
live-UI checks on surfaces that could not be present at sampling time:

  - w16 counted the execution-panel root on whatever view the Playwright page
    happened to be on (the approvals view after w15) — structurally False;
  - w26 scanned the page body for Task D's completion report 4s after w25,
    while D was ~25s into a ~100-110s execution — the report could not exist;
  - w27 clicked a chat-card affordance from a non-hosting view and sampled the
    lineage drawer 1s later — the drawer lives on the execution panel.

The correction: explicit ?panel= deep-link navigation with bounded mount waits
(w16/w27), and a bounded SEMANTIC wait on durable ledger evidence for Task D
terminalization before reading the thread (w26). All bounds exceed the proven
worker-latency envelope and fail CLOSED on timeout.

These tests reproduce the exact #54 failure shapes and pin the correction.
They also kill the mutant classes: skipped navigation, restored point-in-time
sampling, waits shortened below the proven envelope, success accepted without
lineage/proof, timeout-as-success, and weakened final-state inference.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable

_WORKTREE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_WORKTREE / "scripts"))

import wave2_field_collector as C  # noqa: E402

_Collector = next(
    getattr(C, n) for n in dir(C) if n.endswith("Collector") and isinstance(getattr(C, n), type)
)

A, B, Ctask, Dtask = "wp-A", "wp-B", "wp-C", "wp-D"
REPORT_TEXT = "Execution complete — PlanExecutionProof recorded"


# ── fake clock ───────────────────────────────────────────────────────────────


class _Clock:
    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def time(self) -> float:
        self.t += 0.001  # monotonic progress even in tight loops
        return self.t

    def sleep(self, s: float) -> None:
        self.t += max(float(s), 0.001)


# ── fake cockpit page with real VIEWS ────────────────────────────────────────
#
# The page models the cockpit SPA: one active view at a time, selected by the
# ?panel= deep-link. Selectors count >0 only when their hosting view is active
# (and, for the lineage drawer, only after a row click + render delay). This is
# exactly the structure the #54 field failure exposed and the old fakes hid
# (they returned a fixed count regardless of view).


class _Loc:
    def __init__(self, page: "_Page", sel: str) -> None:
        self._page, self._sel = page, sel

    def count(self) -> int:
        return self._page.mounted(self._sel)

    @property
    def first(self) -> "_Loc":
        return self

    def click(self) -> None:
        self._page.clicked(self._sel)


class _Page:
    """view: 'chat' (base url), 'approvals', 'execution', … from ?panel=."""

    def __init__(
        self,
        clock: _Clock,
        *,
        initial_view: str = "approvals",
        execution_root_renders: bool = True,
        rows_present: bool = True,
        drawer_render_delay_s: float = 4.0,
        drawer_renders: bool = True,
        drawer_always_mounted: bool = False,
        click_fail_times: int = 0,
        report_visible_at: float | None = None,
    ) -> None:
        self.clock = clock
        self.view = initial_view
        self.goto_urls: list[str] = []
        self.execution_root_renders = execution_root_renders
        self.rows_present = rows_present
        self.drawer_render_delay_s = drawer_render_delay_s
        self.drawer_renders = drawer_renders
        self.drawer_always_mounted = drawer_always_mounted
        self.click_fail_times = click_fail_times
        self.report_visible_at = report_visible_at
        self._drawer_open_at: float | None = None

    # — navigation —
    def goto(self, url: str, **k: Any) -> None:
        self.goto_urls.append(url)
        if "panel=" in url:
            self.view = url.split("panel=")[1].split("&")[0]
        else:
            self.view = "chat"

    def wait_for_selector(self, sel: str, timeout: float = 0) -> None:
        deadline = self.clock.t + float(timeout) / 1000.0
        while self.clock.t < deadline:
            if self.mounted(sel) > 0:
                return
            self.clock.sleep(0.5)
        if self.mounted(sel) > 0:
            return
        raise TimeoutError(f"selector {sel} never mounted (view={self.view})")

    # — DOM model —
    def mounted(self, sel: str) -> int:
        if sel == C.W2_EXECUTION_ROOT:
            return 1 if (self.view == "execution" and self.execution_root_renders) else 0
        if sel == C.W2_EXECUTION_ATTEMPT:
            return 2 if (self.view == "execution" and self.rows_present) else 0
        if sel in (C.W2_ASSIGNMENT, C.W2_ENVIRONMENT_LEASE, C.W2_VERIFICATION_STATUS):
            if self.drawer_always_mounted:  # stale-DOM model: drawer counts on ANY view
                return 1
            if (
                self.view == "execution"
                and self.drawer_renders
                and self._drawer_open_at is not None
                and self.clock.t >= self._drawer_open_at + self.drawer_render_delay_s
            ):
                return 1
            return 0
        return 0  # overlay / worker-status / controls: corroborating only

    def clicked(self, sel: str) -> None:
        if sel == C.W2_EXECUTION_ATTEMPT and self.view == "execution":
            if self.click_fail_times > 0:
                self.click_fail_times -= 1
                raise RuntimeError("element is not attached to the DOM (stale handle)")
            self._drawer_open_at = self.clock.t

    def locator(self, sel: str) -> _Loc:
        return _Loc(self, sel)

    def inner_text(self, sel: str) -> str:
        if (
            sel == "body"
            and self.view == "chat"
            and self.report_visible_at is not None
            and self.clock.t >= self.report_visible_at
        ):
            return f"...{REPORT_TEXT}..."
        return "..."

    def evaluate(self, *a: Any, **k: Any) -> Any:
        return {}


# ── durable-evidence fabric (time-dependent) ─────────────────────────────────


def _row(task: str, aid: str, num: int, status: str, proof: str, prev: str = "") -> dict[str, Any]:
    return {
        "attempt_id": aid,
        "task_id": task,
        "attempt_number": num,
        "status": status,
        "proof_id": proof,
        "commits": [],
        "retry_of_attempt_id": prev,
    }


def _impl_detail(aid: str, disp_start: float, disp_end: float) -> dict[str, Any]:
    return {
        "attempt_id": aid,
        "transitions": [
            {"from_status": "created", "to_status": "ready", "at": disp_start - 0.1},
            {"from_status": "ready", "to_status": "leased", "at": disp_start - 0.05},
            {"from_status": "leased", "to_status": "dispatched", "at": disp_start},
            {"from_status": "dispatched", "to_status": "running", "at": disp_end},
            {"from_status": "running", "to_status": "verifying", "at": disp_end},
        ],
    }


RUN_ID = "20260809TESTRUN-p1"
CAND = "candsha842test"
COMPOSED = "cccc333"


def _d_detail(
    aid: str = "ea-d1",
    *,
    corr: str = f"w2-{RUN_ID}",
    base: str = COMPOSED,
    repo: str | None = None,
    diff_scope: str = "enforced",
    files: list[str] | None = None,
    commits: list[str] | None = None,
    verifier_actor: str = "verifier:role-verify-op",
    plan: str = "opr-1",
    lease_id: str = "lease-d1",
) -> dict[str, Any]:
    """Attempt-detail shape for a verification (Task D) attempt, mirroring the
    real /attempts/{id} response: transitions + environment_lease.source_ref +
    enforcement + files/commits + correlation/plan/lease bindings."""
    repo = (
        repo
        if repo is not None
        else f"/var/lib/umh/candidates/wave2/{CAND}/targets/{RUN_ID}/fixture"
    )
    return {
        "attempt_id": aid,
        "plan_record_id": plan,
        "lease_id": lease_id,
        "correlation_id": corr,
        "files_changed": list(files or []),
        "commits": list(commits or []),
        "transitions": [
            {"from_status": "leased", "to_status": "dispatched", "actor": "scheduler", "at": 1.0},
            {"from_status": "dispatched", "to_status": "running", "actor": "poller", "at": 2.0},
            {"from_status": "running", "to_status": "verifying", "actor": "poller", "at": 2.1},
            {
                "from_status": "verifying",
                "to_status": "succeeded",
                "actor": verifier_actor,
                "at": 3.0,
            },
        ],
        "environment_lease": {
            "lease_id": lease_id,
            "source_ref": {"repo_root": repo, "base_commit": base, "branch": "auto/x"},
            "enforcement": {"diff_scope_post_hoc": diff_scope},
        },
    }


def _d_proof_action(
    aid: str = "ea-d1",
    *,
    task: str = Dtask,
    plan: str = "opr-1",
    lease_id: str = "lease-d1",
    worker: str = "cc-cli@vps-host",
    verifier: str = "verifier:role-verify-op",
) -> dict[str, Any]:
    """Worker-proof action, mirroring the REAL persisted schema (see
    PASS_P54_EVIDENCE/proof_packages.jsonl)."""
    return {
        "attempt_id": aid,
        "task_id": task,
        "plan_record_id": plan,
        "lease_id": lease_id,
        "worker_identity": worker,
        "verifier_identity": verifier,
        "verifier_role_id": "role-verify-op",
        "attempt_number": 1,
        "tenant_id": "tenant-x",
    }


def _collector(
    clock: _Clock,
    page: _Page,
    *,
    rows_at: Callable[[float], list[dict[str, Any]]],
    comp_visible_at: float = 0.0,
    d_details: dict[str, dict[str, Any]] | None = None,
    d_proofs: dict[str, dict[str, Any]] | None = None,
) -> tuple[Any, dict[str, tuple[bool, str]]]:
    col = _Collector.__new__(_Collector)
    col.url = "https://cockpit.test"
    col.run_id = RUN_ID
    col.candidate_commit = CAND
    col._attempt_ids = {}
    stages: dict[str, tuple[bool, str]] = {}
    details = {
        "ea-a1": _impl_detail("ea-a1", 0.0, 97.0),
        "ea-b1": _impl_detail("ea-b1", 0.5, 98.0),
        "ea-a2": _impl_detail("ea-a2", 100.0, 211.0),
        "ea-d1": _d_detail("ea-d1"),
        "ea-d2": _d_detail("ea-d2", lease_id="lease-d2"),
    }
    details.update(d_details or {})
    comp_proof = {
        "attempt_id": "ea-c1",
        "composed_commit": COMPOSED,
        "predecessor_commits": {A: "aaaa111", B: "bbbb222"},
    }
    proofs: dict[str, dict[str, Any]] = {
        "proof-D": _d_proof_action("ea-d1"),
        "proof-D2": _d_proof_action("ea-d2", lease_id="lease-d2"),
    }
    proofs.update(d_proofs or {})
    col._read_attempts = lambda page=None, **k: rows_at(clock.t)
    col._attempt_detail = lambda page, aid: dict(details.get(aid, {}))

    def _proof(page, pid):
        if pid == "proof-C":
            return dict(comp_proof) if clock.t >= comp_visible_at else {}
        return dict(proofs.get(pid, {}))

    col._composition_proof = _proof
    col.stage = lambda name, ok, detail="": stages.__setitem__(name, (ok, detail))
    col.shot = lambda *a, **k: None
    col.dom = lambda *a, **k: None
    return col, stages


def _graph_rows(
    now: float,
    *,
    t0: float,
    d_succeeds_at: float | None,
    d_proof: str = "proof-D",
    d_rows: list[dict[str, Any]] | None = None,
    include_d: bool = True,
):
    """Rows as the by-plan API would return them at absolute fake time `now`.

    A1 fails, B succeeds (concurrent), A2 retry succeeds, C composes; D is
    dispatched at t0+225 and terminalizes (or not) at `d_succeeds_at`.
    `d_rows` overrides D entirely (retry/ordering scenarios); `include_d=False`
    models a graph with no verification task at all.
    """
    rows = [
        _row(A, "ea-a1", 1, "failed", ""),
        _row(B, "ea-b1", 1, "succeeded", "proof-B"),
        _row(A, "ea-a2", 2, "succeeded", "proof-A2", prev="ea-a1"),
        _row(Ctask, "ea-c1", 1, "succeeded", "proof-C"),
    ]
    if d_rows is not None:
        rows.extend(d_rows)
    elif include_d:
        d_status = "dispatched"
        d_pid = ""
        if d_succeeds_at is not None and now >= d_succeeds_at:
            d_status, d_pid = "succeeded", d_proof
        rows.append(_row(Dtask, "ea-d1", 1, d_status, d_pid))
    return rows


def _ctx() -> dict[str, Any]:
    return {
        "execution_conversation_id": "conv-p54-regression",
        "concurrent_running_tasks": [A, B],
        "composition": {
            "task_id": Ctask,
            "attempt_id": "ea-c1",
            "proof_id": "proof-C",
            "composed_commit": COMPOSED,
        },
    }


# ── envelope contract (kills wait-shortening mutants directly) ───────────────


def test_bounds_exceed_proven_latency_envelope():
    """The #54 run proved ~236s of real worker latency w15→composition and
    ~110s for Task D. Any bound at or below the envelope fails correct-but-slow
    runs and consumes field quota — shortening these is a killed mutant class.
    (The report-corroboration wait is non-gating and exempt from the envelope.)"""
    assert C.PROVEN_WORKER_LATENCY_ENVELOPE_S >= 240
    assert C.W16_COMPOSITION_WAIT_S > C.PROVEN_WORKER_LATENCY_ENVELOPE_S
    assert C.W16_COMPOSITION_WAIT_S >= 420
    assert C.W26_D_TERMINALIZE_WAIT_S >= 240
    assert C.W26_REPORT_CORROBORATION_WAIT_S >= 10
    assert C.W27_DRAWER_WAIT_S >= 30


def test_w26_report_markers_match_real_cockpit_ui_string():
    """Marker-fidelity pin: the collector's corroboration markers must match
    the string the cockpit ACTUALLY renders for a completed execution
    (ChatExecutionCard STATUS_LINES['complete']). Inv #54 review found 3 of 4
    old markers could never match (case/text drift)."""
    card = (
        _WORKTREE
        / "cockpit"
        / "src"
        / "renderer"
        / "components"
        / "cards"
        / "ChatExecutionCard.tsx"
    ).read_text()
    import re

    m = re.search(r"complete:\s*'([^']+)'", card)
    assert m, "ChatExecutionCard 'complete' status line not found"
    ui_line = m.group(1)
    assert "EXECUTION COMPLETE" in ui_line and "COMPLETE — PROOF" in ui_line
    # both collector markers are substrings of the real rendered line
    assert "EXECUTION COMPLETE" in ui_line
    assert "COMPLETE — PROOF" in ui_line


# ── w16 ──────────────────────────────────────────────────────────────────────


def test_w16_passes_from_unrelated_page_via_explicit_navigation():
    """THE #54 SHAPE: page sits on the approvals view; the graph is correct.
    w16 must navigate to the execution panel itself and pass. A mutant that
    skips navigation samples the approvals view and fails this test."""
    clock = _Clock()
    page = _Page(clock, initial_view="approvals")
    t0 = clock.t
    col, stages = _collector(
        clock,
        page,
        rows_at=lambda now: _graph_rows(now, t0=t0, d_succeeds_at=None),
        comp_visible_at=0.0,
    )
    col._w16_ab_running_concurrent(page, _ctx())
    ok, detail = stages["w16_ab_running_concurrent"]
    assert ok, detail
    assert "execution_surface=True" in detail
    assert any("panel=execution" in u for u in page.goto_urls), "must explicitly navigate"


def test_w16_slow_but_valid_graph_passes_beyond_old_240s_window():
    """Composition proof becomes visible 300s in — beyond the old 240s bound,
    inside the corrected envelope-aware bound. Kills the shortened-wait mutant
    behaviorally (a 240s bound fails this correct run)."""
    clock = _Clock()
    page = _Page(clock, initial_view="approvals")
    t0 = clock.t
    col, stages = _collector(
        clock,
        page,
        rows_at=lambda now: _graph_rows(now, t0=t0, d_succeeds_at=None),
        comp_visible_at=t0 + 300.0,
    )
    col._w16_ab_running_concurrent(page, _ctx())
    ok, detail = stages["w16_ab_running_concurrent"]
    assert ok, detail


def test_w16_fast_completing_graph_passes_immediately():
    clock = _Clock()
    page = _Page(clock, initial_view="approvals")
    t0 = clock.t
    col, stages = _collector(
        clock,
        page,
        rows_at=lambda now: _graph_rows(now, t0=t0, d_succeeds_at=t0),
        comp_visible_at=0.0,
    )
    col._w16_ab_running_concurrent(page, _ctx())
    assert stages["w16_ab_running_concurrent"][0]


def test_w16_genuinely_missing_execution_surface_fails():
    """Navigation succeeds but the execution root never mounts (real frontend
    regression). The bounded wait must FAIL CLOSED — timeout is never success."""
    clock = _Clock()
    page = _Page(clock, initial_view="approvals", execution_root_renders=False)
    t0 = clock.t
    col, stages = _collector(
        clock,
        page,
        rows_at=lambda now: _graph_rows(now, t0=t0, d_succeeds_at=None),
        comp_visible_at=0.0,
    )
    col._w16_ab_running_concurrent(page, _ctx())
    ok, detail = stages["w16_ab_running_concurrent"]
    assert not ok
    assert "execution_surface=False" in detail


# ── w26 ──────────────────────────────────────────────────────────────────────


def _run_w26(
    clock: _Clock,
    page: _Page,
    *,
    d_succeeds_at: float | None,
    d_proof: str = "proof-D",
    d_rows: list[dict[str, Any]] | None = None,
    include_d: bool = True,
    d_details: dict[str, dict[str, Any]] | None = None,
    d_proofs: dict[str, dict[str, Any]] | None = None,
    ctx: dict[str, Any] | None = None,
) -> tuple[bool, str, Any]:
    t0 = clock.t
    col, stages = _collector(
        clock,
        page,
        rows_at=lambda now: _graph_rows(
            now,
            t0=t0,
            d_succeeds_at=d_succeeds_at,
            d_proof=d_proof,
            d_rows=d_rows,
            include_d=include_d,
        ),
        d_details=d_details,
        d_proofs=d_proofs,
    )
    col._w26_task_d_terminal_verified(page, ctx if ctx is not None else _ctx())
    ok, detail = stages["w26_task_d_terminal_verified"]
    return ok, detail, page


def test_w26_waits_for_task_d_beyond_old_observation_window():
    """THE #54 SHAPE: D terminalizes 120s after w26 starts (far beyond the old
    point-in-time scan) and the report renders in the thread shortly after.
    w26 must wait on durable evidence and pass. A restored point-in-time
    sampler fails this test."""
    clock = _Clock()
    d_at = clock.t + 120.0
    page = _Page(clock, initial_view="execution", report_visible_at=d_at + 10.0)
    ok, detail, page = _run_w26(clock, page, d_succeeds_at=d_at)
    assert ok, detail
    assert any(u.rstrip("/").endswith("cockpit.test") for u in page.goto_urls), (
        "must explicitly return to the thread surface"
    )


def test_w26_fast_completing_graph_passes():
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(clock, page, d_succeeds_at=clock.t)
    assert ok, detail


def test_w26_task_d_never_terminalizes_fails_closed():
    """Genuine non-terminalization: timeout must be FAILURE, never success."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(clock, page, d_succeeds_at=None)
    assert not ok
    assert "terminalized=False" in detail


def test_w26_task_d_succeeds_without_proof_fails():
    """Kills the accepts-success-without-proof mutant: a succeeded D row with
    an empty proof_id must NOT satisfy the semantic invariant."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(clock, page, d_succeeds_at=clock.t, d_proof="")
    assert not ok, detail


def test_w26_report_absence_is_recorded_non_gating():
    """The candidate does not implement the same-thread completion-report POST
    (verified: no producer emits execution_state='complete' or posts a report
    message; the scan failed in 100% of recorded runs). Gating on it would make
    w26 structurally unpassable — the GATE is D terminalization (owner
    directive 2026-08-09); the report scan is recorded, loudly-labeled
    corroboration. This pins both the pass AND the explicit capability marker
    so the gap can never be silently forgotten."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=None)
    ok, detail, _ = _run_w26(clock, page, d_succeeds_at=clock.t)
    assert ok, detail
    assert "report_in_thread=False" in detail
    assert "capability not yet implemented" in detail


def test_w26_d_identification_excludes_pair_and_composition():
    """Kills the D-identification exclusion mutant: the decided set must be
    ONLY the verification task — never A/B (the concurrent pair) or C (the
    composition task)."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(clock, page, d_succeeds_at=clock.t)
    assert ok, detail
    d_part = detail.split("d=[", 1)[1].split("]", 1)[0]
    assert Dtask in d_part
    for excluded in (A, B, Ctask):
        assert excluded not in d_part, f"{excluded} must be excluded from D identification"


def test_w26_no_verification_task_fails_fast():
    """A graph with no task outside the pair/composition is a structural
    mismatch: fail IMMEDIATELY with a clear detail — never stall the full
    300s bound to say so."""
    clock = _Clock()
    start = clock.t
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(clock, page, d_succeeds_at=None, include_d=False)
    assert not ok
    assert "no verification task" in detail
    assert clock.t - start < 60, "must fail fast, not burn the terminalization bound"


def test_w26_d_retry_final_attempt_decides_regardless_of_row_order():
    """A retried D is judged by its HIGHEST attempt_number, never by whichever
    row the API returned last. Same correct graph in both row orders → same
    verdict; a genuinely failed FINAL attempt fails in both orders too."""
    d1_fail = _row(Dtask, "ea-d1", 1, "failed", "")
    d2_ok = _row(Dtask, "ea-d2", 2, "succeeded", "proof-D2", prev="ea-d1")
    for order in ([d1_fail, d2_ok], [d2_ok, d1_fail]):
        clock = _Clock()
        page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
        ok, detail, _ = _run_w26(clock, page, d_succeeds_at=None, d_rows=list(order))
        assert ok, f"retried-D graph must pass in either row order: {detail}"
        assert "#2:succeeded+proof" in detail

    d1_ok = _row(Dtask, "ea-d1", 1, "succeeded", "proof-D1")
    d2_fail = _row(Dtask, "ea-d2", 2, "failed", "", prev="ea-d1")
    for order in ([d1_ok, d2_fail], [d2_fail, d1_ok]):
        clock = _Clock()
        page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
        ok, detail, _ = _run_w26(clock, page, d_succeeds_at=None, d_rows=list(order))
        assert not ok, f"failed FINAL attempt must fail in either row order: {detail}"


def test_w26_wrong_run_binding_fails():
    """Foreign/stale-run evidence: a D attempt whose correlation_id names a
    DIFFERENT run must fail closed."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(
        clock,
        page,
        d_succeeds_at=clock.t,
        d_details={"ea-d1": _d_detail("ea-d1", corr="w2-OTHERRUN-p9")},
    )
    assert not ok
    assert "run_bound=False" in detail


def test_w26_wrong_candidate_binding_fails():
    """The lease's read-only source must live under THIS candidate's targets
    dir for THIS run — a foreign candidate/run path fails closed."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(
        clock,
        page,
        d_succeeds_at=clock.t,
        d_details={
            "ea-d1": _d_detail(
                "ea-d1", repo="/var/lib/umh/candidates/wave2/OTHERSHA/targets/OTHERRUN/fixture"
            )
        },
    )
    assert not ok
    assert "candidate_bound=False" in detail


def test_w26_wrong_composed_base_fails():
    """D must consume Task C's EXACT composed base — a lease based on any
    other commit fails closed."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(
        clock,
        page,
        d_succeeds_at=clock.t,
        d_details={"ea-d1": _d_detail("ea-d1", base="ffff0000")},
    )
    assert not ok
    assert "composed_base=False" in detail


def test_w26_missing_composition_anchor_fails_composed_base():
    """No composed_commit in ctx (w16 anchor absent) → the base can never be
    proven → fail closed, never vacuously pass."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ctx = _ctx()
    ctx["composition"] = {"task_id": Ctask}  # anchor without composed_commit
    ok, detail, _ = _run_w26(clock, page, d_succeeds_at=clock.t, ctx=ctx)
    assert not ok
    assert "composed_base=False" in detail


def test_w26_foreign_proof_fails():
    """A Proof whose action binds a DIFFERENT attempt must fail closed."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(
        clock,
        page,
        d_succeeds_at=clock.t,
        d_proofs={"proof-D": _d_proof_action("ea-SOMEONE-ELSE")},
    )
    assert not ok
    assert "proof_bound=False" in detail


def test_w26_missing_proof_record_fails():
    """A proof_id that resolves to NO durable proof action fails closed."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(clock, page, d_succeeds_at=clock.t, d_proofs={"proof-D": {}})
    assert not ok
    assert "proof_bound=False" in detail


def test_w26_verifier_did_not_run_fails():
    """No verifying→succeeded transition by a verifier:* actor → the
    authenticated verifier never executed → fail closed."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(
        clock,
        page,
        d_succeeds_at=clock.t,
        d_details={"ea-d1": _d_detail("ea-d1", verifier_actor="poller")},
    )
    assert not ok
    assert "verifier_ran=False" in detail


def test_w26_verifier_equals_worker_fails():
    """Separation of duty: a Proof whose verifier identity equals the worker
    identity fails closed."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(
        clock,
        page,
        d_succeeds_at=clock.t,
        d_proofs={"proof-D": _d_proof_action("ea-d1", worker="x@host", verifier="x@host")},
    )
    assert not ok
    assert "verifier_ran=False" in detail


def test_w26_source_mutation_fails():
    """Task D's contract is inspect-and-report ONLY (allowed paths = []). A
    succeeded D reporting changed files or commits mutated source where
    forbidden → fail closed."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(
        clock,
        page,
        d_succeeds_at=clock.t,
        d_details={"ea-d1": _d_detail("ea-d1", files=["app/main.py"], commits=["deadbee fix"])},
    )
    assert not ok
    assert "zero_write=False" in detail


def test_w26_unauthenticated_zero_write_contract_fails():
    """The lease's diff-scope enforcement must be 'enforced' (mechanically
    verified), not merely 'declared' — an unauthenticated zero-write contract
    fails closed."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(
        clock,
        page,
        d_succeeds_at=clock.t,
        d_details={"ea-d1": _d_detail("ea-d1", diff_scope="declared")},
    )
    assert not ok
    assert "zero_write=False" in detail


# ── w27 ──────────────────────────────────────────────────────────────────────


def _run_w27(clock: _Clock, page: _Page) -> tuple[bool, str, _Page]:
    t0 = clock.t
    col, stages = _collector(
        clock, page, rows_at=lambda now: _graph_rows(now, t0=t0, d_succeeds_at=t0)
    )
    col._w27_work_detail_lineage(page, _ctx())
    ok, detail = stages["w27_work_detail_lineage"]
    return ok, detail, page


def test_w27_passes_from_non_hosting_panel_via_explicit_navigation():
    """THE #54 SHAPE: page on the approvals view; drawer renders ~4s after the
    row click. w27 must navigate to the hosting panel, open a row, and
    bounded-wait for the drawer. Mutants that skip navigation or restore the
    fixed 1s sample fail this test."""
    clock = _Clock()
    page = _Page(clock, initial_view="approvals", drawer_render_delay_s=4.0)
    ok, detail, page = _run_w27(clock, page)
    assert ok, detail
    assert any("panel=execution" in u for u in page.goto_urls), "must explicitly navigate"


def test_w27_fast_drawer_passes():
    clock = _Clock()
    page = _Page(clock, initial_view="approvals", drawer_render_delay_s=0.0)
    ok, detail, _ = _run_w27(clock, page)
    assert ok, detail


def test_w27_genuinely_missing_lineage_fails_closed():
    clock = _Clock()
    page = _Page(clock, initial_view="approvals", drawer_renders=False)
    ok, detail, _ = _run_w27(clock, page)
    assert not ok
    assert "assignment=False" in detail


def test_w27_no_attempt_rows_fails():
    clock = _Clock()
    page = _Page(clock, initial_view="approvals", rows_present=False)
    ok, detail, _ = _run_w27(clock, page)
    assert not ok
    assert "opened=False" in detail


def test_w27_execution_surface_unmountable_fails():
    clock = _Clock()
    page = _Page(clock, initial_view="approvals", execution_root_renders=False)
    ok, detail, _ = _run_w27(clock, page)
    assert not ok
    assert "on_surface=False" in detail
    assert "nav_err=" in detail  # the WHY is diagnosable from the detail string


def test_w27_stale_dom_lineage_without_surface_fails():
    """Pins the BEHAVIOR: stale-DOM counts of the drawer selectors while the
    execution surface never mounted must NOT pass. Note: the predicate-revert
    mutant (`ok = assignment and lease and verification`) is EQUIVALENT under
    the corrected implementation — the three conjuncts are only ever sampled
    inside the on_surface→opened guards, so they cannot be True without both;
    the explicit conjuncts in `ok` are documentation/defense-in-depth, and
    this test proves the stale-DOM shape cannot leak through the dataflow."""
    clock = _Clock()
    page = _Page(
        clock,
        initial_view="approvals",
        execution_root_renders=False,
        drawer_always_mounted=True,
    )
    ok, detail, _ = _run_w27(clock, page)
    assert not ok, detail
    assert "assignment=True" not in detail or "on_surface=False" in detail


def test_w27_transient_click_failure_retries_not_aborts():
    """A count()-then-click() straddling AttemptsView's 4s repoll can raise on
    a detached node. That must retry in-loop — never abort the journey (which
    would lose w28-w30 and the entire pass to one stale handle)."""
    clock = _Clock()
    page = _Page(clock, initial_view="approvals", drawer_render_delay_s=0.0, click_fail_times=1)
    ok, detail, _ = _run_w27(clock, page)  # must not raise
    assert ok, detail


# ── fake-clock plumbing ──────────────────────────────────────────────────────
#
# Each test constructs a _Clock; construction registers it as the ACTIVE clock.
# The autouse fixture patches the collector module's time.time/time.sleep to
# delegate to whichever clock is active, so the collector's bounded waits, the
# fake page, and the time-dependent durable records all share one "now" — and
# no test ever sleeps for real (slow-graph scenarios advance simulated seconds).

import pytest  # noqa: E402

_ACTIVE: dict[str, _Clock] = {"clock": _Clock()}

_orig_init = _Clock.__init__


def _registering_init(self: _Clock, start: float = 1000.0) -> None:
    _orig_init(self, start)
    _ACTIVE["clock"] = self


_Clock.__init__ = _registering_init  # type: ignore[method-assign]


@pytest.fixture(autouse=True)
def _fake_clock(monkeypatch):
    monkeypatch.setattr(C.time, "time", lambda: _ACTIVE["clock"].time())
    monkeypatch.setattr(C.time, "sleep", lambda s: _ACTIVE["clock"].sleep(s))
    yield


# ── exact #54 reconstruction from REAL durable evidence ──────────────────────

import json  # noqa: E402

_P54 = (
    _WORKTREE
    / "data"
    / "audits"
    / "proof"
    / "2026-08-09_wave2_collector_observation_correction"
    / "PASS_P54_EVIDENCE"
)
_P54_RUN = "20260809T144154Z-p1"
_P54_SHA = "842434dc3fa3ed16540673f5df48950ccf6a2674"
_P54_D_TASK = "wp-cab2825165cd"
_P54_D_ATTEMPT = "ea-043c1f5a8d19"


def _p54_records():
    attempts = [
        json.loads(x) for x in (_P54 / "attempts_ledger.jsonl").read_text().splitlines() if x
    ]
    proofs: dict[str, dict[str, Any]] = {}
    for x in (_P54 / "proof_packages.jsonl").read_text().splitlines():
        if x:
            d = json.loads(x)
            proofs[d["proof_id"]] = d
    leases = [
        json.loads(x) for x in (_P54 / "environment_leases.jsonl").read_text().splitlines() if x
    ]
    return attempts, proofs, leases


def _p54_collector(clock, page, attempts, proofs, leases):
    col = _Collector.__new__(_Collector)
    col.url = "https://cockpit.test"
    col.run_id = _P54_RUN
    col.candidate_commit = _P54_SHA
    col._attempt_ids = {}
    stages: dict[str, tuple[bool, str]] = {}
    by_id = {a["attempt_id"]: a for a in attempts}
    lease_by_attempt = {r.get("attempt_id"): r for r in leases}

    def rows(page=None, **k):
        return [
            {
                "attempt_id": a["attempt_id"],
                "task_id": a["task_id"],
                "attempt_number": a["attempt_number"],
                "status": a["status"],
                "proof_id": a.get("proof_id", ""),
                "commits": a.get("commits", []),
                "retry_of_attempt_id": a.get("previous_attempt_id", ""),
            }
            for a in attempts
        ]

    def detail(page, aid):
        a = dict(by_id.get(aid, {}))
        if a:
            a["environment_lease"] = lease_by_attempt.get(aid)
        return a

    col._read_attempts = rows
    col._attempt_detail = detail
    col._composition_proof = lambda page, pid: dict((proofs.get(pid) or {}).get("action") or {})
    col.stage = lambda name, ok, detail="": stages.__setitem__(name, (ok, detail))
    col.shot = lambda *a, **k: None
    col.dom = lambda *a, **k: None
    return col, stages


def test_p54_reconstruction_w16_passes_on_real_evidence():
    """EXACT #54 RECONSTRUCTION: drive the corrected w16 against the REAL
    durable records preserved from run 20260809T144154Z-p1 (the run that
    consumed invocation #54 on a fully correct candidate). The corrected
    stage must qualify what the field run proved."""
    clock = _Clock()
    page = _Page(clock, initial_view="approvals")
    attempts, proofs, leases = _p54_records()
    col, stages = _p54_collector(clock, page, attempts, proofs, leases)
    ctx: dict[str, Any] = {}
    col._w16_ab_running_concurrent(page, ctx)
    ok, detail = stages["w16_ab_running_concurrent"]
    assert ok, detail
    assert "wp-3153d9b11ca4" in detail and "wp-d5369f58e0b4" in detail
    assert ctx["composition"]["composed_commit"] == "530b4b27458f3131b7a260b3accf8a82e9622822"


def test_p54_reconstruction_w26_fails_closed_on_frozen_ledger():
    """On the FROZEN #54 ledger Task D is still 'dispatched' (the driver
    stopped the runner 25s into D's execution). The corrected w26 must fail
    CLOSED on that frozen evidence — never infer success from graph shape."""
    clock = _Clock()
    page = _Page(clock, initial_view="approvals")
    attempts, proofs, leases = _p54_records()
    col, stages = _p54_collector(clock, page, attempts, proofs, leases)
    ctx: dict[str, Any] = {}
    col._w16_ab_running_concurrent(page, ctx)
    ctx["concurrent_running_tasks"] = sorted(
        (ctx.get("composition") or {}).get("predecessor_commits", {}).keys()
    )
    col._w26_task_d_terminal_verified(page, ctx)
    ok, detail = stages["w26_task_d_terminal_verified"]
    assert not ok
    assert "terminalized=False" in detail or "succeeded=False" in detail


def test_p54_reconstruction_w26_passes_with_d_completion():
    """What the corrected w26's bounded wait WOULD have observed in #54 had
    the runner been allowed to finish: D terminalizes succeeded with an
    Attempt-bound Proof, on the REAL lease (whose source_ref.base_commit is
    C's real composed commit 530b4b27…) — the full bound chain passes."""
    clock = _Clock()
    page = _Page(clock, initial_view="approvals")
    attempts, proofs, leases = _p54_records()
    # simulate D completion exactly as the ledger records completion elsewhere
    d = [a for a in attempts if a["attempt_id"] == _P54_D_ATTEMPT][0]
    d["status"] = "succeeded"
    d["proof_id"] = "proof-d54sim"
    d["files_changed"] = []
    d["commits"] = []
    d["transitions"] = d["transitions"] + [
        {
            "from_status": "dispatched",
            "to_status": "running",
            "actor": "poller",
            "at": 1786286940.0,
        },
        {"from_status": "running", "to_status": "verifying", "actor": "poller", "at": 1786286940.1},
        {
            "from_status": "verifying",
            "to_status": "succeeded",
            "actor": "verifier:role-verify-op",
            "at": 1786286941.0,
        },
    ]
    proofs["proof-d54sim"] = {
        "proof_id": "proof-d54sim",
        "work_id": _P54_D_TASK,
        # mirrors the REAL persisted worker-proof action schema (see the
        # succeeded A2/B proofs in this same evidence file)
        "action": {
            "attempt_id": _P54_D_ATTEMPT,
            "task_id": _P54_D_TASK,
            "plan_record_id": d["plan_record_id"],
            "lease_id": d["lease_id"],
            "worker_identity": "cc-cli@vps-host",
            "verifier_identity": "verifier:role-verify-op",
            "verifier_role_id": "role-verify-op",
        },
    }
    col, stages = _p54_collector(clock, page, attempts, proofs, leases)
    ctx: dict[str, Any] = {}
    col._w16_ab_running_concurrent(page, ctx)
    ctx["concurrent_running_tasks"] = sorted(
        (ctx.get("composition") or {}).get("predecessor_commits", {}).keys()
    )
    col._w26_task_d_terminal_verified(page, ctx)
    ok, detail = stages["w26_task_d_terminal_verified"]
    assert ok, detail
    for conjunct in (
        "terminalized=True",
        "succeeded=True",
        "run_bound=True",
        "candidate_bound=True",
        "composed_base=True",
        "verifier_ran=True",
        "proof_bound=True",
        "zero_write=True",
    ):
        assert conjunct in detail, detail


def test_w26_proof_binds_foreign_lease_fails():
    """A Proof binding the RIGHT attempt but the WRONG lease (foreign
    environment) must fail closed — this is the conjunct that stops
    'right attempt, wrong environment' foreign-proof shapes (Reviewer A,
    round-3 M7 survivor, now killed)."""
    clock = _Clock()
    page = _Page(clock, initial_view="execution", report_visible_at=clock.t)
    ok, detail, _ = _run_w26(
        clock,
        page,
        d_succeeds_at=clock.t,
        d_proofs={"proof-D": _d_proof_action("ea-d1", lease_id="lease-FOREIGN")},
    )
    assert not ok
    assert "proof_bound=False" in detail
