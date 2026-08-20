from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "schemas"
VALID_FIXTURES = ROOT / "fixtures" / "v1" / "valid"
INVALID_FIXTURES = ROOT / "fixtures" / "v1" / "invalid"
SUITE = ROOT / "fixtures" / "v1" / "fixture-suite.v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _schemas() -> list[dict[str, Any]]:
    return [_load_json(path) for path in sorted(SCHEMA_ROOT.rglob("*.schema.json"))]


def _suite() -> dict[str, Any]:
    return _load_json(SUITE)


def _registry() -> Registry:
    registry = Registry()
    for schema in _schemas():
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return registry


def _schema_by_title() -> dict[str, dict[str, Any]]:
    return {schema["title"]: schema for schema in _schemas()}


def _schema_by_id() -> dict[str, dict[str, Any]]:
    return {schema["$id"]: schema for schema in _schemas()}


def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(
        _schema_by_title()[schema_name],
        registry=_registry(),
        format_checker=FormatChecker(),
    )


def _pointer(value: Any, ptr: str | None) -> Any:
    if not ptr:
        return value
    current = value
    for part in ptr.split("/")[1:]:
        current = current[part]
    return current


def _fixture(entry: list[str]) -> tuple[Path, str, Any]:
    fixture_path = ROOT / entry[0]
    schema_name = entry[1]
    payload = _pointer(_load_json(fixture_path), entry[2] if len(entry) > 2 else None)
    return fixture_path, schema_name, payload


def _assert_valid(schema_name: str, payload: Any) -> None:
    errors = sorted(_validator(schema_name).iter_errors(payload), key=lambda e: list(e.path))
    assert errors == [], [error.message for error in errors]


def _assert_invalid(schema_name: str, payload: Any) -> None:
    errors = sorted(_validator(schema_name).iter_errors(payload), key=lambda e: list(e.path))
    assert errors, f"{schema_name} unexpectedly accepted payload"


def _load_generated_models():
    sys.path.insert(0, str(ROOT / "generated" / "python"))
    from foundation_contracts import models

    return models


def _commands_by_type() -> dict[str, dict[str, Any]]:
    return {
        command["commandType"]: command
        for command in _load_json(ROOT / "registry" / "commands.v1.json")["commands"]
    }


def _events_by_type() -> dict[str, dict[str, Any]]:
    return {
        event["eventType"]: event
        for event in _load_json(ROOT / "registry" / "events.v1.json")["events"]
    }


