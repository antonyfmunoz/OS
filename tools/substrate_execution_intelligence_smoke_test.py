#!/usr/bin/env python3
"""
Smoke test for Execution Intelligence Layer v1.

Validates the additive bounded upgrade on top of Meeting Intelligence:

  1. extract_commitments pulls commitments from simple utterances.
  2. Commitment cap (MAX_COMMITMENTS) is enforced on merge.
  3. update_meeting_summary merges commitments onto MeetingSummary.
  4. unresolved_commitments counts exclude resolved ones.
  5. detect_follow_up fires when an unresolved commitment exists.
  6. detect_follow_up prefers stale commitments.
  7. compute_escalation_level derives level from pressure/priority/unresolved.
  8. detect_intervention returns follow_up when commitments exist.
  9. Deterministic trigger still works with model forced to fail.
 10. refine_intervention_message remains fallback-safe.
 11. intelligence_report_block exposes new execution fields.
 12. Bad input does not crash extract_commitments / detect_follow_up.
 13. All bounds remain enforced (cap on commitments list).
 14. Hot-path imports remain clean.

Prints:
    EXECUTION INTELLIGENCE SMOKE TEST PASSED
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/OS")

from umh.runtime_engine.substrate import meeting_intelligence as mi  # noqa: E402


class _FakeResult:
    def __init__(self, output: str) -> None:
        self.output = output


def _force_model_failure() -> None:
    import umh.runtime_engine.model_router as mr

    def _boom(*a, **kw):
        raise RuntimeError("forced failure for execution smoke test")

    mr.call_with_fallback = _boom  # type: ignore


def _stub_speak() -> list[dict]:
    import umh.substrate.station_helpers as sh

    calls: list[dict] = []

    def _fake_speak(node_id, text, *, voice=None, issued_by="x"):
        calls.append({"node_id": node_id, "text": text, "issued_by": issued_by})

        class _Stub:
            pass

        return _Stub()

    sh.propose_speak_text = _fake_speak  # type: ignore
    return calls


def _fresh(node_id: str, meeting_id: str) -> mi.MeetingSummary:
    mi.reset_meeting_summary_store_for_tests()
    s = mi.MeetingSummary(node_id=node_id, meeting_id=meeting_id)
    mi.get_meeting_summary_store().put(s)
    return s


def main() -> int:
    # ── 1. extract_commitments basic ───────────────────────────────────
    utterances = [
        {"text": "Hello everyone", "participant_name": "Alice"},
        {"text": "I will send the contract by EOD", "participant_name": "Bob"},
        {"text": "We'll follow up with legal tomorrow", "participant_name": "Alice"},
        {"text": "Just a comment about the weather", "participant_name": "Carol"},
    ]
    c = mi.extract_commitments(utterances)
    assert len(c) == 2, f"expected 2 commitments, got {len(c)}"
    assert c[0].owner == "Bob"
    assert "contract" in c[0].text
    # Coordination Intelligence v1: "we'll" → group owner, not speaker.
    assert c[1].owner == mi.GROUP_OWNER_LABEL

    # ── 2. Cap enforcement on merge ────────────────────────────────────
    many = [{"text": f"I will do task {i}", "participant_name": "X"} for i in range(20)]
    cs = mi.extract_commitments(many)
    assert len(cs) == mi.MAX_COMMITMENTS
    merged = mi._merge_commitments([], cs)
    assert len(merged) == mi.MAX_COMMITMENTS
    # Additional merge doesn't exceed cap
    more = mi.extract_commitments(
        [{"text": f"I will do extra {i}", "participant_name": "Y"} for i in range(10)]
    )
    merged2 = mi._merge_commitments(merged, more)
    assert len(merged2) == mi.MAX_COMMITMENTS

    # ── 3. update_meeting_summary merges commitments ──────────────────
    _force_model_failure()
    mi.reset_meeting_summary_store_for_tests()
    res = mi.update_meeting_summary(
        "nA",
        "mA",
        [
            {"text": "I will send the deck later today", "participant_name": "Alice"},
            {"text": "Random remark", "participant_name": "Bob"},
        ],
    )
    assert res.get("commitments"), "commitments should be populated"
    assert len(res["commitments"]) == 1
    assert res["commitments"][0]["owner"] == "Alice"

    # ── 4. unresolved_commitments ──────────────────────────────────────
    live = mi.get_meeting_summary_store().get("nA", "mA")
    assert live is not None
    assert len(mi.unresolved_commitments(live)) == 1
    live.commitments[0]["resolved"] = True
    assert len(mi.unresolved_commitments(live)) == 0
    live.commitments[0]["resolved"] = False

    # ── 5. detect_follow_up fires on unresolved ───────────────────────
    fu = mi.detect_follow_up(live)
    assert fu is not None
    assert fu["type"] == "follow_up"
    assert "deck" in fu["message"].lower()
    assert fu["owner"] == "Alice"

    # ── 6. detect_follow_up prefers stale commitments ─────────────────
    now = time.time()
    live.commitments = [
        {
            "text": "fresh promise",
            "owner": "Alice",
            "created_at": now,
            "resolved": False,
            "source": "meeting",
        },
        {
            "text": "very stale promise",
            "owner": "Bob",
            "created_at": now - (mi.COMMITMENT_STALE_SECONDS + 100),
            "resolved": False,
            "source": "meeting",
        },
    ]
    fu2 = mi.detect_follow_up(live)
    assert fu2 is not None
    assert fu2["stale"] is True
    assert (
        "stale" in fu2["message"].lower() or "stale promise" in fu2["commitment_text"]
    )

    # ── 7. compute_escalation_level derives from scores + unresolved ──
    s = _fresh("nB", "mB")
    s.open_loops = []
    s.decisions = []
    s.key_points = []
    mi.compute_scores(s)
    mi.compute_escalation_level(s)
    assert s.escalation_level == "low"

    s.commitments = [
        {
            "text": "t1",
            "owner": None,
            "created_at": time.time(),
            "resolved": False,
            "source": "meeting",
        }
    ]
    mi.compute_escalation_level(s)
    assert s.escalation_level == "medium", s.escalation_level

    s.commitments = [
        {
            "text": f"t{i}",
            "owner": None,
            "created_at": time.time(),
            "resolved": False,
            "source": "meeting",
        }
        for i in range(4)
    ]
    mi.compute_escalation_level(s)
    assert s.escalation_level == "high", s.escalation_level

    # High via existing pressure still works without commitments
    s.commitments = []
    s.open_loops = ["a", "b", "c", "d"]
    s.decisions = ["x"]
    mi.compute_scores(s)
    mi.compute_escalation_level(s)
    assert s.escalation_level == "high"

    # ── 8. detect_intervention returns follow_up when commitments ────
    s2 = _fresh("nC", "mC")
    s2.commitments = [
        {
            "text": "send the contract",
            "owner": "Alice",
            "created_at": time.time(),
            "resolved": False,
            "source": "meeting",
        }
    ]
    s2.last_intervention_ts = None
    mi.compute_scores(s2)
    interv = mi.detect_intervention(s2)
    assert interv is not None
    assert interv["type"] == "follow_up"
    assert interv.get("escalation_level") in ("low", "medium", "high")

    # ── 9. Deterministic still works with model forced to fail ───────
    _force_model_failure()
    s3 = _fresh("nD", "mD")
    s3.open_loops = ["o1", "o2", "o3"]
    s3.decisions = []
    s3.last_intervention_ts = None
    mi.compute_scores(s3)
    mi.compute_escalation_level(s3)
    interv3 = mi.detect_intervention(s3)
    assert interv3 is not None
    assert interv3["type"] == "decision_prompt"
    assert interv3.get("escalation_level") == "high"

    # ── 10. refine_intervention_message remains fallback-safe ────────
    refined = mi.refine_intervention_message("decide now", "ceo", s3)
    assert refined.startswith("Decision needed — ")

    # ── 11. report block exposes execution fields ─────────────────────
    speak_calls = _stub_speak()
    mi.derive_active_role = lambda node_id=None: "ceo"  # type: ignore
    s4 = _fresh("nE", "mE")
    s4.commitments = [
        {
            "text": "send the proposal",
            "owner": "Alice",
            "created_at": time.time(),
            "resolved": False,
            "source": "meeting",
        }
    ]
    s4.open_loops = ["pick vendor"]
    s4.last_intervention_ts = None
    mi.compute_scores(s4)
    mi.compute_escalation_level(s4)
    mi.get_meeting_summary_store().put(s4)
    emit = mi.maybe_emit_intervention("nE", "mE", s4)
    assert emit is not None
    assert emit["type"] == "follow_up"
    assert len(speak_calls) == 1

    block = mi.intelligence_report_block(node_id="nE", meeting_id="mE")
    for key in (
        "commitments_count",
        "unresolved_commitments_count",
        "follow_up_candidates",
        "intervention_escalation_level",
        "recent_commitments",
    ):
        assert key in block, f"missing {key}"
    assert block["commitments_count"] == 1
    assert block["unresolved_commitments_count"] == 1
    assert block["intervention_escalation_level"] in ("medium", "high")
    assert len(block["recent_commitments"]) == 1
    assert block["recent_commitments"][0]["owner"] == "Alice"

    # last_followup_ts should have been set on emit
    live4 = mi.get_meeting_summary_store().get("nE", "mE")
    assert live4 is not None and live4.last_followup_ts is not None

    # ── 12. Bad input does not crash ──────────────────────────────────
    assert mi.extract_commitments(None) == []  # type: ignore
    assert mi.extract_commitments("not a list") == []  # type: ignore
    assert mi.extract_commitments([{"text": None}, {}, 123, {"text": ""}]) == []  # type: ignore
    empty = mi.MeetingSummary(node_id="z", meeting_id="z")
    assert mi.detect_follow_up(empty) is None
    assert mi.unresolved_commitments(empty) == []

    # ── 13. Bounds enforced through update flow ───────────────────────
    mi.reset_meeting_summary_store_for_tests()
    giant = [
        {"text": f"I will do thing {i}", "participant_name": "P"} for i in range(50)
    ]
    res2 = mi.update_meeting_summary("nF", "mF", giant)
    assert len(res2["commitments"]) <= mi.MAX_COMMITMENTS

    # ── 14. Hot path imports remain clean ─────────────────────────────
    import umh.runtime_engine.gateway  # noqa: F401
    import umh.runtime_engine.cognitive_loop  # noqa: F401
    import umh.runtime_engine.model_router  # noqa: F401
    import umh.runtime_engine.agent_runtime  # noqa: F401
    import umh.runtime_engine.primitives  # noqa: F401

    print("EXECUTION INTELLIGENCE SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
