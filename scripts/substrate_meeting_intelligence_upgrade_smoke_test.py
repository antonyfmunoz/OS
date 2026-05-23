#!/usr/bin/env python3
"""
Smoke test for Meeting Intelligence Decision Upgrade.

Validates the additive bounded cognition upgrade:
  1. compute_scores produces deterministic pressure/ambiguity/priority.
  2. priority_level thresholds classify correctly (low / medium / high).
  3. Deterministic trigger still fires with no model available.
  4. refine_intervention_message uses the model path when it succeeds.
  5. refine_intervention_message is fallback-safe on model failure.
  6. Role-aware phrasing differs across ceo / ea_orchestrator / portfolio_advisor.
  7. Unknown role → raw passthrough (capped).
  8. maybe_emit_intervention records role + priority_level.
  9. intelligence_report_block includes scoring + actionable + memory counts.
 10. Bounds: refined message <= MAX_REFINED_MESSAGE_CHARS; caps still enforced.

Prints:
    MEETING INTELLIGENCE UPGRADE SMOKE TEST PASSED
"""

from __future__ import annotations

import sys

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from substrate.execution.bridge import meeting_intelligence as mi  # noqa: E402


class _FakeResult:
    def __init__(self, output: str) -> None:
        self.output = output


def _patch_model(outputs: list[str]) -> list[dict]:
    """Replace call_with_fallback with a stub that returns queued outputs."""
    import execution.runtime.model_router as mr

    calls: list[dict] = []
    queue = list(outputs)

    def _stub(*, prompt, system, task_type, trigger_source, **kw):
        calls.append(
            {"prompt": prompt, "system": system, "trigger_source": trigger_source}
        )
        if queue:
            return _FakeResult(queue.pop(0))
        return _FakeResult("")

    mr.call_with_fallback = _stub  # type: ignore
    return calls


def _force_model_failure() -> None:
    import execution.runtime.model_router as mr

    def _boom(*a, **kw):
        raise RuntimeError("forced failure for upgrade smoke test")

    mr.call_with_fallback = _boom  # type: ignore


def _stub_speak() -> list[dict]:
    import execution.bridge.station_helpers as sh

    calls: list[dict] = []

    class _Stub:
        pass

    def _fake_speak(node_id, text, *, voice=None, issued_by="x"):
        calls.append({"node_id": node_id, "text": text, "issued_by": issued_by})
        return _Stub()

    sh.propose_speak_text = _fake_speak  # type: ignore
    return calls


def _fresh_summary(node_id: str, meeting_id: str) -> mi.MeetingSummary:
    mi.reset_meeting_summary_store_for_tests()
    s = mi.MeetingSummary(node_id=node_id, meeting_id=meeting_id)
    mi.get_meeting_summary_store().put(s)
    return s


