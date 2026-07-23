"""Wave 2 C7 — field failure-injection policy is ACTUALLY consumed (review W1).

Pins that the ``.inject_failure`` marker written by the dispatcher's
``inject-failure`` subcommand changes the computed dispatch tool policy — so the
failure-qualification pass injects a GENUINE worker failure and cannot silently
run clean (a false green). Also pins that the marker is scoped: only task A's
first attempt is revoked; the retry and all other tasks run unrevoked.
"""

from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from substrate.execution.attempts.field_failure_policy import (  # noqa: E402
    disallowed_tools_for,
    read_variant,
)


def test_no_marker_is_clean(tmp_path):
    assert read_variant(str(tmp_path)) == ""
    assert disallowed_tools_for(targets_dir=str(tmp_path), task_id="A", attempt_number=1) == []


def test_clean_marker_is_clean(tmp_path):
    (tmp_path / ".inject_failure").write_text("clean", encoding="utf-8")
    assert read_variant(str(tmp_path)) == ""
    assert disallowed_tools_for(targets_dir=str(tmp_path), task_id="A", attempt_number=1) == []


def test_tools_revoked_a_revokes_A_first_attempt(tmp_path):
    (tmp_path / ".inject_failure").write_text("tools-revoked-a", encoding="utf-8")
    revoked = disallowed_tools_for(targets_dir=str(tmp_path), task_id="A", attempt_number=1)
    # A genuine, real revocation of every file-mutation tool → worker can't commit.
    assert set(revoked) == {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def test_tools_revoked_a_matches_task_id_forms(tmp_path):
    (tmp_path / ".inject_failure").write_text("tools-revoked-a", encoding="utf-8")
    for tid in ("A", "a", "wp-a", "task-a", "A-1"):
        assert disallowed_tools_for(targets_dir=str(tmp_path), task_id=tid, attempt_number=1), tid


def test_tools_revoked_a_does_not_touch_retry_or_other_tasks(tmp_path):
    (tmp_path / ".inject_failure").write_text("tools-revoked-a", encoding="utf-8")
    # Retry (attempt 2) of A runs UNREVOKED — this is what proves recovery works.
    assert disallowed_tools_for(targets_dir=str(tmp_path), task_id="A", attempt_number=2) == []
    # B, C, D never revoked.
    for tid in ("B", "C", "D", "wp-b"):
        assert disallowed_tools_for(targets_dir=str(tmp_path), task_id=tid, attempt_number=1) == []


def test_marker_actually_changes_policy(tmp_path):
    """The load-bearing anti-W1 assertion: arming the marker CHANGES the output.
    Without this, inject-failure would be a dead write and the failure pass a
    false green."""
    before = disallowed_tools_for(targets_dir=str(tmp_path), task_id="A", attempt_number=1)
    (tmp_path / ".inject_failure").write_text("tools-revoked-a", encoding="utf-8")
    after = disallowed_tools_for(targets_dir=str(tmp_path), task_id="A", attempt_number=1)
    assert before == [] and after != [], "arming the marker must change the dispatch policy"
