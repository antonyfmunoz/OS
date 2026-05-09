"""Tests for Phase 96.8AP — Workstation Relay Autostart and Self-Heal.

Verifies:
  1. Autostart marker read/write
  2. Heartbeat age computation
  3. Relay health assessment (online, offline, stale, degraded)
  4. Autostart detection in health report
  5. Chrome-proof dispatch gating
  6. Offline relay blocks execution
  7. Fresh heartbeat allows execution
  8. Stale heartbeat triggers restart recommendation
  9. Denial reasons propagated correctly
  10. Self-heal module integration with existing heartbeat
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, "/opt/OS")
sys.path.insert(0, "/opt/OS/services")


class TestAutostartMarker:
    def test_no_marker_returns_none(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            read_autostart_marker,
        )

        result = read_autostart_marker(tmp_path)
        assert result is None

    def test_valid_marker(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            AUTOSTART_MARKER_PATH,
            read_autostart_marker,
        )

        marker_path = tmp_path / AUTOSTART_MARKER_PATH
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(
            json.dumps(
                {
                    "task_name": "EOS-WorkstationRelay",
                    "installed_at": "2026-05-09T12:00:00.000Z",
                    "machine_name": "DESKTOP-TEST",
                }
            )
        )

        result = read_autostart_marker(tmp_path)
        assert result is not None
        assert result["task_name"] == "EOS-WorkstationRelay"

    def test_corrupt_marker(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            AUTOSTART_MARKER_PATH,
            read_autostart_marker,
        )

        marker_path = tmp_path / AUTOSTART_MARKER_PATH
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text("not json {{{")

        result = read_autostart_marker(tmp_path)
        assert result is None


class TestHeartbeatAge:
    def test_fresh_heartbeat_age(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import RelayHeartbeat
        from core.workstation.workstation_relay_self_heal_v1 import (
            compute_heartbeat_age,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(timestamp=now.isoformat())
        age = compute_heartbeat_age(hb, now=now)
        assert 0 <= age < 1

    def test_old_heartbeat_age(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import RelayHeartbeat
        from core.workstation.workstation_relay_self_heal_v1 import (
            compute_heartbeat_age,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(timestamp=(now - timedelta(seconds=120)).isoformat())
        age = compute_heartbeat_age(hb, now=now)
        assert 119 < age < 121

    def test_no_heartbeat_returns_negative(self) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            compute_heartbeat_age,
        )

        age = compute_heartbeat_age(None)
        assert age == -1

    def test_empty_timestamp_returns_negative(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import RelayHeartbeat
        from core.workstation.workstation_relay_self_heal_v1 import (
            compute_heartbeat_age,
        )

        hb = RelayHeartbeat()
        hb.timestamp = ""
        age = compute_heartbeat_age(hb)
        assert age == -1

    def test_z_suffix_parsed(self) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import RelayHeartbeat
        from core.workstation.workstation_relay_self_heal_v1 import (
            compute_heartbeat_age,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat()
        hb.timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        age = compute_heartbeat_age(hb, now=now)
        assert 0 <= age < 2


class TestRelayHealthAssessment:
    def test_healthy_relay(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_relay_self_heal_v1 import (
            assess_relay_health,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-healthy",
            desktop_session_active=True,
            desktop_unlocked=True,
            chrome_available=True,
            timestamp=now.isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        report = assess_relay_health(tmp_path, now=now)
        assert report.online is True
        assert report.health == "alive"
        assert report.execution_allowed is True
        assert report.heartbeat_fresh is True
        assert report.heartbeat_stale is False
        assert report.denial_reason == ""

    def test_offline_no_heartbeat(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            assess_relay_health,
        )

        report = assess_relay_health(tmp_path)
        assert report.online is False
        assert report.health == "dead"
        assert report.execution_allowed is False
        assert report.denial_reason == "relay_offline"
        assert report.restart_recommended is True

    def test_stale_heartbeat(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_relay_self_heal_v1 import (
            assess_relay_health,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-stale",
            desktop_session_active=True,
            chrome_available=True,
            timestamp=(now - timedelta(seconds=120)).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        report = assess_relay_health(tmp_path, now=now)
        assert report.online is False
        assert report.health == "timeout"
        assert report.restart_recommended is True
        assert report.execution_allowed is False

    def test_degraded_heartbeat(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_relay_self_heal_v1 import (
            assess_relay_health,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-degraded",
            desktop_session_active=True,
            desktop_unlocked=True,
            chrome_available=True,
            timestamp=(now - timedelta(seconds=35)).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        report = assess_relay_health(tmp_path, now=now, stale_seconds=60)
        assert report.online is True
        assert report.health == "degraded"
        assert report.execution_allowed is True

    def test_no_desktop_denies_execution(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_relay_self_heal_v1 import (
            assess_relay_health,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-nodesktop",
            desktop_session_active=False,
            chrome_available=True,
            timestamp=now.isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        report = assess_relay_health(tmp_path, now=now)
        assert report.online is True
        assert report.execution_allowed is False
        assert report.denial_reason == "no_desktop_session"

    def test_no_chrome_denies_execution(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_relay_self_heal_v1 import (
            assess_relay_health,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-nochrome",
            desktop_session_active=True,
            chrome_available=False,
            timestamp=now.isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        report = assess_relay_health(tmp_path, now=now)
        assert report.online is True
        assert report.execution_allowed is False
        assert report.denial_reason == "chrome_unavailable"


class TestAutostartInHealthReport:
    def test_autostart_detected(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            AUTOSTART_MARKER_PATH,
            assess_relay_health,
        )

        marker_path = tmp_path / AUTOSTART_MARKER_PATH
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        marker_path.write_text(
            json.dumps(
                {
                    "task_name": "EOS-WorkstationRelay",
                    "installed_at": "2026-05-09T12:00:00.000Z",
                }
            )
        )

        report = assess_relay_health(tmp_path)
        assert report.autostart_installed is True
        assert report.autostart_task_name == "EOS-WorkstationRelay"

    def test_no_autostart(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            assess_relay_health,
        )

        report = assess_relay_health(tmp_path)
        assert report.autostart_installed is False
        assert report.autostart_task_name == ""


class TestChromeProofGating:
    def test_healthy_relay_allows_chrome_proof(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_relay_self_heal_v1 import (
            should_allow_chrome_proof,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-gate-ok",
            desktop_session_active=True,
            desktop_unlocked=True,
            chrome_available=True,
            timestamp=now.isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        allowed, reason = should_allow_chrome_proof(tmp_path)
        assert allowed is True
        assert reason == "relay_healthy"

    def test_offline_blocks_chrome_proof(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            should_allow_chrome_proof,
        )

        allowed, reason = should_allow_chrome_proof(tmp_path)
        assert allowed is False
        assert "relay_offline" in reason

    def test_stale_blocks_chrome_proof(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_relay_self_heal_v1 import (
            should_allow_chrome_proof,
        )

        hb = RelayHeartbeat(
            node_id="WRN-gate-stale",
            desktop_session_active=True,
            chrome_available=True,
            timestamp=(datetime.now(timezone.utc) - timedelta(seconds=300)).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        allowed, reason = should_allow_chrome_proof(tmp_path)
        assert allowed is False

    def test_no_chrome_blocks_proof(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_relay_self_heal_v1 import (
            should_allow_chrome_proof,
        )

        hb = RelayHeartbeat(
            node_id="WRN-gate-nochrome",
            desktop_session_active=True,
            chrome_available=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        allowed, reason = should_allow_chrome_proof(tmp_path)
        assert allowed is False
        assert reason == "chrome_unavailable"


class TestHealthReportSerialization:
    def test_to_dict_serializable(self) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            RelayHealthReport,
        )

        report = RelayHealthReport(
            online=True,
            health="alive",
            autostart_installed=True,
            heartbeat_age_seconds=5.123,
            execution_allowed=True,
        )
        d = report.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0
        assert d["online"] is True
        assert d["heartbeat_age_seconds"] == 5.1

    def test_offline_report_dict(self) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            RelayHealthReport,
        )

        report = RelayHealthReport()
        d = report.to_dict()
        assert d["online"] is False
        assert d["denial_reason"] == ""


class TestSelfHealIntegration:
    def test_assess_uses_existing_heartbeat(self, tmp_path: Path) -> None:
        from core.workstation.workstation_relay_heartbeat_v1 import (
            RelayHeartbeat,
            write_relay_heartbeat,
        )
        from core.workstation.workstation_relay_self_heal_v1 import (
            assess_relay_health,
        )

        now = datetime.now(timezone.utc)
        hb = RelayHeartbeat(
            node_id="WRN-integration",
            machine_name="DESKTOP-INT",
            desktop_session_active=True,
            desktop_unlocked=True,
            chrome_available=True,
            capabilities=["launch_chrome"],
            timestamp=now.isoformat(),
        )
        write_relay_heartbeat(hb, tmp_path)

        report = assess_relay_health(tmp_path, now=now)
        assert report.online is True
        assert report.heartbeat_age_seconds < 1
        assert report.execution_allowed is True

    def test_live_vps_health_check(self) -> None:
        from core.workstation.workstation_relay_self_heal_v1 import (
            assess_relay_health,
        )

        report = assess_relay_health(Path("/opt/OS"))
        assert isinstance(report.online, bool)
        assert report.health in ("alive", "degraded", "timeout", "dead")
        d = report.to_dict()
        assert "execution_allowed" in d
