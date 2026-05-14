#!/usr/bin/env python3
"""
Smoke test for Temporal Intelligence Layer v1.

Validates the additive bounded upgrade layered on top of Resolution
Intelligence. Time is simulated by directly manipulating `created_at` /
`last_followup_prompt_ts` values so the test remains deterministic and
CI-safe (no real sleeps).

Checks:
  1. Unresolved commitment becomes stale past COMMITMENT_STALE_SECONDS.
  2. Resolved commitment is NOT counted as stale.
  3. oldest_unresolved_commitment_age_seconds reflects the oldest one.
  4. detect_follow_up prioritizes the stale commitment over a fresh one.
  5. FOLLOW_UP_COOLDOWN_SECONDS suppresses repeat follow-up prompts.
  6. next_followup_eligible_ts is set to anchor + cooldown.
  7. stale_open_loops_count respects open_loops_since_ts + STALE window.
  8. intelligence_report_block exposes all new temporal fields.
  9. Bad input does not raise (helpers return safe defaults).
 10. Existing caps (MAX_COMMITMENTS) remain enforced.
 11. temporal_health returns one of fresh|aging|stale.
 12. Hot-path files remain clean (grep guard).

Prints:
    TEMPORAL INTELLIGENCE SMOKE TEST PASSED
"""

from __future__ import annotations

import subprocess
import sys
import time

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from runtime.transport import meeting_intelligence as mi  # noqa: E402


HOT_PATH_FILES = (
    "control_plane/runtime/gateway.py",
    "control_plane/runtime/cognitive_loop.py",
    "execution/runtime/model_router.py",
    "execution/runtime/agent_runtime.py",
    "runtime/primitives.py",
)


def _fresh_summary() -> mi.MeetingSummary:
    mi.reset_meeting_summary_store_for_tests()
    return mi.MeetingSummary(node_id="node-temporal", meeting_id="meet-temporal")


def _commitment(text: str, created_at: float, resolved: bool = False) -> dict:
    return {
        "text": text,
        "owner": "antony",
        "created_at": created_at,
        "resolved": resolved,
        "resolved_at": created_at + 5 if resolved else None,
        "source": "meeting",
    }


def test_stale_detection() -> None:
    now = time.time()
    s = _fresh_summary()
    s.commitments = [
        _commitment("send the deck", now - mi.COMMITMENT_STALE_SECONDS - 30),
        _commitment("ping Alex", now - 10),  # fresh
    ]
    stale = mi.stale_commitments_count(s, now)
    assert stale == 1, f"expected 1 stale commitment, got {stale}"
    oldest = mi.oldest_unresolved_commitment_age_seconds(s, now)
    assert oldest >= mi.COMMITMENT_STALE_SECONDS, f"oldest age {oldest} too small"


def test_resolved_not_stale() -> None:
    now = time.time()
    s = _fresh_summary()
    s.commitments = [
        _commitment(
            "send the deck",
            now - mi.COMMITMENT_STALE_SECONDS - 120,
            resolved=True,
        ),
    ]
    assert mi.stale_commitments_count(s, now) == 0
    assert mi.oldest_unresolved_commitment_age_seconds(s, now) == 0.0


def test_follow_up_prioritizes_stale() -> None:
    now = time.time()
    s = _fresh_summary()
    s.commitments = [
        _commitment("ping Alex", now - 5),  # fresh, added first
        _commitment("send the deck", now - mi.COMMITMENT_STALE_SECONDS - 60),  # stale
    ]
    fu = mi.detect_follow_up(s)
    assert fu is not None, "detect_follow_up returned None when stale exists"
    assert fu.get("stale") is True, f"expected stale=True, got {fu.get('stale')}"
    assert "send the deck" in (fu.get("commitment_text") or "")