def main() -> int:
    # ── 1. compute_scores: low ──────────────────────────────────────────
    s = _fresh_summary("n1", "m1")
    s.open_loops = []
    s.decisions = []
    s.key_points = ["alpha"]
    mi.compute_scores(s)
    assert s.decision_pressure_score == 0
    assert s.ambiguity_score == 0
    assert s.priority_level == "low"

    # ── 2a. compute_scores: medium via pressure=1 ───────────────────────
    s.open_loops = ["pick color"]
    s.decisions = []
    mi.compute_scores(s)
    assert s.decision_pressure_score == 1
    assert s.priority_level == "medium", s.priority_level

    # ── 2b. compute_scores: high via pressure>=3 ────────────────────────
    s.open_loops = ["a", "b", "c", "d"]
    s.decisions = ["x"]
    mi.compute_scores(s)
    assert s.decision_pressure_score == 3
    assert s.priority_level == "high"

    # ── 2c. compute_scores: ambiguity promotes to medium ────────────────
    s.open_loops = []
    s.decisions = []
    s.key_points = [
        "launch timeline marketing approval",
        "marketing approval launch budget",
    ]
    mi.compute_scores(s)
    assert s.ambiguity_score >= 1
    assert s.priority_level == "medium"

    # ── 3. Deterministic trigger with no model ──────────────────────────
    _force_model_failure()
    s = _fresh_summary("n2", "m2")
    s.open_loops = ["o1", "o2", "o3"]
    s.decisions = []
    mi.compute_scores(s)
    mi.get_meeting_summary_store().put(s)
    interv = mi.detect_intervention(s)
    assert interv is not None and interv["type"] == "decision_prompt"

    # ── 4. refine_intervention_message uses model path ─────────────────
    calls = _patch_model(["Decide on o1 now to unblock the launch."])
    refined = mi.refine_intervention_message(
        "Do you want to finalize a decision on: o1", "ceo", s
    )
    assert len(calls) == 1
    assert refined == "Decide on o1 now to unblock the launch."
    assert len(refined) <= mi.MAX_REFINED_MESSAGE_CHARS

    # Model returns quoted/multi-line — must be sanitized to one line.
    _patch_model(['"Line one"\nLine two'])
    refined2 = mi.refine_intervention_message("raw", "ea_orchestrator", s)
    assert refined2 == "Line one"

    # ── 5. Fallback-safe on model failure ───────────────────────────────
    _force_model_failure()
    fallback = mi.refine_intervention_message("Decide on naming", "ceo", s)
    assert fallback.startswith("Decision needed — "), fallback
    assert "Decide on naming" in fallback

    # ── 6. Role-aware phrasing via static fallback differs per role ─────
    ceo_msg = mi.refine_intervention_message("clarify scope", "ceo", s)
    ea_msg = mi.refine_intervention_message("clarify scope", "ea_orchestrator", s)
    pa_msg = mi.refine_intervention_message("clarify scope", "portfolio_advisor", s)
    assert ceo_msg != ea_msg != pa_msg
    assert ceo_msg.startswith("Decision needed — ")
    assert ea_msg.startswith("Next step — ")
    assert pa_msg.startswith("Risk check — ")

    # ── 7. Unknown role → raw passthrough ───────────────────────────────
    raw = "raw message body"
    assert mi.refine_intervention_message(raw, None, s) == raw
    assert mi.refine_intervention_message(raw, "random_role", s) == raw
    # Empty input → empty output
    assert mi.refine_intervention_message("", "ceo", s) == ""

    # ── 8. maybe_emit_intervention records role + priority ─────────────
    _force_model_failure()
    speak_calls = _stub_speak()
    s2 = _fresh_summary("n3", "m3")
    s2.open_loops = ["finalize copy", "approve video", "clear legal"]
    s2.decisions = []
    s2.last_intervention_ts = None
    mi.compute_scores(s2)
    mi.get_meeting_summary_store().put(s2)
    # Force derive_active_role to return 'ceo' deterministically.
    mi.derive_active_role = lambda node_id=None: "ceo"  # type: ignore
    interv = mi.maybe_emit_intervention("n3", "m3", s2)
    assert interv is not None
    assert interv.get("role") == "ceo"
    assert interv.get("priority_level") == "high"
    assert len(speak_calls) == 1
    assert speak_calls[0]["text"].startswith("Decision needed — ")

    # ── 9. intelligence_report_block includes new structured fields ─────
    block = mi.intelligence_report_block(node_id="n3", meeting_id="m3")
    assert "scoring" in block
    assert block["scoring"]["priority_level"] == "high"
    assert block["scoring"]["decision_pressure_score"] == 3
    assert "high_priority_open_loops" in block
    assert len(block["high_priority_open_loops"]) == 3
    assert "actionable_tasks" in block
    assert all(t["actionable"] is True for t in block["actionable_tasks"])
    assert "memory_counts_by_type" in block
    assert set(block["memory_counts_by_type"].keys()) == {
        "decision",
        "task",
        "insight",
    }
    assert "recent_intervention_reasons" in block
    assert any(r.get("role") == "ceo" for r in block["recent_intervention_reasons"])

    # ── 10. Bounds: refined message length + existing caps ──────────────
    long_raw = "x" * 1000
    bounded = mi.refine_intervention_message(long_raw, "ceo", s2)
    assert len(bounded) <= mi.MAX_REFINED_MESSAGE_CHARS

    # Existing caps still enforced in update flow (force failure, huge fallback).
    _force_model_failure()
    original_fb = mi._fallback_summary
    mi._fallback_summary = lambda prev, ut: {  # type: ignore
        "key_points": [f"p{i}" for i in range(50)],
        "decisions": [f"d{i}" for i in range(50)],
        "open_loops": [f"o{i}" for i in range(50)],
    }
    try:
        mi.reset_meeting_summary_store_for_tests()
        res = mi.update_meeting_summary("n4", "m4", [{"text": "hi"}])
        assert len(res["key_points"]) <= mi.MAX_KEY_POINTS
        assert len(res["decisions"]) <= mi.MAX_DECISIONS
        assert len(res["open_loops"]) <= mi.MAX_OPEN_LOOPS
        # After caps: open_loops=5, decisions=5 → pressure=0 → low.
        assert res["decision_pressure_score"] == 0
        assert res["priority_level"] == "low"
    finally:
        mi._fallback_summary = original_fb  # type: ignore

    print("MEETING INTELLIGENCE UPGRADE SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
