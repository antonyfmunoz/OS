"""Producer/consumer agreement on the grant-binding correlation id.

The exact-correlation binding in ``wave2_field_dispatch._capture_execution_binding``
is fail-closed by design: it accepts exactly ONE grant whose ``correlation_id``
equals ``f"w2-{run_id}"``, so a parallel or prior run's ACTIVE grant can never be
mistaken for this run's. That gate is correct and is NOT relaxed here.

The defect these tests pin was entirely on the PRODUCER side, in two places:

1. ``wave2_field_collector`` computed ``f"w2-{run_id}-p{pass_num}"``. The
   dispatcher's ``run_id`` already carries the pass suffix, so the collector
   stamped ``w2-<stamp>-p1-p1`` — a doubled suffix the consumer could never
   match.
2. ``objective_plan_routes.try_chat_planning_rail`` hardcoded
   ``correlation_id=resolution.intent_id`` when minting the grant, discarding
   the collector's ``X-Correlation-ID`` header entirely. Every grant therefore
   carried an ``intent_*`` correlation, and NO grant the system could mint would
   ever satisfy the gate.

Field evidence: run ``20260805T062433Z-p1`` refused with
"0 execution-authorization grants carry exact correlation_id
'w2-20260805T062433Z-p1' (need exactly 1)", while the run's own live grant
carried ``intent_f14c647c77bd``.

No field quota is spent by these tests.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

COLLECTOR = Path(REPO) / "scripts" / "wave2_field_collector.py"
DISPATCH = Path(REPO) / "scripts" / "wave2_field_dispatch.py"
ROUTES = Path(REPO) / "transports" / "api" / "objective_plan_routes.py"
CHAT = Path(REPO) / "transports" / "api" / "cockpit_chat_routes.py"


# ── the contract itself ─────────────────────────────────────────────────────


def _producer_correlation(run_id: str, pass_num: int) -> str:
    """Evaluate the collector's ACTUAL correlation expression for (run_id, pass).

    Parsed out of the shipped source rather than re-typed, so a change to the
    collector's formula is what this test sees — not a copy of it that can drift.
    """
    tree = ast.parse(COLLECTOR.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if (
                isinstance(tgt, ast.Attribute)
                and tgt.attr == "correlation_id"
                and isinstance(tgt.value, ast.Name)
                and tgt.value.id == "self"
            ):
                expr = ast.unparse(node.value)
                return eval(  # noqa: S307 - evaluating our own f-string literal
                    expr, {"run_id": run_id, "pass_num": pass_num}
                )
    raise AssertionError("collector no longer assigns self.correlation_id")


def _consumer_correlation(run_id: str) -> str:
    """Evaluate the dispatcher's ACTUAL wanted-correlation expression."""
    tree = ast.parse(DISPATCH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "wanted_corr":
                    expr = ast.unparse(node.value)
                    return eval(  # noqa: S307 - our own expression
                        expr, {"run_id": run_id}
                    )
    raise AssertionError("dispatcher no longer computes wanted_corr")


@pytest.mark.parametrize(
    "run_id,pass_num",
    [
        ("20260805T062433Z-p1", 1),
        ("20260101T000000Z-p1", 1),
        ("20261231T235959Z-p2", 2),
        ("20260805T062433Z-p3", 3),
    ],
)
def test_producer_and_consumer_agree_on_the_correlation(run_id, pass_num):
    """THE contract: what the collector stamps is what the binding looks for.

    Kills the doubled-suffix mutation directly — with
    ``f"w2-{run_id}-p{pass_num}"`` restored, producer becomes
    ``w2-<stamp>-p1-p1`` and this fails for every case.
    """
    produced = _producer_correlation(run_id, pass_num)
    wanted = _consumer_correlation(run_id)
    assert produced == wanted, (
        f"producer stamps {produced!r} but the binding requires {wanted!r} — "
        f"the grant would be unbindable and every field run refuses"
    )


def test_correlation_carries_the_pass_suffix_exactly_once():
    """``run_id`` already ends in ``-pN``; the correlation must not double it."""
    corr = _producer_correlation("20260805T062433Z-p1", 1)
    assert corr == "w2-20260805T062433Z-p1"
    assert corr.count("-p1") == 1, f"pass suffix appears more than once in {corr!r}"
    assert not corr.endswith("-p1-p1")


def test_run_tag_is_not_the_binding_and_may_keep_its_shape():
    """``run_tag`` is an evidence/log tag, NOT part of the grant identity.

    It legitimately keeps the ``[w2-<run_id>-p<N>]`` form. This test exists so a
    future reader does not "fix" run_tag to match the correlation and think the
    binding changed — nothing binds on run_tag.
    """
    src = COLLECTOR.read_text(encoding="utf-8")
    assert 'self.run_tag = f"[w2-{run_id}-p{pass_num}]"' in src
    tree = ast.parse(DISPATCH.read_text(encoding="utf-8"))
    binding_fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_capture_execution_binding"
    )
    # strip the docstring — it legitimately explains why run_tag is excluded
    code_only = (
        binding_fn.body[1:]
        if (
            binding_fn.body
            and isinstance(binding_fn.body[0], ast.Expr)
            and isinstance(binding_fn.body[0].value, ast.Constant)
        )
        else binding_fn.body
    )
    code = "\n".join(ast.unparse(n) for n in code_only)
    assert "run_tag" not in code, "the binding must never match on run_tag"