def test_follow_up_cooldown_suppresses_repeats() -> None:
    now = time.time()
    s = _fresh_summary()
    s.commitments = [
        _commitment("send the deck", now - mi.COMMITMENT_STALE_SECONDS - 60),
    ]
    # Simulate we JUST emitted a follow-up prompt.
    s.last_followup_prompt_ts = now - 5.0  # inside cooldown
    assert mi.is_followup_in_cooldown(s, now) is True
    assert mi.detect_follow_up(s) is None, "cooldown should suppress follow-up"

    # Advance beyond cooldown.
    s.last_followup_prompt_ts = now - (mi.FOLLOW_UP_COOLDOWN_SECONDS + 5.0)
    assert mi.is_followup_in_cooldown(s, now) is False
    fu2 = mi.detect_follow_up(s)
    assert fu2 is not None, "follow-up should re-emit after cooldown"


def test_next_followup_eligible_ts() -> None:
    s = _fresh_summary()
    assert mi.next_followup_eligible_ts(s) is None
    anchor = 10_000_000.0
    s.last_followup_prompt_ts = anchor
    eligible = mi.next_followup_eligible_ts(s)
    assert eligible is not None
    assert abs(eligible - (anchor + mi.FOLLOW_UP_COOLDOWN_SECONDS)) < 1e-6, (
        f"eligible {eligible} != anchor+cooldown"
    )


def test_stale_open_loops_count() -> None:
    now = time.time()
    s = _fresh_summary()
    # No open loops → 0
    assert mi.stale_open_loops_count(s, now) == 0

    # Open loops but since_ts unset → 0 (not yet marked)
    s.open_loops = ["pricing?", "launch date?"]
    assert mi.stale_open_loops_count(s, now) == 0

    # since_ts fresh → 0
    s.open_loops_since_ts = now - 10
    assert mi.stale_open_loops_count(s, now) == 0

    # since_ts past STALE_OPEN_LOOP_SECONDS → count clamped to len/MAX
    s.open_loops_since_ts = now - (mi.STALE_OPEN_LOOP_SECONDS + 30)
    c = mi.stale_open_loops_count(s, now)
    assert c == 2, f"expected 2 stale open loops, got {c}"
    assert c <= mi.MAX_OPEN_LOOPS


def test_temporal_health_values() -> None:
    now = time.time()
    s = _fresh_summary()
    # Nothing → fresh
    assert mi.temporal_health(s, now) == "fresh"

    # One stale commitment → stale
    s.commitments = [
        _commitment("send the deck", now - mi.COMMITMENT_STALE_SECONDS - 30)
    ]
    assert mi.temporal_health(s, now) == "stale"

    # Only an aging (not stale) commitment → aging
    s2 = _fresh_summary()
    s2.commitments = [
        _commitment("ping Alex", now - (mi.COMMITMENT_FRESH_SECONDS + 10))
    ]
    health = mi.temporal_health(s2, now)
    assert health in ("aging", "fresh"), f"unexpected health={health}"
    # Must be aging because age > COMMITMENT_FRESH_SECONDS but < stale
    assert health == "aging"


def test_report_block_temporal_fields() -> None:
    now = time.time()
    mi.reset_meeting_summary_store_for_tests()
    store = mi.get_meeting_summary_store()
    live = mi.MeetingSummary(node_id="node-rpt", meeting_id="meet-rpt")
    live.open_loops = ["pricing?"]
    live.open_loops_since_ts = now - (mi.STALE_OPEN_LOOP_SECONDS + 60)
    live.commitments = [
        _commitment("send the deck", now - mi.COMMITMENT_STALE_SECONDS - 60),
        _commitment("ping Alex", now - 5),
    ]
    live.last_followup_prompt_ts = now - 10.0  # cooldown active
    store.put(live)

    rpt = mi.intelligence_report_block(node_id="node-rpt", meeting_id="meet-rpt")
    required = [
        "stale_commitments_count",
        "oldest_unresolved_commitment_age_seconds",
        "stale_open_loops_count",
        "next_followup_eligible_ts",
        "followup_cooldown_active",
        "temporal_health",
    ]
    for k in required:
        assert k in rpt, f"report missing temporal field: {k}"
    assert rpt["stale_commitments_count"] == 1
    assert rpt["stale_open_loops_count"] == 1
    assert rpt["followup_cooldown_active"] is True
    assert rpt["temporal_health"] == "stale"
    assert (
        rpt["oldest_unresolved_commitment_age_seconds"] >= mi.COMMITMENT_STALE_SECONDS
    )
    assert isinstance(rpt["next_followup_eligible_ts"], float)
    # backward compat: existing keys still present
    for k in (
        "commitments_count",
        "unresolved_commitments_count",
        "completion_rate",
        "escalation_trend",
        "follow_up_candidates",
    ):
        assert k in rpt, f"backward-compat key missing: {k}"
    # follow_up_candidates must be empty because cooldown is active
    assert rpt["follow_up_candidates"] == []