def _normalized(value: Any) -> str:
    def normalize_numbers(item: Any) -> Any:
        if isinstance(item, float) and item.is_integer():
            return int(item)
        if isinstance(item, list):
            return [normalize_numbers(child) for child in item]
        if isinstance(item, dict):
            return {key: normalize_numbers(child) for key, child in item.items()}
        return item

    value = normalize_numbers(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _dump_model(model: Any) -> dict[str, Any]:
    return model.model_dump(exclude_unset=True)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _state_machine_errors(schema: dict[str, Any]) -> list[str]:
    meta = schema.get("x-umh", {}).get("stateMachine")
    if not meta:
        return []
    declared = set(meta["states"])
    enum_values: set[str] = set()
    for name in ("status", "state"):
        prop = schema.get("properties", {}).get(name, {})
        enum_values.update(prop.get("enum", []))
    errors = []
    if enum_values and enum_values != declared:
        errors.append(f"{schema['title']}: state enum drift {sorted(enum_values)} != {sorted(declared)}")
    for transition in meta.get("legalTransitions", []):
        if transition[0] not in declared or transition[1] not in declared:
            errors.append(f"{schema['title']}: transition references unknown state {transition}")
    for terminal in meta.get("terminalStates", []):
        if terminal not in declared:
            errors.append(f"{schema['title']}: terminal state not declared {terminal}")
    return errors


def _field_value_semantic_errors(definitions: list[dict[str, Any]], values: list[dict[str, Any]]) -> list[str]:
    defs = {definition["id"]: definition["field_type"] for definition in definitions}
    errors: list[str] = []
    for value in values:
        expected = defs.get(value["field_id"])
        if expected and expected != value["field_type"]:
            errors.append("field_type_does_not_match_stable_field_definition")
        if expected == "number" and not isinstance(value["value"], (int, float)):
            errors.append("number_field_value_must_be_numeric")
        if expected in {"text", "rich_text", "email", "phone", "url"} and not isinstance(value["value"], str):
            errors.append("textual_field_value_must_be_string")
        if expected == "boolean" and not isinstance(value["value"], bool):
            errors.append("boolean_field_value_must_be_boolean")
    return errors


def _transaction_balance_errors(transaction: dict[str, Any]) -> list[str]:
    totals: dict[str, dict[str, float]] = {}
    for line in transaction["lines"]:
        bucket = totals.setdefault(line["currency"], {"debit": 0.0, "credit": 0.0})
        bucket[line["line_type"]] += float(line["amount"])
    return [
        f"unbalanced_transaction:{currency}"
        for currency, values in totals.items()
        if round(values["debit"] - values["credit"], 8) != 0
    ]


def test_json_schema_valid_fixture_suite() -> None:
    for entry in _suite()["valid"]:
        _, schema_name, payload = _fixture(entry)
        _assert_valid(schema_name, payload)


def test_json_schema_invalid_fixture_suite_fails_closed() -> None:
    for entry in _suite()["invalid"]:
        _, schema_name, payload = _fixture(entry)
        _assert_invalid(schema_name, payload)


def test_generated_python_bindings_round_trip_valid_fixtures() -> None:
    models = _load_generated_models()
    for entry in _suite()["valid"]:
        _, schema_name, payload = _fixture(entry)
        model = getattr(models, schema_name)
        assert _normalized(_dump_model(model.model_validate(payload))) == _normalized(payload)


def test_generated_python_bindings_reject_invalid_fixtures() -> None:
    models = _load_generated_models()
    for entry in _suite()["invalid"]:
        _, schema_name, payload = _fixture(entry)
        with pytest.raises(Exception):
            getattr(models, schema_name).model_validate(payload)


def test_generated_zod_fixture_suites_validate_and_reject() -> None:
    subprocess.run(["npm", "run", "validate:valid"], cwd=ROOT, check=True, capture_output=True, text=True)
    subprocess.run(["npm", "run", "validate:invalid"], cwd=ROOT, check=True, capture_output=True, text=True)


def test_registry_integrity_and_reference_resolution() -> None:
    schemas = _schemas()
    schema_ids = [schema["$id"] for schema in schemas]
    schema_titles = [schema["title"] for schema in schemas]
    assert len(schema_ids) == len(set(schema_ids))
    assert len(schema_titles) == len(set(schema_titles))

    schemas_by_id = _schema_by_id()
    commands = _commands_by_type()
    events = _events_by_type()
    for command_type, command in commands.items():
        assert command_type.endswith(".v1")
        assert command["semanticVersion"] == "1.0.0"
        assert command["envelopeSchema"] in schemas_by_id
        assert command["payloadSchema"] in schemas_by_id
        payload_schema = schemas_by_id[command["payloadSchema"]]
        assert payload_schema["x-umh"]["commandType"] == command_type
        assert command["expectedEventTypes"], f"{command_type} missing expected events"
        for event_type in command["expectedEventTypes"]:
            assert event_type in events

    aggregate_types = {
        "Person",
        "Relationship",
        "Interaction",
        "File",
        "Message",
        "Document",
        "Database",
        "Record",
        "FormSubmission",
        "Reservation",
        "Transaction",
        "Invoice",
    }
    for event_type, event in events.items():
        assert event_type.endswith(".v1")
        assert event["semanticVersion"] == "1.0.0"
        assert event["envelopeSchema"] in schemas_by_id
        assert event["payloadSchema"] in schemas_by_id
        assert event["aggregateObjectType"] in aggregate_types
        payload_schema = schemas_by_id[event["payloadSchema"]]
        assert payload_schema["x-umh"]["eventType"] == event_type


def test_command_event_pairing_and_canonical_rename_drift() -> None:
    commands = _commands_by_type()
    assert commands["CreatePerson.v1"]["expectedEventTypes"] == ["PersonCreated.v1"]
    assert commands["RecordInteraction.v1"]["expectedEventTypes"] == ["InteractionRecorded.v1"]
    assert commands["TrashFile.v1"]["expectedEventTypes"] == ["FileTrashed.v1"]
    assert commands["RestoreFile.v1"]["expectedEventTypes"] == ["FileRestored.v1"]
    assert commands["QueueMessage.v1"]["expectedEventTypes"] == ["MessageQueued.v1"]
    assert commands["RequestDocumentReview.v1"]["expectedEventTypes"] == ["DocumentReviewRequested.v1"]
    assert commands["SubmitReviewDecision.v1"]["expectedEventTypes"] == ["ReviewDecisionSubmitted.v1"]
    assert commands["CreateDatabase.v1"]["expectedEventTypes"] == ["DatabaseCreated.v1"]
    assert commands["CreateRecord.v1"]["expectedEventTypes"] == ["RecordCreated.v1"]
    assert commands["SubmitForm.v1"]["expectedEventTypes"] == ["FormSubmitted.v1"]
    assert commands["CreateReservation.v1"]["expectedEventTypes"] == ["ReservationCreated.v1"]
    assert commands["PostTransaction.v1"]["expectedEventTypes"] == ["TransactionPosted.v1"]
    assert commands["IssueInvoice.v1"]["expectedEventTypes"] == ["InvoiceIssued.v1"]

    forbidden_commands = {"CreateContact.v1", "LogInteraction.v1", "DeleteFile.v1", "SubmitDocumentReview.v1"}
    forbidden_events = {"ContactCreated.v1", "InteractionLogged.v1", "FileDeleted.v1", "DocumentReviewSubmitted.v1"}
    assert forbidden_commands.isdisjoint(commands)
    assert forbidden_events.isdisjoint(_events_by_type())


def test_aliases_are_migration_only_and_targets_resolve() -> None:
    aliases = _load_json(ROOT / "registry" / "legacy-aliases.v1.json")["aliases"]
    canonical_commands = set(_commands_by_type())
    canonical_events = set(_events_by_type())
    canonical_objects = {schema["title"] for schema in _schemas()} | {
        schema.get("x-umh", {}).get("canonicalName") for schema in _schemas()
    }
    for alias in aliases:
        assert alias["status"] == "migration-alias-only"
        assert alias["legacyName"] != alias["canonicalName"]
        target = alias["canonicalName"]
        assert target in canonical_commands | canonical_events | canonical_objects

    _assert_valid("CommandEnvelope", _load_json(INVALID_FIXTURES / "log-interaction-command-alias.invalid.json"))
    _assert_valid("CommandEnvelope", _load_json(INVALID_FIXTURES / "delete-file-command-alias.invalid.json"))


def test_state_machine_metadata_matches_schema_state_values() -> None:
    errors: list[str] = []
    for schema in _schemas():
        errors.extend(_state_machine_errors(schema))
    assert errors == []


def test_cross_domain_semantic_conformance_rules() -> None:
    relationship = _load_json(INVALID_FIXTURES / "relationship-self.invalid.json")
    assert relationship["subject_ref"]["objectId"] == relationship["object_ref"]["objectId"]

    stale = _load_json(INVALID_FIXTURES / "stale-review-target.semantic-invalid.json")
    assert stale["command"]["payload"]["revision_id"] != stale["document"]["current_revision_id"]

    collapsed = _load_json(INVALID_FIXTURES / "approval-publication-collapsed.semantic-invalid.json")
    assert collapsed["review_decision"]["decision"] == "approved"
    assert collapsed["document"]["status"] == "published"

    db_mismatch = _load_json(INVALID_FIXTURES / "record-value-type-mismatch.semantic-invalid.json")
    assert _field_value_semantic_errors(db_mismatch["field_definitions"], db_mismatch["record"]["values"]) == [
        "number_field_value_must_be_numeric"
    ]

    form_mismatch = _load_json(INVALID_FIXTURES / "form-submission-value-type-mismatch.semantic-invalid.json")
    assert _field_value_semantic_errors(form_mismatch["form"]["fields"], form_mismatch["submission"]["values"]) == [
        "number_field_value_must_be_numeric"
    ]

    reservation = _load_json(INVALID_FIXTURES / "reservation-end-before-start.semantic-invalid.json")
    assert _parse_time(reservation["end_at"]) <= _parse_time(reservation["start_at"])

    transaction = _load_json(INVALID_FIXTURES / "transaction-unbalanced.semantic-invalid.json")
    assert _transaction_balance_errors(transaction) == ["unbalanced_transaction:USD"]

    mutation = _load_json(INVALID_FIXTURES / "posted-transaction-mutation.semantic-invalid.json")
    assert mutation["before"]["status"] == "posted"
    assert mutation["before"]["id"] == mutation["after"]["id"]
    assert mutation["before"]["lines"] != mutation["after"]["lines"]


def test_message_retry_attempt_history_and_internal_note_boundary() -> None:
    receipt_schema = _schema_by_title()["DeliveryReceipt"]
    assert "delivery_attempt_id" in receipt_schema["required"]
    assert receipt_schema["x-umh"]["historyRule"].startswith("retry-creates-new-delivery-attempt")
    _assert_invalid("Message", _load_json(INVALID_FIXTURES / "internal-note-as-outbound-message.invalid.json"))


def test_compatibility_policy_and_extension_namespace_rules() -> None:
    compatibility = _load_json(ROOT / "registry" / "compatibility.v1.json")
    ranges = {item["contract"] for item in compatibility["supportedRanges"]}
    assert {
        "foundation.envelopes",
        "foundation.identity",
        "foundation.files",
        "foundation.messages",
        "foundation.docs",
        "foundation.databases",
        "foundation.forms",
        "foundation.calendar",
        "foundation.finance",
    }.issubset(ranges)
    for schema in _schemas():
        meta = schema.get("x-umh", {})
        assert meta.get("contractVersion") == "1.0.0"
        assert meta.get("compatibility") in {"minor-additive", None}


def test_generated_artifact_manifest_is_complete() -> None:
    manifest = _load_json(ROOT / "generated" / "artifact-manifest.v1.json")
    schemas = _schemas()
    assert manifest["schemaCount"] == len(schemas)
    assert manifest["commandCount"] == len(_commands_by_type())
    assert manifest["eventCount"] == len(_events_by_type())
    assert manifest["aliasCount"] == len(_load_json(ROOT / "registry" / "legacy-aliases.v1.json")["aliases"])
    manifest_ids = {schema["schemaId"] for schema in manifest["schemas"]}
    assert manifest_ids == {schema["$id"] for schema in schemas}
    assert "pythonModels" in manifest["generatedArtifacts"]
    assert "typescriptRuntime" in manifest["generatedArtifacts"]
