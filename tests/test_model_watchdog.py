"""
Behavioral tests for the model watchdog.

Exercises real temp files, real JSON, real cursors — not mocked internals.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time

import pytest

sys.path.insert(0, "/opt/OS")

# Patch module-level constants before import
_test_tmpdir = tempfile.mkdtemp(prefix="mw_test_")


def _patch_constants():
    """Patch module constants to use temp dirs."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "model_watchdog",
        os.path.join(os.path.dirname(__file__), "..", "scripts", "model-watchdog.py"),
    )
    mw = importlib.util.module_from_spec(spec)
    sys.modules["model_watchdog"] = mw
    spec.loader.exec_module(mw)

    mw.STATE_DIR = os.path.join(_test_tmpdir, "state")
    mw.CURSOR_FILE = os.path.join(mw.STATE_DIR, "cursors.json")
    mw.PROVENANCE_FILE = os.path.join(mw.STATE_DIR, "provenance.jsonl")
    mw.HEALTH_FILE = os.path.join(mw.STATE_DIR, "health.json")
    mw.SETTINGS_LOCK = os.path.join(mw.STATE_DIR, "settings.lock")
    mw.LOG_FILE = os.path.join(_test_tmpdir, "watchdog.log")
    mw.DISCORD_BOT_TOKEN = ""
    mw.DISCORD_CHANNEL_ID = ""
    os.makedirs(mw.STATE_DIR, exist_ok=True)
    return mw


mw = _patch_constants()


@pytest.fixture(autouse=True)
def _clean_provenance():
    """Remove provenance file between tests to prevent cross-test leakage."""
    yield
    for f in [mw.PROVENANCE_FILE, mw.CURSOR_FILE, mw.HEALTH_FILE]:
        try:
            os.unlink(f)
        except FileNotFoundError:
            pass


def _make_settings(tmpdir: str, model: str = "claude-fable-5[1m]") -> str:
    path = os.path.join(tmpdir, "settings.json")
    with open(path, "w") as f:
        json.dump(
            {
                "model": model,
                "theme": "dark",
                "permissions": {"allow": ["Read"]},
            },
            f,
            indent=4,
        )
    return path


def _make_transcript(tmpdir: str, entries: list[dict]) -> str:
    path = os.path.join(tmpdir, "transcript.jsonl")
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    return path


def _assistant_entry(model: str, turn_id: str = "msg_001") -> dict:
    return {
        "type": "assistant",
        "message": {
            "id": turn_id,
            "model": model,
            "role": "assistant",
            "content": [{"type": "text", "text": "test"}],
        },
    }


def _user_entry() -> dict:
    return {"type": "human", "message": {"role": "user", "content": "test"}}


class TestTargetModelDetection:
    def test_target_model_is_match(self):
        wd = mw.ModelWatchdog()
        assert wd._is_target_model("claude-fable-5") is True

    def test_target_model_with_suffix(self):
        wd = mw.ModelWatchdog()
        assert wd._is_target_model("claude-fable-5-20260801") is True

    def test_wrong_model_is_not_match(self):
        wd = mw.ModelWatchdog()
        assert wd._is_target_model("claude-opus-4-6") is False
        assert wd._is_target_model("claude-opus-4-8") is False
        assert wd._is_target_model("claude-opus-5") is False

    def test_empty_model_is_not_match(self):
        wd = mw.ModelWatchdog()
        assert wd._is_target_model("") is False


