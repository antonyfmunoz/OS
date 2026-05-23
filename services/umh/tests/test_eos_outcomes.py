"""Tests for EOS outcome receiver — Phase 3 writeback logic."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.umh.integrations.eos.correlation import EOSCorrelationMap, EOSWritebackTarget
from services.umh.integrations.eos.outcomes import EOSOutcomeReceiver, _build_audit_payload
from services.umh.integrations.eos.tables import (
    SEVERITY_LADDER,
    SOURCE_ROW_UPDATE_TYPES,
    outcome_severity,
)
from substrate.sockets.envelopes import OutcomeEnvelope


def _make_envelope(
    outcome_type: str = "success",
    correlation_id: Any = None,
    summary: str = "test outcome",
    result_data: dict[str, Any] | None = None,
) -> OutcomeEnvelope:
    return OutcomeEnvelope(
        outcome_id=uuid4(),
        signal_id=uuid4(),
        trace_id=uuid4(),
        integration_id="eos",
        outcome_type=outcome_type,
        summary=summary,
        result_data=result_data or {},
        correlation_id=correlation_id,
    )


def _make_receiver(
    correlation_map: EOSCorrelationMap | None = None,
) -> EOSOutcomeReceiver:
    return EOSOutcomeReceiver(
        database_url="postgresql://fake:fake@localhost/fake",
        correlation_map=correlation_map or EOSCorrelationMap(),
    )


def _mock_conn() -> MagicMock:
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = ("new-id",)
    return conn


# ---------------------------------------------------------------------------
# Severity ladder
# ---------------------------------------------------------------------------


class TestSeverityLadder:
    def test_severity_order(self) -> None:
        assert outcome_severity("success") < outcome_severity("timeout")
        assert outcome_severity("timeout") < outcome_severity("governance_denied")
        assert outcome_severity("governance_denied") < outcome_severity("error")

    def test_unknown_type_gets_max_severity(self) -> None:
        assert outcome_severity("unknown_thing") > outcome_severity("error")

    def test_all_ladder_entries_present(self) -> None:
        assert set(SEVERITY_LADDER.keys()) == {"success", "timeout", "governance_denied", "error"}


# ---------------------------------------------------------------------------
# Source row update types (Decision 4)
# ---------------------------------------------------------------------------


class TestSourceRowUpdateTypes:
    def test_success_updates_source_row(self) -> None:
        assert "success" in SOURCE_ROW_UPDATE_TYPES

    def test_timeout_updates_source_row(self) -> None:
        assert "timeout" in SOURCE_ROW_UPDATE_TYPES

    def test_governance_denied_updates_source_row(self) -> None:
        assert "governance_denied" in SOURCE_ROW_UPDATE_TYPES

    def test_error_does_not_update_source_row(self) -> None:
        assert "error" not in SOURCE_ROW_UPDATE_TYPES

    def test_failure_does_not_update_source_row(self) -> None:
        assert "failure" not in SOURCE_ROW_UPDATE_TYPES


# ---------------------------------------------------------------------------
# Audit payload builder
# ---------------------------------------------------------------------------


class TestBuildAuditPayload:
    def test_basic_fields(self) -> None:
        env = _make_envelope(summary="hello world", outcome_type="success")
        payload = _build_audit_payload(env)
        assert payload["signal_id"] == str(env.signal_id)
        assert payload["outcome_type"] == "success"
        assert payload["summary"] == "hello world"
        assert "confidence" in payload
        assert "duration_ms" in payload

    def test_summary_truncated_to_500(self) -> None:
        env = _make_envelope(summary="x" * 1000)
        payload = _build_audit_payload(env)
        assert len(payload["summary"]) == 500

    def test_optional_fields_included_when_present(self) -> None:
        env = OutcomeEnvelope(
            outcome_id=uuid4(),
            signal_id=uuid4(),
            trace_id=uuid4(),
            integration_id="eos",
            outcome_type="success",
            summary="ok",
            governance_decision="approved",
            result_data={"key": "val"},
            metadata={"m": 1},
        )
        payload = _build_audit_payload(env)
        assert payload["governance_decision"] == "approved"
        assert payload["result_data"] == {"key": "val"}
        assert payload["metadata"] == {"m": 1}

    def test_optional_fields_excluded_when_empty(self) -> None:
        env = _make_envelope()
        payload = _build_audit_payload(env)
        assert "governance_decision" not in payload
        assert "metadata" not in payload


# ---------------------------------------------------------------------------
# Outcome receiver: no correlation
# ---------------------------------------------------------------------------


class TestNoCorrelation:
    def test_no_correlation_id_skips(self) -> None:
        receiver = _make_receiver()
        env = _make_envelope(correlation_id=None)
        receiver.on_outcome(env)
        # No exception, no DB call

    def test_correlation_not_in_map_skips(self) -> None:
        receiver = _make_receiver()
        env = _make_envelope(correlation_id=uuid4())
        receiver.on_outcome(env)

    def test_wrong_integration_skips(self) -> None:
        cmap = EOSCorrelationMap()
        cid = uuid4()
        cmap.register(
            cid,
            EOSWritebackTarget(
                org_id="org-1", table_name="events", row_id="row-1", integration="notion"
            ),
        )
        receiver = _make_receiver(cmap)
        env = _make_envelope(correlation_id=cid)
        receiver.on_outcome(env)
        assert cmap.lookup(cid) is not None  # not removed


# ---------------------------------------------------------------------------
# Outcome receiver: success writeback
# ---------------------------------------------------------------------------


class TestSuccessWriteback:
    @patch("services.umh.integrations.eos.outcomes.insert_umh_outcome", return_value="audit-1")
    @patch("services.umh.integrations.eos.outcomes.update_umh_status", return_value=True)
    @patch.object(EOSOutcomeReceiver, "_get_connection")
    def test_success_writes_both(
        self, mock_conn: MagicMock, mock_update: MagicMock, mock_insert: MagicMock
    ) -> None:
        cmap = EOSCorrelationMap()
        cid = uuid4()
        cmap.register(cid, EOSWritebackTarget(org_id="org-1", table_name="events", row_id="row-1"))
        receiver = _make_receiver(cmap)
        mock_conn.return_value = _mock_conn()

        env = _make_envelope(outcome_type="success", correlation_id=cid)
        receiver.on_outcome(env)

        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args.kwargs.get("table_name", call_args[0][1]) == "events"
        assert call_args.kwargs.get("new_status", call_args[0][3]) == "success"

        mock_insert.assert_called_once()

        assert cmap.lookup(cid) is None  # cleaned up

    @patch("services.umh.integrations.eos.outcomes.insert_umh_outcome", return_value="audit-1")
    @patch("services.umh.integrations.eos.outcomes.update_umh_status", return_value=True)
    @patch.object(EOSOutcomeReceiver, "_get_connection")
    def test_timeout_writes_both(
        self, mock_conn: MagicMock, mock_update: MagicMock, mock_insert: MagicMock
    ) -> None:
        cmap = EOSCorrelationMap()
        cid = uuid4()
        cmap.register(cid, EOSWritebackTarget(org_id="org-1", table_name="clients", row_id="row-2"))
        receiver = _make_receiver(cmap)
        mock_conn.return_value = _mock_conn()

        env = _make_envelope(outcome_type="timeout", correlation_id=cid)
        receiver.on_outcome(env)

        mock_update.assert_called_once()
        mock_insert.assert_called_once()


# ---------------------------------------------------------------------------
# Outcome receiver: failure writeback (Decision 4)
# ---------------------------------------------------------------------------


class TestFailureWriteback:
    @patch("services.umh.integrations.eos.outcomes.insert_umh_outcome", return_value="audit-1")
    @patch("services.umh.integrations.eos.outcomes.update_umh_status")
    @patch.object(EOSOutcomeReceiver, "_get_connection")
    def test_error_skips_source_row_writes_audit(
        self, mock_conn: MagicMock, mock_update: MagicMock, mock_insert: MagicMock
    ) -> None:
        cmap = EOSCorrelationMap()
        cid = uuid4()
        cmap.register(cid, EOSWritebackTarget(org_id="org-1", table_name="events", row_id="row-1"))
        receiver = _make_receiver(cmap)
        mock_conn.return_value = _mock_conn()

        env = _make_envelope(outcome_type="error", correlation_id=cid)
        receiver.on_outcome(env)

        mock_update.assert_not_called()
        mock_insert.assert_called_once()

    @patch("services.umh.integrations.eos.outcomes.insert_umh_outcome", return_value="audit-1")
    @patch("services.umh.integrations.eos.outcomes.update_umh_status")
    @patch.object(EOSOutcomeReceiver, "_get_connection")
    def test_failure_skips_source_row_writes_audit(
        self, mock_conn: MagicMock, mock_update: MagicMock, mock_insert: MagicMock
    ) -> None:
        cmap = EOSCorrelationMap()
        cid = uuid4()
        cmap.register(cid, EOSWritebackTarget(org_id="org-1", table_name="clients", row_id="row-2"))
        receiver = _make_receiver(cmap)
        mock_conn.return_value = _mock_conn()

        env = _make_envelope(outcome_type="failure", correlation_id=cid)
        receiver.on_outcome(env)

        mock_update.assert_not_called()
        mock_insert.assert_called_once()


# ---------------------------------------------------------------------------
# Outcome receiver: governance_denied writeback
# ---------------------------------------------------------------------------


class TestGovernanceDeniedWriteback:
    @patch("services.umh.integrations.eos.outcomes.insert_umh_outcome", return_value="audit-1")
    @patch("services.umh.integrations.eos.outcomes.update_umh_status", return_value=True)
    @patch.object(EOSOutcomeReceiver, "_get_connection")
    def test_governance_denied_writes_both(
        self, mock_conn: MagicMock, mock_update: MagicMock, mock_insert: MagicMock
    ) -> None:
        cmap = EOSCorrelationMap()
        cid = uuid4()
        cmap.register(
            cid, EOSWritebackTarget(org_id="org-1", table_name="ventures", row_id="row-3")
        )
        receiver = _make_receiver(cmap)
        mock_conn.return_value = _mock_conn()

        env = _make_envelope(outcome_type="governance_denied", correlation_id=cid)
        receiver.on_outcome(env)

        mock_update.assert_called_once()
        mock_insert.assert_called_once()


# ---------------------------------------------------------------------------
# Outcome receiver: severity enforcement (Decision 5)
# ---------------------------------------------------------------------------


class TestSeverityEnforcement:
    @patch("services.umh.integrations.eos.outcomes.insert_umh_outcome", return_value="audit-1")
    @patch("services.umh.integrations.eos.outcomes.update_umh_status", return_value=False)
    @patch.object(EOSOutcomeReceiver, "_get_connection")
    def test_lower_severity_does_not_overwrite(
        self, mock_conn: MagicMock, mock_update: MagicMock, mock_insert: MagicMock
    ) -> None:
        """update_umh_status returns False when current severity is higher."""
        cmap = EOSCorrelationMap()
        cid = uuid4()
        cmap.register(cid, EOSWritebackTarget(org_id="org-1", table_name="events", row_id="row-1"))
        receiver = _make_receiver(cmap)
        mock_conn.return_value = _mock_conn()

        env = _make_envelope(outcome_type="success", correlation_id=cid)
        receiver.on_outcome(env)

        # Source update attempted but returned False (higher severity already set)
        mock_update.assert_called_once()
        # Audit still inserted
        mock_insert.assert_called_once()
        # Correlation still cleaned up
        assert cmap.lookup(cid) is None


# ---------------------------------------------------------------------------
# Outcome receiver: no row_id (capability-direct with missing row)
# ---------------------------------------------------------------------------


class TestNoRowId:
    @patch("services.umh.integrations.eos.outcomes.insert_umh_outcome", return_value="audit-1")
    @patch("services.umh.integrations.eos.outcomes.update_umh_status")
    @patch.object(EOSOutcomeReceiver, "_get_connection")
    def test_no_row_id_skips_source_update(
        self, mock_conn: MagicMock, mock_update: MagicMock, mock_insert: MagicMock
    ) -> None:
        cmap = EOSCorrelationMap()
        cid = uuid4()
        cmap.register(cid, EOSWritebackTarget(org_id="org-1", table_name="events", row_id=""))
        receiver = _make_receiver(cmap)
        mock_conn.return_value = _mock_conn()

        env = _make_envelope(outcome_type="success", correlation_id=cid)
        receiver.on_outcome(env)

        mock_update.assert_not_called()
        mock_insert.assert_called_once()


# ---------------------------------------------------------------------------
# tables.py Phase 3 helpers — unit tests
# ---------------------------------------------------------------------------


class TestUpdateUmhStatus:
    def test_invalid_table_raises(self) -> None:
        conn = _mock_conn()
        with pytest.raises(ValueError, match="invalid source table"):
            from services.umh.integrations.eos.tables import update_umh_status

            update_umh_status(conn, "nonexistent_table", "row-1", "success")

    def test_valid_call(self) -> None:
        from services.umh.integrations.eos.tables import update_umh_status

        conn = _mock_conn()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("row-1",)

        result = update_umh_status(conn, "events", "row-1", "success")
        assert result is True
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()

    def test_row_not_found_returns_false(self) -> None:
        from services.umh.integrations.eos.tables import update_umh_status

        conn = _mock_conn()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None

        result = update_umh_status(conn, "events", "row-1", "success")
        assert result is False


class TestInsertUmhOutcome:
    def test_invalid_table_raises(self) -> None:
        conn = _mock_conn()
        with pytest.raises(ValueError, match="invalid source table"):
            from services.umh.integrations.eos.tables import insert_umh_outcome

            insert_umh_outcome(conn, "trace-1", "bad_table", "row-1", "org-1", "success", 0, {})

    def test_valid_call(self) -> None:
        from services.umh.integrations.eos.tables import insert_umh_outcome

        conn = _mock_conn()
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("audit-id-1",)

        result = insert_umh_outcome(
            conn, "trace-1", "events", "row-1", "org-1", "success", 0, {"key": "val"}
        )
        assert result == "audit-id-1"
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()
