#!/usr/bin/env python3
"""
Smoke test for Coordination Intelligence Layer v1.

Validates the additive, bounded ownership-awareness layered on top of
Temporal/Resolution/Execution intelligence. No hot-path changes, no new
pipelines, no daemons. Time is simulated where needed.

Checks:
  1. "I will" with speaker metadata → owner = speaker, high confidence
  2. "I will" without speaker metadata → owner = None, low confidence
  3. "Name will" phrase → owner = Name, high confidence
  4. "We will" phrase → owner = "group", high confidence
  5. ownership_distribution counts per owner correctly
  6. unassigned_commitments_count counts unowned unresolved correctly
  7. pressure increases when owned unresolved commitments exist
  8. ambiguity increases when unowned unresolved commitments exist
  9. detect_follow_up targets owner directly when known
 10. detect_follow_up prompts assignment when owner missing
 11. High escalation produces more direct wording
 12. intelligence_report_block exposes all ownership fields
 13. ownership_pressure_hint: clear | diffused | missing
 14. MAX_OWNERSHIP_DISTRIBUTION_ENTRIES cap enforced
 15. Malformed input does not raise
 16. Hot-path files remain clean (grep guard)

Prints:
    COORDINATION INTELLIGENCE SMOKE TEST PASSED
"""

from __future__ import annotations

import subprocess
import sys
import time

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from eos_ai.substrate import meeting_intelligence as mi  # noqa: E402

HOT_PATH_FILES = (
    "eos_ai/gateway.py",
    "eos_ai/cognitive_loop.py",
    "eos_ai/model_router.py",
    "eos_ai/agent_runtime.py",
    "eos_ai/primitives.py",
)


def _fresh_summary() -> mi.MeetingSummary:
    mi.reset_meeting_summary_store_for_tests()
    return mi.MeetingSummary(node_id="node-coord", meeting_id="meet-coord")


def _utt(text: str, speaker: str | None = None) -> dict:
    d: dict = {"text": text}
    if speaker:
        d["participant_name"] = speaker
    return d


def check_first_person_with_speaker() -> None:
    cs = mi.extract_commitments([_utt("I will send the deck", speaker="Antony")])
    assert len(cs) == 1, cs
    assert cs[0].owner == "Antony", cs[0].owner
    assert cs[0].owner_confidence == "high", cs[0].owner_confidence


def check_first_person_no_speaker() -> None:
    cs = mi.extract_commitments([_utt("I will follow up on that later")])
    assert len(cs) == 1
    assert cs[0].owner is None, cs[0].owner
    assert cs[0].owner_confidence == "low"


def check_named_third_party() -> None:
    cs = mi.extract_commitments([_utt("John will send over the contract")])
    assert len(cs) == 1
    assert cs[0].owner == "John", cs[0].owner
    assert cs[0].owner_confidence == "high"


def check_group_owner() -> None:
    cs = mi.extract_commitments([_utt("We will circle back next week")])
    assert len(cs) == 1
    assert cs[0].owner == mi.GROUP_OWNER_LABEL
    assert cs[0].owner_confidence == "high"


def check_distribution_and_unassigned() -> None:
    s = _fresh_summary()
    s.commitments = [
        {"text": "ship doc", "owner": "Antony", "resolved": False, "created_at": 1.0},
        {"text": "send invoice", "owner": "Antony", "resolved": False, "created_at": 1.0},
        {"text": "draft email", "owner": "John", "resolved": False, "created_at": 1.0},
        {"text": "mystery task", "owner": None, "resolved": False, "created_at": 1.0},
    ]
    dist = mi.ownership_distribution(s)
    assert dist == {"Antony": 2, "John": 1}, dist
    assert mi.unassigned_commitments_count(s) == 1


def check_scoring_pressure_owned() -> None:
    s = _fresh_summary()
    s.commitments = [
        {"text": "ship doc", "owner": "Antony", "resolved": False, "created_at": 1.0},
    ]
    mi.compute_scores(s)
    # No open_loops → base pressure 0, bonus 1 for owned unresolved.
    assert s.decision_pressure_score == mi.OWNED_UNRESOLVED_PRESSURE_BONUS, (
        s.decision_pressure_score
    )


def check_scoring_ambiguity_unowned() -> None:
    s = _fresh_summary()
    s.commitments = [
        {"text": "mystery task", "owner": None, "resolved": False, "created_at": 1.0},
    ]
    mi.compute_scores(s)
    assert s.ambiguity_score >= mi.UNOWNED_UNRESOLVED_AMBIGUITY_BONUS


def check_follow_up_targets_owner() -> None:
    s = _fresh_summary()
    s.commitments = [
        {"text": "send the deck", "owner": "Antony", "resolved": False, "created_at": 1.0, "owner_confidence": "high"},
    ]
    mi.compute_scores(s)
    mi.compute_escalation_level(s)
    fu = mi.detect_follow_up(s)
    assert fu is not None
    assert fu["owner"] == "Antony"
    assert "Antony" in fu["message"]
    assert fu["owner_confidence"] == "high"