class TestTranscriptParsing:
    def test_desired_model_no_remediation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_transcript(
                tmpdir,
                [
                    _user_entry(),
                    _assistant_entry("claude-fable-5"),
                    _user_entry(),
                    _assistant_entry("claude-fable-5"),
                ],
            )
            wd = mw.ModelWatchdog()
            # First call establishes cursor at end
            obs = wd._check_transcript(path, "test-session-1")
            assert obs == []  # first discovery, no replay

            # Append more target-model entries
            with open(path, "a") as f:
                f.write(json.dumps(_assistant_entry("claude-fable-5")) + "\n")

            obs = wd._check_transcript(path, "test-session-1")
            assert len(obs) == 1
            assert obs[0][0] == "claude-fable-5"

    def test_wrong_model_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_transcript(
                tmpdir,
                [
                    _assistant_entry("claude-fable-5"),
                ],
            )
            wd = mw.ModelWatchdog()
            wd._check_transcript(path, "s1")  # establish cursor

            with open(path, "a") as f:
                f.write(json.dumps(_assistant_entry("claude-opus-4-6")) + "\n")

            obs = wd._check_transcript(path, "s1")
            assert len(obs) == 1
            assert obs[0][0] == "claude-opus-4-6"

    def test_malformed_line_contained(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_transcript(tmpdir, [])
            wd = mw.ModelWatchdog()
            wd._check_transcript(path, "s1")

            with open(path, "a") as f:
                f.write("NOT VALID JSON\n")
                f.write(json.dumps(_assistant_entry("claude-opus-5")) + "\n")
                f.write("{incomplete\n")
                f.write(json.dumps(_assistant_entry("claude-fable-5")) + "\n")

            obs = wd._check_transcript(path, "s1")
            assert len(obs) == 2
            assert obs[0][0] == "claude-opus-5"
            assert obs[1][0] == "claude-fable-5"

    def test_no_model_field_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_transcript(tmpdir, [])
            wd = mw.ModelWatchdog()
            wd._check_transcript(path, "s1")

            entry_no_model = {"type": "assistant", "message": {"id": "x", "role": "assistant"}}
            with open(path, "a") as f:
                f.write(json.dumps(entry_no_model) + "\n")

            obs = wd._check_transcript(path, "s1")
            assert len(obs) == 0

    def test_synthetic_model_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_transcript(tmpdir, [])
            wd = mw.ModelWatchdog()
            wd._check_transcript(path, "s1")

            with open(path, "a") as f:
                f.write(json.dumps(_assistant_entry("<synthetic>")) + "\n")

            obs = wd._check_transcript(path, "s1")
            assert len(obs) == 0


class TestCursorPersistence:
    def test_cursor_survives_save_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_transcript(
                tmpdir,
                [
                    _assistant_entry("claude-fable-5"),
                    _assistant_entry("claude-fable-5"),
                ],
            )
            wd1 = mw.ModelWatchdog()
            wd1._check_transcript(path, "persist-test")
            wd1._save_cursors()

            # New watchdog loads saved cursors
            wd2 = mw.ModelWatchdog()
            assert path in wd2._cursors
            assert wd2._cursors[path].offset > 0

            # No new data → no observations
            obs = wd2._check_transcript(path, "persist-test")
            assert obs == []

    def test_no_historical_replay_after_restart(self):
        """Historical wrong-model records must not trigger alerts on restart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_transcript(
                tmpdir,
                [
                    _assistant_entry("claude-opus-4-8"),
                    _assistant_entry("claude-opus-4-8"),
                    _assistant_entry("claude-opus-4-8"),
                ],
            )
            # First watchdog discovers transcript but doesn't replay
            wd1 = mw.ModelWatchdog()
            obs = wd1._check_transcript(path, "restart-test")
            assert obs == []  # first discovery skips to end

            wd1._save_cursors()

            # Restart: load cursors, no new data
            wd2 = mw.ModelWatchdog()
            obs = wd2._check_transcript(path, "restart-test")
            assert obs == []

    def test_truncation_resumes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_transcript(
                tmpdir,
                [
                    _assistant_entry("claude-fable-5"),
                    _assistant_entry("claude-fable-5"),
                    _assistant_entry("claude-fable-5"),
                ],
            )
            wd = mw.ModelWatchdog()
            wd._check_transcript(path, "trunc-test")

            # Truncate to smaller size
            with open(path, "w") as f:
                f.write(json.dumps(_assistant_entry("claude-opus-4-6")) + "\n")

            obs = wd._check_transcript(path, "trunc-test")
            assert len(obs) == 1
            assert obs[0][0] == "claude-opus-4-6"

    def test_rotation_detected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _make_transcript(
                tmpdir,
                [
                    _assistant_entry("claude-fable-5"),
                ],
            )
            wd = mw.ModelWatchdog()
            wd._check_transcript(path, "rot-test")
            old_inode = wd._cursors[path].inode

            # Delete and recreate (different inode)
            os.unlink(path)
            with open(path, "w") as f:
                f.write(json.dumps(_assistant_entry("claude-opus-5")) + "\n")

            new_inode = os.stat(path).st_ino
            if new_inode != old_inode:
                obs = wd._check_transcript(path, "rot-test")
                assert len(obs) == 1
                assert obs[0][0] == "claude-opus-5"

    def test_corrupt_cursor_file_handled(self):
        os.makedirs(mw.STATE_DIR, exist_ok=True)
        with open(mw.CURSOR_FILE, "w") as f:
            f.write("NOT JSON{{{")

        wd = mw.ModelWatchdog()
        assert len(wd._cursors) == 0


class TestSettingsWrite:
    def test_wrong_model_corrected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            mw.SETTINGS_FILE = _make_settings(tmpdir, "claude-opus-4-8[1m]")
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            try:
                wd = mw.ModelWatchdog()
                changed, detail = wd._ensure_settings_model()
                assert changed is True
                with open(mw.SETTINGS_FILE) as f:
                    data = json.load(f)
                assert data["model"] == "claude-fable-5[1m]"
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock

    def test_correct_model_no_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            mw.SETTINGS_FILE = _make_settings(tmpdir, "claude-fable-5[1m]")
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            try:
                wd = mw.ModelWatchdog()
                changed, detail = wd._ensure_settings_model()
                assert changed is False
                assert "already correct" in detail
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock

    def test_unrelated_settings_preserved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            mw.SETTINGS_FILE = _make_settings(tmpdir, "claude-opus-4-6[1m]")
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            try:
                wd = mw.ModelWatchdog()
                wd._ensure_settings_model()
                with open(mw.SETTINGS_FILE) as f:
                    data = json.load(f)
                assert data["theme"] == "dark"
                assert data["permissions"] == {"allow": ["Read"]}
                assert data["model"] == "claude-fable-5[1m]"
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock

    def test_concurrent_writes_no_corruption(self):
        """Two threads writing settings must not corrupt JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            mw.SETTINGS_FILE = _make_settings(tmpdir, "claude-opus-4-8[1m]")
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")

            errors = []

            def write_settings():
                try:
                    wd = mw.ModelWatchdog()
                    wd._ensure_settings_model()
                except Exception as e:
                    errors.append(str(e))

            try:
                threads = [threading.Thread(target=write_settings) for _ in range(5)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=10)

                # Verify JSON is valid after all writes
                with open(mw.SETTINGS_FILE) as f:
                    data = json.load(f)
                assert data["model"] == "claude-fable-5[1m]"
                assert data["theme"] == "dark"
                assert not errors, f"Errors during concurrent writes: {errors}"
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock

    def test_malformed_settings_handled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            path = os.path.join(tmpdir, "settings.json")
            with open(path, "w") as f:
                f.write("NOT JSON{{{")
            mw.SETTINGS_FILE = path
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            try:
                wd = mw.ModelWatchdog()
                changed, detail = wd._ensure_settings_model()
                assert changed is False
                assert "failed" in detail.lower() or "read" in detail.lower()
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock

    def test_missing_settings_handled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            mw.SETTINGS_FILE = os.path.join(tmpdir, "nonexistent.json")
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            try:
                wd = mw.ModelWatchdog()
                changed, detail = wd._ensure_settings_model()
                assert changed is False
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock


class TestProvenance:
    def test_provenance_records_actual_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            mw.SETTINGS_FILE = _make_settings(tmpdir, "claude-opus-4-6[1m]")
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            try:
                wd = mw.ModelWatchdog()
                observations = [("claude-opus-4-6", "msg_001")]
                wd._handle_observations("test-sid", "/tmp/t.jsonl", observations)

                # Read provenance
                events = []
                with open(mw.PROVENANCE_FILE) as f:
                    for line in f:
                        events.append(json.loads(line))

                assert len(events) == 1
                e = events[0]
                assert e["observed_model"] == "claude-opus-4-6"
                assert e["desired_model"] == "claude-fable-5"
                assert e["match"] is False
                assert e["remediation_required"] is True
                assert e["remediation_attempted"] is True
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock

    def test_provenance_immutable_after_remediation(self):
        """Remediation must not overwrite the fact that prior turn used wrong model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            mw.SETTINGS_FILE = _make_settings(tmpdir, "claude-opus-4-8[1m]")
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            try:
                wd = mw.ModelWatchdog()

                wd._handle_observations("s1", "/t.jsonl", [("claude-opus-4-8", "m1")])
                wd._handle_observations("s1", "/t.jsonl", [("claude-fable-5", "m2")])

                events = []
                with open(mw.PROVENANCE_FILE) as f:
                    for line in f:
                        events.append(json.loads(line))

                deviation_events = [e for e in events if not e["match"]]
                match_events = [e for e in events if e["match"]]

                assert len(deviation_events) == 1
                assert deviation_events[0]["observed_model"] == "claude-opus-4-8"
                assert len(match_events) == 1
                assert match_events[0]["observed_model"] == "claude-fable-5"
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock


class TestCooldownAndAlerts:
    def test_cooldown_suppresses_duplicate_alerts(self):
        wd = mw.ModelWatchdog()
        wd._sessions["s1"] = mw.SessionState(
            last_alert_time=time.time(),
            cooldown_seconds=60,
        )
        assert wd._should_alert("s1") is False

    def test_cooldown_allows_after_expiry(self):
        wd = mw.ModelWatchdog()
        wd._sessions["s1"] = mw.SessionState(
            last_alert_time=time.time() - 120,
            cooldown_seconds=60,
        )
        assert wd._should_alert("s1") is True

    def test_new_session_always_alerts(self):
        wd = mw.ModelWatchdog()
        assert wd._should_alert("brand-new-session") is True

    def test_burst_limit_enforced(self):
        wd = mw.ModelWatchdog()
        now = time.time()
        wd._global_alerts = [now - i for i in range(mw.ALERT_BURST_LIMIT)]

        # Even new session should be suppressed
        assert wd._should_alert("new-session") is False

    def test_different_sessions_independent(self):
        wd = mw.ModelWatchdog()
        wd._sessions["s1"] = mw.SessionState(
            last_alert_time=time.time(),
            cooldown_seconds=60,
        )
        assert wd._should_alert("s1") is False
        assert wd._should_alert("s2") is True


class TestDiscordFailureContainment:
    def test_discord_failure_does_not_block_remediation(self):
        """Discord failure must not prevent settings correction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            old_token = mw.DISCORD_BOT_TOKEN
            old_channel = mw.DISCORD_CHANNEL_ID

            mw.SETTINGS_FILE = _make_settings(tmpdir, "claude-opus-4-6[1m]")
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            mw.DISCORD_BOT_TOKEN = "fake-token-will-fail"
            mw.DISCORD_CHANNEL_ID = "000000000"

            try:
                wd = mw.ModelWatchdog()
                wd._handle_observations("s1", "/t.jsonl", [("claude-opus-4-6", "m1")])

                with open(mw.SETTINGS_FILE) as f:
                    data = json.load(f)
                assert data["model"] == "claude-fable-5[1m]"

                events = []
                with open(mw.PROVENANCE_FILE) as f:
                    for line in f:
                        events.append(json.loads(line))
                assert len(events) >= 1
                assert events[-1]["remediation_attempted"] is True
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock
                mw.DISCORD_BOT_TOKEN = old_token
                mw.DISCORD_CHANNEL_ID = old_channel


class TestSummary:
    def test_summary_math(self):
        """Summary counters must match known fixtures."""
        # Write known provenance
        events = [
            {
                "timestamp": "2026-08-06T10:00:00",
                "session_id": "s1",
                "desired_model": "claude-fable-5",
                "observed_model": "claude-fable-5",
                "match": True,
                "remediation_required": False,
                "remediation_attempted": False,
                "remediation_succeeded": False,
            },
            {
                "timestamp": "2026-08-06T10:01:00",
                "session_id": "s1",
                "desired_model": "claude-fable-5",
                "observed_model": "claude-opus-4-8",
                "match": False,
                "remediation_required": True,
                "remediation_attempted": True,
                "remediation_succeeded": True,
            },
            {
                "timestamp": "2026-08-06T10:02:00",
                "session_id": "s1",
                "desired_model": "claude-fable-5",
                "observed_model": "claude-opus-4-8",
                "match": False,
                "remediation_required": True,
                "remediation_attempted": True,
                "remediation_succeeded": True,
            },
            {
                "timestamp": "2026-08-06T10:03:00",
                "session_id": "s1",
                "desired_model": "claude-fable-5",
                "observed_model": "claude-fable-5",
                "match": True,
                "remediation_required": False,
                "remediation_attempted": False,
                "remediation_succeeded": False,
            },
        ]
        with open(mw.PROVENANCE_FILE, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        summary = mw.generate_summary()
        assert summary["total_observed"] == 4
        assert summary["target_matches"] == 2
        assert summary["substituted_turns"] == 2
        assert summary["substitution_rate"] == "50.0%"
        assert summary["observed_models"]["claude-fable-5"] == 2
        assert summary["observed_models"]["claude-opus-4-8"] == 2
        assert summary["remediation_attempts"] == 2
        assert summary["remediation_successes"] == 2
        # fable→opus (1), opus→opus (same), opus→fable (2)
        assert summary["model_transitions"] == 2

    def test_summary_session_filter(self):
        events = [
            {
                "timestamp": "2026-08-06T10:00:00",
                "session_id": "session-a",
                "desired_model": "claude-fable-5",
                "observed_model": "claude-opus-4-8",
                "match": False,
            },
            {
                "timestamp": "2026-08-06T10:01:00",
                "session_id": "session-b",
                "desired_model": "claude-fable-5",
                "observed_model": "claude-fable-5",
                "match": True,
            },
        ]
        with open(mw.PROVENANCE_FILE, "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")

        summary = mw.generate_summary(session_id="session-a")
        assert summary["total_observed"] == 1
        assert summary["substituted_turns"] == 1


class TestHealthCounters:
    def test_health_tracking(self):
        wd = mw.ModelWatchdog()
        assert wd._health.polls_total == 0
        assert wd._health.watchdog_version == mw.WATCHDOG_VERSION

    def test_health_save_load(self):
        wd = mw.ModelWatchdog()
        wd._health.polls_total = 42
        wd._health.remediation_successes = 7
        wd._save_health()

        with open(mw.HEALTH_FILE) as f:
            data = json.load(f)
        assert data["polls_total"] == 42
        assert data["remediation_successes"] == 7


class TestAtomicWrite:
    def test_atomic_write_produces_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            data = {"key": "value", "nested": {"a": 1}}
            assert mw.ModelWatchdog._atomic_write_json(path, data) is True

            with open(path) as f:
                loaded = json.load(f)
            assert loaded == data

    def test_atomic_write_replaces_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            mw.ModelWatchdog._atomic_write_json(path, {"v": 1})
            mw.ModelWatchdog._atomic_write_json(path, {"v": 2})

            with open(path) as f:
                data = json.load(f)
            assert data["v"] == 2


class TestIntentionalTargetChange:
    def test_env_target_respected(self):
        """If MODEL_WATCHDOG_TARGET changes, the new target is enforced."""
        old_target = mw.TARGET_MODEL
        try:
            mw.TARGET_MODEL = "claude-opus-5"
            wd = mw.ModelWatchdog()
            assert wd._is_target_model("claude-opus-5") is True
            assert wd._is_target_model("claude-fable-5") is False
        finally:
            mw.TARGET_MODEL = old_target


class TestAdversarial:
    """Adversarial tests — verify mutations would be caught."""

    def test_inverting_model_equality_caught(self):
        """If match logic were inverted, target model would be flagged."""
        wd = mw.ModelWatchdog()
        assert wd._is_target_model("claude-fable-5") is True
        assert wd._is_target_model("claude-opus-4-6") is False

    def test_unknown_model_not_treated_as_target(self):
        wd = mw.ModelWatchdog()
        assert wd._is_target_model("UNKNOWN") is False
        assert wd._is_target_model("") is False

    def test_provenance_not_rewritten_after_remediation(self):
        """Observed_model must remain the ACTUAL model, not the desired model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            mw.SETTINGS_FILE = _make_settings(tmpdir, "claude-opus-4-6[1m]")
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            try:
                wd = mw.ModelWatchdog()
                wd._handle_observations("s1", "/t.jsonl", [("claude-opus-4-6", "m1")])

                with open(mw.PROVENANCE_FILE) as f:
                    events = [json.loads(l) for l in f if l.strip()]

                for e in events:
                    if not e["match"]:
                        assert e["observed_model"] == "claude-opus-4-6"
                        assert e["observed_model"] != e["desired_model"]
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock

    def test_settings_not_truncated(self):
        """Settings must preserve all keys, not just model."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            path = os.path.join(tmpdir, "settings.json")
            original = {
                "model": "claude-opus-4-8[1m]",
                "$schema": "https://example.com",
                "theme": "dark",
                "permissions": {"allow": ["Read", "Write"]},
                "hooks": {"onSave": "echo saved"},
                "custom_key": [1, 2, 3],
            }
            with open(path, "w") as f:
                json.dump(original, f, indent=4)
            mw.SETTINGS_FILE = path
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            try:
                wd = mw.ModelWatchdog()
                wd._ensure_settings_model()

                with open(path) as f:
                    result = json.load(f)

                for key in original:
                    if key == "model":
                        continue
                    assert key in result, f"Key '{key}' was dropped"
                    assert result[key] == original[key], f"Key '{key}' was modified"
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock

    def test_cooldown_not_global_only(self):
        """Per-session cooldown must not suppress independent sessions."""
        wd = mw.ModelWatchdog()
        wd._sessions["s1"] = mw.SessionState(
            last_alert_time=time.time(),
            cooldown_seconds=600,
        )
        # s2 must not be blocked by s1's cooldown
        assert wd._should_alert("s2") is True

    def test_remediation_attempted_vs_succeeded_distinct(self):
        """Remediation attempted must not imply succeeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_settings = mw.SETTINGS_FILE
            old_lock = mw.SETTINGS_LOCK
            path = os.path.join(tmpdir, "settings.json")
            with open(path, "w") as f:
                f.write("CORRUPT")
            mw.SETTINGS_FILE = path
            mw.SETTINGS_LOCK = os.path.join(tmpdir, "settings.lock")
            try:
                wd = mw.ModelWatchdog()
                wd._handle_observations("s1", "/t.jsonl", [("claude-opus-4-6", "m1")])

                with open(mw.PROVENANCE_FILE) as f:
                    events = [json.loads(l) for l in f if l.strip()]

                deviation = [e for e in events if not e["match"]]
                assert len(deviation) == 1
                assert deviation[0]["remediation_attempted"] is True
                assert deviation[0]["remediation_succeeded"] is False
            finally:
                mw.SETTINGS_FILE = old_settings
                mw.SETTINGS_LOCK = old_lock