# ── the gate must stay fail-closed (NOT weakened) ───────────────────────────


def test_binding_still_requires_exactly_one_exact_match():
    """The consumer is unchanged: exact equality, exactly one grant, ACTIVE."""
    tree = ast.parse(DISPATCH.read_text(encoding="utf-8"))
    fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "_capture_execution_binding"
    )
    body = ast.unparse(fn)
    normalized = body.replace("'", '"').replace(" ", "")
    assert 'str(g.get("correlation_id",""))==wanted_corr' in normalized, (
        "the binding must match correlation by EXACT equality — no prefix, "
        "startswith, or normalization"
    )
    # the MATCH expression specifically must not be relaxed
    match_line = next(ln for ln in body.split("\n") if "wanted_corr" in ln and "grants = " in ln)
    for weakener in ("startswith(", ".lower()", "removesuffix", "rsplit", " in wanted_corr"):
        assert weakener not in match_line, (
            f"the binding match must not be weakened with {weakener!r}: {match_line.strip()[:120]}"
        )
    assert "len(grants) != 1" in body, "the binding must require exactly one grant"
    assert "!= 'active'" in body or '!= "active"' in body, (
        "the binding must require the grant be ACTIVE"
    )
    assert "len(grants) != 1" in body


def test_binding_refuses_zero_one_and_many(monkeypatch):
    """Behavioural: run the REAL binding against synthetic grant records."""
    import importlib.util

    sys.argv = ["wave2_field_dispatch.py"]
    for name in ("substrate", "substrate.execution", "substrate.execution.attempts"):
        __import__(name)
    spec = importlib.util.spec_from_file_location("_wfd_corr", str(DISPATCH))
    m = importlib.util.module_from_spec(spec)
    sys.modules["_wfd_corr"] = m
    spec.loader.exec_module(m)

    run_id = "20260805T062433Z-p1"
    sha = "0" * 40
    wanted = f"w2-{run_id}"

    def grant(corr, status="active", gid="g1"):
        return {
            "grant_id": gid,
            "task_frontier": ["wp-a"],
            "correlation_id": corr,
            "status": status,
            "plan_record_id": "opr-1",
            "plan_version": 1,
            "decision_ref": "objective_plan:opr-1:execution_authorization:v1",
            "tenant_id": "t",
            "principal_id": "p",
            "membership_id": "m",
            "conversation_id": "c",
        }

    # zero matches — the observed field failure (grant carried intent_*)
    b, err = m._capture_execution_binding([grant("intent_f14c647c77bd")], sha=sha, run_id=run_id)
    assert b is None and "0 execution-authorization grants" in err

    # the OLD doubled suffix must still be refused
    b, err = m._capture_execution_binding([grant(f"{wanted}-p1")], sha=sha, run_id=run_id)
    assert b is None, "the doubled-suffix correlation must NOT bind"

    # two matches — ambiguous, refuse
    b, err = m._capture_execution_binding(
        [grant(wanted, gid="g1"), grant(wanted, gid="g2")], sha=sha, run_id=run_id
    )
    assert b is None and "2 execution-authorization grants" in err

    # matching but not ACTIVE — refuse
    b, err = m._capture_execution_binding([grant(wanted, status="revoked")], sha=sha, run_id=run_id)
    assert b is None and "not ACTIVE" in err

    # exactly one ACTIVE exact match — binds
    b, err = m._capture_execution_binding([grant(wanted)], sha=sha, run_id=run_id)
    assert b is not None, f"the correct grant must bind, got refusal: {err}"
    assert b.correlation_id == wanted


