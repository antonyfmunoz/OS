"""Wave 2 collector w15 async-render-retry invariant.

Regression pin for field run 20260725T171015Z-p1, where the full pass failed at
w15 (`authorize_execution authorized=False decision_response=<empty>`) while the
backend grant was correctly still ACTIVATING and approvable.

Root cause: the Top HUD renders the pending-approval list from an ASYNC poll of
/unified-approval. w14 (which READS the execution-decision row) tolerates that
with a retry loop up to 60s; w15 (which CLICKS the approve button on the same
row) did a single `_open_approvals` + immediate `row.count()` check, racing the
poll — the row was momentarily absent, the click block was skipped, and the
stage failed with an EMPTY decision_response. No worker quota was spent (workers
only start after authorization).

Invariant: `_w15_authorize_execution` must retry finding the APPROVE BUTTON
(mirroring w14's tolerance) before clicking — a deadline-bounded loop that
re-opens the approvals surface — so the async render can't produce a false
`authorized=False`. Source-level test; it does not drive Playwright.
"""

from __future__ import annotations

import ast
from pathlib import Path

_COLLECTOR = (
    Path(__file__).resolve().parent.parent / "scripts" / "wave2_field_collector.py"
)


def _method_source(class_hint: str, method: str) -> str:
    tree = ast.parse(_COLLECTOR.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method:
            return ast.get_source_segment(_COLLECTOR.read_text(encoding="utf-8"), node) or ""
    return ""


def test_collector_exists() -> None:
    assert _COLLECTOR.exists(), _COLLECTOR


def test_w15_retries_for_the_approve_button_before_clicking() -> None:
    src = _method_source("W2FieldCollector", "_w15_authorize_execution")
    assert src, "could not locate _w15_authorize_execution"
    # Must have a deadline-bounded retry loop (like w14) — not a single-shot check.
    assert "while time.time() < deadline" in src, (
        "w15 must retry until the approve button appears (async HUD render); "
        "a single _open_approvals + immediate click races the poll"
    )
    # The retry must re-open the approvals surface each iteration.
    assert src.count("_open_approvals") >= 1, "w15 must re-open the approvals surface while retrying"
    # It must locate the approve button (not just the row) before deciding it can click.
    assert "W2_EXEC_APPROVE_BTN" in src, "w15 must confirm the approve button is present"
    # A missing button must be reported as a distinct, non-empty reason (never a
    # bare empty decision_response that reads like a backend refusal).
    assert "approve-button-never-appeared" in src, (
        "w15 must surface a distinct reason when the button never renders, "
        "not an empty decision_response"
    )


def test_w14_and_w15_share_the_same_async_render_tolerance() -> None:
    """Both read/act on the same async-rendered row → both must retry."""
    w14 = _method_source("W2FieldCollector", "_w14_hud_execution_row")
    w15 = _method_source("W2FieldCollector", "_w15_authorize_execution")
    assert "while time.time() < deadline" in w14
    assert "while time.time() < deadline" in w15