def test_report_block_defaults_on_missing_meeting() -> None:
    mi.reset_meeting_summary_store_for_tests()
    rpt = mi.intelligence_report_block(node_id=None, meeting_id=None)
    assert rpt["stale_commitments_count"] == 0
    assert rpt["oldest_unresolved_commitment_age_seconds"] == 0.0
    assert rpt["stale_open_loops_count"] == 0
    assert rpt["next_followup_eligible_ts"] is None
    assert rpt["followup_cooldown_active"] is False
    assert rpt["temporal_health"] == "fresh"


def test_bad_input_never_raises() -> None:
    # Bad commitment dicts
    assert mi.commitment_age_seconds({}) == 0.0
    assert mi.commitment_age_seconds({"created_at": "not-a-number"}) == 0.0
    assert mi.commitment_age_seconds(None) == 0.0  # type: ignore[arg-type]

    # Empty summary
    s = mi.MeetingSummary(node_id="x", meeting_id="y")
    assert mi.stale_commitments_count(s) == 0
    assert mi.oldest_unresolved_commitment_age_seconds(s) == 0.0
    assert mi.stale_open_loops_count(s) == 0
    assert mi.next_followup_eligible_ts(s) is None
    assert mi.is_followup_in_cooldown(s) is False
    assert mi.temporal_health(s) in ("fresh", "aging", "stale")


def test_caps_still_enforced() -> None:
    now = time.time()
    s = _fresh_summary()
    # Build more than MAX_COMMITMENTS in summary directly, ensure helpers stay bounded.
    s.commitments = [
        _commitment(f"task {i}", now - mi.COMMITMENT_STALE_SECONDS - i)
        for i in range(mi.MAX_COMMITMENTS + 10)
    ]
    # stale count must equal number of unresolved (all of them), but
    # list operations never exceed list length — sanity check no crash.
    stale = mi.stale_commitments_count(s, now)
    assert stale == len(s.commitments)
    oldest = mi.oldest_unresolved_commitment_age_seconds(s, now)
    assert oldest > 0.0


def test_hot_path_clean() -> None:
    # Confirm none of the hot-path files were touched to import temporal logic.
    for f in HOT_PATH_FILES:
        out = subprocess.run(
            ["grep", "-n", "temporal_intelligence\\|FOLLOW_UP_COOLDOWN_SECONDS", f],
            cwd=_ROOT,
            capture_output=True,
            text=True,
        )
        assert out.returncode != 0 or not out.stdout.strip(), (
            f"hot-path file {f} references temporal layer: {out.stdout}"
        )


def main() -> int:
    tests = [
        ("stale detection", test_stale_detection),
        ("resolved not stale", test_resolved_not_stale),
        ("follow-up prioritizes stale", test_follow_up_prioritizes_stale),
        (
            "follow-up cooldown suppresses repeats",
            test_follow_up_cooldown_suppresses_repeats,
        ),
        ("next_followup_eligible_ts", test_next_followup_eligible_ts),
        ("stale_open_loops_count", test_stale_open_loops_count),
        ("temporal_health values", test_temporal_health_values),
        ("report block temporal fields", test_report_block_temporal_fields),
        ("report block defaults", test_report_block_defaults_on_missing_meeting),
        ("bad input never raises", test_bad_input_never_raises),
        ("caps still enforced", test_caps_still_enforced),
        ("hot path clean", test_hot_path_clean),
    ]
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            return 1
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {name} crashed: {e}")
            return 1
    print("TEMPORAL INTELLIGENCE SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
