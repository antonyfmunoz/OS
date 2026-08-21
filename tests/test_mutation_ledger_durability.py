import importlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest


def _reload_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path))
    return importlib.reload(importlib.import_module("transports.api.cockpit_audit"))


def _ledger_path(tmp_path: Path) -> Path:
    return tmp_path / "audit" / "mutation_ledger.jsonl"


def _event(request_id: str, *, target: str = "objective_plan:opr-1:plan_acceptance:v1"):
    return {
        "request_id": request_id,
        "timestamp": "2026-08-20T01:37:47.255500+00:00",
        "actor": "field",
        "domain": "approvals",
        "surface": "cockpit",
        "action": "approve",
        "target": target,
        "old_value": None,
        "new_value": {"source_type": "objective_plan"},
        "persisted": True,
        "constraint_warnings": [],
    }


def _line(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n"


def _transitional_line(audit, obj: dict, *, schema_version: str = "mutation-ledger-v2") -> str:
    record = dict(obj)
    record["_ledger"] = {
        "schema_version": schema_version,
        "record_type": "mutation_audit",
        "payload_sha256": audit._payload_sha256(record),
    }
    return json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"


def test_emit_mutation_audit_writes_fsync_validated_records(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)

    out = audit.emit_mutation_audit(
        "approvals",
        "approve",
        "objective_plan:opr-1:plan_acceptance:v1",
        actor="field",
        new_value={"source_type": "objective_plan"},
    )

    rows = audit.read_mutation_ledger()
    assert rows["parse_ok"] is True
    assert rows["integrity_ok"] is True
    assert rows["records"][0]["request_id"] == out["request_id"]
    assert rows["records"][0]["_ledger"]["schema_version"] == "mutation-ledger-v2"
    assert rows["records"][0]["_ledger"]["record_type"] == "mutation_audit"
    assert len(rows["records"][0]["_ledger"]["payload_sha256"]) == 64


def test_concurrent_mutation_writers_do_not_interleave(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)

    def write_one(i: int) -> None:
        audit.emit_mutation_audit("execution", "start", f"packet-{i}", new_value={"i": i})

    threads = [threading.Thread(target=write_one, args=(i,)) for i in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
        assert not t.is_alive()

    rows = audit.read_mutation_ledger()
    assert rows["parse_ok"] is True
    assert rows["integrity_ok"] is True
    assert len(rows["records"]) == 40
    assert len({r["request_id"] for r in rows["records"]}) == 40


def test_incomplete_object_plus_recoverable_object_repairs_to_truth_gap(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    before = _event("before")
    after = _event("after")
    recovered_obj = _event(recovered)
    damaged = (
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(recovered_obj, sort_keys=True)
        + "\n"
    )
    ledger.parent.mkdir(parents=True)
    ledger.write_text(_line(before) + damaged + _line(after), encoding="utf-8")
    original_digest = audit.file_sha256(ledger)

    invalid = audit.read_mutation_ledger()
    assert invalid["parse_ok"] is False
    assert invalid["malformed"][0]["line"] == 2

    result = audit.repair_mutation_ledger_truth_gap(
        expected_original_sha256=original_digest,
        malformed_line=2,
        unresolved_request_id=unresolved,
        recoverable_request_id=recovered,
        preservation_dir=tmp_path / "preserve",
        repair_authority="unit-test",
    )

    assert result["ok"] is True
    rows = audit.read_mutation_ledger()
    assert rows["parse_ok"] is True
    assert rows["integrity_ok"] is True
    assert [r["request_id"] for r in rows["records"]] == [before["request_id"], unresolved, recovered, after["request_id"]]
    gap = rows["records"][1]
    assert gap["_ledger"]["record_type"] == "integrity_gap"
    assert gap["resolution_status"] == "unresolved"
    assert gap["authority_disposition"] == "fail_closed"
    assert gap["replay_prohibited"] is True
    assert gap["unknown_fields"]
    assert rows["records"][2]["request_id"] == recovered
    assert rows["records"][2]["action"] == recovered_obj["action"]
    assert audit.request_authority_disposition(unresolved)["authority_disposition"] == "fail_closed"


def test_repair_refuses_wrong_original_digest(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    ledger.parent.mkdir(parents=True)
    ledger.write_text('{"request_id":"x","timestamp":"2026-08-20T0{"request_id":"y"}\n')

    with pytest.raises(audit.MutationLedgerRepairError):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256="0" * 64,
            malformed_line=1,
            unresolved_request_id="x",
            recoverable_request_id="y",
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
        )


def test_repair_accepts_strict_append_extension_and_preserves_tail(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    tail = [_event("tail-1"), _event("tail-2")]
    ledger.parent.mkdir(parents=True)
    original = (
        _line(_event("before"))
        + '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    ledger.write_text(original, encoding="utf-8")
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_bytes(ledger.read_bytes())
    original_digest = audit.file_sha256(ledger)
    ledger.write_text(original + "".join(_line(e) for e in tail), encoding="utf-8")
    frozen_digest = audit.file_sha256(ledger)
    malformed_line_sha = audit.hashlib.sha256(
        preserved_original.read_bytes().splitlines(keepends=True)[1]
    ).hexdigest()
    tail_bytes = b"".join(_line(e).encode("utf-8") for e in tail)

    result = audit.repair_mutation_ledger_truth_gap(
        expected_original_sha256=original_digest,
        malformed_line=2,
        unresolved_request_id=unresolved,
        recoverable_request_id=recovered,
        preservation_dir=tmp_path / "preserve",
        repair_authority="unit-test",
        preserved_original_path=preserved_original,
        expected_current_sha256=frozen_digest,
        expected_malformed_line_sha256=malformed_line_sha,
    )

    assert result["ok"] is True
    assert result["append_extension"] is True
    assert result["tail_sha256"] == audit.hashlib.sha256(tail_bytes).hexdigest()
    rows = audit.read_mutation_ledger()
    assert rows["parse_ok"] is True
    assert rows["integrity_ok"] is True
    assert [r["request_id"] for r in rows["records"]][-2:] == ["tail-1", "tail-2"]
    assert ledger.read_bytes().endswith(tail_bytes)


def test_repair_migrates_valid_transitional_append_tail(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    transitional = [_event("tail-transitional-1"), _event("tail-transitional-2")]
    current = audit._with_ledger_metadata(_event("tail-current"), "mutation_audit")
    ledger.parent.mkdir(parents=True)
    original = (
        _line(_event("before"))
        + '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    ledger.write_text(original, encoding="utf-8")
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_bytes(ledger.read_bytes())
    original_digest = audit.file_sha256(ledger)
    tail_text = "".join(_transitional_line(audit, event) for event in transitional) + _line(current)
    ledger.write_text(original + tail_text, encoding="utf-8")
    frozen_digest = audit.file_sha256(ledger)
    malformed_line_sha = audit.hashlib.sha256(
        preserved_original.read_bytes().splitlines(keepends=True)[1]
    ).hexdigest()

    result = audit.repair_mutation_ledger_truth_gap(
        expected_original_sha256=original_digest,
        malformed_line=2,
        unresolved_request_id=unresolved,
        recoverable_request_id=recovered,
        preservation_dir=tmp_path / "preserve",
        repair_authority="unit-test",
        preserved_original_path=preserved_original,
        expected_current_sha256=frozen_digest,
        expected_malformed_line_sha256=malformed_line_sha,
        migrate_transitional_tail_records=True,
    )

    assert result["ok"] is True
    migrations = result["transitional_tail_migrations"]
    assert [m["request_id"] for m in migrations] == [
        "tail-transitional-1",
        "tail-transitional-2",
    ]
    assert all(len(m["computed_integrity_sha256"]) == 64 for m in migrations)
    rows = audit.read_mutation_ledger()
    assert rows["parse_ok"] is True
    assert rows["integrity_ok"] is True
    tail_records = rows["records"][-3:]
    assert [r["request_id"] for r in tail_records] == [
        "tail-transitional-1",
        "tail-transitional-2",
        "tail-current",
    ]
    assert all("integrity_sha256" in r["_ledger"] for r in tail_records)
    assert result["migrated_tail_record_count"] == 2


def test_repair_refuses_transitional_tail_without_explicit_migration(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    original = (
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_text(original, encoding="utf-8")
    ledger.write_text(
        original + _transitional_line(audit, _event("tail-transitional")),
        encoding="utf-8",
    )

    with pytest.raises(audit.MutationLedgerRepairError, match="missing integrity_sha256"):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=audit.hashlib.sha256(original.encode("utf-8")).hexdigest(),
            malformed_line=1,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
            preserved_original_path=preserved_original,
            expected_current_sha256=audit.file_sha256(ledger),
        )


def test_repair_refuses_transitional_tail_payload_digest_mismatch(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    original = (
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    bad = json.loads(_transitional_line(audit, _event("tail-transitional")))
    bad["_ledger"]["payload_sha256"] = "0" * 64
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_text(original, encoding="utf-8")
    ledger.write_text(original + _line(bad), encoding="utf-8")

    with pytest.raises(audit.MutationLedgerRepairError, match="payload_sha256 mismatch"):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=audit.hashlib.sha256(original.encode("utf-8")).hexdigest(),
            malformed_line=1,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
            preserved_original_path=preserved_original,
            expected_current_sha256=audit.file_sha256(ledger),
            migrate_transitional_tail_records=True,
        )


def test_repair_refuses_transitional_tail_unknown_schema(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    original = (
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_text(original, encoding="utf-8")
    ledger.write_text(
        original
        + _transitional_line(audit, _event("tail-transitional"), schema_version="future"),
        encoding="utf-8",
    )

    with pytest.raises(audit.MutationLedgerRepairError, match="unsupported mutation ledger schema"):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=audit.hashlib.sha256(original.encode("utf-8")).hexdigest(),
            malformed_line=1,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
            preserved_original_path=preserved_original,
            expected_current_sha256=audit.file_sha256(ledger),
            migrate_transitional_tail_records=True,
        )


def test_repair_refuses_transitional_tail_missing_required_metadata(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    original = (
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    missing = json.loads(_transitional_line(audit, _event("tail-transitional")))
    missing["_ledger"].pop("record_type")
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_text(original, encoding="utf-8")
    ledger.write_text(original + _line(missing), encoding="utf-8")

    with pytest.raises(audit.MutationLedgerRepairError, match="unsupported mutation ledger record_type"):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=audit.hashlib.sha256(original.encode("utf-8")).hexdigest(),
            malformed_line=1,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
            preserved_original_path=preserved_original,
            expected_current_sha256=audit.file_sha256(ledger),
            migrate_transitional_tail_records=True,
        )


def test_repair_refuses_transitional_tail_extra_metadata(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    original = (
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    extra = json.loads(_transitional_line(audit, _event("tail-transitional")))
    extra["_ledger"]["unexpected"] = "metadata"
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_text(original, encoding="utf-8")
    ledger.write_text(original + _line(extra), encoding="utf-8")

    with pytest.raises(audit.MutationLedgerRepairError, match="transitional metadata not exact"):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=audit.hashlib.sha256(original.encode("utf-8")).hexdigest(),
            malformed_line=1,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
            preserved_original_path=preserved_original,
            expected_current_sha256=audit.file_sha256(ledger),
            migrate_transitional_tail_records=True,
        )


def test_repair_refuses_changed_prefix_for_append_extension(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    original = (
        _line(_event("before"))
        + '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_text(original, encoding="utf-8")
    ledger.write_text(original.replace("before", "mutated-before") + _line(_event("tail")), encoding="utf-8")

    with pytest.raises(audit.MutationLedgerRepairError, match="not a strict append"):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=audit.hashlib.sha256(original.encode("utf-8")).hexdigest(),
            malformed_line=2,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
            preserved_original_path=preserved_original,
            expected_current_sha256=audit.file_sha256(ledger),
        )


def test_repair_refuses_changed_malformed_fragment_digest(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    original = (
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_text(original, encoding="utf-8")
    ledger.write_text(original + _line(_event("tail")), encoding="utf-8")

    with pytest.raises(audit.MutationLedgerRepairError, match="malformed line digest"):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=audit.hashlib.sha256(original.encode("utf-8")).hexdigest(),
            malformed_line=1,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
            preserved_original_path=preserved_original,
            expected_current_sha256=audit.file_sha256(ledger),
            expected_malformed_line_sha256="0" * 64,
        )


def test_repair_refuses_malformed_appended_tail(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    original = (
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_text(original, encoding="utf-8")
    ledger.write_text(original + '{"request_id":"tail"', encoding="utf-8")

    with pytest.raises(audit.MutationLedgerRepairError, match="append tail failed validation"):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=audit.hashlib.sha256(original.encode("utf-8")).hexdigest(),
            malformed_line=1,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
            preserved_original_path=preserved_original,
            expected_current_sha256=audit.file_sha256(ledger),
        )


def test_repair_refuses_duplicate_appended_tail_record(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    original = (
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_text(original, encoding="utf-8")
    ledger.write_text(original + _line(_event(recovered)), encoding="utf-8")

    with pytest.raises(audit.MutationLedgerRepairError, match="append tail conflicts"):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=audit.hashlib.sha256(original.encode("utf-8")).hexdigest(),
            malformed_line=1,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
            preserved_original_path=preserved_original,
            expected_current_sha256=audit.file_sha256(ledger),
        )


def test_repair_refuses_file_changed_after_frozen_snapshot(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    original = (
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n"
    )
    preserved_original = tmp_path / "preserved-original.jsonl"
    preserved_original.write_text(original, encoding="utf-8")
    ledger.write_text(original + _line(_event("tail-1")), encoding="utf-8")
    frozen_digest = audit.file_sha256(ledger)
    ledger.write_text(ledger.read_text(encoding="utf-8") + _line(_event("tail-2")), encoding="utf-8")

    with pytest.raises(audit.MutationLedgerRepairError, match="frozen current digest"):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=audit.hashlib.sha256(original.encode("utf-8")).hexdigest(),
            malformed_line=1,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
            preserved_original_path=preserved_original,
            expected_current_sha256=frozen_digest,
        )


def test_repair_replay_is_idempotent_and_refuses_changed_source(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    original_digest = audit.file_sha256(ledger)
    kwargs = {
        "expected_original_sha256": original_digest,
        "malformed_line": 1,
        "unresolved_request_id": unresolved,
        "recoverable_request_id": recovered,
        "preservation_dir": tmp_path / "preserve",
        "repair_authority": "unit-test",
    }
    first = audit.repair_mutation_ledger_truth_gap(**kwargs)
    second = audit.repair_mutation_ledger_truth_gap(**kwargs)
    assert second["ok"] is True
    assert second["replayed"] is True
    assert second["repaired_sha256"] == first["repaired_sha256"]

    ledger.write_text(ledger.read_text() + _line(_event("new")), encoding="utf-8")
    with pytest.raises(audit.MutationLedgerRepairError):
        audit.repair_mutation_ledger_truth_gap(**kwargs)


def test_reader_fails_closed_when_authority_references_truth_gap(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    gap = audit.build_integrity_gap_record(
        unresolved_request_id="gap-1",
        original_file_sha256="a" * 64,
        malformed_line_sha256="b" * 64,
        byte_range=[10, 20],
        preserved_fragment_path="preserve/fragment.raw",
        preserved_fragment_sha256="c" * 64,
        visible_fields={"request_id": "gap-1"},
        unknown_fields=["action", "target", "outcome"],
        repair_id="repair-1",
        repair_authority="unit-test",
        recovered_second_object_sha256="d" * 64,
    )
    audit._append_mutation_record(gap)

    disposition = audit.request_authority_disposition("gap-1")
    assert disposition["authority_disposition"] == "fail_closed"
    assert disposition["may_derive_authority"] is False
    assert disposition["may_replay"] is False


def test_gap_record_is_non_authoritative_for_legacy_readers(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    gap = audit.build_integrity_gap_record(
        unresolved_request_id="gap-legacy",
        original_file_sha256="a" * 64,
        malformed_line_sha256="b" * 64,
        byte_range=[10, 20],
        preserved_fragment_path="preserve/fragment.raw",
        preserved_fragment_sha256="c" * 64,
        visible_fields={"request_id": "gap-legacy"},
        unknown_fields=["action", "target", "outcome"],
        repair_id="repair-legacy",
        repair_authority="unit-test",
        recovered_second_object_sha256="d" * 64,
    )
    audit._append_mutation_record(gap)

    raw = json.loads(_ledger_path(tmp_path).read_text())
    assert raw["persisted"] is False
    assert raw["authority_disposition"] == "fail_closed"
    assert raw["may_derive_authority"] is False


def test_record_type_tampering_is_detected(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    gap = audit.build_integrity_gap_record(
        unresolved_request_id="gap-tamper",
        original_file_sha256="a" * 64,
        malformed_line_sha256="b" * 64,
        byte_range=[10, 20],
        preserved_fragment_path="preserve/fragment.raw",
        preserved_fragment_sha256="c" * 64,
        visible_fields={"request_id": "gap-tamper"},
        unknown_fields=["action", "target", "outcome"],
        repair_id="repair-tamper",
        repair_authority="unit-test",
        recovered_second_object_sha256="d" * 64,
    )
    audit._append_mutation_record(gap)
    row = json.loads(_ledger_path(tmp_path).read_text())
    row["_ledger"]["record_type"] = "mutation_audit"
    _ledger_path(tmp_path).write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")

    rows = audit.read_mutation_ledger()
    assert rows["integrity_ok"] is False
    assert rows["integrity_errors"][0]["error"] == "integrity_sha256 mismatch"
    assert audit.request_authority_disposition("gap-tamper")["may_derive_authority"] is False


def test_duplicate_request_id_degrades_ledger_and_fails_closed(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    audit._append_mutation_record(_event("dupe"))
    audit._append_mutation_record(_event("dupe", target="other"))

    rows = audit.read_mutation_ledger()
    assert rows["integrity_ok"] is False
    assert rows["duplicate_request_ids"] == ["dupe"]
    disposition = audit.request_authority_disposition("dupe")
    assert disposition["may_derive_authority"] is False
    assert disposition["may_replay"] is False


def test_repair_lock_prevents_concurrent_append_loss(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    original_digest = audit.file_sha256(ledger)
    original_write = audit._write_preserved_bytes
    append_started = threading.Event()
    append_done = threading.Event()
    append_errors: list[BaseException] = []
    append_thread: threading.Thread | None = None

    def slow_write(path, data, mode=0o600):
        nonlocal append_thread
        if str(path).endswith(".original.jsonl"):
            def append_later() -> None:
                append_started.set()
                try:
                    audit.emit_mutation_audit("execution", "start", "late-append")
                except BaseException as exc:  # pragma: no cover - assertion reports below
                    append_errors.append(exc)
                finally:
                    append_done.set()

            append_thread = threading.Thread(target=append_later)
            append_thread.start()
            time.sleep(0.2)
            original_write(path, data, mode)
            return
        original_write(path, data, mode)

    monkeypatch.setattr(audit, "_write_preserved_bytes", slow_write)
    result = audit.repair_mutation_ledger_truth_gap(
        expected_original_sha256=original_digest,
        malformed_line=1,
        unresolved_request_id=unresolved,
        recoverable_request_id=recovered,
        preservation_dir=tmp_path / "preserve",
        repair_authority="unit-test",
    )
    assert result["ok"] is True
    assert append_started.is_set()
    assert append_thread is not None
    append_thread.join(timeout=5)
    assert append_done.is_set()
    assert not append_errors
    records = audit.read_mutation_ledger()["records"]
    assert records[-1]["target"] == "late-append"


def test_repair_refuses_to_promote_if_manifest_write_fails(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    unresolved = "568b9c5c-2455-4854-8efd-79eaf24419a0"
    recovered = "db337aeb-3eda-449e-a91e-e02f682c944c"
    ledger.parent.mkdir(parents=True)
    ledger.write_text(
        '{"request_id": "'
        + unresolved
        + '", "timestamp": "2026-08-20T0'
        + json.dumps(_event(recovered), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    original_digest = audit.file_sha256(ledger)
    original_write = audit._write_preserved_text

    def fail_manifest(path, text, mode=0o600):
        if str(path).endswith(".manifest.json"):
            raise OSError("manifest fsync failed")
        return original_write(path, text, mode)

    monkeypatch.setattr(audit, "_write_preserved_text", fail_manifest)
    with pytest.raises(OSError):
        audit.repair_mutation_ledger_truth_gap(
            expected_original_sha256=original_digest,
            malformed_line=1,
            unresolved_request_id=unresolved,
            recoverable_request_id=recovered,
            preservation_dir=tmp_path / "preserve",
            repair_authority="unit-test",
        )
    assert audit.file_sha256(ledger) == original_digest


def test_short_write_or_fsync_failure_does_not_ack_success(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    real_fsync = os.fsync

    def fail_fsync(_fd):
        raise OSError("fsync refused")

    monkeypatch.setattr(audit.os, "fsync", fail_fsync)
    with pytest.raises(audit.MutationLedgerDurabilityError):
        audit.emit_mutation_audit("execution", "start", "packet-x")
    monkeypatch.setattr(audit.os, "fsync", real_fsync)

    rows = audit.read_mutation_ledger()
    assert rows["parse_ok"] is True
    assert rows["records"] == []


def test_writer_death_during_append_leaves_reader_degraded_not_silent(tmp_path, monkeypatch):
    audit = _reload_audit(tmp_path, monkeypatch)
    ledger = _ledger_path(tmp_path)
    ledger.parent.mkdir(parents=True)
    script = (
        "from pathlib import Path; import os; "
        f"p=Path({str(ledger)!r}); p.open('ab').write(b'{{\"request_id\":\"dead\"'); os._exit(9)"
    )
    subprocess.run([sys.executable, "-c", script], check=False, timeout=5)

    rows = audit.read_mutation_ledger()
    assert rows["parse_ok"] is False
    assert rows["degraded"] is True
    assert rows["malformed"][0]["line"] == 1