# ── producer plumbing: the header must reach the grant ──────────────────────


def test_rail_prefers_the_caller_correlation_over_the_intent_fallback():
    """``try_chat_planning_rail`` must mint the grant under the CALLER's
    correlation when one is supplied, falling back to the intent id otherwise.

    Kills the mutation that restores ``correlation_id=resolution.intent_id``.
    """
    tree = ast.parse(ROUTES.read_text(encoding="utf-8"))
    fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "try_chat_planning_rail"
    )
    assert "correlation_id" in {a.arg for a in fn.args.args}, (
        "the rail must accept a correlation_id from its caller"
    )
    call = next(
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Call)
        and getattr(n.func, "id", "") == "request_execution_authorization"
    )
    kw = {k.arg: ast.unparse(k.value) for k in call.keywords}
    assert kw.get("correlation_id") == "correlation_id or resolution.intent_id", (
        f"the grant must be minted under the caller's correlation when supplied; "
        f"got correlation_id={kw.get('correlation_id')!r}"
    )


def test_clarification_reentry_carries_the_correlation():
    """The clarification re-entry must not drop the correlation.

    Without this, any journey that asks a clarifying question mints its grant
    under the intent fallback — the same unbindable-grant defect on a path that
    only appears when clarification happens.
    """
    tree = ast.parse(ROUTES.read_text(encoding="utf-8"))
    fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "try_chat_planning_rail"
    )
    recursive = [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "try_chat_planning_rail"
    ]
    assert recursive, "expected the clarification re-entry call"
    for call in recursive:
        kw = {k.arg for k in call.keywords}
        assert "correlation_id" in kw, "the clarification re-entry must forward correlation_id"


def test_chat_route_reads_the_correlation_header_and_threads_it():
    """`/advisor/converse` must read ``X-Correlation-ID`` and pass it to the rail.

    This is the seam the collector actually drives; without it the header the
    collector already sends never reaches grant minting.
    """
    tree = ast.parse(CHAT.read_text(encoding="utf-8"))
    fn = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "advisor_converse"
    )
    body = ast.unparse(fn)
    assert "x-correlation-id" in body.lower(), (
        "the chat route must read the X-Correlation-ID header"
    )
    call = next(
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "try_chat_planning_rail"
    )
    kw = {k.arg for k in call.keywords}
    assert "correlation_id" in kw, "the chat route must thread correlation_id to the rail"


def test_header_read_never_breaks_chat_when_absent():
    """Ordinary chat sends no correlation header — that must be harmless."""
    tree = ast.parse(CHAT.read_text(encoding="utf-8"))
    fn = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "advisor_converse"
    )
    body = ast.unparse(fn)
    assert "try" in body and "except" in body, (
        "the header read must be guarded — a header failure must never break chat"
    )
