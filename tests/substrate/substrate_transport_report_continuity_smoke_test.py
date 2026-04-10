#!/usr/bin/env python3
"""
Continuity + augmentation smoke test for unified_transport_report.

Covers the additive operator-facing blocks added alongside the Google Meet
caption bridge integration:
    - continuity
    - ingress
    - playback_last
    - meet_bridges (real filesystem scan)
    - supervision_hints

Also exercises the operator CLI at scripts/pump_meet_source.py to ensure it
runs, emits valid JSON, and honors --no-attach.

Standalone. Plain asserts. Exit 1 on first failure.
"""

from __future__ import annotations

import json
import subprocess
import sys

sys.path.insert(0, "/opt/OS")

from eos_ai.substrate.meet_caption_bridge import (  # noqa: E402
    BRIDGE_ROOT,
    CaptionWriter,
    bridge_path_for,
    sanitize_meeting_code,
)
from eos_ai.substrate.transport_report import unified_transport_report  # noqa: E402

TEST_CODE = "report-test-continuity"
OLD_KEYS = (
    "node_id",
    "discord_transport",
    "meeting_transport",
    "transcripts",
    "playback_aggregates",
    "voice_sessions_recent",
    "audio_loop_snapshot",
    "operator_state_snapshot",
    "workstation",
)
NEW_KEYS = (
    "continuity",
    "ingress",
    "playback_last",
    "meet_bridges",
    "supervision_hints",
)


def test_unified_report_has_new_keys() -> None:
    r = unified_transport_report()
    for k in NEW_KEYS:
        assert k in r, f"missing new key: {k}"
    c = r["continuity"]
    assert set(["shared_role_slug", "active_transports", "transports_seen",
                "common_node_role_count", "any_active_session"]).issubset(c.keys())
    ing = r["ingress"]
    for t in ("discord", "meeting", "local"):
        assert t in ing and "last_at" in ing[t] and "count" in ing[t]
    assert "by_source_total" in ing
    pbl = r["playback_last"]
    assert "discord" in pbl and "meeting" in pbl
    assert isinstance(r["meet_bridges"], list)
    assert isinstance(r["supervision_hints"], list)


def test_unified_report_existing_keys_preserved() -> None:
    r = unified_transport_report()
    for k in OLD_KEYS:
        assert k in r, f"existing key gone: {k}"


def test_meet_bridges_scan_picks_up_real_bridge() -> None:
    # Write 3 captions to a real temp bridge file.
    slug = sanitize_meeting_code(TEST_CODE)
    path = bridge_path_for(slug)
    # Clean any previous leftover.
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
    try:
        w = CaptionWriter(TEST_CODE)
        for i in range(3):
            res = w.append(f"line {i}", speaker="tester")
            assert res["status"] == "ok", res
        assert path.exists()
        r = unified_transport_report()
        entry = None
        for b in r["meet_bridges"]:
            if b.get("meeting_code") == slug:
                entry = b
                break
        assert entry is not None, f"bridge {slug} not found in {r['meet_bridges']}"
        assert entry["exists"] is True
        assert entry["size_bytes"] > 0
        assert entry["path"].endswith(f"{slug}.jsonl")
        # Backlog estimate may be small (1-2) but must be an int or None.
        assert entry["backlog_estimate_lines"] is None or isinstance(
            entry["backlog_estimate_lines"], int
        )
    finally:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass


def test_supervision_hints_bounded() -> None:
    r = unified_transport_report()
    hints = r["supervision_hints"]
    assert len(hints) <= 10
    for h in hints:
        assert isinstance(h, str)
        assert len(h) < 200


def test_continuity_block_safe_when_empty() -> None:
    r = unified_transport_report()
    c = r["continuity"]
    assert isinstance(c["any_active_session"], bool)
    assert isinstance(c["transports_seen"], list)
    assert isinstance(c["active_transports"], list)
    assert isinstance(c["common_node_role_count"], int)


def test_ingress_keys_have_count_and_last_at() -> None:
    r = unified_transport_report()
    ing = r["ingress"]
    for t in ("discord", "meeting", "local"):
        assert isinstance(ing[t]["count"], int)
        # last_at may be None, otherwise a string
        la = ing[t]["last_at"]
        assert la is None or isinstance(la, str)


def test_pump_meet_source_cli_runs() -> None:
    result = subprocess.run(
        [
            "python3",
            "/opt/OS/scripts/pump_meet_source.py",
            "--meeting-code",
            "cli-test-pump",
            "--max",
            "3",
            "--no-attach",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode in (0, 1), result.stderr
    stdout = result.stdout.strip()
    assert stdout, f"no stdout; stderr={result.stderr}"
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"stdout not valid json: {e}\n{stdout[:400]}")
    # --no-attach prints source_status
    assert parsed.get("mode") == "no_attach", parsed
    assert "source_status" in parsed


def run_all() -> int:
    tests = [
        test_unified_report_has_new_keys,
        test_unified_report_existing_keys_preserved,
        test_meet_bridges_scan_picks_up_real_bridge,
        test_supervision_hints_bounded,
        test_continuity_block_safe_when_empty,
        test_ingress_keys_have_count_and_last_at,
        test_pump_meet_source_cli_runs,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok: {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL: {t.__name__}: {e}")
    if failed:
        print(f"\n{failed} failed")
        return 1
    print("\nCONTINUITY REPORT SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_all())