def check_follow_up_unassigned_prompts_assignment() -> None:
    s = _fresh_summary()
    s.commitments = [
        {"text": "handle the rollout", "owner": None, "resolved": False, "created_at": 1.0},
    ]
    mi.compute_scores(s)
    mi.compute_escalation_level(s)
    fu = mi.detect_follow_up(s)
    assert fu is not None
    lower = fu["message"].lower()
    assert "owner" in lower or "who" in lower, fu["message"]
    assert fu["ownership_pressure_hint"] == "missing"


def check_high_escalation_more_direct() -> None:
    s = _fresh_summary()
    s.commitments = [
        {"text": "ship the deck", "owner": "Antony", "resolved": False, "created_at": 1.0},
    ]
    s.escalation_level = "high"
    fu = mi.detect_follow_up(s)
    assert fu is not None
    assert "Status now" in fu["message"] or "status" in fu["message"].lower()


def check_report_block_exposes_ownership() -> None:
    mi.reset_meeting_summary_store_for_tests()
    store = mi.get_meeting_summary_store()
    s = mi.MeetingSummary(node_id="n1", meeting_id="m1")
    s.commitments = [
        {"text": "ship doc", "owner": "Antony", "resolved": False, "created_at": 1.0, "owner_confidence": "high"},
        {"text": "draft email", "owner": "John", "resolved": False, "created_at": 1.0, "owner_confidence": "high"},
        {"text": "mystery task", "owner": None, "resolved": False, "created_at": 1.0},
    ]
    mi.compute_scores(s)
    mi.compute_escalation_level(s)
    store.put(s)
    block = mi.intelligence_report_block("n1", "m1")
    assert "ownership_distribution" in block
    assert block["ownership_distribution"] == {"Antony": 1, "John": 1}
    assert block["unassigned_commitments_count"] == 1
    assert block["top_owner"] in ("Antony", "John")
    assert block["ownership_pressure_hint"] == "diffused"
    assert "commitments_by_owner" in block
    assert "Antony" in block["commitments_by_owner"]


def check_pressure_hint_values() -> None:
    s = _fresh_summary()
    s.commitments = [
        {"text": "a", "owner": "X", "resolved": False, "created_at": 1.0},
    ]
    assert mi.ownership_pressure_hint(s) == "clear"
    s.commitments.append(
        {"text": "b", "owner": None, "resolved": False, "created_at": 1.0}
    )
    assert mi.ownership_pressure_hint(s) == "diffused"
    s.commitments = [
        {"text": "c", "owner": None, "resolved": False, "created_at": 1.0},
    ]
    assert mi.ownership_pressure_hint(s) == "missing"


def check_distribution_cap() -> None:
    s = _fresh_summary()
    s.commitments = [
        {"text": f"t{i}", "owner": f"user{i}", "resolved": False, "created_at": 1.0}
        for i in range(mi.MAX_OWNERSHIP_DISTRIBUTION_ENTRIES + 5)
    ]
    dist = mi.ownership_distribution(s)
    assert len(dist) <= mi.MAX_OWNERSHIP_DISTRIBUTION_ENTRIES


def check_malformed_input() -> None:
    # Should not raise.
    assert mi.extract_commitments(None) == []  # type: ignore[arg-type]
    assert mi.extract_commitments([None, 42, {"text": None}]) == []  # type: ignore[list-item]
    s = _fresh_summary()
    s.commitments = [None, 42, {}]  # type: ignore[list-item]
    mi.ownership_distribution(s)
    mi.unassigned_commitments_count(s)
    mi.ownership_pressure_hint(s)
    mi.compute_scores(s)


def check_hot_path_clean() -> None:
    for f in HOT_PATH_FILES:
        out = subprocess.run(
            ["grep", "-n", "coordination_intelligence\\|ownership_distribution", f],
            cwd="/opt/OS",
            capture_output=True,
            text=True,
        )
        assert out.returncode != 0 or not out.stdout.strip(), (
            f"hot-path file referenced coordination layer: {f}\n{out.stdout}"
        )


CHECKS = [
    check_first_person_with_speaker,
    check_first_person_no_speaker,
    check_named_third_party,
    check_group_owner,
    check_distribution_and_unassigned,
    check_scoring_pressure_owned,
    check_scoring_ambiguity_unowned,
    check_follow_up_targets_owner,
    check_follow_up_unassigned_prompts_assignment,
    check_high_escalation_more_direct,
    check_report_block_exposes_ownership,
    check_pressure_hint_values,
    check_distribution_cap,
    check_malformed_input,
    check_hot_path_clean,
]


def main() -> int:
    t0 = time.time()
    for fn in CHECKS:
        try:
            fn()
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}", file=sys.stderr)
            return 1
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {fn.__name__}: {e}", file=sys.stderr)
            return 1
    print(
        f"COORDINATION INTELLIGENCE SMOKE TEST PASSED "
        f"({len(CHECKS)} checks in {time.time() - t0:.2f}s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
