#!/usr/bin/env python3
"""
Smoke test for Resolution Intelligence Layer v1.

Validates the additive bounded upgrade on top of Execution Intelligence:

  1. A commitment is created via update_meeting_summary.
  2. A matching utterance with a resolution phrase flips resolved=True.
  3. resolved_at is set to a non-None timestamp.
  4. unresolved_commitments_count decreases after resolution.
  5. detect_follow_up no longer targets the resolved commitment.
  6. decision_pressure_score decays (bounded) after resolution.
  7. resolve_commitments returns [] on bad / empty input (never raises).
  8. Commitment cap (MAX_COMMITMENTS) is still enforced.
  9. intelligence_report_block exposes resolved_commitments_count,
     completion_rate, recently_resolved_commitments, escalation_trend.
 10. Hot-path files remain clean (grep guard).

Prints:
    RESOLUTION INTELLIGENCE SMOKE TEST PASSED
"""

from __future__ import annotations

import subprocess
import sys
import time

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from runtime.substrate import meeting_intelligence as mi  # noqa: E402


def _force_model_failure() -> None:
    import runtime.model_router as mr

    def _boom(*a, **kw):
        raise RuntimeError("forced failure for resolution smoke test")

    mr.call_with_fallback = _boom  # type: ignore


def _stub_speak() -> list[dict]:
    import runtime.substrate.station_helpers as sh

    calls: list[dict] = []

    def _fake_speak(node_id, text, *, voice=None, issued_by="x"):
        calls.append({"node_id": node_id, "text": text, "issued_by": issued_by})

        class _Stub:
            pass

        return _Stub()

    sh.propose_speak_text = _fake_speak  # type: ignore
    return calls


def main() -> int:
    mi.reset_meeting_summary_store_for_tests()
    _force_model_failure()
    _stub_speak()

    node = "node-res-1"
    meeting = "mtg-res-1"

    # 1. create a commitment via update_meeting_summary
    mi.update_meeting_summary(
        node,
        meeting,
        [
            {
                "text": "I will send the onboarding deck to the partner tomorrow.",
                "participant_name": "Antony",
                "event_id": "e1",
            }
        ],
    )
    live = mi.get_meeting_summary_store().get(node, meeting)
    assert live is not None, "summary missing"
    assert len(live.commitments) == 1, f"expected 1 commitment got {live.commitments}"
    assert live.commitments[0]["resolved"] is False
    assert live.commitments[0].get("resolved_at") is None

    unresolved_before = len(mi.unresolved_commitments(live))
    pressure_before = live.decision_pressure_score
    assert unresolved_before == 1

    # Detect follow-up before resolution
    fu_before = mi.detect_follow_up(live)
    assert fu_before is not None, "follow-up should fire pre-resolution"

    # 2. matching utterance with resolution phrase — strong keyword overlap
    #    ("onboarding", "deck", "partner", "sent")
    mi.update_meeting_summary(
        node,
        meeting,
        [
            {
                "text": "Just sent the onboarding deck to the partner, done.",
                "participant_name": "Antony",
                "event_id": "e2",
            }
        ],
    )
    live = mi.get_meeting_summary_store().get(node, meeting)
    assert live is not None

    # 3. resolved flag flipped
    assert live.commitments[0]["resolved"] is True, (
        f"commitment not resolved: {live.commitments[0]}"
    )
    # 4. resolved_at set
    assert live.commitments[0]["resolved_at"] is not None
    assert isinstance(live.commitments[0]["resolved_at"], float)

    # 5. unresolved count decreases
    unresolved_after = len(mi.unresolved_commitments(live))
    assert unresolved_after == 0, f"unresolved should be 0 got {unresolved_after}"

    # 6. follow-up no longer triggers
    fu_after = mi.detect_follow_up(live)
    assert fu_after is None, f"follow-up should be None post-resolution got {fu_after}"

    # 7. pressure decreased (bounded, >=0)
    assert live.decision_pressure_score <= pressure_before, (
        f"pressure should not increase: before={pressure_before} "
        f"after={live.decision_pressure_score}"
    )
    assert live.decision_pressure_score >= 0

    # 8. bad input safety
    assert mi.resolve_commitments(live, None) == []  # type: ignore
    assert mi.resolve_commitments(live, []) == []
    assert mi.resolve_commitments(live, [{"bogus": 1}, None, 42]) == []  # type: ignore

    # 9. cap still enforced — push many commitments
    mi.reset_meeting_summary_store_for_tests()
    burst = [
        {
            "text": f"I will handle task number {i} right away.",
            "participant_name": "Antony",
            "event_id": f"b{i}",
        }
        for i in range(25)
    ]
    mi.update_meeting_summary(node, meeting, burst)
    live2 = mi.get_meeting_summary_store().get(node, meeting)
    assert live2 is not None
    assert len(live2.commitments) <= mi.MAX_COMMITMENTS

    # 10. reporting exposes new fields
    report = mi.intelligence_report_block(node_id=node, meeting_id=meeting)
    for key in (
        "resolved_commitments_count",
        "completion_rate",
        "recently_resolved_commitments",
        "escalation_trend",
    ):
        assert key in report, f"report missing {key}"
    assert report["escalation_trend"] in ("rising", "stable", "falling")
    assert isinstance(report["completion_rate"], float)
    assert isinstance(report["recently_resolved_commitments"], list)

    # 11. escalation trend — force falling path
    mi.reset_meeting_summary_store_for_tests()
    mi.update_meeting_summary(
        node,
        meeting,
        [
            {
                "text": "I will send the quarterly report to the board soon.",
                "participant_name": "Antony",
                "event_id": "t1",
            },
            {
                "text": "I will finalize the vendor contract by Friday.",
                "participant_name": "Antony",
                "event_id": "t2",
            },
            {
                "text": "I will follow up with legal on the NDA.",
                "participant_name": "Antony",
                "event_id": "t3",
            },
        ],
    )
    pre = mi.get_meeting_summary_store().get(node, meeting)
    assert pre is not None
    pressure_pre = pre.decision_pressure_score

    mi.update_meeting_summary(
        node,
        meeting,
        [
            {
                "text": "Already sent the quarterly report to the board, done.",
                "participant_name": "Antony",
                "event_id": "t4",
            },
            {
                "text": "Finalized the vendor contract, that's done.",
                "participant_name": "Antony",
                "event_id": "t5",
            },
        ],
    )
    post = mi.get_meeting_summary_store().get(node, meeting)
    assert post is not None
    resolved_ct = sum(1 for c in post.commitments if c.get("resolved"))
    assert resolved_ct >= 2, f"expected >=2 resolved got {resolved_ct}"
    assert post.decision_pressure_score <= pressure_pre

    report2 = mi.intelligence_report_block(node_id=node, meeting_id=meeting)
    assert report2["resolved_commitments_count"] >= 2
    assert 0.0 <= report2["completion_rate"] <= 1.0

    # 12. hot-path guard — none of the untouchable files mention resolution
    hot = [
        "runtime/gateway.py",
        "runtime/cognitive_loop.py",
        "runtime/model_router.py",
        "runtime/agent_runtime.py",
        "runtime/primitives.py",
    ]
    out = subprocess.run(
        ["grep", "-l", "resolve_commitments", *hot],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    assert out.stdout.strip() == "", f"hot-path leak: {out.stdout}"

    print("RESOLUTION INTELLIGENCE SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
