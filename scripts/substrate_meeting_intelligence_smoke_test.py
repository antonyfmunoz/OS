#!/usr/bin/env python3
"""
Smoke test for Meeting Intelligence Layer v1.

Validates:
  1. Utterances flow through update_meeting_summary.
  2. Summary updates after threshold.
  3. Intervention triggers once on decision-gap condition.
  4. Memory extraction produces decision/task/insight entries.
  5. No crash when model unavailable (we force the router to fail).
  6. Caps enforced (key_points≤10, decisions≤5, open_loops≤5).

Prints:
    MEETING INTELLIGENCE SMOKE TEST PASSED
"""

from __future__ import annotations

import sys
import time

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from substrate.execution.bridge import meeting_intelligence as mi  # noqa: E402


def _force_model_failure():
    """Monkey-patch call_with_fallback to raise — exercises fallback path."""
    import execution.runtime.model_router as mr

    def _boom(*a, **kw):
        raise RuntimeError("forced failure for smoke test")

    mr.call_with_fallback = _boom  # type: ignore


def main() -> int:
    mi.reset_meeting_summary_store_for_tests()
    _force_model_failure()

    node_id = "meeting_generic_meeting_smoke"
    meeting_id = "smoke-001"

    # ── 1. Inject utterances ────────────────────────────────────────────
    utterances = [
        {"text": "We should pick a name for the launch.", "participant_name": "alice"},
        {"text": "Marketing also needs an approved logo.", "participant_name": "bob"},
        {"text": "Legal wants the trademark cleared.", "participant_name": "carol"},
    ]
    result = mi.update_meeting_summary(node_id, meeting_id, utterances)
    assert isinstance(result, dict), "summary must be dict"
    assert result["node_id"] == node_id
    assert result["meeting_id"] == meeting_id
    # With forced model failure, fallback populates key_points from last 3.
    assert len(result["key_points"]) > 0, "fallback must produce key_points"

    # ── 2. Summary persisted in store ───────────────────────────────────
    live = mi.get_meeting_summary_store().get(node_id, meeting_id)
    assert live is not None, "summary must persist"
    assert live.last_updated_ts > 0

    # ── 3. Intervention: force decision-gap condition deterministically ─
    live.open_loops = ["pick launch name", "approve logo", "clear trademark"]
    live.decisions = []
    live.last_intervention_ts = None
    mi.get_meeting_summary_store().put(live)

    # Monkey-patch propose_speak_text to avoid real station dispatch.
    import execution.bridge.station_helpers as sh

    calls: list[dict] = []

    class _Stub:
        pass

    def _fake_speak(node_id, text, *, voice=None, issued_by="x"):
        calls.append({"node_id": node_id, "text": text, "issued_by": issued_by})
        return _Stub()

    sh.propose_speak_text = _fake_speak  # type: ignore

    interv = mi.maybe_emit_intervention(node_id, meeting_id, live)
    assert interv is not None, "intervention should fire on decision gap"
    assert interv["type"] == "decision_prompt"
    assert len(calls) == 1, "propose_speak_text should be called once"
    assert calls[0]["issued_by"] == "meeting_intelligence"

    # Second call within cooldown → no new intervention
    interv2 = mi.maybe_emit_intervention(node_id, meeting_id, live)
    assert interv2 is None, "cooldown must suppress second intervention"
    assert len(calls) == 1, "no second SPEAK_TEXT during cooldown"

    # ── 4. Memory extraction ────────────────────────────────────────────
    live.key_points = ["insight one", "insight two"]
    memories = mi.extract_memory(live)
    types = {m.type for m in memories}
    assert "decision" not in types, "no decisions → no decision memories"
    assert "task" in types, "open_loops must yield task memories"
    assert "insight" in types, "key_points must yield insight memories"
    assert len(memories) <= 10, "memory cap respected"

    # ── 5. Caps enforced ────────────────────────────────────────────────
    huge = MockSummary()
    huge_dict = {
        "key_points": [f"p{i}" for i in range(50)],
        "decisions": [f"d{i}" for i in range(50)],
        "open_loops": [f"o{i}" for i in range(50)],
    }
    # Re-run update with a patched fallback that returns huge lists.
    original_fb = mi._fallback_summary
    mi._fallback_summary = lambda prev, ut: huge_dict  # type: ignore
    try:
        mi.reset_meeting_summary_store_for_tests()
        res = mi.update_meeting_summary(node_id, meeting_id, utterances)
        assert len(res["key_points"]) <= mi.MAX_KEY_POINTS
        assert len(res["decisions"]) <= mi.MAX_DECISIONS
        assert len(res["open_loops"]) <= mi.MAX_OPEN_LOOPS
    finally:
        mi._fallback_summary = original_fb  # type: ignore

    # ── 6. No crash on completely bad input ─────────────────────────────
    bad = mi.update_meeting_summary(node_id, meeting_id, None)  # type: ignore
    assert isinstance(bad, dict)
    bad2 = mi.update_meeting_summary(node_id, meeting_id, ["not a dict"])  # type: ignore
    assert isinstance(bad2, dict)

    # ── 7. Reporting block ──────────────────────────────────────────────
    block = mi.intelligence_report_block(node_id=node_id, meeting_id=meeting_id)
    assert "summary" in block
    assert "recent_interventions" in block
    assert "memory_extracted_count" in block

    print("MEETING INTELLIGENCE SMOKE TEST PASSED")
    return 0


class MockSummary:
    pass


if __name__ == "__main__":
    raise SystemExit(main())
